"""The token check flags a Plex.tv token that plex.tv rejects."""

import queue

import pytest
import requests

import plexpy
from plexpy import http_handler
from plexpy import plextv
from plexpy import webserve

BAD = "bad-token"


class Reply:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.content = b""
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("%s Client Error" % self.status_code)


@pytest.fixture
def env(app_config, monkeypatch):
    app_config.PMS_TOKEN = BAD
    monkeypatch.setattr(plexpy, "PLEXTV_BAD_TOKEN", None)
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: None)
    notify_queue = queue.Queue()
    monkeypatch.setattr(plexpy, "NOTIFY_QUEUE", notify_queue)
    sent = []

    def fake_request(method, url, **kwargs):
        sent.append((url, kwargs["headers"].get("X-Plex-Token")))
        return Reply(env.status)

    env.status = 200
    monkeypatch.setattr(http_handler._session, "request", fake_request)
    env.sent = sent
    env.queue = notify_queue
    return env


def flag(token=BAD):
    plexpy.PLEXTV_BAD_TOKEN = token


def set_ping(monkeypatch, result):
    monkeypatch.setattr(plextv.PlexTV, "check_token", lambda self: result)


def test_false_sets_flag_and_queues_notification(env, monkeypatch):
    set_ping(monkeypatch, False)
    plextv.notify_token_expired()
    assert plexpy.PLEXTV_BAD_TOKEN == BAD
    assert plexpy.plextv_token_is_bad()
    assert env.queue.get_nowait() == {"notify_action": "on_tokenexpired"}


def test_true_clears_flag_and_queues_nothing(env, monkeypatch):
    flag()
    set_ping(monkeypatch, True)
    plextv.notify_token_expired()
    assert plexpy.PLEXTV_BAD_TOKEN is None
    assert env.queue.empty()


def test_none_leaves_flag_as_it_is(env, monkeypatch):
    flag()
    set_ping(monkeypatch, None)
    plextv.notify_token_expired()
    assert plexpy.PLEXTV_BAD_TOKEN == BAD
    assert env.queue.empty()
    plexpy.PLEXTV_BAD_TOKEN = None
    plextv.notify_token_expired()
    assert plexpy.PLEXTV_BAD_TOKEN is None


def test_ping_401_flags_the_token_that_was_checked(env):
    env.status = 401
    plexpy.CONFIG.PMS_TOKEN = BAD
    plextv.notify_token_expired()
    assert plexpy.PLEXTV_BAD_TOKEN == BAD


def test_new_token_clears_flag(env, app_config):
    flag()
    assert plexpy.plextv_token_is_bad()
    app_config.PMS_TOKEN = "new-token"
    assert not plexpy.plextv_token_is_bad()


def test_empty_token_is_never_flagged(env, app_config):
    app_config.PMS_TOKEN = ""
    flag("")
    assert not plexpy.plextv_token_is_bad()


def test_check_token_clears_flag_after_a_good_ping(env):
    flag()
    plextv.notify_token_expired()
    assert plexpy.PLEXTV_BAD_TOKEN is None


def test_check_pms_token_answers_401_for_a_bad_token(env, monkeypatch):
    import cherrypy
    env.status = 401
    monkeypatch.setattr(cherrypy.response, "status", 200, raising=False)
    webserve.WebInterface().check_pms_token()
    assert cherrypy.response.status == 401
    assert plexpy.PLEXTV_BAD_TOKEN == BAD
