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

from . import Net
from .asn import IPASN
from .nir import NIRWhois
import logging

log = logging.getLogger(__name__)


class IPWhois:
    """
    The wrapper class for performing whois/RDAP lookups and parsing for
    IPv4 and IPv6 addresses.

    Args:
        address (:obj:`str`/:obj:`int`/:obj:`IPv4Address`/:obj:`IPv6Address`):
            An IPv4 or IPv6 address
        timeout (:obj:`int`): The default timeout for socket connections in
            seconds. Defaults to 5.
        proxy_opener (:obj:`urllib.request.OpenerDirector`): The request for
            proxy support. Defaults to None.
    """

    def __init__(self, address, timeout=5, proxy_opener=None):

        self.net = Net(
            address=address, timeout=timeout, proxy_opener=proxy_opener
        )
        self.ipasn = IPASN(self.net)

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

    def lookup_whois(self, inc_raw=False, retry_count=3, get_referral=False,
                     extra_blacklist=None, ignore_referral_errors=False,
                     field_list=None, extra_org_map=None,
                     inc_nir=True, nir_field_list=None, asn_methods=None,
                     get_asn_description=True):
        """
        The function for retrieving and parsing whois information for an IP
        address via port 43 (WHOIS).

        Args:
            inc_raw (:obj:`bool`): Whether to include the raw whois results in
                the returned dictionary. Defaults to False.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            get_referral (:obj:`bool`): Whether to retrieve referral whois
                information, if available. Defaults to False.
            extra_blacklist (:obj:`list`): Blacklisted whois servers in
                addition to the global BLACKLIST. Defaults to None.
            ignore_referral_errors (:obj:`bool`): Whether to ignore and
                continue when an exception is encountered on referral whois
                lookups. Defaults to False.
            field_list (:obj:`list`): If provided, a list of fields to parse:
                ['name', 'handle', 'description', 'country', 'state', 'city',
                'address', 'postal_code', 'emails', 'created', 'updated']
                If None, defaults to all.
            extra_org_map (:obj:`dict`): Dictionary mapping org handles to
                RIRs. This is for limited cases where ARIN REST (ASN fallback
                HTTP lookup) does not show an RIR as the org handle e.g., DNIC
                (which is now the built in ORG_MAP) e.g., {'DNIC': 'arin'}.
                Valid RIR values are (note the case-sensitive - this is meant
                to match the REST result):
                'ARIN', 'RIPE', 'apnic', 'lacnic', 'afrinic'
                Defaults to None.
            inc_nir (:obj:`bool`): Whether to retrieve NIR (National Internet
                Registry) information, if registry is JPNIC (Japan) or KRNIC
                (Korea). If True, extra network requests will be required.
                If False, the information returned for JP or KR IPs is
                severely restricted. Defaults to True.
            nir_field_list (:obj:`list`): If provided and inc_nir, a list of
                fields to parse:
                ['name', 'handle', 'country', 'address', 'postal_code',
                'nameservers', 'created', 'updated', 'contacts']
                If None, defaults to all.
            asn_methods (:obj:`list`): ASN lookup types to attempt, in order.
                If None, defaults to all ['dns', 'whois', 'http'].
            get_asn_description (:obj:`bool`): Whether to run an additional
                query when pulling ASN information via dns, in order to get
                the ASN description. Defaults to True.

        Returns:
            dict: The IP whois lookup results

            ::

                {
                    'query' (str) - The IP address
                    'asn' (str) - The Autonomous System Number
                    'asn_date' (str) - The ASN Allocation date
                    'asn_registry' (str) - The assigned ASN registry
                    'asn_cidr' (str) - The assigned ASN CIDR
                    'asn_country_code' (str) - The assigned ASN country code
                    'asn_description' (str) - The ASN description
                    'nets' (list) - Dictionaries containing network
                        information which consists of the fields listed in the
                        ipwhois.whois.RIR_WHOIS dictionary.
                    'raw' (str) - Raw whois results if the inc_raw parameter
                        is True.
                    'referral' (dict) - Referral whois information if
                        get_referral is True and the server is not blacklisted.
                        Consists of fields listed in the ipwhois.whois.RWHOIS
                        dictionary.
                    'raw_referral' (str) - Raw referral whois results if the
                        inc_raw parameter is True.
                    'nir' (dict) - ipwhois.nir.NIRWhois() results if inc_nir
                        is True.
                }
        """

        from .whois import Whois

        # Create the return dictionary.
        results = {'nir': None}

        # Retrieve the ASN information.
        log.debug('ASN lookup for {0}'.format(self.address_str))

        asn_data = self.ipasn.lookup(
            inc_raw=inc_raw, retry_count=retry_count,
            extra_org_map=extra_org_map, asn_methods=asn_methods,
            get_asn_description=get_asn_description
        )

        # Add the ASN information to the return dictionary.
        results.update(asn_data)

        # Retrieve the whois data and parse.
        whois = Whois(self.net)
        log.debug('WHOIS lookup for {0}'.format(self.address_str))
        whois_data = whois.lookup(
            inc_raw=inc_raw, retry_count=retry_count, response=None,
            get_referral=get_referral, extra_blacklist=extra_blacklist,
            ignore_referral_errors=ignore_referral_errors, asn_data=asn_data,
            field_list=field_list
        )

        # Add the WHOIS information to the return dictionary.
        results.update(whois_data)

        if inc_nir:

            nir = None
            if 'JP' == asn_data['asn_country_code']:
                nir = 'jpnic'
            elif 'KR' == asn_data['asn_country_code']:
                nir = 'krnic'

            if nir:

                nir_whois = NIRWhois(self.net)
                nir_data = nir_whois.lookup(
                    nir=nir, inc_raw=inc_raw, retry_count=retry_count,
                    response=None,
                    field_list=nir_field_list, is_offline=False
                )

                # Add the NIR information to the return dictionary.
                results['nir'] = nir_data

        return results

    def lookup_rdap(self, inc_raw=False, retry_count=3, depth=0,
                    excluded_entities=None, bootstrap=False,
                    rate_limit_timeout=120, extra_org_map=None,
                    inc_nir=True, nir_field_list=None, asn_methods=None,
                    get_asn_description=True, root_ent_check=True):
        """
        The function for retrieving and parsing whois information for an IP
        address via HTTP (RDAP).

        **This is now the recommended method, as RDAP contains much better
        information to parse.**

        Args:
            inc_raw (:obj:`bool`): Whether to include the raw whois results in
                the returned dictionary. Defaults to False.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            depth (:obj:`int`): How many levels deep to run queries when
                additional referenced objects are found. Defaults to 0.
            excluded_entities (:obj:`list`): Entity handles to not perform
                lookups. Defaults to None.
            bootstrap (:obj:`bool`): If True, performs lookups via ARIN
                bootstrap rather than lookups based on ASN data. ASN lookups
                are not performed and no output for any of the asn* fields is
                provided. Defaults to False.
            rate_limit_timeout (:obj:`int`): The number of seconds to wait
                before retrying when a rate limit notice is returned via
                rdap+json. Defaults to 120.
            extra_org_map (:obj:`dict`): Dictionary mapping org handles to
                RIRs. This is for limited cases where ARIN REST (ASN fallback
                HTTP lookup) does not show an RIR as the org handle e.g., DNIC
                (which is now the built in ORG_MAP) e.g., {'DNIC': 'arin'}.
                Valid RIR values are (note the case-sensitive - this is meant
                to match the REST result):
                'ARIN', 'RIPE', 'apnic', 'lacnic', 'afrinic'
                Defaults to None.
            inc_nir (:obj:`bool`): Whether to retrieve NIR (National Internet
                Registry) information, if registry is JPNIC (Japan) or KRNIC
                (Korea). If True, extra network requests will be required.
                If False, the information returned for JP or KR IPs is
                severely restricted. Defaults to True.
            nir_field_list (:obj:`list`): If provided and inc_nir, a list of
                fields to parse:
                ['name', 'handle', 'country', 'address', 'postal_code',
                'nameservers', 'created', 'updated', 'contacts']
                If None, defaults to all.
            asn_methods (:obj:`list`): ASN lookup types to attempt, in order.
                If None, defaults to all ['dns', 'whois', 'http'].
            get_asn_description (:obj:`bool`): Whether to run an additional
                query when pulling ASN information via dns, in order to get
                the ASN description. Defaults to True.
            root_ent_check (:obj:`bool`): If True, will perform
                additional RDAP HTTP queries for missing entity data at the
                root level. Defaults to True.

        Returns:
            dict: The IP RDAP lookup results

            ::

                {
                    'query' (str) - The IP address
                    'asn' (str) - The Autonomous System Number
                    'asn_date' (str) - The ASN Allocation date
                    'asn_registry' (str) - The assigned ASN registry
                    'asn_cidr' (str) - The assigned ASN CIDR
                    'asn_country_code' (str) - The assigned ASN country code
                    'asn_description' (str) - The ASN description
                    'entities' (list) - Entity handles referred by the top
                        level query.
                    'network' (dict) - Network information which consists of
                        the fields listed in the ipwhois.rdap._RDAPNetwork
                        dict.
                    'objects' (dict) - Mapping of entity handle->entity dict
                        which consists of the fields listed in the
                        ipwhois.rdap._RDAPEntity dict. The raw result is
                        included for each object if the inc_raw parameter
                        is True.
                    'raw' (dict) - Whois results in json format if the inc_raw
                        parameter is True.
                    'nir' (dict) - ipwhois.nir.NIRWhois results if inc_nir is
                        True.
                }
        """

        from .rdap import RDAP

        # Create the return dictionary.
        results = {'nir': None}

        asn_data = None
        response = None
        if not bootstrap:

            # Retrieve the ASN information.
            log.debug('ASN lookup for {0}'.format(self.address_str))
            asn_data = self.ipasn.lookup(
                inc_raw=inc_raw, retry_count=retry_count,
                extra_org_map=extra_org_map, asn_methods=asn_methods,
                get_asn_description=get_asn_description
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
            rate_limit_timeout=rate_limit_timeout,
            root_ent_check=root_ent_check
        )

        # Add the RDAP information to the return dictionary.
        results.update(rdap_data)

        if inc_nir:

            nir = None
            if 'JP' == asn_data['asn_country_code']:
                nir = 'jpnic'
            elif 'KR' == asn_data['asn_country_code']:
                nir = 'krnic'

            if nir:
                nir_whois = NIRWhois(self.net)
                nir_data = nir_whois.lookup(
                    nir=nir, inc_raw=inc_raw, retry_count=retry_count,
                    response=None,
                    field_list=nir_field_list, is_offline=False
                )

                # Add the NIR information to the return dictionary.
                results['nir'] = nir_data

        return results
