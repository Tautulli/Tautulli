"""
A high-speed, production ready, thread pooled, generic HTTP server.

For those of you wanting to understand internals of this module, here's the
basic call flow. The server's listening thread runs a very tight loop,
sticking incoming connections onto a Queue::

    server = HTTPServer(...)
    server.start()
    ->  serve()
        while ready:
            _connections.run()
                while not stop_requested:
                    child = socket.accept()  # blocks until a request comes in
                    conn = HTTPConnection(child, ...)
                    server.process_conn(conn)  # adds conn to threadpool

Worker threads are kept in a pool and poll the Queue, popping off and then
handling each connection in turn. Each connection can consist of an arbitrary
number of requests and their responses, so we run a nested loop::

    while True:
        conn = server.requests.get()
        conn.communicate()
        ->  while True:
                req = HTTPRequest(...)
                req.parse_request()
                ->  # Read the Request-Line, e.g. "GET /page HTTP/1.1"
                    req.rfile.readline()
                    read_headers(req.rfile, req.inheaders)
                req.respond()
                ->  response = app(...)
                    try:
                        for chunk in response:
                            if chunk:
                                req.write(chunk)
                    finally:
                        if hasattr(response, "close"):
                            response.close()
                if req.close_connection:
                    return

For running a server you can invoke :func:`start() <HTTPServer.start()>` (it
will run the server forever) or use invoking :func:`prepare()
<HTTPServer.prepare()>` and :func:`serve() <HTTPServer.serve()>` like this::

    server = HTTPServer(...)
    server.prepare()
    try:
        threading.Thread(target=server.serve).start()

        # waiting/detecting some appropriate stop condition here
        ...

    finally:
        server.stop()

And now for a trivial doctest to exercise the test suite

.. testsetup::

   from cheroot.server import HTTPServer

>>> 'HTTPServer' in globals()
True
"""

import os
import io
import re
import email.utils
import socket
import sys
import time
import traceback as traceback_
import logging
import platform
import queue
import contextlib
import threading
import urllib.parse
from functools import lru_cache

from . import connections, errors, __version__
from ._compat import bton
from ._compat import IS_PPC
from .workers import threadpool
from .makefile import MakeFile, StreamWriter


__all__ = (
    'HTTPRequest', 'HTTPConnection', 'HTTPServer',
    'HeaderReader', 'DropUnderscoreHeaderReader',
    'SizeCheckWrapper', 'KnownLengthRFile', 'ChunkedRFile',
    'Gateway', 'get_ssl_adapter_class',
)


IS_WINDOWS = platform.system() == 'Windows'
"""Flag indicating whether the app is running under Windows."""


IS_GAE = os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/')
"""Flag indicating whether the app is running in GAE env.

Ref:
https://cloud.google.com/appengine/docs/standard/python/tools
/using-local-server#detecting_application_runtime_environment
"""


IS_UID_GID_RESOLVABLE = not IS_WINDOWS and not IS_GAE
"""Indicates whether UID/GID resolution's available under current platform."""


if IS_UID_GID_RESOLVABLE:
    try:
        import grp
        import pwd
    except ImportError:
        """Unavailable in the current env.

        This shouldn't be happening normally.
        All of the known cases are excluded via the if clause.
        """
        IS_UID_GID_RESOLVABLE = False
        grp, pwd = None, None
    import struct


if IS_WINDOWS and hasattr(socket, 'AF_INET6'):
    if not hasattr(socket, 'IPPROTO_IPV6'):
        socket.IPPROTO_IPV6 = 41
    if not hasattr(socket, 'IPV6_V6ONLY'):
        socket.IPV6_V6ONLY = 27


if not hasattr(socket, 'SO_PEERCRED'):
    """
    NOTE: the value for SO_PEERCRED can be architecture specific, in
    which case the getsockopt() will hopefully fail. The arch
    specific value could be derived from platform.processor()
    """
    socket.SO_PEERCRED = 21 if IS_PPC else 17


LF = b'\n'
CRLF = b'\r\n'
TAB = b'\t'
SPACE = b' '
COLON = b':'
SEMICOLON = b';'
EMPTY = b''
ASTERISK = b'*'
FORWARD_SLASH = b'/'
QUOTED_SLASH = b'%2F'
QUOTED_SLASH_REGEX = re.compile(b''.join((b'(?i)', QUOTED_SLASH)))


_STOPPING_FOR_INTERRUPT = Exception()  # sentinel used during shutdown


comma_separated_headers = [
    b'Accept', b'Accept-Charset', b'Accept-Encoding',
    b'Accept-Language', b'Accept-Ranges', b'Allow', b'Cache-Control',
    b'Connection', b'Content-Encoding', b'Content-Language', b'Expect',
    b'If-Match', b'If-None-Match', b'Pragma', b'Proxy-Authenticate', b'TE',
    b'Trailer', b'Transfer-Encoding', b'Upgrade', b'Vary', b'Via', b'Warning',
    b'WWW-Authenticate',
]


if not hasattr(logging, 'statistics'):
    logging.statistics = {}


class HeaderReader:
    """Object for reading headers from an HTTP request.

    Interface and default implementation.
    """

    def __call__(self, rfile, hdict=None):  # noqa: C901  # FIXME
        """
        Read headers from the given stream into the given header dict.

        If hdict is None, a new header dict is created. Returns the populated
        header dict.

        Headers which are repeated are folded together using a comma if their
        specification so dictates.

        This function raises ValueError when the read bytes violate the HTTP
        spec.
        You should probably return "400 Bad Request" if this happens.
        """
        if hdict is None:
            hdict = {}

        while True:
            line = rfile.readline()
            if not line:
                # No more data--illegal end of headers
                raise ValueError('Illegal end of headers.')

            if line == CRLF:
                # Normal end of headers
                break
            if not line.endswith(CRLF):
                raise ValueError('HTTP requires CRLF terminators')

            if line[:1] in (SPACE, TAB):
                # NOTE: `type(line[0]) is int` and `type(line[:1]) is bytes`.
                # NOTE: The former causes a the following warning:
                # NOTE: `BytesWarning('Comparison between bytes and int')`
                # NOTE: The latter is equivalent and does not.
                # It's a continuation line.
                v = line.strip()
            else:
                try:
                    k, v = line.split(COLON, 1)
                except ValueError:
                    raise ValueError('Illegal header line.')
                v = v.strip()
                k = self._transform_key(k)
                hname = k

            if not self._allow_header(k):
                continue

            if k in comma_separated_headers:
                existing = hdict.get(hname)
                if existing:
                    v = b', '.join((existing, v))
            hdict[hname] = v

        return hdict

    def _allow_header(self, key_name):
        return True

    def _transform_key(self, key_name):
        # TODO: what about TE and WWW-Authenticate?
        return key_name.strip().title()


class DropUnderscoreHeaderReader(HeaderReader):
    """Custom HeaderReader to exclude any headers with underscores in them."""

    def _allow_header(self, key_name):
        orig = super(DropUnderscoreHeaderReader, self)._allow_header(key_name)
        return orig and '_' not in key_name


class SizeCheckWrapper:
    """Wraps a file-like object, raising MaxSizeExceeded if too large.

    :param rfile: ``file`` of a limited size
    :param int maxlen: maximum length of the file being read
    """

    def __init__(self, rfile, maxlen):
        """Initialize SizeCheckWrapper instance."""
        self.rfile = rfile
        self.maxlen = maxlen
        self.bytes_read = 0

    def _check_length(self):
        if self.maxlen and self.bytes_read > self.maxlen:
            raise errors.MaxSizeExceeded()

    def read(self, size=None):
        """Read a chunk from ``rfile`` buffer and return it.

        :param size: amount of data to read
        :type size: int

        :returns: chunk from ``rfile``, limited by size if specified
        :rtype: bytes
        """
        data = self.rfile.read(size)
        self.bytes_read += len(data)
        self._check_length()
        return data

    def readline(self, size=None):
        """Read a single line from ``rfile`` buffer and return it.

        :param size: minimum amount of data to read
        :type size: int

        :returns: one line from ``rfile``
        :rtype: bytes
        """
        if size is not None:
            data = self.rfile.readline(size)
            self.bytes_read += len(data)
            self._check_length()
            return data

        # User didn't specify a size ...
        # We read the line in chunks to make sure it's not a 100MB line !
        res = []
        while True:
            data = self.rfile.readline(256)
            self.bytes_read += len(data)
            self._check_length()
            res.append(data)
            # See https://github.com/cherrypy/cherrypy/issues/421
            if len(data) < 256 or data[-1:] == LF:
                return EMPTY.join(res)

    def readlines(self, sizehint=0):
        """Read all lines from ``rfile`` buffer and return them.

        :param sizehint: hint of minimum amount of data to read
        :type sizehint: int

        :returns: lines of bytes read from ``rfile``
        :rtype: list[bytes]
        """
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline(sizehint)
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline(sizehint)
        return lines

    def close(self):
        """Release resources allocated for ``rfile``."""
        self.rfile.close()

    def __iter__(self):
        """Return file iterator."""
        return self

    def __next__(self):
        """Generate next file chunk."""
        data = next(self.rfile)
        self.bytes_read += len(data)
        self._check_length()
        return data

    next = __next__


