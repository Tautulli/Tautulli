"""Tests for managing HTTP issues (malformed requests, etc)."""

import errno
import socket
import urllib.parse  # noqa: WPS301

import pytest

from cheroot.test import helper


HTTP_BAD_REQUEST = 400
HTTP_LENGTH_REQUIRED = 411
HTTP_NOT_FOUND = 404
HTTP_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_OK = 200
HTTP_VERSION_NOT_SUPPORTED = 505


class HelloController(helper.Controller):
    """Controller for serving WSGI apps."""

    def hello(req, resp):
        """Render Hello world."""
        return 'Hello world!'

    def body_required(req, resp):
        """Render Hello world or set 411."""
        if req.environ.get('Content-Length', None) is None:
            resp.status = '411 Length Required'
            return
        return 'Hello world!'

    def query_string(req, resp):
        """Render QUERY_STRING value."""
        return req.environ.get('QUERY_STRING', '')

    def asterisk(req, resp):
        """Render request method value."""
        # pylint: disable=possibly-unused-variable
        method = req.environ.get('REQUEST_METHOD', 'NO METHOD FOUND')
        tmpl = 'Got asterisk URI path with {method} method'
        return tmpl.format(**locals())

    def _munge(string):
        """Encode PATH_INFO correctly depending on Python version.

        WSGI 1.0 is a mess around unicode. Create endpoints
        that match the PATH_INFO that it produces.
        """
        return string.encode('utf-8').decode('latin-1')

    handlers = {
        '/hello': hello,
        '/no_body': hello,
        '/body_required': body_required,
        '/query_string': query_string,
        # FIXME: Unignore the pylint rules in pylint >= 2.15.4.
        # Refs:
        # * https://github.com/PyCQA/pylint/issues/6592
        # * https://github.com/PyCQA/pylint/pull/7395
        # pylint: disable-next=too-many-function-args
        _munge('/привіт'): hello,
        # pylint: disable-next=too-many-function-args
        _munge('/Юххууу'): hello,
        '/\xa0Ðblah key 0 900 4 data': hello,
        '/*': asterisk,
    }


def _get_http_response(connection, method='GET'):
    return connection.response_class(connection.sock, method=method)


@pytest.fixture
def testing_server(wsgi_server_client):
    """Attach a WSGI app to the given server and preconfigure it."""
    wsgi_server = wsgi_server_client.server_instance
    wsgi_server.wsgi_app = HelloController()
    wsgi_server.max_request_body_size = 30000000
    wsgi_server.server_client = wsgi_server_client
    return wsgi_server


@pytest.fixture
def test_client(testing_server):
    """Get and return a test client out of the given server."""
    return testing_server.server_client


@pytest.fixture
def testing_server_with_defaults(wsgi_server_client):
    """Attach a WSGI app to the given server and preconfigure it."""
    wsgi_server = wsgi_server_client.server_instance
    wsgi_server.wsgi_app = HelloController()
    wsgi_server.server_client = wsgi_server_client
    return wsgi_server


@pytest.fixture
def test_client_with_defaults(testing_server_with_defaults):
    """Get and return a test client out of the given server."""
    return testing_server_with_defaults.server_client


def test_http_connect_request(test_client):
    """Check that CONNECT query results in Method Not Allowed status."""
    status_line = test_client.connect('/anything')[0]
    actual_status = int(status_line[:3])
    assert actual_status == 405


def test_normal_request(test_client):
    """Check that normal GET query succeeds."""
    status_line, _, actual_resp_body = test_client.get('/hello')
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_OK
    assert actual_resp_body == b'Hello world!'


def test_query_string_request(test_client):
    """Check that GET param is parsed well."""
    status_line, _, actual_resp_body = test_client.get(
        '/query_string?test=True',
    )
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_OK
    assert actual_resp_body == b'test=True'


@pytest.mark.parametrize(
    'uri',
    (
        '/hello',  # plain
        '/query_string?test=True',  # query
        '/{0}?{1}={2}'.format(  # quoted unicode
            *map(urllib.parse.quote, ('Юххууу', 'ї', 'йо')),
        ),
    ),
)
def test_parse_acceptable_uri(test_client, uri):
    """Check that server responds with OK to valid GET queries."""
    status_line = test_client.get(uri)[0]
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_OK


