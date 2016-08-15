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

"""IPv6 helper functions."""

import re
import binascii

import dns.exception
import dns.ipv4
from ._compat import xrange, binary_type

_leading_zero = re.compile(b'0+([0-9a-f]+)')

def inet_ntoa(address):
    """Convert a network format IPv6 address into text.

    @param address: the binary address
    @type address: string
    @rtype: string
    @raises ValueError: the address isn't 16 bytes long
    """

    if len(address) != 16:
        raise ValueError("IPv6 addresses are 16 bytes long")
    hex = binascii.hexlify(address)
    chunks = []
    i = 0
    l = len(hex)
    while i < l:
        chunk = hex[i : i + 4]
        # strip leading zeros.  we do this with an re instead of
        # with lstrip() because lstrip() didn't support chars until
        # python 2.2.2
        m = _leading_zero.match(chunk)
        if not m is None:
            chunk = m.group(1)
        chunks.append(chunk)
        i += 4
    #
    # Compress the longest subsequence of 0-value chunks to ::
    #
    best_start = 0
    best_len = 0
    start = -1
    last_was_zero = False
    for i in xrange(8):
        if chunks[i] != b'0':
            if last_was_zero:
                end = i
                current_len = end - start
                if current_len > best_len:
                    best_start = start
                    best_len = current_len
                last_was_zero = False
        elif not last_was_zero:
            start = i
            last_was_zero = True
    if last_was_zero:
        end = 8
        current_len = end - start
        if current_len > best_len:
            best_start = start
            best_len = current_len
    if best_len > 1:
        if best_start == 0 and \
           (best_len == 6 or
            best_len == 5 and chunks[5] == b'ffff'):
            # We have an embedded IPv4 address
            if best_len == 6:
                prefix = b'::'
            else:
                prefix = b'::ffff:'
            hex = prefix + dns.ipv4.inet_ntoa(address[12:])
        else:
            hex = b':'.join(chunks[:best_start]) + b'::' + \
                  b':'.join(chunks[best_start + best_len:])
    else:
        hex = b':'.join(chunks)
    return hex

_v4_ending = re.compile(b'(.*):(\d+\.\d+\.\d+\.\d+)$')
_colon_colon_start = re.compile(b'::.*')
_colon_colon_end = re.compile(b'.*::$')

def inet_aton(text):
    """Convert a text format IPv6 address into network format.

    @param text: the textual address
    @type text: string
    @rtype: string
    @raises dns.exception.SyntaxError: the text was not properly formatted
    """

    #
    # Our aim here is not something fast; we just want something that works.
    #
    if not isinstance(text, binary_type):
        text = text.encode()

    if text == b'::':
        text = b'0::'
    #
    # Get rid of the icky dot-quad syntax if we have it.
    #
    m = _v4_ending.match(text)
    if not m is None:
        b = bytearray(dns.ipv4.inet_aton(m.group(2)))
        text = (u"%s:%02x%02x:%02x%02x" % (m.group(1).decode(), b[0], b[1],
                                           b[2], b[3])).encode()
    #
    # Try to turn '::<whatever>' into ':<whatever>'; if no match try to
    # turn '<whatever>::' into '<whatever>:'
    #
    m = _colon_colon_start.match(text)
    if not m is None:
        text = text[1:]
    else:
        m = _colon_colon_end.match(text)
        if not m is None:
            text = text[:-1]
    #
    # Now canonicalize into 8 chunks of 4 hex digits each
    #
    chunks = text.split(b':')
    l = len(chunks)
    if l > 8:
        raise dns.exception.SyntaxError
    seen_empty = False
    canonical = []
    for c in chunks:
        if c == b'':
            if seen_empty:
                raise dns.exception.SyntaxError
            seen_empty = True
            for i in xrange(0, 8 - l + 1):
                canonical.append(b'0000')
        else:
            lc = len(c)
            if lc > 4:
                raise dns.exception.SyntaxError
            if lc != 4:
                c = (b'0' * (4 - lc)) + c
            canonical.append(c)
    if l < 8 and not seen_empty:
        raise dns.exception.SyntaxError
    text = b''.join(canonical)

    #
    # Finally we can go to binary.
    #
    try:
        return binascii.unhexlify(text)
    except (binascii.Error, TypeError):
        raise dns.exception.SyntaxError

_mapped_prefix = b'\x00' * 10 + b'\xff\xff'

def is_mapped(address):
    return address.startswith(_mapped_prefix)
