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

import os
from Queue import Queue
import sqlite3
import sys
import subprocess
import websocket
import threading
from threading import Event, Thread
import datetime
import uuid
from plextv import PlexTV

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import helpers
import json
import http_handler
import plexpy
import activity_handler
import activity_processor
import activity_pinger
import database
import logger
from config import bool_int, ServerConfig
from web_socket import ServerWebSocket
from pmsconnect import PmsConnect
import libraries
import users
import session


class plexServers(object):
    SCHED = None
    SCHED_LOCK = None
    SCHED_LIST = []

    def __init__(self):
        self.SCHED = BackgroundScheduler()
        self.SCHED_LOCK = threading.Lock()

        db = database.MonitorDatabase()
        result = db.select('SELECT * FROM servers')
        for pms in result:
            name = pms['pms_name']
            vars(self)[name] = plexServer(pms)

        self.initialize_scheduler()

    def __iter__(self):
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer):
                yield server

    def __getattr__(self, key):
        return getattr(self, key)

    def __setattr__(self, key, value):
        vars(self)[key] = value

    def start(self):
        if plexpy.CONFIG.REFRESH_SERVERS_ON_STARTUP:
            self.refresh()

        if plexpy.CONFIG.REFRESH_USERS_ON_STARTUP:
            threading.Thread(target=self.refresh_users).start()

        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and server.CONFIG.PMS_IS_ENABLED and not server.CONFIG.PMS_IS_DELETED:
                server.start()

    def stop(self):
        if self.SCHED.running:
            self.SCHED.shutdown(wait=False)
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and server.PLEX_SERVER_UP:
                server.shutdown()

    def delete(self, server_id=None, keep_history=True):
        result = False
        if server_id:
            server = plexpy.PMS_SERVERS.get_server_by_id(server_id)
            result = server.delete(keep_history=keep_history)
            if result and not keep_history:
                delattr(self, server.CONFIG.PMS_NAME)
        return result

    def refresh(self):
        logger.info(u"Tautulli Servers :: Servers refreshing...")
        thread_list = []
        new_servers = False

        if plexpy.PLEXTV:
            plextv_servers = plexpy.PLEXTV.get_servers_list(include_cloud=True, all_servers=False)
            if plextv_servers:
                for server in plextv_servers:
                    pmsServer = self.get_server_by_identifier(server['pms_identifier'])
                    if pmsServer:
                        pmsServer.CONFIG.process_kwargs(server)
                        if not pmsServer.CONFIG.PMS_IS_DELETED:
                            t = threading.Thread(target=pmsServer.refresh)
                            t.start()
                            thread_list.append(t)
                    else:
                        new_servers = True
                        pmsServer = plexServer(server)
                        logger.info(u"Tautulli Servers :: %s: Server Discovered..." % pmsServer.CONFIG.PMS_NAME)
                        t = threading.Thread(target=pmsServer.refresh)
                        t.start()
                        thread_list.append(t)
                for t in thread_list:
                    t.join()
                if new_servers:
                    threading.Thread(target=self.refresh_users).start()

        # Mark as deleted any servers that the token doesn't match the current PlexTV account token
        for server in plexpy.PMS_SERVERS:
            if server.CONFIG.PMS_TOKEN != plexpy.CONFIG.PMS_TOKEN:
                server.delete(keep_history=True)

    def refresh_libraries(self):
        thread_list = []
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and server.PLEX_SERVER_UP:
                result = server.refresh_libraries()
                t = threading.Thread(target=server.refresh)
                t.start()
                thread_list.append(t)
        for t in thread_list:
            t.join()
        return True

    def refresh_users(self):
        result = users.refresh_users()
        return result

    def get_server_by_id(self, server_id):
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and int(server_id) == server.CONFIG.ID:
                return server

    def get_server_by_identifier(self, pms_identifier):
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and pms_identifier == server.CONFIG.PMS_IDENTIFIER:
                return server

    def get_server_ids(self):
        server_ids = []
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer):
                if session.allow_session_server(server.CONFIG.ID):
                    server_ids.append(server.CONFIG.ID)
        return server_ids

    def get_server_names(self):
        server_names = []
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer):
                if session.allow_session_server(server.CONFIG.ID):
                    server_name = {'server_id': server.CONFIG.ID, 'pms_name': server.CONFIG.PMS_NAME}
                    server_names.append(server_name)
        return server_names

    def get_recently_added_media(self, server_id=None, count='0', media_type='', **kwargs):
        recently_added = []
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and server.PLEX_SERVER_UP:
                if session.allow_session_server(server.CONFIG.ID):
                    if server_id and int(server_id) != server.CONFIG.ID:
                        continue
                    result = server.PMSCONNECTION.get_recently_added_details(count=count, media_type=media_type)
                    if 'recently_added' in result:
                        recently_added.append({'server_name': server_name, 'server_id': server.CONFIG.ID, 'items': result['recently_added']})
                    if server_id:
                        break
        if recently_added:
            recently_added = sorted(recently_added, key=lambda k: k['server_name'])

        return recently_added

    def get_server_status(self, server_id=None, session_key=None, **kwargs):
        server_status = {
            'data': [],
            'recordsFiltered': 0,
            'recordsTotal': 0,
            }

        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer) and not server.CONFIG.PMS_IS_DELETED:
                if session.allow_session_server(server.CONFIG.ID):
                    server_status['data'].append(server.get_server_status())

        server_status['recordsFiltered'] = len(server_status['data'])
        server_status['recordsTotal'] = len(server_status['data'])

        return server_status

    def get_current_activity(self, server_id=None, session_key=None, **kwargs):
        current_activity = {
            'lan_bandwidth': 0,
            'sessions': [],
            'stream_count': 0,
            'stream_count_direct_play': 0,
            'stream_count_direct_stream': 0,
            'stream_count_transcode': 0,
            'total_bandwidth': 0,
            'wan_bandwidth': 0,
            'servers': []
        }
        for (server_name, server) in self.__dict__.items():
            if isinstance(server, plexServer):
                if (server_id and int(server_id) != server.CONFIG.ID) or not server.CONFIG.PMS_IS_ENABLED or not server.WS_CONNECTED:
                    continue
                if session.allow_session_server(server.CONFIG.ID):
                    server_activity = server.get_current_activity(session_key=session_key, **kwargs)
                    if server_activity:
                        current_activity['sessions'].extend(server_activity['sessions'])
                        current_activity['lan_bandwidth'] += int(server_activity['lan_bandwidth'])
                        current_activity['stream_count'] += int(server_activity['stream_count'])
                        current_activity['stream_count_direct_play'] += int(server_activity['stream_count_direct_play'])
                        current_activity['stream_count_direct_stream'] += int(server_activity['stream_count_direct_stream'])
                        current_activity['stream_count_transcode'] += int(server_activity['stream_count_transcode'])
                        current_activity['total_bandwidth'] += int(server_activity['total_bandwidth'])
                        current_activity['wan_bandwidth'] += int(server_activity['wan_bandwidth'])
                        current_activity['servers'].append(server_activity)

        return current_activity

    def initialize_scheduler(self):
        """
        Start the scheduled background tasks. Re-schedule if interval settings changed.
        """
        self.SCHED_LIST = []
        server_hours = plexpy.CONFIG.REFRESH_SERVERS_INTERVAL if 1 <= plexpy.CONFIG.REFRESH_SERVERS_INTERVAL <= 24 else 12
        self.SCHED_LIST.append({'name': 'Refresh Plex Servers',
                                'time': {'hours': server_hours, 'minutes': 0, 'seconds': 0},
                                'func': self.refresh,
                                'args': [],
                                })

        user_hours = plexpy.CONFIG.REFRESH_USERS_INTERVAL if 1 <= plexpy.CONFIG.REFRESH_USERS_INTERVAL <= 24 else 12
        self.SCHED_LIST.append({'name': 'Refresh Users List',
                                'time': {'hours': user_hours, 'minutes': 0, 'seconds': 0},
                                'func': self.refresh_users,
                                'args': [],
                                })

        plexpy.schedule_joblist(lock=self.SCHED_LOCK, scheduler=self.SCHED, jobList=self.SCHED_LIST)


