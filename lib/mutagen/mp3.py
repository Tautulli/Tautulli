# -*- coding: utf-8 -*-

# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""MPEG audio stream information and tags."""

import os
import struct

from ._compat import endswith
from mutagen import StreamInfo
from mutagen._util import MutagenError
from mutagen.id3 import ID3FileType, BitPaddedInt, delete

__all__ = ["MP3", "Open", "delete", "MP3"]


class error(RuntimeError, MutagenError):
    pass


class HeaderNotFoundError(error, IOError):
    pass


class InvalidMPEGHeader(error, IOError):
    pass


# Mode values.
STEREO, JOINTSTEREO, DUALCHANNEL, MONO = range(4)


class MPEGInfo(StreamInfo):
    """MPEG audio stream information

    Parse information about an MPEG audio file. This also reads the
    Xing VBR header format.

    This code was implemented based on the format documentation at
    http://mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm.

    Useful attributes:

    * length -- audio length, in seconds
    * bitrate -- audio bitrate, in bits per second
    * sketchy -- if true, the file may not be valid MPEG audio

    Useless attributes:

    * version -- MPEG version (1, 2, 2.5)
    * layer -- 1, 2, or 3
    * mode -- One of STEREO, JOINTSTEREO, DUALCHANNEL, or MONO (0-3)
    * protected -- whether or not the file is "protected"
    * padding -- whether or not audio frames are padded
    * sample_rate -- audio sample rate, in Hz
    """

    # Map (version, layer) tuples to bitrates.
    __BITRATE = {
        (1, 1): [0, 32, 64, 96, 128, 160, 192, 224,
                 256, 288, 320, 352, 384, 416, 448],
        (1, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128,
                 160, 192, 224, 256, 320, 384],
        (1, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112,
                 128, 160, 192, 224, 256, 320],
        (2, 1): [0, 32, 48, 56, 64, 80, 96, 112, 128,
                 144, 160, 176, 192, 224, 256],
        (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64,
                 80, 96, 112, 128, 144, 160],
    }

    __BITRATE[(2, 3)] = __BITRATE[(2, 2)]
    for i in range(1, 4):
        __BITRATE[(2.5, i)] = __BITRATE[(2, i)]

    # Map version to sample rates.
    __RATES = {
        1: [44100, 48000, 32000],
        2: [22050, 24000, 16000],
        2.5: [11025, 12000, 8000]
    }

    sketchy = False

    def __init__(self, fileobj, offset=None):
        """Parse MPEG stream information from a file-like object.

        If an offset argument is given, it is used to start looking
        for stream information and Xing headers; otherwise, ID3v2 tags
        will be skipped automatically. A correct offset can make
        loading files significantly faster.
        """

        try:
            size = os.path.getsize(fileobj.name)
        except (IOError, OSError, AttributeError):
            fileobj.seek(0, 2)
            size = fileobj.tell()

        # If we don't get an offset, try to skip an ID3v2 tag.
        if offset is None:
            fileobj.seek(0, 0)
            idata = fileobj.read(10)
            try:
                id3, insize = struct.unpack('>3sxxx4s', idata)
            except struct.error:
                id3, insize = '', 0
            insize = BitPaddedInt(insize)
            if id3 == b'ID3' and insize > 0:
                offset = insize + 10
            else:
                offset = 0

        # Try to find two valid headers (meaning, very likely MPEG data)
        # at the given offset, 30% through the file, 60% through the file,
        # and 90% through the file.
        for i in [offset, 0.3 * size, 0.6 * size, 0.9 * size]:
            try:
                self.__try(fileobj, int(i), size - offset)
            except error:
                pass
            else:
                break
        # If we can't find any two consecutive frames, try to find just
        # one frame back at the original offset given.
        else:
            self.__try(fileobj, offset, size - offset, False)
            self.sketchy = True

    def __try(self, fileobj, offset, real_size, check_second=True):
        # This is going to be one really long function; bear with it,
        # because there's not really a sane point to cut it up.
        fileobj.seek(offset, 0)

        # We "know" we have an MPEG file if we find two frames that look like
        # valid MPEG data. If we can't find them in 32k of reads, something
        # is horribly wrong (the longest frame can only be about 4k). This
        # is assuming the offset didn't lie.
        data = fileobj.read(32768)

        frame_1 = data.find(b"\xff")
        while 0 <= frame_1 <= (len(data) - 4):
            frame_data = struct.unpack(">I", data[frame_1:frame_1 + 4])[0]
            if ((frame_data >> 16) & 0xE0) != 0xE0:
                frame_1 = data.find(b"\xff", frame_1 + 2)
            else:
                version = (frame_data >> 19) & 0x3
                layer = (frame_data >> 17) & 0x3
                protection = (frame_data >> 16) & 0x1
                bitrate = (frame_data >> 12) & 0xF
                sample_rate = (frame_data >> 10) & 0x3
                padding = (frame_data >> 9) & 0x1
                # private = (frame_data >> 8) & 0x1
                self.mode = (frame_data >> 6) & 0x3
                # mode_extension = (frame_data >> 4) & 0x3
                # copyright = (frame_data >> 3) & 0x1
                # original = (frame_data >> 2) & 0x1
                # emphasis = (frame_data >> 0) & 0x3
                if (version == 1 or layer == 0 or sample_rate == 0x3 or
                        bitrate == 0 or bitrate == 0xF):
                    frame_1 = data.find(b"\xff", frame_1 + 2)
                else:
                    break
        else:
            raise HeaderNotFoundError("can't sync to an MPEG frame")

        # There is a serious problem here, which is that many flags
        # in an MPEG header are backwards.
        self.version = [2.5, None, 2, 1][version]
        self.layer = 4 - layer
        self.protected = not protection
        self.padding = bool(padding)

        self.bitrate = self.__BITRATE[(self.version, self.layer)][bitrate]
        self.bitrate *= 1000
        self.sample_rate = self.__RATES[self.version][sample_rate]

        if self.layer == 1:
            frame_length = (
                (12 * self.bitrate // self.sample_rate) + padding) * 4
            frame_size = 384
        elif self.version >= 2 and self.layer == 3:
            frame_length = (72 * self.bitrate // self.sample_rate) + padding
            frame_size = 576
        else:
            frame_length = (144 * self.bitrate // self.sample_rate) + padding
            frame_size = 1152

        if check_second:
            possible = int(frame_1 + frame_length)
            if possible > len(data) + 4:
                raise HeaderNotFoundError("can't sync to second MPEG frame")
            try:
                frame_data = struct.unpack(
                    ">H", data[possible:possible + 2])[0]
            except struct.error:
                raise HeaderNotFoundError("can't sync to second MPEG frame")
            if (frame_data & 0xFFE0) != 0xFFE0:
                raise HeaderNotFoundError("can't sync to second MPEG frame")

        self.length = 8 * real_size / float(self.bitrate)

        # Try to find/parse the Xing header, which trumps the above length
        # and bitrate calculation.
        fileobj.seek(offset, 0)
        data = fileobj.read(32768)
        try:
            xing = data[:-4].index(b"Xing")
        except ValueError:
            # Try to find/parse the VBRI header, which trumps the above length
            # calculation.
            try:
                vbri = data[:-24].index(b"VBRI")
            except ValueError:
                pass
            else:
                # If a VBRI header was found, this is definitely MPEG audio.
                self.sketchy = False
                vbri_version = struct.unpack('>H', data[vbri + 4:vbri + 6])[0]
                if vbri_version == 1:
                    frame_count = struct.unpack(
                        '>I', data[vbri + 14:vbri + 18])[0]
                    samples = float(frame_size * frame_count)
                    self.length = (samples / self.sample_rate) or self.length
        else:
            # If a Xing header was found, this is definitely MPEG audio.
            self.sketchy = False
            flags = struct.unpack('>I', data[xing + 4:xing + 8])[0]
            if flags & 0x1:
                frame_count = struct.unpack('>I', data[xing + 8:xing + 12])[0]
                samples = float(frame_size * frame_count)
                self.length = (samples / self.sample_rate) or self.length
            if flags & 0x2:
                bitrate_data = struct.unpack(
                    '>I', data[xing + 12:xing + 16])[0]
                self.bitrate = int((bitrate_data * 8) // self.length)

    def pprint(self):
        s = "MPEG %s layer %d, %d bps, %s Hz, %.2f seconds" % (
            self.version, self.layer, self.bitrate, self.sample_rate,
            self.length)
        if self.sketchy:
            s += " (sketchy)"
        return s


class MP3(ID3FileType):
    """An MPEG audio (usually MPEG-1 Layer 3) file.

    :ivar info: :class:`MPEGInfo`
    :ivar tags: :class:`ID3 <mutagen.id3.ID3>`
    """

    _Info = MPEGInfo

    _mimes = ["audio/mpeg", "audio/mpg", "audio/x-mpeg"]

    @property
    def mime(self):
        l = self.info.layer
        return ["audio/mp%d" % l, "audio/x-mp%d" % l] + super(MP3, self).mime

    @staticmethod
    def score(filename, fileobj, header_data):
        filename = filename.lower()

        return (header_data.startswith(b"ID3") * 2 +
                endswith(filename, b".mp3") +
                endswith(filename, b".mp2") + endswith(filename, b".mpg") +
                endswith(filename, b".mpeg"))


Open = MP3


class EasyMP3(MP3):
    """Like MP3, but uses EasyID3 for tags.

    :ivar info: :class:`MPEGInfo`
    :ivar tags: :class:`EasyID3 <mutagen.easyid3.EasyID3>`
    """

    from mutagen.easyid3 import EasyID3 as ID3
    ID3 = ID3
