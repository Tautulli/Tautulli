# Copyright Cloudinary

import json
import os
import socket

from six import string_types
from urllib3.exceptions import HTTPError

import cloudinary
from cloudinary import utils
from cloudinary.api_client.execute_request import EXCEPTION_CODES
from cloudinary.cache.responsive_breakpoints_cache import instance as responsive_breakpoints_cache_instance
from cloudinary.exceptions import Error
from cloudinary.utils import build_eager

try:
    from urllib3.contrib.appengine import AppEngineManager, is_appengine_sandbox
except Exception:
    def is_appengine_sandbox():
        return False

try:  # Python 2.7+
    from collections import OrderedDict
except ImportError:
    from urllib3.packages.ordered_dict import OrderedDict

if is_appengine_sandbox():
    # AppEngineManager uses AppEngine's URLFetch API behind the scenes
    _http = AppEngineManager()
else:
    # PoolManager uses a socket-level API behind the scenes
    _http = utils.get_http_connector(cloudinary.config(), cloudinary.CERT_KWARGS)

upload_options = [
    "filename",
    "timeout",
    "chunk_size",
    "use_cache"
]

UPLOAD_LARGE_CHUNK_SIZE = 20000000


def upload(file, **options):
    """
    Uploads a file (image, video, or raw) to your Cloudinary product environment.


    See: https://cloudinary.com/documentation/image_upload_api_reference#upload

    :param file:
        The asset to upload. This can be:
         - A local file path (string)
         - A file-like object / stream
         - A Data URI (Base64 encoded)
         - A remote FTP, HTTP, or HTTPS URL
         - A private storage bucket (S3 or Google Storage) URL from a whitelisted bucket
    :type file: str or file-like object

    :param options:
        Additional parameters and configuration for the upload call.

    :keyword str public_id:
        Overrides the default public ID for the uploaded file.
    :keyword str public_id_prefix:
        Prepends a given prefix to the public ID of all uploaded assets.
    :keyword str callback:
        Callback URL or function for asynchronous notifications.
    :keyword str format:
        Force a specific asset format (e.g., "jpg", "png").
    :keyword str type:
        The storage type (default: "upload"). Possible values:
         - "upload" (publicly accessible)
         - "private"
         - "authenticated" (JWT or token-based access)
    :keyword bool backup:
        Whether to back up the asset.
    :keyword bool faces:
        If True, return face coordinates in the response (if faces are detected).
    :keyword bool image_metadata:
        If True, return image metadata (EXIF, etc.) in the response.
    :keyword bool media_metadata:
        If True, return media metadata for file types like PDF or AI.
    :keyword bool exif:
        If True, return EXIF metadata in the response.
    :keyword bool colors:
        If True, return a list of colors predominant in the image.
    :keyword bool use_filename:
        If True, derive the public ID from the file name's basename.
    :keyword bool unique_filename:
        If True, add random characters to the public ID to ensure uniqueness.
    :keyword str display_name:
        A user-friendly name for the asset, displayed in the Media Library.
    :keyword bool use_filename_as_display_name:
        If True, sets the display_name to the file's original filename.
    :keyword bool discard_original_filename:
        If True, do not include the original filename in the public ID.
    :keyword str filename_override:
        Manually override the final filename (instead of deriving from file).
    :keyword bool invalidate:
        If True, invalidates the cached copies on the CDN after upload or transformation.
    :keyword str notification_url:
        A URL to notify when the upload or related process is completed.
    :keyword str eager_notification_url:
        A URL to notify when eager transformations have completed.
    :keyword bool eager_async:
        If True, performs eager transformations asynchronously.
    :keyword str eval:
        Run custom JavaScript (for video or media) at certain processing steps (Advanced).
    :keyword str on_success:
        A function/URL that triggers upon successful processing (Advanced).
    :keyword str proxy:
        A proxy server address if needed for the upload request.
    :keyword str folder:
        The folder path in your Cloudinary product environment to store the asset.
    :keyword str asset_folder:
        A subfolder path for advanced use-cases.
    :keyword bool use_asset_folder_as_public_id_prefix:
        If True, treat the asset_folder path as part of the public ID.
    :keyword bool unique_display_name:
        If True, ensures that the display_name is unique across the product environment.
    :keyword bool overwrite:
        If True, overwrite an existing asset with the same public ID.
    :keyword str moderation:
        The moderation type (e.g., "manual", "webpurify", "aws_rek").
    :keyword str raw_convert:
        Raw file conversion type (e.g., "aspose").
    :keyword str quality_override:
        Overrides the auto-quality or transformation-based quality setting.
    :keyword bool quality_analysis:
        If True, return the advanced quality analysis results in the response.
    :keyword str ocr:
        OCR extraction setting (e.g., "adv_ocr").
    :keyword str categorization:
        Sets categorization mode (e.g., "google_tagging").
    :keyword str detection:
        Sets detection mode (e.g., "adv_face").
    :keyword str similarity_search:
        Reserved for advanced similarity search tasks.
    :keyword str visual_search:
        Reserved for visual search tasks.
    :keyword str background_removal:
        Background removal feature (e.g., "cloudinary_ai", "pixelz").
    :keyword str upload_preset:
        The name of the upload preset to apply. If omitted, defaults to
        ``cloudinary.config().upload_preset`` if configured.
    :keyword bool phash:
        If True, return the perceptual hash (pHash) for the image.
    :keyword bool return_delete_token:
        If True, returns a token that can be used to delete the asset without authentication.
    :keyword float auto_tagging:
        (Range 0.0-1.0) If set, automatically tag the image based on content analysis.
    :keyword bool async:
        If True, requests asynchronous processing (where applicable).
    :keyword bool cinemagraph_analysis:
        If True, performs analysis for cinemagraph creation.
    :keyword bool accessibility_analysis:
        If True, performs accessibility (image alt text) analysis.
    :keyword int timestamp:
        A UNIX timestamp to sign the request. Defaults to now().
    :keyword dict or list transformation:
        A transformation or list of transformations to apply. Internally merged into a single string.
    :keyword dict headers:
        Additional HTTP headers to store with the asset (Advanced usage).
    :keyword list eager:
        A list of eager transformations to generate during the upload.
    :keyword list tags:
        A list of tags (or a comma-delimited string) to assign to the uploaded asset.
    :keyword list allowed_formats:
        A list of file formats allowed for this upload (e.g., ["jpg", "png"]).
    :keyword list or tuple face_coordinates:
        Face rectangle coordinates, encoded into the upload if required.
    :keyword list or tuple custom_coordinates:
        Custom rectangle coordinates, stored with the asset.
    :keyword dict regions:
        Arbitrary region data for advanced transformations or processing.
    :keyword dict or str context:
        Adds or updates contextual metadata (key-value pairs).
    :keyword str responsive_breakpoints:
        A JSON string or list describing how to create responsive breakpoints for the image.
    :keyword list or dict access_control:
        Access control rules (ACL) for the asset, e.g. restricting or allowing access.
    :keyword dict metadata:
        Key-value pairs for structured metadata fields (by external_id).
    :keyword bool use_cache:
        (Uploader-specific) If True, store responsive breakpoints in the local cache.

    :return:
        The result of the Upload API call, typically including:
        - "public_id"
        - "version"
        - "url", "secure_url"
        - etc.
    :rtype: dict
    """
    params = utils.build_upload_params(**options)
    return call_cacheable_api("upload", params, file=file, **options)


