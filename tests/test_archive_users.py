"""Archived users.

An archived user is hidden from the users list, the history table, and
every statistic. Their session_history rows stay. The seed is the shared
six-row history from test_history_table: alice (user_id 1) owns rows 1,
2, 4, 6 and bob (user_id 2) owns rows 3 and 5, all in section 1. The
tests archive bob.
"""

import json
import os

import pytest

import plexpy
from plexpy import datafactory, graphs, libraries, plextv, pmsconnect, users, webauth, webserve

from tests.test_history_table import build_draw, call_history, insert_history_row, seed_history


ARCHIVE_PENDING = (
    "users have no archive flag, so a user that left the server stays in "
    "the users list, the history table, and every statistic"
)

pytestmark = pytest.mark.xfail(reason=ARCHIVE_PENDING)


@pytest.fixture
def seeded(app_db):
    seed_history(app_db)
    return app_db


@pytest.fixture
def late_bob(seeded):
    # bob's row 7 overlaps alice's last play (row 6, 5000 to 5900) and ends
    # after it. rating_key 204 is an item only bob played.
    insert_history_row(seeded, 7, 15, 2, "bob", 5100, 6100, 204, "Delta Movie", "movie")
    return seeded


@pytest.fixture
def library(seeded):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    seeded.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 1, 'Mixed', 'movie')")
    return seeded


def archive_bob():
    users.Users().set_config(user_id=2, is_archived=1)


def history_user_ids(include_archived):
    result = webserve.WebInterface().get_history(grouping=0, include_activity=0,
                                                 include_archived=include_archived)
    return {row["user_id"] for row in result["data"]}


def test_archive_keeps_history_and_unarchive_restores(seeded):
    web = webserve.WebInterface()

    web.edit_user(user_id="2", is_archived="1")
    # An edit that leaves out is_archived keeps the user archived.
    web.edit_user(user_id="2", friendly_name="Bob")

    assert seeded.select_single(
        "SELECT is_archived, keep_history, deleted_user FROM users WHERE user_id = 2"
    ) == {"is_archived": 1, "keep_history": 1, "deleted_user": 0}
    assert seeded.select_single(
        "SELECT COUNT(*) AS plays FROM session_history WHERE user_id = 2") == {"plays": 2}

    web.edit_user(user_id="2", is_archived="0")
    assert seeded.select_single(
        "SELECT is_archived FROM users WHERE user_id = 2") == {"is_archived": 0}


def test_users_table_hides_archived_until_asked(seeded):
    archive_bob()

    shown = webserve.WebInterface().get_user_list()
    everyone = webserve.WebInterface().get_user_list(include_archived=1)

    assert 2 not in {row["user_id"] for row in shown["data"]}
    bob = next(row for row in everyone["data"] if row["user_id"] == 2)
    assert bob["is_archived"] == 1


def test_history_table_hides_archived_until_asked(seeded):
    archive_bob()

    assert history_user_ids(include_archived=0) == {1}
    assert history_user_ids(include_archived=1) == {1, 2}


def test_profile_history_shows_the_archived_user(seeded):
    # The user page asks for its own user with include_archived=1.
    archive_bob()

    result = webserve.WebInterface().get_history(user_id="2", grouping=0, include_activity=0,
                                                 include_archived=1)

    assert {row["row_id"] for row in result["data"]} == {3, 5}


def test_history_count_and_total_duration_skip_archived(seeded):
    archive_bob()

    result = call_history(grouping=False)

    assert result["recordsFiltered"] == 4
    # alice plays 1950 seconds. bob adds 1000 more.
    assert result["total_duration"] == "32 mins 30 secs"


def test_history_activity_union_skips_archived(seeded):
    # The sessions union copies the history filters with the table
    # prefix stripped, so the archived filter must survive that copy.
    seeded.action("INSERT INTO sessions (session_key, user_id, user, started, media_type, state) "
                  "VALUES (?, ?, ?, ?, ?, ?)", [99, 2, "bob", 6000, "movie", "playing"])
    archive_bob()

    result = datafactory.DataFactory().get_datatables_history(
        kwargs={"json_data": json.dumps(build_draw())},
        grouping=False, include_activity=True)

    assert {row["user_id"] for row in result["data"]} == {1}
    assert result["recordsFiltered"] == 4


