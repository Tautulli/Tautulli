# Copyright Cloudinary
import base64
import copy
import hashlib
import json
import random
import re
import string
import struct
import time
import zlib
from collections import OrderedDict
from datetime import datetime, date
from fractions import Fraction

import six.moves.urllib.parse
from six import iteritems

import cloudinary
from cloudinary import auth_token
from cloudinary.compat import PY3, to_bytes, to_bytearray, to_string, string_types, urlparse

VAR_NAME_RE = r'(\$\([a-zA-Z]\w+\))'

urlencode = six.moves.urllib.parse.urlencode
unquote = six.moves.urllib.parse.unquote

""" @deprecated: use cloudinary.SHARED_CDN """
SHARED_CDN = "res.cloudinary.com"

DEFAULT_RESPONSIVE_WIDTH_TRANSFORMATION = {"width": "auto", "crop": "limit"}

RANGE_VALUE_RE = r'^(?P<value>(\d+\.)?\d+)(?P<modifier>[%pP])?$'
RANGE_RE = r'^(\d+\.)?\d+[%pP]?\.\.(\d+\.)?\d+[%pP]?$'
FLOAT_RE = r'^(\d+)\.(\d+)?$'
__LAYER_KEYWORD_PARAMS = [("font_weight", "normal"),
                          ("font_style", "normal"),
                          ("text_decoration", "none"),
                          ("text_align", None),
                          ("stroke", "none")]


def build_array(arg):
    if isinstance(arg, list):
        return arg
    elif arg is None:
        return []
    else:
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
    else:
        return ",".join([str(i) for i in array])


def encode_dict(arg):
    if isinstance(arg, dict):
        if PY3:
            items = arg.items()
        else:
            items = arg.iteritems()
        return "|".join((k + "=" + v) for k, v in items)
    else:
        return arg


def encode_context(context):
    """
       :param context: dict of context to be encoded
       :return: a joined string of all keys and values properly escaped and separated by a pipe character
    """

    if not isinstance(context, dict):
        return context

    return "|".join(("{}={}".format(k, v.replace("=", "\\=").replace("|", "\\|"))) for k, v in iteritems(context))


def json_encode(value):
    """
    Converts value to a json encoded string

    :param value: value to be encoded

    :return: JSON encoded string
    """
    return json.dumps(value, default=__json_serializer, separators=(',', ':'))


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
            else:
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
    start_offset = norm_range_value(options.pop("start_offset", None))
    end_offset = norm_range_value(options.pop("end_offset", None))
    offset = split_range(options.pop("offset", None))
    if offset:
        start_offset = norm_range_value(offset[0])
        end_offset = norm_range_value(offset[1])

    video_codec = process_video_codec_param(options.pop("video_codec", None))

    aspect_ratio = options.pop("aspect_ratio", None)
    if isinstance(aspect_ratio, Fraction):
        aspect_ratio = str(aspect_ratio.numerator) + ":" + str(aspect_ratio.denominator)

    overlay = process_layer(options.pop("overlay", None), "overlay")
    underlay = process_layer(options.pop("underlay", None), "underlay")
    if_value = process_conditional(options.pop("if", None))

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
        "h": normalize_expression(height),
        "l": overlay,
        "o": normalize_expression(options.pop('opacity',None)),
        "q": normalize_expression(options.pop('quality',None)),
        "r": normalize_expression(options.pop('radius',None)),
        "so": normalize_expression(start_offset),
        "t": named_transformation,
        "u": underlay,
        "w": normalize_expression(width),
        "x": normalize_expression(options.pop('x',None)),
        "y": normalize_expression(options.pop('y',None)),
        "vc": video_codec,
        "z": normalize_expression(options.pop('zoom',None))
    }
    simple_params = {
        "ac": "audio_codec",
        "af": "audio_frequency",
        "br": "bit_rate",
        "cs": "color_space",
        "d": "default_image",
        "dl": "delay",
        "dn": "density",
        "f": "fetch_format",
        "g": "gravity",
        "ki": "keyframe_interval",
        "p": "prefix",
        "pg": "page",
        "sp": "streaming_profile",
        "vs": "video_sampling",
    }

    for param, option in simple_params.items():
        params[param] = options.pop(option, None)

    variables = options.pop('variables',{})
    var_params = []
    for key,value in options.items():
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
    transformation = ",".join(sorted_params)
    if "raw_transformation" in options:
        transformation = transformation + "," + options.pop("raw_transformation")
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


def is_fraction(width):
    width = str(width)
    return re.match(FLOAT_RE, width) and float(width) < 1


