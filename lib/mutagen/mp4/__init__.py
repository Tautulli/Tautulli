# -*- coding: utf-8 -*-

# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write MPEG-4 audio files with iTunes metadata.

This module will read MPEG-4 audio information and metadata,
as found in Apple's MP4 (aka M4A, M4B, M4P) files.

There is no official specification for this format. The source code
for TagLib, FAAD, and various MPEG specifications at

* http://developer.apple.com/documentation/QuickTime/QTFF/
* http://www.geocities.com/xhelmboyx/quicktime/formats/mp4-layout.txt
* http://standards.iso.org/ittf/PubliclyAvailableStandards/\
c041828_ISO_IEC_14496-12_2005(E).zip
* http://wiki.multimedia.cx/index.php?title=Apple_QuickTime

were all consulted.
"""

import struct
import sys

from mutagen import FileType, Metadata, StreamInfo
from mutagen._constants import GENRES
from mutagen._util import (cdata, insert_bytes, DictProxy, MutagenError,
                           hashable, enum)
from mutagen._compat import (reraise, PY2, string_types, text_type, chr_,
                             iteritems, PY3, cBytesIO)
from ._atom import Atoms, Atom, AtomError
from ._util import parse_full_atom
from ._as_entry import AudioSampleEntry, ASEntryError


class error(IOError, MutagenError):
    pass


class MP4MetadataError(error):
    pass


class MP4StreamInfoError(error):
    pass


class MP4MetadataValueError(ValueError, MP4MetadataError):
    pass


__all__ = ['MP4', 'Open', 'delete', 'MP4Cover', 'MP4FreeForm', 'AtomDataType']


@enum
class AtomDataType(object):
    """Enum for `dataformat` attribute of MP4FreeForm.

    .. versionadded:: 1.25
    """

    IMPLICIT = 0
    """for use with tags for which no type needs to be indicated because
       only one type is allowed"""

    UTF8 = 1
    """without any count or null terminator"""

    UTF16 = 2
    """also known as UTF-16BE"""

    SJIS = 3
    """deprecated unless it is needed for special Japanese characters"""

    HTML = 6
    """the HTML file header specifies which HTML version"""

    XML = 7
    """the XML header must identify the DTD or schemas"""

    UUID = 8
    """also known as GUID; stored as 16 bytes in binary (valid as an ID)"""

    ISRC = 9
    """stored as UTF-8 text (valid as an ID)"""

    MI3P = 10
    """stored as UTF-8 text (valid as an ID)"""

    GIF = 12
    """(deprecated) a GIF image"""

    JPEG = 13
    """a JPEG image"""

    PNG = 14
    """PNG image"""

    URL = 15
    """absolute, in UTF-8 characters"""

    DURATION = 16
    """in milliseconds, 32-bit integer"""

    DATETIME = 17
    """in UTC, counting seconds since midnight, January 1, 1904;
       32 or 64-bits"""

    GENRES = 18
    """a list of enumerated values"""

    INTEGER = 21
    """a signed big-endian integer with length one of { 1,2,3,4,8 } bytes"""

    RIAA_PA = 24
    """RIAA parental advisory; { -1=no, 1=yes, 0=unspecified },
       8-bit ingteger"""

    UPC = 25
    """Universal Product Code, in text UTF-8 format (valid as an ID)"""

    BMP = 27
    """Windows bitmap image"""


@hashable
class MP4Cover(bytes):
    """A cover artwork.

    Attributes:

    * imageformat -- format of the image (either FORMAT_JPEG or FORMAT_PNG)
    """

    FORMAT_JPEG = AtomDataType.JPEG
    FORMAT_PNG = AtomDataType.PNG

    def __new__(cls, data, *args, **kwargs):
        return bytes.__new__(cls, data)

    def __init__(self, data, imageformat=FORMAT_JPEG):
        self.imageformat = imageformat

    __hash__ = bytes.__hash__

    def __eq__(self, other):
        if not isinstance(other, MP4Cover):
            return NotImplemented

        if not bytes.__eq__(self, other):
            return False

        if self.imageformat != other.imageformat:
            return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%r, %r)" % (
            type(self).__name__, bytes(self),
            AtomDataType(self.imageformat))


@hashable
class MP4FreeForm(bytes):
    """A freeform value.

    Attributes:

    * dataformat -- format of the data (see AtomDataType)
    """

    FORMAT_DATA = AtomDataType.IMPLICIT  # deprecated
    FORMAT_TEXT = AtomDataType.UTF8  # deprecated

    def __new__(cls, data, *args, **kwargs):
        return bytes.__new__(cls, data)

    def __init__(self, data, dataformat=AtomDataType.UTF8, version=0):
        self.dataformat = dataformat
        self.version = version

    __hash__ = bytes.__hash__

    def __eq__(self, other):
        if not isinstance(other, MP4FreeForm):
            return NotImplemented

        if not bytes.__eq__(self, other):
            return False

        if self.dataformat != other.dataformat:
            return False

        if self.version != other.version:
            return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "%s(%r, %r)" % (
            type(self).__name__, bytes(self),
            AtomDataType(self.dataformat))



def _name2key(name):
    if PY2:
        return name
    return name.decode("latin-1")


def _key2name(key):
    if PY2:
        return key
    return key.encode("latin-1")


class MP4Tags(DictProxy, Metadata):
    r"""Dictionary containing Apple iTunes metadata list key/values.

    Keys are four byte identifiers, except for freeform ('----')
    keys. Values are usually unicode strings, but some atoms have a
    special structure:

    Text values (multiple values per key are supported):

    * '\\xa9nam' -- track title
    * '\\xa9alb' -- album
    * '\\xa9ART' -- artist
    * 'aART' -- album artist
    * '\\xa9wrt' -- composer
    * '\\xa9day' -- year
    * '\\xa9cmt' -- comment
    * 'desc' -- description (usually used in podcasts)
    * 'purd' -- purchase date
    * '\\xa9grp' -- grouping
    * '\\xa9gen' -- genre
    * '\\xa9lyr' -- lyrics
    * 'purl' -- podcast URL
    * 'egid' -- podcast episode GUID
    * 'catg' -- podcast category
    * 'keyw' -- podcast keywords
    * '\\xa9too' -- encoded by
    * 'cprt' -- copyright
    * 'soal' -- album sort order
    * 'soaa' -- album artist sort order
    * 'soar' -- artist sort order
    * 'sonm' -- title sort order
    * 'soco' -- composer sort order
    * 'sosn' -- show sort order
    * 'tvsh' -- show name

    Boolean values:

    * 'cpil' -- part of a compilation
    * 'pgap' -- part of a gapless album
    * 'pcst' -- podcast (iTunes reads this only on import)

    Tuples of ints (multiple values per key are supported):

    * 'trkn' -- track number, total tracks
    * 'disk' -- disc number, total discs

    Others:

    * 'tmpo' -- tempo/BPM, 16 bit int
    * 'covr' -- cover artwork, list of MP4Cover objects (which are
      tagged strs)
    * 'gnre' -- ID3v1 genre. Not supported, use '\\xa9gen' instead.

    The freeform '----' frames use a key in the format '----:mean:name'
    where 'mean' is usually 'com.apple.iTunes' and 'name' is a unique
    identifier for this frame. The value is a str, but is probably
    text that can be decoded as UTF-8. Multiple values per key are
    supported.

    MP4 tag data cannot exist outside of the structure of an MP4 file,
    so this class should not be manually instantiated.

    Unknown non-text tags and tags that failed to parse will be written
    back as is.
    """

    def __init__(self, *args, **kwargs):
        self._failed_atoms = {}
        super(MP4Tags, self).__init__(*args, **kwargs)

    def load(self, atoms, fileobj):
        try:
            ilst = atoms[b"moov.udta.meta.ilst"]
        except KeyError as key:
            raise MP4MetadataError(key)
        for atom in ilst.children:
            ok, data = atom.read(fileobj)
            if not ok:
                raise MP4MetadataError("Not enough data")

            try:
                if atom.name in self.__atoms:
                    info = self.__atoms[atom.name]
                    info[0](self, atom, data)
                else:
                    # unknown atom, try as text
                    self.__parse_text(atom, data, implicit=False)
            except MP4MetadataError:
                # parsing failed, save them so we can write them back
                key = _name2key(atom.name)
                self._failed_atoms.setdefault(key, []).append(data)

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("key has to be str")
        super(MP4Tags, self).__setitem__(key, value)

    @classmethod
    def _can_load(cls, atoms):
        return b"moov.udta.meta.ilst" in atoms

    @staticmethod
    def __key_sort(item):
        (key, v) = item
        # iTunes always writes the tags in order of "relevance", try
        # to copy it as closely as possible.
        order = [b"\xa9nam", b"\xa9ART", b"\xa9wrt", b"\xa9alb",
                 b"\xa9gen", b"gnre", b"trkn", b"disk",
                 b"\xa9day", b"cpil", b"pgap", b"pcst", b"tmpo",
                 b"\xa9too", b"----", b"covr", b"\xa9lyr"]
        order = dict(zip(order, range(len(order))))
        last = len(order)
        # If there's no key-based way to distinguish, order by length.
        # If there's still no way, go by string comparison on the
        # values, so we at least have something determinstic.
        return (order.get(key[:4], last), len(repr(v)), repr(v))

    def save(self, filename):
        """Save the metadata to the given filename."""

        values = []
        items = sorted(self.items(), key=self.__key_sort)
        for key, value in items:
            atom_name = _key2name(key)[:4]
            if atom_name in self.__atoms:
                render_func = self.__atoms[atom_name][1]
            else:
                render_func = type(self).__render_text

            try:
                values.append(render_func(self, key, value))
            except (TypeError, ValueError) as s:
                reraise(MP4MetadataValueError, s, sys.exc_info()[2])

        for atom_name, failed in iteritems(self._failed_atoms):
            # don't write atoms back if we have added a new one with
            # the same name, this excludes freeform which can have
            # multiple atoms with the same key (most parsers seem to be able
            # to handle that)
            if atom_name in self:
                assert atom_name != b"----"
                continue
            for data in failed:
                values.append(Atom.render(_key2name(atom_name), data))

        data = Atom.render(b"ilst", b"".join(values))

        # Find the old atoms.
        with open(filename, "rb+") as fileobj:
            try:
                atoms = Atoms(fileobj)
            except AtomError as err:
                reraise(error, err, sys.exc_info()[2])

            try:
                path = atoms.path(b"moov", b"udta", b"meta", b"ilst")
            except KeyError:
                self.__save_new(fileobj, atoms, data)
            else:
                self.__save_existing(fileobj, atoms, path, data)

    def __pad_ilst(self, data, length=None):
        if length is None:
            length = ((len(data) + 1023) & ~1023) - len(data)
        return Atom.render(b"free", b"\x00" * length)

    def __save_new(self, fileobj, atoms, ilst):
        hdlr = Atom.render(b"hdlr", b"\x00" * 8 + b"mdirappl" + b"\x00" * 9)
        meta = Atom.render(
            b"meta", b"\x00\x00\x00\x00" + hdlr + ilst + self.__pad_ilst(ilst))
        try:
            path = atoms.path(b"moov", b"udta")
        except KeyError:
            # moov.udta not found -- create one
            path = atoms.path(b"moov")
            meta = Atom.render(b"udta", meta)
        offset = path[-1].offset + 8
        insert_bytes(fileobj, len(meta), offset)
        fileobj.seek(offset)
        fileobj.write(meta)
        self.__update_parents(fileobj, path, len(meta))
        self.__update_offsets(fileobj, atoms, len(meta), offset)

    def __save_existing(self, fileobj, atoms, path, data):
        # Replace the old ilst atom.
        ilst = path.pop()
        offset = ilst.offset
        length = ilst.length

        # Check for padding "free" atoms
        meta = path[-1]
        index = meta.children.index(ilst)
        try:
            prev = meta.children[index - 1]
            if prev.name == b"free":
                offset = prev.offset
                length += prev.length
        except IndexError:
            pass
        try:
            next = meta.children[index + 1]
            if next.name == b"free":
                length += next.length
        except IndexError:
            pass

        delta = len(data) - length
        if delta > 0 or (delta < 0 and delta > -8):
            data += self.__pad_ilst(data)
            delta = len(data) - length
            insert_bytes(fileobj, delta, offset)
        elif delta < 0:
            data += self.__pad_ilst(data, -delta - 8)
            delta = 0

        fileobj.seek(offset)
        fileobj.write(data)
        self.__update_parents(fileobj, path, delta)
        self.__update_offsets(fileobj, atoms, delta, offset)

    def __update_parents(self, fileobj, path, delta):
        """Update all parent atoms with the new size."""
        for atom in path:
            fileobj.seek(atom.offset)
            size = cdata.uint_be(fileobj.read(4))
            if size == 1:  # 64bit
                # skip name (4B) and read size (8B)
                size = cdata.ulonglong_be(fileobj.read(12)[4:])
                fileobj.seek(atom.offset + 8)
                fileobj.write(cdata.to_ulonglong_be(size + delta))
            else:  # 32bit
                fileobj.seek(atom.offset)
                fileobj.write(cdata.to_uint_be(size + delta))

    def __update_offset_table(self, fileobj, fmt, atom, delta, offset):
        """Update offset table in the specified atom."""
        if atom.offset > offset:
            atom.offset += delta
        fileobj.seek(atom.offset + 12)
        data = fileobj.read(atom.length - 12)
        fmt = fmt % cdata.uint_be(data[:4])
        offsets = struct.unpack(fmt, data[4:])
        offsets = [o + (0, delta)[offset < o] for o in offsets]
        fileobj.seek(atom.offset + 16)
        fileobj.write(struct.pack(fmt, *offsets))

    def __update_tfhd(self, fileobj, atom, delta, offset):
        if atom.offset > offset:
            atom.offset += delta
        fileobj.seek(atom.offset + 9)
        data = fileobj.read(atom.length - 9)
        flags = cdata.uint_be(b"\x00" + data[:3])
        if flags & 1:
            o = cdata.ulonglong_be(data[7:15])
            if o > offset:
                o += delta
            fileobj.seek(atom.offset + 16)
            fileobj.write(cdata.to_ulonglong_be(o))

    def __update_offsets(self, fileobj, atoms, delta, offset):
        """Update offset tables in all 'stco' and 'co64' atoms."""
        if delta == 0:
            return
        moov = atoms[b"moov"]
        for atom in moov.findall(b'stco', True):
            self.__update_offset_table(fileobj, ">%dI", atom, delta, offset)
        for atom in moov.findall(b'co64', True):
            self.__update_offset_table(fileobj, ">%dQ", atom, delta, offset)
        try:
            for atom in atoms[b"moof"].findall(b'tfhd', True):
                self.__update_tfhd(fileobj, atom, delta, offset)
        except KeyError:
            pass

    def __parse_data(self, atom, data):
        pos = 0
        while pos < atom.length - 8:
            head = data[pos:pos + 12]
            if len(head) != 12:
                raise MP4MetadataError("truncated atom % r" % atom.name)
            length, name = struct.unpack(">I4s", head[:8])
            version = ord(head[8:9])
            flags = struct.unpack(">I", b"\x00" + head[9:12])[0]
            if name != b"data":
                raise MP4MetadataError(
                    "unexpected atom %r inside %r" % (name, atom.name))

            chunk = data[pos + 16:pos + length]
            if len(chunk) != length - 16:
                raise MP4MetadataError("truncated atom % r" % atom.name)
            yield version, flags, chunk
            pos += length

    def __add(self, key, value, single=False):
        assert isinstance(key, str)

        if single:
            self[key] = value
        else:
            self.setdefault(key, []).extend(value)

    def __render_data(self, key, version, flags, value):
        return Atom.render(_key2name(key), b"".join([
            Atom.render(
                b"data", struct.pack(">2I", version << 24 | flags, 0) + data)
            for data in value]))

    def __parse_freeform(self, atom, data):
        length = cdata.uint_be(data[:4])
        mean = data[12:length]
        pos = length
        length = cdata.uint_be(data[pos:pos + 4])
        name = data[pos + 12:pos + length]
        pos += length
        value = []
        while pos < atom.length - 8:
            length, atom_name = struct.unpack(">I4s", data[pos:pos + 8])
            if atom_name != b"data":
                raise MP4MetadataError(
                    "unexpected atom %r inside %r" % (atom_name, atom.name))

            version = ord(data[pos + 8:pos + 8 + 1])
            flags = struct.unpack(">I", b"\x00" + data[pos + 9:pos + 12])[0]
            value.append(MP4FreeForm(data[pos + 16:pos + length],
                                     dataformat=flags, version=version))
            pos += length

        key = _name2key(atom.name + b":" + mean + b":" + name)
        self.__add(key, value)

    def __render_freeform(self, key, value):
        if isinstance(value, bytes):
            value = [value]

        dummy, mean, name = _key2name(key).split(b":", 2)
        mean = struct.pack(">I4sI", len(mean) + 12, b"mean", 0) + mean
        name = struct.pack(">I4sI", len(name) + 12, b"name", 0) + name

        data = b""
        for v in value:
            flags = AtomDataType.UTF8
            version = 0
            if isinstance(v, MP4FreeForm):
                flags = v.dataformat
                version = v.version

            data += struct.pack(
                ">I4s2I", len(v) + 16, b"data", version << 24 | flags, 0)
            data += v

        return Atom.render(b"----", mean + name + data)

    def __parse_pair(self, atom, data):
        key = _name2key(atom.name)
        values = [struct.unpack(">2H", d[2:6]) for
                  version, flags, d in self.__parse_data(atom, data)]
        self.__add(key, values)

    def __render_pair(self, key, value):
        data = []
        for (track, total) in value:
            if 0 <= track < 1 << 16 and 0 <= total < 1 << 16:
                data.append(struct.pack(">4H", 0, track, total, 0))
            else:
                raise MP4MetadataValueError(
                    "invalid numeric pair %r" % ((track, total),))
        return self.__render_data(key, 0, AtomDataType.IMPLICIT, data)

    def __render_pair_no_trailing(self, key, value):
        data = []
        for (track, total) in value:
            if 0 <= track < 1 << 16 and 0 <= total < 1 << 16:
                data.append(struct.pack(">3H", 0, track, total))
            else:
                raise MP4MetadataValueError(
                    "invalid numeric pair %r" % ((track, total),))
        return self.__render_data(key, 0, AtomDataType.IMPLICIT, data)

    def __parse_genre(self, atom, data):
        values = []
        for version, flags, data in self.__parse_data(atom, data):
            # version = 0, flags = 0
            if len(data) != 2:
                raise MP4MetadataValueError("invalid genre")
            genre = cdata.short_be(data)
            # Translate to a freeform genre.
            try:
                genre = GENRES[genre - 1]
            except IndexError:
                # this will make us write it back at least
                raise MP4MetadataValueError("unknown genre")
            values.append(genre)
        key = _name2key(b"\xa9gen")
        self.__add(key, values)

    def __parse_tempo(self, atom, data):
        values = []
        for version, flags, data in self.__parse_data(atom, data):
            # version = 0, flags = 0 or 21
            if len(data) != 2:
                raise MP4MetadataValueError("invalid tempo")
            values.append(cdata.ushort_be(data))
        key = _name2key(atom.name)
        self.__add(key, values)

    def __render_tempo(self, key, value):
        try:
            if len(value) == 0:
                return self.__render_data(key, 0, AtomDataType.INTEGER, b"")

            if (min(value) < 0) or (max(value) >= 2 ** 16):
                raise MP4MetadataValueError(
                    "invalid 16 bit integers: %r" % value)
        except TypeError:
            raise MP4MetadataValueError(
                "tmpo must be a list of 16 bit integers")

        values = [cdata.to_ushort_be(v) for v in value]
        return self.__render_data(key, 0, AtomDataType.INTEGER, values)

    def __parse_bool(self, atom, data):
        for version, flags, data in self.__parse_data(atom, data):
            if len(data) != 1:
                raise MP4MetadataValueError("invalid bool")

            value = bool(ord(data))
            key = _name2key(atom.name)
            self.__add(key, value, single=True)

    def __render_bool(self, key, value):
        return self.__render_data(
            key, 0, AtomDataType.INTEGER, [chr_(bool(value))])

    def __parse_cover(self, atom, data):
        values = []
        pos = 0
        while pos < atom.length - 8:
            length, name, imageformat = struct.unpack(">I4sI",
                                                      data[pos:pos + 12])
            if name != b"data":
                if name == b"name":
                    pos += length
                    continue
                raise MP4MetadataError(
                    "unexpected atom %r inside 'covr'" % name)
            if imageformat not in (MP4Cover.FORMAT_JPEG, MP4Cover.FORMAT_PNG):
                # Sometimes AtomDataType.IMPLICIT or simply wrong.
                # In all cases it was jpeg, so default to it
                imageformat = MP4Cover.FORMAT_JPEG
            cover = MP4Cover(data[pos + 16:pos + length], imageformat)
            values.append(cover)
            pos += length

        key = _name2key(atom.name)
        self.__add(key, values)

    def __render_cover(self, key, value):
        atom_data = []
        for cover in value:
            try:
                imageformat = cover.imageformat
            except AttributeError:
                imageformat = MP4Cover.FORMAT_JPEG
            atom_data.append(Atom.render(
                b"data", struct.pack(">2I", imageformat, 0) + cover))
        return Atom.render(_key2name(key), b"".join(atom_data))

    def __parse_text(self, atom, data, implicit=True):
        # implicit = False, for parsing unknown atoms only take utf8 ones.
        # For known ones we can assume the implicit are utf8 too.
        values = []
        for version, flags, atom_data in self.__parse_data(atom, data):
            if implicit:
                if flags not in (AtomDataType.IMPLICIT, AtomDataType.UTF8):
                    raise MP4MetadataError(
                        "Unknown atom type %r for %r" % (flags, atom.name))
            else:
                if flags != AtomDataType.UTF8:
                    raise MP4MetadataError(
                        "%r is not text, ignore" % atom.name)

            try:
                text = atom_data.decode("utf-8")
            except UnicodeDecodeError as e:
                raise MP4MetadataError("%s: %s" % (atom.name, e))

            values.append(text)

        key = _name2key(atom.name)
        self.__add(key, values)

    def __render_text(self, key, value, flags=AtomDataType.UTF8):
        if isinstance(value, string_types):
            value = [value]

        encoded = []
        for v in value:
            if not isinstance(v, text_type):
                if PY3:
                    raise TypeError("%r not str" % v)
                v = v.decode("utf-8")
            encoded.append(v.encode("utf-8"))

        return self.__render_data(key, 0, flags, encoded)

    def delete(self, filename):
        """Remove the metadata from the given filename."""

        self._failed_atoms.clear()
        self.clear()
        self.save(filename)

    __atoms = {
        b"----": (__parse_freeform, __render_freeform),
        b"trkn": (__parse_pair, __render_pair),
        b"disk": (__parse_pair, __render_pair_no_trailing),
        b"gnre": (__parse_genre, None),
        b"tmpo": (__parse_tempo, __render_tempo),
        b"cpil": (__parse_bool, __render_bool),
        b"pgap": (__parse_bool, __render_bool),
        b"pcst": (__parse_bool, __render_bool),
        b"covr": (__parse_cover, __render_cover),
        b"purl": (__parse_text, __render_text),
        b"egid": (__parse_text, __render_text),
    }

    # these allow implicit flags and parse as text
    for name in [b"\xa9nam", b"\xa9alb", b"\xa9ART", b"aART", b"\xa9wrt",
                 b"\xa9day", b"\xa9cmt", b"desc", b"purd", b"\xa9grp",
                 b"\xa9gen", b"\xa9lyr", b"catg", b"keyw", b"\xa9too",
                 b"cprt", b"soal", b"soaa", b"soar", b"sonm", b"soco",
                 b"sosn", b"tvsh"]:
        __atoms[name] = (__parse_text, __render_text)

    def pprint(self):
        values = []
        for key, value in iteritems(self):
            if not isinstance(key, text_type):
                key = key.decode("latin-1")
            if key == "covr":
                values.append("%s=%s" % (key, ", ".join(
                    ["[%d bytes of data]" % len(data) for data in value])))
            elif isinstance(value, list):
                values.append("%s=%s" %
                              (key, " / ".join(map(text_type, value))))
            else:
                values.append("%s=%s" % (key, value))
        return "\n".join(values)


class MP4Info(StreamInfo):
    """MPEG-4 stream information.

    Attributes:

    * bitrate -- bitrate in bits per second, as an int
    * length -- file length in seconds, as a float
    * channels -- number of audio channels
    * sample_rate -- audio sampling rate in Hz
    * bits_per_sample -- bits per sample
    * codec (string):
        * if starting with ``"mp4a"`` uses an mp4a audio codec
          (see the codec parameter in rfc6381 for details e.g. ``"mp4a.40.2"``)
        * for everything else see a list of possible values at
          http://www.mp4ra.org/codecs.html

        e.g. ``"mp4a"``, ``"alac"``, ``"mp4a.40.2"``, ``"ac-3"`` etc.
    * codec_description (string):
        Name of the codec used (ALAC, AAC LC, AC-3...). Values might change in
        the future, use for display purposes only.
    """

    bitrate = 0
    channels = 0
    sample_rate = 0
    bits_per_sample = 0
    codec = u""
    codec_name = u""

    def __init__(self, atoms, fileobj):
        try:
            moov = atoms[b"moov"]
        except KeyError:
            raise MP4StreamInfoError("not a MP4 file")

        for trak in moov.findall(b"trak"):
            hdlr = trak[b"mdia", b"hdlr"]
            ok, data = hdlr.read(fileobj)
            if not ok:
                raise MP4StreamInfoError("Not enough data")
            if data[8:12] == b"soun":
                break
        else:
            raise MP4StreamInfoError("track has no audio data")

        mdhd = trak[b"mdia", b"mdhd"]
        ok, data = mdhd.read(fileobj)
        if not ok:
            raise MP4StreamInfoError("Not enough data")

        try:
            version, flags, data = parse_full_atom(data)
        except ValueError as e:
            raise MP4StreamInfoError(e)

        if version == 0:
            offset = 8
            fmt = ">2I"
        elif version == 1:
            offset = 16
            fmt = ">IQ"
        else:
            raise MP4StreamInfoError("Unknown mdhd version %d" % version)

        end = offset + struct.calcsize(fmt)
        unit, length = struct.unpack(fmt, data[offset:end])
        try:
            self.length = float(length) / unit
        except ZeroDivisionError:
            self.length = 0

        try:
            atom = trak[b"mdia", b"minf", b"stbl", b"stsd"]
        except KeyError:
            pass
        else:
            self._parse_stsd(atom, fileobj)

    def _parse_stsd(self, atom, fileobj):
        """Sets channels, bits_per_sample, sample_rate and optionally bitrate.

        Can raise MP4StreamInfoError.
        """

        assert atom.name == b"stsd"

        ok, data = atom.read(fileobj)
        if not ok:
            raise MP4StreamInfoError("Invalid stsd")

        try:
            version, flags, data = parse_full_atom(data)
        except ValueError as e:
            raise MP4StreamInfoError(e)

        if version != 0:
            raise MP4StreamInfoError("Unsupported stsd version")

        try:
            num_entries, offset = cdata.uint32_be_from(data, 0)
        except cdata.error as e:
            raise MP4StreamInfoError(e)

        if num_entries == 0:
            return

        # look at the first entry if there is one
        entry_fileobj = cBytesIO(data[offset:])
        try:
            entry_atom = Atom(entry_fileobj)
        except AtomError as e:
            raise MP4StreamInfoError(e)

        try:
            entry = AudioSampleEntry(entry_atom, entry_fileobj)
        except ASEntryError as e:
            raise MP4StreamInfoError(e)
        else:
            self.channels = entry.channels
            self.bits_per_sample = entry.sample_size
            self.sample_rate = entry.sample_rate
            self.bitrate = entry.bitrate
            self.codec = entry.codec
            self.codec_description = entry.codec_description

    def pprint(self):
        return "MPEG-4 audio (%s), %.2f seconds, %d bps" % (
            self.codec_description, self.length, self.bitrate)


class MP4(FileType):
    """An MPEG-4 audio file, probably containing AAC.

    If more than one track is present in the file, the first is used.
    Only audio ('soun') tracks will be read.

    :ivar info: :class:`MP4Info`
    :ivar tags: :class:`MP4Tags`
    """

    MP4Tags = MP4Tags

    _mimes = ["audio/mp4", "audio/x-m4a", "audio/mpeg4", "audio/aac"]

    def load(self, filename):
        self.filename = filename
        with open(filename, "rb") as fileobj:
            try:
                atoms = Atoms(fileobj)
            except AtomError as err:
                reraise(error, err, sys.exc_info()[2])

            try:
                self.info = MP4Info(atoms, fileobj)
            except error:
                raise
            except Exception as err:
                reraise(MP4StreamInfoError, err, sys.exc_info()[2])

            if not MP4Tags._can_load(atoms):
                self.tags = None
            else:
                try:
                    self.tags = self.MP4Tags(atoms, fileobj)
                except error:
                    raise
                except Exception as err:
                    reraise(MP4MetadataError, err, sys.exc_info()[2])

    def add_tags(self):
        if self.tags is None:
            self.tags = self.MP4Tags()
        else:
            raise error("an MP4 tag already exists")

    @staticmethod
    def score(filename, fileobj, header_data):
        return (b"ftyp" in header_data) + (b"mp4" in header_data)


Open = MP4


def delete(filename):
    """Remove tags from a file."""

    MP4(filename).delete()
