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

from __future__ import unicode_literals
from future.builtins import object
from future.builtins import str

import os
import re
import shutil
import time
import threading

from configobj import ConfigObj, ParseError
from hashing_passwords import make_hash

import plexpy
if plexpy.PYTHON2:
    import helpers
    import logger
else:
    from plexpy import helpers
    from plexpy import logger


def bool_int(value):
    """
    Casts a config value into a 0 or 1
    """
    if isinstance(value, str):
        if value.lower() in ('', '0', 'false', 'f', 'no', 'n', 'off'):
            value = 0
    return int(bool(value))


FILENAME = "config.ini"

_CONFIG_DEFINITIONS = {
    'ALLOW_GUEST_ACCESS': (int, 'General', 0),
    'DATE_FORMAT': (str, 'General', 'YYYY-MM-DD'),
    'PMS_IDENTIFIER': (str, 'PMS', ''),
    'PMS_IP': (str, 'PMS', '127.0.0.1'),
    'PMS_IS_CLOUD': (int, 'PMS', 0),
    'PMS_IS_REMOTE': (int, 'PMS', 0),
    'PMS_LOGS_FOLDER': (str, 'PMS', ''),
    'PMS_LOGS_LINE_CAP': (int, 'PMS', 1000),
    'PMS_NAME': (str, 'PMS', ''),
    'PMS_PORT': (int, 'PMS', 32400),
    'PMS_TOKEN': (str, 'PMS', ''),
    'PMS_SSL': (int, 'PMS', 0),
    'PMS_URL': (str, 'PMS', ''),
    'PMS_URL_OVERRIDE': (str, 'PMS', ''),
    'PMS_URL_MANUAL': (int, 'PMS', 0),
    'PMS_USE_BIF': (int, 'PMS', 0),
    'PMS_UUID': (str, 'PMS', ''),
    'PMS_TIMEOUT': (int, 'Advanced', 15),
    'PMS_PLEXPASS': (int, 'PMS', 0),
    'PMS_PLATFORM': (str, 'PMS', ''),
    'PMS_VERSION': (str, 'PMS', ''),
    'PMS_UPDATE_CHANNEL': (str, 'PMS', 'plex'),
    'PMS_UPDATE_DISTRO': (str, 'PMS', ''),
    'PMS_UPDATE_DISTRO_BUILD': (str, 'PMS', ''),
    'PMS_UPDATE_CHECK_INTERVAL': (int, 'Advanced', 24),
    'PMS_WEB_URL': (str, 'PMS', 'https://app.plex.tv/desktop'),
    'TIME_FORMAT': (str, 'General', 'HH:mm'),
    'ANON_REDIRECT': (str, 'General', 'https://www.nullrefer.com/?'),
    'API_ENABLED': (int, 'General', 1),
    'API_KEY': (str, 'General', ''),
    'API_SQL': (int, 'General', 0),
    'BUFFER_THRESHOLD': (int, 'Monitoring', 10),
    'BUFFER_WAIT': (int, 'Monitoring', 900),
    'BACKUP_DAYS': (int, 'General', 3),
    'BACKUP_DIR': (str, 'General', ''),
    'BACKUP_INTERVAL': (int, 'General', 6),
    'CACHE_DIR': (str, 'General', ''),
    'CACHE_IMAGES': (int, 'General', 1),
    'CACHE_SIZEMB': (int, 'Advanced', 32),
    'CHECK_GITHUB': (int, 'General', 1),
    'CHECK_GITHUB_INTERVAL': (int, 'General', 360),
    'CHECK_GITHUB_ON_STARTUP': (int, 'General', 1),
    'CHECK_GITHUB_CACHE_SECONDS': (int, 'Advanced', 3600),
    'CLEANUP_FILES': (int, 'General', 0),
    'CLOUDINARY_CLOUD_NAME': (str, 'Cloudinary', ''),
    'CLOUDINARY_API_KEY': (str, 'Cloudinary', ''),
    'CLOUDINARY_API_SECRET': (str, 'Cloudinary', ''),
    'CONFIG_VERSION': (int, 'Advanced', 0),
    'DO_NOT_OVERRIDE_GIT_BRANCH': (int, 'General', 0),
    'ENABLE_HTTPS': (int, 'General', 0),
    'EXPORT_DIR': (str, 'General', ''),
    'EXPORT_THREADS': (int, 'Advanced', 8),
    'FIRST_RUN_COMPLETE': (int, 'General', 0),
    'FREEZE_DB': (int, 'General', 0),
    'GET_FILE_SIZES': (int, 'General', 0),
    'GET_FILE_SIZES_HOLD': (dict, 'General', {'section_ids': [], 'rating_keys': []}),
    'GIT_BRANCH': (str, 'General', 'master'),
    'GIT_PATH': (str, 'General', ''),
    'GIT_REMOTE': (str, 'General', 'origin'),
    'GIT_TOKEN': (str, 'General', ''),
    'GIT_USER': (str, 'General', 'Tautulli'),
    'GIT_REPO': (str, 'General', 'Tautulli'),
    'GROUP_HISTORY_TABLES': (int, 'General', 1),
    'HISTORY_TABLE_ACTIVITY': (int, 'General', 1),
    'HOME_SECTIONS': (list, 'General', ['current_activity', 'watch_stats', 'library_stats', 'recently_added']),
    'HOME_LIBRARY_CARDS': (list, 'General', ['first_run']),
    'HOME_STATS_CARDS': (list, 'General', ['top_movies', 'popular_movies', 'top_tv', 'popular_tv', 'top_music',
        'popular_music', 'last_watched', 'top_libraries', 'top_users', 'top_platforms', 'most_concurrent']),
    'HOME_REFRESH_INTERVAL': (int, 'General', 10),
    'HTTPS_CREATE_CERT': (int, 'General', 1),
    'HTTPS_CERT': (str, 'General', ''),
    'HTTPS_CERT_CHAIN': (str, 'General', ''),
    'HTTPS_KEY': (str, 'General', ''),
    'HTTPS_DOMAIN': (str, 'General', 'localhost'),
    'HTTPS_IP': (str, 'General', '127.0.0.1'),
    'HTTP_BASIC_AUTH': (int, 'General', 0),
    'HTTP_ENVIRONMENT': (str, 'General', 'production'),
    'HTTP_HASH_PASSWORD': (int, 'General', 1),
    'HTTP_HASHED_PASSWORD': (int, 'General', 1),
    'HTTP_HOST': (str, 'General', '0.0.0.0'),
    'HTTP_PASSWORD': (str, 'General', ''),
    'HTTP_PORT': (int, 'General', 8181),
    'HTTP_PROXY': (int, 'General', 0),
    'HTTP_ROOT': (str, 'General', ''),
    'HTTP_USERNAME': (str, 'General', ''),
    'HTTP_PLEX_ADMIN': (int, 'General', 0),
    'HTTP_BASE_URL': (str, 'General', ''),
    'HTTP_RATE_LIMIT_ATTEMPTS': (int, 'General', 10),
    'HTTP_RATE_LIMIT_ATTEMPTS_INTERVAL': (int, 'General', 300),
    'HTTP_RATE_LIMIT_LOCKOUT_TIME': (int, 'General', 300),
    'HTTP_THREAD_POOL': (int, 'General', 10),
    'INTERFACE': (str, 'General', 'default'),
    'IMGUR_CLIENT_ID': (str, 'Monitoring', ''),
    'JOURNAL_MODE': (str, 'Advanced', 'WAL'),
    'LAUNCH_BROWSER': (int, 'General', 1),
    'LAUNCH_STARTUP': (int, 'General', 1),
    'LOG_BLACKLIST': (int, 'General', 1),
    'LOG_DIR': (str, 'General', ''),
    'LOGGING_IGNORE_INTERVAL': (int, 'Monitoring', 120),
    'METADATA_CACHE_SECONDS': (int, 'Advanced', 1800),
    'MOVIE_WATCHED_PERCENT': (int, 'Monitoring', 85),
    'MUSIC_WATCHED_PERCENT': (int, 'Monitoring', 85),
    'MUSICBRAINZ_LOOKUP': (int, 'General', 0),
    'MONITOR_PMS_UPDATES': (int, 'Monitoring', 0),
    'MONITORING_INTERVAL': (int, 'Monitoring', 60),
    'NEWSLETTER_AUTH': (int, 'Newsletter', 0),
    'NEWSLETTER_PASSWORD': (str, 'Newsletter', ''),
    'NEWSLETTER_CUSTOM_DIR': (str, 'Newsletter', ''),
    'NEWSLETTER_INLINE_STYLES': (int, 'Newsletter', 1),
    'NEWSLETTER_TEMPLATES': (str, 'Newsletter', 'newsletters'),
    'NEWSLETTER_DIR': (str, 'Newsletter', ''),
    'NEWSLETTER_SELF_HOSTED': (int, 'Newsletter', 0),
    'NOTIFICATION_THREADS': (int, 'Advanced', 2),
    'NOTIFY_CONSECUTIVE': (int, 'Monitoring', 1),
    'NOTIFY_CONTINUED_SESSION_THRESHOLD': (int, 'Monitoring', 15),
    'NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT': (int, 'Monitoring', 1),
    'NOTIFY_GROUP_RECENTLY_ADDED_PARENT': (int, 'Monitoring', 1),
    'NOTIFY_UPLOAD_POSTERS': (int, 'Monitoring', 0),
    'NOTIFY_RECENTLY_ADDED_DELAY': (int, 'Monitoring', 300),
    'NOTIFY_RECENTLY_ADDED_GRANDPARENT': (int, 'Monitoring', 0),
    'NOTIFY_RECENTLY_ADDED_UPGRADE': (int, 'Monitoring', 0),
    'NOTIFY_REMOTE_ACCESS_THRESHOLD': (int, 'Monitoring', 60),
    'NOTIFY_CONCURRENT_BY_IP': (int, 'Monitoring', 0),
    'NOTIFY_CONCURRENT_THRESHOLD': (int, 'Monitoring', 2),
    'NOTIFY_NEW_DEVICE_INITIAL_ONLY': (int, 'Monitoring', 1),
    'NOTIFY_SERVER_CONNECTION_THRESHOLD': (int, 'Monitoring', 60),
    'NOTIFY_SERVER_UPDATE_REPEAT': (int, 'Monitoring', 0),
    'NOTIFY_PLEXPY_UPDATE_REPEAT': (int, 'Monitoring', 0),
    'NOTIFY_TEXT_EVAL': (int, 'Advanced', 0),
    'PLEXPY_AUTO_UPDATE': (int, 'General', 0),
    'REFRESH_LIBRARIES_INTERVAL': (int, 'Monitoring', 12),
    'REFRESH_LIBRARIES_ON_STARTUP': (int, 'Monitoring', 1),
    'REFRESH_USERS_INTERVAL': (int, 'Monitoring', 12),
    'REFRESH_USERS_ON_STARTUP': (int, 'Monitoring', 1),
    'SESSION_DB_WRITE_ATTEMPTS': (int, 'Advanced', 5),
    'SHOW_ADVANCED_SETTINGS': (int, 'General', 0),
    'SYNCHRONOUS_MODE': (str, 'Advanced', 'NORMAL'),
    'THEMOVIEDB_APIKEY': (str, 'General', 'e9a6655bae34bf694a0f3e33338dc28e'),
    'THEMOVIEDB_LOOKUP': (int, 'General', 0),
    'TVMAZE_LOOKUP': (int, 'General', 0),
    'TV_WATCHED_PERCENT': (int, 'Monitoring', 85),
    'UPDATE_DB_INTERVAL': (int, 'General', 24),
    'UPDATE_SHOW_CHANGELOG': (int, 'General', 1),
    'UPGRADE_FLAG': (int, 'Advanced', 0),
    'VERBOSE_LOGS': (int, 'Advanced', 1),
    'VERIFY_SSL_CERT': (bool_int, 'Advanced', 1),
    'WEBSOCKET_MONITOR_PING_PONG': (int, 'Advanced', 0),
    'WEBSOCKET_CONNECTION_ATTEMPTS': (int, 'Advanced', 5),
    'WEBSOCKET_CONNECTION_TIMEOUT': (int, 'Advanced', 5),
    'WEEK_START_MONDAY': (int, 'General', 0),
    'JWT_SECRET': (str, 'Advanced', ''),
    'JWT_UPDATE_SECRET': (bool_int, 'Advanced', 0),
    'SYSTEM_ANALYTICS': (int, 'Advanced', 1),
    'SYS_TRAY_ICON': (int, 'General', 1),
}

