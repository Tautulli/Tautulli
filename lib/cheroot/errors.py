"""Collection of exceptions raised and/or processed by Cheroot."""

import errno
import sys


class MaxSizeExceeded(Exception):
    """Exception raised when a client sends more data then allowed under limit.

    Depends on ``request.body.maxbytes`` config option if used within CherryPy.
    """


class NoSSLError(Exception):
    """Exception raised when a client speaks HTTP to an HTTPS socket."""


class FatalSSLAlert(Exception):
    """Exception raised when the SSL implementation signals a fatal alert."""


def plat_specific_errors(*errnames):
    """Return error numbers for all errors in ``errnames`` on this platform.

    The :py:mod:`errno` module contains different global constants
    depending on the specific platform (OS). This function will return
    the list of numeric values for a given list of potential names.
    """
    missing_attr = {None}
    unique_nums = {getattr(errno, k, None) for k in errnames}
    return list(unique_nums - missing_attr)


socket_error_eintr = plat_specific_errors('EINTR', 'WSAEINTR')

socket_errors_to_ignore = plat_specific_errors(
    'EPIPE',
    'EBADF',
    'WSAEBADF',
    'ENOTSOCK',
    'WSAENOTSOCK',
    'ETIMEDOUT',
    'WSAETIMEDOUT',
    'ECONNREFUSED',
    'WSAECONNREFUSED',
    'ECONNRESET',
    'WSAECONNRESET',
    'ECONNABORTED',
    'WSAECONNABORTED',
    'ENETRESET',
    'WSAENETRESET',
    'EHOSTDOWN',
    'EHOSTUNREACH',
)
socket_errors_to_ignore.append('timed out')
socket_errors_to_ignore.append('The read operation timed out')
socket_errors_nonblocking = plat_specific_errors(
    'EAGAIN',
    'EWOULDBLOCK',
    'WSAEWOULDBLOCK',
)

if sys.platform == 'darwin':
    socket_errors_to_ignore.extend(plat_specific_errors('EPROTOTYPE'))
    socket_errors_nonblocking.extend(plat_specific_errors('EPROTOTYPE'))


acceptable_sock_shutdown_error_codes = {
    errno.ENOTCONN,
    errno.EPIPE,
    errno.ESHUTDOWN,  # corresponds to BrokenPipeError in Python 3
    errno.ECONNRESET,  # corresponds to ConnectionResetError in Python 3
}
"""Errors that may happen during the connection close sequence.

* ENOTCONN — client is no longer connected
* EPIPE — write on a pipe while the other end has been closed
* ESHUTDOWN — write on a socket which has been shutdown for writing
* ECONNRESET — connection is reset by the peer, we received a TCP RST packet

Refs:
* https://github.com/cherrypy/cheroot/issues/341#issuecomment-735884889
* https://bugs.python.org/issue30319
* https://bugs.python.org/issue30329
* https://github.com/python/cpython/commit/83a2c28
* https://github.com/python/cpython/blob/c39b52f/Lib/poplib.py#L297-L302
* https://docs.microsoft.com/windows/win32/api/winsock/nf-winsock-shutdown
"""

acceptable_sock_shutdown_exceptions = (BrokenPipeError, ConnectionResetError)
