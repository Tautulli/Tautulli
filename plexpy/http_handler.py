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

from __future__ import unicode_literals
from future.builtins import object
from future.builtins import str

from multiprocessing.dummy import Pool as ThreadPool
from future.moves.urllib.parse import urljoin

import certifi
import requests
import urllib3

import plexpy
if plexpy.PYTHON2:
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
        self._valid_request_types = {'GET', 'POST', 'PUT', 'DELETE'}
        self._silent = silent

        if isinstance(urls, str):
            self.urls = urls.split() or urls.split(',')
        else:
            self.urls = urls

        if headers:
            self.headers = headers
        else:
            self.headers = {
                'X-Plex-Product': plexpy.common.PRODUCT,
                'X-Plex-Version': plexpy.common.RELEASE,
                'X-Plex-Client-Identifier': plexpy.CONFIG.PMS_CLIENT_ID or plexpy.CONFIG.PMS_UUID,
                'X-Plex-Platform': plexpy.common.PLATFORM,
                'X-Plex-Platform-Version': plexpy.common.PLATFORM_RELEASE,
                'X-Plex-Device': '{} {}'.format(plexpy.common.PLATFORM,
                                                plexpy.common.PLATFORM_RELEASE),
                'X-Plex-Device-Name': '{} ({})'.format(plexpy.common.PLATFORM_DEVICE_NAME,
                                                       plexpy.common.PRODUCT),
                'X-Plex-Language': plexpy.CONFIG.PMS_LANGUAGE or plexpy.SYS_LANGUAGE
            }

        self.token = token
        if self.token:
            self.headers['X-Plex-Token'] = self.token

        self._session = requests.Session()
        self.timeout = timeout
        self.ssl_verify = certifi.where() if ssl_verify else False
        if not self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


    def make_request(self,
                     uri=None,
                     headers=None,
                     data=None,
                     request_type='GET',
                     output_format='raw',
                     return_response=False,
                     return_type=False,
                     no_token=False,
                     timeout=None,
                     callback=None,
                     **request_kwargs):
        """
        Handle the HTTP requests.

        Output: list
        """
        if request_type not in self._valid_request_types:
            logger.debug("HTTP request made but unsupported request type given.")
            return None

        requests = []

        if uri:
            request_urls = [urljoin(str(url), uri) for url in self.urls]

            for url in request_urls:
                request = { 
                            'uri': uri,
                            'url': url,
                            'output_format':output_format.lower(),
                            'request_type': request_type.upper(),
                            'return_type': return_type,
                            'data': data,
                            'return_response': return_response,
                            'callback': callback,
                            'timeout': timeout or self.timeout,
                            'request_kwargs': request_kwargs
                }
                requests.append(request)

            if no_token:
                self.headers.pop('X-Plex-Token', None)
            if headers:
                self.headers.update(headers)

            responses = []
            for r in self._http_requests_pool(requests):
                responses.append(r)

            return responses[0]

        else:
            logger.debug("HTTP request made but no uri endpoint provided.")
            return None

    def _http_requests_pool(self, requests, workers=10, chunk=None):
        """Generator function to request urls in chunks"""
        # From cpython
        if chunk is None:
            chunk, extra = divmod(len(requests), workers * 4)
            if extra:
                chunk += 1
            if len(requests) == 0:
                chunk = 0

        if len(requests) == 1:
            yield self._http_requests_single(requests[0])
        else:
            pool = ThreadPool(workers)

            try:
                for work in pool.imap_unordered(self._http_requests_single, requests, chunk):
                    yield work
            except Exception as e:
                if not self._silent:
                    logger.error("Failed to yield request: %s" % e)
            finally:
                pool.close()
                pool.join()

    def _http_requests_single(self, urlproperties):
        """Request the data from the url"""
        err = False
        error_msg = "Failed to access uri endpoint %s. " % urlproperties['uri']
        try:
            r = self._session.request(urlproperties['request_type'], urlproperties['url'], headers=self.headers, data=urlproperties['data'],
                                      timeout=urlproperties['timeout'], verify=self.ssl_verify, **urlproperties['request_kwargs'])
            r.raise_for_status()
        except requests.exceptions.Timeout as e:
            err = True
            if not self._silent:
                logger.error(error_msg + "Request timed out: %s", e)
        except requests.exceptions.SSLError as e:
            err = True
            if not self._silent:
                logger.error(error_msg + "Is your server maybe accepting SSL connections only? %s", e)
        except requests.exceptions.HTTPError as e:
            err = True
            if not self._silent:
                logger.error(error_msg + "Status code %s", e)
        except requests.exceptions.ConnectionError as e:
            err = True
            if not self._silent:
                logger.error(error_msg + "Connection error: %s", e)
        except requests.exceptions.RequestException as e:
            err = True
            if not self._silent:
                logger.error(error_msg + "Uncaught exception: %s", e)

        if urlproperties['return_response']:
            return r
        elif err:
            return None

        response_status = r.status_code
        response_content = r.content
        response_headers = r.headers

        if response_status in (200, 201):
            return self._http_format_output(response_content, response_headers, urlproperties)

    def _http_format_output(self, response_content, response_headers, urlproperties):
        """Formats the request response to the desired type"""
        try:
            output_format = urlproperties['output_format']
            if output_format == 'text':
                output = response_content.decode('utf-8', 'ignore')
            elif output_format == 'dict':
                output = helpers.convert_xml_to_dict(response_content)
            elif output_format == 'json':
                output = helpers.convert_xml_to_json(response_content)
            elif output_format == 'xml':
                output = helpers.parse_xml(response_content)
            else:
                output = response_content
            callback = urlproperties['callback']
            if callback:
                return callback(output)

            return_type = urlproperties['return_type']
            if return_type:
                return output, response_headers['Content-Type']

            return output

        except Exception as e:
            if not self._silent:
                logger.warn("Failed format response from uri %s to %s error %s" % (self.uri, output_format, e))
            return None
