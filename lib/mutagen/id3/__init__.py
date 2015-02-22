# -*- coding: utf-8 -*-

# Copyright (C) 2005  Michael Urman
#               2006  Lukas Lalinsky
#               2013  Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

"""ID3v2 reading and writing.

This is based off of the following references:

* http://id3.org/id3v2.4.0-structure
* http://id3.org/id3v2.4.0-frames
* http://id3.org/id3v2.3.0
* http://id3.org/id3v2-00
* http://id3.org/ID3v1

Its largest deviation from the above (versions 2.3 and 2.2) is that it
will not interpret the / characters as a separator, and will almost
always accept null separators to generate multi-valued text frames.

Because ID3 frame structure differs between frame types, each frame is
implemented as a different class (e.g. TIT2 as mutagen.id3.TIT2). Each
frame's documentation contains a list of its attributes.

Since this file's documentation is a little unwieldy, you are probably
interested in the :class:`ID3` class to start with.
"""

__all__ = ['ID3', 'ID3FileType', 'Frames', 'Open', 'delete']

import struct
import errno

from struct import unpack, pack, error as StructError

import mutagen
from mutagen._util import insert_bytes, delete_bytes, DictProxy, enum
from .._compat import chr_, PY3

from ._util import *
from ._frames import *
from ._specs import *


@enum
class ID3v1SaveOptions(object):

    REMOVE = 0
    """ID3v1 tags will be removed"""

    UPDATE = 1
    """ID3v1 tags will be updated but not added"""

    CREATE = 2
    """ID3v1 tags will be created and/or updated"""


