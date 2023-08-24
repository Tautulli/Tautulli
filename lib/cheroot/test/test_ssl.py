"""Tests for TLS support."""

import functools
import json
import os
import ssl
import subprocess
import sys
import threading
import time
import traceback
import http.client

import OpenSSL.SSL
import pytest
import requests
import trustme

from .._compat import bton, ntob, ntou
from .._compat import IS_ABOVE_OPENSSL10, IS_CI, IS_PYPY
from .._compat import IS_LINUX, IS_MACOS, IS_WINDOWS
from ..server import HTTPServer, get_ssl_adapter_class
from ..testing import (
    ANY_INTERFACE_IPV4,
    ANY_INTERFACE_IPV6,
    EPHEMERAL_PORT,
    # get_server_client,
    _get_conn_data,
    _probe_ipv6_sock,
)
from ..wsgi import Gateway_10


IS_GITHUB_ACTIONS_WORKFLOW = bool(os.getenv('GITHUB_WORKFLOW'))
IS_WIN2016 = (
    IS_WINDOWS
    # pylint: disable=unsupported-membership-test
    and b'Microsoft Windows Server 2016 Datacenter' in subprocess.check_output(
        ('systeminfo',),
    )
)
IS_LIBRESSL_BACKEND = ssl.OPENSSL_VERSION.startswith('LibreSSL')
IS_PYOPENSSL_SSL_VERSION_1_0 = (
    OpenSSL.SSL.SSLeay_version(OpenSSL.SSL.SSLEAY_VERSION).
    startswith(b'OpenSSL 1.0.')
)
PY310_PLUS = sys.version_info[:2] >= (3, 10)


_stdlib_to_openssl_verify = {
    ssl.CERT_NONE: OpenSSL.SSL.VERIFY_NONE,
    ssl.CERT_OPTIONAL: OpenSSL.SSL.VERIFY_PEER,
    ssl.CERT_REQUIRED:
        OpenSSL.SSL.VERIFY_PEER + OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
}


missing_ipv6 = pytest.mark.skipif(
    not _probe_ipv6_sock('::1'),
    reason=''
    'IPv6 is disabled '
    '(for example, under Travis CI '
    'which runs under GCE supporting only IPv4)',
)


class HelloWorldGateway(Gateway_10):
    """Gateway responding with Hello World to root URI."""

    def respond(self):
        """Respond with dummy content via HTTP."""
        req = self.req
        req_uri = bton(req.uri)
        if req_uri == '/':
            req.status = b'200 OK'
            req.ensure_headers_sent()
            req.write(b'Hello world!')
            return
        if req_uri == '/env':
            req.status = b'200 OK'
            req.ensure_headers_sent()
            env = self.get_environ()
            # drop files so that it can be json dumped
            env.pop('wsgi.errors')
            env.pop('wsgi.input')
            print(env)
            req.write(json.dumps(env).encode('utf-8'))
            return
        return super(HelloWorldGateway, self).respond()


def make_tls_http_server(bind_addr, ssl_adapter, request):
    """Create and start an HTTP server bound to ``bind_addr``."""
    httpserver = HTTPServer(
        bind_addr=bind_addr,
        gateway=HelloWorldGateway,
    )
    # httpserver.gateway = HelloWorldGateway
    httpserver.ssl_adapter = ssl_adapter

    threading.Thread(target=httpserver.safe_start).start()

    while not httpserver.ready:
        time.sleep(0.1)

    request.addfinalizer(httpserver.stop)

    return httpserver


@pytest.fixture
def tls_http_server(request):
    """Provision a server creator as a fixture."""
    return functools.partial(make_tls_http_server, request=request)


@pytest.fixture
def ca():
    """Provide a certificate authority via fixture."""
    return trustme.CA()


@pytest.fixture
def tls_ca_certificate_pem_path(ca):
    """Provide a certificate authority certificate file via fixture."""
    with ca.cert_pem.tempfile() as ca_cert_pem:
        yield ca_cert_pem


