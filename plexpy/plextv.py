# This file is part of PlexPy.
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

from plexpy import logger, helpers, common, request

from xml.dom import minidom
from httplib import HTTPSConnection
from urlparse import parse_qsl
from urllib import urlencode
from pynma import pynma

import base64
import cherrypy
import urllib
import urllib2
import plexpy
import os.path
import subprocess
import json


class PlexTV(object):
    """
    Plex.tv authentication
    """

    def __init__(self, username='', password=''):
        self.username = username
        self.password = password

    def get_plex_auth(self):

        http_handler = HTTPSConnection("plex.tv")
        base64string = base64.encodestring('%s:%s' % (self.username, self.password)).replace('\n', '')

        http_handler.request("POST",
                             '/users/sign_in.xml',
                             headers={'Content-Type': 'application/xml; charset=utf-8',
                                      'Content-Length': '0',
                                      'X-Plex-Device-Name': 'PlexPy',
                                      'X-Plex-Product': 'PlexPy',
                                      'X-Plex-Version': 'v0.1 dev',
                                      'X-Plex-Client-Identifier': 'f0864d3531d75b19fa9204eaea456515e2502017',
                                      'Authorization': 'Basic %s' % base64string + ":"
                             })

        response = http_handler.getresponse()
        request_status = response.status
        request_body = response.read()
        logger.debug(u"Plex.tv response status: %r" % request_status)
        logger.debug(u"Plex.tv response headers: %r" % response.getheaders())
        logger.debug(u"Plex.tv content type: %r" % response.getheader('content-type'))
        logger.debug(u"Plex.tv response body: %r" % request_body)

        if request_status == 201:
            logger.info(u"Plex.tv connection successful.")
            return request_body
        elif request_status >= 400 and request_status < 500:
            logger.info(u"Plex.tv request failed: %s" % response.reason)
            return False
        else:
            logger.info(u"Plex.tv notification failed serverside.")
            return False

    def get_token(self):

        plextv_response = self.get_plex_auth()

        if plextv_response:
            try:
                xml_parse = minidom.parseString(helpers.latinToAscii(plextv_response))
            except IOError, e:
                logger.warn("Error parsing XML for Plex.tv token: %s" % e)
                return False

            xml_head = xml_parse.getElementsByTagName('user')
            if not xml_head:
                logger.warn("Error parsing XML for Plex.tv token: %s" % e)
                return False

            auth_token = xml_head[0].getAttribute('authenticationToken')

            return auth_token
        else:
            return False

    def get_plextv_user_data(self):

        plextv_response = self.get_plex_auth()

        if plextv_response:
            try:
                user_data = helpers.convert_xml_to_dict(plextv_response)
            except IOError, e:
                logger.warn("Error parsing XML for Plex.tv user data: %s" % e)
                return False

            return user_data
        else:
            return False