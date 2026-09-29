import json

import plexpy
from plexpy import common
from plexpy import datafactory


# ---------------------------------------------------------------------------
# datafactory.DataFactory.get_datatables_history
#
# Draw shape reduced from webserve.py's get_history(): when the caller
# sends no json_data, get_history builds this exact dt_columns list and
# passes it through helpers.build_datatables_json to make the draw dict
# that ends up as kwargs['json_data'].
# ---------------------------------------------------------------------------

HISTORY_COLUMNS = [
    ("date", True, False),
    ("friendly_name", True, True),
    ("ip_address", True, True),
    ("platform", True, True),
    ("product", True, True),
    ("player", True, True),
    ("full_title", True, True),
    ("started", True, False),
    ("paused_counter", True, False),
    ("stopped", True, False),
    ("duration", True, False),
    ("watched_status", False, False),
]


def build_draw(order_column="date", direction="desc", start=0, length=25, search="", draw=1):
    # build_datatables_json always defaults the order to date descending, so
    # a real draw never arrives with an empty order list.
    names = [c[0] for c in HISTORY_COLUMNS]
    order = [{"column": names.index(order_column), "dir": direction}]

    return {
        "draw": draw,
        "start": start,
        "length": length,
        "search": {"value": search, "regex": False},
        "order": order,
        "columns": [
            {"data": name, "orderable": orderable, "searchable": searchable,
             "search": {"value": "", "regex": False}}
            for name, orderable, searchable in HISTORY_COLUMNS
        ],
    }


def call_history(grouping=True, custom_where=None, draw=None):
    factory = datafactory.DataFactory()
    return factory.get_datatables_history(
        kwargs={"json_data": json.dumps(draw or build_draw())},
        custom_where=custom_where or [],
        grouping=grouping,
        # Keep the "sessions" table union out of scope: HISTORY_TABLE_ACTIVITY
        # defaults on, but the test db never has live sessions to union in.
        include_activity=False,
    )


# Six session_history rows across two users (alice, bob) and three items.
# Rows 1 and 2 share reference_id 10 (a paused/resumed play of the same
# episode) -- the only multi-row group; every other reference_id groups a
# single row. started is distinct on every row so ordering and paging are
# unambiguous.
#
# Row 6 is marked live (session_history_metadata.live=1) even though its
# underlying media_type is "movie", same title as row 3 (Beta Movie). This
# is what the media_type_live CASE expression in get_datatables_history is
# for: media_type_live IN ['live'] must return row 6, and
# media_type_live IN ['movie'] must exclude it despite the shared title.
#
# columns: id, reference_id, user_id, user, started, stopped, paused_counter,
#          player, rating_key, title, media_type, transcode_decision, live
_HISTORY_ROWS = [
    (1, 10, 1, "alice", 1000, 1300, 0, "Roku", 201, "Alpha Show - Episode 1", "episode", "direct play", 0),
    (2, 10, 1, "alice", 1300, 1900, 50, "Chromecast", 201, "Alpha Show - Episode 1", "episode", "transcode", 0),
    (3, 11, 2, "bob", 2000, 2600, 0, "Shield", 202, "Beta Movie", "movie", "transcode", 0),
    (4, 12, 1, "alice", 3000, 3200, 0, "Roku", 203, "Gamma Track", "track", "direct play", 0),
    (5, 13, 2, "bob", 4000, 4400, 0, "Shield", 201, "Alpha Show - Episode 1", "episode", "direct play", 0),
    (6, 14, 1, "alice", 5000, 5900, 0, "Roku", 202, "Beta Movie", "movie", "transcode", 1),
]


