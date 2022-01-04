"""Extensions to unittest for web frameworks.

Use the :py:meth:`WebCase.getPage` method to request a page
from your HTTP server.

Framework Integration
=====================
If you have control over your server process, you can handle errors
in the server-side of the HTTP conversation a bit better. You must run
both the client (your :py:class:`WebCase` tests) and the server in the
same process (but in separate threads, obviously).
When an error occurs in the framework, call server_error. It will print
the traceback to stdout, and keep any assertions you have from running
(the assumption is that, if the server errors, the page output will not
be of further significance to your tests).
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pprint
import re
import socket
import sys
import time
import traceback
import os
import json
import unittest  # pylint: disable=deprecated-module,preferred-module
import warnings
import functools

from six.moves import http_client, map, urllib_parse
import six

from more_itertools.more import always_iterable
import jaraco.functools


def interface(host):
    """Return an IP address for a client connection given the server host.

    If the server is listening on '0.0.0.0' (INADDR_ANY)
    or '::' (IN6ADDR_ANY), this will return the proper localhost.
    """
    if host == '0.0.0.0':
        # INADDR_ANY, which should respond on localhost.
        return '127.0.0.1'
    if host == '::':
        # IN6ADDR_ANY, which should respond on localhost.
        return '::1'
    return host


try:
    # Jython support
    if sys.platform[:4] == 'java':
        def getchar():
            """Get a key press."""
            # Hopefully this is enough
            return sys.stdin.read(1)
    else:
        # On Windows, msvcrt.getch reads a single char without output.
        import msvcrt

        def getchar():
            """Get a key press."""
            return msvcrt.getch()
except ImportError:
    # Unix getchr
    import tty
    import termios

    def getchar():
        """Get a key press."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


# from jaraco.properties
class NonDataProperty:
    """Non-data property decorator."""

    def __init__(self, fget):
        """Initialize a non-data property."""
        assert fget is not None, 'fget cannot be none'
        assert callable(fget), 'fget must be callable'
        self.fget = fget

    def __get__(self, obj, objtype=None):
        """Return a class property."""
        if obj is None:
            return self
        return self.fget(obj)


