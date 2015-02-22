# -*- coding: utf-8 -*-

# Copyright (C) 2006  Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""OptimFROG audio streams with APEv2 tags.

OptimFROG is a lossless audio compression program. Its main goal is to
reduce at maximum the size of audio files, while permitting bit
identical restoration for all input. It is similar with the ZIP
compression, but it is highly specialized to compress audio data.

Only versions 4.5 and higher are supported.

For more information, see http://www.losslessaudio.org/
"""

__all__ = ["OptimFROG", "Open", "delete"]

import struct

from ._compat import endswith
from mutagen import StreamInfo
from mutagen.apev2 import APEv2File, error, delete


class OptimFROGHeaderError(error):
    pass


class OptimFROGInfo(StreamInfo):
    """OptimFROG stream information.

    Attributes:

    * channels - number of audio channels
    * length - file length in seconds, as a float
    * sample_rate - audio sampling rate in Hz
    """

    def __init__(self, fileobj):
        header = fileobj.read(76)
        if (len(header) != 76 or not header.startswith(b"OFR ") or
                struct.unpack("<I", header[4:8])[0] not in [12, 15]):
            raise OptimFROGHeaderError("not an OptimFROG file")
        (total_samples, total_samples_high, sample_type, self.channels,
         self.sample_rate) = struct.unpack("<IHBBI", header[8:20])
        total_samples += total_samples_high << 32
        self.channels += 1
        if self.sample_rate:
            self.length = float(total_samples) / (self.channels *
                                                  self.sample_rate)
        else:
            self.length = 0.0

    def pprint(self):
        return "OptimFROG, %.2f seconds, %d Hz" % (self.length,
                                                   self.sample_rate)


class OptimFROG(APEv2File):
    _Info = OptimFROGInfo

    @staticmethod
    def score(filename, fileobj, header):
        filename = filename.lower()

        return (header.startswith(b"OFR") + endswith(filename, b".ofr") +
                endswith(filename, b".ofs"))

Open = OptimFROG
