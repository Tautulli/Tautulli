"""Compatibility code for using CherryPy with various versions of Python.

To retain compatibility with older Python versions, this module provides a
useful abstraction over the differences between Python versions, sometimes by
preferring a newer idiom, sometimes an older one, and sometimes a custom one.

In particular, Python 2 uses str and '' for byte strings, while Python 3
uses str and '' for unicode strings. We will call each of these the 'native
string' type for each version. Because of this major difference, this module
provides
two functions: 'ntob', which translates native strings (of type 'str') into
byte strings regardless of Python version, and 'ntou', which translates native
strings to unicode strings.

Try not to use the compatibility functions 'ntob', 'ntou', 'tonative'.
They were created with Python 2.3-2.5 compatibility in mind.
Instead, use unicode literals (from __future__) and bytes literals
and their .encode/.decode methods as needed.
"""

import re
import sys
import threading

import six
from six.moves import urllib


if six.PY3:
    def ntob(n, encoding='ISO-8859-1'):
        """Return the given native string as a byte string in the given
        encoding.
        """
        assert_native(n)
        # In Python 3, the native string type is unicode
        return n.encode(encoding)

    def ntou(n, encoding='ISO-8859-1'):
        """Return the given native string as a unicode string with the given
        encoding.
        """
        assert_native(n)
        # In Python 3, the native string type is unicode
        return n

    def tonative(n, encoding='ISO-8859-1'):
        """Return the given string as a native string in the given encoding."""
        # In Python 3, the native string type is unicode
        if isinstance(n, bytes):
            return n.decode(encoding)
        return n
else:
    # Python 2
    def ntob(n, encoding='ISO-8859-1'):
        """Return the given native string as a byte string in the given
        encoding.
        """
        assert_native(n)
        # In Python 2, the native string type is bytes. Assume it's already
        # in the given encoding, which for ISO-8859-1 is almost always what
        # was intended.
        return n

    def ntou(n, encoding='ISO-8859-1'):
        """Return the given native string as a unicode string with the given
        encoding.
        """
        assert_native(n)
        # In Python 2, the native string type is bytes.
        # First, check for the special encoding 'escape'. The test suite uses
        # this to signal that it wants to pass a string with embedded \uXXXX
        # escapes, but without having to prefix it with u'' for Python 2,
        # but no prefix for Python 3.
        if encoding == 'escape':
            return six.text_type(  # unicode for Python 2
                re.sub(r'\\u([0-9a-zA-Z]{4})',
                       lambda m: six.unichr(int(m.group(1), 16)),
                       n.decode('ISO-8859-1')))
        # Assume it's already in the given encoding, which for ISO-8859-1
        # is almost always what was intended.
        return n.decode(encoding)

    def tonative(n, encoding='ISO-8859-1'):
        """Return the given string as a native string in the given encoding."""
        # In Python 2, the native string type is bytes.
        if isinstance(n, six.text_type):  # unicode for Python 2
            return n.encode(encoding)
        return n


def assert_native(n):
    if not isinstance(n, str):
        raise TypeError('n must be a native str (got %s)' % type(n).__name__)


# Some platforms don't expose HTTPSConnection, so handle it separately
HTTPSConnection = getattr(six.moves.http_client, 'HTTPSConnection', None)


def _unquote_plus_compat(string, encoding='utf-8', errors='replace'):
    return urllib.parse.unquote_plus(string).decode(encoding, errors)


def _unquote_compat(string, encoding='utf-8', errors='replace'):
    return urllib.parse.unquote(string).decode(encoding, errors)


def _quote_compat(string, encoding='utf-8', errors='replace'):
    return urllib.parse.quote(string.encode(encoding, errors))


unquote_plus = urllib.parse.unquote_plus if six.PY3 else _unquote_plus_compat
unquote = urllib.parse.unquote if six.PY3 else _unquote_compat
quote = urllib.parse.quote if six.PY3 else _quote_compat

try:
    # Prefer simplejson
    import simplejson as json
except ImportError:
    import json


json_decode = json.JSONDecoder().decode
_json_encode = json.JSONEncoder().iterencode


if six.PY3:
    # Encode to bytes on Python 3
    def json_encode(value):
        for chunk in _json_encode(value):
            yield chunk.encode('utf-8')
else:
    json_encode = _json_encode


text_or_bytes = six.text_type, bytes


if sys.version_info >= (3, 3):
    Timer = threading.Timer
    Event = threading.Event
else:
    # Python 3.2 and earlier
    Timer = threading._Timer
    Event = threading._Event

# html module come in 3.2 version
try:
    from html import escape
except ImportError:
    from cgi import escape


# html module needed the argument quote=False because in cgi the default
# is False. With quote=True the results differ.

def escape_html(s, escape_quote=False):
    """Replace special characters "&", "<" and ">" to HTML-safe sequences.

    When escape_quote=True, escape (') and (") chars.
    """
    return escape(s, quote=escape_quote)
