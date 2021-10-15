"""Test wsgi."""

from concurrent.futures.thread import ThreadPoolExecutor

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

    def app(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return [b'Hello world!']

    host = '::'
    addr = host, port
    server = wsgi.Server(addr, app, timeout=600 if IS_SLOW_ENV else 20)
    url = 'http://localhost:{port}/'.format(**locals())
    with server._run_in_thread() as thread:
        yield locals()


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
        return bool(trap)

    with ThreadPoolExecutor(max_workers=10 if IS_SLOW_ENV else 50) as pool:
        tasks = [
            pool.submit(do_request)
            for n in range(250 if IS_SLOW_ENV else 1000)
        ]
        failures = sum(task.result() for task in tasks)

    assert not failures