def split_range(range):
    if (isinstance(range, list) or isinstance(range, tuple)) and len(range) >= 2:
        return [range[0], range[-1]]
    elif isinstance(range, string_types) and re.match(RANGE_RE, range):
        return range.split("..", 1)
    else:
        return None


def norm_range_value(value):
    if value is None: return None

    match = re.match(RANGE_VALUE_RE, str(value))

    if match is None: return None

    modifier = ''
    if match.group('modifier') is not None:
      modifier = 'p'
    return match.group('value') + modifier


def process_video_codec_param(param):
    out_param = param
    if isinstance(out_param, dict):
        out_param = param['codec']
        if 'profile' in param:
            out_param = out_param + ':' + param['profile']
            if 'level' in param:
                out_param = out_param + ':' + param['level']
    return out_param


def cleanup_params(params):
    return dict([(k, __safe_value(v)) for (k, v) in params.items() if v is not None and not v == ""])


def sign_request(params, options):
    api_key = options.get("api_key", cloudinary.config().api_key)
    if not api_key: raise ValueError("Must supply api_key")
    api_secret = options.get("api_secret", cloudinary.config().api_secret)
    if not api_secret: raise ValueError("Must supply api_secret")

    params = cleanup_params(params)
    params["signature"] = api_sign_request(params, api_secret)
    params["api_key"] = api_key

    return params


def api_sign_request(params_to_sign, api_secret):
    params = [(k + "=" + (",".join(v) if isinstance(v, list) else str(v))) for k, v in params_to_sign.items() if v]
    to_sign = "&".join(sorted(params))
    return hashlib.sha1(to_bytes(to_sign + api_secret)).hexdigest()


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
        if not PY3: source = source.encode('utf8')
        source = smart_escape(source)
        source_to_sign = source
        if url_suffix is not None:
            if re.search(r'[\./]', url_suffix): raise ValueError("url_suffix should not include . or /")
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
        if (resource_type == "image" and upload_type == "upload") or (resource_type == "images" and upload_type is None):
            resource_type = None
            upload_type = None
        else:
            raise ValueError("Root path only supported for image/upload")

    if shorten and resource_type == "image" and upload_type == "upload":
        resource_type = "iu"
        upload_type = None

    return resource_type, upload_type


def unsigned_download_url_prefix(source, cloud_name, private_cdn, cdn_subdomain, secure_cdn_subdomain, cname, secure,
                                 secure_distribution):
    """cdn_subdomain and secure_cdn_subdomain
    1) Customers in shared distribution (e.g. res.cloudinary.com)
      if cdn_domain is true uses res-[1-5].cloudinary.com for both http and https. Setting secure_cdn_subdomain to false disables this for https.
    2) Customers with private cdn
      if cdn_domain is true uses cloudname-res-[1-5].cloudinary.com for http
      if secure_cdn_domain is true uses cloudname-res-[1-5].cloudinary.com for https (please contact support if you require this)
    3) Customers with cname
      if cdn_domain is true uses a[1-5].cname for http. For https, uses the same naming scheme as 1 for shared distribution and as 2 for private distribution."""
    shared_domain = not private_cdn
    shard = __crc(source)
    if secure:
        if secure_distribution is None or secure_distribution == cloudinary.OLD_AKAMAI_SHARED_CDN:
            secure_distribution = cloud_name + "-res.cloudinary.com" if private_cdn else cloudinary.SHARED_CDN

        shared_domain = shared_domain or secure_distribution == cloudinary.SHARED_CDN
        if secure_cdn_subdomain is None and shared_domain:
            secure_cdn_subdomain = cdn_subdomain

        if secure_cdn_subdomain:
            secure_distribution = re.sub('res.cloudinary.com', "res-" + shard + ".cloudinary.com", secure_distribution)

        prefix = "https://" + secure_distribution
    elif cname:
        subdomain = "a" + shard + "." if cdn_subdomain else ""
        prefix = "http://" + subdomain + cname
    else:
        subdomain = cloud_name + "-res" if private_cdn else "res"
        if cdn_subdomain: subdomain = subdomain + "-" + shard
        prefix = "http://" + subdomain + ".cloudinary.com"

    if shared_domain: prefix += "/" + cloud_name

    return prefix


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

    type = options.pop("type", "upload")
    if type == 'fetch':
        options["fetch_format"] = options.get("fetch_format", options.pop("format", None))
    transformation, options = generate_transformation_string(**options)

    resource_type = options.pop("resource_type", "image")
    version = options.pop("version", None)
    format = options.pop("format", None)
    cdn_subdomain = options.pop("cdn_subdomain", cloudinary.config().cdn_subdomain)
    secure_cdn_subdomain = options.pop("secure_cdn_subdomain", cloudinary.config().secure_cdn_subdomain)
    cname = options.pop("cname", cloudinary.config().cname)
    shorten = options.pop("shorten", cloudinary.config().shorten)

    cloud_name = options.pop("cloud_name", cloudinary.config().cloud_name or None)
    if cloud_name is None:
        raise ValueError("Must supply cloud_name in tag or in configuration")
    secure = options.pop("secure", cloudinary.config().secure)
    private_cdn = options.pop("private_cdn", cloudinary.config().private_cdn)
    secure_distribution = options.pop("secure_distribution", cloudinary.config().secure_distribution)
    sign_url = options.pop("sign_url", cloudinary.config().sign_url)
    api_secret = options.pop("api_secret", cloudinary.config().api_secret)
    url_suffix = options.pop("url_suffix", None)
    use_root_path = options.pop("use_root_path", cloudinary.config().use_root_path)
    auth_token = options.pop("auth_token", None)
    if auth_token is not False:
        auth_token = merge(cloudinary.config().auth_token, auth_token)

    if (not source) or type == "upload" and re.match(r'^https?:', source):
        return original_source, options

    resource_type, type = finalize_resource_type(resource_type, type, url_suffix, use_root_path, shorten)
    source, source_to_sign = finalize_source(source, format, url_suffix)

    if source_to_sign.find("/") >= 0 \
            and not re.match(r'^https?:/', source_to_sign) \
            and not re.match(r'^v[0-9]+', source_to_sign) \
            and not version:
        version = "1"
    if version: version = "v" + str(version)

    transformation = re.sub(r'([^:])/+', r'\1/', transformation)

    signature = None
    if sign_url and not auth_token:
        to_sign = "/".join(__compact([transformation, source_to_sign]))
        signature = "s--" + to_string(
            base64.urlsafe_b64encode(hashlib.sha1(to_bytes(to_sign + api_secret)).digest())[0:8]) + "--"

    prefix = unsigned_download_url_prefix(source, cloud_name, private_cdn, cdn_subdomain, secure_cdn_subdomain, cname,
                                          secure, secure_distribution)
    source = "/".join(__compact([prefix, resource_type, type, signature, transformation, version, source]))
    if sign_url and auth_token:
        path = urlparse(source).path
        token = cloudinary.auth_token.generate( **merge(auth_token, {"url": path}))
        source = "%s?%s" % (source, token)
    return source, options


