# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# Copyright (C) 2001-2017 Nominum, Inc.
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

"""DNS Result Codes."""

import dns.enum
import dns.exception

class Rcode(dns.enum.IntEnum):
    #: No error
    NOERROR = 0
    #: Format error
    FORMERR = 1
    #: Server failure
    SERVFAIL = 2
    #: Name does not exist ("Name Error" in RFC 1025 terminology).
    NXDOMAIN = 3
    #: Not implemented
    NOTIMP = 4
    #: Refused
    REFUSED = 5
    #: Name exists.
    YXDOMAIN = 6
    #: RRset exists.
    YXRRSET = 7
    #: RRset does not exist.
    NXRRSET = 8
    #: Not authoritative.
    NOTAUTH = 9
    #: Name not in zone.
    NOTZONE = 10
    #: DSO-TYPE Not Implemented
    DSOTYPENI = 11
    #: Bad EDNS version.
    BADVERS = 16
    #: TSIG Signature Failure
    BADSIG = 16
    #: Key not recognized.
    BADKEY = 17
    #: Signature out of time window.
    BADTIME = 18
    #: Bad TKEY Mode.
    BADMODE = 19
    #: Duplicate key name.
    BADNAME = 20
    #: Algorithm not supported.
    BADALG = 21
    #: Bad Truncation
    BADTRUNC = 22
    #: Bad/missing Server Cookie
    BADCOOKIE = 23

    @classmethod
    def _maximum(cls):
        return 4095

    @classmethod
    def _unknown_exception_class(cls):
        return UnknownRcode


class UnknownRcode(dns.exception.DNSException):
    """A DNS rcode is unknown."""


def from_text(text):
    """Convert text into an rcode.

    *text*, a ``str``, the textual rcode or an integer in textual form.

    Raises ``dns.rcode.UnknownRcode`` if the rcode mnemonic is unknown.

    Returns an ``int``.
    """

    return Rcode.from_text(text)


def from_flags(flags, ednsflags):
    """Return the rcode value encoded by flags and ednsflags.

    *flags*, an ``int``, the DNS flags field.

    *ednsflags*, an ``int``, the EDNS flags field.

    Raises ``ValueError`` if rcode is < 0 or > 4095

    Returns an ``int``.
    """

    value = (flags & 0x000f) | ((ednsflags >> 20) & 0xff0)
    return value


def to_flags(value):
    """Return a (flags, ednsflags) tuple which encodes the rcode.

    *value*, an ``int``, the rcode.

    Raises ``ValueError`` if rcode is < 0 or > 4095.

    Returns an ``(int, int)`` tuple.
    """

    if value < 0 or value > 4095:
        raise ValueError('rcode must be >= 0 and <= 4095')
    v = value & 0xf
    ev = (value & 0xff0) << 20
    return (v, ev)


def to_text(value, tsig=False):
    """Convert rcode into text.

    *value*, an ``int``, the rcode.

    Raises ``ValueError`` if rcode is < 0 or > 4095.

    Returns a ``str``.
    """

    if tsig and value == Rcode.BADVERS:
        return 'BADSIG'
    return Rcode.to_text(value)

### BEGIN generated Rcode constants

NOERROR = Rcode.NOERROR
FORMERR = Rcode.FORMERR
SERVFAIL = Rcode.SERVFAIL
NXDOMAIN = Rcode.NXDOMAIN
NOTIMP = Rcode.NOTIMP
REFUSED = Rcode.REFUSED
YXDOMAIN = Rcode.YXDOMAIN
YXRRSET = Rcode.YXRRSET
NXRRSET = Rcode.NXRRSET
NOTAUTH = Rcode.NOTAUTH
NOTZONE = Rcode.NOTZONE
DSOTYPENI = Rcode.DSOTYPENI
BADVERS = Rcode.BADVERS
BADSIG = Rcode.BADSIG
BADKEY = Rcode.BADKEY
BADTIME = Rcode.BADTIME
BADMODE = Rcode.BADMODE
BADNAME = Rcode.BADNAME
BADALG = Rcode.BADALG
BADTRUNC = Rcode.BADTRUNC
BADCOOKIE = Rcode.BADCOOKIE

### END generated Rcode constants