@pytest.fixture
def tls_certificate(ca):
    """Provide a leaf certificate via fixture."""
    interface, _host, _port = _get_conn_data(ANY_INTERFACE_IPV4)
    return ca.issue_cert(ntou(interface))


@pytest.fixture
def tls_certificate_chain_pem_path(tls_certificate):
    """Provide a certificate chain PEM file path via fixture."""
    with tls_certificate.private_key_and_cert_chain_pem.tempfile() as cert_pem:
        yield cert_pem


@pytest.fixture
def tls_certificate_private_key_pem_path(tls_certificate):
    """Provide a certificate private key PEM file path via fixture."""
    with tls_certificate.private_key_pem.tempfile() as cert_key_pem:
        yield cert_key_pem


def _thread_except_hook(exceptions, args):
    """Append uncaught exception ``args`` in threads to ``exceptions``."""
    if issubclass(args.exc_type, SystemExit):
        return
    # cannot store the exception, it references the thread's stack
    exceptions.append((
        args.exc_type,
        str(args.exc_value),
        ''.join(
            traceback.format_exception(
                args.exc_type, args.exc_value, args.exc_traceback,
            ),
        ),
    ))


@pytest.fixture
def thread_exceptions():
    """Provide a list of uncaught exceptions from threads via a fixture.

    Only catches exceptions on Python 3.8+.
    The list contains: ``(type, str(value), str(traceback))``
    """
    exceptions = []
    # Python 3.8+
    orig_hook = getattr(threading, 'excepthook', None)
    if orig_hook is not None:
        threading.excepthook = functools.partial(
            _thread_except_hook, exceptions,
        )
    try:
        yield exceptions
    finally:
        if orig_hook is not None:
            threading.excepthook = orig_hook


@pytest.mark.parametrize(
    'adapter_type',
    (
        'builtin',
        'pyopenssl',
    ),
)
def test_ssl_adapters(
    http_request_timeout,
    tls_http_server, adapter_type,
    tls_certificate,
    tls_certificate_chain_pem_path,
    tls_certificate_private_key_pem_path,
    tls_ca_certificate_pem_path,
):
    """Test ability to connect to server via HTTPS using adapters."""
    interface, _host, port = _get_conn_data(ANY_INTERFACE_IPV4)
    tls_adapter_cls = get_ssl_adapter_class(name=adapter_type)
    tls_adapter = tls_adapter_cls(
        tls_certificate_chain_pem_path, tls_certificate_private_key_pem_path,
    )
    if adapter_type == 'pyopenssl':
        tls_adapter.context = tls_adapter.get_context()

    tls_certificate.configure_cert(tls_adapter.context)

    tlshttpserver = tls_http_server((interface, port), tls_adapter)

    # testclient = get_server_client(tlshttpserver)
    # testclient.get('/')

    interface, _host, port = _get_conn_data(
        tlshttpserver.bind_addr,
    )

    resp = requests.get(
        'https://{host!s}:{port!s}/'.format(host=interface, port=port),
        timeout=http_request_timeout,
        verify=tls_ca_certificate_pem_path,
    )

    assert resp.status_code == 200
    assert resp.text == 'Hello world!'


