"""Archived users.

An archived user is hidden from the users list, the history table, and
every statistic. Their session_history rows stay. The seed is the shared
six-row history from test_history_table: alice (user_id 1) owns rows 1,
2, 4, 6 and bob (user_id 2) owns rows 3 and 5, all in section 1. The
tests archive bob.
"""

import json
import os
import re

import pytest

import plexpy
from plexpy import datafactory, graphs, libraries, plextv, pmsconnect, users, webauth, webserve

from tests.test_history_table import build_draw, call_history, insert_history_row, seed_history


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


TOKENS = {"tok-alice", "tok-bob", "tok-bob-admin"}


@pytest.fixture
def logins(seeded):
    # alice and bob each have a guest session. bob also has an admin session.
    for user_id, group, token in ((1, "guest", "tok-alice"), (2, "guest", "tok-bob"), (2, "admin", "tok-bob-admin")):
        seeded.action("INSERT INTO user_login (timestamp, user_id, user_group, success, jwt_token) "
                      "VALUES (?, ?, ?, ?, ?)", [1700000000, user_id, group, 1, token])
    return seeded


def live_tokens():
    # check_jwt_token rejects a token that get_user_login no longer finds.
    return {token for token in TOKENS if users.Users().get_user_login(jwt_token=token)}


def test_archive_logs_out_the_guest(logins):
    web = webserve.WebInterface()

    web.edit_user(user_id="2", friendly_name="Bob", is_archived="0")
    assert live_tokens() == TOKENS

    web.edit_user(user_id="2", is_archived="1")
    assert live_tokens() == {"tok-alice", "tok-bob-admin"}


def test_delete_logs_out_the_guest_and_purge_does_not(logins):
    users.Users().delete(user_id=2, purge_only=True)
    assert live_tokens() == TOKENS

    users.Users().delete(user_id=2)
    assert live_tokens() == {"tok-alice", "tok-bob-admin"}


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


SHOW_ARCHIVED = 'id="nav-show-archived"'
ARCHIVED_INDICATOR = 'id="nav-archived-indicator"'


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
    # The settings menu is in base.html, so every full page has it.
    return [web.home(), web.users(), web.history(), web.library(section_id=1),
            web.info(rating_key=202, source="history"), web.graphs()]


def test_show_archived_is_in_the_settings_menu_on_every_page(web_pages):
    # With no archived user, the pages also ignore the stored choice.
    assert not any(SHOW_ARCHIVED in page or ARCHIVED_INDICATOR in page
                   or "getLocalStorage('include_archived'" in page
                   for page in show_archived_pages(web_pages))

    archive_bob()

    assert all(SHOW_ARCHIVED in page and ARCHIVED_INDICATOR in page
               for page in show_archived_pages(web_pages))


def test_show_archived_is_admin_only(web_pages, monkeypatch):
    # A guest page still defines include_archived, because the page scripts send it.
    monkeypatch.setattr(webserve, "get_session_info",
                        lambda: {"user_id": "1", "user": "alice", "user_group": "guest", "exp": None})
    archive_bob()

    for page in show_archived_pages(web_pages):
        assert SHOW_ARCHIVED not in page
        assert ARCHIVED_INDICATOR not in page
        assert "var include_archived = 0;" in page
        assert "getLocalStorage('include_archived'" not in page


def test_show_archived_resets_while_no_user_is_archived(web_pages, monkeypatch):
    # The next archive then starts with archived users hidden. A guest page
    # leaves the admin's choice alone.
    reset = "setLocalStorage('include_archived', 0, false);"
    assert all(reset in page for page in show_archived_pages(web_pages))

    archive_bob()
    assert not any(reset in page for page in show_archived_pages(web_pages))

    users.Users().set_config(user_id=2, is_archived=0)
    monkeypatch.setattr(webserve, "get_session_info",
                        lambda: {"user_id": "1", "user": "alice", "user_group": "guest", "exp": None})
    assert not any(reset in page for page in show_archived_pages(web_pages))


def test_graph_popup_keeps_the_show_archived_state(web_pages):
    # A graph click sends include_archived to the history popup. The popup
    # sends it to get_history.
    shown = web_pages.history_table_modal(user_id="", start_date="1970-01-01", include_archived="1")
    default = web_pages.history_table_modal(user_id="", start_date="1970-01-01")

    assert 'include_archived: "1"' in shown
    assert 'include_archived: "0"' in default


def test_show_archived_position(web_pages):
    archive_bob()
    page = web_pages.history()

    def in_order(*needles):
        positions = [page.index(n) for n in needles]
        return positions == sorted(positions)

    # The indicator sits left of the settings menu. The menu item comes right after Settings.
    assert in_order('<a href="graphs">', ARCHIVED_INDICATOR, 'id="settings-dropdown-menu"',
                    '<a href="settings">', SHOW_ARCHIVED, '<a href="logs">')


