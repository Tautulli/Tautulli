import cloudinary
from cloudinary.api_client.execute_request import execute_request
from cloudinary.provisioning.account_config import account_config
from cloudinary.utils import get_http_connector


PROVISIONING_SUB_PATH = "provisioning"
ACCOUNT_SUB_PATH = "accounts"
_http = get_http_connector(account_config(), cloudinary.CERT_KWARGS)


def _call_account_api(method, uri, params=None, headers=None, **options):
    prefix = options.pop("upload_prefix",
                         cloudinary.config().upload_prefix) or "https://api.cloudinary.com"
    account_id = options.pop("account_id", account_config().account_id)
    if not account_id:
        raise Exception("Must supply account_id")
    provisioning_api_key = options.pop("provisioning_api_key", account_config().provisioning_api_key)
    if not provisioning_api_key:
        raise Exception("Must supply provisioning_api_key")
    provisioning_api_secret = options.pop("provisioning_api_secret",
                                          account_config().provisioning_api_secret)
    if not provisioning_api_secret:
        raise Exception("Must supply provisioning_api_secret")
    provisioning_api_url = "/".join(
        [prefix, cloudinary.API_VERSION, PROVISIONING_SUB_PATH, ACCOUNT_SUB_PATH, account_id] + uri)
    auth = {"key": provisioning_api_key, "secret": provisioning_api_secret}

    return execute_request(http_connector=_http,
                           method=method,
                           params=params,
                           headers=headers,
                           auth=auth,
                           api_url=provisioning_api_url,
                           **options)
