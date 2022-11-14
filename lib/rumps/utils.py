# -*- coding: utf-8 -*-

"""
rumps.utils
~~~~~~~~~~~

Generic container classes and utility functions.

:copyright: (c) 2020 by Jared Suttles
:license: BSD-3-Clause, see LICENSE for details.
"""

from .packages.ordereddict import OrderedDict as _OrderedDict


# ListDict: OrderedDict subclass with insertion methods for modifying the order of the linked list in O(1) time
# https://gist.github.com/jaredks/6276032
class ListDict(_OrderedDict):
    def __insertion(self, link_prev, key_value):
        key, value = key_value
        if link_prev[2] != key:
            if key in self:
                del self[key]
            link_next = link_prev[1]
            self._OrderedDict__map[key] = link_prev[1] = link_next[0] = [link_prev, link_next, key]
        dict.__setitem__(self, key, value)

    def insert_after(self, existing_key, key_value):
        self.__insertion(self._OrderedDict__map[existing_key], key_value)

    def insert_before(self, existing_key, key_value):
        self.__insertion(self._OrderedDict__map[existing_key][0], key_value)
