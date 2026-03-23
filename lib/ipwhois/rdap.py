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

from . import (Net, NetError, InvalidEntityContactObject, InvalidNetworkObject,
               InvalidEntityObject, HTTPLookupError)
from .utils import ipv4_lstrip_zeros, calculate_cidr, unique_everseen
from .net import ip_address
import logging
import json
from collections import namedtuple

log = logging.getLogger(__name__)

BOOTSTRAP_URL = 'https://rdap-bootstrap.arin.net/bootstrap'

RIR_RDAP = {
    'arin': {
        'ip_url': 'https://rdap.arin.net/registry/ip/{0}',
        'entity_url': 'https://rdap.arin.net/registry/entity/{0}'
    },
    'ripencc': {
        'ip_url': 'https://rdap.db.ripe.net/ip/{0}',
        'entity_url': 'https://rdap.db.ripe.net/entity/{0}'
    },
    'apnic': {
        'ip_url': 'https://rdap.apnic.net/ip/{0}',
        'entity_url': 'https://rdap.apnic.net/entity/{0}'
    },
    'lacnic': {
        'ip_url': 'https://rdap.lacnic.net/rdap/ip/{0}',
        'entity_url': 'https://rdap.lacnic.net/rdap/entity/{0}'
    },
    'afrinic': {
        'ip_url': 'https://rdap.afrinic.net/rdap/ip/{0}',
        'entity_url': 'https://rdap.afrinic.net/rdap/entity/{0}'
    }
}


class _RDAPContact:
    """
    The class for parsing RDAP entity contact information objects:
    https://tools.ietf.org/html/rfc7483#section-5.1
    https://tools.ietf.org/html/rfc7095

    Args:
        vcard (:obj:`list` of :obj:`list`): The vcard list from an RDAP IP
            address query.

    Raises:
        InvalidEntityContactObject: vcard is not an RDAP entity contact
            information object.
    """

    def __init__(self, vcard):

        if not isinstance(vcard, list):

            raise InvalidEntityContactObject('JSON result must be a list.')

        self.vcard = vcard
        self.vars = {
            'name': None,
            'kind': None,
            'address': None,
            'phone': None,
            'email': None,
            'role': None,
            'title': None
        }

    def _parse_name(self, val):
        """
        The function for parsing the vcard name.

        Args:
            val (:obj:`list`): The value to parse.
        """

        self.vars['name'] = val[3].strip()

    def _parse_kind(self, val):
        """
        The function for parsing the vcard kind.

        Args:
            val (:obj:`list`): The value to parse.
        """

        self.vars['kind'] = val[3].strip()

    def _parse_address(self, val):
        """
        The function for parsing the vcard address.

        Args:
            val (:obj:`list`): The value to parse.
        """

        ret = {
            'type': None,
            'value': None
        }

        try:

            ret['type'] = val[1]['type']

        except (KeyError, ValueError, TypeError):

                pass

        try:

            ret['value'] = val[1]['label']

        except (KeyError, ValueError, TypeError):

            ret['value'] = '\n'.join(val[3]).strip()

        try:

            self.vars['address'].append(ret)

        except AttributeError:

            self.vars['address'] = []
            self.vars['address'].append(ret)

    def _parse_phone(self, val):
        """
        The function for parsing the vcard phone numbers.

        Args:
            val (:obj:`list`): The value to parse.
        """

        ret = {
            'type': None,
            'value': None
        }

        try:

            ret['type'] = val[1]['type']

        except (IndexError, KeyError, ValueError, TypeError):

                pass

        ret['value'] = val[3].strip()

        try:

            self.vars['phone'].append(ret)

        except AttributeError:

            self.vars['phone'] = []
            self.vars['phone'].append(ret)

    def _parse_email(self, val):
        """
        The function for parsing the vcard email addresses.

        Args:
            val (:obj:`list`): The value to parse.
        """

        ret = {
            'type': None,
            'value': None
        }

        try:

            ret['type'] = val[1]['type']

        except (KeyError, ValueError, TypeError):

                pass

        ret['value'] = val[3].strip()

        try:

            self.vars['email'].append(ret)

        except AttributeError:

            self.vars['email'] = []
            self.vars['email'].append(ret)

    def _parse_role(self, val):
        """
        The function for parsing the vcard role.

        Args:
            val (:obj:`list`): The value to parse.
        """

        self.vars['role'] = val[3].strip()

    def _parse_title(self, val):
        """
        The function for parsing the vcard title.

        Args:
            val (:obj:`list`): The value to parse.
        """

        self.vars['title'] = val[3].strip()

    def parse(self):
        """
        The function for parsing the vcard to the vars dictionary.
        """

        keys = {
            'fn': self._parse_name,
            'kind': self._parse_kind,
            'adr': self._parse_address,
            'tel': self._parse_phone,
            'email': self._parse_email,
            'role': self._parse_role,
            'title': self._parse_title
        }

        for val in self.vcard:

            try:

                parser = keys.get(val[0])
                parser(val)

            except (KeyError, ValueError, TypeError):

                pass


