# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
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

from __future__ import unicode_literals
from future.builtins import str

from logutils.queue import QueueHandler, QueueListener
from logging import handlers

import contextlib
import errno
import logging
import multiprocessing
import os
import re
import sys
import threading
import traceback

import plexpy
if plexpy.PYTHON2:
    import helpers
    from config import _BLACKLIST_KEYS, _WHITELIST_KEYS
else:
    from plexpy import helpers
    from plexpy.config import _BLACKLIST_KEYS, _WHITELIST_KEYS


# These settings are for file logging only
FILENAME = "tautulli.log"
FILENAME_API = "tautulli_api.log"
FILENAME_PLEX_WEBSOCKET = "plex_websocket.log"
MAX_SIZE = 5000000  # 5 MB
MAX_FILES = 5

_BLACKLIST_WORDS = set()

# Tautulli logger
logger = logging.getLogger("tautulli")
# Tautulli API logger
logger_api = logging.getLogger("tautulli_api")
# Tautulli websocket logger
logger_plex_websocket = logging.getLogger("plex_websocket")

# Global queue for multiprocessing logging
queue = None


def blacklist_config(config):
    blacklist = set()
    blacklist_keys = ['HOOK', 'APIKEY', 'KEY', 'PASSWORD', 'TOKEN']

    for key, value in config.items():
        if isinstance(value, str) and len(value.strip()) > 5 and \
            key.upper() not in _WHITELIST_KEYS and (key.upper() in blacklist_keys or
                                                    any(bk in key.upper() for bk in _BLACKLIST_KEYS)):
            blacklist.add(value.strip())

    _BLACKLIST_WORDS.update(blacklist)


class NoThreadFilter(logging.Filter):
    """
    Log filter for the current thread
    """
    def __init__(self, threadName):
        self.threadName = threadName

    def filter(self, record):
        return not record.threadName == self.threadName


# Taken from Hellowlol/HTPC-Manager
class BlacklistFilter(logging.Filter):
    """
    Log filter for blacklisted tokens and passwords
    """
    def __init__(self):
        super(BlacklistFilter, self).__init__()

    def filter(self, record):
        if not plexpy.CONFIG.LOG_BLACKLIST:
            return True

        for item in _BLACKLIST_WORDS:
            try:
                if item in record.msg:
                    record.msg = record.msg.replace(item, 8 * '*' + item[-2:])
                if any(item in str(arg) for arg in record.args):
                    record.args = tuple(arg.replace(item, 8 * '*' + item[-2:]) if isinstance(arg, str) else arg
                                        for arg in record.args)
            except:
                pass
        return True


class RegexFilter(logging.Filter):
    """
    Base class for regex log filter
    """
    def __init__(self):
        super(RegexFilter, self).__init__()

        self.regex = re.compile(r'')

    def filter(self, record):
        if not plexpy.CONFIG.LOG_BLACKLIST:
            return True

        try:
            matches = self.regex.findall(record.msg)
            for match in matches:
                record.msg = self.replace(record.msg, match)

            args = []
            for arg in record.args:
                matches = self.regex.findall(arg) if isinstance(arg, str) else []
                for match in matches:
                    arg = self.replace(arg, match)
                args.append(arg)
            record.args = tuple(args)
        except:
            pass

        return True

    def replace(self, text, match):
        return text


class PublicIPFilter(RegexFilter):
    """
    Log filter for public IP addresses
    """
    def __init__(self):
        super(PublicIPFilter, self).__init__()

        # Currently only checking for ipv4 addresses
        self.regex = re.compile(r'[0-9]+(?:[.-][0-9]+){3}(?!\d*-[a-z0-9]{6})')

    def replace(self, text, ip):
        if helpers.is_public_ip(ip.replace('-', '.')):
            partition = '-' if '-' in ip else '.'
            return text.replace(ip, ip.partition(partition)[0] + (partition + '***') * 3)
        return text


class EmailFilter(RegexFilter):
    """
    Log filter for email addresses
    """
    def __init__(self):
        super(EmailFilter, self).__init__()

        self.regex = re.compile(r'([a-z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*@'
                                r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)',
                                re.IGNORECASE)

    def replace(self, text, email):
        email_parts = email.partition('@')
        return text.replace(email, email_parts[0][:2] + 8 * '*' + email_parts[1] + 8 * '*')


class PlexTokenFilter(RegexFilter):
    """
    Log filter for X-Plex-Token
    """
    def __init__(self):
        super(PlexTokenFilter, self).__init__()

        self.regex = re.compile(r'X-Plex-Token(?:=|%3D)([a-zA-Z0-9]+)')

    def replace(self, text, token):
        return text.replace(token, 8 * '*' + token[-2:])


@contextlib.contextmanager
def listener():
    """
    Wrapper that create a QueueListener, starts it and automatically stops it.
    To be used in a with statement in the main process, for multiprocessing.
    """

    global queue

    # Initialize queue if not already done
    if queue is None:
        try:
            queue = multiprocessing.Queue()
        except OSError as e:
            queue = False

            # Some machines don't have access to /dev/shm. See
            # http://stackoverflow.com/questions/2009278 for more information.
            if e.errno == errno.EACCES:
                logger.warning('Multiprocess logging disabled, because '
                               'current user cannot map shared memory. You won\'t see any' \
                               'logging generated by the worker processed.')

    # Multiprocess logging may be disabled.
    if not queue:
        yield
    else:
        queue_listener = QueueListener(queue, *logger.handlers)

        try:
            queue_listener.start()
            yield
        finally:
            queue_listener.stop()


