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

import json
import os
import time
import websocket
import threading
from threading import Event, Thread
from apscheduler.schedulers.background import BackgroundScheduler
import urllib.parse

import plexpy
from plexpy import helpers
from plexpy import common
from plexpy import http_handler
from plexpy import activity_handler
from plexpy import activity_processor
from plexpy import activity_pinger
from plexpy import database
from plexpy import logger
from plexpy.config import bool_int, ServerConfig
from plexpy.web_socket import ServerWebSocket
from plexpy import libraries
from plexpy import users
from plexpy import session


class plexServers(object):
    SCHED = None
    SCHED_LOCK = None
    SCHED_LIST = []

    def __init__(self):
        self.SCHED = BackgroundScheduler()
        self.SCHED_LOCK = threading.Lock()
        self.initialize_scheduler()
        self.update_unowned_servers()

    def __iter__(self):
        for server in self.servers:
            yield server

    def __setattr__(self, key, value):
        vars(self)[key] = value

    @property
    def servers(self):
        servers = []
        for account in plexpy.PLEXTV_ACCOUNTS.accounts:
            for server in account.servers:
                servers.append(server)
        for server in self.unowned_servers:
            servers.append(server)
        return servers

    def update_unowned_servers(self):
        # Add servers for which there are unknown PlexTV accounts
        self.unowned_servers = []
        tokens = []
        for account in plexpy.PLEXTV_ACCOUNTS.accounts:
            tokens.append(account.token)
        db = database.MonitorDatabase()
        result = db.select('SELECT * FROM servers WHERE pms_token not in ("%s")' % '","'.join(tokens))
        for serverValues in result:
            server = plexServer(serverValues)
            self.unowned_servers.append(server)

    def start(self):
        for server in self.servers:
            threading.Thread(target=server.start).start()

    def stop(self):
        if self.SCHED.running:
            self.SCHED.shutdown(wait=False)
        for server in self.servers:
            server.shutdown()

    def delete(self, server_id=None, keep_history=True):
        result = False
        if server_id:
            server = plexpy.PMS_SERVERS.get_server_by_id(server_id)
            result = server.delete(keep_history=keep_history)
            if result and not keep_history:
                delattr(self, server.CONFIG.PMS_IDENTIFIER)
        return result

    def refresh(self):
        logger.info(u"Tautulli Servers :: Servers refreshing...")
        plexpy.PLEXTV_ACCOUNTS.refresh_servers()


    def refresh_libraries(self):
        thread_list = []
        for server in self.servers:
            if server.PLEX_SERVER_UP:
                t = threading.Thread(target=server.refresh_libraries)
                t.start()
                thread_list.append(t)
        for t in thread_list:
            t.join()
        return True

    def refresh_users(self):
        result = users.refresh_users()
        return result

    def get_server_by_id(self, server_id):
        for server in self.servers:
            if int(server_id) == server.CONFIG.ID:
                return server
        return None

    def get_server_by_identifier(self, pms_identifier):
        for server in self.servers:
            if pms_identifier == server.CONFIG.PMS_IDENTIFIER:
                return server
        return None

    def get_server_ids(self):
        server_ids = []
        for server in self.servers:
            if session.allow_session_server(server.CONFIG.ID):
                server_ids.append(server.CONFIG.ID)
        return server_ids

    def get_server_names(self):
        server_names = []
        for server in self.servers:
            if session.allow_session_server(server.CONFIG.ID):
                server_name = {'server_id': server.CONFIG.ID, 'pms_name': server.CONFIG.PMS_NAME}
                server_names.append(server_name)
        return server_names

    def get_recently_added_media(self, server_id=None, count='0', media_type='', **kwargs):
        recently_added = []
        for server in self.servers:
            if server.PLEX_SERVER_UP:
                if session.allow_session_server(server.CONFIG.ID):
                    if server_id and int(server_id) != server.CONFIG.ID:
                        continue
                    result = server.get_recently_added_details(count=count, media_type=media_type)
                    if 'recently_added' in result:
                        recently_added.append({'server_name': server.CONFIG.PMS_NAME, 'server_id': server.CONFIG.ID, 'items': result['recently_added']})
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

        for server in self.servers:
            if not server.CONFIG.PMS_IS_DELETED:
                if session.allow_session_server(server.CONFIG.ID):
                    server_status['data'].append(server.get_server_status())

        server_status['recordsFiltered'] = len(server_status['data'])
        server_status['recordsTotal'] = len(server_status['data'])

        return server_status

    def get_current_activity(self, server_id=None, session_key=None, session_id=None, **kwargs):
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
        for server in self.servers:
            if (server_id and int(server_id) != server.CONFIG.ID) or not server.CONFIG.PMS_IS_ENABLED or not server.WS_CONNECTED:
                continue
            if session.allow_session_server(server.CONFIG.ID):
                server_activity = server.get_activity(session_key=session_key, **kwargs)
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

        if session_key:
            return next((s for s in current_activity['sessions'] if s['session_key'] == session_key), {})
        if session_id:
            return next((s for s in current_activity['sessions'] if s['session_id'] == session_id), {})

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
    PLEXTV = None
    CONFIG = None
    PLEX_SERVER_UP = None
    WS_CONNECTED = False
    WS = None
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
        self.SCHED = BackgroundScheduler()
        self.SCHED_LOCK = threading.Lock()
        self.monitor_lock = threading.Lock()

    @property
    def url(self):
        if self.CONFIG.PMS_SSL or self.CONFIG.PMS_URL == '':
            return self.CONFIG.PMS_URI
        else:
            return self.CONFIG.PMS_URL

    def start(self):
        if self.PLEX_SERVER_UP:
            return

        if not self.PLEXTV:
            for account in plexpy.PLEXTV_ACCOUNTS.accounts:
                if account.user_token == self.CONFIG.PMS_TOKEN:
                    self.PLEXTV = account
                    break

        if not self.PLEXTV or not self.PLEXTV.is_validated:
            logger.info(u"Tautulli Servers :: %s: Unable to start. No Valid PlexTV Account." % self.CONFIG.PMS_NAME)
            return

        if self.CONFIG.PMS_IS_ENABLED and not self.CONFIG.PMS_IS_DELETED:
            logger.info(u"Tautulli Servers :: %s: Monitor Starting." % self.CONFIG.PMS_NAME)
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
                if self.PLEXTV and self.CONFIG.PMS_IP and self.CONFIG.REFRESH_LIBRARIES_ON_STARTUP:
                    threading.Thread(target=self.refresh_libraries).start()

            self.initialize_scheduler()

    def shutdown(self):
        if self.PLEX_SERVER_UP is not None:
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
                  "owner": self.PLEXTV.username if self.PLEXTV else None,
                  }

        return config

    def refresh(self):
        logger.info(u"Tautulli Servers :: %s: Refreshing..." % self.CONFIG.PMS_NAME)
        self.refresh_libraries()

        self.update_available = False
        if self.CONFIG.MONITOR_PMS_UPDATES:
            server_info = self.get_server_info()
            if server_info:
                self.CONFIG.PMS_UPDATE_DISTRO = server_info['distro']
                self.CONFIG.PMS_UPDATE_DISTRO_BUILD = server_info['distro_build']
                self.update_available = server_info['update_available']
        if self.CONFIG.PMS_IS_ENABLED and not self.PLEX_SERVER_UP:
            self.start()

    def refresh_libraries(self):
        result = libraries.refresh_libraries(server_id=self._server_id)
        return result

    def get_server_status(self):
        server_status = {
            'id': self.CONFIG.ID,
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
            'owner': None,
        }

        """
         Server Status:
            0 - Server not enabled
            1 - Server enabled and functioning
            2 - Token not valid
            3 - Monitoring not running
            4 - Server is down
        """
        server_status['server_status'] = (0 if not self.CONFIG.PMS_IS_ENABLED else
                                          1 if self.WS_CONNECTED else
                                          2 if not self.PLEXTV or not self.PLEXTV.is_validated else
                                          3 if self.PLEX_SERVER_UP is None else
                                          4
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
                server_status.update(self.get_activity())

        server_status['update_available'] = (1 if self.update_available else 0)
        server_status['owner'] = self.PLEXTV.username if self.PLEXTV else None

        return server_status

    def get_activity(self, session_key=None, **kwargs):
        current_activity = {
            'server_id': self.CONFIG.ID,
            'pms_name': self.CONFIG.PMS_NAME,
            'plexpass': self.PLEXTV.plexpass,
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
            activity = self.get_current_activity()

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
                rclone_time = (60 if self.CONFIG.MONITOR_RCLONE_MOUNT else 0)
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
        logger.info(u"Tautulli Servers :: %s: Deleting server." % self.CONFIG.PMS_NAME)
        self.CONFIG.PMS_IS_ENABLED = False
        self.CONFIG.PMS_IS_DELETED = True
        if self.WS_CONNECTED:
            self.shutdown()
        self.delete_all_sessions()
        if not keep_history:
            try:
                self.delete_all_history()
                self.delete_all_libraries()
                self.delete_all_users()
                monitor_db = database.MonitorDatabase()
                logger.info(u"Tautulli Servers :: %s: Deleting server from database." % self.CONFIG.PMS_NAME)
                monitor_db.action('DELETE FROM servers WHERE id = ?', [self.CONFIG.ID])
                return True

            except Exception as e:
                logger.warn(
                    "Tautulli Servers :: %s: Unable to execute database query for delete_all_history: %s." % (
                    self.CONFIG.PMS_NAME, e))
                return False

        return True

    def undelete(self):
        if self.PLEXTV is None:
            for account in plexpy.PLEXTV_ACCOUNTS.accounts:
                if self.CONFIG.PMS_TOKEN == account.user_token:
                    self.PLEXTV = account
                    break

        if self.PLEXTV is None:
            msg = 'No PlexTV Account for this server'
            return False, msg

        if not self.PLEXTV.is_validated:
            msg = 'PlexTV Account Token is not valid'
            return False, msg

        self.CONFIG.PMS_IS_DELETED = False
        self.refresh()
        threading.Thread(target=plexpy.PMS_SERVERS.refresh_users).start()
        return True, ''

    def delete_all_sessions(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli Servers :: %s: Deleting all active sessions." % self.CONFIG.PMS_NAME)

            query = 'SELECT session_key FROM sessions WHERE server_id = ?'
            result = monitor_db.select(query, [self.CONFIG.ID])
            ap = activity_processor.ActivityProcessor(server=self)
            for item in result:
                ap.delete_session(session_key=item['session_key'])
                activity_handler.delete_metadata_cache(session_key=item['session_key'], server=self)
            monitor_db.action('DELETE FROM sessions WHERE server_id = ?', [self.CONFIG.ID])
            return True

        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_sessions: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return False

    def delete_all_history(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli Servers :: %s: Deleting all history from database." % self.CONFIG.PMS_NAME)
            monitor_db.action('DELETE FROM '
                              'session_history_media_info '
                              'WHERE server_id = ?', [self.CONFIG.ID])
            monitor_db.action('DELETE FROM '
                              'session_history_metadata '
                              'WHERE server_id = ?', [self.CONFIG.ID])
            monitor_db.action('DELETE FROM '
                              'session_history '
                              'WHERE server_id = ?', [self.CONFIG.ID])
            monitor_db.action('DELETE FROM '
                              'recently_added '
                              'WHERE server_id = ?', [self.CONFIG.ID])
            monitor_db.action('DELETE FROM '
                              'themoviedb_lookup '
                              'WHERE server_id = ?', [self.CONFIG.ID])
            monitor_db.action('DELETE FROM '
                              'tvmaze_lookup '
                              'WHERE server_id = ?', [self.CONFIG.ID])
            return True

        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_history: %s."
                        % (self.CONFIG.PMS_NAME, e))
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
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_users: %s."
                        % (self.CONFIG.PMS_NAME, e))
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
            logger.warn(u"Tautulli Servers :: %s: Unable to execute database query for delete_all_libraries: %s."
                        % (self.CONFIG.PMS_NAME, e))
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

    def get_sessions(self, output_format=''):
        """
        Return current sessions.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/status/sessions'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_sessions_terminate(self, session_id='', reason='', output_format=''):
        """
        Return current sessions.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/status/sessions/terminate?sessionId=%s&reason=%s' % (session_id, reason)
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_metadata(self, rating_key='', output_format=''):
        """
        Return metadata for request item.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/metadata/' + rating_key
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_metadata_children(self, rating_key='', output_format=''):
        """
        Return metadata for children of the request item.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/metadata/' + rating_key + '/children'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_metadata_grandchildren(self, rating_key='', output_format=''):
        """
        Return metadata for graandchildren of the request item.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/metadata/' + rating_key + '/grandchildren'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_recently_added(self, start='0', count='0', output_format=''):
        """
        Return list of recently added items.

        Parameters required:    count { number of results to return }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/recentlyAdded?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s' % (start, count)
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_library_recently_added(self, section_id='', start='0', count='0', output_format=''):
        """
        Return list of recently added items.

        Parameters required:    count { number of results to return }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/sections/%s/recentlyAdded?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s' % (
        section_id, start, count)
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_children_list_related(self, rating_key='', output_format=''):
        """
        Return list of related children in requested collection item.

        Parameters required:    rating_key { ratingKey of parent }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/hubs/metadata/' + rating_key + '/related'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_childrens_list(self, rating_key='', output_format=''):
        """
        Return list of children in requested library item.

        Parameters required:    rating_key { ratingKey of parent }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/metadata/' + rating_key + '/allLeaves'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_server_list(self, output_format=''):
        """
        Return list of local servers.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/servers'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_server_prefs(self, output_format=''):
        """
        Return the local servers preferences.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/:/prefs'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_local_server_identity(self, output_format=''):
        """
        Return the local server identity.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/identity'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_libraries_list(self, output_format=''):
        """
        Return list of libraries on server.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/sections'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_library_list(self, section_id='', list_type='all', count='0', sort_type='', label_key='', output_format=''):
        """
        Return list of items in library on server.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        count = '&X-Plex-Container-Size=' + count if count else ''
        label_key = '&label=' + label_key if label_key else ''

        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/sections/' + section_id + '/' + list_type + '?X-Plex-Container-Start=0' + count + sort_type + label_key
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_library_labels(self, section_id='', output_format=''):
        """
        Return list of labels for a library on server.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/library/sections/' + section_id + '/label'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_sync_item(self, sync_id='', output_format=''):
        """
        Return sync item details.

        Parameters required:    sync_id { unique sync id for item }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/sync/items/' + sync_id
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_sync_transcode_queue(self, output_format=''):
        """
        Return sync transcode queue.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/sync/transcodeQueue'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_search(self, query='', limit='', output_format=''):
        """
        Return search results.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/hubs/search?query=' + urllib.parse.quote(
            query.encode('utf8')) + '&limit=' + limit + '&includeCollections=1'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_account(self, output_format=''):
        """
        Return account details.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/myplex/account'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def put_refresh_reachability(self):
        """
        Refresh Plex remote access port mapping.

        Optional parameters:    None

        Output: None
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/myplex/refreshReachability'
        request = request_handler.make_request(uri=uri,
                                               request_type='PUT',
                                               output_format='raw')

        return request

    def put_updater(self, output_format=''):
        """
        Refresh updater status.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/updater/check?download=0'
        request = request_handler.make_request(uri=uri,
                                               request_type='PUT',
                                               output_format=output_format)

        return request

    def get_updater(self, output_format=''):
        """
        Return updater status.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/updater/status'
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_hub_recently_added(self, start='0', count='0', media_type='', other_video=False, output_format=''):
        """
        Return Plex hub recently added.

        Parameters required:    start { item number to start from }
                                count { number of results to return }
                                media_type { str }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        personal = '&personal=1' if other_video else ''
        request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
        uri = '/hubs/home/recentlyAdded?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s&type=%s%s' \
              % (start, count, media_type, personal)
        request = request_handler.make_request(uri=uri,
                                               request_type='GET',
                                               output_format=output_format)

        return request

    def get_recently_added_details(self, start='0', count='0', media_type='', section_id=''):
        """
        Return processed and validated list of recently added items.

        Parameters required:    count { number of results to return }

        Output: array
        """
        if media_type in ('movie', 'show', 'artist', 'other_video'):
            other_video = False
            if media_type == 'movie':
                media_type = '1'
            elif media_type == 'show':
                media_type = '2'
            elif media_type == 'artist':
                media_type = '8'
            elif media_type == 'other_video':
                media_type = '1'
                other_video = True
            recent = self.get_hub_recently_added(start, count, media_type, other_video, output_format='xml')
        elif section_id:
            recent = self.get_library_recently_added(section_id, start, count, output_format='xml')
        else:
            recent = self.get_recently_added(start, count, output_format='xml')

        try:
            xml_head = recent.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_recently_added: %s." % (
            self.CONFIG.PMS_NAME, e))
            return []

        recents_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    output = {'recently_added': []}
                    return output

            recents_main = []
            if a.getElementsByTagName('Directory'):
                recents_main += a.getElementsByTagName('Directory')
            if a.getElementsByTagName('Video'):
                recents_main += a.getElementsByTagName('Video')

            for m in recents_main:
                directors = []
                writers = []
                actors = []
                genres = []
                labels = []
                collections = []

                if m.getElementsByTagName('Director'):
                    for director in m.getElementsByTagName('Director'):
                        directors.append(helpers.get_xml_attr(director, 'tag'))

                if m.getElementsByTagName('Writer'):
                    for writer in m.getElementsByTagName('Writer'):
                        writers.append(helpers.get_xml_attr(writer, 'tag'))

                if m.getElementsByTagName('Role'):
                    for actor in m.getElementsByTagName('Role'):
                        actors.append(helpers.get_xml_attr(actor, 'tag'))

                if m.getElementsByTagName('Genre'):
                    for genre in m.getElementsByTagName('Genre'):
                        genres.append(helpers.get_xml_attr(genre, 'tag'))

                if m.getElementsByTagName('Label'):
                    for label in m.getElementsByTagName('Label'):
                        labels.append(helpers.get_xml_attr(label, 'tag'))

                if m.getElementsByTagName('Collection'):
                    for collection in m.getElementsByTagName('Collection'):
                        collections.append(helpers.get_xml_attr(collection, 'tag'))

                recent_item = {'media_type': helpers.get_xml_attr(m, 'type'),
                               'server_id': self.CONFIG.ID,
                               'server_name': self.CONFIG.PMS_NAME,
                               'pms_identifier': self.CONFIG.PMS_IDENTIFIER,
                               'pms_web_url': self.CONFIG.PMS_WEB_URL,
                               'section_id': helpers.get_xml_attr(m, 'librarySectionID'),
                               'library_id': libraries.get_section_index(server_id=self.CONFIG.ID,
                                                                         section_id=helpers.get_xml_attr(m,
                                                                                                         'librarySectionID')),
                               'library_name': helpers.get_xml_attr(m, 'librarySectionTitle'),
                               'rating_key': helpers.get_xml_attr(m, 'ratingKey'),
                               'parent_rating_key': helpers.get_xml_attr(m, 'parentRatingKey'),
                               'grandparent_rating_key': helpers.get_xml_attr(m, 'grandparentRatingKey'),
                               'title': helpers.get_xml_attr(m, 'title'),
                               'parent_title': helpers.get_xml_attr(m, 'parentTitle'),
                               'grandparent_title': helpers.get_xml_attr(m, 'grandparentTitle'),
                               'original_title': helpers.get_xml_attr(m, 'originalTitle'),
                               'sort_title': helpers.get_xml_attr(m, 'titleSort'),
                               'media_index': helpers.get_xml_attr(m, 'index'),
                               'parent_media_index': helpers.get_xml_attr(m, 'parentIndex'),
                               'studio': helpers.get_xml_attr(m, 'studio'),
                               'content_rating': helpers.get_xml_attr(m, 'contentRating'),
                               'summary': helpers.get_xml_attr(m, 'summary'),
                               'tagline': helpers.get_xml_attr(m, 'tagline'),
                               'rating': helpers.get_xml_attr(m, 'rating'),
                               'rating_image': helpers.get_xml_attr(m, 'ratingImage'),
                               'audience_rating': helpers.get_xml_attr(m, 'audienceRating'),
                               'audience_rating_image': helpers.get_xml_attr(m, 'audienceRatingImage'),
                               'user_rating': helpers.get_xml_attr(m, 'userRating'),
                               'duration': helpers.get_xml_attr(m, 'duration'),
                               'year': helpers.get_xml_attr(m, 'year'),
                               'thumb': helpers.get_xml_attr(m, 'thumb'),
                               'parent_thumb': helpers.get_xml_attr(m, 'parentThumb'),
                               'grandparent_thumb': helpers.get_xml_attr(m, 'grandparentThumb'),
                               'art': helpers.get_xml_attr(m, 'art'),
                               'banner': helpers.get_xml_attr(m, 'banner'),
                               'originally_available_at': helpers.get_xml_attr(m, 'originallyAvailableAt'),
                               'added_at': helpers.get_xml_attr(m, 'addedAt'),
                               'updated_at': helpers.get_xml_attr(m, 'updatedAt'),
                               'last_viewed_at': helpers.get_xml_attr(m, 'lastViewedAt'),
                               'guid': helpers.get_xml_attr(m, 'guid'),
                               'directors': directors,
                               'writers': writers,
                               'actors': actors,
                               'genres': genres,
                               'labels': labels,
                               'collections': collections,
                               'full_title': helpers.get_xml_attr(m, 'title'),
                               'child_count': helpers.get_xml_attr(m, 'childCount')
                               }

                recents_list.append(recent_item)

        output = {'recently_added': sorted(recents_list, key=lambda k: k['added_at'], reverse=True)}

        return output

    def get_metadata_details(self, rating_key='', sync_id='', cache_key=None, media_info=True):
        """
        Return processed and validated metadata list for requested item.

        Parameters required:    rating_key { Plex ratingKey }

        Output: array
        """
        metadata = {}

        if cache_key:
            in_file_folder = os.path.join(plexpy.CONFIG.CACHE_DIR, 'session_metadata')
            in_file_path = os.path.join(in_file_folder,
                                        'metadata-sessionKey-%s-%s.json' % (self.CONFIG.ID, cache_key))

            if not os.path.exists(in_file_folder):
                os.mkdir(in_file_folder)

            try:
                with open(in_file_path, 'r') as inFile:
                    metadata = json.load(inFile)
            except (IOError, ValueError) as e:
                pass

            if metadata:
                _cache_time = metadata.pop('_cache_time', 0)
                # Return cached metadata if less than METADATA_CACHE_SECONDS ago
                if int(time.time()) - _cache_time <= plexpy.CONFIG.METADATA_CACHE_SECONDS:
                    return metadata

        if rating_key:
            metadata_xml = self.get_metadata(str(rating_key), output_format='xml')
        elif sync_id:
            metadata_xml = self.get_sync_item(str(sync_id), output_format='xml')
        else:
            return metadata

        try:
            xml_head = metadata_xml.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_metadata_details: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return {}

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return metadata

            if a.getElementsByTagName('Directory'):
                metadata_main_list = a.getElementsByTagName('Directory')
            elif a.getElementsByTagName('Video'):
                metadata_main_list = a.getElementsByTagName('Video')
            elif a.getElementsByTagName('Track'):
                metadata_main_list = a.getElementsByTagName('Track')
            elif a.getElementsByTagName('Photo'):
                metadata_main_list = a.getElementsByTagName('Photo')
            else:
                logger.debug(u"Tautulli Servers :: %s: Metadata failed" % self.CONFIG.PMS_NAME)
                return {}

            if sync_id and len(metadata_main_list) > 1:
                for metadata_main in metadata_main_list:
                    if helpers.get_xml_attr(metadata_main, 'ratingKey') == rating_key:
                        break
            else:
                metadata_main = metadata_main_list[0]

            metadata_type = helpers.get_xml_attr(metadata_main, 'type')
            if metadata_main.nodeName == 'Directory' and metadata_type == 'photo':
                metadata_type = 'photo_album'

            section_id = helpers.get_xml_attr(a, 'librarySectionID')
            library_name = helpers.get_xml_attr(a, 'librarySectionTitle')
            library_id = ''

            if section_id.isdigit():
                for x in range(2):
                    library_id = libraries.get_section_index(server_id=self.CONFIG.ID, section_id=section_id)
                    if library_id:
                        break
                    else:
                        self.refresh_libraries()

        directors = []
        writers = []
        actors = []
        genres = []
        labels = []
        collections = []

        if metadata_main.getElementsByTagName('Director'):
            for director in metadata_main.getElementsByTagName('Director'):
                directors.append(helpers.get_xml_attr(director, 'tag'))

        if metadata_main.getElementsByTagName('Writer'):
            for writer in metadata_main.getElementsByTagName('Writer'):
                writers.append(helpers.get_xml_attr(writer, 'tag'))

        if metadata_main.getElementsByTagName('Role'):
            for actor in metadata_main.getElementsByTagName('Role'):
                actors.append(helpers.get_xml_attr(actor, 'tag'))

        if metadata_main.getElementsByTagName('Genre'):
            for genre in metadata_main.getElementsByTagName('Genre'):
                genres.append(helpers.get_xml_attr(genre, 'tag'))

        if metadata_main.getElementsByTagName('Label'):
            for label in metadata_main.getElementsByTagName('Label'):
                labels.append(helpers.get_xml_attr(label, 'tag'))

        if metadata_main.getElementsByTagName('Collection'):
            for collection in metadata_main.getElementsByTagName('Collection'):
                collections.append(helpers.get_xml_attr(collection, 'tag'))

        if metadata_type == 'movie':
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'show':
            # Workaround for for duration sometimes reported in minutes for a show
            duration = helpers.get_xml_attr(metadata_main, 'duration')
            if duration.isdigit() and int(duration) < 1000:
                duration = str(int(duration) * 60 * 1000)

            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': duration,
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'season':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            show_details = self.get_metadata_details(parent_rating_key)
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': show_details['studio'],
                        'content_rating': show_details['content_rating'],
                        'summary': show_details['summary'],
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': show_details['duration'],
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': show_details['banner'],
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': show_details['directors'],
                        'writers': show_details['writers'],
                        'actors': show_details['actors'],
                        'genres': show_details['genres'],
                        'labels': show_details['labels'],
                        'collections': show_details['collections'],
                        'full_title': u'{} - {}'.format(helpers.get_xml_attr(metadata_main, 'parentTitle'),
                                                        helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'episode':
            grandparent_rating_key = helpers.get_xml_attr(metadata_main, 'grandparentRatingKey')
            show_details = self.get_metadata_details(grandparent_rating_key)

            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            parent_media_index = helpers.get_xml_attr(metadata_main, 'parentIndex')
            parent_thumb = helpers.get_xml_attr(metadata_main, 'parentThumb')

            if not parent_rating_key:
                # Try getting the parent_rating_key from the parent_thumb
                if parent_thumb.startswith('/library/metadata/'):
                    parent_rating_key = parent_thumb.split('/')[3]

                # Try getting the parent_rating_key from the grandparent's children
                if not parent_rating_key:
                    children_list = self.get_item_children(grandparent_rating_key)
                    parent_rating_key = next((c['rating_key'] for c in children_list['children_list']
                                              if c['media_index'] == parent_media_index), '')

            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': parent_rating_key,
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': 'Season %s' % helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': parent_media_index,
                        'studio': show_details['studio'],
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': parent_thumb,
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': show_details['banner'],
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': show_details['actors'],
                        'genres': show_details['genres'],
                        'labels': show_details['labels'],
                        'collections': show_details['collections'],
                        'full_title': u'{} - {}'.format(helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                                                        helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'artist':
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'album':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            artist_details = self.get_metadata_details(parent_rating_key)
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary') or artist_details['summary'],
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': artist_details['banner'],
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': u'{} - {}'.format(helpers.get_xml_attr(metadata_main, 'parentTitle'),
                                                        helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'track':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            album_details = self.get_metadata_details(parent_rating_key)
            track_artist = helpers.get_xml_attr(metadata_main, 'originalTitle') or \
                           helpers.get_xml_attr(metadata_main, 'grandparentTitle')
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': album_details['year'],
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': album_details['banner'],
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': album_details['genres'],
                        'labels': album_details['labels'],
                        'collections': album_details['collections'],
                        'full_title': u'{} - {}'.format(helpers.get_xml_attr(metadata_main, 'title'),
                                                        track_artist),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'photo_album':
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'photo':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            photo_album_details = self.get_metadata_details(parent_rating_key)
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': photo_album_details.get('banner', ''),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': photo_album_details.get('genres', ''),
                        'labels': photo_album_details.get('labels', ''),
                        'collections': photo_album_details.get('collections', ''),
                        'full_title': u'{} - {}'.format(
                            helpers.get_xml_attr(metadata_main, 'parentTitle') or library_name,
                            helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'collection':
            metadata = {'media_type': metadata_type,
                        'sub_media_type': helpers.get_xml_attr(metadata_main, 'subtype'),
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'min_year': helpers.get_xml_attr(metadata_main, 'minYear'),
                        'max_year': helpers.get_xml_attr(metadata_main, 'maxYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb').split('?')[0],
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'child_count': helpers.get_xml_attr(metadata_main, 'childCount'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.get_xml_attr(metadata_main, 'leafCount')
                        }

        elif metadata_type == 'clip':
            metadata = {'media_type': metadata_type,
                        'server_id': self.CONFIG.ID,
                        'server_name': self.CONFIG.PMS_NAME,
                        'section_id': section_id,
                        'library_id': library_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'extra_type': helpers.get_xml_attr(metadata_main, 'extraType'),
                        'sub_type': helpers.get_xml_attr(metadata_main, 'subtype')
                        }

        else:
            return metadata

        if metadata and media_info:
            medias = []
            media_items = metadata_main.getElementsByTagName('Media')
            for media in media_items:

                parts = []
                part_items = media.getElementsByTagName('Part')
                for part in part_items:

                    streams = []
                    stream_items = part.getElementsByTagName('Stream')
                    for stream in stream_items:
                        if helpers.get_xml_attr(stream, 'streamType') == '1':
                            streams.append({'id': helpers.get_xml_attr(stream, 'id'),
                                            'type': helpers.get_xml_attr(stream, 'streamType'),
                                            'video_codec': helpers.get_xml_attr(stream, 'codec'),
                                            'video_codec_level': helpers.get_xml_attr(stream, 'level'),
                                            'video_bitrate': helpers.get_xml_attr(stream, 'bitrate'),
                                            'video_bit_depth': helpers.get_xml_attr(stream, 'bitDepth'),
                                            'video_frame_rate': helpers.get_xml_attr(stream, 'frameRate'),
                                            'video_ref_frames': helpers.get_xml_attr(stream, 'refFrames'),
                                            'video_height': helpers.get_xml_attr(stream, 'height'),
                                            'video_width': helpers.get_xml_attr(stream, 'width'),
                                            'video_language': helpers.get_xml_attr(stream, 'language'),
                                            'video_language_code': helpers.get_xml_attr(stream, 'languageCode'),
                                            'video_profile': helpers.get_xml_attr(stream, 'profile'),
                                            'selected': int(helpers.get_xml_attr(stream, 'selected') == '1')
                                            })

                        elif helpers.get_xml_attr(stream, 'streamType') == '2':
                            streams.append({'id': helpers.get_xml_attr(stream, 'id'),
                                            'type': helpers.get_xml_attr(stream, 'streamType'),
                                            'audio_codec': helpers.get_xml_attr(stream, 'codec'),
                                            'audio_bitrate': helpers.get_xml_attr(stream, 'bitrate'),
                                            'audio_bitrate_mode': helpers.get_xml_attr(stream, 'bitrateMode'),
                                            'audio_channels': helpers.get_xml_attr(stream, 'channels'),
                                            'audio_channel_layout': helpers.get_xml_attr(stream, 'audioChannelLayout'),
                                            'audio_sample_rate': helpers.get_xml_attr(stream, 'samplingRate'),
                                            'audio_language': helpers.get_xml_attr(stream, 'language'),
                                            'audio_language_code': helpers.get_xml_attr(stream, 'languageCode'),
                                            'audio_profile': helpers.get_xml_attr(stream, 'profile'),
                                            'selected': int(helpers.get_xml_attr(stream, 'selected') == '1')
                                            })

                        elif helpers.get_xml_attr(stream, 'streamType') == '3':
                            streams.append({'id': helpers.get_xml_attr(stream, 'id'),
                                            'type': helpers.get_xml_attr(stream, 'streamType'),
                                            'subtitle_codec': helpers.get_xml_attr(stream, 'codec'),
                                            'subtitle_container': helpers.get_xml_attr(stream, 'container'),
                                            'subtitle_format': helpers.get_xml_attr(stream, 'format'),
                                            'subtitle_forced': int(helpers.get_xml_attr(stream, 'forced') == '1'),
                                            'subtitle_location': 'external' if helpers.get_xml_attr(stream,
                                                                                                    'key') else 'embedded',
                                            'subtitle_language': helpers.get_xml_attr(stream, 'language'),
                                            'subtitle_language_code': helpers.get_xml_attr(stream, 'languageCode'),
                                            'selected': int(helpers.get_xml_attr(stream, 'selected') == '1')
                                            })

                    parts.append({'id': helpers.get_xml_attr(part, 'id'),
                                  'file': helpers.get_xml_attr(part, 'file'),
                                  'file_size': helpers.get_xml_attr(part, 'size'),
                                  'indexes': int(helpers.get_xml_attr(part, 'indexes') == 'sd'),
                                  'streams': streams,
                                  'selected': int(helpers.get_xml_attr(part, 'selected') == '1')
                                  })

                audio_channels = helpers.get_xml_attr(media, 'audioChannels')

                medias.append({'id': helpers.get_xml_attr(media, 'id'),
                               'container': helpers.get_xml_attr(media, 'container'),
                               'bitrate': helpers.get_xml_attr(media, 'bitrate'),
                               'height': helpers.get_xml_attr(media, 'height'),
                               'width': helpers.get_xml_attr(media, 'width'),
                               'aspect_ratio': helpers.get_xml_attr(media, 'aspectRatio'),
                               'video_codec': helpers.get_xml_attr(media, 'videoCodec'),
                               'video_resolution': helpers.get_xml_attr(media, 'videoResolution'),
                               'video_framerate': helpers.get_xml_attr(media, 'videoFrameRate'),
                               'video_profile': helpers.get_xml_attr(media, 'videoProfile'),
                               'audio_codec': helpers.get_xml_attr(media, 'audioCodec'),
                               'audio_channels': audio_channels,
                               'audio_channel_layout': common.AUDIO_CHANNELS.get(audio_channels, audio_channels),
                               'audio_profile': helpers.get_xml_attr(media, 'audioProfile'),
                               'optimized_version': int(helpers.get_xml_attr(media, 'proxyType') == '42'),
                               'parts': parts
                               })

            metadata['media_info'] = medias

        if metadata:
            if cache_key:
                metadata['_cache_time'] = int(time.time())

                out_file_folder = os.path.join(plexpy.CONFIG.CACHE_DIR, 'session_metadata')
                out_file_path = os.path.join(out_file_folder,
                                             'metadata-sessionKey-%s-%s.json' % (self.CONFIG.ID, cache_key))

                if not os.path.exists(out_file_folder):
                    os.mkdir(out_file_folder)

                try:
                    with open(out_file_path, 'w') as outFile:
                        json.dump(metadata, outFile)
                except (IOError, ValueError) as e:
                    logger.error(
                        u"Tautulli Servers :: %s: Unable to create cache file for metadata (sessionKey %s): %s"
                        % (self.CONFIG.PMS_NAME, cache_key, e))

            return metadata
        else:
            return metadata

    def get_metadata_children_details(self, rating_key='', get_children=False):
        """
        Return processed and validated metadata list for all children of requested item.

        Parameters required:    rating_key { Plex ratingKey }

        Output: array
        """
        metadata = self.get_metadata_children(str(rating_key), output_format='xml')

        try:
            xml_head = metadata.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_metadata_children: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        metadata_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return metadata_list

            if a.getElementsByTagName('Video'):
                metadata_main = a.getElementsByTagName('Video')
                for item in metadata_main:
                    child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                    metadata = self.get_metadata_details(str(child_rating_key))
                    if metadata:
                        metadata_list.append(metadata)

            elif a.getElementsByTagName('Track'):
                metadata_main = a.getElementsByTagName('Track')
                for item in metadata_main:
                    child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                    metadata = self.get_metadata_details(str(child_rating_key))
                    if metadata:
                        metadata_list.append(metadata)

            elif get_children and a.getElementsByTagName('Directory'):
                dir_main = a.getElementsByTagName('Directory')
                metadata_main = [d for d in dir_main if helpers.get_xml_attr(d, 'ratingKey')]
                for item in metadata_main:
                    child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                    metadata = self.get_metadata_children_details(str(child_rating_key), get_children)
                    if metadata:
                        metadata_list.extend(metadata)

        return metadata_list

    def get_library_metadata_details(self, section_id=''):
        """
        Return processed and validated metadata list for requested library.

        Parameters required:    section_id { Plex library key }

        Output: array
        """
        libraries_data = self.get_libraries_list(output_format='xml')

        try:
            xml_head = libraries_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_library_metadata_details: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        metadata_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    metadata_list = {'metadata': None}
                    return metadata_list

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
                for result in result_data:
                    key = helpers.get_xml_attr(result, 'key')
                    if key == section_id:
                        metadata = {'media_type': 'library',
                                    'section_id': helpers.get_xml_attr(result, 'key'),
                                    'library': helpers.get_xml_attr(result, 'type'),
                                    'title': helpers.get_xml_attr(result, 'title'),
                                    'art': helpers.get_xml_attr(result, 'art'),
                                    'thumb': helpers.get_xml_attr(result, 'thumb')
                                    }
                        if metadata['library'] == 'movie':
                            metadata['section_type'] = 'movie'
                        elif metadata['library'] == 'show':
                            metadata['section_type'] = 'episode'
                        elif metadata['library'] == 'artist':
                            metadata['section_type'] = 'track'

            metadata_list = {'metadata': metadata}

        return metadata_list

    def get_current_activity(self):
        """
        Return processed and validated session list.

        Output: array
        """
        session_data = self.get_sessions(output_format='xml')

        if session_data:
            try:
                xml_head = session_data.getElementsByTagName('MediaContainer')
            except Exception as e:
                logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_current_activity: %s."
                            % (self.CONFIG.PMS_NAME, e))
                return []

            session_list = []

            for a in xml_head:
                if a.getAttribute('size'):
                    if a.getAttribute('size') == '0':
                        session_list = {'stream_count': '0',
                                        'sessions': []
                                        }
                        return session_list

                if a.getElementsByTagName('Track'):
                    session_data = a.getElementsByTagName('Track')
                    for session_ in session_data:
                        session_output = self.get_session_each(session_)
                        session_list.append(session_output)
                if a.getElementsByTagName('Video'):
                    session_data = a.getElementsByTagName('Video')
                    for session_ in session_data:
                        session_output = self.get_session_each(session_)
                        session_list.append(session_output)
                if a.getElementsByTagName('Photo'):
                    session_data = a.getElementsByTagName('Photo')
                    for session_ in session_data:
                        session_output = self.get_session_each(session_)
                        session_list.append(session_output)

            session_list = sorted(session_list, key=lambda k: k['session_key'])

            output = {'stream_count': helpers.get_xml_attr(xml_head[0], 'size'),
                      'sessions': session.mask_session_info(session_list)
                      }
        else:
            output = {}

        return output

    def get_session_each(self, session=None):
        """
        Return selected data from current sessions.
        This function processes and validates session data

        Parameters required:    session { the session dictionary }
        Output: dict
        """

        # Get the source media type
        media_type = helpers.get_xml_attr(session, 'type')
        rating_key = helpers.get_xml_attr(session, 'ratingKey')
        session_key = helpers.get_xml_attr(session, 'sessionKey')

        # Get the user details
        user_info = session.getElementsByTagName('User')[0]
        user_details = users.Users().get_details(user=helpers.get_xml_attr(user_info, 'title'))

        # Get the player details
        player_info = session.getElementsByTagName('Player')[0]

        # Override platform names
        platform = helpers.get_xml_attr(player_info, 'platform')
        platform = common.PLATFORM_NAME_OVERRIDES.get(platform, platform)
        if not platform and helpers.get_xml_attr(player_info, 'product') == 'DLNA':
            platform = 'DLNA'

        platform_name = next((v for k, v in common.PLATFORM_NAMES.items() if k in platform.lower()), 'default')

        player_details = {'ip_address': helpers.get_xml_attr(player_info, 'address').split('::ffff:')[-1],
                          'ip_address_public':
                              helpers.get_xml_attr(player_info, 'remotePublicAddress').split('::ffff:')[-1],
                          'device': helpers.get_xml_attr(player_info, 'device'),
                          'server_name': self.CONFIG.PMS_NAME,
                          'platform': platform,
                          'platform_name': platform_name,
                          'platform_version': helpers.get_xml_attr(player_info, 'platformVersion'),
                          'product': helpers.get_xml_attr(player_info, 'product'),
                          'product_version': helpers.get_xml_attr(player_info, 'version'),
                          'profile': helpers.get_xml_attr(player_info, 'profile'),
                          'player': helpers.get_xml_attr(player_info, 'title') or helpers.get_xml_attr(player_info,
                                                                                                       'product'),
                          'machine_id': helpers.get_xml_attr(player_info, 'machineIdentifier'),
                          'state': helpers.get_xml_attr(player_info, 'state'),
                          'local': helpers.get_xml_attr(player_info, 'local')
                          }

        # Get the session details
        if session.getElementsByTagName('Session'):
            session_info = session.getElementsByTagName('Session')[0]

            session_details = {'session_id': helpers.get_xml_attr(session_info, 'id'),
                               'bandwidth': helpers.get_xml_attr(session_info, 'bandwidth'),
                               'location': helpers.get_xml_attr(session_info, 'location')
                               }
        else:
            session_details = {'session_id': '',
                               'bandwidth': '',
                               'location': 'wan' if player_details['local'] == '0' else 'lan'
                               }

        # Check if using Plex Relay
        session_details['relay'] = int(session_details['location'] != 'lan'
                                       and player_details['ip_address_public'] == '127.0.0.1')

        # Get the transcode details
        if session.getElementsByTagName('TranscodeSession'):
            transcode_session = True

            transcode_info = session.getElementsByTagName('TranscodeSession')[0]

            transcode_progress = helpers.get_xml_attr(transcode_info, 'progress')
            transcode_speed = helpers.get_xml_attr(transcode_info, 'speed')

            transcode_details = {'transcode_key': helpers.get_xml_attr(transcode_info, 'key'),
                                 'transcode_throttled': int(helpers.get_xml_attr(transcode_info, 'throttled') == '1'),
                                 'transcode_progress': int(round(helpers.cast_to_float(transcode_progress), 0)),
                                 'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                                 'transcode_audio_channels': helpers.get_xml_attr(transcode_info, 'audioChannels'),
                                 'transcode_audio_codec': helpers.get_xml_attr(transcode_info, 'audioCodec'),
                                 'transcode_video_codec': helpers.get_xml_attr(transcode_info, 'videoCodec'),
                                 'transcode_width': helpers.get_xml_attr(transcode_info, 'width'),
                                 # Blank but keep for backwards compatibility
                                 'transcode_height': helpers.get_xml_attr(transcode_info, 'height'),
                                 # Blank but keep backwards compatibility
                                 'transcode_container': helpers.get_xml_attr(transcode_info, 'container'),
                                 'transcode_protocol': helpers.get_xml_attr(transcode_info, 'protocol'),
                                 'transcode_hw_requested': int(
                                     helpers.get_xml_attr(transcode_info, 'transcodeHwRequested') == '1'),
                                 'transcode_hw_decode': helpers.get_xml_attr(transcode_info, 'transcodeHwDecoding'),
                                 'transcode_hw_decode_title': helpers.get_xml_attr(transcode_info,
                                                                                   'transcodeHwDecodingTitle'),
                                 'transcode_hw_encode': helpers.get_xml_attr(transcode_info, 'transcodeHwEncoding'),
                                 'transcode_hw_encode_title': helpers.get_xml_attr(transcode_info,
                                                                                   'transcodeHwEncodingTitle'),
                                 'transcode_hw_full_pipeline': int(
                                     helpers.get_xml_attr(transcode_info, 'transcodeHwFullPipeline') == '1'),
                                 'audio_decision': helpers.get_xml_attr(transcode_info, 'audioDecision'),
                                 'video_decision': helpers.get_xml_attr(transcode_info, 'videoDecision'),
                                 'subtitle_decision': helpers.get_xml_attr(transcode_info, 'subtitleDecision'),
                                 'throttled': '1' if helpers.get_xml_attr(transcode_info, 'throttled') == '1' else '0'
                                 # Keep for backwards compatibility
                                 }
        else:
            transcode_session = False

            transcode_details = {'transcode_key': '',
                                 'transcode_throttled': 0,
                                 'transcode_progress': 0,
                                 'transcode_speed': '',
                                 'transcode_audio_channels': '',
                                 'transcode_audio_codec': '',
                                 'transcode_video_codec': '',
                                 'transcode_width': '',
                                 'transcode_height': '',
                                 'transcode_container': '',
                                 'transcode_protocol': '',
                                 'transcode_hw_requested': 0,
                                 'transcode_hw_decode': '',
                                 'transcode_hw_decode_title': '',
                                 'transcode_hw_encode': '',
                                 'transcode_hw_encode_title': '',
                                 'transcode_hw_full_pipeline': 0,
                                 'audio_decision': 'direct play',
                                 'video_decision': 'direct play',
                                 'subtitle_decision': '',
                                 'throttled': '0'  # Keep for backwards compatibility
                                 }

        # Check HW decoding/encoding
        transcode_details['transcode_hw_decoding'] = int(
            transcode_details['transcode_hw_decode'].lower() in common.HW_DECODERS)
        transcode_details['transcode_hw_encoding'] = int(
            transcode_details['transcode_hw_encode'].lower() in common.HW_ENCODERS)

        # Determine if a synced version is being played
        sync_id = None
        if media_type not in ('photo', 'clip') \
                and not session.getElementsByTagName('Session') \
                and not session.getElementsByTagName('TranscodeSession') \
                and helpers.get_xml_attr(session, 'ratingKey').isdigit() \
                and self.PLEXTV.plexpass:
            parent_rating_key = helpers.get_xml_attr(session, 'parentRatingKey')
            grandparent_rating_key = helpers.get_xml_attr(session, 'grandparentRatingKey')

            synced_items = self.PLEXTV.get_synced_items(client_id_filter=player_details['machine_id'],
                                                        rating_key_filter=[rating_key, parent_rating_key,
                                                                           grandparent_rating_key])
            if synced_items:
                synced_item_details = synced_items[0]
                sync_id = synced_item_details['sync_id']
                synced_xml = self.get_sync_item(sync_id=sync_id, output_format='xml')
                synced_xml_head = synced_xml.getElementsByTagName('MediaContainer')
                if synced_xml_head[0].getElementsByTagName('Track'):
                    synced_xml_items = synced_xml_head[0].getElementsByTagName('Track')
                elif synced_xml_head[0].getElementsByTagName('Video'):
                    synced_xml_items = synced_xml_head[0].getElementsByTagName('Video')

                for synced_session_data in synced_xml_items:
                    if helpers.get_xml_attr(synced_session_data, 'ratingKey') == rating_key:
                        break

        # Figure out which version is being played
        if sync_id:
            media_info_all = synced_session_data.getElementsByTagName('Media')
        else:
            media_info_all = session.getElementsByTagName('Media')
        stream_media_info = next((m for m in media_info_all if helpers.get_xml_attr(m, 'selected') == '1'),
                                 media_info_all[0])
        part_info_all = stream_media_info.getElementsByTagName('Part')
        stream_media_parts_info = next((p for p in part_info_all if helpers.get_xml_attr(p, 'selected') == '1'),
                                       part_info_all[0])

        # Get the stream details
        video_stream_info = audio_stream_info = subtitle_stream_info = None
        for stream in stream_media_parts_info.getElementsByTagName('Stream'):
            if helpers.get_xml_attr(stream, 'streamType') == '1':
                video_stream_info = stream

            elif helpers.get_xml_attr(stream, 'streamType') == '2':
                audio_stream_info = stream

            elif helpers.get_xml_attr(stream, 'streamType') == '3':
                subtitle_stream_info = stream

        video_id = audio_id = subtitle_id = None
        if video_stream_info:
            video_id = helpers.get_xml_attr(video_stream_info, 'id')
            video_details = {'stream_video_bitrate': helpers.get_xml_attr(video_stream_info, 'bitrate'),
                             'stream_video_bit_depth': helpers.get_xml_attr(video_stream_info, 'bitDepth'),
                             'stream_video_codec_level': helpers.get_xml_attr(video_stream_info, 'level'),
                             'stream_video_ref_frames': helpers.get_xml_attr(video_stream_info, 'refFrames'),
                             'stream_video_language': helpers.get_xml_attr(video_stream_info, 'language'),
                             'stream_video_language_code': helpers.get_xml_attr(video_stream_info, 'languageCode'),
                             'stream_video_decision': helpers.get_xml_attr(video_stream_info,
                                                                           'decision') or 'direct play'
                             }
        else:
            video_details = {'stream_video_bitrate': '',
                             'stream_video_bit_depth': '',
                             'stream_video_codec_level': '',
                             'stream_video_ref_frames': '',
                             'stream_video_language': '',
                             'stream_video_language_code': '',
                             'stream_video_decision': ''
                             }

        if audio_stream_info:
            audio_id = helpers.get_xml_attr(audio_stream_info, 'id')
            audio_details = {'stream_audio_bitrate': helpers.get_xml_attr(audio_stream_info, 'bitrate'),
                             'stream_audio_bitrate_mode': helpers.get_xml_attr(audio_stream_info, 'bitrateMode'),
                             'stream_audio_sample_rate': helpers.get_xml_attr(audio_stream_info, 'samplingRate'),
                             'stream_audio_channel_layout_': helpers.get_xml_attr(audio_stream_info,
                                                                                  'audioChannelLayout'),
                             'stream_audio_language': helpers.get_xml_attr(audio_stream_info, 'language'),
                             'stream_audio_language_code': helpers.get_xml_attr(audio_stream_info, 'languageCode'),
                             'stream_audio_decision': helpers.get_xml_attr(audio_stream_info,
                                                                           'decision') or 'direct play'
                             }
        else:
            audio_details = {'stream_audio_bitrate': '',
                             'stream_audio_bitrate_mode': '',
                             'stream_audio_sample_rate': '',
                             'stream_audio_channel_layout_': '',
                             'stream_audio_language': '',
                             'stream_audio_language_code': '',
                             'stream_audio_decision': ''
                             }

        if subtitle_stream_info:
            subtitle_id = helpers.get_xml_attr(subtitle_stream_info, 'id')
            subtitle_selected = helpers.get_xml_attr(subtitle_stream_info, 'selected')
            subtitle_details = {'stream_subtitle_codec': helpers.get_xml_attr(subtitle_stream_info, 'codec'),
                                'stream_subtitle_container': helpers.get_xml_attr(subtitle_stream_info, 'container'),
                                'stream_subtitle_format': helpers.get_xml_attr(subtitle_stream_info, 'format'),
                                'stream_subtitle_forced': int(
                                    helpers.get_xml_attr(subtitle_stream_info, 'forced') == '1'),
                                'stream_subtitle_location': helpers.get_xml_attr(subtitle_stream_info, 'location'),
                                'stream_subtitle_language': helpers.get_xml_attr(subtitle_stream_info, 'language'),
                                'stream_subtitle_language_code': helpers.get_xml_attr(subtitle_stream_info,
                                                                                      'languageCode'),
                                'stream_subtitle_decision': helpers.get_xml_attr(subtitle_stream_info, 'decision')
                                }
        else:
            subtitle_details = {'stream_subtitle_codec': '',
                                'stream_subtitle_container': '',
                                'stream_subtitle_format': '',
                                'stream_subtitle_forced': 0,
                                'stream_subtitle_location': '',
                                'stream_subtitle_language': '',
                                'stream_subtitle_language_code': '',
                                'stream_subtitle_decision': ''
                                }

        # Get the bif thumbnail
        indexes = helpers.get_xml_attr(stream_media_parts_info, 'indexes')
        view_offset = helpers.get_xml_attr(session, 'viewOffset')
        if indexes == 'sd':
            part_id = helpers.get_xml_attr(stream_media_parts_info, 'id')
            bif_thumb = '/library/parts/{part_id}/indexes/sd/{view_offset}'.format(part_id=part_id,
                                                                                   view_offset=view_offset)
        else:
            bif_thumb = ''

        stream_video_width = helpers.get_xml_attr(stream_media_info, 'width')
        if helpers.cast_to_int(stream_video_width) >= 3840:
            stream_video_resolution = '4k'
        else:
            stream_video_resolution = helpers.get_xml_attr(stream_media_info, 'videoResolution').rstrip('p')

        stream_audio_channels = helpers.get_xml_attr(stream_media_info, 'audioChannels')

        stream_details = {'stream_container': helpers.get_xml_attr(stream_media_info, 'container'),
                          'stream_bitrate': helpers.get_xml_attr(stream_media_info, 'bitrate'),
                          'stream_aspect_ratio': helpers.get_xml_attr(stream_media_info, 'aspectRatio'),
                          'stream_audio_codec': helpers.get_xml_attr(stream_media_info, 'audioCodec'),
                          'stream_audio_channels': stream_audio_channels,
                          'stream_audio_channel_layout': audio_details.get(
                              'stream_audio_channel_layout_') or common.AUDIO_CHANNELS.get(stream_audio_channels,
                                                                                           stream_audio_channels),
                          'stream_video_codec': helpers.get_xml_attr(stream_media_info, 'videoCodec'),
                          'stream_video_framerate': helpers.get_xml_attr(stream_media_info, 'videoFrameRate'),
                          'stream_video_resolution': stream_video_resolution,
                          'stream_video_height': helpers.get_xml_attr(stream_media_info, 'height'),
                          'stream_video_width': helpers.get_xml_attr(stream_media_info, 'width'),
                          'stream_duration': helpers.get_xml_attr(stream_media_info,
                                                                  'duration') or helpers.get_xml_attr(session,
                                                                                                      'duration'),
                          'stream_container_decision': 'direct play' if sync_id else helpers.get_xml_attr(
                              stream_media_parts_info, 'decision').replace('directplay', 'direct play'),
                          'optimized_version': int(helpers.get_xml_attr(stream_media_info, 'proxyType') == '42'),
                          'optimized_version_title': helpers.get_xml_attr(stream_media_info, 'title'),
                          'synced_version': 1 if sync_id else 0,
                          'live': int(helpers.get_xml_attr(session, 'live') == '1'),
                          'live_uuid': helpers.get_xml_attr(stream_media_info, 'uuid'),
                          'indexes': int(indexes == 'sd'),
                          'bif_thumb': bif_thumb,
                          'subtitles': 1 if subtitle_id and subtitle_selected else 0
                          }

        # Get the source media info
        source_media_details = source_media_part_details = \
            source_video_details = source_audio_details = source_subtitle_details = {}

        if not helpers.get_xml_attr(session, 'ratingKey').isdigit():
            channel_stream = 1

            audio_channels = helpers.get_xml_attr(stream_media_info, 'audioChannels')
            metadata_details = {'media_type': media_type,
                                'server_id': self.CONFIG.ID,
                                'server_name': self.CONFIG.PMS_NAME,
                                'section_id': helpers.get_xml_attr(session, 'librarySectionID'),
                                'library_name': helpers.get_xml_attr(session, 'librarySectionTitle'),
                                'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                                'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                                'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                                'title': helpers.get_xml_attr(session, 'title'),
                                'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                                'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                                'original_title': helpers.get_xml_attr(session, 'originalTitle'),
                                'sort_title': helpers.get_xml_attr(session, 'titleSort'),
                                'media_index': helpers.get_xml_attr(session, 'index'),
                                'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                                'studio': helpers.get_xml_attr(session, 'studio'),
                                'content_rating': helpers.get_xml_attr(session, 'contentRating'),
                                'summary': helpers.get_xml_attr(session, 'summary'),
                                'tagline': helpers.get_xml_attr(session, 'tagline'),
                                'rating': helpers.get_xml_attr(session, 'rating'),
                                'rating_image': helpers.get_xml_attr(session, 'ratingImage'),
                                'audience_rating': helpers.get_xml_attr(session, 'audienceRating'),
                                'audience_rating_image': helpers.get_xml_attr(session, 'audienceRatingImage'),
                                'user_rating': helpers.get_xml_attr(session, 'userRating'),
                                'duration': helpers.get_xml_attr(session, 'duration'),
                                'year': helpers.get_xml_attr(session, 'year'),
                                'thumb': helpers.get_xml_attr(session, 'thumb'),
                                'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                                'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                                'art': helpers.get_xml_attr(session, 'art'),
                                'banner': helpers.get_xml_attr(session, 'banner'),
                                'originally_available_at': helpers.get_xml_attr(session, 'originallyAvailableAt'),
                                'added_at': helpers.get_xml_attr(session, 'addedAt'),
                                'updated_at': helpers.get_xml_attr(session, 'updatedAt'),
                                'last_viewed_at': helpers.get_xml_attr(session, 'lastViewedAt'),
                                'guid': helpers.get_xml_attr(session, 'guid'),
                                'directors': [],
                                'writers': [],
                                'actors': [],
                                'genres': [],
                                'labels': [],
                                'full_title': helpers.get_xml_attr(session, 'title'),
                                'container': helpers.get_xml_attr(stream_media_info, 'container') \
                                             or helpers.get_xml_attr(stream_media_parts_info, 'container'),
                                'height': helpers.get_xml_attr(stream_media_info, 'height'),
                                'width': helpers.get_xml_attr(stream_media_info, 'width'),
                                'video_codec': helpers.get_xml_attr(stream_media_info, 'videoCodec'),
                                'video_resolution': helpers.get_xml_attr(stream_media_info, 'videoResolution'),
                                'audio_codec': helpers.get_xml_attr(stream_media_info, 'audioCodec'),
                                'audio_channels': audio_channels,
                                'audio_channel_layout': common.AUDIO_CHANNELS.get(audio_channels, audio_channels),
                                'channel_icon': helpers.get_xml_attr(session, 'sourceIcon'),
                                'channel_title': helpers.get_xml_attr(session, 'sourceTitle'),
                                'extra_type': helpers.get_xml_attr(session, 'extraType'),
                                'sub_type': helpers.get_xml_attr(session, 'subtype')
                                }
        else:
            channel_stream = 0

            media_id = helpers.get_xml_attr(stream_media_info, 'id')
            part_id = helpers.get_xml_attr(stream_media_parts_info, 'id')

            if sync_id:
                metadata_details = self.get_metadata_details(rating_key=rating_key, sync_id=sync_id,
                                                             cache_key=session_key)
            else:
                metadata_details = self.get_metadata_details(rating_key=rating_key, cache_key=session_key)

            # Get the media info, fallback to first item if match id is not found
            source_medias = metadata_details.pop('media_info', [])
            source_media_details = next((m for m in source_medias if m['id'] == media_id),
                                        next((m for m in source_medias), {}))
            source_media_parts = source_media_details.pop('parts', [])
            source_media_part_details = next((p for p in source_media_parts if p['id'] == part_id),
                                             next((p for p in source_media_parts), {}))
            source_media_part_streams = source_media_part_details.pop('streams', [])

            source_video_details = {'id': '',
                                    'type': '',
                                    'video_codec': '',
                                    'video_codec_level': '',
                                    'video_bitrate': '',
                                    'video_bit_depth': '',
                                    'video_frame_rate': '',
                                    'video_ref_frames': '',
                                    'video_height': '',
                                    'video_width': '',
                                    'video_language': '',
                                    'video_language_code': '',
                                    'video_profile': ''
                                    }
            source_audio_details = {'id': '',
                                    'type': '',
                                    'audio_codec': '',
                                    'audio_bitrate': '',
                                    'audio_bitrate_mode': '',
                                    'audio_channels': '',
                                    'audio_channel_layout': '',
                                    'audio_sample_rate': '',
                                    'audio_language': '',
                                    'audio_language_code': '',
                                    'audio_profile': ''
                                    }
            source_subtitle_details = {'id': '',
                                       'type': '',
                                       'subtitle_codec': '',
                                       'subtitle_container': '',
                                       'subtitle_format': '',
                                       'subtitle_forced': 0,
                                       'subtitle_location': '',
                                       'subtitle_language': '',
                                       'subtitle_language_code': ''
                                       }
            if video_id:
                source_video_details = next((p for p in source_media_part_streams if p['id'] == video_id),
                                            next((p for p in source_media_part_streams if p['type'] == '1'),
                                                 source_video_details))
            if audio_id:
                source_audio_details = next((p for p in source_media_part_streams if p['id'] == audio_id),
                                            next((p for p in source_media_part_streams if p['type'] == '2'),
                                                 source_audio_details))
            if subtitle_id:
                source_subtitle_details = next((p for p in source_media_part_streams if p['id'] == subtitle_id),
                                               next((p for p in source_media_part_streams if p['type'] == '3'),
                                                    source_subtitle_details))

        # Overrides for live sessions
        if stream_details['live'] and transcode_session:
            stream_details['stream_container_decision'] = 'transcode'
            stream_details['stream_container'] = transcode_details['transcode_container']

            video_details['stream_video_decision'] = transcode_details['video_decision']
            stream_details['stream_video_codec'] = transcode_details['transcode_video_codec']

            audio_details['stream_audio_decision'] = transcode_details['audio_decision']
            stream_details['stream_audio_codec'] = transcode_details['transcode_audio_codec']
            stream_details['stream_audio_channels'] = transcode_details['transcode_audio_channels']
            stream_details['stream_audio_channel_layout'] = common.AUDIO_CHANNELS.get(
                transcode_details['transcode_audio_channels'], transcode_details['transcode_audio_channels'])

        # Generate a combined transcode decision value
        if video_details['stream_video_decision'] == 'transcode' or audio_details[
            'stream_audio_decision'] == 'transcode':
            transcode_decision = 'transcode'
        elif video_details['stream_video_decision'] == 'copy' or audio_details['stream_audio_decision'] == 'copy':
            transcode_decision = 'copy'
        else:
            transcode_decision = 'direct play'

        stream_details['transcode_decision'] = transcode_decision

        # Override * in audio codecs
        if stream_details['stream_audio_codec'] == '*':
            stream_details['stream_audio_codec'] = source_audio_details['audio_codec']
        if transcode_details['transcode_audio_codec'] == '*':
            transcode_details['transcode_audio_codec'] = source_audio_details['audio_codec']

        # Override * in video codecs
        if stream_details['stream_video_codec'] == '*':
            stream_details['stream_video_codec'] = source_video_details['video_codec']
        if transcode_details['transcode_video_codec'] == '*':
            transcode_details['transcode_video_codec'] = source_video_details['video_codec']

        # Get the quality profile
        if media_type in ('movie', 'episode', 'clip') and 'stream_bitrate' in stream_details:
            if sync_id:
                quality_profile = 'Original'

                synced_item_bitrate = helpers.cast_to_int(synced_item_details['video_bitrate'])
                try:
                    synced_bitrate = max(b for b in common.VIDEO_QUALITY_PROFILES if b <= synced_item_bitrate)
                    synced_version_profile = common.VIDEO_QUALITY_PROFILES[synced_bitrate]
                except ValueError:
                    synced_version_profile = 'Original'
            else:
                synced_version_profile = ''

                stream_bitrate = helpers.cast_to_int(stream_details['stream_bitrate'])
                source_bitrate = helpers.cast_to_int(source_media_details.get('bitrate'))
                try:
                    quailtiy_bitrate = min(
                        b for b in common.VIDEO_QUALITY_PROFILES if stream_bitrate <= b <= source_bitrate)
                    quality_profile = common.VIDEO_QUALITY_PROFILES[quailtiy_bitrate]
                except ValueError:
                    quality_profile = 'Original'

            if stream_details['optimized_version']:
                optimized_version_profile = '{} Mbps {}'.format(round(source_bitrate / 1000.0, 1),
                                                                plexpy.common.VIDEO_RESOLUTION_OVERRIDES.get(
                                                                    source_media_details['video_resolution'],
                                                                    source_media_details['video_resolution']))
            else:
                optimized_version_profile = ''

        elif media_type == 'track' and 'stream_bitrate' in stream_details:
            if sync_id:
                quality_profile = 'Original'

                synced_item_bitrate = helpers.cast_to_int(synced_item_details['audio_bitrate'])
                try:
                    synced_bitrate = max(b for b in common.AUDIO_QUALITY_PROFILES if b <= synced_item_bitrate)
                    synced_version_profile = common.AUDIO_QUALITY_PROFILES[synced_bitrate]
                except ValueError:
                    synced_version_profile = 'Original'
            else:
                synced_version_profile = ''

                stream_bitrate = helpers.cast_to_int(stream_details['stream_bitrate'])
                source_bitrate = helpers.cast_to_int(source_media_details.get('bitrate'))
                try:
                    quailtiy_bitrate = min(
                        b for b in common.AUDIO_QUALITY_PROFILES if stream_bitrate <= b <= source_bitrate)
                    quality_profile = common.AUDIO_QUALITY_PROFILES[quailtiy_bitrate]
                except ValueError:
                    quality_profile = 'Original'

            optimized_version_profile = ''

        elif media_type == 'photo':
            quality_profile = 'Original'
            synced_version_profile = ''
            optimized_version_profile = ''

        else:
            quality_profile = 'Unknown'
            synced_version_profile = ''
            optimized_version_profile = ''

        # Entire session output (single dict for backwards compatibility)
        session_output = {'server_id': self.CONFIG.ID,
                          'session_key': session_key,
                          'media_type': media_type,
                          'view_offset': view_offset,
                          'progress_percent': str(helpers.get_percent(view_offset, stream_details['stream_duration'])),
                          'quality_profile': quality_profile,
                          'synced_version_profile': synced_version_profile,
                          'optimized_version_profile': optimized_version_profile,
                          'user': user_details['username'],  # Keep for backwards compatibility
                          'channel_stream': channel_stream
                          }

        session_output.update(metadata_details)
        session_output.update(source_media_details)
        session_output.update(source_media_part_details)
        session_output.update(source_video_details)
        session_output.update(source_audio_details)
        session_output.update(source_subtitle_details)
        session_output.update(user_details)
        session_output.update(player_details)
        session_output.update(session_details)
        session_output.update(transcode_details)
        session_output.update(stream_details)
        session_output.update(video_details)
        session_output.update(audio_details)
        session_output.update(subtitle_details)

        return session_output

    def terminate_session(self, session_key='', session_id='', message=''):
        """
        Terminates a streaming session.

        Output: bool
        """
        message = message.encode('utf-8') or 'The server owner has ended the stream.'

        if session_key and not session_id:
            ap = activity_processor.ActivityProcessor(server=self)
            session = ap.get_session_by_key(session_key=session_key)
            session_id = session['session_id']

        elif session_id and not session_key:
            ap = activity_processor.ActivityProcessor(server=self)
            session = ap.get_session_by_id(session_id=session_id)
            session_key = session['session_key']

        if session_id:
            logger.info(u"Tautulli Servers :: %s: Terminating session %s (session_id %s)."
                        % (self.CONFIG.PMS_NAME, session_key, session_id))
            result = self.get_sessions_terminate(session_id=session_id, reason=urllib.parse.quote_plus(message))
            return result
        else:
            logger.warn(u"Tautulli Servers :: %s: Failed to terminate session %s. Missing session_id."
                        % (self.CONFIG.PMS_NAME, session_key))
            return False

    def get_item_children(self, rating_key='', get_grandchildren=False):
        """
        Return processed and validated children list.

        Output: array
        """
        if get_grandchildren:
            children_data = self.get_metadata_grandchildren(rating_key, output_format='xml')
        else:
            children_data = self.get_metadata_children(rating_key, output_format='xml')

        try:
            xml_head = children_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_item_children: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        children_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"Tautulli Servers :: %s: No children data." % self.CONFIG.PMS_NAME)
                    children_list = {'children_count': '0',
                                     'children_list': []
                                     }
                    return children_list

            result_data = []

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
            if a.getElementsByTagName('Video'):
                result_data = a.getElementsByTagName('Video')
            if a.getElementsByTagName('Track'):
                result_data = a.getElementsByTagName('Track')

            if result_data:
                for m in result_data:
                    directors = []
                    writers = []
                    actors = []
                    genres = []
                    labels = []

                    if m.getElementsByTagName('Director'):
                        for director in m.getElementsByTagName('Director'):
                            directors.append(helpers.get_xml_attr(director, 'tag'))

                    if m.getElementsByTagName('Writer'):
                        for writer in m.getElementsByTagName('Writer'):
                            writers.append(helpers.get_xml_attr(writer, 'tag'))

                    if m.getElementsByTagName('Role'):
                        for actor in m.getElementsByTagName('Role'):
                            actors.append(helpers.get_xml_attr(actor, 'tag'))

                    if m.getElementsByTagName('Genre'):
                        for genre in m.getElementsByTagName('Genre'):
                            genres.append(helpers.get_xml_attr(genre, 'tag'))

                    if m.getElementsByTagName('Label'):
                        for label in m.getElementsByTagName('Label'):
                            labels.append(helpers.get_xml_attr(label, 'tag'))

                    children_output = {'media_type': helpers.get_xml_attr(m, 'type'),
                                       'server_id': self.CONFIG.ID,
                                       'server_name': self.CONFIG.PMS_NAME,
                                       'section_id': helpers.get_xml_attr(m, 'librarySectionID'),
                                       'library_name': helpers.get_xml_attr(m, 'librarySectionTitle'),
                                       'rating_key': helpers.get_xml_attr(m, 'ratingKey'),
                                       'parent_rating_key': helpers.get_xml_attr(m, 'parentRatingKey'),
                                       'grandparent_rating_key': helpers.get_xml_attr(m, 'grandparentRatingKey'),
                                       'title': helpers.get_xml_attr(m, 'title'),
                                       'parent_title': helpers.get_xml_attr(m, 'parentTitle'),
                                       'grandparent_title': helpers.get_xml_attr(m, 'grandparentTitle'),
                                       'original_title': helpers.get_xml_attr(m, 'originalTitle'),
                                       'sort_title': helpers.get_xml_attr(m, 'titleSort'),
                                       'media_index': helpers.get_xml_attr(m, 'index'),
                                       'parent_media_index': helpers.get_xml_attr(m, 'parentIndex'),
                                       'studio': helpers.get_xml_attr(m, 'studio'),
                                       'content_rating': helpers.get_xml_attr(m, 'contentRating'),
                                       'summary': helpers.get_xml_attr(m, 'summary'),
                                       'tagline': helpers.get_xml_attr(m, 'tagline'),
                                       'rating': helpers.get_xml_attr(m, 'rating'),
                                       'rating_image': helpers.get_xml_attr(m, 'ratingImage'),
                                       'audience_rating': helpers.get_xml_attr(m, 'audienceRating'),
                                       'audience_rating_image': helpers.get_xml_attr(m, 'audienceRatingImage'),
                                       'user_rating': helpers.get_xml_attr(m, 'userRating'),
                                       'duration': helpers.get_xml_attr(m, 'duration'),
                                       'year': helpers.get_xml_attr(m, 'year'),
                                       'thumb': helpers.get_xml_attr(m, 'thumb'),
                                       'parent_thumb': helpers.get_xml_attr(m, 'parentThumb'),
                                       'grandparent_thumb': helpers.get_xml_attr(m, 'grandparentThumb'),
                                       'art': helpers.get_xml_attr(m, 'art'),
                                       'banner': helpers.get_xml_attr(m, 'banner'),
                                       'originally_available_at': helpers.get_xml_attr(m, 'originallyAvailableAt'),
                                       'added_at': helpers.get_xml_attr(m, 'addedAt'),
                                       'updated_at': helpers.get_xml_attr(m, 'updatedAt'),
                                       'last_viewed_at': helpers.get_xml_attr(m, 'lastViewedAt'),
                                       'guid': helpers.get_xml_attr(m, 'guid'),
                                       'directors': directors,
                                       'writers': writers,
                                       'actors': actors,
                                       'genres': genres,
                                       'labels': labels,
                                       'full_title': helpers.get_xml_attr(m, 'title')
                                       }
                    children_list.append(children_output)

        output = {'children_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'children_type': helpers.get_xml_attr(xml_head[0], 'viewGroup'),
                  'title': helpers.get_xml_attr(xml_head[0], 'title2'),
                  'children_list': children_list
                  }

        return output

    def get_item_children_related(self, rating_key=''):
        """
        Return processed and validated children list.

        Output: array
        """
        children_data = self.get_children_list_related(rating_key, output_format='xml')

        try:
            xml_head = children_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_item_children_related: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        children_results_list = {'movie': [],
                                 'show': [],
                                 'season': [],
                                 'episode': [],
                                 'artist': [],
                                 'album': [],
                                 'track': [],
                                 }

        for a in xml_head:
            section_id = helpers.get_xml_attr(a, 'librarySectionID')
            hubs = a.getElementsByTagName('Hub')

            for h in hubs:
                size = helpers.get_xml_attr(h, 'size')
                media_type = helpers.get_xml_attr(h, 'type')
                title = helpers.get_xml_attr(h, 'title')
                hub_identifier = helpers.get_xml_attr(h, 'hubIdentifier')

                if size == '0' or not hub_identifier.startswith('collection.related') or \
                        media_type not in children_results_list.keys():
                    continue

                result_data = []

                if h.getElementsByTagName('Video'):
                    result_data = h.getElementsByTagName('Video')
                if h.getElementsByTagName('Directory'):
                    result_data = h.getElementsByTagName('Directory')
                if h.getElementsByTagName('Track'):
                    result_data = h.getElementsByTagName('Track')

                for result in result_data:
                    children_output = {'section_id': section_id,
                                       'server_id': self.CONFIG.ID,
                                       'server_name': self.CONFIG.PMS_NAME,
                                       'rating_key': helpers.get_xml_attr(result, 'ratingKey'),
                                       'parent_rating_key': helpers.get_xml_attr(result, 'parentRatingKey'),
                                       'media_index': helpers.get_xml_attr(result, 'index'),
                                       'title': helpers.get_xml_attr(result, 'title'),
                                       'parent_title': helpers.get_xml_attr(result, 'parentTitle'),
                                       'year': helpers.get_xml_attr(result, 'year'),
                                       'thumb': helpers.get_xml_attr(result, 'thumb'),
                                       'parent_thumb': helpers.get_xml_attr(a, 'thumb'),
                                       'duration': helpers.get_xml_attr(result, 'duration')
                                       }
                    children_results_list[media_type].append(children_output)

            output = {'results_count': sum(len(s) for s in children_results_list.items()),
                      'results_list': children_results_list,
                      }

            return output

    def get_server_info(self):
        """
        Return the information about the server.

        Output: array
        """

        update_channel = self.get_server_update_channel()
        # logger.debug(u"Tautulli Servers :: %s: Plex update channel is %s." % (self.CONFIG.PMS_NAME, update_channel))

        plex_downloads = self.PLEXTV.get_plextv_downloads(plexpass=(update_channel == 'beta'))

        try:
            available_downloads = json.loads(plex_downloads)
        except Exception as e:
            logger.warn(
                u"Tautulli Servers :: %s: Unable to load JSON for get_plex_updates." % self.CONFIG.PMS_NAME)
            return {}

        # Get the updates for the platform
        pms_platform = common.PMS_PLATFORM_NAME_OVERRIDES.get(self.CONFIG.PMS_PLATFORM,
                                                              self.CONFIG.PMS_PLATFORM)
        platform_downloads = available_downloads.get('computer').get(pms_platform) or \
                             available_downloads.get('nas').get(pms_platform)

        if not platform_downloads:
            logger.error(
                u"Tautulli Servers :: %s: Unable to retrieve Plex updates: Could not match server platform: %s."
                % (self.CONFIG.PMS_NAME, pms_platform))
            return {}

        v_old = helpers.cast_to_int(
            "".join(v.zfill(4) for v in self.CONFIG.PMS_VERSION.split('-')[0].split('.')[:4]))
        v_new = helpers.cast_to_int(
            "".join(v.zfill(4) for v in platform_downloads.get('version', '').split('-')[0].split('.')[:4]))

        if not v_old:
            logger.error(
                u"Tautulli Servers :: %s: Unable to retrieve Plex updates: Invalid current server version: %s."
                % (self.CONFIG.PMS_NAME, self.CONFIG.PMS_VERSION))
            return {}
        if not v_new:
            logger.error(u"Tautulli Servers :: %s: Unable to retrieve Plex updates: Invalid new server version: %s."
                         % (self.CONFIG.PMS_NAME, platform_downloads.get('version')))
            return {}

        # Get proper download
        releases = platform_downloads.get('releases', [{}])
        release = next((r for r in releases if r['distro'] == "" and
                        r['build'] == ""), releases[0])

        download_info = {'update_available': v_new > v_old,
                         'platform': platform_downloads.get('name'),
                         'release_date': platform_downloads.get('release_date'),
                         'version': platform_downloads.get('version'),
                         'requirements': platform_downloads.get('requirements'),
                         'extra_info': platform_downloads.get('extra_info'),
                         'changelog_added': platform_downloads.get('items_added'),
                         'changelog_fixed': platform_downloads.get('items_fixed'),
                         'label': release.get('label'),
                         'distro': release.get('distro'),
                         'distro_build': release.get('build'),
                         'download_url': release.get('url'),
                         }
        return download_info

    def get_server_identity(self):
        """
        Return the local machine identity.

        Output: dict
        """
        identity = self.get_local_server_identity(output_format='xml')

        try:
            xml_head = identity.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_local_server_identity: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return {}

        server_identity = {}
        for a in xml_head:
            server_identity = {"machine_identifier": helpers.get_xml_attr(a, 'machineIdentifier'),
                               "version": helpers.get_xml_attr(a, 'version')
                               }

        return server_identity

    def get_server_pref(self, pref=None):
        """
        Return a specified server preference.

        Parameters required:    pref { name of preference }

        Output: string
        """
        if pref:
            prefs = self.get_server_prefs(output_format='xml')

            if prefs:
                try:
                    xml_head = prefs.getElementsByTagName('Setting')
                except Exception as e:
                    logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_server_prefs: %s."
                                % (self.CONFIG.PMS_NAME, e))
                    return ''

                pref_value = 'None'
                for a in xml_head:
                    if helpers.get_xml_attr(a, 'id') == pref:
                        pref_value = helpers.get_xml_attr(a, 'value')
                        break

                return pref_value
        else:
            logger.debug(u"Tautulli Servers :: %s: Server preferences queried but no parameter received."
                         % self.CONFIG.PMS_NAME)
        return None

    def get_server_children(self):
        """
        Return processed and validated server libraries list.

        Output: array
        """
        libraries_data = self.get_libraries_list(output_format='xml')

        try:
            xml_head = libraries_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_libraries_list: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        libraries_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"Tautulli Servers :: %s: No libraries data." % self.CONFIG.PMS_NAME)
                    libraries_list = {'libraries_count': '0',
                                      'libraries_list': []
                                      }
                    return libraries_list

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
                for result in result_data:
                    libraries_output = {'section_id': helpers.get_xml_attr(result, 'key'),
                                        'server_id': self.CONFIG.ID,
                                        'server_name': self.CONFIG.PMS_NAME,
                                        'section_type': helpers.get_xml_attr(result, 'type'),
                                        'section_name': helpers.get_xml_attr(result, 'title'),
                                        'agent': helpers.get_xml_attr(result, 'agent'),
                                        'thumb': helpers.get_xml_attr(result, 'thumb'),
                                        'art': helpers.get_xml_attr(result, 'art')
                                        }
                    libraries_list.append(libraries_output)

        output = {'libraries_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'title': helpers.get_xml_attr(xml_head[0], 'title1'),
                  'libraries_list': libraries_list
                  }

        return output

    def get_library_children_details(self, section_id='', section_type='', list_type='all', count='',
                                     rating_key='', label_key='', get_media_info=False):
        """
        Return processed and validated server library items list.

        Parameters required:    section_type { movie, show, episode, artist }
                                section_id { unique library key }

        Output: array
        """

        if section_type == 'movie':
            sort_type = '&type=1'
        elif section_type == 'show':
            sort_type = '&type=2'
        elif section_type == 'season':
            sort_type = '&type=3'
        elif section_type == 'episode':
            sort_type = '&type=4'
        elif section_type == 'artist':
            sort_type = '&type=8'
        elif section_type == 'album':
            sort_type = '&type=9'
        elif section_type == 'track':
            sort_type = '&type=10'
        elif section_type == 'photo':
            sort_type = ''
        elif section_type == 'photo_album':
            sort_type = '&type=14'
        elif section_type == 'picture':
            sort_type = '&type=13&clusterZoomLevel=1'
        elif section_type == 'clip':
            sort_type = '&type=12&clusterZoomLevel=1'
        else:
            sort_type = ''

        if str(section_id).isdigit():
            library_data = self.get_library_list(str(section_id), list_type, count, sort_type, label_key,
                                                 output_format='xml')
        elif str(rating_key).isdigit():
            library_data = self.get_metadata_children(str(rating_key), output_format='xml')
        else:
            logger.warn(
                u"Tautulli Servers :: %s: get_library_children called by invalid section_id or rating_key provided."
                % self.CONFIG.PMS_NAME)
            return []

        try:
            xml_head = library_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_library_children_details: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        children_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"Tautulli Servers :: %s: No library data." % self.CONFIG.PMS_NAME)
                    children_list = {'library_count': '0',
                                     'children_list': []
                                     }
                    return children_list

            if rating_key:
                library_count = helpers.get_xml_attr(xml_head[0], 'size')
            else:
                library_count = helpers.get_xml_attr(xml_head[0], 'totalSize')

            # Get show/season info from xml_head

            item_main = []
            if a.getElementsByTagName('Directory'):
                dir_main = a.getElementsByTagName('Directory')
                item_main += [d for d in dir_main if helpers.get_xml_attr(d, 'ratingKey')]
            if a.getElementsByTagName('Video'):
                item_main += a.getElementsByTagName('Video')
            if a.getElementsByTagName('Track'):
                item_main += a.getElementsByTagName('Track')
            if a.getElementsByTagName('Photo'):
                item_main += a.getElementsByTagName('Photo')

            for item in item_main:
                media_type = helpers.get_xml_attr(item, 'type')
                if item.nodeName == 'Directory' and media_type == 'photo':
                    media_type = 'photo_album'

                item_info = {'server_id': self.CONFIG.ID,
                             'server_name': self.CONFIG.PMS_NAME,
                             'section_id': helpers.get_xml_attr(a, 'librarySectionID'),
                             'media_type': media_type,
                             'rating_key': helpers.get_xml_attr(item, 'ratingKey'),
                             'parent_rating_key': helpers.get_xml_attr(item, 'parentRatingKey'),
                             'grandparent_rating_key': helpers.get_xml_attr(item, 'grandparentRatingKey'),
                             'title': helpers.get_xml_attr(item, 'title'),
                             'parent_title': helpers.get_xml_attr(item, 'parentTitle'),
                             'grandparent_title': helpers.get_xml_attr(item, 'grandparentTitle'),
                             'original_title': helpers.get_xml_attr(item, 'originalTitle'),
                             'sort_title': helpers.get_xml_attr(item, 'titleSort'),
                             'media_index': helpers.get_xml_attr(item, 'index'),
                             'parent_media_index': helpers.get_xml_attr(item, 'parentIndex'),
                             'year': helpers.get_xml_attr(item, 'year'),
                             'thumb': helpers.get_xml_attr(item, 'thumb'),
                             'parent_thumb': helpers.get_xml_attr(item, 'thumb'),
                             'grandparent_thumb': helpers.get_xml_attr(item, 'grandparentThumb'),
                             'added_at': helpers.get_xml_attr(item, 'addedAt')
                             }

                if get_media_info:
                    item_media = item.getElementsByTagName('Media')
                    for media in item_media:
                        media_info = {'container': helpers.get_xml_attr(media, 'container'),
                                      'bitrate': helpers.get_xml_attr(media, 'bitrate'),
                                      'video_codec': helpers.get_xml_attr(media, 'videoCodec'),
                                      'video_resolution': helpers.get_xml_attr(media, 'videoResolution'),
                                      'video_framerate': helpers.get_xml_attr(media, 'videoFrameRate'),
                                      'audio_codec': helpers.get_xml_attr(media, 'audioCodec'),
                                      'audio_channels': helpers.get_xml_attr(media, 'audioChannels'),
                                      'file': helpers.get_xml_attr(media.getElementsByTagName('Part')[0], 'file'),
                                      'file_size': helpers.get_xml_attr(media.getElementsByTagName('Part')[0], 'size'),
                                      }
                        item_info.update(media_info)

                children_list.append(item_info)

        output = {'library_count': library_count,
                  'children_list': children_list
                  }

        return output

    def get_library_details(self):
        """
        Return processed and validated library statistics.

        Output: array
        """
        server_libraries = self.get_server_children()

        server_library_stats = []

        if server_libraries and server_libraries['libraries_count'] != '0':
            libraries_list = server_libraries['libraries_list']

            for library in libraries_list:
                section_type = library['section_type']
                section_id = library['section_id']
                children_list = self.get_library_children_details(section_id=section_id, section_type=section_type,
                                                                  count='1')

                if children_list:
                    library_stats = {'section_id': section_id,
                                     'server_id': self.CONFIG.ID,
                                     'server_name': self.CONFIG.PMS_NAME,
                                     'section_name': library['section_name'],
                                     'section_type': section_type,
                                     'agent': library['agent'],
                                     'thumb': library['thumb'],
                                     'art': library['art'],
                                     'count': children_list['library_count']
                                     }

                    if section_type == 'show':
                        parent_list = self.get_library_children_details(section_id=section_id, section_type='season',
                                                                        count='1')
                        if parent_list:
                            parent_stats = {'parent_count': parent_list['library_count']}
                            library_stats.update(parent_stats)

                        child_list = self.get_library_children_details(section_id=section_id, section_type='episode',
                                                                       count='1')
                        if child_list:
                            child_stats = {'child_count': child_list['library_count']}
                            library_stats.update(child_stats)

                    if section_type == 'artist':
                        parent_list = self.get_library_children_details(section_id=section_id, section_type='album',
                                                                        count='1')
                        if parent_list:
                            parent_stats = {'parent_count': parent_list['library_count']}
                            library_stats.update(parent_stats)

                        child_list = self.get_library_children_details(section_id=section_id, section_type='track',
                                                                       count='1')
                        if child_list:
                            child_stats = {'child_count': child_list['library_count']}
                            library_stats.update(child_stats)

                    if section_type == 'photo':
                        parent_list = self.get_library_children_details(section_id=section_id, section_type='picture',
                                                                        count='1')
                        if parent_list:
                            parent_stats = {'parent_count': parent_list['library_count']}
                            library_stats.update(parent_stats)

                        child_list = self.get_library_children_details(section_id=section_id, section_type='clip',
                                                                       count='1')
                        if child_list:
                            child_stats = {'child_count': child_list['library_count']}
                            library_stats.update(child_stats)

                    server_library_stats.append(library_stats)

        return server_library_stats

    def get_library_label_details(self, section_id=''):
        labels_data = self.get_library_labels(section_id=str(section_id), output_format='xml')

        try:
            xml_head = labels_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_library_label_details: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return None

        labels_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"Tautulli Servers :: %s: No labels data." % self.CONFIG.PMS_NAME)
                    return labels_list

            if a.getElementsByTagName('Directory'):
                labels_main = a.getElementsByTagName('Directory')
                for item in labels_main:
                    label = {'label_key': helpers.get_xml_attr(item, 'key'),
                             'label_title': helpers.get_xml_attr(item, 'title')
                             }
                    labels_list.append(label)

        return labels_list

    def get_image(self, img=None, width=1000, height=1500, opacity=None, background=None, blur=None,
                  img_format='png', clip=False, refresh=False, **kwargs):
        """
        Return image data as array.
        Array contains the image content type and image binary

        Parameters required:    img { Plex image location }
        Optional parameters:    width { the image width }
                                height { the image height }
                                opacity { the image opacity 0-100 }
                                background { the image background HEX }
                                blur { the image blur 0-100 }
        Output: array
        """

        width = width or 1000
        height = height or 1500

        if img:
            if refresh:
                img = '{}/{}'.format(img.rstrip('/'), int(time.time()))

            params = {}
            params['url'] = img
            params['X-Plex-Token'] = self.CONFIG.PMS_TOKEN
            params['width'] = width
            params['height'] = height
            params['format'] = img_format

            if opacity:
                params['opacity'] = opacity
            if background:
                params['background'] = background
            if blur:
                params['blur'] = blur

            request_handler = http_handler.HTTPHandler(urls=self.url, token=self.CONFIG.PMS_TOKEN, timeout=plexpy.CONFIG.PMS_TIMEOUT)
            uri = '/photo/:/transcode?%s' % urllib.parse.urlencode(params)
            result = request_handler.make_request(uri=uri,
                                                  request_type='GET',
                                                  output_format='raw',
                                                  return_type=True)
            if result is None:
                return
            else:
                return result[0], result[1]

        else:
            logger.error(
                u"Tautulli Servers :: %s: Image proxy queried but no input received." % self.CONFIG.PMS_NAME)

    def get_search_results(self, query='', limit=''):
        """
        Return processed list of search results.

        Output: array
        """
        search_results = self.get_search(query=query, limit=limit, output_format='xml')

        try:
            xml_head = search_results.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_search_result: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return []

        search_results_list = {'movie': [],
                               'show': [],
                               'season': [],
                               'episode': [],
                               'artist': [],
                               'album': [],
                               'track': [],
                               'collection': []
                               }

        for a in xml_head:
            hubs = a.getElementsByTagName('Hub')

            for h in hubs:
                if helpers.get_xml_attr(h, 'size') == '0' or \
                        helpers.get_xml_attr(h, 'type') not in search_results_list.keys():
                    continue

                if h.getElementsByTagName('Video'):
                    result_data = h.getElementsByTagName('Video')
                    for result in result_data:
                        rating_key = helpers.get_xml_attr(result, 'ratingKey')
                        metadata = self.get_metadata_details(rating_key=rating_key)
                        search_results_list[metadata['media_type']].append(metadata)

                if h.getElementsByTagName('Directory'):
                    result_data = h.getElementsByTagName('Directory')
                    for result in result_data:
                        rating_key = helpers.get_xml_attr(result, 'ratingKey')
                        metadata = self.get_metadata_details(rating_key=rating_key)
                        search_results_list[metadata['media_type']].append(metadata)

                        if metadata['media_type'] == 'show':
                            show_seasons = self.get_item_children(rating_key=metadata['rating_key'])
                            if show_seasons['children_count'] != '0':
                                for season in show_seasons['children_list']:
                                    if season['rating_key']:
                                        metadata = self.get_metadata_details(rating_key=season['rating_key'])
                                        search_results_list['season'].append(metadata)

                if h.getElementsByTagName('Track'):
                    result_data = h.getElementsByTagName('Track')
                    for result in result_data:
                        rating_key = helpers.get_xml_attr(result, 'ratingKey')
                        metadata = self.get_metadata_details(rating_key=rating_key)
                        search_results_list[metadata['media_type']].append(metadata)

        output = {'results_count': sum(len(s) for s in search_results_list.values()),
                  'results_list': search_results_list
                  }

        return output

    def get_rating_keys_list(self, rating_key='', media_type=''):
        """
        Return processed list of grandparent/parent/child rating keys.

        Output: array
        """

        if media_type == 'movie':
            key_list = {0: {'rating_key': int(rating_key)}}
            return key_list

        if media_type == 'artist' or media_type == 'album' or media_type == 'track':
            match_type = 'title'
        else:
            match_type = 'index'

        section_id = None
        library_name = None

        # get grandparent rating key
        if media_type == 'season' or media_type == 'album':
            try:
                metadata = self.get_metadata_details(rating_key=rating_key)
                rating_key = metadata['parent_rating_key']
                section_id = metadata['section_id']
                library_name = metadata['library_name']
            except Exception as e:
                logger.warn(u"Tautulli Servers :: %s: Unable to get parent_rating_key for get_rating_keys_list: %s."
                            % (self.CONFIG.PMS_NAME, e))
                return {}

        elif media_type == 'episode' or media_type == 'track':
            try:
                metadata = self.get_metadata_details(rating_key=rating_key)
                rating_key = metadata['grandparent_rating_key']
                section_id = metadata['section_id']
                library_name = metadata['library_name']
            except Exception as e:
                logger.warn(
                    u"Tautulli Servers :: %s: Unable to get grandparent_rating_key for get_rating_keys_list: %s."
                    % (self.CONFIG.PMS_NAME, e))
                return {}

        # get parent_rating_keys
        metadata = self.get_metadata_children(str(rating_key), output_format='xml')

        try:
            xml_head = metadata.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_rating_keys_list: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return {}

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return {}

            title = helpers.get_xml_attr(a, 'title2')

            if a.getElementsByTagName('Directory'):
                parents_metadata = a.getElementsByTagName('Directory')
            else:
                parents_metadata = []

            parents = {}
            for item in parents_metadata:
                parent_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                parent_index = helpers.get_xml_attr(item, 'index')
                parent_title = helpers.get_xml_attr(item, 'title')

                if parent_rating_key:
                    # get rating_keys
                    metadata = self.get_metadata_children(str(parent_rating_key), output_format='xml')

                    try:
                        xml_head = metadata.getElementsByTagName('MediaContainer')
                    except Exception as e:
                        logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_rating_keys_list: %s."
                                    % (self.CONFIG.PMS_NAME, e))
                        return {}

                    for a in xml_head:
                        if a.getAttribute('size'):
                            if a.getAttribute('size') == '0':
                                return {}

                        if a.getElementsByTagName('Video'):
                            children_metadata = a.getElementsByTagName('Video')
                        elif a.getElementsByTagName('Track'):
                            children_metadata = a.getElementsByTagName('Track')
                        else:
                            children_metadata = []

                        children = {}
                        for item in children_metadata:
                            child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                            child_index = helpers.get_xml_attr(item, 'index')
                            child_title = helpers.get_xml_attr(item, 'title')

                            if child_rating_key:
                                key = int(child_index) if child_index else child_title
                                children.update({key: {'rating_key': int(child_rating_key)}})

                    key = int(parent_index) if match_type == 'index' else parent_title
                    parents.update({key:
                                        {'rating_key': int(parent_rating_key),
                                         'children': children}
                                    })

        key = 0 if match_type == 'index' else title
        key_list = {key: {'rating_key': int(rating_key),
                          'children': parents},
                    'section_id': section_id,
                    'library_name': library_name
                    }

        return key_list

    def get_server_response(self):
        # Refresh Plex remote access port mapping first
        self.put_refresh_reachability()
        account_data = self.get_account(output_format='xml')

        try:
            xml_head = account_data.getElementsByTagName('MyPlex')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_server_response: %s."
                        % (self.CONFIG.PMS_NAME, e))
            return None

        server_response = {}

        for a in xml_head:
            server_response = {'mapping_state': helpers.get_xml_attr(a, 'mappingState'),
                               'mapping_error': helpers.get_xml_attr(a, 'mappingError'),
                               'public_address': helpers.get_xml_attr(a, 'publicAddress'),
                               'public_port': helpers.get_xml_attr(a, 'publicPort')
                               }

        return server_response

    def get_update_status(self):
        # Refresh the Plex updater status first
        self.put_updater()
        updater_status = self.get_updater(output_format='xml')

        try:
            xml_head = updater_status.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn(u"Tautulli Servers :: %s: Unable to parse XML for get_update_staus: %s."
                        % (self.CONFIG.PMS_NAME, e))

            # Catch the malformed XML on certain PMS version.
            # XML parser helper returns empty list if there is an error parsing XML
            if updater_status == []:
                logger.warn(
                    u"Tautulli Pmsconnecrt :: %s: Plex API updater XML is broken on the current PMS version. Please update your PMS manually."
                    % self.CONFIG.PMS_NAME)
                logger.info(
                    u"Tautulli Servers :: %s: Tautulli is unable to check for Plex updates. Disabling check for Plex updates."
                    % self.CONFIG.PMS_NAME)

                # Disable check for Plex updates
                self.CONFIG.MONITOR_PMS_UPDATES = 0
                self.initialize_scheduler()

            return {}

        updater_info = {}
        for a in xml_head:
            if a.getElementsByTagName('Release'):
                release = a.getElementsByTagName('Release')
                for item in release:
                    updater_info = {'can_install': helpers.get_xml_attr(a, 'canInstall'),
                                    'download_url': helpers.get_xml_attr(a, 'downloadURL'),
                                    'version': helpers.get_xml_attr(item, 'version'),
                                    'state': helpers.get_xml_attr(item, 'state'),
                                    'changelog': helpers.get_xml_attr(item, 'fixed')
                                    }

        return updater_info

    def get_server_version(self):
        identity = self.get_server_identity()
        version = identity.get('version')
        return version

    def get_server_update_channel(self):
        update_channel_value = self.get_server_pref('ButlerUpdateChannel')

        if update_channel_value == '8':
            return 'beta'
        else:
            return 'public'
