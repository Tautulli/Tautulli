# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2003-2017 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import itertools
import sys

if sys.version_info >= (3, 7):
    odict = dict
else:
    from collections import OrderedDict as odict  # pragma: no cover

class Set:

    """A simple set class.

    This class was originally used to deal with sets being missing in
    ancient versions of python, but dnspython will continue to use it
    as these sets are based on lists and are thus indexable, and this
    ability is widely used in dnspython applications.
    """

    __slots__ = ['items']

    def __init__(self, items=None):
        """Initialize the set.

        *items*, an iterable or ``None``, the initial set of items.
        """

        self.items = odict()
        if items is not None:
            for item in items:
                self.add(item)

    def __repr__(self):
        return "dns.set.Set(%s)" % repr(list(self.items.keys()))

    def add(self, item):
        """Add an item to the set.
        """

        if item not in self.items:
            self.items[item] = None

    def remove(self, item):
        """Remove an item from the set.
        """

        try:
            del self.items[item]
        except KeyError:
            raise ValueError

    def discard(self, item):
        """Remove an item from the set if present.
        """

        self.items.pop(item, None)

    def _clone(self):
        """Make a (shallow) copy of the set.

        There is a 'clone protocol' that subclasses of this class
        should use.  To make a copy, first call your super's _clone()
        method, and use the object returned as the new instance.  Then
        make shallow copies of the attributes defined in the subclass.

        This protocol allows us to write the set algorithms that
        return new instances (e.g. union) once, and keep using them in
        subclasses.
        """

        if hasattr(self, '_clone_class'):
            cls = self._clone_class
        else:
            cls = self.__class__
        obj = cls.__new__(cls)
        obj.items = odict()
        obj.items.update(self.items)
        return obj

    def __copy__(self):
        """Make a (shallow) copy of the set.
        """

        return self._clone()

    def copy(self):
        """Make a (shallow) copy of the set.
        """

        return self._clone()

    def union_update(self, other):
        """Update the set, adding any elements from other which are not
        already in the set.
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        if self is other:
            return
        for item in other.items:
            self.add(item)

    def intersection_update(self, other):
        """Update the set, removing any elements from other which are not
        in both sets.
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        if self is other:
            return
        # we make a copy of the list so that we can remove items from
        # the list without breaking the iterator.
        for item in list(self.items):
            if item not in other.items:
                del self.items[item]

    def difference_update(self, other):
        """Update the set, removing any elements from other which are in
        the set.
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        if self is other:
            self.items.clear()
        else:
            for item in other.items:
                self.discard(item)

    def union(self, other):
        """Return a new set which is the union of ``self`` and ``other``.

        Returns the same Set type as this set.
        """

        obj = self._clone()
        obj.union_update(other)
        return obj

    def intersection(self, other):
        """Return a new set which is the intersection of ``self`` and
        ``other``.

        Returns the same Set type as this set.
        """

        obj = self._clone()
        obj.intersection_update(other)
        return obj

    def difference(self, other):
        """Return a new set which ``self`` - ``other``, i.e. the items
        in ``self`` which are not also in ``other``.

        Returns the same Set type as this set.
        """

        obj = self._clone()
        obj.difference_update(other)
        return obj

    def __or__(self, other):
        return self.union(other)

    def __and__(self, other):
        return self.intersection(other)

    def __add__(self, other):
        return self.union(other)

    def __sub__(self, other):
        return self.difference(other)

    def __ior__(self, other):
        self.union_update(other)
        return self

    def __iand__(self, other):
        self.intersection_update(other)
        return self

    def __iadd__(self, other):
        self.union_update(other)
        return self

    def __isub__(self, other):
        self.difference_update(other)
        return self

    def update(self, other):
        """Update the set, adding any elements from other which are not
        already in the set.

        *other*, the collection of items with which to update the set, which
        may be any iterable type.
        """

        for item in other:
            self.add(item)

    def clear(self):
        """Make the set empty."""
        self.items.clear()

    def __eq__(self, other):
        if odict == dict:
            return self.items == other.items
        else:
            # We don't want an ordered comparison.
            if len(self.items) != len(other.items):
                return False
            return all(elt in other.items for elt in self.items)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return list(itertools.islice(self.items, i.start, i.stop, i.step))
        else:
            return next(itertools.islice(self.items, i, i + 1))

    def __delitem__(self, i):
        if isinstance(i, slice):
            for elt in list(self[i]):
                del self.items[elt]
        else:
            del self.items[self[i]]

    def issubset(self, other):
        """Is this set a subset of *other*?

        Returns a ``bool``.
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        for item in self.items:
            if item not in other.items:
                return False
        return True

    def issuperset(self, other):
        """Is this set a superset of *other*?

        Returns a ``bool``.
        """

        if not isinstance(other, Set):
            raise ValueError('other must be a Set instance')
        for item in other.items:
            if item not in self.items:
                return False
        return True
