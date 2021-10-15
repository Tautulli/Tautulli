# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2010, 2011 Nominum, Inc.
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
import binascii

import dns.dnssec
import dns.rdata
import dns.rdatatype


class DSBase(dns.rdata.Rdata):

    """Base class for rdata that is like a DS record"""

    __slots__ = ['key_tag', 'algorithm', 'digest_type', 'digest']

    def __init__(self, rdclass, rdtype, key_tag, algorithm, digest_type,
                 digest):
        super().__init__(rdclass, rdtype)
        object.__setattr__(self, 'key_tag', key_tag)
        object.__setattr__(self, 'algorithm', algorithm)
        object.__setattr__(self, 'digest_type', digest_type)
        object.__setattr__(self, 'digest', digest)

    def to_text(self, origin=None, relativize=True, **kw):
        return '%d %d %d %s' % (self.key_tag, self.algorithm,
                                self.digest_type,
                                dns.rdata._hexify(self.digest,
                                                  chunksize=128))

    @classmethod
    def from_text(cls, rdclass, rdtype, tok, origin=None, relativize=True,
                  relativize_to=None):
        key_tag = tok.get_uint16()
        algorithm = dns.dnssec.algorithm_from_text(tok.get_string())
        digest_type = tok.get_uint8()
        digest = tok.concatenate_remaining_identifiers().encode()
        digest = binascii.unhexlify(digest)
        return cls(rdclass, rdtype, key_tag, algorithm, digest_type,
                   digest)

    def _to_wire(self, file, compress=None, origin=None, canonicalize=False):
        header = struct.pack("!HBB", self.key_tag, self.algorithm,
                             self.digest_type)
        file.write(header)
        file.write(self.digest)

    @classmethod
    def from_wire_parser(cls, rdclass, rdtype, parser, origin=None):
        header = parser.get_struct("!HBB")
        digest = parser.get_remaining()
        return cls(rdclass, rdtype, header[0], header[1], header[2], digest)
