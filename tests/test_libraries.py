"""Library details."""

import plexpy
from plexpy import libraries, webserve

from tests.test_history_table import insert_history_row


def test_get_library_refreshes_a_missing_library_with_last_accessed(app_db, monkeypatch):
    # With no GROUP BY, the MAX() for last_accessed returned one row of NULLs
    # for a missing library. get_details took that row and skipped the refresh.
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    monkeypatch.setattr(libraries, "refresh_libraries", lambda: app_db.action(
        "INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
        "VALUES ('server', 1, 'Movies', 'movie')"))

    result = webserve.WebInterface().get_library(section_id=1, include_last_accessed=1)

    assert (result["section_id"], result["section_name"]) == (1, "Movies")


def library_list_ids(**kwargs):
    rows = webserve.WebInterface().get_library_list(**kwargs)["data"]
    return {row["section_id"] for row in rows}


def seed_deleted_library(app_db):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    for section_id, deleted in ((1, 0), (2, 1)):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type, "
                      "deleted_section) VALUES ('server', ?, 'Library', 'movie', ?)", [section_id, deleted])


def test_libraries_table_lists_deleted_libraries_when_asked(app_db):
    seed_deleted_library(app_db)

    assert library_list_ids() == {1}
    assert library_list_ids(include_deleted="0") == {1}
    assert library_list_ids(include_deleted="1") == {1, 2}


def test_libraries_table_flags_deleted_libraries(app_db):
    seed_deleted_library(app_db)
    rows = webserve.WebInterface().get_library_list(include_deleted="1")["data"]

    assert {row["section_id"]: row["deleted_section"] for row in rows} == {1: 0, 2: 1}


def test_libraries_table_hides_deleted_libraries_from_a_guest(app_db, monkeypatch):
    seed_deleted_library(app_db)
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "1")
    monkeypatch.setattr(plexpy.session, "get_session_shared_libraries", lambda: ("1", "2"))
    monkeypatch.setattr(plexpy.session, "mask_session_info", lambda rows: rows)

    assert library_list_ids(include_deleted="1") == {1}


def test_recently_watched_lists_each_item_once_by_its_latest_play(app_db):
    # Item 301 has two plays. Row 5 is in another section.
    insert_history_row(app_db, 1, 1, 1, "alice", 1000, 1600, 301, "First Movie", "movie")
    insert_history_row(app_db, 2, 2, 1, "alice", 2000, 2600, 302, "Second Movie", "movie")
    insert_history_row(app_db, 3, 3, 1, "alice", 3000, 3600, 301, "First Movie", "movie")
    insert_history_row(app_db, 4, 4, 1, "alice", 4000, 4600, 303, "Third Movie", "movie")
    insert_history_row(app_db, 5, 5, 1, "alice", 5000, 5600, 304, "Other Section", "movie")
    app_db.action("UPDATE session_history SET section_id = 2 WHERE id = 5")

    recent = libraries.Libraries().get_recently_watched(section_id=1)
    latest_two = libraries.Libraries().get_recently_watched(section_id=1, limit="2")

    assert [(row["row_id"], row["title"]) for row in recent] == [
        (4, "Third Movie"), (3, "First Movie"), (2, "Second Movie")]
    assert [row["row_id"] for row in latest_two] == [4, 3]
