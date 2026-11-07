import builtins
import errno
import os
import stat
import sys
import threading

import pytest
from hashing_passwords import check_hash

import plexpy.config
from plexpy import logger


# ---------------------------------------------------------------------------
# defaults from an empty/nonexistent ini
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, expected, expected_type", [
    ("PMS_PORT", 32400, int),
    ("CACHE_SIZEMB", 32, int),
    ("DATE_FORMAT", "YYYY-MM-DD", str),
    ("PMS_IP", "127.0.0.1", str),
    ("HOME_SECTIONS", ["current_activity", "watch_stats", "library_stats", "recently_added"], list),
    ("GET_FILE_SIZES_HOLD", {"section_ids": [], "rating_keys": []}, dict),
])
def test_defaults_from_empty_ini(app_config, name, expected, expected_type):
    value = getattr(app_config, name)
    assert value == expected
    assert type(value) is expected_type


# ---------------------------------------------------------------------------
# round trip: set, write(), reread with a fresh Config on the same file
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, value", [
    ("PMS_PORT", 12345),
    ("DATE_FORMAT", "MM/DD/YYYY"),
    ("HOME_SECTIONS", ["watch_stats", "recently_added"]),
])
def test_round_trip_setting(tmp_path, name, value):
    ini_path = str(tmp_path / "config.ini")
    config = plexpy.config.Config(ini_path)
    setattr(config, name, value)
    config.write()

    reloaded = plexpy.config.Config(ini_path)
    assert getattr(reloaded, name) == value
    assert type(getattr(reloaded, name)) is type(value)


# ---------------------------------------------------------------------------
# hand-edited ini values: configobj strips quotes from scalars, so a
# quoted int still arrives at Config as a plain string that gets cast
# ---------------------------------------------------------------------------

def test_quoted_int_in_ini_is_cast_to_int(tmp_path):
    ini_path = tmp_path / "config.ini"
    ini_path.write_text('[PMS]\npms_port = "12345"\n')

    config = plexpy.config.Config(str(ini_path))
    assert config.PMS_PORT == 12345
    assert type(config.PMS_PORT) is int


@pytest.mark.parametrize("raw, expected", [
    ("false", 0),
    ("no", 0),
    ("true", 1),
    ("1", 1),
])
def test_bool_int_setting_coerces_string_values(tmp_path, raw, expected):
    # VERIFY_SSL_CERT uses the custom bool_int caster, not plain int().
    ini_path = tmp_path / "config.ini"
    ini_path.write_text(f'[Advanced]\nverify_ssl_cert = {raw}\n')

    config = plexpy.config.Config(str(ini_path))
    assert config.VERIFY_SSL_CERT == expected
    assert type(config.VERIFY_SSL_CERT) is int


def test_unparseable_int_falls_back_to_default(tmp_path):
    # A comma in a hand-edited int value makes configobj parse it as a
    # list, which int() can't cast; _cast_setting falls back to the
    # type-default rather than raising.
    ini_path = tmp_path / "config.ini"
    ini_path.write_text("[PMS]\npms_port = 12345, 6\n")

    config = plexpy.config.Config(str(ini_path))
    assert config.PMS_PORT == 32400
    assert type(config.PMS_PORT) is int


# ---------------------------------------------------------------------------
# _upgrade(): the version-walk migration cascade runs on every non-import
# Config() construction, from whatever CONFIG_VERSION is on disk up to the
# latest. These lock in the terminal state after a full walk from 0, and a
# walk that starts partway through with real old-style values.
# ---------------------------------------------------------------------------

def test_upgrade_migrates_fresh_config_to_latest_version(tmp_path):
    ini_path = tmp_path / "config.ini"
    ini_path.write_text("")

    config = plexpy.config.Config(str(ini_path))

    assert config.CONFIG_VERSION == 22
    assert config.GIT_USER == "Tautulli"
    assert config.GIT_REPO == "Tautulli"
    assert config.HTTP_ROOT == ""
    assert config.HTTP_HASH_PASSWORD == 1
    assert config.ANON_REDIRECT == ""
    assert config.ANON_REDIRECT_DYNAMIC == 1
    assert config.PMS_UPDATE_CHANNEL == "plex"
    assert config.CHECK_GITHUB_INTERVAL == 6


