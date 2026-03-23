"""High-performance, pure-Python HTTP server used by CherryPy."""

from importlib import metadata


try:
    __version__ = metadata.version('cheroot')
except Exception:
    __version__ = 'unknown'
