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
import dns.name
import dns.rdata


def _write_string(file, s):
    l = len(s)
    assert l < 256
    file.write(struct.pack('!B', l))
    file.write(s)


def _sanitize(value):
    if isinstance(value, str):
        return value.encode()
    return value


class NAPTR(dns.rdata.Rdata):

    """NAPTR record"""

    # see: RFC 3403

    __slots__ = ['order', 'preference', 'flags', 'service', 'regexp',
                 'replacement']

    def __init__(self, rdclass, rdtype, order, preference, flags, service,
                 regexp, replacement):
        super().__init__(rdclass, rdtype)
        object.__setattr__(self, 'flags', _sanitize(flags))
        object.__setattr__(self, 'service', _sanitize(service))
        object.__setattr__(self, 'regexp', _sanitize(regexp))
        object.__setattr__(self, 'order', order)
        object.__setattr__(self, 'preference', preference)
        object.__setattr__(self, 'replacement', replacement)

    def to_text(self, origin=None, relativize=True, **kw):
        replacement = self.replacement.choose_relativity(origin, relativize)
        return '%d %d "%s" "%s" "%s" %s' % \
               (self.order, self.preference,
                dns.rdata._escapify(self.flags),
                dns.rdata._escapify(self.service),
                dns.rdata._escapify(self.regexp),
                replacement)

    @classmethod
    def from_text(cls, rdclass, rdtype, tok, origin=None, relativize=True,
                  relativize_to=None):
        order = tok.get_uint16()
        preference = tok.get_uint16()
        flags = tok.get_string()
        service = tok.get_string()
        regexp = tok.get_string()
        replacement = tok.get_name(origin, relativize, relativize_to)
        tok.get_eol()
        return cls(rdclass, rdtype, order, preference, flags, service,
                   regexp, replacement)

    def _to_wire(self, file, compress=None, origin=None, canonicalize=False):
        two_ints = struct.pack("!HH", self.order, self.preference)
        file.write(two_ints)
        _write_string(file, self.flags)
        _write_string(file, self.service)
        _write_string(file, self.regexp)
        self.replacement.to_wire(file, compress, origin, canonicalize)

    @classmethod
    def from_wire_parser(cls, rdclass, rdtype, parser, origin=None):
        (order, preference) = parser.get_struct('!HH')
        strings = []
        for i in range(3):
            s = parser.get_counted_bytes()
            strings.append(s)
        replacement = parser.get_name(origin)
        return cls(rdclass, rdtype, order, preference, strings[0], strings[1],
                   strings[2], replacement)
