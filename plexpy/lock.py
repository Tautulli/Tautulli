# -*- coding: utf-8 -*-

# This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import object

import queue
import time
import threading

import plexpy
if plexpy.PYTHON_VERSION < 3:
    import logger
else:
    from plexpy import logger


class TimedLock(object):
    """
    Enforce request rate limit if applicable. This uses the lock so there
    is synchronized access to the API. When N threads enter this method, the
    first will pass trough, since there there was no last request recorded.
    The last request time will be set. Then, the second thread will unlock,
    and see that the last request was X seconds ago. It will sleep
    (request_limit - X) seconds, and then continue. Then the third one will
    unblock, and so on. After all threads finish, the total time will at
    least be (N * request_limit) seconds. If some request takes longer than
    request_limit seconds, the next unblocked thread will wait less.
    """

    def __init__(self, minimum_delta=0):
        """
        Set up the lock
        """
        self.lock = threading.Lock()
        self.last_used = 0
        self.minimum_delta = minimum_delta
        self.queue = queue.Queue()

    def __enter__(self):
        """
        Called when with lock: is invoked
        """
        self.lock.acquire()
        delta = time.time() - self.last_used
        sleep_amount = self.minimum_delta - delta
        if sleep_amount >= 0:
            # zero sleeps give the cpu a chance to task-switch
            logger.debug('Sleeping %s (interval)', sleep_amount)
            time.sleep(sleep_amount)
        while not self.queue.empty():
            try:
                seconds = self.queue.get(False)
                logger.debug('Sleeping %s (queued)', seconds)
                time.sleep(seconds)
            except queue.Empty:
                continue
            self.queue.task_done()

    def __exit__(self, type, value, traceback):
        """
        Called when exiting the with block.
        """
        self.last_used = time.time()
        self.lock.release()

    def snooze(self, seconds):
        """
        Asynchronously add time to the next request. Can be called outside
        of the lock context, but it is possible for the next lock holder
        to not check the queue until after something adds time to it.
        """
        # We use a queue so that we don't have to synchronize
        # across threads and with or without locks
        logger.info('Adding %s to queue', seconds)
        self.queue.put(seconds)


class FakeLock(object):
    """
    If no locking or request throttling is needed, use this
    """

    def __enter__(self):
        """
        Do nothing on enter
        """
        pass

    def __exit__(self, type, value, traceback):
        """
        Do nothing on exit
        """
        pass
