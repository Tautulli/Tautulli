# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
from __future__ import unicode_literals

from future.builtins import zip
from future.builtins import str

import arrow
import base64
import cloudinary
from cloudinary.api import delete_resources_by_tag
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
from collections import OrderedDict
import datetime
from functools import reduce, wraps
import hashlib
import imghdr
from future.moves.itertools import islice, zip_longest
import ipwhois
import ipwhois.exceptions
import ipwhois.utils
from IPy import IP
import json
import math
import operator
import os
import re
import shlex
import socket
import string
import sys
import time
import unicodedata
from future.moves.urllib.parse import urlencode
from xml.dom import minidom
import xmltodict

import plexpy
if plexpy.PYTHON2:
    import common
    import logger
    import request
    from api2 import API2
else:
    from plexpy import common
    from plexpy import logger
    from plexpy import request
    from plexpy.api2 import API2


def addtoapi(*dargs, **dkwargs):
    """ Helper decorator that adds function to the API class.
        is used to reuse as much code as possible

        args:
            dargs: (string, optional) Used to rename a function

        Example:
            @addtoapi("i_was_renamed", "im_a_second_alias")
            @addtoapi()

    """
    def rd(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        if dargs:
            # To rename the function if it sucks.. and
            # allow compat with old api.
            for n in dargs:
                if function.__doc__ and len(function.__doc__):
                    function.__doc__ = function.__doc__.strip()
                setattr(API2, n, function)
            return wrapper

        if function.__doc__ and len(function.__doc__):
            function.__doc__ = function.__doc__.strip()
        setattr(API2, function.__name__, function)
        return wrapper

    return rd


def checked(variable):
    if variable:
        return 'Checked'
    else:
        return ''


def radio(variable, pos):

    if variable == pos:
        return 'Checked'
    else:
        return ''


def latinToAscii(unicrap, replace=False):
    """
    From couch potato
    """
    xlate = {
        0xc0: 'A', 0xc1: 'A', 0xc2: 'A', 0xc3: 'A', 0xc4: 'A', 0xc5: 'A',
        0xc6: 'Ae', 0xc7: 'C',
        0xc8: 'E', 0xc9: 'E', 0xca: 'E', 0xcb: 'E', 0x86: 'e',
        0xcc: 'I', 0xcd: 'I', 0xce: 'I', 0xcf: 'I',
        0xd0: 'Th', 0xd1: 'N',
        0xd2: 'O', 0xd3: 'O', 0xd4: 'O', 0xd5: 'O', 0xd6: 'O', 0xd8: 'O',
        0xd9: 'U', 0xda: 'U', 0xdb: 'U', 0xdc: 'U',
        0xdd: 'Y', 0xde: 'th', 0xdf: 'ss',
        0xe0: 'a', 0xe1: 'a', 0xe2: 'a', 0xe3: 'a', 0xe4: 'a', 0xe5: 'a',
        0xe6: 'ae', 0xe7: 'c',
        0xe8: 'e', 0xe9: 'e', 0xea: 'e', 0xeb: 'e', 0x0259: 'e',
        0xec: 'i', 0xed: 'i', 0xee: 'i', 0xef: 'i',
        0xf0: 'th', 0xf1: 'n',
        0xf2: 'o', 0xf3: 'o', 0xf4: 'o', 0xf5: 'o', 0xf6: 'o', 0xf8: 'o',
        0xf9: 'u', 0xfa: 'u', 0xfb: 'u', 0xfc: 'u',
        0xfd: 'y', 0xfe: 'th', 0xff: 'y',
        0xa1: '!', 0xa2: '{cent}', 0xa3: '{pound}', 0xa4: '{currency}',
        0xa5: '{yen}', 0xa6: '|', 0xa7: '{section}', 0xa8: '{umlaut}',
        0xa9: '{C}', 0xaa: '{^a}', 0xab: '&lt;&lt;', 0xac: '{not}',
        0xad: '-', 0xae: '{R}', 0xaf: '_', 0xb0: '{degrees}',
        0xb1: '{+/-}', 0xb2: '{^2}', 0xb3: '{^3}', 0xb4: "'",
        0xb5: '{micro}', 0xb6: '{paragraph}', 0xb7: '*', 0xb8: '{cedilla}',
        0xb9: '{^1}', 0xba: '{^o}', 0xbb: '&gt;&gt;',
        0xbc: '{1/4}', 0xbd: '{1/2}', 0xbe: '{3/4}', 0xbf: '?',
        0xd7: '*', 0xf7: '/'
    }

    r = ''
    if unicrap:
        for i in unicrap:
            if ord(i) in xlate:
                r += xlate[ord(i)]
            elif ord(i) >= 0x80:
                if replace:
                    r += '?'
            else:
                r += str(i)

    return r


def convert_milliseconds(ms):

    seconds = ms // 1000
    gmtime = time.gmtime(seconds)
    if seconds > 3600:
        minutes = time.strftime("%H:%M:%S", gmtime)
    else:
        minutes = time.strftime("%M:%S", gmtime)

    return minutes


def convert_milliseconds_to_seconds(ms):
    if str(ms).isdigit():
        seconds = float(ms) / 1000
        return math.trunc(seconds)
    return 0


def convert_milliseconds_to_minutes(ms):
    if str(ms).isdigit():
        seconds = float(ms) / 1000
        minutes = round(seconds / 60, 0)
        return math.trunc(minutes)
    return 0


def seconds_to_minutes(s):
    if str(s).isdigit():
        minutes = round(s / 60, 0)
        return math.trunc(minutes)
    return 0


def convert_seconds(s):

    gmtime = time.gmtime(s)
    if s > 3600:
        minutes = time.strftime("%H:%M:%S", gmtime)
    else:
        minutes = time.strftime("%M:%S", gmtime)

    return minutes


def convert_seconds_to_minutes(s):

    if str(s).isdigit():
        minutes = round(float(s) / 60, 0)

        return math.trunc(minutes)

    return 0


def timestamp():
    return int(time.time())


def today():
    today = datetime.date.today()
    yyyymmdd = datetime.date.isoformat(today)

    return yyyymmdd


def utc_now_iso():
    utcnow = datetime.datetime.utcnow()

    return utcnow.isoformat()


def now(sep=False):
    return timestamp_to_YMDHMS(timestamp(), sep=sep)


def timestamp_to_YMDHMS(ts, sep=False):
    dt = timestamp_to_datetime(ts)
    if sep:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y%m%d%H%M%S")


def timestamp_to_datetime(ts):
    return datetime.datetime.fromtimestamp(ts)


def iso_to_YMD(iso):
    return iso_to_datetime(iso).strftime("%Y-%m-%d")


def iso_to_datetime(iso):
    return arrow.get(iso).datetime


def datetime_to_iso(dt, to_date=False):
    if isinstance(dt, datetime.datetime):
        if to_date:
            dt = dt.date()
        return dt.isoformat()
    return dt


def human_duration(ms, sig='dhm', units='ms', return_seconds=300000):
    factors = {'d': 86400000,
               'h': 3600000,
               'm': 60000,
               's': 1000,
               'ms': 1}

    if str(ms).isdigit() and ms > 0:
        if return_seconds and ms < return_seconds:
            sig = 'dhms'

        ms = ms * factors[units]

        d, h = divmod(ms, factors['d'])
        h, m = divmod(h, factors['h'])
        m, s = divmod(m, factors['m'])
        s, ms = divmod(s, factors['s'])

        hd_list = []
        if sig >= 'd' and d > 0:
            d = d + 1 if sig == 'd' and h >= 12 else d
            hd_list.append(str(d) + ' day' + ('s' if d > 1 else ''))

        if sig >= 'dh' and h > 0:
            h = h + 1 if sig == 'dh' and m >= 30 else h
            hd_list.append(str(h) + ' hr' + ('s' if h > 1 else ''))

        if sig >= 'dhm' and m > 0:
            m = m + 1 if sig == 'dhm' and s >= 30 else m
            hd_list.append(str(m) + ' min' + ('s' if m > 1 else ''))

        if sig >= 'dhms' and s > 0:
            hd_list.append(str(s) + ' sec' + ('s' if s > 1 else ''))

        hd = ' '.join(hd_list)
    else:
        hd = '0'

    return hd


def format_timedelta_Hms(td):
    s = td.total_seconds()
    hours = s // 3600
    minutes = (s % 3600) // 60
    seconds = s % 60
    return '{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(seconds))


def get_age(date):

    try:
        split_date = date.split('-')
    except:
        return False

    try:
        days_old = int(split_date[0]) * 365 + int(split_date[1]) * 30 + int(split_date[2])
    except IndexError:
        days_old = False

    return days_old


def bytes_to_mb(bytes):

    mb = float(bytes) / 1048576
    size = '%.1f MB' % mb
    return size


def mb_to_bytes(mb_str):
    result = re.search('^(\d+(?:\.\d+)?)\s?(?:mb)?', mb_str, flags=re.I)
    if result:
        return int(float(result.group(1)) * 1048576)


def piratesize(size):
    split = size.split(" ")
    factor = float(split[0])
    unit = split[1].upper()

    if unit == 'MiB':
        size = factor * 1048576
    elif unit == 'MB':
        size = factor * 1000000
    elif unit == 'GiB':
        size = factor * 1073741824
    elif unit == 'GB':
        size = factor * 1000000000
    elif unit == 'KiB':
        size = factor * 1024
    elif unit == 'KB':
        size = factor * 1000
    elif unit == "B":
        size = factor
    else:
        size = 0

    return size


def replace_all(text, dic, normalize=False):

    if not text:
        return ''

    for i, j in dic.items():
        if normalize:
            try:
                if sys.platform == 'darwin':
                    j = unicodedata.normalize('NFD', j)
                else:
                    j = unicodedata.normalize('NFC', j)
            except TypeError:
                j = unicodedata.normalize('NFC', j.decode(plexpy.SYS_ENCODING, 'replace'))
        text = text.replace(i, j)
    return text


def replace_illegal_chars(string, type="file"):
    if type == "file":
        string = re.sub('[\?"*:|<>/]', '_', string)
    if type == "folder":
        string = re.sub('[:\?<>"|]', '_', string)

    return string


def cleanName(string):

    pass1 = latinToAscii(string).lower()
    out_string = re.sub('[\.\-\/\!\@\#\$\%\^\&\*\(\)\+\-\"\'\,\;\:\[\]\{\}\<\>\=\_]', '', pass1).encode('utf-8')

    return out_string


def cleanTitle(title):

    title = re.sub('[\.\-\/\_]', ' ', title).lower()

    # Strip out extra whitespace
    title = ' '.join(title.split())

    title = title.title()

    return title


def clean_filename(filename, replace='_'):
    whitelist = "-_.()[] {}{}".format(string.ascii_letters, string.digits)
    cleaned_filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    cleaned_filename = ''.join(c if c in whitelist else replace for c in cleaned_filename)
    return cleaned_filename


def split_strip(s, delimiter=','):
    return [x.strip() for x in str(s).split(delimiter) if x.strip()]


def split_path(f):
    """
    Split a path into components, starting with the drive letter (if any). Given
    a path, os.path.join(*split_path(f)) should be path equal to f.
    """

    components = []
    drive, path = os.path.splitdrive(f)

    # Strip the folder from the path, iterate until nothing is left
    while True:
        path, folder = os.path.split(path)

        if folder:
            components.append(folder)
        else:
            if path:
                components.append(path)

            break

    # Append the drive (if any)
    if drive:
        components.append(drive)

    # Reverse components
    components.reverse()

    # Done
    return components


def extract_logline(s):
    # Default log format
    pattern = re.compile(r'(?P<timestamp>.*?)\s\-\s(?P<level>.*?)\s*\:\:\s(?P<thread>.*?)\s\:\s(?P<message>.*)', re.VERBOSE)
    match = pattern.match(s)
    if match:
        timestamp = match.group("timestamp")
        level = match.group("level")
        thread = match.group("thread")
        message = match.group("message")
        return (timestamp, level, thread, message)
    else:
        return None


def split_string(mystring, splitvar=','):
    mylist = []
    for each_word in mystring.split(splitvar):
        mylist.append(each_word.strip())
    return mylist


def create_https_certificates(ssl_cert, ssl_key):
    """
    Create a self-signed HTTPS certificate and store in it in
    'ssl_cert' and 'ssl_key'. Method assumes pyOpenSSL is installed.

    This code is stolen from SickBeard (http://github.com/midgetspy/Sick-Beard).
    """
    try:
        from OpenSSL import crypto
    except ImportError:
        logger.error("Unable to generate self-signed certificates: Missing OpenSSL module.")
        return False
    from certgen import createKeyPair, createSelfSignedCertificate, TYPE_RSA

    issuer = common.PRODUCT
    serial = timestamp()
    not_before = 0
    not_after = 60 * 60 * 24 * 365 * 10  # ten years
    domains = ['DNS:' + d.strip() for d in plexpy.CONFIG.HTTPS_DOMAIN.split(',') if d]
    ips = ['IP:' + d.strip() for d in plexpy.CONFIG.HTTPS_IP.split(',') if d]
    alt_names = ','.join(domains + ips).encode('utf-8')

    # Create the self-signed Tautulli certificate
    logger.debug("Generating self-signed SSL certificate.")
    pkey = createKeyPair(TYPE_RSA, 2048)
    cert = createSelfSignedCertificate(issuer, pkey, serial, not_before, not_after, alt_names)

    # Save the key and certificate to disk
    try:
        with open(ssl_cert, "w") as fp:
            fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode('utf-8'))
        with open(ssl_key, "w") as fp:
            fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey).decode('utf-8'))
    except IOError as e:
        logger.error("Error creating SSL key and certificate: %s", e)
        return False

    return True


