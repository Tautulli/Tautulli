import email.utils
import json
import socket

import urllib3
from urllib3.exceptions import HTTPError

import cloudinary
from cloudinary.exceptions import (
    BadRequest,
    AuthorizationRequired,
    NotAllowed,
    NotFound,
    AlreadyExists,
    RateLimited,
    GeneralError
)
from cloudinary.utils import process_params, safe_cast, smart_escape, unquote

EXCEPTION_CODES = {
    400: BadRequest,
    401: AuthorizationRequired,
    403: NotAllowed,
    404: NotFound,
    409: AlreadyExists,
    420: RateLimited,
    500: GeneralError
}


class Response(dict):
    def __init__(self, result, response, **kwargs):
        super(Response, self).__init__(**kwargs)
        self.update(result)

        self.rate_limit_allowed = safe_cast(response.headers.get("x-featureratelimit-limit"), int)
        self.rate_limit_reset_at = safe_cast(response.headers.get("x-featureratelimit-reset"), email.utils.parsedate)
        self.rate_limit_remaining = safe_cast(response.headers.get("x-featureratelimit-remaining"), int)


def execute_request(http_connector, method, params, headers, auth, api_url, **options):
    # authentication
    key = auth.get("key")
    secret = auth.get("secret")
    oauth_token = auth.get("oauth_token")
    req_headers = urllib3.make_headers(
        user_agent=cloudinary.get_user_agent()
    )
    if oauth_token:
        req_headers["authorization"] = "Bearer {}".format(oauth_token)
    else:
        req_headers.update(urllib3.make_headers(basic_auth="{0}:{1}".format(key, secret)))

    if headers is not None:
        req_headers.update(headers)

    kw = {}
    if "timeout" in options:
        kw["timeout"] = options["timeout"]
    if "body" in options:
        kw["body"] = options["body"]

    processed_params = process_params(params)

    api_url = smart_escape(unquote(api_url))
    try:
        response = http_connector.request(method=method.upper(), url=api_url, fields=processed_params, headers=req_headers, **kw)
        body = response.data
    except HTTPError as e:
        raise GeneralError("Unexpected error %s" % str(e))
    except socket.error as e:
        raise GeneralError("Socket Error: %s" % str(e))

    try:
        result = json.loads(body.decode('utf-8'))
    except Exception as e:
        # Error is parsing json
        raise GeneralError("Error parsing server response (%d) - %s. Got - %s" % (response.status, body, e))

    if "error" in result:
        exception_class = EXCEPTION_CODES.get(response.status) or Exception
        exception_class = exception_class
        raise exception_class("Error {0} - {1}".format(response.status, result["error"]["message"]))

    return Response(result, response)
