"""
Make sure threads don't leak.

Run in an isolated subprocess by ``test_server.py``, to ensure parallelism of
any sort don't cause problems.
"""

import sys
import threading
import time

from cheroot.server import Gateway, HTTPServer
from cheroot.testing import (
    ANY_INTERFACE_IPV4,
    EPHEMERAL_PORT,
    SUCCESSFUL_SUBPROCESS_EXIT,
)


SLEEP_INTERVAL = 0.2


def check_for_leaks():
    """Exit with special success code if no threads were leaked."""
    before_serv = threading.active_count()
    for _ in range(5):
        httpserver = HTTPServer(
            bind_addr=(ANY_INTERFACE_IPV4, EPHEMERAL_PORT),
            gateway=Gateway,
        )
        with httpserver._run_in_thread():
            time.sleep(SLEEP_INTERVAL)

    leaked_threads = threading.active_count() - before_serv
    if leaked_threads == 0:
        sys.exit(SUCCESSFUL_SUBPROCESS_EXIT)
    else:
        # We leaked a thread:
        sys.exit(f'Number of leaked threads: {leaked_threads}')


if __name__ == '__main__':
    check_for_leaks()