def seed_history(app_db):
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (1, 'alice', 'Alice')")
    # Blank friendly_name: get_datatables_history falls back to username.
    app_db.action("INSERT INTO users (user_id, username, friendly_name) VALUES (2, 'bob', '')")

    for (row_id, ref_id, user_id, user, started, stopped, paused,
         player, rating_key, title, media_type, transcode, live) in _HISTORY_ROWS:
        app_db.action(
            "INSERT INTO session_history (id, reference_id, started, stopped, rating_key, "
            "user_id, user, ip_address, paused_counter, player, product, platform, "
            "machine_id, location, secure, relayed, media_type, section_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [row_id, ref_id, started, stopped, rating_key, user_id, user,
             "10.0.0.%d" % user_id, paused, player, "Plex", player,
             "mach%d" % row_id, "lan", 1, 0, media_type, 1],
        )
        app_db.action(
            "INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, "
            "grandparent_rating_key, title, full_title, year, duration, guid, live, media_type) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [row_id, rating_key, rating_key - 1, rating_key - 2, title, title,
             2020, 1800, "guid-%d" % rating_key, live, media_type],
        )
        app_db.action(
            "INSERT INTO session_history_media_info (id, rating_key, transcode_decision) "
            "VALUES (?,?,?)",
            [row_id, rating_key, transcode],
        )


def insert_history_row(app_db, row_id, ref_id, user_id, user, started, stopped,
                       rating_key, title, media_type, platform="Roku", view_offset=0,
                       duration=1800, parent_thumb=None, grandparent_thumb=None):
    # Same shape as seed_history's insert, but with the extra knobs (platform,
    # view_offset, duration, thumbs) that the shared seed leaves at their
    # column defaults. Used by tests that need one specific combination
    # rather than extending the shared six-row seed.
    app_db.action(
        "INSERT INTO session_history (id, reference_id, started, stopped, rating_key, "
        "user_id, user, ip_address, paused_counter, player, product, platform, "
        "machine_id, location, secure, relayed, media_type, section_id, view_offset) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [row_id, ref_id, started, stopped, rating_key, user_id, user,
         "10.0.0.%d" % user_id, 0, platform, "Plex", platform,
         "mach%d" % row_id, "lan", 1, 0, media_type, 1, view_offset],
    )
    app_db.action(
        "INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, "
        "grandparent_rating_key, title, full_title, year, duration, guid, live, media_type, "
        "parent_thumb, grandparent_thumb) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [row_id, rating_key, rating_key - 1, rating_key - 2, title, title,
         2021, duration, "guid-%d" % rating_key, 0, media_type,
         parent_thumb, grandparent_thumb],
    )
    app_db.action(
        "INSERT INTO session_history_media_info (id, rating_key, transcode_decision) "
        "VALUES (?,?,?)",
        [row_id, rating_key, "direct play"],
    )


# ---------------------------------------------------------------------------
# Grouping: reference_id groups vs one row per session_history row.
# ---------------------------------------------------------------------------

def test_grouping_on_aggregates_by_reference_id(app_db):
    seed_history(app_db)

    grouped = call_history(grouping=True)

    # 5 distinct reference_ids: group 10 (rows 1+2) plus one each for 11-14.
    assert grouped["recordsFiltered"] == 5
    assert len(grouped["data"]) == 5
    # recordsTotal is a raw session_history row count, not group count.
    assert grouped["recordsTotal"] == 6

    group = next(row for row in grouped["data"] if row["reference_id"] == 10)
    assert group["group_count"] == 2
    assert group["started"] == 1000
    assert group["stopped"] == 1900
    # (1300-1000) + (1900-1300) - (0 + 50) paused
    assert group["duration"] == 850


def test_grouping_off_returns_every_row(app_db):
    seed_history(app_db)

    ungrouped = call_history(grouping=False)

    assert ungrouped["recordsFiltered"] == 6
    assert ungrouped["recordsTotal"] == 6
    assert len(ungrouped["data"]) == 6
    assert {row["group_count"] for row in ungrouped["data"]} == {1}


# ---------------------------------------------------------------------------
# custom_where filter
# ---------------------------------------------------------------------------

def test_custom_where_filters_by_user_id(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, custom_where=[["session_history.user_id IN", ["1"]]])

    # alice has rows 1, 2, 4, 6.
    assert result["recordsFiltered"] == 4
    assert result["recordsTotal"] == 6
    assert {row["row_id"] for row in result["data"]} == {1, 2, 4, 6}
    assert all(row["user_id"] == 1 for row in result["data"])