class ID3(DictProxy, mutagen.Metadata):
    """A file with an ID3v2 tag.

    Attributes:

    * version -- ID3 tag version as a tuple
    * unknown_frames -- raw frame data of any unknown frames found
    * size -- the total size of the ID3 tag, including the header
    """

    __module__ = "mutagen.id3"

    PEDANTIC = True
    version = (2, 4, 0)
    """ID3 tag version as a tuple (of the loaded file)"""

    filename = None
    size = 0
    __flags = 0
    __readbytes = 0
    __crc = None
    __unknown_version = None

    _V24 = (2, 4, 0)
    _V23 = (2, 3, 0)
    _V22 = (2, 2, 0)
    _V11 = (1, 1)

    def __init__(self, *args, **kwargs):
        self.unknown_frames = []
        super(ID3, self).__init__(*args, **kwargs)

    def __fullread(self, size):
        """ Read a certain number of bytes from the source file. """

        try:
            if size < 0:
                raise ValueError('Requested bytes (%s) less than zero' % size)
            if size > self.__filesize:
                raise EOFError('Requested %#x of %#x (%s)' % (
                    int(size), int(self.__filesize), self.filename))
        except AttributeError:
            pass
        data = self._fileobj.read(size)
        if len(data) != size:
            raise EOFError
        self.__readbytes += size
        return data

    def load(self, filename, known_frames=None, translate=True, v2_version=4):
        """Load tags from a filename.

        Keyword arguments:

        * filename -- filename to load tag data from
        * known_frames -- dict mapping frame IDs to Frame objects
        * translate -- Update all tags to ID3v2.3/4 internally. If you
                       intend to save, this must be true or you have to
                       call update_to_v23() / update_to_v24() manually.
        * v2_version -- if update_to_v23 or update_to_v24 get called (3 or 4)

        Example of loading a custom frame::

            my_frames = dict(mutagen.id3.Frames)
            class XMYF(Frame): ...
            my_frames["XMYF"] = XMYF
            mutagen.id3.ID3(filename, known_frames=my_frames)
        """

        if v2_version not in (3, 4):
            raise ValueError("Only 3 and 4 possible for v2_version")

        from os.path import getsize

        self.filename = filename
        self.__known_frames = known_frames
        self._fileobj = open(filename, 'rb')
        self.__filesize = getsize(filename)
        try:
            try:
                self._load_header()
            except EOFError:
                self.size = 0
                raise ID3NoHeaderError("%s: too small (%d bytes)" % (
                    filename, self.__filesize))
            except (ID3NoHeaderError, ID3UnsupportedVersionError):
                self.size = 0
                frames, offset = _find_id3v1(self._fileobj)
                if frames is None:
                    raise

                self.version = self._V11
                for v in frames.values():
                    self.add(v)
            else:
                frames = self.__known_frames
                if frames is None:
                    if self._V23 <= self.version:
                        frames = Frames
                    elif self._V22 <= self.version:
                        frames = Frames_2_2
                data = self.__fullread(self.size - 10)
                for frame in self.__read_frames(data, frames=frames):
                    if isinstance(frame, Frame):
                        self.add(frame)
                    else:
                        self.unknown_frames.append(frame)
                self.__unknown_version = self.version[:2]
        finally:
            self._fileobj.close()
            del self._fileobj
            del self.__filesize
            if translate:
                if v2_version == 3:
                    self.update_to_v23()
                else:
                    self.update_to_v24()

    def getall(self, key):
        """Return all frames with a given name (the list may be empty).

        This is best explained by examples::

            id3.getall('TIT2') == [id3['TIT2']]
            id3.getall('TTTT') == []
            id3.getall('TXXX') == [TXXX(desc='woo', text='bar'),
                                   TXXX(desc='baz', text='quuuux'), ...]

        Since this is based on the frame's HashKey, which is
        colon-separated, you can use it to do things like
        ``getall('COMM:MusicMatch')`` or ``getall('TXXX:QuodLibet:')``.
        """
        if key in self:
            return [self[key]]
        else:
            key = key + ":"
            return [v for s, v in self.items() if s.startswith(key)]

    def delall(self, key):
        """Delete all tags of a given kind; see getall."""
        if key in self:
            del(self[key])
        else:
            key = key + ":"
            for k in list(self.keys()):
                if k.startswith(key):
                    del(self[k])

    def setall(self, key, values):
        """Delete frames of the given type and add frames in 'values'."""
        self.delall(key)
        for tag in values:
            self[tag.HashKey] = tag

    def pprint(self):
        """Return tags in a human-readable format.

        "Human-readable" is used loosely here. The format is intended
        to mirror that used for Vorbis or APEv2 output, e.g.

            ``TIT2=My Title``

        However, ID3 frames can have multiple keys:

            ``POPM=user@example.org=3 128/255``
        """
        frames = sorted(Frame.pprint(s) for s in self.values())
        return "\n".join(frames)

    def loaded_frame(self, tag):
        """Deprecated; use the add method."""
        # turn 2.2 into 2.3/2.4 tags
        if len(type(tag).__name__) == 3:
            tag = type(tag).__base__(tag)
        self[tag.HashKey] = tag

    # add = loaded_frame (and vice versa) break applications that
    # expect to be able to override loaded_frame (e.g. Quod Libet),
    # as does making loaded_frame call add.
    def add(self, frame):
        """Add a frame to the tag."""
        return self.loaded_frame(frame)

    def _load_header(self):
        fn = self.filename
        data = self.__fullread(10)
        id3, vmaj, vrev, flags, size = unpack('>3sBBB4s', data)
        self.__flags = flags
        self.size = BitPaddedInt(size) + 10
        self.version = (2, vmaj, vrev)

        if id3 != b'ID3':
            raise ID3NoHeaderError("%r doesn't start with an ID3 tag" % fn)
        if vmaj not in [2, 3, 4]:
            raise ID3UnsupportedVersionError("%r ID3v2.%d not supported"
                                             % (fn, vmaj))

        if self.PEDANTIC:
            if not BitPaddedInt.has_valid_padding(size):
                raise ValueError("Header size not synchsafe")

            if (self._V24 <= self.version) and (flags & 0x0f):
                raise ValueError("%r has invalid flags %#02x" % (fn, flags))
            elif (self._V23 <= self.version < self._V24) and (flags & 0x1f):
                raise ValueError("%r has invalid flags %#02x" % (fn, flags))

        if self.f_extended:
            extsize = self.__fullread(4)
            frame_id = extsize.decode("ascii", "replace") if PY3 else extsize
            if frame_id in Frames:
                # Some tagger sets the extended header flag but
                # doesn't write an extended header; in this case, the
                # ID3 data follows immediately. Since no extended
                # header is going to be long enough to actually match
                # a frame, and if it's *not* a frame we're going to be
                # completely lost anyway, this seems to be the most
                # correct check.
                # http://code.google.com/p/quodlibet/issues/detail?id=126
                self.__flags ^= 0x40
                self.__extsize = 0
                self._fileobj.seek(-4, 1)
                self.__readbytes -= 4
            elif self.version >= self._V24:
                # "Where the 'Extended header size' is the size of the whole
                # extended header, stored as a 32 bit synchsafe integer."
                self.__extsize = BitPaddedInt(extsize) - 4
                if self.PEDANTIC:
                    if not BitPaddedInt.has_valid_padding(extsize):
                        raise ValueError("Extended header size not synchsafe")
            else:
                # "Where the 'Extended header size', currently 6 or 10 bytes,
                # excludes itself."
                self.__extsize = unpack('>L', extsize)[0]
            if self.__extsize:
                self.__extdata = self.__fullread(self.__extsize)
            else:
                self.__extdata = b""

    def __determine_bpi(self, data, frames):
        if self.version < self._V24:
            return int

        return _determine_bpi(data, frames)

    def __read_frames(self, data, frames):
        if self.version < self._V24 and self.f_unsynch:
            try:
                data = unsynch.decode(data)
            except ValueError:
                pass

        if self._V23 <= self.version:
            bpi = self.__determine_bpi(data, frames)
            while data:
                header = data[:10]
                try:
                    name, size, flags = unpack('>4sLH', header)
                except struct.error:
                    return  # not enough header
                if name.strip(b'\x00') == b'':
                    return

                size = bpi(size)
                framedata = data[10:10 + size]
                data = data[10 + size:]
                if size == 0:
                    continue  # drop empty frames

                if PY3:
                    try:
                        name = name.decode('ascii')
                    except UnicodeDecodeError:
                        continue

                try:
                    # someone writes 2.3 frames with 2.2 names
                    if name[-1] == "\x00":
                        tag = Frames_2_2[name[:-1]]
                        name = tag.__base__.__name__

                    tag = frames[name]
                except KeyError:
                    if is_valid_frame_id(name):
                        yield header + framedata
                else:
                    try:
                        yield self.__load_framedata(tag, flags, framedata)
                    except NotImplementedError:
                        yield header + framedata
                    except ID3JunkFrameError:
                        pass

        elif self._V22 <= self.version:
            while data:
                header = data[0:6]
                try:
                    name, size = unpack('>3s3s', header)
                except struct.error:
                    return  # not enough header
                size, = struct.unpack('>L', b'\x00' + size)
                if name.strip(b'\x00') == b'':
                    return

                framedata = data[6:6 + size]
                data = data[6 + size:]
                if size == 0:
                    continue  # drop empty frames

                if PY3:
                    try:
                        name = name.decode('ascii')
                    except UnicodeDecodeError:
                        continue

                try:
                    tag = frames[name]
                except KeyError:
                    if is_valid_frame_id(name):
                        yield header + framedata
                else:
                    try:
                        yield self.__load_framedata(tag, 0, framedata)
                    except NotImplementedError:
                        yield header + framedata
                    except ID3JunkFrameError:
                        pass

    def __load_framedata(self, tag, flags, framedata):
        return tag.fromData(self, flags, framedata)

    f_unsynch = property(lambda s: bool(s.__flags & 0x80))
    f_extended = property(lambda s: bool(s.__flags & 0x40))
    f_experimental = property(lambda s: bool(s.__flags & 0x20))
    f_footer = property(lambda s: bool(s.__flags & 0x10))

    # f_crc = property(lambda s: bool(s.__extflags & 0x8000))

    def _prepare_framedata(self, v2_version, v23_sep):
        if v2_version == 3:
            version = self._V23
        elif v2_version == 4:
            version = self._V24
        else:
            raise ValueError("Only 3 or 4 allowed for v2_version")

        # Sort frames by 'importance'
        order = ["TIT2", "TPE1", "TRCK", "TALB", "TPOS", "TDRC", "TCON"]
        order = dict((b, a) for a, b in enumerate(order))
        last = len(order)
        frames = sorted(self.items(),
                        key=lambda a: (order.get(a[0][:4], last), a[0]))

        framedata = [self.__save_frame(frame, version=version, v23_sep=v23_sep)
                     for (key, frame) in frames]

        # only write unknown frames if they were loaded from the version
        # we are saving with or upgraded to it
        if self.__unknown_version == version[:2]:
            framedata.extend(data for data in self.unknown_frames
                             if len(data) > 10)

        return b''.join(framedata)

    def _prepare_id3_header(self, original_header, framesize, v2_version):
        try:
            id3, vmaj, vrev, flags, insize = \
                unpack('>3sBBB4s', original_header)
        except struct.error:
            id3, insize = b'', 0
        insize = BitPaddedInt(insize)
        if id3 != b'ID3':
            insize = -10

        if insize >= framesize:
            outsize = insize
        else:
            outsize = (framesize + 1023) & ~0x3FF

        framesize = BitPaddedInt.to_str(outsize, width=4)
        header = pack('>3sBBB4s', b'ID3', v2_version, 0, 0, framesize)

        return (header, outsize, insize)

    def save(self, filename=None, v1=1, v2_version=4, v23_sep='/'):
        """Save changes to a file.

        Args:
            filename:
                Filename to save the tag to. If no filename is given,
                the one most recently loaded is used.
            v1 (ID3v1SaveOptions):
                if 0, ID3v1 tags will be removed.
                if 1, ID3v1 tags will be updated but not added.
                if 2, ID3v1 tags will be created and/or updated
            v2 (int):
                version of ID3v2 tags (3 or 4).
            v23_sep (str):
                the separator used to join multiple text values
                if v2_version == 3. Defaults to '/' but if it's None
                will be the ID3v2v2.4 null separator.

        By default Mutagen saves ID3v2.4 tags. If you want to save ID3v2.3
        tags, you must call method update_to_v23 before saving the file.

        The lack of a way to update only an ID3v1 tag is intentional.
        """

        framedata = self._prepare_framedata(v2_version, v23_sep)
        framesize = len(framedata)

        if not framedata:
            try:
                self.delete(filename)
            except EnvironmentError as err:
                from errno import ENOENT
                if err.errno != ENOENT:
                    raise
            return

        if filename is None:
            filename = self.filename
        try:
            f = open(filename, 'rb+')
        except IOError as err:
            from errno import ENOENT
            if err.errno != ENOENT:
                raise
            f = open(filename, 'ab')  # create, then reopen
            f = open(filename, 'rb+')
        try:
            idata = f.read(10)

            header = self._prepare_id3_header(idata, framesize, v2_version)
            header, outsize, insize = header

            data = header + framedata + (b'\x00' * (outsize - framesize))

            if (insize < outsize):
                insert_bytes(f, outsize - insize, insize + 10)
            f.seek(0)
            f.write(data)

            self.__save_v1(f, v1)

        finally:
            f.close()

    def __save_v1(self, f, v1):
        tag, offset = _find_id3v1(f)
        has_v1 = tag is not None

        f.seek(offset, 2)
        if v1 == ID3v1SaveOptions.UPDATE and has_v1 or \
                v1 == ID3v1SaveOptions.CREATE:
            f.write(MakeID3v1(self))
        else:
            f.truncate()

    def delete(self, filename=None, delete_v1=True, delete_v2=True):
        """Remove tags from a file.

        If no filename is given, the one most recently loaded is used.

        Keyword arguments:

        * delete_v1 -- delete any ID3v1 tag
        * delete_v2 -- delete any ID3v2 tag
        """
        if filename is None:
            filename = self.filename
        delete(filename, delete_v1, delete_v2)
        self.clear()

    def __save_frame(self, frame, name=None, version=_V24, v23_sep=None):
        flags = 0
        if self.PEDANTIC and isinstance(frame, TextFrame):
            if len(str(frame)) == 0:
                return b''

        if version == self._V23:
            framev23 = frame._get_v23_frame(sep=v23_sep)
            framedata = framev23._writeData()
        else:
            framedata = frame._writeData()

        usize = len(framedata)
        if usize > 2048:
            # Disabled as this causes iTunes and other programs
            # to fail to find these frames, which usually includes
            # e.g. APIC.
            # framedata = BitPaddedInt.to_str(usize) + framedata.encode('zlib')
            # flags |= Frame.FLAG24_COMPRESS | Frame.FLAG24_DATALEN
            pass

        if version == self._V24:
            bits = 7
        elif version == self._V23:
            bits = 8
        else:
            raise ValueError

        datasize = BitPaddedInt.to_str(len(framedata), width=4, bits=bits)

        if name is not None:
            assert isinstance(name, bytes)
            frame_name = name
        else:
            frame_name = type(frame).__name__
            if PY3:
                frame_name = frame_name.encode("ascii")

        header = pack('>4s4sH', frame_name, datasize, flags)
        return header + framedata

    def __update_common(self):
        """Updates done by both v23 and v24 update"""

        if "TCON" in self:
            # Get rid of "(xx)Foobr" format.
            self["TCON"].genres = self["TCON"].genres

        # ID3v2.2 LNK frames are just way too different to upgrade.
        for frame in self.getall("LINK"):
            if len(frame.frameid) != 4:
                del self[frame.HashKey]

        mimes = {"PNG": "image/png", "JPG": "image/jpeg"}
        for pic in self.getall("APIC"):
            if pic.mime in mimes:
                newpic = APIC(
                    encoding=pic.encoding, mime=mimes[pic.mime],
                    type=pic.type, desc=pic.desc, data=pic.data)
                self.add(newpic)

    def update_to_v24(self):
        """Convert older tags into an ID3v2.4 tag.

        This updates old ID3v2 frames to ID3v2.4 ones (e.g. TYER to
        TDRC). If you intend to save tags, you must call this function
        at some point; it is called by default when loading the tag.
        """

        self.__update_common()

        if self.__unknown_version == (2, 3):
            # convert unknown 2.3 frames (flags/size) to 2.4
            converted = []
            for frame in self.unknown_frames:
                try:
                    name, size, flags = unpack('>4sLH', frame[:10])
                    frame = BinaryFrame.fromData(self, flags, frame[10:])
                except (struct.error, error):
                    continue

                converted.append(self.__save_frame(frame, name=name))
            self.unknown_frames[:] = converted
            self.__unknown_version = (2, 4)

        # TDAT, TYER, and TIME have been turned into TDRC.
        try:
            date = text_type(self.get("TYER", ""))
            if date.strip(u"\x00"):
                self.pop("TYER")
                dat = text_type(self.get("TDAT", ""))
                if dat.strip("\x00"):
                    self.pop("TDAT")
                    date = "%s-%s-%s" % (date, dat[2:], dat[:2])
                    time = text_type(self.get("TIME", ""))
                    if time.strip("\x00"):
                        self.pop("TIME")
                        date += "T%s:%s:00" % (time[:2], time[2:])
                if "TDRC" not in self:
                    self.add(TDRC(encoding=0, text=date))
        except UnicodeDecodeError:
            # Old ID3 tags have *lots* of Unicode problems, so if TYER
            # is bad, just chuck the frames.
            pass

        # TORY can be the first part of a TDOR.
        if "TORY" in self:
            f = self.pop("TORY")
            if "TDOR" not in self:
                try:
                    self.add(TDOR(encoding=0, text=str(f)))
                except UnicodeDecodeError:
                    pass

        # IPLS is now TIPL.
        if "IPLS" in self:
            f = self.pop("IPLS")
            if "TIPL" not in self:
                self.add(TIPL(encoding=f.encoding, people=f.people))

        # These can't be trivially translated to any ID3v2.4 tags, or
        # should have been removed already.
        for key in ["RVAD", "EQUA", "TRDA", "TSIZ", "TDAT", "TIME", "CRM"]:
            if key in self:
                del(self[key])

    def update_to_v23(self):
        """Convert older (and newer) tags into an ID3v2.3 tag.

        This updates incompatible ID3v2 frames to ID3v2.3 ones. If you
        intend to save tags as ID3v2.3, you must call this function
        at some point.

        If you want to to go off spec and include some v2.4 frames
        in v2.3, remove them before calling this and add them back afterwards.
        """

        self.__update_common()

        # we could downgrade unknown v2.4 frames here, but given that
        # the main reason to save v2.3 is compatibility and this
        # might increase the chance of some parser breaking.. better not

        # TMCL, TIPL -> TIPL
        if "TIPL" in self or "TMCL" in self:
            people = []
            if "TIPL" in self:
                f = self.pop("TIPL")
                people.extend(f.people)
            if "TMCL" in self:
                f = self.pop("TMCL")
                people.extend(f.people)
            if "IPLS" not in self:
                self.add(IPLS(encoding=f.encoding, people=people))

        # TDOR -> TORY
        if "TDOR" in self:
            f = self.pop("TDOR")
            if f.text:
                d = f.text[0]
                if d.year and "TORY" not in self:
                    self.add(TORY(encoding=f.encoding, text="%04d" % d.year))

        # TDRC -> TYER, TDAT, TIME
        if "TDRC" in self:
            f = self.pop("TDRC")
            if f.text:
                d = f.text[0]
                if d.year and "TYER" not in self:
                    self.add(TYER(encoding=f.encoding, text="%04d" % d.year))
                if d.month and d.day and "TDAT" not in self:
                    self.add(TDAT(encoding=f.encoding,
                                  text="%02d%02d" % (d.day, d.month)))
                if d.hour and d.minute and "TIME" not in self:
                    self.add(TIME(encoding=f.encoding,
                                  text="%02d%02d" % (d.hour, d.minute)))

        # New frames added in v2.4
        v24_frames = [
            'ASPI', 'EQU2', 'RVA2', 'SEEK', 'SIGN', 'TDEN', 'TDOR',
            'TDRC', 'TDRL', 'TDTG', 'TIPL', 'TMCL', 'TMOO', 'TPRO',
            'TSOA', 'TSOP', 'TSOT', 'TSST',
        ]

        for key in v24_frames:
            if key in self:
                del(self[key])


