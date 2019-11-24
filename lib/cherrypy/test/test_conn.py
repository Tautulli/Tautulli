"""Tests for TCP connection handling, including proper and timely close."""

import errno
import socket
import sys
import time

import six
from six.moves import urllib
from six.moves.http_client import BadStatusLine, HTTPConnection, NotConnected

import pytest

from cheroot.test import webtest

import cherrypy
from cherrypy._cpcompat import HTTPSConnection, ntob, tonative
from cherrypy.test import helper


timeout = 1
pov = 'pPeErRsSiIsStTeEnNcCeE oOfF vViIsSiIoOnN'


def setup_server():

    def raise500():
        raise cherrypy.HTTPError(500)

    class Root:

        @cherrypy.expose
        def index(self):
            return pov
        page1 = index
        page2 = index
        page3 = index

        @cherrypy.expose
        def hello(self):
            return 'Hello, world!'

        @cherrypy.expose
        def timeout(self, t):
            return str(cherrypy.server.httpserver.timeout)

        @cherrypy.expose
        @cherrypy.config(**{'response.stream': True})
        def stream(self, set_cl=False):
            if set_cl:
                cherrypy.response.headers['Content-Length'] = 10

            def content():
                for x in range(10):
                    yield str(x)

            return content()

        @cherrypy.expose
        def error(self, code=500):
            raise cherrypy.HTTPError(code)

        @cherrypy.expose
        def upload(self):
            if not cherrypy.request.method == 'POST':
                raise AssertionError("'POST' != request.method %r" %
                                     cherrypy.request.method)
            return "thanks for '%s'" % cherrypy.request.body.read()

        @cherrypy.expose
        def custom(self, response_code):
            cherrypy.response.status = response_code
            return 'Code = %s' % response_code

        @cherrypy.expose
        @cherrypy.config(**{'hooks.on_start_resource': raise500})
        def err_before_read(self):
            return 'ok'

        @cherrypy.expose
        def one_megabyte_of_a(self):
            return ['a' * 1024] * 1024

        @cherrypy.expose
        # Turn off the encoding tool so it doens't collapse
        # our response body and reclaculate the Content-Length.
        @cherrypy.config(**{'tools.encode.on': False})
        def custom_cl(self, body, cl):
            cherrypy.response.headers['Content-Length'] = cl
            if not isinstance(body, list):
                body = [body]
            newbody = []
            for chunk in body:
                if isinstance(chunk, six.text_type):
                    chunk = chunk.encode('ISO-8859-1')
                newbody.append(chunk)
            return newbody

    cherrypy.tree.mount(Root())
    cherrypy.config.update({
        'server.max_request_body_size': 1001,
        'server.socket_timeout': timeout,
    })


