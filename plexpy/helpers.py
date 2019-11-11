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

import base64
import cloudinary
from cloudinary.api import delete_resources_by_tag
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url
import datetime
from functools import wraps
import geoip2.database, geoip2.errors
import gzip
import hashlib
import imghdr
from itertools import izip_longest
import ipwhois, ipwhois.exceptions, ipwhois.utils
from IPy import IP
import json
import math
import maxminddb
from operator import itemgetter
import os
import re
import shlex
import socket
import sys
import time
import unicodedata
import urllib, urllib2
from xml.dom import minidom
import xmltodict

import plexpy
import logger
import request
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


def utc_now_iso():
    utcnow = datetime.datetime.utcnow()

    return utcnow.isoformat()


def human_duration(s, sig='dhms'):

    hd = ''

    if str(s).isdigit() and s > 0:
        d = int(s / 86400)
        h = int((s % 86400) / 3600)
        m = int(((s % 86400) % 3600) / 60)
        s = int(((s % 86400) % 3600) % 60)

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
    from OpenSSL import crypto
    from certgen import createKeyPair, createSelfSignedCertificate, TYPE_RSA

    serial = int(time.time())
    domains = ['DNS:' + d.strip() for d in plexpy.CONFIG.HTTPS_DOMAIN.split(',') if d]
    ips = ['IP:' + d.strip() for d in plexpy.CONFIG.HTTPS_IP.split(',') if d]
    altNames = ','.join(domains + ips)

    # Create the self-signed Tautulli certificate
    logger.debug(u"Generating self-signed SSL certificate.")
    pkey = createKeyPair(TYPE_RSA, 2048)
    cert = createSelfSignedCertificate(("Tautulli", pkey), serial, (0, 60 * 60 * 24 * 365 * 10), altNames) # ten years

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
    if isinstance(obj, basestring):
        return unicode(obj).replace('<', '&lt;').replace('>', '&gt;')
    elif isinstance(obj, list):
        return [sanitize(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.iteritems()}
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
    elif not re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}(?!\d*-[a-z0-9]{6})', host):
        try:
            ip_address = socket.getaddrinfo(host, None)[0][4][0]
            logger.debug(u"IP Checker :: Resolved %s to %s." % (host, ip_address))
        except:
            logger.error(u"IP Checker :: Bad IP or hostname provided: %s." % host)
    return ip_address


def is_valid_ip(address):
    try:
        return IP(address)
    except TypeError:
        return False
    except ValueError:
        return False


