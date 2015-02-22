#  This file is part of PlexPy.
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

from plexpy import logger, db, helpers, notifiers
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

        return serve_template(templatename="history.html", title="History", date_format=date_format, time_format=time_format)

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
    def getLog(self, iDisplayStart=0, iDisplayLength=100, iSortCol_0=0, sSortDir_0="desc", sSearch="", **kwargs):
        iDisplayStart = int(iDisplayStart)
        iDisplayLength = int(iDisplayLength)

        filtered = []
        if sSearch == "":
            filtered = plexpy.LOG_LIST[::]
        else:
            filtered = [row for row in plexpy.LOG_LIST for column in row if sSearch.lower() in column.lower()]

        sortcolumn = 0
        if iSortCol_0 == '1':
            sortcolumn = 2
        elif iSortCol_0 == '2':
            sortcolumn = 1
        filtered.sort(key=lambda x: x[sortcolumn], reverse=sSortDir_0 == "desc")

        rows = filtered[iDisplayStart:(iDisplayStart + iDisplayLength)]
        rows = [[row[0], row[2], row[1]] for row in rows]

        return json.dumps({
            'iTotalDisplayRecords': len(filtered),
            'iTotalRecords': len(plexpy.LOG_LIST),
            'aaData': rows,
        })

    @cherrypy.expose
    def generateAPI(self):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info("New API generated")
        return apikey

    @cherrypy.expose
    def config(self):
        interface_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if os.path.isdir(os.path.join(interface_dir, name))]

        config = {
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": plexpy.CONFIG.HTTP_PASSWORD,
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
            "pms_password": plexpy.CONFIG.PMS_PASSWORD,
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
    def getHistory_json(self, iDisplayStart=0, iDisplayLength=100, sSearch="", iSortCol_0='0', sSortDir_0='asc', **kwargs):
        iDisplayStart = int(iDisplayStart)
        iDisplayLength = int(iDisplayLength)
        filtered = []
        totalcount = 0
        myDB = db.DBConnection()
        db_table = db.DBConnection().get_history_table_name()

        sortcolumn = 'time'
        sortbyhavepercent = False
        if iSortCol_0 == '1':
            sortcolumn = 'user'
        if iSortCol_0 == '2':
            sortcolumn = 'platform'
        elif iSortCol_0 == '3':
            sortcolumn = 'ip_address'
        elif iSortCol_0 == '4':
            sortcolumn = 'title'
        elif iSortCol_0 == '5':
            sortcolumn = 'time'
        elif iSortCol_0 == '6':
            sortcolumn = 'paused_counter'
        elif iSortCol_0 == '7':
            sortcolumn = 'stopped'
        elif iSortCol_0 == '8':
            sortbyhavepercent = True

        if sSearch == "":
            query = 'SELECT * from %s order by %s COLLATE NOCASE %s' % (db_table, sortcolumn, sSortDir_0)
            filtered = myDB.select(query)
            totalcount = len(filtered)
        else:
            query = 'SELECT * from ' + db_table + ' WHERE user LIKE "%' + sSearch + \
                    '%" OR title LIKE "%' + sSearch + '%"' + 'ORDER BY %s COLLATE NOCASE %s' % (sortcolumn, sSortDir_0)
            filtered = myDB.select(query)
            totalcount = myDB.select('SELECT COUNT(*) from processed')[0][0]

        history = filtered[iDisplayStart:(iDisplayStart + iDisplayLength)]
        rows = []
        for item in history:
            row = {"date": item['time'],
                      "user": item["user"],
                      "platform": item["platform"],
                      "ip_address": item["ip_address"],
                      "title": item["title"],
                      "started": item["time"],
                      "paused": item["paused_counter"],
                      "stopped": item["stopped"],
                      "duration": "",
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

                row['duration'] = stopped - item['time'] + paused_counter

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
                        row['percent_complete'] = (view_offset / duration)*100
                    else:
                        row['percent_complete'] = 0

            rows.append(row)

        dict = {'iTotalDisplayRecords': len(filtered),
                'iTotalRecords': totalcount,
                'aaData': rows,
                }
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