@pytest.mark.parametrize(  # noqa: C901  # FIXME
    'adapter_type',
    (
        'builtin',
        'pyopenssl',
    ),
)
@pytest.mark.parametrize(
    ('is_trusted_cert', 'tls_client_identity'),
    (
        (True, 'localhost'), (True, '127.0.0.1'),
        (True, '*.localhost'), (True, 'not_localhost'),
        (False, 'localhost'),
    ),
)
@pytest.mark.parametrize(
    'tls_verify_mode',
    (
        ssl.CERT_NONE,  # server shouldn't validate client cert
        ssl.CERT_OPTIONAL,  # same as CERT_REQUIRED in client mode, don't use
        ssl.CERT_REQUIRED,  # server should validate if client cert CA is OK
    ),
)
@pytest.mark.xfail(
    IS_PYPY and IS_CI,
    reason='Fails under PyPy in CI for unknown reason',
    strict=False,
)
def test_tls_client_auth(  # noqa: C901, WPS213  # FIXME
    # FIXME: remove twisted logic, separate tests
    http_request_timeout,
    mocker,
    tls_http_server, adapter_type,
    ca,
    tls_certificate,
    tls_certificate_chain_pem_path,
    tls_certificate_private_key_pem_path,
    tls_ca_certificate_pem_path,
    is_trusted_cert, tls_client_identity,
    tls_verify_mode,
):
    """Verify that client TLS certificate auth works correctly."""
    test_cert_rejection = (
        tls_verify_mode != ssl.CERT_NONE
        and not is_trusted_cert
    )
    interface, _host, port = _get_conn_data(ANY_INTERFACE_IPV4)

    client_cert_root_ca = ca if is_trusted_cert else trustme.CA()
    with mocker.mock_module.patch(
        'idna.core.ulabel',
        return_value=ntob(tls_client_identity),
    ):
        client_cert = client_cert_root_ca.issue_cert(
            ntou(tls_client_identity),
        )
        del client_cert_root_ca

    with client_cert.private_key_and_cert_chain_pem.tempfile() as cl_pem:
        tls_adapter_cls = get_ssl_adapter_class(name=adapter_type)
        tls_adapter = tls_adapter_cls(
            tls_certificate_chain_pem_path,
            tls_certificate_private_key_pem_path,
        )
        if adapter_type == 'pyopenssl':
            tls_adapter.context = tls_adapter.get_context()
            tls_adapter.context.set_verify(
                _stdlib_to_openssl_verify[tls_verify_mode],
                lambda conn, cert, errno, depth, preverify_ok: preverify_ok,
            )
        else:
            tls_adapter.context.verify_mode = tls_verify_mode

        ca.configure_trust(tls_adapter.context)
        tls_certificate.configure_cert(tls_adapter.context)

        tlshttpserver = tls_http_server((interface, port), tls_adapter)

        interface, _host, port = _get_conn_data(tlshttpserver.bind_addr)

        make_https_request = functools.partial(
            requests.get,
            'https://{host!s}:{port!s}/'.format(host=interface, port=port),

            # Don't wait for the first byte forever:
            timeout=http_request_timeout,

            # Server TLS certificate verification:
            verify=tls_ca_certificate_pem_path,

            # Client TLS certificate verification:
            cert=cl_pem,
        )

        if not test_cert_rejection:
            resp = make_https_request()
            is_req_successful = resp.status_code == 200
            if (
                    not is_req_successful
                    and IS_PYOPENSSL_SSL_VERSION_1_0
                    and adapter_type == 'builtin'
                    and tls_verify_mode == ssl.CERT_REQUIRED
                    and tls_client_identity == 'localhost'
                    and is_trusted_cert
            ):
                pytest.xfail(
                    'OpenSSL 1.0 has problems with verifying client certs',
                )
            assert is_req_successful
            assert resp.text == 'Hello world!'
            resp.close()
            return

        # xfail some flaky tests
        # https://github.com/cherrypy/cheroot/issues/237
        issue_237 = (
            IS_MACOS
            and adapter_type == 'builtin'
            and tls_verify_mode != ssl.CERT_NONE
        )
        if issue_237:
            pytest.xfail('Test sometimes fails')

        expected_ssl_errors = requests.exceptions.SSLError,
        if IS_WINDOWS or IS_GITHUB_ACTIONS_WORKFLOW:
            expected_ssl_errors += requests.exceptions.ConnectionError,
        with pytest.raises(expected_ssl_errors) as ssl_err:
            make_https_request().close()

        try:
            err_text = ssl_err.value.args[0].reason.args[0].args[0]
        except AttributeError:
            if IS_WINDOWS or IS_GITHUB_ACTIONS_WORKFLOW:
                err_text = str(ssl_err.value)
            else:
                raise

        if isinstance(err_text, int):
            err_text = str(ssl_err.value)

        expected_substrings = (
            'sslv3 alert bad certificate' if IS_LIBRESSL_BACKEND
            else 'tlsv1 alert unknown ca',
        )
        if IS_MACOS and IS_PYPY and adapter_type == 'pyopenssl':
            expected_substrings = ('tlsv1 alert unknown ca',)
        if (
                tls_verify_mode in (
                    ssl.CERT_REQUIRED,
                    ssl.CERT_OPTIONAL,
                )
                and not is_trusted_cert
                and tls_client_identity == 'localhost'
        ):
            expected_substrings += (
                'bad handshake: '
                "SysCallError(10054, 'WSAECONNRESET')",
                "('Connection aborted.', "
                'OSError("(10054, \'WSAECONNRESET\')"))',
                "('Connection aborted.', "
                'OSError("(10054, \'WSAECONNRESET\')",))',
                "('Connection aborted.', "
                'error("(10054, \'WSAECONNRESET\')",))',
                "('Connection aborted.', "
                'ConnectionResetError(10054, '
                "'An existing connection was forcibly closed "
                "by the remote host', None, 10054, None))",
                "('Connection aborted.', "
                'error(10054, '
                "'An existing connection was forcibly closed "
                "by the remote host'))",
            ) if IS_WINDOWS else (
                "('Connection aborted.', "
                'OSError("(104, \'ECONNRESET\')"))',
                "('Connection aborted.', "
                'OSError("(104, \'ECONNRESET\')",))',
                "('Connection aborted.', "
                'error("(104, \'ECONNRESET\')",))',
                "('Connection aborted.', "
                "ConnectionResetError(104, 'Connection reset by peer'))",
                "('Connection aborted.', "
                "error(104, 'Connection reset by peer'))",
            ) if (
                IS_GITHUB_ACTIONS_WORKFLOW
                and IS_LINUX
            ) else (
                "('Connection aborted.', "
                "BrokenPipeError(32, 'Broken pipe'))",
            )

        if PY310_PLUS:
            # FIXME: Figure out what's happening and correct the problem
            expected_substrings += (
                'SSLError(SSLEOFError(8, '
                "'EOF occurred in violation of protocol (_ssl.c:",
            )
        if IS_GITHUB_ACTIONS_WORKFLOW and IS_WINDOWS and PY310_PLUS:
            expected_substrings += (
                "('Connection aborted.', "
                'RemoteDisconnected('
                "'Remote end closed connection without response'))",
            )

        assert any(e in err_text for e in expected_substrings)


