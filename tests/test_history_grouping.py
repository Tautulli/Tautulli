"""Tests for ActivityProcessor.group_history (plexpy/activity_processor.py).

group_history decides whether a freshly-inserted session_history row belongs
to an existing playback group (a resume) or starts a new one, by comparing
it against the most recent row for the same user_id + rating_key.

Note: in this codebase reference_id has no DB trigger and no column
DEFAULT that ties it to id. A fresh insert leaves it NULL (see
write_session_history's value_dict, which never sets reference_id).
group_history is solely responsible for setting it, via the UPDATE at the
end of the method. These tests insert rows the same way and then call
group_history directly, the way write_session_history does right after
each insert (`last_id = db.last_insert_id(); self.group_history(last_id,
session, metadata)`). ActivityProcessor() takes no constructor arguments
and does not touch cherrypy request state, so it is used directly.

The non-live path is keyed off rating_key/view_offset (resumed play,
different user, different item, reference_id chaining). The live-TV path is
a separate branch: it groups by guid (same channel/program) within a
1-day window instead. Regression: commit 4582ff4a ("Fix grouping live tv
history") -- before that fix the query had no time window and the boolean
that decides whether to join a group parenthesized wrong, so live sessions
could join a stale group from days ago, or fail to join a genuinely
continuing one.

The live query is:
    SELECT session_history.id, session_history_metadata.guid, session_history.reference_id
    FROM session_history
    JOIN session_history_metadata ON session_history.id == session_history_metadata.id
    WHERE session_history.id <= ? AND session_history.user_id = ?
    AND datetime(session_history.started, 'unixepoch', 'localtime') > datetime('now', '-1 day')
    ORDER BY session_history.id DESC LIMIT 1
It reads only session_history.started/user_id/reference_id and
session_history_metadata.guid, filtered against SQLite's real wall-clock
'now' (not a fixture timestamp), and picks the single most recent row for
that user, not the most recent row for that rating_key/guid. The guid
match is then done in Python against that one row.

Because it compares against the real clock, these tests compute
timestamps as offsets from time.time() with margins (hours, days) far
wider than the 1-day window boundary, so they cannot flake regardless of
how long the test takes to run.

Ordering matters for the fixtures: write_session_history calls
group_history(last_id, session, metadata) *before* it writes the
session_history_metadata row for that same id (see
plexpy/activity_processor.py write_session_history: group_history at line
~324, the session_history_metadata upsert at ~479). So a row being
processed must not have its own metadata row yet when group_history runs
on it -- otherwise the query could self-join and misgroup. The helpers
below insert metadata only for already-processed rows, matching that
order.
"""

import time

import pytest

import plexpy
from plexpy import activity_processor


MOVIE = "movie"
DURATION = 1000  # session['duration']; watched threshold is computed from this


@pytest.fixture
def db(app_db):
    # check_watched (called from group_history) reads these from CONFIG.
    # Pin them explicitly so the join/no-join assertions don't quietly
    # depend on plexpy.config's current defaults.
    plexpy.CONFIG.MOVIE_WATCHED_PERCENT = 90  # threshold = 900 for DURATION=1000
    plexpy.CONFIG.WATCHED_MARKER = 3
    return app_db


def insert_row(db, row_id, user_id, rating_key, view_offset):
    """Insert a lean session_history row, the columns group_history's
    non-live query actually reads. reference_id is left NULL, matching a
    real insert (write_session_history never sets it)."""
    db.action(
        "INSERT INTO session_history (id, reference_id, user_id, rating_key, view_offset) "
        "VALUES (?, NULL, ?, ?, ?)",
        [row_id, user_id, rating_key, view_offset],
    )


def session_for(user_id, rating_key):
    return {
        "live": 0,
        "user_id": user_id,
        "rating_key": rating_key,
        "media_type": MOVIE,
        "duration": DURATION,
        "marker_credits_first": None,
        "marker_credits_final": None,
    }


def reference_id_of(db, row_id):
    row = db.select_single("SELECT reference_id FROM session_history WHERE id = ?", [row_id])
    return row["reference_id"]