# ---------------------------------------------------------------------------
# Global search box
# ---------------------------------------------------------------------------

def test_search_filters_by_title(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, draw=build_draw(search="Beta"))

    assert result["recordsFiltered"] == 2
    assert {row["row_id"] for row in result["data"]} == {3, 6}
    assert all(row["full_title"] == "Beta Movie" for row in result["data"])


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------

def test_order_by_started_descending(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, draw=build_draw(order_column="started", direction="desc"))

    assert [row["row_id"] for row in result["data"]] == [6, 5, 4, 3, 2, 1]
    assert [row["started"] for row in result["data"]] == [5000, 4000, 3000, 2000, 1300, 1000]


# ---------------------------------------------------------------------------
# Paging: first page, a trailing partial page, and a start past the end.
# ---------------------------------------------------------------------------

def test_paging_first_and_trailing_pages(app_db):
    seed_history(app_db)
    draw = lambda start, length: build_draw(order_column="started", direction="desc",
                                            start=start, length=length)

    first_page = call_history(grouping=False, draw=draw(0, 3))
    assert [row["row_id"] for row in first_page["data"]] == [6, 5, 4]
    assert first_page["recordsTotal"] == 6
    assert first_page["recordsFiltered"] == 6

    trailing_page = call_history(grouping=False, draw=draw(4, 3))
    assert [row["row_id"] for row in trailing_page["data"]] == [2, 1]
    assert trailing_page["recordsTotal"] == 6
    assert trailing_page["recordsFiltered"] == 6

    past_the_end = call_history(grouping=False, draw=draw(6, 3))
    assert past_the_end["data"] == []
    assert past_the_end["recordsTotal"] == 6
    assert past_the_end["recordsFiltered"] == 6


# ---------------------------------------------------------------------------
# Row shape: the fields callers render from a single known row.
# ---------------------------------------------------------------------------

def test_row_shape_has_fields_callers_render(app_db):
    seed_history(app_db)

    result = call_history(grouping=False,
                          custom_where=[["session_history.reference_id IN", ["11"]]])

    assert len(result["data"]) == 1
    row = result["data"][0]
    assert row["row_id"] == 3
    assert row["id"] == 3
    assert row["user"] == "bob"
    assert row["friendly_name"] == "bob"  # blank friendly_name falls back to username
    assert row["full_title"] == "Beta Movie"
    assert row["started"] == 2000
    assert row["duration"] == 600  # stopped(2600) - started(2000) - paused(0)
    assert row["transcode_decision"] == "transcode"
    # seed_history never sets view_offset, so it takes the column default of
    # 0: percent_complete is 0/duration, i.e. 0.
    assert row["percent_complete"] == 0


# ---------------------------------------------------------------------------
# media_type_live filter: session_history_metadata.live folded into a
# synthetic "live" media type via a CASE expression, so Live TV recordings
# can be filtered like any other media_type even though there is no real
# media_type value for it.
#
# Regression history:
#   b9d4f57a - the live filter combined with another custom_where filter
#              dropped the other filter.
#   87389320 - the CASE literal was double-quoted, so SQLite read it as a
#              column reference instead of the string 'live'.
#   9432fee1 - media_type=all must pass through unfiltered.
# ---------------------------------------------------------------------------

def test_media_type_live_filter_returns_only_live_rows(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, custom_where=[["media_type_live IN", ["live"]]])

    assert result["recordsFiltered"] == 1
    assert {row["row_id"] for row in result["data"]} == {6}


def test_media_type_live_filter_excludes_live_rows_from_underlying_type(app_db):
    seed_history(app_db)

    # Row 6 is a live recording of a "movie"-typed item, same title as row 3
    # (Beta Movie). Filtering on the real media_type must not pull it in
    # just because session_history.media_type still says "movie".
    result = call_history(grouping=False, custom_where=[["media_type_live IN", ["movie"]]])

    assert result["recordsFiltered"] == 1
    assert {row["row_id"] for row in result["data"]} == {3}


