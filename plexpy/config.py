# This file is part of PlexPy.
#
#  PlexPy is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  PlexPy is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PlexPy.  If not, see <http://www.gnu.org/licenses/>.

import arrow
import os
import re
import shutil

from configobj import ConfigObj

import plexpy
import logger


def bool_int(value):
    """
    Casts a config value into a 0 or 1
    """
    if isinstance(value, basestring):
        if value.lower() in ('', '0', 'false', 'f', 'no', 'n', 'off'):
            value = 0
    return int(bool(value))

FILENAME = "config.ini"

_CONFIG_DEFINITIONS = {
    'ALLOW_GUEST_ACCESS': (int, 'General', 0),
    'DATE_FORMAT': (str, 'General', 'YYYY-MM-DD'),
    'GROUPING_GLOBAL_HISTORY': (int, 'PlexWatch', 0),
    'GROUPING_USER_HISTORY': (int, 'PlexWatch', 0),
    'GROUPING_CHARTS': (int, 'PlexWatch', 0),
    'PLEXWATCH_DATABASE': (str, 'PlexWatch', ''),
    'PMS_IDENTIFIER': (str, 'PMS', ''),
    'PMS_IP': (str, 'PMS', '127.0.0.1'),
    'PMS_IS_REMOTE': (int, 'PMS', 0),
    'PMS_LOGS_FOLDER': (str, 'PMS', ''),
    'PMS_LOGS_LINE_CAP': (int, 'PMS', 1000),
    'PMS_NAME': (unicode, 'PMS', ''),
    'PMS_PORT': (int, 'PMS', 32400),
    'PMS_TOKEN': (str, 'PMS', ''),
    'PMS_SSL': (int, 'PMS', 0),
    'PMS_URL': (str, 'PMS', ''),
    'PMS_USE_BIF': (int, 'PMS', 0),
    'PMS_UUID': (str, 'PMS', ''),
    'PMS_TIMEOUT': (int, 'Advanced', 15),
    'TIME_FORMAT': (str, 'General', 'HH:mm'),
    'ANON_REDIRECT': (str, 'General', 'http://dereferer.org/?'),
    'API_ENABLED': (int, 'General', 0),
    'API_KEY': (str, 'General', ''),
    'API_SQL': (int, 'General', 0),
    'BOXCAR_ENABLED': (int, 'Boxcar', 0),
    'BOXCAR_TOKEN': (str, 'Boxcar', ''),
    'BOXCAR_SOUND': (str, 'Boxcar', ''),
    'BOXCAR_ON_PLAY': (int, 'Boxcar', 0),
    'BOXCAR_ON_STOP': (int, 'Boxcar', 0),
    'BOXCAR_ON_PAUSE': (int, 'Boxcar', 0),
    'BOXCAR_ON_RESUME': (int, 'Boxcar', 0),
    'BOXCAR_ON_BUFFER': (int, 'Boxcar', 0),
    'BOXCAR_ON_WATCHED': (int, 'Boxcar', 0),
    'BOXCAR_ON_CREATED': (int, 'Boxcar', 0),
    'BOXCAR_ON_EXTDOWN': (int, 'Boxcar', 0),
    'BOXCAR_ON_INTDOWN': (int, 'Boxcar', 0),
    'BOXCAR_ON_EXTUP': (int, 'Boxcar', 0),
    'BOXCAR_ON_INTUP': (int, 'Boxcar', 0),
    'BOXCAR_ON_PMSUPDATE': (int, 'Boxcar', 0),
    'BROWSER_ENABLED': (int, 'Boxcar', 0),
    'BROWSER_AUTO_HIDE_DELAY': (int, 'Boxcar', 5),
    'BROWSER_ON_PLAY': (int, 'BROWSER', 0),
    'BROWSER_ON_STOP': (int, 'BROWSER', 0),
    'BROWSER_ON_PAUSE': (int, 'BROWSER', 0),
    'BROWSER_ON_RESUME': (int, 'BROWSER', 0),
    'BROWSER_ON_BUFFER': (int, 'BROWSER', 0),
    'BROWSER_ON_WATCHED': (int, 'BROWSER', 0),
    'BROWSER_ON_CREATED': (int, 'BROWSER', 0),
    'BROWSER_ON_EXTDOWN': (int, 'BROWSER', 0),
    'BROWSER_ON_INTDOWN': (int, 'BROWSER', 0),
    'BROWSER_ON_EXTUP': (int, 'BROWSER', 0),
    'BROWSER_ON_INTUP': (int, 'BROWSER', 0),
    'BROWSER_ON_PMSUPDATE': (int, 'BROWSER', 0),
    'BUFFER_THRESHOLD': (int, 'Monitoring', 3),
    'BUFFER_WAIT': (int, 'Monitoring', 900),
    'BACKUP_DIR': (str, 'General', ''),
    'CACHE_DIR': (str, 'General', ''),
    'CACHE_IMAGES': (int, 'General', 1),
    'CACHE_SIZEMB': (int, 'Advanced', 32),
    'CHECK_GITHUB': (int, 'General', 1),
    'CHECK_GITHUB_INTERVAL': (int, 'General', 360),
    'CHECK_GITHUB_ON_STARTUP': (int, 'General', 1),
    'CLEANUP_FILES': (int, 'General', 0),
    'CONFIG_VERSION': (str, 'General', '0'),
    'DO_NOT_OVERRIDE_GIT_BRANCH': (int, 'General', 0),
    'EMAIL_ENABLED': (int, 'Email', 0),
    'EMAIL_FROM_NAME': (str, 'Email', 'PlexPy'),
    'EMAIL_FROM': (str, 'Email', ''),
    'EMAIL_TO': (str, 'Email', ''),
    'EMAIL_CC': (str, 'Email', ''),
    'EMAIL_BCC': (str, 'Email', ''),
    'EMAIL_SMTP_SERVER': (str, 'Email', ''),
    'EMAIL_SMTP_USER': (str, 'Email', ''),
    'EMAIL_SMTP_PASSWORD': (str, 'Email', ''),
    'EMAIL_SMTP_PORT': (int, 'Email', 25),
    'EMAIL_TLS': (int, 'Email', 0),
    'EMAIL_HTML_SUPPORT': (int, 'Email', 1),
    'EMAIL_ON_PLAY': (int, 'Email', 0),
    'EMAIL_ON_STOP': (int, 'Email', 0),
    'EMAIL_ON_PAUSE': (int, 'Email', 0),
    'EMAIL_ON_RESUME': (int, 'Email', 0),
    'EMAIL_ON_BUFFER': (int, 'Email', 0),
    'EMAIL_ON_WATCHED': (int, 'Email', 0),
    'EMAIL_ON_CREATED': (int, 'Email', 0),
    'EMAIL_ON_EXTDOWN': (int, 'Email', 0),
    'EMAIL_ON_INTDOWN': (int, 'Email', 0),
    'EMAIL_ON_EXTUP': (int, 'Email', 0),
    'EMAIL_ON_INTUP': (int, 'Email', 0),
    'EMAIL_ON_PMSUPDATE': (int, 'Email', 0),
    'ENABLE_HTTPS': (int, 'General', 0),
    'FACEBOOK_ENABLED': (int, 'Facebook', 0),
    'FACEBOOK_REDIRECT_URI': (str, 'Facebook', ''),
    'FACEBOOK_APP_ID': (str, 'Facebook', ''),
    'FACEBOOK_APP_SECRET': (str, 'Facebook', ''),
    'FACEBOOK_TOKEN': (str, 'Facebook', ''),
    'FACEBOOK_GROUP': (str, 'Facebook', ''),
    'FACEBOOK_INCL_PMSLINK': (int, 'Facebook', 0),
    'FACEBOOK_INCL_POSTER': (int, 'Facebook', 1),
    'FACEBOOK_INCL_SUBJECT': (int, 'Facebook', 1),
    'FACEBOOK_ON_PLAY': (int, 'Facebook', 0),
    'FACEBOOK_ON_STOP': (int, 'Facebook', 0),
    'FACEBOOK_ON_PAUSE': (int, 'Facebook', 0),
    'FACEBOOK_ON_RESUME': (int, 'Facebook', 0),
    'FACEBOOK_ON_BUFFER': (int, 'Facebook', 0),
    'FACEBOOK_ON_WATCHED': (int, 'Facebook', 0),
    'FACEBOOK_ON_CREATED': (int, 'Facebook', 0),
    'FACEBOOK_ON_EXTDOWN': (int, 'Facebook', 0),
    'FACEBOOK_ON_INTDOWN': (int, 'Facebook', 0),
    'FACEBOOK_ON_EXTUP': (int, 'Facebook', 0),
    'FACEBOOK_ON_INTUP': (int, 'Facebook', 0),
    'FACEBOOK_ON_PMSUPDATE': (int, 'Facebook', 0),
    'FIRST_RUN_COMPLETE': (int, 'General', 0),
    'FREEZE_DB': (int, 'General', 0),
    'GET_FILE_SIZES': (int, 'General', 0),
    'GET_FILE_SIZES_HOLD': (dict, 'General', {'section_ids': [], 'rating_keys': []}),
    'GIT_BRANCH': (str, 'General', 'master'),
    'GIT_PATH': (str, 'General', ''),
    'GIT_TOKEN': (str, 'General', ''),
    'GIT_USER': (str, 'General', 'drzoidberg33'),
    'GRAPH_TYPE': (str, 'General', 'plays'),
    'GRAPH_DAYS': (int, 'General', 30),
    'GRAPH_TAB': (str, 'General', 'tabs-1'),
    'GROUP_HISTORY_TABLES': (int, 'General', 0),
    'GROWL_ENABLED': (int, 'Growl', 0),
    'GROWL_HOST': (str, 'Growl', ''),
    'GROWL_PASSWORD': (str, 'Growl', ''),
    'GROWL_ON_PLAY': (int, 'Growl', 0),
    'GROWL_ON_STOP': (int, 'Growl', 0),
    'GROWL_ON_PAUSE': (int, 'Growl', 0),
    'GROWL_ON_RESUME': (int, 'Growl', 0),
    'GROWL_ON_BUFFER': (int, 'Growl', 0),
    'GROWL_ON_WATCHED': (int, 'Growl', 0),
    'GROWL_ON_CREATED': (int, 'Growl', 0),
    'GROWL_ON_EXTDOWN': (int, 'Growl', 0),
    'GROWL_ON_INTDOWN': (int, 'Growl', 0),
    'GROWL_ON_EXTUP': (int, 'Growl', 0),
    'GROWL_ON_INTUP': (int, 'Growl', 0),
    'GROWL_ON_PMSUPDATE': (int, 'Growl', 0),
    'HOME_SECTIONS': (list, 'General', ['current_activity','watch_stats','library_stats','recently_added']),
    'HOME_LIBRARY_CARDS': (list, 'General', ['first_run']),
    'HOME_STATS_LENGTH': (int, 'General', 30),
    'HOME_STATS_TYPE': (int, 'General', 0),
    'HOME_STATS_COUNT': (int, 'General', 5),
    'HOME_STATS_CARDS': (list, 'General', ['top_movies', 'popular_movies', 'top_tv', 'popular_tv', 'top_music', \
        'popular_music', 'last_watched', 'top_users', 'top_platforms', 'most_concurrent']),
    'HTTPS_CREATE_CERT': (int, 'General', 1),
    'HTTPS_CERT': (str, 'General', ''),
    'HTTPS_KEY': (str, 'General', ''),
    'HTTPS_DOMAIN': (str, 'General', 'localhost'),
    'HTTPS_IP': (str, 'General', '127.0.0.1'),
    'HTTP_BASIC_AUTH': (int, 'General', 0),
    'HTTP_ENVIRONMENT': (str, 'General', 'production'),
    'HTTP_HASH_PASSWORD': (int, 'General', 0),
    'HTTP_HASHED_PASSWORD': (int, 'General', 0),
    'HTTP_HOST': (str, 'General', '0.0.0.0'),
    'HTTP_PASSWORD': (str, 'General', ''),
    'HTTP_PORT': (int, 'General', 8181),
    'HTTP_PROXY': (int, 'General', 0),
    'HTTP_ROOT': (str, 'General', ''),
    'HTTP_USERNAME': (str, 'General', ''),
    'INTERFACE': (str, 'General', 'default'),
    'IP_LOGGING_ENABLE': (int, 'General', 0),
    'IFTTT_KEY': (str, 'IFTTT', ''),
    'IFTTT_EVENT': (str, 'IFTTT', 'plexpy'),
    'IFTTT_ENABLED': (int, 'IFTTT', 0),
    'IFTTT_ON_PLAY': (int, 'IFTTT', 0),
    'IFTTT_ON_STOP': (int, 'IFTTT', 0),
    'IFTTT_ON_PAUSE': (int, 'IFTTT', 0),
    'IFTTT_ON_RESUME': (int, 'IFTTT', 0),
    'IFTTT_ON_BUFFER': (int, 'IFTTT', 0),
    'IFTTT_ON_WATCHED': (int, 'IFTTT', 0),
    'IFTTT_ON_CREATED': (int, 'IFTTT', 0),
    'IFTTT_ON_EXTDOWN': (int, 'IFTTT', 0),
    'IFTTT_ON_INTDOWN': (int, 'IFTTT', 0),
    'IFTTT_ON_EXTUP': (int, 'IFTTT', 0),
    'IFTTT_ON_INTUP': (int, 'IFTTT', 0),
    'IFTTT_ON_PMSUPDATE': (int, 'IFTTT', 0),
    'IMGUR_CLIENT_ID': (str, 'Monitoring', ''),
    'JOIN_APIKEY': (str, 'Join', ''),
    'JOIN_DEVICEID': (str, 'Join', ''),
    'JOIN_ENABLED': (int, 'Join', 0),
    'JOIN_ON_PLAY': (int, 'Join', 0),
    'JOIN_ON_STOP': (int, 'Join', 0),
    'JOIN_ON_PAUSE': (int, 'Join', 0),
    'JOIN_ON_RESUME': (int, 'Join', 0),
    'JOIN_ON_BUFFER': (int, 'Join', 0),
    'JOIN_ON_WATCHED': (int, 'Join', 0),
    'JOIN_ON_CREATED': (int, 'Join', 0),
    'JOIN_ON_EXTDOWN': (int, 'Join', 0),
    'JOIN_ON_INTDOWN': (int, 'Join', 0),
    'JOIN_ON_EXTUP': (int, 'Join', 0),
    'JOIN_ON_INTUP': (int, 'Join', 0),
    'JOIN_ON_PMSUPDATE': (int, 'Join', 0),
    'JOURNAL_MODE': (str, 'Advanced', 'wal'),
    'LAUNCH_BROWSER': (int, 'General', 1),
    'LOG_BLACKLIST': (int, 'General', 1),
    'LOG_DIR': (str, 'General', ''),
    'LOGGING_IGNORE_INTERVAL': (int, 'Monitoring', 120),
    'MOVIE_LOGGING_ENABLE': (int, 'Monitoring', 1),
    'MOVIE_NOTIFY_ENABLE': (int, 'Monitoring', 0),
    'MOVIE_NOTIFY_ON_START': (int, 'Monitoring', 1),
    'MOVIE_NOTIFY_ON_STOP': (int, 'Monitoring', 0),
    'MOVIE_NOTIFY_ON_PAUSE': (int, 'Monitoring', 0),
    'MUSIC_LOGGING_ENABLE': (int, 'Monitoring', 1),
    'MUSIC_NOTIFY_ENABLE': (int, 'Monitoring', 0),
    'MUSIC_NOTIFY_ON_START': (int, 'Monitoring', 1),
    'MUSIC_NOTIFY_ON_STOP': (int, 'Monitoring', 0),
    'MUSIC_NOTIFY_ON_PAUSE': (int, 'Monitoring', 0),
    'MONITOR_PMS_UPDATES': (int, 'Monitoring', 0),
    'MONITOR_REMOTE_ACCESS': (int, 'Monitoring', 0),
    'MONITORING_INTERVAL': (int, 'Monitoring', 60),
    'MONITORING_USE_WEBSOCKET': (int, 'Monitoring', 0),
    'NMA_APIKEY': (str, 'NMA', ''),
    'NMA_ENABLED': (int, 'NMA', 0),
    'NMA_PRIORITY': (int, 'NMA', 0),
    'NMA_ON_PLAY': (int, 'NMA', 0),
    'NMA_ON_STOP': (int, 'NMA', 0),
    'NMA_ON_PAUSE': (int, 'NMA', 0),
    'NMA_ON_RESUME': (int, 'NMA', 0),
    'NMA_ON_BUFFER': (int, 'NMA', 0),
    'NMA_ON_WATCHED': (int, 'NMA', 0),
    'NMA_ON_CREATED': (int, 'NMA', 0),
    'NMA_ON_EXTDOWN': (int, 'NMA', 0),
    'NMA_ON_INTDOWN': (int, 'NMA', 0),
    'NMA_ON_EXTUP': (int, 'NMA', 0),
    'NMA_ON_INTUP': (int, 'NMA', 0),
    'NMA_ON_PMSUPDATE': (int, 'NMA', 0),
    'NOTIFY_CONSECUTIVE': (int, 'Monitoring', 1),
    'NOTIFY_UPLOAD_POSTERS': (int, 'Monitoring', 0),
    'NOTIFY_RECENTLY_ADDED': (int, 'Monitoring', 0),
    'NOTIFY_RECENTLY_ADDED_GRANDPARENT': (int, 'Monitoring', 0),
    'NOTIFY_RECENTLY_ADDED_DELAY': (int, 'Monitoring', 60),
    'NOTIFY_WATCHED_PERCENT': (int, 'Monitoring', 85),
    'NOTIFY_ON_START_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_START_BODY_TEXT': (unicode, 'Monitoring', '{user} ({player}) started playing {title}.'),
    'NOTIFY_ON_STOP_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_STOP_BODY_TEXT': (unicode, 'Monitoring', '{user} ({player}) has stopped {title}.'),
    'NOTIFY_ON_PAUSE_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_PAUSE_BODY_TEXT': (unicode, 'Monitoring', '{user} ({player}) has paused {title}.'),
    'NOTIFY_ON_RESUME_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_RESUME_BODY_TEXT': (unicode, 'Monitoring', '{user} ({player}) has resumed {title}.'),
    'NOTIFY_ON_BUFFER_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_BUFFER_BODY_TEXT': (unicode, 'Monitoring', '{user} ({player}) is buffering {title}.'),
    'NOTIFY_ON_WATCHED_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_WATCHED_BODY_TEXT': (unicode, 'Monitoring', '{user} ({player}) has watched {title}.'),
    'NOTIFY_ON_CREATED_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_CREATED_BODY_TEXT': (unicode, 'Monitoring', '{title} was recently added to Plex.'),
    'NOTIFY_ON_EXTDOWN_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_EXTDOWN_BODY_TEXT': (unicode, 'Monitoring', 'The Plex Media Server remote access is down.'),
    'NOTIFY_ON_INTDOWN_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_INTDOWN_BODY_TEXT': (unicode, 'Monitoring', 'The Plex Media Server is down.'),
    'NOTIFY_ON_EXTUP_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_EXTUP_BODY_TEXT': (unicode, 'Monitoring', 'The Plex Media Server remote access is back up.'),
    'NOTIFY_ON_INTUP_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_INTUP_BODY_TEXT': (unicode, 'Monitoring', 'The Plex Media Server is back up.'),
    'NOTIFY_ON_PMSUPDATE_SUBJECT_TEXT': (unicode, 'Monitoring', 'PlexPy ({server_name})'),
    'NOTIFY_ON_PMSUPDATE_BODY_TEXT': (unicode, 'Monitoring', 'An update is available for the Plex Media Server (version {update_version}).'),
    'NOTIFY_SCRIPTS_ARGS_TEXT': (unicode, 'Monitoring', ''),
    'OSX_NOTIFY_APP': (str, 'OSX_Notify', '/Applications/PlexPy'),
    'OSX_NOTIFY_ENABLED': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_PLAY': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_STOP': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_PAUSE': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_RESUME': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_BUFFER': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_WATCHED': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_CREATED': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_EXTDOWN': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_INTDOWN': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_EXTUP': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_INTUP': (int, 'OSX_Notify', 0),
    'OSX_NOTIFY_ON_PMSUPDATE': (int, 'OSX_Notify', 0),
    'PLEX_CLIENT_HOST': (str, 'Plex', ''),
    'PLEX_ENABLED': (int, 'Plex', 0),
    'PLEX_PASSWORD': (str, 'Plex', ''),
    'PLEX_USERNAME': (str, 'Plex', ''),
    'PLEX_ON_PLAY': (int, 'Plex', 0),
    'PLEX_ON_STOP': (int, 'Plex', 0),
    'PLEX_ON_PAUSE': (int, 'Plex', 0),
    'PLEX_ON_RESUME': (int, 'Plex', 0),
    'PLEX_ON_BUFFER': (int, 'Plex', 0),
    'PLEX_ON_WATCHED': (int, 'Plex', 0),
    'PLEX_ON_CREATED': (int, 'Plex', 0),
    'PLEX_ON_EXTDOWN': (int, 'Plex', 0),
    'PLEX_ON_INTDOWN': (int, 'Plex', 0),
    'PLEX_ON_EXTUP': (int, 'Plex', 0),
    'PLEX_ON_INTUP': (int, 'Plex', 0),
    'PLEX_ON_PMSUPDATE': (int, 'Plex', 0),
    'PROWL_ENABLED': (int, 'Prowl', 0),
    'PROWL_KEYS': (str, 'Prowl', ''),
    'PROWL_PRIORITY': (int, 'Prowl', 0),
    'PROWL_ON_PLAY': (int, 'Prowl', 0),
    'PROWL_ON_STOP': (int, 'Prowl', 0),
    'PROWL_ON_PAUSE': (int, 'Prowl', 0),
    'PROWL_ON_RESUME': (int, 'Prowl', 0),
    'PROWL_ON_BUFFER': (int, 'Prowl', 0),
    'PROWL_ON_WATCHED': (int, 'Prowl', 0),
    'PROWL_ON_CREATED': (int, 'Prowl', 0),
    'PROWL_ON_EXTDOWN': (int, 'Prowl', 0),
    'PROWL_ON_INTDOWN': (int, 'Prowl', 0),
    'PROWL_ON_EXTUP': (int, 'Prowl', 0),
    'PROWL_ON_INTUP': (int, 'Prowl', 0),
    'PROWL_ON_PMSUPDATE': (int, 'Prowl', 0),
    'PUSHALOT_APIKEY': (str, 'Pushalot', ''),
    'PUSHALOT_ENABLED': (int, 'Pushalot', 0),
    'PUSHALOT_ON_PLAY': (int, 'Pushalot', 0),
    'PUSHALOT_ON_STOP': (int, 'Pushalot', 0),
    'PUSHALOT_ON_PAUSE': (int, 'Pushalot', 0),
    'PUSHALOT_ON_RESUME': (int, 'Pushalot', 0),
    'PUSHALOT_ON_BUFFER': (int, 'Pushalot', 0),
    'PUSHALOT_ON_WATCHED': (int, 'Pushalot', 0),
    'PUSHALOT_ON_CREATED': (int, 'Pushalot', 0),
    'PUSHALOT_ON_EXTDOWN': (int, 'Pushalot', 0),
    'PUSHALOT_ON_INTDOWN': (int, 'Pushalot', 0),
    'PUSHALOT_ON_EXTUP': (int, 'Pushalot', 0),
    'PUSHALOT_ON_INTUP': (int, 'Pushalot', 0),
    'PUSHALOT_ON_PMSUPDATE': (int, 'Pushalot', 0),
    'PUSHBULLET_APIKEY': (str, 'PushBullet', ''),
    'PUSHBULLET_DEVICEID': (str, 'PushBullet', ''),
    'PUSHBULLET_CHANNEL_TAG': (str, 'PushBullet', ''),
    'PUSHBULLET_ENABLED': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_PLAY': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_STOP': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_PAUSE': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_RESUME': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_BUFFER': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_WATCHED': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_CREATED': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_EXTDOWN': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_INTDOWN': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_EXTUP': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_INTUP': (int, 'PushBullet', 0),
    'PUSHBULLET_ON_PMSUPDATE': (int, 'PushBullet', 0),
    'PUSHOVER_APITOKEN': (str, 'Pushover', ''),
    'PUSHOVER_ENABLED': (int, 'Pushover', 0),
    'PUSHOVER_HTML_SUPPORT': (int, 'Pushover', 1),
    'PUSHOVER_KEYS': (str, 'Pushover', ''),
    'PUSHOVER_PRIORITY': (int, 'Pushover', 0),
    'PUSHOVER_SOUND': (str, 'Pushover', ''),
    'PUSHOVER_ON_PLAY': (int, 'Pushover', 0),
    'PUSHOVER_ON_STOP': (int, 'Pushover', 0),
    'PUSHOVER_ON_PAUSE': (int, 'Pushover', 0),
    'PUSHOVER_ON_RESUME': (int, 'Pushover', 0),
    'PUSHOVER_ON_BUFFER': (int, 'Pushover', 0),
    'PUSHOVER_ON_WATCHED': (int, 'Pushover', 0),
    'PUSHOVER_ON_CREATED': (int, 'Pushover', 0),
    'PUSHOVER_ON_EXTDOWN': (int, 'Pushover', 0),
    'PUSHOVER_ON_INTDOWN': (int, 'Pushover', 0),
    'PUSHOVER_ON_EXTUP': (int, 'Pushover', 0),
    'PUSHOVER_ON_INTUP': (int, 'Pushover', 0),
    'PUSHOVER_ON_PMSUPDATE': (int, 'Pushover', 0),
    'REFRESH_LIBRARIES_INTERVAL': (int, 'Monitoring', 12),
    'REFRESH_LIBRARIES_ON_STARTUP': (int, 'Monitoring', 1),
    'REFRESH_USERS_INTERVAL': (int, 'Monitoring', 12),
    'REFRESH_USERS_ON_STARTUP': (int, 'Monitoring', 1),
    'SESSION_DB_WRITE_ATTEMPTS': (int, 'Monitoring', 5),
    'SLACK_ENABLED': (int, 'Slack', 0),
    'SLACK_HOOK': (str, 'Slack', ''),
    'SLACK_CHANNEL': (str, 'Slack', ''),
    'SLACK_ICON_EMOJI': (str, 'Slack', ''),
    'SLACK_INCL_PMSLINK': (int, 'Slack', 0),
    'SLACK_INCL_POSTER': (int, 'Slack', 1),
    'SLACK_INCL_SUBJECT': (int, 'Slack', 1),
    'SLACK_USERNAME': (str, 'Slack', ''),
    'SLACK_ON_PLAY': (int, 'Slack', 0),
    'SLACK_ON_STOP': (int, 'Slack', 0),
    'SLACK_ON_PAUSE': (int, 'Slack', 0),
    'SLACK_ON_RESUME': (int, 'Slack', 0),
    'SLACK_ON_BUFFER': (int, 'Slack', 0),
    'SLACK_ON_WATCHED': (int, 'Slack', 0),
    'SLACK_ON_CREATED': (int, 'Slack', 0),
    'SLACK_ON_EXTDOWN': (int, 'Slack', 0),
    'SLACK_ON_INTDOWN': (int, 'Slack', 0),
    'SLACK_ON_EXTUP': (int, 'Slack', 0),
    'SLACK_ON_INTUP': (int, 'Slack', 0),
    'SLACK_ON_PMSUPDATE': (int, 'Slack', 0),
    'SCRIPTS_ENABLED': (int, 'Scripts', 0),
    'SCRIPTS_FOLDER': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_PLAY': (int, 'Scripts', 0),
    'SCRIPTS_ON_STOP': (int, 'Scripts', 0),
    'SCRIPTS_ON_PAUSE': (int, 'Scripts', 0),
    'SCRIPTS_ON_RESUME': (int, 'Scripts', 0),
    'SCRIPTS_ON_BUFFER': (int, 'Scripts', 0),
    'SCRIPTS_ON_WATCHED': (int, 'Scripts', 0),
    'SCRIPTS_ON_CREATED': (int, 'Scripts', 0),
    'SCRIPTS_ON_EXTDOWN': (int, 'Scripts', 0),
    'SCRIPTS_ON_EXTUP': (int, 'Scripts', 0),
    'SCRIPTS_ON_INTDOWN': (int, 'Scripts', 0),
    'SCRIPTS_ON_INTUP': (int, 'Scripts', 0),
    'SCRIPTS_ON_PMSUPDATE': (int, 'Scripts', 0),
    'SCRIPTS_ON_PLAY_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_STOP_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_PAUSE_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_RESUME_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_BUFFER_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_WATCHED_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_CREATED_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_EXTDOWN_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_EXTUP_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_INTDOWN_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_INTUP_SCRIPT': (unicode, 'Scripts', ''),
    'SCRIPTS_ON_PMSUPDATE_SCRIPT': (unicode, 'Scripts', ''),
    'TELEGRAM_BOT_TOKEN': (str, 'Telegram', ''),
    'TELEGRAM_ENABLED': (int, 'Telegram', 0),
    'TELEGRAM_CHAT_ID': (str, 'Telegram', ''),
    'TELEGRAM_HTML_SUPPORT': (int, 'Telegram', 1),
    'TELEGRAM_INCL_POSTER': (int, 'Telegram', 0),
    'TELEGRAM_INCL_SUBJECT': (int, 'Telegram', 1),
    'TELEGRAM_ON_PLAY': (int, 'Telegram', 0),
    'TELEGRAM_ON_STOP': (int, 'Telegram', 0),
    'TELEGRAM_ON_PAUSE': (int, 'Telegram', 0),
    'TELEGRAM_ON_RESUME': (int, 'Telegram', 0),
    'TELEGRAM_ON_BUFFER': (int, 'Telegram', 0),
    'TELEGRAM_ON_WATCHED': (int, 'Telegram', 0),
    'TELEGRAM_ON_CREATED': (int, 'Telegram', 0),
    'TELEGRAM_ON_EXTDOWN': (int, 'Telegram', 0),
    'TELEGRAM_ON_INTDOWN': (int, 'Telegram', 0),
    'TELEGRAM_ON_EXTUP': (int, 'Telegram', 0),
    'TELEGRAM_ON_INTUP': (int, 'Telegram', 0),
    'TELEGRAM_ON_PMSUPDATE': (int, 'Telegram', 0),
    'TV_LOGGING_ENABLE': (int, 'Monitoring', 1),
    'TV_NOTIFY_ENABLE': (int, 'Monitoring', 0),
    'TV_NOTIFY_ON_START': (int, 'Monitoring', 1),
    'TV_NOTIFY_ON_STOP': (int, 'Monitoring', 0),
    'TV_NOTIFY_ON_PAUSE': (int, 'Monitoring', 0),
    'TWITTER_ENABLED': (int, 'Twitter', 0),
    'TWITTER_ACCESS_TOKEN': (str, 'Twitter', ''),
    'TWITTER_ACCESS_TOKEN_SECRET': (str, 'Twitter', ''),
    'TWITTER_CONSUMER_KEY': (str, 'Twitter', ''),
    'TWITTER_CONSUMER_SECRET': (str, 'Twitter', ''),
    'TWITTER_INCL_POSTER': (int, 'Twitter', 1),
    'TWITTER_INCL_SUBJECT': (int, 'Twitter', 1),
    'TWITTER_ON_PLAY': (int, 'Twitter', 0),
    'TWITTER_ON_STOP': (int, 'Twitter', 0),
    'TWITTER_ON_PAUSE': (int, 'Twitter', 0),
    'TWITTER_ON_RESUME': (int, 'Twitter', 0),
    'TWITTER_ON_BUFFER': (int, 'Twitter', 0),
    'TWITTER_ON_WATCHED': (int, 'Twitter', 0),
    'TWITTER_ON_CREATED': (int, 'Twitter', 0),
    'TWITTER_ON_EXTDOWN': (int, 'Twitter', 0),
    'TWITTER_ON_INTDOWN': (int, 'Twitter', 0),
    'TWITTER_ON_EXTUP': (int, 'Twitter', 0),
    'TWITTER_ON_INTUP': (int, 'Twitter', 0),
    'TWITTER_ON_PMSUPDATE': (int, 'Twitter', 0),
    'UPDATE_DB_INTERVAL': (int, 'General', 24),
    'UPDATE_SECTION_IDS': (int, 'General', 1),
    'UPDATE_LABELS': (int, 'General', 1),
    'VERIFY_SSL_CERT': (bool_int, 'Advanced', 1),
    'VIDEO_LOGGING_ENABLE': (int, 'Monitoring', 1),
    'XBMC_ENABLED': (int, 'XBMC', 0),
    'XBMC_HOST': (str, 'XBMC', ''),
    'XBMC_PASSWORD': (str, 'XBMC', ''),
    'XBMC_USERNAME': (str, 'XBMC', ''),
    'XBMC_ON_PLAY': (int, 'XBMC', 0),
    'XBMC_ON_STOP': (int, 'XBMC', 0),
    'XBMC_ON_PAUSE': (int, 'XBMC', 0),
    'XBMC_ON_RESUME': (int, 'XBMC', 0),
    'XBMC_ON_BUFFER': (int, 'XBMC', 0),
    'XBMC_ON_WATCHED': (int, 'XBMC', 0),
    'XBMC_ON_CREATED': (int, 'XBMC', 0),
    'XBMC_ON_EXTDOWN': (int, 'XBMC', 0),
    'XBMC_ON_INTDOWN': (int, 'XBMC', 0),
    'XBMC_ON_EXTUP': (int, 'XBMC', 0),
    'XBMC_ON_INTUP': (int, 'XBMC', 0),
    'XBMC_ON_PMSUPDATE': (int, 'XBMC', 0)
}

