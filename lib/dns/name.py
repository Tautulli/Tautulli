# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS Names.

@var root: The DNS root name.
@type root: dns.name.Name object
@var empty: The empty DNS name.
@type empty: dns.name.Name object
"""

from io import BytesIO
import struct
import sys
import copy
import encodings.idna

import dns.exception
import dns.wiredata

from ._compat import long, binary_type, text_type, unichr

try:
    maxint = sys.maxint
except:
    maxint = (1 << (8 * struct.calcsize("P"))) / 2 - 1

NAMERELN_NONE = 0
NAMERELN_SUPERDOMAIN = 1
NAMERELN_SUBDOMAIN = 2
NAMERELN_EQUAL = 3
NAMERELN_COMMONANCESTOR = 4


class EmptyLabel(dns.exception.SyntaxError):

    """A DNS label is empty."""


class BadEscape(dns.exception.SyntaxError):

    """An escaped code in a text format of DNS name is invalid."""


class BadPointer(dns.exception.FormError):

    """A DNS compression pointer points forward instead of backward."""


class BadLabelType(dns.exception.FormError):

    """The label type in DNS name wire format is unknown."""


class NeedAbsoluteNameOrOrigin(dns.exception.DNSException):

    """An attempt was made to convert a non-absolute name to
    wire when there was also a non-absolute (or missing) origin."""


class NameTooLong(dns.exception.FormError):

    """A DNS name is > 255 octets long."""


class LabelTooLong(dns.exception.SyntaxError):

    """A DNS label is > 63 octets long."""


class AbsoluteConcatenation(dns.exception.DNSException):

    """An attempt was made to append anything other than the
    empty name to an absolute DNS name."""


class NoParent(dns.exception.DNSException):

    """An attempt was made to get the parent of the root name
    or the empty name."""

_escaped = bytearray(b'"().;\\@$')


def _escapify(label, unicode_mode=False):
    """Escape the characters in label which need it.
    @param unicode_mode: escapify only special and whitespace (<= 0x20)
    characters
    @returns: the escaped string
    @rtype: string"""
    if not unicode_mode:
        text = ''
        if isinstance(label, text_type):
            label = label.encode()
        for c in bytearray(label):
            packed = struct.pack('!B', c).decode()
            if c in _escaped:
                text += '\\' + packed
            elif c > 0x20 and c < 0x7F:
                text += packed
            else:
                text += '\\%03d' % c
        return text.encode()

    text = u''
    if isinstance(label, binary_type):
        label = label.decode()
    for c in label:
        if c > u'\x20' and c < u'\x7f':
            text += c
        else:
            if c >= u'\x7f':
                text += c
            else:
                text += u'\\%03d' % c
    return text


def _validate_labels(labels):
    """Check for empty labels in the middle of a label sequence,
    labels that are too long, and for too many labels.
    @raises NameTooLong: the name as a whole is too long
    @raises EmptyLabel: a label is empty (i.e. the root label) and appears
    in a position other than the end of the label sequence"""

    l = len(labels)
    total = 0
    i = -1
    j = 0
    for label in labels:
        ll = len(label)
        total += ll + 1
        if ll > 63:
            raise LabelTooLong
        if i < 0 and label == b'':
            i = j
        j += 1
    if total > 255:
        raise NameTooLong
    if i >= 0 and i != l - 1:
        raise EmptyLabel


def _ensure_bytes(label):
    if isinstance(label, binary_type):
        return label
    if isinstance(label, text_type):
        return label.encode()
    raise ValueError


class Name(object):

    """A DNS name.

    The dns.name.Name class represents a DNS name as a tuple of labels.
    Instances of the class are immutable.

    @ivar labels: The tuple of labels in the name. Each label is a string of
    up to 63 octets."""

    __slots__ = ['labels']

    def __init__(self, labels):
        """Initialize a domain name from a list of labels.
        @param labels: the labels
        @type labels: any iterable whose values are strings
        """
        labels = [_ensure_bytes(x) for x in labels]
        super(Name, self).__setattr__('labels', tuple(labels))
        _validate_labels(self.labels)

    def __setattr__(self, name, value):
        raise TypeError("object doesn't support attribute assignment")

    def __copy__(self):
        return Name(self.labels)

    def __deepcopy__(self, memo):
        return Name(copy.deepcopy(self.labels, memo))

    def __getstate__(self):
        return {'labels': self.labels}

    def __setstate__(self, state):
        super(Name, self).__setattr__('labels', state['labels'])
        _validate_labels(self.labels)

    def is_absolute(self):
        """Is the most significant label of this name the root label?
        @rtype: bool
        """

        return len(self.labels) > 0 and self.labels[-1] == b''

    def is_wild(self):
        """Is this name wild?  (I.e. Is the least significant label '*'?)
        @rtype: bool
        """

        return len(self.labels) > 0 and self.labels[0] == b'*'

    def __hash__(self):
        """Return a case-insensitive hash of the name.
        @rtype: int
        """

        h = long(0)
        for label in self.labels:
            for c in bytearray(label.lower()):
                h += (h << 3) + c
        return int(h % maxint)

    def fullcompare(self, other):
        """Compare two names, returning a 3-tuple (relation, order, nlabels).

        I{relation} describes the relation ship between the names,
        and is one of: dns.name.NAMERELN_NONE,
        dns.name.NAMERELN_SUPERDOMAIN, dns.name.NAMERELN_SUBDOMAIN,
        dns.name.NAMERELN_EQUAL, or dns.name.NAMERELN_COMMONANCESTOR

        I{order} is < 0 if self < other, > 0 if self > other, and ==
        0 if self == other.  A relative name is always less than an
        absolute name.  If both names have the same relativity, then
        the DNSSEC order relation is used to order them.

        I{nlabels} is the number of significant labels that the two names
        have in common.
        """

        sabs = self.is_absolute()
        oabs = other.is_absolute()
        if sabs != oabs:
            if sabs:
                return (NAMERELN_NONE, 1, 0)
            else:
                return (NAMERELN_NONE, -1, 0)
        l1 = len(self.labels)
        l2 = len(other.labels)
        ldiff = l1 - l2
        if ldiff < 0:
            l = l1
        else:
            l = l2

        order = 0
        nlabels = 0
        namereln = NAMERELN_NONE
        while l > 0:
            l -= 1
            l1 -= 1
            l2 -= 1
            label1 = self.labels[l1].lower()
            label2 = other.labels[l2].lower()
            if label1 < label2:
                order = -1
                if nlabels > 0:
                    namereln = NAMERELN_COMMONANCESTOR
                return (namereln, order, nlabels)
            elif label1 > label2:
                order = 1
                if nlabels > 0:
                    namereln = NAMERELN_COMMONANCESTOR
                return (namereln, order, nlabels)
            nlabels += 1
        order = ldiff
        if ldiff < 0:
            namereln = NAMERELN_SUPERDOMAIN
        elif ldiff > 0:
            namereln = NAMERELN_SUBDOMAIN
        else:
            namereln = NAMERELN_EQUAL
        return (namereln, order, nlabels)

    def is_subdomain(self, other):
        """Is self a subdomain of other?

        The notion of subdomain includes equality.
        @rtype: bool
        """

        (nr, o, nl) = self.fullcompare(other)
        if nr == NAMERELN_SUBDOMAIN or nr == NAMERELN_EQUAL:
            return True
        return False

    def is_superdomain(self, other):
        """Is self a superdomain of other?

        The notion of subdomain includes equality.
        @rtype: bool
        """

        (nr, o, nl) = self.fullcompare(other)
        if nr == NAMERELN_SUPERDOMAIN or nr == NAMERELN_EQUAL:
            return True
        return False

    def canonicalize(self):
        """Return a name which is equal to the current name, but is in
        DNSSEC canonical form.
        @rtype: dns.name.Name object
        """

        return Name([x.lower() for x in self.labels])

    def __eq__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] == 0
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] != 0
        else:
            return True

    def __lt__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] < 0
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] <= 0
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] >= 0
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, Name):
            return self.fullcompare(other)[1] > 0
        else:
            return NotImplemented

    def __repr__(self):
        return '<DNS name ' + self.__str__() + '>'

    def __str__(self):
        return self.to_text(False).decode()

    def to_text(self, omit_final_dot=False):
        """Convert name to text format.
        @param omit_final_dot: If True, don't emit the final dot (denoting the
        root label) for absolute names.  The default is False.
        @rtype: string
        """

        if len(self.labels) == 0:
            return b'@'
        if len(self.labels) == 1 and self.labels[0] == b'':
            return b'.'
        if omit_final_dot and self.is_absolute():
            l = self.labels[:-1]
        else:
            l = self.labels
        s = b'.'.join(map(_escapify, l))
        return s

    def to_unicode(self, omit_final_dot=False):
        """Convert name to Unicode text format.

        IDN ACE labels are converted to Unicode.

        @param omit_final_dot: If True, don't emit the final dot (denoting the
        root label) for absolute names.  The default is False.
        @rtype: string
        """

        if len(self.labels) == 0:
            return u'@'
        if len(self.labels) == 1 and self.labels[0] == '':
            return u'.'
        if omit_final_dot and self.is_absolute():
            l = self.labels[:-1]
        else:
            l = self.labels
        s = u'.'.join([_escapify(encodings.idna.ToUnicode(x), True)
                      for x in l])
        return s

    def to_digestable(self, origin=None):
        """Convert name to a format suitable for digesting in hashes.

        The name is canonicalized and converted to uncompressed wire format.

        @param origin: If the name is relative and origin is not None, then
        origin will be appended to it.
        @type origin: dns.name.Name object
        @raises NeedAbsoluteNameOrOrigin: All names in wire format are
        absolute.  If self is a relative name, then an origin must be supplied;
        if it is missing, then this exception is raised
        @rtype: string
        """

        if not self.is_absolute():
            if origin is None or not origin.is_absolute():
                raise NeedAbsoluteNameOrOrigin
            labels = list(self.labels)
            labels.extend(list(origin.labels))
        else:
            labels = self.labels
        dlabels = [struct.pack('!B%ds' % len(x), len(x), x.lower())
                   for x in labels]
        return b''.join(dlabels)

    def to_wire(self, file=None, compress=None, origin=None):
        """Convert name to wire format, possibly compressing it.

        @param file: the file where the name is emitted (typically
        a BytesIO file).  If None, a string containing the wire name
        will be returned.
        @type file: file or None
        @param compress: The compression table.  If None (the default) names
        will not be compressed.
        @type compress: dict
        @param origin: If the name is relative and origin is not None, then
        origin will be appended to it.
        @type origin: dns.name.Name object
        @raises NeedAbsoluteNameOrOrigin: All names in wire format are
        absolute.  If self is a relative name, then an origin must be supplied;
        if it is missing, then this exception is raised
        """

        if file is None:
            file = BytesIO()
            want_return = True
        else:
            want_return = False

        if not self.is_absolute():
            if origin is None or not origin.is_absolute():
                raise NeedAbsoluteNameOrOrigin
            labels = list(self.labels)
            labels.extend(list(origin.labels))
        else:
            labels = self.labels
        i = 0
        for label in labels:
            n = Name(labels[i:])
            i += 1
            if compress is not None:
                pos = compress.get(n)
            else:
                pos = None
            if pos is not None:
                value = 0xc000 + pos
                s = struct.pack('!H', value)
                file.write(s)
                break
            else:
                if compress is not None and len(n) > 1:
                    pos = file.tell()
                    if pos <= 0x3fff:
                        compress[n] = pos
                l = len(label)
                file.write(struct.pack('!B', l))
                if l > 0:
                    file.write(label)
        if want_return:
            return file.getvalue()

    def __len__(self):
        """The length of the name (in labels).
        @rtype: int
        """

        return len(self.labels)

    def __getitem__(self, index):
        return self.labels[index]

    def __getslice__(self, start, stop):
        return self.labels[start:stop]

    def __add__(self, other):
        return self.concatenate(other)

    def __sub__(self, other):
        return self.relativize(other)

    def split(self, depth):
        """Split a name into a prefix and suffix at depth.

        @param depth: the number of labels in the suffix
        @type depth: int
        @raises ValueError: the depth was not >= 0 and <= the length of the
        name.
        @returns: the tuple (prefix, suffix)
        @rtype: tuple
        """

        l = len(self.labels)
        if depth == 0:
            return (self, dns.name.empty)
        elif depth == l:
            return (dns.name.empty, self)
        elif depth < 0 or depth > l:
            raise ValueError(
                'depth must be >= 0 and <= the length of the name')
        return (Name(self[: -depth]), Name(self[-depth:]))

    def concatenate(self, other):
        """Return a new name which is the concatenation of self and other.
        @rtype: dns.name.Name object
        @raises AbsoluteConcatenation: self is absolute and other is
        not the empty name
        """

        if self.is_absolute() and len(other) > 0:
            raise AbsoluteConcatenation
        labels = list(self.labels)
        labels.extend(list(other.labels))
        return Name(labels)

    def relativize(self, origin):
        """If self is a subdomain of origin, return a new name which is self
        relative to origin.  Otherwise return self.
        @rtype: dns.name.Name object
        """

        if origin is not None and self.is_subdomain(origin):
            return Name(self[: -len(origin)])
        else:
            return self

    def derelativize(self, origin):
        """If self is a relative name, return a new name which is the
        concatenation of self and origin.  Otherwise return self.
        @rtype: dns.name.Name object
        """

        if not self.is_absolute():
            return self.concatenate(origin)
        else:
            return self

    def choose_relativity(self, origin=None, relativize=True):
        """Return a name with the relativity desired by the caller.  If
        origin is None, then self is returned.  Otherwise, if
        relativize is true the name is relativized, and if relativize is
        false the name is derelativized.
        @rtype: dns.name.Name object
        """

        if origin:
            if relativize:
                return self.relativize(origin)
            else:
                return self.derelativize(origin)
        else:
            return self

    def parent(self):
        """Return the parent of the name.
        @rtype: dns.name.Name object
        @raises NoParent: the name is either the root name or the empty name,
        and thus has no parent.
        """
        if self == root or self == empty:
            raise NoParent
        return Name(self.labels[1:])

root = Name([b''])
empty = Name([])


def from_unicode(text, origin=root):
    """Convert unicode text into a Name object.

    Labels are encoded in IDN ACE form.

    @rtype: dns.name.Name object
    """

    if not isinstance(text, text_type):
        raise ValueError("input to from_unicode() must be a unicode string")
    if not (origin is None or isinstance(origin, Name)):
        raise ValueError("origin must be a Name or None")
    labels = []
    label = u''
    escaping = False
    edigits = 0
    total = 0
    if text == u'@':
        text = u''
    if text:
        if text == u'.':
            return Name([b''])        # no Unicode "u" on this constant!
        for c in text:
            if escaping:
                if edigits == 0:
                    if c.isdigit():
                        total = int(c)
                        edigits += 1
                    else:
                        label += c
                        escaping = False
                else:
                    if not c.isdigit():
                        raise BadEscape
                    total *= 10
                    total += int(c)
                    edigits += 1
                    if edigits == 3:
                        escaping = False
                        label += unichr(total)
            elif c in [u'.', u'\u3002', u'\uff0e', u'\uff61']:
                if len(label) == 0:
                    raise EmptyLabel
                try:
                    labels.append(encodings.idna.ToASCII(label))
                except UnicodeError:
                    raise LabelTooLong
                label = u''
            elif c == u'\\':
                escaping = True
                edigits = 0
                total = 0
            else:
                label += c
        if escaping:
            raise BadEscape
        if len(label) > 0:
            try:
                labels.append(encodings.idna.ToASCII(label))
            except UnicodeError:
                raise LabelTooLong
        else:
            labels.append(b'')

    if (len(labels) == 0 or labels[-1] != b'') and origin is not None:
        labels.extend(list(origin.labels))
    return Name(labels)


def from_text(text, origin=root):
    """Convert text into a Name object.
    @rtype: dns.name.Name object
    """

    if isinstance(text, text_type):
        return from_unicode(text, origin)
    if not isinstance(text, binary_type):
        raise ValueError("input to from_text() must be a string")
    if not (origin is None or isinstance(origin, Name)):
        raise ValueError("origin must be a Name or None")
    labels = []
    label = b''
    escaping = False
    edigits = 0
    total = 0
    if text == b'@':
        text = b''
    if text:
        if text == b'.':
            return Name([b''])
        for c in bytearray(text):
            byte_ = struct.pack('!B', c)
            if escaping:
                if edigits == 0:
                    if byte_.isdigit():
                        total = int(byte_)
                        edigits += 1
                    else:
                        label += byte_
                        escaping = False
                else:
                    if not byte_.isdigit():
                        raise BadEscape
                    total *= 10
                    total += int(byte_)
                    edigits += 1
                    if edigits == 3:
                        escaping = False
                        label += struct.pack('!B', total)
            elif byte_ == b'.':
                if len(label) == 0:
                    raise EmptyLabel
                labels.append(label)
                label = b''
            elif byte_ == b'\\':
                escaping = True
                edigits = 0
                total = 0
            else:
                label += byte_
        if escaping:
            raise BadEscape
        if len(label) > 0:
            labels.append(label)
        else:
            labels.append(b'')
    if (len(labels) == 0 or labels[-1] != b'') and origin is not None:
        labels.extend(list(origin.labels))
    return Name(labels)


def from_wire(message, current):
    """Convert possibly compressed wire format into a Name.
    @param message: the entire DNS message
    @type message: string
    @param current: the offset of the beginning of the name from the start
    of the message
    @type current: int
    @raises dns.name.BadPointer: a compression pointer did not point backwards
    in the message
    @raises dns.name.BadLabelType: an invalid label type was encountered.
    @returns: a tuple consisting of the name that was read and the number
    of bytes of the wire format message which were consumed reading it
    @rtype: (dns.name.Name object, int) tuple
    """

    if not isinstance(message, binary_type):
        raise ValueError("input to from_wire() must be a byte string")
    message = dns.wiredata.maybe_wrap(message)
    labels = []
    biggest_pointer = current
    hops = 0
    count = message[current]
    current += 1
    cused = 1
    while count != 0:
        if count < 64:
            labels.append(message[current: current + count].unwrap())
            current += count
            if hops == 0:
                cused += count
        elif count >= 192:
            current = (count & 0x3f) * 256 + message[current]
            if hops == 0:
                cused += 1
            if current >= biggest_pointer:
                raise BadPointer
            biggest_pointer = current
            hops += 1
        else:
            raise BadLabelType
        count = message[current]
        current += 1
        if hops == 0:
            cused += 1
    labels.append('')
    return (Name(labels), cused)
