# -*- coding: utf-8 -*-

# Copyright (C) 2005  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""Read and write FLAC Vorbis comments and stream information.

Read more about FLAC at http://flac.sourceforge.net.

FLAC supports arbitrary metadata blocks. The two most interesting ones
are the FLAC stream information block, and the Vorbis comment block;
these are also the only ones Mutagen can currently read.

This module does not handle Ogg FLAC files.

Based off documentation available at
http://flac.sourceforge.net/format.html
"""

__all__ = ["FLAC", "Open", "delete"]

import struct
from ._vorbis import VCommentDict
import mutagen

from ._compat import cBytesIO, endswith, chr_
from mutagen._util import insert_bytes, MutagenError
from mutagen.id3 import BitPaddedInt
from functools import reduce


class error(IOError, MutagenError):
    pass


class FLACNoHeaderError(error):
    pass


class FLACVorbisError(ValueError, error):
    pass


def to_int_be(data):
    """Convert an arbitrarily-long string to a long using big-endian
    byte order."""
    return reduce(lambda a, b: (a << 8) + b, bytearray(data), 0)


class StrictFileObject(object):
    """Wraps a file-like object and raises an exception if the requested
    amount of data to read isn't returned."""

    def __init__(self, fileobj):
        self._fileobj = fileobj
        for m in ["close", "tell", "seek", "write", "name"]:
            if hasattr(fileobj, m):
                setattr(self, m, getattr(fileobj, m))

    def read(self, size=-1):
        data = self._fileobj.read(size)
        if size >= 0 and len(data) != size:
            raise error("file said %d bytes, read %d bytes" % (
                        size, len(data)))
        return data

    def tryread(self, *args):
        return self._fileobj.read(*args)


class MetadataBlock(object):
    """A generic block of FLAC metadata.

    This class is extended by specific used as an ancestor for more specific
    blocks, and also as a container for data blobs of unknown blocks.

    Attributes:

    * data -- raw binary data for this block
    """

    _distrust_size = False

    def __init__(self, data):
        """Parse the given data string or file-like as a metadata block.
        The metadata header should not be included."""
        if data is not None:
            if not isinstance(data, StrictFileObject):
                if isinstance(data, bytes):
                    data = cBytesIO(data)
                elif not hasattr(data, 'read'):
                    raise TypeError(
                        "StreamInfo requires string data or a file-like")
                data = StrictFileObject(data)
            self.load(data)

    def load(self, data):
        self.data = data.read()

    def write(self):
        return self.data

    @staticmethod
    def writeblocks(blocks):
        """Render metadata block as a byte string."""
        data = []
        codes = [[block.code, block.write()] for block in blocks]
        codes[-1][0] |= 128
        for code, datum in codes:
            byte = chr_(code)
            if len(datum) > 2 ** 24:
                raise error("block is too long to write")
            length = struct.pack(">I", len(datum))[-3:]
            data.append(byte + length + datum)
        return b"".join(data)

    @staticmethod
    def group_padding(blocks):
        """Consolidate FLAC padding metadata blocks.

        The overall size of the rendered blocks does not change, so
        this adds several bytes of padding for each merged block.
        """

        paddings = [b for b in blocks if isinstance(b, Padding)]
        for p in paddings:
            blocks.remove(p)
        # total padding size is the sum of padding sizes plus 4 bytes
        # per removed header.
        size = sum(padding.length for padding in paddings)
        padding = Padding()
        padding.length = size + 4 * (len(paddings) - 1)
        blocks.append(padding)


