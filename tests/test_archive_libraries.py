"""Archived libraries.

An archived library is hidden from the libraries table, the home
library cards, and every statistic. Its session_history
rows stay. The seed is the shared six-row history from test_history_table.
The fixture moves bob's rows 3 and 5 into a second library, section 2,
and the tests archive that library. alice keeps rows 1, 2, 4, 6 in
section 1.
"""

import pytest

import plexpy
from plexpy import database, datafactory, graphs, libraries, users, webserve

from tests.test_archive_users import (ARCHIVED_INDICATOR, checkbox_tag, GRAPH_ENDPOINTS, library, page_badges,  # noqa: F401
                                      SHOW_ARCHIVED, seeded, show_archived_pages, web_pages)
from tests.test_history_table import insert_history_row, seed_history


@pytest.fixture
def two_libraries(app_db):
    seed_history(app_db)
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    for section_id, name in ((1, "Mixed"), (2, "Other")):
        app_db.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                      "VALUES ('server', ?, ?, 'movie')", [section_id, name])
    app_db.action("UPDATE session_history SET section_id = 2 WHERE id IN (3, 5)")
    return app_db


@pytest.fixture
def late_bob(two_libraries):
    # bob's row 7 overlaps alice's last play (row 6, 5000 to 5900) and ends
    # after it. It is in section 2.
    insert_history_row(two_libraries, 7, 15, 2, "bob", 5100, 6100, 204, "Delta Movie", "movie")
    two_libraries.action("UPDATE session_history SET section_id = 2 WHERE id = 7")
    return two_libraries


def archive_other():
    libraries.Libraries().set_config(section_id=2, is_archived=1)


def test_archive_keeps_history_and_unarchive_restores(two_libraries):
    web = webserve.WebInterface()

    web.edit_library(section_id="2", is_archived="1")
    # An edit that leaves out is_archived keeps the library archived.
    web.edit_library(section_id="2", keep_history="1")

    assert two_libraries.select_single(
        "SELECT is_archived, keep_history, deleted_section FROM library_sections WHERE section_id = 2"
    ) == {"is_archived": 1, "keep_history": 1, "deleted_section": 0}
    assert two_libraries.select_single(
        "SELECT COUNT(*) AS plays FROM session_history WHERE section_id = 2") == {"plays": 2}

    web.edit_library(section_id="2", is_archived="0")
    assert two_libraries.select_single(
        "SELECT is_archived FROM library_sections WHERE section_id = 2") == {"is_archived": 0}


def library_flags(db):
    return db.select_single("SELECT is_archived, deleted_section FROM library_sections WHERE section_id = 2")


def library_list_ids():
    rows = webserve.WebInterface().get_library_list(grouping=0)["data"]
    return {row["section_id"] for row in rows}


def test_delete_clears_the_archive_flag_and_undelete_lists_the_library(two_libraries):
    archive_other()

    libraries.Libraries().delete(section_id=2, server_id="server")

    assert library_flags(two_libraries) == {"is_archived": 0, "deleted_section": 1}
    libraries.Libraries().undelete(section_id=2)
    assert 2 in library_list_ids()


def test_purge_keeps_the_library_archive_flag(two_libraries):
    archive_other()

    libraries.Libraries().delete(section_id=2, server_id="server", purge_only=True)

    assert library_flags(two_libraries)["is_archived"] == 1


@pytest.mark.parametrize("kwargs", [{"section_id": 2}, {"section_name": "Other"}])
def test_undelete_clears_the_archive_flag_of_a_deleted_library(two_libraries, kwargs):
    # Set the flags directly, like a library deleted before delete cleared is_archived.
    two_libraries.action("UPDATE library_sections SET deleted_section = 1, is_archived = 1 WHERE section_id = 2")

    assert libraries.Libraries().undelete(**kwargs) is True

    assert library_flags(two_libraries) == {"is_archived": 0, "deleted_section": 0}


