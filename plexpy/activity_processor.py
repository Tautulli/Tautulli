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

import threading
import time
import re

import plexpy
import database
import datafactory
import libraries
import log_reader
import logger
import notification_handler
import notifiers
import pmsconnect
import users


class ActivityProcessor(object):

    def __init__(self):
        self.db = database.MonitorDatabase()

    def write_session(self, session=None, notify=True):
        if session:
            values = {'session_key': session['session_key'],
                      'transcode_key': session['transcode_key'],
                      'section_id': session['section_id'],
                      'rating_key': session['rating_key'],
                      'media_type': session['media_type'],
                      'state': session['state'],
                      'user_id': session['user_id'],
                      'user': session['user'],
                      'machine_id': session['machine_id'],
                      'title': session['title'],
                      'parent_title': session['parent_title'],
                      'grandparent_title': session['grandparent_title'],
                      'full_title': session['full_title'],
                      'media_index': session['media_index'],
                      'parent_media_index': session['parent_media_index'],
                      'thumb': session['thumb'],
                      'parent_thumb': session['parent_thumb'],
                      'grandparent_thumb': session['grandparent_thumb'],
                      'year': session['year'],
                      'friendly_name': session['friendly_name'],
                      #'ip_address': session['ip_address'],
                      'player': session['player'],
                      'platform': session['platform'],
                      'parent_rating_key': session['parent_rating_key'],
                      'grandparent_rating_key': session['grandparent_rating_key'],
                      'view_offset': session['view_offset'],
                      'duration': session['duration'],
                      'video_decision': session['video_decision'],
                      'audio_decision': session['audio_decision'],
                      'transcode_decision': session['transcode_decision'],
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
                      'transcode_height': session['transcode_height'],
                      'stopped': None
                      }

            # Add ip_address back into values
            if session['ip_address']:
                values.update({'ip_address': session['ip_address']})

            keys = {'session_key': session['session_key'],
                    'rating_key': session['rating_key']}

            result = self.db.upsert('sessions', values, keys)

            if result == 'insert':
                # Check if any notification agents have notifications enabled
                if notify:
                    values.update({'ip_address': session['ip_address']})
                    plexpy.NOTIFY_QUEUE.put({'stream_data': values, 'notify_action': 'on_play'})

                # If it's our first write then time stamp it.
                started = int(time.time())
                timestamp = {'started': started}
                self.db.upsert('sessions', timestamp, keys)

                if notify:
                    plexpy.NOTIFY_QUEUE.put({'stream_data': values, 'notify_action': 'on_concurrent'})
                    plexpy.NOTIFY_QUEUE.put({'stream_data': values, 'notify_action': 'on_newdevice'})

                return True

    def write_session_history(self, session=None, import_metadata=None, is_import=False, import_ignore_interval=0):
        section_id = session['section_id'] if not is_import else import_metadata['section_id']

        if not is_import:
            user_data = users.Users()
            user_details = user_data.get_details(user_id=session['user_id'])

            library_data = libraries.Libraries()
            library_details = library_data.get_details(section_id=section_id)

            # Return false if failed to retrieve user or library details
            if not user_details or not library_details:
                return False

        if session:
            logging_enabled = False

            if is_import:
                if str(session['stopped']).isdigit():
                    stopped = int(session['stopped'])
                else:
                    stopped = int(time.time())
            elif session['stopped']:
                stopped = int(session['stopped'])
            else:
                stopped = int(time.time())
                self.set_session_state(session_key=session['session_key'],
                                       state='stopped',
                                       stopped=stopped)

            if plexpy.CONFIG.MOVIE_LOGGING_ENABLE and str(session['rating_key']).isdigit() and \
                    session['media_type'] == 'movie':
                logging_enabled = True
            elif plexpy.CONFIG.TV_LOGGING_ENABLE and str(session['rating_key']).isdigit() and \
                    session['media_type'] == 'episode':
                logging_enabled = True
            elif plexpy.CONFIG.MUSIC_LOGGING_ENABLE and str(session['rating_key']).isdigit() and \
                    session['media_type'] == 'track':
                logging_enabled = True
            else:
                logger.debug(u"PlexPy ActivityProcessor :: ratingKey %s not logged. Does not meet logging criteria. "
                             u"Media type is '%s'" % (session['rating_key'], session['media_type']))

            if str(session['paused_counter']).isdigit():
                real_play_time = stopped - session['started'] - int(session['paused_counter'])
            else:
                real_play_time = stopped - session['started']

            if not is_import and plexpy.CONFIG.LOGGING_IGNORE_INTERVAL:
                if (session['media_type'] == 'movie' or session['media_type'] == 'episode') and \
                        (real_play_time < int(plexpy.CONFIG.LOGGING_IGNORE_INTERVAL)):
                    logging_enabled = False
                    logger.debug(u"PlexPy ActivityProcessor :: Play duration for ratingKey %s is %s secs which is less than %s "
                                 u"seconds, so we're not logging it." %
                                 (session['rating_key'], str(real_play_time), plexpy.CONFIG.LOGGING_IGNORE_INTERVAL))
            if not is_import and session['media_type'] == 'track':
                if real_play_time < 15 and session['duration'] >= 30:
                    logging_enabled = False
                    logger.debug(u"PlexPy ActivityProcessor :: Play duration for ratingKey %s is %s secs, "
                                 u"looks like it was skipped so we're not logging it" %
                                 (session['rating_key'], str(real_play_time)))
            elif is_import and import_ignore_interval:
                if (session['media_type'] == 'movie' or session['media_type'] == 'episode') and \
                        (real_play_time < int(import_ignore_interval)):
                    logging_enabled = False
                    logger.debug(u"PlexPy ActivityProcessor :: Play duration for ratingKey %s is %s secs which is less than %s "
                                 u"seconds, so we're not logging it." %
                                 (session['rating_key'], str(real_play_time), import_ignore_interval))

            if not is_import and not user_details['keep_history']:
                logging_enabled = False
                logger.debug(u"PlexPy ActivityProcessor :: History logging for user '%s' is disabled." % user_details['username'])
            elif not is_import and not library_details['keep_history']:
                logging_enabled = False
                logger.debug(u"PlexPy ActivityProcessor :: History logging for library '%s' is disabled." % library_details['section_name'])

            if logging_enabled:

                # Fetch metadata first so we can return false if it fails
                if not is_import:
                    logger.debug(u"PlexPy ActivityProcessor :: Fetching metadata for item ratingKey %s" % session['rating_key'])
                    pms_connect = pmsconnect.PmsConnect()
                    metadata = pms_connect.get_metadata_details(rating_key=str(session['rating_key']))
                    if not metadata:
                        return False
                else:
                    metadata = import_metadata

                # logger.debug(u"PlexPy ActivityProcessor :: Attempting to write to session_history table...")
                query = 'INSERT INTO session_history (started, stopped, rating_key, parent_rating_key, ' \
                        'grandparent_rating_key, media_type, user_id, user, ip_address, paused_counter, player, ' \
                        'platform, machine_id, view_offset) VALUES ' \
                        '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['started'], stopped, session['rating_key'], session['parent_rating_key'],
                        session['grandparent_rating_key'], session['media_type'], session['user_id'], session['user'],
                        session['ip_address'], session['paused_counter'], session['player'], session['platform'],
                        session['machine_id'], session['view_offset']]

                # logger.debug(u"PlexPy ActivityProcessor :: Writing session_history transaction...")
                self.db.action(query=query, args=args)

                # Check if we should group the session, select the last two rows from the user
                query = 'SELECT id, rating_key, view_offset, user_id, reference_id FROM session_history \
                         WHERE user_id = ? ORDER BY id DESC LIMIT 2 '

                args = [session['user_id']]

                result = self.db.select(query=query, args=args)

                new_session = prev_session = last_id = None
                if len(result) > 1:
                    new_session = {'id': result[0]['id'],
                                   'rating_key': result[0]['rating_key'],
                                   'view_offset': result[0]['view_offset'],
                                   'user_id': result[0]['user_id'],
                                   'reference_id': result[0]['reference_id']}

                    prev_session = {'id': result[1]['id'],
                                    'rating_key': result[1]['rating_key'],
                                    'view_offset': result[1]['view_offset'],
                                    'user_id': result[1]['user_id'],
                                    'reference_id': result[1]['reference_id']}
                else:
                    # Get the last insert row id
                    last_id = self.db.last_insert_id()

                query = 'UPDATE session_history SET reference_id = ? WHERE id = ? '
                # If rating_key is the same in the previous session, then set the reference_id to the previous row, else set the reference_id to the new id
                if  prev_session == new_session == None:
                    args = [last_id, last_id]
                elif prev_session['rating_key'] == new_session['rating_key'] and prev_session['view_offset'] <= new_session['view_offset']:
                    args = [prev_session['reference_id'], new_session['id']]
                else:
                    args = [new_session['id'], new_session['id']]

                self.db.action(query=query, args=args)
                
                # logger.debug(u"PlexPy ActivityProcessor :: Successfully written history item, last id for session_history is %s"
                #              % last_id)

                # Write the session_history_media_info table

                # logger.debug(u"PlexPy ActivityProcessor :: Attempting to write to session_history_media_info table...")
                query = 'INSERT INTO session_history_media_info (id, rating_key, video_decision, audio_decision, ' \
                        'duration, width, height, container, video_codec, audio_codec, bitrate, video_resolution, ' \
                        'video_framerate, aspect_ratio, audio_channels, transcode_protocol, transcode_container, ' \
                        'transcode_video_codec, transcode_audio_codec, transcode_audio_channels, transcode_width, ' \
                        'transcode_height, transcode_decision) VALUES ' \
                        '(last_insert_rowid(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['rating_key'], session['video_decision'], session['audio_decision'],
                        session['duration'], session['width'], session['height'], session['container'],
                        session['video_codec'], session['audio_codec'], session['bitrate'],
                        session['video_resolution'], session['video_framerate'], session['aspect_ratio'],
                        session['audio_channels'], session['transcode_protocol'], session['transcode_container'],
                        session['transcode_video_codec'], session['transcode_audio_codec'],
                        session['transcode_audio_channels'], session['transcode_width'], session['transcode_height'],
                        session['transcode_decision']]

                # logger.debug(u"PlexPy ActivityProcessor :: Writing session_history_media_info transaction...")
                self.db.action(query=query, args=args)

                # Write the session_history_metadata table
                directors = ";".join(metadata['directors'])
                writers = ";".join(metadata['writers'])
                actors = ";".join(metadata['actors'])
                genres = ";".join(metadata['genres'])
                labels = ";".join(metadata['labels'])

                # logger.debug(u"PlexPy ActivityProcessor :: Attempting to write to session_history_metadata table...")
                query = 'INSERT INTO session_history_metadata (id, rating_key, parent_rating_key, ' \
                        'grandparent_rating_key, title, parent_title, grandparent_title, full_title, media_index, ' \
                        'parent_media_index, section_id, thumb, parent_thumb, grandparent_thumb, art, media_type, ' \
                        'year, originally_available_at, added_at, updated_at, last_viewed_at, content_rating, ' \
                        'summary, tagline, rating, duration, guid, directors, writers, actors, genres, studio, labels) ' \
                        'VALUES (last_insert_rowid(), ' \
                        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'

                args = [session['rating_key'], session['parent_rating_key'], session['grandparent_rating_key'],
                        session['title'], session['parent_title'], session['grandparent_title'], session['full_title'],
                        metadata['media_index'], metadata['parent_media_index'], metadata['section_id'], metadata['thumb'],
                        metadata['parent_thumb'], metadata['grandparent_thumb'], metadata['art'], session['media_type'],
                        metadata['year'], metadata['originally_available_at'], metadata['added_at'], metadata['updated_at'],
                        metadata['last_viewed_at'], metadata['content_rating'], metadata['summary'], metadata['tagline'], 
                        metadata['rating'], metadata['duration'], metadata['guid'], directors, writers, actors, genres,
                        metadata['studio'], labels]

                # logger.debug(u"PlexPy ActivityProcessor :: Writing session_history_metadata transaction...")
                self.db.action(query=query, args=args)

            # Return true when the session is successfully written to the database
            return True

    def find_session_ip(self, rating_key=None, machine_id=None):

        logger.debug(u"PlexPy ActivityProcessor :: Requesting log lines...")
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
                        # check if IPv4 mapped IPv6 address (::ffff:xxx.xxx.xxx.xxx)
                        #if '::ffff:' + ipv4[0] in line:
                        #    logger.debug(u"PlexPy ActivityProcessor :: Matched IP address (%s) for stream ratingKey %s "
                        #                 u"and machineIdentifier %s."
                        #                 % ('::ffff:' + ipv4[0], rating_key, machine_id))
                        #    return '::ffff:' + ipv4[0]
                        #else:
                        logger.debug(u"PlexPy ActivityProcessor :: Matched IP address (%s) for stream ratingKey %s "
                                        u"and machineIdentifier %s."
                                        % (ipv4[0], rating_key, machine_id))
                        return ipv4[0]

        logger.debug(u"PlexPy ActivityProcessor :: Unable to find IP address on first pass. "
                     u"Attempting fallback check in 5 seconds...")

        # Wait for the log to catch up and read in new lines
        time.sleep(5)

        logger.debug(u"PlexPy ActivityProcessor :: Requesting log lines...")
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
                        #if '::ffff:' + ipv4[0] in line:
                        #    logger.debug(u"PlexPy ActivityProcessor :: Matched IP address (%s) for stream ratingKey %s." %
                        #                 ('::ffff:' + ipv4[0], rating_key))
                        #    return '::ffff:' + ipv4[0]
                        #else:
                        logger.debug(u"PlexPy ActivityProcessor :: Matched IP address (%s) for stream ratingKey %s." %
                                        (ipv4[0], rating_key))
                        return ipv4[0]

        logger.debug(u"PlexPy ActivityProcessor :: Unable to find IP address on fallback search. Not logging IP address.")

        return None

    def get_session_by_key(self, session_key=None):
        if str(session_key).isdigit():
            result = self.db.select('SELECT * '
                                    'FROM sessions WHERE session_key = ? LIMIT 1', args=[session_key])
            for session in result:
                if session:
                    return session

        return None

    def set_session_state(self, session_key=None, state=None, **kwargs):
        if str(session_key).isdigit():
            values = {}

            if state:
                values['state'] = state

            for k,v in kwargs.iteritems():
                values[k] = v

            keys = {'session_key': session_key}
            result = self.db.upsert('sessions', values, keys)

            return result

        return None

    def delete_session(self, session_key=None):
        if str(session_key).isdigit():
            self.db.action('DELETE FROM sessions WHERE session_key = ?', [session_key])

    def set_session_last_paused(self, session_key=None, timestamp=None):
        if str(session_key).isdigit():
            result = self.db.select('SELECT last_paused, paused_counter '
                                    'FROM sessions '
                                    'WHERE session_key = ?', args=[session_key])

            paused_counter = None
            for session in result:
                if session['last_paused']:
                    paused_offset = int(time.time()) - int(session['last_paused'])
                    if session['paused_counter']:
                        paused_counter = int(session['paused_counter']) + int(paused_offset)
                    else:
                        paused_counter = int(paused_offset)

            values = {'state': 'playing',
                      'last_paused': timestamp
                      }
            if paused_counter:
                values['paused_counter'] = paused_counter

            keys = {'session_key': session_key}
            self.db.upsert('sessions', values, keys)

    def increment_session_buffer_count(self, session_key=None):
        if str(session_key).isdigit():
            self.db.action('UPDATE sessions SET buffer_count = buffer_count + 1 '
                           'WHERE session_key = ?',
                           [session_key])

    def get_session_buffer_count(self, session_key=None):
        if str(session_key).isdigit():
            buffer_count = self.db.select_single('SELECT buffer_count '
                                                 'FROM sessions '
                                                 'WHERE session_key = ?',
                                                 [session_key])
            if buffer_count:
                return buffer_count['buffer_count']

            return 0

    def set_session_buffer_trigger_time(self, session_key=None):
        if str(session_key).isdigit():
            self.db.action('UPDATE sessions SET buffer_last_triggered = strftime("%s","now") '
                           'WHERE session_key = ?',
                           [session_key])

    def get_session_buffer_trigger_time(self, session_key=None):
        if str(session_key).isdigit():
            last_time = self.db.select_single('SELECT buffer_last_triggered '
                                              'FROM sessions '
                                              'WHERE session_key = ?',
                                              [session_key])
            if last_time:
                return last_time['buffer_last_triggered']

            return None

    def get_session_by_user_id(self, user_id=None, ip_address=None):
        sessions = []
        if str(user_id).isdigit():
            ip = 'GROUP BY ip_address' if ip_address else ''
            sessions = self.db.select('SELECT * '
                                      'FROM sessions '
                                      'WHERE user_id = ? %s' % ip,
                                      [user_id])
        return sessions

    def set_temp_stopped(self):
        stopped_time = int(time.time())
        monitor_db.action('UPDATE sessions SET stopped = ?', [stopped_time])