# This file is part of the musicbrainzngs library
# Copyright (C) Alastair Porter, Wieland Hoffmann, and others
# This file is distributed under a BSD-2-Clause type license.
# See the COPYING file for more information.

__all__ = [
    'set_caa_hostname', 'get_image_list', 'get_release_group_image_list',
    'get_release_group_image_front', 'get_image_front', 'get_image_back',
    'get_image'
    ]

import json

from musicbrainzngs import compat
from musicbrainzngs import musicbrainz
from musicbrainzngs.util import _unicode

hostname = "coverartarchive.org"
https = True


def set_caa_hostname(new_hostname, use_https=False):
    """Set the base hostname for Cover Art Archive requests.
    Defaults to 'coverartarchive.org', accessing over https.
    For backwards compatibility, `use_https` is False by default.

    :param str new_hostname: The hostname (and port) of the CAA server to connect to
    :param bool use_https: `True` if the host should be accessed using https. Default is `False`
"""
    global hostname
    global https
    hostname = new_hostname
    https = use_https


def _caa_request(mbid, imageid=None, size=None, entitytype="release"):
    """ Make a CAA request.

    :param imageid: ``front``, ``back`` or a number from the listing obtained
                    with :meth:`get_image_list`.
    :type imageid: str

    :param size: "250", "500", "1200"
    :type size: str or None

    :param entitytype: ``release`` or ``release-group``
    :type entitytype: str
    """
    # Construct the full URL for the request, including hostname and
    # query string.
    path = [entitytype, mbid]
    if imageid and size:
        path.append("%s-%s" % (imageid, size))
    elif imageid:
        path.append(imageid)
    url = compat.urlunparse((
        'https' if https else 'http',
        hostname,
        '/%s' % '/'.join(path),
        '',
        '',
        ''
    ))
    musicbrainz._log.debug("GET request for %s" % (url, ))

    # Set up HTTP request handler and URL opener.
    httpHandler = compat.HTTPHandler(debuglevel=0)
    handlers = [httpHandler]

    opener = compat.build_opener(*handlers)

    # Make request.
    req = musicbrainz._MusicbrainzHttpRequest("GET", url, None)
    # Useragent isn't needed for CAA, but we'll add it if it exists
    if musicbrainz._useragent != "":
        req.add_header('User-Agent', musicbrainz._useragent)
        musicbrainz._log.debug("requesting with UA %s" % musicbrainz._useragent)

    resp = musicbrainz._safe_read(opener, req, None)

    # TODO: The content type declared by the CAA for JSON files is
    # 'applicaiton/octet-stream'. This is not useful to detect whether the
    # content is JSON, so default to decoding JSON if no imageid was supplied.
    # http://tickets.musicbrainz.org/browse/CAA-75
    if imageid:
        # If we asked for an image, return the image
        return resp
    else:
        # Otherwise it's json
        data = _unicode(resp)
        return json.loads(data)


def get_image_list(releaseid):
    """Get the list of cover art associated with a release.

    The return value is the deserialized response of the `JSON listing
    <http://musicbrainz.org/doc/Cover_Art_Archive/API#.2Frelease.2F.7Bmbid.7D.2F>`_
    returned by the Cover Art Archive API.

    If an error occurs then a :class:`~musicbrainzngs.ResponseError` will
    be raised with one of the following HTTP codes:

    * 400: `Releaseid` is not a valid UUID
    * 404: No release exists with an MBID of `releaseid`
    * 503: Ratelimit exceeded
    """
    return _caa_request(releaseid)


def get_release_group_image_list(releasegroupid):
    """Get the list of cover art associated with a release group.

    The return value is the deserialized response of the `JSON listing
    <http://musicbrainz.org/doc/Cover_Art_Archive/API#.2Frelease-group.2F.7Bmbid.7D.2F>`_
    returned by the Cover Art Archive API.

    If an error occurs then a :class:`~musicbrainzngs.ResponseError` will
    be raised with one of the following HTTP codes:

    * 400: `Releaseid` is not a valid UUID
    * 404: No release exists with an MBID of `releaseid`
    * 503: Ratelimit exceeded
    """
    return _caa_request(releasegroupid, entitytype="release-group")


def get_release_group_image_front(releasegroupid, size=None):
    """Download the front cover art for a release group.
    The `size` argument and the possible error conditions are the same as for
    :meth:`get_image`.
    """
    return get_image(releasegroupid, "front", size=size,
                     entitytype="release-group")


def get_image_front(releaseid, size=None):
    """Download the front cover art for a release.
    The `size` argument and the possible error conditions are the same as for
    :meth:`get_image`.
    """
    return get_image(releaseid, "front", size=size)


def get_image_back(releaseid, size=None):
    """Download the back cover art for a release.
    The `size` argument and the possible error conditions are the same as for
    :meth:`get_image`.
    """
    return get_image(releaseid, "back", size=size)


def get_image(mbid, coverid, size=None, entitytype="release"):
    """Download cover art for a release. The coverart file to download
    is specified by the `coverid` argument.

    If `size` is not specified, download the largest copy present, which can be
    very large.

    If an error occurs then a :class:`~musicbrainzngs.ResponseError`
    will be raised with one of the following HTTP codes:

    * 400: `Releaseid` is not a valid UUID or `coverid` is invalid
    * 404: No release exists with an MBID of `releaseid`
    * 503: Ratelimit exceeded

    :param coverid: ``front``, ``back`` or a number from the listing obtained with
                    :meth:`get_image_list`
    :type coverid: int or str

    :param size: "250", "500", "1200" or None. If it is None, the largest
                 available picture will be downloaded. If the image originally
                 uploaded to the Cover Art Archive was smaller than the
                 requested size, only the original image will be returned.
    :type size: str or None

    :param entitytype: The type of entity for which to download the cover art.
                       This is either ``release`` or ``release-group``.
    :type entitytype: str
    :return: The binary image data
    :type: str
    """
    if isinstance(coverid, int):
        coverid = "%d" % (coverid, )
    if isinstance(size, int):
        size = "%d" % (size, )
    return _caa_request(mbid, coverid, size=size, entitytype=entitytype)
