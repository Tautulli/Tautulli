# -*- coding: utf-8 -*-
"""
oauthlib.oauth2.rfc6749.endpoint.revocation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An implementation of the OAuth 2 `Token Revocation`_ spec (draft 11).

.. _`Token Revocation`: http://tools.ietf.org/html/draft-ietf-oauth-revocation-11
"""
from __future__ import absolute_import, unicode_literals

import logging

from oauthlib.common import Request

from .base import BaseEndpoint, catch_errors_and_unavailability
from ..errors import InvalidClientError, UnsupportedTokenTypeError
from ..errors import InvalidRequestError, OAuth2Error

log = logging.getLogger(__name__)


class RevocationEndpoint(BaseEndpoint):

    """Token revocation endpoint.

    Endpoint used by authenticated clients to revoke access and refresh tokens.
    Commonly this will be part of the Authorization Endpoint.
    """

    valid_token_types = ('access_token', 'refresh_token')

    def __init__(self, request_validator, supported_token_types=None,
            enable_jsonp=False):
        BaseEndpoint.__init__(self)
        self.request_validator = request_validator
        self.supported_token_types = (
            supported_token_types or self.valid_token_types)
        self.enable_jsonp = enable_jsonp

    @catch_errors_and_unavailability
    def create_revocation_response(self, uri, http_method='POST', body=None,
                                   headers=None):
        """Revoke supplied access or refresh token.


        The authorization server responds with HTTP status code 200 if the
        token has been revoked sucessfully or if the client submitted an
        invalid token.

        Note: invalid tokens do not cause an error response since the client
        cannot handle such an error in a reasonable way.  Moreover, the purpose
        of the revocation request, invalidating the particular token, is
        already achieved.

        The content of the response body is ignored by the client as all
        necessary information is conveyed in the response code.

        An invalid token type hint value is ignored by the authorization server
        and does not influence the revocation response.
        """
        request = Request(
            uri, http_method=http_method, body=body, headers=headers)
        try:
            self.validate_revocation_request(request)
            log.debug('Token revocation valid for %r.', request)
        except OAuth2Error as e:
            log.debug('Client error during validation of %r. %r.', request, e)
            response_body = e.json
            if self.enable_jsonp and request.callback:
                response_body = '%s(%s);' % (request.callback, response_body)
            return {}, response_body, e.status_code

        self.request_validator.revoke_token(request.token,
                                            request.token_type_hint, request)

        response_body = ''
        if self.enable_jsonp and request.callback:
            response_body = request.callback + '();'
        return {}, response_body, 200

    def validate_revocation_request(self, request):
        """Ensure the request is valid.

        The client constructs the request by including the following parameters
        using the "application/x-www-form-urlencoded" format in the HTTP
        request entity-body:

        token (REQUIRED).  The token that the client wants to get revoked.

        token_type_hint (OPTIONAL).  A hint about the type of the token
        submitted for revocation.  Clients MAY pass this parameter in order to
        help the authorization server to optimize the token lookup.  If the
        server is unable to locate the token using the given hint, it MUST
        extend its search accross all of its supported token types.  An
        authorization server MAY ignore this parameter, particularly if it is
        able to detect the token type automatically.  This specification
        defines two such values:

                *  access_token: An Access Token as defined in [RFC6749],
                    `section 1.4`_

                *  refresh_token: A Refresh Token as defined in [RFC6749],
                    `section 1.5`_

                Specific implementations, profiles, and extensions of this
                specification MAY define other values for this parameter using
                the registry defined in `Section 4.1.2`_.

        The client also includes its authentication credentials as described in
        `Section 2.3`_. of [`RFC6749`_].

        .. _`section 1.4`: http://tools.ietf.org/html/rfc6749#section-1.4
        .. _`section 1.5`: http://tools.ietf.org/html/rfc6749#section-1.5
        .. _`section 2.3`: http://tools.ietf.org/html/rfc6749#section-2.3
        .. _`Section 4.1.2`: http://tools.ietf.org/html/draft-ietf-oauth-revocation-11#section-4.1.2
        .. _`RFC6749`: http://tools.ietf.org/html/rfc6749
        """
        if not request.token:
            raise InvalidRequestError(request=request,
                                      description='Missing token parameter.')

        if self.request_validator.client_authentication_required(request):
            if not self.request_validator.authenticate_client(request):
                raise InvalidClientError(request=request)

        if (request.token_type_hint and
                request.token_type_hint in self.valid_token_types and
                request.token_type_hint not in self.supported_token_types):
            raise UnsupportedTokenTypeError(request=request)
