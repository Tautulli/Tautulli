import re

import cherrypy
from cherrypy.lib import set_vary_header
import httpagentparser


CORS_ALLOW_METHODS = 'Access-Control-Allow-Methods'
CORS_ALLOW_ORIGIN = 'Access-Control-Allow-Origin'
CORS_ALLOW_CREDENTIALS = 'Access-Control-Allow-Credentials'
CORS_EXPOSE_HEADERS = 'Access-Control-Expose-Headers'
CORS_REQUEST_METHOD = 'Access-Control-Request-Method'
CORS_REQUEST_HEADERS = 'Access-Control-Request-Headers'
CORS_MAX_AGE = 'Access-Control-Max-Age'
CORS_ALLOW_HEADERS = 'Access-Control-Allow-Headers'
PUBLIC_ORIGIN = '*'


def expose(allow_credentials=False, expose_headers=None, origins=None):
    """Adds CORS support to the resource.

    If the resource is allowed to be exposed, the value of the
    `Access-Control-Allow-Origin`_ header in the response will echo
    the `Origin`_ request header, and `Origin` will be
    appended to the `Vary`_ response header.

    :param allow_credentials: Use credentials to make cookies work
                              (see `Access-Control-Allow-Credentials`_).
    :type allow_credentials: bool
    :param expose_headers: List of headers clients will be able to access
                           (see `Access-Control-Expose-Headers`_).
    :type expose_headers: list or None
    :param origins: List of allowed origins clients must reference.
    :type origins: list or None

    :returns: Whether the resource is being exposed.
    :rtype: bool

    - Configuration example:

        .. code-block:: python

            config = {
                '/static': {
                    'tools.staticdir.on': True,
                    'cors.expose.on': True,
                }
            }
    - Decorator example:

        .. code-block:: python

            @cherrypy_cors.tools.expose()
            def DELETE(self):
                self._delete()

    """
    if _get_cors().expose(allow_credentials, expose_headers, origins):
        _safe_caching_headers()
        return True
    return False


def expose_public(expose_headers=None):
    """Adds CORS support to the resource from any origin.

    If the resource is allowed to be exposed, the value of the
    `Access-Control-Allow-Origin`_ header in the response will be `*`.

    :param expose_headers: List of headers clients will be able to access
                           (see `Access-Control-Expose-Headers`_).
    :type expose_headers: list or None

    :rtype: None
    """
    _get_cors().expose_public(expose_headers)


def preflight(
    allowed_methods,
    allowed_headers=None,
    allow_credentials=False,
    max_age=None,
    origins=None,
):
    """Adds CORS `preflight`_ support to a `HTTP OPTIONS` request.

    :param allowed_methods: List of supported `HTTP` methods
                            (see `Access-Control-Allow-Methods`_).
    :type allowed_methods: list or None
    :param allowed_headers: List of supported `HTTP` headers
                            (see `Access-Control-Allow-Headers`_).
    :type allowed_headers: list or None
    :param allow_credentials: Use credentials to make cookies work
                              (see `Access-Control-Allow-Credentials`_).
    :type allow_credentials: bool
    :param max_age: Seconds to cache the preflight request
                    (see `Access-Control-Max-Age`_).
    :type max_age: int
    :param origins: List of allowed origins clients must reference.
    :type origins: list or None

    :returns: Whether the preflight is allowed.
    :rtype: bool

    - Used as a decorator with the `Method Dispatcher`_

        .. code-block:: python

                @cherrypy_cors.tools.preflight(
                    allowed_methods=["GET", "DELETE", "PUT"])
                def OPTIONS(self):
                    pass

    - Function call with the `Object Dispatcher`_

        .. code-block:: python

                @cherrypy.expose
                @cherrypy.tools.allow(
                    methods=["GET", "DELETE", "PUT", "OPTIONS"])
                def thing(self):
                    if cherrypy.request.method == "OPTIONS":
                        cherrypy_cors.preflight(
                            allowed_methods=["GET", "DELETE", "PUT"])
                    else:
                        self._do_other_things()

    """
    if _get_cors().preflight(
        allowed_methods, allowed_headers, allow_credentials, max_age, origins
    ):
        _safe_caching_headers()
        return True
    return False


