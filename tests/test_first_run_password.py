import logging
import os

from hashing_passwords import check_hash

import pytest

import plexpy
from plexpy import webserve


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def run():
    # The plexpy logger does not reach caplog, so attach a handler directly.
    handler = Capture()
    plexpy.logger.logger.addHandler(handler)
    try:
        plexpy.generate_first_run_password()
    finally:
        plexpy.logger.logger.removeHandler(handler)
    return [x for x in handler.lines if x.startswith("*")]


def test_generates_password(app_config):
    lines = run()
    assert app_config.HTTP_USERNAME == "tautulli"
    box = lines[1:-1]
    assert len(lines) == 4
    assert set(lines[0]) == {"*"} and lines[-1] == lines[0]
    assert all(x.startswith("* ") and x.endswith(" *") and len(x) == len(lines[0]) for x in box)
    assert "Username: tautulli " in box[1]
    password = box[1].split("Password: ")[1][:-2].strip()
    assert len(password) >= 16
    assert check_hash(password, app_config.HTTP_PASSWORD)
    assert password not in app_config.HTTP_PASSWORD
    assert app_config.HTTP_HASH_PASSWORD == 1
    assert app_config.HTTP_HASHED_PASSWORD == 1
    # The password must reach config.ini, not only memory.
    saved = plexpy.config.Config(app_config._config_file)
    assert check_hash(password, saved.HTTP_PASSWORD)


def test_keeps_username(app_config):
    app_config.HTTP_USERNAME = "sam"
    lines = run()
    assert app_config.HTTP_USERNAME == "sam"
    assert app_config.HTTP_PASSWORD
    assert "Username: sam " in lines[2]
    assert len(lines[0]) == len(lines[2])


def test_keeps_existing_password(app_config):
    app_config.HTTP_PASSWORD = "existing"
    assert run() == []
    assert app_config.HTTP_PASSWORD == "existing"
    assert app_config.HTTP_USERNAME == ""


def test_skips_after_wizard(app_config):
    app_config.FIRST_RUN_COMPLETE = 1
    assert run() == []
    assert app_config.HTTP_PASSWORD == ""


@pytest.fixture
def login_page(app_config, monkeypatch):
    app_config.HTTP_PLEX_ADMIN = 1
    monkeypatch.setattr(webserve, "TEMPLATE_LOOKUP", None)
    monkeypatch.setattr(plexpy, "PROG_DIR", os.getcwd())
    app_config.INTERFACE = "default"
    monkeypatch.setattr(webserve, "get_session_info", lambda: {})
    monkeypatch.setattr(webserve, "get_session_csrf_token", lambda: "")
    monkeypatch.setattr(webserve.helpers, "pms_name", lambda: "")
    monkeypatch.setattr(webserve.cherrypy.response, "headers", {}, raising=False)
    return lambda: webserve.serve_template("login.html", title="Login", redirect_uri="")


HINT = ('<div class="alert alert-warning" role="alert">On a new install, the username and password are in the '
        '<a class="alert-link" href="https://github.com/Tautulli/Tautulli/wiki/Asking-for-Support#how-can-i-share-my-logs" '
        'target="_blank" rel="noreferrer">Tautulli log</a>.</div>')


def test_login_page_during_the_wizard(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 0
    html = login_page()
    assert HINT in html
    assert "Sign In with Plex" not in html


def test_login_page_after_the_wizard(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 1
    html = login_page()
    assert HINT not in html
    assert "Sign In with Plex" in html


@pytest.mark.parametrize("allowed, form", [(0, False), (1, True)])
def test_login_form_follows_the_allow_setting(app_config, login_page, allowed, form):
    app_config.FIRST_RUN_COMPLETE = 1
    app_config.ALLOW_TAUTULLI_LOGIN = allowed
    assert ('id="login-form"' in login_page()) is form
