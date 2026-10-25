"""Handlers that no longer exist return 404."""

import io
import sys

import cherrypy
import pytest

import plexpy
from plexpy import webserve
from tests.test_static_files import static_config  # noqa: F401


API_KEY = "test-key"
API_HEADERS = {"HTTP_X_API_KEY": API_KEY}


def request(app, method, path, query="", body=b"", headers=None):
    status = []
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "SCRIPT_NAME": "", "QUERY_STRING": query,
               "SERVER_NAME": "localhost", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1",
               "HTTP_HOST": "localhost", "REMOTE_ADDR": "127.0.0.1", "CONTENT_LENGTH": str(len(body)),
               "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(body), "wsgi.errors": sys.stderr,
               "wsgi.version": (1, 0), "wsgi.multithread": False, "wsgi.multiprocess": False,
               "wsgi.run_once": False}
    environ.update(headers or {})
    out = b"".join(app(environ, lambda s, h, exc_info=None: status.append(s)))
    return status[0], out


@pytest.fixture
def app(static_config, monkeypatch):  # noqa: F811
    # The API key header passes the CSRF check, so a POST reaches the dispatcher.
    monkeypatch.setattr(plexpy.CONFIG, "API_KEY", API_KEY)
    return cherrypy.Application(webserve.WebInterface(), "", config=static_config)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_delete_duplicate_libraries_is_gone(app, method):
    status, _ = request(app, method, "/delete_duplicate_libraries", headers=API_HEADERS)
    assert status.startswith("404")