def test_history_rows_flag_archived_users(seeded):
    # The history tables dim a row by this flag. Session 99 is bob's live stream.
    seeded.action("INSERT INTO sessions (session_key, user_id, user, started, media_type, state) "
                  "VALUES (?, ?, ?, ?, ?, ?)", [99, 2, "bob", 6000, "movie", "playing"])
    archive_bob()

    result = datafactory.DataFactory().get_datatables_history(
        kwargs={"json_data": json.dumps(build_draw())},
        grouping=False, include_activity=True, include_archived=True)

    flags = {(row["user_id"], row["state"]): row["is_archived"] for row in result["data"]}
    assert flags == {(1, None): 0, (2, None): 1, (2, "playing"): 1}


def test_guest_history_is_unchanged_by_another_users_archive(seeded, monkeypatch):
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "1")
    archive_bob()

    result = call_history(grouping=False)

    assert {row["row_id"] for row in result["data"]} == {1, 2, 4, 6}


def test_user_names_hide_archived_until_asked(seeded):
    archive_bob()

    shown = webserve.WebInterface().get_user_names()
    everyone = webserve.WebInterface().get_user_names(include_archived=1)

    assert 2 not in {row["user_id"] for row in shown}
    assert 2 in {row["user_id"] for row in everyone}


def test_home_stats_skip_archived(seeded):
    archive_bob()

    # The seed rows are from 1970, so anchor the stats window at the epoch.
    stats = datafactory.DataFactory().get_home_stats(stats_cards=["top_users"], after="1970-01-01")

    assert [row["user_id"] for row in stats[0]["rows"]] == [1]


def test_home_stats_return_an_archived_user_asked_for_by_id(seeded):
    archive_bob()

    stats = datafactory.DataFactory().get_home_stats(stats_cards=["top_users"], after="1970-01-01",
                                                     user_id="2")

    assert [row["user_id"] for row in stats[0]["rows"]] == [2]


def test_item_user_stats_skip_archived(seeded):
    archive_bob()

    # rating_key 202 is Beta Movie, played by bob (row 3) and alice (row 6).
    stats = datafactory.DataFactory().get_user_stats(rating_key=202)

    assert [row["user_id"] for row in stats] == [1]


def test_graphs_skip_archived(seeded):
    archive_bob()

    # A 100 year window reaches the 1970 seed rows.
    result = graphs.Graphs().get_total_plays_by_top_10_users(time_range=36500)

    assert result["categories"] == ["Alice"]


@pytest.mark.parametrize("user_id, categories", [("2", ["bob"]), ("1,2", ["Alice", "bob"])])
def test_graphs_return_an_archived_user_asked_for_by_id(seeded, user_id, categories):
    archive_bob()

    result = graphs.Graphs().get_total_plays_by_top_10_users(time_range=36500, user_id=user_id)

    assert result["categories"] == categories


def test_library_stats_skip_archived(library):
    archive_bob()

    library = webserve.WebInterface().get_library_list(grouping=0)["data"][0]
    user_stats = libraries.Libraries().get_user_stats(section_id=1)

    assert library["plays"] == 4
    assert [row["user_id"] for row in user_stats] == [1]


class FakePlexTV:
    def __init__(self, user_ids):
        self.user_ids = user_ids

    def get_full_users_list(self):
        return [{"user_id": str(user_id), "username": "user%d" % user_id, "title": "",
                 "thumb": "", "is_active": 1, "shared_libraries": ["1"]}
                for user_id in self.user_ids]


