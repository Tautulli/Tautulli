"""
A library for integrating :doc:`pyOpenSSL <pyopenssl:index>` with Cheroot.

The :py:mod:`OpenSSL <pyopenssl:OpenSSL>` module must be importable
for SSL/TLS/HTTPS functionality.
You can obtain it from `here <https://github.com/pyca/pyopenssl>`_.

To use this module, set :py:attr:`HTTPServer.ssl_adapter
<cheroot.server.HTTPServer.ssl_adapter>` to an instance of
:py:class:`ssl.Adapter <cheroot.ssl.Adapter>`.
There are two ways to use :abbr:`TLS (Transport-Level Security)`:

Method One
----------

 * :py:attr:`ssl_adapter.context
   <cheroot.ssl.pyopenssl.pyOpenSSLAdapter.context>`: an instance of
   :py:class:`SSL.Context <pyopenssl:OpenSSL.SSL.Context>`.

If this is not None, it is assumed to be an :py:class:`SSL.Context
<pyopenssl:OpenSSL.SSL.Context>` instance, and will be passed to
:py:class:`SSL.Connection <pyopenssl:OpenSSL.SSL.Connection>` on bind().
The developer is responsible for forming a valid :py:class:`Context
<pyopenssl:OpenSSL.SSL.Context>` object. This
approach is to be preferred for more flexibility, e.g. if the cert and
key are streams instead of files, or need decryption, or
:py:data:`SSL.SSLv3_METHOD <pyopenssl:OpenSSL.SSL.SSLv3_METHOD>`
is desired instead of the default :py:data:`SSL.SSLv23_METHOD
<pyopenssl:OpenSSL.SSL.SSLv3_METHOD>`, etc. Consult
the :doc:`pyOpenSSL <pyopenssl:api/ssl>` documentation for
complete options.

Method Two (shortcut)
---------------------

 * :py:attr:`ssl_adapter.certificate
   <cheroot.ssl.pyopenssl.pyOpenSSLAdapter.certificate>`: the file name
   of the server's TLS certificate.
 * :py:attr:`ssl_adapter.private_key
   <cheroot.ssl.pyopenssl.pyOpenSSLAdapter.private_key>`: the file name
   of the server's private key file.

Both are :py:data:`None` by default. If :py:attr:`ssl_adapter.context
<cheroot.ssl.pyopenssl.pyOpenSSLAdapter.context>` is :py:data:`None`,
but ``.private_key`` and ``.certificate`` are both given and valid, they
will be read, and the context will be automatically created from them.

.. spelling::

   pyopenssl
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import socket
import sys
import threading
import time

import six

try:
    import OpenSSL.version
    from OpenSSL import SSL
    from OpenSSL import crypto

    try:
        ssl_conn_type = SSL.Connection
    except AttributeError:
        ssl_conn_type = SSL.ConnectionType
except ImportError:
    SSL = None

from . import Adapter
from .. import errors, server as cheroot_server
from ..makefile import StreamReader, StreamWriter


class SSLFileobjectMixin:
    """Base mixin for a TLS socket stream."""

    ssl_timeout = 3
    ssl_retry = .01

    # FIXME:
    def _safe_call(self, is_reader, call, *args, **kwargs):  # noqa: C901
        """Wrap the given call with TLS error-trapping.

        is_reader: if False EOF errors will be raised. If True, EOF errors
        will return "" (to emulate normal sockets).
        """
        start = time.time()
        while True:
            try:
                return call(*args, **kwargs)
            except SSL.WantReadError:
                # Sleep and try again. This is dangerous, because it means
                # the rest of the stack has no way of differentiating
                # between a "new handshake" error and "client dropped".
                # Note this isn't an endless loop: there's a timeout below.
                # Ref: https://stackoverflow.com/a/5133568/595220
                time.sleep(self.ssl_retry)
            except SSL.WantWriteError:
                time.sleep(self.ssl_retry)
            except SSL.SysCallError as e:
                if is_reader and e.args == (-1, 'Unexpected EOF'):
                    return b''

                errnum = e.args[0]
                if is_reader and errnum in errors.socket_errors_to_ignore:
                    return b''
                raise socket.error(errnum)
            except SSL.Error as e:
                if is_reader and e.args == (-1, 'Unexpected EOF'):
                    return b''

                thirdarg = None
                try:
                    thirdarg = e.args[0][0][2]
                except IndexError:
                    pass

                if thirdarg == 'http request':
                    # The client is talking HTTP to an HTTPS server.
                    raise errors.NoSSLError()

                raise errors.FatalSSLAlert(*e.args)

            if time.time() - start > self.ssl_timeout:
                raise socket.timeout('timed out')

    def recv(self, size):
        """Receive message of a size from the socket."""
        return self._safe_call(
            True,
            super(SSLFileobjectMixin, self).recv,
            size,
        )

    def readline(self, size=-1):
        """Receive message of a size from the socket.

        Matches the following interface:
        https://docs.python.org/3/library/io.html#io.IOBase.readline
        """
        return self._safe_call(
            True,
            super(SSLFileobjectMixin, self).readline,
            size,
        )

    def sendall(self, *args, **kwargs):
        """Send whole message to the socket."""
        return self._safe_call(
            False,
            super(SSLFileobjectMixin, self).sendall,
            *args, **kwargs
        )

    def send(self, *args, **kwargs):
        """Send some part of message to the socket."""
        return self._safe_call(
            False,
            super(SSLFileobjectMixin, self).send,
            *args, **kwargs
        )


class SSLFileobjectStreamReader(SSLFileobjectMixin, StreamReader):
    """SSL file object attached to a socket object."""


class SSLFileobjectStreamWriter(SSLFileobjectMixin, StreamWriter):
    """SSL file object attached to a socket object."""


class SSLConnectionProxyMeta:
    """Metaclass for generating a bunch of proxy methods."""

    def __new__(mcl, name, bases, nmspc):
        """Attach a list of proxy methods to a new class."""
        proxy_methods = (
            'get_context', 'pending', 'send', 'write', 'recv', 'read',
            'renegotiate', 'bind', 'listen', 'connect', 'accept',
            'setblocking', 'fileno', 'close', 'get_cipher_list',
            'getpeername', 'getsockname', 'getsockopt', 'setsockopt',
            'makefile', 'get_app_data', 'set_app_data', 'state_string',
            'sock_shutdown', 'get_peer_certificate', 'want_read',
            'want_write', 'set_connect_state', 'set_accept_state',
            'connect_ex', 'sendall', 'settimeout', 'gettimeout',
            'shutdown',
        )
        proxy_methods_no_args = (
            'shutdown',
        )

        proxy_props = (
            'family',
        )

        def lock_decorator(method):
            """Create a proxy method for a new class."""
            def proxy_wrapper(self, *args):
                self._lock.acquire()
                try:
                    new_args = (
                        args[:] if method not in proxy_methods_no_args else []
                    )
                    return getattr(self._ssl_conn, method)(*new_args)
                finally:
                    self._lock.release()
            return proxy_wrapper
        for m in proxy_methods:
            nmspc[m] = lock_decorator(m)
            nmspc[m].__name__ = m

        def make_property(property_):
            """Create a proxy method for a new class."""
            def proxy_prop_wrapper(self):
                return getattr(self._ssl_conn, property_)
            proxy_prop_wrapper.__name__ = property_
            return property(proxy_prop_wrapper)
        for p in proxy_props:
            nmspc[p] = make_property(p)

        # Doesn't work via super() for some reason.
        # Falling back to type() instead:
        return type(name, bases, nmspc)


@six.add_metaclass(SSLConnectionProxyMeta)
class SSLConnection:
    r"""A thread-safe wrapper for an ``SSL.Connection``.

    :param tuple args: the arguments to create the wrapped \
                        :py:class:`SSL.Connection(*args) \
                        <pyopenssl:OpenSSL.SSL.Connection>`
    """

    def __init__(self, *args):
        """Initialize SSLConnection instance."""
        self._ssl_conn = SSL.Connection(*args)
        self._lock = threading.RLock()


class pyOpenSSLAdapter(Adapter):
    """A wrapper for integrating pyOpenSSL with Cheroot."""

    certificate = None
    """The file name of the server's TLS certificate."""

    private_key = None
    """The file name of the server's private key file."""

    certificate_chain = None
    """Optional. The file name of CA's intermediate certificate bundle.

    This is needed for cheaper "chained root" TLS certificates,
    and should be left as :py:data:`None` if not required."""

    context = None
    """
    An instance of :py:class:`SSL.Context <pyopenssl:OpenSSL.SSL.Context>`.
    """

    ciphers = None
    """The ciphers list of TLS."""

    def __init__(
            self, certificate, private_key, certificate_chain=None,
            ciphers=None,
    ):
        """Initialize OpenSSL Adapter instance."""
        if SSL is None:
            raise ImportError('You must install pyOpenSSL to use HTTPS.')

        super(pyOpenSSLAdapter, self).__init__(
            certificate, private_key, certificate_chain, ciphers,
        )

        self._environ = None

    def bind(self, sock):
        """Wrap and return the given socket."""
        if self.context is None:
            self.context = self.get_context()
        conn = SSLConnection(self.context, sock)
        self._environ = self.get_environ()
        return conn

    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        # pyOpenSSL doesn't perform the handshake until the first read/write
        # forcing the handshake to complete tends to result in the connection
        # closing so we can't reliably access protocol/client cert for the env
        return sock, self._environ.copy()

    def get_context(self):
        """Return an ``SSL.Context`` from self attributes.

        Ref: :py:class:`SSL.Context <pyopenssl:OpenSSL.SSL.Context>`
        """
        # See https://code.activestate.com/recipes/442473/
        c = SSL.Context(SSL.SSLv23_METHOD)
        c.use_privatekey_file(self.private_key)
        if self.certificate_chain:
            c.load_verify_locations(self.certificate_chain)
        c.use_certificate_file(self.certificate)
        return c

    def get_environ(self):
        """Return WSGI environ entries to be merged into each request."""
        ssl_environ = {
            'wsgi.url_scheme': 'https',
            'HTTPS': 'on',
            'SSL_VERSION_INTERFACE': '%s %s/%s Python/%s' % (
                cheroot_server.HTTPServer.version,
                OpenSSL.version.__title__, OpenSSL.version.__version__,
                sys.version,
            ),
            'SSL_VERSION_LIBRARY': SSL.SSLeay_version(
                SSL.SSLEAY_VERSION,
            ).decode(),
        }

        if self.certificate:
            # Server certificate attributes
            with open(self.certificate, 'rb') as cert_file:
                cert = crypto.load_certificate(
                    crypto.FILETYPE_PEM, cert_file.read(),
                )

            ssl_environ.update({
                'SSL_SERVER_M_VERSION': cert.get_version(),
                'SSL_SERVER_M_SERIAL': cert.get_serial_number(),
                # 'SSL_SERVER_V_START':
                #   Validity of server's certificate (start time),
                # 'SSL_SERVER_V_END':
                #   Validity of server's certificate (end time),
            })

            for prefix, dn in [
                ('I', cert.get_issuer()),
                ('S', cert.get_subject()),
            ]:
                # X509Name objects don't seem to have a way to get the
                # complete DN string. Use str() and slice it instead,
                # because str(dn) == "<X509Name object '/C=US/ST=...'>"
                dnstr = str(dn)[18:-2]

                wsgikey = 'SSL_SERVER_%s_DN' % prefix
                ssl_environ[wsgikey] = dnstr

                # The DN should be of the form: /k1=v1/k2=v2, but we must allow
                # for any value to contain slashes itself (in a URL).
                while dnstr:
                    pos = dnstr.rfind('=')
                    dnstr, value = dnstr[:pos], dnstr[pos + 1:]
                    pos = dnstr.rfind('/')
                    dnstr, key = dnstr[:pos], dnstr[pos + 1:]
                    if key and value:
                        wsgikey = 'SSL_SERVER_%s_DN_%s' % (prefix, key)
                        ssl_environ[wsgikey] = value

        return ssl_environ

    def makefile(self, sock, mode='r', bufsize=-1):
        """Return socket file object."""
        cls = (
            SSLFileobjectStreamReader
            if 'r' in mode else
            SSLFileobjectStreamWriter
        )
        if SSL and isinstance(sock, ssl_conn_type):
            wrapped_socket = cls(sock, mode, bufsize)
            wrapped_socket.ssl_timeout = sock.gettimeout()
            return wrapped_socket
        # This is from past:
        # TODO: figure out what it's meant for
        else:
            return cheroot_server.CP_fileobject(sock, mode, bufsize)
