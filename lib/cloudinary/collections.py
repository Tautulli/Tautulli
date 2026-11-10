# Copyright Cloudinary

import json

from six import string_types

import cloudinary
from cloudinary.api import only
from cloudinary.api_client.call_api import _call_v2_api
from cloudinary.utils import base64url_decode

CUSTOMER_ID_HEADER = "X-Cld-Customer-External-Id"

__COLLECTION_PARAMS = ["name", "description", "configuration"]

__PUBLIC_PAGE_PARAMS = ["name", "available_from", "expires_at", "show_download_original_option",
                        "download_transformations", "create_download_transformations"]

__PUBLIC_PAGE_UPDATE_PARAMS = __PUBLIC_PAGE_PARAMS + ["protection_mode", "allowed_emails", "allowed_domains",
                                                      "allow_any", "custom_layout_url"]


def collections(**options):
    """
    Lists the collections the caller may read, most-recently-updated first by default.

    :param options: Additional options.
    :keyword str query: Case-insensitive filter on the collection name. Matches collections with a
                        word in their name that starts with this text.
    :keyword str sort_by: Sort expression, "<field> <direction>", optionally comma-separated.
                          Field is one of "name", "created_at" or "updated_at"; direction is "asc"
                          or "desc". Defaults to "updated_at desc".
    :keyword int max_results: Maximum number of collections to return. 1-100, default 20.
    :keyword str next_cursor: The cursor from a previous response, to fetch the next page.
    :return: The collections, as {"data": [...], "next_cursor": ...}.
    :rtype: Response
    """
    params = only(options, "query", "sort_by", "max_results", "next_cursor")
    return __call_collections_api("get", [], params, **options)


def create_collection(name, **options):
    """
    Creates a collection and makes the caller its owner.

    :param name: The name of the collection.
    :type name: str
    :param options: Additional options.
    :keyword str description: The description of the collection.
    :keyword str type: "manual" (the default) holds an explicit asset list, populated with
                       `add_collection_assets`; "dynamic" is populated by a saved search expression.
    :keyword dict configuration: The configuration of a dynamic collection, as
                                 {"expression": "<search expression>"}. Required for "dynamic",
                                 not allowed for "manual".
    :return: The created collection.
    :rtype: Response
    """
    params = only(options, "description", "type", "configuration")
    params["name"] = name
    return __call_collections_api("post", [], params, **options)


def collection(collection_id, **options):
    """
    Returns a single collection.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param options: Additional options.
    :return: The collection.
    :rtype: Response
    """
    return __call_collections_api("get", [collection_id], {}, **options)


def update_collection(collection_id, **options):
    """
    Updates a collection. Only the fields passed are changed. The type of a collection can't be changed.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param options: Additional options.
    :keyword str name: The new name of the collection.
    :keyword str description: The new description of the collection.
    :keyword dict configuration: The new configuration of a dynamic collection, as
                                 {"expression": "<search expression>"}.
    :return: The updated collection.
    :rtype: Response
    """
    params = only(options, *__COLLECTION_PARAMS)
    return __call_collections_api("put", [collection_id], params, **options)


def delete_collection(collection_id, **options):
    """
    Deletes a collection. The assets in it are not modified or deleted.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param options: Additional options.
    :return: A dictionary with a "message" key.
    :rtype: Response
    """
    return __call_collections_api("delete", [collection_id], {}, **options)


def collection_assets(collection_id, **options):
    """
    Lists the assets in a collection that the caller may view, newest first by default.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param options: Additional options.
    :keyword str sort_by: Sort expression, "<field> <direction>", optionally comma-separated.
                          Field is one of "created_at", "uploaded_at", "public_id", "display_name"
                          or "bytes"; direction is "asc" or "desc". Defaults to "created_at desc".
                          Send the same sort_by on every page.
    :keyword int max_results: Maximum number of assets to return. 1-100, default 20.
    :keyword str next_cursor: The cursor from a previous response, to fetch the next page.
    :return: The assets, as {"data": [...], "next_cursor": ...}.
    :rtype: Response
    """
    params = only(options, "sort_by", "max_results", "next_cursor")
    return __call_collections_api("get", [collection_id, "assets"], params, **options)


def add_collection_assets(collection_id, asset_ids, **options):
    """
    Adds assets to a collection.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param asset_ids: The asset IDs of the assets to add. A single ID may be passed as a string.
    :type asset_ids: list[str] or str
    :param options: Additional options.
    :return: The collection.
    :rtype: Response
    """
    return __call_collections_api("post", [collection_id, "assets"], __asset_ids_list(asset_ids), **options)