def test_upgrade_migrates_old_style_values(tmp_path):
    # config_version 9: a 'plexpass' update channel is renamed to 'beta'.
    # config_version 15: a non-root, non-empty HTTP_ROOT forces a JWT secret
    # rotation. Starting below both versions exercises the walk through them.
    ini_path = tmp_path / "config.ini"
    ini_path.write_text(
        "[Advanced]\n"
        "config_version = 3\n"
        "\n"
        "[PMS]\n"
        "pms_update_channel = plexpass\n"
        "\n"
        "[General]\n"
        "http_root = /tautulli/\n"
    )

    config = plexpy.config.Config(str(ini_path))

    assert config.CONFIG_VERSION == 22
    assert config.PMS_UPDATE_CHANNEL == "beta"
    assert config.HTTP_ROOT == "/tautulli/"
    assert config.JWT_UPDATE_SECRET == 1


def test_upgrade_does_not_duplicate_top_libraries(tmp_path):
    # An old config_version with no home_stats_cards line already gets the
    # modern default, which carries top_libraries. The version 17 migration
    # must not insert a second one.
    ini_path = tmp_path / "config.ini"
    ini_path.write_text("[Advanced]\nconfig_version = 17\n")

    config = plexpy.config.Config(str(ini_path))

    assert config.HOME_STATS_CARDS.count("top_libraries") == 1


def test_upgrade_migrates_more_old_style_values(tmp_path, monkeypatch):
    # config_version 3: a bare '/' HTTP_ROOT is stripped to ''.
    # config_version 5: MONITOR_PMS_UPDATES is forced off.
    # config_version 12: BUFFER_THRESHOLD is floored at 10.
    # config_version 17: a pre-v18 home_stats_cards list (has 'top_users' but
    # not yet 'top_libraries') gets 'top_libraries' inserted just before it.
    # config_version 18: a CHECK_GITHUB_INTERVAL left in minutes (>24) is
    # converted to hours.
    # config_version 19: a plain-text HTTP_PASSWORD gets hashed when
    # HTTP_HASHED_PASSWORD is still unset.
    # config_version 21: ANON_REDIRECT_DYNAMIC turns on when both it and
    # ANON_REDIRECT are unset.
    monkeypatch.setattr(logger, "_BLACKLIST_WORDS", set())

    ini_path = tmp_path / "config.ini"
    ini_path.write_text(
        "[Advanced]\n"
        "config_version = 1\n"
        "\n"
        "[General]\n"
        "http_root = /\n"
        "home_stats_cards = top_movies, popular_movies, top_tv, popular_tv, top_music, popular_music, last_watched, top_users, top_platforms, most_concurrent\n"
        "check_github_interval = 1440\n"
        "http_password = plaintextpw123\n"
        "http_hashed_password = 0\n"
        "anon_redirect_dynamic = 0\n"
        "\n"
        "[Monitoring]\n"
        "monitor_pms_updates = 1\n"
        "buffer_threshold = 3\n"
    )

    config = plexpy.config.Config(str(ini_path))

    assert config.CONFIG_VERSION == 22
    assert config.HTTP_ROOT == ""
    assert config.MONITOR_PMS_UPDATES == 0
    assert config.BUFFER_THRESHOLD == 10
    assert config.CHECK_GITHUB_INTERVAL == 24
    assert config.HTTP_PASSWORD != "plaintextpw123"
    assert check_hash("plaintextpw123", config.HTTP_PASSWORD)
    assert config.HTTP_HASHED_PASSWORD == 1
    assert config.HOME_STATS_CARDS.count("top_libraries") == 1
    assert (config.HOME_STATS_CARDS.index("top_libraries")
            == config.HOME_STATS_CARDS.index("top_users") - 1)
    assert config.ANON_REDIRECT == ""
    assert config.ANON_REDIRECT_DYNAMIC == 1


