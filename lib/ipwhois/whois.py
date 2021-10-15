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

import sys
import re
import copy
from datetime import datetime
import logging
from .utils import unique_everseen
from . import (BlacklistError, WhoisLookupError, NetError)

if sys.version_info >= (3, 3):  # pragma: no cover
    from ipaddress import (ip_address,
                           ip_network,
                           summarize_address_range,
                           collapse_addresses)
else:  # pragma: no cover
    from ipaddr import (IPAddress as ip_address,
                        IPNetwork as ip_network,
                        summarize_address_range,
                        collapse_address_list as collapse_addresses)

log = logging.getLogger(__name__)

# Legacy base whois output dictionary.
BASE_NET = {
    'cidr': None,
    'name': None,
    'handle': None,
    'range': None,
    'description': None,
    'country': None,
    'state': None,
    'city': None,
    'address': None,
    'postal_code': None,
    'emails': None,
    'created': None,
    'updated': None
}

RIR_WHOIS = {
    'arin': {
        'server': 'whois.arin.net',
        'fields': {
            'name': r'(NetName):[^\S\n]+(?P<val>.+?)\n',
            'handle': r'(NetHandle):[^\S\n]+(?P<val>.+?)\n',
            'description': r'(OrgName|CustName):[^\S\n]+(?P<val>.+?)'
                    '(?=(\n\\S):?)',
            'country': r'(Country):[^\S\n]+(?P<val>.+?)\n',
            'state': r'(StateProv):[^\S\n]+(?P<val>.+?)\n',
            'city': r'(City):[^\S\n]+(?P<val>.+?)\n',
            'address': r'(Address):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'postal_code': r'(PostalCode):[^\S\n]+(?P<val>.+?)\n',
            'emails': (
                r'.+?:.*?[^\S\n]+(?P<val>[\w\-\.]+?@[\w\-\.]+\.[\w\-]+)('
                '[^\\S\n]+.*?)*?\n'
            ),
            'created': r'(RegDate):[^\S\n]+(?P<val>.+?)\n',
            'updated': r'(Updated):[^\S\n]+(?P<val>.+?)\n',
        },
        'dt_format': '%Y-%m-%d'
    },
    'ripencc': {
        'server': 'whois.ripe.net',
        'fields': {
            'name': r'(netname):[^\S\n]+(?P<val>.+?)\n',
            'handle': r'(nic-hdl):[^\S\n]+(?P<val>.+?)\n',
            'description': r'(descr):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'country': r'(country):[^\S\n]+(?P<val>.+?)\n',
            'address': r'(address):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'emails': (
                r'.+?:.*?[^\S\n]+(?P<val>[\w\-\.]+?@[\w\-\.]+\.[\w\-]+)('
                '[^\\S\n]+.*?)*?\n'
            ),
            'created': (
                r'(created):[^\S\n]+(?P<val>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]'
                '{2}:[0-9]{2}:[0-9]{2}Z).*?\n'
            ),
            'updated': (
                r'(last-modified):[^\S\n]+(?P<val>[0-9]{4}-[0-9]{2}-[0-9]{2}T'
                '[0-9]{2}:[0-9]{2}:[0-9]{2}Z).*?\n'
            )
        },
        'dt_format': '%Y-%m-%dT%H:%M:%SZ'
    },
    'apnic': {
        'server': 'whois.apnic.net',
        'fields': {
            'name': r'(netname):[^\S\n]+(?P<val>.+?)\n',
            'handle': r'(nic-hdl):[^\S\n]+(?P<val>.+?)\n',
            'description': r'(descr):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'country': r'(country):[^\S\n]+(?P<val>.+?)\n',
            'address': r'(address):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'emails': (
                r'.+?:.*?[^\S\n]+(?P<val>[\w\-\.]+?@[\w\-\.]+\.[\w\-]+)('
                '[^\\S\n]+.*?)*?\n'
            ),
            'updated': r'(changed):[^\S\n]+.*(?P<val>[0-9]{8}).*?\n'
        },
        'dt_format': '%Y%m%d'
    },
    'lacnic': {
        'server': 'whois.lacnic.net',
        'fields': {
            'handle': r'(nic-hdl):[^\S\n]+(?P<val>.+?)\n',
            'description': r'(owner):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'country': r'(country):[^\S\n]+(?P<val>.+?)\n',
            'emails': (
                r'.+?:.*?[^\S\n]+(?P<val>[\w\-\.]+?@[\w\-\.]+\.[\w\-]+)('
                '[^\\S\n]+.*?)*?\n'
            ),
            'created': r'(created):[^\S\n]+(?P<val>[0-9]{8}).*?\n',
            'updated': r'(changed):[^\S\n]+(?P<val>[0-9]{8}).*?\n'
        },
        'dt_format': '%Y%m%d'
    },
    'afrinic': {
        'server': 'whois.afrinic.net',
        'fields': {
            'name': r'(netname):[^\S\n]+(?P<val>.+?)\n',
            'handle': r'(nic-hdl):[^\S\n]+(?P<val>.+?)\n',
            'description': r'(descr):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'country': r'(country):[^\S\n]+(?P<val>.+?)\n',
            'address': r'(address):[^\S\n]+(?P<val>.+?)(?=(\n\S):?)',
            'emails': (
                r'.+?:.*?[^\S\n]+(?P<val>[\w\-\.]+?@[\w\-\.]+\.[\w\-]+)('
                '[^\\S\n]+.*?)*?\n'
            ),
        }
    }
}

