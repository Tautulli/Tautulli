# Copyright (c) 2013, 2014, 2015, 2016 Philip Hane
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

from . import Net
import logging

log = logging.getLogger(__name__)


class IPWhois:
    """
    The wrapper class for performing whois/RDAP lookups and parsing for
    IPv4 and IPv6 addresses.

    Args:
        address: An IPv4 or IPv6 address as a string, integer, IPv4Address, or
            IPv6Address.
        timeout: The default timeout for socket connections in seconds.
        proxy_opener: The urllib.request.OpenerDirector request for proxy
            support or None.
        allow_permutations: allow net.Net() to use additional methods if DNS
            lookups to Cymru fail.
    """

    def __init__(self, address, timeout=5, proxy_opener=None,
                 allow_permutations=True):

        self.net = Net(
            address=address, timeout=timeout, proxy_opener=proxy_opener,
            allow_permutations=allow_permutations
        )

        self.address = self.net.address
        self.timeout = self.net.timeout
        self.address_str = self.net.address_str
        self.version = self.net.version
        self.reversed = self.net.reversed
        self.dns_zone = self.net.dns_zone

    def __repr__(self):

        return 'IPWhois({0}, {1}, {2})'.format(
            self.address_str, str(self.timeout), repr(self.net.opener)
        )

    def lookup(self, *args, **kwargs):
        """
        Temporary wrapper for legacy whois lookups (moved to
        IPWhois.lookup_whois()). This will be removed in a future
        release (TBD).
        """

        from warnings import warn
        warn("IPWhois.lookup() has been deprecated and will be removed. "
             "You should now use IPWhois.lookup_whois() for legacy whois "
             "lookups.")
        return self.lookup_whois(*args, **kwargs)

    def lookup_whois(self, inc_raw=False, retry_count=3, get_referral=False,
                     extra_blacklist=None, ignore_referral_errors=False,
                     field_list=None, asn_alts=None, extra_org_map=None):
        """
        The function for retrieving and parsing whois information for an IP
        address via port 43 (WHOIS).

        Args:
            inc_raw: Boolean for whether to include the raw whois results in
                the returned dictionary.
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            get_referral: Boolean for whether to retrieve referral whois
                information, if available.
            extra_blacklist: A list of blacklisted whois servers in addition to
                the global BLACKLIST.
            ignore_referral_errors: Boolean for whether to ignore and continue
                when an exception is encountered on referral whois lookups.
            field_list: If provided, a list of fields to parse:
                ['name', 'handle', 'description', 'country', 'state', 'city',
                'address', 'postal_code', 'emails', 'created', 'updated']
            asn_alts: Array of additional lookup types to attempt if the
                ASN dns lookup fails. Allow permutations must be enabled.
                Defaults to all ['whois', 'http'].
            extra_org_map: Dictionary mapping org handles to RIRs. This is for
                limited cases where ARIN REST (ASN fallback HTTP lookup) does
                not show an RIR as the org handle e.g., DNIC (which is now the
                built in ORG_MAP) e.g., {'DNIC': 'arin'}. Valid RIR values are
                (note the case-sensitive - this is meant to match the REST
                result): 'ARIN', 'RIPE', 'apnic', 'lacnic', 'afrinic'

        Returns:
            Dictionary:

            :query: The IP address (String)
            :asn: The Autonomous System Number (String)
            :asn_date: The ASN Allocation date (String)
            :asn_registry: The assigned ASN registry (String)
            :asn_cidr: The assigned ASN CIDR (String)
            :asn_country_code: The assigned ASN country code (String)
            :nets: Dictionaries containing network information which consists
                of the fields listed in the ipwhois.whois.RIR_WHOIS dictionary.
                (List)
            :raw: Raw whois results if the inc_raw parameter is True. (String)
            :referral: Dictionary of referral whois information if get_referral
                is True and the server isn't blacklisted. Consists of fields
                listed in the ipwhois.whois.RWHOIS dictionary.
            :raw_referral: Raw referral whois results if the inc_raw parameter
                is True. (String)
        """

        from .whois import Whois

        # Create the return dictionary.
        results = {}

        # Retrieve the ASN information.
        log.debug('ASN lookup for {0}'.format(self.address_str))
        asn_data, response = self.net.lookup_asn(
            retry_count=retry_count, asn_alts=asn_alts,
            extra_org_map=extra_org_map
        )

        # Add the ASN information to the return dictionary.
        results.update(asn_data)

        # Retrieve the whois data and parse.
        whois = Whois(self.net)
        log.debug('WHOIS lookup for {0}'.format(self.address_str))
        whois_data = whois.lookup(
            inc_raw=inc_raw, retry_count=retry_count, response=response,
            get_referral=get_referral, extra_blacklist=extra_blacklist,
            ignore_referral_errors=ignore_referral_errors, asn_data=asn_data,
            field_list=field_list
        )

        # Add the RDAP information to the return dictionary.
        results.update(whois_data)

        return results

    def lookup_rdap(self, inc_raw=False, retry_count=3, depth=0,
                    excluded_entities=None, bootstrap=False,
                    rate_limit_timeout=120, asn_alts=None, extra_org_map=None):
        """
        The function for retrieving and parsing whois information for an IP
        address via HTTP (RDAP).

        **This is now the recommended method, as RDAP contains much better
        information to parse.**

        Args:
            inc_raw: Boolean for whether to include the raw whois results in
                the returned dictionary.
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            depth: How many levels deep to run queries when additional
                referenced objects are found.
            excluded_entities: A list of entity handles to not perform lookups.
            bootstrap: If True, performs lookups via ARIN bootstrap rather
                than lookups based on ASN data. ASN lookups are not performed
                and no output for any of the asn* fields is provided.
            rate_limit_timeout: The number of seconds to wait before retrying
                when a rate limit notice is returned via rdap+json.
            asn_alts: Array of additional lookup types to attempt if the
                ASN dns lookup fails. Allow permutations must be enabled.
                Defaults to all ['whois', 'http'].
            extra_org_map: Dictionary mapping org handles to RIRs. This is for
                limited cases where ARIN REST (ASN fallback HTTP lookup) does
                not show an RIR as the org handle e.g., DNIC (which is now the
                built in ORG_MAP) e.g., {'DNIC': 'arin'}. Valid RIR values are
                (note the case-sensitive - this is meant to match the REST
                result): 'ARIN', 'RIPE', 'apnic', 'lacnic', 'afrinic'

        Returns:
            Dictionary:

            :query: The IP address (String)
            :asn: The Autonomous System Number (String)
            :asn_date: The ASN Allocation date (String)
            :asn_registry: The assigned ASN registry (String)
            :asn_cidr: The assigned ASN CIDR (String)
            :asn_country_code: The assigned ASN country code (String)
            :entities: List of entity handles referred by the top level query.
            :network: Dictionary containing network information which consists
                of the fields listed in the ipwhois.rdap._RDAPNetwork dict.
            :objects: Dictionary of (entity handle: entity dict) which consists
                of the fields listed in the ipwhois.rdap._RDAPEntity dict.
            :raw: (Dictionary) - Whois results in json format if the inc_raw
                parameter is True.
        """

        from .rdap import RDAP

        # Create the return dictionary.
        results = {}

        asn_data = None
        response = None
        if not bootstrap:

            # Retrieve the ASN information.
            log.debug('ASN lookup for {0}'.format(self.address_str))
            asn_data, asn_response = self.net.lookup_asn(
                retry_count=retry_count, asn_alts=asn_alts,
                extra_org_map=extra_org_map
            )

            # Add the ASN information to the return dictionary.
            results.update(asn_data)

        # Retrieve the RDAP data and parse.
        rdap = RDAP(self.net)
        log.debug('RDAP lookup for {0}'.format(self.address_str))
        rdap_data = rdap.lookup(
            inc_raw=inc_raw, retry_count=retry_count, asn_data=asn_data,
            depth=depth, excluded_entities=excluded_entities,
            response=response, bootstrap=bootstrap,
            rate_limit_timeout=rate_limit_timeout
        )

        # Add the RDAP information to the return dictionary.
        results.update(rdap_data)

        return results
