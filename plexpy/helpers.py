﻿#  This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

import base64
import datetime
import fnmatch
from functools import wraps
from IPy import IP
import json
import math
from operator import itemgetter
import os
import re
import shutil
import socket
import sys
import time
import unicodedata
import urllib, urllib2
from xml.dom import minidom

import xmltodict
import arrow

import plexpy
from api2 import API2


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

def multikeysort(items, columns):
    comparers = [((itemgetter(col[1:].strip()), -1) if col.startswith('-') else (itemgetter(col.strip()), 1)) for col in columns]

    def comparer(left, right):
        for fn, mult in comparers:
            result = cmp(fn(left), fn(right))
            if result:
                return mult * result
        else:
            return 0

    return sorted(items, cmp=comparer)


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


def latinToAscii(unicrap):
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
                pass
            else:
                r += str(i)

    return r


def convert_milliseconds(ms):

    seconds = ms / 1000
    gmtime = time.gmtime(seconds)
    if seconds > 3600:
        minutes = time.strftime("%H:%M:%S", gmtime)
    else:
        minutes = time.strftime("%M:%S", gmtime)

    return minutes

def convert_milliseconds_to_minutes(ms):

    if str(ms).isdigit():
        seconds = float(ms) / 1000
        minutes = round(seconds / 60, 0)

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


def today():
    today = datetime.date.today()
    yyyymmdd = datetime.date.isoformat(today)
    return yyyymmdd


def now():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def human_duration(s, sig='dhms'):

    hd = ''

    if str(s).isdigit() and s > 0:
        d = int(s / 84600)
        h = int((s % 84600) / 3600)
        m = int(((s % 84600) % 3600) / 60)
        s = int(((s % 84600) % 3600) % 60)

        hd_list = []
        if sig >= 'd' and d > 0:
            d = d + 1 if sig == 'd' and h >= 12 else d
            hd_list.append(str(d) + ' days')

        if sig >= 'dh' and h > 0:
            h = h + 1 if sig == 'dh' and m >= 30 else h
            hd_list.append(str(h) + ' hrs')

        if sig >= 'dhm' and m > 0:
            m = m + 1 if sig == 'dhm' and s >= 30 else m
            hd_list.append(str(m) + ' mins')

        if sig >= 'dhms' and s > 0:
            hd_list.append(str(s) + ' secs')

        hd = ' '.join(hd_list)
    else:
        hd = '0'

    return hd

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

    mb = int(bytes) / 1048576
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

    for i, j in dic.iteritems():
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

    from plexpy import logger

    from OpenSSL import crypto
    from certgen import createKeyPair, createSelfSignedCertificate, TYPE_RSA

    serial = int(time.time())
    domains = ['DNS:' + d.strip() for d in plexpy.CONFIG.HTTPS_DOMAIN.split(',') if d]
    ips = ['IP:' + d.strip() for d in plexpy.CONFIG.HTTPS_IP.split(',') if d]
    altNames = ','.join(domains + ips)

    # Create the self-signed PlexPy certificate
    logger.debug(u"Generating self-signed SSL certificate.")
    pkey = createKeyPair(TYPE_RSA, 2048)
    cert = createSelfSignedCertificate(("PlexPy", pkey), serial, (0, 60 * 60 * 24 * 365 * 10), altNames) # ten years

    # Save the key and certificate to disk
    try:
        with open(ssl_cert, "w") as fp:
            fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        with open(ssl_key, "w") as fp:
            fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
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

def convert_xml_to_json(xml):
    o = xmltodict.parse(xml)
    return json.dumps(o)


def convert_xml_to_dict(xml):
    o = xmltodict.parse(xml)
    return o


def get_percent(value1, value2):

    if str(value1).isdigit() and str(value2).isdigit():
        value1 = cast_to_float(value1)
        value2 = cast_to_float(value2)
    else:
        return 0

    if value1 != 0 and value2 != 0:
        percent = (value1 / value2) * 100
    else:
        percent = 0

    return math.trunc(percent)

def parse_xml(unparsed=None):
    from plexpy import logger

    if unparsed:
        try:
            xml_parse = minidom.parseString(unparsed)
            return xml_parse
        except Exception, e:
            logger.warn("Error parsing XML. %s" % e)
            return []
        except:
            logger.warn("Error parsing XML.")
            return []
    else:
        logger.warn("XML parse request made but no data received.")
        return []

"""
Validate xml keys to make sure they exist and return their attribute value, return blank value is none found
"""
def get_xml_attr(xml_key, attribute, return_bool=False, default_return=''):
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

