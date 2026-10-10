"""Recently added notifications expose {new_show} when the show itself is new.

A brand new show (created in the same batch as its season and episodes) falls
back to a season notification when it only has one season, which is
indistinguishable from a new season of an existing show. The show's own
"created" timeline event is tracked in RECENTLY_ADDED_NEW_SHOW so
clear_recently_added_queue can pass new_show=1 down to the notification.
"""

import pytest

from plexpy import activity_handler


@pytest.fixture
def queue_state(monkeypatch):
    monkeypatch.setattr(activity_handler, "RECENTLY_ADDED_QUEUE", {})
    monkeypatch.setattr(activity_handler, "RECENTLY_ADDED_NEW_SHOW", set())


def test_show_created_event_marks_show_as_new(queue_state, app_config, monkeypatch):
    monkeypatch.setattr(activity_handler, "schedule_callback", lambda *args, **kwargs: None)

    handler = activity_handler.TimelineHandler({
        "itemID": "1064801",
        "identifier": "com.plexapp.plugins.library",
        "type": 2,
        "state": 0,
        "metadataState": "created",
        "sectionID": "1",
        "title": "Sheriff Country",
    })
    handler.process()

    assert activity_handler.RECENTLY_ADDED_NEW_SHOW == {1064801}


@pytest.mark.parametrize("new_show, expected", [(True, 1), (False, 0)])
def test_clear_recently_added_queue_passes_new_show(
        queue_state, app_config, monkeypatch, new_show, expected):
    show_key = 1064801
    season_key = 1064802
    episode_keys = {1064803, 1064804}

    activity_handler.RECENTLY_ADDED_QUEUE = {
        show_key: {season_key},
        season_key: set(episode_keys),
        list(episode_keys)[0]: {show_key},
        list(episode_keys)[1]: {show_key},
    }
    if new_show:
        activity_handler.RECENTLY_ADDED_NEW_SHOW.add(show_key)

    # A single season falls back to the grouped season notification.
    app_config.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT = 0
    app_config.NOTIFY_GROUP_RECENTLY_ADDED_PARENT = 1

    calls = []
    monkeypatch.setattr(activity_handler, "on_created",
                        lambda rating_key, **kwargs: calls.append((rating_key, kwargs)))

    activity_handler.clear_recently_added_queue(show_key, "Sheriff Country")

    assert calls == [(season_key, {"child_keys": episode_keys, "new_show": expected})]
    assert activity_handler.RECENTLY_ADDED_NEW_SHOW == set()
