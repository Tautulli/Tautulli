"""Collection of exceptions raised and/or processed by Cheroot."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import errno
import sys


class MaxSizeExceeded(Exception):
    """Exception raised when a client sends more data then acceptable within limit.

    Depends on ``request.body.maxbytes`` config option if used within CherryPy
    """


class NoSSLError(Exception):
    """Exception raised when a client speaks HTTP to an HTTPS socket."""


class FatalSSLAlert(Exception):
    """Exception raised when the SSL implementation signals a fatal alert."""


def plat_specific_errors(*errnames):
    """Return error numbers for all errors in errnames on this platform.

    The 'errno' module contains different global constants depending on
    the specific platform (OS). This function will return the list of
    numeric values for a given list of potential names.
    """
    missing_attr = set([None, ])
    unique_nums = set(getattr(errno, k, None) for k in errnames)
    return list(unique_nums - missing_attr)


socket_error_eintr = plat_specific_errors('EINTR', 'WSAEINTR')

socket_errors_to_ignore = plat_specific_errors(
    'EPIPE',
    'EBADF', 'WSAEBADF',
    'ENOTSOCK', 'WSAENOTSOCK',
    'ETIMEDOUT', 'WSAETIMEDOUT',
    'ECONNREFUSED', 'WSAECONNREFUSED',
    'ECONNRESET', 'WSAECONNRESET',
    'ECONNABORTED', 'WSAECONNABORTED',
    'ENETRESET', 'WSAENETRESET',
    'EHOSTDOWN', 'EHOSTUNREACH',
)
socket_errors_to_ignore.append('timed out')
socket_errors_to_ignore.append('The read operation timed out')
socket_errors_nonblocking = plat_specific_errors(
    'EAGAIN', 'EWOULDBLOCK', 'WSAEWOULDBLOCK',
)

if sys.platform == 'darwin':
    socket_errors_to_ignore.extend(plat_specific_errors('EPROTOTYPE'))
    socket_errors_nonblocking.extend(plat_specific_errors('EPROTOTYPE'))