_BLACKLIST_KEYS = ['_APITOKEN', '_TOKEN', '_KEY', '_SECRET', '_PASSWORD', '_APIKEY', '_ID']
_WHITELIST_KEYS = ['HTTPS_KEY', 'UPDATE_SECTION_IDS']


def make_backup(cleanup=False, scheduler=False):
    """ Makes a backup of config file, removes all but the last 5 backups """

    if scheduler:
        backup_file = 'config.backup-%s.sched.ini' % arrow.now().format('YYYYMMDDHHmmss')
    else:
        backup_file = 'config.backup-%s.ini' % arrow.now().format('YYYYMMDDHHmmss')
    backup_folder = plexpy.CONFIG.BACKUP_DIR
    backup_file_fp = os.path.join(backup_folder, backup_file)

    # In case the user has deleted it manually
    if not os.path.exists(backup_folder):
        os.makedirs(backup_folder)

    plexpy.CONFIG.write()
    shutil.copyfile(plexpy.CONFIG_FILE, backup_file_fp)

    if cleanup:
        # Delete all scheduled backup files except from the last 5.
        for root, dirs, files in os.walk(backup_folder):
            db_files = [os.path.join(root, f) for f in files if f.endswith('.sched.ini')]
            if len(db_files) > 5:
                backups_sorted_on_age = sorted(db_files, key=os.path.getctime, reverse=True)
                for file_ in backups_sorted_on_age[5:]:
                    try:
                        os.remove(file_)
                    except OSError as e:
                        logger.error(u"PlexPy Config :: Failed to delete %s from the backup folder: %s" % (file_, e))

    if backup_file in os.listdir(backup_folder):
        logger.debug(u"PlexPy Config :: Successfully backed up %s to %s" % (plexpy.CONFIG_FILE, backup_file))
        return True
    else:
        logger.warn(u"PlexPy Config :: Failed to backup %s to %s" % (plexpy.CONFIG_FILE, backup_file))
        return False


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
        self._upgrade()
        self._blacklist()

    def _blacklist(self):
        """ Add tokens and passwords to blacklisted words in logger """
        blacklist = []

        for key, subkeys in self._config.iteritems():
            for subkey, value in subkeys.iteritems():
                if isinstance(value, basestring) and len(value.strip()) > 5 and \
                    subkey.upper() not in _WHITELIST_KEYS and any(bk in subkey.upper() for bk in _BLACKLIST_KEYS):
                    blacklist.append(value.strip())

        logger._BLACKLIST_WORDS = blacklist

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
        logger.info(u"PlexPy Config :: Writing configuration to file")

        try:
            new_config.write()
        except IOError as e:
            logger.error(u"PlexPy Config :: Error writing configuration file: %s", e)

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
        if self.CONFIG_VERSION == '0':
            # Separate out movie and tv notifications
            if self.MOVIE_NOTIFY_ENABLE == 1:
                self.TV_NOTIFY_ENABLE = 1
            # Separate out movie and tv logging
            if self.VIDEO_LOGGING_ENABLE == 0:
                self.MOVIE_LOGGING_ENABLE = 0
                self.TV_LOGGING_ENABLE = 0
            self.CONFIG_VERSION = '1'

        if self.CONFIG_VERSION == '1':
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
            self.CONFIG_VERSION = '2'

        if self.CONFIG_VERSION == '2':
            self.NOTIFY_ON_START_SUBJECT_TEXT = self.NOTIFY_ON_START_SUBJECT_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_START_BODY_TEXT = self.NOTIFY_ON_START_BODY_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_STOP_SUBJECT_TEXT = self.NOTIFY_ON_STOP_SUBJECT_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_STOP_BODY_TEXT = self.NOTIFY_ON_STOP_BODY_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_PAUSE_SUBJECT_TEXT = self.NOTIFY_ON_PAUSE_SUBJECT_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_PAUSE_BODY_TEXT = self.NOTIFY_ON_PAUSE_BODY_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_RESUME_SUBJECT_TEXT = self.NOTIFY_ON_RESUME_SUBJECT_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_RESUME_BODY_TEXT = self.NOTIFY_ON_RESUME_BODY_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_BUFFER_SUBJECT_TEXT = self.NOTIFY_ON_BUFFER_SUBJECT_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_BUFFER_BODY_TEXT = self.NOTIFY_ON_BUFFER_BODY_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_WATCHED_SUBJECT_TEXT = self.NOTIFY_ON_WATCHED_SUBJECT_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_ON_WATCHED_BODY_TEXT = self.NOTIFY_ON_WATCHED_BODY_TEXT.replace('{progress}','{progress_duration}')
            self.NOTIFY_SCRIPTS_ARGS_TEXT = self.NOTIFY_SCRIPTS_ARGS_TEXT.replace('{progress}','{progress_duration}')
            self.CONFIG_VERSION = '3'

        if self.CONFIG_VERSION == '3':
            if self.HTTP_ROOT == '/': self.HTTP_ROOT = ''
            self.CONFIG_VERSION = '4'

        if self.CONFIG_VERSION == '4':
            if not len(self.HOME_STATS_CARDS) and 'watch_stats' in self.HOME_SECTIONS:
                home_sections = self.HOME_SECTIONS
                home_sections.remove('watch_stats')
                self.HOME_SECTIONS = home_sections
            if not len(self.HOME_LIBRARY_CARDS) and 'library_stats' in self.HOME_SECTIONS:
                home_sections = self.HOME_SECTIONS
                home_sections.remove('library_stats')
                self.HOME_SECTIONS = home_sections
            self.CONFIG_VERSION = '5'