"""
JSON support.

Expose preferred json module as json and provide encode/decode
convenience functions.
"""

try:
    # Prefer simplejson
    import simplejson as json
except ImportError:
    import json


__all__ = ['json', 'encode', 'decode']


decode = json.JSONDecoder().decode
_encode = json.JSONEncoder().iterencode


def encode(value):
    """Encode to bytes."""
    for chunk in _encode(value):
        yield chunk.encode('utf-8')
