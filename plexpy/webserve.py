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

from plexpy import logger, notifiers, plextv, pmsconnect, common, log_reader, datafactory, graphs, users
from plexpy.helpers import checked, radio

from mako.lookup import TemplateLookup
from mako import exceptions

import plexpy
import threading
import cherrypy
import hashlib
import random
import json
import os

try:
    # pylint:disable=E0611
    # ignore this error because we are catching the ImportError
    from collections import OrderedDict
    # pylint:enable=E0611
except ImportError:
    # Python 2.6.x fallback, from libs
    from ordereddict import OrderedDict


def serve_template(templatename, **kwargs):
    interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), plexpy.CONFIG.INTERFACE)

    _hplookup = TemplateLookup(directories=[template_dir])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


class WebInterface(object):

    def __init__(self):
        self.interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/')

    @cherrypy.expose
    def index(self):
        if plexpy.CONFIG.FIRST_RUN_COMPLETE:
            raise cherrypy.HTTPRedirect("home")
        else:
            raise cherrypy.HTTPRedirect("welcome")

    @cherrypy.expose
    def home(self):
        config = {
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_type": plexpy.CONFIG.HOME_STATS_TYPE,
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
        }
        return serve_template(templatename="index.html", title="Home", config=config)

    @cherrypy.expose
    def welcome(self, **kwargs):
        config = {
            "launch_browser": checked(plexpy.CONFIG.LAUNCH_BROWSER),
            "refresh_users_on_startup": checked(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_is_remote": checked(plexpy.CONFIG.PMS_IS_REMOTE),
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "pms_ssl": checked(plexpy.CONFIG.PMS_SSL),
            "pms_uuid": plexpy.CONFIG.PMS_UUID,
            "tv_notify_enable": checked(plexpy.CONFIG.TV_NOTIFY_ENABLE),
            "movie_notify_enable": checked(plexpy.CONFIG.MOVIE_NOTIFY_ENABLE),
            "music_notify_enable": checked(plexpy.CONFIG.MUSIC_NOTIFY_ENABLE),
            "tv_notify_on_start": checked(plexpy.CONFIG.TV_NOTIFY_ON_START),
            "movie_notify_on_start": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_START),
            "music_notify_on_start": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_START),
            "video_logging_enable": checked(plexpy.CONFIG.VIDEO_LOGGING_ENABLE),
            "music_logging_enable": checked(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "check_github": checked(plexpy.CONFIG.CHECK_GITHUB)
        }

        # The setup wizard just refreshes the page on submit so we must redirect to home if config set.
        # Also redirecting to home if a PMS token already exists - will remove this in future.
        if plexpy.CONFIG.FIRST_RUN_COMPLETE or plexpy.CONFIG.PMS_TOKEN:
            raise cherrypy.HTTPRedirect("home")
        else:
            return serve_template(templatename="welcome.html", title="Welcome", config=config)

    @cherrypy.expose
    def get_date_formats(self):
        if plexpy.CONFIG.DATE_FORMAT:
            date_format = plexpy.CONFIG.DATE_FORMAT
        else:
            date_format = 'YYYY-MM-DD'
        if plexpy.CONFIG.TIME_FORMAT:
            time_format = plexpy.CONFIG.TIME_FORMAT
        else:
            time_format = 'HH:mm'

        formats = {'date_format': date_format,
                   'time_format': time_format}

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(formats)

    @cherrypy.expose
    def home_stats(self, time_range='30', stat_type='0', stat_count='5', **kwargs):
        data_factory = datafactory.DataFactory()
        stats_data = data_factory.get_home_stats(time_range=time_range, stat_type=stat_type, stat_count=stat_count)

        return serve_template(templatename="home_stats.html", title="Stats", data=stats_data)

    @cherrypy.expose
    def library_stats(self, **kwargs):
        pms_connect = pmsconnect.PmsConnect()
        stats_data = pms_connect.get_library_stats()

        return serve_template(templatename="library_stats.html", title="Library Stats", data=stats_data)

    @cherrypy.expose
    def history(self):
        return serve_template(templatename="history.html", title="History")

    @cherrypy.expose
    def users(self):
        return serve_template(templatename="users.html", title="Users")

    @cherrypy.expose
    def graphs(self):
        return serve_template(templatename="graphs.html", title="Graphs")

    @cherrypy.expose
    def sync(self):
        return serve_template(templatename="sync.html", title="Synced Items")

    @cherrypy.expose
    def user(self, user=None, user_id=None):
        user_data = users.Users()
        if user_id:
            try:
                user_details = user_data.get_user_details(user_id=user_id)
            except:
                logger.warn("Unable to retrieve friendly name for user_id %s " % user_id)
        elif user:
            try:
                user_details = user_data.get_user_details(user=user)
            except:
                logger.warn("Unable to retrieve friendly name for user %s " % user)
        else:
            logger.debug(u"User page requested but no parameters received.")
            raise cherrypy.HTTPRedirect("home")

        return serve_template(templatename="user.html", title="User", data=user_details)

    @cherrypy.expose
    def edit_user_dialog(self, user=None, user_id=None, **kwargs):
        user_data = users.Users()
        if user_id:
            result = user_data.get_user_friendly_name(user_id=user_id)
            status_message = ''
        elif user:
            result = user_data.get_user_friendly_name(user=user)
            status_message = ''
        else:
            result = None
            status_message = 'An error occured.'

        return serve_template(templatename="edit_user.html", title="Edit User", data=result, status_message=status_message)

    @cherrypy.expose
    def edit_user(self, user=None, user_id=None, friendly_name=None, **kwargs):
        if 'do_notify' in kwargs:
            do_notify = kwargs.get('do_notify')
        else:
            do_notify = 0
        if 'keep_history' in kwargs:
            keep_history = kwargs.get('keep_history')
        else:
            keep_history = 0
        if 'thumb' in kwargs:
            custom_avatar = kwargs['thumb']
        else:
            custom_avatar = ''

        user_data = users.Users()
        if user_id:
            try:
                user_data.set_user_friendly_name(user_id=user_id,
                                                 friendly_name=friendly_name,
                                                 do_notify=do_notify,
                                                 keep_history=keep_history)
                user_data.set_user_profile_url(user_id=user_id,
                                               profile_url=custom_avatar)

                status_message = "Successfully updated user."
                return status_message
            except:
                status_message = "Failed to update user."
                return status_message
        if user:
            try:
                user_data.set_user_friendly_name(user=user,
                                                 friendly_name=friendly_name,
                                                 do_notify=do_notify,
                                                 keep_history=keep_history)
                user_data.set_user_profile_url(user=user,
                                               profile_url=custom_avatar)

                status_message = "Successfully updated user."
                return status_message
            except:
                status_message = "Failed to update user."
                return status_message

    @cherrypy.expose
    def get_stream_data(self, row_id=None, user=None, **kwargs):

        data_factory = datafactory.DataFactory()
        stream_data = data_factory.get_stream_details(row_id)

        return serve_template(templatename="stream_data.html", title="Stream Data", data=stream_data, user=user)

    @cherrypy.expose
    def get_ip_address_details(self, ip_address=None, **kwargs):
        import socket

        try:
            socket.inet_aton(ip_address)
        except socket.error:
            ip_address = None

        return serve_template(templatename="ip_address_modal.html", title="IP Address Details", data=ip_address)

    @cherrypy.expose
    def get_user_list(self, **kwargs):

        user_data = users.Users()
        user_list = user_data.get_user_list(kwargs=kwargs)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(user_list)

    @cherrypy.expose
    def checkGithub(self):
        from plexpy import versioncheck

        versioncheck.checkGithub()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def logs(self):
        return serve_template(templatename="logs.html", title="Log", lineList=plexpy.LOG_LIST)

    @cherrypy.expose
    def clearLogs(self):
        plexpy.LOG_LIST = []
        logger.info("Web logs cleared")
        raise cherrypy.HTTPRedirect("logs")

    @cherrypy.expose
    def toggleVerbose(self):
        plexpy.VERBOSE = not plexpy.VERBOSE
        logger.initLogger(console=not plexpy.QUIET,
                          log_dir=plexpy.CONFIG.LOG_DIR, verbose=plexpy.VERBOSE)
        logger.info("Verbose toggled, set to %s", plexpy.VERBOSE)
        logger.debug("If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect("logs")

    @cherrypy.expose
    def getLog(self, start=0, length=100, **kwargs):
        start = int(start)
        length = int(length)
        search_value = ""
        search_regex = ""
        order_column = 0
        order_dir = "desc"

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', "0")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        filtered = []
        if search_value == "":
            filtered = plexpy.LOG_LIST[::]
        else:
            filtered = [row for row in plexpy.LOG_LIST for column in row if search_value.lower() in column.lower()]

        sortcolumn = 0
        if order_column == '1':
            sortcolumn = 2
        elif order_column == '2':
            sortcolumn = 1
        filtered.sort(key=lambda x: x[sortcolumn], reverse=order_dir == "desc")

        rows = filtered[start:(start + length)]
        rows = [[row[0], row[2], row[1]] for row in rows]

        return json.dumps({
            'recordsFiltered': len(filtered),
            'recordsTotal': len(plexpy.LOG_LIST),
            'data': rows,
        })

    @cherrypy.expose
    def get_plex_log(self, window=1000, **kwargs):
        log_lines = []
        try:
            log_lines = {'data': log_reader.get_log_tail(window=window)}
        except:
            logger.warn("Unable to retrieve Plex Logs.")

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(log_lines)

    @cherrypy.expose
    def generateAPI(self):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info("New API generated")
        return apikey

    @cherrypy.expose
    def settings(self):
        interface_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if
                          os.path.isdir(os.path.join(interface_dir, name))]

        # Initialise blank passwords so we do not expose them in the html forms
        # but users are still able to clear them
        if plexpy.CONFIG.HTTP_PASSWORD != '':
            http_password = '    '
        else:
            http_password = ''

        config = {
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": http_password,
            "launch_browser": checked(plexpy.CONFIG.LAUNCH_BROWSER),
            "enable_https": checked(plexpy.CONFIG.ENABLE_HTTPS),
            "https_cert": plexpy.CONFIG.HTTPS_CERT,
            "https_key": plexpy.CONFIG.HTTPS_KEY,
            "api_enabled": checked(plexpy.CONFIG.API_ENABLED),
            "api_key": plexpy.CONFIG.API_KEY,
            "update_db_interval": plexpy.CONFIG.UPDATE_DB_INTERVAL,
            "freeze_db": checked(plexpy.CONFIG.FREEZE_DB),
            "log_dir": plexpy.CONFIG.LOG_DIR,
            "cache_dir": plexpy.CONFIG.CACHE_DIR,
            "check_github": checked(plexpy.CONFIG.CHECK_GITHUB),
            "interface_list": interface_list,
            "growl_enabled": checked(plexpy.CONFIG.GROWL_ENABLED),
            "growl_host": plexpy.CONFIG.GROWL_HOST,
            "growl_password": plexpy.CONFIG.GROWL_PASSWORD,
            "prowl_enabled": checked(plexpy.CONFIG.PROWL_ENABLED),
            "prowl_keys": plexpy.CONFIG.PROWL_KEYS,
            "prowl_priority": plexpy.CONFIG.PROWL_PRIORITY,
            "xbmc_enabled": checked(plexpy.CONFIG.XBMC_ENABLED),
            "xbmc_host": plexpy.CONFIG.XBMC_HOST,
            "xbmc_username": plexpy.CONFIG.XBMC_USERNAME,
            "xbmc_password": plexpy.CONFIG.XBMC_PASSWORD,
            "plex_enabled": checked(plexpy.CONFIG.PLEX_ENABLED),
            "plex_client_host": plexpy.CONFIG.PLEX_CLIENT_HOST,
            "plex_username": plexpy.CONFIG.PLEX_USERNAME,
            "plex_password": plexpy.CONFIG.PLEX_PASSWORD,
            "nma_enabled": checked(plexpy.CONFIG.NMA_ENABLED),
            "nma_apikey": plexpy.CONFIG.NMA_APIKEY,
            "nma_priority": int(plexpy.CONFIG.NMA_PRIORITY),
            "pushalot_enabled": checked(plexpy.CONFIG.PUSHALOT_ENABLED),
            "pushalot_apikey": plexpy.CONFIG.PUSHALOT_APIKEY,
            "pushover_enabled": checked(plexpy.CONFIG.PUSHOVER_ENABLED),
            "pushover_keys": plexpy.CONFIG.PUSHOVER_KEYS,
            "pushover_apitoken": plexpy.CONFIG.PUSHOVER_APITOKEN,
            "pushover_priority": plexpy.CONFIG.PUSHOVER_PRIORITY,
            "pushbullet_enabled": checked(plexpy.CONFIG.PUSHBULLET_ENABLED),
            "pushbullet_apikey": plexpy.CONFIG.PUSHBULLET_APIKEY,
            "pushbullet_deviceid": plexpy.CONFIG.PUSHBULLET_DEVICEID,
            "twitter_enabled": checked(plexpy.CONFIG.TWITTER_ENABLED),
            "osx_notify_enabled": checked(plexpy.CONFIG.OSX_NOTIFY_ENABLED),
            "osx_notify_app": plexpy.CONFIG.OSX_NOTIFY_APP,
            "boxcar_enabled": checked(plexpy.CONFIG.BOXCAR_ENABLED),
            "boxcar_token": plexpy.CONFIG.BOXCAR_TOKEN,
            "cache_sizemb": plexpy.CONFIG.CACHE_SIZEMB,
            "email_enabled": checked(plexpy.CONFIG.EMAIL_ENABLED),
            "email_from": plexpy.CONFIG.EMAIL_FROM,
            "email_to": plexpy.CONFIG.EMAIL_TO,
            "email_smtp_server": plexpy.CONFIG.EMAIL_SMTP_SERVER,
            "email_smtp_user": plexpy.CONFIG.EMAIL_SMTP_USER,
            "email_smtp_password": plexpy.CONFIG.EMAIL_SMTP_PASSWORD,
            "email_smtp_port": int(plexpy.CONFIG.EMAIL_SMTP_PORT),
            "email_tls": checked(plexpy.CONFIG.EMAIL_TLS),
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_logs_folder": plexpy.CONFIG.PMS_LOGS_FOLDER,
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "pms_ssl": checked(plexpy.CONFIG.PMS_SSL),
            "pms_use_bif": checked(plexpy.CONFIG.PMS_USE_BIF),
            "pms_uuid": plexpy.CONFIG.PMS_UUID,
            "plexwatch_database": plexpy.CONFIG.PLEXWATCH_DATABASE,
            "date_format": plexpy.CONFIG.DATE_FORMAT,
            "time_format": plexpy.CONFIG.TIME_FORMAT,
            "grouping_global_history": checked(plexpy.CONFIG.GROUPING_GLOBAL_HISTORY),
            "grouping_user_history": checked(plexpy.CONFIG.GROUPING_USER_HISTORY),
            "grouping_charts": checked(plexpy.CONFIG.GROUPING_CHARTS),
            "tv_notify_enable": checked(plexpy.CONFIG.TV_NOTIFY_ENABLE),
            "movie_notify_enable": checked(plexpy.CONFIG.MOVIE_NOTIFY_ENABLE),
            "music_notify_enable": checked(plexpy.CONFIG.MUSIC_NOTIFY_ENABLE),
            "tv_notify_on_start": checked(plexpy.CONFIG.TV_NOTIFY_ON_START),
            "movie_notify_on_start": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_START),
            "music_notify_on_start": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_START),
            "tv_notify_on_stop": checked(plexpy.CONFIG.TV_NOTIFY_ON_STOP),
            "movie_notify_on_stop": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_STOP),
            "music_notify_on_stop": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_STOP),
            "tv_notify_on_pause": checked(plexpy.CONFIG.TV_NOTIFY_ON_PAUSE),
            "movie_notify_on_pause": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_PAUSE),
            "music_notify_on_pause": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_PAUSE),
            "monitoring_interval": plexpy.CONFIG.MONITORING_INTERVAL,
            "refresh_users_interval": plexpy.CONFIG.REFRESH_USERS_INTERVAL,
            "refresh_users_on_startup": checked(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "ip_logging_enable": checked(plexpy.CONFIG.IP_LOGGING_ENABLE),
            "video_logging_enable": checked(plexpy.CONFIG.VIDEO_LOGGING_ENABLE),
            "music_logging_enable": checked(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "pms_is_remote": checked(plexpy.CONFIG.PMS_IS_REMOTE),
            "notify_watched_percent": plexpy.CONFIG.NOTIFY_WATCHED_PERCENT,
            "notify_on_start_subject_text": plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT,
            "notify_on_start_body_text": plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT,
            "notify_on_stop_subject_text": plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT,
            "notify_on_stop_body_text": plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT,
            "notify_on_pause_subject_text": plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT,
            "notify_on_pause_body_text": plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT,
            "notify_on_resume_subject_text": plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT,
            "notify_on_resume_body_text": plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT,
            "notify_on_buffer_subject_text": plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT,
            "notify_on_buffer_body_text": plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT,
            "notify_on_watched_subject_text": plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT,
            "notify_on_watched_body_text": plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT,
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_type": checked(plexpy.CONFIG.HOME_STATS_TYPE),
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "buffer_threshold": plexpy.CONFIG.BUFFER_THRESHOLD,
            "buffer_wait": plexpy.CONFIG.BUFFER_WAIT,
            "group_history_tables": checked(plexpy.CONFIG.GROUP_HISTORY_TABLES)
        }

        return serve_template(templatename="settings.html", title="Settings", config=config)

    @cherrypy.expose
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "launch_browser", "enable_https", "api_enabled", "freeze_db", "growl_enabled",
            "prowl_enabled", "xbmc_enabled", "check_github",
            "plex_enabled", "nma_enabled", "pushalot_enabled",
            "pushover_enabled", "pushbullet_enabled",
            "twitter_enabled", "osx_notify_enabled",
            "boxcar_enabled", "email_enabled", "email_tls",
            "grouping_global_history", "grouping_user_history", "grouping_charts", "pms_use_bif", "pms_ssl",
            "tv_notify_enable", "movie_notify_enable", "music_notify_enable",
            "tv_notify_on_start", "movie_notify_on_start", "music_notify_on_start",
            "tv_notify_on_stop", "movie_notify_on_stop", "music_notify_on_stop",
            "tv_notify_on_pause", "movie_notify_on_pause", "music_notify_on_pause", "refresh_users_on_startup",
            "ip_logging_enable", "video_logging_enable", "music_logging_enable", "pms_is_remote", "home_stats_type",
            "group_history_tables"
        ]
        for checked_config in checked_configs:
            if checked_config not in kwargs:
                # checked items should be zero or one. if they were not sent then the item was not checked
                kwargs[checked_config] = 0

        # If http password exists in config, do not overwrite when blank value received
        if 'http_password' in kwargs:
            if kwargs['http_password'] == '    ' and plexpy.CONFIG.HTTP_PASSWORD != '':
                kwargs['http_password'] = plexpy.CONFIG.HTTP_PASSWORD

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        # Check if we should refresh our data
        refresh_users = False
        reschedule = False

        if 'monitoring_interval' in kwargs and 'refresh_users_interval' in kwargs:
            if (kwargs['monitoring_interval'] != str(plexpy.CONFIG.MONITORING_INTERVAL)) or \
                    (kwargs['refresh_users_interval'] != str(plexpy.CONFIG.REFRESH_USERS_INTERVAL)):
                reschedule = True

        if 'pms_ip' in kwargs:
            if kwargs['pms_ip'] != plexpy.CONFIG.PMS_IP:
                refresh_users = True

        plexpy.CONFIG.process_kwargs(kwargs)

        # Write the config
        plexpy.CONFIG.write()

        # Get new server URLs for SSL communications.
        plextv.get_real_pms_url()

        # Reconfigure scheduler if intervals changed
        if reschedule:
            plexpy.initialize_scheduler()

        # Refresh users table if our server IP changes.
        if refresh_users:
            threading.Thread(target=plextv.refresh_users).start()

        raise cherrypy.HTTPRedirect("settings")

    @cherrypy.expose
    def set_notification_config(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "email_tls"
        ]
        for checked_config in checked_configs:
            if checked_config not in kwargs:
                # checked items should be zero or one. if they were not sent then the item was not checked
                kwargs[checked_config] = 0

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        plexpy.CONFIG.process_kwargs(kwargs)

        # Write the config
        plexpy.CONFIG.write()

        cherrypy.response.status = 200

    @cherrypy.expose
    def do_state_change(self, signal, title, timer):
        message = title
        quote = self.random_arnold_quotes()
        plexpy.SIGNAL = signal

        return serve_template(templatename="shutdown.html", title=title,
                              message=message, timer=timer, quote=quote)

    @cherrypy.expose
    def get_history(self, user=None, user_id=None, grouping=0, **kwargs):

        if grouping == 'false':
            grouping = 0
        else:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        custom_where=[]
        if user_id:
            custom_where = [['user_id', user_id]]
        elif user:
            custom_where = [['user', user]]
        if 'rating_key' in kwargs:
            rating_key = kwargs.get('rating_key', "")
            custom_where = [['rating_key', rating_key]]
        if 'parent_rating_key' in kwargs:
            rating_key = kwargs.get('parent_rating_key', "")
            custom_where = [['parent_rating_key', rating_key]]
        if 'grandparent_rating_key' in kwargs:
            rating_key = kwargs.get('grandparent_rating_key', "")
            custom_where = [['grandparent_rating_key', rating_key]]
        if 'start_date' in kwargs:
            start_date = kwargs.get('start_date', "")
            custom_where = [['strftime("%Y-%m-%d", datetime(date, "unixepoch", "localtime"))', start_date]]
        if 'group_start_id' in kwargs:
            group_start_id = kwargs.get('group_start_id', "")
            custom_where = [['group_start_id', int(group_start_id)]]

        data_factory = datafactory.DataFactory()
        history = data_factory.get_history(kwargs=kwargs, custom_where=custom_where, grouping=grouping)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(history)

    @cherrypy.expose
    def history_table_modal(self, start_date=None, **kwargs):

        return serve_template(templatename="history_table_modal.html", title="History Data", data=start_date)

    @cherrypy.expose
    def shutdown(self):
        return self.do_state_change('shutdown', 'Shutting Down', 15)

    @cherrypy.expose
    def restart(self):
        return self.do_state_change('restart', 'Restarting', 30)

    @cherrypy.expose
    def update(self):
        return self.do_state_change('update', 'Updating', 120)

    @cherrypy.expose
    def api(self, *args, **kwargs):
        from plexpy.api import Api

        a = Api()
        a.checkParams(*args, **kwargs)

        return a.fetchData()

    @cherrypy.expose
    def twitterStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        return tweet._get_authorization()

    @cherrypy.expose
    def twitterStep2(self, key):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet._get_credentials(key)
        logger.info(u"result: " + str(result))
        if result:
            return "Key verification successful"
        else:
            return "Unable to verify key"

    @cherrypy.expose
    def testTwitter(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet.test_notify()
        if result:
            return "Tweet successful, check your twitter to make sure it worked"
        else:
            return "Error sending tweet"

    @cherrypy.expose
    def osxnotifyregister(self, app):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        from osxnotify import registerapp as osxnotify

        result, msg = osxnotify.registerapp(app)
        if result:
            osx_notify = notifiers.OSX_NOTIFY()
            osx_notify.notify('Registered', result, 'Success :-)')
            logger.info('Registered %s, to re-register a different app, delete this app first' % result)
        else:
            logger.warn(msg)
        return msg

    @cherrypy.expose
    def get_pms_token(self):

        token = plextv.PlexTV()
        result = token.get_token()

        if result:
            return result
        else:
            logger.warn('Unable to retrieve Plex.tv token.')
            return False

    @cherrypy.expose
    def get_pms_sessions_json(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sessions('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')
            return False

    @cherrypy.expose
    def get_current_activity(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_current_activity()
        except:
            return serve_template(templatename="current_activity.html", data=None)

        if result:
            return serve_template(templatename="current_activity.html", data=result)
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="current_activity.html", data=None)

    @cherrypy.expose
    def get_current_activity_header(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_current_activity()
        except IOError, e:
            return serve_template(templatename="current_activity_header.html", data=None)

        if result:
            return serve_template(templatename="current_activity_header.html", data=result['stream_count'])
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="current_activity_header.html", data=None)

    @cherrypy.expose
    def get_recently_added(self, count='0', **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(count)
        except IOError, e:
            return serve_template(templatename="recently_added.html", data=None)

        if result:
            return serve_template(templatename="recently_added.html", data=result['recently_added'])
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="recently_added.html", data=None)

    @cherrypy.expose
    def pms_image_proxy(self, img='', width='0', height='0', fallback=None, **kwargs):
        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_image(img, width, height)
            cherrypy.response.headers['Content-type'] = result[1]
            return result[0]
        except:
            logger.warn('Image proxy queried but errors occured.')
            if fallback == 'poster':
                logger.info('Trying fallback image...')
                try:
                    fallback_image = open(self.interface_dir + common.DEFAULT_POSTER_THUMB, 'rb')
                    cherrypy.response.headers['Content-type'] = 'image/png'
                    return fallback_image
                except IOError, e:
                    logger.error('Unable to read fallback image. %s' % e)
            elif fallback == 'cover':
                logger.info('Trying fallback image...')
                try:
                    fallback_image = open(self.interface_dir + common.DEFAULT_COVER_THUMB, 'rb')
                    cherrypy.response.headers['Content-type'] = 'image/png'
                    return fallback_image
                except IOError, e:
                    logger.error('Unable to read fallback image. %s' % e)

            return None

    @cherrypy.expose
    def info(self, item_id=None, source=None, **kwargs):
        metadata = None

        config = {
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER
        }

        if source == 'history':
            data_factory = datafactory.DataFactory()
            metadata = data_factory.get_metadata_details(row_id=item_id)
        else:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_metadata_details(rating_key=item_id)
            if result:
                metadata = result['metadata']

        if metadata:
            return serve_template(templatename="info.html", data=metadata, title="Info", config=config)
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="info.html", data=None, title="Info")

    @cherrypy.expose
    def get_user_recently_watched(self, user=None, user_id=None, limit='10', **kwargs):

        data_factory = datafactory.DataFactory()
        result = data_factory.get_recently_watched(user_id=user_id, user=user, limit=limit)

        if result:
            return serve_template(templatename="user_recently_watched.html", data=result,
                                  title="Recently Watched")
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="user_recently_watched.html", data=None,
                                  title="Recently Watched")

    @cherrypy.expose
    def get_user_watch_time_stats(self, user=None, user_id=None, **kwargs):

        user_data = users.Users()
        result = user_data.get_user_watch_time_stats(user_id=user_id, user=user)

        if result:
            return serve_template(templatename="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    def get_user_platform_stats(self, user=None, user_id=None, **kwargs):

        user_data = users.Users()
        result = user_data.get_user_platform_stats(user_id=user_id, user=user)

        if result:
            return serve_template(templatename="user_platform_stats.html", data=result,
                                  title="Platform Stats")
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="user_platform_stats.html", data=None, title="Platform Stats")

    @cherrypy.expose
    def get_item_children(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_item_children(rating_key)

        if result:
            return serve_template(templatename="info_children_list.html", data=result, title="Children List")
        else:
            logger.warn('Unable to retrieve data.')
            return serve_template(templatename="info_children_list.html", data=None, title="Children List")

    @cherrypy.expose
    def get_metadata_json(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata(rating_key, 'json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_metadata_xml(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata(rating_key)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/xml'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_recently_added_json(self, count='0', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_recently_added(count, 'json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_episode_list_json(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_episode_list(rating_key, 'json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_ips(self, user_id=None, user=None, **kwargs):

        custom_where=[]
        if user_id:
            custom_where = [['user_id', user_id]]
        elif user:
            custom_where = [['user', user]]

        user_data = users.Users()
        history = user_data.get_user_unique_ips(kwargs=kwargs,
                                                custom_where=custom_where)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(history)

    @cherrypy.expose
    def get_plays_by_date(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_day(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_dayofweek(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_dayofweek(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_hourofday(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_hourofday(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_per_month(self, y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_month(y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_top_10_platforms(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_top_10_users(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_users(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_stream_type(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_stream_type(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_source_resolution(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_source_resolution(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_stream_resolution(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_stream_resolution(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_users(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_friends_list(self, **kwargs):

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_friends('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_details(self, **kwargs):

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_user_details('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_server_list(self, **kwargs):

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_server_list('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_sync_lists(self, machine_id='', **kwargs):

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_sync_lists(machine_id=machine_id, output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_servers(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_list(output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_servers_info(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_servers_info()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_server_prefs(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_prefs(output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_activity(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_current_activity()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_full_users_list(self, **kwargs):

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_full_users_list()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def refresh_users_list(self, **kwargs):
        threading.Thread(target=plextv.refresh_users).start()
        logger.info('Manual user list refresh requested.')

    @cherrypy.expose
    def get_sync(self, machine_id=None, user_id=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        server_id = pms_connect.get_server_identity()

        plex_tv = plextv.PlexTV()
        if not machine_id:
            result = plex_tv.get_synced_items(machine_id=server_id['machine_identifier'], user_id=user_id)
        else:
            result = plex_tv.get_synced_items(machine_id=machine_id, user_id=user_id)

        if result:
            output = {"data": result}
        else:
            logger.warn('Unable to retrieve sync data for user.')
            output = {"data": []}

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(output)

    @cherrypy.expose
    def get_sync_item(self, sync_id, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sync_item(sync_id, output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_sync_transcode_queue(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sync_transcode_queue(output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_server_pref(self, pref=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_pref(pref=pref)

        if result:
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plexwatch_export_data(self, database_path=None, table_name=None, import_ignore_interval=0, **kwargs):
        from plexpy import plexwatch_import

        db_check_msg = plexwatch_import.validate_database(database=database_path,
                                                          table_name=table_name)
        if db_check_msg == 'success':
            threading.Thread(target=plexwatch_import.import_from_plexwatch,
                             kwargs={'database': database_path,
                                     'table_name': table_name,
                                     'import_ignore_interval': import_ignore_interval}).start()
            return 'Import has started. Check the PlexPy logs to monitor any problems.'
        else:
            return db_check_msg

    @cherrypy.expose
    def plexwatch_import(self, **kwargs):
        return serve_template(templatename="plexwatch_import.html", title="Import PlexWatch Database")

    @cherrypy.expose
    def get_server_id(self, hostname=None, port=None, **kwargs):
        from plexpy import http_handler

        if hostname and port:
            request_handler = http_handler.HTTPHandler(host=hostname,
                                                       port=port,
                                                       token=None)
            uri = '/identity'
            request = request_handler.make_request(uri=uri,
                                                   proto='http',
                                                   request_type='GET',
                                                   output_format='',
                                                   no_token=True)
            if request:
                cherrypy.response.headers['Content-type'] = 'application/xml'
                return request
            else:
                logger.warn('Unable to retrieve data.')
                return None
        else:
            return None

    @cherrypy.expose
    def random_arnold_quotes(self, **kwargs):
        from random import randint
        quote_list = ['To crush your enemies, see them driven before you, and to hear the lamentation of their women!',
                      'Your clothes, give them to me, now!',
                      'Do it!',
                      'If it bleeds, we can kill it',
                      'See you at the party Richter!',
                      'Let off some steam, Bennett',
                      'I\'ll be back',
                      'Get to the chopper!',
                      'Hasta La Vista, Baby!',
                      'It\'s not a tumor!',
                      'Dillon, you son of a bitch!',
                      'Benny!! Screw you!!',
                      'Stop whining! You kids are soft. You lack discipline.',
                      'Nice night for a walk.',
                      'Stick around!',
                      'I need your clothes, your boots and your motorcycle.',
                      'No, it\'s not a tumor. It\'s not a tumor!',
                      'I LIED!',
                      'See you at the party, Richter!',
                      'Are you Sarah Conner?',
                      'I\'m a cop you idiot!',
                      'Come with me if you want to live.',
                      'Who is your daddy and what does he do?'
                      ]

        random_number = randint(0, len(quote_list) - 1)
        return quote_list[int(random_number)]

    @cherrypy.expose
    def get_notification_agent_config(self, config_id, **kwargs):
        config = notifiers.get_notification_agent_config(config_id=config_id)

        checkboxes = {'email_tls': checked(plexpy.CONFIG.EMAIL_TLS)}

        return serve_template(templatename="notification_config.html", title="Notification Configuration",
                              data=config, checkboxes=checkboxes)

    @cherrypy.expose
    def get_notification_agent_triggers(self, config_id, **kwargs):
        if config_id.isdigit():
            agents = notifiers.available_notification_agents()
            for agent in agents:
                if int(config_id) == agent['id']:
                    this_agent = agent
                    break
                else:
                    this_agent = None
        else:
            return None

        return serve_template(templatename="notification_triggers_modal.html", title="Notification Triggers",
                              data=this_agent)

    @cherrypy.expose
    def delete_history_rows(self, row_id, **kwargs):
        data_factory = datafactory.DataFactory()

        if row_id:
            delete_row = data_factory.delete_session_history_rows(row_id=row_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    def delete_all_user_history(self, user_id, **kwargs):
        data_factory = datafactory.DataFactory()

        if user_id:
            delete_row = data_factory.delete_all_user_history(user_id=user_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