_BLACKLIST_KEYS = ['_APITOKEN', '_TOKEN', '_KEY', '_SECRET', '_PASSWORD', '_APIKEY', '_ID', '_HOOK']
_WHITELIST_KEYS = ['HTTPS_KEY']

_DO_NOT_IMPORT_KEYS = [
    'FIRST_RUN_COMPLETE', 'GET_FILE_SIZES_HOLD', 'GIT_PATH', 'PMS_LOGS_FOLDER',
    'BACKUP_DIR', 'CACHE_DIR', 'EXPORT_DIR', 'LOG_DIR', 'NEWSLETTER_DIR', 'NEWSLETTER_CUSTOM_DIR',
    'HTTP_HOST', 'HTTP_PORT', 'HTTP_ROOT',
    'HTTP_USERNAME', 'HTTP_PASSWORD', 'HTTP_HASH_PASSWORD', 'HTTP_HASHED_PASSWORD',
    'ENABLE_HTTPS', 'HTTPS_CREATE_CERT', 'HTTPS_CERT', 'HTTPS_CERT_CHAIN', 'HTTPS_KEY'
]
_DO_NOT_IMPORT_KEYS_DOCKER = [
    'PLEXPY_AUTO_UPDATE', 'GIT_REMOTE', 'GIT_BRANCH'
]

