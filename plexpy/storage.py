# -*- coding: utf-8 -*-

# This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

"""Storage capacity of the filesystems used by the Plex libraries.

Only the library folders reported by the Plex server are inspected,
optionally rewritten by the user configured path mappings. Capacity is
read from the operating system, the media folders are never scanned.
"""

import os
import shutil
import threading
import time

import plexpy
from plexpy import helpers
from plexpy import logger
from plexpy import pmsconnect


# Filesystem capacity does not change quickly, so the lookup is cached to
# keep the homepage off the filesystem (and off the Plex server) on every
# refresh.
CACHE_SECONDS = 300

_CACHE = {'timestamp': 0, 'storage': []}
_CACHE_LOCK = threading.Lock()


def clear_cache():
    """ Discard the cached storage info so the next lookup is refreshed. """
    with _CACHE_LOCK:
        _CACHE['timestamp'] = 0
        _CACHE['storage'] = []


def get_mount_point(path):
    """
    Return the mount point (or drive root) containing the path.

    Output: str
    """
    path = os.path.abspath(path)

    while not os.path.ismount(path):
        parent = os.path.dirname(path)
        if parent == path:
            # Reached the root without finding a mount point
            break
        path = parent

    return path


def get_filesystem_id(path):
    """
    Return an identifier which is unique per filesystem.

    The device id is used where it is available so that multiple library
    folders on the same filesystem are only counted once. Falls back to
    the mount point for platforms which do not report a device id.

    Output: str
    """
    try:
        device_id = os.stat(path).st_dev
    except OSError:
        device_id = 0

    if device_id:
        return str(device_id)

    return os.path.normcase(get_mount_point(path))


def get_path_mappings():
    """
    Return the configured path mappings as (plex_path, local_path) tuples.

    Output: list
    """
    mappings = []

    for mapping in plexpy.CONFIG.STORAGE_PATH_MAPPINGS:
        plex_path, _, local_path = mapping.partition('|')
        plex_path, local_path = plex_path.strip(), local_path.strip()

        if plex_path and local_path:
            mappings.append((plex_path, local_path))

    # Longest Plex path first so that the most specific mapping wins
    return sorted(mappings, key=lambda mapping: len(mapping[0]), reverse=True)


def _normalize_path(path):
    """ Normalize a path for comparison across platforms. """
    return path.replace('\\', '/').rstrip('/').lower()


def map_path(path):
    """
    Rewrite a Plex library path to a path accessible to Tautulli.

    Returns the path unchanged when no mapping applies.

    Output: str
    """
    for plex_path, local_path in get_path_mappings():
        prefix = _normalize_path(plex_path)
        if not prefix:
            continue

        normalized = _normalize_path(path)
        if normalized != prefix and not normalized.startswith(prefix + '/'):
            continue

        remainder = path.replace('\\', '/').rstrip('/')[len(plex_path.rstrip('/\\')):].strip('/')
        if remainder:
            return os.path.join(local_path, *remainder.split('/'))
        return local_path

    return path


def get_storage_info(path):
    """
    Return the filesystem capacity information for a single path.

    Never raises. A path which cannot be inspected is reported with a
    status of 'unavailable' so that a single unreachable library folder
    cannot break the homepage.

    Output: dict
    """
    storage_info = {'path': path,
                    'mount_point': None,
                    'total_bytes': None,
                    'used_bytes': None,
                    'free_bytes': None,
                    'percent_used': None,
                    'status': 'unavailable'
                    }

    if not path:
        return storage_info

    try:
        real_path = os.path.realpath(path)

        if not os.path.exists(real_path):
            # Plex may be running on a different machine or in a different
            # container than Tautulli, so the library folders it reports are
            # not necessarily visible from here.
            logger.debug("Tautulli Storage :: Library path is not accessible: %s." % path)
            return storage_info

        mount_point = get_mount_point(real_path)
        usage = shutil.disk_usage(mount_point)

    except (OSError, ValueError) as e:
        logger.warn("Tautulli Storage :: Unable to get storage info for %s: %s." % (path, e))
        return storage_info

    storage_info['mount_point'] = mount_point
    storage_info['total_bytes'] = usage.total
    storage_info['used_bytes'] = usage.used
    storage_info['free_bytes'] = usage.free
    storage_info['percent_used'] = round(usage.used / usage.total * 100, 1) if usage.total else 0
    storage_info['status'] = 'ok'

    return storage_info


def get_library_storage(refresh=False):
    """
    Return the storage capacity of each filesystem used by the Plex libraries.

    Libraries sharing a filesystem are grouped together so that the
    filesystem is only counted once. Library folders which cannot be
    inspected are grouped into a single unavailable entry.

    Output: list
    """
    with _CACHE_LOCK:
        if not refresh and _CACHE['timestamp'] and \
                time.time() - _CACHE['timestamp'] < CACHE_SECONDS:
            return _CACHE['storage']

        storage = _get_library_storage()

        _CACHE['timestamp'] = time.time()
        _CACHE['storage'] = storage

        return storage


def _get_library_storage():
    try:
        server_libraries = pmsconnect.PmsConnect().get_server_children()
    except Exception as e:
        logger.warn("Tautulli Storage :: Unable to retrieve libraries list: %s." % e)
        return []

    if not server_libraries:
        return []

    filesystems = {}
    unavailable = None

    for library in server_libraries.get('libraries_list', []):
        section = {'section_id': helpers.cast_to_int(library['section_id']),
                   'section_name': library['section_name'],
                   'section_type': library['section_type']
                   }

        for location in library.get('section_locations', []):
            storage_info = get_storage_info(map_path(location))

            if storage_info['status'] == 'ok':
                filesystem_id = get_filesystem_id(storage_info['mount_point'])

                if filesystem_id not in filesystems:
                    filesystems[filesystem_id] = _new_entry(storage_info)

                entry = filesystems[filesystem_id]

            else:
                if unavailable is None:
                    unavailable = _new_entry(storage_info)

                entry = unavailable

            if location not in entry['paths']:
                entry['paths'].append(location)
            if section not in entry['libraries']:
                entry['libraries'].append(section)

    storage = sorted(filesystems.values(), key=lambda entry: entry['mount_point'])

    if unavailable is not None:
        storage.append(unavailable)

    return storage


def _new_entry(storage_info):
    entry = dict(storage_info, paths=[], libraries=[])
    del entry['path']
    return entry
