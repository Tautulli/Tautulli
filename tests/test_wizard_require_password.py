import pytest

import plexpy
from plexpy import activity_pinger, logger, plextv, webserve, webstart


@pytest.fixture
def web(app_config, monkeypatch):
    class Quiet:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(logger, "initLogger", lambda **kw: None)
    monkeypatch.setattr(plexpy, "run_analytics", lambda **kw: None)
    monkeypatch.setattr(plexpy, "initialize_scheduler", lambda: None)
    monkeypatch.setattr(webstart, "restart", lambda: None)
    monkeypatch.setattr(activity_pinger, "connect_server", lambda **kw: None)
    monkeypatch.setattr(plextv, "get_server_resources", lambda **kw: None)
    monkeypatch.setattr(webserve.threading, "Thread", Quiet)
    return webserve.WebInterface()


@pytest.mark.parametrize("user, password", [
    ("admin", ""), ("admin", "    "), ("admin", None),
    ("", "pw"), ("   ", "pw"), (None, "pw"), ("", ""),
])
def test_first_run_without_credentials_is_rejected(web, app_config, user, password):
    form = {"first_run": "1", "pms_port": "12345"}
    if user is not None:
        form["http_username"] = user
    if password is not None:
        form["http_password"] = password

    result = web.configUpdate(**form)

    assert result["result"] == "error"
    assert result["message"] == "A username and password are required."
    assert app_config.FIRST_RUN_COMPLETE == 0
    assert app_config.HTTP_PASSWORD == ""
    assert app_config.PMS_PORT != 12345


def test_first_run_with_credentials_succeeds(web, app_config):
    result = web.configUpdate(first_run="1", http_username="admin", http_password="pw")

    assert result["result"] == "success"
    assert app_config.FIRST_RUN_COMPLETE == 1
    assert app_config.HTTP_USERNAME == "admin"
    assert app_config.HTTP_PASSWORD not in ("", "pw")


def test_normal_save_without_password_is_unaffected(web, app_config):
    result = web.configUpdate(http_username="", http_password="", http_port="8181")

    assert result["result"] == "success"
    assert app_config.HTTP_PORT == 8181
