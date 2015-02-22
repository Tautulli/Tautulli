# -*- coding: utf-8 -*-

# Copyright (C) 2014  Evan Purkhiser
#               2014  Ben Ockmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""AIFF audio stream information and tags."""

# NOTE from Ben Ockmore - according to the Py3k migration guidelines, AIFF
# chunk keys should be unicode in Py3k, and unicode or bytes in Py2k (ASCII).
# To make this easier, chunk keys should be stored internally as unicode.

import struct
from struct import pack

from ._compat import endswith, text_type, PY3
from mutagen import StreamInfo, FileType

from mutagen.id3 import ID3
from mutagen.id3._util import error as ID3Error
from mutagen._util import insert_bytes, delete_bytes, MutagenError

__all__ = ["AIFF", "Open", "delete"]


class error(MutagenError, RuntimeError):
    pass


class InvalidChunk(error, IOError):
    pass


# based on stdlib's aifc
_HUGE_VAL = 1.79769313486231e+308


def is_valid_chunk_id(id):
    if not isinstance(id, text_type):
        if PY3:
            raise TypeError("AIFF chunk must be unicode")

        try:
            id = id.decode('ascii')
        except UnicodeDecodeError:
            return False

    return ((len(id) <= 4) and (min(id) >= u' ') and
            (max(id) <= u'~'))


def read_float(data):  # 10 bytes
    expon, himant, lomant = struct.unpack('>hLL', data)
    sign = 1
    if expon < 0:
        sign = -1
        expon = expon + 0x8000
    if expon == himant == lomant == 0:
        f = 0.0
    elif expon == 0x7FFF:
        f = _HUGE_VAL
    else:
        expon = expon - 16383
        f = (himant * 0x100000000 + lomant) * pow(2.0, expon - 63)
    return sign * f


class IFFChunk(object):
    """Representation of a single IFF chunk"""

    # Chunk headers are 8 bytes long (4 for ID and 4 for the size)
    HEADER_SIZE = 8

    def __init__(self, fileobj, parent_chunk=None):
        self.__fileobj = fileobj
        self.parent_chunk = parent_chunk
        self.offset = fileobj.tell()

        header = fileobj.read(self.HEADER_SIZE)
        if len(header) < self.HEADER_SIZE:
            raise InvalidChunk()

        self.id, self.data_size = struct.unpack('>4si', header)

        if not isinstance(self.id, text_type):
            self.id = self.id.decode('ascii')

        if not is_valid_chunk_id(self.id):
            raise InvalidChunk()

        self.size = self.HEADER_SIZE + self.data_size
        self.data_offset = fileobj.tell()
        self.data = None

    def read(self):
        """Read the chunks data"""
        self.__fileobj.seek(self.data_offset)
        self.data = self.__fileobj.read(self.data_size)

    def delete(self):
        """Removes the chunk from the file"""
        delete_bytes(self.__fileobj, self.size, self.offset)
        if self.parent_chunk is not None:
            self.parent_chunk.resize(self.parent_chunk.data_size - self.size)

    def resize(self, data_size):
        """Update the size of the chunk"""
        self.__fileobj.seek(self.offset + 4)
        self.__fileobj.write(pack('>I', data_size))
        if self.parent_chunk is not None:
            size_diff = self.data_size - data_size
            self.parent_chunk.resize(self.parent_chunk.data_size - size_diff)
        self.data_size = data_size
        self.size = data_size + self.HEADER_SIZE


class IFFFile(object):
    """Representation of a IFF file"""

    def __init__(self, fileobj):
        self.__fileobj = fileobj
        self.__chunks = {}

        # AIFF Files always start with the FORM chunk which contains a 4 byte
        # ID before the start of other chunks
        fileobj.seek(0)
        self.__chunks[u'FORM'] = IFFChunk(fileobj)

        # Skip past the 4 byte FORM id
        fileobj.seek(IFFChunk.HEADER_SIZE + 4)

        # Where the next chunk can be located. We need to keep track of this
        # since the size indicated in the FORM header may not match up with the
        # offset determined from the size of the last chunk in the file
        self.__next_offset = fileobj.tell()

        # Load all of the chunks
        while True:
            try:
                chunk = IFFChunk(fileobj, self[u'FORM'])
            except InvalidChunk:
                break
            self.__chunks[chunk.id.strip()] = chunk

            # Calculate the location of the next chunk,
            # considering the pad byte
            self.__next_offset = chunk.offset + chunk.size
            self.__next_offset += self.__next_offset % 2
            fileobj.seek(self.__next_offset)

    def __contains__(self, id_):
        """Check if the IFF file contains a specific chunk"""

        if not isinstance(id_, text_type):
            id_ = id_.decode('ascii')

        if not is_valid_chunk_id(id_):
            raise KeyError("AIFF key must be four ASCII characters.")

        return id_ in self.__chunks

    def __getitem__(self, id_):
        """Get a chunk from the IFF file"""

        if not isinstance(id_, text_type):
            id_ = id_.decode('ascii')

        if not is_valid_chunk_id(id_):
            raise KeyError("AIFF key must be four ASCII characters.")

        try:
            return self.__chunks[id_]
        except KeyError:
            raise KeyError(
                "%r has no %r chunk" % (self.__fileobj.name, id_))

    def __delitem__(self, id_):
        """Remove a chunk from the IFF file"""

        if not isinstance(id_, text_type):
            id_ = id_.decode('ascii')

        if not is_valid_chunk_id(id_):
            raise KeyError("AIFF key must be four ASCII characters.")

        self.__chunks.pop(id_).delete()

    def insert_chunk(self, id_):
        """Insert a new chunk at the end of the IFF file"""

        if not isinstance(id_, text_type):
            id_ = id_.decode('ascii')

        if not is_valid_chunk_id(id_):
            raise KeyError("AIFF key must be four ASCII characters.")

        self.__fileobj.seek(self.__next_offset)
        self.__fileobj.write(pack('>4si', id_.ljust(4).encode('ascii'), 0))
        self.__fileobj.seek(self.__next_offset)
        chunk = IFFChunk(self.__fileobj, self[u'FORM'])
        self[u'FORM'].resize(self[u'FORM'].data_size + chunk.size)

        self.__chunks[id_] = chunk
        self.__next_offset = chunk.offset + chunk.size


