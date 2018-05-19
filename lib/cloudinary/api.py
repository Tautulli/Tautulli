# Copyright Cloudinary

import email.utils
import json
import socket

import cloudinary
from six import string_types

import urllib3
import certifi

from cloudinary import utils
from urllib3.exceptions import HTTPError

logger = cloudinary.logger

# intentionally one-liners
class Error(Exception): pass
class NotFound(Error): pass
class NotAllowed(Error): pass
class AlreadyExists(Error): pass
class RateLimited(Error): pass
class BadRequest(Error): pass
class GeneralError(Error): pass
class AuthorizationRequired(Error): pass


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
        self.rate_limit_allowed = int(response.headers["x-featureratelimit-limit"])
        self.rate_limit_reset_at = email.utils.parsedate(response.headers["x-featureratelimit-reset"])
        self.rate_limit_remaining = int(response.headers["x-featureratelimit-remaining"])

_http = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi.where()
        )


def ping(**options):
    return call_api("get", ["ping"], {}, **options)


def usage(**options):
    return call_api("get", ["usage"], {}, **options)


def resource_types(**options):
    return call_api("get", ["resources"], {}, **options)


def resources(**options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", None)
    uri = ["resources", resource_type]
    if upload_type: uri.append(upload_type)
    params = only(options,
                  "next_cursor", "max_results", "prefix", "tags", "context", "moderations", "direction", "start_at")
    return call_api("get", uri, params, **options)


def resources_by_tag(tag, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "tags", tag]
    params = only(options, "next_cursor", "max_results", "tags", "context", "moderations", "direction")
    return call_api("get", uri, params, **options)


def resources_by_moderation(kind, status, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "moderations", kind, status]
    params = only(options, "next_cursor", "max_results", "tags", "context", "moderations", "direction")
    return call_api("get", uri, params, **options)


def resources_by_ids(public_ids, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = dict(only(options, "tags", "moderations", "context"), public_ids=public_ids)
    return call_api("get", uri, params, **options)


def resource(public_id, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type, public_id]
    params = only(options, "exif", "faces", "colors", "image_metadata", "pages", "phash", "coordinates", "max_results")
    return call_api("get", uri, params, **options)


def update(public_id, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type, public_id]
    params = only(options, "moderation_status", "raw_convert",
                  "quality_override", "ocr",
                  "categorization", "detection", "similarity_search",
                  "background_removal", "notification_url")
    if "tags" in options:
        params["tags"] = ",".join(utils.build_array(options["tags"]))
    if "face_coordinates" in options:
        params["face_coordinates"] = utils.encode_double_array(options.get("face_coordinates"))
    if "custom_coordinates" in options:
        params["custom_coordinates"] = utils.encode_double_array(options.get("custom_coordinates"))
    if "context" in options:
        params["context"] = utils.encode_context(options.get("context"))
    if "auto_tagging" in options:
        params["auto_tagging"] = str(options.get("auto_tagging"))
    if "access_control" in options:
        params["access_control"] = utils.json_encode(utils.build_list_of_dicts(options.get("access_control")))

    return call_api("post", uri, params, **options)


def delete_resources(public_ids, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = __delete_resource_params(options, public_ids=public_ids)
    return call_api("delete", uri, params, **options)


def delete_resources_by_prefix(prefix, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = __delete_resource_params(options, prefix=prefix)
    return call_api("delete", uri, params, **options)


def delete_all_resources(**options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = __delete_resource_params(options, all=True)
    return call_api("delete", uri, params, **options)


def delete_resources_by_tag(tag, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "tags", tag]
    params = __delete_resource_params(options)
    return call_api("delete", uri, params, **options)


def delete_derived_resources(derived_resource_ids, **options):
    uri = ["derived_resources"]
    params = {"derived_resource_ids": derived_resource_ids}
    return call_api("delete", uri, params, **options)


def delete_derived_by_transformation(public_ids, transformations,
                                     resource_type='image', type='upload', invalidate=None,
                                     **options):
    """
    Delete derived resources of public ids, identified by transformations

    :param public_ids: the base resources
    :type public_ids: list of str
    :param transformations: the transformation of derived resources, optionally including the format
    :type transformations: list of (dict or str)
    :param type: The upload type
    :type type: str
    :param resource_type: The type of the resource: defaults to "image"
    :type resource_type: str
    :param invalidate: (optional) True to invalidate the resources after deletion
    :type invalidate: bool
    :return: a list of the public ids for which derived resources were deleted
    :rtype: dict
    """
    uri = ["resources", resource_type, type]
    if not isinstance(public_ids, list):
        public_ids = [public_ids]
    params = {"public_ids": public_ids,
              "transformations": utils.build_eager(transformations),
              "keep_original": True}
    if invalidate is not None:
        params['invalidate'] = invalidate
    return call_api("delete", uri, params, **options)


def tags(**options):
    resource_type = options.pop("resource_type", "image")
    uri = ["tags", resource_type]
    return call_api("get", uri, only(options, "next_cursor", "max_results", "prefix"), **options)


def transformations(**options):
    uri = ["transformations"]
    return call_api("get", uri, only(options, "next_cursor", "max_results"), **options)


def transformation(transformation, **options):
    uri = ["transformations", transformation_string(transformation)]
    return call_api("get", uri, only(options, "next_cursor", "max_results"), **options)


def delete_transformation(transformation, **options):
    uri = ["transformations", transformation_string(transformation)]
    return call_api("delete", uri, {}, **options)


# updates - currently only supported update is the "allowed_for_strict" boolean flag and unsafe_update
def update_transformation(transformation, **options):
    uri = ["transformations", transformation_string(transformation)]
    updates = only(options, "allowed_for_strict")
    if "unsafe_update" in options:
        updates["unsafe_update"] = transformation_string(options.get("unsafe_update"))
    if not updates: raise Exception("No updates given")

    return call_api("put", uri, updates, **options)


def create_transformation(name, definition, **options):
    uri = ["transformations", name]
    return call_api("post", uri, {"transformation": transformation_string(definition)}, **options)


def publish_by_ids(public_ids, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "publish_resources"]
    params = dict(only(options, "type", "overwrite", "invalidate"), public_ids=public_ids)
    return call_api("post", uri, params, **options)


def publish_by_prefix(prefix, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "publish_resources"]
    params = dict(only(options, "type", "overwrite", "invalidate"), prefix=prefix)
    return call_api("post", uri, params, **options)


def publish_by_tag(tag, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "publish_resources"]
    params = dict(only(options, "type", "overwrite", "invalidate"), tag=tag)
    return call_api("post", uri, params, **options)


def upload_presets(**options):
    uri = ["upload_presets"]
    return call_api("get", uri, only(options, "next_cursor", "max_results"), **options)


def upload_preset(name, **options):
    uri = ["upload_presets", name]
    return call_api("get", uri, only(options, "max_results"), **options)


def delete_upload_preset(name, **options):
    uri = ["upload_presets", name]
    return call_api("delete", uri, {}, **options)


def update_upload_preset(name, **options):
    uri = ["upload_presets", name]
    params = utils.build_upload_params(**options)
    params = utils.cleanup_params(params)
    params.update(only(options, "unsigned", "disallow_public_id"))
    return call_api("put", uri, params, **options)


def create_upload_preset(**options):
    uri = ["upload_presets"]
    params = utils.build_upload_params(**options)
    params = utils.cleanup_params(params)
    params.update(only(options, "unsigned", "disallow_public_id", "name"))
    return call_api("post", uri, params, **options)


def root_folders(**options):
    return call_api("get", ["folders"], {}, **options)


def subfolders(of_folder_path, **options):
    return call_api("get", ["folders", of_folder_path], {}, **options)


def restore(public_ids, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type, "restore"]
    params = dict(public_ids=public_ids)
    return call_api("post", uri, params, **options)


def upload_mappings(**options):
    uri = ["upload_mappings"]
    return call_api("get", uri, only(options, "next_cursor", "max_results"), **options)


def upload_mapping(name, **options):
    uri = ["upload_mappings"]
    params = dict(folder=name)
    return call_api("get", uri, params, **options)


def delete_upload_mapping(name, **options):
    uri = ["upload_mappings"]
    params = dict(folder=name)
    return call_api("delete", uri, params, **options)


def update_upload_mapping(name, **options):
    uri = ["upload_mappings"]
    params = dict(folder=name)
    params.update(only(options, "template"))
    return call_api("put", uri, params, **options)


def create_upload_mapping(name, **options):
    uri = ["upload_mappings"]
    params = dict(folder=name)
    params.update(only(options, "template"))
    return call_api("post", uri, params, **options)


def list_streaming_profiles(**options):
    uri = ["streaming_profiles"]
    return call_api('GET', uri, {}, **options)


def get_streaming_profile(name, **options):
    uri = ["streaming_profiles", name]
    return call_api('GET', uri, {}, **options)


def delete_streaming_profile(name, **options):
    uri = ["streaming_profiles", name]
    return call_api('DELETE', uri, {}, **options)


def create_streaming_profile(name, **options):
    uri = ["streaming_profiles"]
    params = __prepare_streaming_profile_params(**options)
    params["name"] = name
    return call_api('POST', uri, params, **options)


def update_streaming_profile(name, **options):
    uri = ["streaming_profiles", name]
    params = __prepare_streaming_profile_params(**options)
    return call_api('PUT', uri, params, **options)


def call_json_api(method, uri, jsonBody, **options):
    logger.debug(jsonBody)
    data = json.dumps(jsonBody).encode('utf-8')
    return _call_api(method, uri, body=data, headers={'Content-Type': 'application/json'}, **options)


def call_api(method, uri, params, **options):
    return _call_api(method, uri, params=params, **options)


def _call_api(method, uri, params=None, body=None, headers=None, **options):
    prefix = options.pop("upload_prefix",
                         cloudinary.config().upload_prefix) or "https://api.cloudinary.com"
    cloud_name = options.pop("cloud_name", cloudinary.config().cloud_name)
    if not cloud_name: raise Exception("Must supply cloud_name")
    api_key = options.pop("api_key", cloudinary.config().api_key)
    if not api_key: raise Exception("Must supply api_key")
    api_secret = options.pop("api_secret", cloudinary.config().api_secret)
    if not cloud_name: raise Exception("Must supply api_secret")
    api_url = "/".join([prefix, "v1_1", cloud_name] + uri)

    processed_params = None
    if isinstance(params, dict):
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, list):
                value_list = {"{}[{}]".format(key, i): i_value for i, i_value in enumerate(value)}
                processed_params.update(value_list)
            elif value:
                processed_params[key] = value

    # Add authentication
    req_headers = urllib3.make_headers(
        basic_auth="{0}:{1}".format(api_key, api_secret),
        user_agent=cloudinary.get_user_agent()
    )
    if headers is not None:
        req_headers.update(headers)
    kw = {}
    if 'timeout' in options:
        kw['timeout'] = options['timeout']
    if body is not None:
        kw['body'] = body
    try:
        response = _http.request(method.upper(), api_url, processed_params, req_headers, **kw)
        body = response.data
    except HTTPError as e:
        raise GeneralError("Unexpected error {0}", e.message)
    except socket.error as e:
        raise GeneralError("Socket Error: %s" % (str(e)))

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


def only(source, *keys):
    return {key: source[key] for key in keys if key in source}


def transformation_string(transformation):
    if isinstance(transformation, string_types):
        return transformation
    else:
        return cloudinary.utils.generate_transformation_string(**transformation)[0]


def __prepare_streaming_profile_params(**options):
    params = only(options, "display_name")
    if "representations" in options:
        representations = [{"transformation": transformation_string(trans)} for trans in options["representations"]]
        params["representations"] = json.dumps(representations)
    return params

def __delete_resource_params(options, **params):
    p = dict(transformations=utils.build_eager(options.get('transformations')),
             **only(options, "keep_original", "next_cursor", "invalidate"))
    p.update(params)
    return p