IS_IMPORTING = False
IMPORT_THREAD = None


def set_is_importing(value):
    global IS_IMPORTING
    IS_IMPORTING = value


def set_import_thread(config=None, backup=False):
    global IMPORT_THREAD
    if config:
        if IMPORT_THREAD:
            return
        IMPORT_THREAD = threading.Thread(target=import_tautulli_config,
                                         kwargs={'config': config, 'backup': backup})
    else:
        IMPORT_THREAD = None


def import_tautulli_config(config=None, backup=False):
    if IS_IMPORTING:
        logger.warn("Tautulli Config :: Another Tautulli config is currently being imported. "
                    "Please wait until it is complete before importing another config.")
        return False

    if backup:
        # Make a backup of the current config first
        logger.info("Tautulli Config :: Creating a config backup before importing.")
        if not make_backup():
            logger.error("Tautulli Config :: Failed to import Tautulli config: failed to create config backup")
            return False

    # Create a new Config object with the imported config file
    try:
        imported_config = Config(config, is_import=True)
    except:
        logger.error("Tautulli Config :: Failed to import Tautulli config: error reading imported config file")
        return False

    logger.info("Tautulli Config :: Importing Tautulli config '%s'...", config)
    set_is_importing(True)

    # Remove keys that should not be imported
    for key in _DO_NOT_IMPORT_KEYS:
        delattr(imported_config, key)
    if plexpy.DOCKER or plexpy.SNAP:
        for key in _DO_NOT_IMPORT_KEYS_DOCKER:
            delattr(imported_config, key)

    # Merge the imported config file into the current config file
    plexpy.CONFIG._config.merge(imported_config._config)
    plexpy.CONFIG.write()

    logger.info("Tautulli Config :: Tautulli config import complete.")
    set_import_thread(None)
    set_is_importing(False)

    # Restart to apply changes
    plexpy.SIGNAL = 'restart'


