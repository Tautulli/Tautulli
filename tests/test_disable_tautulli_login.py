"""The disable setting refuses the username and password path in check_credentials."""

import pytest
from hashing_passwords import make_hash

from plexpy import config, webauth


@pytest.fixture
def cfg(app_config, monkeypatch):
    app_config.HTTP_USERNAME = "admin"
    app_config.HTTP_PASSWORD = make_hash("secret")
    app_config.ALLOW_TAUTULLI_LOGIN = 0
    app_config.HTTP_PLEX_ADMIN = 1
    app_config.FIRST_RUN_COMPLETE = 1
    app_config.ALLOW_GUEST_ACCESS = 0
    monkeypatch.setattr(webauth, "plex_user_login", lambda **kwargs: ({"user_id": 1, "username": "plex"}, "admin")
                        if kwargs.get("token") == "good" else None)
    return app_config


@pytest.mark.parametrize("admin_login", ["0", "1"])
def test_password_refused_when_setting_takes_effect(cfg, admin_login):
    assert webauth.check_credentials("admin", "secret", admin_login=admin_login) == (False, None, None)


@pytest.mark.parametrize("key, value", [("HTTP_PLEX_ADMIN", 0), ("FIRST_RUN_COMPLETE", 0), ("ALLOW_TAUTULLI_LOGIN", 1)])
def test_password_accepted_when_a_part_of_the_condition_fails(cfg, key, value):
    setattr(cfg, key, value)
    valid, _, group = webauth.check_credentials("admin", "secret", admin_login="1")
    assert valid and group == "admin"


def test_plex_token_still_works(cfg):
    valid, details, group = webauth.check_credentials(token="good")
    assert valid and details["username"] == "plex" and group == "admin"
    assert webauth.check_credentials(token="bad") == (False, None, None)


def test_setting_is_on_by_default_and_a_checked_setting(tmp_path):
    cfg = config.Config(str(tmp_path / "config.ini"))
    assert cfg.ALLOW_TAUTULLI_LOGIN == 1
    assert "ALLOW_TAUTULLI_LOGIN" in config.CHECKED_SETTINGS
