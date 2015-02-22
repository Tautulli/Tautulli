# -*- coding: utf-8 -*-

# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Utility classes for Mutagen.

You should not rely on the interfaces here being stable. They are
intended for internal use in Mutagen only.
"""

import struct
import codecs

from fnmatch import fnmatchcase

from ._compat import chr_, text_type, PY2, iteritems, iterbytes, \
    integer_types, xrange


class MutagenError(Exception):
    """Base class for all custom exceptions in mutagen

    .. versionadded:: 1.25
    """


def total_ordering(cls):
    assert "__eq__" in cls.__dict__
    assert "__lt__" in cls.__dict__

    cls.__le__ = lambda self, other: self == other or self < other
    cls.__gt__ = lambda self, other: not (self == other or self < other)
    cls.__ge__ = lambda self, other: not self < other
    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls


def hashable(cls):
    """Makes sure the class is hashable.

    Needs a working __eq__ and __hash__ and will add a __ne__.
    """

    # py2
    assert "__hash__" in cls.__dict__
    # py3
    assert cls.__dict__["__hash__"] is not None
    assert "__eq__" in cls.__dict__

    cls.__ne__ = lambda self, other: not self.__eq__(other)

    return cls


def enum(cls):
    assert cls.__bases__ == (object,)

    d = dict(cls.__dict__)
    new_type = type(cls.__name__, (int,), d)
    new_type.__module__ = cls.__module__

    map_ = {}
    for key, value in iteritems(d):
        if key.upper() == key and isinstance(value, integer_types):
            value_instance = new_type(value)
            setattr(new_type, key, value_instance)
            map_[value] = key

    def repr_(self):
        if self in map_:
            return "%s.%s" % (type(self).__name__, map_[self])
        else:
            return "%s(%s)" % (type(self).__name__, self)

    setattr(new_type, "__repr__", repr_)

    return new_type


@total_ordering
class DictMixin(object):
    """Implement the dict API using keys() and __*item__ methods.

    Similar to UserDict.DictMixin, this takes a class that defines
    __getitem__, __setitem__, __delitem__, and keys(), and turns it
    into a full dict-like object.

    UserDict.DictMixin is not suitable for this purpose because it's
    an old-style class.

    This class is not optimized for very large dictionaries; many
    functions have linear memory requirements. I recommend you
    override some of these functions if speed is required.
    """

    def __iter__(self):
        return iter(self.keys())

    def __has_key(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    if PY2:
        has_key = __has_key

    __contains__ = __has_key

    if PY2:
        iterkeys = lambda self: iter(self.keys())

    def values(self):
        return [self[k] for k in self.keys()]

    if PY2:
        itervalues = lambda self: iter(self.values())

    def items(self):
        return list(zip(self.keys(), self.values()))

    if PY2:
        iteritems = lambda s: iter(s.items())

    def clear(self):
        for key in list(self.keys()):
            self.__delitem__(key)

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError("pop takes at most two arguments")
        try:
            value = self[key]
        except KeyError:
            if args:
                return args[0]
            else:
                raise
        del(self[key])
        return value

    def popitem(self):
        for key in self.keys():
            break
        else:
            raise KeyError("dictionary is empty")
        return key, self.pop(key)

    def update(self, other=None, **kwargs):
        if other is None:
            self.update(kwargs)
            other = {}

        try:
            for key, value in other.items():
                self.__setitem__(key, value)
        except AttributeError:
            for key, value in other:
                self[key] = value

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __repr__(self):
        return repr(dict(self.items()))

    def __eq__(self, other):
        return dict(self.items()) == other

    def __lt__(self, other):
        return dict(self.items()) < other

    __hash__ = object.__hash__

    def __len__(self):
        return len(self.keys())


class DictProxy(DictMixin):
    def __init__(self, *args, **kwargs):
        self.__dict = {}
        super(DictProxy, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        return self.__dict[key]

    def __setitem__(self, key, value):
        self.__dict[key] = value

    def __delitem__(self, key):
        del(self.__dict[key])

    def keys(self):
        return self.__dict.keys()


def _fill_cdata(cls):
    """Add struct pack/unpack functions"""

    funcs = {}
    for key, name in [("b", "char"), ("h", "short"),
                      ("i", "int"), ("q", "longlong")]:
        for echar, esuffix in [("<", "le"), (">", "be")]:
            esuffix = "_" + esuffix
            for unsigned in [True, False]:
                s = struct.Struct(echar + (key.upper() if unsigned else key))
                get_wrapper = lambda f: lambda *a, **k: f(*a, **k)[0]
                unpack = get_wrapper(s.unpack)
                unpack_from = get_wrapper(s.unpack_from)

                def get_unpack_from(s):
                    def unpack_from(data, offset=0):
                        return s.unpack_from(data, offset)[0], offset + s.size
                    return unpack_from

                unpack_from = get_unpack_from(s)
                pack = s.pack

                prefix = "u" if unsigned else ""
                if s.size == 1:
                    esuffix = ""
                bits = str(s.size * 8)
                funcs["%s%s%s" % (prefix, name, esuffix)] = unpack
                funcs["%sint%s%s" % (prefix, bits, esuffix)] = unpack
                funcs["%s%s%s_from" % (prefix, name, esuffix)] = unpack_from
                funcs["%sint%s%s_from" % (prefix, bits, esuffix)] = unpack_from
                funcs["to_%s%s%s" % (prefix, name, esuffix)] = pack
                funcs["to_%sint%s%s" % (prefix, bits, esuffix)] = pack

    for key, func in iteritems(funcs):
        setattr(cls, key, staticmethod(func))


class cdata(object):
    """C character buffer to Python numeric type conversions.

    For each size/sign/endianness:
    uint32_le(data)/to_uint32_le(num)/uint32_le_from(data, offset=0)
    """

    from struct import error
    error = error

    bitswap = b''.join(
        chr_(sum(((val >> i) & 1) << (7 - i) for i in range(8)))
        for val in range(256))

    test_bit = staticmethod(lambda value, n: bool((value >> n) & 1))


_fill_cdata(cdata)


def lock(fileobj):
    """Lock a file object 'safely'.

    That means a failure to lock because the platform doesn't
    support fcntl or filesystem locks is not considered a
    failure. This call does block.

    Returns whether or not the lock was successful, or
    raises an exception in more extreme circumstances (full
    lock table, invalid file).
    """

    try:
        import fcntl
    except ImportError:
        return False
    else:
        try:
            fcntl.lockf(fileobj, fcntl.LOCK_EX)
        except IOError:
            # FIXME: There's possibly a lot of complicated
            # logic that needs to go here in case the IOError
            # is EACCES or EAGAIN.
            return False
        else:
            return True


def unlock(fileobj):
    """Unlock a file object.

    Don't call this on a file object unless a call to lock()
    returned true.
    """

    # If this fails there's a mismatched lock/unlock pair,
    # so we definitely don't want to ignore errors.
    import fcntl
    fcntl.lockf(fileobj, fcntl.LOCK_UN)


def insert_bytes(fobj, size, offset, BUFFER_SIZE=2 ** 16):
    """Insert size bytes of empty space starting at offset.

    fobj must be an open file object, open rb+ or
    equivalent. Mutagen tries to use mmap to resize the file, but
    falls back to a significantly slower method if mmap fails.
    """

    assert 0 < size
    assert 0 <= offset
    locked = False
    fobj.seek(0, 2)
    filesize = fobj.tell()
    movesize = filesize - offset
    fobj.write(b'\x00' * size)
    fobj.flush()
    try:
        try:
            import mmap
            file_map = mmap.mmap(fobj.fileno(), filesize + size)
            try:
                file_map.move(offset + size, offset, movesize)
            finally:
                file_map.close()
        except (ValueError, EnvironmentError, ImportError):
            # handle broken mmap scenarios
            locked = lock(fobj)
            fobj.truncate(filesize)

            fobj.seek(0, 2)
            padsize = size
            # Don't generate an enormous string if we need to pad
            # the file out several megs.
            while padsize:
                addsize = min(BUFFER_SIZE, padsize)
                fobj.write(b"\x00" * addsize)
                padsize -= addsize

            fobj.seek(filesize, 0)
            while movesize:
                # At the start of this loop, fobj is pointing at the end
                # of the data we need to move, which is of movesize length.
                thismove = min(BUFFER_SIZE, movesize)
                # Seek back however much we're going to read this frame.
                fobj.seek(-thismove, 1)
                nextpos = fobj.tell()
                # Read it, so we're back at the end.
                data = fobj.read(thismove)
                # Seek back to where we need to write it.
                fobj.seek(-thismove + size, 1)
                # Write it.
                fobj.write(data)
                # And seek back to the end of the unmoved data.
                fobj.seek(nextpos)
                movesize -= thismove

            fobj.flush()
    finally:
        if locked:
            unlock(fobj)


def delete_bytes(fobj, size, offset, BUFFER_SIZE=2 ** 16):
    """Delete size bytes of empty space starting at offset.

    fobj must be an open file object, open rb+ or
    equivalent. Mutagen tries to use mmap to resize the file, but
    falls back to a significantly slower method if mmap fails.
    """

    locked = False
    assert 0 < size
    assert 0 <= offset
    fobj.seek(0, 2)
    filesize = fobj.tell()
    movesize = filesize - offset - size
    assert 0 <= movesize
    try:
        if movesize > 0:
            fobj.flush()
            try:
                import mmap
                file_map = mmap.mmap(fobj.fileno(), filesize)
                try:
                    file_map.move(offset, offset + size, movesize)
                finally:
                    file_map.close()
            except (ValueError, EnvironmentError, ImportError):
                # handle broken mmap scenarios
                locked = lock(fobj)
                fobj.seek(offset + size)
                buf = fobj.read(BUFFER_SIZE)
                while buf:
                    fobj.seek(offset)
                    fobj.write(buf)
                    offset += len(buf)
                    fobj.seek(offset + size)
                    buf = fobj.read(BUFFER_SIZE)
        fobj.truncate(filesize - size)
        fobj.flush()
    finally:
        if locked:
            unlock(fobj)


def dict_match(d, key, default=None):
    """Like __getitem__ but works as if the keys() are all filename patterns.
    Returns the value of any dict key that matches the passed key.
    """

    if key in d and "[" not in key:
        return d[key]
    else:
        for pattern, value in iteritems(d):
            if fnmatchcase(key, pattern):
                return value
    return default


def decode_terminated(data, encoding, strict=True):
    """Returns the decoded data until the first NULL terminator
    and all data after it.

    In case the data can't be decoded raises UnicodeError.
    In case the encoding is not found raises LookupError.
    In case the data isn't null terminated (even if it is encoded correctly)
    raises ValueError except if strict is False, then the decoded string
    will be returned anyway.
    """

    codec_info = codecs.lookup(encoding)

    # normalize encoding name so we can compare by name
    encoding = codec_info.name

    # fast path
    if encoding in ("utf-8", "iso8859-1"):
        index = data.find(b"\x00")
        if index == -1:
            # make sure we raise UnicodeError first, like in the slow path
            res = data.decode(encoding), b""
            if strict:
                raise ValueError("not null terminated")
            else:
                return res
        return data[:index].decode(encoding), data[index + 1:]

    # slow path
    decoder = codec_info.incrementaldecoder()
    r = []
    for i, b in enumerate(iterbytes(data)):
        c = decoder.decode(b)
        if c == u"\x00":
            return u"".join(r), data[i + 1:]
        r.append(c)
    else:
        # make sure the decoder is finished
        r.append(decoder.decode(b"", True))
        if strict:
            raise ValueError("not null terminated")
        return u"".join(r), b""


def split_escape(string, sep, maxsplit=None, escape_char="\\"):
    """Like unicode/str/bytes.split but allows for the separator to be escaped

    If passed unicode/str/bytes will only return list of unicode/str/bytes.
    """

    assert len(sep) == 1
    assert len(escape_char) == 1

    if isinstance(string, bytes):
        if isinstance(escape_char, text_type):
            escape_char = escape_char.encode("ascii")
        iter_ = iterbytes
    else:
        iter_ = iter

    if maxsplit is None:
        maxsplit = len(string)

    empty = string[:0]
    result = []
    current = empty
    escaped = False
    for char in iter_(string):
        if escaped:
            if char != escape_char and char != sep:
                current += escape_char
            current += char
            escaped = False
        else:
            if char == escape_char:
                escaped = True
            elif char == sep and len(result) < maxsplit:
                result.append(current)
                current = empty
            else:
                current += char
    result.append(current)
    return result


class BitReaderError(Exception):
    pass


class BitReader(object):

    def __init__(self, fileobj):
        self._fileobj = fileobj
        self._buffer = 0
        self._bits = 0
        self._pos = fileobj.tell()

    def bits(self, count):
        """Reads `count` bits and returns an uint, MSB read first.

        May raise BitReaderError if not enough data could be read or
        IOError by the underlying file object.
        """

        if count < 0:
            raise ValueError

        if count > self._bits:
            n_bytes = (count - self._bits + 7) // 8
            data = self._fileobj.read(n_bytes)
            if len(data) != n_bytes:
                raise BitReaderError("not enough data")
            for b in bytearray(data):
                self._buffer = (self._buffer << 8) | b
            self._bits += n_bytes * 8

        self._bits -= count
        value = self._buffer >> self._bits
        self._buffer &= (1 << self._bits) - 1
        assert self._bits < 8
        return value

    def bytes(self, count):
        """Returns a bytearray of length `count`. Works unaligned."""

        if count < 0:
            raise ValueError

        # fast path
        if self._bits == 0:
            data = self._fileobj.read(count)
            if len(data) != count:
                raise BitReaderError("not enough data")
            return data

        return bytes(bytearray(self.bits(8) for _ in xrange(count)))

    def skip(self, count):
        """Skip `count` bits.

        Might raise BitReaderError if there wasn't enough data to skip,
        but might also fail on the next bits() instead.
        """

        if count < 0:
            raise ValueError

        if count <= self._bits:
            self.bits(count)
        else:
            count -= self.align()
            n_bytes = count // 8
            self._fileobj.seek(n_bytes, 1)
            count -= n_bytes * 8
            self.bits(count)

    def get_position(self):
        """Returns the amount of bits read or skipped so far"""

        return (self._fileobj.tell() - self._pos) * 8 - self._bits

    def align(self):
        """Align to the next byte, returns the amount of bits skipped"""

        bits = self._bits
        self._buffer = 0
        self._bits = 0
        return bits

    def is_aligned(self):
        """If we are currently aligned to bytes and nothing is buffered"""

        return self._bits == 0
