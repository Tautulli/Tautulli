import pytest

import plexpy
from plexpy import versioncheck


@pytest.fixture
def git(monkeypatch):
    """Mock runGit. Record every command and answer `remote` with two remotes."""
    calls = []

    def fake_run_git(args):
        calls.append(args)
        return ('origin\nupstream' if args == 'remote' else 'ok'), None

    class Config:
        GIT_REMOTE = 'origin'
        GIT_BRANCH = 'nightly'
        GIT_USER = 'Tautulli'
        GIT_REPO = 'Tautulli'

    monkeypatch.setattr(versioncheck, 'runGit', fake_run_git)
    monkeypatch.setattr(plexpy, 'CONFIG', Config(), raising=False)
    monkeypatch.setattr(plexpy, 'INSTALL_TYPE', 'git', raising=False)
    monkeypatch.setattr(versioncheck, 'clean_pyc', lambda: None)
    return calls


def run_all():
    versioncheck.update()
    versioncheck.checkout_git_branch()
    versioncheck.reset_git_install()


def mutating(calls):
    return [c for c in calls if c != 'remote']


@pytest.mark.parametrize('field, value', [
    ('GIT_REMOTE', '--upload-pack=x'),
    ('GIT_BRANCH', '-D'),
    ('GIT_REMOTE', 'origin extra'),
    ('GIT_BRANCH', 'nightly extra'),
    ('GIT_REMOTE', 'origin"x'),
    ('GIT_BRANCH', "nightly'x"),
    ('GIT_BRANCH', ''),
    ('GIT_REMOTE', ''),
    ('GIT_BRANCH', ' -D'),
    ('GIT_REMOTE', ' -x'),
    ('GIT_BRANCH', '.'),
    ('GIT_BRANCH', '..'),
    ('GIT_BRANCH', 'x\n'),
])
def test_bad_name_runs_no_git_command(git, field, value):
    setattr(plexpy.CONFIG, field, value)
    run_all()
    assert git == []


def test_unknown_remote_runs_no_git_command(git):
    plexpy.CONFIG.GIT_REMOTE = 'https://example.invalid/repo.git'
    run_all()
    assert mutating(git) == []

    for remote in ('nosuchremote', 'orig'):
        plexpy.CONFIG.GIT_REMOTE = remote
        run_all()
        assert mutating(git) == []


def test_reset_returns_false_on_bad_value(git):
    plexpy.CONFIG.GIT_BRANCH = '-x'
    assert versioncheck.reset_git_install() is False


def test_valid_values_reach_git_unchanged(git):
    plexpy.CONFIG.GIT_REMOTE = 'upstream'
    plexpy.CONFIG.GIT_BRANCH = 'feature/x-1.2'
    versioncheck.checkout_git_branch()
    assert mutating(git) == [
        'fetch upstream',
        'checkout feature/x-1.2',
        'pull upstream feature/x-1.2',
    ]


@pytest.mark.parametrize('field', ['GIT_USER', 'GIT_REPO'])
@pytest.mark.parametrize('value', ['-x', 'a b', 'a"b', ' -x', 'x\n', '.', '..', '', None])
def test_bad_user_or_repo_runs_no_git_command(git, field, value):
    setattr(plexpy.CONFIG, field, value)
    assert versioncheck.reset_git_install() is False
    assert mutating(git) == []


@pytest.mark.parametrize('user, repo', [
    ('Tautulli', 'Tautulli'),
    ('my-fork', 'user_1'),
    ('a.b', 'Tautulli.git-style.v2'),
])
def test_valid_user_and_repo_reach_set_url(git, user, repo):
    plexpy.CONFIG.GIT_USER = user
    plexpy.CONFIG.GIT_REPO = repo
    versioncheck.reset_git_install()
    assert 'remote set-url origin https://github.com/{}/{}.git'.format(user, repo) in git
