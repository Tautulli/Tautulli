# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2006, 2007, 2009-2011 Nominum, Inc.
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

import struct

import dns.exception
import dns.rdtypes.util


class Relay(dns.rdtypes.util.Gateway):
    name = 'AMTRELAY relay'

class AMTRELAY(dns.rdata.Rdata):

    """AMTRELAY record"""

    # see: RFC 8777

    __slots__ = ['precedence', 'discovery_optional', 'relay_type', 'relay']

    def __init__(self, rdclass, rdtype, precedence, discovery_optional,
                 relay_type, relay):
        super().__init__(rdclass, rdtype)
        Relay(relay_type, relay).check()
        object.__setattr__(self, 'precedence', precedence)
        object.__setattr__(self, 'discovery_optional', discovery_optional)
        object.__setattr__(self, 'relay_type', relay_type)
        object.__setattr__(self, 'relay', relay)

    def to_text(self, origin=None, relativize=True, **kw):
        relay = Relay(self.relay_type, self.relay).to_text(origin, relativize)
        return '%d %d %d %s' % (self.precedence, self.discovery_optional,
                                self.relay_type, relay)

    @classmethod
    def from_text(cls, rdclass, rdtype, tok, origin=None, relativize=True,
                  relativize_to=None):
        precedence = tok.get_uint8()
        discovery_optional = tok.get_uint8()
        if discovery_optional > 1:
            raise dns.exception.SyntaxError('expecting 0 or 1')
        discovery_optional = bool(discovery_optional)
        relay_type = tok.get_uint8()
        if relay_type > 0x7f:
            raise dns.exception.SyntaxError('expecting an integer <= 127')
        relay = Relay(relay_type).from_text(tok, origin, relativize,
                                            relativize_to)
        return cls(rdclass, rdtype, precedence, discovery_optional, relay_type,
                   relay)

    def _to_wire(self, file, compress=None, origin=None, canonicalize=False):
        relay_type = self.relay_type | (self.discovery_optional << 7)
        header = struct.pack("!BB", self.precedence, relay_type)
        file.write(header)
        Relay(self.relay_type, self.relay).to_wire(file, compress, origin,
                                                   canonicalize)

    @classmethod
    def from_wire_parser(cls, rdclass, rdtype, parser, origin=None):
        (precedence, relay_type) = parser.get_struct('!BB')
        discovery_optional = bool(relay_type >> 7)
        relay_type &= 0x7f
        relay = Relay(relay_type).from_wire_parser(parser, origin)
        return cls(rdclass, rdtype, precedence, discovery_optional, relay_type,
                   relay)