def cloudinary_api_url(action='upload', **options):
    cloudinary_prefix = options.get("upload_prefix", cloudinary.config().upload_prefix) or "https://api.cloudinary.com"
    cloud_name = options.get("cloud_name", cloudinary.config().cloud_name)
    if not cloud_name: raise ValueError("Must supply cloud_name")
    resource_type = options.get("resource_type", "image")
    return "/".join([cloudinary_prefix, "v1_1", cloud_name, resource_type, action])


# Based on ruby's CGI::unescape. In addition does not escape / :
def smart_escape(source,unsafe = r"([^a-zA-Z0-9_.\-\/:]+)"):
    def pack(m):
        return to_bytes('%' + "%".join(["%02X" % x for x in struct.unpack('B' * len(m.group(1)), m.group(1))]).upper())
    return to_string(re.sub(to_bytes(unsafe), pack, to_bytes(source)))


def random_public_id():
    return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(16))


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
    params = options.copy()
    params.update(mode="download")
    cloudinary_params = sign_request(archive_params(**params), options)
    return cloudinary_api_url("generate_archive", **options) + "?" + urlencode(bracketize_seq(cloudinary_params), True)


def download_zip_url(**options):
    new_options = options.copy()
    new_options.update(target_format="zip")
    return download_archive_url(**new_options)

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
        "skip_transformation_name": options.get("skip_transformation_name"),
        "tags": options.get("tags") and build_array(options.get("tags")),
        "target_format": options.get("target_format"),
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
    eager = []
    for tr in build_array(transformations):
        if isinstance(tr, string_types):
            single_eager = tr
        else:
            ext = tr.get("format")
            single_eager = "/".join([x for x in [generate_transformation_string(**tr)[0], ext] if x])
        eager.append(single_eager)
    return "|".join(eager)


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
    params = {"timestamp": now(),
              "transformation": generate_transformation_string(**options)[0],
              "public_id": options.get("public_id"),
              "callback": options.get("callback"),
              "format": options.get("format"),
              "type": options.get("type"),
              "backup": options.get("backup"),
              "faces": options.get("faces"),
              "image_metadata": options.get("image_metadata"),
              "exif": options.get("exif"),
              "colors": options.get("colors"),
              "headers": build_custom_headers(options.get("headers")),
              "eager": build_eager(options.get("eager")),
              "use_filename": options.get("use_filename"),
              "unique_filename": options.get("unique_filename"),
              "discard_original_filename": options.get("discard_original_filename"),
              "invalidate": options.get("invalidate"),
              "notification_url": options.get("notification_url"),
              "eager_notification_url": options.get("eager_notification_url"),
              "eager_async": options.get("eager_async"),
              "proxy": options.get("proxy"),
              "folder": options.get("folder"),
              "overwrite": options.get("overwrite"),
              "tags": options.get("tags") and ",".join(build_array(options["tags"])),
              "allowed_formats": options.get("allowed_formats") and ",".join(build_array(options["allowed_formats"])),
              "face_coordinates": encode_double_array(options.get("face_coordinates")),
              "custom_coordinates": encode_double_array(options.get("custom_coordinates")),
              "context": encode_context(options.get("context")),
              "moderation": options.get("moderation"),
              "raw_convert": options.get("raw_convert"),
              "quality_override": options.get("quality_override"),
              "ocr": options.get("ocr"),
              "categorization": options.get("categorization"),
              "detection": options.get("detection"),
              "similarity_search": options.get("similarity_search"),
              "background_removal": options.get("background_removal"),
              "upload_preset": options.get("upload_preset"),
              "phash": options.get("phash"),
              "return_delete_token": options.get("return_delete_token"),
              "auto_tagging": options.get("auto_tagging") and str(options.get("auto_tagging")),
              "responsive_breakpoints": generate_responsive_breakpoints_string(options.get("responsive_breakpoints")),
              "async": options.get("async"),
              "access_control": options.get("access_control") and json_encode(build_list_of_dicts(options.get("access_control")))}
    return params


