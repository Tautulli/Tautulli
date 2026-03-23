# Copyright Cloudinary

import datetime
import json

from six import string_types

import cloudinary
from cloudinary import utils
from cloudinary.api_client.call_api import (
    call_metadata_api,
    call_metadata_rules_api,
    call_api,
    call_json_api,
    _call_v2_api,

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
    """
    Tests the reachability of the Cloudinary API.

    See: https://cloudinary.com/documentation/admin_api#ping_cloudinary_servers

    :param options: Additional optional configuration parameters (none currently recognized).

    :return: The result of the API call.
    :rtype: Response
    """
    return call_json_api("get", ["ping"], {}, **options)


def usage(**options):
    """
    Get account usage details.

    Get a report on the status of your Cloudinary account usage details, including storage, credits, bandwidth,
    requests, number of resources, and add-on usage. Note that numbers are updated periodically.

    See: https://cloudinary.com/documentation/admin_api#get_product_environment_usage_details

    :param options: Additional optional parameters.
    :keyword date: The date for usage details (string in "YYYY-MM" format or a datetime.date object).
                   If omitted, returns usage for the current billing period.
    :type date: str or datetime.date

    :return: Detailed usage information
    :rtype: Response
    """
    date = options.pop("date", None)
    uri = ["usage"]
    if date:
        if isinstance(date, datetime.date):
            date = utils.encode_date_to_usage_api_format(date)
        uri.append(date)
    return call_json_api("get", uri, {}, **options)


def config(**options):
    """
    Get account config details.

    Fetches the account's configuration details with optional settings.

    See: https://cloudinary.com/documentation/admin_api#get_product_environment_config_details

    :param options: The optional parameters for the API request.
    :keyword bool settings: When True, returns extended settings in the response (if available).
    :return: Detailed config information.
    :rtype: Response
    """
    params = only(options, "settings")
    return call_json_api("get", ["config"], params, **options)


def resource_types(**options):
    """
    Retrieves the types of resources (assets) available.

    See: https://cloudinary.com/documentation/admin_api#get_resources

    :param options: Additional optional configuration parameters (none currently recognized).
    :return: The result of the API call.
    :rtype: Response
    """
    return call_json_api("get", ["resources"], {}, **options)


def resources(**options):
    """
    Retrieves resources (assets) based on the provided options.

    See: https://cloudinary.com/documentation/admin_api#get_resources

    :param options: Additional options to filter the resources.
    :keyword str resource_type: The type of the resources. Defaults to "image".
    :keyword str type: The specific asset type. Defaults to None (not added to URI).
    :keyword str prefix: Return only resources with a public ID (or folder) that starts with this prefix.
    :keyword str start_at: Return resources updated since the specified timestamp (format: "yyyy-mm-dd hh:mm:ss").
    :keyword str direction: Return resources sorted by "asc" or "desc" order of creation.
    :keyword str next_cursor: A string that is returned as part of the response when there are more results to retrieve.
    :keyword int max_results: Maximum number of resources to return. Default=10.
    :return: The result of the API call.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", None)
    uri = ["resources", resource_type]
    if upload_type:
        uri.append(upload_type)
    params = __list_resources_params(**options)
    params.update(only(options, "prefix", "start_at"))
    return call_json_api("get", uri, params, **options)


def resources_by_tag(tag, **options):
    """
    Lists resources (assets) with the specified tag.

    This method does not return matching deleted assets, even if they have been backed up.

    See: https://cloudinary.com/documentation/admin_api#get_resources_by_tag

    :param tag: The tag value.
    :type tag: str
    :param options: Additional options to filter the resources.
    :keyword str resource_type: The type of the resources. Defaults to "image".
    :keyword str direction: Return resources in "asc" or "desc" order (by creation).
    :keyword int max_results: Maximum number of resources to return. Default=10.
    :keyword str next_cursor: A string returned when there are more results to fetch.
    :return: The result of the API call.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "tags", tag]
    params = __list_resources_params(**options)
    return call_json_api("get", uri, params, **options)


def resources_by_moderation(kind, status, **options):
    """
    Lists resources (assets) currently in the specified moderation queue and status.

    See: https://cloudinary.com/documentation/admin_api#get_resources_in_moderation

    :param kind: Type of image moderation queue to list (e.g., "manual", "webpurify", "aws_rek", "metascan").
    :type kind: str
    :param status: Only assets with this moderation status will be returned.
                   Valid values: "pending", "approved", "rejected".
    :type status: str
    :param options: Additional options to filter the resources.
    :keyword str resource_type: The type of the resources. Defaults to "image".
    :keyword str direction: Return resources in "asc" or "desc" order (by creation).
    :keyword int max_results: Maximum number of resources to return. Default=10.
    :keyword str next_cursor: A string returned when there are more results to fetch.
    :return: The result of the API call.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "moderations", kind, status]
    params = __list_resources_params(**options)
    return call_json_api("get", uri, params, **options)


def resources_by_ids(public_ids, **options):
    """
    Lists resources (assets) with the specified public IDs.

    See: https://cloudinary.com/documentation/admin_api#get_resources

    :param public_ids: The requested public_ids (up to 100).
    :type public_ids: list[str]
    :param options: The optional parameters.
    :keyword str resource_type: The type of the resources. Defaults to "image".
    :keyword str type: The specific asset type. Defaults to "upload".
    :keyword str direction: Return resources in "asc" or "desc" order.
    :keyword int max_results: Maximum number of resources to return.
    :keyword str next_cursor: A string returned when there are more results to fetch.
    :return: The result of the API call.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = dict(__resources_params(**options), public_ids=public_ids)
    return call_json_api("get", uri, params, **options)


def resources_by_asset_folder(asset_folder, **options):
    """
    Returns the details of the resources (assets) under a specified asset_folder.

    See: https://cloudinary.com/documentation/admin_api#get_resources_by_asset_folder

    :param asset_folder: The Asset Folder of the asset.
    :type asset_folder: str
    :param options: Additional options to filter the resources.
    :keyword str direction: Return resources in "asc" or "desc" order.
    :keyword int max_results: Maximum number of resources to return.
    :keyword str next_cursor: A string returned when there are more results to fetch.
    :return: Resources (assets) of a specific asset_folder.
    :rtype: Response
    """
    uri = ["resources", "by_asset_folder"]
    params = __list_resources_params(**options)
    params["asset_folder"] = asset_folder
    return call_json_api("get", uri, params, **options)


