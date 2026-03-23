# Copyright Cloudinary
import base64
import copy
import hashlib
import json
import os
import random
import re
import string
import struct
import time
import urllib
import zlib
from collections import OrderedDict
from datetime import datetime, date
from fractions import Fraction
from numbers import Number

import six.moves.urllib.parse
from six import iteritems
from urllib3 import ProxyManager, PoolManager

import cloudinary
from cloudinary import auth_token
from cloudinary.api_client.tcp_keep_alive_manager import TCPKeepAlivePoolManager, TCPKeepAliveProxyManager
from cloudinary.compat import PY3, to_bytes, to_bytearray, to_string, string_types, urlparse

try:  # Python 3.4+
    from pathlib import Path as PathLibPathType
except ImportError:
    PathLibPathType = None

VAR_NAME_RE = r'(\$\([a-zA-Z]\w+\))'

urlencode = six.moves.urllib.parse.urlencode
unquote = six.moves.urllib.parse.unquote

""" @deprecated: use cloudinary.SHARED_CDN """
SHARED_CDN = "res.cloudinary.com"

DEFAULT_RESPONSIVE_WIDTH_TRANSFORMATION = {"width": "auto", "crop": "limit"}

RANGE_VALUE_RE = r'^(?P<value>(\d+\.)?\d+)(?P<modifier>[%pP])?$'
RANGE_RE = r'^(\d+\.)?\d+[%pP]?\.\.(\d+\.)?\d+[%pP]?$'
FLOAT_RE = r'^(\d+)\.(\d+)?$'
REMOTE_URL_RE = r'ftp:|https?:|s3:|gs:|data:([\w-]+\/[\w-]+(\+[\w-]+)?)?(;[\w-]+=[\w-]+)*;base64,([a-zA-Z0-9\/+\n=]+)$'
__LAYER_KEYWORD_PARAMS = [("font_weight", "normal"),
                          ("font_style", "normal"),
                          ("text_decoration", "none"),
                          ("text_align", None),
                          ("stroke", "none")]

# a list of keys used by the cloudinary_url function
__URL_KEYS = [
    'api_secret',
    'auth_token',
    'cdn_subdomain',
    'cloud_name',
    'cname',
    'format',
    'private_cdn',
    'resource_type',
    'secure',
    'secure_cdn_subdomain',
    'secure_distribution',
    'shorten',
    'sign_url',
    'ssl_detected',
    'type',
    'url_suffix',
    'use_root_path',
    'version',
    'long_url_signature',
    'signature_algorithm',
]

__SIMPLE_UPLOAD_PARAMS = [
    "public_id",
    "public_id_prefix",
    "callback",
    "format",
    "type",
    "backup",
    "faces",
    "image_metadata",
    "media_metadata",
    "exif",
    "colors",
    "use_filename",
    "unique_filename",
    "display_name",
    "use_filename_as_display_name",
    "discard_original_filename",
    "filename_override",
    "invalidate",
    "notification_url",
    "eager_notification_url",
    "eager_async",
    "eval",
    "on_success",
    "proxy",
    "folder",
    "asset_folder",
    "use_asset_folder_as_public_id_prefix",
    "unique_display_name",
    "overwrite",
    "moderation",
    "raw_convert",
    "quality_override",
    "quality_analysis",
    "ocr",
    "categorization",
    "detection",
    "similarity_search",
    "visual_search",
    "background_removal",
    "upload_preset",
    "phash",
    "return_delete_token",
    "auto_tagging",
    "async",
    "cinemagraph_analysis",
    "accessibility_analysis",
]

__SERIALIZED_UPLOAD_PARAMS = [
    "timestamp",
    "transformation",
    "headers",
    "eager",
    "tags",
    "allowed_formats",
    "face_coordinates",
    "custom_coordinates",
    "regions",
    "context",
    "auto_tagging",
    "responsive_breakpoints",
    "access_control",
    "metadata",
]

upload_params = __SIMPLE_UPLOAD_PARAMS + __SERIALIZED_UPLOAD_PARAMS

_SIMPLE_TRANSFORMATION_PARAMS = {
        "ac": "audio_codec",
        "af": "audio_frequency",
        "br": "bit_rate",
        "cs": "color_space",
        "d": "default_image",
        "dl": "delay",
        "dn": "density",
        "f": "fetch_format",
        "g": "gravity",
        "p": "prefix",
        "pg": "page",
        "sp": "streaming_profile",
        "vs": "video_sampling",
    }

SHORT_URL_SIGNATURE_LENGTH = 8
LONG_URL_SIGNATURE_LENGTH = 32

SIGNATURE_SHA1 = "sha1"
SIGNATURE_SHA256 = "sha256"

signature_algorithms = {
    SIGNATURE_SHA1: hashlib.sha1,
    SIGNATURE_SHA256: hashlib.sha256,
}


def compute_hex_hash(s, algorithm=SIGNATURE_SHA1):
    """
    Computes string hash using specified algorithm and return HEX string representation of hash.

    :param s:         String to compute hash for
    :param algorithm: The name of algorithm to use for computing hash

    :return: HEX string of computed hash value
    """
    try:
        hash_fn = signature_algorithms[algorithm]
    except KeyError:
        raise ValueError('Unsupported hash algorithm: {}'.format(algorithm))
    return hash_fn(to_bytes(s)).hexdigest()


def build_array(arg):
    if isinstance(arg, (list, tuple)):
        return arg
    elif arg is None:
        return []
    return [arg]


def build_list_of_dicts(val):
    """
    Converts a value that can be presented as a list of dict.

    In case top level item is not a list, it is wrapped with a list

    Valid values examples:
        - Valid dict: {"k": "v", "k2","v2"}
        - List of dict: [{"k": "v"}, {"k2","v2"}]
        - JSON decodable string: '{"k": "v"}', or '[{"k": "v"}]'
        - List of JSON decodable strings: ['{"k": "v"}', '{"k2","v2"}']

    Invalid values examples:
        - ["not", "a", "dict"]
        - [123, None],
        - [["another", "list"]]

    :param val: Input value
    :type val: Union[list, dict, str]

    :return: Converted(or original) list of dict
    :raises: ValueError in case value cannot be converted to a list of dict
    """
    if val is None:
        return []

    if isinstance(val, str):
        # use OrderedDict to preserve order
        val = json.loads(val, object_pairs_hook=OrderedDict)

    if isinstance(val, dict):
        val = [val]

    for index, item in enumerate(val):
        if isinstance(item, str):
            # use OrderedDict to preserve order
            val[index] = json.loads(item, object_pairs_hook=OrderedDict)
        if not isinstance(val[index], dict):
            raise ValueError("Expected a list of dicts")
    return val