def install():
    """Install the toolbox such that it's available in all applications."""
    cherrypy._cptree.Application.toolboxes.update(cors=tools)


class CORS:
    """A generic CORS handler."""

    def __init__(self, req_headers, resp_headers):
        self.req_headers = req_headers
        self.resp_headers = resp_headers

    def expose(self, allow_credentials, expose_headers, origins):
        if self._is_valid_origin(origins):
            self._add_origin_and_credentials_headers(allow_credentials)
            self._add_expose_headers(expose_headers)
            return True
        return False

    def expose_public(self, expose_headers):
        self._add_public_origin()
        self._add_expose_headers(expose_headers)

    def preflight(
        self, allowed_methods, allowed_headers, allow_credentials, max_age, origins
    ):
        if self._is_valid_preflight_request(allowed_headers, allowed_methods, origins):
            self._add_origin_and_credentials_headers(allow_credentials)
            self._add_prefligt_headers(allowed_methods, max_age)
            return True
        return False

    @property
    def origin(self):
        return self.req_headers.get('Origin')

    def _is_valid_origin(self, origins):
        if origins is None:
            origins = [self.origin]
        origins = map(self._make_regex, origins)
        return self.origin is not None and any(
            origin.match(self.origin) for origin in origins
        )

    @staticmethod
    def _make_regex(pattern):
        if isinstance(pattern, str):
            pattern = re.compile(re.escape(pattern) + '$')
        return pattern

    def _add_origin_and_credentials_headers(self, allow_credentials):
        self.resp_headers[CORS_ALLOW_ORIGIN] = self.origin
        if allow_credentials:
            self.resp_headers[CORS_ALLOW_CREDENTIALS] = 'true'

    def _add_public_origin(self):
        self.resp_headers[CORS_ALLOW_ORIGIN] = PUBLIC_ORIGIN

    def _add_expose_headers(self, expose_headers):
        if expose_headers:
            self.resp_headers[CORS_EXPOSE_HEADERS] = expose_headers

    @property
    def requested_method(self):
        return self.req_headers.get(CORS_REQUEST_METHOD)

    @property
    def requested_headers(self):
        return self.req_headers.get(CORS_REQUEST_HEADERS)

    def _has_valid_method(self, allowed_methods):
        return self.requested_method and self.requested_method in allowed_methods

    def _valid_headers(self, allowed_headers):
        if self.requested_headers and allowed_headers:
            for header in self.requested_headers.split(','):
                if header.strip() not in allowed_headers:
                    return False
        return True

    def _is_valid_preflight_request(self, allowed_headers, allowed_methods, origins):
        return (
            self._is_valid_origin(origins)
            and self._has_valid_method(allowed_methods)
            and self._valid_headers(allowed_headers)
        )

    def _add_prefligt_headers(self, allowed_methods, max_age):
        rh = self.resp_headers
        rh[CORS_ALLOW_METHODS] = ', '.join(allowed_methods)
        if max_age:
            rh[CORS_MAX_AGE] = max_age
        if self.requested_headers:
            rh[CORS_ALLOW_HEADERS] = self.requested_headers


def _get_cors():
    return CORS(cherrypy.serving.request.headers, cherrypy.serving.response.headers)


def _safe_caching_headers():
    """Adds `Origin`_ to the `Vary`_ header to ensure caching works properly.

    Except in IE because it will disable caching completely. The caching
    strategy in that case is out of the scope of this library.
    https://blogs.msdn.microsoft.com/ieinternals/2009/06/17/vary-with-care/
    """
    uah = cherrypy.serving.request.headers.get('User-Agent', '')
    ua = httpagentparser.detect(uah)
    IE = 'Microsoft Internet Explorer'
    if ua.get('browser', {}).get('name') != IE:
        set_vary_header(cherrypy.serving.response, "Origin")


tools = cherrypy._cptools.Toolbox("cors")
tools.expose = cherrypy.Tool('before_handler', expose)
tools.expose_public = cherrypy.Tool('before_handler', expose_public)
tools.preflight = cherrypy.Tool('before_handler', preflight)
