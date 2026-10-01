"""Graphs read live and transcode_decision from the history row.

The seed is the shared six-row history from test_history_table. Row 6 is
a live movie. Rows 2, 3, and 6 transcode. The fixture makes row 4 a
direct stream, so each stream type has its own count. It adds a live
episode (row 7) and a live track (row 8), which direct play. Every seed
row is on 1970-01-01, so the time ranges reach back past it.
"""

import pytest

from plexpy import graphs, libraries

from tests.test_history_table import insert_history_row, seed_history


# Durations are stopped - started - paused_counter per row.
LIVE_SPLIT = {
    "plays": {"TV": 3, "Movies": 1, "Music": 1, "Live TV": 3},
    "duration": {"TV": 300 + 550 + 400, "Movies": 600, "Music": 200, "Live TV": 900 + 500 + 100},
}
STREAM_TYPES = {
    "plays": {"Direct Play": 4, "Direct Stream": 1, "Transcode": 3},
    "duration": {"Direct Play": 300 + 400 + 500 + 100, "Direct Stream": 200, "Transcode": 550 + 600 + 900},
}


@pytest.fixture
def seeded(app_db, monkeypatch):
    seed_history(app_db)
    for table in ("session_history", "session_history_media_info"):
        app_db.action("UPDATE %s SET transcode_decision = 'copy' WHERE id = 4" % table)
    insert_history_row(app_db, 7, 15, 1, "alice", 6000, 6500, 204, "Live News", "episode")
    insert_history_row(app_db, 8, 16, 1, "alice", 7000, 7100, 205, "Live Radio", "track")
    for table in ("session_history", "session_history_metadata"):
        app_db.action("UPDATE %s SET live = 1 WHERE id IN (7, 8)" % table)
    # Show every media type series.
    monkeypatch.setattr(libraries, "has_library_type", lambda section_type: True)


def totals(result):
    return {s["name"]: sum(s["data"]) for s in result["series"] if s["name"] != "Total"}


@pytest.mark.parametrize("y_axis", ["plays", "duration"])
@pytest.mark.parametrize("name, time_range", [
    ("get_total_plays_per_day", 36500),
    ("get_total_plays_per_dayofweek", 36500),
    ("get_total_plays_per_hourofday", 36500),
    ("get_total_plays_per_month", 1200),
    ("get_total_plays_by_top_10_platforms", 36500),
    ("get_total_plays_by_top_10_users", 36500),
])
def test_live_plays_split_out(seeded, name, time_range, y_axis):
    result = getattr(graphs.Graphs(), name)(time_range=time_range, y_axis=y_axis, grouping=False)

    assert totals(result) == LIVE_SPLIT[y_axis]


@pytest.mark.parametrize("y_axis", ["plays", "duration"])
@pytest.mark.parametrize("name", [
    "get_total_plays_per_stream_type",
    "get_stream_type_by_top_10_platforms",
    "get_stream_type_by_top_10_users",
])
def test_stream_types_split_out(seeded, name, y_axis):
    result = getattr(graphs.Graphs(), name)(time_range=36500, y_axis=y_axis, grouping=False)

    assert totals(result) == STREAM_TYPES[y_axis]


def test_concurrent_streams_split_by_stream_type(seeded):
    result = graphs.Graphs().get_total_concurrent_streams_per_stream_type(time_range=36500)

    # No two plays of one stream type overlap.
    assert {name: count for name, count in totals(result).items()
            if name != "Max. Concurrent Streams"} == {"Direct Play": 1, "Direct Stream": 1, "Transcode": 1}