class WebCase(unittest.TestCase):
    """Helper web test suite base."""

    HOST = '127.0.0.1'
    PORT = 8000
    HTTP_CONN = http_client.HTTPConnection
    PROTOCOL = 'HTTP/1.1'

    scheme = 'http'
    url = None
    ssl_context = None

    status = None
    headers = None
    body = None

    encoding = 'utf-8'

    time = None

    @property
    def _Conn(self):
        """Return HTTPConnection or HTTPSConnection based on self.scheme.

        * from :py:mod:`python:http.client`.
        """
        cls_name = '{scheme}Connection'.format(scheme=self.scheme.upper())
        return getattr(http_client, cls_name)

    def get_conn(self, auto_open=False):
        """Return a connection to our HTTP server."""
        conn = self._Conn(self.interface(), self.PORT)
        # Automatically re-connect?
        conn.auto_open = auto_open
        conn.connect()
        return conn

    def set_persistent(self, on=True, auto_open=False):
        """Make our HTTP_CONN persistent (or not).

        If the 'on' argument is True (the default), then self.HTTP_CONN
        will be set to an instance of HTTP(S)?Connection
        to persist across requests.
        As this class only allows for a single open connection, if
        self already has an open connection, it will be closed.
        """
        try:
            self.HTTP_CONN.close()
        except (TypeError, AttributeError):
            pass

        self.HTTP_CONN = (
            self.get_conn(auto_open=auto_open)
            if on
            else self._Conn
        )

    @property
    def persistent(self):
        """Presence of the persistent HTTP connection."""
        return hasattr(self.HTTP_CONN, '__class__')

    @persistent.setter
    def persistent(self, on):
        self.set_persistent(on)

    def interface(self):
        """Return an IP address for a client connection.

        If the server is listening on '0.0.0.0' (INADDR_ANY)
        or '::' (IN6ADDR_ANY), this will return the proper localhost.
        """
        return interface(self.HOST)

    def getPage(
        self, url, headers=None, method='GET', body=None,
        protocol=None, raise_subcls=(),
    ):
        """Open the url with debugging support.

        Return status, headers, body.

        url should be the identifier passed to the server, typically a
        server-absolute path and query string (sent between method and
        protocol), and should only be an absolute URI if proxy support is
        enabled in the server.

        If the application under test generates absolute URIs, be sure
        to wrap them first with :py:func:`strip_netloc`::

            >>> class MyAppWebCase(WebCase):
            ...     def getPage(url, *args, **kwargs):
            ...         super(MyAppWebCase, self).getPage(
            ...             cheroot.test.webtest.strip_netloc(url),
            ...             *args, **kwargs
            ...         )

        ``raise_subcls`` is passed through to :py:func:`openURL`.
        """
        ServerError.on = False

        if isinstance(url, six.text_type):
            url = url.encode('utf-8')
        if isinstance(body, six.text_type):
            body = body.encode('utf-8')

        # for compatibility, support raise_subcls is None
        raise_subcls = raise_subcls or ()

        self.url = url
        self.time = None
        start = time.time()
        result = openURL(
            url, headers, method, body, self.HOST, self.PORT,
            self.HTTP_CONN, protocol or self.PROTOCOL,
            raise_subcls=raise_subcls,
            ssl_context=self.ssl_context,
        )
        self.time = time.time() - start
        self.status, self.headers, self.body = result

        # Build a list of request cookies from the previous response cookies.
        self.cookies = [
            ('Cookie', v) for k, v in self.headers
            if k.lower() == 'set-cookie'
        ]

        if ServerError.on:
            raise ServerError()
        return result

    @NonDataProperty
    def interactive(self):
        """Determine whether tests are run in interactive mode.

        Load interactivity setting from environment, where
        the value can be numeric or a string like true or
        False or 1 or 0.
        """
        env_str = os.environ.get('WEBTEST_INTERACTIVE', 'True')
        is_interactive = bool(json.loads(env_str.lower()))
        if is_interactive:
            warnings.warn(
                'Interactive test failure interceptor support via '
                'WEBTEST_INTERACTIVE environment variable is deprecated.',
                DeprecationWarning,
            )
        return is_interactive

    console_height = 30

    def _handlewebError(self, msg):  # noqa: C901  # FIXME
        print('')
        print('    ERROR: %s' % msg)

        if not self.interactive:
            raise self.failureException(msg)

        p = (
            '    Show: '
            '[B]ody [H]eaders [S]tatus [U]RL; '
            '[I]gnore, [R]aise, or sys.e[X]it >> '
        )
        sys.stdout.write(p)
        sys.stdout.flush()
        while True:
            i = getchar().upper()
            if not isinstance(i, type('')):
                i = i.decode('ascii')
            if i not in 'BHSUIRX':
                continue
            print(i.upper())  # Also prints new line
            if i == 'B':
                for x, line in enumerate(self.body.splitlines()):
                    if (x + 1) % self.console_height == 0:
                        # The \r and comma should make the next line overwrite
                        sys.stdout.write('<-- More -->\r')
                        m = getchar().lower()
                        # Erase our "More" prompt
                        sys.stdout.write('            \r')
                        if m == 'q':
                            break
                    print(line)
            elif i == 'H':
                pprint.pprint(self.headers)
            elif i == 'S':
                print(self.status)
            elif i == 'U':
                print(self.url)
            elif i == 'I':
                # return without raising the normal exception
                return
            elif i == 'R':
                raise self.failureException(msg)
            elif i == 'X':
                sys.exit()
            sys.stdout.write(p)
            sys.stdout.flush()

    @property
    def status_code(self):  # noqa: D401; irrelevant for properties
        """Integer HTTP status code."""
        return int(self.status[:3])

    def status_matches(self, expected):
        """Check whether actual status matches expected."""
        actual = (
            self.status_code
            if isinstance(expected, int) else
            self.status
        )
        return expected == actual

    def assertStatus(self, status, msg=None):
        """Fail if self.status != status.

        status may be integer code, exact string status, or
        iterable of allowed possibilities.
        """
        if any(map(self.status_matches, always_iterable(status))):
            return

        tmpl = 'Status {self.status} does not match {status}'
        msg = msg or tmpl.format(**locals())
        self._handlewebError(msg)

    def assertHeader(self, key, value=None, msg=None):
        """Fail if (key, [value]) not in self.headers."""
        lowkey = key.lower()
        for k, v in self.headers:
            if k.lower() == lowkey:
                if value is None or str(value) == v:
                    return v

        if msg is None:
            if value is None:
                msg = '%r not in headers' % key
            else:
                msg = '%r:%r not in headers' % (key, value)
        self._handlewebError(msg)

    def assertHeaderIn(self, key, values, msg=None):
        """Fail if header indicated by key doesn't have one of the values."""
        lowkey = key.lower()
        for k, v in self.headers:
            if k.lower() == lowkey:
                matches = [value for value in values if str(value) == v]
                if matches:
                    return matches

        if msg is None:
            msg = '%(key)r not in %(values)r' % vars()
        self._handlewebError(msg)

    def assertHeaderItemValue(self, key, value, msg=None):
        """Fail if the header does not contain the specified value."""
        actual_value = self.assertHeader(key, msg=msg)
        header_values = map(str.strip, actual_value.split(','))
        if value in header_values:
            return value

        if msg is None:
            msg = '%r not in %r' % (value, header_values)
        self._handlewebError(msg)

    def assertNoHeader(self, key, msg=None):
        """Fail if key in self.headers."""
        lowkey = key.lower()
        matches = [k for k, v in self.headers if k.lower() == lowkey]
        if matches:
            if msg is None:
                msg = '%r in headers' % key
            self._handlewebError(msg)

    def assertNoHeaderItemValue(self, key, value, msg=None):
        """Fail if the header contains the specified value."""
        lowkey = key.lower()
        hdrs = self.headers
        matches = [k for k, v in hdrs if k.lower() == lowkey and v == value]
        if matches:
            if msg is None:
                msg = '%r:%r in %r' % (key, value, hdrs)
            self._handlewebError(msg)

    def assertBody(self, value, msg=None):
        """Fail if value != self.body."""
        if isinstance(value, six.text_type):
            value = value.encode(self.encoding)
        if value != self.body:
            if msg is None:
                msg = 'expected body:\n%r\n\nactual body:\n%r' % (
                    value, self.body,
                )
            self._handlewebError(msg)

    def assertInBody(self, value, msg=None):
        """Fail if value not in self.body."""
        if isinstance(value, six.text_type):
            value = value.encode(self.encoding)
        if value not in self.body:
            if msg is None:
                msg = '%r not in body: %s' % (value, self.body)
            self._handlewebError(msg)

    def assertNotInBody(self, value, msg=None):
        """Fail if value in self.body."""
        if isinstance(value, six.text_type):
            value = value.encode(self.encoding)
        if value in self.body:
            if msg is None:
                msg = '%r found in body' % value
            self._handlewebError(msg)

    def assertMatchesBody(self, pattern, msg=None, flags=0):
        """Fail if value (a regex pattern) is not in self.body."""
        if isinstance(pattern, six.text_type):
            pattern = pattern.encode(self.encoding)
        if re.search(pattern, self.body, flags) is None:
            if msg is None:
                msg = 'No match for %r in body' % pattern
            self._handlewebError(msg)


