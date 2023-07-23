# Copyright (c) 2013-2020 Philip Hane
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


class BaseIpwhoisException(Exception):
    """
    Base exception for all the ipwhois custom ones.
    """


class NetError(BaseIpwhoisException):
    """
    An Exception for when a parameter provided is not an instance of
    ipwhois.net.Net.
    """


class IPDefinedError(BaseIpwhoisException):
    """
    An Exception for when the IP is defined (does not need to be resolved).
    """


class ASNLookupError(BaseIpwhoisException):
    """
    An Exception for when the ASN lookup failed.
    """


class ASNRegistryError(BaseIpwhoisException):
    """
    An Exception for when the ASN registry does not match one of the five
    expected values (arin, ripencc, apnic, lacnic, afrinic).
    """


class ASNParseError(BaseIpwhoisException):
    """
    An Exception for when the ASN parsing failed.
    """


class ASNOriginLookupError(BaseIpwhoisException):
    """
    An Exception for when the ASN origin lookup failed.
    """


class HostLookupError(BaseIpwhoisException):
    """
    An Exception for when the host lookup failed.
    """


class BlacklistError(BaseIpwhoisException):
    """
    An Exception for when the server is in a blacklist.
    """


class WhoisLookupError(BaseIpwhoisException):
    """
    An Exception for when the whois lookup failed.
    """


class WhoisRateLimitError(BaseIpwhoisException):
    """
    An Exception for when Whois queries exceed the NIC's request limit and have
    exhausted all retries.
    """


class HTTPLookupError(BaseIpwhoisException):
    """
    An Exception for when the RDAP lookup failed.
    """


class HTTPRateLimitError(BaseIpwhoisException):
    """
    An Exception for when HTTP queries exceed the NIC's request limit and have
    exhausted all retries.
    """


class InvalidEntityContactObject(BaseIpwhoisException):
    """
    An Exception for when JSON output is not an RDAP entity contact information
    object:
    https://tools.ietf.org/html/rfc7483#section-5.4
    """


class InvalidNetworkObject(BaseIpwhoisException):
    """
    An Exception for when JSON output is not an RDAP network object:
    https://tools.ietf.org/html/rfc7483#section-5.4
    """


class InvalidEntityObject(BaseIpwhoisException):
    """
    An Exception for when JSON output is not an RDAP entity object:
    https://tools.ietf.org/html/rfc7483#section-5.1
    """