class StreamInfo(MetadataBlock, mutagen.StreamInfo):
    """FLAC stream information.

    This contains information about the audio data in the FLAC file.
    Unlike most stream information objects in Mutagen, changes to this
    one will rewritten to the file when it is saved. Unless you are
    actually changing the audio stream itself, don't change any
    attributes of this block.

    Attributes:

    * min_blocksize -- minimum audio block size
    * max_blocksize -- maximum audio block size
    * sample_rate -- audio sample rate in Hz
    * channels -- audio channels (1 for mono, 2 for stereo)
    * bits_per_sample -- bits per sample
    * total_samples -- total samples in file
    * length -- audio length in seconds
    """

    code = 0

    def __eq__(self, other):
        try:
            return (self.min_blocksize == other.min_blocksize and
                    self.max_blocksize == other.max_blocksize and
                    self.sample_rate == other.sample_rate and
                    self.channels == other.channels and
                    self.bits_per_sample == other.bits_per_sample and
                    self.total_samples == other.total_samples)
        except:
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        self.min_blocksize = int(to_int_be(data.read(2)))
        self.max_blocksize = int(to_int_be(data.read(2)))
        self.min_framesize = int(to_int_be(data.read(3)))
        self.max_framesize = int(to_int_be(data.read(3)))
        # first 16 bits of sample rate
        sample_first = to_int_be(data.read(2))
        # last 4 bits of sample rate, 3 of channels, first 1 of bits/sample
        sample_channels_bps = to_int_be(data.read(1))
        # last 4 of bits/sample, 36 of total samples
        bps_total = to_int_be(data.read(5))

        sample_tail = sample_channels_bps >> 4
        self.sample_rate = int((sample_first << 4) + sample_tail)
        if not self.sample_rate:
            raise error("A sample rate value of 0 is invalid")
        self.channels = int(((sample_channels_bps >> 1) & 7) + 1)
        bps_tail = bps_total >> 36
        bps_head = (sample_channels_bps & 1) << 4
        self.bits_per_sample = int(bps_head + bps_tail + 1)
        self.total_samples = bps_total & 0xFFFFFFFFF
        self.length = self.total_samples / float(self.sample_rate)

        self.md5_signature = to_int_be(data.read(16))

    def write(self):
        f = cBytesIO()
        f.write(struct.pack(">I", self.min_blocksize)[-2:])
        f.write(struct.pack(">I", self.max_blocksize)[-2:])
        f.write(struct.pack(">I", self.min_framesize)[-3:])
        f.write(struct.pack(">I", self.max_framesize)[-3:])

        # first 16 bits of sample rate
        f.write(struct.pack(">I", self.sample_rate >> 4)[-2:])
        # 4 bits sample, 3 channel, 1 bps
        byte = (self.sample_rate & 0xF) << 4
        byte += ((self.channels - 1) & 7) << 1
        byte += ((self.bits_per_sample - 1) >> 4) & 1
        f.write(chr_(byte))
        # 4 bits of bps, 4 of sample count
        byte = ((self.bits_per_sample - 1) & 0xF) << 4
        byte += (self.total_samples >> 32) & 0xF
        f.write(chr_(byte))
        # last 32 of sample count
        f.write(struct.pack(">I", self.total_samples & 0xFFFFFFFF))
        # MD5 signature
        sig = self.md5_signature
        f.write(struct.pack(
            ">4I", (sig >> 96) & 0xFFFFFFFF, (sig >> 64) & 0xFFFFFFFF,
            (sig >> 32) & 0xFFFFFFFF, sig & 0xFFFFFFFF))
        return f.getvalue()

    def pprint(self):
        return "FLAC, %.2f seconds, %d Hz" % (self.length, self.sample_rate)


class SeekPoint(tuple):
    """A single seek point in a FLAC file.

    Placeholder seek points have first_sample of 0xFFFFFFFFFFFFFFFFL,
    and byte_offset and num_samples undefined. Seek points must be
    sorted in ascending order by first_sample number. Seek points must
    be unique by first_sample number, except for placeholder
    points. Placeholder points must occur last in the table and there
    may be any number of them.

    Attributes:

    * first_sample -- sample number of first sample in the target frame
    * byte_offset -- offset from first frame to target frame
    * num_samples -- number of samples in target frame
    """

    def __new__(cls, first_sample, byte_offset, num_samples):
        return super(cls, SeekPoint).__new__(
            cls, (first_sample, byte_offset, num_samples))

    first_sample = property(lambda self: self[0])
    byte_offset = property(lambda self: self[1])
    num_samples = property(lambda self: self[2])


class SeekTable(MetadataBlock):
    """Read and write FLAC seek tables.

    Attributes:

    * seekpoints -- list of SeekPoint objects
    """

    __SEEKPOINT_FORMAT = '>QQH'
    __SEEKPOINT_SIZE = struct.calcsize(__SEEKPOINT_FORMAT)

    code = 3

    def __init__(self, data):
        self.seekpoints = []
        super(SeekTable, self).__init__(data)

    def __eq__(self, other):
        try:
            return (self.seekpoints == other.seekpoints)
        except (AttributeError, TypeError):
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        self.seekpoints = []
        sp = data.tryread(self.__SEEKPOINT_SIZE)
        while len(sp) == self.__SEEKPOINT_SIZE:
            self.seekpoints.append(SeekPoint(
                *struct.unpack(self.__SEEKPOINT_FORMAT, sp)))
            sp = data.tryread(self.__SEEKPOINT_SIZE)

    def write(self):
        f = cBytesIO()
        for seekpoint in self.seekpoints:
            packed = struct.pack(
                self.__SEEKPOINT_FORMAT,
                seekpoint.first_sample, seekpoint.byte_offset,
                seekpoint.num_samples)
            f.write(packed)
        return f.getvalue()

    def __repr__(self):
        return "<%s seekpoints=%r>" % (type(self).__name__, self.seekpoints)