def test_edit_library_dialog_disables_the_checkboxes_of_a_deleted_library(web_pages):
    ids = ("keep_history", "is_archived")

    def disabled():
        dialog = web_pages.edit_library_dialog(section_id="1")
        return [("disabled" in checkbox_tag(dialog, name)) for name in ids]

    assert disabled() == [False, False]

    libraries.Libraries().delete(section_id=1, server_id="server")
    assert disabled() == [True, True]

    libraries.Libraries().undelete(section_id=1)
    assert disabled() == [False, False]


def test_get_library_returns_the_archive_flag(two_libraries):
    archive_other()
    web = webserve.WebInterface()

    assert web.get_library(section_id="2")["is_archived"] == 1
    assert web.get_library(section_id="1")["is_archived"] == 0


def test_libraries_table_hides_archived_until_asked(two_libraries):
    archive_other()

    shown = webserve.WebInterface().get_library_list(grouping=0)
    everyone = webserve.WebInterface().get_library_list(grouping=0, include_archived=1)

    assert {row["section_id"] for row in shown["data"]} == {1}
    assert {row["section_id"]: row["is_archived"] for row in everyone["data"]} == {1: 0, 2: 1}


def test_library_names_list_an_archived_library(two_libraries):
    # The settings page picks the home library cards from this list.
    archive_other()

    names = webserve.WebInterface().get_library_sections()

    assert {row["section_id"] for row in names} == {1, 2}


def test_home_library_cards_hide_archived_until_asked(two_libraries):
    archive_other()
    factory = datafactory.DataFactory()

    shown = factory.get_library_stats(library_cards=["1", "2"])
    everyone = factory.get_library_stats(library_cards=["1", "2"], include_archived=True)

    assert [card["section_id"] for card in shown["movie"]] == [1]
    assert {card["section_id"] for card in everyone["movie"]} == {1, 2}


def test_upgrade_adds_the_archive_column(app_db):
    app_db.action("ALTER TABLE library_sections DROP COLUMN is_archived")

    plexpy.dbcheck()

    app_db.action("INSERT INTO library_sections (server_id, section_id) VALUES ('server', 1)")
    assert app_db.select_single("SELECT is_archived FROM library_sections") == {"is_archived": 0}


def history_row_ids(**kwargs):
    result = webserve.WebInterface().get_history(grouping=0, include_activity=0, **kwargs)
    return {row["row_id"] for row in result["data"]}


def test_history_hides_archived_library_until_asked(two_libraries):
    archive_other()

    assert history_row_ids() == {1, 2, 4, 6}
    assert history_row_ids(include_archived=1) == {1, 2, 3, 4, 5, 6}


def test_history_returns_an_archived_library_asked_for_by_id(two_libraries):
    archive_other()

    assert history_row_ids(section_id="2") == {3, 5}
    assert history_row_ids(section_id="1,2") == {1, 2, 3, 4, 5, 6}


def test_history_count_and_total_duration_skip_archived_library(two_libraries):
    archive_other()

    result = webserve.WebInterface().get_history(grouping=0, include_activity=0)

    assert result["recordsFiltered"] == 4
    # alice plays 1950 seconds. bob adds 1000 more.
    assert result["total_duration"] == "32 mins 30 secs"


def test_history_activity_union_skips_archived_library(two_libraries):
    two_libraries.action("INSERT INTO sessions (session_key, user_id, user, started, media_type, state, section_id) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?)", [99, 2, "bob", 6000, "movie", "playing", 2])
    archive_other()

    hidden = webserve.WebInterface().get_history(grouping=0, include_activity=1)
    shown = webserve.WebInterface().get_history(grouping=0, include_activity=1, include_archived=1)

    assert {row["user_id"] for row in hidden["data"]} == {1}
    assert 99 in {row["session_key"] for row in shown["data"] if row["session_key"]}


