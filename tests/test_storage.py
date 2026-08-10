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

"""Tests for the Plex library storage capacity lookup.

Run from the repository root with:  python -m unittest discover tests
"""

import collections
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, 'lib'))

import plexpy
from plexpy import storage


DiskUsage = collections.namedtuple('DiskUsage', ['total', 'used', 'free'])


class FakeConfig(object):
    def __init__(self, storage_path_mappings=None):
        self.STORAGE_PATH_MAPPINGS = storage_path_mappings or []


class FakeFilesystem(object):
    """A set of mount points, each with its own device id and capacity."""

    def __init__(self, mounts):
        # mounts: {mount_point: (device_id, total, used, free)}
        self.mounts = mounts

    def mount_point(self, path):
        matches = [mount for mount in self.mounts if self._contains(mount, path)]
        if not matches:
            raise OSError("No such file or directory: %s" % path)
        return max(matches, key=len)

    def exists(self, path):
        return any(self._contains(mount, path) for mount in self.mounts)

    def stat(self, path):
        device_id, _, _, _ = self.mounts[self.mount_point(path)]
        return mock.Mock(st_dev=device_id)

    def disk_usage(self, path):
        _, total, used, free = self.mounts[self.mount_point(path)]
        return DiskUsage(total, used, free)

    @staticmethod
    def _contains(mount, path):
        mount = mount.replace('\\', '/').rstrip('/').lower()
        path = path.replace('\\', '/').rstrip('/').lower()
        return path == mount or path.startswith(mount + '/')


class FakeOsPath(object):
    """os.path with the filesystem lookups redirected to the fake filesystem."""

    def __init__(self, filesystem):
        self._filesystem = filesystem

    def __getattr__(self, name):
        return getattr(os.path, name)

    def realpath(self, path):
        return path

    def exists(self, path):
        return self._filesystem.exists(path)


class FakeOs(object):
    def __init__(self, filesystem):
        self._filesystem = filesystem
        self.path = FakeOsPath(filesystem)

    def __getattr__(self, name):
        return getattr(os, name)

    def stat(self, path):
        return self._filesystem.stat(path)


class FakeShutil(object):
    def __init__(self, filesystem):
        self._filesystem = filesystem

    def disk_usage(self, path):
        return self._filesystem.disk_usage(path)


def library(section_id, section_name, section_type, locations):
    return {'section_id': str(section_id),
            'section_name': section_name,
            'section_type': section_type,
            'agent': '',
            'thumb': '',
            'art': '',
            'section_locations': locations
            }


def normalize(path):
    return path.replace('\\', '/') if path else path


class StorageTestCase(unittest.TestCase):
    """Base class patching out the logger, the config and the filesystem."""

    filesystem = FakeFilesystem({})
    path_mappings = []

    def setUp(self):
        storage.clear_cache()
        self.addCleanup(storage.clear_cache)

        patches = [
            mock.patch.object(storage, 'logger', mock.Mock()),
            mock.patch.object(plexpy, 'CONFIG', FakeConfig(self.path_mappings)),
            mock.patch.object(storage, 'os', FakeOs(self.filesystem)),
            mock.patch.object(storage, 'shutil', FakeShutil(self.filesystem)),
            mock.patch.object(storage, 'get_mount_point', side_effect=self.filesystem.mount_point),
        ]

        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def get_library_storage(self, libraries):
        pms_connect = mock.Mock()
        pms_connect.return_value.get_server_children.return_value = {
            'libraries_count': str(len(libraries)),
            'title': 'Plex Library',
            'libraries_list': libraries
        }

        with mock.patch.object(storage.pmsconnect, 'PmsConnect', pms_connect):
            return storage.get_library_storage(refresh=True)


