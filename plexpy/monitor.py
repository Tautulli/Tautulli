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

from plexpy import logger, helpers, pmsconnect, notification_handler, config, log_reader, common

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
            db_streams = monitor_db.select('SELECT started, session_key, rating_key, media_type, title, parent_title, '
                                           'grandparent_title, user_id, user, friendly_name, ip_address, player, '
                                           'platform, machine_id, parent_rating_key, grandparent_rating_key, state, '
                                           'view_offset, duration, video_decision, audio_decision, width, height, '
                                           'container, video_codec, audio_codec, bitrate, video_resolution, '
                                           'video_framerate, aspect_ratio, audio_channels, transcode_protocol, '
                                           'transcode_container, transcode_video_codec, transcode_audio_codec, '
                                           'transcode_audio_channels, transcode_width, transcode_height, paused_counter '
                                           'FROM sessions')
            for result in db_streams:
                # Build a result dictionary for easier referencing
                stream = {'started': result[0],
                          'session_key': result[1],
                          'rating_key': result[2],
                          'media_type': result[3],
                          'title': result[4],
                          'parent_title': result[5],
                          'grandparent_title': result[6],
                          'user_id': result[7],
                          'user': result[8],
                          'friendly_name': result[9],
                          'ip_address': result[10],
                          'player': result[11],
                          'platform': result[12],
                          'machine_id': result[13],
                          'parent_rating_key': result[14],
                          'grandparent_rating_key': result[15],
                          'state': result[16],
                          'view_offset': result[17],
                          'duration': result[18],
                          'video_decision': result[19],
                          'audio_decision': result[20],
                          'width': result[21],
                          'height': result[22],
                          'container': result[23],
                          'video_codec': result[24],
                          'audio_codec': result[25],
                          'bitrate': result[26],
                          'video_resolution': result[27],
                          'video_framerate': result[28],
                          'aspect_ratio': result[29],
                          'audio_channels': result[30],
                          'transcode_protocol': result[31],
                          'transcode_container': result[32],
                          'transcode_video_codec': result[33],
                          'transcode_audio_codec': result[34],
                          'transcode_audio_channels': result[35],
                          'transcode_width': result[36],
                          'transcode_height': result[37],
                          'paused_counter': result[38]
                          }

                if any(d['session_key'] == str(stream['session_key']) and d['rating_key'] == str(stream['rating_key'])
                       for d in media_container):
                    # The user's session is still active
                    for session in media_container:
                        if session['session_key'] == str(stream['session_key']) and \
                                session['rating_key'] == str(stream['rating_key']):
                            # The user is still playing the same media item
                            # Here we can check the play states
                            if session['state'] != stream['state']:
                                if session['state'] == 'paused':
                                    # Push any notifications
                                    notify(stream_data=stream, notify_action='pause')
                            if stream['state'] == 'paused':
                                # The stream is still paused so we need to increment the paused_counter
                                # Using the set config parameter as the interval, probably not the most accurate but
                                # it will have to do for now.
                                paused_counter = int(stream['paused_counter']) + plexpy.CONFIG.MONITORING_INTERVAL
                                monitor_db.action('UPDATE sessions SET paused_counter = ? '
                                                  'WHERE session_key = ? AND rating_key = ?',
                                                  [paused_counter, stream['session_key'], stream['rating_key']])
                else:
                    # The user has stopped playing a stream
                    logger.debug(u"PlexPy Monitor :: Removing sessionKey %s ratingKey %s from session queue"
                                 % (stream['session_key'], stream['rating_key']))
                    monitor_db.action('DELETE FROM sessions WHERE session_key = ? AND rating_key = ?',
                                      [stream['session_key'], stream['rating_key']])
                    # Push any notifications
                    notify(stream_data=stream, notify_action='stop')
                    # Write the item history on playback stop
                    monitor_process.write_session_history(session=stream)

            # Process the newly received session data
            for session in media_container:
                monitor_process.write_session(session)
        else:
            logger.debug(u"PlexPy Monitor :: Unable to read session list.")

def drop_session_db():
    monitor_db = MonitorDatabase()
    monitor_db.action('DROP TABLE sessions')

