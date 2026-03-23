# pylint: disable=unused-import
"""Compatibility code for using Cheroot with various versions of Python."""

import os
import platform


try:
    import ssl

    IS_ABOVE_OPENSSL31 = ssl.OPENSSL_VERSION_INFO > (3, 1)
    IS_ABOVE_OPENSSL10 = ssl.OPENSSL_VERSION_INFO >= (1, 1)
    del ssl
except ImportError:
    IS_ABOVE_OPENSSL31 = None
    IS_ABOVE_OPENSSL10 = None


IS_CI = bool(os.getenv('CI'))
IS_GITHUB_ACTIONS_WORKFLOW = bool(os.getenv('GITHUB_WORKFLOW'))


IS_PYPY = platform.python_implementation() == 'PyPy'


SYS_PLATFORM = platform.system()
IS_WINDOWS = SYS_PLATFORM == 'Windows'
IS_LINUX = SYS_PLATFORM == 'Linux'
IS_MACOS = SYS_PLATFORM == 'Darwin'
IS_SOLARIS = SYS_PLATFORM == 'SunOS'

PLATFORM_ARCH = platform.machine()
IS_PPC = PLATFORM_ARCH.startswith('ppc')


def ntob(n, encoding='ISO-8859-1'):
    """Return the native string as bytes in the given encoding."""
    assert_native(n)
    # In Python 3, the native string type is unicode
    return n.encode(encoding)


def ntou(n, encoding='ISO-8859-1'):
    """Return the native string as Unicode with the given encoding."""
    assert_native(n)
    # In Python 3, the native string type is unicode
    return n


def bton(b, encoding='ISO-8859-1'):
    """Return the byte string as native string in the given encoding."""
    return b.decode(encoding)


def assert_native(n):
    """Check whether the input is of native :py:class:`str` type.

    Raises:
        TypeError: in case of failed check

    """
    if not isinstance(n, str):
        raise TypeError('n must be a native str (got %s)' % type(n).__name__)


def extract_bytes(mv):
    r"""Retrieve bytes out of the given input buffer.

    :param mv: input :py:func:`buffer`
    :type mv: memoryview or bytes

    :return: unwrapped bytes
    :rtype: bytes

    :raises ValueError: if the input is not one of \
                        :py:class:`memoryview`/:py:func:`buffer` \
                        or :py:class:`bytes`
    """
    if isinstance(mv, memoryview):
        return mv.tobytes()

    if isinstance(mv, bytes):
        return mv

    raise ValueError(
        'extract_bytes() only accepts bytes and memoryview/buffer',
    )
