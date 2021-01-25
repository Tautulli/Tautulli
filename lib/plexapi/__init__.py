# -*- coding: utf-8 -*-
import logging
import os
from logging.handlers import RotatingFileHandler
from platform import uname
from uuid import getnode

from plexapi.config import PlexConfig, reset_base_headers
from plexapi.utils import SecretsFilter

# Load User Defined Config
DEFAULT_CONFIG_PATH = os.path.expanduser('~/.config/plexapi/config.ini')
CONFIG_PATH = os.environ.get('PLEXAPI_CONFIG_PATH', DEFAULT_CONFIG_PATH)
CONFIG = PlexConfig(CONFIG_PATH)

# PlexAPI Settings
PROJECT = 'PlexAPI'
VERSION = '4.3.0'
TIMEOUT = CONFIG.get('plexapi.timeout', 30, int)
X_PLEX_CONTAINER_SIZE = CONFIG.get('plexapi.container_size', 100, int)
X_PLEX_ENABLE_FAST_CONNECT = CONFIG.get('plexapi.enable_fast_connect', False, bool)

# Plex Header Configuation
X_PLEX_PROVIDES = CONFIG.get('header.provides', 'controller')
X_PLEX_PLATFORM = CONFIG.get('header.platform', CONFIG.get('header.platorm', uname()[0]))
X_PLEX_PLATFORM_VERSION = CONFIG.get('header.platform_version', uname()[2])
X_PLEX_PRODUCT = CONFIG.get('header.product', PROJECT)
X_PLEX_VERSION = CONFIG.get('header.version', VERSION)
X_PLEX_DEVICE = CONFIG.get('header.device', X_PLEX_PLATFORM)
X_PLEX_DEVICE_NAME = CONFIG.get('header.device_name', uname()[1])
X_PLEX_IDENTIFIER = CONFIG.get('header.identifier', str(hex(getnode())))
BASE_HEADERS = reset_base_headers()

# Logging Configuration
log = logging.getLogger('plexapi')
logfile = CONFIG.get('log.path')
logformat = CONFIG.get('log.format', '%(asctime)s %(module)12s:%(lineno)-4s %(levelname)-9s %(message)s')
loglevel = CONFIG.get('log.level', 'INFO').upper()
loghandler = logging.NullHandler()

if logfile:  # pragma: no cover
    logbackups = CONFIG.get('log.backup_count', 3, int)
    logbytes = CONFIG.get('log.rotate_bytes', 512000, int)
    loghandler = RotatingFileHandler(os.path.expanduser(logfile), 'a', logbytes, logbackups)

loghandler.setFormatter(logging.Formatter(logformat))
log.addHandler(loghandler)
log.setLevel(loglevel)
logfilter = SecretsFilter()
if CONFIG.get('log.show_secrets', '').lower() != 'true':
    log.addFilter(logfilter)