class _RDAPCommon:
    """
    The common class for parsing RDAP objects:
    https://tools.ietf.org/html/rfc7483#section-5

    Args:
        json_result (:obj:`dict`): The JSON response from an RDAP query.

    Raises:
        ValueError: vcard is not a known RDAP object.
    """

    def __init__(self, json_result):

        if not isinstance(json_result, dict):

            raise ValueError

        self.json = json_result
        self.vars = {
            'handle': None,
            'status': None,
            'remarks': None,
            'notices': None,
            'links': None,
            'events': None,
            'raw': None
        }

    def summarize_links(self, links_json):
        """
        The function for summarizing RDAP links in to a unique list.
        https://tools.ietf.org/html/rfc7483#section-4.2

        Args:
            links_json (:obj:`dict`): A json mapping of links from RDAP
                results.

        Returns:
            list of str: Unique RDAP links.
        """

        ret = []

        for link_dict in links_json:

            ret.append(link_dict['href'])

        ret = list(unique_everseen(ret))

        return ret

    def summarize_notices(self, notices_json):
        """
        The function for summarizing RDAP notices in to a unique list.
        https://tools.ietf.org/html/rfc7483#section-4.3

        Args:
            notices_json (:obj:`dict`): A json mapping of notices from RDAP
                results.

        Returns:
            list of dict: Unique RDAP notices information:

            ::

                [{
                    'title' (str) - The title/header of the notice.
                    'description' (str) - The description/body of the notice.
                    'links' (list) - Unique links returned by
                        :obj:`ipwhois.rdap._RDAPCommon.summarize_links()`.
               }]
        """

        ret = []

        for notices_dict in notices_json:

            tmp = {
                'title': None,
                'description': None,
                'links': None
            }

            try:

                tmp['title'] = notices_dict['title']

            except (KeyError, ValueError, TypeError):

                pass

            try:

                tmp['description'] = '\n'.join(notices_dict['description'])

            except (KeyError, ValueError, TypeError):

                pass

            try:

                tmp['links'] = self.summarize_links(notices_dict['links'])

            except (KeyError, ValueError, TypeError):

                pass

            if any(tmp.values()):

                ret.append(tmp)

        return ret

    def summarize_events(self, events_json):
        """
        The function for summarizing RDAP events in to a unique list.
        https://tools.ietf.org/html/rfc7483#section-4.5

        Args:
            events_json (:obj:`dict`): A json mapping of events from RDAP
                results.

        Returns:
            list of dict: Unique RDAP events information:

            ::

                [{
                    'action' (str) - The reason for an event.
                    'timestamp' (str) - The timestamp for when an event
                        occured.
                    'actor' (str) - The identifier for an event initiator.
               }]
        """

        ret = []

        for event in events_json:

            event_dict = {
                'action': event['eventAction'],
                'timestamp': event['eventDate'],
                'actor': None
            }

            try:

                event_dict['actor'] = event['eventActor']

            except (KeyError, ValueError, TypeError):

                pass

            ret.append(event_dict)

        return ret

    def _parse(self):
        """
        The function for parsing the JSON response to the vars dictionary.
        """

        try:

            self.vars['status'] = self.json['status']

        except (KeyError, ValueError, TypeError):

            pass

        for v in ['remarks', 'notices']:

            try:

                self.vars[v] = self.summarize_notices(self.json[v])

            except (KeyError, ValueError, TypeError):

                pass

        try:

            self.vars['links'] = self.summarize_links(self.json['links'])

        except (KeyError, ValueError, TypeError):

            pass

        try:

            self.vars['events'] = self.summarize_events(self.json['events'])

        except (KeyError, ValueError, TypeError):

            pass


