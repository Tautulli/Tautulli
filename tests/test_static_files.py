"""Static files and the web server config.

webstart.initialize builds the CherryPy config, mounts the app, and
starts the server. The fixture stops it at the mount and keeps the
config. The tests serve files through a WSGI call, with no socket.
"""

import io
import os
import sys
import time

import cherrypy
import pytest

import plexpy
from plexpy import webserve, webstart


class Mounted(Exception):
    pass


@pytest.fixture
def static_config(app_config, monkeypatch):
    config = {}

    def mount(root, script_name='', config=None, _captured=config):
        _captured.update(config)
        raise Mounted

    monkeypatch.setattr(plexpy, "PROG_DIR", os.path.dirname(os.path.dirname(plexpy.__file__)))
    monkeypatch.setattr(plexpy, "HTTP_ROOT", plexpy.HTTP_ROOT)
    monkeypatch.setattr(plexpy, "AUTH_ENABLED", plexpy.AUTH_ENABLED)
    monkeypatch.setattr(cherrypy.tree, "mount", mount)
    monkeypatch.setattr(cherrypy.config, "update", lambda *args, **kwargs: None)

    with pytest.raises(Mounted):
        webstart.initialize({"enable_https": False, "https_cert": "", "https_cert_chain": "", "https_key": "",
                             "http_host": "127.0.0.1", "http_port": 0, "http_environment": "production",
                             "http_proxy": False, "http_root": "/", "http_username": "", "http_password": "",
                             "http_basic_auth": False})
    return config


def get(app, path):
    status = []
    environ = {"REQUEST_METHOD": "GET", "PATH_INFO": path, "SCRIPT_NAME": "", "QUERY_STRING": "",
               "SERVER_NAME": "localhost", "SERVER_PORT": "80", "SERVER_PROTOCOL": "HTTP/1.1",
               "HTTP_HOST": "localhost", "HTTP_ACCEPT_ENCODING": "gzip", "REMOTE_ADDR": "127.0.0.1",
               "wsgi.url_scheme": "http", "wsgi.input": io.BytesIO(), "wsgi.errors": sys.stderr,
               "wsgi.version": (1, 0), "wsgi.multithread": False, "wsgi.multiprocess": False, "wsgi.run_once": False}
    body = b"".join(app(environ, lambda s, headers, exc_info=None: status.append(s)))
    return status[0], body


def test_a_large_static_file_is_served_without_a_wait(static_config):
    # ace.js is over the 100 KB limit of the CherryPy memory cache, even
    # gzipped. With the cache on, the third request waited 5 seconds for a
    # copy that the cache never stored.
    app = cherrypy.Application(webserve.WebInterface(), "", config=static_config)

    for _ in range(3):
        start = time.time()
        status, body = get(app, "/js/ace/ace.js")

        assert status == "200 OK"
        assert len(body) > 100000
        assert time.time() - start < 2


def test_static_files_skip_the_server_cache_and_keep_the_browser_cache(static_config):
    static = {path: conf for path, conf in static_config.items()
              if conf.get("tools.staticdir.on") or conf.get("tools.staticfile.on")}

    assert sorted(static) == ["/css", "/favicon.ico", "/fonts", "/images", "/interfaces", "/js"]
    assert not any(conf.get("tools.caching.on") for conf in static_config.values())
    assert all(conf.get("tools.expires.on") for conf in static.values())
