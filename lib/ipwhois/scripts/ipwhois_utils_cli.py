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

# CLI python script interface for ipwhois.utils lookups.

import argparse
from collections import OrderedDict
import json
from ipwhois.utils import (ipv4_lstrip_zeros, calculate_cidr, get_countries,
                           ipv4_is_defined, ipv6_is_defined,
                           ipv4_generate_random, ipv6_generate_random,
                           unique_everseen, unique_addresses)

# CLI ANSI rendering
ANSI = {
    'end': '\033[0m',
    'b': '\033[1m',
    'ul': '\033[4m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'cyan': '\033[36m'
}

# Setup the arg parser.
parser = argparse.ArgumentParser(
    description='ipwhois utilities CLI interface'
)
parser.add_argument(
    '--ipv4_lstrip_zeros',
    type=str,
    nargs=1,
    metavar='"IP ADDRESS"',
    help='Strip leading zeros in each octet of an IPv4 address.'
)
parser.add_argument(
    '--calculate_cidr',
    type=str,
    nargs=2,
    metavar='"IP ADDRESS"',
    help='Calculate a CIDR range(s) from a start and end IP address.'
)
parser.add_argument(
    '--get_countries',
    action='store_true',
    help='Output a dictionary containing ISO_3166-1 country codes to names.'
)
parser.add_argument(
    '--get_country',
    type=str,
    nargs=1,
    metavar='"COUNTRY CODE"',
    help='Output the ISO_3166-1 name for a country code.'
)
parser.add_argument(
    '--ipv4_is_defined',
    type=str,
    nargs=1,
    metavar='"IP ADDRESS"',
    help='Check if an IPv4 address is defined (in a reserved address range).'
)
parser.add_argument(
    '--ipv6_is_defined',
    type=str,
    nargs=1,
    metavar='"IP ADDRESS"',
    help='Check if an IPv6 address is defined (in a reserved address range).'
)
parser.add_argument(
    '--ipv4_generate_random',
    type=int,
    nargs=1,
    metavar='TOTAL',
    help='Generate random, unique IPv4 addresses that are not defined (can be '
         'looked up using ipwhois).'
)
parser.add_argument(
    '--ipv6_generate_random',
    type=int,
    nargs=1,
    metavar='TOTAL',
    help='Generate random, unique IPv6 addresses that are not defined (can be '
         'looked up using ipwhois).'
)
parser.add_argument(
    '--unique_everseen',
    type=json.loads,
    nargs=1,
    metavar='"ITERABLE"',
    help='List unique elements from input iterable, preserving the order.'
)
parser.add_argument(
    '--unique_addresses',
    type=str,
    nargs=1,
    metavar='"FILE PATH"',
    help='Search an input file, extracting, counting, and summarizing '
         'IPv4/IPv6 addresses/networks.'
)

# Output options
group = parser.add_argument_group('Output options')
group.add_argument(
    '--colorize',
    action='store_true',
    help='If set, colorizes the output using ANSI. Should work in most '
         'platform consoles.'
)

# Get the args
script_args = parser.parse_args()

if script_args.ipv4_lstrip_zeros:

    print(ipv4_lstrip_zeros(address=script_args.ipv4_lstrip_zeros[0]))

elif script_args.calculate_cidr:

    try:

        result = calculate_cidr(
            start_address=script_args.calculate_cidr[0],
            end_address=script_args.calculate_cidr[1]
        )

        print('{0}Found {1} CIDR blocks for ({2}, {3}){4}:\n{5}'.format(
            ANSI['green'] if script_args.colorize else '',
            len(result),
            script_args.calculate_cidr[0],
            script_args.calculate_cidr[1],
            ANSI['end'] if script_args.colorize else '',
            '\n'.join(result)
        ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.get_countries:

    try:

        result = get_countries()

        print('{0}Found {1} countries{2}:\n{3}'.format(
            ANSI['green'] if script_args.colorize else '',
            len(result),
            ANSI['end'] if script_args.colorize else '',
            '\n'.join(['{0}: {1}'.format(k, v) for k, v in (
                OrderedDict(sorted(result.items())).iteritems())])
        ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.get_country:

    try:

        countries = get_countries()
        result = countries[script_args.get_country[0].upper()]

        print('{0}Match found for country code ({1}){2}:\n{3}'.format(
            ANSI['green'] if script_args.colorize else '',
            script_args.get_country[0],
            ANSI['end'] if script_args.colorize else '',
            result
        ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.ipv4_is_defined:

    try:

        result = ipv4_is_defined(address=script_args.ipv4_is_defined[0])

        if result[0]:
            print('{0}{1} is defined{2}:\n{3}'.format(
                ANSI['green'] if script_args.colorize else '',
                script_args.ipv4_is_defined[0],
                ANSI['end'] if script_args.colorize else '',
                'Name: {0}\nRFC: {1}'.format(result[1], result[2])
            ))
        else:
            print('{0}{1} is not defined{2}'.format(
                ANSI['yellow'] if script_args.colorize else '',
                script_args.ipv4_is_defined[0],
                ANSI['end'] if script_args.colorize else ''
            ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.ipv6_is_defined:

    try:

        result = ipv6_is_defined(address=script_args.ipv6_is_defined[0])

        if result[0]:
            print('{0}{1} is defined{2}:\n{3}'.format(
                ANSI['green'] if script_args.colorize else '',
                script_args.ipv6_is_defined[0],
                ANSI['end'] if script_args.colorize else '',
                'Name: {0}\nRFC: {1}'.format(result[1], result[2])
            ))
        else:
            print('{0}{1} is not defined{2}'.format(
                ANSI['yellow'] if script_args.colorize else '',
                script_args.ipv6_is_defined[0],
                ANSI['end'] if script_args.colorize else ''
            ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.ipv4_generate_random:

    try:

        result = ipv4_generate_random(total=script_args.ipv4_generate_random[0])

        for random_ip in result:

            print(random_ip)

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.ipv6_generate_random:

    try:

        result = ipv6_generate_random(total=script_args.ipv6_generate_random[0])

        for random_ip in result:

            print(random_ip)

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.unique_everseen:

    try:

        result = list(unique_everseen(iterable=script_args.unique_everseen[0]))

        print('{0}Unique everseen{1}:\n{2}'.format(
            ANSI['green'] if script_args.colorize else '',
            ANSI['end'] if script_args.colorize else '',
            result
        ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))

elif script_args.unique_addresses:

    try:

        result = unique_addresses(file_path=script_args.unique_addresses[0])

        tmp = []
        for k, v in sorted(result.items(), key=lambda kv: int(kv[1]['count']),
                           reverse=True):
            tmp.append('{0}{1}{2}: Count: {3}, Ports: {4}'.format(
                ANSI['b'] if script_args.colorize else '',
                k,
                ANSI['end'] if script_args.colorize else '',
                v['count'],
                json.dumps(v['ports'])
            ))

        print('{0}Found {1} unique addresses{2}:\n{3}'.format(
            ANSI['green'] if script_args.colorize else '',
            len(result),
            ANSI['end'] if script_args.colorize else '',
            '\n'.join(tmp)
        ))

    except Exception as e:

        print('{0}Error{1}: {2}'.format(ANSI['red'], ANSI['end'], str(e)))