def delete(filename, delete_v1=True, delete_v2=True):
    """Remove tags from a file.

    Keyword arguments:

    * delete_v1 -- delete any ID3v1 tag
    * delete_v2 -- delete any ID3v2 tag
    """

    f = open(filename, 'rb+')

    if delete_v1:
        tag, offset = _find_id3v1(f)
        if tag is not None:
            f.seek(offset, 2)
            f.truncate()

    # technically an insize=0 tag is invalid, but we delete it anyway
    # (primarily because we used to write it)
    if delete_v2:
        f.seek(0, 0)
        idata = f.read(10)
        try:
            id3, vmaj, vrev, flags, insize = unpack('>3sBBB4s', idata)
        except struct.error:
            id3, insize = b'', -1
        insize = BitPaddedInt(insize)
        if id3 == b'ID3' and insize >= 0:
            delete_bytes(f, insize + 10, 0)


# support open(filename) as interface
Open = ID3


def _determine_bpi(data, frames, EMPTY=b"\x00" * 10):
    """Takes id3v2.4 frame data and determines if ints or bitpaddedints
    should be used for parsing. Needed because iTunes used to write
    normal ints for frame sizes.
    """

    # count number of tags found as BitPaddedInt and how far past
    o = 0
    asbpi = 0
    while o < len(data) - 10:
        part = data[o:o + 10]
        if part == EMPTY:
            bpioff = -((len(data) - o) % 10)
            break
        name, size, flags = unpack('>4sLH', part)
        size = BitPaddedInt(size)
        o += 10 + size
        if PY3:
            try:
                name = name.decode("ascii")
            except UnicodeDecodeError:
                continue
        if name in frames:
            asbpi += 1
    else:
        bpioff = o - len(data)

    # count number of tags found as int and how far past
    o = 0
    asint = 0
    while o < len(data) - 10:
        part = data[o:o + 10]
        if part == EMPTY:
            intoff = -((len(data) - o) % 10)
            break
        name, size, flags = unpack('>4sLH', part)
        o += 10 + size
        if PY3:
            try:
                name = name.decode("ascii")
            except UnicodeDecodeError:
                continue
        if name in frames:
            asint += 1
    else:
        intoff = o - len(data)

    # if more tags as int, or equal and bpi is past and int is not
    if asint > asbpi or (asint == asbpi and (bpioff >= 1 and intoff <= 1)):
        return int
    return BitPaddedInt


