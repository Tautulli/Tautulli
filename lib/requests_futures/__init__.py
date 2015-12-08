# -*- coding: utf-8 -*-

# Requests Futures

"""
async requests HTTP library
~~~~~~~~~~~~~~~~~~~~~


"""

__title__ = 'requests-futures'
__version__ = '0.9.5'
__build__ = 0x000000
__author__ = 'Ross McFarland'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2013 Ross McFarland'

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