def test_first_play_references_itself(db):
    ap = activity_processor.ActivityProcessor()
    insert_row(db, 1, user_id=1, rating_key=100, view_offset=500)

    ap.group_history(1, session_for(1, 100))

    assert reference_id_of(db, 1) == 1


def test_resumed_play_joins_group_and_chain_keeps_head_id(db):
    ap = activity_processor.ActivityProcessor()

    insert_row(db, 1, user_id=1, rating_key=100, view_offset=500)
    ap.group_history(1, session_for(1, 100))

    insert_row(db, 2, user_id=1, rating_key=100, view_offset=600)
    ap.group_history(2, session_for(1, 100))

    insert_row(db, 3, user_id=1, rating_key=100, view_offset=700)
    ap.group_history(3, session_for(1, 100))

    assert reference_id_of(db, 1) == 1
    assert reference_id_of(db, 2) == 1
    # Row 3 groups off row 2, but row 2's reference_id already points at
    # the group head (row 1), so row 3 lands on the head too, not row 2.
    assert reference_id_of(db, 3) == 1


def test_different_user_starts_new_group(db):
    ap = activity_processor.ActivityProcessor()

    insert_row(db, 1, user_id=1, rating_key=100, view_offset=500)
    ap.group_history(1, session_for(1, 100))

    insert_row(db, 2, user_id=2, rating_key=100, view_offset=600)
    ap.group_history(2, session_for(2, 100))

    assert reference_id_of(db, 2) == 2


def test_different_item_starts_new_group(db):
    ap = activity_processor.ActivityProcessor()

    insert_row(db, 1, user_id=1, rating_key=100, view_offset=500)
    ap.group_history(1, session_for(1, 100))

    insert_row(db, 2, user_id=1, rating_key=200, view_offset=600)
    ap.group_history(2, session_for(1, 200))

    assert reference_id_of(db, 2) == 2


@pytest.mark.parametrize(
    "prev_offset, new_offset, joins_group",
    [
        (500, 600, True),   # forward resume of an unfinished play -> joins
        (500, 500, True),   # equal view_offset (duplicate heartbeat/reconnect) -> join condition is <=, so it joins
        (950, 990, False),  # previous play already crossed the watched threshold -> new group
        (600, 100, False),  # view_offset went backwards (replay from the start) -> new group
    ],
)
def test_group_join_decision(db, prev_offset, new_offset, joins_group):
    ap = activity_processor.ActivityProcessor()

    insert_row(db, 1, user_id=1, rating_key=100, view_offset=prev_offset)
    ap.group_history(1, session_for(1, 100))

    insert_row(db, 2, user_id=1, rating_key=100, view_offset=new_offset)
    ap.group_history(2, session_for(1, 100))

    assert reference_id_of(db, 2) == (1 if joins_group else 2)


# check_watched (called from group_history for the non-live path) has a
# marker-based branch: with WATCHED_MARKER = 3 (the db fixture's default)
# and a real marker_credits_first on the *new* play's session dict, a
# previous view_offset past the marker but below the percent threshold
# still counts as watched, via `view_offset >= min(threshold, marker_first)`.
# Every other test in this file passes marker_credits_first=None (via
# session_for), so that branch never fires. threshold here is 900 (90% of
# DURATION=1000); prev_offset=250 is below it, so only the marker -- not
# the percent threshold -- can flip prev_watched to True.
@pytest.mark.parametrize(
    "marker_credits_first, joins_group",
    [
        (None, True),   # no marker -> percent check only (250 < 900) -> not watched -> joins
        (200, False),   # marker: 250 >= min(900, 200) -> watched -> new group
    ],
)
def test_marker_based_watched_flips_group_decision(db, marker_credits_first, joins_group):
    ap = activity_processor.ActivityProcessor()

    insert_row(db, 1, user_id=1, rating_key=100, view_offset=250)
    ap.group_history(1, session_for(1, 100))

    insert_row(db, 2, user_id=1, rating_key=100, view_offset=300)
    new_session = session_for(1, 100)
    new_session['marker_credits_first'] = marker_credits_first
    ap.group_history(2, new_session)

    assert reference_id_of(db, 2) == (1 if joins_group else 2)


