"""Heavy admin handlers accept POST only.

A GET link from another site carries the SameSite=Lax session cookie, and
the CSRF check skips GET. These handlers must refuse GET so the check applies.
Each test sends a real WSGI request through the mounted CherryPy app.
"""

import io
import sys

import cherrypy
import pytest

from plexpy import libraries, webserve
from tests.test_static_files import static_config  # noqa: F401

calls = []


class FakeLibraries(object):
    """Records each call and returns an empty result in place of the PMS crawl."""
    def __getattr__(self, name):
        def method(*args, **kwargs):
            calls.append(name)
            return {"success": True, "data": [], "recordsTotal": 0, "recordsFiltered": 0, "draw": 1}
        return method


def request(app, method, path, query=""):
    status = []
    environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "SCRIPT_NAME": "", "QUERY_STRING": query,
               "SERVER_NAME": "localhost", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1",
               "HTTP_HOST": "localhost", "HTTP_X_API_KEY": "testkey", "REMOTE_ADDR": "127.0.0.1",
               "CONTENT_LENGTH": "0", "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(),
               "wsgi.errors": sys.stderr, "wsgi.version": (1, 0), "wsgi.multithread": False,
               "wsgi.multiprocess": False, "wsgi.run_once": False}
    body = b"".join(app(environ, lambda s, headers, exc_info=None: status.append(s)))
    return status[0], body


@pytest.fixture
def app(static_config, app_config, monkeypatch):  # noqa: F811
    # The API key header skips the CSRF check, so the tests reach the method check.
    app_config.API_KEY = "testkey"
    del calls[:]
    monkeypatch.setattr(libraries, "Libraries", FakeLibraries)
    return cherrypy.Application(webserve.WebInterface(), "", config=static_config)


@pytest.mark.parametrize("path, query", [
    ("/get_media_info_file_sizes", "section_id=1"),
    ("/get_library_media_info", "section_id=1&refresh=true"),
])
def test_get_is_rejected_and_does_no_work(app, path, query):
    status, body = request(app, "GET", path, query)

    assert status.startswith("405")
    assert calls == []


@pytest.mark.parametrize("path, query", [
    ("/get_media_info_file_sizes", "section_id=1"),
    ("/get_library_media_info", "section_id=1&refresh=true"),
])
def test_post_reaches_the_handler(app, path, query):
    status, body = request(app, "POST", path, query)

    assert status.startswith("200")
    assert calls
