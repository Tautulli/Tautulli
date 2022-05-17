import re
import operator
import collections.abc
import itertools
import copy
import functools
import random

from jaraco.classes.properties import NonDataProperty
import jaraco.text


class Projection(collections.abc.Mapping):
    """
    Project a set of keys over a mapping

    >>> sample = {'a': 1, 'b': 2, 'c': 3}
    >>> prj = Projection(['a', 'c', 'd'], sample)
    >>> prj == {'a': 1, 'c': 3}
    True

    Keys should only appear if they were specified and exist in the space.

    >>> sorted(list(prj.keys()))
    ['a', 'c']

    Attempting to access a key not in the projection
    results in a KeyError.

    >>> prj['b']
    Traceback (most recent call last):
    ...
    KeyError: 'b'

    Use the projection to update another dict.

    >>> target = {'a': 2, 'b': 2}
    >>> target.update(prj)
    >>> target == {'a': 1, 'b': 2, 'c': 3}
    True

    Also note that Projection keeps a reference to the original dict, so
    if you modify the original dict, that could modify the Projection.

    >>> del sample['a']
    >>> dict(prj)
    {'c': 3}
    """

    def __init__(self, keys, space):
        self._keys = tuple(keys)
        self._space = space

    def __getitem__(self, key):
        if key not in self._keys:
            raise KeyError(key)
        return self._space[key]

    def __iter__(self):
        return iter(set(self._keys).intersection(self._space))

    def __len__(self):
        return len(tuple(iter(self)))


class DictFilter(object):
    """
    Takes a dict, and simulates a sub-dict based on the keys.

    >>> sample = {'a': 1, 'b': 2, 'c': 3}
    >>> filtered = DictFilter(sample, ['a', 'c'])
    >>> filtered == {'a': 1, 'c': 3}
    True
    >>> set(filtered.values()) == {1, 3}
    True
    >>> set(filtered.items()) == {('a', 1), ('c', 3)}
    True

    One can also filter by a regular expression pattern

    >>> sample['d'] = 4
    >>> sample['ef'] = 5

    Here we filter for only single-character keys

    >>> filtered = DictFilter(sample, include_pattern='.$')
    >>> filtered == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    True

    >>> filtered['e']
    Traceback (most recent call last):
    ...
    KeyError: 'e'

    Also note that DictFilter keeps a reference to the original dict, so
    if you modify the original dict, that could modify the filtered dict.

    >>> del sample['d']
    >>> del sample['a']
    >>> filtered == {'b': 2, 'c': 3}
    True
    >>> filtered != {'b': 2, 'c': 3}
    False
    """

    def __init__(self, dict, include_keys=[], include_pattern=None):
        self.dict = dict
        self.specified_keys = set(include_keys)
        if include_pattern is not None:
            self.include_pattern = re.compile(include_pattern)
        else:
            # for performance, replace the pattern_keys property
            self.pattern_keys = set()

    def get_pattern_keys(self):
        keys = filter(self.include_pattern.match, self.dict.keys())
        return set(keys)

    pattern_keys = NonDataProperty(get_pattern_keys)

    @property
    def include_keys(self):
        return self.specified_keys.union(self.pattern_keys)

    def keys(self):
        return self.include_keys.intersection(self.dict.keys())

    def values(self):
        return map(self.dict.get, self.keys())

    def __getitem__(self, i):
        if i not in self.include_keys:
            raise KeyError(i)
        return self.dict[i]

    def items(self):
        keys = self.keys()
        values = map(self.dict.get, keys)
        return zip(keys, values)

    def __eq__(self, other):
        return dict(self) == other

    def __ne__(self, other):
        return dict(self) != other


def dict_map(function, dictionary):
    """
    dict_map is much like the built-in function map.  It takes a dictionary
    and applys a function to the values of that dictionary, returning a
    new dictionary with the mapped values in the original keys.

    >>> d = dict_map(lambda x:x+1, dict(a=1, b=2))
    >>> d == dict(a=2,b=3)
    True
    """
    return dict((key, function(value)) for key, value in dictionary.items())


