"""A library of helper functions for the Cheroot test suite."""

import datetime
import http.client
import logging
import os
import sys
import threading
import time
import types

import cheroot.server
import cheroot.wsgi
from cheroot.test import webtest


log = logging.getLogger(__name__)
thisdir = os.path.abspath(os.path.dirname(__file__))


config = {
    'bind_addr': ('127.0.0.1', 54583),
    'server': 'wsgi',
    'wsgi_app': None,
}


class CherootWebCase(webtest.WebCase):
    """Helper class for a web app test suite."""

    script_name = ''
    scheme = 'http'

    available_servers = {
        'wsgi': cheroot.wsgi.Server,
        'native': cheroot.server.HTTPServer,
    }

    @classmethod
    def setup_class(cls):
        """Create and run one HTTP server per class."""
        conf = config.copy()
        conf.update(getattr(cls, 'config', {}))

        s_class = conf.pop('server', 'wsgi')
        server_factory = cls.available_servers.get(s_class)
        if server_factory is None:
            raise RuntimeError('Unknown server in config: %s' % conf['server'])
        cls.httpserver = server_factory(**conf)

        cls.HOST, cls.PORT = cls.httpserver.bind_addr
        if cls.httpserver.ssl_adapter is None:
            ssl = ''
            cls.scheme = 'http'
        else:
            ssl = ' (ssl)'
            cls.HTTP_CONN = http.client.HTTPSConnection
            cls.scheme = 'https'

        v = sys.version.split()[0]
        log.info('Python version used to run this test script: %s', v)
        log.info('Cheroot version: %s', cheroot.__version__)
        log.info('HTTP server version: %s%s', cls.httpserver.protocol, ssl)
        log.info('PID: %s', os.getpid())

        if hasattr(cls, 'setup_server'):
            # Clear the wsgi server so that
            # it can be updated with the new root
            cls.setup_server()
            cls.start()

    @classmethod
    def teardown_class(cls):
        """Cleanup HTTP server."""
        if hasattr(cls, 'setup_server'):
            cls.stop()

    @classmethod
    def start(cls):
        """Load and start the HTTP server."""
        threading.Thread(target=cls.httpserver.safe_start).start()
        while not cls.httpserver.ready:
            time.sleep(0.1)

    @classmethod
    def stop(cls):
        """Terminate HTTP server."""
        cls.httpserver.stop()
        td = getattr(cls, 'teardown', None)
        if td:
            td()

    date_tolerance = 2

    def assertEqualDates(self, dt1, dt2, seconds=None):
        """Assert ``abs(dt1 - dt2)`` is within ``Y`` seconds."""
        if seconds is None:
            seconds = self.date_tolerance

        if dt1 > dt2:
            diff = dt1 - dt2
        else:
            diff = dt2 - dt1
        if not diff < datetime.timedelta(seconds=seconds):
            raise AssertionError(
                '%r and %r are not within %r seconds.' % (dt1, dt2, seconds),
            )


class Request:
    """HTTP request container."""

    def __init__(self, environ):
        """Initialize HTTP request."""
        self.environ = environ


class Response:
    """HTTP response container."""

    def __init__(self):
        """Initialize HTTP response."""
        self.status = '200 OK'
        self.headers = {'Content-Type': 'text/html'}
        self.body = None

    def output(self):
        """Generate iterable response body object."""
        if self.body is None:
            return []
        if isinstance(self.body, str):
            return [self.body.encode('iso-8859-1')]
        if isinstance(self.body, bytes):
            return [self.body]
        return [x.encode('iso-8859-1') for x in self.body]


class Controller:
    """WSGI app for tests."""

    def __call__(self, environ, start_response):
        """WSGI request handler."""
        req, resp = Request(environ), Response()
        try:
            # Python 3 supports unicode attribute names
            # Python 2 encodes them
            handler = self.handlers[environ['PATH_INFO']]
        except KeyError:
            resp.status = '404 Not Found'
        else:
            output = handler(req, resp)
            if output is not None and not any(
                resp.status.startswith(status_code)
                for status_code in ('204', '304')
            ):
                resp.body = output
                try:
                    resp.headers.setdefault('Content-Length', str(len(output)))
                except TypeError:
                    if not isinstance(output, types.GeneratorType):
                        raise
        start_response(resp.status, resp.headers.items())
        return resp.output()