class _RDAPNetwork(_RDAPCommon):
    """
    The class for parsing RDAP network objects:
    https://tools.ietf.org/html/rfc7483#section-5.4

    Args:
        json_result (:obj:`dict`): The JSON response from an RDAP IP address
            query.

    Raises:
        InvalidNetworkObject: json_result is not an RDAP network object.
    """

    def __init__(self, json_result):

        try:

            _RDAPCommon.__init__(self, json_result)

        except ValueError:

            raise InvalidNetworkObject('JSON result must be a dict.')

        self.vars.update({
            'start_address': None,
            'end_address': None,
            'cidr': None,
            'ip_version': None,
            'type': None,
            'name': None,
            'country': None,
            'parent_handle': None
        })

    def parse(self):
        """
        The function for parsing the JSON response to the vars dictionary.
        """

        try:

            self.vars['handle'] = self.json['handle'].strip()

        except (KeyError, ValueError):

            log.debug('Handle missing, json_output: {0}'.format(json.dumps(
                self.json)))
            raise InvalidNetworkObject('Handle is missing for RDAP network '
                                       'object')

        try:

            self.vars['ip_version'] = self.json['ipVersion'].strip()

            # RDAP IPv4 addresses are padded to 3 digits per octet, remove
            # the leading 0's.
            if self.vars['ip_version'] == 'v4':

                self.vars['start_address'] = ip_address(
                    ipv4_lstrip_zeros(self.json['startAddress'])
                ).__str__()

                self.vars['end_address'] = ip_address(
                    ipv4_lstrip_zeros(self.json['endAddress'])
                ).__str__()

            # No bugs found for IPv6 yet, proceed as normal.
            else:

                self.vars['start_address'] = self.json['startAddress'].strip()
                self.vars['end_address'] = self.json['endAddress'].strip()

        except (KeyError, ValueError, TypeError):

            log.debug('IP address data incomplete. Data parsed prior to '
                      'exception: {0}'.format(json.dumps(self.vars)))
            raise InvalidNetworkObject('IP address data is missing for RDAP '
                                       'network object.')

        try:

            self.vars['cidr'] = ', '.join(calculate_cidr(
                self.vars['start_address'], self.vars['end_address']
            ))

        except (KeyError, ValueError, TypeError, AttributeError) as \
                e:  # pragma: no cover

            log.debug('CIDR calculation failed: {0}'.format(e))
            pass

        for v in ['name', 'type', 'country']:

            try:

                self.vars[v] = self.json[v].strip()

            except (KeyError, ValueError, AttributeError):

                pass

        try:

            self.vars['parent_handle'] = self.json['parentHandle'].strip()

        except (KeyError, ValueError):

            pass

        self._parse()


class _RDAPEntity(_RDAPCommon):
    """
    The class for parsing RDAP entity objects:
    https://tools.ietf.org/html/rfc7483#section-5.1

    Args:
        json_result (:obj:`dict`): The JSON response from an RDAP query.

    Raises:
        InvalidEntityObject: json_result is not an RDAP entity object.
    """

    def __init__(self, json_result):

        try:

            _RDAPCommon.__init__(self, json_result)

        except ValueError:

            raise InvalidEntityObject('JSON result must be a dict.')

        self.vars.update({
            'roles': None,
            'contact': None,
            'events_actor': None,
            'entities': []
        })

    def parse(self):
        """
        The function for parsing the JSON response to the vars dictionary.
        """

        try:

            self.vars['handle'] = self.json['handle'].strip()

        except (KeyError, ValueError, TypeError):

            raise InvalidEntityObject('Handle is missing for RDAP entity')

        for v in ['roles', 'country']:

            try:

                self.vars[v] = self.json[v]

            except (KeyError, ValueError):

                pass

        try:

            vcard = self.json['vcardArray'][1]
            c = _RDAPContact(vcard)
            c.parse()

            self.vars['contact'] = c.vars

        except (KeyError, ValueError, TypeError):

            pass

        try:

            self.vars['events_actor'] = self.summarize_events(
                self.json['asEventActor'])

        except (KeyError, ValueError, TypeError):

            pass

        self.vars['entities'] = []
        try:

            for ent in self.json['entities']:

                if ent['handle'] not in self.vars['entities']:

                    self.vars['entities'].append(ent['handle'])

        except (KeyError, ValueError, TypeError):

            pass

        if not self.vars['entities']:

            self.vars['entities'] = None

        self._parse()