methods_with_bodies = ('POST', 'PUT', 'PATCH')


def cleanHeaders(headers, method, body, host, port):
    """Return request headers, with required headers added (if missing)."""
    if headers is None:
        headers = []

    # Add the required Host request header if not present.
    # [This specifies the host:port of the server, not the client.]
    found = False
    for k, _v in headers:
        if k.lower() == 'host':
            found = True
            break
    if not found:
        if port == 80:
            headers.append(('Host', host))
        else:
            headers.append(('Host', '%s:%s' % (host, port)))

    if method in methods_with_bodies:
        # Stick in default type and length headers if not present
        found = False
        for k, v in headers:
            if k.lower() == 'content-type':
                found = True
                break
        if not found:
            headers.append(
                ('Content-Type', 'application/x-www-form-urlencoded'),
            )
            headers.append(('Content-Length', str(len(body or ''))))

    return headers


def shb(response):
    """Return status, headers, body the way we like from a response."""
    resp_status_line = '%s %s' % (response.status, response.reason)

    if not six.PY2:
        return resp_status_line, response.getheaders(), response.read()

    h = []
    key, value = None, None
    for line in response.msg.headers:
        if line:
            if line[0] in ' \t':
                value += line.strip()
            else:
                if key and value:
                    h.append((key, value))
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
    if key and value:
        h.append((key, value))

    return resp_status_line, h, response.read()