def resources_by_asset_ids(asset_ids, **options):
    """
    Retrieves the resources (assets) indicated in the asset IDs.
    This method does not return deleted assets even if they have been backed up.

    See: https://cloudinary.com/documentation/admin_api#get_resources_by_asset_ids

    :param asset_ids: The requested asset IDs.
    :type asset_ids: list[str]
    :param options: Additional options to filter the resources.
    :keyword str direction: Return resources in "asc" or "desc" order.
    :keyword int max_results: Maximum number of resources to return.
    :keyword str next_cursor: A string returned when there are more results to fetch.
    :return: Resources (assets) as indicated in the asset IDs.
    :rtype: Response
    """
    uri = ["resources", "by_asset_ids"]
    params = dict(__resources_params(**options), asset_ids=asset_ids)
    return call_json_api("get", uri, params, **options)


def resources_by_context(key, value=None, **options):
    """
    Retrieves resources (assets) with a specified context key.
    This method does not return deleted assets even if they have been backed up.

    See: https://cloudinary.com/documentation/admin_api#get_resources_by_context

    :param key: Only assets with this context key are returned.
    :type key: str
    :param value: Only assets with this value for the context key are returned.
    :type value: str, optional
    :param options: Additional options to filter the resources.
    :keyword str resource_type: The type of the resources. Defaults to "image".
    :keyword str direction: Return resources in "asc" or "desc" order.
    :keyword int max_results: Maximum number of resources to return.
    :keyword str next_cursor: A string returned when there are more results to fetch.
    :return: Resources (assets) with a specified context key.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "context"]
    params = __list_resources_params(**options)
    params["key"] = key
    if value is not None:
        params["value"] = value
    return call_json_api("get", uri, params, **options)


def __resources_params(**options):
    """
    Prepares optional parameters for resources_* API calls.

    :param options: Additional options
    :return: Optional parameters
    :rtype: dict
    :internal
    """
    params = only(options, "tags", "context", "metadata", "moderations")
    if options.get("fields"):
        params["fields"] = utils.encode_list(utils.build_array(options["fields"]))

    return params


def __list_resources_params(**options):
    """
    Prepares optional parameters for resources_* API calls.

    :param options: Additional options
    :return: Optional parameters
    :rtype: dict
    :internal
    """
    resources_params = __resources_params(**options)
    resources_params.update(only(options, "next_cursor", "max_results", "direction"))
    return resources_params


def visual_search(image_url=None, image_asset_id=None, text=None, image_file=None, **options):
    """
    Find images based on their visual content.

    See: https://cloudinary.com/documentation/admin_api#visual_search_for_resources

    :param image_url: The URL of an image.
    :type image_url: str, optional
    :param image_asset_id: The asset_id of an image in your account.
    :type image_asset_id: str, optional
    :param text: A textual description (e.g. "cat").
    :type text: str, optional
    :param image_file: The image file. (str|callable|Path|bytes)
    :type image_file: str or callable or Path or bytes, optional
    :param options: Additional optional parameters to pass along.

    :return: Resources (assets) that were found
    :rtype: Response
    """
    uri = ["resources", "visual_search"]
    params = {
        "image_url": image_url,
        "image_asset_id": image_asset_id,
        "text": text,
        "image_file": utils.handle_file_parameter(image_file, "file")
    }
    return call_api("post", uri, params, **options)


def resource(public_id, **options):
    """
    Returns the details of the specified asset and all its derived assets (by public ID).

    See: https://cloudinary.com/documentation/admin_api#get_details_of_a_single_resource_by_public_id

    :param public_id: The public ID of the resource.
    :type public_id: str
    :param options: Additional optional parameters for retrieval.
    :keyword str resource_type: The resource type (e.g. "image", "raw").
    :keyword str type: The asset's storage type (e.g. "upload").
    :keyword bool exif: Whether to return Exif metadata.
    :keyword bool faces: Whether to return face coordinates.
    :keyword bool colors: Whether to return color information.
    :keyword bool image_metadata: Whether to return image metadata.
    :keyword bool media_metadata: Whether to return extended media metadata.
    :keyword bool cinemagraph_analysis: Whether to include cinemagraph analysis data.
    :keyword bool pages: Whether to include the page count of multi-page files.
    :keyword bool phash: Whether to include perceptual hash data.
    :keyword bool coordinates: Whether to return custom and face coordinates.
    :keyword int max_results: The maximum number of derived resources to return.
    :keyword bool quality_analysis: Whether to include quality analysis data.
    :keyword str derived_next_cursor: A pagination cursor for derived resources.
    :keyword bool accessibility_analysis: Whether to include accessibility analysis data.
    :keyword bool versions: Whether to include version information for the asset.
    :keyword bool related: Whether to include related assets.
    :keyword str related_next_cursor: A pagination cursor for related assets.
    :return: The result of the API call.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type, public_id]
    params = _prepare_asset_details_params(**options)
    return call_json_api("get", uri, params, **options)


def resource_by_asset_id(asset_id, **options):
    """
    Returns the details of the specified asset and all its derived assets (by asset ID).

    See: https://cloudinary.com/documentation/admin_api#get_details_of_a_single_resource_by_asset_id

    :param asset_id: The Asset ID of the asset
    :type asset_id: str
    :param options: Additional optional parameters for retrieval.
    :keyword bool exif: Whether to return Exif metadata.
    :keyword bool faces: Whether to return face coordinates.
    :keyword bool colors: Whether to return color information.
    :keyword bool image_metadata: Whether to return image metadata.
    :keyword bool media_metadata: Whether to return extended media metadata.
    :keyword bool cinemagraph_analysis: Whether to include cinemagraph analysis data.
    :keyword bool pages: Whether to include the page count of multi-page files.
    :keyword bool phash: Whether to include perceptual hash data.
    :keyword bool coordinates: Whether to return custom and face coordinates.
    :keyword int max_results: The maximum number of derived resources to return.
    :keyword bool quality_analysis: Whether to include quality analysis data.
    :keyword str derived_next_cursor: A pagination cursor for derived resources.
    :keyword bool accessibility_analysis: Whether to include accessibility analysis data.
    :keyword bool versions: Whether to include version information for the asset.
    :keyword bool related: Whether to include related assets.
    :keyword str related_next_cursor: A pagination cursor for related assets.
    :return: Resource (asset) of a specific asset_id
    :rtype: Response
    """
    uri = ["resources", asset_id]
    params = _prepare_asset_details_params(**options)
    return call_json_api("get", uri, params, **options)


