import sqlite3

import pytest

import plexpy.database


# ---------------------------------------------------------------------------
# action(): args=None branch, and the "no query" no-op
# ---------------------------------------------------------------------------

def test_action_with_no_args_executes_query(app_db):
    result = app_db.action("SELECT 1 AS one")
    assert result.fetchone() == {"one": 1}


def test_action_with_none_query_returns_none(app_db):
    assert app_db.action(None) is None


# ---------------------------------------------------------------------------
# insert / select / select_single round trip
# ---------------------------------------------------------------------------

def test_insert_and_select_round_trip(app_db):
    app_db.action(
        "INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)",
        [1, "alice", "alice@example.com"],
    )

    rows = app_db.select(
        "SELECT user_id, username, email FROM users WHERE user_id = ?", [1]
    )

    assert rows == [{"user_id": 1, "username": "alice", "email": "alice@example.com"}]


def test_select_returns_list_of_dict_rows(app_db):
    # dbcheck() seeds a "Local" user (user_id 0), so scope the query to
    # the rows this test actually inserted.
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "alice"])
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [2, "bob"])

    rows = app_db.select(
        "SELECT user_id, username FROM users WHERE user_id IN (1, 2) ORDER BY user_id"
    )

    assert rows == [
        {"user_id": 1, "username": "alice"},
        {"user_id": 2, "username": "bob"},
    ]
    assert all(isinstance(row, dict) for row in rows)


def test_select_no_match_returns_empty_list(app_db):
    assert app_db.select("SELECT * FROM users WHERE user_id = ?", [999]) == []


def test_select_single_returns_one_row_as_dict(app_db):
    app_db.action(
        "INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "alice"]
    )

    row = app_db.select_single(
        "SELECT username FROM users WHERE user_id = ?", [1]
    )

    assert row == {"username": "alice"}


def test_select_single_no_match_returns_empty_dict(app_db):
    assert app_db.select_single("SELECT * FROM users WHERE user_id = ?", [999]) == {}


def test_session_history_round_trip_preserves_types(app_db):
    # A second real table, with integer columns, to confirm dict_factory
    # doesn't stringify values coming back out of sqlite.
    app_db.action(
        "INSERT INTO session_history (started, stopped, user_id, user, rating_key) "
        "VALUES (?, ?, ?, ?, ?)",
        [1000, 2000, 1, "alice", 555],
    )

    row = app_db.select_single(
        "SELECT started, stopped, user_id, user, rating_key FROM session_history"
    )

    assert row == {
        "started": 1000,
        "stopped": 2000,
        "user_id": 1,
        "user": "alice",
        "rating_key": 555,
    }
    assert isinstance(row["started"], int)


# ---------------------------------------------------------------------------
# upsert()
# ---------------------------------------------------------------------------

def test_upsert_inserts_new_row(app_db):
    trans_type = app_db.upsert(
        "users", {"username": "bob", "email": "bob@example.com"}, {"user_id": 5}
    )

    assert trans_type == "insert"
    row = app_db.select_single(
        "SELECT username, email FROM users WHERE user_id = ?", [5]
    )
    assert row == {"username": "bob", "email": "bob@example.com"}


def test_upsert_updates_existing_row_without_duplicating(app_db):
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [7, "carol"])

    trans_type = app_db.upsert("users", {"username": "carol2"}, {"user_id": 7})

    assert trans_type == "update"
    rows = app_db.select("SELECT username FROM users WHERE user_id = ?", [7])
    assert rows == [{"username": "carol2"}]


def test_upsert_failed_insert_writes_nothing_and_db_stays_usable(app_db):
    # username is NOT NULL; omitting it means the update matches nothing
    # (no such user_id yet) and the fallback insert then violates the
    # NOT NULL constraint. upsert() catches IntegrityError and logs it
    # rather than raising.
    app_db.upsert("users", {"email": "no-username@example.com"}, {"user_id": 999})

    assert app_db.select_single("SELECT * FROM users WHERE user_id = ?", [999]) == {}

    # the connection is still usable afterwards
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1000, "still-works"])
    assert app_db.select_single(
        "SELECT username FROM users WHERE user_id = ?", [1000]
    ) == {"username": "still-works"}


def test_upsert_failed_insert_does_not_report_insert(app_db):
    # The fallback INSERT here fails the users.username NOT NULL constraint.
    # Reporting 'insert' would tell callers like refresh_users and
    # ActivityProcessor to act on a row that was never written.
    trans_type = app_db.upsert("users", {"email": "no-username@example.com"}, {"user_id": 999})
    assert trans_type != "insert"


def test_upsert_with_composite_key_inserts_then_updates_matching_both_keys(app_db):
    # libraries.py upserts into library_sections keyed on (server_id,
    # section_id) together -- a real 2-column key_dict, unlike every other
    # upsert test here. This pins the " AND ".join(...) WHERE clause: a
    # survivor that mangles it into OR, or drops a key, would match rows it
    # shouldn't and update/insert incorrectly.
    trans_type = app_db.upsert(
        "library_sections",
        {"section_name": "Movies"},
        {"server_id": "srv1", "section_id": 1},
    )
    assert trans_type == "insert"

    # a row sharing only ONE of the two keys must be untouched by the update
    app_db.action(
        "INSERT INTO library_sections (server_id, section_id, section_name) VALUES (?, ?, ?)",
        ["srv1", 2, "Other Library"],
    )

    trans_type = app_db.upsert(
        "library_sections",
        {"section_name": "Movies Renamed"},
        {"server_id": "srv1", "section_id": 1},
    )
    assert trans_type == "update"

    rows = app_db.select(
        "SELECT server_id, section_id, section_name FROM library_sections ORDER BY section_id"
    )
    assert rows == [
        {"server_id": "srv1", "section_id": 1, "section_name": "Movies Renamed"},
        {"server_id": "srv1", "section_id": 2, "section_name": "Other Library"},
    ]


