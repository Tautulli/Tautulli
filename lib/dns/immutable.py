# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

import collections.abc
import sys

# pylint: disable=unused-import
if sys.version_info >= (3, 7):
    odict = dict
    from dns._immutable_ctx import immutable
else:
    # pragma: no cover
    from collections import OrderedDict as odict
    from dns._immutable_attr import immutable  # noqa
# pylint: enable=unused-import


@immutable
class Dict(collections.abc.Mapping):
    def __init__(self, dictionary, no_copy=False):
        """Make an immutable dictionary from the specified dictionary.

        If *no_copy* is `True`, then *dictionary* will be wrapped instead
        of copied.  Only set this if you are sure there will be no external
        references to the dictionary.
        """
        if no_copy and isinstance(dictionary, odict):
            self._odict = dictionary
        else:
            self._odict = odict(dictionary)
        self._hash = None

    def __getitem__(self, key):
        return self._odict.__getitem__(key)

    def __hash__(self):  # pylint: disable=invalid-hash-returned
        if self._hash is None:
            h = 0
            for key in sorted(self._odict.keys()):
                h ^= hash(key)
            object.__setattr__(self, '_hash', h)
        # this does return an int, but pylint doesn't figure that out
        return self._hash

    def __len__(self):
        return len(self._odict)

    def __iter__(self):
        return iter(self._odict)


def constify(o):
    """
    Convert mutable types to immutable types.
    """
    if isinstance(o, bytearray):
        return bytes(o)
    if isinstance(o, tuple):
        try:
            hash(o)
            return o
        except Exception:
            return tuple(constify(elt) for elt in o)
    if isinstance(o, list):
        return tuple(constify(elt) for elt in o)
    if isinstance(o, dict):
        cdict = odict()
        for k, v in o.items():
            cdict[k] = constify(v)
        return Dict(cdict, True)
    return o
