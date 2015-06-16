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

from plexpy import logger, db, helpers, notifiers, plextv, pmsconnect
from plexpy.helpers import checked, radio, today, cleanName
from xml.dom import minidom

from mako.lookup import TemplateLookup
from mako import exceptions

from operator import itemgetter

import plexpy
import threading
import cherrypy
import urllib2
import hashlib
import random
import urllib
import json
import time
import sys
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
        return serve_template(templatename="index.html", title="Home")

    @cherrypy.expose
    def history(self):
        if plexpy.CONFIG.DATE_FORMAT:
            date_format = plexpy.CONFIG.DATE_FORMAT
        else:
            date_format = 'YYYY-MM-DD'
        if plexpy.CONFIG.TIME_FORMAT:
            time_format = plexpy.CONFIG.TIME_FORMAT
        else:
            time_format = 'HH:mm'

        return serve_template(templatename="history.html", title="History", date_format=date_format,
                              time_format=time_format)

    @cherrypy.expose
    def users(self):
        return serve_template(templatename="users.html", title="Users")

    @cherrypy.expose
    def get_user_list(self, start=0, length=100, **kwargs):
        start = int(start)
        length = int(length)
        filtered = []
        totalcount = 0
        search_value = ""
        search_regex = ""
        order_column = 1
        order_dir = "desc"

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', "1")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        sortcolumn = 'user'
        if order_column == '2':
            sortcolumn = 'time'
        elif order_column == '3':
            sortcolumn = 'ip_address'
        elif order_column == '4':
            sortcolumn = 'plays'

        myDB = db.DBConnection()
        db_table = db.DBConnection().get_history_table_name()

        if search_value == "":
            query = 'SELECT COUNT(title) as plays, user, time, \
                    SUM(time) as timeTotal, SUM(stopped) as stoppedTotal, \
                    SUM(paused_counter) as paused_counterTotal, platform, \
                    ip_address, xml \
                    from %s GROUP by user ORDER by %s COLLATE NOCASE %s' % (db_table, sortcolumn, order_dir)
            filtered = myDB.select(query)
            totalcount = len(filtered)
        else:
            query = 'SELECT COUNT(title) as plays, user, time, \
                    SUM(time) as timeTotal, SUM(stopped) as stoppedTotal, \
                    SUM(paused_counter) as paused_counterTotal, platform, \
                    ip_address, xml \
                    from ' + db_table + ' WHERE user LIKE "%' + search_value + '%" \
                    GROUP by user' + ' ORDER by %s COLLATE NOCASE %s' % (sortcolumn, order_dir)
            filtered = myDB.select(query)
            totalcount = myDB.select('SELECT COUNT(*) from %s' % db_table)[0][0]

        users = filtered[start:(start + length)]
        rows = []
        for item in users:
            row = {"plays": item['plays'],
                   "time": item['time'],
                   "user": item["user"],
                   "timeTotal": item["timeTotal"],
                   "ip_address": item["ip_address"],
                   "stoppedTotal": item["stoppedTotal"],
                   "paused_counterTotal": item["paused_counterTotal"],
                   "platform": item["platform"]
                   }

            try:
                xml_parse = minidom.parseString(helpers.latinToAscii(item['xml']))
            except IOError, e:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            xml_head = xml_parse.getElementsByTagName('User')
            if not xml_head:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            for s in xml_head:
                if s.getAttribute('thumb'):
                    row['user_thumb'] = s.getAttribute('thumb')
                else:
                    row['user_thumb'] = ""
                if s.getAttribute('id'):
                    row['user_id'] = s.getAttribute('id')
                else:
                    row['user_id'] = ""

            rows.append(row)

        dict = {'recordsFiltered': len(filtered),
                'recordsTotal': totalcount,
                'data': rows,
        }
        s = json.dumps(dict)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return s

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
        if plexpy.CONFIG.PMS_PASSWORD != '':
            pms_password = '    '
        else:
            pms_password = ''

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
            "pms_username": plexpy.CONFIG.PMS_USERNAME,
            "pms_password": pms_password,
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

        # Write Plex token to the config
        if (not plexpy.CONFIG.PMS_TOKEN or plexpy.CONFIG.PMS_TOKEN == '' \
                or kwargs['pms_username'] != plexpy.CONFIG.PMS_USERNAME) \
                and (kwargs['pms_username'] != '' or kwargs['pms_password'] != ''):

            plex_tv = plextv.PlexTV(kwargs['pms_username'], kwargs['pms_password'])
            token = plex_tv.get_token()

            if token:
                kwargs['pms_token'] = token
                logger.info('Plex.tv token sucessfully written to config.')
            else:
                logger.warn('Unable to write Plex.tv token to config.')

        # Clear Plex token if username or password set to blank
        if kwargs['pms_username'] == '' or kwargs['pms_password'] == '':
            kwargs['pms_token'] = ''

        # If passwords exists in config, do not overwrite when blank value received
        if kwargs['http_password'] == '    ' and plexpy.CONFIG.HTTP_PASSWORD != '':
            kwargs['http_password'] = plexpy.CONFIG.HTTP_PASSWORD
        if kwargs['pms_password'] == '    ' and plexpy.CONFIG.PMS_PASSWORD != '':
            kwargs['pms_password'] = plexpy.CONFIG.PMS_PASSWORD

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
    def getHistory_json(self, start=0, length=100, **kwargs):
        start = int(start)
        length = int(length)
        filtered = []
        totalcount = 0
        search_value = ""
        search_regex = ""
        order_column = 1
        order_dir = "desc"

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', "1")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        myDB = db.DBConnection()
        db_table = db.DBConnection().get_history_table_name()

        sortcolumn = 'time'
        sortbyhavepercent = False
        if order_column == '2':
            sortcolumn = 'user'
        if order_column == '3':
            sortcolumn = 'platform'
        elif order_column == '4':
            sortcolumn = 'ip_address'
        elif order_column == '5':
            sortcolumn = 'title'
        elif order_column == '6':
            sortcolumn = 'time'
        elif order_column == '7':
            sortcolumn = 'paused_counter'
        elif order_column == '8':
            sortcolumn = 'stopped'
        elif order_column == '9':
            sortcolumn = 'duration'

        if search_value == "":
            query = 'SELECT id, time, user, platform, ip_address, title, time, paused_counter, stopped, ratingKey, xml, \
                    round((julianday(datetime(stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(time, "unixepoch", "localtime"))) * 86400) - \
                    (case when paused_counter is null then 0 else paused_counter end) as duration \
                    from %s order by %s COLLATE NOCASE %s' % (db_table, sortcolumn, order_dir)
            filtered = myDB.select(query)
            totalcount = len(filtered)
        else:
            query = 'SELECT id, time, user, platform, ip_address, title, time, paused_counter, stopped, ratingKey, xml, \
                    round((julianday(datetime(stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(time, "unixepoch", "localtime"))) * 86400) - \
                    (case when paused_counter is null then 0 else paused_counter end) as duration \
                    from ' + db_table + ' WHERE user LIKE "%' + search_value + '%" OR title LIKE "%' + search_value \
                    + '%"' + 'ORDER BY %s COLLATE NOCASE %s' % (sortcolumn, order_dir)
            filtered = myDB.select(query)
            totalcount = myDB.select('SELECT COUNT(*) from processed')[0][0]

        history = filtered[start:(start + length)]
        rows = []
        for item in history:
            row = {"id": item['id'],
                   "date": item['time'],
                   "user": item["user"],
                   "platform": item["platform"],
                   "ip_address": item["ip_address"],
                   "title": item["title"],
                   "started": item["time"],
                   "paused": item["paused_counter"],
                   "stopped": item["stopped"],
                   "rating_key": item["ratingKey"],
                   "duration": item["duration"],
                   "percent_complete": 0,
            }

            if item['paused_counter'] > 0:
                row['paused'] = item['paused_counter']
            else:
                row['paused'] = 0

            if item['time']:
                if item['stopped'] > 0:
                    stopped = item['stopped']
                else:
                    stopped = 0
                if item['paused_counter'] > 0:
                    paused_counter = item['paused_counter']
                else:
                    paused_counter = 0

            try:
                xml_parse = minidom.parseString(helpers.latinToAscii(item['xml']))
            except IOError, e:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            xml_head = xml_parse.getElementsByTagName('opt')
            if not xml_head:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            for s in xml_head:
                if s.getAttribute('duration') and s.getAttribute('viewOffset'):
                    view_offset = helpers.cast_to_float(s.getAttribute('viewOffset'))
                    duration = helpers.cast_to_float(s.getAttribute('duration'))
                    if duration > 0:
                        row['percent_complete'] = (view_offset / duration) * 100
                    else:
                        row['percent_complete'] = 0

            rows.append(row)

        dict = {'recordsFiltered': len(filtered),
                'recordsTotal': totalcount,
                'data': rows,
        }
        s = json.dumps(dict)
        cherrypy.response.headers['Content-type'] = 'application/json'
        return s


    @cherrypy.expose
    def getStreamDetails(self, id=0, **kwargs):

        myDB = db.DBConnection()
        db_table = db.DBConnection().get_history_table_name()

        query = 'SELECT xml from %s where id = %s' % (db_table, id)
        xml = myDB.select_single(query)

        try:
            dict_data = helpers.convert_xml_to_dict(helpers.latinToAscii(xml))
        except IOError, e:
            logger.warn("Error parsing XML in PlexWatch db: %s" % e)

        dict = {'id': id,
                'data': dict_data}

        s = json.dumps(dict)
        cherrypy.response.headers['Content-type'] = 'application/json'
        return s


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
            return serve_template(templatename="current_activity.html", activity=None)

        if result:
            return serve_template(templatename="current_activity.html", activity=result)
        else:
            return serve_template(templatename="current_activity.html", activity=None)
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_current_activity_header(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_current_activity()
        except IOError, e:
            return serve_template(templatename="current_activity_header.html", activity=None)

        if result:
            return serve_template(templatename="current_activity_header.html", activity=result['stream_count'])
        else:
            return serve_template(templatename="current_activity_header.html", activity=None)
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def get_recently_added(self, count='0', **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(count)
        except IOError, e:
            return serve_template(templatename="recently_added.html", recently_added=None)

        if result:
            return serve_template(templatename="recently_added.html", recently_added=result['recently_added'])
        else:
            return serve_template(templatename="recently_added.html", recently_added=None)
            logger.warn('Unable to retrieve data.')

    @cherrypy.expose
    def pms_image_proxy(self, img='', width='0', height='0', **kwargs):
        if img != '':
            try:
                pms_connect = pmsconnect.PmsConnect()
                result = pms_connect.get_image(img, width, height)
                logger.info('Image proxy queried. Content type is %s' % result[0])
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
            return serve_template(templatename="info.html", metadata=result['metadata'], title="Info")
        else:
            return serve_template(templatename="info.html", metadata='', title="Info")
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