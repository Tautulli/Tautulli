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

# CLI python script interface for ipwhois.IPWhois lookups.

import argparse
import json
from os import path
from ipwhois import IPWhois
from ipwhois.hr import (HR_ASN, HR_RDAP, HR_RDAP_COMMON, HR_WHOIS,
                        HR_WHOIS_NIR)

try:  # pragma: no cover
    from urllib.request import (ProxyHandler,
                                build_opener)
except ImportError:  # pragma: no cover
    from urllib2 import (ProxyHandler,
                         build_opener)

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

# Color definitions for sub lines
COLOR_DEPTH = {
    '0': ANSI['green'],
    '1': ANSI['yellow'],
    '2': ANSI['red'],
    '3': ANSI['cyan']
}

# Line formatting, keys ending in C are colorized versions.
LINES = {
    '1': '>> ',
    '2': '>> >>> ',
    '3': '>> >>> >>>> ',
    '4': '>> >>> >>>> >>>>> ',
    '1C': '{0}>>{1} '.format(COLOR_DEPTH['0'], ANSI['end']),
    '2C': '{0}>>{1} >>>{2} '.format(
        COLOR_DEPTH['0'], COLOR_DEPTH['1'], ANSI['end']
    ),
    '3C': '{0}>>{1} >>>{2} >>>>{3} '.format(
        COLOR_DEPTH['0'], COLOR_DEPTH['1'], COLOR_DEPTH['2'], ANSI['end']
    ),
    '4C': '{0}>>{1} >>>{2} >>>>{3} >>>>>{4} '.format(
        COLOR_DEPTH['0'], COLOR_DEPTH['1'], COLOR_DEPTH['2'], COLOR_DEPTH['3'],
        ANSI['end']
    ),
}

# Setup the arg parser.
parser = argparse.ArgumentParser(
    description='ipwhois CLI interface'
)
parser.add_argument(
    '--whois',
    action='store_true',
    help='Retrieve whois data via legacy Whois (port 43) instead of RDAP '
         '(default).'
)
parser.add_argument(
    '--exclude_nir',
    action='store_true',
    help='Disable NIR whois lookups (JPNIC, KRNIC). This is the opposite of '
         'the ipwhois inc_nir, in order to enable inc_nir by default in the '
         'CLI.',
    default=False
)
parser.add_argument(
    '--json',
    action='store_true',
    help='Output results in JSON format.',
    default=False
)

# Output options
group = parser.add_argument_group('Output options')
group.add_argument(
    '--hr',
    action='store_true',
    help='If set, returns results with human readable key translations.'
)
group.add_argument(
    '--show_name',
    action='store_true',
    help='If this and --hr are set, the key name is shown in parentheses after'
         'its short value'
)
group.add_argument(
    '--colorize',
    action='store_true',
    help='If set, colorizes the output using ANSI. Should work in most '
         'platform consoles.'
)

# IPWhois settings (common)
group = parser.add_argument_group('IPWhois settings')
group.add_argument(
    '--timeout',
    type=int,
    default=5,
    metavar='TIMEOUT',
    help='The default timeout for socket connections in seconds.'
)
group.add_argument(
    '--proxy_http',
    type=str,
    nargs=1,
    default='',
    metavar='"PROXY_HTTP"',
    help='The proxy HTTP address passed to request.ProxyHandler. User auth '
         'can be passed like "http://user:pass@192.168.0.1:80"',
    required=False
)
group.add_argument(
    '--proxy_https',
    type=str,
    nargs=1,
    default='',
    metavar='"PROXY_HTTPS"',
    help='The proxy HTTPS address passed to request.ProxyHandler. User auth'
         'can be passed like "https://user:pass@192.168.0.1:443"',
    required=False
)

