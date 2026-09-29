"""Regression tests for API2.sql()'s database-backup freshness check
(plexpy/api2.py, ~line 320-335).

The check decides whether ``sql`` must trigger a fresh backup before running
a raw query: it should back up only when BACKUP_DIR has no backup newer than
24h. It has regressed twice with the same symptom (a backup on every single
API sql call):

- 2018, commit 6b94292c: the condition was inverted to "any backup is OLDER
  than 24h" instead of "none is newer", so a single stale backup file forced
  a new backup even when a fresh one already existed.
- 2026-08-21, commit d7598d6e: after backups started being written as
  ``.db.zip``, the check still matched ``.db``, so it never saw a fresh
  backup and backed up on every query again. Fixed to match ``.db.zip``.
"""

import time

import pytest

from plexpy.api2 import API2

DAY = 86400


def _touch(path):
    with open(path, "wb"):
        pass


@pytest.fixture
def sql_api(app_db, app_config, monkeypatch, tmp_path):
    """An API2 instance configured to allow API SQL, with backup_db()
    monkeypatched to record calls instead of running a real backup."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    app_config.API_SQL = 1
    app_config.BACKUP_DIR = str(backup_dir)

    api = API2()
    calls = []
    monkeypatch.setattr(api, "backup_db", lambda: calls.append(True))

    return api, backup_dir, calls


def test_empty_backup_dir_triggers_backup(sql_api):
    api, backup_dir, calls = sql_api

    api.sql(query="SELECT 1")

    assert calls == [True]


def test_fresh_zip_backup_suppresses_backup(sql_api):
    api, backup_dir, calls = sql_api
    _touch(backup_dir / "backup-fresh.db.zip")

    api.sql(query="SELECT 1")

    assert calls == []


def test_only_stale_zip_backup_triggers_backup(sql_api, monkeypatch):
    api, backup_dir, calls = sql_api
    _touch(backup_dir / "backup-stale.db.zip")

    # The file's real ctime is "now"; push the code's notion of "now" forward
    # two days so that ctime reads as older than the 24h window.
    real_now = time.time()
    monkeypatch.setattr("plexpy.api2.time.time", lambda: real_now + 2 * DAY)

    api.sql(query="SELECT 1")

    assert calls == [True]


def test_stale_plus_fresh_zip_suppresses_backup(sql_api, monkeypatch):
    # The 2018 regression: a stale backup must not force a new backup when a
    # fresh one also exists alongside it.
    api, backup_dir, calls = sql_api
    stale = backup_dir / "backup-stale.db.zip"
    fresh = backup_dir / "backup-fresh.db.zip"
    _touch(stale)
    _touch(fresh)

    # Both files get the same real ctime (created moments apart in the same
    # test). Fake per-file ctimes so one is clearly stale and one is fresh,
    # without depending on the real clock.
    real_now = time.time()
    stale_path = str(stale)

    def fake_getctime(path):
        if path == stale_path:
            return real_now - 2 * DAY
        return real_now

    monkeypatch.setattr("plexpy.api2.os.path.getctime", fake_getctime)

    api.sql(query="SELECT 1")

    assert calls == []


def test_fresh_plain_db_file_still_triggers_backup(sql_api):
    # Documents the post-d7598d6e contract: only .db.zip counts as a backup,
    # a plain .db file (pre-zip era leftover) does not suppress a new backup.
    api, backup_dir, calls = sql_api
    _touch(backup_dir / "backup-fresh.db")

    api.sql(query="SELECT 1")

    assert calls == [True]


def test_sql_returns_query_result(sql_api):
    # The above tests only check the backup side effect; also check that
    # sql() actually runs the query and returns its rows.
    api, backup_dir, calls = sql_api

    result = api.sql(query="SELECT 1 AS one")

    assert result == [{"one": 1}]
