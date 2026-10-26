"""Text a remote caller types is logged on one line."""

import plexpy
from plexpy import api2, webauth

FORGED = "\n2026-10-15 12:00:00 - INFO :: MainThread : forged"


def test_a_newline_in_the_username_cannot_forge_a_log_line(app_config, monkeypatch, caplog):
    monkeypatch.setattr(webauth, "check_rate_limit", lambda ip: None)
    monkeypatch.setattr(webauth, "check_credentials", lambda **kwargs: (False, None, None))
    monkeypatch.setattr(webauth.AuthController, "on_login", lambda self, **kwargs: None)

    with caplog.at_level("WARNING", logger="tautulli"):
        webauth.AuthController().signin(username="bob" + FORGED, password="x", admin_login="1")
        webauth.AuthController().signin(username="bob" + FORGED, password="x")

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 2
    assert all("\n" not in message and "forged" in message for message in messages)


def test_a_newline_in_the_api_cmd_cannot_forge_a_log_line(app_config, monkeypatch, caplog):
    monkeypatch.setattr(plexpy.CONFIG, "API_ENABLED", 1)
    monkeypatch.setattr(plexpy.CONFIG, "API_KEY", "a" * 32)

    with caplog.at_level("WARNING", logger="tautulli_api"):
        api2.API2()._api_validate(apikey="x", cmd="foo" + FORGED)

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 1
    assert "\n" not in messages[0] and "forged" in messages[0]