def encode_double_array(array):
    array = build_array(array)
    if len(array) > 0 and isinstance(array[0], list):
        return "|".join([",".join([str(i) for i in build_array(inner)]) for inner in array])
    return encode_list([str(i) for i in array])


def encode_dict(arg):
    if isinstance(arg, dict):
        if PY3:
            items = arg.items()
        else:
            items = arg.iteritems()
        return "|".join((k + "=" + v) for k, v in items)
    return arg


def normalize_context_value(value):
    """
    Escape "=" and "|" delimiter characters and json encode lists

    :param value: Value to escape
    :type value: int or str or list or tuple

    :return: The normalized value
    :rtype: str
    """

    if isinstance(value, (list, tuple)):
        value = json_encode(value)

    return str(value).replace("=", "\\=").replace("|", "\\|")


def encode_context(context):
    """
    Encode metadata fields based on incoming value.

    List and tuple values are encoded to json strings.

    :param context: dict of context to be encoded

    :return: a joined string of all keys and values properly escaped and separated by a pipe character
    """
    if not isinstance(context, dict):
        return context

    return "|".join(("{}={}".format(k, normalize_context_value(v))) for k, v in iteritems(context))


def json_encode(value, sort_keys=False):
    """
    Converts value to a json encoded string

    :param value: value to be encoded
    :param sort_keys: whether to sort keys

    :return: JSON encoded string
    """

    if isinstance(value, str) or value is None:
        return value

    return json.dumps(value, default=__json_serializer, separators=(',', ':'), sort_keys=sort_keys)


def encode_date_to_usage_api_format(date_obj):
    """
    Encodes date object to `dd-mm-yyyy` format string

    :param date_obj: datetime.date object to encode

    :return: Encoded date as a string
    """
    return date_obj.strftime('%d-%m-%Y')


def patch_fetch_format(options):
    """
    When upload type is fetch, remove the format options.
    In addition, set the fetch_format options to the format value unless it was already set.
    Mutates the "options" parameter!

    :param options: URL and transformation options
    """
    use_fetch_format = options.pop("use_fetch_format", cloudinary.config().use_fetch_format)

    if options.get("type", "upload") != "fetch" and not use_fetch_format:
        return

    resource_format = options.pop("format", None)
    if "fetch_format" not in options:
        options["fetch_format"] = resource_format


def generate_transformation_string(**options):
    responsive_width = options.pop("responsive_width", cloudinary.config().responsive_width)
    size = options.pop("size", None)
    if size:
        options["width"], options["height"] = size.split("x")
    width = options.get("width")
    height = options.get("height")
    has_layer = ("underlay" in options) or ("overlay" in options)

    crop = options.pop("crop", None)
    angle = ".".join([str(value) for value in build_array(options.pop("angle", None))])
    no_html_sizes = has_layer or angle or crop == "fit" or crop == "limit" or responsive_width

    if width and (str(width).startswith("auto") or str(width) == "ow" or is_fraction(width) or no_html_sizes):
        del options["width"]
    if height and (str(height) == "oh" or is_fraction(height) or no_html_sizes):
        del options["height"]

    background = options.pop("background", None)
    if background:
        background = background.replace("#", "rgb:")
    color = options.pop("color", None)
    if color:
        color = color.replace("#", "rgb:")

    base_transformations = build_array(options.pop("transformation", None))
    if any(isinstance(bs, dict) for bs in base_transformations):
        def recurse(bs):
            if isinstance(bs, dict):
                return generate_transformation_string(**bs)[0]
            return generate_transformation_string(transformation=bs)[0]

        base_transformations = list(map(recurse, base_transformations))
        named_transformation = None
    else:
        named_transformation = ".".join(base_transformations)
        base_transformations = []

    effect = options.pop("effect", None)
    if isinstance(effect, list):
        effect = ":".join([str(x) for x in effect])
    elif isinstance(effect, dict):
        effect = ":".join([str(x) for x in list(effect.items())[0]])

    border = options.pop("border", None)
    if isinstance(border, dict):
        border_color = border.get("color", "black").replace("#", "rgb:")
        border = "%(width)spx_solid_%(color)s" % {"color": border_color,
                                                  "width": str(border.get("width", 2))}

    flags = ".".join(build_array(options.pop("flags", None)))
    dpr = options.pop("dpr", cloudinary.config().dpr)
    duration = norm_range_value(options.pop("duration", None))

    so_raw = options.pop("start_offset", None)
    start_offset = norm_auto_range_value(so_raw)
    if start_offset == None:
        start_offset = so_raw

    eo_raw = options.pop("end_offset", None)
    end_offset = norm_range_value(eo_raw)
    if end_offset == None:
        end_offset = eo_raw

    offset = split_range(options.pop("offset", None))
    if offset:
        start_offset = norm_auto_range_value(offset[0])
        end_offset = norm_range_value(offset[1])

    video_codec = process_video_codec_param(options.pop("video_codec", None))

    aspect_ratio = options.pop("aspect_ratio", None)
    if isinstance(aspect_ratio, Fraction):
        aspect_ratio = str(aspect_ratio.numerator) + ":" + str(aspect_ratio.denominator)

    overlay = process_layer(options.pop("overlay", None), "overlay")
    underlay = process_layer(options.pop("underlay", None), "underlay")
    if_value = process_conditional(options.pop("if", None))
    custom_function = process_custom_function(options.pop("custom_function", None))
    custom_pre_function = process_custom_pre_function(options.pop("custom_pre_function", None))
    fps = process_fps(options.pop("fps", None))

    params = {
        "a": normalize_expression(angle),
        "ar": normalize_expression(aspect_ratio),
        "b": background,
        "bo": border,
        "c": crop,
        "co": color,
        "dpr": normalize_expression(dpr),
        "du": normalize_expression(duration),
        "e": normalize_expression(effect),
        "eo": normalize_expression(end_offset),
        "fl": flags,
        "fn": custom_function or custom_pre_function,
        "fps": fps,
        "h": normalize_expression(height),
        "ki": process_ki(options.pop("keyframe_interval", None)),
        "l": overlay,
        "o": normalize_expression(options.pop('opacity', None)),
        "q": normalize_expression(options.pop('quality', None)),
        "r": process_radius(options.pop('radius', None)),
        "so": normalize_expression(start_offset),
        "t": named_transformation,
        "u": underlay,
        "w": normalize_expression(width),
        "x": normalize_expression(options.pop('x', None)),
        "y": normalize_expression(options.pop('y', None)),
        "vc": video_codec,
        "z": normalize_expression(options.pop('zoom', None))
    }

    for param, option in _SIMPLE_TRANSFORMATION_PARAMS.items():
        params[param] = options.pop(option, None)

    variables = options.pop('variables', {})
    var_params = []
    for key, value in options.items():
        if re.match(r'^\$', key):
            var_params.append(u"{0}_{1}".format(key, normalize_expression(str(value))))

    var_params.sort()

    if variables:
        for var in variables:
            var_params.append(u"{0}_{1}".format(var[0], normalize_expression(str(var[1]))))

    variables = ','.join(var_params)

    sorted_params = sorted([param + "_" + str(value) for param, value in params.items() if (value or value == 0)])
    if variables:
        sorted_params.insert(0, str(variables))

    if if_value is not None:
        sorted_params.insert(0, "if_" + str(if_value))

    if "raw_transformation" in options and (options["raw_transformation"] or options["raw_transformation"] == 0):
        sorted_params.append(options.pop("raw_transformation"))

    transformation = ",".join(sorted_params)

    transformations = base_transformations + [transformation]

    if responsive_width:
        responsive_width_transformation = cloudinary.config().responsive_width_transformation \
                                          or DEFAULT_RESPONSIVE_WIDTH_TRANSFORMATION
        transformations += [generate_transformation_string(**responsive_width_transformation)[0]]
    url = "/".join([trans for trans in transformations if trans])

    if str(width).startswith("auto") or responsive_width:
        options["responsive"] = True
    if dpr == "auto":
        options["hidpi"] = True
    return url, options