def unsigned_upload(file, upload_preset, **options):
    """
    Uploads an asset to Cloudinary without requiring authentication.

    See: https://cloudinary.com/documentation/image_upload_api_reference#unsigned_upload_syntax

    :param file: The asset to upload (local path, file-like object, Data URI, remote URL, or bucket URL).
    :type file: str or file-like object
    :param upload_preset: The unsigned upload preset name to use.
    :type upload_preset: str
    :param options: Additional options for the upload.
    :return: The result of the upload API call.
    :rtype: dict
    """
    return upload(file, upload_preset=upload_preset, unsigned=True, **options)


def upload_image(file, **options):
    """
    Uploads a file and returns a CloudinaryImage object.

    See: https://cloudinary.com/documentation/image_upload_api_reference#upload

    :param file: The asset to upload.
    :type file: Any or str
    :param options: Additional parameters for the upload call.
    :return: A CloudinaryImage object referencing the uploaded image.
    :rtype: cloudinary.CloudinaryImage
    """
    result = upload(file, **options)
    return cloudinary.CloudinaryImage(
        result["public_id"], version=str(result["version"]),
        format=result.get("format"), metadata=result
    )


def upload_resource(file, **options):
    """
    Uploads a file and returns a CloudinaryResource object (image, raw, or video).

    See: https://cloudinary.com/documentation/image_upload_api_reference#upload

    :param file: The asset to upload.
    :type file: Any or str
    :param options: Additional parameters for the upload call.
    :return: A CloudinaryResource object referencing the uploaded asset.
    :rtype: cloudinary.CloudinaryResource
    """
    upload_func = upload
    if hasattr(file, 'size') and file.size > UPLOAD_LARGE_CHUNK_SIZE:
        upload_func = upload_large

    result = upload_func(file, **options)

    return cloudinary.CloudinaryResource(
        result["public_id"],
        version=str(result["version"]),
        format=result.get("format"),
        type=result["type"],
        resource_type=result["resource_type"],
        metadata=result
    )