def library_flags_by_row():
    result = webserve.WebInterface().get_history(grouping=0, include_activity=0, include_archived=1)
    return {row["row_id"]: row["library_is_archived"] for row in result["data"]}


def test_history_rows_carry_the_library_archive_flag(two_libraries):
    assert set(library_flags_by_row().values()) == {0}

    archive_other()

    assert library_flags_by_row() == {1: 0, 2: 0, 3: 1, 4: 0, 5: 1, 6: 0}


def test_history_activity_row_carries_the_library_archive_flag(two_libraries):
    for key, user_id, user, section_id in ((99, 2, "bob", 2), (98, 1, "alice", 1)):
        two_libraries.action("INSERT INTO sessions (session_key, user_id, user, started, media_type, state, section_id) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?)", [key, user_id, user, 6000, "movie", "playing", section_id])
    archive_other()
    two_libraries.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                         "VALUES ('other', 2, 'Other', 'movie')")

    result = webserve.WebInterface().get_history(grouping=0, include_activity=1, include_archived=1)

    flags = {row["session_key"]: row["library_is_archived"] for row in result["data"] if row["session_key"]}
    assert flags == {99: 1, 98: 0}


def test_history_rows_do_not_repeat_for_a_section_id_on_two_servers(two_libraries):
    archive_other()
    two_libraries.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                         "VALUES ('other', 2, 'Other', 'movie')")

    result = webserve.WebInterface().get_history(grouping=0, include_activity=0, include_archived=1)

    assert sorted(row["row_id"] for row in result["data"]) == [1, 2, 3, 4, 5, 6]
    assert library_flags_by_row()[3] == 1


def test_library_sections_return_the_archive_flag(two_libraries):
    archive_other()

    flags = {item["section_id"]: item["is_archived"] for item in libraries.Libraries().get_sections()}
    api_flags = {item["section_id"]: item["is_archived"] for item in webserve.WebInterface().get_library_sections()}

    assert flags == api_flags == {1: 0, 2: 1}


def test_user_and_library_filters_are_independent(two_libraries):
    # alice is archived and library 2 is archived. No row is left.
    archive_other()
    users.Users().set_config(user_id=1, is_archived=1)

    assert history_row_ids() == set()
    assert history_row_ids(section_id="2") == {3, 5}
    assert history_row_ids(user_id="1") == {1, 2, 4, 6}
    assert history_row_ids(include_archived=1) == {1, 2, 3, 4, 5, 6}


def test_archived_user_own_history_drops_archived_library_rows(two_libraries):
    # The user page asks for its own user with the global include_archived.
    archive_other()
    users.Users().set_config(user_id=1, is_archived=1)
    two_libraries.action("UPDATE session_history SET section_id = 2 WHERE id = 6")

    assert history_row_ids(user_id="1", include_archived=0) == {1, 2, 4}
    assert history_row_ids(user_id="1", include_archived=1) == {1, 2, 4, 6}


def test_home_stats_skip_archived_library(two_libraries):
    archive_other()
    factory = datafactory.DataFactory()

    # The seed rows are from 1970, so anchor the stats window at the epoch.
    stats = factory.get_home_stats(stats_cards=["top_users"], after="1970-01-01")
    named = factory.get_home_stats(stats_cards=["top_users"], after="1970-01-01", section_id="2")
    everyone = factory.get_home_stats(stats_cards=["top_users"], after="1970-01-01", include_archived=True)

    assert [row["user_id"] for row in stats[0]["rows"]] == [1]
    assert [row["user_id"] for row in named[0]["rows"]] == [2]
    assert [row["user_id"] for row in everyone[0]["rows"]] == [1, 2]


def test_most_concurrent_skips_archived_library(late_bob):
    archive_other()

    stats = datafactory.DataFactory().get_home_stats(stats_cards=["most_concurrent"], after="1970-01-01")

    assert stats[0]["rows"][0]["count"] == 1