# ---------------------------------------------------------------------------
# action(): retry exhaustion on a persistently locked database
# ---------------------------------------------------------------------------

class _AlwaysLockedConnection:
    """Stands in for sqlite3.Connection: every `with self.connection as c`
    (commit-on-success/rollback-on-exception context manager) then c.execute(...)
    raises "database is locked", the one retryable OperationalError action()
    handles."""

    def __init__(self):
        self.raise_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, query, args=None):
        self.raise_count += 1
        raise sqlite3.OperationalError("database is locked")


def test_action_returns_none_after_five_failed_retries(app_db, monkeypatch):
    fake_connection = _AlwaysLockedConnection()
    monkeypatch.setattr(app_db, "connection", fake_connection)

    sleep_calls = []
    monkeypatch.setattr(plexpy.database.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    result = app_db.action("SELECT 1")

    assert result is None
    assert fake_connection.raise_count == 5
    assert len(sleep_calls) == 5


# ---------------------------------------------------------------------------
# action(): error paths raise, and the database stays usable afterwards
# ---------------------------------------------------------------------------

def test_action_bad_sql_raises_operational_error_and_db_stays_usable(app_db):
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "alice"])

    with pytest.raises(sqlite3.OperationalError):
        app_db.action("SELECT * FROM no_such_table")

    # prior committed data is untouched
    assert app_db.select_single(
        "SELECT username FROM users WHERE user_id = ?", [1]
    ) == {"username": "alice"}

    # new writes still work
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [2, "dave"])
    assert len(app_db.select("SELECT * FROM users WHERE user_id IN (1, 2)")) == 2


def test_action_constraint_violation_raises_integrity_error_and_db_stays_usable(app_db):
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "alice"])

    with pytest.raises(sqlite3.IntegrityError):
        app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, "duplicate"])

    # the failed insert did not get committed, and the row was not changed
    rows = app_db.select("SELECT username FROM users WHERE user_id = ?", [1])
    assert rows == [{"username": "alice"}]

    # new writes still work
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [2, "erin"])
    assert len(app_db.select("SELECT * FROM users WHERE user_id IN (1, 2)")) == 2


# ---------------------------------------------------------------------------
# last_insert_id()
# ---------------------------------------------------------------------------

def test_last_insert_id_matches_inserted_row(app_db):
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [42, "erin"])

    inserted_id = app_db.last_insert_id()

    row = app_db.select_single("SELECT id FROM users WHERE user_id = ?", [42])
    assert inserted_id == row["id"]


# ---------------------------------------------------------------------------
# commit visibility across separate MonitorDatabase instances
# ---------------------------------------------------------------------------

def test_second_instance_sees_data_committed_by_first(app_db):
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [11, "frank"])

    second_db = plexpy.database.MonitorDatabase()
    try:
        rows = second_db.select("SELECT username FROM users WHERE user_id = ?", [11])
        assert rows == [{"username": "frank"}]
    finally:
        second_db.connection.close()


# ---------------------------------------------------------------------------
# delete_rows_from_table(): chunks the id list so a single DELETE never
# exceeds SQLite's default 999-variable limit (regression test for
# ad195f09, "Fix deleteing more than 1000 history entries at the same
# time" -- bulk-deleting a large library's history is a real UI/API action)
# ---------------------------------------------------------------------------

def test_delete_rows_from_table_bulk_delete_past_sqlite_variable_limit(app_db):
    row_count = 1100
    for user_id in range(row_count):
        app_db.action("INSERT INTO session_history (user_id) VALUES (?)", [user_id])

    ids = [row["id"] for row in app_db.select("SELECT id FROM session_history")]
    assert len(ids) == row_count

    result = plexpy.database.delete_rows_from_table("session_history", ids)

    assert result is True
    assert app_db.select_single("SELECT COUNT(*) AS c FROM session_history") == {"c": 0}


def test_delete_rows_from_table_small_list_deletes_only_specified_rows(app_db):
    for user_id in range(5):
        app_db.action("INSERT INTO session_history (user_id) VALUES (?)", [user_id])

    ids = [row["id"] for row in app_db.select("SELECT id FROM session_history ORDER BY id")]
    ids_to_delete = ids[:3]

    result = plexpy.database.delete_rows_from_table("session_history", ids_to_delete)

    assert result is True
    remaining = app_db.select("SELECT id FROM session_history ORDER BY id")
    assert [row["id"] for row in remaining] == ids[3:]


def test_delete_rows_from_table_accepts_comma_separated_id_string(app_db):
    # webserve.py's delete_history_rows() passes row_ids as a comma
    # separated string, e.g. "65,110,2,3645" -- not a list, so that's what
    # delete_rows_from_table needs to accept from its real caller.
    for user_id in range(3):
        app_db.action("INSERT INTO session_history (user_id) VALUES (?)", [user_id])

    ids = [row["id"] for row in app_db.select("SELECT id FROM session_history")]
    row_ids_str = ",".join(str(i) for i in ids)

    result = plexpy.database.delete_rows_from_table("session_history", row_ids_str)

    assert result is True
    assert app_db.select_single("SELECT COUNT(*) AS c FROM session_history") == {"c": 0}