def upload_large(file, **options):
    """
    Uploads a large file (in chunks) to Cloudinary.

    See: https://cloudinary.com/documentation/image_upload_api_reference#upload

    :param file: The file to upload (local path or file-like object).
    :type file: str or file-like object
    :param options: Additional options for the upload.
    :keyword str filename: Override for the file name (for streams).
    :keyword int chunk_size: Size of each uploaded chunk (default=20000000).
    :keyword bool use_cache: Whether to store responsive breakpoints in cache after upload.
    :return: The result of the upload API call.
    :rtype: dict
    """
    if utils.is_remote_url(file):
        return upload(file, **options)

    if hasattr(file, 'read') and callable(file.read):
        file_io = file
    else:
        file_io = open(file, 'rb')

    upload_result = None

    with file_io:
        upload_id = utils.random_public_id()
        current_loc = 0
        chunk_size = options.get("chunk_size", UPLOAD_LARGE_CHUNK_SIZE)
        file_size = utils.file_io_size(file_io)

        file_name = options.get(
            "filename",
            file_io.name if hasattr(file_io, 'name') and isinstance(file_io.name, str) else "stream"
        )

        chunk = file_io.read(chunk_size)

        while chunk:
            content_range = "bytes {0}-{1}/{2}".format(current_loc, current_loc + len(chunk) - 1, file_size)
            current_loc += len(chunk)
            http_headers = {
                "Content-Range": content_range,
                "X-Unique-Upload-Id": upload_id
            }

            upload_result = upload_large_part((file_name, chunk), http_headers=http_headers, **options)

            options["public_id"] = upload_result.get("public_id")

            chunk = file_io.read(chunk_size)

    return upload_result


def upload_large_part(file, **options):
    """
    Uploads a large chunk (part) of a file to Cloudinary.

    See: https://cloudinary.com/documentation/image_upload_api_reference#upload

    :param file: A tuple of (filename, chunk_data) for the file part to upload.
    :type file: tuple
    :param options: Additional parameters for the chunk upload.
    :return: The result of the chunk upload API call.
    :rtype: dict
    """
    params = utils.build_upload_params(**options)

    if 'resource_type' not in options:
        options['resource_type'] = "raw"

    return call_cacheable_api("upload", params, file=file, **options)


def destroy(public_id, **options):
    """
    Deletes a resource (asset) from Cloudinary by public ID.

    See: https://cloudinary.com/documentation/image_upload_api_reference#destroy

    :param public_id: The public ID of the resource to delete.
    :type public_id: str
    :param options: Additional options for the deletion.
    :keyword str type: The storage type (upload, private, authenticated).
    :keyword bool invalidate: Invalidate cached copies on the CDN if True.
    :return: The result of the API call.
    :rtype: dict
    """
    params = {
        "timestamp": utils.now(),
        "type": options.get("type"),
        "invalidate": options.get("invalidate"),
        "public_id": public_id
    }
    return call_api("destroy", params, **options)


def rename(from_public_id, to_public_id, **options):
    """
    Renames a resource (asset) in Cloudinary.

    See: https://cloudinary.com/documentation/image_upload_api_reference#rename_public_id

    :param from_public_id: The current public ID of the resource.
    :type from_public_id: str
    :param to_public_id: The new public ID for the resource.
    :type to_public_id: str
    :param options: Additional options for the rename operation.
    :keyword str type: The storage type of the original asset. Default=upload.
    :keyword bool overwrite: Whether to overwrite if the to_public_id already exists.
    :keyword bool invalidate: Invalidate cached copies on the CDN if True.
    :keyword str to_type: Change the resource to the specified upload type.
    :keyword dict context: Set or update contextual metadata.
    :keyword dict metadata: Set or update structured metadata.
    :return: The result of the API call.
    :rtype: dict
    """
    params = {
        "timestamp": utils.now(),
        "type": options.get("type"),
        "overwrite": options.get("overwrite"),
        "invalidate": options.get("invalidate"),
        "from_public_id": from_public_id,
        "to_public_id": to_public_id,
        "to_type": options.get("to_type"),
        "context": options.get("context"),
        "metadata": options.get("metadata")
    }
    return call_api("rename", params, **options)