def _prepare_asset_details_params(**options):
    """
    Prepares optional parameters for resource_by_asset_id or resource_by_public_id API calls.

    :param options: Additional options
    :return: Optional parameters
    :rtype: dict
    :internal
    """
    return only(options, "exif", "faces", "colors", "image_metadata", "media_metadata", "cinemagraph_analysis",
                "pages", "phash", "coordinates", "max_results", "quality_analysis", "derived_next_cursor",
                "accessibility_analysis", "versions", "related", "related_next_cursor")


def update(public_id, **options):
    """
    Updates the details of a specified resource by public ID.

    See: https://cloudinary.com/documentation/admin_api#update_details_of_an_existing_resource

    :param public_id: The public ID of the resource to update.
    :type public_id: str
    :param options: Additional options for the update operation.
    :keyword str resource_type: The resource type (e.g. "image", "raw").
    :keyword str type: The asset's storage type (e.g. "upload").
    :keyword str moderation_status: Sets the moderation status ("approved" / "rejected").
    :keyword str raw_convert: Requests raw file conversion ("aspose", etc.).
    :keyword str quality_override: Overrides the quality setting.
    :keyword str ocr: Requests OCR extraction ("adv_ocr").
    :keyword str categorization: Sets the categorization mode (e.g. "google_tagging").
    :keyword str detection: Sets the detection mode (e.g. "adv_face").
    :keyword str similarity_search: Reserved for similarity search tasks.
    :keyword str background_removal: The background removal setting (e.g. "cloudinary_ai" or "pixelz").
    :keyword str notification_url: A URL for receiving notifications.
    :keyword list tags: The tags to assign to the asset.
    :keyword list or str face_coordinates: The face coordinates to set.
    :keyword list or str custom_coordinates: The custom coordinates to set.
    :keyword list regions: Region data for partial image transformations.
    :keyword dict context: Contextual (key/value) metadata.
    :keyword dict metadata: Structured metadata.
    :keyword float auto_tagging: A float from 0.0 to 1.0. If set, automatically tags an image.
    :keyword list access_control: An array of access control rules in dictionary form.
    :keyword str asset_folder: The folder path in which to place the asset.
    :keyword str display_name: A user-friendly name for the asset.
    :keyword bool unique_display_name: If True, ensures the display name is unique.
    :keyword bool clear_invalid: If True, removes or corrects invalid data (e.g., invalid context).
    :return: The result of the API call.
    :rtype: Response
    """
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
    if "regions" in options:
        params["regions"] = utils.json_encode(options.get("regions"))
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
    if "clear_invalid" in options:
        params["clear_invalid"] = options.get("clear_invalid")

    return call_json_api("post", uri, params, **options)


def delete_resources(public_ids, **options):
    """
    Deletes resources (assets) given their public IDs.

    The resources must belong to the specified resource_type and type.

    See: https://cloudinary.com/documentation/admin_api#delete_resources

    :param public_ids: The public IDs of the resources to delete.
    :type public_ids: list[str]
    :param options: Additional options.
    :keyword str resource_type: Defaults to "image".
    :keyword str type: Defaults to "upload".
    :keyword list transformations: The derived transformations to delete (if any).
    :keyword bool keep_original: When True, keeps the original resource.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword bool invalidate: When True, invalidates the assets on the CDN.
    :return: The result of the command.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = __delete_resource_params(options, public_ids=public_ids)
    return call_json_api("delete", uri, params, **options)


def delete_resources_by_asset_ids(asset_ids, **options):
    """
    Deletes resources (assets) by asset IDs.

    See: https://cloudinary.com/documentation/admin_api#delete_resources_by_asset_id

    :param asset_ids: The asset IDs of the assets to delete.
    :type asset_ids: list[str]
    :param options: Additional options.
    :keyword list transformations: The derived transformations to delete (if any).
    :keyword bool keep_original: When True, keeps the original resource.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword bool invalidate: When True, invalidates the assets on the CDN.
    :return: The result of the command.
    :rtype: dict
    """
    uri = ["resources"]
    params = __delete_resource_params(options, asset_ids=asset_ids)
    return call_json_api("delete", uri, params, **options)


def delete_resources_by_prefix(prefix, **options):
    """
    Deletes resources (assets) that have a specified prefix for their Public IDs.

    See: https://cloudinary.com/documentation/admin_api#delete_resources

    :param prefix: The prefix of the Public IDs to delete.
    :type prefix: str
    :param options: Additional options.
    :keyword str resource_type: Defaults to "image".
    :keyword str type: Defaults to "upload".
    :keyword list transformations: The derived transformations to delete (if any).
    :keyword bool keep_original: When True, keeps the original resource.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword bool invalidate: When True, invalidates the assets on the CDN.
    :return: The result of the command.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = __delete_resource_params(options, prefix=prefix)
    return call_json_api("delete", uri, params, **options)


def delete_all_resources(**options):
    """
    Deletes **all** resources (assets) of a specified resource_type and type.

    Use with caution: This removes all matching resources from your account.

    See: https://cloudinary.com/documentation/admin_api#delete_resources

    :param options: Additional options.
    :keyword str resource_type: Defaults to "image".
    :keyword str type: Defaults to "upload".
    :keyword list transformations: The derived transformations to delete (if any).
    :keyword bool keep_original: When True, keeps the original resource.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword bool invalidate: When True, invalidates the assets on the CDN.
    :keyword bool all: (Added internally) If True, indicates all resources are to be deleted.
    :return: The result of the command.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type]
    params = __delete_resource_params(options, all=True)
    return call_json_api("delete", uri, params, **options)


def delete_resources_by_tag(tag, **options):
    """
    Deletes resources (assets) that contain a specified tag.

    See: https://cloudinary.com/documentation/admin_api#delete_resources_by_tags

    :param tag: The tag whose associated resources should be deleted.
    :type tag: str
    :param options: Additional options.
    :keyword str resource_type: Defaults to "image".
    :keyword list transformations: The derived transformations to delete (if any).
    :keyword bool keep_original: When True, keeps the original resource.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword bool invalidate: When True, invalidates the assets on the CDN.
    :return: The result of the command.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "tags", tag]
    params = __delete_resource_params(options)
    return call_json_api("delete", uri, params, **options)


def delete_derived_resources(derived_resource_ids, **options):
    """
    Deletes derived resources by their derived resource IDs.

    See: https://cloudinary.com/documentation/admin_api#delete_derived_resources

    :param derived_resource_ids: A list of derived resource IDs.
    :type derived_resource_ids: list[str]
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command.
    :rtype: Response
    """
    uri = ["derived_resources"]
    params = {"derived_resource_ids": derived_resource_ids}
    return call_json_api("delete", uri, params, **options)


