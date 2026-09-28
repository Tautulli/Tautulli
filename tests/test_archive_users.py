"""Archived users.

An archived user is hidden from the users list, the history table, and
every statistic. Their session_history rows stay. The seed is the shared
six-row history from test_history_table: alice (user_id 1) owns rows 1,
2, 4, 6 and bob (user_id 2) owns rows 3 and 5, all in section 1. The
tests archive bob.
"""

import json

import pytest

import plexpy
from plexpy import datafactory, graphs, libraries, plextv, users, webauth, webserve

from tests.test_history_table import build_draw, call_history, seed_history


ARCHIVE_PENDING = (
    "users have no archive flag, so a user that left the server stays in "
    "the users list, the history table, and every statistic"
)

pytestmark = pytest.mark.xfail(reason=ARCHIVE_PENDING)


@pytest.fixture
def seeded(app_db):
    seed_history(app_db)
    return app_db


def archive_bob():
    users.Users().set_config(user_id=2, is_archived=1)


def history_user_ids(include_archived):
    result = webserve.WebInterface().get_history(grouping=0, include_activity=0,
                                                 include_archived=include_archived)
    return {row["user_id"] for row in result["data"]}


def test_archive_keeps_history_and_unarchive_restores(seeded):
    assert users.Users().archive(user_id=2) is True

    assert seeded.select_single(
        "SELECT is_archived, keep_history, deleted_user FROM users WHERE user_id = 2"
    ) == {"is_archived": 1, "keep_history": 1, "deleted_user": 0}
    assert seeded.select_single(
        "SELECT COUNT(*) AS plays FROM session_history WHERE user_id = 2") == {"plays": 2}

    assert users.Users().unarchive(user_id=2) is True
    assert seeded.select_single(
        "SELECT is_archived FROM users WHERE user_id = 2") == {"is_archived": 0}


def test_archive_by_row_ids(seeded):
    row_ids = ",".join(str(row["id"]) for row in seeded.select(
        "SELECT id FROM users WHERE user_id IN (1, 2)"))

    assert users.Users().archive(row_ids=row_ids) is True

    assert users.Users().get_archived_user_ids() == [1, 2]


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


def test_item_user_stats_skip_archived(seeded):
    archive_bob()

    # rating_key 202 is Beta Movie, played by bob (row 3) and alice (row 6).
    stats = datafactory.DataFactory().get_user_stats(rating_key=202)

    assert [row["user_id"] for row in stats] == [1]


@pytest.mark.parametrize("user_id", [None, "1,2"])
def test_graphs_skip_archived(seeded, user_id):
    archive_bob()

    # A 100 year window reaches the 1970 seed rows.
    result = graphs.Graphs().get_total_plays_by_top_10_users(time_range=36500, user_id=user_id)

    assert result["categories"] == ["Alice"]


def test_library_stats_skip_archived(seeded):
    seeded.action("INSERT INTO library_sections (server_id, section_id, section_name, section_type) "
                  "VALUES ('server', 1, 'Mixed', 'movie')")
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

    users.Users().archive(user_id=2)
    assert webauth.plex_user_login(token="user-token") is None

    # Archiving leaves allow_guest alone, so unarchiving restores the login.
    users.Users().unarchive(user_id=2)
    assert webauth.plex_user_login(token="user-token")[1] == "guest"