@pytest.mark.parametrize(  # noqa: C901  # FIXME
    'adapter_type',
    (
        pytest.param(
            'builtin',
            marks=pytest.mark.xfail(
                IS_MACOS and PY310_PLUS,
                reason='Unclosed TLS resource warnings happen on macOS '
                'under Python 3.10 (#508)',
                strict=False,
            ),
        ),
        'pyopenssl',
    ),
)
@pytest.mark.parametrize(
    ('tls_verify_mode', 'use_client_cert'),
    (
        (ssl.CERT_NONE, False),
        (ssl.CERT_NONE, True),
        (ssl.CERT_OPTIONAL, False),
        (ssl.CERT_OPTIONAL, True),
        (ssl.CERT_REQUIRED, True),
    ),
)
def test_ssl_env(  # noqa: C901  # FIXME
        thread_exceptions,
        recwarn,
        mocker,
        http_request_timeout,
        tls_http_server, adapter_type,
        ca, tls_verify_mode, tls_certificate,
        tls_certificate_chain_pem_path,
        tls_certificate_private_key_pem_path,
        tls_ca_certificate_pem_path,
        use_client_cert,
):
    """Test the SSL environment generated by the SSL adapters."""
    interface, _host, port = _get_conn_data(ANY_INTERFACE_IPV4)

    with mocker.mock_module.patch(
        'idna.core.ulabel',
        return_value=ntob('127.0.0.1'),
    ):
        client_cert = ca.issue_cert(ntou('127.0.0.1'))

    with client_cert.private_key_and_cert_chain_pem.tempfile() as cl_pem:
        tls_adapter_cls = get_ssl_adapter_class(name=adapter_type)
        tls_adapter = tls_adapter_cls(
            tls_certificate_chain_pem_path,
            tls_certificate_private_key_pem_path,
        )
        if adapter_type == 'pyopenssl':
            tls_adapter.context = tls_adapter.get_context()
            tls_adapter.context.set_verify(
                _stdlib_to_openssl_verify[tls_verify_mode],
                lambda conn, cert, errno, depth, preverify_ok: preverify_ok,
            )
        else:
            tls_adapter.context.verify_mode = tls_verify_mode

        ca.configure_trust(tls_adapter.context)
        tls_certificate.configure_cert(tls_adapter.context)

        tlswsgiserver = tls_http_server((interface, port), tls_adapter)

        interface, _host, port = _get_conn_data(tlswsgiserver.bind_addr)

        resp = requests.get(
            'https://' + interface + ':' + str(port) + '/env',
            timeout=http_request_timeout,
            verify=tls_ca_certificate_pem_path,
            cert=cl_pem if use_client_cert else None,
        )

        env = json.loads(resp.content.decode('utf-8'))

        # hard coded env
        assert env['wsgi.url_scheme'] == 'https'
        assert env['HTTPS'] == 'on'

        # ensure these are present
        for key in {'SSL_VERSION_INTERFACE', 'SSL_VERSION_LIBRARY'}:
            assert key in env

        # pyOpenSSL generates the env before the handshake completes
        if adapter_type == 'pyopenssl':
            return

        for key in {'SSL_PROTOCOL', 'SSL_CIPHER'}:
            assert key in env

        # client certificate env
        if tls_verify_mode == ssl.CERT_NONE or not use_client_cert:
            assert env['SSL_CLIENT_VERIFY'] == 'NONE'
        else:
            assert env['SSL_CLIENT_VERIFY'] == 'SUCCESS'

            with open(cl_pem, 'rt') as f:
                assert env['SSL_CLIENT_CERT'] in f.read()

            for key in {
                'SSL_CLIENT_M_VERSION', 'SSL_CLIENT_M_SERIAL',
                'SSL_CLIENT_I_DN', 'SSL_CLIENT_S_DN',
            }:
                assert key in env

    # builtin ssl environment generation may use a loopback socket
    # ensure no ResourceWarning was raised during the test
    if IS_PYPY:
        # NOTE: PyPy doesn't have ResourceWarning
        # Ref: https://doc.pypy.org/en/latest/cpython_differences.html
        return
    for warn in recwarn:
        if not issubclass(warn.category, ResourceWarning):
            continue

        # the tests can sporadically generate resource warnings
        # due to timing issues
        # all of these sporadic warnings appear to be about socket.socket
        # and have been observed to come from requests connection pool
        msg = str(warn.message)
        if 'socket.socket' in msg:
            pytest.xfail(
                '\n'.join((
                    'Sometimes this test fails due to '
                    'a socket.socket ResourceWarning:',
                    msg,
                )),
            )
        pytest.fail(msg)

    # to perform the ssl handshake over that loopback socket,
    # the builtin ssl environment generation uses a thread
    for _, _, trace in thread_exceptions:
        print(trace, file=sys.stderr)
    assert not thread_exceptions, ': '.join((
        thread_exceptions[0][0].__name__,
        thread_exceptions[0][1],
    ))