def cast_to_int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def cast_to_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0


def helper_divmod(a, b):
    try:
        return divmod(a, b)
    except (ValueError, TypeError):
        return 0


def helper_len(s):
    try:
        return len(s)
    except (ValueError, TypeError):
        return 0


def helper_round(n, ndigits=None):
    try:
        return round(n, ndigits)
    except (ValueError, TypeError):
        return 0


def convert_xml_to_json(xml):
    o = xmltodict.parse(xml)
    return json.dumps(o)


def convert_xml_to_dict(xml):
    o = xmltodict.parse(xml)
    return o


def get_percent(value1, value2):

    value1 = cast_to_float(value1)
    value2 = cast_to_float(value2)

    if value1 != 0 and value2 != 0:
        percent = (value1 / value2) * 100
    else:
        percent = 0

    return math.trunc(round(percent, 0))


def hex_to_int(hex):
    try:
        return int(hex, 16)
    except (ValueError, TypeError):
        return 0


def parse_xml(unparsed=None):
    if unparsed:
        try:
            xml_parse = minidom.parseString(unparsed)
            return xml_parse
        except Exception as e:
            logger.warn("Error parsing XML. %s" % e)
            return []
        except:
            logger.warn("Error parsing XML.")
            return []
    else:
        logger.warn("XML parse request made but no data received.")
        return []