def initMultiprocessing():
    """
    Remove all handlers and add QueueHandler on top. This should only be called
    inside a multiprocessing worker process, since it changes the logger
    completely.
    """

    # Multiprocess logging may be disabled.
    if not queue:
        return

    # Remove all handlers and add the Queue handler as the only one.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    queue_handler = QueueHandler(queue)
    queue_handler.setLevel(logging.DEBUG)

    logger.addHandler(queue_handler)

    # Change current thread name for log record
    threading.current_thread().name = multiprocessing.current_process().name


def initLogger(console=False, log_dir=False, verbose=False):
    """
    Setup logging for Tautulli. It uses the logger instance with the name
    'tautulli'. Three log handlers are added:

    * RotatingFileHandler: for the file tautulli.log
    * LogListHandler: for Web UI
    * StreamHandler: for console (if console)

    Console logging is only enabled if console is set to True. This method can
    be invoked multiple times, during different stages of Tautulli.
    """

    # Close and remove old handlers. This is required to reinit the loggers
    # at runtime
    for handler in logger.handlers[:] + logger_api.handlers[:] + logger_plex_websocket.handlers[:]:
        # Just make sure it is cleaned up.
        if isinstance(handler, handlers.RotatingFileHandler):
            handler.close()
        elif isinstance(handler, logging.StreamHandler):
            handler.flush()

        logger.removeHandler(handler)
        logger_api.removeHandler(handler)
        logger_plex_websocket.removeHandler(handler)

    # Configure the logger to accept all messages
    logger.propagate = False
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger_api.propagate = False
    logger_api.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger_plex_websocket.propagate = False
    logger_plex_websocket.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Setup file logger
    if log_dir:
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)-7s :: %(threadName)s : %(message)s', '%Y-%m-%d %H:%M:%S')

        # Main Tautulli logger
        filename = os.path.join(log_dir, FILENAME)
        file_handler = handlers.RotatingFileHandler(filename, maxBytes=MAX_SIZE, backupCount=MAX_FILES, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)

        # Tautulli API logger
        filename = os.path.join(log_dir, FILENAME_API)
        file_handler = handlers.RotatingFileHandler(filename, maxBytes=MAX_SIZE, backupCount=MAX_FILES, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        logger_api.addHandler(file_handler)

        # Tautulli websocket logger
        filename = os.path.join(log_dir, FILENAME_PLEX_WEBSOCKET)
        file_handler = handlers.RotatingFileHandler(filename, maxBytes=MAX_SIZE, backupCount=MAX_FILES, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        logger_plex_websocket.addHandler(file_handler)

    # Setup console logger
    if console:
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s :: %(threadName)s : %(message)s', '%Y-%m-%d %H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)

        logger.addHandler(console_handler)

    # Add filters to log handlers
    # Only add filters after the config file has been initialized
    # Nothing prior to initialization should contain sensitive information
    if not plexpy.DEV and plexpy.CONFIG:
        for handler in logger.handlers + logger_api.handlers + logger_plex_websocket.handlers:
            handler.addFilter(BlacklistFilter())
            handler.addFilter(PublicIPFilter())
            handler.addFilter(EmailFilter())
            handler.addFilter(PlexTokenFilter())

    # Install exception hooks
    initHooks()


def initHooks(global_exceptions=True, thread_exceptions=True, pass_original=True):
    """
    This method installs exception catching mechanisms. Any exception caught
    will pass through the exception hook, and will be logged to the logger as
    an error. Additionally, a traceback is provided.

    This is very useful for crashing threads and any other bugs, that may not
    be exposed when running as daemon.

    The default exception hook is still considered, if pass_original is True.
    """

    def excepthook(*exception_info):
        # We should always catch this to prevent loops!
        try:
            message = "".join(traceback.format_exception(*exception_info))
            logger.error("Uncaught exception: %s", message)
        except:
            pass

        # Original excepthook
        if pass_original:
            sys.__excepthook__(*exception_info)

    # Global exception hook
    if global_exceptions:
        sys.excepthook = excepthook

    # Thread exception hook
    if thread_exceptions:
        old_init = threading.Thread.__init__

        def new_init(self, *args, **kwargs):
            old_init(self, *args, **kwargs)
            old_run = self.run

            def new_run(*args, **kwargs):
                try:
                    old_run(*args, **kwargs)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    excepthook(*sys.exc_info())
            self.run = new_run

        # Monkey patch the run() by monkey patching the __init__ method
        threading.Thread.__init__ = new_init


def shutdown():
    logging.shutdown()


# Expose logger methods
# Main Tautulli logger
info = logger.info
warn = logger.warning
error = logger.error
debug = logger.debug
warning = logger.warning
exception = logger.exception

# Tautulli API logger
api_info = logger_api.info
api_warn = logger_api.warning
api_error = logger_api.error
api_debug = logger_api.debug
api_warning = logger_api.warning
api_exception = logger_api.exception

# Tautulli websocket logger
websocket_info = logger_plex_websocket.info
websocket_warn = logger_plex_websocket.warning
websocket_error = logger_plex_websocket.error
websocket_debug = logger_plex_websocket.debug
websocket_warning = logger_plex_websocket.warning
websocket_exception = logger_plex_websocket.exception
