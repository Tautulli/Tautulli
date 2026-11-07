import logging
import os

from hashing_passwords import check_hash
import jwt

import pytest

import plexpy
from plexpy import webauth, webserve


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
    assert "Setup wizard login " in box[0]
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


def restart(config, monkeypatch):
    config.write()
    config = plexpy.config.Config(config._config_file)
    monkeypatch.setattr(plexpy, "CONFIG", config)
    return config, run()


def upgrade(app_config, monkeypatch, password=""):
    app_config.CONFIG_VERSION = 22
    app_config.FIRST_RUN_COMPLETE = 1
    app_config.HTTP_PASSWORD = password
    app_config.JWT_SECRET = "0123456789abcdef0123456789abcdef"
    return restart(app_config, monkeypatch)


def test_upgrade_without_password(app_config, monkeypatch):
    config, lines = upgrade(app_config, monkeypatch)
    assert len(lines) == 4
    assert "Tautulli login " in lines[1]
    assert "Username: tautulli " in lines[2]
    password = lines[2].split("Password: ")[1][:-2].strip()
    saved = plexpy.config.Config(config._config_file)
    assert check_hash(password, saved.HTTP_PASSWORD)
    assert saved.HTTP_GENERATED_PASSWORD == saved.HTTP_PASSWORD
    assert saved.CONFIG_VERSION == 23
    # A remember-me cookie from before the upgrade no longer decodes.
    token = jwt.encode({"user_group": "admin"}, "0123456789abcdef0123456789abcdef", algorithm=webauth.JWT_ALGORITHM)
    with pytest.raises(jwt.DecodeError):
        jwt.decode(token, saved.JWT_SECRET, algorithms=[webauth.JWT_ALGORITHM])
    # A second start keeps the password and logs nothing.
    config, lines = restart(config, monkeypatch)
    assert lines == []
    assert config.HTTP_PASSWORD == saved.HTTP_PASSWORD


def test_upgrade_secret_is_random(app_config, monkeypatch):
    config, _ = upgrade(app_config, monkeypatch)
    first = config.JWT_SECRET
    config, _ = upgrade(config, monkeypatch)
    assert config.JWT_SECRET != first


def test_upgrade_once_after_clear(app_config, monkeypatch):
    config, _ = upgrade(app_config, monkeypatch)
    config.HTTP_PASSWORD = ""
    config, lines = restart(config, monkeypatch)
    assert lines == []
    assert config.HTTP_PASSWORD == ""


def test_upgrade_keeps_existing_password(app_config, monkeypatch):
    config, lines = upgrade(app_config, monkeypatch, password="existing")
    assert lines == []
    assert config.HTTP_PASSWORD == "existing"
    assert config.HTTP_USERNAME == ""
    assert config.CONFIG_VERSION == 23
    assert not config.no_password_upgrade
    assert config.JWT_SECRET == "0123456789abcdef0123456789abcdef"


def test_upgrade_keeps_the_public_opt_out(app_config, monkeypatch):
    app_config.ALLOW_PUBLIC_NO_PASSWORD = 1
    config, lines = upgrade(app_config, monkeypatch)
    assert lines == []
    assert config.HTTP_PASSWORD == ""
    assert config.CONFIG_VERSION == 23


def test_upgrade_during_wizard(app_config, monkeypatch):
    app_config.CONFIG_VERSION = 22
    config, lines = restart(app_config, monkeypatch)
    assert "Setup wizard login " in lines[1]
    assert config.HTTP_PASSWORD


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
        '<a class="alert-link" href="https://github.com/Tautulli/Tautulli/wiki/Installation#accessing-the-setup-wizard" '
        'target="_blank" rel="noreferrer">Tautulli logs</a>.</div>')


def test_login_page_during_the_wizard(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 0
    html = login_page()
    assert HINT in html
    assert "Sign In with Plex" not in html


UPGRADE_HINT = ('<div class="alert alert-warning" role="alert">Tautulli set a password because none was set. '
                'The username and password are in the <a class="alert-link" '
                'href="https://github.com/Tautulli/Tautulli/wiki/Installation#accessing-the-setup-wizard" '
                'target="_blank" rel="noreferrer">Tautulli logs</a>.</div>')


def test_login_page_during_the_wizard_with_the_generated_password(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 0
    app_config.HTTP_PASSWORD = app_config.HTTP_GENERATED_PASSWORD = "hash"
    html = login_page()
    assert HINT in html
    assert UPGRADE_HINT not in html


def test_import_keeps_the_generated_copy(app_config, tmp_path, monkeypatch):
    imported = tmp_path / "imported.ini"
    imported.write_text("[General]\nhttp_port = 8282\n")
    monkeypatch.setattr(plexpy, "SIGNAL", None)
    app_config.HTTP_PASSWORD = app_config.HTTP_GENERATED_PASSWORD = "hash"
    plexpy.config.import_tautulli_config(str(imported))
    assert app_config.HTTP_GENERATED_PASSWORD == "hash"


def test_login_page_after_the_wizard(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 1
    html = login_page()
    assert HINT not in html
    assert UPGRADE_HINT not in html
    assert "Sign In with Plex" in html


def test_login_page_after_upgrade(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 1
    app_config.HTTP_PASSWORD = app_config.HTTP_GENERATED_PASSWORD = "hash"
    html = login_page()
    assert UPGRADE_HINT in html
    assert HINT not in html
    assert "Sign In with Plex" in html
    # Plex sign-in opens first, so the notice sits above the collapsed Tautulli form.
    assert html.index(UPGRADE_HINT) < html.index('id="login-methods"')
    # A new password from the admin ends the notice.
    app_config.HTTP_PASSWORD = "other"
    assert UPGRADE_HINT not in login_page()


def test_login_page_after_upgrade_without_tautulli_login(app_config, login_page):
    app_config.FIRST_RUN_COMPLETE = 1
    app_config.ALLOW_TAUTULLI_LOGIN = 0
    app_config.HTTP_PASSWORD = app_config.HTTP_GENERATED_PASSWORD = "hash"
    assert UPGRADE_HINT not in login_page()


@pytest.mark.parametrize("allowed, form", [(0, False), (1, True)])
def test_login_form_follows_the_allow_setting(app_config, login_page, allowed, form):
    app_config.FIRST_RUN_COMPLETE = 1
    app_config.ALLOW_TAUTULLI_LOGIN = allowed
    assert ('id="login-form"' in login_page()) is form