class RDAP:
    """
    The class for parsing IP address whois information via RDAP:
    https://tools.ietf.org/html/rfc7483
    https://www.arin.net/resources/rdap.html

    Args:
        net (:obj:`ipwhois.net.Net`): The network object.

    Raises:
        NetError: The parameter provided is not an instance of
            ipwhois.net.Net
        IPDefinedError: The address provided is defined (does not need to be
            resolved).
    """

    def __init__(self, net):

        if isinstance(net, Net):

            self._net = net

        else:

            raise NetError('The provided net parameter is not an instance of '
                           'ipwhois.net.Net')

    def _get_entity(self, entity=None, roles=None, inc_raw=False, retry_count=3,
                    asn_data=None, bootstrap=False, rate_limit_timeout=120):
        """
        The function for retrieving and parsing information for an entity via
        RDAP (HTTP).

        Args:
            entity (:obj:`str`): The entity name to lookup.
            roles (:obj:`dict`): The mapping of entity handles to roles.
            inc_raw (:obj:`bool`, optional): Whether to include the raw
                results in the returned dictionary. Defaults to False.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            asn_data (:obj:`dict`): Result from
                :obj:`ipwhois.asn.IPASN.lookup`. Optional if the bootstrap
                parameter is True.
            bootstrap (:obj:`bool`): If True, performs lookups via ARIN
                bootstrap rather than lookups based on ASN data. Defaults to
                False.
            rate_limit_timeout (:obj:`int`): The number of seconds to wait
                before retrying when a rate limit notice is returned via
                rdap+json. Defaults to 120.

        Returns:
            namedtuple:

            :result (dict): Consists of the fields listed in the
                ipwhois.rdap._RDAPEntity dict. The raw result is included for
                each object if the inc_raw parameter is True.
            :roles (dict): The mapping of entity handles to roles.
        """

        result = {}

        if bootstrap:
            entity_url = '{0}/entity/{1}'.format(
                BOOTSTRAP_URL, entity)
        else:
            tmp_reg = asn_data['asn_registry']
            entity_url = RIR_RDAP[tmp_reg]['entity_url']
            entity_url = str(entity_url).format(entity)

        try:

            # RDAP entity query
            response = self._net.get_http_json(
                url=entity_url, retry_count=retry_count,
                rate_limit_timeout=rate_limit_timeout
            )

            # Parse the entity
            result_ent = _RDAPEntity(response)
            result_ent.parse()
            result = result_ent.vars

            result['roles'] = None
            try:

                result['roles'] = roles[entity]

            except KeyError:  # pragma: no cover

                pass

            try:

                for tmp in response['entities']:

                    if tmp['handle'] not in roles:
                        roles[tmp['handle']] = tmp['roles']

            except (IndexError, KeyError):

                pass

            if inc_raw:
                result['raw'] = response

        except (HTTPLookupError, InvalidEntityObject):

            pass

        return_tuple = namedtuple('return_tuple', ['result', 'roles'])
        return return_tuple(result, roles)

    def lookup(self, inc_raw=False, retry_count=3, asn_data=None, depth=0,
               excluded_entities=None, response=None, bootstrap=False,
               rate_limit_timeout=120, root_ent_check=True):
        """
        The function for retrieving and parsing information for an IP
        address via RDAP (HTTP).

        Args:
            inc_raw (:obj:`bool`, optional): Whether to include the raw
                results in the returned dictionary. Defaults to False.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            asn_data (:obj:`dict`): Result from
                :obj:`ipwhois.asn.IPASN.lookup`. Optional if the bootstrap
                parameter is True.
            depth (:obj:`int`): How many levels deep to run queries when
                additional referenced objects are found. Defaults to 0.
            excluded_entities (:obj:`list`): Entity handles to not perform
                lookups. Defaults to None.
            response (:obj:`str`): Optional response object, this bypasses the
                RDAP lookup.
            bootstrap (:obj:`bool`): If True, performs lookups via ARIN
                bootstrap rather than lookups based on ASN data. Defaults to
                False.
            rate_limit_timeout (:obj:`int`): The number of seconds to wait
                before retrying when a rate limit notice is returned via
                rdap+json. Defaults to 120.
            root_ent_check (:obj:`bool`): If True, will perform
                additional RDAP HTTP queries for missing entity data at the
                root level. Defaults to True.

        Returns:
            dict: The IP RDAP lookup results

            ::

                {
                    'query' (str) - The IP address
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
                }
        """

        if not excluded_entities:

            excluded_entities = []

        # Create the return dictionary.
        results = {
            'query': self._net.address_str,
            'network': None,
            'entities': None,
            'objects': None,
            'raw': None
        }

        if bootstrap:

            ip_url = '{0}/ip/{1}'.format(BOOTSTRAP_URL, self._net.address_str)

        else:

            ip_url = str(RIR_RDAP[asn_data['asn_registry']]['ip_url']).format(
                self._net.address_str)

        # Only fetch the response if we haven't already.
        if response is None:

            log.debug('Response not given, perform RDAP lookup for {0}'.format(
                ip_url))

            # Retrieve the whois data.
            response = self._net.get_http_json(
                url=ip_url, retry_count=retry_count,
                rate_limit_timeout=rate_limit_timeout
            )

        if inc_raw:

            results['raw'] = response

        log.debug('Parsing RDAP network object')
        result_net = _RDAPNetwork(response)
        result_net.parse()
        results['network'] = result_net.vars
        results['entities'] = []
        results['objects'] = {}
        roles = {}

        # Iterate through and parse the root level entities.
        log.debug('Parsing RDAP root level entities')
        try:

            for ent in response['entities']:

                if ent['handle'] not in [results['entities'],
                                         excluded_entities]:

                    if 'vcardArray' not in ent and root_ent_check:
                        entity_object, roles = self._get_entity(
                            entity=ent['handle'],
                            roles=roles,
                            inc_raw=inc_raw,
                            retry_count=retry_count,
                            asn_data=asn_data,
                            bootstrap=bootstrap,
                            rate_limit_timeout=rate_limit_timeout
                        )
                        results['objects'][ent['handle']] = entity_object

                    else:
                        result_ent = _RDAPEntity(ent)
                        result_ent.parse()

                        results['objects'][ent['handle']] = result_ent.vars

                    results['entities'].append(ent['handle'])

                    try:

                        for tmp in ent['entities']:

                            roles[tmp['handle']] = tmp['roles']

                    except KeyError:

                        pass

        except KeyError:

            pass

        # Iterate through to the defined depth, retrieving and parsing all
        # unique entities.
        temp_objects = results['objects']

        if depth > 0 and len(temp_objects) > 0:

            log.debug('Parsing RDAP sub-entities to depth: {0}'.format(str(
                depth)))

        while depth > 0 and len(temp_objects) > 0:

            new_objects = {}
            for obj in temp_objects.values():

                try:

                    for ent in obj['entities']:

                        if ent not in (list(results['objects'].keys()) +
                                       list(new_objects.keys()) +
                                       excluded_entities):

                            entity_object, roles = self._get_entity(
                                entity=ent,
                                roles=roles,
                                inc_raw=inc_raw,
                                retry_count=retry_count,
                                asn_data=asn_data,
                                bootstrap=bootstrap,
                                rate_limit_timeout=rate_limit_timeout
                            )
                            new_objects[ent] = entity_object

                except (KeyError, TypeError):

                    pass

            # Update the result objects, and set the new temp object list to
            # iterate for the next depth of entities.
            results['objects'].update(new_objects)
            temp_objects = new_objects
            depth -= 1

        return results
