# Copyright Cloudinary
import json
import os
import socket

from six import string_types
from urllib3.exceptions import HTTPError

import cloudinary
from cloudinary import utils
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

try:  # Python 3.4+
    from pathlib import Path as PathLibPathType
except ImportError:
    PathLibPathType = None

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
    params = utils.build_upload_params(**options)
    return call_cacheable_api("upload", params, file=file, **options)


def unsigned_upload(file, upload_preset, **options):
    return upload(file, upload_preset=upload_preset, unsigned=True, **options)


def upload_image(file, **options):
    result = upload(file, **options)
    return cloudinary.CloudinaryImage(
        result["public_id"], version=str(result["version"]),
        format=result.get("format"), metadata=result)


def upload_resource(file, **options):
    upload_func = upload
    if hasattr(file, 'size') and file.size > UPLOAD_LARGE_CHUNK_SIZE:
        upload_func = upload_large

    result = upload_func(file, **options)

    return cloudinary.CloudinaryResource(
        result["public_id"], version=str(result["version"]),
        format=result.get("format"), type=result["type"],
        resource_type=result["resource_type"], metadata=result)


def upload_large(file, **options):
    """ Upload large files. """
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
            file_io.name if hasattr(file_io, 'name') and isinstance(file_io.name, str) else "stream")

        chunk = file_io.read(chunk_size)

        while chunk:
            content_range = "bytes {0}-{1}/{2}".format(current_loc, current_loc + len(chunk) - 1, file_size)
            current_loc += len(chunk)
            http_headers = {"Content-Range": content_range, "X-Unique-Upload-Id": upload_id}

            upload_result = upload_large_part((file_name, chunk), http_headers=http_headers, **options)

            options["public_id"] = upload_result.get("public_id")

            chunk = file_io.read(chunk_size)

    return upload_result


def upload_large_part(file, **options):
    """ Upload large files. """
    params = utils.build_upload_params(**options)

    if 'resource_type' not in options:
        options['resource_type'] = "raw"

    return call_cacheable_api("upload", params, file=file, **options)


def destroy(public_id, **options):
    params = {
        "timestamp": utils.now(),
        "type": options.get("type"),
        "invalidate": options.get("invalidate"),
        "public_id": public_id
    }
    return call_api("destroy", params, **options)


def rename(from_public_id, to_public_id, **options):
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
    Populates metadata fields with the given values. Existing values will be overwritten.

    Any metadata-value pairs given are merged with any existing metadata-value pairs
    (an empty value for an existing metadata field clears the value)

    :param metadata: A list of custom metadata fields (by external_id) and the values to assign to each
                     of them.
    :param public_ids: An array of Public IDs of assets uploaded to Cloudinary.
    :param options: Options such as
            *resource_type* (the type of file. Default: image. Valid values: image, raw, or video) and
            *type* (The storage type. Default: upload. Valid values: upload, private, or authenticated.)

    :return: A list of public IDs that were updated
    :rtype: mixed
    """
    params = {
        "timestamp": utils.now(),
        "metadata": utils.encode_context(metadata),
        "public_ids": utils.build_array(public_ids),
        "type": options.get("type")
    }

    return call_api("metadata", params, **options)


def explicit(public_id, **options):
    params = utils.build_upload_params(**options)
    params["public_id"] = public_id
    return call_cacheable_api("explicit", params, **options)


def create_archive(**options):
    params = utils.archive_params(**options)
    if options.get("target_format") is not None:
        params["target_format"] = options.get("target_format")
    return call_api("generate_archive", params, **options)


def create_zip(**options):
    return create_archive(target_format="zip", **options)


def generate_sprite(tag=None, urls=None, **options):
    """
    Generates sprites by merging multiple images into a single large image.

    See: `Sprite method API reference
    <https://cloudinary.com/documentation/image_upload_api_reference#sprite_method>`_

    :param tag:     The sprite is created from all images with this tag. If not set - `urls` parameter is required
    :type tag:      str
    :param urls:    List of URLs to create a sprite from. Can only be used if `tag` is not set
    :type urls:     list
    :param options: Additional options
    :type options:  dict, optional
    :return:        Dictionary with meta information URLs of generated sprite resources
    :rtype:         dict
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return call_api("sprite", params, **options)


def download_generated_sprite(tag=None, urls=None, **options):
    """
    Returns signed URL for the sprite endpoint with `mode=download`

    :param tag:     The sprite is created from all images with this tag. If not set - `urls` parameter is required
    :type tag:      str
    :param urls:    List of URLs to create a sprite from. Can only be used if `tag` is not set
    :type urls:     list
    :param options: Additional options
    :type options:  dict, optional
    :return:        The signed URL to download sprite
    :rtype:         str
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return utils.cloudinary_api_download_url(action="sprite", params=params, **options)


def multi(tag=None, urls=None, **options):
    """
    Creates either a single animated image, video or a PDF.

    See: `Upload method API reference
    <https://cloudinary.com/documentation/image_upload_api_reference#multi_method>`_

    :param tag:     The animated image, video or PDF is created from all images with this tag.
                    If not set - `urls` parameter is required
    :type tag:      str
    :param urls:    List of URLs to create an animated image, video or PDF from. Can only be used if `tag` is not set
    :type urls:     list
    :param options: Additional options
    :type options:  dict, optional
    :return:        Dictionary with meta information URLs of the generated file
    :rtype:         dict
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return call_api("multi", params, **options)


