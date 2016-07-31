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

import sys
import socket
import dns.resolver
import json
import logging
from time import sleep

# Import the dnspython3 rdtypes to fix the dynamic import problem when frozen.
import dns.rdtypes.ANY.TXT  # @UnusedImport

from .exceptions import (IPDefinedError, ASNRegistryError, ASNLookupError,
                         BlacklistError, WhoisLookupError, HTTPLookupError,
                         HostLookupError, HTTPRateLimitError)
from .whois import RIR_WHOIS
from .utils import ipv4_is_defined, ipv6_is_defined

if sys.version_info >= (3, 3):  # pragma: no cover
    from ipaddress import (ip_address,
                           IPv4Address,
                           IPv6Address,
                           ip_network,
                           summarize_address_range,
                           collapse_addresses)
else:  # pragma: no cover
    from ipaddr import (IPAddress as ip_address,
                        IPv4Address,
                        IPv6Address,
                        IPNetwork as ip_network,
                        summarize_address_range,
                        collapse_address_list as collapse_addresses)

try:  # pragma: no cover
    from urllib.request import (OpenerDirector,
                                ProxyHandler,
                                build_opener,
                                Request,
                                URLError)
    from urllib.parse import urlencode
except ImportError:  # pragma: no cover
    from urllib2 import (OpenerDirector,
                         ProxyHandler,
                         build_opener,
                         Request,
                         URLError)
    from urllib import urlencode

log = logging.getLogger(__name__)

# POSSIBLY UPDATE TO USE RDAP
ARIN = 'http://whois.arin.net/rest/nets;q={0}?showDetails=true&showARIN=true'

# National Internet Registry
NIR = {
    'jpnic': {
        'url': ('http://whois.nic.ad.jp/cgi-bin/whois_gw?lang=%2Fe&key={0}'
                '&submit=query'),
        'request_type': 'GET',
        'request_headers': {'Accept': 'text/html'}
    },
    'krnic': {
        'url': 'http://whois.kisa.or.kr/eng/whois.jsc',
        'request_type': 'POST',
        'request_headers': {'Accept': 'text/html'},
        'form_data_ip_field': 'query'
    }
}

CYMRU_WHOIS = 'whois.cymru.com'

IPV4_DNS_ZONE = '{0}.origin.asn.cymru.com'

IPV6_DNS_ZONE = '{0}.origin6.asn.cymru.com'

BLACKLIST = [
    'root.rwhois.net'
]

ORG_MAP = {
    'ARIN': 'arin',
    'VR-ARIN': 'arin',
    'RIPE': 'ripencc',
    'APNIC': 'apnic',
    'LACNIC': 'lacnic',
    'AFRINIC': 'afrinic',
    'DNIC': 'arin'
}