def delete_derived_by_transformation(public_ids, transformations,
                                     resource_type='image', type='upload', invalidate=None,
                                     **options):
    """
    Deletes derived resources of public IDs, identified by transformations.

    See: https://cloudinary.com/documentation/admin_api#delete_derived_resources

    :param public_ids: The base resources (list of public IDs).
    :type public_ids: list[str]
    :param transformations: The transformations of derived resources, optionally including the format.
    :type transformations: list[dict or str]
    :param resource_type: The type of the resource. Defaults to "image".
    :type resource_type: str
    :param type: The upload type. Defaults to "upload".
    :type type: str
    :param invalidate: (optional) True to invalidate the resources after deletion.
    :type invalidate: bool, optional
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command, including the public IDs for which derived resources were deleted.
    :rtype: dict
    """
    uri = ["resources", resource_type, type]
    if not isinstance(public_ids, list):
        public_ids = [public_ids]
    params = {
        "public_ids": public_ids,
        "transformations": utils.build_eager(transformations),
        "keep_original": True
    }
    if invalidate is not None:
        params['invalidate'] = invalidate
    return call_json_api("delete", uri, params, **options)


def delete_backed_up_assets(asset_id, version_ids, **options):
    """
    Deletes backed up versions of a resource by asset IDs.

    See: https://cloudinary.com/documentation/admin_api#delete_backed_up_versions_of_a_resource

    :param asset_id: The asset ID of the asset to update.
    :type asset_id: str
    :param version_ids: The array of version IDs.
    :type version_ids: list[str]
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command.
    :rtype: dict
    """
    uri = ["resources", "backup", asset_id]
    params = {"version_ids": utils.build_array(version_ids)}
    return call_json_api("delete", uri, params, **options)


def add_related_assets(public_id, assets_to_relate, resource_type="image", type="upload", **options):
    """
    Relates an asset to other assets by public IDs.

    See: https://cloudinary.com/documentation/admin_api#add_related_assets

    :param public_id: The public ID of the asset to update.
    :type public_id: str
    :param assets_to_relate: Array of up to 10 fully_qualified_public_ids as resource_type/type/public_id.
    :type assets_to_relate: list[str]
    :param resource_type: The type of the resource. Defaults to "image".
    :type resource_type: str
    :param type: The upload type. Defaults to "upload".
    :type type: str
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command.
    :rtype: dict
    """
    uri = ["resources", "related_assets", resource_type, type, public_id]
    params = {"assets_to_relate": utils.build_array(assets_to_relate)}
    return call_json_api("post", uri, params, **options)


def add_related_assets_by_asset_ids(asset_id, assets_to_relate, **options):
    """
    Relates an asset to other assets by asset IDs.

    See: https://cloudinary.com/documentation/admin_api#add_related_assets_by_asset_id

    :param asset_id: The asset ID of the asset to update.
    :type asset_id: str
    :param assets_to_relate: The array of up to 10 asset IDs.
    :type assets_to_relate: list[str]
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command.
    :rtype: dict
    """
    uri = ["resources", "related_assets", asset_id]
    params = {"assets_to_relate": utils.build_array(assets_to_relate)}
    return call_json_api("post", uri, params, **options)


def delete_related_assets(public_id, assets_to_unrelate, resource_type="image", type="upload", **options):
    """
    Unrelates an asset from other assets by public IDs.

    See: https://cloudinary.com/documentation/admin_api#delete_related_assets

    :param public_id: The public ID of the asset to update.
    :type public_id: str
    :param assets_to_unrelate: Array of up to 10 fully_qualified_public_ids as resource_type/type/public_id.
    :type assets_to_unrelate: list[str]
    :param resource_type: The type of the resource. Defaults to "image".
    :type resource_type: str
    :param type: The upload type. Defaults to "upload".
    :type type: str
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command.
    :rtype: dict
    """
    uri = ["resources", "related_assets", resource_type, type, public_id]
    params = {"assets_to_unrelate": utils.build_array(assets_to_unrelate)}
    return call_json_api("delete", uri, params, **options)


def delete_related_assets_by_asset_ids(asset_id, assets_to_unrelate, **options):
    """
    Unrelates an asset from other assets by asset IDs.

    See: https://cloudinary.com/documentation/admin_api#delete_related_assets_by_asset_id

    :param asset_id: The asset ID of the asset to update.
    :type asset_id: str
    :param assets_to_unrelate: The array of up to 10 asset IDs.
    :type assets_to_unrelate: list[str]
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the command.
    :rtype: dict
    """
    uri = ["resources", "related_assets", asset_id]
    params = {"assets_to_unrelate": utils.build_array(assets_to_unrelate)}
    return call_json_api("delete", uri, params, **options)