def clear_history_tables():
    logger.debug(u"PlexPy Monitor :: Deleting all session_history records... No turning back now bub.")
    monitor_db = MonitorDatabase()
    monitor_db.action('DELETE FROM session_history')
    monitor_db.action('DELETE FROM session_history_media_info')
    monitor_db.action('DELETE FROM session_history_metadata')
    monitor_db.action('VACUUM;')

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

    def action(self, query, args=None, return_last_id=False):

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

    def select_single(self, query, args=None):

        sql_results = self.action(query, args).fetchone()[0]

        if sql_results is None or sql_results == "":
            return ""

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
                  'user_id': session['user_id'],
                  'user': session['user'],
                  'machine_id': session['machine_id'],
                  'title': session['title'],
                  'parent_title': session['parent_title'],
                  'grandparent_title': session['grandparent_title'],
                  'friendly_name': session['friendly_name'],
                  'player': session['player'],
                  'platform': session['platform'],
                  'parent_rating_key': session['parent_rating_key'],
                  'grandparent_rating_key': session['grandparent_rating_key'],
                  'view_offset': session['progress'],
                  'duration': session['duration'],
                  'video_decision': session['video_decision'],
                  'audio_decision': session['audio_decision'],
                  'width': session['width'],
                  'height': session['height'],
                  'container': session['container'],
                  'video_codec': session['video_codec'],
                  'audio_codec': session['audio_codec'],
                  'bitrate': session['bitrate'],
                  'video_resolution': session['video_resolution'],
                  'video_framerate': session['video_framerate'],
                  'aspect_ratio': session['aspect_ratio'],
                  'audio_channels': session['audio_channels'],
                  'transcode_protocol': session['transcode_protocol'],
                  'transcode_container': session['transcode_container'],
                  'transcode_video_codec': session['transcode_video_codec'],
                  'transcode_audio_codec': session['transcode_audio_codec'],
                  'transcode_audio_channels': session['transcode_audio_channels'],
                  'transcode_width': session['transcode_width'],
                  'transcode_height': session['transcode_height']
                  }

        keys = {'session_key': session['session_key'],
                'rating_key': session['rating_key']}

        result = self.db.upsert('sessions', values, keys)

        if result == 'insert':
            # Push any notifications
            notify(stream_data=values, notify_action='play')
            started = int(time.time())

            # Try and grab IP address from logs
            if plexpy.CONFIG.IP_LOGGING_ENABLE and plexpy.CONFIG.PMS_LOGS_FOLDER:
                ip_address = self.find_session_ip(rating_key=session['rating_key'],
                                                  machine_id=session['machine_id'])
            else:
                ip_address = None

            timestamp = {'started': started,
                         'ip_address': ip_address}

            # If it's our first write then time stamp it.
            self.db.upsert('sessions', timestamp, keys)

    def write_session_history(self, session=None, import_metadata=None, is_import=False, import_ignore_interval=0):

        if session:
            logging_enabled = False

            if is_import:
                if str(session['stopped']).isdigit():
                    stopped = session['stopped']
                else:
                    stopped = int(time.time())
            else:
                stopped = int(time.time())

            if plexpy.CONFIG.VIDEO_LOGGING_ENABLE and \
                    (session['media_type'] == 'movie' or session['media_type'] == 'episode'):
                logging_enabled = True
            elif plexpy.CONFIG.MUSIC_LOGGING_ENABLE and \
                    session['media_type'] == 'track':
                logging_enabled = True
            else:
                logger.debug(u"PlexPy Monitor :: ratingKey %s not logged. Does not meet logging criteria. "
                             u"Media type is '%s'" % (session['rating_key'], session['media_type']))

            if plexpy.CONFIG.LOGGING_IGNORE_INTERVAL and not is_import:
                if (session['media_type'] == 'movie' or session['media_type'] == 'episode') and \
                        (int(stopped) - session['started'] < int(plexpy.CONFIG.LOGGING_IGNORE_INTERVAL)):
                    logging_enabled = False
                    logger.debug(u"PlexPy Monitor :: Play duration for ratingKey %s is %s secs which is less than %s "
                                 u"seconds, so we're not logging it." %
                                 (session['rating_key'], str(int(stopped) - session['started']),
                                  plexpy.CONFIG.LOGGING_IGNORE_INTERVAL))
            elif is_import and import_ignore_interval:
                if (session['media_type'] == 'movie' or session['media_type'] == 'episode') and \
                        (int(stopped) - session['started'] < int(import_ignore_interval)):
                    logging_enabled = False
                    logger.debug(u"PlexPy Monitor :: Play duration for ratingKey %s is %s secs which is less than %s "
                                 u"seconds, so we're not logging it." %
                                 (session['rating_key'], str(int(stopped) - session['started']),
                                  import_ignore_interval))

            if logging_enabled:
                # logger.debug(u"PlexPy Monitor :: Attempting to write to session_history table...")
                query = 'INSERT INTO session_history (started, stopped, rating_key, parent_rating_key, ' \
                        'grandparent_rating_key, media_type, user_id, user, ip_address, paused_counter, player, ' \
                        'platform, machine_id, view_offset) VALUES ' \
                        '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['started'], stopped, session['rating_key'], session['parent_rating_key'],
                        session['grandparent_rating_key'], session['media_type'], session['user_id'], session['user'],
                        session['ip_address'], session['paused_counter'], session['player'], session['platform'],
                        session['machine_id'], session['view_offset']]

                # logger.debug(u"PlexPy Monitor :: Writing session_history transaction...")
                self.db.action(query=query, args=args)

                # logger.debug(u"PlexPy Monitor :: Successfully written history item, last id for session_history is %s"
                #              % last_id)

                # Write the session_history_media_info table
                # logger.debug(u"PlexPy Monitor :: Attempting to write to session_history_media_info table...")
                query = 'INSERT INTO session_history_media_info (id, rating_key, video_decision, audio_decision, ' \
                        'duration, width, height, container, video_codec, audio_codec, bitrate, video_resolution, ' \
                        'video_framerate, aspect_ratio, audio_channels, transcode_protocol, transcode_container, ' \
                        'transcode_video_codec, transcode_audio_codec, transcode_audio_channels, transcode_width, ' \
                        'transcode_height) VALUES ' \
                        '(last_insert_rowid(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['rating_key'], session['video_decision'], session['audio_decision'],
                        session['duration'], session['width'], session['height'], session['container'],
                        session['video_codec'], session['audio_codec'], session['bitrate'],
                        session['video_resolution'], session['video_framerate'], session['aspect_ratio'],
                        session['audio_channels'], session['transcode_protocol'], session['transcode_container'],
                        session['transcode_video_codec'], session['transcode_audio_codec'],
                        session['transcode_audio_channels'], session['transcode_width'], session['transcode_height']]

                # logger.debug(u"PlexPy Monitor :: Writing session_history_media_info transaction...")
                self.db.action(query=query, args=args)

                if not is_import:
                    logger.debug(u"PlexPy Monitor :: Fetching metadata for item ratingKey %s" % session['rating_key'])
                    pms_connect = pmsconnect.PmsConnect()
                    result = pms_connect.get_metadata_details(rating_key=str(session['rating_key']))
                    metadata = result['metadata']
                else:
                    metadata = import_metadata

                # Write the session_history_metadata table
                directors = ";".join(metadata['directors'])
                writers = ";".join(metadata['writers'])
                actors = ";".join(metadata['actors'])
                genres = ";".join(metadata['genres'])

                # Build media item title
                if session['media_type'] == 'episode' or session['media_type'] == 'track':
                    full_title = '%s - %s' % (metadata['grandparent_title'], metadata['title'])
                elif session['media_type'] == 'movie':
                    full_title = metadata['title']
                else:
                    full_title = metadata['title']

                # logger.debug(u"PlexPy Monitor :: Attempting to write to session_history_metadata table...")
                query = 'INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, ' \
                        'grandparent_rating_key, title, parent_title, grandparent_title, full_title, media_index, ' \
                        'parent_media_index, thumb, parent_thumb, grandparent_thumb, art, media_type, year, ' \
                        'originally_available_at, added_at, updated_at, last_viewed_at, content_rating, summary, ' \
                        'rating, duration, guid, directors, writers, actors, genres, studio) VALUES ' \
                        '(last_insert_rowid(), ' \
                        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['rating_key'], session['parent_rating_key'], session['grandparent_rating_key'],
                        session['title'], session['parent_title'], session['grandparent_title'], full_title,
                        metadata['index'], metadata['parent_index'], metadata['thumb'], metadata['parent_thumb'],
                        metadata['grandparent_thumb'], metadata['art'], session['media_type'], metadata['year'],
                        metadata['originally_available_at'], metadata['added_at'], metadata['updated_at'],
                        metadata['last_viewed_at'], metadata['content_rating'], metadata['summary'], metadata['rating'],
                        metadata['duration'], metadata['guid'], directors, writers, actors, genres, metadata['studio']]

                # logger.debug(u"PlexPy Monitor :: Writing session_history_metadata transaction...")
                self.db.action(query=query, args=args)

    def find_session_ip(self, rating_key=None, machine_id=None):

        logger.debug(u"PlexPy Monitor :: Requesting log lines...")
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
                        logger.debug(u"PlexPy Monitor :: Matched IP address (%s) for stream ratingKey %s "
                                     u"and machineIdentifier %s."
                                     % (ipv4[0], rating_key, machine_id))
                        return ipv4[0]

        logger.debug(u"PlexPy Monitor :: Unable to find IP address on first pass. "
                     u"Attempting fallback check in 5 seconds...")

        # Wait for the log to catch up and read in new lines
        time.sleep(5)

        logger.debug(u"PlexPy Monitor :: Requesting log lines...")
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
                        logger.debug(u"PlexPy Monitor :: Matched IP address (%s) for stream ratingKey %s." %
                                     (ipv4[0], rating_key))
                        return ipv4[0]

        logger.debug(u"PlexPy Monitor :: Unable to find IP address on fallback search. Not logging IP address.")

        return None