def update_metadata(metadata, public_ids, **options):
    """
    Populates or updates metadata fields with the given values.

    See: https://cloudinary.com/documentation/image_upload_api_reference#metadata

    :param metadata: Key-value pairs for custom metadata fields (by external_id).
    :type metadata: dict
    :param public_ids: A list of public IDs (assets) to update.
    :type public_ids: list[str]
    :param options: Additional options such as resource_type or type.
    :keyword str resource_type: The resource type (image, raw, video). Default="image".
    :keyword str type: The storage type (upload, private, authenticated).
    :keyword bool clear_invalid: If True, remove keys that are not valid.
    :return: A list of public IDs that were updated.
    :rtype: dict
    """
    params = {
        "timestamp": utils.now(),
        "metadata": utils.encode_context(metadata),
        "public_ids": utils.build_array(public_ids),
        "type": options.get("type"),
        "clear_invalid": options.get("clear_invalid")
    }
    return call_api("metadata", params, **options)


def explicit(public_id, **options):
    """
    Applies actions to already uploaded assets (raw, image, or video) via an explicit call.

    See: https://cloudinary.com/documentation/image_upload_api_reference#explicit

    :param public_id: The public ID of the asset to process.
    :type public_id: str
    :param options: Additional options for the explicit API call.
    :return: The result of the API call.
    :rtype: dict
    """
    params = utils.build_upload_params(**options)
    params["public_id"] = public_id
    return call_cacheable_api("explicit", params, **options)


def create_archive(**options):
    """
    Creates an archive of assets in Cloudinary.

    See: https://cloudinary.com/documentation/image_upload_api_reference#generate_archive

    :param options: Additional options for the archive creation (filters, transformations, etc.).
    :keyword str target_format: Archive format (zip, tgz, etc.).
    :return: The result of the API call.
    :rtype: dict
    """
    params = utils.archive_params(**options)
    if options.get("target_format") is not None:
        params["target_format"] = options.get("target_format")
    return call_api("generate_archive", params, **options)


def create_zip(**options):
    """
    Creates a ZIP archive of assets in Cloudinary.

    See: https://cloudinary.com/documentation/image_upload_api_reference#create_zip_syntax

    :param options: Additional options for archive creation.
    :return: The result of the API call.
    :rtype: dict
    """
    return create_archive(target_format="zip", **options)


def generate_sprite(tag=None, urls=None, **options):
    """
    Generates sprites by merging multiple images into a single large image.

    See: https://cloudinary.com/documentation/image_upload_api_reference#sprite

    :param tag: Images with this tag will be used to create the sprite (if set).
    :type tag: str
    :param urls: List of URLs to create a sprite from (only if tag not set).
    :type urls: list[str], optional
    :param options: Additional sprite configuration.
    :return: Dictionary with metadata and URLs of generated sprite resources.
    :rtype: dict
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return call_api("sprite", params, **options)


def download_generated_sprite(tag=None, urls=None, **options):
    """
    Generates a downloadable URL for the sprite (with `mode=download`).

    :param tag: Images with this tag will be used to create the sprite (if set).
    :type tag: str
    :param urls: List of URLs to create a sprite from (only if tag not set).
    :type urls: list[str], optional
    :param options: Additional sprite configuration.
    :return: The signed URL to download the sprite.
    :rtype: str
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return utils.cloudinary_api_download_url(action="sprite", params=params, **options)


