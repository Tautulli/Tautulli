import json
from hashlib import sha1

from cloudinary.cache.adapter.cache_adapter import CacheAdapter
from cloudinary.cache.storage.key_value_storage import KeyValueStorage
from cloudinary.utils import check_property_enabled


class KeyValueCacheAdapter(CacheAdapter):
    """
    A cache adapter for a key-value storage type
    """
    def __init__(self, storage):
        """Create a new adapter for the provided storage interface"""
        if not isinstance(storage, KeyValueStorage):
            raise ValueError("An instance of valid KeyValueStorage must be provided")

        self._key_value_storage = storage

    @property
    def enabled(self):
        return self._key_value_storage is not None

    @check_property_enabled
    def get(self, public_id, type, resource_type, transformation, format):
        key = self.generate_cache_key(public_id, type, resource_type, transformation, format)
        value_str = self._key_value_storage.get(key)
        return json.loads(value_str) if value_str else value_str

    @check_property_enabled
    def set(self, public_id, type, resource_type, transformation, format, value):
        key = self.generate_cache_key(public_id, type, resource_type, transformation, format)
        return self._key_value_storage.set(key, json.dumps(value))

    @check_property_enabled
    def delete(self, public_id, type, resource_type, transformation, format):
        return self._key_value_storage.delete(
            self.generate_cache_key(public_id, type, resource_type, transformation, format)
        )

    @check_property_enabled
    def flush_all(self):
        return self._key_value_storage.clear()

    @staticmethod
    def generate_cache_key(public_id, type, resource_type, transformation, format):
        """
        Generates key-value storage key from parameters

        :param public_id:       The public ID of the resource
        :param type:            The storage type
        :param resource_type:   The type of the resource
        :param transformation:  The transformation string
        :param format:          The format of the resource

        :return: Resulting cache key
        """

        valid_params = [p for p in [public_id, type, resource_type, transformation, format] if p]

        return sha1("/".join(valid_params).encode("utf-8")).hexdigest()