def download_multi(tag=None, urls=None, **options):
    """
    Returns signed URL for the multi endpoint with `mode=download`

    :param tag:     The sprite is created from all images with this tag. If not set - `urls` parameter is required
    :type tag:      str
    :param urls:    List of URLs to create a sprite from. Can only be used if `tag` is not set
    :type urls:     list
    :param options: Additional options
    :type options:  dict, optional
    :return:        The signed URL to download multi
    :rtype:         str
    """
    params = utils.build_multi_and_sprite_params(tag=tag, urls=urls, **options)
    return utils.cloudinary_api_download_url(action="multi", params=params, **options)


def explode(public_id, **options):
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
    Adds a single tag or a list of tags or a comma-separated tags to the assets.

    :param tag:         The tag or tags to assign. Can specify multiple tags in a single string,
                        separated by commas - "t1,t2,t3" or list of tags - ["t1","t2","t3"].
    :param public_ids:  A list of public IDs (up to 1000).
    :param options:     Configuration options may include 'exclusive' (boolean) which causes
                        clearing this tag from all other assets.

    :return:            Dictionary with a list of public IDs that were updated.
    """
    exclusive = options.pop("exclusive", None)
    command = "set_exclusive" if exclusive else "add"
    return call_tags_api(tag, command, public_ids, **options)


def remove_tag(tag, public_ids=None, **options):
    """
    Removes a single tag or a list of tags or a comma-separated tags from the assets.

    :param tag:         The tag or tags to assign. Can specify multiple tags in a single string,
                        separated by commas - "t1,t2,t3" or list of tags - ["t1","t2","t3"].
    :param public_ids:  A list of public IDs (up to 1000).
    :param options:     Additional options.

    :return:            Dictionary with a list of public IDs that were updated.
    """
    return call_tags_api(tag, "remove", public_ids, **options)


def replace_tag(tag, public_ids=None, **options):
    """
    Replaces all existing tags with a single tag or a list of tags or a comma-separated tags of the assets.

    :param tag:         The tag or tags to assign. Can specify multiple tags in a single string,
                        separated by commas - "t1,t2,t3" or list of tags - ["t1","t2","t3"].
    :param public_ids:  A list of public IDs (up to 1000).
    :param options:     Additional options.

    :return:            Dictionary with a list of public IDs that were updated.
    """
    return call_tags_api(tag, "replace", public_ids, **options)


def remove_all_tags(public_ids, **options):
    """
    Remove all tags from the specified public IDs.

    :param public_ids: the public IDs of the resources to update
    :param options: additional options passed to the request

    :return: dictionary with a list of public IDs that were updated
    """
    return call_tags_api(None, "remove_all", public_ids, **options)


def add_context(context, public_ids, **options):
    """
    Add a context keys and values. If a particular key already exists, the value associated with the key is updated.

    :param context: dictionary of context
    :param public_ids: the public IDs of the resources to update
    :param options: additional options passed to the request

    :return: dictionary with a list of public IDs that were updated
    """
    return call_context_api(context, "add", public_ids, **options)


def remove_all_context(public_ids, **options):
    """
    Remove all custom context from the specified public IDs.

    :param public_ids: the public IDs of the resources to update
    :param options: additional options passed to the request

    :return: dictionary with a list of public IDs that were updated
    """
    return call_context_api(None, "remove_all", public_ids, **options)


def call_tags_api(tag, command, public_ids=None, **options):
    params = {
        "timestamp": utils.now(),
        "tag": tag,
        "public_ids": utils.build_array(public_ids),
        "command": command,
        "type": options.get("type")
    }
    return call_api("tags", params, **options)


def call_context_api(context, command, public_ids=None, **options):
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
    Creates auto-generated video slideshows.

    :param options: The optional parameters.  See the upload API documentation.

    :return: a dictionary with details about created slideshow
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
    Saves responsive breakpoints parsed from upload result to cache

    :param result: Upload result
    """
    if "responsive_breakpoints" not in result:
        return

    if "public_id" not in result:
        # We have some faulty result, nothing to cache
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
    Calls Upload API and saves results to cache (if enabled)
    """

    result = call_api(action, params, http_headers, return_error, unsigned, file, timeout, **options)

    if "use_cache" in options or cloudinary.config().use_cache:
        _save_responsive_breakpoints_to_cache(result)

    return result


def call_api(action, params, http_headers=None, return_error=False, unsigned=False, file=None, timeout=None, **options):
    params = utils.cleanup_params(params)

    headers = {"User-Agent": cloudinary.get_user_agent()}

    if http_headers is not None:
        headers.update(http_headers)

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
        filename = options.get("filename")  # Custom filename provided by user (relevant only for streams and files)

        if PathLibPathType and isinstance(file, PathLibPathType):
            name = filename or file.name
            data = file.read_bytes()
        elif isinstance(file, string_types):
            if utils.is_remote_url(file):
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

        param_list.append(("file", (name, data) if name else data))

    kw = {}
    if timeout is not None:
        kw['timeout'] = timeout

    code = 200
    try:
        response = _http.request("POST", api_url, param_list, headers, **kw)
    except HTTPError as e:
        raise Error("Unexpected error - {0!r}".format(e))
    except socket.error as e:
        raise Error("Socket error: {0!r}".format(e))

    try:
        result = json.loads(response.data.decode('utf-8'))
    except Exception as e:
        # Error is parsing json
        raise Error("Error parsing server response (%d) - %s. Got - %s" % (response.status, response.data, e))

    if "error" in result:
        if response.status not in [200, 400, 401, 403, 404, 500]:
            code = response.status
        if return_error:
            result["error"]["http_code"] = code
        else:
            raise Error(result["error"]["message"])

    return result
