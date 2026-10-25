"""The /image/<hash> route has no login. Its query string must not steer the PMS fetch."""

import pytest

from plexpy import notification_handler
from plexpy import pmsconnect
from plexpy import webserve

INFO = {
    "img": "/library/metadata/1/thumb/2",
    "rating_key": "1",
    "width": 300,
    "height": 450,
    "opacity": 100,
    "background": "000000",
    "blur": 0,
    "fallback": "poster",
}


@pytest.fixture
def fetches(app_config, tmp_path, monkeypatch):
    app_config.CACHE_DIR = str(tmp_path)
    app_config.CACHE_IMAGES = 0
    calls = []

    def get_image(self, **kwargs):
        calls.append(kwargs)
        return b"image", "image/png"

    monkeypatch.setattr(pmsconnect.PmsConnect, "get_image", get_image)
    monkeypatch.setattr(notification_handler, "get_hash_image_info", lambda img_hash=None: dict(INFO))
    return calls


def test_hash_request_serves_the_stored_image(fetches):
    assert webserve.WebInterface().image("abc123") == b"image"
    (call,) = fetches
    assert call["img"] == "/library/metadata/1/thumb"
    assert call["width"] == 300
    assert call["height"] == 450
    assert not call["refresh"]
    assert not call["clip"]
    assert call["img_format"] == "png"


@pytest.mark.parametrize("key, value", [("refresh", "true"), ("clip", "true"), ("img_format", "jpg"), ("return_hash", "true")])
def test_hash_request_ignores_query_parameter(fetches, key, value):
    assert webserve.WebInterface().image("abc123", **{key: value}) == b"image"
    (call,) = fetches
    assert call["refresh"] is False
    assert call["clip"] is False
    assert call["img_format"] == "png"