def get_xml_attr(xml_key, attribute, return_bool=False, default_return=''):
    """
    Validate xml keys to make sure they exist and return their attribute value, return blank value is none found
    """
    if xml_key.getAttribute(attribute):
        if return_bool:
            return True
        else:
            return xml_key.getAttribute(attribute)
    else:
        if return_bool:
            return False
        else:
            return default_return


def process_json_kwargs(json_kwargs):
    params = {}
    if json_kwargs:
        params = json.loads(json_kwargs)

    return params


def process_datatable_rows(rows, json_data, default_sort, search_cols=None, sort_keys=None):
    if search_cols is None:
        search_cols = []
    if sort_keys is None:
        sort_keys = {}

    results = []

    total_count = len(rows)

    # Search results
    search_value = json_data['search']['value'].lower()
    if search_value:
        searchable_columns = [d['data'] for d in json_data['columns'] if d['searchable']] + search_cols
        for row in rows:
            for k, v in row.items():
                if k in sort_keys:
                    value = sort_keys[k].get(v, v)
                else:
                    value = v
                value = str(value).lower()
                if k in searchable_columns and search_value in value:
                    results.append(row)
                    break
    else:
        results = rows

    filtered_count = len(results)

    # Sort results
    results = sorted(results, key=lambda k: k[default_sort].lower())
    sort_order = json_data['order']
    for order in reversed(sort_order):
        sort_key = json_data['columns'][int(order['column'])]['data']
        reverse = True if order['dir'] == 'desc' else False
        results = sorted(results, key=lambda k: sort_helper(k, sort_key, sort_keys), reverse=reverse)

    # Paginate results
    results = results[json_data['start']:(json_data['start'] + json_data['length'])]

    data = {
        'results': results,
        'total_count': total_count,
        'filtered_count': filtered_count
    }

    return data


def sort_helper(k, sort_key, sort_keys):
    v = k[sort_key]
    if sort_key in sort_keys:
        v = sort_keys[sort_key].get(k[sort_key], v)
    if isinstance(v, str):
        v = v.lower()
    return v