def _find_id3v1(fileobj):
    """Returns a tuple of (id3tag, offset_to_end) or (None, 0)

    offset mainly because we used to write too short tags in some cases and
    we need the offset to delete them.
    """

    # id3v1 is always at the end (after apev2)

    extra_read = b"APETAGEX".index(b"TAG")

    try:
        fileobj.seek(-128 - extra_read, 2)
    except IOError as e:
        if e.errno == errno.EINVAL:
            # If the file is too small, might be ok since we wrote too small
            # tags at some point. let's see how the parsing goes..
            fileobj.seek(0, 0)
        else:
            raise

    data = fileobj.read(128 + extra_read)
    try:
        idx = data.index(b"TAG")
    except ValueError:
        return (None, 0)
    else:
        # FIXME: make use of the apev2 parser here
        # if TAG is part of APETAGEX assume this is an APEv2 tag
        try:
            ape_idx = data.index(b"APETAGEX")
        except ValueError:
            pass
        else:
            if idx == ape_idx + extra_read:
                return (None, 0)

        tag = ParseID3v1(data[idx:])
        if tag is None:
            return (None, 0)

        offset = idx - len(data)
        return (tag, offset)


# ID3v1.1 support.
def ParseID3v1(data):
    """Parse an ID3v1 tag, returning a list of ID3v2.4 frames.

    Returns a {frame_name: frame} dict or None.
    """

    try:
        data = data[data.index(b"TAG"):]
    except ValueError:
        return None
    if 128 < len(data) or len(data) < 124:
        return None

    # Issue #69 - Previous versions of Mutagen, when encountering
    # out-of-spec TDRC and TYER frames of less than four characters,
    # wrote only the characters available - e.g. "1" or "" - into the
    # year field. To parse those, reduce the size of the year field.
    # Amazingly, "0s" works as a struct format string.
    unpack_fmt = "3s30s30s30s%ds29sBB" % (len(data) - 124)

    try:
        tag, title, artist, album, year, comment, track, genre = unpack(
            unpack_fmt, data)
    except StructError:
        return None

    if tag != b"TAG":
        return None

    def fix(data):
        return data.split(b"\x00")[0].strip().decode('latin1')

    title, artist, album, year, comment = map(
        fix, [title, artist, album, year, comment])

    frames = {}
    if title:
        frames["TIT2"] = TIT2(encoding=0, text=title)
    if artist:
        frames["TPE1"] = TPE1(encoding=0, text=[artist])
    if album:
        frames["TALB"] = TALB(encoding=0, text=album)
    if year:
        frames["TDRC"] = TDRC(encoding=0, text=year)
    if comment:
        frames["COMM"] = COMM(
            encoding=0, lang="eng", desc="ID3v1 Comment", text=comment)
    # Don't read a track number if it looks like the comment was
    # padded with spaces instead of nulls (thanks, WinAmp).
    if track and ((track != 32) or (data[-3] == b'\x00'[0])):
        frames["TRCK"] = TRCK(encoding=0, text=str(track))
    if genre != 255:
        frames["TCON"] = TCON(encoding=0, text=str(genre))
    return frames


