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

import sys
import socket
import dns.resolver
import json
from collections import namedtuple
import logging
from time import sleep

# Import the dnspython rdtypes to fix the dynamic import problem when frozen.
import dns.rdtypes.ANY.TXT  # @UnusedImport

from .exceptions import (IPDefinedError, ASNLookupError, BlacklistError,
                         WhoisLookupError, HTTPLookupError, HostLookupError,
                         HTTPRateLimitError, WhoisRateLimitError)
from .whois import RIR_WHOIS
from .asn import ASN_ORIGIN_WHOIS
from .utils import ipv4_is_defined, ipv6_is_defined

if sys.version_info >= (3, 3):  # pragma: no cover
    from ipaddress import (ip_address,
                           IPv4Address,
                           IPv6Address)
else:  # pragma: no cover
    from ipaddr import (IPAddress as ip_address,
                        IPv4Address,
                        IPv6Address)

try:  # pragma: no cover
    from urllib.request import (OpenerDirector,
                                ProxyHandler,
                                build_opener,
                                Request,
                                URLError,
                                HTTPError)
    from urllib.parse import urlencode
except ImportError:  # pragma: no cover
    from urllib2 import (OpenerDirector,
                         ProxyHandler,
                         build_opener,
                         Request,
                         URLError,
                         HTTPError)
    from urllib import urlencode

log = logging.getLogger(__name__)

# POSSIBLY UPDATE TO USE RDAP
ARIN = 'https://whois.arin.net/rest/nets;q={0}?showDetails=true&showARIN=true'

CYMRU_WHOIS = 'whois.cymru.com'

IPV4_DNS_ZONE = '{0}.origin.asn.cymru.com.'