class KnownLengthRFile:
    """Wraps a file-like object, returning an empty string when exhausted.

    :param rfile: ``file`` of a known size
    :param int content_length: length of the file being read
    """

    def __init__(self, rfile, content_length):
        """Initialize KnownLengthRFile instance."""
        self.rfile = rfile
        self.remaining = content_length

    def read(self, size=None):
        """Read a chunk from ``rfile`` buffer and return it.

        :param size: amount of data to read
        :type size: int

        :rtype: bytes
        :returns: chunk from ``rfile``, limited by size if specified
        """
        if self.remaining == 0:
            return b''
        if size is None:
            size = self.remaining
        else:
            size = min(size, self.remaining)

        data = self.rfile.read(size)
        self.remaining -= len(data)
        return data

    def readline(self, size=None):
        """Read a single line from ``rfile`` buffer and return it.

        :param size: minimum amount of data to read
        :type size: int

        :returns: one line from ``rfile``
        :rtype: bytes
        """
        if self.remaining == 0:
            return b''
        if size is None:
            size = self.remaining
        else:
            size = min(size, self.remaining)

        data = self.rfile.readline(size)
        self.remaining -= len(data)
        return data

    def readlines(self, sizehint=0):
        """Read all lines from ``rfile`` buffer and return them.

        :param sizehint: hint of minimum amount of data to read
        :type sizehint: int

        :returns: lines of bytes read from ``rfile``
        :rtype: list[bytes]
        """
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline(sizehint)
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline(sizehint)
        return lines

    def close(self):
        """Release resources allocated for ``rfile``."""
        self.rfile.close()

    def __iter__(self):
        """Return file iterator."""
        return self

    def __next__(self):
        """Generate next file chunk."""
        data = next(self.rfile)
        self.remaining -= len(data)
        return data

    next = __next__


class ChunkedRFile:
    """Wraps a file-like object, returning an empty string when exhausted.

    This class is intended to provide a conforming wsgi.input value for
    request entities that have been encoded with the 'chunked' transfer
    encoding.

    :param rfile: file encoded with the 'chunked' transfer encoding
    :param int maxlen: maximum length of the file being read
    :param int bufsize: size of the buffer used to read the file
    """

    def __init__(self, rfile, maxlen, bufsize=8192):
        """Initialize ChunkedRFile instance."""
        self.rfile = rfile
        self.maxlen = maxlen
        self.bytes_read = 0
        self.buffer = EMPTY
        self.bufsize = bufsize
        self.closed = False

    def _fetch(self):
        if self.closed:
            return

        line = self.rfile.readline()
        self.bytes_read += len(line)

        if self.maxlen and self.bytes_read > self.maxlen:
            raise errors.MaxSizeExceeded(
                'Request Entity Too Large', self.maxlen,
            )

        line = line.strip().split(SEMICOLON, 1)

        try:
            chunk_size = line.pop(0)
            chunk_size = int(chunk_size, 16)
        except ValueError:
            raise ValueError(
                'Bad chunked transfer size: {chunk_size!r}'.
                format(chunk_size=chunk_size),
            )

        if chunk_size <= 0:
            self.closed = True
            return

#            if line: chunk_extension = line[0]

        if self.maxlen and self.bytes_read + chunk_size > self.maxlen:
            raise IOError('Request Entity Too Large')

        chunk = self.rfile.read(chunk_size)
        self.bytes_read += len(chunk)
        self.buffer += chunk

        crlf = self.rfile.read(2)
        if crlf != CRLF:
            raise ValueError(
                "Bad chunked transfer coding (expected '\\r\\n', "
                'got ' + repr(crlf) + ')',
            )

    def read(self, size=None):
        """Read a chunk from ``rfile`` buffer and return it.

        :param size: amount of data to read
        :type size: int

        :returns: chunk from ``rfile``, limited by size if specified
        :rtype: bytes
        """
        data = EMPTY

        if size == 0:
            return data

        while True:
            if size and len(data) >= size:
                return data

            if not self.buffer:
                self._fetch()
                if not self.buffer:
                    # EOF
                    return data

            if size:
                remaining = size - len(data)
                data += self.buffer[:remaining]
                self.buffer = self.buffer[remaining:]
            else:
                data += self.buffer
                self.buffer = EMPTY

    def readline(self, size=None):
        """Read a single line from ``rfile`` buffer and return it.

        :param size: minimum amount of data to read
        :type size: int

        :returns: one line from ``rfile``
        :rtype: bytes
        """
        data = EMPTY

        if size == 0:
            return data

        while True:
            if size and len(data) >= size:
                return data

            if not self.buffer:
                self._fetch()
                if not self.buffer:
                    # EOF
                    return data

            newline_pos = self.buffer.find(LF)
            if size:
                if newline_pos == -1:
                    remaining = size - len(data)
                    data += self.buffer[:remaining]
                    self.buffer = self.buffer[remaining:]
                else:
                    remaining = min(size - len(data), newline_pos)
                    data += self.buffer[:remaining]
                    self.buffer = self.buffer[remaining:]
            else:
                if newline_pos == -1:
                    data += self.buffer
                    self.buffer = EMPTY
                else:
                    data += self.buffer[:newline_pos]
                    self.buffer = self.buffer[newline_pos:]

    def readlines(self, sizehint=0):
        """Read all lines from ``rfile`` buffer and return them.

        :param sizehint: hint of minimum amount of data to read
        :type sizehint: int

        :returns: lines of bytes read from ``rfile``
        :rtype: list[bytes]
        """
        # Shamelessly stolen from StringIO
        total = 0
        lines = []
        line = self.readline(sizehint)
        while line:
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
            line = self.readline(sizehint)
        return lines

    def read_trailer_lines(self):
        """Read HTTP headers and yield them.

        :yields: CRLF separated lines
        :ytype: bytes

        """
        if not self.closed:
            raise ValueError(
                'Cannot read trailers until the request body has been read.',
            )

        while True:
            line = self.rfile.readline()
            if not line:
                # No more data--illegal end of headers
                raise ValueError('Illegal end of headers.')

            self.bytes_read += len(line)
            if self.maxlen and self.bytes_read > self.maxlen:
                raise IOError('Request Entity Too Large')

            if line == CRLF:
                # Normal end of headers
                break
            if not line.endswith(CRLF):
                raise ValueError('HTTP requires CRLF terminators')

            yield line

    def close(self):
        """Release resources allocated for ``rfile``."""
        self.rfile.close()