def multi(tag=None, urls=None, **options):
    """
    Creates an animated image, video, or PDF from a set of images.

    See: https://cloudinary.com/documentation/image_upload_api_reference#multi

    :param tag: Assets with this tag will be used (if set).
    :type tag: str
    :param urls: A list of image URLs (if no tag is set).
    :type urls: list[str], optional
    :param options: Additional multi-configuration options.
    :return: Dictionary with metadata and URLs of the generated file.
    :rtype: dict
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return call_api("multi", params, **options)


def download_multi(tag=None, urls=None, **options):
    """
    Generates a downloadable URL for the multi (with `mode=download`).

    :param tag: Assets with this tag will be used (if set).
    :type tag: str
    :param urls: A list of image URLs (if no tag is set).
    :type urls: list[str], optional
    :param options: Additional multi-configuration options.
    :return: The signed URL to download the multi.
    :rtype: str
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return utils.cloudinary_api_download_url(action="multi", params=params, **options)


def explode(public_id, **options):
    """
    Creates derived images for all the individual pages in a multi-page file (PDF or animated GIF).

    See: https://cloudinary.com/documentation/image_upload_api_reference#explode

    :param public_id: The public ID of the file to explode.
    :type public_id: str
    :param options: Additional explode options (format, notification_url, transformation).
    :return: The result of the API call.
    :rtype: dict
    """
    params = {
        "timestamp": utils.now(),
        "public_id": public_id,
        "format": options.get("format"),
        "notification_url": options.get("notification_url"),
        "transformation": utils.generate_transformation_string(**options)[0]
    }
    return call_api("explode", params, **options)


def add_tag(tag, public_ids=None, **options):
    """
    Adds one or more tags to the specified assets.

    See: https://cloudinary.com/documentation/image_upload_api_reference#adding_tags_syntax

    :param tag: A single tag or multiple tags (comma-separated string or list).
    :type tag: str or list[str]
    :param public_ids: A list of public IDs (up to 1000).
    :type public_ids: list[str], optional
    :param options: Additional options (e.g., exclusive).
    :keyword bool exclusive: If True, clears this tag from all other assets in the product environment.
    :return: Dictionary with a list of updated public IDs.
    :rtype: dict
    """
    exclusive = options.pop("exclusive", None)
    command = "set_exclusive" if exclusive else "add"
    return call_tags_api(tag, command, public_ids, **options)


def remove_tag(tag, public_ids=None, **options):
    """
    Removes one or more tags from the specified assets.

    See: https://cloudinary.com/documentation/image_upload_api_reference#removing_tags_syntax

    :param tag: A single tag or multiple tags (comma-separated string or list).
    :type tag: str or list[str]
    :param public_ids: A list of public IDs (up to 1000).
    :type public_ids: list[str], optional
    :param options: Additional options.
    :return: Dictionary with a list of updated public IDs.
    :rtype: dict
    """
    return call_tags_api(tag, "remove", public_ids, **options)


def replace_tag(tag, public_ids=None, **options):
    """
    Replaces all existing tags on the specified assets with a given tag (or tags).

    See: https://cloudinary.com/documentation/image_upload_api_reference#replacing_tags_syntax

    :param tag: A single tag or multiple tags (comma-separated string or list).
    :type tag: str or list[str]
    :param public_ids: A list of public IDs (up to 1000).
    :type public_ids: list[str], optional
    :param options: Additional options.
    :return: Dictionary with a list of updated public IDs.
    :rtype: dict
    """
    return call_tags_api(tag, "replace", public_ids, **options)


def remove_all_tags(public_ids, **options):
    """
    Removes all tags from the specified public IDs.

    See: https://cloudinary.com/documentation/image_upload_api_reference#removing_all_tags_syntax

    :param public_ids: The public IDs of the assets.
    :type public_ids: list[str]
    :param options: Additional options.
    :return: Dictionary with a list of updated public IDs.
    :rtype: dict
    """
    return call_tags_api(None, "remove_all", public_ids, **options)


def add_context(context, public_ids, **options):
    """
    Adds contextual metadata (key-value pairs) to the specified assets.

    See: https://cloudinary.com/documentation/image_upload_api_reference#adding_context_syntax

    :param context: A dictionary of context key-value pairs.
    :type context: dict
    :param public_ids: The public IDs of the assets to update.
    :type public_ids: list[str]
    :param options: Additional options.
    :return: Dictionary with a list of updated public IDs.
    :rtype: dict
    """
    return call_context_api(context, "add", public_ids, **options)


def remove_all_context(public_ids, **options):
    """
    Removes all custom contextual metadata from the specified public IDs.

    See: https://cloudinary.com/documentation/image_upload_api_reference#removing_all_context_syntax

    :param public_ids: The public IDs of the assets to update.
    :type public_ids: list[str]
    :param options: Additional options.
    :return: Dictionary with a list of updated public IDs.
    :rtype: dict
    """
    return call_context_api(None, "remove_all", public_ids, **options)


