#!/usr/bin/env python


class TwitterError(Exception):
    """Base class for Twitter errors"""

    @property
    def message(self):
        '''Returns the first argument used to construct this error.'''
        return self.args[0]


class PythonTwitterDeprecationWarning(DeprecationWarning):
    """Base class for python-twitter deprecation warnings"""
    pass


class PythonTwitterDeprecationWarning330(PythonTwitterDeprecationWarning):
    """Warning for features to be removed in version 3.3.0"""
    pass


class PythonTwitterDeprecationWarning340(PythonTwitterDeprecationWarning):
    """Warning for features to be removed in version 3.4.0"""
    pass