# def openURL(*args, raise_subcls=(), **kwargs):
# py27 compatible signature:
def openURL(*args, **kwargs):
    """
    Open a URL, retrying when it fails.

    Specify ``raise_subcls`` (class or tuple of classes) to exclude
    those socket.error subclasses from being suppressed and retried.
    """
    raise_subcls = kwargs.pop('raise_subcls', ())
    opener = functools.partial(_open_url_once, *args, **kwargs)

    def on_exception():
        exc = sys.exc_info()[1]
        if isinstance(exc, raise_subcls):
            raise exc
        time.sleep(0.5)

    # Try up to 10 times
    return jaraco.functools.retry_call(
        opener,
        retries=9,
        cleanup=on_exception,
        trap=socket.error,
    )


def _open_url_once(
    url, headers=None, method='GET', body=None,
    host='127.0.0.1', port=8000, http_conn=http_client.HTTPConnection,
    protocol='HTTP/1.1', ssl_context=None,
):
    """Open the given HTTP resource and return status, headers, and body."""
    headers = cleanHeaders(headers, method, body, host, port)

    # Allow http_conn to be a class or an instance
    if hasattr(http_conn, 'host'):
        conn = http_conn
    else:
        kw = {}
        if ssl_context:
            kw['context'] = ssl_context
        conn = http_conn(interface(host), port, **kw)
    conn._http_vsn_str = protocol
    conn._http_vsn = int(''.join([x for x in protocol if x.isdigit()]))
    if not six.PY2 and isinstance(url, bytes):
        url = url.decode()
    conn.putrequest(
        method.upper(), url, skip_host=True,
        skip_accept_encoding=True,
    )
    for key, value in headers:
        conn.putheader(key, value.encode('Latin-1'))
    conn.endheaders()
    if body is not None:
        conn.send(body)
    # Handle response
    response = conn.getresponse()
    s, h, b = shb(response)
    if not hasattr(http_conn, 'host'):
        # We made our own conn instance. Close it.
        conn.close()
    return s, h, b


def strip_netloc(url):
    """Return absolute-URI path from URL.

    Strip the scheme and host from the URL, returning the
    server-absolute portion.

    Useful for wrapping an absolute-URI for which only the
    path is expected (such as in calls to :py:meth:`WebCase.getPage`).

    .. testsetup::

       from cheroot.test.webtest import strip_netloc

    >>> strip_netloc('https://google.com/foo/bar?bing#baz')
    '/foo/bar?bing'

    >>> strip_netloc('//google.com/foo/bar?bing#baz')
    '/foo/bar?bing'

    >>> strip_netloc('/foo/bar?bing#baz')
    '/foo/bar?bing'
    """
    parsed = urllib_parse.urlparse(url)
    _scheme, _netloc, path, params, query, _fragment = parsed
    stripped = '', '', path, params, query, ''
    return urllib_parse.urlunparse(stripped)


# Add any exceptions which your web framework handles
# normally (that you don't want server_error to trap).
ignored_exceptions = []

# You'll want set this to True when you can't guarantee
# that each response will immediately follow each request;
# for example, when handling requests via multiple threads.
ignore_all = False


class ServerError(Exception):
    """Exception for signalling server error."""

    on = False


def server_error(exc=None):
    """Server debug hook.

    Return True if exception handled, False if ignored.
    You probably want to wrap this, so you can still handle an error using
    your framework when it's ignored.
    """
    if exc is None:
        exc = sys.exc_info()

    if ignore_all or exc[0] in ignored_exceptions:
        return False
    else:
        ServerError.on = True
        print('')
        print(''.join(traceback.format_exception(*exc)))
        return True
