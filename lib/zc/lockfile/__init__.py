##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
import logging
import os


logger = logging.getLogger("zc.lockfile")


class LockError(Exception):
    """Couldn't get a lock
    """


try:
    import fcntl
except ImportError:
    try:
        import msvcrt
    except ImportError:
        def _lock_file(file):
            raise TypeError('No file-locking support on this platform')

        def _unlock_file(file):
            raise TypeError('No file-locking support on this platform')

    else:
        # Windows
        def _lock_file(file):
            # Lock just the first byte
            try:
                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise LockError("Couldn't lock %r" % file.name)

        def _unlock_file(file):
            try:
                file.seek(0)
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                raise LockError("Couldn't unlock %r" % file.name)

else:
    # Unix
    _flags = fcntl.LOCK_EX | fcntl.LOCK_NB

    def _lock_file(file):
        try:
            fcntl.flock(file.fileno(), _flags)
        except OSError:
            raise LockError("Couldn't lock %r" % file.name)

    def _unlock_file(file):
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


class LazyHostName:
    """Avoid importing socket and calling gethostname() unnecessarily"""

    def __str__(self):
        import socket
        return socket.gethostname()


class SimpleLockFile:

    _fp = None

    def __init__(self, path):
        self._path = path
        try:
            # Try to open for writing without truncation:
            fp = open(path, 'r+')
        except OSError:
            # If the file doesn't exist, we'll get an IO error, try a+
            # Note that there may be a race here. Multiple processes
            # could fail on the r+ open and open the file a+, but only
            # one will get the the lock and write a pid.
            fp = open(path, 'a+')

        try:
            _lock_file(fp)
            self._fp = fp
        except BaseException:
            fp.close()
            raise

        # Lock acquired
        self._on_lock()
        fp.flush()

    def close(self):
        if self._fp is not None:
            _unlock_file(self._fp)
            self._fp.close()
            self._fp = None

    def _on_lock(self):
        """
        Allow subclasses to supply behavior to occur following
        lock acquisition.
        """


class LockFile(SimpleLockFile):

    def __init__(self, path, content_template='{pid}'):
        self._content_template = content_template
        super().__init__(path)

    def _on_lock(self):
        content = self._content_template.format(
            pid=os.getpid(),
            hostname=LazyHostName(),
        )
        self._fp.write(" %s\n" % content)
        self._fp.truncate()
