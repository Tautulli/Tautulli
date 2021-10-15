# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2009-2017 Nominum, Inc.
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

"""EDNS Options"""

import math
import socket
import struct

import dns.enum
import dns.inet

class OptionType(dns.enum.IntEnum):
    #: NSID
    NSID = 3
    #: DAU
    DAU = 5
    #: DHU
    DHU = 6
    #: N3U
    N3U = 7
    #: ECS (client-subnet)
    ECS = 8
    #: EXPIRE
    EXPIRE = 9
    #: COOKIE
    COOKIE = 10
    #: KEEPALIVE
    KEEPALIVE = 11
    #: PADDING
    PADDING = 12
    #: CHAIN
    CHAIN = 13

    @classmethod
    def _maximum(cls):
        return 65535

globals().update(OptionType.__members__)

class Option:

    """Base class for all EDNS option types."""

    def __init__(self, otype):
        """Initialize an option.

        *otype*, an ``int``, is the option type.
        """
        self.otype = otype

    def to_wire(self, file=None):
        """Convert an option to wire format.

        Returns a ``bytes`` or ``None``.

        """
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_wire_parser(cls, otype, parser):
        """Build an EDNS option object from wire format.

        *otype*, an ``int``, is the option type.

        *parser*, a ``dns.wire.Parser``, the parser, which should be
        restructed to the option length.

        Returns a ``dns.edns.Option``.
        """
        raise NotImplementedError  # pragma: no cover

    def _cmp(self, other):
        """Compare an EDNS option with another option of the same type.

        Returns < 0 if < *other*, 0 if == *other*, and > 0 if > *other*.
        """
        wire = self.to_wire()
        owire = other.to_wire()
        if wire == owire:
            return 0
        if wire > owire:
            return 1
        return -1

    def __eq__(self, other):
        if not isinstance(other, Option):
            return False
        if self.otype != other.otype:
            return False
        return self._cmp(other) == 0

    def __ne__(self, other):
        if not isinstance(other, Option):
            return True
        if self.otype != other.otype:
            return True
        return self._cmp(other) != 0

    def __lt__(self, other):
        if not isinstance(other, Option) or \
                self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) < 0

    def __le__(self, other):
        if not isinstance(other, Option) or \
                self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) <= 0

    def __ge__(self, other):
        if not isinstance(other, Option) or \
                self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) >= 0

    def __gt__(self, other):
        if not isinstance(other, Option) or \
                self.otype != other.otype:
            return NotImplemented
        return self._cmp(other) > 0

    def __str__(self):
        return self.to_text()


class GenericOption(Option):

    """Generic Option Class

    This class is used for EDNS option types for which we have no better
    implementation.
    """

    def __init__(self, otype, data):
        super().__init__(otype)
        self.data = data

    def to_wire(self, file=None):
        if file:
            file.write(self.data)
        else:
            return self.data

    def to_text(self):
        return "Generic %d" % self.otype

    @classmethod
    def from_wire_parser(cls, otype, parser):
        return cls(otype, parser.get_remaining())


