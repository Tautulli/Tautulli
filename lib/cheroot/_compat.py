"""Compatibility code for using Cheroot with various versions of Python."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import platform
import re

import six

try:
    import ssl
    IS_ABOVE_OPENSSL10 = ssl.OPENSSL_VERSION_INFO >= (1, 1)
    del ssl
except ImportError:
    IS_ABOVE_OPENSSL10 = None


IS_PYPY = platform.python_implementation() == 'PyPy'


SYS_PLATFORM = platform.system()
IS_WINDOWS = SYS_PLATFORM == 'Windows'
IS_LINUX = SYS_PLATFORM == 'Linux'
IS_MACOS = SYS_PLATFORM == 'Darwin'

PLATFORM_ARCH = platform.machine()
IS_PPC = PLATFORM_ARCH.startswith('ppc')


if not six.PY2:
    def ntob(n, encoding='ISO-8859-1'):
        """Return the native string as bytes in the given encoding."""
        assert_native(n)
        # In Python 3, the native string type is unicode
        return n.encode(encoding)

    def ntou(n, encoding='ISO-8859-1'):
        """Return the native string as unicode with the given encoding."""
        assert_native(n)
        # In Python 3, the native string type is unicode
        return n

    def bton(b, encoding='ISO-8859-1'):
        """Return the byte string as native string in the given encoding."""
        return b.decode(encoding)
else:
    # Python 2
    def ntob(n, encoding='ISO-8859-1'):
        """Return the native string as bytes in the given encoding."""
        assert_native(n)
        # In Python 2, the native string type is bytes. Assume it's already
        # in the given encoding, which for ISO-8859-1 is almost always what
        # was intended.
        return n

    def ntou(n, encoding='ISO-8859-1'):
        """Return the native string as unicode with the given encoding."""
        assert_native(n)
        # In Python 2, the native string type is bytes.
        # First, check for the special encoding 'escape'. The test suite uses
        # this to signal that it wants to pass a string with embedded \uXXXX
        # escapes, but without having to prefix it with u'' for Python 2,
        # but no prefix for Python 3.
        if encoding == 'escape':
            return re.sub(
                r'\\u([0-9a-zA-Z]{4})',
                lambda m: six.unichr(int(m.group(1), 16)),
                n.decode('ISO-8859-1'),
            )
        # Assume it's already in the given encoding, which for ISO-8859-1
        # is almost always what was intended.
        return n.decode(encoding)

    def bton(b, encoding='ISO-8859-1'):
        """Return the byte string as native string in the given encoding."""
        return b


def assert_native(n):
    """Check whether the input is of nativ ``str`` type.

    Raises:
        TypeError: in case of failed check

    """
    if not isinstance(n, str):
        raise TypeError('n must be a native str (got %s)' % type(n).__name__)


if not six.PY2:
    """Python 3 has memoryview builtin."""
    # Python 2.7 has it backported, but socket.write() does
    # str(memoryview(b'0' * 100)) -> <memory at 0x7fb6913a5588>
    # instead of accessing it correctly.
    memoryview = memoryview
else:
    """Link memoryview to buffer under Python 2."""
    memoryview = buffer  # noqa: F821


def extract_bytes(mv):
    """Retrieve bytes out of memoryview/buffer or bytes."""
    if isinstance(mv, memoryview):
        return bytes(mv) if six.PY2 else mv.tobytes()

    if isinstance(mv, bytes):
        return mv

    raise ValueError
