# Copyright (c) 2013-2024 Philip Hane
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

from . import NetError
from .utils import unique_everseen
import logging
import sys
import re
import copy
from datetime import (datetime, timedelta)

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

# Base NIR whois output dictionary.
BASE_NET = {
    'cidr': None,
    'name': None,
    'handle': None,
    'range': None,
    'country': None,
    'address': None,
    'postal_code': None,
    'nameservers': None,
    'created': None,
    'updated': None,
    'contacts': None
}

# Base NIR whois contact output dictionary.
BASE_CONTACT = {
    'name': None,
    'email': None,
    'reply_email': None,
    'organization': None,
    'division': None,
    'title': None,
    'phone': None,
    'fax': None,
    'updated': None
}

# National Internet Registry
NIR_WHOIS = {
    'jpnic': {
        'country_code': 'JP',
        'url': ('http://whois.nic.ad.jp/cgi-bin/whois_gw?lang=%2Fe&key={0}'
                '&submit=query'),
        'request_type': 'GET',
        'request_headers': {'Accept': 'text/html'},
        'form_data_ip_field': None,
        'fields': {
            'name': r'(\[Organization\])[^\S\n]+(?P<val>.*?)\n',
            'handle': r'(\[Network Name\])[^\S\n]+(?P<val>.*?)\n',
            'created': r'(\[Assigned Date\])[^\S\n]+(?P<val>.*?)\n',
            'updated': r'(\[Last Update\])[^\S\n]+(?P<val>.*?)\n',
            'nameservers': r'(\[Nameserver\])[^\S\n]+(?P<val>.*?)\n',
            'contact_admin': r'(\[Administrative Contact\])[^\S\n]+.+?\>'
                             '(?P<val>.+?)\\<\\/A\\>\n',
            'contact_tech': r'(\[Technical Contact\])[^\S\n]+.+?\>'
                             '(?P<val>.+?)\\<\\/A\\>\n'
        },
        'contact_fields': {
            'name': r'(\[Last, First\])[^\S\n]+(?P<val>.*?)\n',
            'email': r'(\[E-Mail\])[^\S\n]+(?P<val>.*?)\n',
            'reply_email': r'(\[Reply Mail\])[^\S\n]+(?P<val>.*?)\n',
            'organization': r'(\[Organization\])[^\S\n]+(?P<val>.*?)\n',
            'division': r'(\[Division\])[^\S\n]+(?P<val>.*?)\n',
            'title': r'(\[Title\])[^\S\n]+(?P<val>.*?)\n',
            'phone': r'(\[TEL\])[^\S\n]+(?P<val>.*?)\n',
            'fax': r'(\[FAX\])[^\S\n]+(?P<val>.*?)\n',
            'updated': r'(\[Last Update\])[^\S\n]+(?P<val>.*?)\n'
        },
        'dt_format': '%Y/%m/%d %H:%M:%S(JST)',
        'dt_hourdelta': 9,
        'multi_net': False
    },
    'krnic': {
        'country_code': 'KR',
        'url': 'https://xn--c79as89aj0e29b77z.xn--3e0b707e/eng/whois.jsc',
        'request_type': 'POST',
        'request_headers': {
            'Accept': 'text/html',
            'Referer': (
                'https://xn--c79as89aj0e29b77z.xn--3e0b707e/eng/whois.jsp'
            ),
        },
        'form_data_ip_field': 'query',
        'fields': {
            'name': r'(Organization Name)[\s]+\:[^\S\n]+(?P<val>.+?)\n',
            'handle': r'(Service Name|Network Type)[\s]+\:[^\S\n]+(?P<val>.+?)'
                      '\n',
            'address': r'(Address)[\s]+\:[^\S\n]+(?P<val>.+?)\n',
            'postal_code': r'(Zip Code)[\s]+\:[^\S\n]+(?P<val>.+?)\n',
            'created': r'(Registration Date)[\s]+\:[^\S\n]+(?P<val>.+?)\n',
            'contact_admin': r'(id="eng_isp_contact").+?\>(?P<val>.*?)\<'
                              '\\/div\\>\n',
            'contact_tech': r'(id="eng_user_contact").+?\>(?P<val>.*?)\<'
                             '\\/div\\>\n'
        },
        'contact_fields': {
            'name': r'(Name)[^\S\n]+?:[^\S\n]+?(?P<val>.*?)\n',
            'email': r'(E-Mail)[^\S\n]+?:[^\S\n]+?(?P<val>.*?)\n',
            'phone': r'(Phone)[^\S\n]+?:[^\S\n]+?(?P<val>.*?)\n'
        },
        'dt_format': '%Y%m%d',
        'dt_hourdelta': 0,
        'multi_net': True
    }
}