def test_media_type_live_filter_combined_with_user_filter(app_db):
    seed_history(app_db)

    # b9d4f57a shape: a user filter and the live filter together, both must
    # hold. Row 6 (the live row) belongs to alice (user_id 1), not bob.
    alice_live = call_history(
        grouping=False,
        custom_where=[["session_history.user_id IN", ["1"]], ["media_type_live IN", ["live"]]],
    )
    assert {row["row_id"] for row in alice_live["data"]} == {6}

    bob_live = call_history(
        grouping=False,
        custom_where=[["session_history.user_id IN", ["2"]], ["media_type_live IN", ["live"]]],
    )
    assert bob_live["data"] == []


def test_media_type_live_row_carries_live_flag_and_underlying_media_type(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, custom_where=[["media_type_live IN", ["live"]]])

    row = result["data"][0]
    assert row["row_id"] == 6
    assert row["live"] == 1
    # media_type_live is filter-only; the returned media_type stays the real type.
    assert row["media_type"] == "movie"


# ---------------------------------------------------------------------------
# DataTables length: 0 means "no rows, counts only", -1 means "all rows".
# Both are distinct from a normal positive page size, and from each other.
# ---------------------------------------------------------------------------

def test_length_zero_returns_no_rows_but_real_counts(app_db):
    seed_history(app_db)

    result = call_history(grouping=True, draw=build_draw(length=0))

    assert result["data"] == []
    assert result["recordsFiltered"] == 5
    assert result["recordsTotal"] == 6


def test_length_negative_one_returns_all_rows(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, draw=build_draw(length=-1))

    assert len(result["data"]) == 6
    assert result["recordsFiltered"] == 6
    assert result["recordsTotal"] == 6


# ---------------------------------------------------------------------------
# draw counter: the response must echo the request's draw value, so an
# async client can match a response back to the request that asked for it.
# ---------------------------------------------------------------------------

def test_draw_counter_echoes_request(app_db):
    seed_history(app_db)

    result = call_history(grouping=False, draw=build_draw(draw=42))

    assert result["draw"] == 42


# ---------------------------------------------------------------------------
# filter_duration/total_duration: human-readable summed play durations.
# total_duration sums every session_history row matched by custom_where
# (independent of the draw's search box and of grouping). filter_duration
# sums only the play_duration of the rows the draw actually returns, so a
# search that narrows the page makes the two diverge.
# ---------------------------------------------------------------------------

def test_duration_totals_match_seeded_play_durations(app_db):
    seed_history(app_db)

    # Row play_durations: 300, 550, 600, 200, 400, 900 -> 2950s = 49m10s,
    # whether summed per-row or per-group (group 10 is rows 1+2 = 850).
    result = call_history(grouping=False)
    assert result["total_duration"] == "49 mins 10 secs"
    assert result["filter_duration"] == "49 mins 10 secs"

    grouped = call_history(grouping=True)
    assert grouped["total_duration"] == "49 mins 10 secs"
    assert grouped["filter_duration"] == "49 mins 10 secs"

    # The draw's search box narrows the returned page to rows 3 and 6
    # (600 + 900 = 1500s = 25 mins), but total_duration ignores search and
    # still covers all 6 rows.
    filtered = call_history(grouping=False, draw=build_draw(search="Beta"))
    assert filtered["filter_duration"] == "25 mins"
    assert filtered["total_duration"] == "49 mins 10 secs"
    assert filtered["filter_duration"] != filtered["total_duration"]


# ---------------------------------------------------------------------------
# watched_status tiers: percent_complete against the *_WATCHED_PERCENT
# config, in quarters of that threshold (1, 0.75, 0.5, 0.25, 0). Set
# MOVIE_WATCHED_PERCENT explicitly so the tiers don't ride on the config
# default. Base threshold = 80/4 = 20% per quarter.
# ---------------------------------------------------------------------------

