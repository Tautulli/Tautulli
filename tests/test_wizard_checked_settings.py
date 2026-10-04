import re
from pathlib import Path

import pytest

import plexpy
from plexpy import activity_pinger, config, logger, plextv, webserve, webstart

WELCOME = Path(__file__).resolve().parent.parent / "data/interfaces/default/welcome.html"

# The only named checkbox in the wizard form.
WIZARD_KEYS = {"SYSTEM_ANALYTICS"}
UNSHOWN_KEYS = sorted(set(config.CHECKED_SETTINGS) - WIZARD_KEYS)


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


def test_wizard_renders_only_the_assumed_checkboxes():
    html = WELCOME.read_text()
    names = set(re.findall(r'<input[^>]*name="(\w+)"', html))
    assert {k.lower() for k in WIZARD_KEYS} <= names
    assert not {k.lower() for k in UNSHOWN_KEYS} & names


def test_first_run_keeps_unshown_checked_settings(web, app_config):
    assert len(UNSHOWN_KEYS) == len(config.CHECKED_SETTINGS) - 1
    before = {k: getattr(app_config, k) for k in UNSHOWN_KEYS}
    assert any(before.values())

    web.configUpdate(first_run="1", http_username="", pms_port="32400")

    assert {k: getattr(app_config, k) for k in UNSHOWN_KEYS} == before
    assert app_config.FIRST_RUN_COMPLETE == 1


@pytest.mark.parametrize("posted, expected", [(False, 0), (True, 1)])
def test_first_run_system_analytics_follows_the_box(web, app_config, posted, expected):
    form = {"first_run": "1"}
    if posted:
        form["system_analytics"] = "1"

    web.configUpdate(**form)

    assert app_config.SYSTEM_ANALYTICS == expected


def test_normal_save_zeroes_missing_checked_settings(web, app_config):
    assert app_config.API_ENABLED == 1

    web.configUpdate(http_port="8181")

    assert all(getattr(app_config, k) == 0 for k in config.CHECKED_SETTINGS)
