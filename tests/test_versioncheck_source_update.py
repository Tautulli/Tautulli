import io
import os
import tarfile

import pytest

import plexpy
from plexpy import versioncheck


def make_tar(members):
    """Build a gzip tar. Each member is (name, kind, payload)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for name, kind, payload in members:
            info = tarfile.TarInfo(name)
            if kind == 'file':
                data = payload.encode()
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif kind == 'dir':
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            elif kind == 'sym':
                info.type = tarfile.SYMTYPE
                info.linkname = payload
                tar.addfile(info)
            elif kind == 'hard':
                info.type = tarfile.LNKTYPE
                info.linkname = payload
                tar.addfile(info)
    return buf.getvalue()


@pytest.fixture
def src(monkeypatch, tmp_path):
    """Source install rooted in tmp_path. request_content returns src.data."""
    class Config:
        GIT_BRANCH = 'nightly'
        GIT_USER = 'Tautulli'
        GIT_REPO = 'Tautulli'

    class Src:
        data = b''
        urls = []
        prog = tmp_path / 'prog'
        data_dir = tmp_path / 'data'
        outside = tmp_path / 'outside'

    s = Src()
    s.prog.mkdir()
    s.data_dir.mkdir()
    s.outside.mkdir()

    def fake_request(url, *args, **kwargs):
        s.urls.append(url)
        return s.data

    monkeypatch.setattr(plexpy, 'CONFIG', Config(), raising=False)
    monkeypatch.setattr(plexpy, 'INSTALL_TYPE', 'source', raising=False)
    monkeypatch.setattr(plexpy, 'PROG_DIR', str(s.prog), raising=False)
    monkeypatch.setattr(plexpy, 'DATA_DIR', str(s.data_dir), raising=False)
    monkeypatch.setattr(plexpy, 'LATEST_VERSION', 'abc', raising=False)
    monkeypatch.setattr(versioncheck.request, 'request_content', fake_request)
    monkeypatch.setattr(versioncheck, 'clean_pyc', lambda: None)
    s.urls = []
    return s


def extract(data, dest):
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        versioncheck.safe_extract(tar, str(dest))


def test_symlink_then_file_escape_is_rejected(src, tmp_path):
    data = make_tar([
        ('top/lnk', 'sym', str(src.outside)),
        ('top/lnk/pwn.txt', 'file', 'pwned'),
    ])
    with pytest.raises(ValueError, match='link to an absolute path'):
        extract(data, tmp_path / 'dest')
    assert not (src.outside / 'pwn.txt').exists()


def test_hardlink_overwrite_is_rejected(src, tmp_path):
    victim = src.outside / 'victim.txt'
    victim.write_text('original')
    data = make_tar([
        ('top/h', 'hard', str(victim)),
        ('top/h', 'file', 'pwned'),
    ])
    with pytest.raises(ValueError, match='link to an absolute path'):
        extract(data, tmp_path / 'dest')
    assert victim.read_text() == 'original'


@pytest.mark.parametrize('name', ['../evil.txt', 'top/../../evil.txt'])
def test_dotdot_members_are_rejected(src, tmp_path, name):
    with pytest.raises(ValueError, match='outside the destination'):
        extract(make_tar([(name, 'file', 'x')]), tmp_path / 'dest')
    assert not (tmp_path / 'evil.txt').exists()


def test_in_tree_relative_symlink_extracts(src, tmp_path):
    data = make_tar([
        ('top/init-scripts/init.freebsd', 'file', 'rc'),
        ('top/init-scripts/init.freenas', 'sym', 'init.freebsd'),
    ])
    dest = tmp_path / 'dest'
    extract(data, dest)
    link = dest / 'top' / 'init-scripts' / 'init.freenas'
    assert link.is_symlink()
    assert link.read_text() == 'rc'


def test_old_python_is_refused(src, tmp_path, monkeypatch):
    monkeypatch.delattr(tarfile, 'data_filter')
    dest = tmp_path / 'dest'
    with pytest.raises(ValueError, match='3.11.4'):
        extract(make_tar([('top/a.txt', 'file', 'x')]), dest)
    assert not dest.exists()


def test_absolute_member_stays_inside_dest(src, tmp_path):
    target = src.outside / 'evil.txt'
    dest = tmp_path / 'dest'
    extract(make_tar([(str(target), 'file', 'x')]), dest)
    assert not target.exists()
    assert (dest / str(target).lstrip('/')).read_text() == 'x'


def run_update(src, data):
    src.data = data
    versioncheck.update()


def downloads(src):
    """Files in data_dir other than the update directory."""
    return [n for n in os.listdir(src.data_dir) if n != 'update']


def test_traversal_archive_does_not_crash_update(src, caplog):
    run_update(src, make_tar([('../evil.txt', 'file', 'x')]))
    assert downloads(src) == []
    assert 'Invalid update archive' in caplog.text


def test_html_body_does_not_crash(src, caplog):
    run_update(src, b'<html>')
    assert downloads(src) == []
    assert 'Invalid update archive' in caplog.text


def test_truncated_gzip_does_not_crash(src, caplog):
    good = make_tar([('top/a.txt', 'file', 'x' * 5000)])
    run_update(src, good[:len(good) // 2])
    assert downloads(src) == []
    assert 'Invalid update archive' in caplog.text


def test_oserror_on_open_does_not_crash(src, caplog, monkeypatch):
    data = make_tar([('top/a.txt', 'file', 'x')])  # build before patching

    def boom(*a, **k):
        raise PermissionError('denied')

    monkeypatch.setattr(versioncheck.tarfile, 'open', boom)
    run_update(src, data)
    assert downloads(src) == []
    assert 'Invalid update archive' in caplog.text


def test_stale_update_dir_does_not_block_update(src, monkeypatch, tmp_path):
    cwd = tmp_path / 'cwd'
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    removed = []
    real_remove = os.remove
    monkeypatch.setattr(os, 'remove', lambda p: (removed.append(p), real_remove(p)))
    (src.data_dir / 'update' / 'stale').mkdir(parents=True)
    run_update(src, make_tar([('top/new.txt', 'file', 'fresh')]))
    assert (src.prog / 'new.txt').read_text() == 'fresh'
    assert not (src.data_dir / 'update' / 'stale').exists()
    assert removed == [str(src.data_dir / 'nightly-github')]
    assert os.listdir(cwd) == []


def test_slash_in_branch_does_not_crash(src):
    plexpy.CONFIG.GIT_BRANCH = 'feature/x'
    src.data = make_tar([('top/new.txt', 'file', 'fresh')])
    versioncheck.update()
    assert 'feature/x' in src.urls[0]
    assert (src.prog / 'new.txt').read_text() == 'fresh'
