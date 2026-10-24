"""Mask Sensitive Information in Logs hides public IP addresses and keeps private ones."""

import logging

import pytest

from plexpy import logger

PLEX_DIRECT_URL = "https://{}.0123456789abcdef0123456789abcdef.plex.direct:32400"


def masked(log_filter, msg):
    record = logging.LogRecord("tautulli", logging.INFO, __file__, 0, msg, (), None)
    log_filter.filter(record)
    return record.getMessage()


@pytest.mark.parametrize("ip, expected", [
    ("8.8.8.8", "***.***.***.***"),
    ("192.168.1.5", "192.168.1.5"),
])
def test_public_ip_filter(app_config, ip, expected):
    app_config.LOG_BLACKLIST = 1
    assert masked(logger.PublicIPFilter(), "Connected to %s." % ip) == "Connected to %s." % expected


@pytest.mark.parametrize("ip, expected", [
    ("8-8-8-8", "***-***-***-***"),
    ("192-168-1-5", "192-168-1-5"),
])
def test_plex_direct_ip_filter(app_config, ip, expected):
    app_config.LOG_BLACKLIST = 1
    assert masked(logger.PlexDirectIPFilter(), PLEX_DIRECT_URL.format(ip)) == PLEX_DIRECT_URL.format(expected)


def keep_ip_record(msg, keep_ip=None):
    record = logging.LogRecord("tautulli", logging.WARNING, __file__, 0, msg, (), None)
    if keep_ip:
        record.keep_ip = keep_ip
    return record


def test_public_ip_filter_keeps_the_ip_of_a_marked_record(app_config):
    app_config.LOG_BLACKLIST = 1
    record = keep_ip_record("bad login at IP '8.8.8.8'.", keep_ip=True)
    assert logger.PublicIPFilter().filter(record) is True
    assert record.getMessage() == "bad login at IP '8.8.8.8'."


def test_public_ip_filter_masks_an_unmarked_record(app_config):
    app_config.LOG_BLACKLIST = 1
    record = keep_ip_record("bad login at IP '8.8.8.8'.")
    logger.PublicIPFilter().filter(record)
    assert record.getMessage() == "bad login at IP '***.***.***.***'."


def test_failed_login_lines_send_the_keep_ip_mark(monkeypatch, caplog):
    from plexpy import webauth

    monkeypatch.setattr(webauth.cherrypy.request.remote, "ip", "8.8.8.8", raising=False)
    monkeypatch.setattr(webauth, "check_credentials", lambda **kwargs: (False, None, None))
    monkeypatch.setattr(webauth.AuthController, "on_login", lambda self, **kwargs: None)
    controller = webauth.AuthController()
    calls = [
        dict(username="bob", password="x", admin_login="1"),
        dict(username="bob", password="x"),
        dict(token="t"),
    ]

    with caplog.at_level("DEBUG", logger="tautulli"):
        monkeypatch.setattr(webauth, "check_rate_limit", lambda ip: None)
        for kwargs in calls:
            controller.signin(**kwargs)
        monkeypatch.setattr(webauth, "check_rate_limit", lambda ip: 30)
        controller.signin(username="bob", password="x")

    assert len(caplog.records) == 4
    assert [r.keep_ip for r in caplog.records] == [True] * 4
