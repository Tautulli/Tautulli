from abc import ABCMeta, abstractmethod


class CacheAdapter:
    """
    CacheAdapter Abstract Base Class
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get(self, public_id, type, resource_type, transformation, format):
        """
        Gets value specified by parameters

        :param public_id:       The public ID of the resource
        :param type:            The storage type
        :param resource_type:   The type of the resource
        :param transformation:  The transformation string
        :param format:          The format of the resource

        :return: None|mixed value, None if not found
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, public_id, type, resource_type, transformation, format, value):
        """
        Sets value specified by parameters

        :param public_id:       The public ID of the resource
        :param type:            The storage type
        :param resource_type:   The type of the resource
        :param transformation:  The transformation string
        :param format:          The format of the resource
        :param value:           The value to set

        :return: bool True on success or False on failure
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, public_id, type, resource_type, transformation, format):
        """
        Deletes entry specified by parameters

        :param public_id:       The public ID of the resource
        :param type:            The storage type
        :param resource_type:   The type of the resource
        :param transformation:  The transformation string
        :param format:          The format of the resource

        :return: bool True on success or False on failure
        """
        raise NotImplementedError

    @abstractmethod
    def flush_all(self):
        """
        Flushes all entries from cache

        :return: bool True on success or False on failure
        """
        raise NotImplementedError