def tags(**options):
    """
    Lists all the tags currently used for a specified asset type.

    See: https://cloudinary.com/documentation/admin_api#get_tags

    :param options: The optional parameters.
    :keyword str resource_type: Defaults to "image".
    :keyword str prefix: Return only tags that begin with the specified prefix.
    :keyword int max_results: Maximum number of tags to return.
    :keyword str next_cursor: A string returned when more results are available.
    :return: The result of the API call.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["tags", resource_type]
    return call_json_api("get", uri, only(options, "next_cursor", "max_results", "prefix"), **options)


def transformations(**options):
    """
    Lists all transformations.

    See: https://cloudinary.com/documentation/admin_api#get_transformations

    :param options: The optional parameters.
    :keyword bool named: When True, return only named transformations.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword int max_results: Maximum number of transformations to return.
    :return: The list of transformations.
    :rtype: Response
    """
    uri = ["transformations"]
    params = only(options, "named", "next_cursor", "max_results")
    return call_json_api("get", uri, params, **options)


def transformation(transformation, **options):
    """
    Returns the details of a single transformation.

    See: https://cloudinary.com/documentation/admin_api#get_transformation_details

    :param transformation: The transformation to retrieve (string or dict).
    :type transformation: str or dict
    :param options: The optional parameters.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword int max_results: Maximum number of derived assets to return.
    :return: The transformation details.
    :rtype: Response
    """
    uri = ["transformations"]
    params = only(options, "next_cursor", "max_results")
    params["transformation"] = utils.build_single_eager(transformation)
    return call_json_api("get", uri, params, **options)


def delete_transformation(transformation, **options):
    """
    Deletes a transformation.

    See: https://cloudinary.com/documentation/admin_api#delete_transformation

    :param transformation: The transformation to delete (string or dict).
    :type transformation: str or dict
    :param options: Additional options (none currently recognized).
    :return: The result of the API call.
    :rtype: Response
    """
    uri = ["transformations"]
    params = {"transformation": utils.build_single_eager(transformation)}
    return call_json_api("delete", uri, params, **options)


def update_transformation(transformation, **options):
    """
    Updates a transformation.

    Currently, the only supported update is setting the "allowed_for_strict" flag
    and the "unsafe_update" transformation.

    See: https://cloudinary.com/documentation/admin_api#update_transformation

    :param transformation: The transformation to update (string or dict).
    :type transformation: str or dict
    :param options: Additional update options.
    :keyword bool allowed_for_strict: Whether the transformation is allowed in strict mode.
    :keyword dict or str unsafe_update: The transformation to associate under unsafe_update.
    :return: The result of the API call.
    :rtype: Response
    """
    uri = ["transformations"]
    updates = only(options, "allowed_for_strict")
    if "unsafe_update" in options:
        updates["unsafe_update"] = transformation_string(options.get("unsafe_update"))
    updates["transformation"] = utils.build_single_eager(transformation)
    return call_json_api("put", uri, updates, **options)


def create_transformation(name, definition, **options):
    """
    Creates a named transformation based on an existing transformation.

    See: https://cloudinary.com/documentation/admin_api#create_a_named_transformation

    :param name: The name of the transformation to create.
    :type name: str
    :param definition: The transformation definition (string or dict).
    :type definition: str or dict
    :param options: Additional options (none currently recognized).
    :return: The result of the API call.
    :rtype: Response
    """
    uri = ["transformations"]
    params = {"name": name, "transformation": utils.build_single_eager(definition)}
    return call_json_api("post", uri, params, **options)


def publish_by_ids(public_ids, **options):
    """
    Publishes specific assets by their public IDs.

    :param public_ids: The list of public IDs to publish.
    :type public_ids: list[str]
    :param options: Additional options.
    :keyword str resource_type: The resource type (e.g. "image").
    :keyword str type: The asset type (e.g. "upload").
    :keyword bool overwrite: Whether to overwrite existing published assets.
    :keyword bool invalidate: Whether to invalidate the CDN.
    :return: The result of the publish operation.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "publish_resources"]
    params = dict(only(options, "type", "overwrite", "invalidate"), public_ids=public_ids)
    return call_json_api("post", uri, params, **options)