def test_item_stats_skip_archived_library(two_libraries):
    archive_other()
    factory = datafactory.DataFactory()

    # bob's row 3 and alice's row 6 played rating_key 202.
    by_key = factory.get_watch_time_stats(rating_key=202, grouping=False, query_days="0")
    shown = factory.get_watch_time_stats(rating_key=202, grouping=False, query_days="0", include_archived=True)
    by_user = factory.get_user_stats(rating_key=202, grouping=False)
    shown_by_user = factory.get_user_stats(rating_key=202, grouping=False, include_archived=True)

    assert [row["total_plays"] for row in by_key] == [1]
    assert [row["total_plays"] for row in shown] == [2]
    assert [row["user_id"] for row in by_user] == [1]
    assert [row["user_id"] for row in shown_by_user] == [1, 2]


@pytest.mark.parametrize("name", GRAPH_ENDPOINTS)
def test_graph_show_archived_matches_the_unarchived_graph(late_bob, name):
    graph = getattr(webserve.WebInterface(), name)
    # The seed rows are from 1970. The per month graph counts months.
    time_range = "1200" if name == "get_plays_per_month" else "36500"
    before = graph(time_range=time_range)

    archive_other()

    assert graph(time_range=time_range) != before
    assert graph(time_range=time_range, include_archived="1") == before


def test_stream_type_graph_skips_archived_library(late_bob):
    archive_other()

    # With no user_id, the archived filters are the query's only WHERE clause.
    result = graphs.Graphs().get_total_concurrent_streams_per_stream_type(time_range=36500)

    assert max(result["series"][3]["data"]) == 1


def test_users_table_counts_skip_archived_library(two_libraries):
    archive_other()
    web = webserve.WebInterface()

    def plays(**kwargs):
        return {row["user_id"]: row["plays"] for row in web.get_user_list(grouping=0, **kwargs)["data"]}

    assert (plays()[1], plays()[2]) == (4, 0)
    assert (plays(include_archived=1)[1], plays(include_archived=1)[2]) == (4, 2)


def test_user_page_stats_skip_archived_library(two_libraries):
    archive_other()
    user_data = users.Users()

    def all_time(include_archived):
        result = user_data.get_watch_time_stats(user_id=2, grouping=False, query_days="0",
                                                include_archived=include_archived)
        return result[0]["total_plays"]

    assert all_time(False) == 0
    assert all_time(True) == 2
    assert user_data.get_player_stats(user_id=2) == []
    assert len(user_data.get_player_stats(user_id=2, include_archived=True)) == 1
    assert user_data.get_recently_watched(user_id=2) == []
    assert len(user_data.get_recently_watched(user_id=2, include_archived=True)) == 2


def test_user_page_ips_and_last_seen_skip_archived_library(two_libraries):
    archive_other()
    web = webserve.WebInterface()

    assert web.get_user_ips(user_id="2")["data"] == []
    assert len(web.get_user_ips(user_id="2", include_archived="1")["data"]) == 1
    assert web.get_user(user_id="2", include_last_seen=True)["last_seen"] is None
    assert web.get_user(user_id="2", include_last_seen=True, include_archived="1")["last_seen"] == 4000


def test_library_page_shows_an_archived_library_own_data(two_libraries):
    archive_other()
    library_data = libraries.Libraries()

    user_stats = library_data.get_user_stats(section_id=2)
    watch_time = library_data.get_watch_time_stats(section_id=2, grouping=False, query_days="0")
    recent = library_data.get_recently_watched(section_id=2)
    details = library_data.get_library_details(section_id=2, include_last_accessed=True)

    assert [row["user_id"] for row in user_stats] == [2]
    assert watch_time[0]["total_plays"] == 2
    assert {row["user"] for row in recent} == {"bob"}
    assert details["last_accessed"] == 4000