def MakeID3v1(id3):
    """Return an ID3v1.1 tag string from a dict of ID3v2.4 frames."""

    v1 = {}

    for v2id, name in {"TIT2": "title", "TPE1": "artist",
                       "TALB": "album"}.items():
        if v2id in id3:
            text = id3[v2id].text[0].encode('latin1', 'replace')[:30]
        else:
            text = b""
        v1[name] = text + (b"\x00" * (30 - len(text)))

    if "COMM" in id3:
        cmnt = id3["COMM"].text[0].encode('latin1', 'replace')[:28]
    else:
        cmnt = b""
    v1["comment"] = cmnt + (b"\x00" * (29 - len(cmnt)))

    if "TRCK" in id3:
        try:
            v1["track"] = chr_(+id3["TRCK"])
        except ValueError:
            v1["track"] = b"\x00"
    else:
        v1["track"] = b"\x00"

    if "TCON" in id3:
        try:
            genre = id3["TCON"].genres[0]
        except IndexError:
            pass
        else:
            if genre in TCON.GENRES:
                v1["genre"] = chr_(TCON.GENRES.index(genre))
    if "genre" not in v1:
        v1["genre"] = b"\xff"

    if "TDRC" in id3:
        year = text_type(id3["TDRC"]).encode('ascii')
    elif "TYER" in id3:
        year = text_type(id3["TYER"]).encode('ascii')
    else:
        year = b""
    v1["year"] = (year + b"\x00\x00\x00\x00")[:4]

    return (
        b"TAG" +
        v1["title"] +
        v1["artist"] +
        v1["album"] +
        v1["year"] +
        v1["comment"] +
        v1["track"] +
        v1["genre"]
    )


