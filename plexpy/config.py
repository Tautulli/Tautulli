import plexpy.logger
import itertools
import os
import re
from configobj import ConfigObj


def bool_int(value):
    """
    Casts a config value into a 0 or 1
    """
    if isinstance(value, basestring):
        if value.lower() in ('', '0', 'false', 'f', 'no', 'n', 'off'):
            value = 0
    return int(bool(value))



_CONFIG_DEFINITIONS = {
    'DATE_FORMAT': (str, 'General', 'YYYY-MM-DD'),
    'GROUPING_GLOBAL_HISTORY': (int, 'PlexWatch', 0),
    'GROUPING_USER_HISTORY': (int, 'PlexWatch', 0),
    'GROUPING_CHARTS': (int, 'PlexWatch', 0),
    'PLEXWATCH_DATABASE': (str, 'PlexWatch', ''),
    'PMS_IDENTIFIER': (str, 'PMS', ''),
    'PMS_IP': (str, 'PMS', '127.0.0.1'),
    'PMS_IS_REMOTE': (int, 'PMS', 0),
    'PMS_LOGS_FOLDER': (str, 'PMS', ''),
    'PMS_PORT': (int, 'PMS', 32400),
    'PMS_PASSWORD': (str, 'PMS', ''),
    'PMS_TOKEN': (str, 'PMS', ''),
    'PMS_SSL': (int, 'General', 0),
    'PMS_URL': (str, 'PMS', ''),
    'PMS_USERNAME': (str, 'PMS', ''),
    'PMS_USE_BIF': (int, 'PMS', 0),
    'PMS_UUID': (str, 'PMS', ''),
    'TIME_FORMAT': (str, 'General', 'HH:mm'),
    'API_ENABLED': (int, 'General', 0),
    'API_KEY': (str, 'General', ''),
    'BOXCAR_ENABLED': (int, 'Boxcar', 0),
    'BOXCAR_TOKEN': (str, 'Boxcar', ''),
    'BOXCAR_ON_PLAY': (int, 'Boxcar', 0),
    'BOXCAR_ON_STOP': (int, 'Boxcar', 0),
    'BOXCAR_ON_WATCHED': (int, 'Boxcar', 0),
    'CACHE_DIR': (str, 'General', ''),
    'CACHE_SIZEMB': (int, 'Advanced', 32),
    'CHECK_GITHUB': (int, 'General', 1),
    'CHECK_GITHUB_INTERVAL': (int, 'General', 360),
    'CHECK_GITHUB_ON_STARTUP': (int, 'General', 1),
    'CLEANUP_FILES': (int, 'General', 0),
    'CONFIG_VERSION': (str, 'General', '0'),
    'DO_NOT_OVERRIDE_GIT_BRANCH': (int, 'General', 0),
    'EMAIL_ENABLED': (int, 'Email', 0),
    'EMAIL_FROM': (str, 'Email', ''),
    'EMAIL_TO': (str, 'Email', ''),
    'EMAIL_SMTP_SERVER': (str, 'Email', ''),
    'EMAIL_SMTP_USER': (str, 'Email', ''),
    'EMAIL_SMTP_PASSWORD': (str, 'Email', ''),
    'EMAIL_SMTP_PORT': (int, 'Email', 25),
    'EMAIL_TLS': (int, 'Email', 0),
    'EMAIL_ON_PLAY': (int, 'Email', 0),
    'EMAIL_ON_STOP': (int, 'Email', 0),
    'EMAIL_ON_WATCHED': (int, 'Email', 0),
    'ENABLE_HTTPS': (int, 'General', 0),
    'FIRST_RUN_COMPLETE': (int, 'General', 0),
    'FREEZE_DB': (int, 'General', 0),
    'GIT_BRANCH': (str, 'General', 'master'),
    'GIT_PATH': (str, 'General', ''),
    'GIT_USER': (str, 'General', 'drzoidberg33'),
    'GROWL_ENABLED': (int, 'Growl', 0),
    'GROWL_HOST': (str, 'Growl', ''),
    'GROWL_PASSWORD': (str, 'Growl', ''),
    'GROWL_ON_PLAY': (int, 'Growl', 0),
    'GROWL_ON_STOP': (int, 'Growl', 0),
    'GROWL_ON_WATCHED': (int, 'Growl', 0),
    'HTTPS_CERT': (str, 'General', ''),
    'HTTPS_KEY': (str, 'General', ''),
    'HTTP_HOST': (str, 'General', '0.0.0.0'),
    'HTTP_PASSWORD': (str, 'General', ''),
    'HTTP_PORT': (int, 'General', 8181),
    'HTTP_PROXY': (int, 'General', 0),
    'HTTP_ROOT': (str, 'General', '/'),
    'HTTP_USERNAME': (str, 'General', ''),
    'INTERFACE': (str, 'General', 'default'),
    'IP_LOGGING_ENABLE': (int, 'General', 0),
    'JOURNAL_MODE': (str, 'Advanced', 'wal'),
    'LAUNCH_BROWSER': (int, 'General', 1),
    'LOG_DIR': (str, 'General', ''),
    'LOGGING_IGNORE_INTERVAL': (int, 'Monitoring', 120),
    'MOVIE_NOTIFY_ENABLE': (int, 'Monitoring', 0),
    'MOVIE_NOTIFY_ON_START': (int, 'Monitoring', 1),
    'MOVIE_NOTIFY_ON_STOP': (int, 'Monitoring', 0),
    'MOVIE_NOTIFY_ON_PAUSE': (int, 'Monitoring', 0),
    'MUSIC_NOTIFY_ENABLE': (int, 'Monitoring', 0),
    'MUSIC_NOTIFY_ON_START': (int, 'Monitoring', 1),
    'MUSIC_NOTIFY_ON_STOP': (int, 'Monitoring', 0),
    'MUSIC_NOTIFY_ON_PAUSE': (int, 'Monitoring', 0),
    'MUSIC_LOGGING_ENABLE': (int, 'Monitoring', 0),
    'MONITORING_INTERVAL': (int, 'Monitoring', 60),
    'NMA_APIKEY': (str, 'NMA', ''),
    'NMA_ENABLED': (int, 'NMA', 0),
    'NMA_PRIORITY': (int, 'NMA', 0),
    'NMA_ON_PLAY': (int, 'NMA', 0),
    'NMA_ON_STOP': (int, 'NMA', 0),
    'NMA_ON_WATCHED': (int, 'NMA', 0),
    'NOTIFY_WATCHED_PERCENT': (int, 'Monitoring', 85),
    'NOTIFY_ON_START_SUBJECT_TEXT': (str, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_START_BODY_TEXT': (str, 'Monitoring', '{user} ({player}) started playing {title}.'),
    'NOTIFY_ON_STOP_SUBJECT_TEXT': (str, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_STOP_BODY_TEXT': (str, 'Monitoring', '{user} ({player}) has stopped {title}.'),
    'NOTIFY_ON_WATCHED_SUBJECT_TEXT': (str, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_WATCHED_BODY_TEXT': (str, 'Monitoring', '{user} ({player}) has watched {title}.'),
    'OSX_NOTIFY_APP': (str, 'OSX_Notify', '/Applications/PlexPy'),
    'OSX_NOTIFY_ENABLED': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_PLAY': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_STOP': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_WATCHED': (int, 'OSX_Notify', 0),
    'PLEX_CLIENT_HOST': (str, 'Plex', ''),
    'PLEX_ENABLED': (int, 'Plex', 0),
    'PLEX_PASSWORD': (str, 'Plex', ''),
    'PLEX_USERNAME': (str, 'Plex', ''),
    'PLEX_ON_PLAY': (int, 'Plex', 0),
    'PLEX_ON_STOP': (int, 'Plex', 0),
    'PLEX_ON_WATCHED': (int, 'Plex', 0),
    'PROWL_ENABLED': (int, 'Prowl', 0),
    'PROWL_KEYS': (str, 'Prowl', ''),
    'PROWL_PRIORITY': (int, 'Prowl', 0),
    'PROWL_ON_PLAY': (int, 'Prowl', 0),
    'PROWL_ON_STOP': (int, 'Prowl', 0),
    'PROWL_ON_WATCHED': (int, 'Prowl', 0),
    'PUSHALOT_APIKEY': (str, 'Pushalot', ''),
    'PUSHALOT_ENABLED': (int, 'Pushalot', 0),
    'PUSHALOT_ON_PLAY': (int, 'Pushalot', 0),
    'PUSHALOT_ON_STOP': (int, 'Pushalot', 0),
    'PUSHALOT_ON_WATCHED': (int, 'Pushalot', 0),
    'PUSHBULLET_APIKEY': (str, 'PushBullet', ''),
    'PUSHBULLET_DEVICEID': (str, 'PushBullet', ''),
    'PUSHBULLET_CHANNEL_TAG': (str, 'PushBullet', ''),
    'PUSHBULLET_ENABLED': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_PLAY': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_STOP': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_WATCHED': (int, 'PushBullet', 0),
    'PUSHOVER_APITOKEN': (str, 'Pushover', ''),
    'PUSHOVER_ENABLED': (int, 'Pushover', 0),
    'PUSHOVER_KEYS': (str, 'Pushover', ''),
    'PUSHOVER_PRIORITY': (int, 'Pushover', 0),
    'PUSHOVER_ON_PLAY': (int, 'Pushover', 0),
    'PUSHOVER_ON_STOP': (int, 'Pushover', 0),
    'PUSHOVER_ON_WATCHED': (int, 'Pushover', 0),
    'REFRESH_USERS_INTERVAL': (int, 'Monitoring', 12),
    'REFRESH_USERS_ON_STARTUP': (int, 'Monitoring', 1),
    'TV_NOTIFY_ENABLE': (int, 'Monitoring', 0),
    'TV_NOTIFY_ON_START': (int, 'Monitoring', 1),
    'TV_NOTIFY_ON_STOP': (int, 'Monitoring', 0),
    'TV_NOTIFY_ON_PAUSE': (int, 'Monitoring', 0),
    'TWITTER_ENABLED': (int, 'Twitter', 0),
    'TWITTER_PASSWORD': (str, 'Twitter', ''),
    'TWITTER_PREFIX': (str, 'Twitter', 'Headphones'),
    'TWITTER_USERNAME': (str, 'Twitter', ''),
    'UPDATE_DB_INTERVAL': (int, 'General', 24),
    'VERIFY_SSL_CERT': (bool_int, 'Advanced', 1),
    'VIDEO_LOGGING_ENABLE': (int, 'Monitoring', 1),
    'XBMC_ENABLED': (int, 'XBMC', 0),
    'XBMC_HOST': (str, 'XBMC', ''),
    'XBMC_PASSWORD': (str, 'XBMC', ''),
    'XBMC_USERNAME': (str, 'XBMC', ''),
    'XBMC_ON_PLAY': (int, 'XBMC', 0),
    'XBMC_ON_STOP': (int, 'XBMC', 0),
    'XBMC_ON_WATCHED': (int, 'XBMC', 0)
}
# pylint:disable=R0902
# it might be nice to refactor for fewer instance variables
class Config(object):
    """ Wraps access to particular values in a config file """

    def __init__(self, config_file):
        """ Initialize the config with values from a file """
        self._config_file = config_file
        self._config = ConfigObj(self._config_file, encoding='utf-8')
        for key in _CONFIG_DEFINITIONS.keys():
            self.check_setting(key)

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
        for key in _CONFIG_DEFINITIONS.keys():
            key, definition_type, section, ini_key, default = self._define(key)
            self.check_setting(key)
            if section not in new_config:
                new_config[section] = {}
            new_config[section][ini_key] = self._config[section][ini_key]

        # Write it to file
        plexpy.logger.info("Writing configuration to file")

        try:
            new_config.write()
        except IOError as e:
            plexpy.logger.error("Error writing configuration file: %s", e)

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

    def process_kwargs(self, kwargs):
        """
        Given a big bunch of key value pairs, apply them to the ini.
        """
        for name, value in kwargs.items():
            key, definition_type, section, ini_key, default = self._define(name)
            self._config[section][ini_key] = definition_type(value)