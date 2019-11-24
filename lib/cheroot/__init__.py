"""High-performance, pure-Python HTTP server used by CherryPy."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

try:
    import pkg_resources
except ImportError:
    pass


try:
    __version__ = pkg_resources.get_distribution('cheroot').version
except Exception:
    __version__ = 'unknown'