class plexServer(object):

    _server_id = 0
    _server_name = ''
    CONFIG = None
    PLEX_SERVER_UP = None
    WS_CONNECTED = False
    WS = None
    PMSCONNECTION = None
    SCHED = None
    SCHED_LOCK = None
    SCHED_LIST = []
    monitor_lock = None
    ping_count = 0
    server_shutdown = False
    update_available = False
    rclone_status = None
    remote_access_status = None

    def __init__(self, pms):
        self.CONFIG = ServerConfig(pms)
        self._server_id = self.CONFIG.ID
        self._server_name = self.CONFIG.PMS_NAME
        self.PMSCONNECTION = PmsConnect(server=self)
        self.SCHED = BackgroundScheduler()
        self.SCHED_LOCK = threading.Lock()
        self.monitor_lock = threading.Lock()

        if plexpy.PMS_SERVERS:
            setattr(plexpy.PMS_SERVERS, self.CONFIG.PMS_NAME, self)

    def start(self):
        if self.CONFIG.PMS_IS_ENABLED:
            logger.info(u"Tautulli Servers :: %s: Monitor Starting." % self.CONFIG.PMS_NAME)
            self.PMSCONNECTION = PmsConnect(server=self)
            self.server_shutdown = False
            ready = Event()
            self.WS = ServerWebSocket(self, ready)
            self.WS.start()
            ready.wait()

            if self.CONFIG.MONITOR_REMOTE_ACCESS:
                activity_pinger.check_server_access(self)

            if plexpy.CONFIG.MONITOR_RCLONE and self.CONFIG.MONITOR_RCLONE_MOUNT:
                activity_pinger.check_rclone_status(self)

            if self.PLEX_SERVER_UP and self.WS_CONNECTED:
                # Refresh the libraries list on startup
                if plexpy.PLEXTV and self.CONFIG.PMS_IP and self.CONFIG.REFRESH_LIBRARIES_ON_STARTUP:
                    threading.Thread(target=self.refresh_libraries).start()

            self.initialize_scheduler()

    def shutdown(self):
        logger.info(u"Tautulli Servers :: %s: Stopping Server Monitoring." % self.CONFIG.PMS_NAME)
        self.server_shutdown = True
        self.WS.shutdown()
        self.initialize_scheduler()
        self.PLEX_SERVER_UP = None

    def restart(self):
        logger.info(u"Tautulli Servers :: %s: Restarting Server." % self.CONFIG.PMS_NAME)
        self.shutdown()
        self.start()

    def get_config(self):

        config = {'id': self.CONFIG.ID,
                  'pms_name': self.CONFIG.PMS_NAME,
                  'pms_ip': self.CONFIG.PMS_IP,
                  'pms_port': self.CONFIG.PMS_PORT,
                  'pms_identifier': self.CONFIG.PMS_IDENTIFIER,
                  'pms_token': self.CONFIG.PMS_TOKEN,
                  'pms_is_enabled': self.CONFIG.PMS_IS_ENABLED,
                  'pms_is_deleted': self.CONFIG.PMS_IS_DELETED,
                  'pms_is_remote': self.CONFIG.PMS_IS_REMOTE,
                  'pms_is_cloud': self.CONFIG.PMS_IS_CLOUD,
                  'pms_ssl': self.CONFIG.PMS_SSL,
                  'pms_ssl_pref': self.CONFIG.PMS_SSL_PREF,
                  'pms_uri': self.CONFIG.PMS_URI,
                  'pms_url': self.CONFIG.PMS_URL,
                  'pms_url_manual': self.CONFIG.PMS_URL_MANUAL,
                  'pms_web_url': self.CONFIG.PMS_WEB_URL,
                  'pms_url_override': self.CONFIG.PMS_URL_OVERRIDE,
                  'pms_use_bif': self.CONFIG.PMS_USE_BIF,
                  'pms_update_channel': self.CONFIG.PMS_UPDATE_CHANNEL,
                  'pms_version': self.CONFIG.PMS_VERSION,
                  'pms_platform': self.CONFIG.PMS_PLATFORM,
                  'pms_update_distro': self.CONFIG.PMS_UPDATE_DISTRO,
                  'pms_update_distro_build': self.CONFIG.PMS_UPDATE_DISTRO_BUILD,
                  "refresh_libraries_interval": self.CONFIG.REFRESH_LIBRARIES_INTERVAL,
                  "refresh_libraries_on_startup": self.CONFIG.REFRESH_LIBRARIES_ON_STARTUP,
                  "monitor_pms_updates": self.CONFIG.MONITOR_PMS_UPDATES,
                  "monitor_remote_access": self.CONFIG.MONITOR_REMOTE_ACCESS,
                  "monitor_rclone_mount": self.CONFIG.MONITOR_RCLONE_MOUNT,
                  "rclone_user": self.CONFIG.RCLONE_USER,
                  "rclone_pass": self.CONFIG.RCLONE_PASS,
                  "rclone_mountdir": self.CONFIG.RCLONE_MOUNTDIR,
                  "rclone_tmpdir": self.CONFIG.RCLONE_TMPDIR,
                  "rclone_testfile": self.CONFIG.RCLONE_TESTFILE,
                  "rclone_port": self.CONFIG.RCLONE_PORT,
                  "rclone_ssl": self.CONFIG.RCLONE_SSL,
                  "rclone_ssl_hostname": self.CONFIG.RCLONE_SSL_HOSTNAME,
                  }

        return config

    def refresh(self):
        logger.info(u"Tautulli Servers :: %s: Refreshing..." % self.CONFIG.PMS_NAME)
        self.PMSCONNECTION = PmsConnect(server=self)
        self.refresh_libraries()

        self.update_available = False
        if self.CONFIG.MONITOR_PMS_UPDATES:
            server_info = self.PMSCONNECTION.get_server_info()
            if server_info:
                self.CONFIG.PMS_UPDATE_DISTRO = server_info['distro']
                self.CONFIG.PMS_UPDATE_DISTRO_BUILD = server_info['distro_build']
                self.update_available = server_info['update_available']

    def refresh_libraries(self):
        result = libraries.refresh_libraries(server_id=self._server_id)
        return result

    def get_server_status(self):
        server_status = {
            'server_id': self.CONFIG.ID,
            'pms_name': self.CONFIG.PMS_NAME,
            'sessions': [],
            'stream_count': '',
            'stream_count_direct_play': '',
            'stream_count_direct_stream': '',
            'stream_count_transcode': '',
            'total_bandwidth': '',
            'wan_bandwidth': '',
            'lan_bandwidth': '',
            'update_available': '',
            'server_status': '',
            'rclone_status': '',
        }

        """
         Server Status:
            0 - Server not enabled
            1 - Server enabled and functioning
            2 - 
            3 - Server not connected
        """
        server_status['server_status'] = (0 if not self.CONFIG.PMS_IS_ENABLED else
                                          1 if self.WS_CONNECTED else
                                          3
                                          )

        """
         Remote Access Status:
            0 - Server not enabled
            1 - Remote Access monitoring not enabled for this server
            2 - Remote Access is up
            3 - Remote Access is down
        """
        server_status['remote_access_status'] = (0 if not self.CONFIG.PMS_IS_ENABLED or self.remote_access_status == None or not self.WS_CONNECTED else
                                                 1 if not self.CONFIG.MONITOR_REMOTE_ACCESS else
                                                 2 if self.remote_access_status else
                                                 3
                                                 )
        """
         rclone Status:
            0 - rclone monitoring not enabled
            1 - rclone monitoring not enabled for this server
            2 - rclone is alive and well
            3 - rclone not functioning
        """
        server_status['rclone_status'] = (0 if not self.CONFIG.PMS_IS_ENABLED else
                                          1 if plexpy.CONFIG.MONITOR_RCLONE and not self.CONFIG.MONITOR_RCLONE_MOUNT else
                                          2 if self.rclone_status else
                                          3
                                          )

        if self.CONFIG.PMS_IS_ENABLED:
            if self.WS and self.WS.WS_CONNECTION and self.WS.WS_CONNECTION.connected:
                server_status.update(self.get_current_activity())

        server_status['update_available'] = (1 if self.update_available else 0)

        return server_status

    def get_current_activity(self, session_key=None, **kwargs):
        current_activity = {
            'server_id': self.CONFIG.ID,
            'pms_name': self.CONFIG.PMS_NAME,
            'sessions': [],
            'stream_count': 0,
            'stream_count_direct_play': 0,
            'stream_count_direct_stream': 0,
            'stream_count_transcode': 0,
            'total_bandwidth': 0,
            'wan_bandwidth': 0,
            'lan_bandwidth': 0,
        }

        if self.WS and self.WS.WS_CONNECTION and self.WS.WS_CONNECTION.connected:
            activity = self.PMSCONNECTION.get_current_activity()

            if activity:
                current_activity.update(activity)
                counts = {'stream_count_direct_play': 0,
                          'stream_count_direct_stream': 0,
                          'stream_count_transcode': 0,
                          'total_bandwidth': 0,
                          'lan_bandwidth': 0,
                          'wan_bandwidth': 0}

                for s in current_activity['sessions']:
                    if s['transcode_decision'] == 'transcode':
                        counts['stream_count_transcode'] += 1
                    elif s['transcode_decision'] == 'copy':
                        counts['stream_count_direct_stream'] += 1
                    else:
                        counts['stream_count_direct_play'] += 1

                    counts['total_bandwidth'] += helpers.cast_to_int(s['bandwidth'])
                    if s['location'] == 'lan':
                        counts['lan_bandwidth'] += helpers.cast_to_int(s['bandwidth'])
                    else:
                        counts['wan_bandwidth'] += helpers.cast_to_int(s['bandwidth'])

                current_activity.update(counts)

        return current_activity

    def initialize_scheduler(self):
        """
        Start the scheduled background tasks. Re-schedule if interval settings changed.
        """
        if self.server_shutdown or not self.CONFIG.PMS_IS_ENABLED:
            for job in self.SCHED.get_jobs():
                plexpy.schedule_job(self.SCHED, None, job.id, hours=0, minutes=0, seconds=0)
        else:
            self.SCHED_LIST = []

            checker_jobname = '%s: Check Server Connection' % self.CONFIG.PMS_NAME
            self.SCHED_LIST.append({'name': checker_jobname,
                                    'time': {'hours': 0, 'minutes': 0, 'seconds': 30},
                                    'func': activity_pinger.connect_server,
                                    'args': [self],
                                    })

            rclone_jobname = '%s: Check Rclone Mount Status' % self.CONFIG.PMS_NAME
            if plexpy.CONFIG.MONITOR_RCLONE:
                rclone_time = (30 if self.CONFIG.MONITOR_RCLONE_MOUNT else 0)
                self.SCHED_LIST.append({'name': rclone_jobname,
                                        'time': {'hours': 0, 'minutes': 0, 'seconds': rclone_time},
                                        'func': activity_pinger.check_rclone_status,
                                        'args': [self],
                                        })
            elif self.SCHED.get_job(rclone_jobname):
                plexpy.schedule_job(self.SCHED, None, rclone_jobname, hours=0, minutes=0, seconds=0)

            # Start the Plex and rclone checkers if the server is supposed to be connected.
            plexpy.schedule_joblist(lock=self.SCHED_LOCK, scheduler=self.SCHED, jobList=self.SCHED_LIST)

            library_hours = self.CONFIG.REFRESH_LIBRARIES_INTERVAL if 1 <= self.CONFIG.REFRESH_LIBRARIES_INTERVAL <= 24 else 12
            self.SCHED_LIST.append({'name': '%s: Check Plex remote access' % self.CONFIG.PMS_NAME,
                                    'time': {'hours': 0, 'minutes': 0, 'seconds': 60 * bool(self.CONFIG.MONITOR_REMOTE_ACCESS)},
                                    'func': activity_pinger.check_server_access,
                                    'args': [self],
                                    })

            self.SCHED_LIST.append({'name': '%s: Check for Plex updates' % self.CONFIG.PMS_NAME,
                                    'time': {'hours': 0, 'minutes': 15 * bool(self.CONFIG.MONITOR_PMS_UPDATES), 'seconds': 0},
                                    'func': activity_pinger.check_server_updates,
                                    'args': [self],
                                    })

            self.SCHED_LIST.append({'name': '%s: Refresh Libraries List' % self.CONFIG.PMS_NAME,
                                    'time': {'hours': library_hours, 'minutes': 0, 'seconds': 0},
                                    'func': self.refresh_libraries,
                                    'args': [],
                                    })

            self.SCHED_LIST.append({'name': '%s: Websocket ping' % self.CONFIG.PMS_NAME,
                                    'time': {'hours': 0, 'minutes': 0, 'seconds': 10 * bool(plexpy.CONFIG.WEBSOCKET_MONITOR_PING_PONG)},
                                    'func': self.WS.send_ping,
                                    'args': [],
                                    })

            if self.WS_CONNECTED:
                plexpy.schedule_joblist(lock=self.SCHED_LOCK, scheduler=self.SCHED, jobList=self.SCHED_LIST)
            else:
                # Cancel all jobs except the PMS connection and rclone status checkers.
                for job in self.SCHED.get_jobs():
                    if job.id not in [checker_jobname, rclone_jobname]:
                        plexpy.schedule_job(self.SCHED, None, job.id, hours=0, minutes=0, seconds=0)

    def delete(self, keep_history=False):
        logger.info(u"Tautulli Servers :: %s: Deleting server from database." % self.CONFIG.PMS_NAME)
        self.CONFIG.PMS_IS_ENABLED = False
        self.CONFIG.PMS_IS_DELETED = True
        if self.WS_CONNECTED:
            self.shutdown()

        if not keep_history:
            try:
                delete_history = self.delete_all_history()
                delete_libraries = self.delete_all_libraries()
                delete_users = self.delete_all_users()
                monitor_db = database.MonitorDatabase()
                logger.info(u"Tautulli Servers :: %s: Deleting server from database." % self.CONFIG.PMS_NAME)
                server_del = monitor_db.action('DELETE FROM servers '
                                               'WHERE id = ?', [self.CONFIG.ID])
                return True

            except Exception as e:
                logger.warn(
                    "Tautulli Servers :: %s: Unable to execute database query for delete_all_history: %s." % (
                    self.CONFIG.PMS_NAME, e))
                return False

        return True

    def undelete(self):
        self.CONFIG.PMS_IS_DELETED = False
        self.refresh()
        threading.Thread(target=plexpy.PMS_SERVERS.refresh_users).start()
        return True

    def delete_all_history(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli Servers :: %s: Deleting all history from database." % self.CONFIG.PMS_NAME)
            query = 'SELECT session_key FROM sessions WHERE server_id = ?'
            result = monitor_db.select(query, [self.CONFIG.ID])
            ap = activity_processor.ActivityProcessor(server=self)
            for item in result:
                ap.delete_session(session_key=item['session_key'])
                activity_handler.delete_metadata_cache(session_key=item['session_key'], server=self)
            sessions_del = \
                monitor_db.action('DELETE FROM '
                                  'sessions '
                                  'WHERE server_id = ?', [self.CONFIG.ID])
            session_history_media_info_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history_media_info '
                                  'WHERE server_id = ?', [self.CONFIG.ID])
            session_history_metadata_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history_metadata '
                                  'WHERE server_id = ?', [self.CONFIG.ID])
            session_history_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history '
                                  'WHERE server_id = ?', [self.CONFIG.ID])
            recently_added_del = \
                monitor_db.action('DELETE FROM '
                                  'recently_added '
                                  'WHERE server_id = ?', [self.CONFIG.ID])
            themoviedb_lookup_del = \
                monitor_db.action('DELETE FROM '
                                  'themoviedb_lookup '
                                  'WHERE server_id = ?', [self.CONFIG.ID])
            tvmaze_lookup_del = \
                monitor_db.action('DELETE FROM '
                                  'tvmaze_lookup '
                                  'WHERE server_id = ?', [self.CONFIG.ID])

            return True

        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_history: %s." % (self.CONFIG.PMS_NAME, e))
            return False

    def delete_all_users(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli Servers :: %s: Deleting all user tokens from database." % self.CONFIG.PMS_NAME)
            user_shared_libraries_del = \
                monitor_db.action('DELETE FROM '
                                  'user_shared_libraries '
                                  'WHERE server_id = ?', [self.CONFIG.ID])

            return True

        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_users: %s." % (self.CONFIG.PMS_NAME, e))
            return False

    def delete_all_libraries(self):
        logger.info(u"Tautulli Servers :: %s: Deleting all libraries from database." % self.CONFIG.PMS_NAME)

        monitor_db = database.MonitorDatabase()
        query = 'SELECT id FROM library_sections ' \
                'WHERE server_id = ?'
        result = monitor_db.select(query, [self.CONFIG.ID])
        if result:
            home_library_cards = plexpy.CONFIG.HOME_LIBRARY_CARDS
            for library_id in result:
                libID = str(library_id['id']).encode("utf-8").decode("utf-8")
                if libID in home_library_cards:
                    home_library_cards.remove(libID)
            plexpy.CONFIG.__setattr__('HOME_LIBRARY_CARDS', home_library_cards)
            plexpy.CONFIG.write()

        try:
            monitor_db.action('DELETE FROM '
                              'library_sections '
                              'WHERE server_id = ?', [self.CONFIG.ID])

            return True

        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_libraries: %s." % (self.CONFIG.PMS_NAME, e))
            return False

    def test_websocket(self):
        # Quick test websocket connection
        result = {}
        ws_url = self.CONFIG.PMS_URL.replace('http', 'ws', 1) + '/:/websockets/notifications'
        header = ['X-Plex-Token: %s' % self.CONFIG.PMS_TOKEN]

        logger.debug(u"Testing websocket connection...")
        try:
            test_ws = websocket.create_connection(ws_url, header=header)
            test_ws.close()
            logger.debug(u"Websocket connection test for %s successful." % self.CONFIG.PMS_NAME)
            return True
        except (websocket.WebSocketException, IOError, Exception) as e:
            logger.error("Websocket connection test for %s failed: %s" % (self.CONFIG.PMS_NAME, e))
            return False