# Common (RDAP & Legacy Whois)
group = parser.add_argument_group('Common settings (RDAP & Legacy Whois)')
group.add_argument(
    '--inc_raw',
    action='store_true',
    help='Include the raw whois results in the output.'
)
group.add_argument(
    '--retry_count',
    type=int,
    default=3,
    metavar='RETRY_COUNT',
    help='The number of times to retry in case socket errors, timeouts, '
         'connection resets, etc. are encountered.'
)
group.add_argument(
    '--asn_methods',
    type=str,
    nargs=1,
    default='dns,whois,http',
    metavar='"ASN_METHODS"',
    help='List of ASN lookup types to attempt, in order. '
         'Defaults to all [\'dns\', \'whois\', \'http\'].'
)
group.add_argument(
    '--extra_org_map',
    type=json.loads,
    nargs=1,
    default='{"DNIC": "arin"}',
    metavar='"EXTRA_ORG_MAP"',
    help='Dictionary mapping org handles to RIRs. This is for limited cases '
         'where ARIN REST (ASN fallback HTTP lookup) does not show an RIR as '
         'the org handle e.g., DNIC (which is now the built in ORG_MAP) e.g., '
         '{\\"DNIC\\": \\"arin\\"}. Valid RIR values are (note the '
         'case-sensitive - this is meant to match the REST result): '
         '\'ARIN\', \'RIPE\', \'apnic\', \'lacnic\', \'afrinic\''
)
group.add_argument(
    '--skip_asn_description',
    action='store_true',
    help='Don\'t run an additional query when pulling ASN information via dns '
         '(to get the ASN description). This is the opposite of the ipwhois '
         'get_asn_description argument, in order to enable '
         'get_asn_description by default in the CLI.',
    default=False
)

# RDAP
group = parser.add_argument_group('RDAP settings')
group.add_argument(
    '--depth',
    type=int,
    default=0,
    metavar='COLOR_DEPTH',
    help='If not --whois, how many levels deep to run RDAP queries when '
         'additional referenced objects are found.'
)
group.add_argument(
    '--excluded_entities',
    type=str,
    nargs=1,
    default=None,
    metavar='"EXCLUDED_ENTITIES"',
    help='If not --whois, a comma delimited list of entity handles to not '
         'perform lookups.'
)
group.add_argument(
    '--bootstrap',
    action='store_true',
    help='If not --whois, performs lookups via ARIN bootstrap rather than '
         'lookups based on ASN data. ASN lookups are not performed and no '
         'output for any of the asn* fields is provided.'
)
group.add_argument(
    '--rate_limit_timeout',
    type=int,
    default=120,
    metavar='RATE_LIMIT_TIMEOUT',
    help='If not --whois, the number of seconds to wait before retrying when '
         'a rate limit notice is returned via rdap+json.'
)

# Legacy Whois
group = parser.add_argument_group('Legacy Whois settings')
group.add_argument(
    '--get_referral',
    action='store_true',
    help='If --whois, retrieve referral whois information, if available.'
)
group.add_argument(
    '--extra_blacklist',
    type=str,
    nargs=1,
    default='',
    metavar='"EXTRA_BLACKLIST"',
    help='If --whois, A list of blacklisted whois servers in addition to the '
         'global BLACKLIST.'
)
group.add_argument(
    '--ignore_referral_errors',
    action='store_true',
    help='If --whois, ignore and continue when an exception is encountered on '
         'referral whois lookups.'
)
group.add_argument(
    '--field_list',
    type=str,
    nargs=1,
    default='',
    metavar='"FIELD_LIST"',
    help='If --whois, a list of fields to parse: '
         '[\'name\', \'handle\', \'description\', \'country\', \'state\', '
         '\'city\', \'address\', \'postal_code\', \'emails\', \'created\', '
         '\'updated\']'
)

# NIR (National Internet Registry -- JPNIC, KRNIC)
group = parser.add_argument_group('NIR (National Internet Registry) settings')
group.add_argument(
    '--nir_field_list',
    type=str,
    nargs=1,
    default='',
    metavar='"NIR_FIELD_LIST"',
    help='If not --exclude_nir, a list of fields to parse: '
         '[\'name\', \'handle\', \'country\', \'address\', \'postal_code\', '
         '\'nameservers\', \'created\', \'updated\', \'contact_admin\', '
         '\'contact_tech\']'
)

# Input (required)
group = parser.add_argument_group('Input (Required)')
group.add_argument(
    '--addr',
    type=str,
    nargs=1,
    metavar='"IP"',
    help='An IPv4 or IPv6 address as a string.',
    required=True
)

