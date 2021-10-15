"""Basic tests for the CherryPy core: request handling."""

import logging

from cheroot.test import webtest
import pytest
import requests  # FIXME: Temporary using it directly, better switch

import cherrypy
from cherrypy.test.logtest import LogCase


# Some unicode strings.
tartaros = u'\u03a4\u1f71\u03c1\u03c4\u03b1\u03c1\u03bf\u03c2'
erebos = u'\u0388\u03c1\u03b5\u03b2\u03bf\u03c2.com'


@pytest.fixture
def access_log_file(tmp_path_factory):
    return tmp_path_factory.mktemp('logs') / 'access.log'


@pytest.fixture
def error_log_file(tmp_path_factory):
    return tmp_path_factory.mktemp('logs') / 'access.log'


@pytest.fixture
def server(configure_server):
    cherrypy.engine.start()
    cherrypy.engine.wait(cherrypy.engine.states.STARTED)

    yield

    shutdown_server()


def shutdown_server():
    cherrypy.engine.exit()
    cherrypy.engine.block()

    for name, server in getattr(cherrypy, 'servers', {}).copy().items():
        server.unsubscribe()
        del cherrypy.servers[name]


@pytest.fixture
def configure_server(access_log_file, error_log_file):
    class Root:

        @cherrypy.expose
        def index(self):
            return 'hello'

        @cherrypy.expose
        def uni_code(self):
            cherrypy.request.login = tartaros
            cherrypy.request.remote.name = erebos

        @cherrypy.expose
        def slashes(self):
            cherrypy.request.request_line = r'GET /slashed\path HTTP/1.1'

        @cherrypy.expose
        def whitespace(self):
            # User-Agent = "User-Agent" ":" 1*( product | comment )
            # comment    = "(" *( ctext | quoted-pair | comment ) ")"
            # ctext      = <any TEXT excluding "(" and ")">
            # TEXT       = <any OCTET except CTLs, but including LWS>
            # LWS        = [CRLF] 1*( SP | HT )
            cherrypy.request.headers['User-Agent'] = 'Browzuh (1.0\r\n\t\t.3)'

        @cherrypy.expose
        def as_string(self):
            return 'content'

        @cherrypy.expose
        def as_yield(self):
            yield 'content'

        @cherrypy.expose
        @cherrypy.config(**{'tools.log_tracebacks.on': True})
        def error(self):
            raise ValueError()

    root = Root()

    cherrypy.config.reset()
    cherrypy.config.update({
        'server.socket_host': webtest.WebCase.HOST,
        'server.socket_port': webtest.WebCase.PORT,
        'server.protocol_version': webtest.WebCase.PROTOCOL,
        'environment': 'test_suite',
    })
    cherrypy.config.update({
        'log.error_file': str(error_log_file),
        'log.access_file': str(access_log_file),
    })
    cherrypy.tree.mount(root)


@pytest.fixture
def log_tracker(access_log_file):
    class LogTracker(LogCase):
        logfile = str(access_log_file)
    return LogTracker()


def test_normal_return(log_tracker, server):
    log_tracker.markLog()
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    resp = requests.get(
        'http://%s:%s/as_string' % (host, port),
        headers={
            'Referer': 'http://www.cherrypy.org/',
            'User-Agent': 'Mozilla/5.0',
        },
    )
    expected_body = 'content'
    assert resp.text == expected_body
    assert resp.status_code == 200

    intro = '%s - - [' % host

    log_tracker.assertLog(-1, intro)

    content_length = len(expected_body)
    if not any(
            k for k, v in resp.headers.items()
            if k.lower() == 'content-length'
    ):
        content_length = '-'

    log_tracker.assertLog(
        -1,
        '] "GET /as_string HTTP/1.1" 200 %s '
        '"http://www.cherrypy.org/" "Mozilla/5.0"'
        % content_length,
    )


def test_normal_yield(log_tracker, server):
    log_tracker.markLog()
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    resp = requests.get(
        'http://%s:%s/as_yield' % (host, port),
        headers={
            'User-Agent': '',
        },
    )
    expected_body = 'content'
    assert resp.text == expected_body
    assert resp.status_code == 200

    intro = '%s - - [' % host

    log_tracker.assertLog(-1, intro)
    content_length = len(expected_body)
    if not any(
            k for k, v in resp.headers.items()
            if k.lower() == 'content-length'
    ):
        content_length = '-'

    log_tracker.assertLog(
        -1,
        '] "GET /as_yield HTTP/1.1" 200 %s "" ""'
        % content_length,
    )


