from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, cast

import importlib_metadata

from ..compat import py312

if TYPE_CHECKING:
    import email.message
    import importlib.metadata

    from .. import _adapters
    from .._meta import SimplePath


def dist(
    dist: importlib_metadata.Distribution | importlib.metadata.Distribution,
) -> importlib_metadata.Distribution:
    """
    Ensure dist is an :class:`importlib_metadata.Distribution`.

    >>> import importlib.metadata
    >>> stdlib = importlib.metadata.PathDistribution('foo')
    >>> type(stdlib)
    <class 'importlib.metadata.PathDistribution'>
    >>> local = dist(stdlib)
    >>> type(local)
    <class 'importlib_metadata.PathDistribution'>

    A provider of its own Distribution subclass is passed through, as
    long as it implements the interface consumers expect.

    >>> class CustomDist(importlib.metadata.Distribution):
    ...     def read_text(self, name):
    ...         return
    ...     def locate_file(self, name):
    ...         return
    >>> custom = CustomDist()
    >>> dist(custom) is custom
    True

    One that doesn't is passed through too, but names what it omits.

    >>> class Incomplete:
    ...     def read_text(self, name):
    ...         return
    >>> import pytest
    >>> with pytest.warns(UserWarning, match="is missing at, discover"):
    ...     local = dist(Incomplete())
    >>> local is not None
    True
    """
    if isinstance(dist, importlib_metadata.Distribution):
        return dist

    # only a foreign dist gets this far, so defer the cost of the import
    # (python/cpython#109829)
    import importlib.metadata

    if isinstance(dist, importlib.metadata.PathDistribution):
        return importlib_metadata.PathDistribution(cast('SimplePath', dist._path))
    # Warn on what the interface requires and the class omits, rather than
    # on the class not being one of ours; a provider can act on the former.
    # Also tolerates pytest having replaced importlib_metadata, as the
    # replaced class still conforms.
    if not py312.conforms(dist, importlib_metadata.IDistribution):
        warnings.warn(
            f"Distribution subclass {dist.__class__} is missing "
            f"{', '.join(unimplemented(dist))}"
        )
    return cast('importlib_metadata.Distribution', dist)


def unimplemented(dist) -> list[str]:
    """
    The members IDistribution requires that dist's class doesn't supply.
    """
    required = py312.required(importlib_metadata.IDistribution)
    return sorted(attr for attr in required if not hasattr(type(dist), attr))


def message(
    input: _adapters.Message | email.message.Message,
) -> _adapters.Message:
    """
    Ensure a message is adapted to an importlib_metadata.Message.

    >>> import email.message
    >>> stdlib = email.message.Message()
    >>> local = message(stdlib)
    >>> type(local)
    <class 'importlib_metadata._adapters.Message'>
    """
    # deferred for performance (python/cpython#109829)
    from .. import _adapters

    if isinstance(input, _adapters.Message):
        return input
    return _adapters.Message(input)


def package_path(
    input: importlib_metadata.PackagePath | importlib.metadata.PackagePath,
) -> importlib_metadata.PackagePath:
    """
    Ensure a package path is adapted to an importlib_metadata.PackagePath.

    >>> import importlib.metadata
    >>> stdlib = importlib.metadata.PackagePath('foo')
    >>> type(stdlib)
    <class 'importlib.metadata.PackagePath'>
    >>> local = package_path(stdlib)
    >>> type(local)
    <class 'importlib_metadata.PackagePath'>
    """
    if isinstance(input, importlib_metadata.PackagePath):
        return input
    replacement = importlib_metadata.PackagePath(input)
    vars(replacement).update(vars(input))
    return replacement