def chain_transformations(options, transformations):
    """
    Helper function, allows chaining transformations to the end of transformations list

    The result of this function is an updated options parameter

    :param options:         Original options
    :param transformations: Transformations to chain at the end

    :return: Resulting options
    """

    transformations = copy.deepcopy(transformations)

    transformations = build_array(transformations)
    # preserve url options
    url_options = dict((o, options[o]) for o in __URL_KEYS if o in options)

    transformations.insert(0, options)

    url_options["transformation"] = transformations

    return url_options


def is_fraction(width):
    width = str(width)
    return re.match(FLOAT_RE, width) and float(width) < 1


def split_range(range):
    if (isinstance(range, list) or isinstance(range, tuple)) and len(range) >= 2:
        return [range[0], range[-1]]
    elif isinstance(range, string_types) and re.match(RANGE_RE, range):
        return range.split("..", 1)
    return None


def norm_range_value(value):
    if value is None:
        return None

    match = re.match(RANGE_VALUE_RE, str(value))

    if match is None:
        return None

    modifier = ''
    if match.group('modifier') is not None:
        modifier = 'p'
    return match.group('value') + modifier


def norm_auto_range_value(value):
    if value == "auto":
        return value
    return norm_range_value(value)


def process_video_codec_param(param):
    out_param = param
    if isinstance(out_param, dict):
        out_param = param['codec']
        if 'profile' in param:
            out_param = out_param + ':' + param['profile']
            if 'level' in param:
                out_param = out_param + ':' + param['level']
                if param.get('b_frames') is False:
                    out_param = out_param + ':' + 'bframes_no'

    return out_param


def process_radius(param):
    if param is None:
        return

    if isinstance(param, (list, tuple)):
        if not 1 <= len(param) <= 4:
            raise ValueError("Invalid radius param")
        return ':'.join(normalize_expression(t) for t in param)

    return normalize_expression(str(param))


def process_params(params):
    processed_params = None
    if isinstance(params, dict):
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, list) or isinstance(value, tuple):
                if len(value) == 2 and value[0] == "file":  # keep file parameter as is.
                    processed_params[key] = value
                    continue
                value_list = {"{}[{}]".format(key, i): i_value for i, i_value in enumerate(value)}
                processed_params.update(value_list)
            elif value is not None:
                processed_params[key] = value
    return processed_params


def cleanup_params(params):
    """
    Cleans and normalizes parameters when calculating signature in Upload API.

    :param params:
    :return:
    """
    return dict([(k, __safe_value(v)) for (k, v) in params.items() if v is not None and not v == ""])


def normalize_params(params):
    """
    Normalizes Admin API parameters.

    :param params:
    :return:
    """
    if not params or not isinstance(params, dict):
        return params

    return dict([(k, __bool_string(v)) for (k, v) in params.items() if v is not None and not v == ""])


def sign_request(params, options):
    api_key = options.get("api_key", cloudinary.config().api_key)
    if not api_key:
        raise ValueError("Must supply api_key")
    api_secret = options.get("api_secret", cloudinary.config().api_secret)
    if not api_secret:
        raise ValueError("Must supply api_secret")
    signature_algorithm = options.get("signature_algorithm", cloudinary.config().signature_algorithm)
    signature_version = options.get("signature_version", cloudinary.config().signature_version)

    params = cleanup_params(params)
    params["signature"] = api_sign_request(params, api_secret, signature_algorithm, signature_version)
    params["api_key"] = api_key

    return params


def api_sign_request(params_to_sign, api_secret, algorithm=SIGNATURE_SHA1, signature_version=2):
    """
    Signs API request parameters using the specified algorithm and signature version.

    :param params_to_sign: Parameters to include in the signature
    :param api_secret: API secret key
    :param algorithm: Signature algorithm (default: SHA1)
    :param signature_version: Signature version (default: 2)
        - Version 1: Original behavior without parameter encoding
        - Version 2+: Includes parameter encoding to prevent parameter smuggling
    :return: Computed signature
    """
    to_sign = api_string_to_sign(params_to_sign, signature_version)
    return compute_hex_hash(to_sign + api_secret, algorithm)


def api_string_to_sign(params_to_sign, signature_version=2):
    """
    Generates a string to be signed for API requests.

    :param params_to_sign: Parameters to include in the signature
    :param signature_version: Version of signature algorithm to use:
        - Version 1: Original behavior without parameter encoding
        - Version 2+ (default): Includes parameter encoding to prevent parameter smuggling
    :return: String to be signed
    """
    params = []
    for k, v in params_to_sign.items():
        if v:
            if isinstance(v, list):
                value = ",".join(v)
            elif isinstance(v, bool):
                value = str(v).lower()
            else:
                value = str(v)

            param_string = k + "=" + value
            if signature_version >= 2:
                param_string = _encode_param(param_string)
            params.append(param_string)

    return "&".join(sorted(params))


