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

from plexpy import logger, helpers

from xml.dom import minidom
from httplib import HTTPSConnection
from urlparse import parse_qsl
from urllib import urlencode

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
        self.url = 'plex.tv'

    def get_plex_auth(self):

        http_handler = HTTPSConnection(self.url)
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

    def get_plextv_friends(self, output_format=''):
        url_command = '/api/users'
        http_handler = HTTPSConnection(self.url, timeout=10)

        try:
            http_handler.request("GET", url_command + '?X-Plex-Token=' + plexpy.CONFIG.PMS_TOKEN)
            response = http_handler.getresponse()
            request_status = response.status
            request_content = response.read()
        except IOError, e:
            logger.warn(u"Failed to access friends list. %s" % e)
            return None

        if request_status == 200:
            if output_format == 'dict':
                output = helpers.convert_xml_to_dict(request_content)
            elif output_format == 'json':
                output = helpers.convert_xml_to_json(request_content)
            else:
                output = request_content
        else:
            logger.warn(u"Failed to access friends list. Status code %r" % request_status)
            return None

        return output

    def get_plextv_user_details(self, output_format=''):
        url_command = '/users/account'
        http_handler = HTTPSConnection(self.url, timeout=10)

        try:
            http_handler.request("GET", url_command + '?X-Plex-Token=' + plexpy.CONFIG.PMS_TOKEN)
            response = http_handler.getresponse()
            request_status = response.status
            request_content = response.read()
        except IOError, e:
            logger.warn(u"Failed to access user details. %s" % e)
            return None

        if request_status == 200:
            if output_format == 'dict':
                output = helpers.convert_xml_to_dict(request_content)
            elif output_format == 'json':
                output = helpers.convert_xml_to_json(request_content)
            else:
                output = request_content
        else:
            logger.warn(u"Failed to access user details. Status code %r" % request_status)
            return None

        return output

    def get_plextv_server_list(self, output_format=''):
        url_command = '/pms/servers.xml'
        http_handler = HTTPSConnection(self.url, timeout=10)

        try:
            http_handler.request("GET", url_command + '?includeLite=1&X-Plex-Token=' + plexpy.CONFIG.PMS_TOKEN)
            response = http_handler.getresponse()
            request_status = response.status
            request_content = response.read()
        except IOError, e:
            logger.warn(u"Failed to access server list. %s" % e)
            return None

        if request_status == 200:
            if output_format == 'dict':
                output = helpers.convert_xml_to_dict(request_content)
            elif output_format == 'json':
                output = helpers.convert_xml_to_json(request_content)
            else:
                output = request_content
        else:
            logger.warn(u"Failed to access server list. Status code %r" % request_status)
            return None

        return output

    def get_plextv_sync_lists(self, machine_id='', output_format=''):
        url_command = '/servers/' + machine_id + '/sync_lists'
        http_handler = HTTPSConnection(self.url, timeout=10)

        try:
            http_handler.request("GET", url_command + '?X-Plex-Token=' + plexpy.CONFIG.PMS_TOKEN)
            response = http_handler.getresponse()
            request_status = response.status
            request_content = response.read()
        except IOError, e:
            logger.warn(u"Failed to access server list. %s" % e)
            return None

        if request_status == 200:
            if output_format == 'dict':
                output = helpers.convert_xml_to_dict(request_content)
            elif output_format == 'json':
                output = helpers.convert_xml_to_json(request_content)
            else:
                output = request_content
        else:
            logger.warn(u"Failed to access server list. Status code %r" % request_status)
            return None

        return output

    """
    Validate xml keys to make sure they exist and return their attribute value, return blank value is none found
    """
    @staticmethod
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

    def get_full_users_list(self):
        friends_list = self.get_plextv_friends()
        own_account = self.get_plextv_user_details()
        users_list = []

        try:
            xml_parse = minidom.parseString(own_account)
        except Exception, e:
            logger.warn("Error parsing XML for Plex account details: %s" % e)
        except:
            logger.warn("Error parsing XML for Plex account details.")

        xml_head = xml_parse.getElementsByTagName('user')
        if not xml_head:
            logger.warn("Error parsing XML for Plex account details.")
        else:
            for a in xml_head:
                own_details = {"user_id": self.get_xml_attr(a, 'id'),
                               "username": self.get_xml_attr(a, 'username'),
                               "thumb": self.get_xml_attr(a, 'thumb'),
                               "email": self.get_xml_attr(a, 'email'),
                               "is_home_user": self.get_xml_attr(a, 'home'),
                               "is_allow_sync": None,
                               "is_restricted": self.get_xml_attr(a, 'restricted')
                               }

                users_list.append(own_details)

        try:
            xml_parse = minidom.parseString(friends_list)
        except Exception, e:
            logger.warn("Error parsing XML for Plex friends list: %s" % e)
        except:
            logger.warn("Error parsing XML for Plex friends list.")

        xml_head = xml_parse.getElementsByTagName('User')
        if not xml_head:
            logger.warn("Error parsing XML for Plex friends list.")
        else:
            for a in xml_head:
                friend = {"user_id": self.get_xml_attr(a, 'id'),
                          "username": self.get_xml_attr(a, 'title'),
                          "thumb": self.get_xml_attr(a, 'thumb'),
                          "email": self.get_xml_attr(a, 'email'),
                          "is_home_user": self.get_xml_attr(a, 'home'),
                          "is_allow_sync": self.get_xml_attr(a, 'allowSync'),
                          "is_restricted": self.get_xml_attr(a, 'restricted')
                          }

                users_list.append(friend)

        return users_list