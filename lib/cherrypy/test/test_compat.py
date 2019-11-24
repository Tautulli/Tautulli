"""Test Python 2/3 compatibility module."""
from __future__ import unicode_literals

import unittest

import pytest
import six

from cherrypy import _cpcompat as compat


class StringTester(unittest.TestCase):
    """Tests for string conversion."""

    @pytest.mark.skipif(six.PY3, reason='Only useful on Python 2')
    def test_ntob_non_native(self):
        """ntob should raise an Exception on unicode.

        (Python 2 only)

        See #1132 for discussion.
        """
        self.assertRaises(TypeError, compat.ntob, 'fight')


class EscapeTester(unittest.TestCase):
    """Class to test escape_html function from _cpcompat."""

    def test_escape_quote(self):
        """test_escape_quote - Verify the output for &<>"' chars."""
        self.assertEqual(
            """xx&amp;&lt;&gt;"aa'""",
            compat.escape_html("""xx&<>"aa'"""),
        )
