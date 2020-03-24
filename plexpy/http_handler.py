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

from __future__ import absolute_import
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from past.builtins import basestring
from builtins import object
from builtins import str

from functools import partial
from multiprocessing.dummy import Pool as ThreadPool
from urllib.parse import urljoin

import certifi
import urllib3

import plexpy
if plexpy.PYTHON_VERSION < 3:
    import helpers
    import logger
else:
    from plexpy import helpers
    from plexpy import logger


class HTTPHandler(object):
    """
    Retrieve data from Plex Server
    """

    def __init__(self, urls, headers=None, token=None, timeout=10, ssl_verify=True, silent=False):
        self._silent = silent

        if isinstance(urls, basestring):
            self.urls = urls.split() or urls.split(',')
        else:
            self.urls = urls

        if headers:
            self.headers = headers
        else:
            self.headers = {'X-Plex-Product': plexpy.common.PRODUCT,
                            'X-Plex-Version': plexpy.common.RELEASE,
                            'X-Plex-Client-Identifier': plexpy.CONFIG.PMS_UUID,
                            'X-Plex-Platform': plexpy.common.PLATFORM,
                            'X-Plex-Platform-Version': plexpy.common.PLATFORM_RELEASE,
                            'X-Plex-Device': '{} {}'.format(plexpy.common.PLATFORM,
                                                            plexpy.common.PLATFORM_RELEASE),
                            'X-Plex-Device-Name': plexpy.common.PLATFORM_DEVICE_NAME
                            }

        self.token = token
        if self.token:
            self.headers['X-Plex-Token'] = self.token

        self.timeout = timeout
        self.ssl_verify = ssl_verify

        self.valid_request_types = ('GET', 'POST', 'PUT', 'DELETE')

    def make_request(self,
                     uri=None,
                     headers=None,
                     request_type='GET',
                     output_format='raw',
                     return_type=False,
                     no_token=False,
                     timeout=None,
                     callback=None):
        """
        Handle the HTTP requests.

        Output: list
        """

        self.uri = str(uri)
        self.request_type = request_type.upper()
        self.output_format = output_format.lower()
        self.return_type = return_type
        self.callback = callback
        self.timeout = timeout or self.timeout

        if self.request_type not in self.valid_request_types:
            logger.debug("HTTP request made but unsupported request type given.")
            return None

        if uri:
            request_urls = [urljoin(str(url), self.uri) for url in self.urls]

            if no_token:
                self.headers.pop('X-Plex-Token', None)
            if headers:
                self.headers.update(headers)

            responses = []
            for r in self._http_requests_pool(request_urls):
                responses.append(r)

            return responses[0]

        else:
            logger.debug("HTTP request made but no enpoint given.")
            return None

    def _http_requests_pool(self, urls, workers=10, chunk=None):
        """Generator function to request urls in chunks"""
        # From cpython
        if chunk is None:
            chunk, extra = divmod(len(urls), workers * 4)
            if extra:
                chunk += 1
            if len(urls) == 0:
                chunk = 0

        if self.ssl_verify:
            session = urllib3.PoolManager(cert_reqs=2, ca_certs=certifi.where())  # ssl.CERT_REQUIRED = 2
        else:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            session = urllib3.PoolManager()
        part = partial(self._http_requests_urllib3, session=session)

        if len(urls) == 1:
            yield part(urls[0])
        else:
            pool = ThreadPool(workers)

            try:
                for work in pool.imap_unordered(part, urls, chunk):
                    yield work
            except Exception as e:
                if not self._silent:
                    logger.error("Failed to yield request: %s" % e)
            finally:
                pool.close()
                pool.join()

    def _http_requests_urllib3(self, url, session):
        """Request the data from the url"""
        try:
            r = session.request(self.request_type, url, headers=self.headers, timeout=self.timeout)
        except IOError as e:
            if not self._silent:
                logger.warn("Failed to access uri endpoint %s with error %s" % (self.uri, e))
            return None
        except Exception as e:
            if not self._silent:
                logger.warn("Failed to access uri endpoint %s. Is your server maybe accepting SSL connections only? %s" % (self.uri, e))
            return None
        except:
            if not self._silent:
                logger.warn("Failed to access uri endpoint %s with Uncaught exception." % self.uri)
            return None

        response_status = r.status
        response_content = r.data
        response_headers = r.headers

        if response_status in (200, 201):
            return self._http_format_output(response_content, response_headers)
        else:
            if not self._silent:
                logger.warn("Failed to access uri endpoint %s. Status code %r" % (self.uri, response_status))
            return None

    def _http_format_output(self, response_content, response_headers):
        """Formats the request response to the desired type"""
        try:
            if self.output_format == 'text':
                output = response_content.decode('utf-8', 'ignore')
            elif self.output_format == 'dict':
                output = helpers.convert_xml_to_dict(response_content)
            elif self.output_format == 'json':
                output = helpers.convert_xml_to_json(response_content)
            elif self.output_format == 'xml':
                output = helpers.parse_xml(response_content)
            else:
                output = response_content

            if self.callback:
                return self.callback(output)

            if self.return_type:
                return output, response_headers['Content-Type']

            return output

        except Exception as e:
            if not self._silent:
                logger.warn("Failed format response from uri %s to %s error %s" % (self.uri, self.output_format, e))
            return None
