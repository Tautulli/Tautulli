# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.


class Metadata(object):
    """An abstract dict-like object.

    Metadata is the base class for many of the tag objects in Mutagen.
    """

    __module__ = "mutagen"

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            self.load(*args, **kwargs)

    def load(self, *args, **kwargs):
        raise NotImplementedError

    def save(self, filename=None):
        """Save changes to a file."""

        raise NotImplementedError

    def delete(self, filename=None):
        """Remove tags from a file."""

        raise NotImplementedError
