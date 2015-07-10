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

from plexpy import logger, helpers, plexwatch, pmsconnect, notification_handler, config, log_reader, common

from xml.dom import minidom
from httplib import HTTPSConnection
from httplib import HTTPConnection

import os
import sqlite3
import threading
import plexpy
import re
import time

monitor_lock = threading.Lock()

def check_active_sessions():

    with monitor_lock:
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()
        monitor_db = MonitorDatabase()
        monitor_process = MonitorProcessing()
        # logger.debug(u"PlexPy Monitor :: Checking for active streams.")

        if session_list:
            media_container = session_list['sessions']

            # Check our temp table for what we must do with the new streams
            db_streams = monitor_db.select('SELECT session_key, rating_key, media_type, title, parent_title, '
                                           'grandparent_title, user, friendly_name, player, state '
                                           'FROM sessions')
            for result in db_streams:
                # Build a result dictionary for easier referencing
                stream = {'session_key': result[0],
                          'rating_key': result[1],
                          'media_type': result[2],
                          'title': result[3],
                          'parent_title': result[4],
                          'grandparent_title': result[5],
                          'user': result[6],
                          'friendly_name': result[7],
                          'player': result[8],
                          'state': result[9]
                          }

                if any(d['session_key'] == str(stream['session_key']) for d in media_container):
                    # The user's session is still active
                    for session in media_container:
                        if session['rating_key'] == str(stream['rating_key']):
                            # The user is still playing the same media item
                            # Here we can check the play states
                            if session['state'] != stream['state']:
                                if session['state'] == 'paused':
                                    # Push any notifications
                                    notify(stream_data=stream, notify_action='pause')
                        else:
                            # The user has stopped playing a stream
                            monitor_db.action('DELETE FROM sessions WHERE session_key = ? AND rating_key = ?',
                                              [stream['session_key'], stream['rating_key']])
                            # Push any notifications
                            notify(stream_data=stream, notify_action='stop')
                else:
                    # The user's session is no longer active
                    monitor_db.action('DELETE FROM sessions WHERE session_key = ?', [stream['session_key']])
                    # Push any notifications
                    notify(stream_data=stream, notify_action='stop')

            # Process the newly received session data
            for session in media_container:
                monitor_process.write_session(session)
        else:
            logger.debug(u"PlexPy Monitor :: Unable to read session list.")

def drop_session_db():
    monitor_db = MonitorDatabase()
    monitor_db.action('DROP TABLE sessions')

def db_filename(filename="plexpy.db"):

    return os.path.join(plexpy.DATA_DIR, filename)

def get_cache_size():
    # This will protect against typecasting problems produced by empty string and None settings
    if not plexpy.CONFIG.CACHE_SIZEMB:
        # sqlite will work with this (very slowly)
        return 0
    return int(plexpy.CONFIG.CACHE_SIZEMB)


class MonitorDatabase(object):

    def __init__(self, filename='plexpy.db'):
        self.filename = filename
        self.connection = sqlite3.connect(db_filename(filename), timeout=20)
        # Don't wait for the disk to finish writing
        self.connection.execute("PRAGMA synchronous = OFF")
        # Journal disabled since we never do rollbacks
        self.connection.execute("PRAGMA journal_mode = %s" % plexpy.CONFIG.JOURNAL_MODE)
        # 64mb of cache memory, probably need to make it user configurable
        self.connection.execute("PRAGMA cache_size=-%s" % (get_cache_size() * 1024))
        self.connection.row_factory = sqlite3.Row

    def action(self, query, args=None):

        if query is None:
            return

        sql_result = None

        try:
            with self.connection as c:
                if args is None:
                    sql_result = c.execute(query)
                else:
                    sql_result = c.execute(query, args)

        except sqlite3.OperationalError, e:
            if "unable to open database file" in e.message or "database is locked" in e.message:
                logger.warn('Database Error: %s', e)
            else:
                logger.error('Database error: %s', e)
                raise

        except sqlite3.DatabaseError, e:
            logger.error('Fatal Error executing %s :: %s', query, e)
            raise

        return sql_result

    def select(self, query, args=None):

        sql_results = self.action(query, args).fetchall()

        if sql_results is None or sql_results == [None]:
            return []

        return sql_results

    def upsert(self, table_name, value_dict, key_dict):

        trans_type = 'update'
        changes_before = self.connection.total_changes

        gen_params = lambda my_dict: [x + " = ?" for x in my_dict.keys()]

        update_query = "UPDATE " + table_name + " SET " + ", ".join(gen_params(value_dict)) + \
                       " WHERE " + " AND ".join(gen_params(key_dict))

        self.action(update_query, value_dict.values() + key_dict.values())

        if self.connection.total_changes == changes_before:
            trans_type = 'insert'
            insert_query = (
                "INSERT INTO " + table_name + " (" + ", ".join(value_dict.keys() + key_dict.keys()) + ")" +
                " VALUES (" + ", ".join(["?"] * len(value_dict.keys() + key_dict.keys())) + ")"
            )
            try:
                self.action(insert_query, value_dict.values() + key_dict.values())
            except sqlite3.IntegrityError:
                logger.info('Queries failed: %s and %s', update_query, insert_query)

        # We want to know if it was an update or insert
        return trans_type