class TestSingleFilesystem(StorageTestCase):
    filesystem = FakeFilesystem({'/mnt/media': (2049, 1000, 800, 200)})

    def test_one_library_on_one_filesystem(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/media/movies'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'ok')
        self.assertEqual(result[0]['mount_point'], '/mnt/media')
        self.assertEqual(result[0]['total_bytes'], 1000)
        self.assertEqual(result[0]['used_bytes'], 800)
        self.assertEqual(result[0]['free_bytes'], 200)
        self.assertEqual(result[0]['percent_used'], 80.0)
        self.assertEqual(result[0]['paths'], ['/mnt/media/movies'])
        self.assertEqual([lib['section_name'] for lib in result[0]['libraries']], ['Movies'])

    def test_multiple_libraries_on_the_same_filesystem_are_not_double_counted(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/media/movies']),
            library(2, 'TV Shows', 'show', ['/mnt/media/tv']),
            library(3, 'Music', 'artist', ['/mnt/media/music'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['total_bytes'], 1000)
        self.assertEqual(result[0]['paths'],
                         ['/mnt/media/movies', '/mnt/media/tv', '/mnt/media/music'])
        self.assertEqual([lib['section_name'] for lib in result[0]['libraries']],
                         ['Movies', 'TV Shows', 'Music'])

    def test_multiple_locations_for_a_single_library(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/media/movies', '/mnt/media/movies-4k'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['libraries']), 1)
        self.assertEqual(result[0]['paths'], ['/mnt/media/movies', '/mnt/media/movies-4k'])

    def test_library_without_locations_is_ignored(self):
        result = self.get_library_storage([
            library(1, 'Live TV', 'live', [])
        ])

        self.assertEqual(result, [])

    def test_section_id_is_cast_to_an_integer(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/media/movies'])
        ])

        self.assertEqual(result[0]['libraries'][0]['section_id'], 1)


class TestMultipleFilesystems(StorageTestCase):
    filesystem = FakeFilesystem({'/mnt/storage1': (2049, 1000, 250, 750),
                                 '/mnt/storage2': (2050, 2000, 1000, 1000)})

    def test_libraries_across_multiple_filesystems(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/storage1/movies']),
            library(2, 'TV Shows', 'show', ['/mnt/storage2/tv'])
        ])

        self.assertEqual(len(result), 2)
        self.assertEqual([entry['mount_point'] for entry in result],
                         ['/mnt/storage1', '/mnt/storage2'])
        self.assertEqual([entry['percent_used'] for entry in result], [25.0, 50.0])

    def test_a_library_spanning_two_filesystems_is_reported_once_per_filesystem(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/storage1/movies', '/mnt/storage2/movies'])
        ])

        self.assertEqual(len(result), 2)
        for entry in result:
            self.assertEqual([lib['section_name'] for lib in entry['libraries']], ['Movies'])


class TestSameDeviceDifferentMountPoints(StorageTestCase):
    """A bind mount exposes one filesystem under two paths."""

    filesystem = FakeFilesystem({'/mnt/media': (2049, 1000, 800, 200),
                                 '/srv/media': (2049, 1000, 800, 200)})

    def test_bind_mounted_paths_are_counted_once(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/media/movies']),
            library(2, 'TV Shows', 'show', ['/srv/media/tv'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['total_bytes'], 1000)
        self.assertEqual(len(result[0]['libraries']), 2)


class TestWindowsPaths(StorageTestCase):
    filesystem = FakeFilesystem({'D:\\': (1, 1000, 500, 500),
                                 'E:\\': (2, 2000, 400, 1600),
                                 '\\\\nas\\media': (3, 4000, 3000, 1000)})

    def test_separate_drive_letters_are_separate_filesystems(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['D:\\Movies']),
            library(2, 'TV Shows', 'show', ['E:\\TV'])
        ])

        self.assertEqual(len(result), 2)
        self.assertEqual(sorted(entry['mount_point'] for entry in result), ['D:\\', 'E:\\'])

    def test_two_libraries_on_the_same_drive_are_counted_once(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['D:\\Movies']),
            library(2, 'Home Videos', 'movie', ['D:\\Videos'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['total_bytes'], 1000)

    def test_unc_network_path(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['\\\\nas\\media\\movies'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'ok')
        self.assertEqual(result[0]['mount_point'], '\\\\nas\\media')
        self.assertEqual(result[0]['percent_used'], 75.0)


class TestUnavailablePaths(StorageTestCase):
    filesystem = FakeFilesystem({'/mnt/media': (2049, 1000, 800, 200)})

    def test_inaccessible_path_is_reported_as_unavailable(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/does/not/exist'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'unavailable')
        self.assertIsNone(result[0]['mount_point'])
        self.assertIsNone(result[0]['total_bytes'])
        self.assertEqual(result[0]['paths'], ['/does/not/exist'])

    def test_plex_in_a_different_filesystem_namespace(self):
        """Plex reports its own paths, which Tautulli cannot necessarily see."""
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/media/movies']),
            library(2, 'TV Shows', 'show', ['/media/tv'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'unavailable')
        self.assertEqual(result[0]['paths'], ['/media/movies', '/media/tv'])
        self.assertEqual(len(result[0]['libraries']), 2)

    def test_accessible_filesystems_are_still_reported(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/mnt/media/movies']),
            library(2, 'TV Shows', 'show', ['/media/tv'])
        ])

        self.assertEqual([entry['status'] for entry in result], ['ok', 'unavailable'])

    def test_unavailable_statistics_do_not_raise(self):
        with mock.patch.object(storage.shutil, 'disk_usage', side_effect=OSError("boom")):
            result = self.get_library_storage([
                library(1, 'Movies', 'movie', ['/mnt/media/movies'])
            ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'unavailable')

    def test_permission_error_does_not_raise(self):
        with mock.patch.object(storage.shutil, 'disk_usage', side_effect=PermissionError("denied")):
            storage_info = storage.get_storage_info('/mnt/media/movies')

        self.assertEqual(storage_info['status'], 'unavailable')

    def test_empty_path(self):
        self.assertEqual(storage.get_storage_info('')['status'], 'unavailable')

    def test_zero_size_filesystem_does_not_divide_by_zero(self):
        with mock.patch.object(storage.shutil, 'disk_usage', return_value=DiskUsage(0, 0, 0)):
            storage_info = storage.get_storage_info('/mnt/media/movies')

        self.assertEqual(storage_info['status'], 'ok')
        self.assertEqual(storage_info['percent_used'], 0)

    def test_unreachable_plex_server_returns_no_storage(self):
        pms_connect = mock.Mock()
        pms_connect.return_value.get_server_children.side_effect = IOError("connection refused")

        with mock.patch.object(storage.pmsconnect, 'PmsConnect', pms_connect):
            self.assertEqual(storage.get_library_storage(refresh=True), [])

    def test_no_libraries_returns_no_storage(self):
        pms_connect = mock.Mock()
        pms_connect.return_value.get_server_children.return_value = []

        with mock.patch.object(storage.pmsconnect, 'PmsConnect', pms_connect):
            self.assertEqual(storage.get_library_storage(refresh=True), [])


class TestPathMappings(StorageTestCase):
    filesystem = FakeFilesystem({'/mnt/plex': (2049, 1000, 800, 200)})
    path_mappings = ['/media|/mnt/plex']

    def test_mapped_path_is_resolved(self):
        result = self.get_library_storage([
            library(1, 'Movies', 'movie', ['/media/movies'])
        ])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['status'], 'ok')
        self.assertEqual(result[0]['mount_point'], '/mnt/plex')
        # The card shows the path as Plex reports it
        self.assertEqual(result[0]['paths'], ['/media/movies'])

    def test_unmapped_path_remains_unavailable(self):
        result = self.get_library_storage([
            library(1, 'Photos', 'photo', ['/pictures/photos'])
        ])

        self.assertEqual(result[0]['status'], 'unavailable')


class TestMapPath(unittest.TestCase):
    def map_path(self, path, mappings):
        with mock.patch.object(plexpy, 'CONFIG', FakeConfig(mappings)):
            return normalize(storage.map_path(path))

    def test_no_mappings_returns_the_path_unchanged(self):
        self.assertEqual(self.map_path('/media/movies', []), '/media/movies')

    def test_posix_mapping(self):
        self.assertEqual(self.map_path('/media/movies', ['/media|/mnt/plex']),
                         '/mnt/plex/movies')

    def test_exact_match(self):
        self.assertEqual(self.map_path('/media', ['/media|/mnt/plex']), '/mnt/plex')

    def test_trailing_separators_are_ignored(self):
        self.assertEqual(self.map_path('/media/movies', ['/media/|/mnt/plex/']),
                         '/mnt/plex/movies')

    def test_partial_directory_name_is_not_matched(self):
        self.assertEqual(self.map_path('/mediaserver/movies', ['/media|/mnt/plex']),
                         '/mediaserver/movies')

    def test_the_most_specific_mapping_wins(self):
        mappings = ['/media|/mnt/plex', '/media/movies|/mnt/movies']
        self.assertEqual(self.map_path('/media/movies/action', mappings),
                         '/mnt/movies/action')
        self.assertEqual(self.map_path('/media/tv', mappings), '/mnt/plex/tv')

    def test_windows_to_posix_mapping(self):
        self.assertEqual(self.map_path('D:\\Movies\\Action', ['D:\\Movies|/mnt/movies']),
                         '/mnt/movies/Action')

    def test_posix_to_windows_mapping(self):
        self.assertEqual(self.map_path('/media/movies', ['/media|D:\\Media']),
                         'D:/Media/movies')

    def test_unc_mapping(self):
        self.assertEqual(self.map_path('/media/movies', ['/media|\\\\nas\\media']),
                         '//nas/media/movies')

    def test_malformed_mappings_are_ignored(self):
        for mapping in ('', '/media', '|/mnt/plex', '/media|'):
            self.assertEqual(self.map_path('/media/movies', [mapping]), '/media/movies')


class TestCaching(StorageTestCase):
    filesystem = FakeFilesystem({'/mnt/media': (2049, 1000, 800, 200)})

    def test_the_plex_server_is_not_queried_again_within_the_cache_window(self):
        pms_connect = mock.Mock()
        pms_connect.return_value.get_server_children.return_value = {
            'libraries_list': [library(1, 'Movies', 'movie', ['/mnt/media/movies'])]
        }

        with mock.patch.object(storage.pmsconnect, 'PmsConnect', pms_connect):
            storage.get_library_storage(refresh=True)
            storage.get_library_storage()
            storage.get_library_storage()

        self.assertEqual(pms_connect.return_value.get_server_children.call_count, 1)

    def test_clear_cache_forces_a_new_lookup(self):
        pms_connect = mock.Mock()
        pms_connect.return_value.get_server_children.return_value = {
            'libraries_list': [library(1, 'Movies', 'movie', ['/mnt/media/movies'])]
        }

        with mock.patch.object(storage.pmsconnect, 'PmsConnect', pms_connect):
            storage.get_library_storage()
            storage.clear_cache()
            storage.get_library_storage()

        self.assertEqual(pms_connect.return_value.get_server_children.call_count, 2)


class TestRealFilesystem(unittest.TestCase):
    """The mount point walk and the capacity lookup against the real OS."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.addCleanup(os.rmdir, self.temp_dir)

    def test_get_mount_point_returns_a_real_mount_point(self):
        mount_point = storage.get_mount_point(self.temp_dir)

        self.assertTrue(os.path.ismount(mount_point))
        self.assertTrue(normalize(self.temp_dir).lower().startswith(normalize(mount_point).lower()))

    def test_get_storage_info_for_an_existing_path(self):
        storage_info = storage.get_storage_info(self.temp_dir)

        self.assertEqual(storage_info['status'], 'ok')
        self.assertEqual(storage_info['path'], self.temp_dir)
        self.assertGreater(storage_info['total_bytes'], 0)
        self.assertGreaterEqual(storage_info['used_bytes'], 0)
        self.assertGreaterEqual(storage_info['free_bytes'], 0)
        self.assertLessEqual(storage_info['used_bytes'], storage_info['total_bytes'])
        self.assertGreaterEqual(storage_info['percent_used'], 0)
        self.assertLessEqual(storage_info['percent_used'], 100)

    def test_get_storage_info_for_a_missing_path(self):
        missing = os.path.join(self.temp_dir, 'does', 'not', 'exist')

        with mock.patch.object(storage, 'logger', mock.Mock()):
            storage_info = storage.get_storage_info(missing)

        self.assertEqual(storage_info['status'], 'unavailable')
        self.assertIsNone(storage_info['total_bytes'])

    def test_get_filesystem_id_is_stable_for_the_same_filesystem(self):
        sub_dir = os.path.join(self.temp_dir, 'library')
        os.mkdir(sub_dir)
        self.addCleanup(os.rmdir, sub_dir)

        self.assertEqual(storage.get_filesystem_id(self.temp_dir),
                         storage.get_filesystem_id(sub_dir))


if __name__ == '__main__':
    unittest.main()