class HTTPRequest:
    """An HTTP Request (and response).

    A single HTTP connection may consist of multiple request/response pairs.
    """

    server = None
    """The HTTPServer object which is receiving this request."""

    conn = None
    """The HTTPConnection object on which this request connected."""

    inheaders = {}
    """A dict of request headers."""

    outheaders = []
    """A list of header tuples to write in the response."""

    ready = False
    """When True, the request has been parsed and is ready to begin generating
    the response. When False, signals the calling Connection that the response
    should not be generated and the connection should close."""

    close_connection = False
    """Signals the calling Connection that the request should close. This does
    not imply an error! The client and/or server may each request that the
    connection be closed."""

    chunked_write = False
    """If True, output will be encoded with the "chunked" transfer-coding.

    This value is set automatically inside send_headers."""

    header_reader = HeaderReader()
    """
    A HeaderReader instance or compatible reader.
    """

    def __init__(self, server, conn, proxy_mode=False, strict_mode=True):
        """Initialize HTTP request container instance.

        Args:
            server (HTTPServer): web server object receiving this request
            conn (HTTPConnection): HTTP connection object for this request
            proxy_mode (bool): whether this HTTPServer should behave as a PROXY
            server for certain requests
            strict_mode (bool): whether we should return a 400 Bad Request when
            we encounter a request that a HTTP compliant client should not be
            making
        """
        self.server = server
        self.conn = conn

        self.ready = False
        self.started_request = False
        self.scheme = b'http'
        if self.server.ssl_adapter is not None:
            self.scheme = b'https'
        # Use the lowest-common protocol in case read_request_line errors.
        self.response_protocol = 'HTTP/1.0'
        self.inheaders = {}

        self.status = ''
        self.outheaders = []
        self.sent_headers = False
        self.close_connection = self.__class__.close_connection
        self.chunked_read = False
        self.chunked_write = self.__class__.chunked_write
        self.proxy_mode = proxy_mode
        self.strict_mode = strict_mode

    def parse_request(self):
        """Parse the next HTTP request start-line and message-headers."""
        self.rfile = SizeCheckWrapper(
            self.conn.rfile,
            self.server.max_request_header_size,
        )
        try:
            success = self.read_request_line()
        except errors.MaxSizeExceeded:
            self.simple_response(
                '414 Request-URI Too Long',
                'The Request-URI sent with the request exceeds the maximum '
                'allowed bytes.',
            )
            return
        else:
            if not success:
                return

        try:
            success = self.read_request_headers()
        except errors.MaxSizeExceeded:
            self.simple_response(
                '413 Request Entity Too Large',
                'The headers sent with the request exceed the maximum '
                'allowed bytes.',
            )
            return
        else:
            if not success:
                return

        self.ready = True

    def read_request_line(self):  # noqa: C901  # FIXME
        """Read and parse first line of the HTTP request.

        Returns:
            bool: True if the request line is valid or False if it's malformed.

        """
        # HTTP/1.1 connections are persistent by default. If a client
        # requests a page, then idles (leaves the connection open),
        # then rfile.readline() will raise socket.error("timed out").
        # Note that it does this based on the value given to settimeout(),
        # and doesn't need the client to request or acknowledge the close
        # (although your TCP stack might suffer for it: cf Apache's history
        # with FIN_WAIT_2).
        request_line = self.rfile.readline()

        # Set started_request to True so communicate() knows to send 408
        # from here on out.
        self.started_request = True
        if not request_line:
            return False

        if request_line == CRLF:
            # RFC 2616 sec 4.1: "...if the server is reading the protocol
            # stream at the beginning of a message and receives a CRLF
            # first, it should ignore the CRLF."
            # But only ignore one leading line! else we enable a DoS.
            request_line = self.rfile.readline()
            if not request_line:
                return False

        if not request_line.endswith(CRLF):
            self.simple_response(
                '400 Bad Request', 'HTTP requires CRLF terminators',
            )
            return False

        try:
            method, uri, req_protocol = request_line.strip().split(SPACE, 2)
            if not req_protocol.startswith(b'HTTP/'):
                self.simple_response(
                    '400 Bad Request', 'Malformed Request-Line: bad protocol',
                )
                return False
            rp = req_protocol[5:].split(b'.', 1)
            if len(rp) != 2:
                self.simple_response(
                    '400 Bad Request', 'Malformed Request-Line: bad version',
                )
                return False
            rp = tuple(map(int, rp))  # Minor.Major must be threat as integers
            if rp > (1, 1):
                self.simple_response(
                    '505 HTTP Version Not Supported', 'Cannot fulfill request',
                )
                return False
        except (ValueError, IndexError):
            self.simple_response('400 Bad Request', 'Malformed Request-Line')
            return False

        self.uri = uri
        self.method = method.upper()

        if self.strict_mode and method != self.method:
            resp = (
                'Malformed method name: According to RFC 2616 '
                '(section 5.1.1) and its successors '
                'RFC 7230 (section 3.1.1) and RFC 7231 (section 4.1) '
                'method names are case-sensitive and uppercase.'
            )
            self.simple_response('400 Bad Request', resp)
            return False

        try:
            scheme, authority, path, qs, fragment = urllib.parse.urlsplit(uri)
        except UnicodeError:
            self.simple_response('400 Bad Request', 'Malformed Request-URI')
            return False

        uri_is_absolute_form = (scheme or authority)

        if self.method == b'OPTIONS':
            # TODO: cover this branch with tests
            path = (
                uri
                # https://tools.ietf.org/html/rfc7230#section-5.3.4
                if (self.proxy_mode and uri_is_absolute_form)
                else path
            )
        elif self.method == b'CONNECT':
            # TODO: cover this branch with tests
            if not self.proxy_mode:
                self.simple_response('405 Method Not Allowed')
                return False

            # `urlsplit()` above parses "example.com:3128" as path part of URI.
            # this is a workaround, which makes it detect netloc correctly
            uri_split = urllib.parse.urlsplit(b''.join((b'//', uri)))
            _scheme, _authority, _path, _qs, _fragment = uri_split
            _port = EMPTY
            try:
                _port = uri_split.port
            except ValueError:
                pass

            # FIXME: use third-party validation to make checks against RFC
            # the validation doesn't take into account, that urllib parses
            # invalid URIs without raising errors
            # https://tools.ietf.org/html/rfc7230#section-5.3.3
            invalid_path = (
                _authority != uri
                or not _port
                or any((_scheme, _path, _qs, _fragment))
            )
            if invalid_path:
                self.simple_response(
                    '400 Bad Request',
                    'Invalid path in Request-URI: request-'
                    'target must match authority-form.',
                )
                return False

            authority = path = _authority
            scheme = qs = fragment = EMPTY
        else:
            disallowed_absolute = (
                self.strict_mode
                and not self.proxy_mode
                and uri_is_absolute_form
            )
            if disallowed_absolute:
                # https://tools.ietf.org/html/rfc7230#section-5.3.2
                # (absolute form)
                """Absolute URI is only allowed within proxies."""
                self.simple_response(
                    '400 Bad Request',
                    'Absolute URI not allowed if server is not a proxy.',
                )
                return False

            invalid_path = (
                self.strict_mode
                and not uri.startswith(FORWARD_SLASH)
                and not uri_is_absolute_form
            )
            if invalid_path:
                # https://tools.ietf.org/html/rfc7230#section-5.3.1
                # (origin_form) and
                """Path should start with a forward slash."""
                resp = (
                    'Invalid path in Request-URI: request-target must contain '
                    'origin-form which starts with absolute-path (URI '
                    'starting with a slash "/").'
                )
                self.simple_response('400 Bad Request', resp)
                return False

            if fragment:
                self.simple_response(
                    '400 Bad Request',
                    'Illegal #fragment in Request-URI.',
                )
                return False

            if path is None:
                # FIXME: It looks like this case cannot happen
                self.simple_response(
                    '400 Bad Request',
                    'Invalid path in Request-URI.',
                )
                return False

            # Unquote the path+params (e.g. "/this%20path" -> "/this path").
            # https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
            #
            # But note that "...a URI must be separated into its components
            # before the escaped characters within those components can be
            # safely decoded." https://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
            # Therefore, "/this%2Fpath" becomes "/this%2Fpath", not
            # "/this/path".
            try:
                # TODO: Figure out whether exception can really happen here.
                # It looks like it's caught on urlsplit() call above.
                atoms = [
                    urllib.parse.unquote_to_bytes(x)
                    for x in QUOTED_SLASH_REGEX.split(path)
                ]
            except ValueError as ex:
                self.simple_response('400 Bad Request', ex.args[0])
                return False
            path = QUOTED_SLASH.join(atoms)

        if not path.startswith(FORWARD_SLASH):
            path = FORWARD_SLASH + path

        if scheme is not EMPTY:
            self.scheme = scheme
        self.authority = authority
        self.path = path

        # Note that, like wsgiref and most other HTTP servers,
        # we "% HEX HEX"-unquote the path but not the query string.
        self.qs = qs

        # Compare request and server HTTP protocol versions, in case our
        # server does not support the requested protocol. Limit our output
        # to min(req, server). We want the following output:
        #     request    server     actual written   supported response
        #     protocol   protocol  response protocol    feature set
        # a     1.0        1.0           1.0                1.0
        # b     1.0        1.1           1.1                1.0
        # c     1.1        1.0           1.0                1.0
        # d     1.1        1.1           1.1                1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        sp = int(self.server.protocol[5]), int(self.server.protocol[7])

        if sp[0] != rp[0]:
            self.simple_response('505 HTTP Version Not Supported')
            return False

        self.request_protocol = req_protocol
        self.response_protocol = 'HTTP/%s.%s' % min(rp, sp)

        return True

    def read_request_headers(self):  # noqa: C901  # FIXME
        """Read ``self.rfile`` into ``self.inheaders``.

        Ref: :py:attr:`self.inheaders <HTTPRequest.outheaders>`.

        :returns: success status
        :rtype: bool
        """
        # then all the http headers
        try:
            self.header_reader(self.rfile, self.inheaders)
        except ValueError as ex:
            self.simple_response('400 Bad Request', ex.args[0])
            return False

        mrbs = self.server.max_request_body_size

        try:
            cl = int(self.inheaders.get(b'Content-Length', 0))
        except ValueError:
            self.simple_response(
                '400 Bad Request',
                'Malformed Content-Length Header.',
            )
            return False

        if mrbs and cl > mrbs:
            self.simple_response(
                '413 Request Entity Too Large',
                'The entity sent with the request exceeds the maximum '
                'allowed bytes.',
            )
            return False

        # Persistent connection support
        if self.response_protocol == 'HTTP/1.1':
            # Both server and client are HTTP/1.1
            if self.inheaders.get(b'Connection', b'') == b'close':
                self.close_connection = True
        else:
            # Either the server or client (or both) are HTTP/1.0
            if self.inheaders.get(b'Connection', b'') != b'Keep-Alive':
                self.close_connection = True

        # Transfer-Encoding support
        te = None
        if self.response_protocol == 'HTTP/1.1':
            te = self.inheaders.get(b'Transfer-Encoding')
            if te:
                te = [x.strip().lower() for x in te.split(b',') if x.strip()]

        self.chunked_read = False

        if te:
            for enc in te:
                if enc == b'chunked':
                    self.chunked_read = True
                else:
                    # Note that, even if we see "chunked", we must reject
                    # if there is an extension we don't recognize.
                    self.simple_response('501 Unimplemented')
                    self.close_connection = True
                    return False

        # From PEP 333:
        # "Servers and gateways that implement HTTP 1.1 must provide
        # transparent support for HTTP 1.1's "expect/continue" mechanism.
        # This may be done in any of several ways:
        #   1. Respond to requests containing an Expect: 100-continue request
        #      with an immediate "100 Continue" response, and proceed normally.
        #   2. Proceed with the request normally, but provide the application
        #      with a wsgi.input stream that will send the "100 Continue"
        #      response if/when the application first attempts to read from
        #      the input stream. The read request must then remain blocked
        #      until the client responds.
        #   3. Wait until the client decides that the server does not support
        #      expect/continue, and sends the request body on its own.
        #      (This is suboptimal, and is not recommended.)
        #
        # We used to do 3, but are now doing 1. Maybe we'll do 2 someday,
        # but it seems like it would be a big slowdown for such a rare case.
        if self.inheaders.get(b'Expect', b'') == b'100-continue':
            # Don't use simple_response here, because it emits headers
            # we don't want. See
            # https://github.com/cherrypy/cherrypy/issues/951
            msg = b''.join((
                self.server.protocol.encode('ascii'), SPACE, b'100 Continue',
                CRLF, CRLF,
            ))
            try:
                self.conn.wfile.write(msg)
            except socket.error as ex:
                if ex.args[0] not in errors.socket_errors_to_ignore:
                    raise
        return True

    def respond(self):
        """Call the gateway and write its iterable output."""
        mrbs = self.server.max_request_body_size
        if self.chunked_read:
            self.rfile = ChunkedRFile(self.conn.rfile, mrbs)
        else:
            cl = int(self.inheaders.get(b'Content-Length', 0))
            if mrbs and mrbs < cl:
                if not self.sent_headers:
                    self.simple_response(
                        '413 Request Entity Too Large',
                        'The entity sent with the request exceeds the '
                        'maximum allowed bytes.',
                    )
                return
            self.rfile = KnownLengthRFile(self.conn.rfile, cl)

        self.server.gateway(self).respond()
        self.ready and self.ensure_headers_sent()

        if self.chunked_write:
            self.conn.wfile.write(b'0\r\n\r\n')

    def simple_response(self, status, msg=''):
        """Write a simple response back to the client."""
        status = str(status)
        proto_status = '%s %s\r\n' % (self.server.protocol, status)
        content_length = 'Content-Length: %s\r\n' % len(msg)
        content_type = 'Content-Type: text/plain\r\n'
        buf = [
            proto_status.encode('ISO-8859-1'),
            content_length.encode('ISO-8859-1'),
            content_type.encode('ISO-8859-1'),
        ]

        if status[:3] in ('413', '414'):
            # Request Entity Too Large / Request-URI Too Long
            self.close_connection = True
            if self.response_protocol == 'HTTP/1.1':
                # This will not be true for 414, since read_request_line
                # usually raises 414 before reading the whole line, and we
                # therefore cannot know the proper response_protocol.
                buf.append(b'Connection: close\r\n')
            else:
                # HTTP/1.0 had no 413/414 status nor Connection header.
                # Emit 400 instead and trust the message body is enough.
                status = '400 Bad Request'

        buf.append(CRLF)
        if msg:
            if isinstance(msg, str):
                msg = msg.encode('ISO-8859-1')
            buf.append(msg)

        try:
            self.conn.wfile.write(EMPTY.join(buf))
        except socket.error as ex:
            if ex.args[0] not in errors.socket_errors_to_ignore:
                raise

    def ensure_headers_sent(self):
        """Ensure headers are sent to the client if not already sent."""
        if not self.sent_headers:
            self.sent_headers = True
            self.send_headers()

    def write(self, chunk):
        """Write unbuffered data to the client."""
        if self.chunked_write and chunk:
            chunk_size_hex = hex(len(chunk))[2:].encode('ascii')
            buf = [chunk_size_hex, CRLF, chunk, CRLF]
            self.conn.wfile.write(EMPTY.join(buf))
        else:
            self.conn.wfile.write(chunk)

    def send_headers(self):  # noqa: C901  # FIXME
        """Assert, process, and send the HTTP response message-headers.

        You must set ``self.status``, and :py:attr:`self.outheaders
        <HTTPRequest.outheaders>` before calling this.
        """
        hkeys = [key.lower() for key, value in self.outheaders]
        status = int(self.status[:3])

        if status == 413:
            # Request Entity Too Large. Close conn to avoid garbage.
            self.close_connection = True
        elif b'content-length' not in hkeys:
            # "All 1xx (informational), 204 (no content),
            # and 304 (not modified) responses MUST NOT
            # include a message-body." So no point chunking.
            if status < 200 or status in (204, 205, 304):
                pass
            else:
                needs_chunked = (
                    self.response_protocol == 'HTTP/1.1'
                    and self.method != b'HEAD'
                )
                if needs_chunked:
                    # Use the chunked transfer-coding
                    self.chunked_write = True
                    self.outheaders.append((b'Transfer-Encoding', b'chunked'))
                else:
                    # Closing the conn is the only way to determine len.
                    self.close_connection = True

        # Override the decision to not close the connection if the connection
        # manager doesn't have space for it.
        if not self.close_connection:
            can_keep = self.server.can_add_keepalive_connection
            self.close_connection = not can_keep

        if b'connection' not in hkeys:
            if self.response_protocol == 'HTTP/1.1':
                # Both server and client are HTTP/1.1 or better
                if self.close_connection:
                    self.outheaders.append((b'Connection', b'close'))
            else:
                # Server and/or client are HTTP/1.0
                if not self.close_connection:
                    self.outheaders.append((b'Connection', b'Keep-Alive'))

        if (b'Connection', b'Keep-Alive') in self.outheaders:
            self.outheaders.append((
                b'Keep-Alive',
                u'timeout={connection_timeout}'.
                format(connection_timeout=self.server.timeout).
                encode('ISO-8859-1'),
            ))

        if (not self.close_connection) and (not self.chunked_read):
            # Read any remaining request body data on the socket.
            # "If an origin server receives a request that does not include an
            # Expect request-header field with the "100-continue" expectation,
            # the request includes a request body, and the server responds
            # with a final status code before reading the entire request body
            # from the transport connection, then the server SHOULD NOT close
            # the transport connection until it has read the entire request,
            # or until the client closes the connection. Otherwise, the client
            # might not reliably receive the response message. However, this
            # requirement is not be construed as preventing a server from
            # defending itself against denial-of-service attacks, or from
            # badly broken client implementations."
            remaining = getattr(self.rfile, 'remaining', 0)
            if remaining > 0:
                self.rfile.read(remaining)

        if b'date' not in hkeys:
            self.outheaders.append((
                b'Date',
                email.utils.formatdate(usegmt=True).encode('ISO-8859-1'),
            ))

        if b'server' not in hkeys:
            self.outheaders.append((
                b'Server',
                self.server.server_name.encode('ISO-8859-1'),
            ))

        proto = self.server.protocol.encode('ascii')
        buf = [proto + SPACE + self.status + CRLF]
        for k, v in self.outheaders:
            buf.append(k + COLON + SPACE + v + CRLF)
        buf.append(CRLF)
        self.conn.wfile.write(EMPTY.join(buf))


