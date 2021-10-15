# Copyright (c) 2017-2019 Philip Hane
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

import socket
import logging
import time
from collections import namedtuple

from .exceptions import (ASNLookupError, HTTPLookupError, HTTPRateLimitError,
                         ASNRegistryError)
from .asn import IPASN
from .net import (CYMRU_WHOIS, Net)
from .rdap import RDAP
from .utils import unique_everseen

log = logging.getLogger(__name__)


def get_bulk_asn_whois(addresses=None, retry_count=3, timeout=120):
    """
    The function for retrieving ASN information for multiple IP addresses from
    Cymru via port 43/tcp (WHOIS).

    Args:
        addresses (:obj:`list` of :obj:`str`): IP addresses to lookup.
        retry_count (:obj:`int`): The number of times to retry in case socket
            errors, timeouts, connection resets, etc. are encountered.
            Defaults to 3.
        timeout (:obj:`int`): The default timeout for socket connections in
            seconds. Defaults to 120.

    Returns:
        str: The raw ASN bulk data, new line separated.

    Raises:
        ValueError: addresses argument must be a list of IPv4/v6 address
            strings.
        ASNLookupError: The ASN bulk lookup failed.
    """

    if not isinstance(addresses, list):

        raise ValueError('addresses argument must be a list of IPv4/v6 '
                         'address strings.')

    try:

        # Create the connection for the Cymru whois query.
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(timeout)
        log.debug('ASN bulk query initiated.')
        conn.connect((CYMRU_WHOIS, 43))

        # Query the Cymru whois server, and store the results.
        conn.sendall((
            ' -r -a -c -p -f begin\n{0}\nend'.format(
                '\n'.join(addresses))
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

        log.debug('ASN bulk query socket error: {0}'.format(e))
        if retry_count > 0:

            log.debug('ASN bulk query retrying (count: {0})'.format(
                str(retry_count)))
            return get_bulk_asn_whois(addresses, retry_count - 1, timeout)

        else:

            raise ASNLookupError('ASN bulk lookup failed.')

    except:  # pragma: no cover

        raise ASNLookupError('ASN bulk lookup failed.')


def bulk_lookup_rdap(addresses=None, inc_raw=False, retry_count=3, depth=0,
                     excluded_entities=None, rate_limit_timeout=60,
                     socket_timeout=10, asn_timeout=240, proxy_openers=None):
    """
    The function for bulk retrieving and parsing whois information for a list
    of IP addresses via HTTP (RDAP). This bulk lookup method uses bulk
    ASN Whois lookups first to retrieve the ASN for each IP. It then optimizes
    RDAP queries to achieve the fastest overall time, accounting for
    rate-limiting RIRs.

    Args:
        addresses (:obj:`list` of :obj:`str`): IP addresses to lookup.
        inc_raw (:obj:`bool`, optional): Whether to include the raw whois
            results in the returned dictionary. Defaults to False.
        retry_count (:obj:`int`): The number of times to retry in case socket
            errors, timeouts, connection resets, etc. are encountered.
            Defaults to 3.
        depth (:obj:`int`): How many levels deep to run queries when additional
            referenced objects are found. Defaults to 0.
        excluded_entities (:obj:`list` of :obj:`str`): Entity handles to not
            perform lookups. Defaults to None.
        rate_limit_timeout (:obj:`int`): The number of seconds to wait before
            retrying when a rate limit notice is returned via rdap+json.
            Defaults to 60.
        socket_timeout (:obj:`int`): The default timeout for socket
            connections in seconds. Defaults to 10.
        asn_timeout (:obj:`int`): The default timeout for bulk ASN lookups in
            seconds. Defaults to 240.
        proxy_openers (:obj:`list` of :obj:`OpenerDirector`): Proxy openers
            for single/rotating proxy support. Defaults to None.

    Returns:
        namedtuple:

        :results (dict): IP address keys with the values as dictionaries
            returned by IPWhois.lookup_rdap().
        :stats (dict): Stats for the lookups:

        ::

            {
                'ip_input_total' (int) - The total number of addresses
                    originally provided for lookup via the addresses argument.
                'ip_unique_total' (int) - The total number of unique addresses
                    found in the addresses argument.
                'ip_lookup_total' (int) - The total number of addresses that
                    lookups were attempted for, excluding any that failed ASN
                    registry checks.
                'ip_failed_total' (int) - The total number of addresses that
                    lookups failed for. Excludes any that failed initially, but
                    succeeded after further retries.
                'lacnic' (dict) -
                {
                    'failed' (list) - The addresses that failed to lookup.
                        Excludes any that failed initially, but succeeded after
                        further retries.
                    'rate_limited' (list) - The addresses that encountered
                        rate-limiting. Unless an address is also in 'failed',
                        it eventually succeeded.
                    'total' (int) - The total number of addresses belonging to
                        this RIR that lookups were attempted for.
                }
                'ripencc' (dict) - Same as 'lacnic' above.
                'apnic' (dict) - Same as 'lacnic' above.
                'afrinic' (dict) - Same as 'lacnic' above.
                'arin' (dict) - Same as 'lacnic' above.
                'unallocated_addresses' (list) - The addresses that are
                    unallocated/failed ASN lookups. These can be addresses that
                    are not listed for one of the 5 RIRs (other). No attempt
                    was made to perform an RDAP lookup for these.
            }

    Raises:
        ASNLookupError: The ASN bulk lookup failed, cannot proceed with bulk
            RDAP lookup.
    """

    if not isinstance(addresses, list):

        raise ValueError('addresses must be a list of IP address strings')

    # Initialize the dicts/lists
    results = {}
    failed_lookups_dict = {}
    rated_lookups = []
    stats = {
        'ip_input_total': len(addresses),
        'ip_unique_total': 0,
        'ip_lookup_total': 0,
        'ip_failed_total': 0,
        'lacnic': {'failed': [], 'rate_limited': [], 'total': 0},
        'ripencc': {'failed': [], 'rate_limited': [], 'total': 0},
        'apnic': {'failed': [], 'rate_limited': [], 'total': 0},
        'afrinic': {'failed': [], 'rate_limited': [], 'total': 0},
        'arin': {'failed': [], 'rate_limited': [], 'total': 0},
        'unallocated_addresses': []
    }
    asn_parsed_results = {}

    if proxy_openers is None:

        proxy_openers = [None]

    proxy_openers_copy = iter(proxy_openers)

    # Make sure addresses is unique
    unique_ip_list = list(unique_everseen(addresses))

    # Get the unique count to return
    stats['ip_unique_total'] = len(unique_ip_list)

    # This is needed for iteration order
    rir_keys_ordered = ['lacnic', 'ripencc', 'apnic', 'afrinic', 'arin']

    # First query the ASN data for all IPs, can raise ASNLookupError, no catch
    bulk_asn = get_bulk_asn_whois(unique_ip_list, timeout=asn_timeout)

    # ASN results are returned as string, parse lines to list and remove first
    asn_result_list = bulk_asn.split('\n')
    del asn_result_list[0]

    # We need to instantiate IPASN, which currently needs a Net object,
    # IP doesn't matter here
    net = Net('1.2.3.4')
    ipasn = IPASN(net)

    # Iterate each IP ASN result, and add valid RIR results to
    # asn_parsed_results for RDAP lookups
    for asn_result in asn_result_list:

        temp = asn_result.split('|')

        # Not a valid entry, move on to next
        if len(temp) == 1:

            continue

        ip = temp[1].strip()

        # We need this since ASN bulk lookup is returning duplicates
        # This is an issue on the Cymru end
        if ip in asn_parsed_results.keys():  # pragma: no cover

            continue

        try:

            asn_parsed = ipasn.parse_fields_whois(asn_result)

        except ASNRegistryError:  # pragma: no cover

            continue

        # Add valid IP ASN result to asn_parsed_results for RDAP lookup
        asn_parsed_results[ip] = asn_parsed
        stats[asn_parsed['asn_registry']]['total'] += 1

    # Set the list of IPs that are not allocated/failed ASN lookup
    stats['unallocated_addresses'] = list(k for k in addresses if k not in
                                          asn_parsed_results)

    # Set the total lookup count after unique IP and ASN result filtering
    stats['ip_lookup_total'] = len(asn_parsed_results)

    # Track the total number of LACNIC queries left. This is tracked in order
    # to ensure the 9 priority LACNIC queries/min don't go into infinite loop
    lacnic_total_left = stats['lacnic']['total']

    # Set the start time, this value is updated when the rate limit is reset
    old_time = time.time()

    # Rate limit tracking dict for all RIRs
    rate_tracker = {
        'lacnic': {'time': old_time, 'count': 0},
        'ripencc': {'time': old_time, 'count': 0},
        'apnic': {'time': old_time, 'count': 0},
        'afrinic': {'time': old_time, 'count': 0},
        'arin': {'time': old_time, 'count': 0}
    }

    # Iterate all of the IPs to perform RDAP lookups until none are left
    while len(asn_parsed_results) > 0:

        # Sequentially run through each RIR to minimize lookups in a row to
        # the same RIR.
        for rir in rir_keys_ordered:

            # If there are still LACNIC IPs left to lookup and the rate limit
            # hasn't been reached, skip to find a LACNIC IP to lookup
            if (
                rir != 'lacnic' and lacnic_total_left > 0 and
                (rate_tracker['lacnic']['count'] != 9 or
                    (time.time() - rate_tracker['lacnic']['time']
                     ) >= rate_limit_timeout
                 )
               ):  # pragma: no cover

                continue

            # If the RIR rate limit has been reached and hasn't expired,
            # move on to the next RIR
            if (
                rate_tracker[rir]['count'] == 9 and (
                    (time.time() - rate_tracker[rir]['time']
                     ) < rate_limit_timeout)
               ):  # pragma: no cover

                continue

            # If the RIR rate limit has expired, reset the count/timer
            # and perform the lookup
            elif ((time.time() - rate_tracker[rir]['time']
                   ) >= rate_limit_timeout):  # pragma: no cover

                rate_tracker[rir]['count'] = 0
                rate_tracker[rir]['time'] = time.time()

            # Create a copy of the lookup IP dict so we can modify on
            # successful/failed queries. Loop each IP until it matches the
            # correct RIR in the parent loop, and attempt lookup
            tmp_dict = asn_parsed_results.copy()

            for ip, asn_data in tmp_dict.items():

                # Check to see if IP matches parent loop RIR for lookup
                if asn_data['asn_registry'] == rir:

                    log.debug('Starting lookup for IP: {0} '
                              'RIR: {1}'.format(ip, rir))

                    # Add to count for rate-limit tracking only for LACNIC,
                    # since we have not seen aggressive rate-limiting from the
                    # other RIRs yet
                    if rir == 'lacnic':

                        rate_tracker[rir]['count'] += 1

                    # Get the next proxy opener to use, or None
                    try:

                        opener = next(proxy_openers_copy)

                    # Start at the beginning if all have been used
                    except StopIteration:

                        proxy_openers_copy = iter(proxy_openers)
                        opener = next(proxy_openers_copy)

                    # Instantiate the objects needed for the RDAP lookup
                    net = Net(ip, timeout=socket_timeout, proxy_opener=opener)
                    rdap = RDAP(net)

                    try:

                        # Perform the RDAP lookup. retry_count is set to 0
                        # here since we handle that in this function
                        rdap_result = rdap.lookup(
                            inc_raw=inc_raw, retry_count=0, asn_data=asn_data,
                            depth=depth, excluded_entities=excluded_entities
                        )

                        log.debug('Successful lookup for IP: {0} '
                                  'RIR: {1}'.format(ip, rir))

                        # Lookup was successful, add to result. Set the nir
                        # key to None as this is not supported
                        # (yet - requires more queries)
                        results[ip] = asn_data
                        results[ip].update(rdap_result)

                        results[ip]['nir'] = None

                        # Remove the IP from the lookup queue
                        del asn_parsed_results[ip]

                        # If this was LACNIC IP, reduce the total left count
                        if rir == 'lacnic':

                            lacnic_total_left -= 1

                        log.debug(
                            '{0} total lookups left, {1} LACNIC lookups left'
                            ''.format(str(len(asn_parsed_results)),
                                      str(lacnic_total_left))
                        )

                        # If this IP failed previously, remove it from the
                        # failed return dict
                        if (
                            ip in failed_lookups_dict.keys()
                        ):  # pragma: no cover

                            del failed_lookups_dict[ip]

                        # Break out of the IP list loop, we need to change to
                        # the next RIR
                        break

                    except HTTPLookupError:  # pragma: no cover

                        log.debug('Failed lookup for IP: {0} '
                                  'RIR: {1}'.format(ip, rir))

                        # Add the IP to the failed lookups dict if not there
                        if ip not in failed_lookups_dict.keys():

                            failed_lookups_dict[ip] = 1

                        # This IP has already failed at least once, increment
                        # the failure count until retry_count reached, then
                        # stop trying
                        else:

                            failed_lookups_dict[ip] += 1

                            if failed_lookups_dict[ip] == retry_count:

                                del asn_parsed_results[ip]
                                stats[rir]['failed'].append(ip)
                                stats['ip_failed_total'] += 1

                                if rir == 'lacnic':

                                    lacnic_total_left -= 1

                        # Since this IP failed, we don't break to move to next
                        # RIR, we check the next IP for this RIR
                        continue

                    except HTTPRateLimitError:  # pragma: no cover

                        # Add the IP to the rate-limited lookups dict if not
                        # there
                        if ip not in rated_lookups:

                            rated_lookups.append(ip)
                            stats[rir]['rate_limited'].append(ip)

                        log.debug('Rate limiting triggered for IP: {0} '
                                  'RIR: {1}'.format(ip, rir))

                        # Since rate-limit was reached, reset the timer and
                        # max out the count
                        rate_tracker[rir]['time'] = time.time()
                        rate_tracker[rir]['count'] = 9

                        # Break out of the IP list loop, we need to change to
                        # the next RIR
                        break

    return_tuple = namedtuple('return_tuple', ['results', 'stats'])
    return return_tuple(results, stats)
