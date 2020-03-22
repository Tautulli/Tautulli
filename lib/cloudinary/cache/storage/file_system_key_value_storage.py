import glob
from tempfile import gettempdir

import os

import errno

from cloudinary.cache.storage.key_value_storage import KeyValueStorage


class FileSystemKeyValueStorage(KeyValueStorage):
    """File-based key-value storage"""
    _item_ext = ".cldci"

    def __init__(self, root_path):
        """
        Create a new Storage object.

        All files will be stored under the root_path location

        :param root_path: The base folder for all storage files
        """
        if root_path is None:
            root_path = gettempdir()

        if not os.path.isdir(root_path):
            os.makedirs(root_path)

        self._root_path = root_path

    def get(self, key):
        if not self._exists(key):
            return None

        with open(self._get_key_full_path(key), 'r') as f:
            value = f.read()

        return value

    def set(self, key, value):
        with open(self._get_key_full_path(key), 'w') as f:
            f.write(value)

        return True

    def delete(self, key):
        try:
            os.remove(self._get_key_full_path(key))
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT - no such file or directory
                raise  # re-raise exception if a different error occurred

        return True

    def clear(self):
        for cache_item_path in glob.iglob(os.path.join(self._root_path, '*' + self._item_ext)):
            os.remove(cache_item_path)

        return True

    def _get_key_full_path(self, key):
        """
        Generate the file path for the key

        :param key: The key

        :return: The absolute path of the value file associated with the key
        """
        return os.path.join(self._root_path, key + self._item_ext)

    def _exists(self, key):
        """
        Indicate whether key exists

        :param key: The key

        :return: bool True if the file for the given key exists
        """
        return os.path.isfile(self._get_key_full_path(key))