def _encode_param(value):
    """
    Encodes a parameter for safe inclusion in URL query strings.

    Specifically replaces "&" characters with their percent-encoded equivalent "%26"
    to prevent them from being interpreted as parameter separators in URL query strings.

    :param value: The parameter to encode
    :return: Encoded parameter
    """
    return str(value).replace("&", "%26")


def breakpoint_settings_mapper(breakpoint_settings):
    breakpoint_settings = copy.deepcopy(breakpoint_settings)
    transformation = breakpoint_settings.get("transformation")
    if transformation is not None:
        breakpoint_settings["transformation"], _ = generate_transformation_string(**transformation)
    return breakpoint_settings


def generate_responsive_breakpoints_string(breakpoints):
    if breakpoints is None:
        return None
    breakpoints = build_array(breakpoints)
    return json.dumps(list(map(breakpoint_settings_mapper, breakpoints)))


def finalize_source(source, format, url_suffix):
    source = re.sub(r'([^:])/+', r'\1/', source)
    if re.match(r'^https?:/', source):
        source = smart_escape(source)
        source_to_sign = source
    else:
        source = unquote(source)
        if not PY3:
            source = source.encode('utf8')
        source = smart_escape(source)
        source_to_sign = source
        if url_suffix is not None:
            if re.search(r'[\./]', url_suffix):
                raise ValueError("url_suffix should not include . or /")
            source = source + "/" + url_suffix
        if format is not None:
            source = source + "." + format
            source_to_sign = source_to_sign + "." + format

    return source, source_to_sign


def finalize_resource_type(resource_type, type, url_suffix, use_root_path, shorten):
    upload_type = type or "upload"
    if url_suffix is not None:
        if resource_type == "image" and upload_type == "upload":
            resource_type = "images"
            upload_type = None
        elif resource_type == "raw" and upload_type == "upload":
            resource_type = "files"
            upload_type = None
        else:
            raise ValueError("URL Suffix only supported for image/upload and raw/upload")

    if use_root_path:
        if (resource_type == "image" and upload_type == "upload") or (
                resource_type == "images" and upload_type is None):
            resource_type = None
            upload_type = None
        else:
            raise ValueError("Root path only supported for image/upload")

    if shorten and resource_type == "image" and upload_type == "upload":
        resource_type = "iu"
        upload_type = None

    return resource_type, upload_type


def unsigned_download_url_prefix(source, cloud_name, private_cdn, cdn_subdomain,
                                 secure_cdn_subdomain, cname, secure, secure_distribution):
    """cdn_subdomain and secure_cdn_subdomain
    1) Customers in shared distribution (e.g. res.cloudinary.com)
      if cdn_domain is true uses res-[1-5].cloudinary.com for both http and https.
      Setting secure_cdn_subdomain to false disables this for https.
    2) Customers with private cdn
      if cdn_domain is true uses cloudname-res-[1-5].cloudinary.com for http
      if secure_cdn_domain is true uses cloudname-res-[1-5].cloudinary.com for https
      (please contact support if you require this)
    3) Customers with cname
      if cdn_domain is true uses a[1-5].cname for http. For https, uses the same naming scheme
      as 1 for shared distribution and as 2 for private distribution."""
    shared_domain = not private_cdn
    shard = __crc(source)
    if secure:
        if secure_distribution is None or secure_distribution == cloudinary.OLD_AKAMAI_SHARED_CDN:
            secure_distribution = cloud_name + "-res.cloudinary.com" \
                if private_cdn else cloudinary.SHARED_CDN

        shared_domain = shared_domain or secure_distribution == cloudinary.SHARED_CDN
        if secure_cdn_subdomain is None and shared_domain:
            secure_cdn_subdomain = cdn_subdomain

        if secure_cdn_subdomain:
            secure_distribution = re.sub('res.cloudinary.com', "res-" + shard + ".cloudinary.com",
                                         secure_distribution)

        prefix = "https://" + secure_distribution
    elif cname:
        subdomain = "a" + shard + "." if cdn_subdomain else ""
        prefix = "http://" + subdomain + cname
    else:
        subdomain = cloud_name + "-res" if private_cdn else "res"
        if cdn_subdomain:
            subdomain = subdomain + "-" + shard
        prefix = "http://" + subdomain + ".cloudinary.com"

    if shared_domain:
        prefix += "/" + cloud_name

    return prefix


def build_distribution_domain(options):
    source = options.pop('source', '')
    cloud_name = options.pop("cloud_name", cloudinary.config().cloud_name or None)
    if cloud_name is None:
        raise ValueError("Must supply cloud_name in tag or in configuration")
    secure = options.pop("secure", cloudinary.config().secure)
    private_cdn = options.pop("private_cdn", cloudinary.config().private_cdn)
    cname = options.pop("cname", cloudinary.config().cname)
    secure_distribution = options.pop("secure_distribution",
                                      cloudinary.config().secure_distribution)
    cdn_subdomain = options.pop("cdn_subdomain", cloudinary.config().cdn_subdomain)
    secure_cdn_subdomain = options.pop("secure_cdn_subdomain",
                                       cloudinary.config().secure_cdn_subdomain)

    return unsigned_download_url_prefix(
        source, cloud_name, private_cdn, cdn_subdomain, secure_cdn_subdomain,
        cname, secure, secure_distribution)


def merge(*dict_args):
    result = None
    for dictionary in dict_args:
        if dictionary is not None:
            if result is None:
                result = dictionary.copy()
            else:
                result.update(dictionary)
    return result


