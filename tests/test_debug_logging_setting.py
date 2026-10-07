"""The Enable Debug Logging checkbox replaces the toggleVerbose handler."""

import re

import cherrypy
import pytest

import plexpy
from plexpy import activity_pinger, libraries, logger, plextv, users, webserve, webstart
from tests.test_removed_handlers import API_HEADERS, app, request  # noqa: F401
from tests.test_static_files import static_config  # noqa: F401


@pytest.fixture
def init_calls(app_config, monkeypatch):
    calls = []
    monkeypatch.setattr(logger, "initLogger", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(plexpy, "VERBOSE", False)
    # configUpdate also reschedules tasks and refreshes the server data.
    monkeypatch.setattr(plexpy, "initialize_scheduler", lambda: None)
    monkeypatch.setattr(plextv, "get_server_resources", lambda: None)
    monkeypatch.setattr(libraries, "refresh_libraries", lambda: None)
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    return calls


def test_checking_the_box_turns_debug_logging_on(init_calls):
    plexpy.CONFIG.VERBOSE_LOGS = 0

    webserve.WebInterface().configUpdate(verbose_logs="1")

    assert plexpy.CONFIG.VERBOSE_LOGS == 1
    assert plexpy.VERBOSE is True
    assert [call["verbose"] for call in init_calls] == [True]
    assert init_calls[0]["log_dir"] == plexpy.CONFIG.LOG_DIR
    assert init_calls[0]["console"] == (not plexpy.QUIET)


def test_unchecking_the_box_turns_debug_logging_off(init_calls, monkeypatch):
    plexpy.CONFIG.VERBOSE_LOGS = 1
    monkeypatch.setattr(plexpy, "VERBOSE", True)

    webserve.WebInterface().configUpdate()

    assert plexpy.CONFIG.VERBOSE_LOGS == 0
    assert plexpy.VERBOSE is False
    assert [call["verbose"] for call in init_calls] == [False]


def test_the_logger_stays_as_it_is_when_the_setting_is_unchanged(init_calls):
    plexpy.CONFIG.VERBOSE_LOGS = 1

    webserve.WebInterface().configUpdate(verbose_logs="1")

    assert init_calls == []


def test_a_first_run_save_leaves_the_logger_alone(init_calls, monkeypatch):
    # The setup wizard has no debug logging box, so the save omits the key.
    monkeypatch.setattr(webstart, "restart", lambda: None)
    monkeypatch.setattr(activity_pinger, "connect_server", lambda **kwargs: None)
    monkeypatch.setattr(plexpy, "run_analytics", lambda **kwargs: None)
    plexpy.CONFIG.VERBOSE_LOGS = 1

    webserve.WebInterface().configUpdate(first_run="1")

    assert init_calls == []
    assert plexpy.VERBOSE is False


@pytest.mark.parametrize("value, checked", [(1, True), (0, False)])
def test_settings_page_shows_the_box_from_the_config(app, app_db, value, checked):
    plexpy.CONFIG.VERBOSE_LOGS = value

    status, body = request(app, "GET", "/settings")
    html = body.decode()

    assert status.startswith("200")

    box = re.search(r'<input type="checkbox" id="verbose_logs"[^>]*>', html).group(0)
    assert 'name="verbose_logs"' in box
    assert 'value="1"' in box
    assert ("Checked" in box) is checked
    assert "Enable Debug Logging" in html
    assert re.search(r"<h3>System</h3>", html)
    assert "<h3>System Analytics</h3>" not in html


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_toggle_verbose_is_gone(app, method):
    status, _ = request(app, method, "/toggleVerbose", headers=API_HEADERS)
    assert status.startswith("404")