def activity_session(session_key, user_id, **extra):
    return dict({"session_key": session_key, "user_id": user_id, "username": "user%d" % user_id,
                 "friendly_name": "User %d" % user_id, "user_thumb": "", "media_type": "movie",
                 "state": "playing", "rating_key": "202", "section_id": "1", "live": 0}, **extra)


def test_activity_card_badges_an_archived_user(web_pages, monkeypatch):
    # PmsConnect copies is_archived into each session from the user details.
    # A session without the flag must not read as archived.
    sessions = [activity_session("1", 1, is_archived=0), activity_session("2", 2, is_archived=1),
                activity_session("3", 3)]
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_current_activity", lambda self: {"sessions": sessions})

    cards = {key: web_pages.get_current_activity_instance(session_key=key) for key in ("1", "2", "3")}

    assert {key for key, card in cards.items() if 'title="Archived user"' in card} == {"2"}


def test_activity_card_badges_a_deleted_user(web_pages, monkeypatch):
    # A deleted user shows the trash badge alone, even when also archived.
    sessions = [activity_session("1", 1, deleted_user=1), activity_session("2", 2, deleted_user=1, is_archived=1),
                activity_session("3", 3, deleted_user=0), activity_session("4", 4)]
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_current_activity", lambda self: {"sessions": sessions})

    cards = {key: web_pages.get_current_activity_instance(session_key=key) for key in ("1", "2", "3", "4")}

    assert {key for key, card in cards.items() if 'title="Deleted user"' in card} == {"1", "2"}
    assert 'fa-trash-o' in cards["2"] and 'title="Archived user"' not in cards["2"]
    assert all('title="Deleted user"' not in cards[key] for key in ("3", "4"))


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


@pytest.fixture
def collection(seeded, monkeypatch):
    # The collection holds rating_key 202. The seed sets parent_rating_key
    # to rating_key - 1, so it matches bob's row 3 and alice's row 6 by
    # rating_key and alice's row 4 (rating_key 203) by parent_rating_key.
    monkeypatch.setattr(pmsconnect.PmsConnect, "get_item_children",
                        lambda self, rating_key=None, media_type=None: {"children_list": [{"rating_key": "202"}]})
    return seeded


def collection_history(**kwargs):
    return webserve.WebInterface().get_history(media_type="collection", rating_key="900", grouping=0,
                                               include_activity=0, **kwargs)


def test_collection_history_skips_archived(collection):
    # The archived filter came after the three rating key clauses and became
    # a fourth OR, which returned every play of every user not archived.
    archive_bob()

    assert {row["row_id"] for row in collection_history()["data"]} == {4, 6}
    assert {row["row_id"] for row in collection_history(include_archived=1)["data"]} == {3, 4, 6}


def test_collection_history_keeps_the_other_filters(collection):
    # Rows 3 and 6 were transcoded, row 4 was direct play. Row 2 is a
    # transcode outside the collection.
    result = collection_history(transcode_decision="transcode")

    assert {row["row_id"] for row in result["data"]} == {3, 6}
    assert result["recordsFiltered"] == 2


def test_collection_history_total_duration(collection):
    # Rows 3, 4, and 6 play 600, 200, and 900 seconds. The total duration
    # query used to get the three rating key clauses ANDed and summed nothing.
    assert collection_history()["total_duration"] == "28 mins 20 secs"


def test_guest_collection_history_shows_only_their_rows(collection, monkeypatch):
    # alice's session filter came after the rating key clauses too, so a
    # guest saw bob's row 3.
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "1")

    assert {row["row_id"] for row in collection_history()["data"]} == {4, 6}


@pytest.mark.parametrize("kwargs, row_ids", [
    ({"user_id": "2"}, {3, 5}),
    ({"user_id": "1,2"}, {1, 2, 3, 4, 5, 6}),
    ({"user": "bob"}, {3, 5}),
])
def test_history_returns_an_archived_user_asked_for_by_name_or_id(seeded, kwargs, row_ids):
    # The same rule as the graphs and home stats. A named user wins over
    # the archived filter.
    archive_bob()

    result = webserve.WebInterface().get_history(grouping=0, include_activity=0, **kwargs)

    assert {row["row_id"] for row in result["data"]} == row_ids


def test_archived_guest_history_shows_their_own_rows(seeded, monkeypatch):
    # The guest session names its own user, so the archived filter does
    # not apply to it.
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: "2")
    archive_bob()

    assert {row["row_id"] for row in call_history(grouping=False)["data"]} == {3, 5}