def test_upgrade_renames_git_user_from_drzoidberg33(tmp_path, monkeypatch):
    # config_version 6 renames the old GitHub user 'drzoidberg33' to
    # 'JonnyWong16', but config_version 10 unconditionally resets GIT_USER
    # to 'Tautulli' later in the same upgrade walk. The rename is only
    # observable as a value GIT_USER passes through, not in the end state,
    # so record every value it's set to instead of only checking the end.
    seen_git_users = []
    original_set_setting = plexpy.config.Config.set_setting

    def recording_set_setting(self, name, value):
        if name == "GIT_USER":
            seen_git_users.append(value)
        return original_set_setting(self, name, value)

    monkeypatch.setattr(plexpy.config.Config, "set_setting", recording_set_setting)

    ini_path = tmp_path / "config.ini"
    ini_path.write_text(
        "[Advanced]\nconfig_version = 3\n\n[General]\ngit_user = drzoidberg33\n"
    )

    config = plexpy.config.Config(str(ini_path))

    assert "JonnyWong16" in seen_git_users
    assert config.GIT_USER == "Tautulli"


# ---------------------------------------------------------------------------
# _blacklist(): token/password-like values get redacted from the logs.
# logger._BLACKLIST_WORDS is a process-global set, so swap it out for a
# fresh one and let monkeypatch put the real one back after the test.
# ---------------------------------------------------------------------------

def test_blacklist_redacts_tokens_and_passwords(tmp_path, monkeypatch):
    monkeypatch.setattr(logger, "_BLACKLIST_WORDS", set())

    ini_path = tmp_path / "config.ini"
    ini_path.write_text(
        "[PMS]\npms_token = supersecrettoken123\n"
        "[General]\ndate_format = MM/DD/YYYY\n"
    )

    plexpy.config.Config(str(ini_path))

    assert "supersecrettoken123" in logger._BLACKLIST_WORDS
    assert "MM/DD/YYYY" not in logger._BLACKLIST_WORDS


@pytest.mark.parametrize("length, expect_blacklisted", [(6, True), (5, False)])
def test_blacklist_length_boundary(tmp_path, monkeypatch, length, expect_blacklisted):
    # _blacklist() only redacts values longer than 5 characters: 6 lands in
    # the set, 5 does not.
    monkeypatch.setattr(logger, "_BLACKLIST_WORDS", set())

    value = "a" * length
    ini_path = tmp_path / "config.ini"
    ini_path.write_text(f"[PMS]\npms_token = {value}\n")

    plexpy.config.Config(str(ini_path))

    assert (value in logger._BLACKLIST_WORDS) is expect_blacklisted


# ---------------------------------------------------------------------------
# TAUTULLI_* environment overrides (documented Docker feature): an env var
# wins over both the ini default and a later in-process setattr.
# ---------------------------------------------------------------------------

def test_env_override_wins_over_ini_default(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUTULLI_PMS_PORT", "9999")
    ini_path = tmp_path / "config.ini"

    config = plexpy.config.Config(str(ini_path))

    assert config.PMS_PORT == 9999
    assert type(config.PMS_PORT) is int


def test_env_override_wins_over_setattr(tmp_path, monkeypatch):
    monkeypatch.setenv("TAUTULLI_PMS_PORT", "9999")
    ini_path = tmp_path / "config.ini"
    config = plexpy.config.Config(str(ini_path))

    # set_setting() refuses to write when the env var is present, so the
    # ini stays untouched and the env value keeps winning on read.
    config.PMS_PORT = 12345

    assert config.PMS_PORT == 9999


# ---------------------------------------------------------------------------
# write(): the new config goes to a temp file, gets fsynced, and then
# replaces config.ini, so a crash mid-write leaves the old file whole.
# ---------------------------------------------------------------------------

def _saved_config(tmp_path, port):
    ini_path = os.path.realpath(tmp_path / "config.ini")
    config = plexpy.config.Config(ini_path)
    config.PMS_PORT = port
    config.write()
    return config, ini_path


def _lock_held_by_another_thread():
    # An RLock always lets its owner back in, so try it from a second thread.
    result = []

    def probe():
        acquired = plexpy.config.WRITE_LOCK.acquire(blocking=False)
        if acquired:
            plexpy.config.WRITE_LOCK.release()
        result.append(not acquired)
    thread = threading.Thread(target=probe)
    thread.start()
    thread.join()
    return result[0]


def test_write_crash_before_replace_keeps_old_config(tmp_path, monkeypatch):
    config, ini_path = _saved_config(tmp_path, 1111)
    config.PMS_PORT = 2222

    def power_cut(src, dst):
        raise SystemExit("power cut")
    monkeypatch.setattr(os, "replace", power_cut)

    with pytest.raises(SystemExit):
        config.write()

    assert plexpy.config.Config(ini_path).PMS_PORT == 1111


def test_write_syncs_whole_temp_file_before_replace(tmp_path, monkeypatch):
    config, ini_path = _saved_config(tmp_path, 1111)
    config.PMS_PORT = 2222
    events = []
    opened = []
    real_fsync, real_replace = os.fsync, os.replace

    def zfs_open(path, mode):
        # ZFS reports 128 KiB blocks, so the whole config stays in the buffer until flushed.
        events.append(("open", _lock_held_by_another_thread()))
        opened.append(builtins.open(path, mode, buffering=128 * 1024))
        return opened[-1]

    def fsync(fd):
        events.append(("fsync", os.fstat(fd).st_size))
        real_fsync(fd)

    def replace(src, dst):
        # Windows cannot rename a file that is still open.
        events.append(("replace", src, dst, _lock_held_by_another_thread(), opened[-1].closed))
        real_replace(src, dst)

    monkeypatch.setattr(plexpy.config, "open", zfs_open, raising=False)
    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "replace", replace)
    config.write()

    assert events == [
        ("open", True),
        ("fsync", os.path.getsize(ini_path)),
        ("replace", ini_path + ".tmp", ini_path, True, True),
    ]
    assert not _lock_held_by_another_thread()
    assert plexpy.config.Config(ini_path).PMS_PORT == 2222