class Net:
    """
    The class for performing network queries.

    Args:
        address: An IPv4 or IPv6 address in string format.
        timeout: The default timeout for socket connections in seconds.
        proxy_opener: The urllib.request.OpenerDirector request for proxy
            support or None.
        allow_permutations: Use additional methods if DNS lookups to Cymru
            fail.

    Raises:
        IPDefinedError: The address provided is defined (does not need to be
            resolved).
    """

    def __init__(self, address, timeout=5, proxy_opener=None,
                 allow_permutations=True):

        # IPv4Address or IPv6Address
        if isinstance(address, IPv4Address) or isinstance(
                address, IPv6Address):

            self.address = address

        else:

            # Use ipaddress package exception handling.
            self.address = ip_address(address)

        # Default timeout for socket connections.
        self.timeout = timeout

        # Allow other than DNS lookups for ASNs.
        self.allow_permutations = allow_permutations

        self.dns_resolver = dns.resolver.Resolver()
        self.dns_resolver.timeout = timeout
        self.dns_resolver.lifetime = timeout

        # Proxy opener.
        if isinstance(proxy_opener, OpenerDirector):

            self.opener = proxy_opener

        else:

            handler = ProxyHandler()
            self.opener = build_opener(handler)

        # IP address in string format for use in queries.
        self.address_str = self.address.__str__()

        # Determine the IP version, 4 or 6
        self.version = self.address.version

        if self.version == 4:

            # Check if no ASN/whois resolution needs to occur.
            is_defined = ipv4_is_defined(self.address_str)

            if is_defined[0]:

                raise IPDefinedError(
                    'IPv4 address {0} is already defined as {1} via '
                    '{2}.'.format(
                        self.address_str, is_defined[1], is_defined[2]
                    )
                )

            # Reverse the IPv4Address for the DNS ASN query.
            split = self.address_str.split('.')
            split.reverse()
            self.reversed = '.'.join(split)

            self.dns_zone = IPV4_DNS_ZONE.format(self.reversed)

        else:

            # Check if no ASN/whois resolution needs to occur.
            is_defined = ipv6_is_defined(self.address_str)

            if is_defined[0]:

                raise IPDefinedError(
                    'IPv6 address {0} is already defined as {1} via '
                    '{2}.'.format(
                        self.address_str, is_defined[1], is_defined[2]
                    )
                )

            # Explode the IPv6Address to fill in any missing 0's.
            exploded = self.address.exploded

            # Cymru seems to timeout when the IPv6 address has trailing '0000'
            # groups. Remove these groups.
            groups = exploded.split(':')
            for index, value in reversed(list(enumerate(groups))):

                if value == '0000':

                    del groups[index]

                else:

                    break

            exploded = ':'.join(groups)

            # Reverse the IPv6Address for the DNS ASN query.
            val = str(exploded).replace(':', '')
            val = val[::-1]
            self.reversed = '.'.join(val)

            self.dns_zone = IPV6_DNS_ZONE.format(self.reversed)

    def get_asn_dns(self, result=None):
        """
        The function for retrieving ASN information for an IP address from
        Cymru via port 53 (DNS).

        Args:
            result: Optional result object. This bypasses the ASN lookup.

        Returns:
            Dictionary: A dictionary containing the following keys:
                    asn (String) - The Autonomous System Number.
                    asn_date (String) - The ASN Allocation date.
                    asn_registry (String) - The assigned ASN registry.
                    asn_cidr (String) - The assigned ASN CIDR.
                    asn_country_code (String) - The assigned ASN country code.

        Raises:
            ASNRegistryError: The ASN registry is not known.
            ASNLookupError: The ASN lookup failed.
        """

        try:

            if result is None:

                log.debug('ASN query for {0}'.format(self.dns_zone))
                data = self.dns_resolver.query(self.dns_zone, 'TXT')
                temp = str(data[0]).split('|')

            else:

                temp = result

            # Parse out the ASN information.
            ret = {'asn_registry': temp[3].strip(' \n')}

            if ret['asn_registry'] not in RIR_WHOIS.keys():

                raise ASNRegistryError(
                    'ASN registry {0} is not known.'.format(
                        ret['asn_registry'])
                )

            ret['asn'] = temp[0].strip(' "\n')
            ret['asn_cidr'] = temp[1].strip(' \n')
            ret['asn_country_code'] = temp[2].strip(' \n').upper()
            ret['asn_date'] = temp[4].strip(' "\n')

            return ret

        except ASNRegistryError:

            raise

        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers,
                dns.resolver.NoAnswer, dns.exception.Timeout) as e:

            raise ASNLookupError(
                'ASN lookup failed (DNS {0}) for {1}.'.format(
                    e.__class__.__name__, self.address_str)
            )

        except:

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(self.address_str)
            )

    def get_asn_whois(self, retry_count=3, result=None):
        """
        The function for retrieving ASN information for an IP address from
        Cymru via port 43/tcp (WHOIS).

        Args:
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            result: Optional result object. This bypasses the ASN lookup.

        Returns:
            Dictionary: A dictionary containing the following keys:
                    asn (String) - The Autonomous System Number.
                    asn_date (String) - The ASN Allocation date.
                    asn_registry (String) - The assigned ASN registry.
                    asn_cidr (String) - The assigned ASN CIDR.
                    asn_country_code (String) - The assigned ASN country code.

        Raises:
            ASNRegistryError: The ASN registry is not known.
            ASNLookupError: The ASN lookup failed.
        """

        try:

            if result is None:

                # Create the connection for the Cymru whois query.
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.settimeout(self.timeout)
                log.debug('ASN query for {0}'.format(self.address_str))
                conn.connect((CYMRU_WHOIS, 43))

                # Query the Cymru whois server, and store the results.
                conn.send((
                    ' -r -a -c -p -f -o {0}{1}'.format(
                        self.address_str, '\r\n')
                ).encode())

                data = ''
                while True:

                    d = conn.recv(4096).decode()
                    data += d

                    if not d:

                        break

                conn.close()

            else:

                data = result

            # Parse out the ASN information.
            temp = str(data).split('|')

            ret = {'asn_registry': temp[4].strip(' \n')}

            if ret['asn_registry'] not in RIR_WHOIS.keys():

                raise ASNRegistryError(
                    'ASN registry {0} is not known.'.format(
                        ret['asn_registry'])
                )

            ret['asn'] = temp[0].strip(' \n')
            ret['asn_cidr'] = temp[2].strip(' \n')
            ret['asn_country_code'] = temp[3].strip(' \n').upper()
            ret['asn_date'] = temp[5].strip(' \n')

            return ret

        except (socket.timeout, socket.error) as e:  # pragma: no cover

            log.debug('ASN query socket error: {0}'.format(e))
            if retry_count > 0:

                log.debug('ASN query retrying (count: {0})'.format(
                    str(retry_count)))
                return self.get_asn_whois(retry_count - 1)

            else:

                raise ASNLookupError(
                    'ASN lookup failed for {0}.'.format(self.address_str)
                )

        except ASNRegistryError:

            raise

        except:

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(self.address_str)
            )

    def get_asn_http(self, retry_count=3, result=None, extra_org_map=None):
        """
        The function for retrieving ASN information for an IP address from
        Arin via port 80 (HTTP). Currently limited to fetching asn_registry
        through a Arin whois (REST) lookup. The other values are returned as
        None to keep a consistent dict output. This should be used as a last
        chance fallback call behind ASN DNS & ASN Whois lookups.

        Args:
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            result: Optional result object. This bypasses the ASN lookup.
            extra_org_map: Dictionary mapping org handles to RIRs. This is for
                limited cases where ARIN REST (ASN fallback HTTP lookup) does
                not show an RIR as the org handle e.g., DNIC (which is now the
                built in ORG_MAP) e.g., {'DNIC': 'arin'}. Valid RIR values are
                (note the case-sensitive - this is meant to match the REST
                result): 'ARIN', 'RIPE', 'apnic', 'lacnic', 'afrinic'

        Returns:
            Dictionary: A dictionary containing the following keys:
                    asn (String) - None, can't retrieve with this method.
                    asn_date (String) - None, can't retrieve with this method.
                    asn_registry (String) - The assigned ASN registry.
                    asn_cidr (String) - None, can't retrieve with this method.
                    asn_country_code (String) - None, can't retrieve with this
                    method.

        Raises:
            ASNRegistryError: The ASN registry is not known.
            ASNLookupError: The ASN lookup failed.
        """

        # Set the org_map. Map the orgRef handle to an RIR.
        org_map = ORG_MAP.copy()
        try:

            org_map.update(extra_org_map)

        except (TypeError, ValueError, IndexError, KeyError):

            pass

        try:

            if result is None:

                # Lets attempt to get the ASN registry information from
                # ARIN.
                log.debug('ASN query for {0}'.format(self.address_str))
                response = self.get_http_json(
                    url=str(ARIN).format(self.address_str),
                    retry_count=retry_count,
                    headers={'Accept': 'application/json'}
                )

            else:

                response = result

            asn_data = {
                'asn_registry': None,
                'asn': None,
                'asn_cidr': None,
                'asn_country_code': None,
                'asn_date': None
            }

            try:

                net_list = response['nets']['net']

                if not isinstance(net_list, list):
                    net_list = [net_list]

            except (KeyError, TypeError):

                log.debug('No networks found')
                net_list = []

            for n in net_list:

                try:

                    asn_data['asn_registry'] = (
                        org_map[n['orgRef']['@handle'].upper()]
                    )

                except KeyError as e:

                    log.debug('Could not parse ASN registry via HTTP: '
                              '{0}'.format(str(e)))
                    raise ASNRegistryError('ASN registry lookup failed.')

                break

            return asn_data

        except (socket.timeout, socket.error) as e:  # pragma: no cover

            log.debug('ASN query socket error: {0}'.format(e))
            if retry_count > 0:

                log.debug('ASN query retrying (count: {0})'.format(
                    str(retry_count)))
                return self.get_asn_http(retry_count=retry_count-1)

            else:

                raise ASNLookupError(
                    'ASN lookup failed for {0}.'.format(self.address_str)
                )

        except ASNRegistryError:

            raise

        except:

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(self.address_str)
            )

    def get_whois(self, asn_registry='arin', retry_count=3, server=None,
                  port=43, extra_blacklist=None):
        """
        The function for retrieving whois or rwhois information for an IP
        address via any port. Defaults to port 43/tcp (WHOIS).

        Args:
            asn_registry: The NIC to run the query against.
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            server: An optional server to connect to. If provided, asn_registry
                will be ignored.
            port: The network port to connect on.
            extra_blacklist: A list of blacklisted whois servers in addition to
                the global BLACKLIST.

        Returns:
            String: The raw whois data.

        Raises:
            BlacklistError: Raised if the whois server provided is in the
                global BLACKLIST or extra_blacklist.
            WhoisLookupError: The whois lookup failed.
        """

        try:

            extra_bl = extra_blacklist if extra_blacklist else []

            if any(server in srv for srv in (BLACKLIST, extra_bl)):
                raise BlacklistError(
                    'The server {0} is blacklisted.'.format(server)
                )

            if server is None:
                server = RIR_WHOIS[asn_registry]['server']

            # Create the connection for the whois query.
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(self.timeout)
            log.debug('WHOIS query for {0} at {1}:{2}'.format(
                self.address_str, server, port))
            conn.connect((server, port))

            # Prep the query.
            query = self.address_str + '\r\n'
            if asn_registry == 'arin':

                query = 'n + {0}'.format(query)

            # Query the whois server, and store the results.
            conn.send(query.encode())

            response = ''
            while True:

                d = conn.recv(4096).decode('ascii', 'ignore')

                response += d

                if not d:

                    break

            conn.close()

            if 'Query rate limit exceeded' in response:  # pragma: no cover

                log.debug('WHOIS query rate limit exceeded. Waiting...')
                sleep(1)
                return self.get_whois(
                    asn_registry=asn_registry, retry_count=retry_count-1,
                    server=server, port=port, extra_blacklist=extra_blacklist
                )

            elif ('error 501' in response or 'error 230' in response
                  ):  # pragma: no cover

                log.debug('WHOIS query error: {0}'.format(response))
                raise ValueError

            return str(response)

        except (socket.timeout, socket.error) as e:

            log.debug('WHOIS query socket error: {0}'.format(e))
            if retry_count > 0:

                log.debug('WHOIS query retrying (count: {0})'.format(
                    str(retry_count)))
                return self.get_whois(
                    asn_registry=asn_registry, retry_count=retry_count-1,
                    server=server, port=port, extra_blacklist=extra_blacklist
                )

            else:

                raise WhoisLookupError(
                    'WHOIS lookup failed for {0}.'.format(self.address_str)
                )

        except BlacklistError:

            raise

        except:  # pragma: no cover

            raise WhoisLookupError(
                'WHOIS lookup failed for {0}.'.format(self.address_str)
            )

    def get_http_json(self, url=None, retry_count=3, rate_limit_timeout=120,
                      headers=None):
        """
        The function for retrieving a json result via HTTP.

        Args:
            url: The URL to retrieve.
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            rate_limit_timeout: The number of seconds to wait before retrying
                when a rate limit notice is returned via rdap+json.
            headers: The HTTP headers dictionary. The Accept header defaults
                to 'application/rdap+json'.

        Returns:
            Dictionary: The data in json format.

        Raises:
            HTTPLookupError: The HTTP lookup failed.
            HTTPRateLimitError: The HTTP request rate limited and retries
                were exhausted.
        """

        if headers is None:
            headers = {'Accept': 'application/rdap+json'}

        try:

            # Create the connection for the whois query.
            log.debug('HTTP query for {0} at {1}'.format(
                self.address_str, url))
            conn = Request(url, headers=headers)
            data = self.opener.open(conn, timeout=self.timeout)
            try:
                d = json.loads(data.readall().decode('utf-8', 'ignore'))
            except AttributeError:  # pragma: no cover
                d = json.loads(data.read().decode('utf-8', 'ignore'))

            try:
                # Tests written but commented out. I do not want to send a
                # flood of requests on every test.
                for tmp in d['notices']:  # pragma: no cover
                    if tmp['title'] == 'Rate Limit Notice':
                        log.debug('RDAP query rate limit exceeded.')

                        if retry_count > 0:
                            log.debug('Waiting {0} seconds...'.format(
                                str(rate_limit_timeout)))

                            sleep(rate_limit_timeout)
                            return self.get_http_json(
                                url=url, retry_count=retry_count-1,
                                rate_limit_timeout=rate_limit_timeout,
                                headers=headers
                            )
                        else:
                            raise HTTPRateLimitError(
                                'HTTP lookup failed for {0}. Rate limit '
                                'exceeded, wait and try again (possibly a '
                                'temporary block).'.format(url))

            except (KeyError, IndexError):  # pragma: no cover

                pass

            return d

        except (URLError, socket.timeout, socket.error) as e:

            # Check needed for Python 2.6, also why URLError is caught.
            try:  # pragma: no cover
                if not isinstance(e.reason, (socket.timeout, socket.error)):
                    raise HTTPLookupError('HTTP lookup failed for {0}.'
                                          ''.format(url))
            except AttributeError:  # pragma: no cover

                pass

            log.debug('HTTP query socket error: {0}'.format(e))
            if retry_count > 0:

                log.debug('HTTP query retrying (count: {0})'.format(
                    str(retry_count)))

                return self.get_http_json(
                    url=url, retry_count=retry_count-1,
                    rate_limit_timeout=rate_limit_timeout, headers=headers
                )

            else:

                raise HTTPLookupError('HTTP lookup failed for {0}.'.format(
                    url))

        except (HTTPLookupError, HTTPRateLimitError) as e:  # pragma: no cover

            raise e

        except:  # pragma: no cover

            raise HTTPLookupError('HTTP lookup failed for {0}.'.format(url))

    def get_host(self, retry_count=3):
        """
        The function for retrieving host information for an IP address.

        Args:
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.

        Returns:
            Tuple: hostname, aliaslist, ipaddrlist

        Raises:
            HostLookupError: The host lookup failed.
        """

        try:

            default_timeout_set = False
            if not socket.getdefaulttimeout():

                socket.setdefaulttimeout(self.timeout)
                default_timeout_set = True

            log.debug('Host query for {0}'.format(self.address_str))
            ret = socket.gethostbyaddr(self.address_str)

            if default_timeout_set:  # pragma: no cover

                socket.setdefaulttimeout(None)

            return ret

        except (socket.timeout, socket.error) as e:

            log.debug('Host query socket error: {0}'.format(e))
            if retry_count > 0:

                log.debug('Host query retrying (count: {0})'.format(
                    str(retry_count)))

                return self.get_host(retry_count - 1)

            else:

                raise HostLookupError(
                    'Host lookup failed for {0}.'.format(self.address_str)
                )

        except:  # pragma: no cover

            raise HostLookupError(
                'Host lookup failed for {0}.'.format(self.address_str)
            )

    def lookup_asn(self, retry_count=3, asn_alts=None, extra_org_map=None):
        """
        The wrapper function for retrieving and parsing ASN information for an
        IP address.

        Args:
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
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
            Tuple:

            :Dictionary: Result from get_asn_dns() or get_asn_whois().
            :Dictionary: The response returned by get_asn_dns() or
                get_asn_whois().

        Raises:
            ASNRegistryError: ASN registry does not match.
            HTTPLookupError: The HTTP lookup failed.
        """

        lookups = asn_alts if asn_alts is not None else ['whois', 'http']

        # Initialize the response.
        response = None

        # Attempt to resolve ASN info via Cymru. DNS is faster, try that first.
        try:

            self.dns_resolver.lifetime = self.dns_resolver.timeout * (
                retry_count and retry_count or 1)
            asn_data = self.get_asn_dns()

        except (ASNLookupError, ASNRegistryError) as e:

            if not self.allow_permutations:

                raise ASNRegistryError('ASN registry lookup failed. '
                                       'Permutations not allowed.')

            try:
                if 'whois' in lookups:

                    log.debug('ASN DNS lookup failed, trying ASN WHOIS: '
                              '{0}'.format(e))
                    asn_data = self.get_asn_whois(retry_count)

                else:

                    raise ASNLookupError

            except (ASNLookupError, ASNRegistryError):  # pragma: no cover

                if 'http' in lookups:

                    # Lets attempt to get the ASN registry information from
                    # ARIN.
                    log.debug('ASN WHOIS lookup failed, trying ASN via HTTP')
                    try:

                        asn_data = self.get_asn_http(
                            retry_count=retry_count,
                            extra_org_map=extra_org_map
                        )

                    except ASNRegistryError:

                        raise ASNRegistryError('ASN registry lookup failed.')

                    except ASNLookupError:

                        raise HTTPLookupError('ASN HTTP lookup failed.')

                else:

                    raise ASNRegistryError('ASN registry lookup failed.')

        return asn_data, response

    def get_http_raw(self, url=None, retry_count=3, headers=None,
                     request_type='GET', form_data=None):
        """
        The function for retrieving a raw HTML result via HTTP.

        Args:
            url: The URL to retrieve.
            retry_count: The number of times to retry in case socket errors,
                timeouts, connection resets, etc. are encountered.
            headers: The HTTP headers dictionary. The Accept header defaults
                to 'application/rdap+json'.
            request_type: 'GET' or 'POST'
            form_data: Dictionary of form POST data

        Returns:
            String: The raw data.

        Raises:
            HTTPLookupError: The HTTP lookup failed.
        """

        if headers is None:
            headers = {'Accept': 'text/html'}

        if form_data:
            form_data = urlencode(form_data)
            try:
                form_data = bytes(form_data, encoding='ascii')
            except TypeError:  # pragma: no cover
                pass

        try:

            # Create the connection for the HTTP query.
            log.debug('HTTP query for {0} at {1}'.format(
                self.address_str, url))
            try:
                conn = Request(url=url, data=form_data, headers=headers,
                               method=request_type)
            except TypeError:  # pragma: no cover
                conn = Request(url=url, data=form_data, headers=headers)
            data = self.opener.open(conn, timeout=self.timeout)

            try:
                d = data.readall().decode('ascii', 'ignore')
            except AttributeError:  # pragma: no cover
                d = data.read().decode('ascii', 'ignore')

            return str(d)

        except (URLError, socket.timeout, socket.error) as e:

            # Check needed for Python 2.6, also why URLError is caught.
            try:  # pragma: no cover
                if not isinstance(e.reason, (socket.timeout, socket.error)):
                    raise HTTPLookupError('HTTP lookup failed for {0}.'
                                          ''.format(url))
            except AttributeError:  # pragma: no cover

                pass

            log.debug('HTTP query socket error: {0}'.format(e))
            if retry_count > 0:

                log.debug('HTTP query retrying (count: {0})'.format(
                    str(retry_count)))

                return self.get_http_raw(
                    url=url, retry_count=retry_count - 1, headers=headers,
                    request_type=request_type, form_data=form_data
                )

            else:

                raise HTTPLookupError('HTTP lookup failed for {0}.'.format(
                    url))

        except HTTPLookupError as e:  # pragma: no cover

            raise e

        except Exception:  # pragma: no cover

            raise HTTPLookupError('HTTP lookup failed for {0}.'.format(url))