@pytest.mark.parametrize("was_active, auto_unarchive, is_archived", [
    (0, 1, 0),  # returned to the server, so unarchived
    (1, 1, 1),  # never left the server, so an admin choice stays
    (0, 0, 1),  # setting off
])
def test_refresh_users_unarchives_returning_users(seeded, monkeypatch, was_active,
                                                  auto_unarchive, is_archived):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    plexpy.CONFIG.AUTO_UNARCHIVE_USERS = auto_unarchive
    seeded.action("UPDATE users SET is_archived = 1, is_active = ? WHERE user_id = 2", [was_active])
    monkeypatch.setattr(plextv, "PlexTV", lambda: FakePlexTV([1, 2]))

    assert users.refresh_users() is True

    assert seeded.select_single(
        "SELECT is_archived, is_active FROM users WHERE user_id = 2"
    ) == {"is_archived": is_archived, "is_active": 1}


def test_refresh_users_keeps_a_user_that_is_still_gone_archived(seeded, monkeypatch):
    plexpy.CONFIG.PMS_IDENTIFIER = "server"
    seeded.action("UPDATE users SET is_archived = 1, is_active = 0 WHERE user_id = 2")
    monkeypatch.setattr(plextv, "PlexTV", lambda: FakePlexTV([1]))

    users.refresh_users()

    assert seeded.select_single(
        "SELECT is_archived FROM users WHERE user_id = 2") == {"is_archived": 1}


class FakeGuestPlexTV:
    def __init__(self, token=None, headers=None):
        pass

    def get_plex_account_details(self):
        return {"user_id": "2"}

    def get_server_token(self):
        return "server-token"


def test_archived_guest_cannot_log_in_until_unarchived(seeded, monkeypatch):
    plexpy.CONFIG.ALLOW_GUEST_ACCESS = 1
    seeded.action("UPDATE users SET allow_guest = 1 WHERE user_id = 2")
    monkeypatch.setattr(webauth, "PlexTV", FakeGuestPlexTV)
    monkeypatch.setattr(webauth, "refresh_users", lambda: None)

    archive_bob()
    assert webauth.plex_user_login(token="user-token") is None

    # Archiving leaves allow_guest alone, so unarchiving restores the login.
    users.Users().set_config(user_id=2, is_archived=0)
    assert webauth.plex_user_login(token="user-token")[1] == "guest"


def test_most_concurrent_skips_archived(late_bob):
    archive_bob()

    stats = datafactory.DataFactory().get_home_stats(stats_cards=["most_concurrent"], after="1970-01-01")

    assert stats[0]["rows"][0]["count"] == 1


def test_stream_type_graph_skips_archived(late_bob):
    archive_bob()

    # With no user_id, the archived filter is the query's only WHERE clause.
    result = graphs.Graphs().get_total_concurrent_streams_per_stream_type(time_range=36500)

    assert max(result["series"][3]["data"]) == 1


def test_library_card_and_last_accessed_skip_archived(late_bob, library):
    archive_bob()

    card = datafactory.DataFactory().get_library_stats(library_cards=["1"])["movie"][0]
    details = libraries.Libraries().get_library_details(section_id=1, include_last_accessed=True)

    assert card["row_id"] == 6
    assert details["last_accessed"] == 5000


def test_library_watch_time_and_recently_watched_skip_archived(late_bob):
    archive_bob()

    # Day 0 is all time. 36500 days reaches the 1970 seed rows.
    watch_time = libraries.Libraries().get_watch_time_stats(section_id=1, grouping=False,
                                                            query_days="0,36500")
    recent = libraries.Libraries().get_recently_watched(section_id=1)

    assert [row["total_plays"] for row in watch_time] == [4, 4]
    assert {row["user"] for row in recent} == {"alice"}


def test_item_watch_time_skips_archived(late_bob):
    archive_bob()
    factory = datafactory.DataFactory()

    # bob's row 3 and alice's row 6 played rating_key 202, which has guid-202.
    by_key = factory.get_watch_time_stats(rating_key=202, grouping=False, query_days="0,36500")
    by_guid = factory.get_watch_time_stats(guid="guid-202", grouping=False, query_days="0,36500")
    users_by_guid = factory.get_user_stats(guid="guid-202", grouping=False)

    assert [row["total_plays"] for row in by_key] == [1, 1]
    assert [row["total_plays"] for row in by_guid] == [1, 1]
    assert [row["user_id"] for row in users_by_guid] == [1]


