"""Test wsgi."""

from concurrent.futures.thread import ThreadPoolExecutor
from traceback import print_tb

import pytest
import portend
import requests
from requests_toolbelt.sessions import BaseUrlSession as Session
from jaraco.context import ExceptionTrap

from cheroot import wsgi
from cheroot._compat import IS_MACOS, IS_WINDOWS


IS_SLOW_ENV = IS_MACOS or IS_WINDOWS


@pytest.fixture
def simple_wsgi_server():
    """Fucking simple wsgi server fixture (duh)."""
    port = portend.find_available_local_port()

    def app(_environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return [b'Hello world!']

    host = '::'
    addr = host, port
    server = wsgi.Server(addr, app, timeout=600 if IS_SLOW_ENV else 20)
    # pylint: disable=possibly-unused-variable
    url = 'http://localhost:{port}/'.format(**locals())
    # pylint: disable=possibly-unused-variable
    with server._run_in_thread() as thread:
        yield locals()


@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_connection_keepalive(simple_wsgi_server):
    """Test the connection keepalive works (duh)."""
    session = Session(base_url=simple_wsgi_server['url'])
    pooled = requests.adapters.HTTPAdapter(
        pool_connections=1, pool_maxsize=1000,
    )
    session.mount('http://', pooled)

    def do_request():
        with ExceptionTrap(requests.exceptions.ConnectionError) as trap:
            resp = session.get('info')
            resp.raise_for_status()
        print_tb(trap.tb)
        return bool(trap)

    with ThreadPoolExecutor(max_workers=10 if IS_SLOW_ENV else 50) as pool:
        tasks = [
            pool.submit(do_request)
            for n in range(250 if IS_SLOW_ENV else 1000)
        ]
        failures = sum(task.result() for task in tasks)

    session.close()
    assert not failures


def test_gateway_start_response_called_twice(monkeypatch):
    """Verify that repeat calls of ``Gateway.start_response()`` fail."""
    monkeypatch.setattr(wsgi.Gateway, 'get_environ', lambda self: {})
    wsgi_gateway = wsgi.Gateway(None)
    wsgi_gateway.started_response = True

    err_msg = '^WSGI start_response called a second time with no exc_info.$'
    with pytest.raises(RuntimeError, match=err_msg):
        wsgi_gateway.start_response('200', (), None)


def test_gateway_write_needs_start_response_called_before(monkeypatch):
    """Check that calling ``Gateway.write()`` needs started response."""
    monkeypatch.setattr(wsgi.Gateway, 'get_environ', lambda self: {})
    wsgi_gateway = wsgi.Gateway(None)

    err_msg = '^WSGI write called before start_response.$'
    with pytest.raises(RuntimeError, match=err_msg):
        wsgi_gateway.write(None)  # The actual arg value is unimportant
