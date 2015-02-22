# -*- coding: utf-8 -*-

# Copyright (C) 2012, 2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write Ogg Opus comments.

This module handles Opus files wrapped in an Ogg bitstream. The
first Opus stream found is used.

Based on http://tools.ietf.org/html/draft-terriberry-oggopus-01
"""

__all__ = ["OggOpus", "Open", "delete"]

import struct

from mutagen import StreamInfo
from mutagen._compat import BytesIO
from mutagen._vorbis import VCommentDict
from mutagen.ogg import OggPage, OggFileType, error as OggError


class error(OggError):
    pass


class OggOpusHeaderError(error):
    pass


class OggOpusInfo(StreamInfo):
    """Ogg Opus stream information.

    Attributes:

    * length - file length in seconds, as a float
    * channels - number of channels
    """

    length = 0

    def __init__(self, fileobj):
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"OpusHead"):
            page = OggPage(fileobj)

        self.serial = page.serial

        if not page.first:
            raise OggOpusHeaderError(
                "page has ID header, but doesn't start a stream")

        (version, self.channels, pre_skip, orig_sample_rate, output_gain,
         channel_map) = struct.unpack("<BBHIhB", page.packets[0][8:19])

        self.__pre_skip = pre_skip

        # only the higher 4 bits change on incombatible changes
        major = version >> 4
        if major != 0:
            raise OggOpusHeaderError("version %r unsupported" % major)

    def _post_tags(self, fileobj):
        page = OggPage.find_last(fileobj, self.serial)
        self.length = (page.position - self.__pre_skip) / float(48000)

    def pprint(self):
        return u"Ogg Opus, %.2f seconds" % (self.length)


class OggOpusVComment(VCommentDict):
    """Opus comments embedded in an Ogg bitstream."""

    def __get_comment_pages(self, fileobj, info):
        # find the first tags page with the right serial
        page = OggPage(fileobj)
        while ((info.serial != page.serial) or
                not page.packets[0].startswith(b"OpusTags")):
            page = OggPage(fileobj)

        # get all comment pages
        pages = [page]
        while not (pages[-1].complete or len(pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == pages[0].serial:
                pages.append(page)

        return pages

    def __init__(self, fileobj, info):
        pages = self.__get_comment_pages(fileobj, info)
        data = OggPage.to_packets(pages)[0][8:]  # Strip OpusTags
        fileobj = BytesIO(data)
        super(OggOpusVComment, self).__init__(fileobj, framing=False)

        # in case the LSB of the first byte after v-comment is 1, preserve the
        # following data
        padding_flag = fileobj.read(1)
        if padding_flag and ord(padding_flag) & 0x1:
            self._pad_data = padding_flag + fileobj.read()
        else:
            self._pad_data = b""

    def _inject(self, fileobj):
        fileobj.seek(0)
        info = OggOpusInfo(fileobj)
        old_pages = self.__get_comment_pages(fileobj, info)

        packets = OggPage.to_packets(old_pages)
        packets[0] = b"OpusTags" + self.write(framing=False) + self._pad_data
        new_pages = OggPage.from_packets(packets, old_pages[0].sequence)
        OggPage.replace(fileobj, old_pages, new_pages)


class OggOpus(OggFileType):
    """An Ogg Opus file."""

    _Info = OggOpusInfo
    _Tags = OggOpusVComment
    _Error = OggOpusHeaderError
    _mimes = ["audio/ogg", "audio/ogg; codecs=opus"]

    @staticmethod
    def score(filename, fileobj, header):
        return (header.startswith(b"OggS") * (b"OpusHead" in header))


Open = OggOpus


def delete(filename):
    """Remove tags from a file."""

    OggOpus(filename).delete()