class ConnectionCloseTests(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def test_HTTP11(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        self.persistent = True

        # Make the first request and assert there's no "Connection: close".
        self.getPage('/')
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader('Connection')

        # Make another request on the same connection.
        self.getPage('/page1')
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader('Connection')

        # Test client-side close.
        self.getPage('/page2', headers=[('Connection', 'close')])
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertHeader('Connection', 'close')

        # Make another request on the same connection, which should error.
        self.assertRaises(NotConnected, self.getPage, '/')

    def test_Streaming_no_len(self):
        try:
            self._streaming(set_cl=False)
        finally:
            try:
                self.HTTP_CONN.close()
            except (TypeError, AttributeError):
                pass

    def test_Streaming_with_len(self):
        try:
            self._streaming(set_cl=True)
        finally:
            try:
                self.HTTP_CONN.close()
            except (TypeError, AttributeError):
                pass

    def _streaming(self, set_cl):
        if cherrypy.server.protocol_version == 'HTTP/1.1':
            self.PROTOCOL = 'HTTP/1.1'

            self.persistent = True

            # Make the first request and assert there's no "Connection: close".
            self.getPage('/')
            self.assertStatus('200 OK')
            self.assertBody(pov)
            self.assertNoHeader('Connection')

            # Make another, streamed request on the same connection.
            if set_cl:
                # When a Content-Length is provided, the content should stream
                # without closing the connection.
                self.getPage('/stream?set_cl=Yes')
                self.assertHeader('Content-Length')
                self.assertNoHeader('Connection', 'close')
                self.assertNoHeader('Transfer-Encoding')

                self.assertStatus('200 OK')
                self.assertBody('0123456789')
            else:
                # When no Content-Length response header is provided,
                # streamed output will either close the connection, or use
                # chunked encoding, to determine transfer-length.
                self.getPage('/stream')
                self.assertNoHeader('Content-Length')
                self.assertStatus('200 OK')
                self.assertBody('0123456789')

                chunked_response = False
                for k, v in self.headers:
                    if k.lower() == 'transfer-encoding':
                        if str(v) == 'chunked':
                            chunked_response = True

                if chunked_response:
                    self.assertNoHeader('Connection', 'close')
                else:
                    self.assertHeader('Connection', 'close')

                    # Make another request on the same connection, which should
                    # error.
                    self.assertRaises(NotConnected, self.getPage, '/')

                # Try HEAD. See
                # https://github.com/cherrypy/cherrypy/issues/864.
                self.getPage('/stream', method='HEAD')
                self.assertStatus('200 OK')
                self.assertBody('')
                self.assertNoHeader('Transfer-Encoding')
        else:
            self.PROTOCOL = 'HTTP/1.0'

            self.persistent = True

            # Make the first request and assert Keep-Alive.
            self.getPage('/', headers=[('Connection', 'Keep-Alive')])
            self.assertStatus('200 OK')
            self.assertBody(pov)
            self.assertHeader('Connection', 'Keep-Alive')

            # Make another, streamed request on the same connection.
            if set_cl:
                # When a Content-Length is provided, the content should
                # stream without closing the connection.
                self.getPage('/stream?set_cl=Yes',
                             headers=[('Connection', 'Keep-Alive')])
                self.assertHeader('Content-Length')
                self.assertHeader('Connection', 'Keep-Alive')
                self.assertNoHeader('Transfer-Encoding')
                self.assertStatus('200 OK')
                self.assertBody('0123456789')
            else:
                # When a Content-Length is not provided,
                # the server should close the connection.
                self.getPage('/stream', headers=[('Connection', 'Keep-Alive')])
                self.assertStatus('200 OK')
                self.assertBody('0123456789')

                self.assertNoHeader('Content-Length')
                self.assertNoHeader('Connection', 'Keep-Alive')
                self.assertNoHeader('Transfer-Encoding')

                # Make another request on the same connection, which should
                # error.
                self.assertRaises(NotConnected, self.getPage, '/')

    def test_HTTP10_KeepAlive(self):
        self.PROTOCOL = 'HTTP/1.0'
        if self.scheme == 'https':
            self.HTTP_CONN = HTTPSConnection
        else:
            self.HTTP_CONN = HTTPConnection

        # Test a normal HTTP/1.0 request.
        self.getPage('/page2')
        self.assertStatus('200 OK')
        self.assertBody(pov)
        # Apache, for example, may emit a Connection header even for HTTP/1.0
        # self.assertNoHeader("Connection")

        # Test a keep-alive HTTP/1.0 request.
        self.persistent = True

        self.getPage('/page3', headers=[('Connection', 'Keep-Alive')])
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertHeader('Connection', 'Keep-Alive')

        # Remove the keep-alive header again.
        self.getPage('/page3')
        self.assertStatus('200 OK')
        self.assertBody(pov)
        # Apache, for example, may emit a Connection header even for HTTP/1.0
        # self.assertNoHeader("Connection")


class PipelineTests(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def test_HTTP11_Timeout(self):
        # If we timeout without sending any data,
        # the server will close the conn with a 408.
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        # Connect but send nothing.
        self.persistent = True
        conn = self.HTTP_CONN
        conn.auto_open = False
        conn.connect()

        # Wait for our socket timeout
        time.sleep(timeout * 2)

        # The request should have returned 408 already.
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 408)
        conn.close()

        # Connect but send half the headers only.
        self.persistent = True
        conn = self.HTTP_CONN
        conn.auto_open = False
        conn.connect()
        conn.send(b'GET /hello HTTP/1.1')
        conn.send(('Host: %s' % self.HOST).encode('ascii'))

        # Wait for our socket timeout
        time.sleep(timeout * 2)

        # The conn should have already sent 408.
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 408)
        conn.close()

    def test_HTTP11_Timeout_after_request(self):
        # If we timeout after at least one request has succeeded,
        # the server will close the conn without 408.
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        # Make an initial request
        self.persistent = True
        conn = self.HTTP_CONN
        conn.putrequest('GET', '/timeout?t=%s' % timeout, skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 200)
        self.body = response.read()
        self.assertBody(str(timeout))

        # Make a second request on the same socket
        conn._output(b'GET /hello HTTP/1.1')
        conn._output(ntob('Host: %s' % self.HOST, 'ascii'))
        conn._send_output()
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 200)
        self.body = response.read()
        self.assertBody('Hello, world!')

        # Wait for our socket timeout
        time.sleep(timeout * 2)

        # Make another request on the same socket, which should error
        conn._output(b'GET /hello HTTP/1.1')
        conn._output(ntob('Host: %s' % self.HOST, 'ascii'))
        conn._send_output()
        response = conn.response_class(conn.sock, method='GET')
        try:
            response.begin()
        except Exception:
            if not isinstance(sys.exc_info()[1],
                              (socket.error, BadStatusLine)):
                self.fail("Writing to timed out socket didn't fail"
                          ' as it should have: %s' % sys.exc_info()[1])
        else:
            if response.status != 408:
                self.fail("Writing to timed out socket didn't fail"
                          ' as it should have: %s' %
                          response.read())

        conn.close()

        # Make another request on a new socket, which should work
        self.persistent = True
        conn = self.HTTP_CONN
        conn.putrequest('GET', '/', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 200)
        self.body = response.read()
        self.assertBody(pov)

        # Make another request on the same socket,
        # but timeout on the headers
        conn.send(b'GET /hello HTTP/1.1')
        # Wait for our socket timeout
        time.sleep(timeout * 2)
        response = conn.response_class(conn.sock, method='GET')
        try:
            response.begin()
        except Exception:
            if not isinstance(sys.exc_info()[1],
                              (socket.error, BadStatusLine)):
                self.fail("Writing to timed out socket didn't fail"
                          ' as it should have: %s' % sys.exc_info()[1])
        else:
            self.fail("Writing to timed out socket didn't fail"
                      ' as it should have: %s' %
                      response.read())

        conn.close()

        # Retry the request on a new connection, which should work
        self.persistent = True
        conn = self.HTTP_CONN
        conn.putrequest('GET', '/', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.assertEqual(response.status, 200)
        self.body = response.read()
        self.assertBody(pov)
        conn.close()

    def test_HTTP11_pipelining(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        # Test pipelining. httplib doesn't support this directly.
        self.persistent = True
        conn = self.HTTP_CONN

        # Put request 1
        conn.putrequest('GET', '/hello', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()

        for trial in range(5):
            # Put next request
            conn._output(b'GET /hello HTTP/1.1')
            conn._output(ntob('Host: %s' % self.HOST, 'ascii'))
            conn._send_output()

            # Retrieve previous response
            response = conn.response_class(conn.sock, method='GET')
            # there is a bug in python3 regarding the buffering of
            # ``conn.sock``. Until that bug get's fixed we will
            # monkey patch the ``response`` instance.
            # https://bugs.python.org/issue23377
            if six.PY3:
                response.fp = conn.sock.makefile('rb', 0)
            response.begin()
            body = response.read(13)
            self.assertEqual(response.status, 200)
            self.assertEqual(body, b'Hello, world!')

        # Retrieve final response
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        body = response.read()
        self.assertEqual(response.status, 200)
        self.assertEqual(body, b'Hello, world!')

        conn.close()

    def test_100_Continue(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        self.persistent = True
        conn = self.HTTP_CONN

        # Try a page without an Expect request header first.
        # Note that httplib's response.begin automatically ignores
        # 100 Continue responses, so we must manually check for it.
        try:
            conn.putrequest('POST', '/upload', skip_host=True)
            conn.putheader('Host', self.HOST)
            conn.putheader('Content-Type', 'text/plain')
            conn.putheader('Content-Length', '4')
            conn.endheaders()
            conn.send(ntob("d'oh"))
            response = conn.response_class(conn.sock, method='POST')
            version, status, reason = response._read_status()
            self.assertNotEqual(status, 100)
        finally:
            conn.close()

        # Now try a page with an Expect header...
        try:
            conn.connect()
            conn.putrequest('POST', '/upload', skip_host=True)
            conn.putheader('Host', self.HOST)
            conn.putheader('Content-Type', 'text/plain')
            conn.putheader('Content-Length', '17')
            conn.putheader('Expect', '100-continue')
            conn.endheaders()
            response = conn.response_class(conn.sock, method='POST')

            # ...assert and then skip the 100 response
            version, status, reason = response._read_status()
            self.assertEqual(status, 100)
            while True:
                line = response.fp.readline().strip()
                if line:
                    self.fail(
                        '100 Continue should not output any headers. Got %r' %
                        line)
                else:
                    break

            # ...send the body
            body = b'I am a small file'
            conn.send(body)

            # ...get the final response
            response.begin()
            self.status, self.headers, self.body = webtest.shb(response)
            self.assertStatus(200)
            self.assertBody("thanks for '%s'" % body)
        finally:
            conn.close()


class ConnectionTests(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def test_readall_or_close(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        if self.scheme == 'https':
            self.HTTP_CONN = HTTPSConnection
        else:
            self.HTTP_CONN = HTTPConnection

        # Test a max of 0 (the default) and then reset to what it was above.
        old_max = cherrypy.server.max_request_body_size
        for new_max in (0, old_max):
            cherrypy.server.max_request_body_size = new_max

            self.persistent = True
            conn = self.HTTP_CONN

            # Get a POST page with an error
            conn.putrequest('POST', '/err_before_read', skip_host=True)
            conn.putheader('Host', self.HOST)
            conn.putheader('Content-Type', 'text/plain')
            conn.putheader('Content-Length', '1000')
            conn.putheader('Expect', '100-continue')
            conn.endheaders()
            response = conn.response_class(conn.sock, method='POST')

            # ...assert and then skip the 100 response
            version, status, reason = response._read_status()
            self.assertEqual(status, 100)
            while True:
                skip = response.fp.readline().strip()
                if not skip:
                    break

            # ...send the body
            conn.send(ntob('x' * 1000))

            # ...get the final response
            response.begin()
            self.status, self.headers, self.body = webtest.shb(response)
            self.assertStatus(500)

            # Now try a working page with an Expect header...
            conn._output(b'POST /upload HTTP/1.1')
            conn._output(ntob('Host: %s' % self.HOST, 'ascii'))
            conn._output(b'Content-Type: text/plain')
            conn._output(b'Content-Length: 17')
            conn._output(b'Expect: 100-continue')
            conn._send_output()
            response = conn.response_class(conn.sock, method='POST')

            # ...assert and then skip the 100 response
            version, status, reason = response._read_status()
            self.assertEqual(status, 100)
            while True:
                skip = response.fp.readline().strip()
                if not skip:
                    break

            # ...send the body
            body = b'I am a small file'
            conn.send(body)

            # ...get the final response
            response.begin()
            self.status, self.headers, self.body = webtest.shb(response)
            self.assertStatus(200)
            self.assertBody("thanks for '%s'" % body)
            conn.close()

    def test_No_Message_Body(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        # Set our HTTP_CONN to an instance so it persists between requests.
        self.persistent = True

        # Make the first request and assert there's no "Connection: close".
        self.getPage('/')
        self.assertStatus('200 OK')
        self.assertBody(pov)
        self.assertNoHeader('Connection')

        # Make a 204 request on the same connection.
        self.getPage('/custom/204')
        self.assertStatus(204)
        self.assertNoHeader('Content-Length')
        self.assertBody('')
        self.assertNoHeader('Connection')

        # Make a 304 request on the same connection.
        self.getPage('/custom/304')
        self.assertStatus(304)
        self.assertNoHeader('Content-Length')
        self.assertBody('')
        self.assertNoHeader('Connection')

    def test_Chunked_Encoding(self):
        if cherrypy.server.protocol_version != 'HTTP/1.1':
            return self.skip()

        if (hasattr(self, 'harness') and
                'modpython' in self.harness.__class__.__name__.lower()):
            # mod_python forbids chunked encoding
            return self.skip()

        self.PROTOCOL = 'HTTP/1.1'

        # Set our HTTP_CONN to an instance so it persists between requests.
        self.persistent = True
        conn = self.HTTP_CONN

        # Try a normal chunked request (with extensions)
        body = ntob('8;key=value\r\nxx\r\nxxxx\r\n5\r\nyyyyy\r\n0\r\n'
                    'Content-Type: application/json\r\n'
                    '\r\n')
        conn.putrequest('POST', '/upload', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.putheader('Transfer-Encoding', 'chunked')
        conn.putheader('Trailer', 'Content-Type')
        # Note that this is somewhat malformed:
        # we shouldn't be sending Content-Length.
        # RFC 2616 says the server should ignore it.
        conn.putheader('Content-Length', '3')
        conn.endheaders()
        conn.send(body)
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus('200 OK')
        self.assertBody("thanks for '%s'" % b'xx\r\nxxxxyyyyy')

        # Try a chunked request that exceeds server.max_request_body_size.
        # Note that the delimiters and trailer are included.
        body = ntob('3e3\r\n' + ('x' * 995) + '\r\n0\r\n\r\n')
        conn.putrequest('POST', '/upload', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.putheader('Transfer-Encoding', 'chunked')
        conn.putheader('Content-Type', 'text/plain')
        # Chunked requests don't need a content-length
        # #        conn.putheader("Content-Length", len(body))
        conn.endheaders()
        conn.send(body)
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus(413)
        conn.close()

    def test_Content_Length_in(self):
        # Try a non-chunked request where Content-Length exceeds
        # server.max_request_body_size. Assert error before body send.
        self.persistent = True
        conn = self.HTTP_CONN
        conn.putrequest('POST', '/upload', skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.putheader('Content-Type', 'text/plain')
        conn.putheader('Content-Length', '9999')
        conn.endheaders()
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus(413)
        self.assertBody('The entity sent with the request exceeds '
                        'the maximum allowed bytes.')
        conn.close()

    def test_Content_Length_out_preheaders(self):
        # Try a non-chunked response where Content-Length is less than
        # the actual bytes in the response body.
        self.persistent = True
        conn = self.HTTP_CONN
        conn.putrequest('GET', '/custom_cl?body=I+have+too+many+bytes&cl=5',
                        skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus(500)
        self.assertBody(
            'The requested resource returned more bytes than the '
            'declared Content-Length.')
        conn.close()

    def test_Content_Length_out_postheaders(self):
        # Try a non-chunked response where Content-Length is less than
        # the actual bytes in the response body.
        self.persistent = True
        conn = self.HTTP_CONN
        conn.putrequest(
            'GET', '/custom_cl?body=I+too&body=+have+too+many&cl=5',
            skip_host=True)
        conn.putheader('Host', self.HOST)
        conn.endheaders()
        response = conn.getresponse()
        self.status, self.headers, self.body = webtest.shb(response)
        self.assertStatus(200)
        self.assertBody('I too')
        conn.close()

    def test_598(self):
        tmpl = '{scheme}://{host}:{port}/one_megabyte_of_a/'
        url = tmpl.format(
            scheme=self.scheme,
            host=self.HOST,
            port=self.PORT,
        )
        remote_data_conn = urllib.request.urlopen(url)
        buf = remote_data_conn.read(512)
        time.sleep(timeout * 0.6)
        remaining = (1024 * 1024) - 512
        while remaining:
            data = remote_data_conn.read(remaining)
            if not data:
                break
            else:
                buf += data
            remaining -= len(data)

        self.assertEqual(len(buf), 1024 * 1024)
        self.assertEqual(buf, ntob('a' * 1024 * 1024))
        self.assertEqual(remaining, 0)
        remote_data_conn.close()


def setup_upload_server():

    class Root:
        @cherrypy.expose
        def upload(self):
            if not cherrypy.request.method == 'POST':
                raise AssertionError("'POST' != request.method %r" %
                                     cherrypy.request.method)
            return "thanks for '%s'" % tonative(cherrypy.request.body.read())

    cherrypy.tree.mount(Root())
    cherrypy.config.update({
        'server.max_request_body_size': 1001,
        'server.socket_timeout': 10,
        'server.accepted_queue_size': 5,
        'server.accepted_queue_timeout': 0.1,
    })


reset_names = 'ECONNRESET', 'WSAECONNRESET'
socket_reset_errors = [
    getattr(errno, name)
    for name in reset_names
    if hasattr(errno, name)
]
'reset error numbers available on this platform'

socket_reset_errors += [
    # Python 3.5 raises an http.client.RemoteDisconnected
    # with this message
    'Remote end closed connection without response',
]


class LimitedRequestQueueTests(helper.CPWebCase):
    setup_server = staticmethod(setup_upload_server)

    @pytest.mark.xfail(reason='#1535')
    def test_queue_full(self):
        conns = []
        overflow_conn = None

        try:
            # Make 15 initial requests and leave them open, which should use
            # all of wsgiserver's WorkerThreads and fill its Queue.
            for i in range(15):
                conn = self.HTTP_CONN(self.HOST, self.PORT)
                conn.putrequest('POST', '/upload', skip_host=True)
                conn.putheader('Host', self.HOST)
                conn.putheader('Content-Type', 'text/plain')
                conn.putheader('Content-Length', '4')
                conn.endheaders()
                conns.append(conn)

            # Now try a 16th conn, which should be closed by the
            # server immediately.
            overflow_conn = self.HTTP_CONN(self.HOST, self.PORT)
            # Manually connect since httplib won't let us set a timeout
            for res in socket.getaddrinfo(self.HOST, self.PORT, 0,
                                          socket.SOCK_STREAM):
                af, socktype, proto, canonname, sa = res
                overflow_conn.sock = socket.socket(af, socktype, proto)
                overflow_conn.sock.settimeout(5)
                overflow_conn.sock.connect(sa)
                break

            overflow_conn.putrequest('GET', '/', skip_host=True)
            overflow_conn.putheader('Host', self.HOST)
            overflow_conn.endheaders()
            response = overflow_conn.response_class(
                overflow_conn.sock,
                method='GET',
            )
            try:
                response.begin()
            except socket.error as exc:
                if exc.args[0] in socket_reset_errors:
                    pass  # Expected.
                else:
                    tmpl = (
                        'Overflow conn did not get RST. '
                        'Got {exc.args!r} instead'
                    )
                    raise AssertionError(tmpl.format(**locals()))
            except BadStatusLine:
                # This is a special case in OS X. Linux and Windows will
                # RST correctly.
                assert sys.platform == 'darwin'
            else:
                raise AssertionError('Overflow conn did not get RST ')
        finally:
            for conn in conns:
                conn.send(b'done')
                response = conn.response_class(conn.sock, method='POST')
                response.begin()
                self.body = response.read()
                self.assertBody("thanks for 'done'")
                self.assertEqual(response.status, 200)
                conn.close()
            if overflow_conn:
                overflow_conn.close()


class BadRequestTests(helper.CPWebCase):
    setup_server = staticmethod(setup_server)

    def test_No_CRLF(self):
        self.persistent = True

        conn = self.HTTP_CONN
        conn.send(b'GET /hello HTTP/1.1\n\n')
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.body = response.read()
        self.assertBody('HTTP requires CRLF terminators')
        conn.close()

        conn.connect()
        conn.send(b'GET /hello HTTP/1.1\r\n\n')
        response = conn.response_class(conn.sock, method='GET')
        response.begin()
        self.body = response.read()
        self.assertBody('HTTP requires CRLF terminators')
        conn.close()