def sanitize_out(*dargs, **dkwargs):
    """ Helper decorator that sanitized the output
    """
    def rd(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            return sanitize(function(*args, **kwargs))
        return wrapper
    return rd


def sanitize(obj):
    if isinstance(obj, str):
        return str(obj).replace('<', '&lt;').replace('>', '&gt;')
    elif isinstance(obj, list):
        return [sanitize(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(sanitize(list(obj)))
    else:
        return obj


def is_public_ip(host):
    ip = is_valid_ip(get_ip(host))
    if ip and ip.iptype() == 'PUBLIC':
        return True
    return False


def get_ip(host):
    ip_address = ''
    if is_valid_ip(host):
        return host
    elif not re.match(r'^[0-9]+(?:\.[0-9]+){3}(?!\d*-[a-z0-9]{6})$', host):
        try:
            ip_address = socket.getaddrinfo(host, None)[0][4][0]
            logger.debug("IP Checker :: Resolved %s to %s." % (host, ip_address))
        except:
            logger.error("IP Checker :: Bad IP or hostname provided: %s." % host)
    return ip_address


def is_valid_ip(address):
    try:
        return IP(address)
    except TypeError:
        return False
    except ValueError:
        return False


def whois_lookup(ip_address):

    nets = []
    err = None
    try:
        whois = ipwhois.IPWhois(ip_address).lookup_whois(retry_count=0,
                                                         asn_methods=['dns', 'whois', 'http'])
        countries = ipwhois.utils.get_countries()
        nets = whois['nets']
        for net in nets:
            net['country'] = countries.get(net['country'])
            if net['postal_code']:
                 net['postal_code'] = net['postal_code'].replace('-', ' ')
    except ValueError as e:
        err = 'Invalid IP address provided: %s.' % ip_address
    except ipwhois.exceptions.IPDefinedError as e:
        err = '%s' % e
    except ipwhois.exceptions.ASNRegistryError as e:
        err = '%s' % e
    except Exception as e:
        err = 'Error: %s' % e

    host = ''
    try:
        host = ipwhois.Net(ip_address).get_host(retry_count=0)[0]
    except Exception as e:
        host = 'Not available'

    whois_info = {"host": host,
                  "nets": nets
                  }

    if err:
        whois_info['error'] = err

    return whois_info


# Taken from SickRage
def anon_url(*url):
    """
    Return a URL string consisting of the Anonymous redirect URL and an arbitrary number of values appended.
    """
    return '' if None in url else '%s%s' % (plexpy.CONFIG.ANON_REDIRECT, ''.join(str(s) for s in url))


def get_img_service(include_self=False):
    if plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS == 1:
        return 'imgur'
    elif plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS == 2 and include_self:
        return 'self-hosted'
    elif plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS == 3:
        return 'cloudinary'
    else:
        return None


def upload_to_imgur(img_data, img_title='', rating_key='', fallback=''):
    """ Uploads an image to Imgur """
    img_url = delete_hash = ''

    if not plexpy.CONFIG.IMGUR_CLIENT_ID:
        logger.error("Tautulli Helpers :: Cannot upload image to Imgur. No Imgur client id specified in the settings.")
        return img_url, delete_hash

    headers = {'Authorization': 'Client-ID %s' % plexpy.CONFIG.IMGUR_CLIENT_ID}
    data = {'image': base64.b64encode(img_data),
            'title': img_title.encode('utf-8'),
            'name': str(rating_key) + '.png',
            'type': 'png'}

    response, err_msg, req_msg = request.request_response2('https://api.imgur.com/3/image', 'POST',
                                                           headers=headers, data=data)

    if response and not err_msg:
        logger.debug("Tautulli Helpers :: Image '{}' ({}) uploaded to Imgur.".format(img_title, fallback))
        imgur_response_data = response.json().get('data')
        img_url = imgur_response_data.get('link', '').replace('http://', 'https://')
        delete_hash = imgur_response_data.get('deletehash', '')
    else:
        if err_msg:
            logger.error("Tautulli Helpers :: Unable to upload image '{}' ({}) to Imgur: {}".format(img_title, fallback, err_msg))
        else:
            logger.error("Tautulli Helpers :: Unable to upload image '{}' ({}) to Imgur.".format(img_title, fallback))

        if req_msg:
            logger.debug("Tautulli Helpers :: Request response: {}".format(req_msg))

    return img_url, delete_hash


def delete_from_imgur(delete_hash, img_title='', fallback=''):
    """ Deletes an image from Imgur """
    if not plexpy.CONFIG.IMGUR_CLIENT_ID:
        logger.error("Tautulli Helpers :: Cannot delete image from Imgur. No Imgur client id specified in the settings.")
        return False

    headers = {'Authorization': 'Client-ID %s' % plexpy.CONFIG.IMGUR_CLIENT_ID}

    response, err_msg, req_msg = request.request_response2('https://api.imgur.com/3/image/%s' % delete_hash, 'DELETE',
                                                           headers=headers)

    if response and not err_msg:
        logger.debug("Tautulli Helpers :: Image '{}' ({}) deleted from Imgur.".format(img_title, fallback))
        return True
    else:
        if err_msg:
            logger.error("Tautulli Helpers :: Unable to delete image '{}' ({}) from Imgur: {}".format(img_title, fallback, err_msg))
        else:
            logger.error("Tautulli Helpers :: Unable to delete image '{}' ({}) from Imgur.".format(img_title, fallback))
        return False


def upload_to_cloudinary(img_data, img_title='', rating_key='', fallback=''):
    """ Uploads an image to Cloudinary """
    img_url = ''

    if not plexpy.CONFIG.CLOUDINARY_CLOUD_NAME or not plexpy.CONFIG.CLOUDINARY_API_KEY or not plexpy.CONFIG.CLOUDINARY_API_SECRET:
        logger.error("Tautulli Helpers :: Cannot upload image to Cloudinary. Cloudinary settings not specified in the settings.")
        return img_url

    cloudinary.config(
        cloud_name=plexpy.CONFIG.CLOUDINARY_CLOUD_NAME,
        api_key=plexpy.CONFIG.CLOUDINARY_API_KEY,
        api_secret=plexpy.CONFIG.CLOUDINARY_API_SECRET
    )

    # Cloudinary library has very poor support for non-ASCII characters on Python 2
    if plexpy.PYTHON2:
        _img_title = latinToAscii(img_title, replace=True)
    else:
        _img_title = img_title

    try:
        response = upload((img_title, img_data),
                          public_id='{}_{}'.format(fallback, rating_key),
                          tags=['tautulli', fallback, str(rating_key)],
                          context={'title': _img_title, 'rating_key': str(rating_key), 'fallback': fallback})
        logger.debug("Tautulli Helpers :: Image '{}' ({}) uploaded to Cloudinary.".format(img_title, fallback))
        img_url = response.get('url', '')
    except Exception as e:
        logger.error("Tautulli Helpers :: Unable to upload image '{}' ({}) to Cloudinary: {}".format(img_title, fallback, e))

    return img_url


def delete_from_cloudinary(rating_key=None, delete_all=False):
    """ Deletes an image from Cloudinary """
    if not plexpy.CONFIG.CLOUDINARY_CLOUD_NAME or not plexpy.CONFIG.CLOUDINARY_API_KEY or not plexpy.CONFIG.CLOUDINARY_API_SECRET:
        logger.error("Tautulli Helpers :: Cannot delete image from Cloudinary. Cloudinary settings not specified in the settings.")
        return False

    cloudinary.config(
        cloud_name=plexpy.CONFIG.CLOUDINARY_CLOUD_NAME,
        api_key=plexpy.CONFIG.CLOUDINARY_API_KEY,
        api_secret=plexpy.CONFIG.CLOUDINARY_API_SECRET
    )

    if delete_all:
        delete_resources_by_tag('tautulli')
        logger.debug("Tautulli Helpers :: Deleted all images from Cloudinary.")
    elif rating_key:
        delete_resources_by_tag(str(rating_key))
        logger.debug("Tautulli Helpers :: Deleted images from Cloudinary with rating_key {}.".format(rating_key))
    else:
        logger.debug("Tautulli Helpers :: Unable to delete images from Cloudinary: No rating_key provided.")

    return True


def cloudinary_transform(rating_key=None, width=1000, height=1500, opacity=100, background='000000', blur=0,
                         img_format='png', img_title='', fallback=None):
    url = ''

    if not plexpy.CONFIG.CLOUDINARY_CLOUD_NAME or not plexpy.CONFIG.CLOUDINARY_API_KEY or not plexpy.CONFIG.CLOUDINARY_API_SECRET:
        logger.error("Tautulli Helpers :: Cannot transform image on Cloudinary. Cloudinary settings not specified in the settings.")
        return url

    cloudinary.config(
        cloud_name=plexpy.CONFIG.CLOUDINARY_CLOUD_NAME,
        api_key=plexpy.CONFIG.CLOUDINARY_API_KEY,
        api_secret=plexpy.CONFIG.CLOUDINARY_API_SECRET
    )

    img_options = {'format': img_format,
                   'fetch_format': 'auto',
                   'quality': 'auto',
                   'version': timestamp(),
                   'secure': True}

    if width != 1000:
        img_options['width'] = str(width)
        img_options['crop'] = 'fill'
    if height != 1500:
        img_options['height'] = str(height)
        img_options['crop'] = 'fill'
    if opacity != 100:
        img_options['opacity'] = opacity
    if background != '000000':
        img_options['background'] = 'rgb:{}'.format(background)
    if blur != 0:
        img_options['effect'] = 'blur:{}'.format(blur * 100)

    try:
        url, options = cloudinary_url('{}_{}'.format(fallback, rating_key), **img_options)
        logger.debug("Tautulli Helpers :: Image '{}' ({}) transformed on Cloudinary.".format(img_title, fallback))
    except Exception as e:
        logger.error("Tautulli Helpers :: Unable to transform image '{}' ({}) on Cloudinary: {}".format(img_title, fallback, e))

    return url


def cache_image(url, image=None):
    """
    Saves an image to the cache directory.
    If no image is provided, tries to return the image from the cache directory.
    """
    # Create image directory if it doesn't exist
    imgdir = os.path.join(plexpy.CONFIG.CACHE_DIR, 'images/')
    if not os.path.exists(imgdir):
        logger.debug("Tautulli Helpers :: Creating image cache directory at %s" % imgdir)
        os.makedirs(imgdir)

    # Create a hash of the url to use as the filename
    imghash = hashlib.md5(url).hexdigest()
    imagefile = os.path.join(imgdir, imghash)

    # If an image is provided, save it to the cache directory
    if image:
        try:
            with open(imagefile, 'wb') as cache_file:
                cache_file.write(image)
        except IOError as e:
            logger.error("Tautulli Helpers :: Failed to cache image %s: %s" % (imagefile, e))

    # Try to return the image from the cache directory
    if os.path.isfile(imagefile):
        imagetype = 'image/' + imghdr.what(os.path.abspath(imagefile))
    else:
        imagefile = None
        imagetype = 'image/jpeg'

    return imagefile, imagetype


def build_datatables_json(kwargs, dt_columns, default_sort_col=None):
    """ Builds datatables json data

        dt_columns:    list of tuples [("column name", "orderable", "searchable"), ...]
    """

    columns = [{"data": c[0], "orderable": c[1], "searchable": c[2]} for c in dt_columns]

    if not default_sort_col:
        default_sort_col = dt_columns[0][0]

    column_names = [c[0] for c in dt_columns]
    order_columns = [c.strip() for c in kwargs.pop("order_column", default_sort_col).split(",")]
    order_dirs = [d.strip() for d in kwargs.pop("order_dir", "desc").split(",")]

    order = []
    for c, d in zip_longest(order_columns, order_dirs, fillvalue=""):
        try:
            order_column = column_names.index(c)
        except ValueError:
            continue

        if d.lower() in ("asc", "desc"):
            order_dir = d.lower()
        else:
            order_dir = "desc"

        order.append({"column": order_column, "dir": order_dir})

    # Build json data
    json_data = {"draw": 1,
                 "columns": columns,
                 "order": order,
                 "start": int(kwargs.pop("start", 0)),
                 "length": int(kwargs.pop("length", 25)),
                 "search": {"value": kwargs.pop("search", "")}
                 }
    return json.dumps(json_data)


def human_file_size(bytes, si=True):
    if str(bytes).isdigit():
        bytes = cast_to_float(bytes)
    else:
        return bytes

    #thresh = 1000 if si else 1024
    thresh = 1024  # Always divide by 2^10 but display SI units
    if bytes < thresh:
        return str(bytes) + ' B'

    if si:
        units = ('kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    else:
        units = ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')

    u = -1

    while bytes >= thresh and u < len(units):
        bytes /= thresh
        u += 1

    return "{0:.2f} {1}".format(bytes, units[u])


def parse_condition_logic_string(s, num_cond=0):
    """ Parse a logic string into a nested list
    Based on http://stackoverflow.com/a/23185606
    """
    valid_tokens = re.compile(r'(\(|\)|and|or)')
    conditions_pattern = re.compile(r'{\d+}')

    tokens = [x.strip() for x in re.split(valid_tokens, s.lower()) if x.strip()]

    stack = [[]]

    cond_next = True
    bool_next = False
    open_bracket_next = True
    close_bracket_next = False
    nest_and = 0
    nest_nest_and = 0

    for i, x in enumerate(tokens):
        if open_bracket_next and x == '(':
            stack[-1].append([])
            stack.append(stack[-1][-1])
            cond_next = True
            bool_next = False
            open_bracket_next = True
            close_bracket_next = False
            if nest_and:
                nest_nest_and += 1

        elif close_bracket_next and x == ')':
            stack.pop()
            if not stack:
                raise ValueError('opening bracket is missing')
            cond_next = False
            bool_next = True
            open_bracket_next = False
            close_bracket_next = True
            if nest_and > 0 and nest_nest_and > 0 and nest_and == nest_nest_and:
                stack.pop()
                nest_and -= 1
                nest_nest_and -= 1

        elif cond_next and re.match(conditions_pattern, x):
            try:
                num = int(x[1:-1])
            except:
                raise ValueError('invalid condition logic')
            if not 0 < num <= num_cond:
                raise ValueError('invalid condition number in condition logic')
            stack[-1].append(num)
            cond_next = False
            bool_next = True
            open_bracket_next = False
            close_bracket_next = True
            if nest_and > nest_nest_and:
                stack.pop()
                nest_and -= 1

        elif bool_next and x == 'and' and i < len(tokens)-1:
            stack[-1].append([])
            stack.append(stack[-1][-1])
            stack[-1].append(stack[-2].pop(-2))
            stack[-1].append(x)
            cond_next = True
            bool_next = False
            open_bracket_next = True
            close_bracket_next = False
            nest_and += 1

        elif bool_next and x == 'or' and i < len(tokens)-1:
            stack[-1].append(x)
            cond_next = True
            bool_next = False
            open_bracket_next = True
            close_bracket_next = False

        else:
            raise ValueError('invalid condition logic')

    if len(stack) > 1:
        raise ValueError('closing bracket is missing')

    return stack.pop()


def nested_list_to_string(l):
    for i, x in enumerate(l):
        if isinstance(x, list):
            l[i] = nested_list_to_string(x)
    s = '(' + ' '.join(l) + ')'
    return s


def eval_logic_groups_to_bool(logic_groups, eval_conds):
    first_cond = logic_groups[0]

    if isinstance(first_cond, list):
        result = eval_logic_groups_to_bool(first_cond, eval_conds)
    else:
        result = eval_conds[first_cond]

    for op, cond in zip(logic_groups[1::2], logic_groups[2::2]):
        if isinstance(cond, list):
            eval_cond = eval_logic_groups_to_bool(cond, eval_conds)
        else:
            eval_cond = eval_conds[cond]

        if op == 'and':
            result = result and eval_cond
        elif op == 'or':
            result = result or eval_cond

    return result


def get_plexpy_url(hostname=None):
    if plexpy.CONFIG.ENABLE_HTTPS:
        scheme = 'https'
    else:
        scheme = 'http'

    if hostname is None and plexpy.CONFIG.HTTP_HOST == '0.0.0.0':
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.connect(('<broadcast>', 0))
            hostname = s.getsockname()[0]
        except socket.error:
            try:
                hostname = socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                pass

        if not hostname:
            hostname = 'localhost'
    elif hostname == 'localhost' and plexpy.CONFIG.HTTP_HOST != '0.0.0.0':
        hostname = plexpy.CONFIG.HTTP_HOST
    else:
        hostname = hostname or plexpy.CONFIG.HTTP_HOST

    if plexpy.HTTP_PORT not in (80, 443):
        port = ':' + str(plexpy.HTTP_PORT)
    else:
        port = ''

    if plexpy.HTTP_ROOT is not None and plexpy.HTTP_ROOT.strip('/'):
        root = '/' + plexpy.HTTP_ROOT.strip('/')
    else:
        root = ''

    return scheme + '://' + hostname + port + root


def momentjs_to_arrow(format, duration=False):
    invalid_formats = ['Mo', 'DDDo', 'do']
    if duration:
        invalid_formats += ['A', 'a']
    for f in invalid_formats:
        format = format.replace(f, '')
    return format


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)


def chunk(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


def traverse_map(obj, func):
    if isinstance(obj, list):
        new_obj = []
        for i in obj:
            new_obj.append(traverse_map(i, func))

    elif isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            new_obj[traverse_map(k, func)] = traverse_map(v, func)

    else:
        new_obj = func(obj)

    return new_obj


def split_args(args=None):
    if isinstance(args, list):
        return args
    elif isinstance(args, str):
        if plexpy.PYTHON2:
            args = args.encode('utf-8')
        args = shlex.split(args)
        if plexpy.PYTHON2:
            args = [a.decode('utf-8') for a in args]
        return args
    return []


def mask_config_passwords(config):
    if isinstance(config, list):
        for cfg in config:
            if 'password' in cfg.get('name', '') and cfg.get('value', '') != '':
                cfg['value'] = '    '

    elif isinstance(config, dict):
        for cfg, val in config.items():
            # Check for a password config keys and if the password is not blank
            if 'password' in cfg and val != '':
                # Set the password to blank so it is not exposed in the HTML form
                config[cfg] = '    '

    return config


def bool_true(value, return_none=False):
    if value is None and return_none:
        return None
    elif value is True or value == 1:
        return True
    elif isinstance(value, str) and value.lower() in ('1', 'true', 't', 'yes', 'y', 'on'):
        return True
    return False


def sort_attrs(attr):
    if isinstance(attr, (list, tuple)):
        a = attr[0].split('.')
    else:
        a = attr.split('.')
    return len(a), a


def sort_obj(obj):
    if isinstance(obj, list):
        result_obj = []
        for item in obj:
            result_obj.append(sort_obj(item))
    elif isinstance(obj, dict):
        result_start = []
        result_end = []
        for k, v in obj.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        result_end.append([k, sort_obj(v)])
                    else:
                        result_start.append([k, sort_obj(v)])
                if not v:
                    result_end.append([k, v])
            else:
                result_start.append([k, sort_obj(v)])

        result_obj = OrderedDict(sorted(result_start) + sorted(result_end))
    else:
        result_obj = obj

    return result_obj


def get_attrs_to_dict(obj, attrs):
    d = {}

    for attr, sub in attrs.items():
        no_attr = False

        if isinstance(obj, dict):
            value = obj.get(attr, None)
        else:
            try:
                value = getattr(obj, attr)
            except AttributeError:
                no_attr = True
                value = None

        if callable(value):
            value = value()

        if isinstance(sub, str):
            if isinstance(value, list):
                value = [getattr(o, sub, None) for o in value]
            else:
                value = getattr(value, sub, None)
        elif isinstance(sub, dict):
            if isinstance(value, list):
                value = [get_attrs_to_dict(o, sub) for o in value] or [get_attrs_to_dict({}, sub)]
            else:
                value = get_attrs_to_dict(value, sub)
        elif callable(sub):
            if isinstance(value, list):
                value = [sub(o) for o in value]
            else:
                if no_attr:
                    value = sub(obj)
                else:
                    value = sub(value)

        d[attr] = value

    return d


def flatten_dict(obj):
    return flatten_tree(flatten_keys(obj))


def flatten_keys(obj, key='', sep='.'):
    if isinstance(obj, list):
        new_obj = [flatten_keys(o, key=key) for o in obj]
    elif isinstance(obj, dict):
        new_key = key + sep if key else ''
        new_obj = {new_key + k: flatten_keys(v, key=new_key + k) for k, v in obj.items()}
    else:
        new_obj = obj

    return new_obj


def flatten_tree(obj, key=''):
    if isinstance(obj, list):
        new_rows = []

        for o in obj:
            if isinstance(o, dict):
                new_rows.extend(flatten_tree(o))
            else:
                new_rows.append({key: o})

    elif isinstance(obj, dict):
        common_keys = {}
        all_rows = [[common_keys]]

        for k, v in obj.items():
            if isinstance(v, list):
                all_rows.append(flatten_tree(v, k))
            elif isinstance(v, dict):
                common_keys.update(*flatten_tree(v))
            else:
                common_keys[k] = v

        new_rows = [{k: v for r in row for k, v in r.items()}
                    for row in zip_longest(*all_rows, fillvalue={})]

    else:
        new_rows = []

    return new_rows


# https://stackoverflow.com/a/14692747
def get_by_path(root, items):
    """Access a nested object in root by item sequence."""
    return reduce(operator.getitem, items, root)


def set_by_path(root, items, value):
    """Set a value in a nested object in root by item sequence."""
    get_by_path(root, items[:-1])[items[-1]] = value


def get_dict_value_by_path(root, attr):
    split_attr = attr.split('.')
    value = get_by_path(root, split_attr)
    for _attr in reversed(split_attr):
        value = {_attr: value}
    return value


# https://stackoverflow.com/a/7205107
def dict_merge(a, b, path=None):
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass
            else:
                pass
        else:
            a[key] = b[key]
    return a


#https://stackoverflow.com/a/26853961
def dict_update(*dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


# https://stackoverflow.com/a/28703510
def escape_xml(value):
    if value is None:
        return ''

    value = str(value) \
        .replace("&", "&amp;") \
        .replace("<", "&lt;") \
        .replace(">", "&gt;") \
        .replace('"', "&quot;") \
        .replace("'", "&apos;")
    return value


# https://gist.github.com/reimund/5435343/
def dict_to_xml(d, root_node=None, indent=None, level=0):
    line_break = '' if indent is None else '\n'
    wrap = not bool(root_node is None or isinstance(d, list))
    root = root_node or 'objects'
    root_singular = root[:-1] if root.endswith('s') and isinstance(d, list) else root
    xml = ''
    children = []

    if isinstance(d, dict):
        for key, value in sorted(d.items()):
            if isinstance(value, dict):
                children.append(dict_to_xml(value, key, indent, level + 1))
            elif isinstance(value, list):
                children.append(dict_to_xml(value, key, indent, level + 1))
            else:
                xml = '{} {}="{}"'.format(xml, key, escape_xml(value))
    elif isinstance(d, list):
        for value in d:
            # Custom tag replacement for collections/playlists
            if isinstance(value, dict) and root in ('children', 'items'):
                root_singular = value.get('type', root_singular)
            children.append(dict_to_xml(value, root_singular, indent, level))
    else:
        children.append(escape_xml(d))

    end_tag = '>' if len(children) > 0 else '/>'
    end_tag += line_break if isinstance(d, list) or isinstance(d, dict) else ''
    spaces = ' ' * level * (indent or 0)

    if wrap or isinstance(d, dict):
        xml = '{}<{}{}{}'.format(spaces, root, xml, end_tag)

    if len(children) > 0:
        for child in children:
            xml = '{}{}'.format(xml, child)

        if wrap or isinstance(d, dict):
            spaces = spaces if isinstance(d, dict) else ''
            xml = '{}{}</{}>{}'.format(xml, spaces, root, line_break)

    return xml


def move_to_front(l, value):
    try:
        l.insert(0, l.pop(l.index(value)))
    except (ValueError, IndexError):
        pass
    return l


def is_hdr(bit_depth, color_space):
    bit_depth = cast_to_int(bit_depth)
    return bit_depth > 8 and color_space == 'bt2020nc'


def version_to_tuple(version):
    return tuple(cast_to_int(v) for v in version.strip('v').split('.'))


# https://stackoverflow.com/a/1855118
def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       arcname=os.path.relpath(os.path.join(root, file),
                                               os.path.join(path, '.')))


def page(endpoint, *args, **kwargs):
    endpoints = {
        'pms_image_proxy': pms_image_proxy,
        'info': info_page,
        'library': library_page,
        'user': user_page
    }

    params = {}

    if endpoint in endpoints:
        params = endpoints[endpoint](*args, **kwargs)

    return endpoint + '?' + urlencode(params)


def pms_image_proxy(img=None, rating_key=None, width=None, height=None,
                    opacity=None, background=None, blur=None, img_format=None,
                    fallback=None, refresh=None, clip=None):
    params = {}

    if img is not None:
        params['img'] = img
    if rating_key is not None:
        params['rating_key'] = rating_key
    if width is not None:
        params['width'] = width
    if height is not None:
        params['height'] = height
    if opacity is not None:
        params['opacity'] = opacity
    if background is not None:
        params['background'] = background
    if blur is not None:
        params['blur'] = blur
    if img_format is not None:
        params['img_format'] = img_format
    if fallback is not None:
        params['fallback'] = fallback
    if refresh is not None:
        params['refresh'] = 'true'
    if clip is not None:
        params['clip'] = 'true'

    return params


def info_page(rating_key=None, guid=None, history=None, live=None):
    params = {}

    if live and history:
        params['guid'] = guid
    else:
        params['rating_key'] = rating_key

    if history:
        params['source'] = 'history'

    return params


def library_page(section_id=None):
    params = {}

    if section_id is not None:
        params['section_id'] = section_id

    return params


def user_page(user_id=None, user=None):
    params = {}

    if user_id is not None:
        params['user_id'] = user_id
    if user is not None:
        params['user'] = user

    return params


def browse_path(path=None, include_hidden=False, filter_ext=''):
    output = []

    if os.name == 'nt' and path.lower() == 'my computer':
        drives = ['%s:\\' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
        for drive in drives:
            out = {
                'key': base64.b64encode(drive.encode('UTF-8')),
                'path': drive,
                'title': drive,
                'type': 'folder',
                'icon': 'folder'
            }
            output.append(out)

    if os.path.isfile(path):
        path = os.path.dirname(path)

    if not os.path.isdir(path):
        return output

    if path != os.path.dirname(path):
        parent_path = os.path.dirname(path)
        out = {
            'key': base64.b64encode(parent_path.encode('UTF-8')),
            'path': parent_path,
            'title': '..',
            'type': 'folder',
            'icon': 'level-up-alt'
        }
        output.append(out)
    elif os.name == 'nt':
        parent_path = 'My Computer'
        out = {
            'key': base64.b64encode(parent_path.encode('UTF-8')),
            'path': parent_path,
            'title': parent_path,
            'type': 'folder',
            'icon': 'level-up-alt'
        }
        output.append(out)

    for root, dirs, files in os.walk(path):
        for d in sorted(dirs):
            if not include_hidden and d.startswith('.'):
                continue
            dir_path = os.path.join(root, d)
            out = {
                'key': base64.b64encode(dir_path.encode('UTF-8')),
                'path': dir_path,
                'title': d,
                'type': 'folder',
                'icon': 'folder'
            }
            output.append(out)

        if filter_ext == '.folderonly':
            break

        for f in sorted(files):
            if not include_hidden and f.startswith('.'):
                continue
            if filter_ext and not f.endswith(filter_ext):
                continue
            file_path = os.path.join(root, f)
            out = {
                'key': base64.b64encode(file_path.encode('UTF-8')),
                'path': file_path,
                'title': f,
                'type': 'file',
                'icon': 'file'
            }
            output.append(out)

        break

    return output


def delete_file(file_path):
    logger.info("Tautulli Helpers :: Deleting file: %s", file_path)
    try:
        os.remove(file_path)
        return True
    except OSError:
        logger.error("Tautulli Helpers :: Failed to delete file: %s", file_path)
        return False


def short_season(title):
    if title.startswith('Season ') and title[7:].isdigit():
        return 'S%s' % title[7:]
    return title