class ECSOption(Option):
    """EDNS Client Subnet (ECS, RFC7871)"""

    def __init__(self, address, srclen=None, scopelen=0):
        """*address*, a ``str``, is the client address information.

        *srclen*, an ``int``, the source prefix length, which is the
        leftmost number of bits of the address to be used for the
        lookup.  The default is 24 for IPv4 and 56 for IPv6.

        *scopelen*, an ``int``, the scope prefix length.  This value
        must be 0 in queries, and should be set in responses.
        """

        super().__init__(OptionType.ECS)
        af = dns.inet.af_for_address(address)

        if af == socket.AF_INET6:
            self.family = 2
            if srclen is None:
                srclen = 56
        elif af == socket.AF_INET:
            self.family = 1
            if srclen is None:
                srclen = 24
        else:
            raise ValueError('Bad ip family')

        self.address = address
        self.srclen = srclen
        self.scopelen = scopelen

        addrdata = dns.inet.inet_pton(af, address)
        nbytes = int(math.ceil(srclen / 8.0))

        # Truncate to srclen and pad to the end of the last octet needed
        # See RFC section 6
        self.addrdata = addrdata[:nbytes]
        nbits = srclen % 8
        if nbits != 0:
            last = struct.pack('B',
                               ord(self.addrdata[-1:]) & (0xff << (8 - nbits)))
            self.addrdata = self.addrdata[:-1] + last

    def to_text(self):
        return "ECS {}/{} scope/{}".format(self.address, self.srclen,
                                           self.scopelen)

    @staticmethod
    def from_text(text):
        """Convert a string into a `dns.edns.ECSOption`

        *text*, a `str`, the text form of the option.

        Returns a `dns.edns.ECSOption`.

        Examples:

        >>> import dns.edns
        >>>
        >>> # basic example
        >>> dns.edns.ECSOption.from_text('1.2.3.4/24')
        >>>
        >>> # also understands scope
        >>> dns.edns.ECSOption.from_text('1.2.3.4/24/32')
        >>>
        >>> # IPv6
        >>> dns.edns.ECSOption.from_text('2001:4b98::1/64/64')
        >>>
        >>> # it understands results from `dns.edns.ECSOption.to_text()`
        >>> dns.edns.ECSOption.from_text('ECS 1.2.3.4/24/32')
        """
        optional_prefix = 'ECS'
        tokens = text.split()
        ecs_text = None
        if len(tokens) == 1:
            ecs_text = tokens[0]
        elif len(tokens) == 2:
            if tokens[0] != optional_prefix:
                raise ValueError('could not parse ECS from "{}"'.format(text))
            ecs_text = tokens[1]
        else:
            raise ValueError('could not parse ECS from "{}"'.format(text))
        n_slashes = ecs_text.count('/')
        if n_slashes == 1:
            address, srclen = ecs_text.split('/')
            scope = 0
        elif n_slashes == 2:
            address, srclen, scope = ecs_text.split('/')
        else:
            raise ValueError('could not parse ECS from "{}"'.format(text))
        try:
            scope = int(scope)
        except ValueError:
            raise ValueError('invalid scope ' +
                             '"{}": scope must be an integer'.format(scope))
        try:
            srclen = int(srclen)
        except ValueError:
            raise ValueError('invalid srclen ' +
                             '"{}": srclen must be an integer'.format(srclen))
        return ECSOption(address, srclen, scope)

    def to_wire(self, file=None):
        value = (struct.pack('!HBB', self.family, self.srclen, self.scopelen) +
                 self.addrdata)
        if file:
            file.write(value)
        else:
            return value

    @classmethod
    def from_wire_parser(cls, otype, parser):
        family, src, scope = parser.get_struct('!HBB')
        addrlen = int(math.ceil(src / 8.0))
        prefix = parser.get_bytes(addrlen)
        if family == 1:
            pad = 4 - addrlen
            addr = dns.ipv4.inet_ntoa(prefix + b'\x00' * pad)
        elif family == 2:
            pad = 16 - addrlen
            addr = dns.ipv6.inet_ntoa(prefix + b'\x00' * pad)
        else:
            raise ValueError('unsupported family')

        return cls(addr, src, scope)


_type_to_class = {
    OptionType.ECS: ECSOption
}

def get_option_class(otype):
    """Return the class for the specified option type.

    The GenericOption class is used if a more specific class is not
    known.
    """

    cls = _type_to_class.get(otype)
    if cls is None:
        cls = GenericOption
    return cls


def option_from_wire_parser(otype, parser):
    """Build an EDNS option object from wire format.

    *otype*, an ``int``, is the option type.

    *parser*, a ``dns.wire.Parser``, the parser, which should be
    restricted to the option length.

    Returns an instance of a subclass of ``dns.edns.Option``.
    """
    cls = get_option_class(otype)
    otype = OptionType.make(otype)
    return cls.from_wire_parser(otype, parser)


def option_from_wire(otype, wire, current, olen):
    """Build an EDNS option object from wire format.

    *otype*, an ``int``, is the option type.

    *wire*, a ``bytes``, is the wire-format message.

    *current*, an ``int``, is the offset in *wire* of the beginning
    of the rdata.

    *olen*, an ``int``, is the length of the wire-format option data

    Returns an instance of a subclass of ``dns.edns.Option``.
    """
    parser = dns.wire.Parser(wire, current)
    with parser.restrict_to(olen):
        return option_from_wire_parser(otype, parser)