def test_parse_uri_unsafe_uri(test_client):
    """Test that malicious URI does not allow HTTP injection.

    This effectively checks that sending GET request with URL

    /%A0%D0blah%20key%200%20900%204%20data

    is not converted into

    GET /
    blah key 0 900 4 data
    HTTP/1.1

    which would be a security issue otherwise.
    """
    c = test_client.get_connection()
    resource = '/\xa0Ðblah key 0 900 4 data'.encode('latin-1')
    quoted = urllib.parse.quote(resource)
    assert quoted == '/%A0%D0blah%20key%200%20900%204%20data'
    request = 'GET {quoted} HTTP/1.1'.format(**locals())
    c._output(request.encode('utf-8'))
    c._send_output()
    response = _get_http_response(c, method='GET')
    response.begin()
    assert response.status == HTTP_OK
    assert response.read(12) == b'Hello world!'
    c.close()


def test_parse_uri_invalid_uri(test_client):
    """Check that server responds with Bad Request to invalid GET queries.

    Invalid request line test case: it should only contain US-ASCII.
    """
    c = test_client.get_connection()
    c._output(u'GET /йопта! HTTP/1.1'.encode('utf-8'))
    c._send_output()
    response = _get_http_response(c, method='GET')
    response.begin()
    assert response.status == HTTP_BAD_REQUEST
    assert response.read(21) == b'Malformed Request-URI'
    c.close()


@pytest.mark.parametrize(
    'uri',
    (
        'hello',  # ascii
        'привіт',  # non-ascii
    ),
)
def test_parse_no_leading_slash_invalid(test_client, uri):
    """Check that server responds with Bad Request to invalid GET queries.

    Invalid request line test case: it should have leading slash (be absolute).
    """
    status_line, _, actual_resp_body = test_client.get(
        urllib.parse.quote(uri),
    )
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_BAD_REQUEST
    assert b'starting with a slash' in actual_resp_body


def test_parse_uri_absolute_uri(test_client):
    """Check that server responds with Bad Request to Absolute URI.

    Only proxy servers should allow this.
    """
    status_line, _, actual_resp_body = test_client.get('http://google.com/')
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_BAD_REQUEST
    expected_body = b'Absolute URI not allowed if server is not a proxy.'
    assert actual_resp_body == expected_body


def test_parse_uri_asterisk_uri(test_client):
    """Check that server responds with OK to OPTIONS with "*" Absolute URI."""
    status_line, _, actual_resp_body = test_client.options('*')
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_OK
    expected_body = b'Got asterisk URI path with OPTIONS method'
    assert actual_resp_body == expected_body


def test_parse_uri_fragment_uri(test_client):
    """Check that server responds with Bad Request to URI with fragment."""
    status_line, _, actual_resp_body = test_client.get(
        '/hello?test=something#fake',
    )
    actual_status = int(status_line[:3])
    assert actual_status == HTTP_BAD_REQUEST
    expected_body = b'Illegal #fragment in Request-URI.'
    assert actual_resp_body == expected_body


def test_no_content_length(test_client):
    """Test POST query with an empty body being successful."""
    # "The presence of a message-body in a request is signaled by the
    # inclusion of a Content-Length or Transfer-Encoding header field in
    # the request's message-headers."
    #
    # Send a message with neither header and no body.
    c = test_client.get_connection()
    c.request('POST', '/no_body')
    response = c.getresponse()
    actual_resp_body = response.read()
    actual_status = response.status
    assert actual_status == HTTP_OK
    assert actual_resp_body == b'Hello world!'

    c.close()  # deal with the resource warning


def test_content_length_required(test_client):
    """Test POST query with body failing because of missing Content-Length."""
    # Now send a message that has no Content-Length, but does send a body.
    # Verify that CP times out the socket and responds
    # with 411 Length Required.

    c = test_client.get_connection()
    c.request('POST', '/body_required')
    response = c.getresponse()
    response.read()

    actual_status = response.status
    assert actual_status == HTTP_LENGTH_REQUIRED

    c.close()  # deal with the resource warning


@pytest.mark.xfail(
    reason='https://github.com/cherrypy/cheroot/issues/106',
    strict=False,  # sometimes it passes
)
def test_large_request(test_client_with_defaults):
    """Test GET query with maliciously large Content-Length."""
    # If the server's max_request_body_size is not set (i.e. is set to 0)
    # then this will result in an `OverflowError: Python int too large to
    # convert to C ssize_t` in the server.
    # We expect that this should instead return that the request is too
    # large.
    c = test_client_with_defaults.get_connection()
    c.putrequest('GET', '/hello')
    c.putheader('Content-Length', str(2**64))
    c.endheaders()

    response = c.getresponse()
    actual_status = response.status

    assert actual_status == HTTP_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.parametrize(
    ('request_line', 'status_code', 'expected_body'),
    (
        (
            b'GET /',  # missing proto
            HTTP_BAD_REQUEST, b'Malformed Request-Line',
        ),
        (
            b'GET / HTTPS/1.1',  # invalid proto
            HTTP_BAD_REQUEST, b'Malformed Request-Line: bad protocol',
        ),
        (
            b'GET / HTTP/1',  # invalid version
            HTTP_BAD_REQUEST, b'Malformed Request-Line: bad version',
        ),
        (
            b'GET / HTTP/2.15',  # invalid ver
            HTTP_VERSION_NOT_SUPPORTED, b'Cannot fulfill request',
        ),
    ),
)
def test_malformed_request_line(
    test_client, request_line,
    status_code, expected_body,
):
    """Test missing or invalid HTTP version in Request-Line."""
    c = test_client.get_connection()
    c._output(request_line)
    c._send_output()
    response = _get_http_response(c, method='GET')
    response.begin()
    assert response.status == status_code
    assert response.read(len(expected_body)) == expected_body
    c.close()