def publish_by_prefix(prefix, **options):
    """
    Publishes assets that have a specified prefix for their public IDs.

    :param prefix: The prefix of the public IDs to publish.
    :type prefix: str
    :param options: Additional options.
    :keyword str resource_type: The resource type (e.g. "image").
    :keyword str type: The asset type (e.g. "upload").
    :keyword bool overwrite: Whether to overwrite existing published assets.
    :keyword bool invalidate: Whether to invalidate the CDN.
    :return: The result of the publish operation.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "publish_resources"]
    params = dict(only(options, "type", "overwrite", "invalidate"), prefix=prefix)
    return call_json_api("post", uri, params, **options)


def publish_by_tag(tag, **options):
    """
    Publishes assets that contain a specified tag.

    :param tag: The tag whose associated resources should be published.
    :type tag: str
    :param options: Additional options.
    :keyword str resource_type: The resource type (e.g. "image").
    :keyword str type: The asset type (e.g. "upload").
    :keyword bool overwrite: Whether to overwrite existing published assets.
    :keyword bool invalidate: Whether to invalidate the CDN.
    :return: The result of the publish operation.
    :rtype: Response
    """
    resource_type = options.pop("resource_type", "image")
    uri = ["resources", resource_type, "publish_resources"]
    params = dict(only(options, "type", "overwrite", "invalidate"), tag=tag)
    return call_json_api("post", uri, params, **options)


def upload_presets(**options):
    """
    Lists all upload presets.

    See: https://cloudinary.com/documentation/admin_api#get_upload_presets

    :param options: Additional options.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword int max_results: Maximum number of presets to return.
    :return: A list of upload presets.
    :rtype: Response
    """
    uri = ["upload_presets"]
    return call_json_api("get", uri, only(options, "next_cursor", "max_results"), **options)


def upload_preset(name, **options):
    """
    Retrieves the details of a single upload preset.

    See: https://cloudinary.com/documentation/admin_api#get_the_details_of_a_single_upload_preset

    :param name: The name of the upload preset.
    :type name: str
    :param options: Additional options.
    :keyword int max_results: Maximum number of details to return (if relevant).
    :return: The upload preset details.
    :rtype: Response
    """
    uri = ["upload_presets", name]
    return call_json_api("get", uri, only(options, "max_results"), **options)


def delete_upload_preset(name, **options):
    """
    Deletes an upload preset by name.

    See: https://cloudinary.com/documentation/admin_api#delete_an_upload_preset

    :param name: The name of the upload preset to delete.
    :type name: str
    :param options: Additional options (none currently recognized).
    :return: The result of the deletion.
    :rtype: Response
    """
    uri = ["upload_presets", name]
    return call_json_api("delete", uri, {}, **options)


def update_upload_preset(name, **options):
    """
    Updates an existing upload preset.

    See: https://cloudinary.com/documentation/admin_api#update_an_upload_preset

    :param name: The name of the upload preset to update.
    :type name: str
    :param options: The parameters to update for the preset (e.g., folder, tags).
    :keyword bool unsigned: Whether this preset is unsigned (public).
    :keyword bool disallow_public_id: When True, the public ID cannot be overridden during upload.
    :keyword bool live: Whether this preset is for live (video) usage.
    :return: The updated upload preset.
    :rtype: Response
    """
    uri = ["upload_presets", name]
    params = utils.build_upload_params(**options)
    params = utils.cleanup_params(params)
    params.update(only(options, "unsigned", "disallow_public_id", "live"))
    return call_json_api("put", uri, params, **options)


def create_upload_preset(**options):
    """
    Creates a new upload preset.

    See: https://cloudinary.com/documentation/admin_api#create_an_upload_preset

    :param options: The parameters for the new preset (e.g., folder, tags).
    :keyword bool unsigned: Whether this preset is unsigned (public).
    :keyword bool disallow_public_id: When True, the public ID cannot be overridden during upload.
    :keyword str name: The name of the new upload preset.
    :keyword bool live: Whether this preset is for live (video) usage.
    :return: The created upload preset.
    :rtype: Response
    """
    uri = ["upload_presets"]
    params = utils.build_upload_params(**options)
    params = utils.cleanup_params(params)
    params.update(only(options, "unsigned", "disallow_public_id", "name", "live"))
    return call_json_api("post", uri, params, **options)


def root_folders(**options):
    """
    Lists the top-level folders in your Cloudinary account.

    See: https://cloudinary.com/documentation/admin_api#get_root_folders

    :param options: Additional options.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword int max_results: Maximum number of folders to return.
    :return: The list of top-level folders.
    :rtype: Response
    """
    return call_json_api("get", ["folders"], only(options, "next_cursor", "max_results"), **options)


def subfolders(of_folder_path, **options):
    """
    Lists the subfolders of a given folder path.

    See: https://cloudinary.com/documentation/admin_api#get_subfolders

    :param of_folder_path: The path of the parent folder.
    :type of_folder_path: str
    :param options: Additional options.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword int max_results: Maximum number of folders to return.
    :return: The list of subfolders.
    :rtype: Response
    """
    return call_json_api("get", ["folders", of_folder_path], only(options, "next_cursor", "max_results"), **options)


def create_folder(path, **options):
    """
    Creates a folder at the specified path.

    See: https://cloudinary.com/documentation/admin_api#create_folder

    :param path: The path for the new folder.
    :type path: str
    :param options: Additional options (none currently recognized).
    :return: The result of the folder creation.
    :rtype: Response
    """
    return call_json_api("post", ["folders", path], {}, **options)


def rename_folder(from_path, to_path, **options):
    """
    Renames a folder.

    See: https://cloudinary.com/documentation/admin_api#update_folder

    :param from_path: The full path of an existing asset folder.
    :type from_path: str
    :param to_path: The full path of the new asset folder.
    :type to_path: str
    :param options: Additional options (none currently recognized).
    :return: A response indicating the success or failure of the rename operation.
    :rtype: Response
    """
    params = {"to_folder": to_path}
    return call_json_api("put", ["folders", from_path], params, **options)


def delete_folder(path, **options):
    """
    Deletes a folder.

    The folder must be empty, but can have descendant empty subfolders.

    See: https://cloudinary.com/documentation/admin_api#delete_folder

    :param path: The folder to delete.
    :type path: str
    :param options: Additional options.
    :keyword bool skip_backup: Whether to skip backing up the folder before deletion.
    :return: A response indicating the success or failure of the delete operation.
    :rtype: Response
    """
    params = only(options, "skip_backup")
    return call_json_api("delete", ["folders", path], params, **options)


def restore(public_ids, **options):
    """
    Restores deleted resources (assets) by public IDs, if backups are available.

    See: https://cloudinary.com/documentation/admin_api#restore_resources

    :param public_ids: The list of public IDs to restore.
    :type public_ids: list[str]
    :param options: Additional options, e.g., "versions".
    :keyword list[str] versions: A list of specific version IDs to restore.
    :keyword str resource_type: Defaults to "image".
    :keyword str type: Defaults to "upload".
    :return: The result of the restore operation.
    :rtype: dict
    """
    resource_type = options.pop("resource_type", "image")
    upload_type = options.pop("type", "upload")
    uri = ["resources", resource_type, upload_type, "restore"]
    params = dict(public_ids=public_ids, **only(options, "versions"))
    return call_json_api("post", uri, params, **options)


def restore_by_asset_ids(asset_ids, **options):
    """
    Restores deleted resources (assets) by their asset IDs, if backups are available.

    See: https://cloudinary.com/documentation/admin_api#restore_resources_by_asset_id

    :param asset_ids: The asset IDs of the assets to restore.
    :type asset_ids: list[str]
    :param options: Additional options (e.g., versions).
    :keyword list[str] versions: A list of specific version IDs to restore.
    :return: The result of the restore operation.
    :rtype: dict
    """
    uri = ["resources", "restore"]
    params = dict(asset_ids=asset_ids, **only(options, "versions"))
    return call_json_api("post", uri, params, **options)


def upload_mappings(**options):
    """
    Lists all upload mappings in your account.

    See: https://cloudinary.com/documentation/admin_api#get_upload_mappings

    :param options: Additional options.
    :keyword str next_cursor: A string returned when more results are available.
    :keyword int max_results: Maximum number of mappings to return.
    :return: A list of upload mappings.
    :rtype: Response
    """
    uri = ["upload_mappings"]
    return call_json_api("get", uri, only(options, "next_cursor", "max_results"), **options)


def upload_mapping(name, **options):
    """
    Retrieves a single upload mapping by folder name.

    See: https://cloudinary.com/documentation/admin_api#get_the_details_of_a_single_upload_mapping

    :param name: The folder name.
    :type name: str
    :param options: Additional options (none currently recognized).
    :return: Details of the specified upload mapping.
    :rtype: Response
    """
    uri = ["upload_mappings"]
    params = dict(folder=name)
    return call_json_api("get", uri, params, **options)


def delete_upload_mapping(name, **options):
    """
    Deletes an upload mapping by folder name.

    See: https://cloudinary.com/documentation/admin_api#delete_an_upload_mapping

    :param name: The folder name.
    :type name: str
    :param options: Additional options (none currently recognized).
    :return: The result of the deletion.
    :rtype: Response
    """
    uri = ["upload_mappings"]
    params = dict(folder=name)
    return call_json_api("delete", uri, params, **options)


def update_upload_mapping(name, **options):
    """
    Updates an upload mapping by folder name.

    See: https://cloudinary.com/documentation/admin_api#update_an_upload_mapping

    :param name: The folder name.
    :type name: str
    :param options: Additional parameters to update.
    :keyword str template: A URL template for the given folder name.
    :return: The result of the update operation.
    :rtype: Response
    """
    uri = ["upload_mappings"]
    params = dict(folder=name)
    params.update(only(options, "template"))
    return call_json_api("put", uri, params, **options)


def create_upload_mapping(name, **options):
    """
    Creates a new upload mapping.

    See: https://cloudinary.com/documentation/admin_api#create_an_upload_mapping

    :param name: The folder name.
    :type name: str
    :param options: Additional parameters.
    :keyword str template: A URL template for the given folder name.
    :return: The result of the creation.
    :rtype: Response
    """
    uri = ["upload_mappings"]
    params = dict(folder=name)
    params.update(only(options, "template"))
    return call_json_api("post", uri, params, **options)


def list_streaming_profiles(**options):
    """
    Lists all custom and built-in streaming profiles.

    See: https://cloudinary.com/documentation/admin_api#get_adaptive_streaming_profiles

    :param options: Additional optional parameters (none currently recognized).
    :return: The list of streaming profiles.
    :rtype: Response
    """
    uri = ["streaming_profiles"]
    return call_json_api('GET', uri, {}, **options)


def get_streaming_profile(name, **options):
    """
    Retrieves details of a specific streaming profile by name.

    See: https://cloudinary.com/documentation/admin_api#get_details_of_a_single_streaming_profile

    :param name: The name of the streaming profile.
    :type name: str
    :param options: Additional optional parameters (none currently recognized).
    :return: The details of the streaming profile.
    :rtype: Response
    """
    uri = ["streaming_profiles", name]
    return call_json_api('GET', uri, {}, **options)


def delete_streaming_profile(name, **options):
    """
    Deletes a specific streaming profile by name (or reverts a built-in).

    See: https://cloudinary.com/documentation/admin_api#delete_or_revert_the_specified_streaming_profile

    :param name: The name of the streaming profile to delete.
    :type name: str
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the deletion.
    :rtype: Response
    """
    uri = ["streaming_profiles", name]
    return call_json_api('DELETE', uri, {}, **options)


def create_streaming_profile(name, **options):
    """
    Creates a new custom streaming profile.

    See: https://cloudinary.com/documentation/admin_api#create_a_streaming_profile

    :param name: The name for the new streaming profile.
    :type name: str
    :param options: Additional options.
    :keyword str display_name: A display name for the streaming profile.
    :keyword list representations: A list of transformations (dict or str).
    :return: The created streaming profile.
    :rtype: Response
    """
    uri = ["streaming_profiles"]
    params = __prepare_streaming_profile_params(**options)
    params["name"] = name
    return call_json_api('POST', uri, params, **options)


def update_streaming_profile(name, **options):
    """
    Updates an existing streaming profile.

    See: https://cloudinary.com/documentation/admin_api#update_an_existing_streaming_profile

    :param name: The name of the streaming profile to update.
    :type name: str
    :param options: Additional options.
    :keyword str display_name: A display name for the streaming profile.
    :keyword list representations: A list of transformations (dict or str).
    :return: The updated streaming profile.
    :rtype: Response
    """
    uri = ["streaming_profiles", name]
    params = __prepare_streaming_profile_params(**options)
    return call_json_api('PUT', uri, params, **options)


def only(source, *keys):
    """
    Returns a dictionary containing only the specified keys from the source.

    :param source: The source dictionary.
    :type source: dict
    :param keys: The keys to retain.
    :type keys: list or tuple of str or str
    :return: A new dictionary with only the specified keys.
    :rtype: dict
    :internal
    """
    return {key: source[key] for key in keys if key in source}


def transformation_string(transformation):
    """
    Converts a transformation (dict or str) into the correct string format.

    :param transformation: The transformation to convert.
    :type transformation: dict or str
    :return: The transformation as a string.
    :rtype: str
    :internal
    """
    if isinstance(transformation, string_types):
        return transformation
    else:
        return cloudinary.utils.generate_transformation_string(**transformation)[0]


def __prepare_streaming_profile_params(**options):
    """
    Prepares the parameters for creating or updating a streaming profile.

    :param options: Additional options, typically including "representations" and "display_name".
    :return: A dictionary of parameters for the streaming profile API call.
    :rtype: dict
    :internal
    """
    params = only(options, "display_name")
    if "representations" in options:
        representations = [{"transformation": transformation_string(trans)}
                           for trans in options["representations"]]
        params["representations"] = json.dumps(representations)
    return params


def __delete_resource_params(options, **params):
    """
    Prepares parameters for delete resource methods, including transformations, keep_original,
    next_cursor, invalidate, etc.

    :param options: A dict of delete-related options.
    :param params: Additional parameters (e.g., prefix, public_ids, asset_ids).
    :type params: dict
    :return: A combined dictionary of params.
    :rtype: dict
    :internal
    """
    p = dict(transformations=utils.build_eager(options.get('transformations')),
             **only(options, "keep_original", "next_cursor", "invalidate"))
    p.update(params)
    return p


def list_metadata_fields(**options):
    """
    Returns a list of all metadata field definitions.

    See: https://cloudinary.com/documentation/admin_api#get_metadata_fields

    :param options: Additional optional parameters (none currently recognized).
    :return: A list of metadata fields.
    :rtype: Response
    """
    return call_metadata_api("get", [], {}, **options)


def metadata_field_by_field_id(field_external_id, **options):
    """
    Gets a metadata field by external id.

    See: https://cloudinary.com/documentation/admin_api#get_a_metadata_field_by_external_id

    :param field_external_id: The ID of the metadata field to retrieve.
    :type field_external_id: str
    :param options: Additional optional parameters (none currently recognized).
    :return: The metadata field details.
    :rtype: Response
    """
    uri = [field_external_id]
    return call_metadata_api("get", uri, {}, **options)


def add_metadata_field(field, **options):
    """
    Creates a new metadata field definition.

    See: https://cloudinary.com/documentation/admin_api#create_a_metadata_field

    :param field: The field to add.
    :type field: dict
    :param options: Additional optional parameters (none currently recognized).
    :return: The created metadata field.
    :rtype: Response
    """
    return call_metadata_api("post", [], __metadata_field_params(field), **options)


def update_metadata_field(field_external_id, field, **options):
    """
    Updates a metadata field by external id.

    See: https://cloudinary.com/documentation/admin_api#update_a_metadata_field_by_external_id

    :param field_external_id: The ID of the metadata field to update.
    :type field_external_id: str
    :param field: The field definition to update.
    :type field: dict
    :param options: Additional optional parameters (none currently recognized).
    :return: The updated metadata field.
    :rtype: Response
    """
    uri = [field_external_id]
    return call_metadata_api("put", uri, __metadata_field_params(field), **options)


def __metadata_field_params(field):
    """
    Builds the parameters needed for creating or updating a metadata field.

    :param field: The field definition.
    :type field: dict
    :return: The relevant key-value pairs.
    :rtype: dict
    :internal
    """
    return only(field, "type", "external_id", "label", "mandatory", "restrictions",
                "default_value", "default_disabled", "validation", "datasource", "allow_dynamic_list_values")


def delete_metadata_field(field_external_id, **options):
    """
    Deletes a metadata field definition.

    See: https://cloudinary.com/documentation/admin_api#delete_a_metadata_field_by_external_id

    :param field_external_id: The external ID of the field to delete.
    :type field_external_id: str
    :param options: Additional optional parameters (none currently recognized).
    :return: An array with a "message" key. "ok" value indicates a successful deletion.
    :rtype: Response
    """
    uri = [field_external_id]
    return call_metadata_api("delete", uri, {}, **options)


def delete_datasource_entries(field_external_id, entries_external_id, **options):
    """
    Deletes entries in a metadata field datasource.

    See: https://cloudinary.com/documentation/admin_api#delete_entries_in_a_metadata_field_datasource

    :param field_external_id: The ID of the field to update.
    :type field_external_id: str
    :param entries_external_id: The IDs of the entries to delete from the datasource.
    :type entries_external_id: list[str]
    :param options: Additional optional parameters (none currently recognized).
    :return: A response indicating the success or failure of the deletion.
    :rtype: Response
    """
    uri = [field_external_id, "datasource"]
    params = {"external_ids": entries_external_id}
    return call_metadata_api("delete", uri, params, **options)


def update_metadata_field_datasource(field_external_id, entries_external_id, **options):
    """
    Updates a metadata field datasource.

    See: https://cloudinary.com/documentation/admin_api#update_a_metadata_field_datasource

    :param field_external_id: The external ID of the field to update.
    :type field_external_id: str
    :param entries_external_id: The list of entries to update/add.
    :type entries_external_id: list[dict]
    :param options: Additional optional parameters (none currently recognized).
    :return: The updated metadata field.
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
    """
    Restores entries in a metadata field datasource.

    See: https://cloudinary.com/documentation/admin_api#restore_entries_in_a_metadata_field_datasource

    :param field_external_id: The ID of the metadata field.
    :type field_external_id: str
    :param entries_external_ids: An array of IDs of datasource entries to restore (unblock).
    :type entries_external_ids: list[str]
    :param options: Additional optional parameters (none currently recognized).
    :return: A response indicating the success or failure of the restore operation.
    :rtype: Response
    """
    uri = [field_external_id, 'datasource_restore']
    params = {"external_ids": entries_external_ids}
    return call_metadata_api("post", uri, params, **options)


