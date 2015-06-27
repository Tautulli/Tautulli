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

from plexpy import logger, notifiers, plextv, pmsconnect, plexwatch
from plexpy.helpers import checked, radio

from mako.lookup import TemplateLookup
from mako import exceptions

import plexpy
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
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def home(self):
        if plexpy.CONFIG.PLEXWATCH_DATABASE == '':
            raise cherrypy.HTTPRedirect("config")
        else:
            return serve_template(templatename="index.html", title="Home")

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
    def home_stats(self, time_range='30', **kwargs):
        plex_watch = plexwatch.PlexWatch()
        stats_data = plex_watch.get_home_stats(time_range)

        return serve_template(templatename="home_stats.html", title="Stats", data=stats_data)

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
    def user(self, user=None):
        return serve_template(templatename="user.html", title="User", user=user)

    @cherrypy.expose
    def get_stream_data(self, row_id=None, user=None, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        stream_data = plex_watch.get_stream_details(row_id)

        return serve_template(templatename="stream_data.html", title="Stream Data", data=stream_data, user=user)

    @cherrypy.expose
    def get_user_list(self, start=0, length=100, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        users = plex_watch.get_user_list(start, length, kwargs)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(users)

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
    def generateAPI(self):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info("New API generated")
        return apikey

    @cherrypy.expose
    def config(self):
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
            "lms_enabled": checked(plexpy.CONFIG.LMS_ENABLED),
            "lms_host": plexpy.CONFIG.LMS_HOST,
            "plex_enabled": checked(plexpy.CONFIG.PLEX_ENABLED),
            "plex_client_host": plexpy.CONFIG.PLEX_CLIENT_HOST,
            "plex_username": plexpy.CONFIG.PLEX_USERNAME,
            "plex_password": plexpy.CONFIG.PLEX_PASSWORD,
            "nma_enabled": checked(plexpy.CONFIG.NMA_ENABLED),
            "nma_apikey": plexpy.CONFIG.NMA_APIKEY,
            "nma_priority": int(plexpy.CONFIG.NMA_PRIORITY),
            "pushalot_enabled": checked(plexpy.CONFIG.PUSHALOT_ENABLED),
            "pushalot_apikey": plexpy.CONFIG.PUSHALOT_APIKEY,
            "synoindex_enabled": checked(plexpy.CONFIG.SYNOINDEX_ENABLED),
            "pushover_enabled": checked(plexpy.CONFIG.PUSHOVER_ENABLED),
            "pushover_keys": plexpy.CONFIG.PUSHOVER_KEYS,
            "pushover_apitoken": plexpy.CONFIG.PUSHOVER_APITOKEN,
            "pushover_priority": plexpy.CONFIG.PUSHOVER_PRIORITY,
            "pushbullet_enabled": checked(plexpy.CONFIG.PUSHBULLET_ENABLED),
            "pushbullet_apikey": plexpy.CONFIG.PUSHBULLET_APIKEY,
            "pushbullet_deviceid": plexpy.CONFIG.PUSHBULLET_DEVICEID,
            "subsonic_enabled": checked(plexpy.CONFIG.SUBSONIC_ENABLED),
            "subsonic_host": plexpy.CONFIG.SUBSONIC_HOST,
            "subsonic_username": plexpy.CONFIG.SUBSONIC_USERNAME,
            "subsonic_password": plexpy.CONFIG.SUBSONIC_PASSWORD,
            "twitter_enabled": checked(plexpy.CONFIG.TWITTER_ENABLED),
            "osx_notify_enabled": checked(plexpy.CONFIG.OSX_NOTIFY_ENABLED),
            "osx_notify_app": plexpy.CONFIG.OSX_NOTIFY_APP,
            "boxcar_enabled": checked(plexpy.CONFIG.BOXCAR_ENABLED),
            "boxcar_token": plexpy.CONFIG.BOXCAR_TOKEN,
            "cache_sizemb": plexpy.CONFIG.CACHE_SIZEMB,
            "mpc_enabled": checked(plexpy.CONFIG.MPC_ENABLED),
            "email_enabled": checked(plexpy.CONFIG.EMAIL_ENABLED),
            "email_from": plexpy.CONFIG.EMAIL_FROM,
            "email_to": plexpy.CONFIG.EMAIL_TO,
            "email_smtp_server": plexpy.CONFIG.EMAIL_SMTP_SERVER,
            "email_smtp_user": plexpy.CONFIG.EMAIL_SMTP_USER,
            "email_smtp_password": plexpy.CONFIG.EMAIL_SMTP_PASSWORD,
            "email_smtp_port": int(plexpy.CONFIG.EMAIL_SMTP_PORT),
            "email_tls": checked(plexpy.CONFIG.EMAIL_TLS),
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "plexwatch_database": plexpy.CONFIG.PLEXWATCH_DATABASE,
            "date_format": plexpy.CONFIG.DATE_FORMAT,
            "time_format": plexpy.CONFIG.TIME_FORMAT,
            "grouping_global_history": checked(plexpy.CONFIG.GROUPING_GLOBAL_HISTORY),
            "grouping_user_history": checked(plexpy.CONFIG.GROUPING_USER_HISTORY),
            "grouping_charts": checked(plexpy.CONFIG.GROUPING_CHARTS)
        }

        return serve_template(templatename="config.html", title="Settings", config=config)

    @cherrypy.expose
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "launch_browser", "enable_https", "api_enabled", "freeze_db", "growl_enabled",
            "prowl_enabled", "xbmc_enabled", "lms_enabled",
            "plex_enabled", "nma_enabled", "pushalot_enabled",
            "synoindex_enabled", "pushover_enabled", "pushbullet_enabled",
            "subsonic_enabled", "twitter_enabled", "osx_notify_enabled",
            "boxcar_enabled", "mpc_enabled", "email_enabled", "email_tls",
            "grouping_global_history", "grouping_user_history", "grouping_charts"
        ]
        for checked_config in checked_configs:
            if checked_config not in kwargs:
                # checked items should be zero or one. if they were not sent then the item was not checked
                kwargs[checked_config] = 0

        # If http password exists in config, do not overwrite when blank value received
        if kwargs['http_password'] == '    ' and plexpy.CONFIG.HTTP_PASSWORD != '':
            kwargs['http_password'] = plexpy.CONFIG.HTTP_PASSWORD

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        plexpy.CONFIG.process_kwargs(kwargs)

        # Write the config
        plexpy.CONFIG.write()

        # Reconfigure scheduler
        plexpy.initialize_scheduler()

        raise cherrypy.HTTPRedirect("config")

    @cherrypy.expose
    def do_state_change(self, signal, title, timer):
        plexpy.SIGNAL = signal
        message = title + '...'
        return serve_template(templatename="shutdown.html", title=title,
                              message=message, timer=timer)

    @cherrypy.expose
    def get_history(self, start=0, length=100, custom_where='', **kwargs):

        if 'user' in kwargs:
            user = kwargs.get('user', "")
            custom_where = 'user = "%s"' % user
        if 'rating_key' in kwargs:
            rating_key = kwargs.get('rating_key', "")
            custom_where = 'rating_key = %s' % rating_key
        if 'grandparent_rating_key' in kwargs:
            rating_key = kwargs.get('grandparent_rating_key', "")
            custom_where = 'grandparent_rating_key = %s' % rating_key

        plex_watch = plexwatch.PlexWatch()
        history = plex_watch.get_history(start, length, kwargs, custom_where)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(history)

    @cherrypy.expose
    def get_stream_details(self, rating_key=0, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        stream_details = plex_watch.get_stream_details(rating_key)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(stream_details)

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
            return serve_template(templatename="current_activity.html", data=None)
            logger.warn('Unable to retrieve data.')

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
            return serve_template(templatename="current_activity_header.html", data=None)
            logger.warn('Unable to retrieve data.')

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
            return serve_template(templatename="recently_added.html", data=None)
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def pms_image_proxy(self, img='', width='0', height='0', **kwargs):
        if img != '':
            try:
                pms_connect = pmsconnect.PmsConnect()
                result = pms_connect.get_image(img, width, height)
                cherrypy.response.headers['Content-type'] = result[0]
                return result[1]
            except:
                logger.warn('Image proxy queried but errors occured.')
                return 'No image'
        else:
            logger.warn('Image proxy queried but no parameters received.')
            return 'No image'

    @cherrypy.expose
    def info(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata_details(rating_key)

        if result:
            return serve_template(templatename="info.html", data=result['metadata'], title="Info")
        else:
            return serve_template(templatename="info.html", data=None, title="Info")
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_recently_watched(self, user=None, limit='10', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_recently_watched(user, limit)

        if result:
            return serve_template(templatename="user_recently_watched.html", data=result,
                                  title="Recently Watched")
        else:
            return serve_template(templatename="user_recently_watched.html", data=None,
                                  title="Recently Watched")
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_watch_time_stats(self, user=None, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_user_watch_time_stats(user)

        if result:
            return serve_template(templatename="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_platform_stats(self, user=None, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_user_platform_stats(user)

        if result:
            return serve_template(templatename="user_platform_stats.html", data=result,
                                  title="Platform Stats")
        else:
            return serve_template(templatename="user_platform_stats.html", data=None, title="Platform Stats")
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_children(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_season_children(rating_key)

        if result:
            return serve_template(templatename="info_episode_list.html", data=result, title="Episode List")
        else:
            return serve_template(templatename="info_episode_list.html", data=None, title="Episode List")
            logger.warn('Unable to retrieve data.')

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
    def get_stream(self, row_id='', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_stream_details('122')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_ips(self, start=0, length=100, custom_where='', **kwargs):

        if 'user' in kwargs:
            user = kwargs.get('user', "")
            custom_where = 'user = "%s"' % user

        plex_watch = plexwatch.PlexWatch()
        history = plex_watch.get_user_unique_ips(start, length, kwargs, custom_where)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(history)

    @cherrypy.expose
    def get_watched(self, user=None, limit='10', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_recently_watched(user, limit)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_time_stats(self, user=None, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_user_watch_time_stats(user)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_platform_stats(self, user=None, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_user_platform_stats(user)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_user_gravatar_image(self, user=None, **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_user_gravatar_image(user)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_home_stats(self, time_range='30', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_home_stats(time_range)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_date(self, time_range='30', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_total_plays_per_day(time_range)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_dayofweek(self, time_range='30', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_total_plays_per_dayofweek(time_range)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_plays_by_hourofday(self, time_range='30', **kwargs):

        plex_watch = plexwatch.PlexWatch()
        result = plex_watch.get_total_plays_per_hourofday(time_range)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn('Unable to retrieve data.')