def __process_text_options(layer, layer_parameter):
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
    if isinstance(layer, string_types) and layer.startswith("fetch:"):
        layer = {"url": layer[len('fetch:'):]}
    if not isinstance(layer, dict):
        return layer

    resource_type = layer.get("resource_type")
    text = layer.get("text")
    type = layer.get("type")
    public_id = layer.get("public_id")
    format = layer.get("format")
    fetch = layer.get("url")
    components = list()

    if text is not None and resource_type is None:
        resource_type = "text"

    if fetch and resource_type is None:
        resource_type = "fetch"

    if public_id is not None and format is not None:
        public_id = public_id + "." + format

    if public_id is None and resource_type != "text" and resource_type != "fetch":
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
            match = re.findall(var_pattern,text)

            parts= filter(lambda p: p is not None, re.split(var_pattern,text))
            encoded_text = []
            for part in parts:
                if re.match(var_pattern,part):
                    encoded_text.append(part)
                else:
                    encoded_text.append(smart_escape(smart_escape(part, r"([,/])")))

            text = ''.join(encoded_text)
            # text = text.replace("%2C", "%252C")
            # text = text.replace("/", "%252F")
            components.append(text)
    elif resource_type == "fetch":
        b64 = base64_encode_url(fetch)
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
    "-": 'sub'
}

PREDEFINED_VARS = {
    "aspect_ratio": "ar",
    "current_page": "cp",
    "face_count": "fc",
    "height": "h",
    "initial_aspect_ratio": "iar",
    "initial_height": "ih",
    "initial_width": "iw",
    "page_count": "pc",
    "page_x": "px",
    "page_y": "py",
    "tags": "tags",
    "width": "w"
}

replaceRE = "((\\|\\||>=|<=|&&|!=|>|=|<|/|-|\\+|\\*)(?=[ _])|" + '|'.join(PREDEFINED_VARS.keys())+ ")"


def translate_if(match):
    name = match.group(0)
    return IF_OPERATORS.get(name,
                            PREDEFINED_VARS.get(name,
                                              name))

def process_conditional(conditional):
    if conditional is None:
        return conditional
    result = normalize_expression(conditional)
    return result

def normalize_expression(expression):
    if re.match(r'^!.+!$',str(expression)): # quoted string
        return expression
    elif expression:
        result = str(expression)
        result = re.sub(replaceRE, translate_if, result)
        result = re.sub('[ _]+', '_', result)
        return result
    else:
        return expression

def __join_pair(key, value):
    if value is None or value == "":
        return None
    elif value is True:
        return key
    else:
        return u"{0}=\"{1}\"".format(key, value)


def html_attrs(attrs, only=None):
    return ' '.join(sorted([__join_pair(key, value) for key, value in attrs.items() if only is None or key in only]))


def __safe_value(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    else:
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
    except:
        pass
    url = smart_escape(url)
    b64 = base64.b64encode(url.encode('utf-8'))
    return b64.decode('ascii')


def __json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Object of type %s is not JSON serializable" % type(obj))