def cloudinary_url(source, **options):
    original_source = source

    patch_fetch_format(options)
    type = options.pop("type", "upload")

    transformation, options = generate_transformation_string(**options)

    resource_type = options.pop("resource_type", "image")

    force_version = options.pop("force_version", cloudinary.config().force_version)
    if force_version is None:
        force_version = True

    version = options.pop("version", None)

    format = options.pop("format", None)
    shorten = options.pop("shorten", cloudinary.config().shorten)

    sign_url = options.pop("sign_url", cloudinary.config().sign_url)
    api_secret = options.pop("api_secret", cloudinary.config().api_secret)
    url_suffix = options.pop("url_suffix", None)
    use_root_path = options.pop("use_root_path", cloudinary.config().use_root_path)
    auth_token = options.pop("auth_token", None)
    long_url_signature = options.pop("long_url_signature", cloudinary.config().long_url_signature)
    signature_algorithm = options.pop("signature_algorithm", cloudinary.config().signature_algorithm)
    if auth_token is not False:
        auth_token = merge(cloudinary.config().auth_token, auth_token)

    if (not source) or type == "upload" and re.match(r'^https?:', source):
        return original_source, options

    resource_type, type = finalize_resource_type(
        resource_type, type, url_suffix, use_root_path, shorten)
    source, source_to_sign = finalize_source(source, format, url_suffix)

    if not version and force_version \
            and source_to_sign.find("/") >= 0 \
            and not re.match(r'^https?:/', source_to_sign) \
            and not re.match(r'^v[0-9]+', source_to_sign):
        version = "1"
    if version:
        version = "v" + str(version)
    else:
        version = None

    transformation = re.sub(r'([^:])/+', r'\1/', transformation)

    signature = None
    if sign_url and (not auth_token or auth_token.pop('set_url_signature', False)):
        to_sign = "/".join(__compact([transformation, source_to_sign]))
        if long_url_signature:
            # Long signature forces SHA256
            signature_algorithm = SIGNATURE_SHA256
            chars_length = LONG_URL_SIGNATURE_LENGTH
        else:
            chars_length = SHORT_URL_SIGNATURE_LENGTH
        if signature_algorithm not in signature_algorithms:
            raise ValueError("Unsupported signature algorithm '{}'".format(signature_algorithm))
        hash_fn = signature_algorithms[signature_algorithm]
        signature = "s--" + to_string(
            base64.urlsafe_b64encode(
                hash_fn(to_bytes(to_sign + api_secret)).digest())[0:chars_length]) + "--"

    options["source"] = source
    prefix = build_distribution_domain(options)

    source = "/".join(__compact(
        [prefix, resource_type, type, signature, transformation, version, source]))
    if sign_url and auth_token:
        path = urlparse(source).path
        token = cloudinary.auth_token.generate(**merge(auth_token, {"url": path}))
        source = "%s?%s" % (source, token)
    return source, options


def base_api_url(path, **options):
    cloudinary_prefix = options.get("upload_prefix", cloudinary.config().upload_prefix) \
                        or "https://api.cloudinary.com"
    cloud_name = options.get("cloud_name", cloudinary.config().cloud_name)

    if not cloud_name:
        raise ValueError("Must supply cloud_name")

    path = build_array(path)

    return encode_unicode_url("/".join([cloudinary_prefix, cloudinary.API_VERSION, cloud_name] + path))


def cloudinary_api_url(action='upload', **options):
    resource_type = options.get("resource_type", "image")

    return base_api_url([resource_type, action], **options)


def cloudinary_api_download_url(action, params, **options):
    params = params.copy()
    params["mode"] = "download"
    cloudinary_params = sign_request(params, options)
    return cloudinary_api_url(action, **options) + "?" + urlencode(bracketize_seq(cloudinary_params), True)


def cloudinary_scaled_url(source, width, transformation, options):
    """
    Generates a cloudinary url scaled to specified width.

    :param source:          The resource
    :param width:           Width in pixels of the srcset item
    :param transformation:  Custom transformation that overrides transformations provided in options
    :param options:         A dict with additional options

    :return: Resulting URL of the item
    """

    # preserve options from being destructed
    options = copy.deepcopy(options)

    if transformation:
        if isinstance(transformation, string_types):
            transformation = {"raw_transformation": transformation}

        # Remove all transformation related options
        options = dict((o, options[o]) for o in __URL_KEYS if o in options)
        options.update(transformation)

    scale_transformation = {"crop": "scale", "width": width}

    url_options = options
    patch_fetch_format(url_options)
    url_options = chain_transformations(url_options, scale_transformation)

    return cloudinary_url(source, **url_options)[0]


def smart_escape(source, unsafe=r"([^a-zA-Z0-9_.\-\/:]+)"):
    """
    Based on ruby's CGI::unescape. In addition does not escape / :

    :param source: Source string to escape
    :param unsafe: Unsafe characters

    :return: Escaped string
    """
    def pack(m):
        return to_bytes('%' + "%".join(
            ["%02X" % x for x in struct.unpack('B' * len(m.group(1)), m.group(1))]
        ).upper())

    return to_string(re.sub(to_bytes(unsafe), pack, to_bytes(source)))


def random_public_id():
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits)
                   for _ in range(16))


def signed_preloaded_image(result):
    filename = ".".join([x for x in [result["public_id"], result["format"]] if x])
    path = "/".join([result["resource_type"], "upload", "v" + str(result["version"]), filename])
    return path + "#" + result["signature"]


def now():
    return str(int(time.time()))


def private_download_url(public_id, format, **options):
    cloudinary_params = sign_request({
        "timestamp": now(),
        "public_id": public_id,
        "format": format,
        "type": options.get("type"),
        "attachment": options.get("attachment"),
        "expires_at": options.get("expires_at")
    }, options)

    return cloudinary_api_url("download", **options) + "?" + urlencode(cloudinary_params)


def zip_download_url(tag, **options):
    cloudinary_params = sign_request({
        "timestamp": now(),
        "tag": tag,
        "transformation": generate_transformation_string(**options)[0]
    }, options)

    return cloudinary_api_url("download_tag.zip", **options) + "?" + urlencode(cloudinary_params)


def bracketize_seq(params):
    url_params = dict()
    for param_name in params:
        param_value = params[param_name]
        if isinstance(param_value, list):
            param_name += "[]"
        url_params[param_name] = param_value
    return url_params


def download_archive_url(**options):
    return cloudinary_api_download_url(action="generate_archive", params=archive_params(**options), **options)


def download_zip_url(**options):
    new_options = options.copy()
    new_options.update(target_format="zip")
    return download_archive_url(**new_options)


def download_folder(folder_path, **options):
    """
    Creates and returns a URL that when invoked creates an archive of a folder.
    :param folder_path: The full path from the root that is used to generate download url.
    :type folder_path:  str
    :param options:     Additional options.
    :type options:      dict, optional
    :return:            Signed URL to download the folder.
    :rtype:             str
    """
    options["prefixes"] = folder_path
    options.setdefault("resource_type", "all")

    return download_archive_url(**options)