class HTTPConnection:
    """An HTTP connection (active socket)."""

    remote_addr = None
    remote_port = None
    ssl_env = None
    rbufsize = io.DEFAULT_BUFFER_SIZE
    wbufsize = io.DEFAULT_BUFFER_SIZE
    RequestHandlerClass = HTTPRequest
    peercreds_enabled = False
    peercreds_resolve_enabled = False

    # Fields set by ConnectionManager.
    last_used = None

    def __init__(self, server, sock, makefile=MakeFile):
        """Initialize HTTPConnection instance.

        Args:
            server (HTTPServer): web server object receiving this request
            sock (socket._socketobject): the raw socket object (usually
                TCP) for this connection
            makefile (file): a fileobject class for reading from the socket
        """
        self.server = server
        self.socket = sock
        self.rfile = makefile(sock, 'rb', self.rbufsize)
        self.wfile = makefile(sock, 'wb', self.wbufsize)
        self.requests_seen = 0

        self.peercreds_enabled = self.server.peercreds_enabled
        self.peercreds_resolve_enabled = self.server.peercreds_resolve_enabled

        # LRU cached methods:
        # Ref: https://stackoverflow.com/a/14946506/595220
        self.resolve_peer_creds = (
            lru_cache(maxsize=1)(self.resolve_peer_creds)
        )
        self.get_peer_creds = (
            lru_cache(maxsize=1)(self.get_peer_creds)
        )

    def communicate(self):  # noqa: C901  # FIXME
        """Read each request and respond appropriately.

        Returns true if the connection should be kept open.
        """
        request_seen = False
        try:
            req = self.RequestHandlerClass(self.server, self)
            req.parse_request()
            if self.server.stats['Enabled']:
                self.requests_seen += 1
            if not req.ready:
                # Something went wrong in the parsing (and the server has
                # probably already made a simple_response). Return and
                # let the conn close.
                return False

            request_seen = True
            req.respond()
            if not req.close_connection:
                return True
        except socket.error as ex:
            errnum = ex.args[0]
            # sadly SSL sockets return a different (longer) time out string
            timeout_errs = 'timed out', 'The read operation timed out'
            if errnum in timeout_errs:
                # Don't error if we're between requests; only error
                # if 1) no request has been started at all, or 2) we're
                # in the middle of a request.
                # See https://github.com/cherrypy/cherrypy/issues/853
                if (not request_seen) or (req and req.started_request):
                    self._conditional_error(req, '408 Request Timeout')
            elif errnum not in errors.socket_errors_to_ignore:
                self.server.error_log(
                    'socket.error %s' % repr(errnum),
                    level=logging.WARNING, traceback=True,
                )
                self._conditional_error(req, '500 Internal Server Error')
        except (KeyboardInterrupt, SystemExit):
            raise
        except errors.FatalSSLAlert:
            pass
        except errors.NoSSLError:
            self._handle_no_ssl(req)
        except Exception as ex:
            self.server.error_log(
                repr(ex), level=logging.ERROR, traceback=True,
            )
            self._conditional_error(req, '500 Internal Server Error')
        return False

    linger = False

    def _handle_no_ssl(self, req):
        if not req or req.sent_headers:
            return
        # Unwrap wfile
        try:
            resp_sock = self.socket._sock
        except AttributeError:
            # self.socket is of OpenSSL.SSL.Connection type
            resp_sock = self.socket._socket
        self.wfile = StreamWriter(resp_sock, 'wb', self.wbufsize)
        msg = (
            'The client sent a plain HTTP request, but '
            'this server only speaks HTTPS on this port.'
        )
        req.simple_response('400 Bad Request', msg)
        self.linger = True

    def _conditional_error(self, req, response):
        """Respond with an error.

        Don't bother writing if a response
        has already started being written.
        """
        if not req or req.sent_headers:
            return

        try:
            req.simple_response(response)
        except errors.FatalSSLAlert:
            pass
        except errors.NoSSLError:
            self._handle_no_ssl(req)

    def close(self):
        """Close the socket underlying this connection."""
        self.rfile.close()

        if not self.linger:
            self._close_kernel_socket()
            # close the socket file descriptor
            # (will be closed in the OS if there is no
            # other reference to the underlying socket)
            self.socket.close()
        else:
            # On the other hand, sometimes we want to hang around for a bit
            # to make sure the client has a chance to read our entire
            # response. Skipping the close() calls here delays the FIN
            # packet until the socket object is garbage-collected later.
            # Someday, perhaps, we'll do the full lingering_close that
            # Apache does, but not today.
            pass

    def get_peer_creds(self):  # LRU cached on per-instance basis, see __init__
        """Return the PID/UID/GID tuple of the peer socket for UNIX sockets.

        This function uses SO_PEERCRED to query the UNIX PID, UID, GID
        of the peer, which is only available if the bind address is
        a UNIX domain socket.

        Raises:
            NotImplementedError: in case of unsupported socket type
            RuntimeError: in case of SO_PEERCRED lookup unsupported or disabled

        """
        PEERCRED_STRUCT_DEF = '3i'

        if IS_WINDOWS or self.socket.family != socket.AF_UNIX:
            raise NotImplementedError(
                'SO_PEERCRED is only supported in Linux kernel and WSL',
            )
        elif not self.peercreds_enabled:
            raise RuntimeError(
                'Peer creds lookup is disabled within this server',
            )

        try:
            peer_creds = self.socket.getsockopt(
                # FIXME: Use LOCAL_CREDS for BSD-like OSs
                # Ref: https://gist.github.com/LucaFilipozzi/e4f1e118202aff27af6aadebda1b5d91  # noqa
                socket.SOL_SOCKET, socket.SO_PEERCRED,
                struct.calcsize(PEERCRED_STRUCT_DEF),
            )
        except socket.error as socket_err:
            """Non-Linux kernels don't support SO_PEERCRED.

            Refs:
            http://welz.org.za/notes/on-peer-cred.html
            https://github.com/daveti/tcpSockHack
            msdn.microsoft.com/en-us/commandline/wsl/release_notes#build-15025
            """
            raise RuntimeError from socket_err
        else:
            pid, uid, gid = struct.unpack(PEERCRED_STRUCT_DEF, peer_creds)
            return pid, uid, gid

    @property
    def peer_pid(self):
        """Return the id of the connected peer process."""
        pid, _, _ = self.get_peer_creds()
        return pid

    @property
    def peer_uid(self):
        """Return the user id of the connected peer process."""
        _, uid, _ = self.get_peer_creds()
        return uid

    @property
    def peer_gid(self):
        """Return the group id of the connected peer process."""
        _, _, gid = self.get_peer_creds()
        return gid

    def resolve_peer_creds(self):  # LRU cached on per-instance basis
        """Look up the username and group tuple of the ``PEERCREDS``.

        :returns: the username and group tuple of the ``PEERCREDS``

        :raises NotImplementedError: if the OS is unsupported
        :raises RuntimeError: if UID/GID lookup is unsupported or disabled
        """
        if not IS_UID_GID_RESOLVABLE:
            raise NotImplementedError(
                'UID/GID lookup is unavailable under current platform. '
                'It can only be done under UNIX-like OS '
                'but not under the Google App Engine',
            )
        elif not self.peercreds_resolve_enabled:
            raise RuntimeError(
                'UID/GID lookup is disabled within this server',
            )

        user = pwd.getpwuid(self.peer_uid).pw_name  # [0]
        group = grp.getgrgid(self.peer_gid).gr_name  # [0]

        return user, group

    @property
    def peer_user(self):
        """Return the username of the connected peer process."""
        user, _ = self.resolve_peer_creds()
        return user

    @property
    def peer_group(self):
        """Return the group of the connected peer process."""
        _, group = self.resolve_peer_creds()
        return group

    def _close_kernel_socket(self):
        """Terminate the connection at the transport level."""
        # Honor ``sock_shutdown`` for PyOpenSSL connections.
        shutdown = getattr(
            self.socket, 'sock_shutdown',
            self.socket.shutdown,
        )

        try:
            shutdown(socket.SHUT_RDWR)  # actually send a TCP FIN
        except errors.acceptable_sock_shutdown_exceptions:
            pass
        except socket.error as e:
            if e.errno not in errors.acceptable_sock_shutdown_error_codes:
                raise