def call_tags_api(tag, command, public_ids=None, **options):
    """
    Internal helper function for adding/removing/replacing tags on assets.

    See: https://cloudinary.com/documentation/image_upload_api_reference#tags

    :param tag: A single tag or multiple tags.
    :type tag: str or list[str], optional
    :param command: The command to execute ("add", "remove", "replace", or "remove_all").
    :type command: str
    :param public_ids: A list of asset public IDs.
    :type public_ids: list[str], optional
    :param options: Additional options (e.g., type).
    :return: The result of the API call.
    :rtype: dict
    """
    params = {
        "timestamp": utils.now(),
        "tag": tag,
        "public_ids": utils.build_array(public_ids),
        "command": command,
        "type": options.get("type")
    }
    return call_api("tags", params, **options)


def call_context_api(context, command, public_ids=None, **options):
    """
    Internal helper for adding/removing context on assets.

    See: https://cloudinary.com/documentation/image_upload_api_reference#context

    :param context: A dictionary of context or None.
    :type context: dict or None
    :param command: The context command ("add", "remove_all").
    :type command: str
    :param public_ids: A list of asset public IDs.
    :type public_ids: list[str], optional
    :param options: Additional options (e.g., type).
    :return: The result of the API call.
    :rtype: dict
    """
    params = {
        "timestamp": utils.now(),
        "context": utils.encode_context(context),
        "public_ids": utils.build_array(public_ids),
        "command": command,
        "type": options.get("type")
    }
    return call_api("context", params, **options)


TEXT_PARAMS = [
    "public_id",
    "font_family",
    "font_size",
    "font_color",
    "text_align",
    "font_weight",
    "font_style",
    "background",
    "opacity",
    "text_decoration"
]


def text(text, **options):
    """
    Dynamically generates an image of a given text string.

    See: https://cloudinary.com/documentation/image_upload_api_reference#text

    :param text: The text string to generate an image for.
    :type text: str
    :param options: Additional options (e.g., font_family, font_size, etc.).
    :return: The result of the text API call.
    :rtype: dict
    """
    params = {"timestamp": utils.now(), "text": text}
    for key in TEXT_PARAMS:
        params[key] = options.get(key)
    return call_api("text", params, **options)


_SLIDESHOW_PARAMS = [
    "notification_url",
    "public_id",
    "overwrite",
    "upload_preset",
]


def create_slideshow(**options):
    """
    Creates an auto-generated video slideshow from existing assets.

    :param options: Additional parameters for the slideshow creation.
    :keyword str resource_type: The resource type, defaults to "video".
    :keyword str notification_url: A URL to be notified when the processing is completed.
    :keyword str public_id: The public ID to assign to the generated slideshow.
    :keyword bool overwrite: Whether to overwrite the slideshow if public_id already exists.
    :keyword str upload_preset: An upload preset to apply to the slideshow creation.
    :keyword list transformation: A list or dict describing transformations to apply.
    :keyword list manifest_transformation: A list or dict transformations for the manifest.
    :keyword dict manifest_json: A JSON specification for advanced slideshow creation.
    :keyword list tags: A list of tags for the slideshow.
    :return: Dictionary with details about the created slideshow.
    :rtype: dict
    """
    options["resource_type"] = options.get("resource_type", "video")

    params = {param_name: options.get(param_name) for param_name in _SLIDESHOW_PARAMS}

    serialized_params = {
        "timestamp": utils.now(),
        "transformation": build_eager(options.get("transformation")),
        "manifest_transformation": build_eager(options.get("manifest_transformation")),
        "manifest_json": options.get("manifest_json") and utils.json_encode(options.get("manifest_json")),
        "tags": options.get("tags") and utils.encode_list(utils.build_array(options["tags"])),
    }

    params.update(serialized_params)

    return call_api("create_slideshow", params, **options)