class NIRWhois:
    """
    The class for parsing whois data for NIRs (National Internet Registry).
    JPNIC and KRNIC are currently the only NIRs supported. Output varies
    based on NIR specific whois formatting.

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
                     net_end=None, dt_format=None, field_list=None,
                     hourdelta=0, is_contact=False):
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
                parse. Defaults to :obj:`ipwhois.nir.BASE_NET` if is_contact
                is False. Otherwise, defaults to
                :obj:`ipwhois.nir.BASE_CONTACT`.
            hourdelta (:obj:`int`): The timezone delta for created/updated
                fields. Defaults to 0.
            is_contact (:obj:`bool`): If True, uses contact information
                field parsing. Defaults to False.

        Returns:
            dict: A dictionary of fields provided in fields_dict, mapping to
                the results of the regex searches.
        """

        response = '{0}\n'.format(response)
        if is_contact:

            ret = {}

            if not field_list:

                field_list = list(BASE_CONTACT.keys())

        else:

            ret = {
                'contacts': {'admin': None, 'tech': None},
                'contact_admin': {},
                'contact_tech': {}
            }

            if not field_list:

                field_list = list(BASE_NET.keys())
                field_list.remove('contacts')
                field_list.append('contact_admin')
                field_list.append('contact_tech')

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
            for m in match:

                try:

                    values.append(m.group('val').strip())

                except IndexError:

                    pass

            if len(values) > 0:

                value = None
                try:

                    if field in ['created', 'updated'] and dt_format:

                        try:
                            value = (
                                datetime.strptime(
                                    values[0],
                                    str(dt_format)
                                ) - timedelta(hours=hourdelta)
                            ).isoformat('T')
                        except ValueError:
                            value = (
                                datetime.strptime(
                                    values[0],
                                    '%Y/%m/%d'
                                )
                            ).isoformat('T')

                    elif field in ['nameservers']:

                        value = list(unique_everseen(values))

                    else:

                        values = unique_everseen(values)
                        value = '\n'.join(values)

                except ValueError as e:

                    log.debug('NIR whois field parsing failed for {0}: {1}'
                              ''.format(field, e))
                    pass

                ret[field] = value

        return ret

    def get_nets_jpnic(self, response):
        """
        The function for parsing network blocks from jpnic whois data.

        Args:
            response (:obj:`str`): The response from the jpnic server.

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
                r'^.*?(\[Network Number\])[^\S\n]+.+?>(?P<val>.+?)</A>$',
                response,
                re.MULTILINE
        ):

            try:

                net = copy.deepcopy(BASE_NET)
                tmp = ip_network(match.group(2))

                try:  # pragma: no cover
                    network_address = tmp.network_address
                except AttributeError:  # pragma: no cover
                    network_address = tmp.ip
                    pass

                try:  # pragma: no cover
                    broadcast_address = tmp.broadcast_address
                except AttributeError:  # pragma: no cover
                    broadcast_address = tmp.broadcast
                    pass

                net['range'] = '{0} - {1}'.format(
                    network_address + 1, broadcast_address
                )

                cidr = ip_network(match.group(2).strip()).__str__()

                net['cidr'] = cidr
                net['start'] = match.start()
                net['end'] = match.end()
                nets.append(net)

            except (ValueError, TypeError):

                pass

        return nets

    def get_nets_krnic(self, response):
        """
        The function for parsing network blocks from krnic whois data.

        Args:
            response (:obj:`str`): The response from the krnic server.

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
                r'^(IPv4 Address)[\s]+:[^\S\n]+((.+?)[^\S\n]-[^\S\n](.+?)'
                '[^\\S\n]\\((.+?)\\)|.+)$',
                response,
                re.MULTILINE
        ):

            try:

                net = copy.deepcopy(BASE_NET)
                net['range'] = match.group(2)

                if match.group(3) and match.group(4):

                    addrs = []
                    addrs.extend(summarize_address_range(
                        ip_address(match.group(3).strip()),
                        ip_address(match.group(4).strip())))

                    cidr = ', '.join(
                        [i.__str__() for i in collapse_addresses(addrs)]
                    )

                    net['range'] = '{0} - {1}'.format(
                        match.group(3), match.group(4)
                    )

                else:

                    cidr = ip_network(match.group(2).strip()).__str__()

                net['cidr'] = cidr
                net['start'] = match.start()
                net['end'] = match.end()
                nets.append(net)

            except (ValueError, TypeError):

                pass

        return nets

    def get_contact(self, response=None, nir=None, handle=None,
                    retry_count=3, dt_format=None):
        """
        The function for retrieving and parsing NIR whois data based on
        NIR_WHOIS contact_fields.

        Args:
            response (:obj:`str`): Optional response object, this bypasses the
                lookup.
            nir (:obj:`str`): The NIR to query ('jpnic' or 'krnic'). Required
                if response is None.
            handle (:obj:`str`): For NIRs that have separate contact queries
                (JPNIC), this is the contact handle to use in the query.
                Defaults to None.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            dt_format (:obj:`str`): The format of datetime fields if known.
                Defaults to None.

        Returns:
            dict: Mapping of the fields provided in contact_fields, to their
                parsed results.
        """

        if response or nir == 'krnic':

            contact_response = response

        else:

            # Retrieve the whois data.
            contact_response = self._net.get_http_raw(
                url=str(NIR_WHOIS[nir]['url']).format(handle),
                retry_count=retry_count,
                headers=NIR_WHOIS[nir]['request_headers'],
                request_type=NIR_WHOIS[nir]['request_type']
            )

        return self.parse_fields(
            response=contact_response,
            fields_dict=NIR_WHOIS[nir]['contact_fields'],
            dt_format=dt_format,
            hourdelta=int(NIR_WHOIS[nir]['dt_hourdelta']),
            is_contact=True
        )

    def lookup(self, nir=None, inc_raw=False, retry_count=3, response=None,
               field_list=None, is_offline=False):
        """
        The function for retrieving and parsing NIR whois information for an IP
        address via HTTP (HTML scraping).

        Args:
            nir (:obj:`str`): The NIR to query ('jpnic' or 'krnic'). Required
                if response is None.
            inc_raw (:obj:`bool`, optional): Whether to include the raw
                results in the returned dictionary. Defaults to False.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            response (:obj:`str`): Optional response object, this bypasses the
                NIR lookup. Required when is_offline=True.
            field_list (:obj:`list` of :obj:`str`): If provided, fields to
                parse. Defaults to :obj:`ipwhois.nir.BASE_NET`.
            is_offline (:obj:`bool`): Whether to perform lookups offline. If
                True, response and asn_data must be provided. Primarily used
                for testing.

        Returns:
            dict: The NIR whois results:

            ::

                {
                    'query' (str) - The IP address.
                    'nets' (list of dict) - Network information which consists
                        of the fields listed in the ipwhois.nir.NIR_WHOIS
                        dictionary.
                    'raw' (str) - Raw NIR whois results if the inc_raw
                        parameter is True.
                }
        """

        if nir not in NIR_WHOIS.keys():

            raise KeyError('Invalid arg for nir (National Internet Registry')

        # Create the return dictionary.
        results = {
            'query': self._net.address_str,
            'raw': None
        }

        # Only fetch the response if we haven't already.
        if response is None:

            if is_offline:

                raise KeyError('response argument required when '
                               'is_offline=True')

            log.debug('Response not given, perform WHOIS lookup for {0}'
                      .format(self._net.address_str))

            form_data = None
            if NIR_WHOIS[nir]['form_data_ip_field']:
                form_data = {NIR_WHOIS[nir]['form_data_ip_field']:
                             self._net.address_str}

            # Retrieve the whois data.
            response = self._net.get_http_raw(
                url=str(NIR_WHOIS[nir]['url']).format(self._net.address_str),
                retry_count=retry_count,
                headers=NIR_WHOIS[nir]['request_headers'],
                request_type=NIR_WHOIS[nir]['request_type'],
                form_data=form_data
            )

        # If inc_raw parameter is True, add the response to return dictionary.
        if inc_raw:

            results['raw'] = response

        nets = []
        nets_response = None
        if nir == 'jpnic':

            nets_response = self.get_nets_jpnic(response)

        elif nir == 'krnic':

            nets_response = self.get_nets_krnic(response)

        nets.extend(nets_response)

        global_contacts = {}

        # Iterate through all of the network sections and parse out the
        # appropriate fields for each.
        log.debug('Parsing NIR WHOIS data')
        for index, net in enumerate(nets):

            section_end = None
            if index + 1 < len(nets):
                section_end = nets[index + 1]['start']

            try:

                dt_format = NIR_WHOIS[nir]['dt_format']

            except KeyError:  # pragma: no cover

                dt_format = None

            temp_net = self.parse_fields(
                response=response,
                fields_dict=NIR_WHOIS[nir]['fields'],
                net_start=section_end,
                net_end=net['end'],
                dt_format=dt_format,
                field_list=field_list,
                hourdelta=int(NIR_WHOIS[nir]['dt_hourdelta'])
            )
            temp_net['country'] = NIR_WHOIS[nir]['country_code']
            contacts = {
                'admin': temp_net['contact_admin'],
                'tech': temp_net['contact_tech']
            }

            del (
                temp_net['contact_admin'],
                temp_net['contact_tech']
            )

            if not is_offline:

                for key, val in contacts.items():

                    if len(val) > 0:

                        if isinstance(val, str):

                            val = val.splitlines()

                        for contact in val:

                            if contact in global_contacts.keys():

                                temp_net['contacts'][key] = (
                                    global_contacts[contact]
                                )

                            else:

                                if nir == 'krnic':

                                    tmp_response = contact
                                    tmp_handle = None

                                else:

                                    tmp_response = None
                                    tmp_handle = contact

                                temp_net['contacts'][key] = self.get_contact(
                                    response=tmp_response,
                                    handle=tmp_handle,
                                    nir=nir,
                                    retry_count=retry_count,
                                    dt_format=dt_format
                                )
                                global_contacts[contact] = (
                                    temp_net['contacts'][key]
                                )

            # Merge the net dictionaries.
            net.update(temp_net)

            # The start and end values are no longer needed.
            del net['start'], net['end']

        # Add the networks to the return dictionary.
        results['nets'] = nets

        return results