class MonitorProcessing(object):

    def __init__(self):
        self.db = MonitorDatabase()

    def write_session(self, session=None):

        values = {'rating_key': session['rating_key'],
                  'media_type': session['type'],
                  'state': session['state'],
                  'user': session['user'],
                  'machine_id': session['machine_id'],
                  'title': session['title'],
                  'parent_title': session['parent_title'],
                  'grandparent_title': session['grandparent_title'],
                  'friendly_name': session['friendly_name'],
                  'player': session['player']
                  }

        timestamp = {'started': int(time.time())}

        keys = {'session_key': session['session_key'],
                'rating_key': session['rating_key']}

        result = self.db.upsert('sessions', values, keys)

        if result == 'insert':
            # If it's our first write then time stamp it.
            self.db.upsert('sessions', timestamp, keys)

            # Push any notifications
            notify(stream_data=values, notify_action='play')

            # Try and grab IP address from logs
            if plexpy.CONFIG.IP_LOGGING_ENABLE and plexpy.CONFIG.PMS_LOGS_FOLDER:
                ip_address = self.find_session_ip(rating_key=session['rating_key'],
                                                  machine_id=session['machine_id'])

    def find_session_ip(self, rating_key=None, machine_id=None):

        logger.debug(u"Requesting log lines...")
        log_lines = log_reader.get_log_tail(window=5000, parsed=False)

        rating_key_line = 'metadata%2F' + rating_key
        machine_id_line = 'session=' + machine_id

        for line in reversed(log_lines):
            # We're good if we find a line with both machine id and rating key
            # This is usually when there is a transcode session
            if machine_id_line in line and rating_key_line in line:
                # Currently only checking for ipv4 addresses
                ipv4 = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)
                if ipv4:
                    # The logged IP will always be the first match and we don't want localhost entries
                    if ipv4[0] != '127.0.0.1':
                        logger.debug(u"Matched IP address (%s) for stream ratingKey %s and machineIdentifier %s."
                                     % (ipv4[0], rating_key, machine_id))
                        return ipv4[0]

        logger.debug(u"Unable to find IP address on first pass. Attempting fallback check in 5 seconds...")

        # Wait for the log to catch up and read in new lines
        time.sleep(5)

        logger.debug(u"Requesting log lines...")
        log_lines = log_reader.get_log_tail(window=5000, parsed=False)

        for line in reversed(log_lines):
            if 'GET /:/timeline' in line and rating_key_line in line:
                # Currently only checking for ipv4 addresses
                # This method can return the wrong IP address if more than one user
                # starts watching the same media item around the same time.
                ipv4 = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)
                if ipv4:
                    # The logged IP will always be the first match and we don't want localhost entries
                    if ipv4[0] != '127.0.0.1':
                        logger.debug(u"Matched IP address (%s) for stream ratingKey %s." % (ipv4[0], rating_key))
                        return ipv4[0]

        logger.debug(u"Unable to find IP address on fallback search. Not logging IP address.")

        return None

def notify(stream_data=None, notify_action=None):

    if stream_data and notify_action:
        # Build media item title
        if stream_data['media_type'] == 'episode' or stream_data['media_type'] == 'track':
            item_title = '%s - %s' % (stream_data['grandparent_title'], stream_data['title'])
        elif stream_data['media_type'] == 'movie':
            item_title = stream_data['title']
        else:
            item_title = stream_data['title']

        if notify_action == 'play':
            logger.info('%s (%s) started playing %s.' % (stream_data['friendly_name'], stream_data['player'], item_title))

        if stream_data['media_type'] == 'movie':
            if plexpy.CONFIG.MOVIE_NOTIFY_ENABLE:

                if plexpy.CONFIG.MOVIE_NOTIFY_ON_START and notify_action == 'play':
                    message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

                elif plexpy.CONFIG.MOVIE_NOTIFY_ON_PAUSE and notify_action == 'pause':
                    message = '%s (%s) has paused %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

                elif plexpy.CONFIG.MOVIE_NOTIFY_ON_STOP and notify_action == 'stop':
                    message = '%s (%s) stopped playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

        elif stream_data['media_type'] == 'episode':
            if plexpy.CONFIG.TV_NOTIFY_ENABLE:

                if plexpy.CONFIG.TV_NOTIFY_ON_START and notify_action == 'play':
                    message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

                elif plexpy.CONFIG.TV_NOTIFY_ON_PAUSE and notify_action == 'pause':
                    message = '%s (%s) has paused %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

                elif plexpy.CONFIG.TV_NOTIFY_ON_STOP and notify_action == 'stop':
                    message = '%s (%s) stopped playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

        elif stream_data['media_type'] == 'track':
            if plexpy.CONFIG.MUSIC_NOTIFY_ENABLE:

                if plexpy.CONFIG.MUSIC_NOTIFY_ON_START and notify_action == 'play':
                    message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

                elif plexpy.CONFIG.MUSIC_NOTIFY_ON_PAUSE and notify_action == 'pause':
                    message = '%s (%s) has paused %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

                elif plexpy.CONFIG.MUSIC_NOTIFY_ON_STOP and notify_action == 'stop':
                    message = '%s (%s) stopped playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            logger.debug(u"Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"Notify called but incomplete data received.")