def reorder_metadata_field_datasource(field_external_id, order_by, direction=None, **options):
    """
    Reorders a metadata field datasource. Currently supports ordering by 'value'.

    See: https://cloudinary.com/documentation/admin_api#order_a_metadata_field_datasource

    :param field_external_id: The ID of the metadata field.
    :type field_external_id: str
    :param order_by: Criteria for the order. Currently, supports only 'value'.
    :type order_by: str
    :param direction: Optional direction: 'asc' or 'desc'.
    :type direction: str, optional
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the ordering operation.
    :rtype: Response
    """
    uri = [field_external_id, 'datasource', 'order']
    params = {'order_by': order_by, 'direction': direction}
    return call_metadata_api('post', uri, params, **options)


def reorder_metadata_fields(order_by, direction=None, **options):
    """
    Reorders metadata fields.

    :param order_by: Criteria for the order (one of 'label', 'external_id', 'created_at').
    :type order_by: str
    :param direction: Optional direction: 'asc' or 'desc'.
    :type direction: str, optional
    :param options: Additional optional parameters (none currently recognized).
    :return: The result of the ordering operation.
    :rtype: Response
    """
    uri = ['order']
    params = {'order_by': order_by, 'direction': direction}
    return call_metadata_api('put', uri, params, **options)