# Get the args
script_args = parser.parse_args()

# Get the current working directory.
CUR_DIR = path.dirname(__file__)


def generate_output(line='0', short=None, name=None, value=None,
                    is_parent=False, colorize=True):
    """
    The function for formatting CLI output results.

    Args:
        line (:obj:`str`): The line number (0-4). Determines indentation.
            Defaults to '0'.
        short (:obj:`str`): The optional abbreviated name for a field.
            See hr.py for values.
        name (:obj:`str`): The optional name for a field. See hr.py for values.
        value (:obj:`str`): The field data (required).
        is_parent (:obj:`bool`): Set to True if the field value has sub-items
            (dicts/lists). Defaults to False.
        colorize (:obj:`bool`): Colorize the console output with ANSI colors.
            Defaults to True.

    Returns:
        str: The generated output.
    """

    # TODO: so ugly
    output = '{0}{1}{2}{3}{4}{5}{6}{7}\n'.format(
        LINES['{0}{1}'.format(line, 'C' if colorize else '')] if (
            line in LINES.keys()) else '',
        COLOR_DEPTH[line] if (colorize and line in COLOR_DEPTH) else '',
        ANSI['b'],
        short if short is not None else (
            name if (name is not None) else ''
        ),
        '' if (name is None or short is None) else ' ({0})'.format(
            name),
        '' if (name is None and short is None) else ': ',
        ANSI['end'] if colorize else '',
        '' if is_parent else value
    )

    return output


