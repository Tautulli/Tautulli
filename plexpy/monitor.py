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
        # logger.debug(u"Checking for active streams.")

        if session_list['stream_count'] != '0':
            media_container = session_list['sessions']
            active_streams = []

            for session in media_container:
                session_key = session['session_key']
                rating_key = session['rating_key']
                media_type = session['type']
                friendly_name = session['friendly_name']
                platform = session['player']
                title = session['title']
                parent_title = session['parent_title']
                grandparent_title = session['grandparent_title']
                machine_id = session['machine_id']
                user = session['user']

                write_session = monitor_db.write_session_key(session_key, rating_key, media_type)
                if write_session == 'insert':
                    # User started playing a stream :: We notify here
                    if media_type == 'track' or media_type == 'episode':
                        item_title = grandparent_title + ' - ' + title
                    elif media_type == 'movie':
                        item_title = title
                    else:
                        item_title = title
                    logger.info('%s (%s) starting playing %s' % (friendly_name, platform, item_title))
                    pushmessage = '%s (%s) starting playing %s' % (friendly_name, platform, item_title)

                    # Push any notifications
                    monitor_notifications = MonitorNotifications(media_type=media_type, user=user)
                    monitor_notifications.notify(pushmessage)

                    # Try and grab IP address from logs
                    if plexpy.CONFIG.PMS_LOGS_FOLDER:
                        monitor_processing = MonitorProcessing()
                        ip_address = monitor_processing.find_session_ip(rating_key=rating_key,
                                                                        machine_id=machine_id)

                keys = {'session_key': session_key,
                        'rating_key': rating_key}
                active_streams.append(keys)

            # Check our temp table for what we must do with the new stream
            db_streams = monitor_db.select('SELECT session_key, rating_key, media_type FROM sessions')
            for result in db_streams:
                if any(d['session_key'] == str(result[0]) for d in active_streams):
                    # The user's session is still active
                    pass
                    if any(d['rating_key'] == str(result[1]) for d in active_streams):
                        # The user is still playing the same media item
                        # Here we can check the play states
                        pass
                    else:
                        # The user has stopped playing a stream
                        monitor_db.action('DELETE FROM sessions WHERE session_key = ? AND rating_key = ?', [result[0], result[1]])
                else:
                    # The user's session is no longer active
                    monitor_db.action('DELETE FROM sessions WHERE session_key = ?', [result[0]])
        else:
            # No sessions exist
            # monitor_db.action('DELETE FROM sessions')
            pass

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

    def write_session_key(self, session_key=None, rating_key=None, media_type=None):

        values = {'rating_key': rating_key,
                  'media_type': media_type}

        keys = {'session_key': session_key,
                'rating_key': rating_key}

        result = self.upsert('sessions', values, keys)
        return result

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
        pass

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


class MonitorNotifications(object):

    def __init__(self, media_type, user=None):
        self.media_type = media_type
        self.user = user
        self.tv_notify_enabled = plexpy.CONFIG.TV_NOTIFY_ENABLE
        self.movie_notify_enabled = plexpy.CONFIG.MOVIE_NOTIFY_ENABLE
        self.music_notify_enabled = plexpy.CONFIG.MUSIC_NOTIFY_ENABLE

    def notify(self, message=None):
        if message:
            if self.media_type == 'movie':
                if self.movie_notify_enabled:
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])
            elif self.media_type == 'episode':
                if self.tv_notify_enabled:
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])
            elif self.media_type == 'track':
                if self.music_notify_enabled:
                    notification_handler.push_nofitications(message, 'PlexPy', common.notify_strings[1])
            elif self.media_type == 'clip':
                pass
            else:
                logger.debug(u"Notify called with unsupported media type.")
                pass
        else:
            logger.debug(u"Notify called without a message.")