class HTTPServer:
    """An HTTP server."""

    _bind_addr = '127.0.0.1'
    _interrupt = None

    gateway = None
    """A Gateway instance."""

    minthreads = None
    """The minimum number of worker threads to create (default 10)."""

    maxthreads = None
    """The maximum number of worker threads to create.

    (default -1 = no limit)"""

    server_name = None
    """The name of the server; defaults to ``self.version``."""

    protocol = 'HTTP/1.1'
    """The version string to write in the Status-Line of all HTTP responses.

    For example, "HTTP/1.1" is the default. This also limits the supported
    features used in the response."""

    request_queue_size = 5
    """The 'backlog' arg to socket.listen(); max queued connections.

    (default 5)."""

    shutdown_timeout = 5
    """The total time to wait for worker threads to cleanly exit.

    Specified in seconds."""

    timeout = 10
    """The timeout in seconds for accepted connections (default 10)."""

    expiration_interval = 0.5
    """The interval, in seconds, at which the server checks for
    expired connections (default 0.5).
    """

    version = 'Cheroot/{version!s}'.format(version=__version__)
    """A version string for the HTTPServer."""

    software = None
    """The value to set for the SERVER_SOFTWARE entry in the WSGI environ.

    If None, this defaults to ``'%s Server' % self.version``.
    """

    ready = False
    """Internal flag which indicating the socket is accepting connections."""

    max_request_header_size = 0
    """The maximum size, in bytes, for request headers, or 0 for no limit."""

    max_request_body_size = 0
    """The maximum size, in bytes, for request bodies, or 0 for no limit."""

    nodelay = True
    """If True (the default since 3.1), sets the TCP_NODELAY socket option."""

    ConnectionClass = HTTPConnection
    """The class to use for handling HTTP connections."""

    ssl_adapter = None
    """An instance of ``ssl.Adapter`` (or a subclass).

    Ref: :py:class:`ssl.Adapter <cheroot.ssl.Adapter>`.

    You must have the corresponding TLS driver library installed.
    """

    peercreds_enabled = False
    """
    If :py:data:`True`, peer creds will be looked up via UNIX domain socket.
    """

    peercreds_resolve_enabled = False
    """
    If :py:data:`True`, username/group will be looked up in the OS from
    ``PEERCREDS``-provided IDs.
    """

    reuse_port = False
    """If True, set SO_REUSEPORT on the socket."""

    keep_alive_conn_limit = 10
    """Maximum number of waiting keep-alive connections that will be kept open.

    Default is 10. Set to None to have unlimited connections."""

    def __init__(
        self, bind_addr, gateway,
        minthreads=10, maxthreads=-1, server_name=None,
        peercreds_enabled=False, peercreds_resolve_enabled=False,
        reuse_port=False,
    ):
        """Initialize HTTPServer instance.

        Args:
            bind_addr (tuple): network interface to listen to
            gateway (Gateway): gateway for processing HTTP requests
            minthreads (int): minimum number of threads for HTTP thread pool
            maxthreads (int): maximum number of threads for HTTP thread pool
            server_name (str): web server name to be advertised via Server
                HTTP header
            reuse_port (bool): if True SO_REUSEPORT option would be set to
                socket
        """
        self.bind_addr = bind_addr
        self.gateway = gateway

        self.requests = threadpool.ThreadPool(
            self, min=minthreads or 1, max=maxthreads,
        )

        if not server_name:
            server_name = self.version
        self.server_name = server_name
        self.peercreds_enabled = peercreds_enabled
        self.peercreds_resolve_enabled = (
            peercreds_resolve_enabled and peercreds_enabled
        )
        self.reuse_port = reuse_port
        self.clear_stats()

    def clear_stats(self):
        """Reset server stat counters.."""
        self._start_time = None
        self._run_time = 0
        self.stats = {
            'Enabled': False,
            'Bind Address': lambda s: repr(self.bind_addr),
            'Run time': lambda s: (not s['Enabled']) and -1 or self.runtime(),
            'Accepts': 0,
            'Accepts/sec': lambda s: s['Accepts'] / self.runtime(),
            'Queue': lambda s: getattr(self.requests, 'qsize', None),
            'Threads': lambda s: len(getattr(self.requests, '_threads', [])),
            'Threads Idle': lambda s: getattr(self.requests, 'idle', None),
            'Socket Errors': 0,
            'Requests': lambda s: (not s['Enabled']) and -1 or sum(
                (w['Requests'](w) for w in s['Worker Threads'].values()), 0,
            ),
            'Bytes Read': lambda s: (not s['Enabled']) and -1 or sum(
                (w['Bytes Read'](w) for w in s['Worker Threads'].values()), 0,
            ),
            'Bytes Written': lambda s: (not s['Enabled']) and -1 or sum(
                (w['Bytes Written'](w) for w in s['Worker Threads'].values()),
                0,
            ),
            'Work Time': lambda s: (not s['Enabled']) and -1 or sum(
                (w['Work Time'](w) for w in s['Worker Threads'].values()), 0,
            ),
            'Read Throughput': lambda s: (not s['Enabled']) and -1 or sum(
                (
                    w['Bytes Read'](w) / (w['Work Time'](w) or 1e-6)
                    for w in s['Worker Threads'].values()
                ), 0,
            ),
            'Write Throughput': lambda s: (not s['Enabled']) and -1 or sum(
                (
                    w['Bytes Written'](w) / (w['Work Time'](w) or 1e-6)
                    for w in s['Worker Threads'].values()
                ), 0,
            ),
            'Worker Threads': {},
        }
        logging.statistics['Cheroot HTTPServer %d' % id(self)] = self.stats

    def runtime(self):
        """Return server uptime."""
        if self._start_time is None:
            return self._run_time
        else:
            return self._run_time + (time.time() - self._start_time)

    def __str__(self):
        """Render Server instance representing bind address."""
        return '%s.%s(%r)' % (
            self.__module__, self.__class__.__name__,
            self.bind_addr,
        )

    @property
    def bind_addr(self):
        """Return the interface on which to listen for connections.

        For TCP sockets, a (host, port) tuple. Host values may be any
        :term:`IPv4` or :term:`IPv6` address, or any valid hostname.
        The string 'localhost' is a synonym for '127.0.0.1' (or '::1',
        if your hosts file prefers :term:`IPv6`).
        The string '0.0.0.0' is a special :term:`IPv4` entry meaning
        "any active interface" (INADDR_ANY), and '::' is the similar
        IN6ADDR_ANY for :term:`IPv6`.
        The empty string or :py:data:`None` are not allowed.

        For UNIX sockets, supply the file name as a string.

        Systemd socket activation is automatic and doesn't require tempering
        with this variable.

        .. glossary::

           :abbr:`IPv4 (Internet Protocol version 4)`
              Internet Protocol version 4

           :abbr:`IPv6 (Internet Protocol version 6)`
              Internet Protocol version 6
        """
        return self._bind_addr

    @bind_addr.setter
    def bind_addr(self, value):
        """Set the interface on which to listen for connections."""
        if isinstance(value, tuple) and value[0] in ('', None):
            # Despite the socket module docs, using '' does not
            # allow AI_PASSIVE to work. Passing None instead
            # returns '0.0.0.0' like we want. In other words:
            #     host    AI_PASSIVE     result
            #      ''         Y         192.168.x.y
            #      ''         N         192.168.x.y
            #     None        Y         0.0.0.0
            #     None        N         127.0.0.1
            # But since you can get the same effect with an explicit
            # '0.0.0.0', we deny both the empty string and None as values.
            raise ValueError(
                "Host values of '' or None are not allowed. "
                "Use '0.0.0.0' (IPv4) or '::' (IPv6) instead "
                'to listen on all active interfaces.',
            )
        self._bind_addr = value

    def safe_start(self):
        """Run the server forever, and stop it cleanly on exit."""
        try:
            self.start()
        except KeyboardInterrupt as kb_intr_exc:
            underlying_interrupt = self.interrupt
            if not underlying_interrupt:
                self.interrupt = kb_intr_exc
            raise kb_intr_exc from underlying_interrupt
        except SystemExit as sys_exit_exc:
            underlying_interrupt = self.interrupt
            if not underlying_interrupt:
                self.interrupt = sys_exit_exc
            raise sys_exit_exc from underlying_interrupt

    def prepare(self):  # noqa: C901  # FIXME
        """Prepare server to serving requests.

        It binds a socket's port, setups the socket to ``listen()`` and does
        other preparing things.
        """
        self._interrupt = None

        if self.software is None:
            self.software = '%s Server' % self.version

        # Select the appropriate socket
        self.socket = None
        msg = 'No socket could be created'
        if os.getenv('LISTEN_PID', None):
            # systemd socket activation
            self.socket = socket.fromfd(3, socket.AF_INET, socket.SOCK_STREAM)
        elif isinstance(self.bind_addr, (str, bytes)):
            # AF_UNIX socket
            try:
                self.bind_unix_socket(self.bind_addr)
            except socket.error as serr:
                msg = '%s -- (%s: %s)' % (msg, self.bind_addr, serr)
                raise socket.error(msg) from serr
        else:
            # AF_INET or AF_INET6 socket
            # Get the correct address family for our host (allows IPv6
            # addresses)
            host, port = self.bind_addr
            try:
                info = socket.getaddrinfo(
                    host, port, socket.AF_UNSPEC,
                    socket.SOCK_STREAM, 0, socket.AI_PASSIVE,
                )
            except socket.gaierror:
                sock_type = socket.AF_INET
                bind_addr = self.bind_addr

                if ':' in host:
                    sock_type = socket.AF_INET6
                    bind_addr = bind_addr + (0, 0)

                info = [(sock_type, socket.SOCK_STREAM, 0, '', bind_addr)]

            for res in info:
                af, socktype, proto, _canonname, sa = res
                try:
                    self.bind(af, socktype, proto)
                    break
                except socket.error as serr:
                    msg = '%s -- (%s: %s)' % (msg, sa, serr)
                    if self.socket:
                        self.socket.close()
                    self.socket = None

        if not self.socket:
            raise socket.error(msg)

        # Timeout so KeyboardInterrupt can be caught on Win32
        self.socket.settimeout(1)
        self.socket.listen(self.request_queue_size)

        # must not be accessed once stop() has been called
        self._connections = connections.ConnectionManager(self)

        # Create worker threads
        self.requests.start()

        self.ready = True
        self._start_time = time.time()

    def serve(self):
        """Serve requests, after invoking :func:`prepare()`."""
        while self.ready and not self.interrupt:
            try:
                self._connections.run(self.expiration_interval)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                self.error_log(
                    'Error in HTTPServer.serve', level=logging.ERROR,
                    traceback=True,
                )

        # raise exceptions reported by any worker threads,
        # such that the exception is raised from the serve() thread.
        if self.interrupt:
            while self._stopping_for_interrupt:
                time.sleep(0.1)
            if self.interrupt:
                raise self.interrupt

    def start(self):
        """Run the server forever.

        It is shortcut for invoking :func:`prepare()` then :func:`serve()`.
        """
        # We don't have to trap KeyboardInterrupt or SystemExit here,
        # because cherrypy.server already does so, calling self.stop() for us.
        # If you're using this server with another framework, you should
        # trap those exceptions in whatever code block calls start().
        self.prepare()
        self.serve()

    @contextlib.contextmanager
    def _run_in_thread(self):
        """Context manager for running this server in a thread."""
        self.prepare()
        thread = threading.Thread(target=self.serve)
        thread.daemon = True
        thread.start()
        try:
            yield thread
        finally:
            self.stop()

    @property
    def can_add_keepalive_connection(self):
        """Flag whether it is allowed to add a new keep-alive connection."""
        return self.ready and self._connections.can_add_keepalive_connection

    def put_conn(self, conn):
        """Put an idle connection back into the ConnectionManager."""
        if self.ready:
            self._connections.put(conn)
        else:
            # server is shutting down, just close it
            conn.close()

    def error_log(self, msg='', level=20, traceback=False):
        """Write error message to log.

        Args:
            msg (str): error message
            level (int): logging level
            traceback (bool): add traceback to output or not
        """
        # Override this in subclasses as desired
        sys.stderr.write('{msg!s}\n'.format(msg=msg))
        sys.stderr.flush()
        if traceback:
            tblines = traceback_.format_exc()
            sys.stderr.write(tblines)
            sys.stderr.flush()

    def bind(self, family, type, proto=0):
        """Create (or recreate) the actual socket object."""
        sock = self.prepare_socket(
            self.bind_addr,
            family, type, proto,
            self.nodelay, self.ssl_adapter,
            self.reuse_port,
        )
        sock = self.socket = self.bind_socket(sock, self.bind_addr)
        self.bind_addr = self.resolve_real_bind_addr(sock)
        return sock

    def bind_unix_socket(self, bind_addr):  # noqa: C901  # FIXME
        """Create (or recreate) a UNIX socket object."""
        if IS_WINDOWS:
            """
            Trying to access socket.AF_UNIX under Windows
            causes an AttributeError.
            """
            raise ValueError(  # or RuntimeError?
                'AF_UNIX sockets are not supported under Windows.',
            )

        fs_permissions = 0o777  # TODO: allow changing mode

        try:
            # Make possible reusing the socket...
            os.unlink(self.bind_addr)
        except OSError:
            """
            File does not exist, which is the primary goal anyway.
            """
        except TypeError as typ_err:
            err_msg = str(typ_err)
            if (
                    'remove() argument 1 must be encoded '
                    'string without null bytes, not unicode'
                    not in err_msg
            ):
                raise
        except ValueError as val_err:
            err_msg = str(val_err)
            if (
                    'unlink: embedded null '
                    'character in path' not in err_msg
                    and 'embedded null byte' not in err_msg
                    and 'argument must be a '
                    'string without NUL characters' not in err_msg  # pypy3
            ):
                raise

        sock = self.prepare_socket(
            bind_addr=bind_addr,
            family=socket.AF_UNIX, type=socket.SOCK_STREAM, proto=0,
            nodelay=self.nodelay, ssl_adapter=self.ssl_adapter,
            reuse_port=self.reuse_port,
        )

        try:
            """Linux way of pre-populating fs mode permissions."""
            # Allow everyone access the socket...
            os.fchmod(sock.fileno(), fs_permissions)
            FS_PERMS_SET = True
        except OSError:
            FS_PERMS_SET = False

        try:
            sock = self.bind_socket(sock, bind_addr)
        except socket.error:
            sock.close()
            raise

        bind_addr = self.resolve_real_bind_addr(sock)

        try:
            """FreeBSD/macOS pre-populating fs mode permissions."""
            if not FS_PERMS_SET:
                try:
                    os.lchmod(bind_addr, fs_permissions)
                except AttributeError:
                    os.chmod(bind_addr, fs_permissions, follow_symlinks=False)
                FS_PERMS_SET = True
        except OSError:
            pass

        if not FS_PERMS_SET:
            self.error_log(
                'Failed to set socket fs mode permissions',
                level=logging.WARNING,
            )

        self.bind_addr = bind_addr
        self.socket = sock
        return sock

    @staticmethod
    def _make_socket_reusable(socket_, bind_addr):
        host, port = bind_addr[:2]
        IS_EPHEMERAL_PORT = port == 0

        if socket_.family not in (socket.AF_INET, socket.AF_INET6):
            raise ValueError('Cannot reuse a non-IP socket')

        if IS_EPHEMERAL_PORT:
            raise ValueError('Cannot reuse an ephemeral port (0)')

        # Most BSD kernels implement SO_REUSEPORT the way that only the
        # latest listener can read from socket. Some of BSD kernels also
        # have SO_REUSEPORT_LB that works similarly to SO_REUSEPORT
        # in Linux.
        if hasattr(socket, 'SO_REUSEPORT_LB'):
            socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT_LB, 1)
        elif hasattr(socket, 'SO_REUSEPORT'):
            socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        elif IS_WINDOWS:
            socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        else:
            raise NotImplementedError(
                'Current platform does not support port reuse',
            )

    @classmethod
    def prepare_socket(
            cls, bind_addr, family, type, proto, nodelay, ssl_adapter,
            reuse_port=False,
    ):
        """Create and prepare the socket object."""
        sock = socket.socket(family, type, proto)
        connections.prevent_socket_inheritance(sock)

        host, port = bind_addr[:2]
        IS_EPHEMERAL_PORT = port == 0

        if reuse_port:
            cls._make_socket_reusable(socket_=sock, bind_addr=bind_addr)

        if not (IS_WINDOWS or IS_EPHEMERAL_PORT):
            """Enable SO_REUSEADDR for the current socket.

            Skip for Windows (has different semantics)
            or ephemeral ports (can steal ports from others).

            Refs:
            * https://msdn.microsoft.com/en-us/library/ms740621(v=vs.85).aspx
            * https://github.com/cherrypy/cheroot/issues/114
            * https://gavv.github.io/blog/ephemeral-port-reuse/
            """
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if nodelay and not isinstance(bind_addr, (str, bytes)):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if ssl_adapter is not None:
            sock = ssl_adapter.bind(sock)

        # If listening on the IPV6 any address ('::' = IN6ADDR_ANY),
        # activate dual-stack. See
        # https://github.com/cherrypy/cherrypy/issues/871.
        listening_ipv6 = (
            hasattr(socket, 'AF_INET6')
            and family == socket.AF_INET6
            and host in ('::', '::0', '::0.0.0.0')
        )
        if listening_ipv6:
            try:
                sock.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0,
                )
            except (AttributeError, socket.error):
                # Apparently, the socket option is not available in
                # this machine's TCP stack
                pass

        return sock

    @staticmethod
    def bind_socket(socket_, bind_addr):
        """Bind the socket to given interface."""
        socket_.bind(bind_addr)
        return socket_

    @staticmethod
    def resolve_real_bind_addr(socket_):
        """Retrieve actual bind address from bound socket."""
        # FIXME: keep requested bind_addr separate real bound_addr (port
        # is different in case of ephemeral port 0)
        bind_addr = socket_.getsockname()
        if socket_.family in (
            # Windows doesn't have socket.AF_UNIX, so not using it in check
            socket.AF_INET,
            socket.AF_INET6,
        ):
            """UNIX domain sockets are strings or bytes.

            In case of bytes with a leading null-byte it's an abstract socket.
            """
            return bind_addr[:2]

        if isinstance(bind_addr, bytes):
            bind_addr = bton(bind_addr)

        return bind_addr

    def process_conn(self, conn):
        """Process an incoming HTTPConnection."""
        try:
            self.requests.put(conn)
        except queue.Full:
            # Just drop the conn. TODO: write 503 back?
            conn.close()

    @property
    def interrupt(self):
        """Flag interrupt of the server."""
        return self._interrupt

    @property
    def _stopping_for_interrupt(self):
        """Return whether the server is responding to an interrupt."""
        return self._interrupt is _STOPPING_FOR_INTERRUPT

    @interrupt.setter
    def interrupt(self, interrupt):
        """Perform the shutdown of this server and save the exception.

        Typically invoked by a worker thread in
        :py:mod:`~cheroot.workers.threadpool`, the exception is raised
        from the thread running :py:meth:`serve` once :py:meth:`stop`
        has completed.
        """
        self._interrupt = _STOPPING_FOR_INTERRUPT

        if isinstance(interrupt, KeyboardInterrupt):
            self.error_log('Keyboard Interrupt: shutting down')

        if isinstance(interrupt, SystemExit):
            self.error_log('SystemExit raised: shutting down')

        self.stop()
        self._interrupt = interrupt

    def stop(self):  # noqa: C901  # FIXME
        """Gracefully shutdown a server that is serving forever."""
        if not self.ready:
            return  # already stopped

        self.ready = False
        if self._start_time is not None:
            self._run_time += (time.time() - self._start_time)
        self._start_time = None

        self._connections.stop()

        sock = getattr(self, 'socket', None)
        if sock:
            if not isinstance(self.bind_addr, (str, bytes)):
                # Touch our own socket to make accept() return immediately.
                try:
                    host, port = sock.getsockname()[:2]
                except socket.error as ex:
                    if ex.args[0] not in errors.socket_errors_to_ignore:
                        # Changed to use error code and not message
                        # See
                        # https://github.com/cherrypy/cherrypy/issues/860.
                        raise
                else:
                    # Note that we're explicitly NOT using AI_PASSIVE,
                    # here, because we want an actual IP to touch.
                    # localhost won't work if we've bound to a public IP,
                    # but it will if we bound to '0.0.0.0' (INADDR_ANY).
                    for res in socket.getaddrinfo(
                        host, port, socket.AF_UNSPEC,
                        socket.SOCK_STREAM,
                    ):
                        af, socktype, proto, _canonname, _sa = res
                        s = None
                        try:
                            s = socket.socket(af, socktype, proto)
                            # See
                            # https://groups.google.com/group/cherrypy-users/
                            #     browse_frm/thread/bbfe5eb39c904fe0
                            s.settimeout(1.0)
                            s.connect((host, port))
                            s.close()
                        except socket.error:
                            if s:
                                s.close()
            if hasattr(sock, 'close'):
                sock.close()
            self.socket = None

        self._connections.close()
        self.requests.stop(self.shutdown_timeout)