def install_geoip_db():
    maxmind_url = 'http://geolite.maxmind.com/download/geoip/database/'
    geolite2_gz = 'GeoLite2-City.mmdb.gz'
    geolite2_md5 = 'GeoLite2-City.md5'
    geolite2_db = geolite2_gz[:-3]
    md5_checksum = ''

    temp_gz = os.path.join(plexpy.CONFIG.CACHE_DIR, geolite2_gz)
    geolite2_db = plexpy.CONFIG.GEOIP_DB or os.path.join(plexpy.DATA_DIR, geolite2_db)

    # Retrieve the GeoLite2 gzip file
    logger.debug(u"Tautulli Helpers :: Downloading GeoLite2 gzip file from MaxMind...")
    try:
        maxmind = urllib.URLopener()
        maxmind.retrieve(maxmind_url + geolite2_gz, temp_gz)
        md5_checksum = urllib2.urlopen(maxmind_url + geolite2_md5).read()
    except Exception as e:
        logger.error(u"Tautulli Helpers :: Failed to download GeoLite2 gzip file from MaxMind: %s" % e)
        return False

    # Extract the GeoLite2 database file
    logger.debug(u"Tautulli Helpers :: Extracting GeoLite2 database...")
    try:
        with gzip.open(temp_gz, 'rb') as gz:
            with open(geolite2_db, 'wb') as db:
                db.write(gz.read())
    except Exception as e:
        logger.error(u"Tautulli Helpers :: Failed to extract the GeoLite2 database: %s" % e)
        return False

    # Check MD5 hash for GeoLite2 database file
    logger.debug(u"Tautulli Helpers :: Checking MD5 checksum for GeoLite2 database...")
    try:
        hash_md5 = hashlib.md5()
        with open(geolite2_db, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        md5_hash = hash_md5.hexdigest()

        if md5_hash != md5_checksum:
            logger.error(u"Tautulli Helpers :: MD5 checksum doesn't match for GeoLite2 database. "
                         "Checksum: %s, file hash: %s" % (md5_checksum, md5_hash))
            return False
    except Exception as e:
        logger.error(u"Tautulli Helpers :: Failed to generate MD5 checksum for GeoLite2 database: %s" % e)
        return False

    # Delete temportary GeoLite2 gzip file
    logger.debug(u"Tautulli Helpers :: Deleting temporary GeoLite2 gzip file...")
    try:
        os.remove(temp_gz)
    except Exception as e:
        logger.warn(u"Tautulli Helpers :: Failed to remove temporary GeoLite2 gzip file: %s" % e)

    logger.debug(u"Tautulli Helpers :: GeoLite2 database installed successfully.")
    plexpy.CONFIG.__setattr__('GEOIP_DB', geolite2_db)
    plexpy.CONFIG.write()

    return True


def uninstall_geoip_db():
    logger.debug(u"Tautulli Helpers :: Uninstalling the GeoLite2 database...")
    try:
        os.remove(plexpy.CONFIG.GEOIP_DB)
        plexpy.CONFIG.__setattr__('GEOIP_DB', '')
        plexpy.CONFIG.write()
    except Exception as e:
        logger.error(u"Tautulli Helpers :: Failed to uninstall the GeoLite2 database: %s" % e)
        return False

    logger.debug(u"Tautulli Helpers :: GeoLite2 database uninstalled successfully.")
    return True


def geoip_lookup(ip_address):
    if not plexpy.CONFIG.GEOIP_DB:
        return 'GeoLite2 database not installed. Please install from the ' \
            '<a href="settings?install_geoip=true">Settings</a> page.'

    if not ip_address:
        return 'No IP address provided.'

    try:
        reader = geoip2.database.Reader(plexpy.CONFIG.GEOIP_DB)
        geo = reader.city(ip_address)
        reader.close()
    except ValueError as e:
        return 'Invalid IP address provided: %s.' % ip_address
    except IOError as e:
        return 'Missing GeoLite2 database. Please reinstall from the ' \
            '<a href="settings?install_geoip=true">Settings</a> page.'
    except maxminddb.InvalidDatabaseError as e:
        return 'Invalid GeoLite2 database. Please reinstall from the ' \
            '<a href="settings?reinstall_geoip=true">Settings</a> page.'
    except geoip2.errors.AddressNotFoundError as e:
        return '%s' % e
    except Exception as e:
        return 'Error: %s' % e

    geo_info = {'continent': geo.continent.name,
                'country': geo.country.name,
                'region': geo.subdivisions.most_specific.name,
                'city': geo.city.name,
                'postal_code': geo.postal.code,
                'timezone': geo.location.time_zone,
                'latitude': geo.location.latitude,
                'longitude': geo.location.longitude,
                'accuracy': geo.location.accuracy_radius
                }

    return geo_info


def whois_lookup(ip_address):

    nets = []
    err = None
    try:
        whois = ipwhois.IPWhois(ip_address).lookup_whois(retry_count=0)
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
        logger.error(u"Tautulli Helpers :: Cannot upload image to Imgur. No Imgur client id specified in the settings.")
        return img_url, delete_hash

    headers = {'Authorization': 'Client-ID %s' % plexpy.CONFIG.IMGUR_CLIENT_ID}
    data = {'image': base64.b64encode(img_data),
            'title': img_title.encode('utf-8'),
            'name': str(rating_key) + '.png',
            'type': 'png'}

    response, err_msg, req_msg = request.request_response2('https://api.imgur.com/3/image', 'POST',
                                                           headers=headers, data=data)

    if response and not err_msg:
        logger.debug(u"Tautulli Helpers :: Image '{}' ({}) uploaded to Imgur.".format(img_title, fallback))
        imgur_response_data = response.json().get('data')
        img_url = imgur_response_data.get('link', '').replace('http://', 'https://')
        delete_hash = imgur_response_data.get('deletehash', '')
    else:
        if err_msg:
            logger.error(u"Tautulli Helpers :: Unable to upload image '{}' ({}) to Imgur: {}".format(img_title, fallback, err_msg))
        else:
            logger.error(u"Tautulli Helpers :: Unable to upload image '{}' ({}) to Imgur.".format(img_title, fallback))

        if req_msg:
            logger.debug(u"Tautulli Helpers :: Request response: {}".format(req_msg))

    return img_url, delete_hash


def delete_from_imgur(delete_hash, img_title='', fallback=''):
    """ Deletes an image from Imgur """
    if not plexpy.CONFIG.IMGUR_CLIENT_ID:
        logger.error(u"Tautulli Helpers :: Cannot delete image from Imgur. No Imgur client id specified in the settings.")
        return False

    headers = {'Authorization': 'Client-ID %s' % plexpy.CONFIG.IMGUR_CLIENT_ID}

    response, err_msg, req_msg = request.request_response2('https://api.imgur.com/3/image/%s' % delete_hash, 'DELETE',
                                                           headers=headers)

    if response and not err_msg:
        logger.debug(u"Tautulli Helpers :: Image '{}' ({}) deleted from Imgur.".format(img_title, fallback))
        return True
    else:
        if err_msg:
            logger.error(u"Tautulli Helpers :: Unable to delete image '{}' ({}) from Imgur: {}".format(img_title, fallback, err_msg))
        else:
            logger.error(u"Tautulli Helpers :: Unable to delete image '{}' ({}) from Imgur.".format(img_title, fallback))
        return False


def upload_to_cloudinary(img_data, img_title='', rating_key='', fallback=''):
    """ Uploads an image to Cloudinary """
    img_url = ''

    if not plexpy.CONFIG.CLOUDINARY_CLOUD_NAME or not plexpy.CONFIG.CLOUDINARY_API_KEY or not plexpy.CONFIG.CLOUDINARY_API_SECRET:
        logger.error(u"Tautulli Helpers :: Cannot upload image to Cloudinary. Cloudinary settings not specified in the settings.")
        return img_url

    cloudinary.config(
        cloud_name=plexpy.CONFIG.CLOUDINARY_CLOUD_NAME,
        api_key=plexpy.CONFIG.CLOUDINARY_API_KEY,
        api_secret=plexpy.CONFIG.CLOUDINARY_API_SECRET
    )

    try:
        response = upload('data:image/png;base64,{}'.format(base64.b64encode(img_data)),
                          public_id='{}_{}'.format(fallback, rating_key),
                          tags=['tautulli', fallback, str(rating_key)],
                          context={'title': img_title.encode('utf-8'), 'rating_key': str(rating_key), 'fallback': fallback})
        logger.debug(u"Tautulli Helpers :: Image '{}' ({}) uploaded to Cloudinary.".format(img_title, fallback))
        img_url = response.get('url', '')
    except Exception as e:
        logger.error(u"Tautulli Helpers :: Unable to upload image '{}' ({}) to Cloudinary: {}".format(img_title, fallback, e))

    return img_url


def delete_from_cloudinary(rating_key=None, delete_all=False):
    """ Deletes an image from Cloudinary """
    if not plexpy.CONFIG.CLOUDINARY_CLOUD_NAME or not plexpy.CONFIG.CLOUDINARY_API_KEY or not plexpy.CONFIG.CLOUDINARY_API_SECRET:
        logger.error(u"Tautulli Helpers :: Cannot delete image from Cloudinary. Cloudinary settings not specified in the settings.")
        return False

    cloudinary.config(
        cloud_name=plexpy.CONFIG.CLOUDINARY_CLOUD_NAME,
        api_key=plexpy.CONFIG.CLOUDINARY_API_KEY,
        api_secret=plexpy.CONFIG.CLOUDINARY_API_SECRET
    )

    if delete_all:
        delete_resources_by_tag('tautulli')
        logger.debug(u"Tautulli Helpers :: Deleted all images from Cloudinary.")
    elif rating_key:
        delete_resources_by_tag(str(rating_key))
        logger.debug(u"Tautulli Helpers :: Deleted images from Cloudinary with rating_key {}.".format(rating_key))
    else:
        logger.debug(u"Tautulli Helpers :: Unable to delete images from Cloudinary: No rating_key provided.")

    return True


def cloudinary_transform(rating_key=None, width=1000, height=1500, opacity=100, background='000000', blur=0,
                         img_format='png', img_title='', fallback=None):
    url = ''

    if not plexpy.CONFIG.CLOUDINARY_CLOUD_NAME or not plexpy.CONFIG.CLOUDINARY_API_KEY or not plexpy.CONFIG.CLOUDINARY_API_SECRET:
        logger.error(u"Tautulli Helpers :: Cannot transform image on Cloudinary. Cloudinary settings not specified in the settings.")
        return url

    cloudinary.config(
        cloud_name=plexpy.CONFIG.CLOUDINARY_CLOUD_NAME,
        api_key=plexpy.CONFIG.CLOUDINARY_API_KEY,
        api_secret=plexpy.CONFIG.CLOUDINARY_API_SECRET
    )

    img_options = {'format': img_format,
                   'fetch_format': 'auto',
                   'quality': 'auto',
                   'version': int(time.time()),
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
        logger.debug(u"Tautulli Helpers :: Image '{}' ({}) transformed on Cloudinary.".format(img_title, fallback))
    except Exception as e:
        logger.error(u"Tautulli Helpers :: Unable to transform image '{}' ({}) on Cloudinary: {}".format(img_title, fallback, e))

    return url


def cache_image(url, image=None):
    """
    Saves an image to the cache directory.
    If no image is provided, tries to return the image from the cache directory.
    """
    # Create image directory if it doesn't exist
    imgdir = os.path.join(plexpy.CONFIG.CACHE_DIR, 'images/')
    if not os.path.exists(imgdir):
        logger.debug(u"Tautulli Helpers :: Creating image cache directory at %s" % imgdir)
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
            logger.error(u"Tautulli Helpers :: Failed to cache image %s: %s" % (imagefile, e))

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

    order_column = [c[0] for c in dt_columns].index(kwargs.pop("order_column", default_sort_col))

    # Build json data
    json_data = {"draw": 1,
                 "columns": columns,
                 "order": [{"column": order_column,
                            "dir": kwargs.pop("order_dir", "desc")}],
                 "start": int(kwargs.pop("start", 0)),
                 "length": int(kwargs.pop("length", 25)),
                 "search": {"value": kwargs.pop("search", "")}
                 }
    return json.dumps(json_data)


def humanFileSize(bytes, si=False):
    if str(bytes).isdigit():
        bytes = int(bytes)
    else:
        return bytes

    thresh = 1000 if si else 1024
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

    return "{0:.1f} {1}".format(bytes, units[u])


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
    return izip_longest(fillvalue=fillvalue, *args)


def traverse_map(obj, func):
    if isinstance(obj, list):
        new_obj = []
        for i in obj:
            new_obj.append(traverse_map(i, func))

    elif isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.iteritems():
            new_obj[traverse_map(k, func)] = traverse_map(v, func)

    else:
        new_obj = func(obj)

    return new_obj


def split_args(args=None):
    if isinstance(args, list):
        return args
    elif isinstance(args, basestring):
        return [arg.decode(plexpy.SYS_ENCODING, 'ignore')
                for arg in shlex.split(args.encode(plexpy.SYS_ENCODING, 'ignore'))]
    return []


def mask_config_passwords(config):
    if isinstance(config, list):
        for cfg in config:
            if 'password' in cfg.get('name', '') and cfg.get('value', '') != '':
                cfg['value'] = '    '

    elif isinstance(config, dict):
        for cfg, val in config.iteritems():
            # Check for a password config keys and if the password is not blank
            if 'password' in cfg and val != '':
                # Set the password to blank so it is not exposed in the HTML form
                config[cfg] = '    '

    return config