def download_backedup_asset(asset_id, version_id, **options):
    """
    The returned url allows downloading the backedup asset based on the the asset ID and the version ID.

    Parameters asset_id and version_id are returned with api.resource(<PUBLIC_ID1>, versions=True) API call.

    :param  asset_id:   The asset ID of the asset.
    :type   asset_id:   str
    :param  version_id: The version ID of the asset.
    :type   version_id: str
    :param  options:    Additional options.
    :type   options:    dict, optional
    :return:The signed URL for downloading backup version of the asset.
    :rtype: str
    """
    params = {
        "timestamp": options.get("timestamp", now()),
        "asset_id": asset_id,
        "version_id": version_id
    }
    cloudinary_params = sign_request(params, options)

    return base_api_url("download_backup", **options) + "?" + urlencode(bracketize_seq(cloudinary_params), True)


def generate_auth_token(**options):
    token_options = merge(cloudinary.config().auth_token, options)
    return auth_token.generate(**token_options)


def archive_params(**options):
    if options.get("timestamp") is None:
        timestamp = now()
    else:
        timestamp = options.get("timestamp")
    params = {
        "allow_missing": options.get("allow_missing"),
        "async": options.get("async"),
        "expires_at": options.get("expires_at"),
        "flatten_folders": options.get("flatten_folders"),
        "flatten_transformations": options.get("flatten_transformations"),
        "keep_derived": options.get("keep_derived"),
        "mode": options.get("mode"),
        "notification_url": options.get("notification_url"),
        "phash": options.get("phash"),
        "prefixes": options.get("prefixes") and build_array(options.get("prefixes")),
        "public_ids": options.get("public_ids") and build_array(options.get("public_ids")),
        "fully_qualified_public_ids": options.get("fully_qualified_public_ids") and build_array(
            options.get("fully_qualified_public_ids")),
        "skip_transformation_name": options.get("skip_transformation_name"),
        "tags": options.get("tags") and build_array(options.get("tags")),
        "target_format": options.get("target_format"),
        "target_asset_folder": options.get("target_asset_folder"),
        "target_public_id": options.get("target_public_id"),
        "target_tags": options.get("target_tags") and build_array(options.get("target_tags")),
        "timestamp": timestamp,
        "transformations": build_eager(options.get("transformations")),
        "type": options.get("type"),
        "use_original_filename": options.get("use_original_filename"),
    }
    return params


def build_eager(transformations):
    if transformations is None:
        return None

    return "|".join([build_single_eager(et) for et in build_array(transformations)])


def build_single_eager(options):
    """
    Builds a single eager transformation which consists of transformation and (optionally) format joined by "/"

    :param options: Options containing transformation parameters and (optionally) a "format" key
        format can be a string value (jpg, gif, etc) or can be set to "" (empty string).
        The latter leads to transformation ending with "/", which means "No extension, use original format"
        If format is not provided or set to None, only transformation is used (without the trailing "/")

    :return: Resulting eager transformation string
    """
    if isinstance(options, string_types):
        return options

    trans_str = generate_transformation_string(**options)[0]

    if not trans_str:
        return ""

    file_format = options.get("format")

    return trans_str + ("/" + file_format if file_format is not None else "")


def build_custom_headers(headers):
    if headers is None:
        return None
    elif isinstance(headers, list):
        pass
    elif isinstance(headers, dict):
        headers = [k + ": " + v for k, v in headers.items()]
    else:
        return headers
    return "\n".join(headers)


def build_upload_params(**options):
    params = {param_name: options.get(param_name) for param_name in __SIMPLE_UPLOAD_PARAMS if param_name in options}
    params["upload_preset"] = params.pop("upload_preset", cloudinary.config().upload_preset)

    serialized_params = {
        "timestamp": now(),
        "metadata": encode_context(options.get("metadata")),
        "transformation": generate_transformation_string(**options)[0],
        "headers": build_custom_headers(options.get("headers")),
        "eager": build_eager(options.get("eager")),
        "tags": options.get("tags") and encode_list(build_array(options["tags"])),
        "allowed_formats": options.get("allowed_formats") and encode_list(build_array(options["allowed_formats"])),
        "face_coordinates": encode_double_array(options.get("face_coordinates")),
        "custom_coordinates": encode_double_array(options.get("custom_coordinates")),
        "regions": json_encode(options.get("regions")),
        "context": encode_context(options.get("context")),
        "auto_tagging": options.get("auto_tagging") and str(options.get("auto_tagging")),
        "responsive_breakpoints": generate_responsive_breakpoints_string(options.get("responsive_breakpoints")),
        "access_control": options.get("access_control") and json_encode(
            build_list_of_dicts(options.get("access_control")))
    }

    # make sure that we are in-sync with __SERIALIZED_UPLOAD_PARAMS which are in use by other methods
    serialized_params = {param_name: serialized_params[param_name] for param_name in __SERIALIZED_UPLOAD_PARAMS}

    params.update(serialized_params)

    return params


def handle_file_parameter(file, filename):
    if not file:
        return None

    if PathLibPathType and isinstance(file, PathLibPathType):
        name = filename or file.name
        data = file.read_bytes()
    elif isinstance(file, string_types):
        if is_remote_url(file):
            # URL
            name = None
            data = file
        else:
            # file path
            name = filename or file
            with open(file, "rb") as opened:
                data = opened.read()
    elif hasattr(file, 'read') and callable(file.read):
        # stream
        data = file.read()
        name = filename or (file.name if hasattr(file, 'name') and isinstance(file.name, str) else "stream")
    elif isinstance(file, tuple):
        name, data = file
    else:
        # Not a string, not a stream
        name = filename or "file"
        data = file

    return (name, data) if name else data


def build_multi_and_sprite_params(**options):
    """
    Build params for multi, download_multi, generate_sprite, and download_generated_sprite methods
    """
    tag = options.get("tag")
    urls = options.get("urls")
    if bool(tag) == bool(urls):
        raise ValueError("Either 'tag' or 'urls' parameter has to be set but not both")
    params = {
        "mode": options.get("mode"),
        "timestamp": now(),
        "async": options.get("async"),
        "notification_url": options.get("notification_url"),
        "tag": tag,
        "urls": urls,
        "transformation": generate_transformation_string(fetch_format=options.get("format"), **options)[0]
    }
    return params