def test_custom_log_format(log_tracker, monkeypatch, server):
    """Test a customized access_log_format string, which is a
    feature of _cplogging.LogManager.access()."""
    monkeypatch.setattr(
        'cherrypy._cplogging.LogManager.access_log_format',
        '{h} {l} {u} {t} "{r}" {s} {b} "{f}" "{a}" {o}',
    )
    log_tracker.markLog()
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    requests.get(
        'http://%s:%s/as_string' % (host, port),
        headers={
            'Referer': 'REFERER',
            'User-Agent': 'USERAGENT',
            'Host': 'HOST',
        },
    )
    log_tracker.assertLog(-1, '%s - - [' % host)
    log_tracker.assertLog(
        -1,
        '] "GET /as_string HTTP/1.1" '
        '200 7 "REFERER" "USERAGENT" HOST',
    )


def test_timez_log_format(log_tracker, monkeypatch, server):
    """Test a customized access_log_format string, which is a
    feature of _cplogging.LogManager.access()."""
    monkeypatch.setattr(
        'cherrypy._cplogging.LogManager.access_log_format',
        '{h} {l} {u} {z} "{r}" {s} {b} "{f}" "{a}" {o}',
    )
    log_tracker.markLog()

    expected_time = str(cherrypy._cplogging.LazyRfc3339UtcTime())
    monkeypatch.setattr(
        'cherrypy._cplogging.LazyRfc3339UtcTime',
        lambda: expected_time,
    )
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    requests.get(
        'http://%s:%s/as_string' % (host, port),
        headers={
            'Referer': 'REFERER',
            'User-Agent': 'USERAGENT',
            'Host': 'HOST',
        },
    )

    log_tracker.assertLog(-1, '%s - - ' % host)
    log_tracker.assertLog(-1, expected_time)
    log_tracker.assertLog(
        -1,
        ' "GET /as_string HTTP/1.1" '
        '200 7 "REFERER" "USERAGENT" HOST',
    )


def test_UUIDv4_parameter_log_format(log_tracker, monkeypatch, server):
    """Test rendering of UUID4 within access log."""
    monkeypatch.setattr(
        'cherrypy._cplogging.LogManager.access_log_format',
        '{i}',
    )
    log_tracker.markLog()
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    requests.get('http://%s:%s/as_string' % (host, port))
    log_tracker.assertValidUUIDv4()


def test_escaped_output(log_tracker, server):
    # Test unicode in access log pieces.
    log_tracker.markLog()
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    resp = requests.get('http://%s:%s/uni_code' % (host, port))
    assert resp.status_code == 200
    # The repr of a bytestring includes a b'' prefix
    log_tracker.assertLog(-1, repr(tartaros.encode('utf8'))[2:-1])
    # Test the erebos value. Included inline for your enlightenment.
    # Note the 'r' prefix--those backslashes are literals.
    log_tracker.assertLog(
        -1,
        r'\xce\x88\xcf\x81\xce\xb5\xce\xb2\xce\xbf\xcf\x82',
    )

    # Test backslashes in output.
    log_tracker.markLog()
    resp = requests.get('http://%s:%s/slashes' % (host, port))
    assert resp.status_code == 200
    log_tracker.assertLog(-1, b'"GET /slashed\\path HTTP/1.1"')

    # Test whitespace in output.
    log_tracker.markLog()
    resp = requests.get('http://%s:%s/whitespace' % (host, port))
    assert resp.status_code == 200
    # Again, note the 'r' prefix.
    log_tracker.assertLog(-1, r'"Browzuh (1.0\r\n\t\t.3)"')


def test_tracebacks(server, caplog):
    host = webtest.interface(webtest.WebCase.HOST)
    port = webtest.WebCase.PORT
    with caplog.at_level(logging.ERROR, logger='cherrypy.error'):
        resp = requests.get('http://%s:%s/error' % (host, port))

    rec = caplog.records[0]
    exc_cls, exc_msg = rec.exc_info[0], rec.message

    assert 'raise ValueError()' in resp.text
    assert 'HTTP' in exc_msg
    assert exc_cls is ValueError