@pytest.mark.parametrize(
    'ip_addr',
    (
        ANY_INTERFACE_IPV4,
        ANY_INTERFACE_IPV6,
    ),
)
def test_https_over_http_error(http_server, ip_addr):
    """Ensure that connecting over HTTPS to HTTP port is handled."""
    httpserver = http_server.send((ip_addr, EPHEMERAL_PORT))
    interface, _host, port = _get_conn_data(httpserver.bind_addr)
    with pytest.raises(ssl.SSLError) as ssl_err:
        http.client.HTTPSConnection(
            '{interface}:{port}'.format(
                interface=interface,
                port=port,
            ),
        ).request('GET', '/')
    expected_substring = (
        'wrong version number' if IS_ABOVE_OPENSSL10
        else 'unknown protocol'
    )
    assert expected_substring in ssl_err.value.args[-1]


@pytest.mark.parametrize(
    'adapter_type',
    (
        'builtin',
        'pyopenssl',
    ),
)
@pytest.mark.parametrize(
    'ip_addr',
    (
        ANY_INTERFACE_IPV4,
        pytest.param(ANY_INTERFACE_IPV6, marks=missing_ipv6),
    ),
)
@pytest.mark.flaky(reruns=3, reruns_delay=2)
def test_http_over_https_error(
    http_request_timeout,
    tls_http_server, adapter_type,
    ca, ip_addr,
    tls_certificate,
    tls_certificate_chain_pem_path,
    tls_certificate_private_key_pem_path,
):
    """Ensure that connecting over HTTP to HTTPS port is handled."""
    # disable some flaky tests
    # https://github.com/cherrypy/cheroot/issues/225
    issue_225 = (
        IS_MACOS
        and adapter_type == 'builtin'
    )
    if issue_225:
        pytest.xfail('Test fails in Travis-CI')

    tls_adapter_cls = get_ssl_adapter_class(name=adapter_type)
    tls_adapter = tls_adapter_cls(
        tls_certificate_chain_pem_path, tls_certificate_private_key_pem_path,
    )
    if adapter_type == 'pyopenssl':
        tls_adapter.context = tls_adapter.get_context()

    tls_certificate.configure_cert(tls_adapter.context)

    interface, _host, port = _get_conn_data(ip_addr)
    tlshttpserver = tls_http_server((interface, port), tls_adapter)

    interface, _host, port = _get_conn_data(
        tlshttpserver.bind_addr,
    )

    fqdn = interface
    if ip_addr is ANY_INTERFACE_IPV6:
        fqdn = '[{fqdn}]'.format(**locals())

    expect_fallback_response_over_plain_http = (
        (
            adapter_type == 'pyopenssl'
        )
    )
    if expect_fallback_response_over_plain_http:
        resp = requests.get(
            'http://{host!s}:{port!s}/'.format(host=fqdn, port=port),
            timeout=http_request_timeout,
        )
        assert resp.status_code == 400
        assert resp.text == (
            'The client sent a plain HTTP request, '
            'but this server only speaks HTTPS on this port.'
        )
        return

    with pytest.raises(requests.exceptions.ConnectionError) as ssl_err:
        requests.get(  # FIXME: make stdlib ssl behave like PyOpenSSL
            'http://{host!s}:{port!s}/'.format(host=fqdn, port=port),
            timeout=http_request_timeout,
        )

    if IS_LINUX:
        expected_error_code, expected_error_text = (
            104, 'Connection reset by peer',
        )
    if IS_MACOS:
        expected_error_code, expected_error_text = (
            54, 'Connection reset by peer',
        )
    if IS_WINDOWS:
        expected_error_code, expected_error_text = (
            10054,
            'An existing connection was forcibly closed by the remote host',
        )

    underlying_error = ssl_err.value.args[0].args[-1]
    err_text = str(underlying_error)
    assert underlying_error.errno == expected_error_code, (
        'The underlying error is {underlying_error!r}'.
        format(**locals())
    )
    assert expected_error_text in err_text