def __process_text_options(layer, layer_parameter):
    text_style = str(layer.get("text_style", ""))
    if text_style and not text_style.isspace():
        return text_style

    font_family = layer.get("font_family")
    font_size = layer.get("font_size")
    keywords = []
    for attr, default_value in __LAYER_KEYWORD_PARAMS:
        attr_value = layer.get(attr)
        if attr_value != default_value and attr_value is not None:
            keywords.append(attr_value)

    letter_spacing = layer.get("letter_spacing")
    if letter_spacing is not None:
        keywords.append("letter_spacing_" + str(letter_spacing))

    line_spacing = layer.get("line_spacing")
    if line_spacing is not None:
        keywords.append("line_spacing_" + str(line_spacing))

    font_antialiasing = layer.get("font_antialiasing")
    if font_antialiasing is not None:
        keywords.append("antialias_" + str(font_antialiasing))

    font_hinting = layer.get("font_hinting")
    if font_hinting is not None:
        keywords.append("hinting_" + str(font_hinting))

    if font_size is None and font_family is None and len(keywords) == 0:
        return None

    if font_family is None:
        raise ValueError("Must supply font_family for text in " + layer_parameter)

    if font_size is None:
        raise ValueError("Must supply font_size for text in " + layer_parameter)

    keywords.insert(0, font_size)
    keywords.insert(0, font_family)

    return '_'.join([str(k) for k in keywords])


def process_layer(layer, layer_parameter):
    if isinstance(layer, string_types):
        resource_type = None
        if layer.startswith("fetch:"):
            url = layer[len('fetch:'):]
        elif layer.find(":fetch:", 0, 12) != -1:
            resource_type, _, url = layer.split(":", 2)
        else:
            # nothing to process, a raw string, keep as is.
            return layer

        # handle remote fetch URL
        layer = {"url": url, "type": "fetch"}
        if resource_type:
            layer["resource_type"] = resource_type

    if not isinstance(layer, dict):
        return layer

    resource_type = layer.get("resource_type")
    text = layer.get("text")
    type = layer.get("type")
    public_id = layer.get("public_id")
    format = layer.get("format")
    fetch_url = layer.get("url")
    components = list()

    if text is not None and resource_type is None:
        resource_type = "text"

    if fetch_url and type is None:
        type = "fetch"

    if public_id is not None and format is not None:
        public_id = public_id + "." + format

    if public_id is None and resource_type != "text" and type != "fetch":
        raise ValueError("Must supply public_id for for non-text " + layer_parameter)

    if resource_type is not None and resource_type != "image":
        components.append(resource_type)

    if type is not None and type != "upload":
        components.append(type)

    if resource_type == "text" or resource_type == "subtitles":
        if public_id is None and text is None:
            raise ValueError("Must supply either text or public_id in " + layer_parameter)

        text_options = __process_text_options(layer, layer_parameter)

        if text_options is not None:
            components.append(text_options)

        if public_id is not None:
            public_id = public_id.replace("/", ':')
            components.append(public_id)

        if text is not None:
            var_pattern = VAR_NAME_RE
            parts = filter(lambda p: p is not None, re.split(var_pattern, text))
            encoded_text = []
            for part in parts:
                if re.match(var_pattern, part):
                    encoded_text.append(part)
                else:
                    encoded_text.append(smart_escape(smart_escape(part, r"([,/])")))

            text = ''.join(encoded_text)
            components.append(text)
    elif type == "fetch":
        b64 = base64url_encode(fetch_url)
        components.append(b64)
    else:
        public_id = public_id.replace("/", ':')
        components.append(public_id)

    return ':'.join(components)


IF_OPERATORS = {
    "=": 'eq',
    "!=": 'ne',
    "<": 'lt',
    ">": 'gt',
    "<=": 'lte',
    ">=": 'gte',
    "&&": 'and',
    "||": 'or',
    "*": 'mul',
    "/": 'div',
    "+": 'add',
    "-": 'sub',
    "^": 'pow'
}

PREDEFINED_VARS = {
    "aspect_ratio": "ar",
    "aspectRatio": "ar",
    "current_page": "cp",
    "currentPage": "cp",
    "face_count": "fc",
    "faceCount": "fc",
    "height": "h",
    "initial_aspect_ratio": "iar",
    "initialAspectRatio": "iar",
    "trimmed_aspect_ratio": "tar",
    "trimmedAspectRatio": "tar",
    "initial_height": "ih",
    "initialHeight": "ih",
    "initial_width": "iw",
    "initialWidth": "iw",
    "page_count": "pc",
    "pageCount": "pc",
    "page_x": "px",
    "pageX": "px",
    "page_y": "py",
    "pageY": "py",
    "tags": "tags",
    "width": "w",
    "duration": "du",
    "initial_duration": "idu",
    "initialDuration": "idu",
    "illustration_score": "ils",
    "illustrationScore": "ils",
    "context": "ctx"
}

replaceRE = "((\\|\\||>=|<=|&&|!=|>|=|<|/|-|\\+|\\*|\\^)(?=[ _])|(\\$_*[^_ ]+)|(?<![\\$:])(" + \
            '|'.join(PREDEFINED_VARS.keys()) + "))"


def translate_if(match):
    name = match.group(0)
    return IF_OPERATORS.get(name,
                            PREDEFINED_VARS.get(name,
                                                name))


def process_custom_function(custom_function):
    if not isinstance(custom_function, dict):
        return custom_function

    function_type = custom_function.get("function_type")
    source = custom_function.get("source")
    if function_type == "remote":
        source = base64url_encode(source)

    return ":".join([function_type, source])


def process_custom_pre_function(custom_function):
    value = process_custom_function(custom_function)
    return "pre:{0}".format(value) if value else None


def process_fps(fps):
    """
    Serializes fps transformation parameter

    :param fps: A single number, a list of mixed type, a string, including open-ended and closed range values
                Examples: '24-29.97', 24, 24.973, '-24', [24, 29.97]

    :return: string
    """
    if not isinstance(fps, (list, tuple)):
        return fps

    return "-".join(normalize_expression(f) for f in fps)


def process_ki(ki):
    """
    Serializes keyframe_interval parameter
    :param ki: Keyframe interval. Should be either a string or a positive real number.
    :return: string
    """
    if ki is None:
        return None
    if isinstance(ki, string_types):
        return ki
    if not isinstance(ki, Number):
        raise ValueError("Keyframe interval should be a number or a string")
    if ki <= 0:
        raise ValueError("Keyframe interval should be greater than zero")
    return str(float(ki))


def process_conditional(conditional):
    if conditional is None:
        return conditional
    result = normalize_expression(conditional)
    return result


def normalize_expression(expression):
    if re.match(r'^!.+!$', str(expression)):  # quoted string
        return expression
    elif expression:
        result = str(expression)
        result = re.sub(replaceRE, translate_if, result)
        result = re.sub('[ _]+', '_', result)
        return result
    return expression


