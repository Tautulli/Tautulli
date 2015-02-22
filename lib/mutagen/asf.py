# -*- coding: utf-8 -*-

# Copyright (C) 2005-2006  Joe Wreschnig
# Copyright (C) 2006-2007  Lukas Lalinsky

#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Read and write ASF (Window Media Audio) files."""

__all__ = ["ASF", "Open"]

import sys
import struct
from mutagen import FileType, Metadata, StreamInfo
from mutagen._util import (insert_bytes, delete_bytes, DictMixin,
                           total_ordering, MutagenError)
from ._compat import swap_to_string, text_type, PY2, string_types, reraise, \
    xrange, long_, PY3


class error(IOError, MutagenError):
    pass


class ASFError(error):
    pass


class ASFHeaderError(error):
    pass


class ASFInfo(StreamInfo):
    """ASF stream information."""

    def __init__(self):
        self.length = 0.0
        self.sample_rate = 0
        self.bitrate = 0
        self.channels = 0

    def pprint(self):
        s = "Windows Media Audio %d bps, %s Hz, %d channels, %.2f seconds" % (
            self.bitrate, self.sample_rate, self.channels, self.length)
        return s


class ASFTags(list, DictMixin, Metadata):
    """Dictionary containing ASF attributes."""

    def pprint(self):
        return "\n".join("%s=%s" % (k, v) for k, v in self)

    def __getitem__(self, key):
        """A list of values for the key.

        This is a copy, so comment['title'].append('a title') will not
        work.

        """

        # PY3 only
        if isinstance(key, slice):
            return list.__getitem__(self, key)

        values = [value for (k, value) in self if k == key]
        if not values:
            raise KeyError(key)
        else:
            return values

    def __delitem__(self, key):
        """Delete all values associated with the key."""

        # PY3 only
        if isinstance(key, slice):
            return list.__delitem__(self, key)

        to_delete = [x for x in self if x[0] == key]
        if not to_delete:
            raise KeyError(key)
        else:
            for k in to_delete:
                self.remove(k)

    def __contains__(self, key):
        """Return true if the key has any values."""
        for k, value in self:
            if k == key:
                return True
        else:
            return False

    def __setitem__(self, key, values):
        """Set a key's value or values.

        Setting a value overwrites all old ones. The value may be a
        list of Unicode or UTF-8 strings, or a single Unicode or UTF-8
        string.

        """

        # PY3 only
        if isinstance(key, slice):
            return list.__setitem__(self, key, values)

        if not isinstance(values, list):
            values = [values]

        to_append = []
        for value in values:
            if not isinstance(value, ASFBaseAttribute):
                if isinstance(value, string_types):
                    value = ASFUnicodeAttribute(value)
                elif PY3 and isinstance(value, bytes):
                    value = ASFByteArrayAttribute(value)
                elif isinstance(value, bool):
                    value = ASFBoolAttribute(value)
                elif isinstance(value, int):
                    value = ASFDWordAttribute(value)
                elif isinstance(value, long_):
                    value = ASFQWordAttribute(value)
                else:
                    raise TypeError("Invalid type %r" % type(value))
            to_append.append((key, value))

        try:
            del(self[key])
        except KeyError:
            pass

        self.extend(to_append)

    def keys(self):
        """Return all keys in the comment."""
        return self and set(next(iter(zip(*self))))

    def as_dict(self):
        """Return a copy of the comment data in a real dict."""
        d = {}
        for key, value in self:
            d.setdefault(key, []).append(value)
        return d


class ASFBaseAttribute(object):
    """Generic attribute."""
    TYPE = None

    def __init__(self, value=None, data=None, language=None,
                 stream=None, **kwargs):
        self.language = language
        self.stream = stream
        if data:
            self.value = self.parse(data, **kwargs)
        else:
            if value is None:
                # we used to support not passing any args and instead assign
                # them later, keep that working..
                self.value = None
            else:
                self.value = self._validate(value)

    def _validate(self, value):
        """Raises TypeError or ValueError in case the user supplied value
        isn't valid.
        """

        return value

    def data_size(self):
        raise NotImplementedError

    def __repr__(self):
        name = "%s(%r" % (type(self).__name__, self.value)
        if self.language:
            name += ", language=%d" % self.language
        if self.stream:
            name += ", stream=%d" % self.stream
        name += ")"
        return name

    def render(self, name):
        name = name.encode("utf-16-le") + b"\x00\x00"
        data = self._render()
        return (struct.pack("<H", len(name)) + name +
                struct.pack("<HH", self.TYPE, len(data)) + data)

    def render_m(self, name):
        name = name.encode("utf-16-le") + b"\x00\x00"
        if self.TYPE == 2:
            data = self._render(dword=False)
        else:
            data = self._render()
        return (struct.pack("<HHHHI", 0, self.stream or 0, len(name),
                            self.TYPE, len(data)) + name + data)

    def render_ml(self, name):
        name = name.encode("utf-16-le") + b"\x00\x00"
        if self.TYPE == 2:
            data = self._render(dword=False)
        else:
            data = self._render()

        return (struct.pack("<HHHHI", self.language or 0, self.stream or 0,
                            len(name), self.TYPE, len(data)) + name + data)