class VCFLACDict(VCommentDict):
    """Read and write FLAC Vorbis comments.

    FLACs don't use the framing bit at the end of the comment block.
    So this extends VCommentDict to not use the framing bit.
    """

    code = 4
    _distrust_size = True

    def load(self, data, errors='replace', framing=False):
        super(VCFLACDict, self).load(data, errors=errors, framing=framing)

    def write(self, framing=False):
        return super(VCFLACDict, self).write(framing=framing)


class CueSheetTrackIndex(tuple):
    """Index for a track in a cuesheet.

    For CD-DA, an index_number of 0 corresponds to the track
    pre-gap. The first index in a track must have a number of 0 or 1,
    and subsequently, index_numbers must increase by 1. Index_numbers
    must be unique within a track. And index_offset must be evenly
    divisible by 588 samples.

    Attributes:

    * index_number -- index point number
    * index_offset -- offset in samples from track start
    """

    def __new__(cls, index_number, index_offset):
        return super(cls, CueSheetTrackIndex).__new__(
            cls, (index_number, index_offset))

    index_number = property(lambda self: self[0])
    index_offset = property(lambda self: self[1])


class CueSheetTrack(object):
    """A track in a cuesheet.

    For CD-DA, track_numbers must be 1-99, or 170 for the
    lead-out. Track_numbers must be unique within a cue sheet. There
    must be atleast one index in every track except the lead-out track
    which must have none.

    Attributes:

    * track_number -- track number
    * start_offset -- track offset in samples from start of FLAC stream
    * isrc -- ISRC code
    * type -- 0 for audio, 1 for digital data
    * pre_emphasis -- true if the track is recorded with pre-emphasis
    * indexes -- list of CueSheetTrackIndex objects
    """

    def __init__(self, track_number, start_offset, isrc='', type_=0,
                 pre_emphasis=False):
        self.track_number = track_number
        self.start_offset = start_offset
        self.isrc = isrc
        self.type = type_
        self.pre_emphasis = pre_emphasis
        self.indexes = []

    def __eq__(self, other):
        try:
            return (self.track_number == other.track_number and
                    self.start_offset == other.start_offset and
                    self.isrc == other.isrc and
                    self.type == other.type and
                    self.pre_emphasis == other.pre_emphasis and
                    self.indexes == other.indexes)
        except (AttributeError, TypeError):
            return False

    __hash__ = object.__hash__

    def __repr__(self):
        return (("<%s number=%r, offset=%d, isrc=%r, type=%r, "
                "pre_emphasis=%r, indexes=%r)>") %
                (type(self).__name__, self.track_number, self.start_offset,
                 self.isrc, self.type, self.pre_emphasis, self.indexes))


