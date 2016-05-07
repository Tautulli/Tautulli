#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import json
import hashlib
import os
import random
import re
import traceback

import cherrypy
import xmltodict

import plexpy
import datafactory
import graphs
import logger
import plextv
import pmsconnect
import users
import versioncheck


cmd_list = ['getLogs', 'getVersion', 'checkGithub', 'shutdown',
            'getSettings', 'restart', 'update', 'getApikey', 'getHistory',
            'getMetadata', 'getUserips', 'getPlayby', 'getSync']


class Api(object):
    def __init__(self, out='json'):

        self.apikey = None
        self.authenticated = False
        self.cmd = None
        self.kwargs = None
        # For the responses
        self.data = None
        self.msg = None
        self.result_type = 'error'
        # Possible general params
        self.callback = None
        self.out_type = out
        self.debug = None

    def checkParams(self, *args, **kwargs):

        if not plexpy.CONFIG.API_ENABLED:
            self.msg = 'API not enabled'
        elif not plexpy.CONFIG.API_KEY:
            self.msg = 'API key not generated'
        elif len(plexpy.CONFIG.API_KEY) != 32:
            self.msg = 'API key not generated correctly'
        elif 'apikey' not in kwargs:
            self.msg = 'Parameter apikey is required'
        elif kwargs.get('apikey', '') != plexpy.CONFIG.API_KEY:
            self.msg = 'Invalid apikey'
        elif 'cmd' not in kwargs:
            self.msg = 'Parameter %s required. possible commands are: %s' % ', '.join(cmd_list)
        elif 'cmd' in kwargs and kwargs.get('cmd') not in cmd_list:
            self.msg = 'Unknown command, %s possible commands are: %s' % (kwargs.get('cmd', ''), ', '.join(cmd_list))

        # Set default values or remove them from kwargs

        self.callback = kwargs.pop('callback', None)
        self.apikey = kwargs.pop('apikey', None)
        self.cmd = kwargs.pop('cmd', None)
        self.debug = kwargs.pop('debug', False)
        # Allow override for the api.
        self.out_type = kwargs.pop('out_type', 'json')

        if self.apikey == plexpy.CONFIG.API_KEY and plexpy.CONFIG.API_ENABLED and self.cmd in cmd_list:
            self.authenticated = True
            self.msg = None
        elif self.cmd == 'getApikey' and plexpy.CONFIG.API_ENABLED:
            self.authenticated = True
            # Remove the old error msg
            self.msg = None

        self.kwargs = kwargs

    def _responds(self, result_type='success', data=None, msg=''):

        if data is None:
            data = {}
        return {"response": {"result": result_type, "message": msg, "data": data}}

    def _out_as(self, out):

        if self.out_type == 'json':
            cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
            try:
                out = json.dumps(out, indent=4, sort_keys=True)
                if self.callback is not None:
                    cherrypy.response.headers['Content-Type'] = 'application/javascript'
                    # wrap with JSONP call if requested
                    out = self.callback + '(' + out + ');'
            # if we fail to generate the output fake an error
            except Exception as e:
                logger.info(u"API :: " + traceback.format_exc())
                out['message'] = traceback.format_exc()
                out['result'] = 'error'
        if self.out_type == 'xml':
            cherrypy.response.headers['Content-Type'] = 'application/xml'
            try:
                out = xmltodict.unparse(out, pretty=True)
            except ValueError as e:
                logger.error('Failed to parse xml result')
                try:
                    out['message'] = e
                    out['result'] = 'error'
                    out = xmltodict.unparse(out, pretty=True)

                except Exception as e:
                    logger.error('Failed to parse xml result error message')
                    out = '''<?xml version="1.0" encoding="utf-8"?>
                                <response>
                                    <message>%s</message>
                                    <data></data>
                                    <result>error</result>
                                </response>
                          ''' % e

        return out

    def fetchData(self):

        logger.info('Recieved API command: %s' % self.cmd)
        if self.cmd and self.authenticated:
            methodtocall = getattr(self, "_" + self.cmd)
            # Let the traceback hit cherrypy so we can
            # see the traceback there
            if self.debug:
                methodtocall(**self.kwargs)
            else:
                try:
                    methodtocall(**self.kwargs)
                except Exception as e:
                    logger.error(traceback.format_exc())

        # Im just lazy, fix me plx
        if self.data or isinstance(self.data, (dict, list)):
            if len(self.data):
                self.result_type = 'success'

        return self._out_as(self._responds(result_type=self.result_type, msg=self.msg, data=self.data))

    def _dic_from_query(self, query):

        myDB = database.DBConnection()
        rows = myDB.select(query)

        rows_as_dic = []

        for row in rows:
            row_as_dic = dict(zip(row.keys(), row))
            rows_as_dic.append(row_as_dic)

        return rows_as_dic

    def _getApikey(self, username='', password=''):
        """ Returns api key, requires username and password is active """

        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        if plexpy.CONFIG.HTTP_USERNAME and plexpy.CONFIG.HTTP_PASSWORD:
            if username == plexpy.HTTP_USERNAME and password == plexpy.CONFIG.HTTP_PASSWORD:
                if plexpy.CONFIG.API_KEY:
                    self.data = plexpy.CONFIG.API_KEY
                else:
                    self.data = apikey
                    plexpy.CONFIG.API_KEY = apikey
                    plexpy.CONFIG.write()
            else:
                self.msg = 'Authentication is enabled, please add the correct username and password to the parameters'
        else:
            if plexpy.CONFIG.API_KEY:
                self.data = plexpy.CONFIG.API_KEY
            else:
                # Make a apikey if the doesn't exist
                self.data = apikey
                plexpy.CONFIG.API_KEY = apikey
                plexpy.CONFIG.write()

        return self.data

    def _getLogs(self, sort='', search='', order='desc', regex='', **kwargs):
        """
            Returns the log

            Returns [{"response":
                                {"msg": "Hey",
                                 "result": "success"},
                                 "data": [{"time": "29-sept.2015",
                                            "thread: "MainThread",
                                            "msg: "Called x from y",
                                            "loglevel": "DEBUG"
                                           }
                                        ]

                                }
                    ]
        """
        logfile = os.path.join(plexpy.CONFIG.LOG_DIR, 'plexpy.log')
        templog = []
        start = int(kwargs.get('start', 0))
        end = int(kwargs.get('end', 0))

        if regex:
            logger.debug('Filtering log using regex %s' % regex)
            reg = re.compile('u' + regex, flags=re.I)

        for line in open(logfile, 'r').readlines():
            temp_loglevel_and_time = None

            try:
                temp_loglevel_and_time = line.split('- ')
                loglvl = temp_loglevel_and_time[1].split(' :')[0].strip()
                tl_tread = line.split(' :: ')
                if loglvl is None:
                    msg = line.replace('\n', '')
                else:
                    msg = line.split(' : ')[1].replace('\n', '')
                thread = tl_tread[1].split(' : ')[0]
            except IndexError:
                # We assume this is a traceback
                tl = (len(templog) - 1)
                templog[tl]['msg'] += line.replace('\n', '')
                continue

            if len(line) > 1 and temp_loglevel_and_time is not None and loglvl in line:

                d = {
                    'time': temp_loglevel_and_time[0],
                    'loglevel': loglvl,
                    'msg': msg.replace('\n', ''),
                    'thread': thread
                }
                templog.append(d)

        if end > 0:
                logger.debug('Slicing the log from %s to %s' % (start, end))
                templog = templog[start:end]

        if sort:
            logger.debug('Sorting log based on %s' % sort)
            templog = sorted(templog, key=lambda k: k[sort])

        if search:
            logger.debug('Searching log values for %s' % search)
            tt = [d for d in templog for k, v in d.items() if search.lower() in v.lower()]

            if len(tt):
                templog = tt

        if regex:
            tt = []
            for l in templog:
                stringdict = ' '.join('{}{}'.format(k, v) for k, v in l.items())
                if reg.search(stringdict):
                    tt.append(l)

            if len(tt):
                templog = tt

        if order == 'desc':
            templog = templog[::-1]

        self.data = templog
        return templog

    def _getVersion(self, **kwargs):
        self.data = {
            'git_path': plexpy.CONFIG.GIT_PATH,
            'install_type': plexpy.INSTALL_TYPE,
            'current_version': plexpy.CURRENT_VERSION,
            'latest_version': plexpy.LATEST_VERSION,
            'commits_behind': plexpy.COMMITS_BEHIND,
        }
        self.result_type = 'success'

    def _checkGithub(self, **kwargs):
        versioncheck.checkGithub()
        self._getVersion()

    def _shutdown(self, **kwargs):
        plexpy.SIGNAL = 'shutdown'
        self.msg = 'Shutting down plexpy'
        self.result_type = 'success'

    def _restart(self, **kwargs):
        plexpy.SIGNAL = 'restart'
        self.msg = 'Restarting plexpy'
        self.result_type = 'success'

    def _update(self, **kwargs):
        plexpy.SIGNAL = 'update'
        self.msg = 'Updating plexpy'
        self.result_type = 'success'

    def _getHistory(self, user=None, user_id=None, rating_key='', parent_rating_key='', grandparent_rating_key='', start_date='', **kwargs):

        custom_where = []
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

        data_factory = datafactory.DataFactory()
        history = data_factory.get_datatables_history(kwargs=kwargs, custom_where=custom_where)

        self.data = history
        return self.data

    def _getSync(self, machine_id=None, user_id=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        server_id = pms_connect.get_server_identity()

        plex_tv = plextv.PlexTV()
        if not machine_id:
            result = plex_tv.get_synced_items(machine_id=server_id['machine_identifier'], user_id=user_id)
        else:
            result = plex_tv.get_synced_items(machine_id=machine_id, user_id=user_id)

        if result:
            self.data = result
            return result
        else:
            self.msg = 'Unable to retrieve sync data for user'
            logger.warn('Unable to retrieve sync data for user.')

    def _getMetadata(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata(rating_key, 'dict')

        if result:
            self.data = result
            return result
        else:
            self.msg = 'Unable to retrive metadata %s' % rating_key
            logger.warn('Unable to retrieve data.')

    def _getSettings(self):
        interface_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if
                          os.path.isdir(os.path.join(interface_dir, name))]

        config = {
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": plexpy.CONFIG.HTTP_PASSWORD,
            "launch_browser": bool(plexpy.CONFIG.LAUNCH_BROWSER),
            "enable_https": bool(plexpy.CONFIG.ENABLE_HTTPS),
            "https_cert": plexpy.CONFIG.HTTPS_CERT,
            "https_key": plexpy.CONFIG.HTTPS_KEY,
            "api_enabled": plexpy.CONFIG.API_ENABLED,
            "api_key": plexpy.CONFIG.API_KEY,
            "update_db_interval": plexpy.CONFIG.UPDATE_DB_INTERVAL,
            "freeze_db": bool(plexpy.CONFIG.FREEZE_DB),
            "log_dir": plexpy.CONFIG.LOG_DIR,
            "cache_dir": plexpy.CONFIG.CACHE_DIR,
            "check_github": bool(plexpy.CONFIG.CHECK_GITHUB),
            "interface_list": interface_list,
            "cache_sizemb": plexpy.CONFIG.CACHE_SIZEMB,
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_logs_folder": plexpy.CONFIG.PMS_LOGS_FOLDER,
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "pms_ssl": bool(plexpy.CONFIG.PMS_SSL),
            "pms_use_bif": bool(plexpy.CONFIG.PMS_USE_BIF),
            "pms_uuid": plexpy.CONFIG.PMS_UUID,
            "date_format": plexpy.CONFIG.DATE_FORMAT,
            "time_format": plexpy.CONFIG.TIME_FORMAT,
            "grouping_global_history": bool(plexpy.CONFIG.GROUPING_GLOBAL_HISTORY),
            "grouping_user_history": bool(plexpy.CONFIG.GROUPING_USER_HISTORY),
            "grouping_charts": bool(plexpy.CONFIG.GROUPING_CHARTS),
            "movie_notify_enable": bool(plexpy.CONFIG.MOVIE_NOTIFY_ENABLE),
            "tv_notify_enable": bool(plexpy.CONFIG.TV_NOTIFY_ENABLE),
            "music_notify_enable": bool(plexpy.CONFIG.MUSIC_NOTIFY_ENABLE),
            "tv_notify_on_start": bool(plexpy.CONFIG.TV_NOTIFY_ON_START),
            "movie_notify_on_start": bool(plexpy.CONFIG.MOVIE_NOTIFY_ON_START),
            "music_notify_on_start": bool(plexpy.CONFIG.MUSIC_NOTIFY_ON_START),
            "tv_notify_on_stop": bool(plexpy.CONFIG.TV_NOTIFY_ON_STOP),
            "movie_notify_on_stop": bool(plexpy.CONFIG.MOVIE_NOTIFY_ON_STOP),
            "music_notify_on_stop": bool(plexpy.CONFIG.MUSIC_NOTIFY_ON_STOP),
            "tv_notify_on_pause": bool(plexpy.CONFIG.TV_NOTIFY_ON_PAUSE),
            "movie_notify_on_pause": bool(plexpy.CONFIG.MOVIE_NOTIFY_ON_PAUSE),
            "music_notify_on_pause": bool(plexpy.CONFIG.MUSIC_NOTIFY_ON_PAUSE),
            "monitoring_interval": plexpy.CONFIG.MONITORING_INTERVAL,
            "refresh_users_interval": plexpy.CONFIG.REFRESH_USERS_INTERVAL,
            "refresh_users_on_startup": bool(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "ip_logging_enable": bool(plexpy.CONFIG.IP_LOGGING_ENABLE),
            "movie_logging_enable": bool(plexpy.CONFIG.MOVIE_LOGGING_ENABLE),
            "tv_logging_enable": bool(plexpy.CONFIG.TV_LOGGING_ENABLE),
            "music_logging_enable": bool(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "pms_is_remote": bool(plexpy.CONFIG.PMS_IS_REMOTE),
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
            "home_stats_type": bool(plexpy.CONFIG.HOME_STATS_TYPE),
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "home_stats_cards": plexpy.CONFIG.HOME_STATS_CARDS,
            "home_library_cards": plexpy.CONFIG.HOME_LIBRARY_CARDS,
            "buffer_threshold": plexpy.CONFIG.BUFFER_THRESHOLD,
            "buffer_wait": plexpy.CONFIG.BUFFER_WAIT
        }

        self.data = config
        return config

    def _getUserips(self, user_id=None, user=None, **kwargs):
        custom_where = []
        if user_id:
            custom_where = [['user_id', user_id]]
        elif user:
            custom_where = [['user', user]]

        user_data = users.Users()
        history = user_data.get_user_unique_ips(kwargs=kwargs,
                                                custom_where=custom_where)

        if history:
            self.data = history
            return history
        else:
            self.msg = 'Failed to find users ips'

    def _getPlayby(self, time_range='30', y_axis='plays', playtype='total_plays_per_month', **kwargs):

        graph = graphs.Graphs()
        if playtype == 'total_plays_per_month':
            result = graph.get_total_plays_per_month(y_axis=y_axis)

        elif playtype == 'total_plays_per_day':
            result = graph.get_total_plays_per_day(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_per_hourofday':
            result = graph.get_total_plays_per_hourofday(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_per_dayofweek':
            result = graph.get_total_plays_per_dayofweek(time_range=time_range, y_axis=y_axis)

        elif playtype == 'stream_type_by_top_10_users':
            result = graph.get_stream_type_by_top_10_users(time_range=time_range, y_axis=y_axis)

        elif playtype == 'stream_type_by_top_10_platforms':
            result = graph.get_stream_type_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_stream_resolution':
            result = graph.get_total_plays_by_stream_resolution(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_source_resolution':
            result = graph.get_total_plays_by_source_resolution(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_per_stream_type':
            result = graph.get_total_plays_per_stream_type(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_top_10_users':
            result = graph.get_total_plays_by_top_10_users(time_range=time_range, y_axis=y_axis)

        elif playtype == 'total_plays_by_top_10_platforms':
            result = graph.get_total_plays_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        if result:
            self.data = result
            return result
        else:
            logger.warn('Unable to retrieve %s from db' % playtype)