def remove_collection_assets(collection_id, asset_ids, **options):
    """
    Removes assets from a collection. Assets not in the collection are ignored, and the assets
    themselves are not modified or deleted.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param asset_ids: The asset IDs of the assets to remove. A single ID may be passed as a string.
    :type asset_ids: list[str] or str
    :param options: Additional options.
    :return: The collection.
    :rtype: Response
    """
    return __call_collections_api("delete", [collection_id, "assets"], __asset_ids_list(asset_ids), **options)


def create_collection_public_page(collection_id, **options):
    """
    Publishes a collection as a shareable public page.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param options: Additional options.
    :keyword str name: The name of the public page.
    :keyword str available_from: The date-time (ISO 8601) the page becomes available.
    :keyword str expires_at: The date-time (ISO 8601) the page expires.
    :keyword bool show_download_original_option: Whether viewers can download the original assets.
    :keyword list download_transformations: Named transformations viewers can apply when downloading,
                                            as [{"name": "<name>", "types": ["image", ...]}, ...].
                                            At most 200.
    :keyword bool create_download_transformations: Whether to create any listed transformation name
                                                   that isn't a transformation template yet.
    :return: The created public page, including its URL.
    :rtype: Response
    """
    params = only(options, *__PUBLIC_PAGE_PARAMS)
    return __call_collections_api("post", [collection_id, "public_pages"], params, **options)


def collection_public_pages(collection_id, **options):
    """
    Lists the public pages of a collection.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param options: Additional options.
    :return: The public pages, as {"data": [...]}.
    :rtype: Response
    """
    return __call_collections_api("get", [collection_id, "public_pages"], {}, **options)


def collection_public_page(collection_id, public_page_id, **options):
    """
    Returns a single public page of a collection.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param public_page_id: The external ID of the public page.
    :type public_page_id: str
    :param options: Additional options.
    :return: The public page.
    :rtype: Response
    """
    return __call_collections_api("get", [collection_id, "public_pages", public_page_id], {}, **options)


def update_collection_public_page(collection_id, public_page_id, **options):
    """
    Updates the settings of a public page of a collection.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param public_page_id: The external ID of the public page.
    :type public_page_id: str
    :param options: Additional options. Accepts the keywords of `create_collection_public_page`, and:
    :keyword str protection_mode: "none" or "email_otp". "email_otp" requires the secured-sharing
                                  feature on the plan.
    :keyword list allowed_emails: The emails allowed to open a protected page.
    :keyword list allowed_domains: The email domains allowed to open a protected page.
    :keyword bool allow_any: Whether any email may open a protected page.
    :keyword str custom_layout_url: The URL of a custom layout for the page.
    :return: The updated public page.
    :rtype: Response
    """
    params = only(options, *__PUBLIC_PAGE_UPDATE_PARAMS)
    return __call_collections_api("put", [collection_id, "public_pages", public_page_id], params, **options)


def delete_collection_public_page(collection_id, public_page_id, **options):
    """
    Unpublishes a public page of a collection. The collection and its assets are not changed.

    :param collection_id: The external ID of the collection.
    :type collection_id: str
    :param public_page_id: The external ID of the public page.
    :type public_page_id: str
    :param options: Additional options.
    :return: A dictionary with a "message" key.
    :rtype: Response
    """
    return __call_collections_api("delete", [collection_id, "public_pages", public_page_id], {}, **options)


def __asset_ids_list(asset_ids):
    """
    Wraps a single asset ID in a list.

    :internal
    """
    return [asset_ids] if isinstance(asset_ids, string_types) else list(asset_ids)


def __call_collections_api(method, uri, params, **options):
    """
    Private function that assists with performing an API call to the collections endpoints.

    :param method: The HTTP method. Valid methods: get, post, put, delete
    :param uri: REST endpoint of the API (without 'collections', the module or the cloud name)
    :param params: Query/body parameters passed to the method
    :param options: Additional options
    :rtype: Response
    :internal
    """
    oauth_token = options.get("oauth_token", cloudinary.config().oauth_token)
    customer_id = __customer_external_id(oauth_token) if oauth_token else None
    if customer_id:
        extra_headers = {CUSTOMER_ID_HEADER: customer_id}
        extra_headers.update(options.get("extra_headers") or {})
        options["extra_headers"] = extra_headers

    return _call_v2_api(method, ["collections"] + uri, params, module="asset_management", **options)


def __customer_external_id(oauth_token):
    """
    Reads ext.customer_external_id from an unverified JWT payload.

    :param oauth_token: The OAuth access token.
    :return: The customer external ID, or None if absent or unreadable.
    :internal
    """
    try:
        value = json.loads(base64url_decode(oauth_token.split(".")[1]))["ext"]["customer_external_id"]
    except (IndexError, KeyError, TypeError, ValueError):
        return None

    return value if isinstance(value, string_types) and value else None