def test_item_stats_include_archived_when_asked(late_bob):
    archive_bob()
    factory = datafactory.DataFactory()

    # bob's row 3 and alice's row 6 played rating_key 202, which has guid-202.
    by_key = factory.get_watch_time_stats(rating_key=202, grouping=False, query_days="0",
                                          include_archived=True)
    by_guid = factory.get_watch_time_stats(guid="guid-202", grouping=False, query_days="0",
                                           include_archived=True)
    users_by_key = factory.get_user_stats(rating_key=202, grouping=False, include_archived=True)
    users_by_guid = factory.get_user_stats(guid="guid-202", grouping=False, include_archived=True)

    assert [row["total_plays"] for row in by_key + by_guid] == [2, 2]
    assert [row["user_id"] for row in users_by_key] == [1, 2]
    assert [row["user_id"] for row in users_by_guid] == [1, 2]


def test_item_stats_pages_take_include_archived(web_pages):
    # The info page sends include_archived as 0 or 1.
    archive_bob()

    users_shown = web_pages.item_user_stats(rating_key=202, include_archived="1")
    users_default = web_pages.item_user_stats(rating_key=202, include_archived="0")
    plays_shown = web_pages.item_watch_time_stats(rating_key=202, include_archived="1")
    plays_default = web_pages.item_watch_time_stats(rating_key=202, include_archived="0")

    assert 'title="bob"' in users_shown
    assert 'title="bob"' not in users_default
    # bob adds a second play of rating_key 202.
    all_time = r"All Time</h4>\s*<h3>(\d+)</h3>"
    assert re.search(all_time, plays_shown).group(1) == "2"
    assert re.search(all_time, plays_default).group(1) == "1"


def test_item_user_stats_api_takes_include_archived(seeded):
    # The API dispatcher passes the query parameters to the method as kwargs.
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_item_user_stats(rating_key=202, grouping=0, include_archived="1")
    hidden = web.get_item_user_stats(rating_key=202, grouping=0, include_archived="0")

    assert {row["user_id"] for row in shown} == {1, 2}
    assert {row["user_id"] for row in hidden} == {1}


def test_item_watch_time_stats_api_takes_include_archived(seeded):
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_item_watch_time_stats(rating_key=202, grouping=0, query_days="0", include_archived="1")
    hidden = web.get_item_watch_time_stats(rating_key=202, grouping=0, query_days="0", include_archived="0")

    assert shown[0]["total_plays"] == 2
    assert hidden[0]["total_plays"] == 1


def test_library_stats_include_archived_when_asked(library):
    archive_bob()
    library_data = libraries.Libraries()

    # Day 0 is all time. 36500 days reaches the 1970 seed rows.
    watch_time = library_data.get_watch_time_stats(section_id=1, grouping=False, query_days="0,36500",
                                                   include_archived=True)
    user_stats = library_data.get_user_stats(section_id=1, include_archived=True)

    assert [row["total_plays"] for row in watch_time] == [6, 6]
    assert [row["user_id"] for row in user_stats] == [1, 2]


def test_library_stats_pages_take_include_archived(web_pages):
    # The library page sends include_archived as 0 or 1.
    archive_bob()

    users_shown = web_pages.library_user_stats(section_id=1, include_archived="1")
    users_hidden = web_pages.library_user_stats(section_id=1, include_archived="0")
    plays_shown = web_pages.library_watch_time_stats(section_id=1, include_archived="1")
    plays_hidden = web_pages.library_watch_time_stats(section_id=1, include_archived="0")

    assert 'title="bob"' in users_shown
    assert 'title="bob"' not in users_hidden
    # Grouped plays. alice has 3 and bob has 2.
    all_time = r"All Time</h4>\s*<h3>(\d+)</h3>"
    assert re.search(all_time, plays_shown).group(1) == "5"
    assert re.search(all_time, plays_hidden).group(1) == "3"


def test_library_recently_watched_includes_archived_when_asked(late_bob, web_pages):
    # rating_key 204 is Delta Movie, which only bob played. The page template
    # reads parent_title, which the seed leaves NULL.
    late_bob.action("UPDATE session_history_metadata SET parent_title = ''")
    archive_bob()

    shown = libraries.Libraries().get_recently_watched(section_id=1, include_archived=True)
    page_shown = web_pages.library_recently_watched(section_id=1, include_archived="1")
    page_hidden = web_pages.library_recently_watched(section_id=1, include_archived="0")

    assert 204 in {row["rating_key"] for row in shown}
    assert "Delta Movie" in page_shown
    assert "Delta Movie" not in page_hidden


