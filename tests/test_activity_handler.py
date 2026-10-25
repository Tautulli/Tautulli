"""ActivityHandler pause and buffer state checks.

Plex flaps a stalled stream between paused and buffering. on_buffer()
writes state 'buffering' over the stored 'paused', so the next paused
message reads as a state change and fires another on_pause. The pause
branch keys off last_paused, which on_buffer never touches.
"""

import queue

import pytest

import plexpy
from plexpy import activity_handler


SESSION_KEY = 216
RATING_KEY = "12345"
# A stalled stream reports the same offset for every message.
VIEW_OFFSET = 3048000


def quiet_metadata(self, skip_cache=False):
    self.metadata = {"markers": []}


@pytest.fixture
def feed(app_db, monkeypatch):
    notify_queue = queue.Queue()
    monkeypatch.setattr(plexpy, "NOTIFY_QUEUE", notify_queue)
    monkeypatch.setattr(activity_handler, "schedule_callback", lambda *args, **kwargs: None)
    # Both of these reach the Plex server.
    monkeypatch.setattr(activity_handler.ActivityHandler, "get_live_session",
                        lambda self, skip_cache=False: None)
    monkeypatch.setattr(activity_handler.ActivityHandler, "get_metadata", quiet_metadata)

    app_db.action(
        "INSERT INTO sessions (session_key, rating_key, rating_key_websocket, state, media_type, "
        "duration, view_offset, watched, live, stopped, guid, transcode_key) "
        "VALUES (?, ?, ?, 'playing', 'episode', 6000000, ?, 1, 0, 0, 'g', '')",
        [SESSION_KEY, RATING_KEY, RATING_KEY, VIEW_OFFSET],
    )

    def _feed(states):
        """Push one websocket message per state at process()."""
        for state in states:
            activity_handler.ActivityHandler({
                "sessionKey": str(SESSION_KEY),
                "ratingKey": RATING_KEY,
                "key": "/library/metadata/{}".format(RATING_KEY),
                "state": state,
                "viewOffset": VIEW_OFFSET,
                "transcodeSession": "",
            }).process()

        actions = []
        while not notify_queue.empty():
            actions.append(notify_queue.get()["notify_action"])
        return actions

    return _feed


def buffer_count(app_db):
    row = app_db.select_single(
        "SELECT buffer_count FROM sessions WHERE session_key = ?", [SESSION_KEY])
    return row["buffer_count"]


def test_repeated_pause_notifies_once(feed):
    assert feed(["paused"] * 5).count("on_pause") == 1


def test_pause_buffering_flap_notifies_once(feed, app_db):
    actions = feed(["paused", "buffering"] * 5)

    assert actions.count("on_pause") == 1
    # Nothing resumed, so nothing paused again.
    assert "on_resume" not in actions
    # Suppressing the notification does not stop the buffer count.
    assert buffer_count(app_db) == 5


def test_pause_while_buffering_still_notifies(feed):
    # The session was playing, so this is a real pause and not a flap.
    assert feed(["playing", "buffering", "paused"]).count("on_pause") == 1


def test_resume_rearms_the_pause_notification(feed):
    actions = feed(["paused", "buffering", "playing", "paused"])

    assert actions.count("on_pause") == 2
    assert actions.count("on_resume") == 1


def test_every_buffering_message_counts(feed, app_db):
    # on_buffer() sits in both blocks of the state chain. Dropping either stops the count.
    feed(["buffering"] * 5)

    assert buffer_count(app_db) == 5