class ID3FileType(mutagen.FileType):
    """An unknown type of file with ID3 tags."""

    ID3 = ID3

    class _Info(mutagen.StreamInfo):
        length = 0

        def __init__(self, fileobj, offset):
            pass

        @staticmethod
        def pprint():
            return "Unknown format with ID3 tag"

    @staticmethod
    def score(filename, fileobj, header_data):
        return header_data.startswith(b"ID3")

    def add_tags(self, ID3=None):
        """Add an empty ID3 tag to the file.

        A custom tag reader may be used in instead of the default
        mutagen.id3.ID3 object, e.g. an EasyID3 reader.
        """
        if ID3 is None:
            ID3 = self.ID3
        if self.tags is None:
            self.ID3 = ID3
            self.tags = ID3()
        else:
            raise error("an ID3 tag already exists")

    def load(self, filename, ID3=None, **kwargs):
        """Load stream and tag information from a file.

        A custom tag reader may be used in instead of the default
        mutagen.id3.ID3 object, e.g. an EasyID3 reader.
        """

        if ID3 is None:
            ID3 = self.ID3
        else:
            # If this was initialized with EasyID3, remember that for
            # when tags are auto-instantiated in add_tags.
            self.ID3 = ID3
        self.filename = filename
        try:
            self.tags = ID3(filename, **kwargs)
        except error:
            self.tags = None
        if self.tags is not None:
            try:
                offset = self.tags.size
            except AttributeError:
                offset = None
        else:
            offset = None
        try:
            fileobj = open(filename, "rb")
            self.info = self._Info(fileobj, offset)
        finally:
            fileobj.close()
