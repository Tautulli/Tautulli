"""Tests for API key authentication handling in API2."""

import cherrypy
import pytest

from plexpy.api2 import API2

KEY = "a" * 32


@pytest.fixture
def validate(app_config, monkeypatch):
    app_config.API_ENABLED = 1
    app_config.API_KEY = KEY

    def run(headers=None, **kwargs):
        monkeypatch.setattr(cherrypy.request, "headers", dict(headers or {}), raising=False)
        api = API2()
        return api, api._api_validate(**kwargs)

    return run


def test_header_only(validate):
    api, cleaned = validate({"X-Api-Key": KEY}, cmd="get_tautulli_info")
    assert api._api_authenticated and "apikey" not in cleaned


def test_param_only(validate):
    api, _ = validate(apikey=KEY, cmd="get_tautulli_info")
    assert api._api_authenticated


@pytest.mark.parametrize("param", ["", "wrong"])
def test_header_preferred_over_param(validate, param):
    api, cleaned = validate({"X-Api-Key": KEY}, apikey=param, cmd="get_tautulli_info")
    assert api._api_authenticated and "apikey" not in cleaned


def test_wrong_header_not_rescued_by_valid_param(validate):
    api, _ = validate({"X-Api-Key": "wrong"}, apikey=KEY, cmd="get_tautulli_info")
    assert not api._api_authenticated and api._api_response_code == 401


def test_no_key_rejected(validate):
    api, _ = validate(cmd="get_tautulli_info")
    assert not api._api_authenticated and api._api_response_code == 401
