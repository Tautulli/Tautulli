﻿# This file is part of PlexPy.
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

from plexpy import logger, pmsconnect, notification_handler, log_reader, common, database, helpers

import threading
import plexpy
import re
import time

monitor_lock = threading.Lock()

def check_active_sessions():

    with monitor_lock:
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()
        monitor_db = database.MonitorDatabase()
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
            for stream in db_streams:
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
                                    # Push any notifications -
                                    # Push it on it's own thread so we don't hold up our db actions
                                    threading.Thread(target=notification_handler.notify,
                                                     kwargs=dict(stream_data=stream, notify_action='pause')).start()
                                if session['state'] == 'playing' and stream['state'] == 'paused':
                                    # Push any notifications -
                                    # Push it on it's own thread so we don't hold up our db actions
                                    threading.Thread(target=notification_handler.notify,
                                                     kwargs=dict(stream_data=stream, notify_action='resume')).start()
                            if stream['state'] == 'paused':
                                # The stream is still paused so we need to increment the paused_counter
                                # Using the set config parameter as the interval, probably not the most accurate but
                                # it will have to do for now.
                                paused_counter = int(stream['paused_counter']) + plexpy.CONFIG.MONITORING_INTERVAL
                                monitor_db.action('UPDATE sessions SET paused_counter = ? '
                                                  'WHERE session_key = ? AND rating_key = ?',
                                                  [paused_counter, stream['session_key'], stream['rating_key']])
                            if session['state'] == 'buffering' and plexpy.CONFIG.BUFFER_THRESHOLD > 0:
                                # The stream is buffering so we need to increment the buffer_count
                                # We're going just increment on every monitor ping,
                                # would be difficult to keep track otherwise
                                monitor_db.action('UPDATE sessions SET buffer_count = buffer_count + 1 '
                                                  'WHERE session_key = ? AND rating_key = ?',
                                                  [stream['session_key'], stream['rating_key']])

                                # Check the current buffer count and last buffer to determine if we should notify
                                buffer_values = monitor_db.select('SELECT buffer_count, buffer_last_triggered '
                                                                  'FROM sessions '
                                                                  'WHERE session_key = ? AND rating_key = ?',
                                                                  [stream['session_key'], stream['rating_key']])

                                if buffer_values[0]['buffer_count'] >= plexpy.CONFIG.BUFFER_THRESHOLD:
                                    # Push any notifications -
                                    # Push it on it's own thread so we don't hold up our db actions
                                    # Our first buffer notification
                                    if buffer_values[0]['buffer_count'] == plexpy.CONFIG.BUFFER_THRESHOLD:
                                        logger.info(u"PlexPy Monitor :: User '%s' has triggered a buffer warning."
                                                    % stream['user'])
                                        # Set the buffer trigger time
                                        monitor_db.action('UPDATE sessions '
                                                          'SET buffer_last_triggered = strftime("%s","now") '
                                                          'WHERE session_key = ? AND rating_key = ?',
                                                          [stream['session_key'], stream['rating_key']])

                                        threading.Thread(target=notification_handler.notify,
                                                         kwargs=dict(stream_data=stream, notify_action='buffer')).start()
                                    else:
                                        # Subsequent buffer notifications after wait time
                                        if int(time.time()) > buffer_values[0]['buffer_last_triggered'] + \
                                                plexpy.CONFIG.BUFFER_WAIT:
                                            logger.info(u"PlexPy Monitor :: User '%s' has triggered multiple buffer warnings."
                                                    % stream['user'])
                                            # Set the buffer trigger time
                                            monitor_db.action('UPDATE sessions '
                                                              'SET buffer_last_triggered = strftime("%s","now") '
                                                              'WHERE session_key = ? AND rating_key = ?',
                                                              [stream['session_key'], stream['rating_key']])

                                            threading.Thread(target=notification_handler.notify,
                                                             kwargs=dict(stream_data=stream, notify_action='buffer')).start()

                                logger.debug(u"PlexPy Monitor :: Stream buffering. Count is now %s. Last triggered %s."
                                             % (buffer_values[0][0], buffer_values[0][1]))

                            # Check if the user has reached the offset in the media we defined as the "watched" percent
                            # Don't trigger if state is buffer as some clients push the progress to the end when
                            # buffering on start.
                            if session['progress'] and session['duration'] and session['state'] != 'buffering':
                                if helpers.get_percent(session['progress'],
                                                       session['duration']) > plexpy.CONFIG.NOTIFY_WATCHED_PERCENT:
                                    # Push any notifications -
                                    # Push it on it's own thread so we don't hold up our db actions
                                    threading.Thread(target=notification_handler.notify,
                                                     kwargs=dict(stream_data=stream, notify_action='watched')).start()

                else:
                    # The user has stopped playing a stream
                    logger.debug(u"PlexPy Monitor :: Removing sessionKey %s ratingKey %s from session queue"
                                 % (stream['session_key'], stream['rating_key']))
                    monitor_db.action('DELETE FROM sessions WHERE session_key = ? AND rating_key = ?',
                                      [stream['session_key'], stream['rating_key']])

                    # Check if the user has reached the offset in the media we defined as the "watched" percent
                    if stream['view_offset'] and stream['duration']:
                        if helpers.get_percent(stream['view_offset'],
                                               stream['duration']) > plexpy.CONFIG.NOTIFY_WATCHED_PERCENT:
                            # Push any notifications -
                            # Push it on it's own thread so we don't hold up our db actions
                            threading.Thread(target=notification_handler.notify,
                                             kwargs=dict(stream_data=stream, notify_action='watched')).start()

                    # Push any notifications - Push it on it's own thread so we don't hold up our db actions
                    threading.Thread(target=notification_handler.notify,
                                     kwargs=dict(stream_data=stream, notify_action='stop')).start()

                    # Write the item history on playback stop
                    # Just make sure that the ratingKey is indeed an integer
                    if stream['rating_key'].isdigit():
                        monitor_process.write_session_history(session=stream)

            # Process the newly received session data
            for session in media_container:
                monitor_process.write_session(session)
        else:
            logger.debug(u"PlexPy Monitor :: Unable to read session list.")