def _save_responsive_breakpoints_to_cache(result):
    """
    Saves any responsive breakpoints parsed from an upload result to the local cache.

    :param result: The upload result dictionary.
    :type result: dict
    """
    if "responsive_breakpoints" not in result:
        return

    if "public_id" not in result:
        # Invalid result or missing public_id
        return

    options = dict((k, result[k]) for k in ["type", "resource_type"] if k in result)

    for transformation in result.get("responsive_breakpoints", []):
        options["raw_transformation"] = transformation.get("transformation", "")
        options["format"] = os.path.splitext(transformation["breakpoints"][0]["url"])[1][1:]
        breakpoints = [bp["width"] for bp in transformation["breakpoints"]]
        responsive_breakpoints_cache_instance.set(result["public_id"], breakpoints, **options)


def call_cacheable_api(action, params, http_headers=None, return_error=False, unsigned=False, file=None, timeout=None,
                       **options):
    """
    Calls the Upload API and caches responsive breakpoints if enabled.

    :param action: The Cloudinary API endpoint to call (e.g., "upload", "explicit").
    :type action: str
    :param params: The parameters for the API call (already built and signed if needed).
    :type params: dict
    :param http_headers: Optional HTTP headers to send.
    :type http_headers: dict, optional
    :param return_error: If True, returns errors in the response instead of raising them.
    :type return_error: bool
    :param unsigned: If True, the request is not signed (unsigned upload).
    :type unsigned: bool
    :param file: A file-like object or path to send to the endpoint.
    :type file: Any, optional
    :param timeout: Request timeout in seconds.
    :type timeout: int, optional
    :param options: Additional Cloudinary configuration or parameters.
    :return: The parsed JSON response from Cloudinary.
    :rtype: dict
    """
    result = call_api(action, params, http_headers, return_error, unsigned, file, timeout, **options)
    if "use_cache" in options or cloudinary.config().use_cache:
        _save_responsive_breakpoints_to_cache(result)
    return result


def call_api(action, params, http_headers=None, return_error=False, unsigned=False, file=None, timeout=None,
             extra_headers=None, **options):
    """
    A low-level helper to call the Cloudinary Upload API.

    :param action: The specific endpoint to call (e.g. "upload", "destroy").
    :type action: str
    :param params: The dictionary of parameters to send to the endpoint.
    :type params: dict
    :param http_headers: HTTP headers to include in the request.
    :type http_headers: dict, optional
    :param return_error: If True, returns the error in the response instead of raising an exception.
    :type return_error: bool
    :param unsigned: If True, this call is not signed (unsigned upload).
    :type unsigned: bool
    :param file: File data or path to upload if relevant.
    :type file: Any, optional
    :param timeout: Timeout (in seconds) for the request.
    :type timeout: int, optional
    :param extra_headers: Additional headers to add/override.
    :type extra_headers: dict, optional
    :param options: Additional Cloudinary config or advanced parameters.
    :return: The parsed JSON response from Cloudinary.
    :rtype: dict

    :raises Error: If an HTTP error or a Cloudinary error occurs.
    """
    params = utils.cleanup_params(params)

    headers = {"User-Agent": cloudinary.get_user_agent()}

    if http_headers is not None:
        headers.update(http_headers)

    if extra_headers is not None:
        headers.update(extra_headers)

    oauth_token = options.get("oauth_token", cloudinary.config().oauth_token)

    if oauth_token:
        headers["authorization"] = "Bearer {}".format(oauth_token)
    elif not unsigned:
        params = utils.sign_request(params, options)

    param_list = []
    for k, v in params.items():
        if isinstance(v, list):
            for i in v:
                param_list.append(("{0}[]".format(k), i))
        elif v:
            param_list.append((k, v))

    api_url = utils.cloudinary_api_url(action, **options)

    if file:
        filename = options.get("filename")  # Custom filename for streams
        param_list.append(("file", utils.handle_file_parameter(file, filename)))

    kw = {}
    if timeout is not None:
        kw['timeout'] = timeout

    try:
        response = _http.request(method="POST", url=api_url, fields=param_list, headers=headers, **kw)
    except HTTPError as e:
        raise Error("Unexpected error - {0!r}".format(e))
    except socket.error as e:
        raise Error("Socket error: {0!r}".format(e))

    try:
        result = json.loads(response.data.decode('utf-8'))
    except Exception as e:
        raise Error("Error parsing server response ({0}) - {1}. Got - {2}"
                    .format(response.status, response.data, e))

    if "error" in result:
        if return_error:
            result["error"]["http_code"] = response.status
            return result

        exception_class = EXCEPTION_CODES.get(response.status) or Error
        raise exception_class(result["error"]["message"])

    return result