# --- Live-TV path -----------------------------------------------------
#
# session_history.started drives the 1-day window, and
# session_history_metadata.guid drives the same-channel/program check.
# insert_row/session_for above don't write either, so the helpers below
# are separate, minimal variants for this branch only.

def insert_live_row(db, row_id, user_id, started):
    """Insert a lean session_history row for the live-TV query: id,
    user_id, started (the window comparison), and stopped, which every
    real row has. reference_id left NULL, as a real insert leaves it. No session_history_metadata row here -- see
    the module docstring on why that must come after group_history runs
    on this id."""
    db.action(
        "INSERT INTO session_history (id, reference_id, user_id, started, stopped) "
        "VALUES (?, NULL, ?, ?, ?)",
        [row_id, user_id, started, started],
    )


def insert_live_metadata(db, row_id, guid):
    """Write session_history_metadata for a row group_history has already
    processed, so a later row's query (which JOINs this table) can see
    its guid. Only the columns the live query and the table's NOT NULL-free
    schema need are filled in."""
    db.action(
        "INSERT INTO session_history_metadata "
        "(id, rating_key, parent_rating_key, grandparent_rating_key, title, "
        "full_title, year, duration, guid, live, media_type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
        [row_id, row_id, row_id, row_id, "Live show", "Live show", 2024, DURATION, guid, MOVIE],
    )


def live_session_for(user_id, guid):
    """A live session dict with just the fields group_history's live
    branch reads: 'live' (truthy to take this branch), 'user_id' (the
    query filter), and 'guid' (metadata=None in these tests, so
    new_session['guid'] falls back to session['guid'])."""
    return {
        "live": 1,
        "user_id": user_id,
        "guid": guid,
    }


def test_live_first_play_references_itself(db):
    ap = activity_processor.ActivityProcessor()
    now = int(time.time())

    insert_live_row(db, 1, user_id=1, started=now)
    ap.group_history(1, live_session_for(1, "guid-A"))

    assert reference_id_of(db, 1) == 1


def test_live_chain_keeps_head_id(db):
    ap = activity_processor.ActivityProcessor()
    now = int(time.time())

    insert_live_row(db, 1, user_id=1, started=now)
    ap.group_history(1, live_session_for(1, "guid-A"))
    insert_live_metadata(db, 1, "guid-A")

    insert_live_row(db, 2, user_id=1, started=now)
    ap.group_history(2, live_session_for(1, "guid-A"))
    insert_live_metadata(db, 2, "guid-A")

    insert_live_row(db, 3, user_id=1, started=now)
    ap.group_history(3, live_session_for(1, "guid-A"))

    assert reference_id_of(db, 1) == 1
    assert reference_id_of(db, 2) == 1
    # Row 3 groups off row 2 (the live query only looks at the single
    # most recent row), but row 2's reference_id already points at the
    # head (row 1), so row 3 lands on the head too.
    assert reference_id_of(db, 3) == 1


@pytest.mark.parametrize(
    "same_guid, within_window, joins_group",
    [
        (True, True, True),    # same channel/program, recently watched -> joins
        (False, True, False),  # different channel/program -> new group
        (True, False, False),  # same channel/program, but > 1 day ago -> new group
    ],
)
def test_live_group_join_decision(db, same_guid, within_window, joins_group):
    ap = activity_processor.ActivityProcessor()
    now = int(time.time())
    # Margins (1 hour / 3 days) are far wider than the 1-day boundary, so
    # a slow test run can't flip the outcome.
    prev_started = now - 3600 if within_window else now - 3 * 24 * 3600

    insert_live_row(db, 1, user_id=1, started=prev_started)
    ap.group_history(1, live_session_for(1, "guid-A"))
    insert_live_metadata(db, 1, "guid-A")

    insert_live_row(db, 2, user_id=1, started=now)
    ap.group_history(2, live_session_for(1, "guid-A" if same_guid else "guid-B"))

    assert reference_id_of(db, 2) == (1 if joins_group else 2)