class MonitorProcessing(object):

    def __init__(self):
        self.db = database.MonitorDatabase()

    def write_session(self, session=None):

        values = {'session_key': session['session_key'],
                  'rating_key': session['rating_key'],
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
            # Push any notifications - Push it on it's own thread so we don't hold up our db actions
            threading.Thread(target=notification_handler.notify,
                             kwargs=dict(stream_data=values,notify_action='play')).start()

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
        from plexpy import users

        user_data = users.Users()
        user_details = user_data.get_user_friendly_name(user=session['user'])

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

            if not user_details['keep_history'] and not is_import:
                logging_enabled = False
                logger.debug(u"PlexPy Monitor :: History logging for user '%s' is disabled." % session['user'])

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
                        'tagline, rating, duration, guid, directors, writers, actors, genres, studio) VALUES ' \
                        '(last_insert_rowid(), ' \
                        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['rating_key'], session['parent_rating_key'], session['grandparent_rating_key'],
                        session['title'], session['parent_title'], session['grandparent_title'], full_title,
                        metadata['index'], metadata['parent_index'], metadata['thumb'], metadata['parent_thumb'],
                        metadata['grandparent_thumb'], metadata['art'], session['media_type'], metadata['year'],
                        metadata['originally_available_at'], metadata['added_at'], metadata['updated_at'],
                        metadata['last_viewed_at'], metadata['content_rating'], metadata['summary'], metadata['tagline'], 
                        metadata['rating'], metadata['duration'], metadata['guid'], directors, writers, actors, genres, metadata['studio']]

                # logger.debug(u"PlexPy Monitor :: Writing session_history_metadata transaction...")
                self.db.action(query=query, args=args)

    def find_session_ip(self, rating_key=None, machine_id=None):

        logger.debug(u"PlexPy Monitor :: Requesting log lines...")
        log_lines = log_reader.get_log_tail(window=5000, parsed=False)

        rating_key_line = 'ratingKey=' + rating_key
        rating_key_line_2 = 'metadata%2F' + rating_key
        machine_id_line = 'session=' + machine_id

        for line in reversed(log_lines):
            # We're good if we find a line with both machine id and rating key
            # This is usually when there is a transcode session
            if machine_id_line in line and (rating_key_line in line or rating_key_line_2 in line):
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
            if 'GET /:/timeline' in line and (rating_key_line in line or rating_key_line_2 in line):
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
