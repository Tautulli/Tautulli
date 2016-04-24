#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

from httplib import HTTPSConnection
from httplib import HTTPConnection
import ssl
from plexpy import logger, helpers


class HTTPHandler(object):
    """
    Retrieve data from Plex Server
    """

    def __init__(self, host, port, token, ssl_verify=True):
        self.host = host
        self.port = str(port)
        self.token = token
        self.ssl_verify = ssl_verify

    """
    Handle the HTTP requests.

    Output: object
    """
    def make_request(self,
                     uri=None, proto='HTTP',
                     request_type='GET',
                     headers=None,
                     output_format='raw',
                     return_type=False,
                     no_token=False,
                     timeout=20):

        valid_request_types = ['GET', 'POST', 'PUT', 'DELETE']

        if request_type.upper() not in valid_request_types:
            logger.debug(u"HTTP request made but unsupported request type given.")
            return None

        if uri:
            if proto.upper() == 'HTTPS':
                if not self.ssl_verify and hasattr(ssl, '_create_unverified_context'):
                    context = ssl._create_unverified_context()
                    handler = HTTPSConnection(host=self.host, port=self.port, timeout=timeout, context=context)
                    logger.warn(u"PlexPy HTTP Handler :: Unverified HTTPS request made. This connection is not secure.")
                else:
                    handler = HTTPSConnection(host=self.host, port=self.port, timeout=timeout)
            else:
                handler = HTTPConnection(host=self.host, port=self.port, timeout=timeout)

            token_string = ''
            if not no_token:
                if uri.find('?') > 0:
                    token_string = '&X-Plex-Token=' + self.token
                else:
                    token_string = '?X-Plex-Token=' + self.token

            try:
                if headers:
                    handler.request(request_type, uri + token_string, headers=headers)
                else:
                    handler.request(request_type, uri + token_string)
                response = handler.getresponse()
                request_status = response.status
                request_content = response.read()
                content_type = response.getheader('content-type')
            except IOError, e:
                logger.warn(u"Failed to access uri endpoint %s with error %s" % (uri, e))
                return None
            except Exception, e:
                logger.warn(u"Failed to access uri endpoint %s. Is your server maybe accepting SSL connections only? %s" % (uri, e))
                return None
            except:
                logger.warn(u"Failed to access uri endpoint %s with Uncaught exception." % uri)
                return None

            if request_status in (200, 201):
                try:
                    if output_format == 'dict':
                        output = helpers.convert_xml_to_dict(request_content)
                    elif output_format == 'json':
                        output = helpers.convert_xml_to_json(request_content)
                    elif output_format == 'xml':
                        output = helpers.parse_xml(request_content)
                    else:
                        output = request_content

                    if return_type:
                        return output, content_type

                    return output

                except Exception as e:
                    logger.warn(u"Failed format response from uri %s to %s error %s" % (uri, output_format, e))
                    return None

            else:
                logger.warn(u"Failed to access uri endpoint %s. Status code %r" % (uri, request_status))
                return None
        else:
            logger.debug(u"HTTP request made but no enpoint given.")
            return None
