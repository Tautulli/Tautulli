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


@pytest.mark.parametrize("log_blacklist, log_login_ip, record_keep_ip, expected_message", [
    (0, 0, None, "bad login at IP '8.8.8.8'."),
    (0, 1, True, "bad login at IP '8.8.8.8'."),
    (1, 0, None, "bad login at IP '***.***.***.***'."),
    (1, 1, True, "bad login at IP '8.8.8.8'."),
])
def test_public_ip_filter_respects_blacklist_and_login_ip_settings(
    app_config, log_blacklist, log_login_ip, record_keep_ip, expected_message
):
    app_config.LOG_BLACKLIST = log_blacklist
    app_config.LOG_LOGIN_IP = log_login_ip
    record = keep_ip_record("bad login at IP '8.8.8.8'.", keep_ip=record_keep_ip)
    logger.PublicIPFilter().filter(record)
    assert record.getMessage() == expected_message


@pytest.mark.parametrize("log_blacklist, log_login_ip, expected_keep_ips", [
    (0, 0, [False] * 4),
    (0, 1, [True] * 4),
    (1, 0, [False] * 4),
    (1, 1, [True] * 4),
])
def test_failed_login_lines_send_the_keep_ip_mark(
    monkeypatch, caplog, app_config, log_blacklist, log_login_ip, expected_keep_ips
):
    from plexpy import webauth

    app_config.LOG_BLACKLIST = log_blacklist
    app_config.LOG_LOGIN_IP = log_login_ip
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
    assert [r.keep_ip for r in caplog.records] == expected_keep_ips