def make_backup(cleanup=False, scheduler=False):
    """ Makes a backup of config file, removes all but the last 5 backups """

    if scheduler:
        backup_file = 'config.backup-{}.sched.ini'.format(helpers.now())
    else:
        backup_file = 'config.backup-{}.ini'.format(helpers.now())
    backup_folder = plexpy.CONFIG.BACKUP_DIR
    backup_file_fp = os.path.join(backup_folder, backup_file)

    # In case the user has deleted it manually
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    plexpy.CONFIG.write()
    shutil.copyfile(plexpy.CONFIG_FILE, backup_file_fp)

    if cleanup:
        now = time.time()
        # Delete all scheduled backup older than BACKUP_DAYS.
        for root, dirs, files in os.walk(backup_folder):
            ini_files = [os.path.join(root, f) for f in files if f.endswith('.sched.ini')]
            for file_ in ini_files:
                if os.stat(file_).st_mtime < now - plexpy.CONFIG.BACKUP_DAYS * 86400:
                    try:
                        os.remove(file_)
                    except OSError as e:
                        logger.error("Tautulli Config :: Failed to delete %s from the backup folder: %s" % (file_, e))

    if backup_file in os.listdir(backup_folder):
        logger.debug("Tautulli Config :: Successfully backed up %s to %s" % (plexpy.CONFIG_FILE, backup_file))
        return True
    else:
        logger.error("Tautulli Config :: Failed to backup %s to %s" % (plexpy.CONFIG_FILE, backup_file))
        return False


