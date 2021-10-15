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
import dns.name
import dns.ipv4
import dns.ipv6

class Gateway:
    """A helper class for the IPSECKEY gateway and AMTRELAY relay fields"""
    name = ""

    def __init__(self, type, gateway=None):
        self.type = type
        self.gateway = gateway

    def _invalid_type(self):
        return f"invalid {self.name} type: {self.type}"

    def check(self):
        if self.type == 0:
            if self.gateway not in (".", None):
                raise SyntaxError(f"invalid {self.name} for type 0")
            self.gateway = None
        elif self.type == 1:
            # check that it's OK
            dns.ipv4.inet_aton(self.gateway)
        elif self.type == 2:
            # check that it's OK
            dns.ipv6.inet_aton(self.gateway)
        elif self.type == 3:
            if not isinstance(self.gateway, dns.name.Name):
                raise SyntaxError(f"invalid {self.name}; not a name")
        else:
            raise SyntaxError(self._invalid_type())

    def to_text(self, origin=None, relativize=True):
        if self.type == 0:
            return "."
        elif self.type in (1, 2):
            return self.gateway
        elif self.type == 3:
            return str(self.gateway.choose_relativity(origin, relativize))
        else:
            raise ValueError(self._invalid_type())

    def from_text(self, tok, origin=None, relativize=True, relativize_to=None):
        if self.type in (0, 1, 2):
            return tok.get_string()
        elif self.type == 3:
            return tok.get_name(origin, relativize, relativize_to)
        else:
            raise dns.exception.SyntaxError(self._invalid_type())

    def to_wire(self, file, compress=None, origin=None, canonicalize=False):
        if self.type == 0:
            pass
        elif self.type == 1:
            file.write(dns.ipv4.inet_aton(self.gateway))
        elif self.type == 2:
            file.write(dns.ipv6.inet_aton(self.gateway))
        elif self.type == 3:
            self.gateway.to_wire(file, None, origin, False)
        else:
            raise ValueError(self._invalid_type())

    def from_wire_parser(self, parser, origin=None):
        if self.type == 0:
            return None
        elif self.type == 1:
            return dns.ipv4.inet_ntoa(parser.get_bytes(4))
        elif self.type == 2:
            return dns.ipv6.inet_ntoa(parser.get_bytes(16))
        elif self.type == 3:
            return parser.get_name(origin)
        else:
            raise dns.exception.FormError(self._invalid_type())

class Bitmap:
    """A helper class for the NSEC/NSEC3/CSYNC type bitmaps"""
    type_name = ""

    def __init__(self, windows=None):
        self.windows = windows

    def to_text(self):
        text = ""
        for (window, bitmap) in self.windows:
            bits = []
            for (i, byte) in enumerate(bitmap):
                for j in range(0, 8):
                    if byte & (0x80 >> j):
                        rdtype = window * 256 + i * 8 + j
                        bits.append(dns.rdatatype.to_text(rdtype))
            text += (' ' + ' '.join(bits))
        return text

    def from_text(self, tok):
        rdtypes = []
        while True:
            token = tok.get().unescape()
            if token.is_eol_or_eof():
                break
            rdtype = dns.rdatatype.from_text(token.value)
            if rdtype == 0:
                raise dns.exception.SyntaxError(f"{self.type_name} with bit 0")
            rdtypes.append(rdtype)
        rdtypes.sort()
        window = 0
        octets = 0
        prior_rdtype = 0
        bitmap = bytearray(b'\0' * 32)
        windows = []
        for rdtype in rdtypes:
            if rdtype == prior_rdtype:
                continue
            prior_rdtype = rdtype
            new_window = rdtype // 256
            if new_window != window:
                if octets != 0:
                    windows.append((window, bitmap[0:octets]))
                bitmap = bytearray(b'\0' * 32)
                window = new_window
            offset = rdtype % 256
            byte = offset // 8
            bit = offset % 8
            octets = byte + 1
            bitmap[byte] = bitmap[byte] | (0x80 >> bit)
        if octets != 0:
            windows.append((window, bitmap[0:octets]))
        return windows

    def to_wire(self, file):
        for (window, bitmap) in self.windows:
            file.write(struct.pack('!BB', window, len(bitmap)))
            file.write(bitmap)

    def from_wire_parser(self, parser):
        windows = []
        last_window = -1
        while parser.remaining() > 0:
            window = parser.get_uint8()
            if window <= last_window:
                raise dns.exception.FormError(f"bad {self.type_name} bitmap")
            bitmap = parser.get_counted_bytes()
            if len(bitmap) == 0 or len(bitmap) > 32:
                raise dns.exception.FormError(f"bad {self.type_name} octets")
            windows.append((window, bitmap))
            last_window = window
        return windows