def notify(stream_data=None, notify_action=None):

    if stream_data and notify_action:
        # Get the server name
        pms_connect = pmsconnect.PmsConnect()
        server_name = pms_connect.get_server_pref(pref='FriendlyName')

        # Build the notification heading
        notify_header = 'PlexPy (%s)' % server_name

        # Build media item title
        if stream_data['media_type'] == 'episode' or stream_data['media_type'] == 'track':
            item_title = '%s - %s' % (stream_data['grandparent_title'], stream_data['title'])
        elif stream_data['media_type'] == 'movie':
            item_title = stream_data['title']
        else:
            item_title = stream_data['title']

        if notify_action == 'play':
            logger.info('PlexPy Monitor :: %s (%s) started playing %s.' % (stream_data['friendly_name'],
                                                                           stream_data['player'], item_title))

        if stream_data['media_type'] == 'movie':
            if plexpy.CONFIG.MOVIE_NOTIFY_ENABLE:

                if plexpy.CONFIG.MOVIE_NOTIFY_ON_START and notify_action == 'play':
                    message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

                elif plexpy.CONFIG.MOVIE_NOTIFY_ON_PAUSE and notify_action == 'pause':
                    message = '%s (%s) has paused %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

                elif plexpy.CONFIG.MOVIE_NOTIFY_ON_STOP and notify_action == 'stop':
                    message = '%s (%s) stopped playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

        elif stream_data['media_type'] == 'episode':
            if plexpy.CONFIG.TV_NOTIFY_ENABLE:

                if plexpy.CONFIG.TV_NOTIFY_ON_START and notify_action == 'play':
                    message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

                elif plexpy.CONFIG.TV_NOTIFY_ON_PAUSE and notify_action == 'pause':
                    message = '%s (%s) has paused %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

                elif plexpy.CONFIG.TV_NOTIFY_ON_STOP and notify_action == 'stop':
                    message = '%s (%s) stopped playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

        elif stream_data['media_type'] == 'track':
            if plexpy.CONFIG.MUSIC_NOTIFY_ENABLE:

                if plexpy.CONFIG.MUSIC_NOTIFY_ON_START and notify_action == 'play':
                    message = '%s (%s) started playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

                elif plexpy.CONFIG.MUSIC_NOTIFY_ON_PAUSE and notify_action == 'pause':
                    message = '%s (%s) has paused %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

                elif plexpy.CONFIG.MUSIC_NOTIFY_ON_STOP and notify_action == 'stop':
                    message = '%s (%s) stopped playing %s.' % \
                              (stream_data['friendly_name'], stream_data['player'], item_title)
                    notification_handler.push_nofitications(message, notify_header, common.notify_strings[1])

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            logger.debug(u"PlexPy Monitor :: Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"PlexPy Monitor :: Notify called but incomplete data received.")
