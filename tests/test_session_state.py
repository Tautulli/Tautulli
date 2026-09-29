"""ActivityProcessor.set_session_state and set_session_last_paused (cc4fb641).

Both used an upsert keyed on session_key. When the row was already
deleted, the upsert inserted a new row holding only state, view_offset
and stopped. The history table then failed with a KeyError on the
missing media_type, and the History page and get_history returned 500
until the row was flushed. Both are plain UPDATEs now. write_session is
the only place that inserts a session row.
"""

from plexpy import activity_processor


def insert_session(app_db, session_key, **columns):
    columns = {"session_key": session_key, **columns}
    app_db.action(
        "INSERT INTO sessions (%s) VALUES (%s)"
        % (", ".join(columns), ", ".join("?" * len(columns))),
        list(columns.values()),
    )


def session_rows(app_db):
    return app_db.select("SELECT * FROM sessions")


def test_set_session_state_updates_the_existing_row(app_db):
    insert_session(app_db, 100, state="playing", view_offset=100,
                   rating_key=1, media_type="movie")

    activity_processor.ActivityProcessor().set_session_state(
        session_key=100, state="paused", view_offset=500, stopped=2000)

    rows = session_rows(app_db)
    assert len(rows) == 1
    assert rows[0]["state"] == "paused"
    assert rows[0]["view_offset"] == 500
    assert rows[0]["stopped"] == 2000
    assert rows[0]["media_type"] == "movie"


def test_set_session_state_on_a_missing_row_inserts_nothing(app_db):
    activity_processor.ActivityProcessor().set_session_state(
        session_key=999, state="stopped", view_offset=500, stopped=2000)

    assert session_rows(app_db) == []


def test_set_session_last_paused_on_a_missing_row_inserts_nothing(app_db):
    activity_processor.ActivityProcessor().set_session_last_paused(
        session_key=999, timestamp=1000)

    assert session_rows(app_db) == []


def test_set_session_last_paused_sets_the_pause_timestamp(app_db):
    insert_session(app_db, 100, state="playing")

    activity_processor.ActivityProcessor().set_session_last_paused(
        session_key=100, timestamp=1000)

    row = session_rows(app_db)[0]
    assert row["last_paused"] == 1000
    # No prior pause to accumulate: the column keeps its default.
    assert row["paused_counter"] == 0


def test_set_session_last_paused_resume_accumulates_paused_counter(app_db, monkeypatch):
    insert_session(app_db, 100, state="paused", last_paused=1000, paused_counter=30)
    monkeypatch.setattr(activity_processor.helpers, "timestamp", lambda: 1060)

    # timestamp=None is a resume: clear last_paused, bank the 60 seconds
    # paused since last_paused on top of the 30 already counted.
    activity_processor.ActivityProcessor().set_session_last_paused(
        session_key=100, timestamp=None)

    row = session_rows(app_db)[0]
    assert row["last_paused"] is None
    assert row["paused_counter"] == 90