def test_first_write_replaces_and_leaves_no_temp_file(tmp_path, monkeypatch):
    replaced = []
    real_replace = os.replace

    def replace(src, dst):
        replaced.append(dst)
        real_replace(src, dst)
    monkeypatch.setattr(os, "replace", replace)

    _, ini_path = _saved_config(tmp_path, 1111)

    assert replaced == [ini_path]
    assert os.listdir(tmp_path) == ["config.ini"]


def test_write_overwrites_temp_file_left_by_a_crash(tmp_path):
    config, ini_path = _saved_config(tmp_path, 1111)
    (tmp_path / "config.ini.tmp").write_text("[PMS]\npms_port = 9999\n" * 50)
    config.PMS_PORT = 2222
    config.write()

    assert plexpy.config.Config(ini_path).PMS_PORT == 2222


def test_write_from_signal_handler_during_write(tmp_path, monkeypatch):
    # SIGTERM runs shutdown(), which writes the config on the thread that may be writing.
    config, ini_path = _saved_config(tmp_path, 1111)
    config.PMS_PORT = 2222
    reentered = []
    real_fsync = os.fsync

    def fsync(fd):
        real_fsync(fd)
        if not reentered:
            reentered.append(plexpy.config.WRITE_LOCK.acquire(timeout=1))
            if reentered[0]:
                plexpy.config.WRITE_LOCK.release()
                config.write()
    monkeypatch.setattr(os, "fsync", fsync)
    config.write()

    assert reentered == [True]
    assert plexpy.config.Config(ini_path).PMS_PORT == 2222


def test_write_falls_back_to_in_place_when_replace_fails(tmp_path, monkeypatch):
    # A bind mounted config.ini raises EBUSY on rename.
    config, ini_path = _saved_config(tmp_path, 1111)
    config.PMS_PORT = 2222

    def busy(src, dst):
        raise OSError(errno.EBUSY, "Device or resource busy")
    monkeypatch.setattr(os, "replace", busy)
    config.write()

    assert plexpy.config.Config(ini_path).PMS_PORT == 2222


def test_write_logs_error_when_both_writes_fail(tmp_path, monkeypatch):
    config, _ = _saved_config(tmp_path, 1111)
    errors = []

    def read_only(*args, **kwargs):
        raise OSError(errno.EROFS, "Read-only file system")
    monkeypatch.setattr(plexpy.config, "open", read_only, raising=False)
    monkeypatch.setattr(plexpy.config.ConfigObj, "write", read_only)
    monkeypatch.setattr(logger, "error", lambda *args: errors.append(args))
    config.write()

    assert len(errors) == 1