def test_media_info_play_count_skips_archived(library, monkeypatch):
    # A stub media info cache stands in for the Plex server.
    rows = [{"rating_key": "202", "sort_title": "Beta Movie", "file_size": "", "media_index": ""}]
    monkeypatch.setattr(libraries.Libraries, "_load_media_info_cache",
                        lambda self, section_id=None, rating_key=None: (0, rows, 1))
    archive_bob()

    result = webserve.WebInterface().get_library_media_info(section_id=1)

    # bob's row 3 and alice's row 6 both played rating_key 202.
    assert result["data"][0]["play_count"] == 1


def test_upgrade_adds_the_archive_column(app_db):
    app_db.action("ALTER TABLE users DROP COLUMN is_archived")

    plexpy.dbcheck()

    assert app_db.select_single("SELECT is_archived FROM users WHERE user_id = 0") == {"is_archived": 0}


SHOW_ARCHIVED = '<i class="fa fa-archive"></i> Show archived'


@pytest.fixture
def web_pages(library, monkeypatch):
    # Render the real templates. serve_template needs the repo root and a
    # CSRF token from the CherryPy session. The info page falls back to
    # history metadata when the Plex server has no match.
    monkeypatch.setattr(plexpy, "PROG_DIR", os.path.dirname(os.path.dirname(plexpy.__file__)))
    monkeypatch.setattr(webserve, "TEMPLATE_LOOKUP", None)
    monkeypatch.setattr(webserve, "get_session_csrf_token", lambda: "")
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_metadata_details", lambda self, **kwargs: {})
    library.action("UPDATE session_history_metadata SET summary = ''")
    return webserve.WebInterface()


def show_archived_pages(web):
    return [web.history(), web.library(section_id=1), web.info(rating_key=202, source="history"), web.graphs()]


def test_show_archived_button_on_every_page(web_pages):
    assert not any(SHOW_ARCHIVED in page for page in show_archived_pages(web_pages))

    archive_bob()

    assert all(SHOW_ARCHIVED in page for page in show_archived_pages(web_pages))


def test_show_archived_button_is_admin_only(web_pages, monkeypatch):
    monkeypatch.setattr(webserve, "get_session_info",
                        lambda: {"user_id": "1", "user": "alice", "user_group": "guest", "exp": None})
    archive_bob()

    assert not any(SHOW_ARCHIVED in page for page in show_archived_pages(web_pages))


def test_graph_popup_keeps_the_show_archived_state(web_pages):
    # A click on a graph passes the button state to the history popup,
    # which passes it on to get_history.
    shown = web_pages.history_table_modal(user_id="", start_date="1970-01-01", include_archived="1")
    default = web_pages.history_table_modal(user_id="", start_date="1970-01-01")

    assert 'include_archived: "1"' in shown
    assert 'include_archived: "0"' in default


GRAPH_ENDPOINTS = [
    "get_plays_by_date", "get_plays_by_dayofweek", "get_plays_by_hourofday", "get_plays_per_month",
    "get_plays_by_top_10_platforms", "get_plays_by_top_10_users", "get_plays_by_stream_type",
    "get_concurrent_streams_by_stream_type", "get_plays_by_source_resolution",
    "get_plays_by_stream_resolution", "get_stream_type_by_top_10_users", "get_stream_type_by_top_10_platforms",
]


@pytest.mark.parametrize("name", GRAPH_ENDPOINTS)
def test_graph_show_archived_matches_the_unarchived_graph(late_bob, library, name):
    graph = getattr(webserve.WebInterface(), name)
    # The seed rows are from 1970. The per month graph counts months.
    time_range = "1200" if name == "get_plays_per_month" else "36500"
    before = graph(time_range=time_range)

    archive_bob()

    assert graph(time_range=time_range) != before
    assert graph(time_range=time_range, include_archived="1") == before
