import copy

import collections

import cloudinary
from cloudinary.cache.adapter.cache_adapter import CacheAdapter
from cloudinary.utils import check_property_enabled


class ResponsiveBreakpointsCache:
    """
    Caches breakpoint values for image resources
    """
    def __init__(self, **cache_options):
        """
        Initialize the cache

        :param cache_options: Cache configuration options
        """

        self._cache_adapter = None

        cache_adapter = cache_options.get("cache_adapter")

        self.set_cache_adapter(cache_adapter)

    def set_cache_adapter(self, cache_adapter):
        """
        Assigns cache adapter

        :param cache_adapter: The cache adapter used to store and retrieve values

        :return: Returns True if the cache_adapter is valid
        """
        if cache_adapter is None or not isinstance(cache_adapter, CacheAdapter):
            return False

        self._cache_adapter = cache_adapter

        return True

    @property
    def enabled(self):
        """
        Indicates whether cache is enabled or not

        :return: Rrue if a _cache_adapter has been set
        """
        return self._cache_adapter is not None

    @staticmethod
    def _options_to_parameters(**options):
        """
        Extract the parameters required in order to calculate the key of the cache.

        :param options: Input options

        :return: A list of values used to calculate the cache key
        """
        options_copy = copy.deepcopy(options)
        transformation, _ = cloudinary.utils.generate_transformation_string(**options_copy)
        file_format = options.get("format", "")
        storage_type = options.get("type", "upload")
        resource_type = options.get("resource_type", "image")

        return storage_type, resource_type, transformation, file_format

    @check_property_enabled
    def get(self, public_id, **options):
        """
        Retrieve the breakpoints of a particular derived resource identified by the public_id and options

        :param public_id: The public ID of the resource
        :param options: The public ID of the resource

        :return: Array of responsive breakpoints, None if not found
        """
        params = self._options_to_parameters(**options)

        return self._cache_adapter.get(public_id, *params)

    @check_property_enabled
    def set(self, public_id, value, **options):
        """
        Set responsive breakpoints identified by public ID and options

        :param public_id: The public ID of the resource
        :param value:  Array of responsive breakpoints to set
        :param options: Additional options

        :return: True on success or False on failure
        """
        if not (isinstance(value, (list, tuple))):
            raise ValueError("A list of breakpoints is expected")

        storage_type, resource_type, transformation, file_format = self._options_to_parameters(**options)

        return self._cache_adapter.set(public_id, storage_type, resource_type, transformation, file_format, value)

    @check_property_enabled
    def delete(self, public_id, **options):
        """
        Delete responsive breakpoints identified by public ID and options

        :param public_id: The public ID of the resource
        :param options: Additional options

        :return: True on success or False on failure
        """
        params = self._options_to_parameters(**options)

        return self._cache_adapter.delete(public_id, *params)

    @check_property_enabled
    def flush_all(self):
        """
        Flush all entries from cache

        :return: True on success or False on failure
        """
        return self._cache_adapter.flush_all()


instance = ResponsiveBreakpointsCache()