def test_write_does_not_hide_other_errors(tmp_path, monkeypatch):
    # Only file system errors fall back to the in-place write.
    config, _ = _saved_config(tmp_path, 1111)
    real_write = plexpy.config.ConfigObj.write

    def write(self, outfile=None, section=None):
        if outfile is not None:
            raise ValueError("bad value")
        return real_write(self, outfile, section)
    monkeypatch.setattr(plexpy.config.ConfigObj, "write", write)

    with pytest.raises(ValueError):
        config.write()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_write_keeps_file_mode(tmp_path, monkeypatch):
    config, ini_path = _saved_config(tmp_path, 1111)
    os.chmod(ini_path, 0o600)
    modes = []
    real_write = plexpy.config.ConfigObj.write

    def write(self, outfile=None, section=None):
        if outfile is not None:
            modes.append(stat.S_IMODE(os.fstat(outfile.fileno()).st_mode))
        return real_write(self, outfile, section)
    monkeypatch.setattr(plexpy.config.ConfigObj, "write", write)
    config.write()

    # The temp file holds the tokens, so it must be 0600 before any data goes in.
    assert modes == [0o600]
    assert stat.S_IMODE(os.stat(ini_path).st_mode) == 0o600


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_write_keeps_symlinked_config(tmp_path, monkeypatch):
    # The temp file goes next to the target, because a rename across filesystems fails.
    (tmp_path / "data").mkdir()
    real_path = tmp_path / "data" / "real.ini"
    link_path = tmp_path / "config.ini"
    real_path.write_text("")
    link_path.symlink_to(real_path)
    sources = []
    real_replace = os.replace

    def replace(src, dst):
        sources.append(src)
        real_replace(src, dst)
    monkeypatch.setattr(os, "replace", replace)

    config = plexpy.config.Config(str(link_path))
    config.PMS_PORT = 2222
    config.write()

    assert sources == [os.path.realpath(real_path) + ".tmp"]
    assert link_path.is_symlink()
    assert plexpy.config.Config(str(real_path)).PMS_PORT == 2222


# ---------------------------------------------------------------------------
# A config.ini missing a section that every version writes was cut short.
# Config() copies it aside before anything writes the defaults over it.
# ---------------------------------------------------------------------------

def _full_config(tmp_path):
    ini_path = tmp_path / "config.ini"
    config = plexpy.config.Config(str(ini_path))
    config.FIRST_RUN_COMPLETE = 1
    config.HTTP_USERNAME = "admin"
    config.HTTP_PASSWORD = "hashedpw"
    config.PMS_TOKEN = "plextoken123"
    config.write()
    return ini_path, ini_path.read_bytes()


def _cut_before(data, marker):
    return data[:data.index(marker)]


@pytest.mark.parametrize("damage", [
    lambda data: b"",
    lambda data: b"\n\n  \n",
    # first_run_complete survives, the login does not
    lambda data: _cut_before(data, b"http_username"),
    # a cut partway through a line still parses
    lambda data: _cut_before(data, b"http_port = 8181") + b"http_port = 81",
    lambda data: _cut_before(data, b"pms_token"),
    # an install created under Python 2 has its sections in another order
    lambda data: b"[PMS]\npms_token = plextoken123\n[Monitoring]\n[Advanced]\nconfig_version = 22\n",
])
def test_damaged_config_is_copied_aside(tmp_path, damage):
    ini_path, data = _full_config(tmp_path)
    damaged = damage(data)
    ini_path.write_bytes(damaged)

    config = plexpy.config.Config(str(ini_path))

    assert os.path.dirname(config.damaged_copy) == str(tmp_path)
    assert os.path.basename(config.damaged_copy).startswith("config.ini.damaged-")
    with open(config.damaged_copy, "rb") as f:
        assert f.read() == damaged
    assert ini_path.read_bytes() == damaged


def test_valid_config_is_not_copied(tmp_path):
    ini_path, _ = _full_config(tmp_path)

    assert plexpy.config.Config(str(ini_path)).damaged_copy is None
    assert os.listdir(tmp_path) == ["config.ini"]


def test_older_config_without_newer_keys_is_not_copied(tmp_path):
    # Cloudinary and Newsletter arrived in 2018. Email is a section from PlexPy.
    ini_path = tmp_path / "config.ini"
    ini_path.write_text(
        "[General]\nhttp_port = 8282\n"
        "[Advanced]\nconfig_version = 9\n"
        "[PMS]\npms_ip = 10.0.0.5\n"
        "[Monitoring]\nmonitoring_interval = 60\n"
        "[Email]\nemail_enabled = 0\n"
    )

    config = plexpy.config.Config(str(ini_path))

    assert config.damaged_copy is None
    assert config.HTTP_PORT == 8282
    assert os.listdir(tmp_path) == ["config.ini"]


