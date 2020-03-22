# Copyright Cloudinary

import email.utils
import json
import socket

import urllib3
from six import string_types
from urllib3.exceptions import HTTPError

import cloudinary
from cloudinary import utils
from cloudinary.exceptions import (
    BadRequest,
    AuthorizationRequired,
    NotAllowed,
    NotFound,
    AlreadyExists,
    RateLimited,
    GeneralError
)

logger = cloudinary.logger

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


_http = utils.get_http_connector(cloudinary.config(), cloudinary.CERT_KWARGS)


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
    if upload_type:
        uri.append(upload_type)
    params = only(options, "next_cursor", "max_results", "prefix", "tags",
                  "context", "moderations", "direction", "start_at")
    return call_api("get", uri, params, **options)


def resources_by_tag(tag, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "tags", tag]
    params = only(options, "next_cursor", "max_results", "tags",
                  "context", "moderations", "direction")
    return call_api("get", uri, params, **options)


def resources_by_moderation(kind, status, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "moderations", kind, status]
    params = only(options, "next_cursor", "max_results", "tags",
                  "context", "moderations", "direction")
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
    params = only(options, "exif", "faces", "colors", "image_metadata", "cinemagraph_analysis",
                  "pages", "phash", "coordinates", "max_results", "quality_analysis", "derived_next_cursor")
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
        params["face_coordinates"] = utils.encode_double_array(
            options.get("face_coordinates"))
    if "custom_coordinates" in options:
        params["custom_coordinates"] = utils.encode_double_array(
            options.get("custom_coordinates"))
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
    """Delete derived resources of public ids, identified by transformations

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
    params = only(options, "named", "next_cursor", "max_results")

    return call_api("get", uri, params, **options)


def transformation(transformation, **options):
    uri = ["transformations"]

    params = only(options, "next_cursor", "max_results")
    params["transformation"] = utils.build_single_eager(transformation)

    return call_api("get", uri, params, **options)


def delete_transformation(transformation, **options):
    uri = ["transformations"]

    params = {"transformation": utils.build_single_eager(transformation)}

    return call_api("delete", uri, params, **options)


# updates - currently only supported update is the "allowed_for_strict"
# boolean flag and unsafe_update
def update_transformation(transformation, **options):
    uri = ["transformations"]

    updates = only(options, "allowed_for_strict")

    if "unsafe_update" in options:
        updates["unsafe_update"] = transformation_string(options.get("unsafe_update"))

    updates["transformation"] = utils.build_single_eager(transformation)

    return call_api("put", uri, updates, **options)


def create_transformation(name, definition, **options):
    uri = ["transformations"]

    params = {"name": name, "transformation": utils.build_single_eager(definition)}

    return call_api("post", uri, params, **options)


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
    params.update(only(options, "unsigned", "disallow_public_id", "live"))
    return call_api("put", uri, params, **options)


def create_upload_preset(**options):
    uri = ["upload_presets"]
    params = utils.build_upload_params(**options)
    params = utils.cleanup_params(params)
    params.update(only(options, "unsigned", "disallow_public_id", "name", "live"))
    return call_api("post", uri, params, **options)


def create_folder(path, **options):
    return call_api("post", ["folders", path], {}, **options)


def root_folders(**options):
    return call_api("get", ["folders"], only(options, "next_cursor", "max_results"), **options)


def subfolders(of_folder_path, **options):
    return call_api("get", ["folders", of_folder_path], only(options, "next_cursor", "max_results"), **options)


def delete_folder(path, **options):
    """Deletes folder

    Deleted folder must be empty, but can have descendant empty sub folders

    :param path: The folder to delete
    :param options: Additional options

    :rtype: Response
    """
    return call_api("delete", ["folders", path], {}, **options)


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
    return _call_api(method, uri, body=data,
                     headers={'Content-Type': 'application/json'}, **options)


def call_api(method, uri, params, **options):
    return _call_api(method, uri, params=params, **options)


def call_metadata_api(method, uri, params, **options):
    """Private function that assists with performing an API call to the
    metadata_fields part of the Admin API

    :param method: The HTTP method. Valid methods: get, post, put, delete
    :param uri: REST endpoint of the API (without 'metadata_fields')
    :param params: Query/body parameters passed to the method
    :param options: Additional options

    :rtype: Response
    """
    uri = ["metadata_fields"] + (uri or [])
    return call_json_api(method, uri, params, **options)


def _call_api(method, uri, params=None, body=None, headers=None, **options):
    prefix = options.pop("upload_prefix",
                         cloudinary.config().upload_prefix) or "https://api.cloudinary.com"
    cloud_name = options.pop("cloud_name", cloudinary.config().cloud_name)
    if not cloud_name:
        raise Exception("Must supply cloud_name")
    api_key = options.pop("api_key", cloudinary.config().api_key)
    if not api_key:
        raise Exception("Must supply api_key")
    api_secret = options.pop("api_secret", cloudinary.config().api_secret)
    if not cloud_name:
        raise Exception("Must supply api_secret")
    api_url = "/".join([prefix, "v1_1", cloud_name] + uri)

    processed_params = None
    if isinstance(params, dict):
        processed_params = {}
        for key, value in params.items():
            if isinstance(value, list) or isinstance(value, tuple):
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
        representations = [{"transformation": transformation_string(trans)}
                           for trans in options["representations"]]
        params["representations"] = json.dumps(representations)
    return params


def __delete_resource_params(options, **params):
    p = dict(transformations=utils.build_eager(options.get('transformations')),
             **only(options, "keep_original", "next_cursor", "invalidate"))
    p.update(params)
    return p


def list_metadata_fields(**options):
    """Returns a list of all metadata field definitions

    See: `Get metadata fields API reference <https://cloudinary.com/documentation/admin_api#get_metadata_fields>`_

    :param options: Additional options

    :rtype: Response
    """
    return call_metadata_api("get", [], {}, **options)


def metadata_field_by_field_id(field_external_id, **options):
    """Gets a metadata field by external id

    See: `Get metadata field by external ID API reference
    <https://cloudinary.com/documentation/admin_api#get_a_metadata_field_by_external_id>`_

    :param field_external_id: The ID of the metadata field to retrieve
    :param options: Additional options

    :rtype: Response
    """
    uri = [field_external_id]
    return call_metadata_api("get", uri, {}, **options)


def add_metadata_field(field, **options):
    """Creates a new metadata field definition

    See: `Create metadata field API reference <https://cloudinary.com/documentation/admin_api#create_a_metadata_field>`_

    :param field: The field to add
    :param options: Additional options

    :rtype: Response
    """
    params = only(field, "type", "external_id", "label", "mandatory",
                  "default_value", "validation", "datasource")
    return call_metadata_api("post", [], params, **options)


def update_metadata_field(field_external_id, field, **options):
    """Updates a metadata field by external id

    Updates a metadata field definition (partially, no need to pass the entire
    object) passed as JSON data.

    See `Generic structure of a metadata field
    <https://cloudinary.com/documentation/admin_api#generic_structure_of_a_metadata_field>`_ for details.

    :param field_external_id: The id of the metadata field to update
    :param field: The field definition
    :param options: Additional options

    :rtype: Response
    """
    uri = [field_external_id]
    params = only(field, "label", "mandatory", "default_value", "validation")
    return call_metadata_api("put", uri, params, **options)


def delete_metadata_field(field_external_id, **options):
    """Deletes a metadata field definition.
    The field should no longer be considered a valid candidate for all other endpoints

    See: `Delete metadata field API reference
    <https://cloudinary.com/documentation/admin_api#delete_a_metadata_field_by_external_id>`_

    :param field_external_id: The external id of the field to delete
    :param options: Additional options

    :return: An array with a "message" key. "ok" value indicates a successful deletion.
    :rtype: Response
    """
    uri = [field_external_id]
    return call_metadata_api("delete", uri, {}, **options)


def delete_datasource_entries(field_external_id, entries_external_id, **options):
    """Deletes entries in a metadata field datasource

    Deletes (blocks) the datasource entries for a specified metadata field
    definition. Sets the state of the entries to inactive. This is a soft delete,
    the entries still exist under the hood and can be activated again with the
    restore datasource entries method.

    See: `Delete entries in a metadata field datasource API reference
    <https://cloudinary.com/documentation/admin_api#delete_entries_in_a_metadata_field_datasource>`_

    :param field_external_id: The id of the field to update
    :param  entries_external_id: The ids of all the entries to delete from the
                                 datasource
    :param options: Additional options

    :rtype: Response
    """
    uri = [field_external_id, "datasource"]
    params = {"external_ids": entries_external_id}
    return call_metadata_api("delete", uri, params, **options)


def update_metadata_field_datasource(field_external_id, entries_external_id, **options):
    """Updates a metadata field datasource

    Updates the datasource of a supported field type (currently only enum and set),
    passed as JSON data. The update is partial: datasource entries with an
    existing external_id will be updated and entries with new external_id's (or
    without external_id's) will be appended.

    See: `Update a metadata field datasource API reference
    <https://cloudinary.com/documentation/admin_api#update_a_metadata_field_datasource>`_

    :param field_external_id: The external id of the field to update
    :param entries_external_id:
    :param options: Additional options

    :rtype: Response
    """
    values = []
    for item in entries_external_id:
        external = only(item, "external_id", "value")
        if external:
            values.append(external)

    uri = [field_external_id, "datasource"]
    params = {"values": values}
    return call_metadata_api("put", uri, params, **options)


def restore_metadata_field_datasource(field_external_id, entries_external_ids, **options):
    """Restores entries in a metadata field datasource

    Restores (unblocks) any previously deleted datasource entries for a specified
    metadata field definition.
    Sets the state of the entries to active.

    See: `Restore entries in a metadata field datasource API reference
    <https://cloudinary.com/documentation/admin_api#restore_entries_in_a_metadata_field_datasource>`_

    :param field_external_id: The ID of the metadata field
    :param entries_external_ids: An array of IDs of datasource entries to restore
                                 (unblock)
    :param options: Additional options

    :rtype: Response
    """
    uri = [field_external_id, 'datasource_restore']
    params = {"external_ids": entries_external_ids}
    return call_metadata_api("post", uri, params, **options)