RWHOIS = {
    'fields': {
        'cidr': r'(network:IP-Network):(?P<val>.+?)\n',
        'name': r'(network:ID):(?P<val>.+?)\n',
        'description': (
            r'(network:(Org-Name|Organization(;I)?)):(?P<val>.+?)\n'
        ),
        'country': r'(network:(Country|Country-Code)):(?P<val>.+?)\n',
        'state': r'(network:State):(?P<val>.+?)\n',
        'city': r'(network:City):(?P<val>.+?)\n',
        'address': r'(network:Street-Address):(?P<val>.+?)\n',
        'postal_code': r'(network:Postal-Code):(?P<val>.+?)\n',
        'emails': (
            r'.+?:.*?[^\S\n]+(?P<val>[\w\-\.]+?@[\w\-\.]+\.[\w\-]+)('
            '[^\\S\n]+.*?)*?\n'
        ),
        'created': r'(network:Created):(?P<val>.+?)\n',
        'updated': r'(network:Updated):(?P<val>.+?)\n'
    }
}

ASN_REFERRALS = {
    'whois://whois.ripe.net': 'ripencc',
    'whois://whois.apnic.net': 'apnic',
    'whois://whois.lacnic.net': 'lacnic',
    'whois://whois.afrinic.net': 'afrinic',
}


