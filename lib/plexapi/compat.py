# -*- coding: utf-8 -*-
# Python 2/3 compatability
# Always try Py3 first
import os
from sys import version_info

ustr = str
if version_info < (3,):
    ustr = unicode

try:
    string_type = basestring
except NameError:
    string_type = str

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    from urllib.parse import quote_plus
except ImportError:
    from urllib import quote_plus

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree


def makedirs(name, mode=0o777, exist_ok=False):
    """ Mimicks os.makedirs() from Python 3. """
    try:
        os.makedirs(name, mode)
    except OSError:
        if not os.path.isdir(name) or not exist_ok:
            raise