def __join_pair(key, value):
    if value is None or value == "":
        return None
    elif value is True:
        return key
    return u"{0}=\"{1}\"".format(key, value)


def html_attrs(attrs, only=None):
    return ' '.join(sorted([__join_pair(key, value) for key, value in attrs.items() if only is None or key in only]))


def __safe_value(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    return v


def __bool_string(v):
    if isinstance(v, bool):
        return "true" if v else "false"

    return v

def __crc(source):
    return str((zlib.crc32(to_bytearray(source)) & 0xffffffff) % 5 + 1)


def __compact(array):
    return filter(lambda x: x, array)


def base64_encode_url(url):
    """
    Returns the Base64-decoded version of url.
    The method tries to unquote the url because quoting it

    :param str url:
        the url to encode. the value is URIdecoded and then
        re-encoded before converting to base64 representation

    """

    try:
        url = unquote(url)
    except Exception:
        pass
    url = smart_escape(url)
    b64 = base64.b64encode(url.encode('utf-8'))
    return b64.decode('ascii')


def base64url_encode(data):
    """
    Url safe version of urlsafe_b64encode with stripped `=` sign at the end.

    :param data: input data

    :return: Base64 URL safe encoded string
    """
    return to_string(base64.urlsafe_b64encode(to_bytes(data)))


def encode_unicode_url(url_str):
    """
    Quote and encode possible unicode url string (applicable for python2)

    :param url_str: Url string to encode

    :return: Encoded string
    """
    if six.PY2:
        url_str = urllib.quote(url_str.encode('utf-8'), ":/?#[]@!$&'()*+,;=")

    return url_str


def __json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Object of type %s is not JSON serializable" % type(obj))


def is_remote_url(file):
    """Basic URL scheme check to define if it's remote URL"""
    return isinstance(file, string_types) and re.match(REMOTE_URL_RE, file)


def file_io_size(file_io):
    """
    Helper function for getting file-like object size(suitable for both files and streams)

    :param file_io: io.IOBase

    :return: size
    """
    initial_position = file_io.tell()
    file_io.seek(0, os.SEEK_END)
    size = file_io.tell()
    file_io.seek(initial_position, os.SEEK_SET)

    return size


def check_property_enabled(f):
    """
    Used as a class method decorator to check whether class is enabled(self.enabled is True)

    :param f: function to call

    :return: None if not enabled, otherwise calls function f
    """
    def wrapper(*args, **kwargs):
        if not args[0].enabled:
            return None
        return f(*args, **kwargs)

    return wrapper


def verify_api_response_signature(public_id, version, signature, algorithm=None):
    """
    Verifies the authenticity of an API response signature

    :param public_id: The public id of the asset as returned in the API response
    :param version:   The version of the asset as returned in the API response
    :param signature: Actual signature. Can be retrieved from the X-Cld-Signature header
    :param algorithm: Name of hashing algorithm to use for calculation of HMACs.
                      By default, uses `cloudinary.config().signature_algorithm`

    :return: Boolean result of the validation
    """
    if not cloudinary.config().api_secret:
        raise Exception('Api secret key is empty')

    parameters_to_sign = {'public_id': public_id,
                          'version': version}

    # Use signature version 1 for backward compatibility
    return signature == api_sign_request(
        parameters_to_sign,
        cloudinary.config().api_secret,
        algorithm or cloudinary.config().signature_algorithm,
        signature_version=1
    )


def verify_notification_signature(body, timestamp, signature, valid_for=7200, algorithm=None):
    """
    Verifies the authenticity of a notification signature

    :param body: Json of the request's body
    :param timestamp: Unix timestamp. Can be retrieved from the X-Cld-Timestamp header
    :param signature: Actual signature. Can be retrieved from the X-Cld-Signature header
    :param valid_for: The desired time in seconds for considering the request valid
    :param algorithm: Name of hashing algorithm to use for calculation of HMACs.
                      By default, uses `cloudinary.config().signature_algorithm`

    :return: Boolean result of the validation
    """
    if not cloudinary.config().api_secret:
        raise Exception('Api secret key is empty')

    if timestamp < time.time() - valid_for:
        return False

    if not isinstance(body, str):
        raise ValueError('Body should be type of string')

    return signature == compute_hex_hash(
        '{}{}{}'.format(body, timestamp, cloudinary.config().api_secret),
        algorithm or cloudinary.config().signature_algorithm)


def get_http_connector(conf, options):
    """
    Used to create http connector, depends on api_proxy and disable_tcp_keep_alive configuration parameters.

    :param conf: configuration object
    :param options: additional options

    :return: ProxyManager if api_proxy is set, otherwise PoolManager object
    """
    if conf.api_proxy:
        if conf.disable_tcp_keep_alive:
            return ProxyManager(conf.api_proxy, **options)

        return TCPKeepAliveProxyManager(conf.api_proxy, **options)

    if conf.disable_tcp_keep_alive:
        return PoolManager(**options)

    return TCPKeepAlivePoolManager(**options)


def encode_list(obj):
    if isinstance(obj, list):
        return ",".join(obj)
    return obj


def safe_cast(val, casting_fn, default=None):
    """
    Attempts to cast a value to another using a given casting function
    Will return a default value if casting fails (configurable, defaults to None)

    :param val: The value to cast
    :param casting_fn: The casting function that will receive the value to cast
    :param default: The return value if casting fails

    :return: Result of casting the value or the value of the default parameter
    """
    try:
        return casting_fn(val)
    except (ValueError, TypeError):
        return default


def __id(x):
    """
    Identity function. Returns the passed in values.
    """
    return x


def unique(collection, key=None):
    """
    Removes duplicates from collection using key function

    :param collection: The collection to remove duplicates from
    :param key: The function to generate key from each element. If not passed, identity function is used
    """
    if key is None:
        key = __id

    to_return = OrderedDict()

    for element in collection:
        to_return[key(element)] = element

    return list(to_return.values())


def fq_public_id(public_id, resource_type="image", type="upload"):
    """
    Returns the fully qualified public id of form resource_type/type/public_id.

    :param public_id: The public ID of the asset.
    :type public_id: str
    :param resource_type: The type of the asset. Defaults to "image".
    :type resource_type: str
    :param type: The upload type. Defaults to "upload".
    :type type: str

    :return:
    """
    return "{resource_type}/{type}/{public_id}".format(resource_type=resource_type, type=type, public_id=public_id)
