"""Local pytest plugin.

Contains hooks, which are tightly bound to the Cheroot framework
itself, useless for end-users' app testing.
"""

import pytest


pytest_version = tuple(map(int, pytest.__version__.split('.')))


def pytest_load_initial_conftests(early_config, parser, args):
    """Drop unfilterable warning ignores."""
    if pytest_version < (6, 2, 0):
        return

    # pytest>=6.2.0 under Python 3.8:
    # Refs:
    # * https://docs.pytest.org/en/stable/usage.html#unraisable
    # * https://github.com/pytest-dev/pytest/issues/5299
    early_config._inicache['filterwarnings'].extend((
        'ignore:Exception in thread CP Server Thread-:'
        'pytest.PytestUnhandledThreadExceptionWarning:_pytest.threadexception',
        'ignore:Exception in thread Thread-:'
        'pytest.PytestUnhandledThreadExceptionWarning:_pytest.threadexception',
        'ignore:Exception ignored in. '
        '<socket.socket fd=-1, family=AddressFamily.AF_INET, '
        'type=SocketKind.SOCK_STREAM, proto=.:'
        'pytest.PytestUnraisableExceptionWarning:_pytest.unraisableexception',
        'ignore:Exception ignored in. '
        '<socket.socket fd=-1, family=AddressFamily.AF_INET6, '
        'type=SocketKind.SOCK_STREAM, proto=.:'
        'pytest.PytestUnraisableExceptionWarning:_pytest.unraisableexception',
        'ignore:Exception ignored in. '
        '<socket.socket fd=-1, family=AF_INET, '
        'type=SocketKind.SOCK_STREAM, proto=.:'
        'pytest.PytestUnraisableExceptionWarning:_pytest.unraisableexception',
        'ignore:Exception ignored in. '
        '<socket.socket fd=-1, family=AF_INET6, '
        'type=SocketKind.SOCK_STREAM, proto=.:'
        'pytest.PytestUnraisableExceptionWarning:_pytest.unraisableexception',
    ))
