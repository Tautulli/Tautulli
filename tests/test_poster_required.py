"""Media notifications build the poster only when an enabled notifier uses it.

Building the poster fetches the image from Plex and uploads it to the image
host. A notifier uses the poster through an agent setting, or when its text,
custom conditions, MQTT topic, or IFTTT value3 name poster_url or poster_title.
"""

import json
import queue
from unittest.mock import MagicMock

import pytest

import plexpy
from plexpy import notification_handler
from plexpy import notifiers


def make_notifier(agent_name, config=None, **kwargs):
    notifier_id = notifiers.add_notifier_config(agent_id=notifiers.AGENT_IDS[agent_name])
    kwargs.update({'%s_%s' % (agent_name, k): v for k, v in (config or {}).items()})
    assert notifiers.set_notifier_config(notifier_id=notifier_id, **kwargs)
    return notifier_id


def required(notifier_id, notify_action='on_play'):
    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id, load_config_options=False)
    return notification_handler.poster_required(notifier_config, notify_action)


@pytest.mark.parametrize("agent_name, config, expected", [
    ("lunasea", {}, True),
    ("zapier", {}, True),
    ("discord", {"incl_card": 1}, True),
    ("discord", {"incl_card": 0}, False),
    ("slack", {"incl_card": 1}, True),
    ("slack", {"incl_card": 0}, False),
    ("microsoftteams", {"incl_card": 1, "poster_size": 2}, True),
    ("microsoftteams", {"incl_card": 1, "poster_size": 0}, False),
    ("microsoftteams", {"incl_card": 0, "poster_size": 2}, False),
    ("gotify", {"incl_poster": 1}, True),
    ("gotify", {"incl_poster": 0}, False),
    ("join", {"incl_poster": 1}, True),
    ("join", {"incl_poster": 0}, False),
    ("ntfy", {"incl_poster": 1}, True),
    ("ntfy", {"incl_poster": 0}, False),
    ("twitter", {"incl_poster": 1}, True),
    ("twitter", {"incl_poster": 0}, False),
    # These agents send poster_thumb from Plex or no poster at all
    ("pushover", {"incl_poster": 1}, False),
    ("pushbullet", {"incl_poster": 1}, False),
    ("telegram", {"incl_poster": 1}, False),
    ("groupme", {"incl_poster": 1}, False),
    ("facebook", {"incl_card": 1}, False),
    ("remoteapp", {}, False),
])
def test_agent_setting(app_db, agent_name, config, expected):
    assert required(make_notifier(agent_name, config)) is expected


@pytest.mark.parametrize("agent_name, config, kwargs, expected", [
    ("pushover", {}, {"on_play_body": "Poster: {poster_url}"}, True),
    ("pushover", {}, {"on_play_subject": "{poster_title}"}, True),
    ("pushover", {}, {"on_stop_body": "{poster_url}"}, False),
    ("pushover", {}, {"custom_conditions": json.dumps(
        [{"parameter": "poster_url", "operator": "is not", "value": ["x"]}])}, True),
    ("mqtt", {"topic": "tautulli/{poster_title}"}, {}, True),
    ("mqtt", {"topic": "tautulli/{action}"}, {}, False),
    ("ifttt", {"value3": "poster_url"}, {}, True),
    ("ifttt", {"value3": "title"}, {}, False),
    ("webhook", {}, {"on_play_body": '{"poster": "{poster_url}"}'}, True),
    ("scripts", {}, {"on_play_subject": "--poster {poster_url}"}, True),
    ("pushover", {}, {}, False),
])
def test_notification_text(app_db, agent_name, config, kwargs, expected):
    assert required(make_notifier(agent_name, config, **kwargs)) is expected


def test_missing_config_builds_the_poster():
    assert notification_handler.poster_required(None, 'on_play') is True