def test_user_watch_time_recent_window_skips_archived_library(two_libraries):
    # The timed branch (query_days > 0) has its own copy of the filter.
    archive_other()
    user_data = users.Users()

    hidden = user_data.get_watch_time_stats(user_id=2, grouping=False, query_days="36500")
    shown = user_data.get_watch_time_stats(user_id=2, grouping=False, query_days="36500", include_archived=True)

    assert hidden[0]["total_plays"] == 0
    assert shown[0]["total_plays"] == 2


def test_user_api_endpoints_pass_include_archived(two_libraries):
    archive_other()
    web = webserve.WebInterface()

    assert web.get_user_watch_time_stats(user_id="2", grouping=0, query_days="0")[0]["total_plays"] == 0
    assert web.get_user_watch_time_stats(user_id="2", grouping=0, query_days="0",
                                         include_archived="1")[0]["total_plays"] == 2
    assert web.get_user_watch_time_stats(user_id="2", grouping=0, query_days="36500",
                                         include_archived="1")[0]["total_plays"] == 2
    assert web.get_user_player_stats(user_id="2", grouping=0) == []
    assert len(web.get_user_player_stats(user_id="2", grouping=0, include_archived="1")) == 1


def test_user_page_fragments_pass_include_archived(two_libraries, monkeypatch):
    archive_other()
    monkeypatch.setattr(webserve, "serve_template", lambda **kwargs: kwargs["data"])
    web = webserve.WebInterface()

    assert web.user_watch_time_stats(user_id="2")[-1]["total_plays"] == 0
    assert web.user_watch_time_stats(user_id="2", include_archived="1")[-1]["total_plays"] == 2
    assert web.user_player_stats(user_id="2") is None
    assert web.user_player_stats(user_id="2", include_archived="1")
    assert web.get_user_recently_watched(user_id="2") is None
    assert web.get_user_recently_watched(user_id="2", include_archived="1")


def test_history_survives_a_failing_archived_section_query(two_libraries, monkeypatch):
    # get_archived_section_ids must return a list on error, not None.
    archive_other()
    real = database.MonitorDatabase.select

    def select(self, query, args=None):
        if "WHERE is_archived = 1" in query and "library_sections" in query:
            raise Exception("boom")
        return real(self, query, args)

    monkeypatch.setattr(database.MonitorDatabase, "select", select)

    assert libraries.Libraries().get_archived_section_ids() == []
    assert history_row_ids() == {1, 2, 3, 4, 5, 6}


def test_collection_history_keeps_the_archived_library_filter_apart(two_libraries, monkeypatch):
    # The rating_key OR clauses must not merge with the library filter.
    from plexpy import pmsconnect
    archive_other()
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_item_children",
                        lambda self, rating_key=None, media_type=None: {"children_list": [{"rating_key": 101}]})

    assert history_row_ids(rating_key="9", media_type="collection") == set()


def test_edit_library_dialog_has_the_archive_checkbox(web_pages):
    dialog = web_pages.edit_library_dialog(section_id="1")
    assert 'id="is_archived"' in dialog
    assert "Archive library" in dialog
    assert "Checked" not in dialog[dialog.index('id="is_archived"'):].split(">")[0]

    libraries.Libraries().set_config(section_id=1, is_archived=1)

    dialog = web_pages.edit_library_dialog(section_id="1")
    assert "Checked" in dialog[dialog.index('id="is_archived"'):].split(">")[0]


def test_show_archived_data_shows_for_an_archived_library(web_pages):
    # No user is archived in this test.
    assert not any(SHOW_ARCHIVED in page for page in show_archived_pages(web_pages))

    libraries.Libraries().set_config(section_id=1, is_archived=1)
    pages = show_archived_pages(web_pages)

    assert all(SHOW_ARCHIVED in page and ARCHIVED_INDICATOR in page for page in pages)
    assert all("Show Archived Data" in page and "Show Archived Users" not in page for page in pages)
    assert all("Showing archived users and libraries." in page for page in pages)