class AIFFInfo(StreamInfo):
    """AIFF audio stream information.

    Information is parsed from the COMM chunk of the AIFF file

    Useful attributes:

    * length -- audio length, in seconds
    * bitrate -- audio bitrate, in bits per second
    * channels -- The number of audio channels
    * sample_rate -- audio sample rate, in Hz
    * sample_size -- The audio sample size
    """

    length = 0
    bitrate = 0
    channels = 0
    sample_rate = 0

    def __init__(self, fileobj):
        iff = IFFFile(fileobj)
        try:
            common_chunk = iff[u'COMM']
        except KeyError as e:
            raise error(str(e))

        common_chunk.read()

        info = struct.unpack('>hLh10s', common_chunk.data[:18])
        channels, frame_count, sample_size, sample_rate = info

        self.sample_rate = int(read_float(sample_rate))
        self.sample_size = sample_size
        self.channels = channels
        self.bitrate = channels * sample_size * self.sample_rate
        self.length = frame_count / float(self.sample_rate)

    def pprint(self):
        return "%d channel AIFF @ %d bps, %s Hz, %.2f seconds" % (
            self.channels, self.bitrate, self.sample_rate, self.length)


class _IFFID3(ID3):
    """A AIFF file with ID3v2 tags"""

    def _load_header(self):
        try:
            self._fileobj.seek(IFFFile(self._fileobj)[u'ID3'].data_offset)
        except (InvalidChunk, KeyError):
            raise ID3Error()
        super(_IFFID3, self)._load_header()

    def save(self, filename=None, v2_version=4, v23_sep='/'):
        """Save ID3v2 data to the AIFF file"""

        framedata = self._prepare_framedata(v2_version, v23_sep)
        framesize = len(framedata)

        if filename is None:
            filename = self.filename

        # Unlike the parent ID3.save method, we won't save to a blank file
        # since we would have to construct a empty AIFF file
        fileobj = open(filename, 'rb+')
        iff_file = IFFFile(fileobj)

        try:
            if u'ID3' not in iff_file:
                iff_file.insert_chunk(u'ID3')

            chunk = iff_file[u'ID3']
            fileobj.seek(chunk.data_offset)

            header = fileobj.read(10)
            header = self._prepare_id3_header(header, framesize, v2_version)
            header, new_size, _ = header

            data = header + framedata + (b'\x00' * (new_size - framesize))

            # Include ID3 header size in 'new_size' calculation
            new_size += 10

            # Expand the chunk if necessary, including pad byte
            if new_size > chunk.size:
                insert_at = chunk.offset + chunk.size
                insert_size = new_size - chunk.size + new_size % 2
                insert_bytes(fileobj, insert_size, insert_at)
                chunk.resize(new_size)

            fileobj.seek(chunk.data_offset)
            fileobj.write(data)
        finally:
            fileobj.close()

    def delete(self, filename=None):
        """Completely removes the ID3 chunk from the AIFF file"""

        if filename is None:
            filename = self.filename
        delete(filename)
        self.clear()


def delete(filename):
    """Completely removes the ID3 chunk from the AIFF file"""

    with open(filename, "rb+") as file_:
        try:
            del IFFFile(file_)[u'ID3']
        except KeyError:
            pass


class AIFF(FileType):
    """An AIFF audio file.

    :ivar info: :class:`AIFFInfo`
    :ivar tags: :class:`ID3`
    """

    _mimes = ["audio/aiff", "audio/x-aiff"]

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"FORM") * 2 + endswith(filename, b".aif") +
                endswith(filename, b".aiff") + endswith(filename, b".aifc"))

    def add_tags(self):
        """Add an empty ID3 tag to the file."""
        if self.tags is None:
            self.tags = _IFFID3()
        else:
            raise error("an ID3 tag already exists")

    def load(self, filename, **kwargs):
        """Load stream and tag information from a file."""
        self.filename = filename

        try:
            self.tags = _IFFID3(filename, **kwargs)
        except ID3Error:
            self.tags = None

        try:
            fileobj = open(filename, "rb")
            self.info = AIFFInfo(fileobj)
        finally:
            fileobj.close()


Open = AIFF
