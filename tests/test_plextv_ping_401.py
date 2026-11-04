"""check_token returns False when plex.tv answers the ping with a 401."""

import pytest
import requests

import plexpy
from plexpy import http_handler
from plexpy import plextv


class Reply:
    def __init__(self, status_code):
        self.status_code = status_code
        self.content = b""
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError("%s Client Error" % self.status_code)


@pytest.fixture
def ping(app_config, monkeypatch):
    app_config.PMS_TOKEN = "tok"
    monkeypatch.setattr(plexpy.session, "get_session_user_id", lambda: None)

    def answer(status_code):
        monkeypatch.setattr(http_handler._session, "request",
                            lambda method, url, **kwargs: Reply(status_code))
        return plextv.PlexTV().check_token()

    return answer


def test_a_401_means_the_token_is_bad(ping):
    assert ping(401) is False


def test_a_200_means_the_token_is_good(ping):
    assert ping(200) is True


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_other_errors_leave_the_token_unknown(ping, status_code):
    assert ping(status_code) is None
