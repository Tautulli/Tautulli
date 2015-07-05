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

from httplib import HTTPSConnection
from httplib import HTTPConnection


class HTTPHandler(object):
    """
    Retrieve data from Plex Server
    """

    def __init__(self, host, port, token):
        self.host = host
        self.port = str(port)
        self.token = token

    """
    Handle the HTTP requests.

    Output: object
    """
    def make_request(self,
                     uri=None, proto='HTTP',
                     request_type='GET',
                     headers=None,
                     output_format='raw',
                     return_type=False):

        valid_request_types = ['GET', 'POST', 'PUT', 'DELETE']

        if request_type.upper() not in valid_request_types:
            logger.debug(u"HTTP request made but unsupported request type given.")
            return None

        if uri:
            if proto.upper() == 'HTTPS':
                handler = HTTPSConnection(self.host, self.port, timeout=10)
            else:
                handler = HTTPConnection(self.host, self.port, timeout=10)

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

            if request_status == 200:
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
            else:
                logger.warn(u"Failed to access uri endpoint %s. Status code %r" % (uri, request_status))
                return []
        else:
            logger.debug(u"HTTP request made but no enpoint given.")
            return None