class Whois:
    """
    The class for parsing via whois

    Args:
        net (:obj:`ipwhois.net.Net`): The network object.

    Raises:
        NetError: The parameter provided is not an instance of
            ipwhois.net.Net
        IPDefinedError: The address provided is defined (does not need to be
            resolved).
    """

    def __init__(self, net):

        from .net import Net

        # ipwhois.net.Net validation
        if isinstance(net, Net):

            self._net = net

        else:

            raise NetError('The provided net parameter is not an instance of '
                           'ipwhois.net.Net')

    def parse_fields(self, response, fields_dict, net_start=None,
                     net_end=None, dt_format=None, field_list=None):
        """
        The function for parsing whois fields from a data input.

        Args:
            response (:obj:`str`): The response from the whois/rwhois server.
            fields_dict (:obj:`dict`): The mapping of fields to regex search
                values (required).
            net_start (:obj:`int`): The starting point of the network (if
                parsing multiple networks). Defaults to None.
            net_end (:obj:`int`): The ending point of the network (if parsing
                multiple networks). Defaults to None.
            dt_format (:obj:`str`): The format of datetime fields if known.
                Defaults to None.
            field_list (:obj:`list` of :obj:`str`): If provided, fields to
                parse. Defaults to:

                ::

                    ['name', 'handle', 'description', 'country', 'state',
                    'city', 'address', 'postal_code', 'emails', 'created',
                    'updated']

        Returns:
            dict: A dictionary of fields provided in fields_dict, mapping to
                the results of the regex searches.
        """

        ret = {}

        if not field_list:

            field_list = ['name', 'handle', 'description', 'country', 'state',
                          'city', 'address', 'postal_code', 'emails',
                          'created', 'updated']

        generate = ((field, pattern) for (field, pattern) in
                    fields_dict.items() if field in field_list)

        for field, pattern in generate:

            pattern = re.compile(
                str(pattern),
                re.DOTALL
            )

            if net_start is not None:

                match = pattern.finditer(response, net_end, net_start)

            elif net_end is not None:

                match = pattern.finditer(response, net_end)

            else:

                match = pattern.finditer(response)

            values = []
            sub_section_end = None
            for m in match:

                if sub_section_end:

                    if field not in (
                        'emails'
                    ) and (sub_section_end != (m.start() - 1)):

                        break

                try:

                    values.append(m.group('val').strip())

                except IndexError:

                    pass

                sub_section_end = m.end()

            if len(values) > 0:

                value = None
                try:

                    if field == 'country':

                        value = values[0].upper()

                    elif field in ['created', 'updated'] and dt_format:

                        value = datetime.strptime(
                            values[0],
                            str(dt_format)).isoformat('T')

                    elif field in ['emails']:

                        value = list(unique_everseen(values))

                    else:

                        values = unique_everseen(values)
                        value = '\n'.join(values).strip()

                except ValueError as e:

                    log.debug('Whois field parsing failed for {0}: {1}'.format(
                        field, e))
                    pass

                ret[field] = value

        return ret

    def get_nets_arin(self, response):
        """
        The function for parsing network blocks from ARIN whois data.

        Args:
            response (:obj:`str`): The response from the ARIN whois server.

        Returns:
            list of dict: Mapping of networks with start and end positions.

            ::

                [{
                    'cidr' (str) - The network routing block
                    'start' (int) - The starting point of the network
                    'end' (int) - The endpoint point of the network
                }]
        """

        nets = []

        # Find the first NetRange value.
        pattern = re.compile(
            r'^NetRange:[^\S\n]+(.+)$',
            re.MULTILINE
        )
        temp = pattern.search(response)
        net_range = None
        net_range_start = None
        if temp is not None:
            net_range = temp.group(1).strip()
            net_range_start = temp.start()

        # Iterate through all of the networks found, storing the CIDR value
        # and the start and end positions.
        for match in re.finditer(
            r'^CIDR:[^\S\n]+(.+?,[^\S\n].+|.+)$',
            response,
            re.MULTILINE
        ):

            try:

                net = copy.deepcopy(BASE_NET)

                if len(nets) > 0:
                    temp = pattern.search(response, match.start())
                    net_range = None
                    net_range_start = None
                    if temp is not None:
                        net_range = temp.group(1).strip()
                        net_range_start = temp.start()

                if net_range is not None:
                    if net_range_start < match.start() or len(nets) > 0:

                        try:

                            net['range'] = '{0} - {1}'.format(
                                ip_network(net_range)[0].__str__(),
                                ip_network(net_range)[-1].__str__()
                            ) if '/' in net_range else net_range

                        except ValueError:  # pragma: no cover

                            net['range'] = net_range

                net['cidr'] = ', '.join(
                    [ip_network(c.strip()).__str__()
                     for c in match.group(1).split(', ')]
                )
                net['start'] = match.start()
                net['end'] = match.end()
                nets.append(net)

            except ValueError:

                pass

        return nets

    def get_nets_lacnic(self, response):
        """
        The function for parsing network blocks from LACNIC whois data.

        Args:
            response (:obj:`str`): The response from the LACNIC whois server.

        Returns:
            list of dict: Mapping of networks with start and end positions.

            ::

                [{
                    'cidr' (str) - The network routing block
                    'start' (int) - The starting point of the network
                    'end' (int) - The endpoint point of the network
                }]
        """

        nets = []

        # Iterate through all of the networks found, storing the CIDR value
        # and the start and end positions.
        for match in re.finditer(
            r'^(inetnum|inet6num|route):[^\S\n]+(.+?,[^\S\n].+|.+)$',
            response,
            re.MULTILINE
        ):

            try:

                net = copy.deepcopy(BASE_NET)
                net_range = match.group(2).strip()

                try:

                    net['range'] = net['range'] = '{0} - {1}'.format(
                        ip_network(net_range)[0].__str__(),
                        ip_network(net_range)[-1].__str__()
                    ) if '/' in net_range else net_range

                except ValueError:  # pragma: no cover

                    net['range'] = net_range

                temp = []
                for addr in net_range.split(', '):

                    count = addr.count('.')
                    if count != 0 and count < 4:

                        addr_split = addr.strip().split('/')
                        for i in range(count + 1, 4):
                            addr_split[0] += '.0'

                        addr = '/'.join(addr_split)

                    temp.append(ip_network(addr.strip()).__str__())

                net['cidr'] = ', '.join(temp)
                net['start'] = match.start()
                net['end'] = match.end()
                nets.append(net)

            except ValueError:

                pass

        return nets

    def get_nets_other(self, response):
        """
        The function for parsing network blocks from generic whois data.

        Args:
            response (:obj:`str`): The response from the whois/rwhois server.

        Returns:
            list of dict: Mapping of networks with start and end positions.

            ::

                [{
                    'cidr' (str) - The network routing block
                    'start' (int) - The starting point of the network
                    'end' (int) - The endpoint point of the network
                }]
        """

        nets = []

        # Iterate through all of the networks found, storing the CIDR value
        # and the start and end positions.
        for match in re.finditer(
            r'^(inetnum|inet6num|route):[^\S\n]+((.+?)[^\S\n]-[^\S\n](.+)|'
                '.+)$',
            response,
            re.MULTILINE
        ):

            try:

                net = copy.deepcopy(BASE_NET)
                net_range = match.group(2).strip()

                try:

                    net['range'] = net['range'] = '{0} - {1}'.format(
                        ip_network(net_range)[0].__str__(),
                        ip_network(net_range)[-1].__str__()
                    ) if '/' in net_range else net_range

                except ValueError:  # pragma: no cover

                    net['range'] = net_range

                if match.group(3) and match.group(4):

                    addrs = []
                    addrs.extend(summarize_address_range(
                        ip_address(match.group(3).strip()),
                        ip_address(match.group(4).strip())))

                    cidr = ', '.join(
                        [i.__str__() for i in collapse_addresses(addrs)]
                    )

                else:

                    cidr = ip_network(net_range).__str__()

                net['cidr'] = cidr
                net['start'] = match.start()
                net['end'] = match.end()
                nets.append(net)

            except (ValueError, TypeError):

                pass

        return nets

    def lookup(self, inc_raw=False, retry_count=3, response=None,
               get_referral=False, extra_blacklist=None,
               ignore_referral_errors=False, asn_data=None,
               field_list=None, is_offline=False):
        """
        The function for retrieving and parsing whois information for an IP
        address via port 43/tcp (WHOIS).

        Args:
            inc_raw (:obj:`bool`, optional): Whether to include the raw
                results in the returned dictionary. Defaults to False.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            response (:obj:`str`): Optional response object, this bypasses the
                NIR lookup. Required when is_offline=True.
            get_referral (:obj:`bool`): Whether to retrieve referral whois
                information, if available. Defaults to False.
            extra_blacklist (:obj:`list`): Blacklisted whois servers in
                addition to the global BLACKLIST. Defaults to None.
            ignore_referral_errors (:obj:`bool`): Whether to ignore and
                continue when an exception is encountered on referral whois
                lookups. Defaults to False.
            asn_data (:obj:`dict`): Result from
                :obj:`ipwhois.asn.IPASN.lookup` (required).
            field_list (:obj:`list` of :obj:`str`): If provided, fields to
                parse. Defaults to:

                ::

                    ['name', 'handle', 'description', 'country', 'state',
                    'city', 'address', 'postal_code', 'emails', 'created',
                    'updated']

            is_offline (:obj:`bool`): Whether to perform lookups offline. If
                True, response and asn_data must be provided. Primarily used
                for testing. Defaults to False.

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
                }
        """

        # Create the return dictionary.
        results = {
            'query': self._net.address_str,
            'nets': [],
            'raw': None,
            'referral': None,
            'raw_referral': None
        }

        # The referral server and port. Only used if get_referral is True.
        referral_server = None
        referral_port = 0

        # Only fetch the response if we haven't already.
        if response is None or (not is_offline and
                                asn_data['asn_registry'] != 'arin'):

            log.debug('Response not given, perform WHOIS lookup for {0}'
                      .format(self._net.address_str))

            # Retrieve the whois data.
            response = self._net.get_whois(
                asn_registry=asn_data['asn_registry'], retry_count=retry_count,
                extra_blacklist=extra_blacklist
            )

            if get_referral:

                # Search for a referral server.
                for match in re.finditer(
                    r'^ReferralServer:[^\S\n]+(.+:[0-9]+)$',
                    response,
                    re.MULTILINE
                ):

                    try:

                        temp = match.group(1)
                        if 'rwhois://' not in temp:  # pragma: no cover
                            raise ValueError

                        temp = temp.replace('rwhois://', '').split(':')

                        if int(temp[1]) > 65535:  # pragma: no cover
                            raise ValueError

                        referral_server = temp[0]
                        referral_port = int(temp[1])

                    except (ValueError, KeyError):  # pragma: no cover

                        continue

                    break

        # Retrieve the referral whois data.
        if get_referral and referral_server:

            log.debug('Perform referral WHOIS lookup')

            response_ref = None

            try:

                response_ref = self._net.get_whois(
                    asn_registry='', retry_count=retry_count,
                    server=referral_server, port=referral_port,
                    extra_blacklist=extra_blacklist
                )

            except (BlacklistError, WhoisLookupError):

                if ignore_referral_errors:

                    pass

                else:

                    raise

            if response_ref:

                log.debug('Parsing referral WHOIS data')

                if inc_raw:

                    results['raw_referral'] = response_ref

                temp_rnet = self.parse_fields(
                    response_ref,
                    RWHOIS['fields'],
                    field_list=field_list
                )

                # Add the networks to the return dictionary.
                results['referral'] = temp_rnet

        # If inc_raw parameter is True, add the response to return dictionary.
        if inc_raw:

            results['raw'] = response

        nets = []

        if asn_data['asn_registry'] == 'arin':

            nets_response = self.get_nets_arin(response)

        elif asn_data['asn_registry'] == 'lacnic':

            nets_response = self.get_nets_lacnic(response)

        else:

            nets_response = self.get_nets_other(response)

        nets.extend(nets_response)

        # Iterate through all of the network sections and parse out the
        # appropriate fields for each.
        log.debug('Parsing WHOIS data')
        for index, net in enumerate(nets):

            section_end = None
            if index + 1 < len(nets):

                section_end = nets[index + 1]['start']

            try:

                dt_format = RIR_WHOIS[results['asn_registry']]['dt_format']

            except KeyError:

                dt_format = None

            temp_net = self.parse_fields(
                response,
                RIR_WHOIS[asn_data['asn_registry']]['fields'],
                section_end,
                net['end'],
                dt_format,
                field_list
            )

            # Merge the net dictionaries.
            net.update(temp_net)

            # The start and end values are no longer needed.
            del net['start'], net['end']

        # Add the networks to the return dictionary.
        results['nets'] = nets

        return results