class RangeMap(dict):
    """
    A dictionary-like object that uses the keys as bounds for a range.
    Inclusion of the value for that range is determined by the
    key_match_comparator, which defaults to less-than-or-equal.
    A value is returned for a key if it is the first key that matches in
    the sorted list of keys.

    One may supply keyword parameters to be passed to the sort function used
    to sort keys (i.e. cmp [python 2 only], keys, reverse) as sort_params.

    Let's create a map that maps 1-3 -> 'a', 4-6 -> 'b'

    >>> r = RangeMap({3: 'a', 6: 'b'})  # boy, that was easy
    >>> r[1], r[2], r[3], r[4], r[5], r[6]
    ('a', 'a', 'a', 'b', 'b', 'b')

    Even float values should work so long as the comparison operator
    supports it.

    >>> r[4.5]
    'b'

    But you'll notice that the way rangemap is defined, it must be open-ended
    on one side.

    >>> r[0]
    'a'
    >>> r[-1]
    'a'

    One can close the open-end of the RangeMap by using undefined_value

    >>> r = RangeMap({0: RangeMap.undefined_value, 3: 'a', 6: 'b'})
    >>> r[0]
    Traceback (most recent call last):
    ...
    KeyError: 0

    One can get the first or last elements in the range by using RangeMap.Item

    >>> last_item = RangeMap.Item(-1)
    >>> r[last_item]
    'b'

    .last_item is a shortcut for Item(-1)

    >>> r[RangeMap.last_item]
    'b'

    Sometimes it's useful to find the bounds for a RangeMap

    >>> r.bounds()
    (0, 6)

    RangeMap supports .get(key, default)

    >>> r.get(0, 'not found')
    'not found'

    >>> r.get(7, 'not found')
    'not found'
    """

    def __init__(self, source, sort_params={}, key_match_comparator=operator.le):
        dict.__init__(self, source)
        self.sort_params = sort_params
        self.match = key_match_comparator

    def __getitem__(self, item):
        sorted_keys = sorted(self.keys(), **self.sort_params)
        if isinstance(item, RangeMap.Item):
            result = self.__getitem__(sorted_keys[item])
        else:
            key = self._find_first_match_(sorted_keys, item)
            result = dict.__getitem__(self, key)
            if result is RangeMap.undefined_value:
                raise KeyError(key)
        return result

    def get(self, key, default=None):
        """
        Return the value for key if key is in the dictionary, else default.
        If default is not given, it defaults to None, so that this method
        never raises a KeyError.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def _find_first_match_(self, keys, item):
        is_match = functools.partial(self.match, item)
        matches = list(filter(is_match, keys))
        if matches:
            return matches[0]
        raise KeyError(item)

    def bounds(self):
        sorted_keys = sorted(self.keys(), **self.sort_params)
        return (sorted_keys[RangeMap.first_item], sorted_keys[RangeMap.last_item])

    # some special values for the RangeMap
    undefined_value = type(str('RangeValueUndefined'), (object,), {})()

    class Item(int):
        "RangeMap Item"

    first_item = Item(0)
    last_item = Item(-1)


def __identity(x):
    return x


def sorted_items(d, key=__identity, reverse=False):
    """
    Return the items of the dictionary sorted by the keys

    >>> sample = dict(foo=20, bar=42, baz=10)
    >>> tuple(sorted_items(sample))
    (('bar', 42), ('baz', 10), ('foo', 20))

    >>> reverse_string = lambda s: ''.join(reversed(s))
    >>> tuple(sorted_items(sample, key=reverse_string))
    (('foo', 20), ('bar', 42), ('baz', 10))

    >>> tuple(sorted_items(sample, reverse=True))
    (('foo', 20), ('baz', 10), ('bar', 42))
    """
    # wrap the key func so it operates on the first element of each item
    def pairkey_key(item):
        return key(item[0])

    return sorted(d.items(), key=pairkey_key, reverse=reverse)


class KeyTransformingDict(dict):
    """
    A dict subclass that transforms the keys before they're used.
    Subclasses may override the default transform_key to customize behavior.
    """

    @staticmethod
    def transform_key(key):  # pragma: nocover
        return key

    def __init__(self, *args, **kargs):
        super(KeyTransformingDict, self).__init__()
        # build a dictionary using the default constructs
        d = dict(*args, **kargs)
        # build this dictionary using transformed keys.
        for item in d.items():
            self.__setitem__(*item)

    def __setitem__(self, key, val):
        key = self.transform_key(key)
        super(KeyTransformingDict, self).__setitem__(key, val)

    def __getitem__(self, key):
        key = self.transform_key(key)
        return super(KeyTransformingDict, self).__getitem__(key)

    def __contains__(self, key):
        key = self.transform_key(key)
        return super(KeyTransformingDict, self).__contains__(key)

    def __delitem__(self, key):
        key = self.transform_key(key)
        return super(KeyTransformingDict, self).__delitem__(key)

    def get(self, key, *args, **kwargs):
        key = self.transform_key(key)
        return super(KeyTransformingDict, self).get(key, *args, **kwargs)

    def setdefault(self, key, *args, **kwargs):
        key = self.transform_key(key)
        return super(KeyTransformingDict, self).setdefault(key, *args, **kwargs)

    def pop(self, key, *args, **kwargs):
        key = self.transform_key(key)
        return super(KeyTransformingDict, self).pop(key, *args, **kwargs)

    def matching_key_for(self, key):
        """
        Given a key, return the actual key stored in self that matches.
        Raise KeyError if the key isn't found.
        """
        try:
            return next(e_key for e_key in self.keys() if e_key == key)
        except StopIteration:
            raise KeyError(key)


class FoldedCaseKeyedDict(KeyTransformingDict):
    """
    A case-insensitive dictionary (keys are compared as insensitive
    if they are strings).

    >>> d = FoldedCaseKeyedDict()
    >>> d['heLlo'] = 'world'
    >>> list(d.keys()) == ['heLlo']
    True
    >>> list(d.values()) == ['world']
    True
    >>> d['hello'] == 'world'
    True
    >>> 'hello' in d
    True
    >>> 'HELLO' in d
    True
    >>> print(repr(FoldedCaseKeyedDict({'heLlo': 'world'})).replace("u'", "'"))
    {'heLlo': 'world'}
    >>> d = FoldedCaseKeyedDict({'heLlo': 'world'})
    >>> print(d['hello'])
    world
    >>> print(d['Hello'])
    world
    >>> list(d.keys())
    ['heLlo']
    >>> d = FoldedCaseKeyedDict({'heLlo': 'world', 'Hello': 'world'})
    >>> list(d.values())
    ['world']
    >>> key, = d.keys()
    >>> key in ['heLlo', 'Hello']
    True
    >>> del d['HELLO']
    >>> d
    {}

    get should work

    >>> d['Sumthin'] = 'else'
    >>> d.get('SUMTHIN')
    'else'
    >>> d.get('OTHER', 'thing')
    'thing'
    >>> del d['sumthin']

    setdefault should also work

    >>> d['This'] = 'that'
    >>> print(d.setdefault('this', 'other'))
    that
    >>> len(d)
    1
    >>> print(d['this'])
    that
    >>> print(d.setdefault('That', 'other'))
    other
    >>> print(d['THAT'])
    other

    Make it pop!

    >>> print(d.pop('THAT'))
    other

    To retrieve the key in its originally-supplied form, use matching_key_for

    >>> print(d.matching_key_for('this'))
    This

    >>> d.matching_key_for('missing')
    Traceback (most recent call last):
    ...
    KeyError: 'missing'
    """

    @staticmethod
    def transform_key(key):
        return jaraco.text.FoldedCase(key)


class DictAdapter(object):
    """
    Provide a getitem interface for attributes of an object.

    Let's say you want to get at the string.lowercase property in a formatted
    string. It's easy with DictAdapter.

    >>> import string
    >>> print("lowercase is %(ascii_lowercase)s" % DictAdapter(string))
    lowercase is abcdefghijklmnopqrstuvwxyz
    """

    def __init__(self, wrapped_ob):
        self.object = wrapped_ob

    def __getitem__(self, name):
        return getattr(self.object, name)


class ItemsAsAttributes(object):
    """
    Mix-in class to enable a mapping object to provide items as
    attributes.

    >>> C = type(str('C'), (dict, ItemsAsAttributes), dict())
    >>> i = C()
    >>> i['foo'] = 'bar'
    >>> i.foo
    'bar'

    Natural attribute access takes precedence

    >>> i.foo = 'henry'
    >>> i.foo
    'henry'

    But as you might expect, the mapping functionality is preserved.

    >>> i['foo']
    'bar'

    A normal attribute error should be raised if an attribute is
    requested that doesn't exist.

    >>> i.missing
    Traceback (most recent call last):
    ...
    AttributeError: 'C' object has no attribute 'missing'

    It also works on dicts that customize __getitem__

    >>> missing_func = lambda self, key: 'missing item'
    >>> C = type(
    ...     str('C'),
    ...     (dict, ItemsAsAttributes),
    ...     dict(__missing__ = missing_func),
    ... )
    >>> i = C()
    >>> i.missing
    'missing item'
    >>> i.foo
    'missing item'
    """

    def __getattr__(self, key):
        try:
            return getattr(super(ItemsAsAttributes, self), key)
        except AttributeError as e:
            # attempt to get the value from the mapping (return self[key])
            #  but be careful not to lose the original exception context.
            noval = object()

            def _safe_getitem(cont, key, missing_result):
                try:
                    return cont[key]
                except KeyError:
                    return missing_result

            result = _safe_getitem(self, key, noval)
            if result is not noval:
                return result
            # raise the original exception, but use the original class
            #  name, not 'super'.
            (message,) = e.args
            message = message.replace('super', self.__class__.__name__, 1)
            e.args = (message,)
            raise


def invert_map(map):
    """
    Given a dictionary, return another dictionary with keys and values
    switched. If any of the values resolve to the same key, raises
    a ValueError.

    >>> numbers = dict(a=1, b=2, c=3)
    >>> letters = invert_map(numbers)
    >>> letters[1]
    'a'
    >>> numbers['d'] = 3
    >>> invert_map(numbers)
    Traceback (most recent call last):
    ...
    ValueError: Key conflict in inverted mapping
    """
    res = dict((v, k) for k, v in map.items())
    if not len(res) == len(map):
        raise ValueError('Key conflict in inverted mapping')
    return res


class IdentityOverrideMap(dict):
    """
    A dictionary that by default maps each key to itself, but otherwise
    acts like a normal dictionary.

    >>> d = IdentityOverrideMap()
    >>> d[42]
    42
    >>> d['speed'] = 'speedo'
    >>> print(d['speed'])
    speedo
    """

    def __missing__(self, key):
        return key


class DictStack(list, collections.abc.Mapping):
    """
    A stack of dictionaries that behaves as a view on those dictionaries,
    giving preference to the last.

    >>> stack = DictStack([dict(a=1, c=2), dict(b=2, a=2)])
    >>> stack['a']
    2
    >>> stack['b']
    2
    >>> stack['c']
    2
    >>> len(stack)
    3
    >>> stack.push(dict(a=3))
    >>> stack['a']
    3
    >>> set(stack.keys()) == set(['a', 'b', 'c'])
    True
    >>> set(stack.items()) == set([('a', 3), ('b', 2), ('c', 2)])
    True
    >>> dict(**stack) == dict(stack) == dict(a=3, c=2, b=2)
    True
    >>> d = stack.pop()
    >>> stack['a']
    2
    >>> d = stack.pop()
    >>> stack['a']
    1
    >>> stack.get('b', None)
    >>> 'c' in stack
    True
    """

    def __iter__(self):
        dicts = list.__iter__(self)
        return iter(set(itertools.chain.from_iterable(c.keys() for c in dicts)))

    def __getitem__(self, key):
        for scope in reversed(tuple(list.__iter__(self))):
            if key in scope:
                return scope[key]
        raise KeyError(key)

    push = list.append

    def __contains__(self, other):
        return collections.abc.Mapping.__contains__(self, other)

    def __len__(self):
        return len(list(iter(self)))


class BijectiveMap(dict):
    """
    A Bijective Map (two-way mapping).

    Implemented as a simple dictionary of 2x the size, mapping values back
    to keys.

    Note, this implementation may be incomplete. If there's not a test for
    your use case below, it's likely to fail, so please test and send pull
    requests or patches for additional functionality needed.


    >>> m = BijectiveMap()
    >>> m['a'] = 'b'
    >>> m == {'a': 'b', 'b': 'a'}
    True
    >>> print(m['b'])
    a

    >>> m['c'] = 'd'
    >>> len(m)
    2

    Some weird things happen if you map an item to itself or overwrite a
    single key of a pair, so it's disallowed.

    >>> m['e'] = 'e'
    Traceback (most recent call last):
    ValueError: Key cannot map to itself

    >>> m['d'] = 'e'
    Traceback (most recent call last):
    ValueError: Key/Value pairs may not overlap

    >>> m['e'] = 'd'
    Traceback (most recent call last):
    ValueError: Key/Value pairs may not overlap

    >>> print(m.pop('d'))
    c

    >>> 'c' in m
    False

    >>> m = BijectiveMap(dict(a='b'))
    >>> len(m)
    1
    >>> print(m['b'])
    a

    >>> m = BijectiveMap()
    >>> m.update(a='b')
    >>> m['b']
    'a'

    >>> del m['b']
    >>> len(m)
    0
    >>> 'a' in m
    False
    """

    def __init__(self, *args, **kwargs):
        super(BijectiveMap, self).__init__()
        self.update(*args, **kwargs)

    def __setitem__(self, item, value):
        if item == value:
            raise ValueError("Key cannot map to itself")
        overlap = (
            item in self
            and self[item] != value
            or value in self
            and self[value] != item
        )
        if overlap:
            raise ValueError("Key/Value pairs may not overlap")
        super(BijectiveMap, self).__setitem__(item, value)
        super(BijectiveMap, self).__setitem__(value, item)

    def __delitem__(self, item):
        self.pop(item)

    def __len__(self):
        return super(BijectiveMap, self).__len__() // 2

    def pop(self, key, *args, **kwargs):
        mirror = self[key]
        super(BijectiveMap, self).__delitem__(mirror)
        return super(BijectiveMap, self).pop(key, *args, **kwargs)

    def update(self, *args, **kwargs):
        # build a dictionary using the default constructs
        d = dict(*args, **kwargs)
        # build this dictionary using transformed keys.
        for item in d.items():
            self.__setitem__(*item)


class FrozenDict(collections.abc.Mapping, collections.abc.Hashable):
    """
    An immutable mapping.

    >>> a = FrozenDict(a=1, b=2)
    >>> b = FrozenDict(a=1, b=2)
    >>> a == b
    True

    >>> a == dict(a=1, b=2)
    True
    >>> dict(a=1, b=2) == a
    True
    >>> 'a' in a
    True
    >>> type(hash(a)) is type(0)
    True
    >>> set(iter(a)) == {'a', 'b'}
    True
    >>> len(a)
    2
    >>> a['a'] == a.get('a') == 1
    True

    >>> a['c'] = 3
    Traceback (most recent call last):
    ...
    TypeError: 'FrozenDict' object does not support item assignment

    >>> a.update(y=3)
    Traceback (most recent call last):
    ...
    AttributeError: 'FrozenDict' object has no attribute 'update'

    Copies should compare equal

    >>> copy.copy(a) == a
    True

    Copies should be the same type

    >>> isinstance(copy.copy(a), FrozenDict)
    True

    FrozenDict supplies .copy(), even though
    collections.abc.Mapping doesn't demand it.

    >>> a.copy() == a
    True
    >>> a.copy() is not a
    True
    """

    __slots__ = ['__data']

    def __new__(cls, *args, **kwargs):
        self = super(FrozenDict, cls).__new__(cls)
        self.__data = dict(*args, **kwargs)
        return self

    # Container
    def __contains__(self, key):
        return key in self.__data

    # Hashable
    def __hash__(self):
        return hash(tuple(sorted(self.__data.items())))

    # Mapping
    def __iter__(self):
        return iter(self.__data)

    def __len__(self):
        return len(self.__data)

    def __getitem__(self, key):
        return self.__data[key]

    # override get for efficiency provided by dict
    def get(self, *args, **kwargs):
        return self.__data.get(*args, **kwargs)

    # override eq to recognize underlying implementation
    def __eq__(self, other):
        if isinstance(other, FrozenDict):
            other = other.__data
        return self.__data.__eq__(other)

    def copy(self):
        "Return a shallow copy of self"
        return copy.copy(self)


class Enumeration(ItemsAsAttributes, BijectiveMap):
    """
    A convenient way to provide enumerated values

    >>> e = Enumeration('a b c')
    >>> e['a']
    0

    >>> e.a
    0

    >>> e[1]
    'b'

    >>> set(e.names) == set('abc')
    True

    >>> set(e.codes) == set(range(3))
    True

    >>> e.get('d') is None
    True

    Codes need not start with 0

    >>> e = Enumeration('a b c', range(1, 4))
    >>> e['a']
    1

    >>> e[3]
    'c'
    """

    def __init__(self, names, codes=None):
        if isinstance(names, str):
            names = names.split()
        if codes is None:
            codes = itertools.count()
        super(Enumeration, self).__init__(zip(names, codes))

    @property
    def names(self):
        return (key for key in self if isinstance(key, str))

    @property
    def codes(self):
        return (self[name] for name in self.names)


class Everything(object):
    """
    A collection "containing" every possible thing.

    >>> 'foo' in Everything()
    True

    >>> import random
    >>> random.randint(1, 999) in Everything()
    True

    >>> random.choice([None, 'foo', 42, ('a', 'b', 'c')]) in Everything()
    True
    """

    def __contains__(self, other):
        return True


class InstrumentedDict(collections.UserDict):  # type: ignore  # buggy mypy
    """
    Instrument an existing dictionary with additional
    functionality, but always reference and mutate
    the original dictionary.

    >>> orig = {'a': 1, 'b': 2}
    >>> inst = InstrumentedDict(orig)
    >>> inst['a']
    1
    >>> inst['c'] = 3
    >>> orig['c']
    3
    >>> inst.keys() == orig.keys()
    True
    """

    def __init__(self, data):
        super().__init__()
        self.data = data


class Least(object):
    """
    A value that is always lesser than any other

    >>> least = Least()
    >>> 3 < least
    False
    >>> 3 > least
    True
    >>> least < 3
    True
    >>> least <= 3
    True
    >>> least > 3
    False
    >>> 'x' > least
    True
    >>> None > least
    True
    """

    def __le__(self, other):
        return True

    __lt__ = __le__

    def __ge__(self, other):
        return False

    __gt__ = __ge__


class Greatest(object):
    """
    A value that is always greater than any other

    >>> greatest = Greatest()
    >>> 3 < greatest
    True
    >>> 3 > greatest
    False
    >>> greatest < 3
    False
    >>> greatest > 3
    True
    >>> greatest >= 3
    True
    >>> 'x' > greatest
    False
    >>> None > greatest
    False
    """

    def __ge__(self, other):
        return True

    __gt__ = __ge__

    def __le__(self, other):
        return False

    __lt__ = __le__


def pop_all(items):
    """
    Clear items in place and return a copy of items.

    >>> items = [1, 2, 3]
    >>> popped = pop_all(items)
    >>> popped is items
    False
    >>> popped
    [1, 2, 3]
    >>> items
    []
    """
    result, items[:] = items[:], []
    return result


# mypy disabled for pytest-dev/pytest#8332
class FreezableDefaultDict(collections.defaultdict):  # type: ignore
    """
    Often it is desirable to prevent the mutation of
    a default dict after its initial construction, such
    as to prevent mutation during iteration.

    >>> dd = FreezableDefaultDict(list)
    >>> dd[0].append('1')
    >>> dd.freeze()
    >>> dd[1]
    []
    >>> len(dd)
    1
    """

    def __missing__(self, key):
        return getattr(self, '_frozen', super().__missing__)(key)

    def freeze(self):
        self._frozen = lambda key: self.default_factory()


class Accumulator:
    def __init__(self, initial=0):
        self.val = initial

    def __call__(self, val):
        self.val += val
        return self.val


class WeightedLookup(RangeMap):
    """
    Given parameters suitable for a dict representing keys
    and a weighted proportion, return a RangeMap representing
    spans of values proportial to the weights:

    >>> even = WeightedLookup(a=1, b=1)

    [0, 1) -> a
    [1, 2) -> b

    >>> lk = WeightedLookup(a=1, b=2)

    [0, 1) -> a
    [1, 3) -> b

    >>> lk[.5]
    'a'
    >>> lk[1.5]
    'b'

    Adds ``.random()`` to select a random weighted value:

    >>> lk.random() in ['a', 'b']
    True

    >>> choices = [lk.random() for x in range(1000)]

    Statistically speaking, choices should be .5 a:b
    >>> ratio = choices.count('a') / choices.count('b')
    >>> .4 < ratio < .6
    True
    """

    def __init__(self, *args, **kwargs):
        raw = dict(*args, **kwargs)

        # allocate keys by weight
        indexes = map(Accumulator(), raw.values())
        super().__init__(zip(indexes, raw.keys()), key_match_comparator=operator.lt)

    def random(self):
        lower, upper = self.bounds()
        selector = random.random() * upper
        return self[selector]
