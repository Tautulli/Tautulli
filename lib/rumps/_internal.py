# -*- coding: utf-8 -*-

from __future__ import print_function

import inspect
import traceback

import Foundation

from . import compat
from . import exceptions


def require_string(*objs):
    for obj in objs:
        if not isinstance(obj, compat.string_types):
            raise TypeError(
                'a string is required but given {0}, a {1}'.format(obj, type(obj).__name__)
            )


def require_string_or_none(*objs):
    for obj in objs:
        if not(obj is None or isinstance(obj, compat.string_types)):
            raise TypeError(
                'a string or None is required but given {0}, a {1}'.format(obj, type(obj).__name__)
            )


def call_as_function_or_method(func, *args, **kwargs):
    # The idea here is that when using decorators in a class, the functions passed are not bound so we have to
    # determine later if the functions we have (those saved as callbacks) for particular events need to be passed
    # 'self'.
    #
    # This works for an App subclass method or a standalone decorated function. Will attempt to find function as
    # a bound method of the App instance. If it is found, use it, otherwise simply call function.
    from . import rumps
    try:
        app = getattr(rumps.App, '*app_instance')
    except AttributeError:
        pass
    else:
        for name, method in inspect.getmembers(app, predicate=inspect.ismethod):
            if method.__func__ is func:
                return method(*args, **kwargs)
    return func(*args, **kwargs)


def guard_unexpected_errors(func):
    """Decorator to be used in PyObjC callbacks where an error bubbling up
    would cause a crash. Instead of crashing, print the error to stderr and
    prevent passing to PyObjC layer.

    For Python 3, print the exception using chaining. Accomplished by setting
    the cause of :exc:`rumps.exceptions.InternalRumpsError` to the exception.

    For Python 2, emulate exception chaining by printing the original exception
    followed by :exc:`rumps.exceptions.InternalRumpsError`.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            internal_error = exceptions.InternalRumpsError(
                'an unexpected error occurred within an internal callback'
            )
            if compat.PY2:
                import sys
                traceback.print_exc()
                print('\nThe above exception was the direct cause of the following exception:\n', file=sys.stderr)
                traceback.print_exception(exceptions.InternalRumpsError, internal_error, None)
            else:
                internal_error.__cause__ = e
                traceback.print_exception(exceptions.InternalRumpsError, internal_error, None)

    return wrapper


def string_to_objc(x):
    if isinstance(x, compat.binary_type):
        return Foundation.NSData.alloc().initWithData_(x)
    elif isinstance(x, compat.string_types):
        return Foundation.NSString.alloc().initWithString_(x)
    else:
        raise TypeError(
            "expected a string or a bytes-like object but provided %s, "
            "having type '%s'" % (
                x,
                type(x).__name__
            )
        )
