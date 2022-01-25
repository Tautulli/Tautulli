# Copyright (C) Dnspython Contributors, see LICENSE for text of ISC license

# This implementation of the immutable decorator is for python 3.6,
# which doesn't have Context Variables.  This implementation is somewhat
# costly for classes with slots, as it adds a __dict__ to them.


import inspect


class _Immutable:
    """Immutable mixin class"""

    # Note we MUST NOT have __slots__ as that causes
    #
    #    TypeError: multiple bases have instance lay-out conflict
    #
    # when we get mixed in with another class with slots.  When we
    # get mixed into something with slots, it effectively adds __dict__ to
    # the slots of the other class, which allows attribute setting to work,
    # albeit at the cost of the dictionary.

    def __setattr__(self, name, value):
        if not hasattr(self, '_immutable_init') or \
           self._immutable_init is not self:
            raise TypeError("object doesn't support attribute assignment")
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        if not hasattr(self, '_immutable_init') or \
           self._immutable_init is not self:
            raise TypeError("object doesn't support attribute assignment")
        else:
            super().__delattr__(name)


def _immutable_init(f):
    def nf(*args, **kwargs):
        try:
            # Are we already initializing an immutable class?
            previous = args[0]._immutable_init
        except AttributeError:
            # We are the first!
            previous = None
            object.__setattr__(args[0], '_immutable_init', args[0])
        try:
            # call the actual __init__
            f(*args, **kwargs)
        finally:
            if not previous:
                # If we started the initialzation, establish immutability
                # by removing the attribute that allows mutation
                object.__delattr__(args[0], '_immutable_init')
    nf.__signature__ = inspect.signature(f)
    return nf


def immutable(cls):
    if _Immutable in cls.__mro__:
        # Some ancestor already has the mixin, so just make sure we keep
        # following the __init__ protocol.
        cls.__init__ = _immutable_init(cls.__init__)
        if hasattr(cls, '__setstate__'):
            cls.__setstate__ = _immutable_init(cls.__setstate__)
        ncls = cls
    else:
        # Mixin the Immutable class and follow the __init__ protocol.
        class ncls(_Immutable, cls):

            @_immutable_init
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            if hasattr(cls, '__setstate__'):
                @_immutable_init
                def __setstate__(self, *args, **kwargs):
                    super().__setstate__(*args, **kwargs)

        # make ncls have the same name and module as cls
        ncls.__name__ = cls.__name__
        ncls.__qualname__ = cls.__qualname__
        ncls.__module__ = cls.__module__
    return ncls