def test_watched_status_tiers(app_db):
    seed_history(app_db)
    plexpy.CONFIG.MOVIE_WATCHED_PERCENT = 80

    # (row_id, view_offset out of duration=1000, expected watched_status)
    tiers = [
        (101, 100, 0),      # 10%: below the first quarter (20%)
        (102, 300, 0.25),   # 30%: at least one quarter, below two
        (103, 500, 0.50),   # 50%: at least two quarters, below three
        (104, 700, 0.75),   # 70%: at least three quarters, below check_watched
        (105, 900, 1),      # 90%: >= MOVIE_WATCHED_PERCENT -> check_watched
    ]
    for row_id, view_offset, _ in tiers:
        insert_history_row(app_db, row_id, ref_id=row_id, user_id=1, user="alice",
                           started=row_id * 100, stopped=row_id * 100 + 90,
                           rating_key=row_id, title="Tier Movie %d" % row_id,
                           media_type="movie", view_offset=view_offset, duration=1000)

    result = call_history(grouping=False,
                          custom_where=[["session_history.reference_id IN", [str(r) for r, _, _ in tiers]]])

    rows_by_id = {row["row_id"]: row for row in result["data"]}
    for row_id, _, expected_status in tiers:
        assert rows_by_id[row_id]["watched_status"] == expected_status

    # percent_complete for the 30% row is asserted alongside its tier.
    assert rows_by_id[102]["percent_complete"] == 30


# ---------------------------------------------------------------------------
# Row-field resolution: platform name overrides and the episode thumb
# fallback (parent_thumb, falling back to grandparent_thumb) are computed
# in get_datatables_history and never asserted elsewhere.
# ---------------------------------------------------------------------------

def test_platform_name_override_is_applied(app_db):
    seed_history(app_db)
    # 'windows' -> 'Windows' is a real entry in common.PLATFORM_NAME_OVERRIDES.
    assert common.PLATFORM_NAME_OVERRIDES["windows"] == "Windows"
    insert_history_row(app_db, row_id=201, ref_id=201, user_id=1, user="alice",
                       started=9000, stopped=9100, rating_key=901, title="Override Movie",
                       media_type="movie", platform="windows")

    result = call_history(grouping=False, custom_where=[["session_history.reference_id IN", ["201"]]])

    assert result["data"][0]["platform"] == "Windows"


# ---------------------------------------------------------------------------
# A sessions row with no media_type. Before cc4fb641, set_session_state
# could insert one holding only state, view_offset and stopped after the
# real row was deleted, and the whole History page then failed with a
# KeyError looking the missing media_type up in the watched_percent map.
# The row must render instead.
# ---------------------------------------------------------------------------

def test_history_renders_a_sessions_row_with_no_media_type(app_db):
    seed_history(app_db)
    app_db.action("UPDATE users SET thumb = 'plex-thumb-2' WHERE user_id = 2")
    app_db.action(
        "INSERT INTO sessions (session_key, state, view_offset, stopped, user_id) "
        "VALUES (42, 'playing', 0, 5000, 2)")

    factory = datafactory.DataFactory()
    result = factory.get_datatables_history(
        kwargs={"json_data": json.dumps(build_draw(length=-1))},
        custom_where=[],
        grouping=False,
        include_activity=True,
    )

    # 6 history rows plus the activity row.
    assert result["recordsFiltered"] == 7
    session_row = next(row for row in result["data"] if row["session_key"] == 42)
    assert session_row["state"] == "playing"
    assert session_row["media_type"] is None
    # Active rows resolve the user thumb from the users table, because the
    # sessions union selects NULL for it.
    assert session_row["user_thumb"] == "plex-thumb-2"
    # No media_type means a watched threshold of 0, and a 0 threshold puts
    # any percent_complete in the >= 3 * base tier.
    assert session_row["watched_status"] == 0.75


def test_episode_thumb_falls_back_to_parent_thumb(app_db):
    seed_history(app_db)
    insert_history_row(app_db, row_id=202, ref_id=202, user_id=1, user="alice",
                       started=9200, stopped=9300, rating_key=902, title="Thumb Episode",
                       media_type="episode", parent_thumb="/parent/thumb",
                       grandparent_thumb="/grandparent/thumb")

    result = call_history(grouping=False, custom_where=[["session_history.reference_id IN", ["202"]]])

    # media_type == episode with parent_thumb set: parent_thumb wins over
    # grandparent_thumb.
    assert result["data"][0]["thumb"] == "/parent/thumb"
