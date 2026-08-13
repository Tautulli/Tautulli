import cloudinary
from cloudinary.api_client.execute_request import execute_request
from cloudinary.provisioning.account_config import account_config
from cloudinary.utils import get_http_connector, normalize_params

PROVISIONING_SUB_PATH = "provisioning"
ACCOUNT_SUB_PATH = "accounts"
_http = get_http_connector(account_config(), cloudinary.CERT_KWARGS)


# Account-scoped, authenticated call: provisioning/accounts/{account_id}/...
def _call_account_api(method, uri, params=None, headers=None, **options):
    account_uri = [ACCOUNT_SUB_PATH, _account_id(options)] + uri
    return _execute_account_request(method, account_uri, _account_auth(options),
                                    params=params, headers=headers, **options)


# Public, unauthenticated call: provisioning/... with no account_id or credentials
def _call_public_account_api(method, uri, params=None, headers=None, **options):
    return _execute_account_request(method, uri, {"anonymous": True},
                                    params=params, headers=headers, **options)


def _account_id(options):
    account_id = options.pop("account_id", account_config().account_id)
    if not account_id:
        raise Exception("Must supply account_id")
    return account_id


def _account_auth(options):
    provisioning_api_key = options.pop("provisioning_api_key", account_config().provisioning_api_key)
    if not provisioning_api_key:
        raise Exception("Must supply provisioning_api_key")
    provisioning_api_secret = options.pop("provisioning_api_secret", account_config().provisioning_api_secret)
    if not provisioning_api_secret:
        raise Exception("Must supply provisioning_api_secret")
    return {"key": provisioning_api_key, "secret": provisioning_api_secret}


# Core transport: builds the provisioning URL and dispatches with the resolved auth.
# The API version can be overridden via the "api_version" option (defaults to cloudinary.API_VERSION).
def _execute_account_request(method, uri, auth, params=None, headers=None, **options):
    prefix = options.pop("upload_prefix",
                         cloudinary.config().upload_prefix) or "https://api.cloudinary.com"
    api_version = options.pop("api_version", cloudinary.API_VERSION)
    provisioning_api_url = "/".join([prefix, api_version, PROVISIONING_SUB_PATH] + uri)

    return execute_request(http_connector=_http,
                           method=method,
                           params=normalize_params(params),
                           headers=headers,
                           auth=auth,
                           api_url=provisioning_api_url,
                           **options)
