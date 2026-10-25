"""The users and libraries tables keep the archived and guest filters."""

import plexpy
from plexpy import libraries, users

from tests.test_last_played_row import draw, seed_overlapping_plays


def seed_hidden_later_play(app_db):
    seed_overlapping_plays(app_db)
    app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 2, 'Hidden', 'movie')")
    app_db.action("UPDATE session_history SET section_id = 2 WHERE id = 1")
    libraries.Libraries().set_config(section_id=2, is_archived=1)


USER_COLUMNS = ["edit", "user_thumb", "friendly_name", "last_seen", "last_played"]


def test_users_table_last_played_skips_an_archived_library(app_db):
    seed_hidden_later_play(app_db)

    row = users.Users().get_datatables_list(kwargs=draw(USER_COLUMNS, 2))["data"][0]
    assert (row["last_seen"], row["last_played"]) == (7000, "Earlier Movie")

    row = users.Users().get_datatables_list(kwargs=draw(USER_COLUMNS, 2), include_archived=True)["data"][0]
    assert row["last_played"] == "Later Movie"


def test_users_table_tie_on_started_shows_the_highest_id(app_db):
    seed_overlapping_plays(app_db)
    app_db.action("UPDATE session_history SET started = 7000")

    row = users.Users().get_datatables_list(kwargs=draw(USER_COLUMNS, 2))["data"][0]

    assert row["last_played"] == "Earlier Movie"


def test_library_table_for_a_guest_hides_unshared_libraries(app_db, monkeypatch):
    seed_overlapping_plays(app_db)
    app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 2, 'Other', 'movie')")
    monkeypatch.setattr(plexpy.session, "get_session_shared_libraries", lambda: ("1",))
    monkeypatch.setattr(plexpy.session, "mask_session_info", lambda rows: rows)
    columns = ["edit", "library_thumb", "section_name", "last_accessed", "last_played"]

    data = libraries.Libraries().get_datatables_list(kwargs=draw(columns, 2))["data"]

    assert {r["section_id"] for r in data} == {1}
