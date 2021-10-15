# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2003-2007, 2009-2011 Nominum, Inc.
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
import dns.rdata
import dns.name


class SRV(dns.rdata.Rdata):

    """SRV record"""

    # see: RFC 2782

    __slots__ = ['priority', 'weight', 'port', 'target']

    def __init__(self, rdclass, rdtype, priority, weight, port, target):
        super().__init__(rdclass, rdtype)
        object.__setattr__(self, 'priority', priority)
        object.__setattr__(self, 'weight', weight)
        object.__setattr__(self, 'port', port)
        object.__setattr__(self, 'target', target)

    def to_text(self, origin=None, relativize=True, **kw):
        target = self.target.choose_relativity(origin, relativize)
        return '%d %d %d %s' % (self.priority, self.weight, self.port,
                                target)

    @classmethod
    def from_text(cls, rdclass, rdtype, tok, origin=None, relativize=True,
                  relativize_to=None):
        priority = tok.get_uint16()
        weight = tok.get_uint16()
        port = tok.get_uint16()
        target = tok.get_name(origin, relativize, relativize_to)
        tok.get_eol()
        return cls(rdclass, rdtype, priority, weight, port, target)

    def _to_wire(self, file, compress=None, origin=None, canonicalize=False):
        three_ints = struct.pack("!HHH", self.priority, self.weight, self.port)
        file.write(three_ints)
        self.target.to_wire(file, compress, origin, canonicalize)

    @classmethod
    def from_wire_parser(cls, rdclass, rdtype, parser, origin=None):
        (priority, weight, port) = parser.get_struct('!HHH')
        target = parser.get_name(origin)
        return cls(rdclass, rdtype, priority, weight, port, target)