def list_metadata_rules(**options):
    """
    Returns a list of all metadata rules definitions.

    See: https://cloudinary.com/documentation/admin_api#get_metadata_rules

    :param options: Additional optional parameters (none currently recognized).
    :return: A list of metadata rules.
    :rtype: Response
    """
    return call_metadata_rules_api("get", [], {}, **options)

def __metadata_rule_params(rule):
    """
    Builds the parameters needed for creating or updating a metadata rule.

    :param rule: The rule definition.
    :type rule: dict
    :return: The relevant key-value pairs.
    :rtype: dict
    :internal
    """
    return only(rule, "external_id", "metadata_field_id", "condition", "result", "name", "state")


def add_metadata_rule(rule, **options):
    """
    Creates a new metadata rule definition.

    See: https://cloudinary.com/documentation/admin_api#create_a_metadata_rule

    :param rule: The rule to add.
    :type rule: dict
    :param options: Additional optional parameters (none currently recognized).
    :return: The created metadata rule.
    :rtype: Response
    """
    return call_metadata_rules_api("post", [], __metadata_rule_params(rule), **options)

def update_metadata_rule(rule_external_id, rule, **options):
    """
    Updates a metadata rule by external id.

    See: https://cloudinary.com/documentation/admin_api#update_a_metadata_rule_by_id

    :param rule_external_id: The ID of the metadata rule to update.
    :type rule_external_id: str
    :param rule: The rule definition to update.
    :type rule: dict
    :param options: Additional optional parameters (none currently recognized).
    :return: The updated metadata rule.
    :rtype: Response
    """
    uri = [rule_external_id]
    return call_metadata_rules_api("put", uri, __metadata_rule_params(rule), **options)

def delete_metadata_rule(rule_external_id, **options):
    """
    Deletes a metadata rule definition.

    See: https://cloudinary.com/documentation/admin_api#delete_a_metadata_rule_by_id

    :param rule_external_id: The external ID of the rule to delete.
    :type rule_external_id: str
    :param options: Additional optional parameters (none currently recognized).
    :return: An array with a "success" key. true value indicates a successful deletion.
    :rtype: Response
    """
    uri = [rule_external_id]
    return call_metadata_rules_api("delete", uri, {}, **options)


def analyze(input_type, analysis_type, uri=None, **options):
    """
    Analyzes an asset with the requested analysis type.

    :param input_type: The type of input for the asset to analyze (e.g. 'uri').
    :type input_type: str
    :param analysis_type: The type of analysis to run (e.g. 'google_tagging', 'captioning', 'fashion').
    :type analysis_type: str
    :param uri: The URI of the asset to analyze.
    :type uri: str, optional
    :param options: Additional optional parameters (none currently recognized).
    :return: The analysis result.
    :rtype: Response
    """
    api_uri = ['analysis', 'analyze', input_type]
    params = {
        'analysis_type': analysis_type,
        'uri': uri,
        'parameters': options.get("parameters")
    }
    return _call_v2_api('post', api_uri, params, **options)