class CueSheet(MetadataBlock):
    """Read and write FLAC embedded cue sheets.

    Number of tracks should be from 1 to 100. There should always be
    exactly one lead-out track and that track must be the last track
    in the cue sheet.

    Attributes:

    * media_catalog_number -- media catalog number in ASCII
    * lead_in_samples -- number of lead-in samples
    * compact_disc -- true if the cuesheet corresponds to a compact disc
    * tracks -- list of CueSheetTrack objects
    * lead_out -- lead-out as CueSheetTrack or None if lead-out was not found
    """

    __CUESHEET_FORMAT = '>128sQB258xB'
    __CUESHEET_SIZE = struct.calcsize(__CUESHEET_FORMAT)
    __CUESHEET_TRACK_FORMAT = '>QB12sB13xB'
    __CUESHEET_TRACK_SIZE = struct.calcsize(__CUESHEET_TRACK_FORMAT)
    __CUESHEET_TRACKINDEX_FORMAT = '>QB3x'
    __CUESHEET_TRACKINDEX_SIZE = struct.calcsize(__CUESHEET_TRACKINDEX_FORMAT)

    code = 5

    media_catalog_number = b''
    lead_in_samples = 88200
    compact_disc = True

    def __init__(self, data):
        self.tracks = []
        super(CueSheet, self).__init__(data)

    def __eq__(self, other):
        try:
            return (self.media_catalog_number == other.media_catalog_number and
                    self.lead_in_samples == other.lead_in_samples and
                    self.compact_disc == other.compact_disc and
                    self.tracks == other.tracks)
        except (AttributeError, TypeError):
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        header = data.read(self.__CUESHEET_SIZE)
        media_catalog_number, lead_in_samples, flags, num_tracks = \
            struct.unpack(self.__CUESHEET_FORMAT, header)
        self.media_catalog_number = media_catalog_number.rstrip(b'\0')
        self.lead_in_samples = lead_in_samples
        self.compact_disc = bool(flags & 0x80)
        self.tracks = []
        for i in range(num_tracks):
            track = data.read(self.__CUESHEET_TRACK_SIZE)
            start_offset, track_number, isrc_padded, flags, num_indexes = \
                struct.unpack(self.__CUESHEET_TRACK_FORMAT, track)
            isrc = isrc_padded.rstrip(b'\0')
            type_ = (flags & 0x80) >> 7
            pre_emphasis = bool(flags & 0x40)
            val = CueSheetTrack(
                track_number, start_offset, isrc, type_, pre_emphasis)
            for j in range(num_indexes):
                index = data.read(self.__CUESHEET_TRACKINDEX_SIZE)
                index_offset, index_number = struct.unpack(
                    self.__CUESHEET_TRACKINDEX_FORMAT, index)
                val.indexes.append(
                    CueSheetTrackIndex(index_number, index_offset))
            self.tracks.append(val)

    def write(self):
        f = cBytesIO()
        flags = 0
        if self.compact_disc:
            flags |= 0x80
        packed = struct.pack(
            self.__CUESHEET_FORMAT, self.media_catalog_number,
            self.lead_in_samples, flags, len(self.tracks))
        f.write(packed)
        for track in self.tracks:
            track_flags = 0
            track_flags |= (track.type & 1) << 7
            if track.pre_emphasis:
                track_flags |= 0x40
            track_packed = struct.pack(
                self.__CUESHEET_TRACK_FORMAT, track.start_offset,
                track.track_number, track.isrc, track_flags,
                len(track.indexes))
            f.write(track_packed)
            for index in track.indexes:
                index_packed = struct.pack(
                    self.__CUESHEET_TRACKINDEX_FORMAT,
                    index.index_offset, index.index_number)
                f.write(index_packed)
        return f.getvalue()

    def __repr__(self):
        return (("<%s media_catalog_number=%r, lead_in=%r, compact_disc=%r, "
                 "tracks=%r>") %
                (type(self).__name__, self.media_catalog_number,
                 self.lead_in_samples, self.compact_disc, self.tracks))


class Picture(MetadataBlock):
    """Read and write FLAC embed pictures.

    Attributes:

    * type -- picture type (same as types for ID3 APIC frames)
    * mime -- MIME type of the picture
    * desc -- picture's description
    * width -- width in pixels
    * height -- height in pixels
    * depth -- color depth in bits-per-pixel
    * colors -- number of colors for indexed palettes (like GIF),
      0 for non-indexed
    * data -- picture data
    """

    code = 6
    _distrust_size = True

    def __init__(self, data=None):
        self.type = 0
        self.mime = u''
        self.desc = u''
        self.width = 0
        self.height = 0
        self.depth = 0
        self.colors = 0
        self.data = b''
        super(Picture, self).__init__(data)

    def __eq__(self, other):
        try:
            return (self.type == other.type and
                    self.mime == other.mime and
                    self.desc == other.desc and
                    self.width == other.width and
                    self.height == other.height and
                    self.depth == other.depth and
                    self.colors == other.colors and
                    self.data == other.data)
        except (AttributeError, TypeError):
            return False

    __hash__ = MetadataBlock.__hash__

    def load(self, data):
        self.type, length = struct.unpack('>2I', data.read(8))
        self.mime = data.read(length).decode('UTF-8', 'replace')
        length, = struct.unpack('>I', data.read(4))
        self.desc = data.read(length).decode('UTF-8', 'replace')
        (self.width, self.height, self.depth,
         self.colors, length) = struct.unpack('>5I', data.read(20))
        self.data = data.read(length)

    def write(self):
        f = cBytesIO()
        mime = self.mime.encode('UTF-8')
        f.write(struct.pack('>2I', self.type, len(mime)))
        f.write(mime)
        desc = self.desc.encode('UTF-8')
        f.write(struct.pack('>I', len(desc)))
        f.write(desc)
        f.write(struct.pack('>5I', self.width, self.height, self.depth,
                            self.colors, len(self.data)))
        f.write(self.data)
        return f.getvalue()

    def __repr__(self):
        return "<%s '%s' (%d bytes)>" % (type(self).__name__, self.mime,
                                         len(self.data))