@swap_to_string
@total_ordering
class ASFUnicodeAttribute(ASFBaseAttribute):
    """Unicode string attribute."""
    TYPE = 0x0000

    def parse(self, data):
        try:
            return data.decode("utf-16-le").strip("\x00")
        except UnicodeDecodeError as e:
            reraise(ASFError, e, sys.exc_info()[2])

    def _validate(self, value):
        if not isinstance(value, text_type):
            if PY2:
                return value.decode("utf-8")
            else:
                raise TypeError("%r not str" % value)
        return value

    def _render(self):
        return self.value.encode("utf-16-le") + b"\x00\x00"

    def data_size(self):
        return len(self._render())

    def __bytes__(self):
        return self.value.encode("utf-16-le")

    def __str__(self):
        return self.value

    def __eq__(self, other):
        return text_type(self) == other

    def __lt__(self, other):
        return text_type(self) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFByteArrayAttribute(ASFBaseAttribute):
    """Byte array attribute."""
    TYPE = 0x0001

    def parse(self, data):
        assert isinstance(data, bytes)
        return data

    def _render(self):
        assert isinstance(self.value, bytes)
        return self.value

    def _validate(self, value):
        if not isinstance(value, bytes):
            raise TypeError("must be bytes/str: %r" % value)
        return value

    def data_size(self):
        return len(self.value)

    def __bytes__(self):
        return self.value

    def __str__(self):
        return "[binary data (%d bytes)]" % len(self.value)

    def __eq__(self, other):
        return self.value == other

    def __lt__(self, other):
        return self.value < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFBoolAttribute(ASFBaseAttribute):
    """Bool attribute."""
    TYPE = 0x0002

    def parse(self, data, dword=True):
        if dword:
            return struct.unpack("<I", data)[0] == 1
        else:
            return struct.unpack("<H", data)[0] == 1

    def _render(self, dword=True):
        if dword:
            return struct.pack("<I", bool(self.value))
        else:
            return struct.pack("<H", bool(self.value))

    def _validate(self, value):
        return bool(value)

    def data_size(self):
        return 4

    def __bool__(self):
        return bool(self.value)

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return bool(self.value) == other

    def __lt__(self, other):
        return bool(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFDWordAttribute(ASFBaseAttribute):
    """DWORD attribute."""
    TYPE = 0x0003

    def parse(self, data):
        return struct.unpack("<L", data)[0]

    def _render(self):
        return struct.pack("<L", self.value)

    def _validate(self, value):
        value = int(value)
        if not 0 <= value <= 2 ** 32 - 1:
            raise ValueError("Out of range")
        return value

    def data_size(self):
        return 4

    def __int__(self):
        return self.value

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return int(self.value) == other

    def __lt__(self, other):
        return int(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFQWordAttribute(ASFBaseAttribute):
    """QWORD attribute."""
    TYPE = 0x0004

    def parse(self, data):
        return struct.unpack("<Q", data)[0]

    def _render(self):
        return struct.pack("<Q", self.value)

    def _validate(self, value):
        value = int(value)
        if not 0 <= value <= 2 ** 64 - 1:
            raise ValueError("Out of range")
        return value

    def data_size(self):
        return 8

    def __int__(self):
        return self.value

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return int(self.value) == other

    def __lt__(self, other):
        return int(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFWordAttribute(ASFBaseAttribute):
    """WORD attribute."""
    TYPE = 0x0005

    def parse(self, data):
        return struct.unpack("<H", data)[0]

    def _render(self):
        return struct.pack("<H", self.value)

    def _validate(self, value):
        value = int(value)
        if not 0 <= value <= 2 ** 16 - 1:
            raise ValueError("Out of range")
        return value

    def data_size(self):
        return 2

    def __int__(self):
        return self.value

    def __bytes__(self):
        return text_type(self.value).encode('utf-8')

    def __str__(self):
        return text_type(self.value)

    def __eq__(self, other):
        return int(self.value) == other

    def __lt__(self, other):
        return int(self.value) < other

    __hash__ = ASFBaseAttribute.__hash__


@swap_to_string
@total_ordering
class ASFGUIDAttribute(ASFBaseAttribute):
    """GUID attribute."""
    TYPE = 0x0006

    def parse(self, data):
        assert isinstance(data, bytes)
        return data

    def _render(self):
        assert isinstance(self.value, bytes)
        return self.value

    def _validate(self, value):
        if not isinstance(value, bytes):
            raise TypeError("must be bytes/str: %r" % value)
        return value

    def data_size(self):
        return len(self.value)

    def __bytes__(self):
        return self.value

    def __str__(self):
        return repr(self.value)

    def __eq__(self, other):
        return self.value == other

    def __lt__(self, other):
        return self.value < other

    __hash__ = ASFBaseAttribute.__hash__


UNICODE = ASFUnicodeAttribute.TYPE
BYTEARRAY = ASFByteArrayAttribute.TYPE
BOOL = ASFBoolAttribute.TYPE
DWORD = ASFDWordAttribute.TYPE
QWORD = ASFQWordAttribute.TYPE
WORD = ASFWordAttribute.TYPE
GUID = ASFGUIDAttribute.TYPE


def ASFValue(value, kind, **kwargs):
    try:
        attr_type = _attribute_types[kind]
    except KeyError:
        raise ValueError("Unknown value type %r" % kind)
    else:
        return attr_type(value=value, **kwargs)


_attribute_types = {
    ASFUnicodeAttribute.TYPE: ASFUnicodeAttribute,
    ASFByteArrayAttribute.TYPE: ASFByteArrayAttribute,
    ASFBoolAttribute.TYPE: ASFBoolAttribute,
    ASFDWordAttribute.TYPE: ASFDWordAttribute,
    ASFQWordAttribute.TYPE: ASFQWordAttribute,
    ASFWordAttribute.TYPE: ASFWordAttribute,
    ASFGUIDAttribute.TYPE: ASFGUIDAttribute,
}


class BaseObject(object):
    """Base ASF object."""
    GUID = None

    def parse(self, asf, data, fileobj, size):
        self.data = data

    def render(self, asf):
        data = self.GUID + struct.pack("<Q", len(self.data) + 24) + self.data
        return data


class UnknownObject(BaseObject):
    """Unknown ASF object."""
    def __init__(self, guid):
        assert isinstance(guid, bytes)
        self.GUID = guid


class HeaderObject(object):
    """ASF header."""
    GUID = b"\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C"


class ContentDescriptionObject(BaseObject):
    """Content description."""
    GUID = b"\x33\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C"

    NAMES = [
        u"Title",
        u"Author",
        u"Copyright",
        u"Description",
        u"Rating",
    ]

    def parse(self, asf, data, fileobj, size):
        super(ContentDescriptionObject, self).parse(asf, data, fileobj, size)
        asf.content_description_obj = self
        lengths = struct.unpack("<HHHHH", data[:10])
        texts = []
        pos = 10
        for length in lengths:
            end = pos + length
            if length > 0:
                texts.append(data[pos:end].decode("utf-16-le").strip(u"\x00"))
            else:
                texts.append(None)
            pos = end

        for key, value in zip(self.NAMES, texts):
            if value is not None:
                value = ASFUnicodeAttribute(value=value)
                asf._tags.setdefault(self.GUID, []).append((key, value))

    def render(self, asf):
        def render_text(name):
            value = asf.to_content_description.get(name)
            if value is not None:
                return text_type(value).encode("utf-16-le") + b"\x00\x00"
            else:
                return b""

        texts = [render_text(x) for x in self.NAMES]
        data = struct.pack("<HHHHH", *map(len, texts)) + b"".join(texts)
        return self.GUID + struct.pack("<Q", 24 + len(data)) + data


class ExtendedContentDescriptionObject(BaseObject):
    """Extended content description."""
    GUID = b"\x40\xA4\xD0\xD2\x07\xE3\xD2\x11\x97\xF0\x00\xA0\xC9\x5E\xA8\x50"

    def parse(self, asf, data, fileobj, size):
        super(ExtendedContentDescriptionObject, self).parse(
            asf, data, fileobj, size)
        asf.extended_content_description_obj = self
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in xrange(num_attributes):
            name_length, = struct.unpack("<H", data[pos:pos + 2])
            pos += 2
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value_type, value_length = struct.unpack("<HH", data[pos:pos + 4])
            pos += 4
            value = data[pos:pos + value_length]
            pos += value_length
            attr = _attribute_types[value_type](data=value)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_extended_content_description.items()
        data = b"".join(attr.render(name) for (name, attr) in attrs)
        data = struct.pack("<QH", 26 + len(data), len(attrs)) + data
        return self.GUID + data


class FilePropertiesObject(BaseObject):
    """File properties."""
    GUID = b"\xA1\xDC\xAB\x8C\x47\xA9\xCF\x11\x8E\xE4\x00\xC0\x0C\x20\x53\x65"

    def parse(self, asf, data, fileobj, size):
        super(FilePropertiesObject, self).parse(asf, data, fileobj, size)
        length, _, preroll = struct.unpack("<QQQ", data[40:64])
        asf.info.length = (length / 10000000.0) - (preroll / 1000.0)


class StreamPropertiesObject(BaseObject):
    """Stream properties."""
    GUID = b"\x91\x07\xDC\xB7\xB7\xA9\xCF\x11\x8E\xE6\x00\xC0\x0C\x20\x53\x65"

    def parse(self, asf, data, fileobj, size):
        super(StreamPropertiesObject, self).parse(asf, data, fileobj, size)
        channels, sample_rate, bitrate = struct.unpack("<HII", data[56:66])
        asf.info.channels = channels
        asf.info.sample_rate = sample_rate
        asf.info.bitrate = bitrate * 8


class HeaderExtensionObject(BaseObject):
    """Header extension."""
    GUID = b"\xb5\x03\xbf_.\xa9\xcf\x11\x8e\xe3\x00\xc0\x0c Se"

    def parse(self, asf, data, fileobj, size):
        super(HeaderExtensionObject, self).parse(asf, data, fileobj, size)
        asf.header_extension_obj = self
        datasize, = struct.unpack("<I", data[18:22])
        datapos = 0
        self.objects = []
        while datapos < datasize:
            guid, size = struct.unpack(
                "<16sQ", data[22 + datapos:22 + datapos + 24])
            if guid in _object_types:
                obj = _object_types[guid]()
            else:
                obj = UnknownObject(guid)
            obj.parse(asf, data[22 + datapos + 24:22 + datapos + size],
                      fileobj, size)
            self.objects.append(obj)
            datapos += size

    def render(self, asf):
        data = b"".join(obj.render(asf) for obj in self.objects)
        return (self.GUID + struct.pack("<Q", 24 + 16 + 6 + len(data)) +
                b"\x11\xD2\xD3\xAB\xBA\xA9\xcf\x11" +
                b"\x8E\xE6\x00\xC0\x0C\x20\x53\x65" +
                b"\x06\x00" + struct.pack("<I", len(data)) + data)


class MetadataObject(BaseObject):
    """Metadata description."""
    GUID = b"\xea\xcb\xf8\xc5\xaf[wH\x84g\xaa\x8cD\xfaL\xca"

    def parse(self, asf, data, fileobj, size):
        super(MetadataObject, self).parse(asf, data, fileobj, size)
        asf.metadata_obj = self
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in xrange(num_attributes):
            (reserved, stream, name_length, value_type,
             value_length) = struct.unpack("<HHHHI", data[pos:pos + 12])
            pos += 12
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value = data[pos:pos + value_length]
            pos += value_length
            args = {'data': value, 'stream': stream}
            if value_type == 2:
                args['dword'] = False
            attr = _attribute_types[value_type](**args)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_metadata.items()
        data = b"".join([attr.render_m(name) for (name, attr) in attrs])
        return (self.GUID + struct.pack("<QH", 26 + len(data), len(attrs)) +
                data)


class MetadataLibraryObject(BaseObject):
    """Metadata library description."""
    GUID = b"\x94\x1c#D\x98\x94\xd1I\xa1A\x1d\x13NEpT"

    def parse(self, asf, data, fileobj, size):
        super(MetadataLibraryObject, self).parse(asf, data, fileobj, size)
        asf.metadata_library_obj = self
        num_attributes, = struct.unpack("<H", data[0:2])
        pos = 2
        for i in xrange(num_attributes):
            (language, stream, name_length, value_type,
             value_length) = struct.unpack("<HHHHI", data[pos:pos + 12])
            pos += 12
            name = data[pos:pos + name_length]
            name = name.decode("utf-16-le").strip("\x00")
            pos += name_length
            value = data[pos:pos + value_length]
            pos += value_length
            args = {'data': value, 'language': language, 'stream': stream}
            if value_type == 2:
                args['dword'] = False
            attr = _attribute_types[value_type](**args)
            asf._tags.setdefault(self.GUID, []).append((name, attr))

    def render(self, asf):
        attrs = asf.to_metadata_library
        data = b"".join([attr.render_ml(name) for (name, attr) in attrs])
        return (self.GUID + struct.pack("<QH", 26 + len(data), len(attrs)) +
                data)


_object_types = {
    ExtendedContentDescriptionObject.GUID: ExtendedContentDescriptionObject,
    ContentDescriptionObject.GUID: ContentDescriptionObject,
    FilePropertiesObject.GUID: FilePropertiesObject,
    StreamPropertiesObject.GUID: StreamPropertiesObject,
    HeaderExtensionObject.GUID: HeaderExtensionObject,
    MetadataLibraryObject.GUID: MetadataLibraryObject,
    MetadataObject.GUID: MetadataObject,
}


class ASF(FileType):
    """An ASF file, probably containing WMA or WMV."""

    _mimes = ["audio/x-ms-wma", "audio/x-ms-wmv", "video/x-ms-asf",
              "audio/x-wma", "video/x-wmv"]

    def load(self, filename):
        self.filename = filename
        with open(filename, "rb") as fileobj:
            self.size = 0
            self.size1 = 0
            self.size2 = 0
            self.offset1 = 0
            self.offset2 = 0
            self.num_objects = 0
            self.info = ASFInfo()
            self.tags = ASFTags()
            self.__read_file(fileobj)

    def save(self):
        # Move attributes to the right objects
        self.to_content_description = {}
        self.to_extended_content_description = {}
        self.to_metadata = {}
        self.to_metadata_library = []
        for name, value in self.tags:
            library_only = (value.data_size() > 0xFFFF or value.TYPE == GUID)
            can_cont_desc = value.TYPE == UNICODE

            if library_only or value.language is not None:
                self.to_metadata_library.append((name, value))
            elif value.stream is not None:
                if name not in self.to_metadata:
                    self.to_metadata[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            elif name in ContentDescriptionObject.NAMES:
                if name not in self.to_content_description and can_cont_desc:
                    self.to_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))
            else:
                if name not in self.to_extended_content_description:
                    self.to_extended_content_description[name] = value
                else:
                    self.to_metadata_library.append((name, value))

        # Add missing objects
        if not self.content_description_obj:
            self.content_description_obj = \
                ContentDescriptionObject()
            self.objects.append(self.content_description_obj)
        if not self.extended_content_description_obj:
            self.extended_content_description_obj = \
                ExtendedContentDescriptionObject()
            self.objects.append(self.extended_content_description_obj)
        if not self.header_extension_obj:
            self.header_extension_obj = \
                HeaderExtensionObject()
            self.objects.append(self.header_extension_obj)
        if not self.metadata_obj:
            self.metadata_obj = \
                MetadataObject()
            self.header_extension_obj.objects.append(self.metadata_obj)
        if not self.metadata_library_obj:
            self.metadata_library_obj = \
                MetadataLibraryObject()
            self.header_extension_obj.objects.append(self.metadata_library_obj)

        # Render the header
        data = b"".join([obj.render(self) for obj in self.objects])
        data = (HeaderObject.GUID +
                struct.pack("<QL", len(data) + 30, len(self.objects)) +
                b"\x01\x02" + data)

        with open(self.filename, "rb+") as fileobj:
            size = len(data)
            if size > self.size:
                insert_bytes(fileobj, size - self.size, self.size)
            if size < self.size:
                delete_bytes(fileobj, self.size - size, 0)
            fileobj.seek(0)
            fileobj.write(data)

        self.size = size
        self.num_objects = len(self.objects)

    def __read_file(self, fileobj):
        header = fileobj.read(30)
        if len(header) != 30 or header[:16] != HeaderObject.GUID:
            raise ASFHeaderError("Not an ASF file.")

        self.extended_content_description_obj = None
        self.content_description_obj = None
        self.header_extension_obj = None
        self.metadata_obj = None
        self.metadata_library_obj = None

        self.size, self.num_objects = struct.unpack("<QL", header[16:28])
        self.objects = []
        self._tags = {}
        for i in xrange(self.num_objects):
            self.__read_object(fileobj)

        for guid in [ContentDescriptionObject.GUID,
                ExtendedContentDescriptionObject.GUID, MetadataObject.GUID,
                MetadataLibraryObject.GUID]:
            self.tags.extend(self._tags.pop(guid, []))
        assert not self._tags

    def __read_object(self, fileobj):
        guid, size = struct.unpack("<16sQ", fileobj.read(24))
        if guid in _object_types:
            obj = _object_types[guid]()
        else:
            obj = UnknownObject(guid)
        data = fileobj.read(size - 24)
        obj.parse(self, data, fileobj, size)
        self.objects.append(obj)

    @staticmethod
    def score(filename, fileobj, header):
        return header.startswith(HeaderObject.GUID) * 2

Open = ASF