IPV6_DNS_ZONE = '{0}.origin6.asn.cymru.com.'

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
        address (:obj:`str`/:obj:`int`/:obj:`IPv4Address`/:obj:`IPv6Address`):
            An IPv4 or IPv6 address
        timeout (:obj:`int`): The default timeout for socket connections in
            seconds. Defaults to 5.
        proxy_opener (:obj:`urllib.request.OpenerDirector`): The request for
            proxy support. Defaults to None.

    Raises:
        IPDefinedError: The address provided is defined (does not need to be
            resolved).
    """

    def __init__(self, address, timeout=5, proxy_opener=None):

        # IPv4Address or IPv6Address
        if isinstance(address, IPv4Address) or isinstance(
                address, IPv6Address):

            self.address = address

        else:

            # Use ipaddress package exception handling.
            self.address = ip_address(address)

        # Default timeout for socket connections.
        self.timeout = timeout

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

    def get_asn_dns(self):
        """
        The function for retrieving ASN information for an IP address from
        Cymru via port 53 (DNS).

        Returns:
            list: The raw ASN data.

        Raises:
            ASNLookupError: The ASN lookup failed.
        """

        try:

            log.debug('ASN query for {0}'.format(self.dns_zone))
            data = self.dns_resolver.resolve(self.dns_zone, 'TXT')
            log.debug('ASN query results using {0}: {1}'.format(
                self.dns_zone, list(data)))
            return list(data)

        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers,
                dns.resolver.NoAnswer, dns.exception.Timeout) as e:

            raise ASNLookupError(
                'ASN lookup failed (DNS {0}) for {1}.'.format(
                    e.__class__.__name__, self.address_str)
            )

        except:  # pragma: no cover

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(self.address_str)
            )

    def get_asn_verbose_dns(self, asn=None):
        """
        The function for retrieving the information for an ASN from
        Cymru via port 53 (DNS). This is needed since IP to ASN mapping via
        Cymru DNS does not return the ASN Description like Cymru Whois does.

        Args:
            asn (:obj:`str`): The AS number (required).

        Returns:
            str: The raw ASN data.

        Raises:
            ASNLookupError: The ASN lookup failed.
        """

        if asn[0:2] != 'AS':

            asn = 'AS{0}'.format(asn)

        zone = '{0}.asn.cymru.com.'.format(asn)

        try:

            log.debug('ASN verbose query for {0}'.format(zone))
            data = self.dns_resolver.resolve(zone, 'TXT')
            return str(data[0])

        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers,
                dns.resolver.NoAnswer, dns.exception.Timeout) as e:

            raise ASNLookupError(
                'ASN lookup failed (DNS {0}) for {1}.'.format(
                    e.__class__.__name__, asn)
            )

        except:  # pragma: no cover

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(asn)
            )

    def get_asn_whois(self, retry_count=3):
        """
        The function for retrieving ASN information for an IP address from
        Cymru via port 43/tcp (WHOIS).

        Args:
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.

        Returns:
            str: The raw ASN data.

        Raises:
            ASNLookupError: The ASN lookup failed.
        """

        try:

            # Create the connection for the Cymru whois query.
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(self.timeout)
            log.debug('ASN query for {0}'.format(self.address_str))
            conn.connect((CYMRU_WHOIS, 43))

            # Query the Cymru whois server, and store the results.
            conn.send((
                ' -r -a -c -p -f {0}{1}'.format(
                    self.address_str, '\r\n')
            ).encode())

            data = ''
            while True:

                d = conn.recv(4096).decode()
                data += d

                if not d:

                    break

            conn.close()

            return str(data)

        except (socket.timeout, socket.error) as e:  # pragma: no cover

            log.debug('ASN query socket error: {0}'.format(e))
            try:
                conn.close()
            except Exception:
                pass
            if retry_count > 0:

                log.debug('ASN query retrying (count: {0})'.format(
                    str(retry_count)))
                return self.get_asn_whois(retry_count - 1)

            else:

                raise ASNLookupError(
                    'ASN lookup failed for {0}.'.format(self.address_str)
                )

        except:  # pragma: no cover

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(self.address_str)
            )

    def get_asn_http(self, retry_count=3):
        """
        The function for retrieving ASN information for an IP address from
        Arin via port 80 (HTTP). Currently limited to fetching asn_registry
        through a Arin whois (REST) lookup. The other values are returned as
        None to keep a consistent dict output. This should be used as a last
        chance fallback call behind ASN DNS & ASN Whois lookups.

        Args:
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.

        Returns:
            dict: The ASN data in json format.

        Raises:
            ASNLookupError: The ASN lookup failed.
        """

        try:

            # Lets attempt to get the ASN registry information from
            # ARIN.
            log.debug('ASN query for {0}'.format(self.address_str))
            response = self.get_http_json(
                url=str(ARIN).format(self.address_str),
                retry_count=retry_count,
                headers={'Accept': 'application/json'}
                )

            return response

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

        except:

            raise ASNLookupError(
                'ASN lookup failed for {0}.'.format(self.address_str)
            )

    def get_asn_origin_whois(self, asn_registry='radb', asn=None,
                             retry_count=3, server=None, port=43):
        """
        The function for retrieving CIDR info for an ASN via whois.

        Args:
            asn_registry (:obj:`str`): The source to run the query against
                (asn.ASN_ORIGIN_WHOIS).
            asn (:obj:`str`): The AS number (required).
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            server (:obj:`str`): An optional server to connect to.
            port (:obj:`int`): The network port to connect on. Defaults to 43.

        Returns:
            str: The raw ASN origin whois data.

        Raises:
            WhoisLookupError: The ASN origin whois lookup failed.
            WhoisRateLimitError: The ASN origin Whois request rate limited and
                retries were exhausted.
        """

        try:

            if server is None:
                server = ASN_ORIGIN_WHOIS[asn_registry]['server']

            # Create the connection for the whois query.
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(self.timeout)
            log.debug('ASN origin WHOIS query for {0} at {1}:{2}'.format(
                asn, server, port))
            conn.connect((server, port))

            # Prep the query.
            query = ' -i origin {0}{1}'.format(asn, '\r\n')

            # Query the whois server, and store the results.
            conn.send(query.encode())

            response = ''
            while True:

                d = conn.recv(4096).decode()

                response += d

                if not d:

                    break

            conn.close()

            # TODO: this was taken from get_whois(). Need to test rate limiting
            if 'Query rate limit exceeded' in response:  # pragma: no cover

                if retry_count > 0:

                    log.debug('ASN origin WHOIS query rate limit exceeded. '
                              'Waiting...')
                    sleep(1)
                    return self.get_asn_origin_whois(
                        asn_registry=asn_registry, asn=asn,
                        retry_count=retry_count-1,
                        server=server, port=port
                    )

                else:

                    raise WhoisRateLimitError(
                        'ASN origin Whois lookup failed for {0}. Rate limit '
                        'exceeded, wait and try again (possibly a '
                        'temporary block).'.format(asn))

            elif ('error 501' in response or 'error 230' in response
                  ):  # pragma: no cover

                log.debug('ASN origin WHOIS query error: {0}'.format(response))
                raise ValueError

            return str(response)

        except (socket.timeout, socket.error) as e:

            log.debug('ASN origin WHOIS query socket error: {0}'.format(e))
            try:
                conn.close()
            except Exception:
                pass
            if retry_count > 0:

                log.debug('ASN origin WHOIS query retrying (count: {0})'
                          ''.format(str(retry_count)))
                return self.get_asn_origin_whois(
                    asn_registry=asn_registry, asn=asn,
                    retry_count=retry_count-1, server=server, port=port
                )

            else:

                raise WhoisLookupError(
                    'ASN origin WHOIS lookup failed for {0}.'.format(asn)
                )

        except WhoisRateLimitError:  # pragma: no cover

            raise

        except:  # pragma: no cover

            raise WhoisLookupError(
                'ASN origin WHOIS lookup failed for {0}.'.format(asn)
            )

    def get_whois(self, asn_registry='arin', retry_count=3, server=None,
                  port=43, extra_blacklist=None, get_recursive=True):
        """
        The function for retrieving whois or rwhois information for an IP
        address via any port. Defaults to port 43/tcp (WHOIS).

        Args:
            asn_registry (:obj:`str`): The NIC to run the query against.
                Defaults to 'arin'.
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            server (:obj:`str`): An optional server to connect to. If
                provided, asn_registry will be ignored.
            port (:obj:`int`): The network port to connect on. Defaults to 43.
            extra_blacklist (:obj:`list` of :obj:`str`): Blacklisted whois
                servers in addition to the global BLACKLIST. Defaults to None.

        Returns:
            str: The raw whois data.

        Raises:
            BlacklistError: Raised if the whois server provided is in the
                global BLACKLIST or extra_blacklist.
            WhoisLookupError: The whois lookup failed.
            WhoisRateLimitError: The Whois request rate limited and retries
                were exhausted.
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
            if asn_registry == 'ripencc' and get_recursive is False:
                query = '-r {0}'.format(query)

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

                if retry_count > 0:

                    log.debug('WHOIS query rate limit exceeded. Waiting...')
                    sleep(1)
                    return self.get_whois(
                        asn_registry=asn_registry, retry_count=retry_count-1,
                        server=server, port=port,
                        extra_blacklist=extra_blacklist
                    )

                else:

                    raise WhoisRateLimitError(
                        'Whois lookup failed for {0}. Rate limit '
                        'exceeded, wait and try again (possibly a '
                        'temporary block).'.format(self.address_str))

            elif 'error 501' in response:  # pragma: no cover

                log.debug('WHOIS query error: {0}'.format(response))
                raise ValueError

            elif 'error 230' in response:  # pragma: no cover

                # No results found
                log.debug('WHOIS query error: {0}'.format(response))
                pass

            return str(response)

        except (socket.timeout, socket.error) as e:

            log.debug('WHOIS query socket error: {0}'.format(e))
            try:
                conn.close()
            except Exception:
                pass
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

        except WhoisRateLimitError:  # pragma: no cover

            raise

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
            url (:obj:`str`): The URL to retrieve (required).
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            rate_limit_timeout (:obj:`int`): The number of seconds to wait
                before retrying when a rate limit notice is returned via
                rdap+json or HTTP error 429. Defaults to 60.
            headers (:obj:`dict`): The HTTP headers. The Accept header
                defaults to 'application/rdap+json'.

        Returns:
            dict: The data in json format.

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

        except HTTPError as e:  # pragma: no cover

            # RIPE is producing this HTTP error rather than a JSON error.
            if e.code == 429:

                log.debug('HTTP query rate limit exceeded.')

                if retry_count > 0:
                    log.debug('Waiting {0} seconds...'.format(
                        str(rate_limit_timeout)))

                    sleep(rate_limit_timeout)
                    return self.get_http_json(
                        url=url, retry_count=retry_count - 1,
                        rate_limit_timeout=rate_limit_timeout,
                        headers=headers
                    )
                else:
                    raise HTTPRateLimitError(
                        'HTTP lookup failed for {0}. Rate limit '
                        'exceeded, wait and try again (possibly a '
                        'temporary block).'.format(url))

            else:

                raise HTTPLookupError('HTTP lookup failed for {0} with error '
                                      'code {1}.'.format(url, str(e.code)))

        except (URLError, socket.timeout, socket.error) as e:

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
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.

        Returns:
            namedtuple:

            :hostname (str): The hostname returned mapped to the given IP
                address.
            :aliaslist (list): Alternate names for the given IP address.
            :ipaddrlist (list): IPv4/v6 addresses mapped to the same hostname.

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

            results = namedtuple('get_host_results', 'hostname, aliaslist, '
                                                     'ipaddrlist')
            return results(ret)

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

    def get_http_raw(self, url=None, retry_count=3, headers=None,
                     request_type='GET', form_data=None):
        """
        The function for retrieving a raw HTML result via HTTP.

        Args:
            url (:obj:`str`): The URL to retrieve (required).
            retry_count (:obj:`int`): The number of times to retry in case
                socket errors, timeouts, connection resets, etc. are
                encountered. Defaults to 3.
            headers (:obj:`dict`): The HTTP headers. The Accept header
                defaults to 'text/html'.
            request_type (:obj:`str`): Request type 'GET' or 'POST'. Defaults
                to 'GET'.
            form_data (:obj:`dict`): Optional form POST data.

        Returns:
            str: The raw data.

        Raises:
            HTTPLookupError: The HTTP lookup failed.
        """

        if headers is None:
            headers = {'Accept': 'text/html'}

        enc_form_data = None
        if form_data:
            enc_form_data = urlencode(form_data)
            try:
                # Py 2 inspection will alert on the encoding arg, no harm done.
                enc_form_data = bytes(enc_form_data, encoding='ascii')
            except TypeError:  # pragma: no cover
                pass

        try:

            # Create the connection for the HTTP query.
            log.debug('HTTP query for {0} at {1}'.format(
                self.address_str, url))
            try:
                # Py 2 inspection alert bypassed by using kwargs dict.
                conn = Request(url=url, data=enc_form_data, headers=headers,
                               **{'method': request_type})
            except TypeError:  # pragma: no cover
                conn = Request(url=url, data=enc_form_data, headers=headers)
            data = self.opener.open(conn, timeout=self.timeout)

            try:
                d = data.readall().decode('ascii', 'ignore')
            except AttributeError:  # pragma: no cover
                d = data.read().decode('ascii', 'ignore')

            return str(d)

        except (URLError, socket.timeout, socket.error) as e:

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