@pytest.fixture
def harness(app_db, app_config, monkeypatch):
    app_config.NOTIFY_UPLOAD_POSTERS = 1
    activity = MagicMock()
    activity.return_value.get_sessions.return_value = []
    get_img_info = MagicMock(return_value={'img_title': 'Poster', 'img_url': 'https://i.imgur.com/x.png'})
    notify_queue = queue.Queue()
    monkeypatch.setattr(notification_handler.pmsconnect, "PmsConnect", MagicMock())
    monkeypatch.setattr(notification_handler.activity_processor, "ActivityProcessor", activity)
    monkeypatch.setattr(notification_handler.helpers, "pms_name", lambda: "Server")
    monkeypatch.setattr(notification_handler, "get_img_info", get_img_info)
    monkeypatch.setattr(plexpy, "NOTIFY_QUEUE", notify_queue)
    return get_img_info, notify_queue


def queued(notify_queue):
    return [notify_queue.get_nowait() for _ in range(notify_queue.qsize())]


TIMELINE = {"rating_key": "1", "media_type": "movie", "title": "Movie", "thumb": "/library/metadata/1/thumb/1"}


def test_one_of_two_notifiers_needs_the_poster(harness):
    get_img_info, notify_queue = harness
    make_notifier("pushover", on_created=1)
    make_notifier("discord", {"incl_card": 1}, on_created=1)

    notification_handler.add_notifier_each(notify_action='on_created', timeline_data=dict(TIMELINE))

    assert get_img_info.call_count == 1
    sent = queued(notify_queue)
    assert len(sent) == 2
    assert all(s['parameters']['poster_url'] == 'https://i.imgur.com/x.png' for s in sent)


def test_no_notifier_needs_the_poster(harness):
    get_img_info, notify_queue = harness
    make_notifier("pushover", on_created=1)
    make_notifier("discord", {"incl_card": 0}, on_created=1)

    notification_handler.add_notifier_each(notify_action='on_created', timeline_data=dict(TIMELINE))

    get_img_info.assert_not_called()
    sent = queued(notify_queue)
    assert len(sent) == 2
    assert all(s['parameters']['poster_url'] == '' and s['parameters']['poster_title'] == '' for s in sent)


@pytest.mark.parametrize("config, calls", [
    ({"incl_card": 1}, 1),
    ({"incl_card": 0}, 0),
])
def test_manual_on_created(harness, config, calls):
    get_img_info, notify_queue = harness
    notifier_id = make_notifier("discord", config)

    notification_handler.add_notifier_each(notifier_id=notifier_id, notify_action='on_created',
                                           timeline_data=dict(TIMELINE), manual_trigger=True)

    assert get_img_info.call_count == calls
    assert len(queued(notify_queue)) == 1


def test_text_of_the_fired_action_is_read(app_db):
    assert required(make_notifier("pushover", on_created_body="{poster_url}"), 'on_created') is True


def test_text_of_the_fired_action_builds_the_poster(harness):
    get_img_info, notify_queue = harness
    make_notifier("pushover", on_created=1, on_created_body="{poster_url}")

    notification_handler.add_notifier_each(notify_action='on_created', timeline_data=dict(TIMELINE))

    assert get_img_info.call_count == 1


def test_direct_call_builds_the_poster(harness):
    get_img_info, _ = harness

    notification_handler.build_media_notify_params(notify_action='on_created', timeline=dict(TIMELINE))

    assert get_img_info.call_count == 1


def test_self_hosted_skips_the_hash_row(harness, app_config, monkeypatch):
    app_config.NOTIFY_UPLOAD_POSTERS = 2
    app_config.HTTP_BASE_URL = 'https://t.example'
    set_hash = MagicMock(return_value='abc')
    monkeypatch.setattr(notification_handler, "set_hash_image_info", set_hash)
    _, notify_queue = harness
    make_notifier("pushover", on_created=1)

    notification_handler.add_notifier_each(notify_action='on_created', timeline_data=dict(TIMELINE))

    set_hash.assert_not_called()
    assert queued(notify_queue)[0]['parameters']['poster_url'] == ''