def sanitize(string):
    if string:
        return unicode(string).replace('<','&lt;').replace('>','&gt;')
    else:
        return ''

def is_ip_public(host):
    ip_address = get_ip(host)
    ip = IP(ip_address)
    if ip.iptype() == 'PUBLIC':
        return True

    return False

def get_ip(host):
    from plexpy import logger
    ip_address = ''
    try:
        socket.inet_aton(host)
        ip_address = host
    except socket.error:
        try:
            ip_address = socket.gethostbyname(host)
            logger.debug(u"IP Checker :: Resolved %s to %s." % (host, ip_address))
        except:
            logger.error(u"IP Checker :: Bad IP or hostname provided.")

    return ip_address

# Taken from SickRage
def anon_url(*url):
    """
    Return a URL string consisting of the Anonymous redirect URL and an arbitrary number of values appended.
    """
    return '' if None in url else '%s%s' % (plexpy.CONFIG.ANON_REDIRECT, ''.join(str(s) for s in url))

def uploadToImgur(imgPath, imgTitle=''):
    from plexpy import logger

    client_id = '743b1a443ccd2b0'
    img_url = ''

    try:
        with open(imgPath, 'rb') as imgFile:
            img = imgFile.read()
    except IOError as e:
        logger.error(u"PlexPy Helpers :: Unable to read image file for Imgur: %s" % e)
        return img_url

    headers = {'Authorization': 'Client-ID %s' % client_id}
    data = {'type': 'base64',
            'image': base64.b64encode(img)}
    if imgTitle:
        data['title'] = imgTitle.encode('utf-8')
        data['name'] = imgTitle.encode('utf-8') + '.jpg'

    try:
        request = urllib2.Request('https://api.imgur.com/3/image', headers=headers, data=urllib.urlencode(data))
        response = urllib2.urlopen(request)
        response = json.loads(response.read())

        if response.get('status') == 200:
            t = '\'' + imgTitle + '\' ' if imgTitle else ''
            logger.debug(u"PlexPy Helpers :: Image %suploaded to Imgur." % t)
            img_url = response.get('data').get('link', '')
        elif response.get('status') >= 400 and response.get('status') < 500:
            logger.warn(u"PlexPy Helpers :: Unable to upload image to Imgur: %s" % response.reason)
        else:
            logger.warn(u"PlexPy Helpers :: Unable to upload image to Imgur.")
    except (urllib2.HTTPError, urllib2.URLError) as e:
            logger.warn(u"PlexPy Helpers :: Unable to upload image to Imgur: %s" % e)

    return img_url


def get_time_range(time_range_type, n=None, format='', start=None, reverse=False, raw=False):
    """ A list of time/date from current day/hour/month etc

         Params:
            time_range(string): 'years, months, weeks, days, minutes, seconds',
            n(int, optional): number of days/etc
            format(string, optional): see arrow docs
            start(string, int, float, optional): see arrow.get()

        Example:
            get_time_range('months', start='2015-7-13', format='MMMM')

        Returns:
            [u'January', u'February', u'March', u'April', u'May', u'June', u'July', u'August',
             u'September', u'October', u'November', u'December', u'January', u'February']



    """
    # Defaults
    result = []
    base = g = arrow.now()

    if n is not None and isinstance(n, basestring):
        n = int(n)

    # To allow both negative and positive n
    # from current month/day/hour etc
    if n is not None:
        if n < 0:
            n += 1
        else:
            n -= 1

    # To allow subtraction of days: 100
    if start is None:
        start = base.replace(**{time_range_type: n})
    else:
        start = arrow.get(start)

    # Check if we should swap as the
    # oldest datetime always has to be first
    if start > g:
        start, g = g, start

    if time_range_type and time_range_type.endswith('s'):
        time_range_type = time_range_type.replace('s', '')

    # Incase we need access to the raw datetime, used in list comprehension
    if raw:
        result = [r for r in arrow.Arrow.range(time_range_type, start, g)]
    else:
        result = [r.format(format) if format else getattr(r, time_range_type) for r in arrow.Arrow.range(time_range_type, start, g)]

    if reverse is True:
        result = result[::-1]

    return result


def to_filesize(size, precision=2, si=True):
    """ Convert bytes to filesize """

    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffixes_b = ['KiB', 'MiB', 'GiB', 'TiB']
    suffix_index = 0
    num = 1000 if si is True else 1024
    suf = suffixes if si is True else suffixes_b

    while size > num and suffix_index < 4:
        suffix_index += 1
        size = size / float(num)
    return "%.*f %s" % (precision, size, suf[suffix_index])