def test_show_archived_resets_while_no_library_is_archived(web_pages):
    reset = "setLocalStorage('include_archived', 0, false);"
    libraries.Libraries().set_config(section_id=1, is_archived=1)
    assert not any(reset in page for page in show_archived_pages(web_pages))

    libraries.Libraries().set_config(section_id=1, is_archived=0)
    assert all(reset in page for page in show_archived_pages(web_pages))


@pytest.mark.parametrize("thumb", ["http://plex/thumb.jpg", ""], ids=["http thumb", "svg icon"])
@pytest.mark.parametrize("flags, badges", [
    ("deleted_section = 1, is_archived = 1, is_active = 0", [("Deleted library", "fa-trash-o")]),
    ("deleted_section = 1", [("Deleted library", "fa-trash-o")]),
    ("is_archived = 1, is_active = 0", [("Archived library", "fa-archive")]),
    ("is_archived = 1", [("Archived library", "fa-archive")]),
    ("is_active = 0", [("Library not on Plex server", "fa-exclamation-triangle")]),
    ("is_active = 1", []),
])
def test_library_page_badges_the_deleted_archived_and_inactive_library(seeded, web_pages, flags, badges, thumb):
    seeded.action("UPDATE library_sections SET thumb = ?, %s WHERE section_id = 1" % flags, [thumb])

    page = web_pages.library(section_id="1")

    assert ("library-info-poster-face svg-icon" in page) == (thumb == "")
    assert page_badges(page, "inactive-library-tooltip") == badges


def test_undelete_restores_several_libraries_by_row_ids_in_one_call(two_libraries):
    two_libraries.action("UPDATE library_sections SET deleted_section = 1, keep_history = 0, is_archived = 1")
    row_ids = ",".join(str(row["id"]) for row in two_libraries.select("SELECT id FROM library_sections"))

    result = webserve.WebInterface().undelete_library(row_ids=row_ids)

    assert result == {"result": "success", "message": "Restored library with row_ids %s." % row_ids}
    assert two_libraries.select("SELECT section_id, deleted_section, keep_history, is_archived "
                                "FROM library_sections ORDER BY section_id") == [
        {"section_id": 1, "deleted_section": 0, "keep_history": 1, "is_archived": 0},
        {"section_id": 2, "deleted_section": 0, "keep_history": 1, "is_archived": 0}]


def test_undelete_row_ids_restores_only_that_library_row(two_libraries):
    # A second server has a library with the same section_id. Its row stays deleted.
    two_libraries.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                         "VALUES ('other', 2, 'Other', 'movie')")
    two_libraries.action("UPDATE library_sections SET deleted_section = 1 WHERE section_id = 2")
    row_id = two_libraries.select_single(
        "SELECT id FROM library_sections WHERE server_id = 'server' AND section_id = 2")["id"]

    assert libraries.Libraries().undelete(row_ids=str(row_id)) is True

    assert two_libraries.select("SELECT server_id FROM library_sections WHERE deleted_section = 1") == [
        {"server_id": "other"}]


def test_undelete_library_with_an_unknown_row_id_is_an_error(two_libraries):
    two_libraries.action("UPDATE library_sections SET deleted_section = 1 WHERE section_id = 2")

    assert libraries.Libraries().undelete(row_ids="9999") is False
    assert webserve.WebInterface().undelete_library(row_ids="9999")["result"] == "error"
    assert library_flags(two_libraries)["deleted_section"] == 1


def test_undelete_library_still_restores_every_row_of_a_section_id(two_libraries):
    two_libraries.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                         "VALUES ('other', 2, 'Other', 'movie')")
    two_libraries.action("UPDATE library_sections SET deleted_section = 1 WHERE section_id = 2")

    assert webserve.WebInterface().undelete_library(section_id="2")["result"] == "success"

    assert two_libraries.select("SELECT id FROM library_sections WHERE deleted_section = 1") == []