class Padding(MetadataBlock):
    """Empty padding space for metadata blocks.

    To avoid rewriting the entire FLAC file when editing comments,
    metadata is often padded. Padding should occur at the end, and no
    more than one padding block should be in any FLAC file. Mutagen
    handles this with MetadataBlock.group_padding.
    """

    code = 1

    def __init__(self, data=b""):
        super(Padding, self).__init__(data)

    def load(self, data):
        self.length = len(data.read())

    def write(self):
        try:
            return b"\x00" * self.length
        # On some 64 bit platforms this won't generate a MemoryError
        # or OverflowError since you might have enough RAM, but it
        # still generates a ValueError. On other 64 bit platforms,
        # this will still succeed for extremely large values.
        # Those should never happen in the real world, and if they
        # do, writeblocks will catch it.
        except (OverflowError, ValueError, MemoryError):
            raise error("cannot write %d bytes" % self.length)

    def __eq__(self, other):
        return isinstance(other, Padding) and self.length == other.length

    __hash__ = MetadataBlock.__hash__

    def __repr__(self):
        return "<%s (%d bytes)>" % (type(self).__name__, self.length)


class FLAC(mutagen.FileType):
    """A FLAC audio file.

    Attributes:

    * info -- stream information (length, bitrate, sample rate)
    * tags -- metadata tags, if any
    * cuesheet -- CueSheet object, if any
    * seektable -- SeekTable object, if any
    * pictures -- list of embedded pictures
    """

    _mimes = ["audio/x-flac", "application/x-flac"]

    METADATA_BLOCKS = [StreamInfo, Padding, None, SeekTable, VCFLACDict,
                       CueSheet, Picture]
    """Known metadata block types, indexed by ID."""

    @staticmethod
    def score(filename, fileobj, header_data):
        return (header_data.startswith(b"fLaC") +
                endswith(filename.lower(), ".flac") * 3)

    def __read_metadata_block(self, fileobj):
        byte = ord(fileobj.read(1))
        size = to_int_be(fileobj.read(3))
        code = byte & 0x7F
        last_block = bool(byte & 0x80)

        try:
            block_type = self.METADATA_BLOCKS[code] or MetadataBlock
        except IndexError:
            block_type = MetadataBlock

        if block_type._distrust_size:
            # Some jackass is writing broken Metadata block length
            # for Vorbis comment blocks, and the FLAC reference
            # implementaton can parse them (mostly by accident),
            # so we have to too.  Instead of parsing the size
            # given, parse an actual Vorbis comment, leaving
            # fileobj in the right position.
            # http://code.google.com/p/mutagen/issues/detail?id=52
            # ..same for the Picture block:
            # http://code.google.com/p/mutagen/issues/detail?id=106
            block = block_type(fileobj)
        else:
            data = fileobj.read(size)
            block = block_type(data)
        block.code = code

        if block.code == VCFLACDict.code:
            if self.tags is None:
                self.tags = block
            else:
                raise FLACVorbisError("> 1 Vorbis comment block found")
        elif block.code == CueSheet.code:
            if self.cuesheet is None:
                self.cuesheet = block
            else:
                raise error("> 1 CueSheet block found")
        elif block.code == SeekTable.code:
            if self.seektable is None:
                self.seektable = block
            else:
                raise error("> 1 SeekTable block found")
        self.metadata_blocks.append(block)
        return not last_block

    def add_tags(self):
        """Add a Vorbis comment block to the file."""
        if self.tags is None:
            self.tags = VCFLACDict()
            self.metadata_blocks.append(self.tags)
        else:
            raise FLACVorbisError("a Vorbis comment already exists")

    add_vorbiscomment = add_tags

    def delete(self, filename=None):
        """Remove Vorbis comments from a file.

        If no filename is given, the one most recently loaded is used.
        """
        if filename is None:
            filename = self.filename
        for s in list(self.metadata_blocks):
            if isinstance(s, VCFLACDict):
                self.metadata_blocks.remove(s)
                self.tags = None
                self.save()
                break

    vc = property(lambda s: s.tags, doc="Alias for tags; don't use this.")

    def load(self, filename):
        """Load file information from a filename."""

        self.metadata_blocks = []
        self.tags = None
        self.cuesheet = None
        self.seektable = None
        self.filename = filename
        fileobj = StrictFileObject(open(filename, "rb"))
        try:
            self.__check_header(fileobj)
            while self.__read_metadata_block(fileobj):
                pass
        finally:
            fileobj.close()

        try:
            self.metadata_blocks[0].length
        except (AttributeError, IndexError):
            raise FLACNoHeaderError("Stream info block not found")

    @property
    def info(self):
        return self.metadata_blocks[0]

    def add_picture(self, picture):
        """Add a new picture to the file."""
        self.metadata_blocks.append(picture)

    def clear_pictures(self):
        """Delete all pictures from the file."""

        blocks = [b for b in self.metadata_blocks if b.code != Picture.code]
        self.metadata_blocks = blocks

    @property
    def pictures(self):
        """List of embedded pictures"""

        return [b for b in self.metadata_blocks if b.code == Picture.code]

    def save(self, filename=None, deleteid3=False):
        """Save metadata blocks to a file.

        If no filename is given, the one most recently loaded is used.
        """

        if filename is None:
            filename = self.filename
        f = open(filename, 'rb+')

        try:
            # Ensure we've got padding at the end, and only at the end.
            # If adding makes it too large, we'll scale it down later.
            self.metadata_blocks.append(Padding(b'\x00' * 1020))
            MetadataBlock.group_padding(self.metadata_blocks)

            header = self.__check_header(f)
            # "fLaC" and maybe ID3
            available = self.__find_audio_offset(f) - header
            data = MetadataBlock.writeblocks(self.metadata_blocks)

            # Delete ID3v2
            if deleteid3 and header > 4:
                available += header - 4
                header = 4

            if len(data) > available:
                # If we have too much data, see if we can reduce padding.
                padding = self.metadata_blocks[-1]
                newlength = padding.length - (len(data) - available)
                if newlength > 0:
                    padding.length = newlength
                    data = MetadataBlock.writeblocks(self.metadata_blocks)
                    assert len(data) == available

            elif len(data) < available:
                # If we have too little data, increase padding.
                self.metadata_blocks[-1].length += (available - len(data))
                data = MetadataBlock.writeblocks(self.metadata_blocks)
                assert len(data) == available

            if len(data) != available:
                # We couldn't reduce the padding enough.
                diff = (len(data) - available)
                insert_bytes(f, diff, header)

            f.seek(header - 4)
            f.write(b"fLaC" + data)

            # Delete ID3v1
            if deleteid3:
                try:
                    f.seek(-128, 2)
                except IOError:
                    pass
                else:
                    if f.read(3) == b"TAG":
                        f.seek(-128, 2)
                        f.truncate()
        finally:
            f.close()

    def __find_audio_offset(self, fileobj):
        byte = 0x00
        while not (byte & 0x80):
            byte = ord(fileobj.read(1))
            size = to_int_be(fileobj.read(3))
            try:
                block_type = self.METADATA_BLOCKS[byte & 0x7F]
            except IndexError:
                block_type = None

            if block_type and block_type._distrust_size:
                # See comments in read_metadata_block; the size can't
                # be trusted for Vorbis comment blocks and Picture block
                block_type(fileobj)
            else:
                fileobj.read(size)
        return fileobj.tell()

    def __check_header(self, fileobj):
        size = 4
        header = fileobj.read(4)
        if header != b"fLaC":
            size = None
            if header[:3] == b"ID3":
                size = 14 + BitPaddedInt(fileobj.read(6)[2:])
                fileobj.seek(size - 4)
                if fileobj.read(4) != b"fLaC":
                    size = None
        if size is None:
            raise FLACNoHeaderError(
                "%r is not a valid FLAC file" % fileobj.name)
        return size


Open = FLAC


def delete(filename):
    """Remove tags from a file."""
    FLAC(filename).delete()
