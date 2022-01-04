"""Pytest configuration module.

Contains fixtures, which are tightly bound to the Cheroot framework
itself, useless for end-users' app testing.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type  # pylint: disable=invalid-name

import threading
import time

import pytest

from ..server import Gateway, HTTPServer
from ..testing import (  # noqa: F401  # pylint: disable=unused-import
    native_server, wsgi_server,
)
from ..testing import get_server_client


@pytest.fixture
# pylint: disable=redefined-outer-name
def wsgi_server_client(wsgi_server):  # noqa: F811
    """Create a test client out of given WSGI server."""
    return get_server_client(wsgi_server)


@pytest.fixture
# pylint: disable=redefined-outer-name
def native_server_client(native_server):  # noqa: F811
    """Create a test client out of given HTTP server."""
    return get_server_client(native_server)


@pytest.fixture
def http_server():
    """Provision a server creator as a fixture."""
    def start_srv():
        bind_addr = yield
        if bind_addr is None:
            return
        httpserver = make_http_server(bind_addr)
        yield httpserver
        yield httpserver

    srv_creator = iter(start_srv())
    next(srv_creator)  # pylint: disable=stop-iteration-return
    yield srv_creator
    try:
        while True:
            httpserver = next(srv_creator)
            if httpserver is not None:
                httpserver.stop()
    except StopIteration:
        pass


def make_http_server(bind_addr):
    """Create and start an HTTP server bound to ``bind_addr``."""
    httpserver = HTTPServer(
        bind_addr=bind_addr,
        gateway=Gateway,
    )

    threading.Thread(target=httpserver.safe_start).start()

    while not httpserver.ready:
        time.sleep(0.1)

    return httpserver