# pylint:disable=R0902
# it might be nice to refactor for fewer instance variables
class Config(object):
    """ Wraps access to particular values in a config file """

    def __init__(self, config_file, is_import=False):
        """ Initialize the config with values from a file """
        self._config_file = config_file
        try:
            self._config = ConfigObj(self._config_file, encoding='utf-8')
        except ParseError as e:
            logger.error("Tautulli Config :: Error reading configuration file: %s", e)
            raise

        for key in _CONFIG_DEFINITIONS:
            self.check_setting(key)
        if not is_import:
            self._upgrade()
            self._blacklist()

    def _blacklist(self):
        """ Add tokens and passwords to blacklisted words in logger """
        blacklist = set()

        for key, subkeys in self._config.items():
            for subkey, value in subkeys.items():
                if isinstance(value, str) and len(value.strip()) > 5 and \
                    subkey.upper() not in _WHITELIST_KEYS and any(bk in subkey.upper() for bk in _BLACKLIST_KEYS):
                    blacklist.add(value.strip())

        logger._BLACKLIST_WORDS.update(blacklist)

    def _define(self, name):
        key = name.upper()
        ini_key = name.lower()
        definition = _CONFIG_DEFINITIONS[key]
        if len(definition) == 3:
            definition_type, section, default = definition
        else:
            definition_type, section, _, default = definition
        return key, definition_type, section, ini_key, default

    def check_section(self, section):
        """ Check if INI section exists, if not create it """
        if section not in self._config:
            self._config[section] = {}
            return True
        else:
            return False

    def check_setting(self, key):
        """ Cast any value in the config to the right type or use the default """
        key, definition_type, section, ini_key, default = self._define(key)
        self.check_section(section)
        try:
            my_val = definition_type(self._config[section][ini_key])
        except Exception:
            my_val = definition_type(default)
            self._config[section][ini_key] = my_val
        return my_val

    def write(self):
        """ Make a copy of the stored config and write it to the configured file """
        new_config = ConfigObj(encoding="UTF-8")
        new_config.filename = self._config_file

        # first copy over everything from the old config, even if it is not
        # correctly defined to keep from losing data
        for key, subkeys in self._config.items():
            if key not in new_config:
                new_config[key] = {}
            for subkey, value in subkeys.items():
                new_config[key][subkey] = value

        # next make sure that everything we expect to have defined is so
        for key in _CONFIG_DEFINITIONS:
            key, definition_type, section, ini_key, default = self._define(key)
            self.check_setting(key)
            if section not in new_config:
                new_config[section] = {}
            new_config[section][ini_key] = self._config[section][ini_key]

        # Write it to file
        logger.info("Tautulli Config :: Writing configuration to file")

        try:
            new_config.write()
        except IOError as e:
            logger.error("Tautulli Config :: Error writing configuration file: %s", e)

        self._blacklist()

    def __getattr__(self, name):
        """
        Returns something from the ini unless it is a real property
        of the configuration object or is not all caps.
        """
        if not re.match(r'[A-Z_]+$', name):
            return super(Config, self).__getattr__(name)
        else:
            return self.check_setting(name)

    def __setattr__(self, name, value):
        """
        Maps all-caps properties to ini values unless they exist on the
        configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            super(Config, self).__setattr__(name, value)
            return value
        else:
            key, definition_type, section, ini_key, default = self._define(name)
            self._config[section][ini_key] = definition_type(value)
            return self._config[section][ini_key]

    def __delattr__(self, name):
        """
        Deletes a key from the configuration object.
        """
        if not re.match(r'[A-Z_]+$', name):
            return super(Config, self).__delattr__(name)
        else:
            key, definition_type, section, ini_key, default = self._define(name)
            del self._config[section][ini_key]

    def process_kwargs(self, kwargs):
        """
        Given a big bunch of key value pairs, apply them to the ini.
        """
        for name, value in kwargs.items():
            key, definition_type, section, ini_key, default = self._define(name)
            self._config[section][ini_key] = definition_type(value)

    def _upgrade(self):
        """
        Upgrades config file from previous verisions and bumps up config version
        """
        if self.CONFIG_VERSION == 0:
            self.CONFIG_VERSION = 1

        if self.CONFIG_VERSION == 1:
            # Change home_stats_cards to list
            if self.HOME_STATS_CARDS:
                home_stats_cards = ''.join(self.HOME_STATS_CARDS).split(', ')
                if 'watch_statistics' in home_stats_cards:
                    home_stats_cards.remove('watch_statistics')
                    self.HOME_STATS_CARDS = home_stats_cards
            # Change home_library_cards to list
            if self.HOME_LIBRARY_CARDS:
                home_library_cards = ''.join(self.HOME_LIBRARY_CARDS).split(', ')
                if 'library_statistics' in home_library_cards:
                    home_library_cards.remove('library_statistics')
                    self.HOME_LIBRARY_CARDS = home_library_cards

            self.CONFIG_VERSION = 2

        if self.CONFIG_VERSION == 2:
            self.CONFIG_VERSION = 3

        if self.CONFIG_VERSION == 3:
            if self.HTTP_ROOT == '/':
                self.HTTP_ROOT = ''

            self.CONFIG_VERSION = 4

        if self.CONFIG_VERSION == 4:
            if not len(self.HOME_STATS_CARDS) and 'watch_stats' in self.HOME_SECTIONS:
                home_sections = self.HOME_SECTIONS
                home_sections.remove('watch_stats')
                self.HOME_SECTIONS = home_sections
            if not len(self.HOME_LIBRARY_CARDS) and 'library_stats' in self.HOME_SECTIONS:
                home_sections = self.HOME_SECTIONS
                home_sections.remove('library_stats')
                self.HOME_SECTIONS = home_sections

            self.CONFIG_VERSION = 5

        if self.CONFIG_VERSION == 5:
            self.MONITOR_PMS_UPDATES = 0

            self.CONFIG_VERSION = 6

        if self.CONFIG_VERSION == 6:
            if self.GIT_USER.lower() == 'drzoidberg33':
                self.GIT_USER = 'JonnyWong16'

            self.CONFIG_VERSION = 7

        if self.CONFIG_VERSION == 7:
            self.CONFIG_VERSION = 8

        if self.CONFIG_VERSION == 8:
            self.CONFIG_VERSION = 9

        if self.CONFIG_VERSION == 9:
            if self.PMS_UPDATE_CHANNEL == 'plexpass':
                self.PMS_UPDATE_CHANNEL = 'beta'

            self.CONFIG_VERSION = 10

        if self.CONFIG_VERSION == 10:
            self.GIT_USER = 'Tautulli'
            self.GIT_REPO = 'Tautulli'

            self.CONFIG_VERSION = 11

        if self.CONFIG_VERSION == 11:
            self.ANON_REDIRECT = self.ANON_REDIRECT.replace('http://www.nullrefer.com/?',
                                                            'https://www.nullrefer.com/?')
            self.CONFIG_VERSION = 12

        if self.CONFIG_VERSION == 12:
            self.BUFFER_THRESHOLD = max(self.BUFFER_THRESHOLD, 10)

            self.CONFIG_VERSION = 13

        if self.CONFIG_VERSION == 13:
            self.CONFIG_VERSION = 14

        if self.CONFIG_VERSION == 14:
            if plexpy.DOCKER:
                self.PLEXPY_AUTO_UPDATE = 0

            self.CONFIG_VERSION = 15

        if self.CONFIG_VERSION == 15:
            if self.HTTP_ROOT and self.HTTP_ROOT != '/':
                self.JWT_UPDATE_SECRET = True

            self.CONFIG_VERSION = 16

        if self.CONFIG_VERSION == 16:
            if plexpy.SNAP:
                self.PLEXPY_AUTO_UPDATE = 0

            self.CONFIG_VERSION = 17

        if self.CONFIG_VERSION == 17:
            home_stats_cards = self.HOME_STATS_CARDS
            if 'top_users' in home_stats_cards:
                top_users_index = home_stats_cards.index('top_users')
                home_stats_cards.insert(top_users_index, 'top_libraries')
            else:
                home_stats_cards.append('top_libraries')
            self.HOME_STATS_CARDS = home_stats_cards

            self.CONFIG_VERSION = 18

        if self.CONFIG_VERSION == 18:
            self.CHECK_GITHUB_INTERVAL = (
                    int(self.CHECK_GITHUB_INTERVAL // 60)
                    + (self.CHECK_GITHUB_INTERVAL % 60 > 0)
            )

            self.CONFIG_VERSION = 19

        if self.CONFIG_VERSION == 19:
            if self.HTTP_PASSWORD and not self.HTTP_HASHED_PASSWORD:
                self.HTTP_PASSWORD = make_hash(self.HTTP_PASSWORD)
            self.HTTP_HASH_PASSWORD = 1
            self.HTTP_HASHED_PASSWORD = 1

            self.CONFIG_VERSION = 20
