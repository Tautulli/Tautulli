from abc import ABCMeta, abstractmethod


class KeyValueStorage:
    """
    A simple key-value storage abstract base class
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get(self, key):
        """
        Get a value identified by the given key

        :param key: The unique identifier

        :return: The value identified by key or None if no value was found
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key, value):
        """
        Store the value identified by the key

        :param key: The unique identifier
        :param value: Value to store

        :return: bool True on success or False on failure
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key):
        """
        Deletes item by key

        :param key: The unique identifier

        :return: bool True on success or False on failure
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self):
        """
        Clears all entries

        :return: bool True on success or False on failure
        """
        raise NotImplementedError