class Gateway:
    """Base class to interface HTTPServer with other systems, such as WSGI."""

    def __init__(self, req):
        """Initialize Gateway instance with request.

        Args:
            req (HTTPRequest): current HTTP request
        """
        self.req = req

    def respond(self):
        """Process the current request. Must be overridden in a subclass."""
        raise NotImplementedError  # pragma: no cover


# These may either be ssl.Adapter subclasses or the string names
# of such classes (in which case they will be lazily loaded).
ssl_adapters = {
    'builtin': 'cheroot.ssl.builtin.BuiltinSSLAdapter',
    'pyopenssl': 'cheroot.ssl.pyopenssl.pyOpenSSLAdapter',
}


def get_ssl_adapter_class(name='builtin'):
    """Return an SSL adapter class for the given name."""
    adapter = ssl_adapters[name.lower()]
    if isinstance(adapter, str):
        last_dot = adapter.rfind('.')
        attr_name = adapter[last_dot + 1:]
        mod_path = adapter[:last_dot]

        try:
            mod = sys.modules[mod_path]
            if mod is None:
                raise KeyError()
        except KeyError:
            # The last [''] is important.
            mod = __import__(mod_path, globals(), locals(), [''])

        # Let an AttributeError propagate outward.
        try:
            adapter = getattr(mod, attr_name)
        except AttributeError:
            raise AttributeError(
                "'%s' object has no attribute '%s'"
                % (mod_path, attr_name),
            )

    return adapter
