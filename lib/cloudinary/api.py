# Copyright Cloudinary

import datetime
import email.utils
import json
import socket

import urllib3
from six import string_types
from urllib3.exceptions import HTTPError

import cloudinary
from cloudinary import utils
from cloudinary.api_client.call_api import (
    call_api,
    call_metadata_api,
    call_json_api
)
from cloudinary.exceptions import (
    BadRequest,
    AuthorizationRequired,
    NotAllowed,
    NotFound,
    AlreadyExists,
    RateLimited,
    GeneralError
)


def ping(**options):
    return call_api("get", ["ping"], {}, **options)


def usage(**options):
    """Get account usage details.

    Get a report on the status of your Cloudinary account usage details, including storage, credits, bandwidth,
    requests, number of resources, and add-on usage. Note that numbers are updated periodically.

    See: `Get account usage details
    <https://cloudinary.com/documentation/admin_api#get_account_usage_details>`_

    :param options:     Additional options
    :type options:      dict, optional
    :return:            Detailed usage information
    :rtype:             Response
    """
    date = options.pop("date", None)
    uri = ["usage"]
    if date:
        if isinstance(date, datetime.date):
            date = utils.encode_date_to_usage_api_format(date)
        uri.append(date)
    return call_api("get", uri, {}, **options)


def resource_types(**options):
    return call_api("get", ["resources"], {}, **options)


def resources(**options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", None)
    uri = ["resources", resource_type]
    if upload_type:
        uri.append(upload_type)
    params = only(options, "next_cursor", "max_results", "prefix", "tags",
                  "context", "moderations", "direction", "start_at", "metadata")
    return call_api("get", uri, params, **options)


def resources_by_tag(tag, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "tags", tag]
    params = only(options, "next_cursor", "max_results", "tags",
                  "context", "moderations", "direction", "metadata")
    return call_api("get", uri, params, **options)


def resources_by_moderation(kind, status, **options):
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "moderations", kind, status]
    params = only(options, "next_cursor", "max_results", "tags",
                  "context", "moderations", "direction", "metadata")
    return call_api("get", uri, params, **options)


def resources_by_ids(public_ids, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = dict(only(options, "tags", "moderations", "context"), public_ids=public_ids)
    return call_api("get", uri, params, **options)


def resources_by_asset_folder(asset_folder, **options):
    """
    Returns the details of the resources (assets) under a specified asset_folder.

    :param asset_folder:    The Asset Folder of the asset
    :type asset_folder:     string
    :param options:     Additional options
    :type options:      dict, optional
    :return:            Resources (assets) of a specific asset_folder
    :rtype:             Response
    """
    uri = ["resources", "by_asset_folder"]
    params = only(options, "max_results", "tags", "moderations", "context", "next_cursor")
    params["asset_folder"] = asset_folder
    return call_api("get", uri, params, **options)


def resources_by_asset_ids(asset_ids, **options):
    """Retrieves the resources (assets) indicated in the asset IDs.
    This method does not return deleted assets even if they have been backed up.

    See: `Get resources by context API reference
    <https://cloudinary.com/documentation/admin_api#get_resources>`_

    :param asset_ids:   The requested asset IDs.
    :type asset_ids:    list[str]
    :param options:     Additional options
    :type options:      dict, optional
    :return:            Resources (assets) as indicated in the asset IDs
    :rtype:             Response
    """
    uri = ["resources", 'by_asset_ids']
    params = dict(only(options, "tags", "moderations", "context"), asset_ids=asset_ids)
    return call_api("get", uri, params, **options)


def resources_by_context(key, value=None, **options):
    """Retrieves resources (assets) with a specified context key.
    This method does not return deleted assets even if they have been backed up.

    See: `Get resources by context API reference
    <https://cloudinary.com/documentation/admin_api#get_resources_by_context>`_

    :param key:         Only assets with this context key are returned
    :type key:          str
    :param value:       Only assets with this value for the context key are returned
    :type value:        str, optional
    :param options:     Additional options
    :type options:      dict, optional
    :return:            Resources (assets) with a specified context key
    :rtype:             Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "context"]
    params = only(options, "next_cursor", "max_results", "tags",
                  "context", "moderations", "direction", "metadata")
    params["key"] = key
    if value is not None:
        params["value"] = value
    return call_api("get", uri, params, **options)


def resource(public_id, **options):
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type, public_id]
    params = _prepare_asset_details_params(**options)
    return call_api("get", uri, params, **options)


def resource_by_asset_id(asset_id, **options):
    """
    Returns the details of the specified asset and all its derived assets by asset id.

    :param asset_id:    The Asset ID of the asset
    :type asset_id:     string
    :param options:     Additional options
    :type options:      dict, optional
    :return:            Resource (asset) of a specific asset_id
    :rtype:             Response
    """
    uri = ["resources", asset_id]
    params = _prepare_asset_details_params(**options)
    return call_api("get", uri, params, **options)


def _prepare_asset_details_params(**options):
    """
    Prepares optional parameters for resource_by_asset_id API calls.

    :param options: Additional options
    :return: Optional parameters

    :internal
    """
    return only(options, "exif", "faces", "colors", "image_metadata", "cinemagraph_analysis",
                "pages", "phash", "coordinates", "max_results", "quality_analysis", "derived_next_cursor",
                "accessibility_analysis", "versions")


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
    if "metadata" in options:
        params["metadata"] = utils.encode_context(options.get("metadata"))
    if "auto_tagging" in options:
        params["auto_tagging"] = str(options.get("auto_tagging"))
    if "access_control" in options:
        params["access_control"] = utils.json_encode(utils.build_list_of_dicts(options.get("access_control")))
    if "asset_folder" in options:
        params["asset_folder"] = options.get("asset_folder")
    if "display_name" in options:
        params["display_name"] = options.get("display_name")
    if "unique_display_name" in options:
        params["unique_display_name"] = options.get("unique_display_name")

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
    params = dict(public_ids=public_ids, **only(options, "versions"))
    return call_json_api("post", uri, params, **options)


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


def reorder_metadata_field_datasource(field_external_id, order_by, direction=None, **options):
    """Reorders metadata field datasource. Currently, supports only value.

    :param field_external_id: The ID of the metadata field.
    :param order_by: Criteria for the order. Currently, supports only value.
    :param direction: Optional (gets either asc or desc).
    :param options: Additional options.

    :rtype: Response
    """
    uri = [field_external_id, 'datasource', 'order']
    params = {'order_by': order_by, 'direction': direction}
    return call_metadata_api('post', uri, params, **options)


def reorder_metadata_fields(order_by, direction=None, **options):
    """Reorders metadata fields.

    :param order_by: Criteria for the order (one of the fields 'label', 'external_id', 'created_at').
    :param direction: Optional (gets either asc or desc).
    :param options: Additional options.

    :rtype: Response
    """
    uri = ['order']
    params = {'order_by': order_by, 'direction': direction}
    return call_metadata_api('put', uri, params, **options)
