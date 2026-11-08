import sys

from . import py311

# Distribution.origin was added in Python 3.13, so a provider built on
# importlib.metadata cannot supply it on every supported Python and must
# not be faulted for its absence.
exempt = frozenset({'origin'}) if sys.version_info < (3, 13) else frozenset()


def required(protocol):
    """
    The members a protocol expects of a provider on this Python.
    """
    return set(py311.protocol_attrs(protocol)) - exempt


def tolerant_conforms(instance, protocol):  # pragma: no cover
    """
    Determine conformance, overlooking the exempt members.

    Consults the type rather than the instance, which also keeps
    isinstance() from evaluating property members on Python 3.11
    (https://github.com/python/cpython/issues/102433).
    """
    return all(hasattr(type(instance), attr) for attr in required(protocol))


conforms = tolerant_conforms if sys.version_info < (3, 13) else isinstance
