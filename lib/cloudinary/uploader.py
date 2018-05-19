# Copyright Cloudinary
import json
import re
import socket
from os.path import getsize

import cloudinary
import urllib3
import certifi
from cloudinary import utils
from cloudinary.api import Error
from cloudinary.compat import string_types
from urllib3.exceptions import HTTPError
from urllib3 import PoolManager

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
    _http = PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi.where()
    )


def upload(file, **options):
    params = utils.build_upload_params(**options)
    return call_api("upload", params, file=file, **options)


def unsigned_upload(file, upload_preset, **options):
    return upload(file, upload_preset=upload_preset, unsigned=True, **options)


def upload_image(file, **options):
    result = upload(file, **options)
    return cloudinary.CloudinaryImage(
        result["public_id"], version=str(result["version"]),
        format=result.get("format"), metadata=result)


def upload_resource(file, **options):
    result = upload(file, **options)
    return cloudinary.CloudinaryResource(
        result["public_id"], version=str(result["version"]),
        format=result.get("format"), type=result["type"], resource_type=result["resource_type"], metadata=result)


def upload_large(file, **options):
    """ Upload large files. """
    upload_id = utils.random_public_id()
    with open(file, 'rb') as file_io:
        results = None
        current_loc = 0
        chunk_size = options.get("chunk_size", 20000000)
        file_size = getsize(file)
        chunk = file_io.read(chunk_size)
        while chunk:
            range = "bytes {0}-{1}/{2}".format(current_loc, current_loc + len(chunk) - 1, file_size)
            current_loc += len(chunk)

            results = upload_large_part((file, chunk),
                                       http_headers={"Content-Range": range, "X-Unique-Upload-Id": upload_id},
                                       **options)
            options["public_id"] = results.get("public_id")
            chunk = file_io.read(chunk_size)
        return results


def upload_large_part(file, **options):
    """ Upload large files. """
    params = utils.build_upload_params(**options)
    if 'resource_type' not in options: options['resource_type'] = "raw"
    return call_api("upload", params, file=file, **options)


def destroy(public_id, **options):
    params = {
        "timestamp": utils.now(),
        "type": options.get("type"),
        "invalidate": options.get("invalidate"),
        "public_id":    public_id
    }
    return call_api("destroy", params, **options)


def rename(from_public_id, to_public_id, **options):
    params = {
        "timestamp": utils.now(),
        "type": options.get("type"),
        "overwrite": options.get("overwrite"),
        "invalidate": options.get("invalidate"),
        "from_public_id": from_public_id,
        "to_public_id": to_public_id
    }
    return call_api("rename", params, **options)


def explicit(public_id, **options):
    params = utils.build_upload_params(**options)
    params["public_id"] = public_id
    return call_api("explicit", params, **options)


def create_archive(**options):
    params = utils.archive_params(**options)
    if options.get("target_format") is not None:
        params["target_format"] = options.get("target_format")
    return call_api("generate_archive", params, **options)


def create_zip(**options):
    return create_archive(target_format="zip", **options)


def generate_sprite(tag, **options):
    params = {
        "timestamp": utils.now(),
        "tag": tag,
        "async": options.get("async"),
        "notification_url": options.get("notification_url"),
        "transformation": utils.generate_transformation_string(fetch_format=options.get("format"), **options)[0]
    }
    return call_api("sprite", params, **options)


def multi(tag, **options):
    params = {
        "timestamp": utils.now(),
        "tag": tag,
        "format": options.get("format"),
        "async": options.get("async"),
        "notification_url": options.get("notification_url"),
        "transformation": utils.generate_transformation_string(**options)[0]
    }
    return call_api("multi", params, **options)


def explode(public_id, **options):
    params = {
        "timestamp": utils.now(),
        "public_id": public_id,
        "format": options.get("format"),
        "notification_url": options.get("notification_url"),
        "transformation": utils.generate_transformation_string(**options)[0]
    }
    return call_api("explode", params, **options)


# options may include 'exclusive' (boolean) which causes clearing this tag from all other resources
def add_tag(tag, public_ids=None, **options):
    exclusive = options.pop("exclusive", None)
    command = "set_exclusive" if exclusive else "add"
    return call_tags_api(tag, command, public_ids, **options)


def remove_tag(tag, public_ids=None, **options):
    return call_tags_api(tag, "remove", public_ids, **options)


def replace_tag(tag, public_ids=None, **options):
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


TEXT_PARAMS = ["public_id",
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


def call_api(action, params, http_headers=None, return_error=False, unsigned=False, file=None, timeout=None, **options):
    if http_headers is None:
        http_headers = {}
    file_io = None
    try:
        if unsigned:
            params = utils.cleanup_params(params)
        else:
            params = utils.sign_request(params, options)

        param_list = OrderedDict()
        for k, v in params.items():
            if isinstance(v, list):
                for i in range(len(v)):
                    param_list["{0}[{1}]".format(k, i)] = v[i]
            elif v:
                param_list[k] = v

        api_url = utils.cloudinary_api_url(action, **options)
        if file:
            if isinstance(file, string_types):
                if re.match(r'ftp:|https?:|s3:|data:[^;]*;base64,([a-zA-Z0-9\/+\n=]+)$', file):
                    # URL
                    name = None
                    data = file
                else:
                    # file path
                    name = file
                    with open(file, "rb") as opened:
                        data = opened.read()
            elif hasattr(file, 'read') and callable(file.read):
                # stream
                data = file.read()
                name = file.name if hasattr(file, 'name') and isinstance(file.name, str) else "stream"
            elif isinstance(file, tuple):
                name = None
                data = file
            else:
                # Not a string, not a stream
                name = "file"
                data = file

            param_list["file"] = (name, data) if name else data

        headers = {"User-Agent": cloudinary.get_user_agent()}
        headers.update(http_headers)

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
            raise Error("Error parsing server response (%d) - %s. Got - %s", response.status, response, e)

        if "error" in result:
            if response.status not in [200, 400, 401, 403, 404, 500]:
                code = response.status
            if return_error:
                    result["error"]["http_code"] = code
            else:
                raise Error(result["error"]["message"])

        return result
    finally:
        if file_io: file_io.close()
