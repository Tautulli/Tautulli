# This file is part of the musicbrainzngs library
# Copyright (C) Alastair Porter, Adrian Sampson, and others
# This file is distributed under a BSD-2-Clause type license.
# See the COPYING file for more information.

import sys
import locale
import xml.etree.ElementTree as ET

from . import compat

def _unicode(string, encoding=None):
    """Try to decode byte strings to unicode.
    This can only be a guess, but this might be better than failing.
    It is safe to use this on numbers or strings that are already unicode.
    """
    if isinstance(string, compat.unicode):
        unicode_string = string
    elif isinstance(string, compat.bytes):
        # use given encoding, stdin, preferred until something != None is found
        if encoding is None:
            encoding = sys.stdin.encoding
        if encoding is None:
            encoding = locale.getpreferredencoding()
        unicode_string = string.decode(encoding, "ignore")
    else:
        unicode_string = compat.unicode(string)
    return unicode_string.replace('\x00', '').strip()

def bytes_to_elementtree(bytes_or_file):
	"""Given a bytestring or a file-like object that will produce them,
	parse and return an ElementTree.
	"""
	if isinstance(bytes_or_file, compat.basestring):
		s = bytes_or_file
	else:
		s = bytes_or_file.read()

	if compat.is_py3:
		s = _unicode(s, "utf-8")

	f = compat.StringIO(s)
	tree = ET.ElementTree(file=f)
	return tree