class IPWhoisCLI:
    """
    The CLI wrapper class for outputting formatted IPWhois results.

    Args:
        addr (:obj:`str`/:obj:`int`/:obj:`IPv4Address`/:obj:`IPv6Address`):
            An IPv4 or IPv6 address
        timeout (:obj:`int`): The default timeout for socket connections in
            seconds. Defaults to 5.
        proxy_http (:obj:`urllib.request.OpenerDirector`): The request for
            proxy HTTP support or None.
        proxy_https (:obj:`urllib.request.OpenerDirector`): The request for
            proxy HTTPS support or None.
    """

    def __init__(
        self,
        addr,
        timeout,
        proxy_http,
        proxy_https
    ):

        self.addr = addr
        self.timeout = timeout

        handler_dict = None
        if proxy_http is not None:

            handler_dict = {'http': proxy_http}

        if proxy_https is not None:

            if handler_dict is None:

                handler_dict = {'https': proxy_https}

            else:

                handler_dict['https'] = proxy_https

        if handler_dict is None:

            self.opener = None
        else:

            handler = ProxyHandler(handler_dict)
            self.opener = build_opener(handler)

        self.obj = IPWhois(address=self.addr,
                           timeout=self.timeout,
                           proxy_opener=self.opener)

    def generate_output_header(self, query_type='RDAP'):
        """
        The function for generating the CLI output header.

        Args:
            query_type (:obj:`str`): The IPWhois query type. Defaults to
                'RDAP'.

        Returns:
            str: The generated output.
        """

        output = '\n{0}{1}{2} query for {3}:{4}\n\n'.format(
            ANSI['ul'],
            ANSI['b'],
            query_type,
            self.obj.address_str,
            ANSI['end']
        )

        return output

    def generate_output_newline(self, line='0', colorize=True):
        """
        The function for generating a CLI output new line.

        Args:
            line (:obj:`str`): The line number (0-4). Determines indentation.
                Defaults to '0'.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        return generate_output(
            line=line,
            is_parent=True,
            colorize=colorize
        )

    def generate_output_asn(self, json_data=None, hr=True, show_name=False,
                            colorize=True):
        """
        The function for generating CLI output ASN results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        if json_data is None:
            json_data = {}

        keys = {'asn', 'asn_cidr', 'asn_country_code', 'asn_date',
                'asn_registry', 'asn_description'}.intersection(json_data)

        output = ''

        for key in keys:

            output += generate_output(
                line='0',
                short=HR_ASN[key]['_short'] if hr else key,
                name=HR_ASN[key]['_name'] if (hr and show_name) else None,
                value=(json_data[key] if (
                    json_data[key] is not None and
                    len(json_data[key]) > 0 and
                    json_data[key] != 'NA') else 'None'),
                colorize=colorize
            )

        return output

    def generate_output_entities(self, json_data=None, hr=True,
                                 show_name=False, colorize=True):
        """
        The function for generating CLI output RDAP entity results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        output = ''
        short = HR_RDAP['entities']['_short'] if hr else 'entities'
        name = HR_RDAP['entities']['_name'] if (hr and show_name) else None

        output += generate_output(
            line='0',
            short=short,
            name=name,
            is_parent=False if (json_data is None or
                                json_data['entities'] is None) else True,
            value='None' if (json_data is None or
                             json_data['entities'] is None) else None,
            colorize=colorize
        )

        if json_data is not None:

            for ent in json_data['entities']:

                output += generate_output(
                    line='1',
                    value=ent,
                    colorize=colorize
                )

        return output

    def generate_output_events(self, source, key, val, line='2', hr=True,
                               show_name=False, colorize=True):
        """
        The function for generating CLI output RDAP events results.

        Args:
            source (:obj:`str`): The parent key 'network' or 'objects'
                (required).
            key (:obj:`str`): The event key 'events' or 'events_actor'
                (required).
            val (:obj:`dict`): The event dictionary (required).
            line (:obj:`str`): The line number (0-4). Determines indentation.
                Defaults to '0'.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        output = generate_output(
            line=line,
            short=HR_RDAP[source][key]['_short'] if hr else key,
            name=HR_RDAP[source][key]['_name'] if (hr and show_name) else None,
            is_parent=False if (val is None or
                                len(val) == 0) else True,
            value='None' if (val is None or
                             len(val) == 0) else None,
            colorize=colorize
        )

        if val is not None:

            count = 0
            for item in val:

                try:
                    action = item['action']
                except KeyError:
                    action = None

                try:
                    timestamp = item['timestamp']
                except KeyError:
                    timestamp = None

                try:
                    actor = item['actor']
                except KeyError:
                    actor = None

                if count > 0:
                    output += generate_output(
                        line=str(int(line)+1),
                        is_parent=True,
                        colorize=colorize
                    )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['action'][
                        '_short'] if hr else 'action',
                    name=HR_RDAP_COMMON[key]['action'][
                        '_name'] if (hr and show_name) else None,
                    value=action,
                    colorize=colorize
                )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['timestamp'][
                        '_short'] if hr else 'timestamp',
                    name=HR_RDAP_COMMON[key]['timestamp'][
                        '_name'] if (hr and show_name) else None,
                    value=timestamp,
                    colorize=colorize
                )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['actor'][
                        '_short'] if hr else 'actor',
                    name=HR_RDAP_COMMON[key]['actor'][
                        '_name'] if (hr and show_name) else None,
                    value=actor,
                    colorize=colorize
                )

                count += 1

        return output

    def generate_output_list(self, source, key, val, line='2', hr=True,
                             show_name=False, colorize=True):
        """
        The function for generating CLI output RDAP list results.

        Args:
            source (:obj:`str`): The parent key 'network' or 'objects'
                (required).
            key (:obj:`str`): The event key 'events' or 'events_actor'
                (required).
            val (:obj:`dict`): The event dictionary (required).
            line (:obj:`str`): The line number (0-4). Determines indentation.
                Defaults to '0'.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        output = generate_output(
            line=line,
            short=HR_RDAP[source][key]['_short'] if hr else key,
            name=HR_RDAP[source][key]['_name'] if (hr and show_name) else None,
            is_parent=False if (val is None or
                                len(val) == 0) else True,
            value='None' if (val is None or
                             len(val) == 0) else None,
            colorize=colorize
        )

        if val is not None:
            for item in val:
                output += generate_output(
                    line=str(int(line)+1),
                    value=item,
                    colorize=colorize
                )

        return output

    def generate_output_notices(self, source, key, val, line='1', hr=True,
                                show_name=False, colorize=True):
        """
        The function for generating CLI output RDAP notices results.

        Args:
            source (:obj:`str`): The parent key 'network' or 'objects'
                (required).
            key (:obj:`str`): The event key 'events' or 'events_actor'
                (required).
            val (:obj:`dict`): The event dictionary (required).
            line (:obj:`str`): The line number (0-4). Determines indentation.
                Defaults to '0'.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        output = generate_output(
            line=line,
            short=HR_RDAP[source][key]['_short'] if hr else key,
            name=HR_RDAP[source][key]['_name'] if (hr and show_name) else None,
            is_parent=False if (val is None or
                                len(val) == 0) else True,
            value='None' if (val is None or
                             len(val) == 0) else None,
            colorize=colorize
        )

        if val is not None:

            count = 0
            for item in val:

                title = item['title']
                description = item['description']
                links = item['links']

                if count > 0:
                    output += generate_output(
                        line=str(int(line)+1),
                        is_parent=True,
                        colorize=colorize
                    )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['title']['_short'] if hr else (
                        'title'),
                    name=HR_RDAP_COMMON[key]['title']['_name'] if (
                        hr and show_name) else None,
                    value=title,
                    colorize=colorize
                )

                output += generate_output(
                    line=str(int(line)+1),
                    short=HR_RDAP_COMMON[key]['description'][
                        '_short'] if hr else 'description',
                    name=HR_RDAP_COMMON[key]['description'][
                        '_name'] if (hr and show_name) else None,
                    value=description.replace(
                        '\n',
                        '\n{0}'.format(generate_output(line='3'))
                    ),
                    colorize=colorize
                )
                output += self.generate_output_list(
                    source=source,
                    key='links',
                    val=links,
                    line=str(int(line)+1),
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

                count += 1

        return output

    def generate_output_network(self, json_data=None, hr=True, show_name=False,
                                colorize=True):
        """
        The function for generating CLI output RDAP network results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_RDAP['network']['_short'] if hr else 'network',
            name=HR_RDAP['network']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        for key, val in json_data['network'].items():

            if key in ['links', 'status']:

                output += self.generate_output_list(
                    source='network',
                    key=key,
                    val=val,
                    line='1',
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

            elif key in ['notices', 'remarks']:

                output += self.generate_output_notices(
                    source='network',
                    key=key,
                    val=val,
                    line='1',
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

            elif key == 'events':

                output += self.generate_output_events(
                    source='network',
                    key=key,
                    val=val,
                    line='1',
                    hr=hr,
                    show_name=show_name,
                    colorize=colorize
                )

            elif key not in ['raw']:

                output += generate_output(
                    line='1',
                    short=HR_RDAP['network'][key]['_short'] if hr else key,
                    name=HR_RDAP['network'][key]['_name'] if (
                        hr and show_name) else None,
                    value=val,
                    colorize=colorize
                )

        return output

    def generate_output_objects(self, json_data=None, hr=True, show_name=False,
                                colorize=True):
        """
        The function for generating CLI output RDAP object results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_RDAP['objects']['_short'] if hr else 'objects',
            name=HR_RDAP['objects']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        count = 0
        for obj_name, obj in json_data['objects'].items():
            if count > 0:
                output += self.generate_output_newline(
                    line='1',
                    colorize=colorize
                )
            count += 1

            output += generate_output(
                line='1',
                short=obj_name,
                is_parent=True,
                colorize=colorize
            )

            for key, val in obj.items():

                if key in ['links', 'entities', 'roles', 'status']:

                    output += self.generate_output_list(
                        source='objects',
                        key=key,
                        val=val,
                        line='2',
                        hr=hr,
                        show_name=show_name,
                        colorize=colorize
                    )

                elif key in ['notices', 'remarks']:

                    output += self.generate_output_notices(
                        source='objects',
                        key=key,
                        val=val,
                        line='2',
                        hr=hr,
                        show_name=show_name,
                        colorize=colorize
                    )

                elif key == 'events':

                    output += self.generate_output_events(
                        source='objects',
                        key=key,
                        val=val,
                        line='2',
                        hr=hr,
                        show_name=show_name,
                        colorize=colorize
                    )

                elif key == 'contact':

                    output += generate_output(
                        line='2',
                        short=HR_RDAP['objects']['contact'][
                            '_short'] if hr else 'contact',
                        name=HR_RDAP['objects']['contact']['_name'] if (
                            hr and show_name) else None,
                        is_parent=False if (val is None or
                                            len(val) == 0) else True,
                        value='None' if (val is None or
                                         len(val) == 0) else None,
                        colorize=colorize
                    )

                    if val is not None:

                        for k, v in val.items():

                            if k in ['phone', 'address', 'email']:

                                output += generate_output(
                                    line='3',
                                    short=HR_RDAP['objects']['contact'][k][
                                        '_short'] if hr else k,
                                    name=HR_RDAP['objects']['contact'][k][
                                        '_name'] if (
                                        hr and show_name) else None,
                                    is_parent=False if (
                                        val is None or
                                        len(val) == 0
                                    ) else True,
                                    value='None' if (val is None or
                                                     len(val) == 0) else None,
                                    colorize=colorize
                                )

                                if v is not None:
                                    for item in v:
                                        i_type = ', '.join(item['type']) if (
                                            isinstance(item['type'], list)
                                        ) else item['type']

                                        i_type = i_type if (
                                            i_type is not None and
                                            len(i_type) > 0) else ''

                                        i_value = item['value'].replace(
                                            '\n',
                                            '\n{0}'.format(
                                                generate_output(
                                                    line='4',
                                                    is_parent=True,
                                                    colorize=colorize
                                                ).replace('\n', ''))
                                        )

                                        tmp_out = '{0}{1}{2}'.format(
                                            i_type,
                                            ': ' if i_type != '' else '',
                                            i_value
                                        )

                                        output += generate_output(
                                            line='4',
                                            value=tmp_out,
                                            colorize=colorize
                                        )

                            else:

                                output += generate_output(
                                    line='3',
                                    short=HR_RDAP['objects']['contact'][k][
                                        '_short'] if hr else k,
                                    name=HR_RDAP['objects']['contact'][k][
                                        '_name'] if (
                                        hr and show_name) else None,
                                    value=v,
                                    colorize=colorize
                                )

                elif key not in ['raw']:

                    output += generate_output(
                        line='2',
                        short=HR_RDAP['objects'][key]['_short'] if hr else key,
                        name=HR_RDAP['objects'][key]['_name'] if (
                            hr and show_name) else None,
                        value=val,
                        colorize=colorize
                    )

        return output

    def lookup_rdap(self, hr=True, show_name=False, colorize=True, **kwargs):
        """
        The function for wrapping IPWhois.lookup_rdap() and generating
        formatted CLI output.

        Args:
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.
            kwargs: Arguments to pass to IPWhois.lookup_rdap().

        Returns:
            str: The generated output.
        """

        # Perform the RDAP lookup
        ret = self.obj.lookup_rdap(**kwargs)

        if script_args.json:

            output = json.dumps(ret)

        else:

            # Header
            output = self.generate_output_header(query_type='RDAP')

            # ASN
            output += self.generate_output_asn(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            # Entities
            output += self.generate_output_entities(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            # Network
            output += self.generate_output_network(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            # Objects
            output += self.generate_output_objects(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            if 'nir' in ret:

                # NIR
                output += self.generate_output_nir(
                    json_data=ret, hr=hr, show_name=show_name,
                    colorize=colorize
                )
                output += self.generate_output_newline(colorize=colorize)

        return output

    def generate_output_whois_nets(self, json_data=None, hr=True,
                                   show_name=False, colorize=True):
        """
        The function for generating CLI output Legacy Whois networks results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_WHOIS['nets']['_short'] if hr else 'nets',
            name=HR_WHOIS['nets']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        count = 0
        for net in json_data['nets']:
            if count > 0:
                output += self.generate_output_newline(
                    line='1',
                    colorize=colorize
                )
            count += 1

            output += generate_output(
                line='1',
                short=net['handle'],
                is_parent=True,
                colorize=colorize
            )

            for key, val in net.items():

                if val and '\n' in val:

                    output += generate_output(
                        line='2',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        is_parent=False if (val is None or
                                            len(val) == 0) else True,
                        value='None' if (val is None or
                                         len(val) == 0) else None,
                        colorize=colorize
                    )

                    for v in val.split('\n'):
                        output += generate_output(
                            line='3',
                            value=v,
                            colorize=colorize
                        )

                else:

                    output += generate_output(
                        line='2',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        value=val,
                        colorize=colorize
                    )

        return output

    def generate_output_whois_referral(self, json_data=None, hr=True,
                                       show_name=False, colorize=True):
        """
        The function for generating CLI output Legacy Whois referral results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_WHOIS['referral']['_short'] if hr else 'referral',
            name=HR_WHOIS['referral']['_name'] if (hr and show_name) else None,
            is_parent=False if json_data['referral'] is None else True,
            value='None' if json_data['referral'] is None else None,
            colorize=colorize
        )

        if json_data['referral']:

            for key, val in json_data['referral'].items():

                if val and '\n' in val:

                    output += generate_output(
                        line='1',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        is_parent=False if (val is None or
                                            len(val) == 0) else True,
                        value='None' if (val is None or
                                         len(val) == 0) else None,
                        colorize=colorize
                    )

                    for v in val.split('\n'):
                        output += generate_output(
                            line='2',
                            value=v,
                            colorize=colorize
                        )

                else:

                    output += generate_output(
                        line='1',
                        short=HR_WHOIS['nets'][key]['_short'] if hr else key,
                        name=HR_WHOIS['nets'][key]['_name'] if (
                            hr and show_name) else None,
                        value=val,
                        colorize=colorize
                    )

        return output

    def generate_output_nir(self, json_data=None, hr=True, show_name=False,
                            colorize=True):
        """
        The function for generating CLI output NIR network results.

        Args:
            json_data (:obj:`dict`): The data to process. Defaults to None.
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.

        Returns:
            str: The generated output.
        """

        if json_data is None:
            json_data = {}

        output = generate_output(
            line='0',
            short=HR_WHOIS_NIR['nets']['_short'] if hr else 'nir_nets',
            name=HR_WHOIS_NIR['nets']['_name'] if (hr and show_name) else None,
            is_parent=True,
            colorize=colorize
        )

        count = 0
        if json_data['nir']:

            for net in json_data['nir']['nets']:

                if count > 0:

                    output += self.generate_output_newline(
                        line='1',
                        colorize=colorize
                    )

                count += 1

                output += generate_output(
                    line='1',
                    short=net['handle'],
                    is_parent=True,
                    colorize=colorize
                )

                for key, val in net.items():

                    if val and (isinstance(val, dict) or '\n' in val or
                                key == 'nameservers'):

                        output += generate_output(
                            line='2',
                            short=(
                                HR_WHOIS_NIR['nets'][key]['_short'] if (
                                    hr) else key
                            ),
                            name=HR_WHOIS_NIR['nets'][key]['_name'] if (
                                hr and show_name) else None,
                            is_parent=False if (val is None or
                                                len(val) == 0) else True,
                            value='None' if (val is None or
                                             len(val) == 0) else None,
                            colorize=colorize
                        )

                        if key == 'contacts':

                            for k, v in val.items():

                                if v:

                                    output += generate_output(
                                        line='3',
                                        is_parent=False if (
                                            len(v) == 0) else True,
                                        name=k,
                                        colorize=colorize
                                    )

                                    for contact_key, contact_val in v.items():

                                        if v is not None:

                                            tmp_out = '{0}{1}{2}'.format(
                                                contact_key,
                                                ': ',
                                                contact_val
                                            )

                                            output += generate_output(
                                                line='4',
                                                value=tmp_out,
                                                colorize=colorize
                                            )
                        elif key == 'nameservers':

                            for v in val:
                                output += generate_output(
                                    line='3',
                                    value=v,
                                    colorize=colorize
                                )
                        else:

                            for v in val.split('\n'):
                                output += generate_output(
                                    line='3',
                                    value=v,
                                    colorize=colorize
                                )

                    else:

                        output += generate_output(
                            line='2',
                            short=(
                                HR_WHOIS_NIR['nets'][key]['_short'] if (
                                    hr) else key
                            ),
                            name=HR_WHOIS_NIR['nets'][key]['_name'] if (
                                hr and show_name) else None,
                            value=val,
                            colorize=colorize
                        )

        else:

            output += 'None'

        return output

    def lookup_whois(self, hr=True, show_name=False, colorize=True, **kwargs):
        """
        The function for wrapping IPWhois.lookup_whois() and generating
        formatted CLI output.

        Args:
            hr (:obj:`bool`): Enable human readable key translations. Defaults
                to True.
            show_name (:obj:`bool`): Show human readable name (default is to
                only show short). Defaults to False.
            colorize (:obj:`bool`): Colorize the console output with ANSI
                colors. Defaults to True.
            kwargs: Arguments to pass to IPWhois.lookup_whois().

        Returns:
            str: The generated output.
        """

        # Perform the RDAP lookup
        ret = self.obj.lookup_whois(**kwargs)

        if script_args.json:

            output = json.dumps(ret)

        else:

            # Header
            output = self.generate_output_header(query_type='Legacy Whois')

            # ASN
            output += self.generate_output_asn(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            # Network
            output += self.generate_output_whois_nets(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            # Referral
            output += self.generate_output_whois_referral(
                json_data=ret, hr=hr, show_name=show_name, colorize=colorize
            )
            output += self.generate_output_newline(colorize=colorize)

            if 'nir' in ret:

                # NIR
                output += self.generate_output_nir(
                    json_data=ret, hr=hr, show_name=show_name,
                    colorize=colorize
                )
                output += self.generate_output_newline(colorize=colorize)

        return output


if script_args.addr:

    results = IPWhoisCLI(
        addr=script_args.addr[0],
        timeout=script_args.timeout,
        proxy_http=script_args.proxy_http if (
            script_args.proxy_http and len(script_args.proxy_http) > 0
        ) else None,
        proxy_https=script_args.proxy_https if (
            script_args.proxy_https and len(script_args.proxy_https) > 0
        ) else None
    )

    if script_args.whois:

        print(results.lookup_whois(
            hr=script_args.hr,
            show_name=script_args.show_name,
            colorize=script_args.colorize,
            inc_raw=script_args.inc_raw,
            retry_count=script_args.retry_count,
            get_referral=script_args.get_referral,
            extra_blacklist=script_args.extra_blacklist.split(',') if (
                script_args.extra_blacklist and
                len(script_args.extra_blacklist) > 0) else None,
            ignore_referral_errors=script_args.ignore_referral_errors,
            field_list=script_args.field_list.split(',') if (
                script_args.field_list and
                len(script_args.field_list) > 0) else None,
            extra_org_map=script_args.extra_org_map,
            inc_nir=(not script_args.exclude_nir),
            nir_field_list=script_args.nir_field_list.split(',') if (
                script_args.nir_field_list and
                len(script_args.nir_field_list) > 0) else None,
            asn_methods=script_args.asn_methods.split(',') if (
                script_args.asn_methods and
                len(script_args.asn_methods) > 0) else None,
            get_asn_description=(not script_args.skip_asn_description)
        ))

    else:

        print(results.lookup_rdap(
            hr=script_args.hr,
            show_name=script_args.show_name,
            colorize=script_args.colorize,
            inc_raw=script_args.inc_raw,
            retry_count=script_args.retry_count,
            depth=script_args.depth,
            excluded_entities=script_args.excluded_entities.split(',') if (
                script_args.excluded_entities and
                len(script_args.excluded_entities) > 0) else None,
            bootstrap=script_args.bootstrap,
            rate_limit_timeout=script_args.rate_limit_timeout,
            extra_org_map=script_args.extra_org_map,
            inc_nir=(not script_args.exclude_nir),
            nir_field_list=script_args.nir_field_list.split(',') if (
                script_args.nir_field_list and
                len(script_args.nir_field_list) > 0) else None,
            asn_methods=script_args.asn_methods.split(',') if (
                script_args.asn_methods and
                len(script_args.asn_methods) > 0) else None,
            get_asn_description=(not script_args.skip_asn_description)
        ))