def test_malformed_http_method(test_client):
    """Test non-uppercase HTTP method."""
    c = test_client.get_connection()
    c.putrequest('GeT', '/malformed_method_case')
    c.putheader('Content-Type', 'text/plain')
    c.endheaders()

    response = c.getresponse()
    actual_status = response.status
    assert actual_status == HTTP_BAD_REQUEST
    actual_resp_body = response.read(21)
    assert actual_resp_body == b'Malformed method name'

    c.close()  # deal with the resource warning


def test_malformed_header(test_client):
    """Check that broken HTTP header results in Bad Request."""
    c = test_client.get_connection()
    c.putrequest('GET', '/')
    c.putheader('Content-Type', 'text/plain')
    # See https://www.bitbucket.org/cherrypy/cherrypy/issue/941
    c._output(b'Re, 1.2.3.4#015#012')
    c.endheaders()

    response = c.getresponse()
    actual_status = response.status
    assert actual_status == HTTP_BAD_REQUEST
    actual_resp_body = response.read(20)
    assert actual_resp_body == b'Illegal header line.'

    c.close()  # deal with the resource warning


def test_request_line_split_issue_1220(test_client):
    """Check that HTTP request line of exactly 256 chars length is OK."""
    Request_URI = (
        '/hello?'
        'intervenant-entreprise-evenement_classaction='
        'evenement-mailremerciements'
        '&_path=intervenant-entreprise-evenement'
        '&intervenant-entreprise-evenement_action-id=19404'
        '&intervenant-entreprise-evenement_id=19404'
        '&intervenant-entreprise_id=28092'
    )
    assert len('GET %s HTTP/1.1\r\n' % Request_URI) == 256

    actual_resp_body = test_client.get(Request_URI)[2]
    assert actual_resp_body == b'Hello world!'


def test_garbage_in(test_client):
    """Test that server sends an error for garbage received over TCP."""
    # Connect without SSL regardless of server.scheme

    c = test_client.get_connection()
    c._output(b'gjkgjklsgjklsgjkljklsg')
    c._send_output()
    response = c.response_class(c.sock, method='GET')
    try:
        response.begin()
        actual_status = response.status
        assert actual_status == HTTP_BAD_REQUEST
        actual_resp_body = response.read(22)
        assert actual_resp_body == b'Malformed Request-Line'
        c.close()
    except socket.error as ex:
        # "Connection reset by peer" is also acceptable.
        if ex.errno != errno.ECONNRESET:
            raise


class CloseController:
    """Controller for testing the close callback."""

    def __call__(self, environ, start_response):
        """Get the req to know header sent status."""
        self.req = start_response.__self__.req
        resp = CloseResponse(self.close)
        start_response(resp.status, resp.headers.items())
        return resp

    def close(self):
        """Close, writing hello."""
        self.req.write(b'hello')


class CloseResponse:
    """Dummy empty response to trigger the no body status."""

    def __init__(self, close):
        """Use some defaults to ensure we have a header."""
        self.status = '200 OK'
        self.headers = {'Content-Type': 'text/html'}
        self.close = close

    def __getitem__(self, index):
        """Ensure we don't have a body."""
        raise IndexError()

    def output(self):
        """Return self to hook the close method."""
        return self


@pytest.fixture
def testing_server_close(wsgi_server_client):
    """Attach a WSGI app to the given server and preconfigure it."""
    wsgi_server = wsgi_server_client.server_instance
    wsgi_server.wsgi_app = CloseController()
    wsgi_server.max_request_body_size = 30000000
    wsgi_server.server_client = wsgi_server_client
    return wsgi_server


def test_send_header_before_closing(testing_server_close):
    """Test we are actually sending the headers before calling 'close'."""
    _, _, resp_body = testing_server_close.server_client.get('/')
    assert resp_body == b'hello'
