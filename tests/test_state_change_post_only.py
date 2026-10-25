"""State changing admin handlers accept POST only.

A GET link from another site carries the SameSite=Lax session cookie, and
the CSRF check skips GET. The handlers must refuse GET so the check applies.
Each test sends a real WSGI request through the mounted CherryPy app.
"""

import io
import sys

import cherrypy
import pytest

import plexpy
from plexpy import webserve, webstart
from tests.test_static_files import static_config  # noqa: F401

HANDLERS = ["shutdown", "restart", "update", "checkout_git_branch", "reset_git_install",
            "restart_import_config"]


def request(app, method, path):
    status = []
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "SCRIPT_NAME": "", "QUERY_STRING": "",
               "SERVER_NAME": "localhost", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1",
               "HTTP_HOST": "localhost", "HTTP_X_API_KEY": "testkey", "REMOTE_ADDR": "127.0.0.1", "CONTENT_LENGTH": "0",
               "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(), "wsgi.errors": sys.stderr,
               "wsgi.version": (1, 0), "wsgi.multithread": False, "wsgi.multiprocess": False,
               "wsgi.run_once": False}
    body = b"".join(app(environ, lambda s, headers, exc_info=None: status.append(s)))
    return status[0], body


@pytest.fixture
def app(static_config, app_config, monkeypatch):  # noqa: F811
    # The API key header skips the CSRF check, so the tests reach the method check.
    app_config.API_KEY = "testkey"
    monkeypatch.setattr(webserve.WebInterface, "do_state_change",
                        lambda self, signal, title, timer, **kwargs: "state changed")
    monkeypatch.setattr(plexpy, "DOCKER", False)
    monkeypatch.setattr(plexpy, "SNAP", False)
    monkeypatch.setattr(plexpy.config, "IMPORT_THREAD", None, raising=False)
    return cherrypy.Application(webserve.WebInterface(), "", config=static_config)


@pytest.mark.parametrize("handler", HANDLERS)
def test_get_is_rejected(app, handler):
    status, body = request(app, "GET", "/" + handler)

    assert status.startswith("405")
    assert b"state changed" not in body


@pytest.mark.parametrize("handler", HANDLERS)
def test_post_is_accepted(app, handler):
    status, body = request(app, "POST", "/" + handler)

    assert status.startswith("200")
    assert body == b"state changed"


# The CSRF check with a real session token and no API key.

def run_csrf_check(monkeypatch, headers):
    from types import SimpleNamespace
    from plexpy import webauth
    monkeypatch.setattr(cherrypy, "request", SimpleNamespace(
        path_info="/restart", method="POST", headers=headers, params={}))
    monkeypatch.setattr(cherrypy, "session", {"_csrf_token": "s3ssion"}, raising=False)
    webauth.check_csrf_token()


def test_post_with_the_session_token_header_passes(app_config, monkeypatch):
    run_csrf_check(monkeypatch, {"X-CSRF-Token": "s3ssion"})


def test_post_without_a_token_gets_403(app_config, monkeypatch):
    with pytest.raises(cherrypy.HTTPError) as exc:
        run_csrf_check(monkeypatch, {})

    assert exc.value.code == 403
