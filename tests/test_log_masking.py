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
