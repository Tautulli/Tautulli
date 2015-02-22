# -*- coding: utf-8 -*-

# Copyright (C) 2006  Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write Ogg FLAC comments.

This module handles FLAC files wrapped in an Ogg bitstream. The first
FLAC stream found is used. For 'naked' FLACs, see mutagen.flac.

This module is based off the specification at
http://flac.sourceforge.net/ogg_mapping.html.
"""

__all__ = ["OggFLAC", "Open", "delete"]

import struct

from ._compat import cBytesIO

from mutagen.flac import StreamInfo, VCFLACDict, StrictFileObject
from mutagen.ogg import OggPage, OggFileType, error as OggError


class error(OggError):
    pass


class OggFLACHeaderError(error):
    pass


class OggFLACStreamInfo(StreamInfo):
    """Ogg FLAC general header and stream info.

    This encompasses the Ogg wrapper for the FLAC STREAMINFO metadata
    block, as well as the Ogg codec setup that precedes it.

    Attributes (in addition to StreamInfo's):

    * packets -- number of metadata packets
    * serial -- Ogg logical stream serial number
    """

    packets = 0
    serial = 0

    def load(self, data):
        # Ogg expects file objects that don't raise on read
        if isinstance(data, StrictFileObject):
            data = data._fileobj

        page = OggPage(data)
        while not page.packets[0].startswith(b"\x7FFLAC"):
            page = OggPage(data)
        major, minor, self.packets, flac = struct.unpack(
            ">BBH4s", page.packets[0][5:13])
        if flac != b"fLaC":
            raise OggFLACHeaderError("invalid FLAC marker (%r)" % flac)
        elif (major, minor) != (1, 0):
            raise OggFLACHeaderError(
                "unknown mapping version: %d.%d" % (major, minor))
        self.serial = page.serial

        # Skip over the block header.
        stringobj = StrictFileObject(cBytesIO(page.packets[0][17:]))
        super(OggFLACStreamInfo, self).load(stringobj)

    def _post_tags(self, fileobj):
        if self.length:
            return
        page = OggPage.find_last(fileobj, self.serial)
        self.length = page.position / float(self.sample_rate)

    def pprint(self):
        return u"Ogg " + super(OggFLACStreamInfo, self).pprint()


class OggFLACVComment(VCFLACDict):
    def load(self, data, info, errors='replace'):
        # data should be pointing at the start of an Ogg page, after
        # the first FLAC page.
        pages = []
        complete = False
        while not complete:
            page = OggPage(data)
            if page.serial == info.serial:
                pages.append(page)
                complete = page.complete or (len(page.packets) > 1)
        comment = cBytesIO(OggPage.to_packets(pages)[0][4:])
        super(OggFLACVComment, self).load(comment, errors=errors)

    def _inject(self, fileobj):
        """Write tag data into the FLAC Vorbis comment packet/page."""

        # Ogg FLAC has no convenient data marker like Vorbis, but the
        # second packet - and second page - must be the comment data.
        fileobj.seek(0)
        page = OggPage(fileobj)
        while not page.packets[0].startswith(b"\x7FFLAC"):
            page = OggPage(fileobj)

        first_page = page
        while not (page.sequence == 1 and page.serial == first_page.serial):
            page = OggPage(fileobj)

        old_pages = [page]
        while not (old_pages[-1].complete or len(old_pages[-1].packets) > 1):
            page = OggPage(fileobj)
            if page.serial == first_page.serial:
                old_pages.append(page)

        packets = OggPage.to_packets(old_pages, strict=False)

        # Set the new comment block.
        data = self.write()
        data = packets[0][:1] + struct.pack(">I", len(data))[-3:] + data
        packets[0] = data

        new_pages = OggPage.from_packets(packets, old_pages[0].sequence)
        OggPage.replace(fileobj, old_pages, new_pages)


class OggFLAC(OggFileType):
    """An Ogg FLAC file."""

    _Info = OggFLACStreamInfo
    _Tags = OggFLACVComment
    _Error = OggFLACHeaderError
    _mimes = ["audio/x-oggflac"]

    @staticmethod
    def score(filename, fileobj, header):
        return (header.startswith(b"OggS") * (
            (b"FLAC" in header) + (b"fLaC" in header)))


Open = OggFLAC


def delete(filename):
    """Remove tags from a file."""

    OggFLAC(filename).delete()
