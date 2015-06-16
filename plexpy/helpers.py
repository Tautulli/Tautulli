#  This file is part of PlexPy.
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

from operator import itemgetter

import unicodedata
import plexpy
import datetime
import fnmatch
import shutil
import time
import sys
import re
import os
import json
import xmltodict
import math


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
        0xa9: '{C}', 0xaa: '{^a}', 0xab: '<<', 0xac: '{not}',
        0xad: '-', 0xae: '{R}', 0xaf: '_', 0xb0: '{degrees}',
        0xb1: '{+/-}', 0xb2: '{^2}', 0xb3: '{^3}', 0xb4: "'",
        0xb5: '{micro}', 0xb6: '{paragraph}', 0xb7: '*', 0xb8: '{cedilla}',
        0xb9: '{^1}', 0xba: '{^o}', 0xbb: '>>',
        0xbc: '{1/4}', 0xbd: '{1/2}', 0xbe: '{3/4}', 0xbf: '?',
        0xd7: '*', 0xf7: '/'
    }

    r = ''
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

    seconds = float(ms) / 1000
    minutes = round(seconds / 60, 0)

    return math.trunc(minutes)

def convert_seconds(s):

    gmtime = time.gmtime(s)
    if s > 3600:
        minutes = time.strftime("%H:%M:%S", gmtime)
    else:
        minutes = time.strftime("%M:%S", gmtime)

    return minutes


def today():
    today = datetime.date.today()
    yyyymmdd = datetime.date.isoformat(today)
    return yyyymmdd


def now():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


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
    Create a pair of self-signed HTTPS certificares and store in them in
    'ssl_cert' and 'ssl_key'. Method assumes pyOpenSSL is installed.

    This code is stolen from SickBeard (http://github.com/midgetspy/Sick-Beard).
    """

    from plexpy import logger

    from OpenSSL import crypto
    from certgen import createKeyPair, createCertRequest, createCertificate, \
        TYPE_RSA, serial

    # Create the CA Certificate
    cakey = createKeyPair(TYPE_RSA, 2048)
    careq = createCertRequest(cakey, CN="Certificate Authority")
    cacert = createCertificate(careq, (careq, cakey), serial, (0, 60 * 60 * 24 * 365 * 10)) # ten years

    pkey = createKeyPair(TYPE_RSA, 2048)
    req = createCertRequest(pkey, CN="PlexPy")
    cert = createCertificate(req, (cacert, cakey), serial, (0, 60 * 60 * 24 * 365 * 10)) # ten years

    # Save the key and certificate to disk
    try:
        with open(ssl_key, "w") as fp:
            fp.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        with open(ssl_cert, "w") as fp:
            fp.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    except IOError as e:
        logger.error("Error creating SSL key and certificate: %s", e)
        return False

    return True


def cast_to_float(s):
    try:
        return float(s)
    except ValueError:
        return -1


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

    return math.trunc(percent)