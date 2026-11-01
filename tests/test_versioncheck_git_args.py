import pytest

import plexpy
from plexpy import common
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


def test_git_path_is_one_literal_executable(monkeypatch):
    malicious_path = '/bin/sh" -c "id > /tmp/tautulli_rce'
    calls = []

    class Config:
        GIT_PATH = malicious_path

    class Process:
        def communicate(self):
            return b'ok', None

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return Process()

    monkeypatch.setattr(plexpy, 'CONFIG', Config(), raising=False)
    monkeypatch.setattr(plexpy, 'PROG_DIR', '/tmp', raising=False)
    monkeypatch.setattr(versioncheck.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(versioncheck.subprocess, 'Popen', fake_popen)

    assert versioncheck.runGit('status --short') == ('ok', None)
    argv, kwargs = calls[0]
    assert argv == [malicious_path, 'status', '--short']
    assert 'shell' not in kwargs
    assert kwargs['stdout'] == versioncheck.subprocess.PIPE
    assert kwargs['stderr'] == versioncheck.subprocess.STDOUT
    assert kwargs['cwd'] == '/tmp'


def _git_env(monkeypatch, respond):
    """Install a fake runGit driven by respond(args) -> (output, err)."""
    calls = []

    def fake_run_git(args):
        calls.append(args)
        return respond(args)

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


def _popen_env(monkeypatch, git_path):
    """Install a fake Popen for the real runGit. Returns (calls, queue)."""
    calls = []
    queue = []

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))
        behavior = queue.pop(0)
        if behavior is None:
            raise OSError('no such file')

        class Process:
            def communicate(self):
                return behavior, None

        return Process()

    class Config:
        GIT_PATH = git_path

    monkeypatch.setattr(plexpy, 'CONFIG', Config(), raising=False)
    monkeypatch.setattr(plexpy, 'PROG_DIR', '/tmp', raising=False)
    monkeypatch.setattr(versioncheck.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(versioncheck.subprocess, 'Popen', fake_popen)
    return calls, queue


def test_update_runs_pull_and_clean_on_git_install(git):
    versioncheck.update()
    assert git == ['remote', 'pull --ff-only origin nightly', 'clean -fd']


def test_update_skips_clean_when_already_up_to_date(monkeypatch):
    def respond(args):
        if args == 'remote':
            return ('origin\nupstream', None)
        return ('From https://github.com/Tautulli/Tautulli.git\nAlready up-to-date.', None)

    calls = _git_env(monkeypatch, respond)
    versioncheck.update()
    assert calls == ['remote', 'pull --ff-only origin nightly']


def test_update_stops_when_pull_fails(monkeypatch):
    def respond(args):
        if args == 'remote':
            return ('origin\nupstream', None)
        return (None, None)

    calls = _git_env(monkeypatch, respond)
    versioncheck.update()
    assert calls == ['remote', 'pull --ff-only origin nightly']


def test_reset_runs_full_command_sequence(git):
    versioncheck.reset_git_install()
    assert git == [
        'remote',
        'remote set-url origin https://github.com/Tautulli/Tautulli.git',
        'fetch origin',
        'checkout nightly',
        'branch -u origin/nightly',
        'reset --hard {}'.format(common.RELEASE),
        'clean -fd',
    ]


def test_reset_returns_true_when_already_up_to_date(monkeypatch):
    def respond(args):
        if args == 'remote':
            return ('origin\nupstream', None)
        return ('Already up-to-date.', None)

    _git_env(monkeypatch, respond)
    assert versioncheck.reset_git_install() is True


def test_reset_returns_false_when_aborting(monkeypatch):
    def respond(args):
        if args == 'remote':
            return ('origin\nupstream', None)
        return ('error: Aborting.', None)

    _git_env(monkeypatch, respond)
    assert versioncheck.reset_git_install() is False


def test_empty_git_path_uses_bare_git(monkeypatch):
    calls, queue = _popen_env(monkeypatch, '')
    queue.append(b'ok')

    assert versioncheck.runGit('status --short') == ('ok', None)
    assert calls[0][0] == ['git', 'status', '--short']


def test_run_git_takes_darwin_fallback_when_first_path_fails(monkeypatch):
    calls, queue = _popen_env(monkeypatch, '/opt/tautulli/git')
    monkeypatch.setattr(versioncheck.platform, 'system', lambda: 'Darwin')
    queue.append(None)
    queue.append(b'ok')

    assert versioncheck.runGit('status') == ('ok', None)
    assert [argv[0] for argv, _ in calls] == ['/opt/tautulli/git', '/usr/local/git/bin/git']


def test_run_git_treats_not_found_and_fatal_as_failure(monkeypatch):
    calls, queue = _popen_env(monkeypatch, '/opt/tautulli/git')
    queue.append(b'git: command not found')
    assert versioncheck.runGit('status') == (None, None)
    queue.append(b'fatal: not a git repository')
    assert versioncheck.runGit('status') == (None, None)
    queue.append(None)
    assert versioncheck.runGit('status') == (None, None)


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
