"""Utilities to manage open connections."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import io
import os
import select
import socket
import time

from . import errors
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
        self.server = server
        self.connections = []

    def put(self, conn):
        """Put idle connection into the ConnectionManager to be managed.

        Args:
            conn (cheroot.server.HTTPConnection): HTTP connection
                to be managed.
        """
        conn.last_used = time.time()
        conn.ready_with_data = conn.rfile.has_data()
        self.connections.append(conn)

    def expire(self):
        """Expire least recently used connections.

        This happens if there are either too many open connections, or if the
        connections have been timed out.

        This should be called periodically.
        """
        if not self.connections:
            return

        # Look at the first connection - if it can be closed, then do
        # that, and wait for get_conn to return it.
        conn = self.connections[0]
        if conn.closeable:
            return

        # Too many connections?
        ka_limit = self.server.keep_alive_conn_limit
        if ka_limit is not None and len(self.connections) > ka_limit:
            conn.closeable = True
            return

        # Connection too old?
        if (conn.last_used + self.server.timeout) < time.time():
            conn.closeable = True
            return

    def get_conn(self, server_socket):
        """Return a HTTPConnection object which is ready to be handled.

        A connection returned by this method should be ready for a worker
        to handle it. If there are no connections ready, None will be
        returned.

        Any connection returned by this method will need to be `put`
        back if it should be examined again for another request.

        Args:
            server_socket (socket.socket): Socket to listen to for new
            connections.
        Returns:
            cheroot.server.HTTPConnection instance, or None.

        """
        # Grab file descriptors from sockets, but stop if we find a
        # connection which is already marked as ready.
        socket_dict = {}
        for conn in self.connections:
            if conn.closeable or conn.ready_with_data:
                break
            socket_dict[conn.socket.fileno()] = conn
        else:
            # No ready connection.
            conn = None

        # We have a connection ready for use.
        if conn:
            self.connections.remove(conn)
            return conn

        # Will require a select call.
        ss_fileno = server_socket.fileno()
        socket_dict[ss_fileno] = server_socket
        try:
            rlist, _, _ = select.select(list(socket_dict), [], [], 0.1)
            # No available socket.
            if not rlist:
                return None
        except OSError:
            # Mark any connection which no longer appears valid.
            for fno, conn in list(socket_dict.items()):
                # If the server socket is invalid, we'll just ignore it and
                # wait to be shutdown.
                if fno == ss_fileno:
                    continue
                try:
                    os.fstat(fno)
                except OSError:
                    # Socket is invalid, close the connection, insert at
                    # the front.
                    self.connections.remove(conn)
                    self.connections.insert(0, conn)
                    conn.closeable = True

            # Wait for the next tick to occur.
            return None

        try:
            # See if we have a new connection coming in.
            rlist.remove(ss_fileno)
        except ValueError:
            # No new connection, but reuse existing socket.
            conn = socket_dict[rlist.pop()]
        else:
            conn = server_socket

        # All remaining connections in rlist should be marked as ready.
        for fno in rlist:
            socket_dict[fno].ready_with_data = True

        # New connection.
        if conn is server_socket:
            return self._from_server_socket(server_socket)

        self.connections.remove(conn)
        return conn

    def _from_server_socket(self, server_socket):
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
        for conn in self.connections[:]:
            conn.close()
        self.connections = []
