"""Utilities to manage open connections."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import io
import os
import socket
import threading
import time

from . import errors
from ._compat import selectors
from ._compat import suppress
from ._compat import IS_WINDOWS
from .makefile import MakeFile

import six

try:
    import fcntl
except ImportError:
    try:
        from ctypes import windll, WinError
        import ctypes.wintypes
        _SetHandleInformation = windll.kernel32.SetHandleInformation
        _SetHandleInformation.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD,
        ]
        _SetHandleInformation.restype = ctypes.wintypes.BOOL
    except ImportError:
        def prevent_socket_inheritance(sock):
            """Stub inheritance prevention.

            Dummy function, since neither fcntl nor ctypes are available.
            """
            pass
    else:
        def prevent_socket_inheritance(sock):
            """Mark the given socket fd as non-inheritable (Windows)."""
            if not _SetHandleInformation(sock.fileno(), 1, 0):
                raise WinError()
else:
    def prevent_socket_inheritance(sock):
        """Mark the given socket fd as non-inheritable (POSIX)."""
        fd = sock.fileno()
        old_flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC)


class _ThreadsafeSelector:
    """Thread-safe wrapper around a DefaultSelector.

    There are 2 thread contexts in which it may be accessed:
      * the selector thread
      * one of the worker threads in workers/threadpool.py

    The expected read/write patterns are:
      * :py:func:`~iter`: selector thread
      * :py:meth:`register`: selector thread and threadpool,
        via :py:meth:`~cheroot.workers.threadpool.ThreadPool.put`
      * :py:meth:`unregister`: selector thread only

    Notably, this means :py:class:`_ThreadsafeSelector` never needs to worry
    that connections will be removed behind its back.

    The lock is held when iterating or modifying the selector but is not
    required when :py:meth:`select()ing <selectors.BaseSelector.select>` on it.
    """

    def __init__(self):
        self._selector = selectors.DefaultSelector()
        self._lock = threading.Lock()

    def __len__(self):
        with self._lock:
            return len(self._selector.get_map() or {})

    @property
    def connections(self):
        """Retrieve connections registered with the selector."""
        with self._lock:
            mapping = self._selector.get_map() or {}
            for _, (_, sock_fd, _, conn) in mapping.items():
                yield (sock_fd, conn)

    def register(self, fileobj, events, data=None):
        """Register ``fileobj`` with the selector."""
        with self._lock:
            return self._selector.register(fileobj, events, data)

    def unregister(self, fileobj):
        """Unregister ``fileobj`` from the selector."""
        with self._lock:
            return self._selector.unregister(fileobj)

    def select(self, timeout=None):
        """Return socket fd and data pairs from selectors.select call.

        Returns entries ready to read in the form:
            (socket_file_descriptor, connection)
        """
        return (
            (key.fd, key.data)
            for key, _ in self._selector.select(timeout=timeout)
        )

    def close(self):
        """Close the selector."""
        with self._lock:
            self._selector.close()


class ConnectionManager:
    """Class which manages HTTPConnection objects.

    This is for connections which are being kept-alive for follow-up requests.
    """

    def __init__(self, server):
        """Initialize ConnectionManager object.

        Args:
            server (cheroot.server.HTTPServer): web server object
                that uses this ConnectionManager instance.
        """
        self._serving = False
        self._stop_requested = False

        self.server = server
        self._selector = _ThreadsafeSelector()

        self._selector.register(
            server.socket.fileno(),
            selectors.EVENT_READ, data=server,
        )

    def put(self, conn):
        """Put idle connection into the ConnectionManager to be managed.

        :param conn: HTTP connection to be managed
        :type conn: cheroot.server.HTTPConnection
        """
        conn.last_used = time.time()
        # if this conn doesn't have any more data waiting to be read,
        # register it with the selector.
        if conn.rfile.has_data():
            self.server.process_conn(conn)
        else:
            self._selector.register(
                conn.socket.fileno(), selectors.EVENT_READ, data=conn,
            )

    def _expire(self, threshold):
        r"""Expire least recently used connections.

        :param threshold: Connections that have not been used within this \
                          duration (in seconds), are considered expired and \
                          are closed and removed.
        :type threshold: float

        This should be called periodically.
        """
        # find any connections still registered with the selector
        # that have not been active recently enough.
        timed_out_connections = [
            (sock_fd, conn)
            for (sock_fd, conn) in self._selector.connections
            if conn != self.server and conn.last_used < threshold
        ]
        for sock_fd, conn in timed_out_connections:
            self._selector.unregister(sock_fd)
            conn.close()

    def stop(self):
        """Stop the selector loop in run() synchronously.

        May take up to half a second.
        """
        self._stop_requested = True
        while self._serving:
            time.sleep(0.01)

    def run(self, expiration_interval):
        """Run the connections selector indefinitely.

        Args:
            expiration_interval (float): Interval, in seconds, at which
                connections will be checked for expiration.

        Connections that are ready to process are submitted via
        self.server.process_conn()

        Connections submitted for processing must be `put()`
        back if they should be examined again for another request.

        Can be shut down by calling `stop()`.
        """
        self._serving = True
        try:
            self._run(expiration_interval)
        finally:
            self._serving = False

    def _run(self, expiration_interval):
        r"""Run connection handler loop until stop was requested.

        :param expiration_interval: Interval, in seconds, at which \
                                    connections will be checked for \
                                    expiration.
        :type expiration_interval: float

        Use ``expiration_interval`` as ``select()`` timeout
        to assure expired connections are closed in time.

        On Windows cap the timeout to 0.05 seconds
        as ``select()`` does not return when a socket is ready.
        """
        last_expiration_check = time.time()
        if IS_WINDOWS:
            # 0.05 seconds are used as an empirically obtained balance between
            # max connection delay and idle system load. Benchmarks show a
            # mean processing time per connection of ~0.03 seconds on Linux
            # and with 0.01 seconds timeout on Windows:
            # https://github.com/cherrypy/cheroot/pull/352
            # While this highly depends on system and hardware, 0.05 seconds
            # max delay should hence usually not significantly increase the
            # mean time/delay per connection, but significantly reduce idle
            # system load by reducing socket loops to 1/5 with 0.01 seconds.
            select_timeout = min(expiration_interval, 0.05)
        else:
            select_timeout = expiration_interval

        while not self._stop_requested:
            try:
                active_list = self._selector.select(timeout=select_timeout)
            except OSError:
                self._remove_invalid_sockets()
                continue

            for (sock_fd, conn) in active_list:
                if conn is self.server:
                    # New connection
                    new_conn = self._from_server_socket(self.server.socket)
                    if new_conn is not None:
                        self.server.process_conn(new_conn)
                else:
                    # unregister connection from the selector until the server
                    # has read from it and returned it via put()
                    self._selector.unregister(sock_fd)
                    self.server.process_conn(conn)

            now = time.time()
            if (now - last_expiration_check) > expiration_interval:
                self._expire(threshold=now - self.server.timeout)
                last_expiration_check = now

    def _remove_invalid_sockets(self):
        """Clean up the resources of any broken connections.

        This method attempts to detect any connections in an invalid state,
        unregisters them from the selector and closes the file descriptors of
        the corresponding network sockets where possible.
        """
        invalid_conns = []
        for sock_fd, conn in self._selector.connections:
            if conn is self.server:
                continue

            try:
                os.fstat(sock_fd)
            except OSError:
                invalid_conns.append((sock_fd, conn))

        for sock_fd, conn in invalid_conns:
            self._selector.unregister(sock_fd)
            # One of the reason on why a socket could cause an error
            # is that the socket is already closed, ignore the
            # socket error if we try to close it at this point.
            # This is equivalent to OSError in Py3
            with suppress(socket.error):
                conn.close()

    def _from_server_socket(self, server_socket):  # noqa: C901  # FIXME
        try:
            s, addr = server_socket.accept()
            if self.server.stats['Enabled']:
                self.server.stats['Accepts'] += 1
            prevent_socket_inheritance(s)
            if hasattr(s, 'settimeout'):
                s.settimeout(self.server.timeout)

            mf = MakeFile
            ssl_env = {}
            # if ssl cert and key are set, we try to be a secure HTTP server
            if self.server.ssl_adapter is not None:
                try:
                    s, ssl_env = self.server.ssl_adapter.wrap(s)
                except errors.NoSSLError:
                    msg = (
                        'The client sent a plain HTTP request, but '
                        'this server only speaks HTTPS on this port.'
                    )
                    buf = [
                        '%s 400 Bad Request\r\n' % self.server.protocol,
                        'Content-Length: %s\r\n' % len(msg),
                        'Content-Type: text/plain\r\n\r\n',
                        msg,
                    ]

                    sock_to_make = s if not six.PY2 else s._sock
                    wfile = mf(sock_to_make, 'wb', io.DEFAULT_BUFFER_SIZE)
                    try:
                        wfile.write(''.join(buf).encode('ISO-8859-1'))
                    except socket.error as ex:
                        if ex.args[0] not in errors.socket_errors_to_ignore:
                            raise
                    return
                if not s:
                    return
                mf = self.server.ssl_adapter.makefile
                # Re-apply our timeout since we may have a new socket object
                if hasattr(s, 'settimeout'):
                    s.settimeout(self.server.timeout)

            conn = self.server.ConnectionClass(self.server, s, mf)

            if not isinstance(
                    self.server.bind_addr,
                    (six.text_type, six.binary_type),
            ):
                # optional values
                # Until we do DNS lookups, omit REMOTE_HOST
                if addr is None:  # sometimes this can happen
                    # figure out if AF_INET or AF_INET6.
                    if len(s.getsockname()) == 2:
                        # AF_INET
                        addr = ('0.0.0.0', 0)
                    else:
                        # AF_INET6
                        addr = ('::', 0)
                conn.remote_addr = addr[0]
                conn.remote_port = addr[1]

            conn.ssl_env = ssl_env
            return conn

        except socket.timeout:
            # The only reason for the timeout in start() is so we can
            # notice keyboard interrupts on Win32, which don't interrupt
            # accept() by default
            return
        except socket.error as ex:
            if self.server.stats['Enabled']:
                self.server.stats['Socket Errors'] += 1
            if ex.args[0] in errors.socket_error_eintr:
                # I *think* this is right. EINTR should occur when a signal
                # is received during the accept() call; all docs say retry
                # the call, and I *think* I'm reading it right that Python
                # will then go ahead and poll for and handle the signal
                # elsewhere. See
                # https://github.com/cherrypy/cherrypy/issues/707.
                return
            if ex.args[0] in errors.socket_errors_nonblocking:
                # Just try again. See
                # https://github.com/cherrypy/cherrypy/issues/479.
                return
            if ex.args[0] in errors.socket_errors_to_ignore:
                # Our socket was closed.
                # See https://github.com/cherrypy/cherrypy/issues/686.
                return
            raise

    def close(self):
        """Close all monitored connections."""
        for (_, conn) in self._selector.connections:
            if conn is not self.server:  # server closes its own socket
                conn.close()
        self._selector.close()

    @property
    def _num_connections(self):
        """Return the current number of connections.

        Includes all connections registered with the selector,
        minus one for the server socket, which is always registered
        with the selector.
        """
        return len(self._selector) - 1

    @property
    def can_add_keepalive_connection(self):
        """Flag whether it is allowed to add a new keep-alive connection."""
        ka_limit = self.server.keep_alive_conn_limit
        return ka_limit is None or self._num_connections < ka_limit