def test_live_metadata_guid_drives_grouping(db):
    # group_history's live branch takes the new play's guid from
    # metadata['guid'] when metadata is truthy, falling back to
    # session['guid'] only when metadata is None. Production always passes
    # real metadata; every other test here passes metadata=None. Give the
    # session dict a guid that would NOT match the previous row (so a
    # fallback-to-session bug would start a new group) and confirm the
    # metadata guid ("guid-A", matching the previous row) is what actually
    # drives the join.
    #
    # metadata is also truthy enough to trigger group_history's debug
    # logging, which reads session['session_key'] -- live_session_for()
    # doesn't set that key (metadata=None in every other live test), so it
    # must be added here.
    ap = activity_processor.ActivityProcessor()
    now = int(time.time())

    insert_live_row(db, 1, user_id=1, started=now)
    ap.group_history(1, live_session_for(1, "guid-A"))
    insert_live_metadata(db, 1, "guid-A")

    insert_live_row(db, 2, user_id=1, started=now)
    session = live_session_for(1, "guid-B")
    session['session_key'] = 2
    ap.group_history(2, session, metadata={"guid": "guid-A"})

    assert reference_id_of(db, 2) == 1


# --- Regroup, live TV --------------------------------------------------
#
# regroup_history replays group_history over rows that already have their
# metadata row, so it must rebuild the groups live logging built. The
# margins (hours, days) are far wider than the 1-day window, as above.

@pytest.fixture
def regroup_db(db, monkeypatch):
    monkeypatch.setattr(plexpy.database, "make_backup", lambda *args, **kwargs: True)
    return db


def insert_logged_live_play(db, row_id, started, guid, reference_id):
    """A live TV play the way live logging leaves it: a one-hour
    session_history row with reference_id already set, and its metadata
    row."""
    db.action(
        "INSERT INTO session_history (id, reference_id, user_id, started, stopped) "
        "VALUES (?, ?, 1, ?, ?)",
        [row_id, reference_id, started, started + 3600],
    )
    insert_live_metadata(db, row_id, guid)


def reference_ids(db):
    return [row["reference_id"] for row in db.select("SELECT reference_id FROM session_history ORDER BY id")]


@pytest.mark.parametrize("age", [3600, 3 * 24 * 3600], ids=["recent", "three-days-old"])
def test_regroup_keeps_live_group(regroup_db, age):
    start = int(time.time()) - age
    insert_logged_live_play(regroup_db, 1, start, "guid-A", reference_id=1)
    insert_logged_live_play(regroup_db, 2, start + 3600, "guid-A", reference_id=1)

    activity_processor.ActivityProcessor().regroup_history()

    assert reference_ids(regroup_db) == [1, 1]


@pytest.mark.parametrize("age", [3600, 3 * 24 * 3600], ids=["recent", "three-days-old"])
def test_regroup_rebuilds_wrong_live_group(regroup_db, age):
    # Every row starts with a wrong reference_id. Rows 1 and 2 share a
    # guid, row 3 is another program, so regroup must give [1, 1, 3].
    start = int(time.time()) - age
    insert_logged_live_play(regroup_db, 1, start, "guid-A", reference_id=99)
    insert_logged_live_play(regroup_db, 2, start + 3600, "guid-A", reference_id=99)
    insert_logged_live_play(regroup_db, 3, start + 2 * 3600, "guid-B", reference_id=99)

    activity_processor.ActivityProcessor().regroup_history()

    assert reference_ids(regroup_db) == [1, 1, 3]


def test_regroup_splits_live_plays_more_than_a_day_apart(regroup_db):
    start = int(time.time()) - 5 * 24 * 3600
    insert_logged_live_play(regroup_db, 1, start, "guid-A", reference_id=1)
    insert_logged_live_play(regroup_db, 2, start + 2 * 24 * 3600, "guid-A", reference_id=1)

    activity_processor.ActivityProcessor().regroup_history()

    assert reference_ids(regroup_db) == [1, 2]
