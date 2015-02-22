# -*- coding: utf-8 -*-

# Copyright (C) 2006  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Monkey's Audio streams with APEv2 tags.

Monkey's Audio is a very efficient lossless audio compressor developed
by Matt Ashland.

For more information, see http://www.monkeysaudio.com/.
"""

__all__ = ["MonkeysAudio", "Open", "delete"]

import struct

from ._compat import endswith
from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, error, delete
from mutagen._util import cdata


class MonkeysAudioHeaderError(error):
    pass


class MonkeysAudioInfo(StreamInfo):
    """Monkey's Audio stream information.

    Attributes:

    * channels -- number of audio channels
    * length -- file length in seconds, as a float
    * sample_rate -- audio sampling rate in Hz
    * bits_per_sample -- bits per sample
    * version -- Monkey's Audio stream version, as a float (eg: 3.99)
    """

    def __init__(self, fileobj):
        header = fileobj.read(76)
        if len(header) != 76 or not header.startswith(b"MAC "):
            raise MonkeysAudioHeaderError("not a Monkey's Audio file")
        self.version = cdata.ushort_le(header[4:6])
        if self.version >= 3980:
            (blocks_per_frame, final_frame_blocks, total_frames,
             self.bits_per_sample, self.channels,
             self.sample_rate) = struct.unpack("<IIIHHI", header[56:76])
        else:
            compression_level = cdata.ushort_le(header[6:8])
            self.channels, self.sample_rate = struct.unpack(
                "<HI", header[10:16])
            total_frames, final_frame_blocks = struct.unpack(
                "<II", header[24:32])
            if self.version >= 3950:
                blocks_per_frame = 73728 * 4
            elif self.version >= 3900 or (self.version >= 3800 and
                                          compression_level == 4):
                blocks_per_frame = 73728
            else:
                blocks_per_frame = 9216
        self.version /= 1000.0
        self.length = 0.0
        if (self.sample_rate != 0) and (total_frames > 0):
            total_blocks = ((total_frames - 1) * blocks_per_frame +
                            final_frame_blocks)
            self.length = float(total_blocks) / self.sample_rate

    def pprint(self):
        return "Monkey's Audio %.2f, %.2f seconds, %d Hz" % (
            self.version, self.length, self.sample_rate)


class MonkeysAudio(APEv2File):
    _Info = MonkeysAudioInfo
    _mimes = ["audio/ape", "audio/x-ape"]

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(b"MAC ") + endswith(filename.lower(), ".ape")


Open = MonkeysAudio
