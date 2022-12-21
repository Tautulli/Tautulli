"""High-performance, pure-Python HTTP server used by CherryPy."""

try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # noqa: WPS440


try:
    __version__ = metadata.version('cheroot')
except Exception:
    __version__ = 'unknown'
