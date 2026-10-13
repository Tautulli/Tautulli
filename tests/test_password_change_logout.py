"""Changing the HTTP password logs out existing sessions on the next restart."""

import pytest

import plexpy
from hashing_passwords import check_hash, make_hash
from plexpy import libraries, logger, plextv, users, webserve


@pytest.fixture
def web(app_config, monkeypatch):
    monkeypatch.setattr(logger, "initLogger", lambda **kwargs: None)
    # configUpdate also reschedules tasks and refreshes the server data.
    monkeypatch.setattr(plexpy, "initialize_scheduler", lambda: None)
    monkeypatch.setattr(plextv, "get_server_resources", lambda: None)
    monkeypatch.setattr(libraries, "refresh_libraries", lambda: None)
    monkeypatch.setattr(users, "refresh_users", lambda: None)
    # Keep the startup options unchanged so the save leaves the OS alone.
    plexpy.CONFIG.LAUNCH_STARTUP = 0
    plexpy.CONFIG.LAUNCH_BROWSER = 0
    plexpy.CONFIG.JWT_UPDATE_SECRET = 0
    return webserve.WebInterface()


def test_a_new_password_logs_out_existing_sessions(web):
    plexpy.CONFIG.HTTP_PASSWORD = make_hash("old-password")

    web.configUpdate(http_password="new-password")

    assert check_hash("new-password", plexpy.CONFIG.HTTP_PASSWORD)
    assert plexpy.CONFIG.JWT_UPDATE_SECRET


def test_removing_the_password_logs_out_existing_sessions(web):
    plexpy.CONFIG.HTTP_PASSWORD = make_hash("old-password")

    web.configUpdate(http_password="")

    assert plexpy.CONFIG.HTTP_PASSWORD == ""
    assert plexpy.CONFIG.JWT_UPDATE_SECRET


def test_an_unchanged_password_keeps_existing_sessions(web):
    # The settings page sends four spaces in place of the stored password.
    password = make_hash("old-password")
    plexpy.CONFIG.HTTP_PASSWORD = password

    web.configUpdate(http_password="    ")

    assert plexpy.CONFIG.HTTP_PASSWORD == password
    assert not plexpy.CONFIG.JWT_UPDATE_SECRET


def test_saving_without_a_password_keeps_existing_sessions(web):
    plexpy.CONFIG.HTTP_PASSWORD = ""

    web.configUpdate(http_password="")

    assert not plexpy.CONFIG.JWT_UPDATE_SECRET


def test_saving_other_settings_keeps_existing_sessions(web):
    plexpy.CONFIG.HTTP_PASSWORD = make_hash("old-password")

    web.configUpdate(verbose_logs="1")

    assert not plexpy.CONFIG.JWT_UPDATE_SECRET
