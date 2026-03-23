import hashlib
import hmac
import re
import time
from binascii import a2b_hex


AUTH_TOKEN_NAME = "__cld_token__"
AUTH_TOKEN_SEPARATOR = "~"
AUTH_TOKEN_UNSAFE_RE = r'([ "#%&\'\/:;<=>?@\[\\\]^`{\|}~]+)'


def generate(url=None, acl=None, start_time=None, duration=None,
             expiration=None, ip=None, key=None, token_name=AUTH_TOKEN_NAME, **_):
    start_time = _ensure_int(start_time)
    duration = _ensure_int(duration)
    expiration = _ensure_int(expiration)

    if expiration is None:
        if duration is not None:
            start = start_time if start_time is not None else int(time.time())
            expiration = start + duration
        else:
            raise Exception("Must provide either expiration or duration")

    if url is None and acl is None:
        raise Exception("Must provide either acl or url")

    token_parts = []
    if ip is not None:
        token_parts.append("ip=" + ip)
    if start_time is not None:
        token_parts.append("st=%d" % start_time)
    token_parts.append("exp=%d" % expiration)
    if acl is not None:
        acl_list = acl if type(acl) is list else [acl]
        acl_list = [_escape_to_lower(a) for a in acl_list] 
        token_parts.append("acl=%s" % "!".join(acl_list))
    to_sign = list(token_parts)
    if url is not None and acl is None:
        to_sign.append("url=%s" % _escape_to_lower(url))
    auth = _digest(AUTH_TOKEN_SEPARATOR.join(to_sign), key)
    token_parts.append("hmac=%s" % auth)
    return "%(token_name)s=%(token)s" % {"token_name": token_name, "token": AUTH_TOKEN_SEPARATOR.join(token_parts)}


def _digest(message, key):
    bin_key = a2b_hex(key)
    return hmac.new(bin_key, message.encode('utf-8'), hashlib.sha256).hexdigest()


def _escape_to_lower(url):
    # There is a circular import issue in this file, need to resolve it in the next major release
    from cloudinary.utils import smart_escape
    escaped_url = smart_escape(url, unsafe=AUTH_TOKEN_UNSAFE_RE)
    escaped_url = re.sub(r"%[0-9A-F]{2}", lambda x: x.group(0).lower(), escaped_url)
    return escaped_url

def _ensure_int(value):
    """
    Ensures the input value is an integer.
    Attempts to cast it to an integer if it is not already.

    :param value: The value to ensure as an integer.
    :type value: Any
    :return: The integer value.
    :rtype: int
    :raises ValueError: If the value cannot be converted to an integer.
    """
    if isinstance(value, int) or not value:
        return value

    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError("Value '" + value + "' must be an integer.")