def test_library_user_stats_api_takes_include_archived(library):
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_library_user_stats(section_id=1, grouping=0, include_archived="1")
    hidden = web.get_library_user_stats(section_id=1, grouping=0, include_archived="0")

    assert {row["user_id"] for row in shown} == {1, 2}
    assert {row["user_id"] for row in hidden} == {1}


def test_library_watch_time_stats_api_takes_include_archived(library):
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_library_watch_time_stats(section_id=1, grouping=0, query_days="0", include_archived="1")
    hidden = web.get_library_watch_time_stats(section_id=1, grouping=0, query_days="0", include_archived="0")

    assert shown[0]["total_plays"] == 6
    assert hidden[0]["total_plays"] == 4


def test_home_stats_include_archived_when_asked(late_bob, library):
    archive_bob()
    data_factory = datafactory.DataFactory()

    top_users = data_factory.get_home_stats(stats_cards=["top_users"], after="1970-01-01", include_archived=True)
    concurrent = data_factory.get_home_stats(stats_cards=["most_concurrent"], after="1970-01-01",
                                             include_archived=True)
    card = data_factory.get_library_stats(library_cards=["1"], include_archived=True)

    assert {row["user_id"] for row in top_users[0]["rows"]} == {1, 2}
    assert concurrent[0]["rows"][0]["count"] == 2
    # Row 7 is bob's last play.
    assert card["movie"][0]["row_id"] == 7


def test_home_page_stats_take_include_archived(late_bob, web_pages):
    # The home page sends include_archived as 0 or 1. A library card shows
    # the thumb of the library's last play. Row 7 is bob's last play.
    late_bob.action("UPDATE session_history_metadata SET thumb = '/thumb/' || id")
    plexpy.CONFIG.HOME_STATS_CARDS = ["top_users"]
    plexpy.CONFIG.HOME_LIBRARY_CARDS = ["1"]
    archive_bob()

    # 36500 days reaches the 1970 seed rows.
    assert "bob" in web_pages.home_stats(time_range=36500, include_archived="1")
    assert "bob" not in web_pages.home_stats(time_range=36500, include_archived="0")
    assert 'data-thumb="/thumb/7"' in web_pages.library_stats(include_archived="1")
    assert 'data-thumb="/thumb/6"' in web_pages.library_stats(include_archived="0")


def test_home_stats_api_takes_include_archived(seeded):
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_home_stats(stat_id="top_users", after="1970-01-01", include_archived="1")
    hidden = web.get_home_stats(stat_id="top_users", after="1970-01-01", include_archived="0")

    assert {row["user_id"] for row in shown["rows"]} == {1, 2}
    assert {row["user_id"] for row in hidden["rows"]} == {1}


def test_libraries_table_includes_archived_when_asked(late_bob, library):
    # The libraries page sends include_archived as 0 or 1. Row 7 is bob's
    # last play, Delta Movie at 5100. Row 6 is alice's, Beta Movie at 5000.
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_library_list(grouping=0, include_archived="1")["data"][0]
    hidden = web.get_library_list(grouping=0, include_archived="0")["data"][0]

    assert (shown["plays"], shown["last_accessed"], shown["last_played"]) == (7, 5100, "Delta Movie")
    assert (hidden["plays"], hidden["last_accessed"], hidden["last_played"]) == (4, 5000, "Beta Movie")


def test_media_info_play_count_includes_archived_when_asked(library, monkeypatch):
    # The library page sends include_archived as 0 or 1. So do the child
    # tables under each row.
    rows = [{"rating_key": "202", "sort_title": "Beta Movie", "file_size": "", "media_index": ""}]
    monkeypatch.setattr(libraries.Libraries, "_load_media_info_cache",
                        lambda self, section_id=None, rating_key=None: (0, rows, 1))
    archive_bob()
    web = webserve.WebInterface()

    # Each call writes play_count into the same stub row, so read it right away.
    shown = web.get_library_media_info(section_id=1, include_archived="1")["data"][0]["play_count"]
    hidden = web.get_library_media_info(section_id=1, include_archived="0")["data"][0]["play_count"]

    assert (shown, hidden) == (2, 1)


def test_get_library_api_takes_include_archived(late_bob, library):
    # Row 7 is bob's last play. It starts at 5100, after alice's at 5000.
    archive_bob()
    web = webserve.WebInterface()

    shown = web.get_library(section_id=1, include_last_accessed=1, include_archived="1")
    hidden = web.get_library(section_id=1, include_last_accessed=1, include_archived="0")

    assert (shown["last_accessed"], hidden["last_accessed"]) == (5100, 5000)