def test_fresh_install_is_not_copied(tmp_path):
    assert plexpy.config.Config(str(tmp_path / "config.ini")).damaged_copy is None
    assert os.listdir(tmp_path) == []


def test_config_import_is_not_copied(tmp_path):
    ini_path = tmp_path / "import.ini"
    ini_path.write_text("[PMS]\npms_port = 12345\n")

    assert plexpy.config.Config(str(ini_path), is_import=True).damaged_copy is None
    assert os.listdir(tmp_path) == ["import.ini"]


# Each of the four sections counts, each start keeps its own copy, a failed
# copy stops the load, and initialize() logs the copy to the log file.

@pytest.mark.parametrize("section", ["General", "Advanced", "PMS", "Monitoring"])
def test_config_without_one_section_is_copied_aside(tmp_path, section):
    from configobj import ConfigObj
    ini_path, _ = _full_config(tmp_path)
    cfg = ConfigObj(str(ini_path), encoding="utf-8")
    del cfg[section]
    cfg.write()

    assert plexpy.config.Config(str(ini_path)).damaged_copy is not None


def test_each_damaged_start_keeps_its_own_copy(tmp_path, monkeypatch):
    ini_path = tmp_path / "config.ini"
    ini_path.write_bytes(b"")
    times = iter(["20261107000001", "20261107000002"])
    monkeypatch.setattr(plexpy.config.helpers, "now", lambda: next(times))

    plexpy.config.Config(str(ini_path))
    plexpy.config.Config(str(ini_path))

    assert sorted(os.listdir(tmp_path)) == [
        "config.ini", "config.ini.damaged-20261107000001", "config.ini.damaged-20261107000002"]


def test_failed_copy_stops_the_load(tmp_path, monkeypatch):
    ini_path = tmp_path / "config.ini"
    ini_path.write_bytes(b"")

    def fail(*args, **kwargs):
        raise PermissionError("read only")
    monkeypatch.setattr(plexpy.config.shutil, "copy2", fail)

    with pytest.raises(OSError):
        plexpy.config.Config(str(ini_path))


class _StopInit(BaseException):
    pass


def test_initialize_logs_the_damaged_copy_to_the_log_file(tmp_path, monkeypatch):
    ini_path = tmp_path / "config.ini"
    backup_dir = tmp_path / "bk"
    # The cut kept the backup settings, so the message must use them.
    ini_path.write_text("[General]\nbackup_days = 17\nbackup_dir = %s\n" % backup_dir)
    events = []
    monkeypatch.setattr(plexpy, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(plexpy, "CONFIG", None)
    monkeypatch.setattr(plexpy, "CONFIG_FILE", None)
    monkeypatch.setattr(plexpy, "VERBOSE", False)
    monkeypatch.setattr(plexpy, "_INITIALIZED", False)
    monkeypatch.setenv("PLEXAPI_CONFIG_PATH", "")
    monkeypatch.setenv("PLEXAPI_LOG_PATH", "")
    monkeypatch.setenv("PLEXAPI_LOG_LEVEL", "")
    monkeypatch.setattr(plexpy.plex, "initialize_plexapi", lambda: None)
    monkeypatch.setattr(logger, "initLogger", lambda **kw: events.append("initLogger"))
    monkeypatch.setattr(logger, "error", lambda msg, *args: events.append(msg % args))
    # Stop initialize() right after the damage log line.
    monkeypatch.setattr(plexpy, "dbcheck", lambda: (_ for _ in ()).throw(_StopInit()))

    with pytest.raises(_StopInit):
        plexpy.initialize(str(ini_path))

    copy = plexpy.CONFIG.damaged_copy
    assert copy is not None
    errors = [e for e in events if "damaged" in e]
    assert len(errors) == 1
    assert copy in errors[0] and str(ini_path) in errors[0]
    assert "zip in %s that" % backup_dir in errors[0]
    assert "older than 17 days" in errors[0]
    assert events.index("initLogger") < events.index(errors[0])
