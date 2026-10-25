import cherrypy
import pytest

import plexpy
import plexpy.config
from plexpy import versioncheck, webserve


@pytest.fixture
def flatpak(monkeypatch):
    for name, value in (('FLATPAK', True), ('DOCKER', False), ('SNAP', False), ('FROZEN', False)):
        monkeypatch.setattr(plexpy, name, value)
    monkeypatch.setattr(plexpy, 'INSTALL_TYPE', None)
    monkeypatch.setattr(plexpy, 'PROG_DIR', '/app')
    monkeypatch.setattr(versioncheck.os.path, 'isdir', lambda path: False)
    monkeypatch.setattr(versioncheck, 'get_version_from_file', lambda: ('abc123', 'nightly'))


def test_flatpak_install_type(flatpak):
    assert versioncheck.get_version() == ('abc123', 'origin', 'nightly')
    assert plexpy.INSTALL_TYPE == 'flatpak'


def test_flatpak_is_off_by_default():
    assert plexpy.FLATPAK is False


def test_flatpak_update_does_nothing(flatpak, monkeypatch):
    monkeypatch.setattr(plexpy, 'INSTALL_TYPE', 'flatpak')
    calls = []
    # Without the guard, update() would take the git branch and call runGit.
    monkeypatch.setattr(versioncheck, 'runGit', lambda *args: calls.append(args))
    monkeypatch.setattr(versioncheck, 'valid_git_refs', lambda: calls.append('refs') or True)
    monkeypatch.setattr(versioncheck, 'download_and_extract', lambda *a, **k: calls.append('dl'), raising=False)

    assert versioncheck.update() is None
    assert calls == []


@pytest.mark.parametrize('same_release, expected', [(False, 'release'), (True, False)])
def test_flatpak_update_is_a_release_never_a_commit(flatpak, monkeypatch, same_release, expected):
    monkeypatch.setattr(versioncheck, 'check_github', lambda **kwargs: None)
    monkeypatch.setattr(plexpy, 'CURRENT_VERSION', 'abc123')
    monkeypatch.setattr(plexpy, 'LATEST_VERSION', 'def456')
    monkeypatch.setattr(plexpy, 'COMMITS_BEHIND', 3)
    monkeypatch.setattr(plexpy, 'LATEST_RELEASE', 'v2.0.0' if same_release else 'v2.1.0')
    monkeypatch.setattr(plexpy.common, 'BRANCH', 'nightly')
    monkeypatch.setattr(plexpy.common, 'RELEASE', 'v2.0.0')
    monkeypatch.setattr(plexpy, 'WIN_SYS_TRAY_ICON', None)
    monkeypatch.setattr(plexpy, 'MAC_SYS_TRAY_ICON', None)

    versioncheck.check_update()

    assert plexpy.UPDATE_AVAILABLE == ('release' if not same_release else False)


@pytest.fixture
def github(flatpak, app_config, monkeypatch):
    commits = [{'sha': 'c1', 'commit': {'message': 'Fix a bug'}},
               {'sha': 'c2', 'commit': {'message': 'Bump version [skip ci]'}},
               {'sha': 'c3', 'commit': {'message': 'Update changelog [skip ci]'}}]
    data = {'version': {'sha': 'c3'}, 'commits': {'ahead_by': 3, 'commits': commits},
            'releases': [{'tag_name': 'v2.1.0', 'prerelease': False, 'target_commitish': 'x'}]}
    app_config.GIT_BRANCH = 'nightly'
    app_config.GIT_TOKEN = ''
    app_config.PLEXPY_AUTO_UPDATE = 1
    monkeypatch.setattr(versioncheck, 'github_cache',
                        lambda name, github_data=None, use_cache=True: data[name] if github_data is None else None)
    monkeypatch.setattr(plexpy, 'CURRENT_VERSION', 'abc123')
    shutdowns = []
    monkeypatch.setattr(plexpy, 'shutdown', lambda **kwargs: shutdowns.append(kwargs))
    return shutdowns


def test_flatpak_never_updates_itself(github):
    versioncheck.check_github(scheduler=True)

    assert plexpy.COMMITS_BEHIND > 0
    assert github == []


def test_flatpak_skips_ci_commits_on_nightly(github, caplog):
    with caplog.at_level('DEBUG', logger='tautulli'):
        versioncheck.check_github()

    assert 'Flatpak 1 commits behind' in caplog.text
    assert plexpy.COMMITS_BEHIND == 1
    assert plexpy.LATEST_VERSION == 'c1'


@pytest.mark.parametrize('update_available, expected', [('release', 'flatpak'), (False, 'flatpak')])
def test_update_check_reports_flatpak(flatpak, app_config, monkeypatch, update_available, expected):
    monkeypatch.setattr(versioncheck, 'check_update', lambda: None)
    monkeypatch.setattr(plexpy, 'INSTALL_TYPE', 'flatpak')
    monkeypatch.setattr(plexpy, 'UPDATE_AVAILABLE', update_available)

    assert webserve.WebInterface().update_check()['install_type'] == expected


def test_update_endpoint_redirects_flatpak(flatpak, app_config, monkeypatch):
    state = []
    app_config.UPDATE_SHOW_CHANGELOG = 0
    monkeypatch.setattr(plexpy, 'HTTP_ROOT', '/')
    monkeypatch.setattr(webserve.WebInterface, 'do_state_change', lambda self, *a, **k: state.append(a))

    with pytest.raises(cherrypy.HTTPRedirect):
        webserve.WebInterface().update()

    assert state == []
    assert app_config.UPDATE_SHOW_CHANGELOG == 0


def test_config_import_skips_docker_keys_on_flatpak(flatpak, app_config, tmp_path, monkeypatch):
    app_config.GIT_BRANCH = 'nightly'
    app_config.PLEXPY_AUTO_UPDATE = 0
    imported = tmp_path / 'import.ini'
    imported.write_text('[General]\ngit_branch = beta\nplexpy_auto_update = 1\nhttp_port = 8182\n[PMS]\n'
                        'pms_name = Imported\n')
    monkeypatch.setattr(plexpy.config, 'set_is_importing', lambda value: None)
    monkeypatch.setattr(plexpy.config, 'set_import_thread', lambda value: None)

    plexpy.config.import_tautulli_config(str(imported))

    assert app_config.GIT_BRANCH == 'nightly'
    assert app_config.PLEXPY_AUTO_UPDATE == 0
    assert app_config.PMS_NAME == 'Imported'
