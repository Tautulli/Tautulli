"""The watch time windows on the item page."""

import plexpy
from plexpy import database, datafactory, helpers, pmsconnect

from tests.test_history_table import insert_history_row

DAY = 24 * 60 * 60
NOW = 100 * DAY


def seed(app_db, monkeypatch):
    monkeypatch.setattr(helpers, "timestamp", lambda: NOW)
    # Item 301. Row 1 stops on the 1-day edge and row 2 one minute
    # before it. Rows 2 and 3 share reference_id 2. Row 2 has 100 s paused.
    insert_history_row(app_db, 1, 1, 1, "alice", NOW - DAY - 600, NOW - DAY, 301, "Movie", "movie")
    insert_history_row(app_db, 2, 2, 1, "alice", NOW - DAY - 960, NOW - DAY - 60, 301, "Movie", "movie")
    insert_history_row(app_db, 3, 2, 1, "alice", NOW - 10 * DAY, NOW - 10 * DAY + 1200, 301, "Movie", "movie")
    insert_history_row(app_db, 4, 4, 1, "alice", NOW - 40 * DAY, NOW - 40 * DAY + 300, 301, "Movie", "movie")
    app_db.action("UPDATE session_history SET paused_counter = 100 WHERE id = 2")
    # Item 302 has one play of zero length.
    insert_history_row(app_db, 5, 5, 1, "alice", NOW - 100, NOW - 100, 302, "Empty", "movie")
    # Episode 303 of season 402 of show 501.
    insert_history_row(app_db, 6, 6, 1, "alice", NOW - 200, NOW - 100, 303, "Episode", "episode")
    app_db.action("UPDATE session_history SET parent_rating_key = 402, grandparent_rating_key = 501 WHERE id = 6")


def windows(rows):
    return [(row["query_days"], row["total_time"], row["total_plays"]) for row in rows]


def test_each_window_counts_its_own_plays(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    factory = datafactory.DataFactory()

    by_key = factory.get_watch_time_stats(rating_key=301, grouping=False)
    by_guid = factory.get_watch_time_stats(guid="guid-301", grouping=False)
    grouped = factory.get_watch_time_stats(rating_key=301, grouping=True)

    expected = [(1, 600, 1), (7, 1400, 2), (30, 2600, 3), (0, 2900, 4)]
    assert windows(by_key) == expected
    assert windows(by_guid) == expected
    assert windows(grouped) == [(1, 600, 1), (7, 1400, 2), (30, 2600, 2), (0, 2900, 3)]


def test_a_show_and_a_season_count_their_episodes(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    factory = datafactory.DataFactory()

    show = factory.get_watch_time_stats(rating_key=501, grouping=False, query_days="0")
    season = factory.get_watch_time_stats(rating_key=402, grouping=False, query_days="0")

    assert windows(show) == windows(season) == [(0, 100, 1)]


def test_a_rating_key_that_is_not_a_number_returns_nothing(app_db, monkeypatch):
    seed(app_db, monkeypatch)

    assert datafactory.DataFactory().get_watch_time_stats(rating_key="abc") == []


def test_a_window_with_no_watch_time_reports_no_plays(app_db, monkeypatch):
    seed(app_db, monkeypatch)

    rows = datafactory.DataFactory().get_watch_time_stats(rating_key=302, grouping=False, query_days="1,0")

    assert windows(rows) == [(1, 0, 0), (0, 0, 0)]


def test_a_guest_sees_an_item_from_a_shared_library_only(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    factory = datafactory.DataFactory()

    # Two hours later, the 1-day window of item 301 is empty.
    monkeypatch.setattr(helpers, "timestamp", lambda: NOW + 2 * 60 * 60)
    monkeypatch.setattr(plexpy.session, "get_session_shared_libraries", lambda: ("1",))
    shared = factory.get_watch_time_stats(rating_key=301, grouping=False)
    monkeypatch.setattr(plexpy.session, "get_session_shared_libraries", lambda: ("2",))
    unshared = factory.get_watch_time_stats(rating_key=301, grouping=False)

    assert windows(shared)[0] == (1, 0, 0)
    assert unshared == []


def test_a_guest_sees_nothing_for_an_item_also_played_in_an_unshared_library(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    app_db.action("UPDATE session_history SET section_id = 2 WHERE id = 4")
    factory = datafactory.DataFactory()

    results = {}
    for shared in (("1",), ("2",), ("1", "2")):
        monkeypatch.setattr(plexpy.session, "get_session_shared_libraries", lambda shared=shared: shared)
        results[shared] = factory.get_watch_time_stats(rating_key=301, grouping=False, query_days="0")
    # An item with no plays has no library to check
    missing = factory.get_watch_time_stats(rating_key=999, grouping=False, query_days="0")

    assert results[("1",)] == results[("2",)] == []
    assert windows(results[("1", "2")]) == [(0, 2900, 4)]
    assert missing == []


def test_a_null_paused_counter_counts_as_zero(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    app_db.action("UPDATE session_history SET paused_counter = NULL WHERE id IN (1, 4)")

    rows = datafactory.DataFactory().get_watch_time_stats(rating_key=301, grouping=False)

    assert windows(rows) == [(1, 600, 1), (7, 1400, 2), (30, 2600, 3), (0, 2900, 4)]


def test_a_rating_key_wins_over_a_guid(app_db, monkeypatch):
    seed(app_db, monkeypatch)

    rows = datafactory.DataFactory().get_watch_time_stats(rating_key=302, guid="guid-301", grouping=False,
                                                          query_days="0")

    assert windows(rows) == [(0, 0, 0)]


def test_a_failed_query_returns_nothing(app_db, monkeypatch):
    seed(app_db, monkeypatch)

    def fail(self, query, args=None):
        raise RuntimeError("boom")
    monkeypatch.setattr(database.MonitorDatabase, "select_single", fail)

    assert datafactory.DataFactory().get_watch_time_stats(rating_key=301) == []


def test_collection_and_playlist_children_are_summed(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    calls = []

    class FakePms:
        def get_item_children(self, rating_key=None, media_type=None):
            calls.append((rating_key, media_type))
            return {"children_list": [{"rating_key": 301}, {"rating_key": 302}]}
    monkeypatch.setattr(pmsconnect, "PmsConnect", FakePms)
    factory = datafactory.DataFactory()

    for media_type in ("collection", "playlist"):
        rows = factory.get_watch_time_stats(rating_key=900, media_type=media_type, grouping=False, query_days="0")
        assert windows(rows) == [(0, 2900, 5)]
    assert calls == [(900, "collection"), (900, "playlist")]


def test_grouping_defaults_to_the_config_setting(app_db, monkeypatch):
    seed(app_db, monkeypatch)
    factory = datafactory.DataFactory()

    monkeypatch.setattr(plexpy.CONFIG, "GROUP_HISTORY_TABLES", 1)
    grouped = factory.get_watch_time_stats(rating_key=301, query_days="0")
    monkeypatch.setattr(plexpy.CONFIG, "GROUP_HISTORY_TABLES", 0)
    ungrouped = factory.get_watch_time_stats(rating_key=301, query_days="0")

    assert windows(grouped) == [(0, 2900, 3)]
    assert windows(ungrouped) == [(0, 2900, 4)]
