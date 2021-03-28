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

from __future__ import unicode_literals
from future.builtins import str
from future.builtins import object

from collections import defaultdict
import json

import plexpy
if plexpy.PYTHON2:
    import database
    import helpers
    import libraries
    import logger
    import pmsconnect
    import users
else:
    from plexpy import database
    from plexpy import helpers
    from plexpy import libraries
    from plexpy import logger
    from plexpy import pmsconnect
    from plexpy import users


class ActivityProcessor(object):

    def __init__(self):
        self.db = database.MonitorDatabase()

    def write_session(self, session=None, notify=True):
        if session:
            values = {'session_key': session.get('session_key', ''),
                      'session_id': session.get('session_id', ''),
                      'transcode_key': session.get('transcode_key', ''),
                      'section_id': session.get('section_id', ''),
                      'rating_key': session.get('rating_key', ''),
                      'media_type': session.get('media_type', ''),
                      'state': session.get('state', ''),
                      'user_id': session.get('user_id', ''),
                      'user': session.get('user', ''),
                      'machine_id': session.get('machine_id', ''),
                      'title': session.get('title', ''),
                      'parent_title': session.get('parent_title', ''),
                      'grandparent_title': session.get('grandparent_title', ''),
                      'original_title': session.get('original_title', ''),
                      'full_title': session.get('full_title', ''),
                      'media_index': session.get('media_index', ''),
                      'parent_media_index': session.get('parent_media_index', ''),
                      'thumb': session.get('thumb', ''),
                      'parent_thumb': session.get('parent_thumb', ''),
                      'grandparent_thumb': session.get('grandparent_thumb', ''),
                      'year': session.get('year', ''),
                      'friendly_name': session.get('friendly_name', ''),
                      'ip_address': session.get('ip_address', ''),
                      'bandwidth': session.get('bandwidth', 0),
                      'location': session.get('location', ''),
                      'player': session.get('player', ''),
                      'product': session.get('product', ''),
                      'platform': session.get('platform', ''),
                      'parent_rating_key': session.get('parent_rating_key', ''),
                      'grandparent_rating_key': session.get('grandparent_rating_key', ''),
                      'originally_available_at': session.get('originally_available_at', ''),
                      'added_at': session.get('added_at', ''),
                      'guid': session.get('guid', ''),
                      'view_offset': session.get('view_offset', ''),
                      'duration': session.get('duration', ''),
                      'video_decision': session.get('video_decision', ''),
                      'audio_decision': session.get('audio_decision', ''),
                      'transcode_decision': session.get('transcode_decision', ''),
                      'width': session.get('width', ''),
                      'height': session.get('height', ''),
                      'container': session.get('container', ''),
                      'bitrate': session.get('bitrate', ''),
                      'video_codec': session.get('video_codec', ''),
                      'video_bitrate': session.get('video_bitrate', ''),
                      'video_width': session.get('video_width', ''),
                      'video_height': session.get('video_height', ''),
                      'video_resolution': session.get('video_resolution', ''),
                      'video_framerate': session.get('video_framerate', ''),
                      'video_scan_type': session.get('video_scan_type', ''),
                      'video_full_resolution': session.get('video_full_resolution', ''),
                      'video_dynamic_range': session.get('video_dynamic_range', ''),
                      'aspect_ratio': session.get('aspect_ratio', ''),
                      'audio_codec': session.get('audio_codec', ''),
                      'audio_bitrate': session.get('audio_bitrate', ''),
                      'audio_channels': session.get('audio_channels', ''),
                      'audio_language': session.get('audio_language', ''),
                      'audio_language_code': session.get('audio_language_code', ''),
                      'subtitle_codec': session.get('subtitle_codec', ''),
                      'transcode_protocol': session.get('transcode_protocol', ''),
                      'transcode_container': session.get('transcode_container', ''),
                      'transcode_video_codec': session.get('transcode_video_codec', ''),
                      'transcode_audio_codec': session.get('transcode_audio_codec', ''),
                      'transcode_audio_channels': session.get('transcode_audio_channels', ''),
                      'transcode_width': session.get('stream_video_width', ''),
                      'transcode_height': session.get('stream_video_height', ''),
                      'transcode_hw_decoding': session.get('transcode_hw_decoding', ''),
                      'transcode_hw_encoding': session.get('transcode_hw_encoding', ''),
                      'synced_version': session.get('synced_version', ''),
                      'synced_version_profile': session.get('synced_version_profile', ''),
                      'optimized_version': session.get('optimized_version', ''),
                      'optimized_version_profile': session.get('optimized_version_profile', ''),
                      'optimized_version_title': session.get('optimized_version_title', ''),
                      'stream_bitrate': session.get('stream_bitrate', ''),
                      'stream_video_resolution': session.get('stream_video_resolution', ''),
                      'quality_profile': session.get('quality_profile', ''),
                      'stream_container_decision': session.get('stream_container_decision', ''),
                      'stream_container': session.get('stream_container', ''),
                      'stream_video_decision': session.get('stream_video_decision', ''),
                      'stream_video_codec': session.get('stream_video_codec', ''),
                      'stream_video_bitrate': session.get('stream_video_bitrate', ''),
                      'stream_video_width': session.get('stream_video_width', ''),
                      'stream_video_height': session.get('stream_video_height', ''),
                      'stream_video_framerate': session.get('stream_video_framerate', ''),
                      'stream_video_scan_type': session.get('stream_video_scan_type', ''),
                      'stream_video_full_resolution': session.get('stream_video_full_resolution', ''),
                      'stream_video_dynamic_range': session.get('stream_video_dynamic_range', ''),
                      'stream_audio_decision': session.get('stream_audio_decision', ''),
                      'stream_audio_codec': session.get('stream_audio_codec', ''),
                      'stream_audio_bitrate': session.get('stream_audio_bitrate', ''),
                      'stream_audio_channels': session.get('stream_audio_channels', ''),
                      'stream_audio_language': session.get('stream_audio_language', ''),
                      'stream_audio_language_code': session.get('stream_audio_language_code', ''),
                      'stream_subtitle_decision': session.get('stream_subtitle_decision', ''),
                      'stream_subtitle_codec': session.get('stream_subtitle_codec', ''),
                      'subtitles': session.get('subtitles', 0),
                      'live': session.get('live', 0),
                      'live_uuid': session.get('live_uuid', ''),
                      'secure': session.get('secure', None),
                      'relayed': session.get('relayed', 0),
                      'rating_key_websocket': session.get('rating_key_websocket', ''),
                      'raw_stream_info': json.dumps(session),
                      'channel_call_sign': session.get('channel_call_sign', ''),
                      'channel_identifier': session.get('channel_identifier', ''),
                      'channel_thumb': session.get('channel_thumb', ''),
                      'stopped': helpers.timestamp()
                      }

            keys = {'session_key': session.get('session_key', ''),
                    'rating_key': session.get('rating_key', '')}

            result = self.db.upsert('sessions', values, keys)

            if result == 'insert':
                # If it's our first write then time stamp it.
                started = helpers.timestamp()
                initial_stream = self.is_initial_stream(user_id=values['user_id'],
                                                        machine_id=values['machine_id'],
                                                        media_type=values['media_type'],
                                                        started=started)
                timestamp = {'started': started, 'initial_stream': initial_stream}
                self.db.upsert('sessions', timestamp, keys)

                # Check if any notification agents have notifications enabled
                if notify:
                    session.update(timestamp)
                    plexpy.NOTIFY_QUEUE.put({'stream_data': session.copy(), 'notify_action': 'on_play'})

                # Add Live TV library if it hasn't been added
                if values['live']:
                    libraries.add_live_tv_library()

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

            # Reload json from raw stream info
            if session.get('raw_stream_info'):
                raw_stream_info = json.loads(session['raw_stream_info'])
                # Don't overwrite id, session_key, stopped, view_offset
                raw_stream_info.pop('id', None)
                raw_stream_info.pop('session_key', None)
                raw_stream_info.pop('stopped', None)
                raw_stream_info.pop('view_offset', None)
                session.update(raw_stream_info)

            session = defaultdict(str, session)

            if is_import:
                if str(session['stopped']).isdigit():
                    stopped = int(session['stopped'])
                else:
                    stopped = helpers.timestamp()
            elif session['stopped']:
                stopped = int(session['stopped'])
            else:
                stopped = helpers.timestamp()
                self.set_session_state(session_key=session['session_key'],
                                       state='stopped',
                                       stopped=stopped)

            if not is_import:
                self.write_continued_session(user_id=session['user_id'],
                                             machine_id=session['machine_id'],
                                             media_type=session['media_type'],
                                             stopped=stopped)

            if str(session['rating_key']).isdigit() and session['media_type'] in ('movie', 'episode', 'track'):
                logging_enabled = True
            else:
                logger.debug("Tautulli ActivityProcessor :: Session %s ratingKey %s not logged. "
                             "Does not meet logging criteria. Media type is '%s'" %
                             (session['session_key'], session['rating_key'], session['media_type']))
                return session['id']

            real_play_time = stopped - helpers.cast_to_int(session['started']) - helpers.cast_to_int(session['paused_counter'])

            if not is_import and plexpy.CONFIG.LOGGING_IGNORE_INTERVAL:
                if (session['media_type'] == 'movie' or session['media_type'] == 'episode') and \
                        (real_play_time < int(plexpy.CONFIG.LOGGING_IGNORE_INTERVAL)):
                    logging_enabled = False
                    logger.debug("Tautulli ActivityProcessor :: Play duration for session %s ratingKey %s is %s secs "
                                 "which is less than %s seconds, so we're not logging it." %
                                 (session['session_key'], session['rating_key'], str(real_play_time),
                                  plexpy.CONFIG.LOGGING_IGNORE_INTERVAL))
            if not is_import and session['media_type'] == 'track':
                if real_play_time < 15 and helpers.cast_to_int(session['duration']) >= 30:
                    logging_enabled = False
                    logger.debug("Tautulli ActivityProcessor :: Play duration for session %s ratingKey %s is %s secs, "
                                 "looks like it was skipped so we're not logging it" %
                                 (session['session_key'], session['rating_key'], str(real_play_time)))
            elif is_import and import_ignore_interval:
                if (session['media_type'] == 'movie' or session['media_type'] == 'episode') and \
                        (real_play_time < int(import_ignore_interval)):
                    logging_enabled = False
                    logger.debug("Tautulli ActivityProcessor :: Play duration for ratingKey %s is %s secs which is less than %s "
                                 "seconds, so we're not logging it." %
                                 (session['rating_key'], str(real_play_time), import_ignore_interval))

            if not is_import and not user_details['keep_history']:
                logging_enabled = False
                logger.debug("Tautulli ActivityProcessor :: History logging for user '%s' is disabled." % user_details['username'])
            elif not is_import and not library_details['keep_history']:
                logging_enabled = False
                logger.debug("Tautulli ActivityProcessor :: History logging for library '%s' is disabled." % library_details['section_name'])

            if logging_enabled:

                # Fetch metadata first so we can return false if it fails
                if not is_import:
                    logger.debug("Tautulli ActivityProcessor :: Fetching metadata for item ratingKey %s" % session['rating_key'])
                    pms_connect = pmsconnect.PmsConnect()
                    if session['live']:
                        metadata = pms_connect.get_metadata_details(rating_key=str(session['rating_key']),
                                                                    cache_key=session['session_key'],
                                                                    return_cache=True)
                    else:
                        metadata = pms_connect.get_metadata_details(rating_key=str(session['rating_key']))
                    if not metadata:
                        return False
                    else:
                        media_info = {}
                        if 'media_info' in metadata and len(metadata['media_info']) > 0:
                            media_info = metadata['media_info'][0]
                else:
                    metadata = import_metadata
                    ## TODO: Fix media info from imports. Temporary media info from import session.
                    media_info = session

                # logger.debug("Tautulli ActivityProcessor :: Attempting to write sessionKey %s to session_history table..."
                #              % session['session_key'])
                keys = {'id': None}
                values = {'started': session['started'],
                          'stopped': stopped,
                          'rating_key': session['rating_key'],
                          'parent_rating_key': session['parent_rating_key'],
                          'grandparent_rating_key': session['grandparent_rating_key'],
                          'media_type': session['media_type'],
                          'user_id': session['user_id'],
                          'user': session['user'],
                          'ip_address': session['ip_address'],
                          'paused_counter': session['paused_counter'],
                          'player': session['player'],
                          'product': session['product'],
                          'product_version': session['product_version'],
                          'platform': session['platform'],
                          'platform_version': session['platform_version'],
                          'profile': session['profile'],
                          'machine_id': session['machine_id'],
                          'bandwidth': session['bandwidth'],
                          'location': session['location'],
                          'quality_profile': session['quality_profile'],
                          'view_offset': session['view_offset'],
                          'section_id': metadata['section_id'],
                          'secure': session['secure'],
                          'relayed': session['relayed']
                          }

                # logger.debug("Tautulli ActivityProcessor :: Writing sessionKey %s session_history transaction..."
                #              % session['session_key'])
                self.db.upsert(table_name='session_history', key_dict=keys, value_dict=values)

                # Get the last insert row id
                last_id = self.db.last_insert_id()
                new_session = prev_session = None
                prev_progress_percent = media_watched_percent = 0

                if session['live']:
                    # Check if we should group the session, select the last guid from the user
                    query = 'SELECT session_history.id, session_history_metadata.guid, session_history.reference_id ' \
                            'FROM session_history ' \
                            'JOIN session_history_metadata ON session_history.id == session_history_metadata.id ' \
                            'WHERE session_history.user_id = ? ORDER BY session_history.id DESC LIMIT 1 '

                    args = [session['user_id']]

                    result = self.db.select(query=query, args=args)

                    if len(result) > 0:
                        new_session = {'id': last_id,
                                       'guid': metadata['guid'],
                                       'reference_id': last_id}

                        prev_session = {'id': result[0]['id'],
                                        'guid': result[0]['guid'],
                                        'reference_id': result[0]['reference_id']}

                else:
                    # Check if we should group the session, select the last two rows from the user
                    query = 'SELECT id, rating_key, view_offset, reference_id FROM session_history ' \
                            'WHERE user_id = ? AND rating_key = ? ORDER BY id DESC LIMIT 2 '

                    args = [session['user_id'], session['rating_key']]

                    result = self.db.select(query=query, args=args)

                    if len(result) > 1:
                        new_session = {'id': result[0]['id'],
                                       'rating_key': result[0]['rating_key'],
                                       'view_offset': result[0]['view_offset'],
                                       'reference_id': result[0]['reference_id']}

                        prev_session = {'id': result[1]['id'],
                                        'rating_key': result[1]['rating_key'],
                                        'view_offset': result[1]['view_offset'],
                                        'reference_id': result[1]['reference_id']}

                        watched_percent = {'movie': plexpy.CONFIG.MOVIE_WATCHED_PERCENT,
                                           'episode': plexpy.CONFIG.TV_WATCHED_PERCENT,
                                           'track': plexpy.CONFIG.MUSIC_WATCHED_PERCENT
                                           }
                        prev_progress_percent = helpers.get_percent(prev_session['view_offset'], session['duration'])
                        media_watched_percent = watched_percent.get(session['media_type'], 0)

                query = 'UPDATE session_history SET reference_id = ? WHERE id = ? '

                # If previous session view offset less than watched percent,
                # and new session view offset is greater,
                # then set the reference_id to the previous row,
                # else set the reference_id to the new id
                if prev_session is None and new_session is None:
                    args = [last_id, last_id]
                elif prev_progress_percent < media_watched_percent and \
                        prev_session['view_offset'] <= new_session['view_offset'] or \
                        session['live'] and prev_session['guid'] == new_session['guid']:
                    args = [prev_session['reference_id'], new_session['id']]
                else:
                    args = [new_session['id'], new_session['id']]

                self.db.action(query=query, args=args)
                
                # logger.debug("Tautulli ActivityProcessor :: Successfully written history item, last id for session_history is %s"
                #              % last_id)

                # Write the session_history_media_info table

                # logger.debug("Tautulli ActivityProcessor :: Attempting to write to sessionKey %s session_history_media_info table..."
                #              % session['session_key'])
                keys = {'id': last_id}
                values = {'rating_key': session['rating_key'],
                          'video_decision': session['video_decision'],
                          'audio_decision': session['audio_decision'],
                          'transcode_decision': session['transcode_decision'],
                          'duration': session['duration'],
                          'container': session['container'],
                          'bitrate': session['bitrate'],
                          'width': session['width'],
                          'height': session['height'],
                          'video_bit_depth': session['video_bit_depth'],
                          'video_bitrate': session['video_bitrate'],
                          'video_codec': session['video_codec'],
                          'video_codec_level': session['video_codec_level'],
                          'video_width': session['video_width'],
                          'video_height': session['video_height'],
                          'video_resolution': session['video_resolution'],
                          'video_framerate': session['video_framerate'],
                          'video_scan_type': session['video_scan_type'],
                          'video_full_resolution': session['video_full_resolution'],
                          'video_dynamic_range': session['video_dynamic_range'],
                          'aspect_ratio': session['aspect_ratio'],
                          'audio_codec': session['audio_codec'],
                          'audio_bitrate': session['audio_bitrate'],
                          'audio_channels': session['audio_channels'],
                          'audio_language': session['audio_language'],
                          'audio_language_code': session['audio_language_code'],
                          'subtitle_codec': session['subtitle_codec'],
                          'transcode_protocol': session['transcode_protocol'],
                          'transcode_container': session['transcode_container'],
                          'transcode_video_codec': session['transcode_video_codec'],
                          'transcode_audio_codec': session['transcode_audio_codec'],
                          'transcode_audio_channels': session['transcode_audio_channels'],
                          'transcode_width': session['transcode_width'],
                          'transcode_height': session['transcode_height'],
                          'transcode_hw_requested': session['transcode_hw_requested'],
                          'transcode_hw_full_pipeline': session['transcode_hw_full_pipeline'],
                          'transcode_hw_decoding': session['transcode_hw_decoding'],
                          'transcode_hw_decode': session['transcode_hw_decode'],
                          'transcode_hw_decode_title': session['transcode_hw_decode_title'],
                          'transcode_hw_encoding': session['transcode_hw_encoding'],
                          'transcode_hw_encode': session['transcode_hw_encode'],
                          'transcode_hw_encode_title': session['transcode_hw_encode_title'],
                          'stream_container': session['stream_container'],
                          'stream_container_decision': session['stream_container_decision'],
                          'stream_bitrate': session['stream_bitrate'],
                          'stream_video_decision': session['stream_video_decision'],
                          'stream_video_bitrate': session['stream_video_bitrate'],
                          'stream_video_codec': session['stream_video_codec'],
                          'stream_video_codec_level': session['stream_video_codec_level'],
                          'stream_video_bit_depth': session['stream_video_bit_depth'],
                          'stream_video_height': session['stream_video_height'],
                          'stream_video_width': session['stream_video_width'],
                          'stream_video_resolution': session['stream_video_resolution'],
                          'stream_video_framerate': session['stream_video_framerate'],
                          'stream_video_scan_type': session['stream_video_scan_type'],
                          'stream_video_full_resolution': session['stream_video_full_resolution'],
                          'stream_video_dynamic_range': session['stream_video_dynamic_range'],
                          'stream_audio_decision': session['stream_audio_decision'],
                          'stream_audio_codec': session['stream_audio_codec'],
                          'stream_audio_bitrate': session['stream_audio_bitrate'],
                          'stream_audio_channels': session['stream_audio_channels'],
                          'stream_audio_language': session['stream_audio_language'],
                          'stream_audio_language_code': session['stream_audio_language_code'],
                          'stream_subtitle_decision': session['stream_subtitle_decision'],
                          'stream_subtitle_codec': session['stream_subtitle_codec'],
                          'stream_subtitle_container': session['stream_subtitle_container'],
                          'stream_subtitle_forced': session['stream_subtitle_forced'],
                          'subtitles': session['subtitles'],
                          'synced_version': session['synced_version'],
                          'synced_version_profile': session['synced_version_profile'],
                          'optimized_version': session['optimized_version'],
                          'optimized_version_profile': session['optimized_version_profile'],
                          'optimized_version_title': session['optimized_version_title']
                          }

                # logger.debug("Tautulli ActivityProcessor :: Writing sessionKey %s session_history_media_info transaction..."
                #              % session['session_key'])
                self.db.upsert(table_name='session_history_media_info', key_dict=keys, value_dict=values)

                # Write the session_history_metadata table
                directors = ";".join(metadata['directors'])
                writers = ";".join(metadata['writers'])
                actors = ";".join(metadata['actors'])
                genres = ";".join(metadata['genres'])
                labels = ";".join(metadata['labels'])

                # logger.debug("Tautulli ActivityProcessor :: Attempting to write to sessionKey %s session_history_metadata table..."
                #              % session['session_key'])
                keys = {'id': last_id}
                values = {'rating_key': session['rating_key'],
                          'parent_rating_key': session['parent_rating_key'],
                          'grandparent_rating_key': session['grandparent_rating_key'],
                          'title': session['title'],
                          'parent_title': session['parent_title'],
                          'grandparent_title': session['grandparent_title'],
                          'original_title': session['original_title'],
                          'full_title': session['full_title'],
                          'media_index': metadata['media_index'],
                          'parent_media_index': metadata['parent_media_index'],
                          'thumb': metadata['thumb'],
                          'parent_thumb': metadata['parent_thumb'],
                          'grandparent_thumb': metadata['grandparent_thumb'],
                          'art': metadata['art'],
                          'media_type': session['media_type'],
                          'year': metadata['year'],
                          'originally_available_at': metadata['originally_available_at'],
                          'added_at': metadata['added_at'],
                          'updated_at': metadata['updated_at'],
                          'last_viewed_at': metadata['last_viewed_at'],
                          'content_rating': metadata['content_rating'],
                          'summary': metadata['summary'],
                          'tagline': metadata['tagline'],
                          'rating': metadata['rating'],
                          'duration': metadata['duration'],
                          'guid': metadata['guid'],
                          'directors': directors,
                          'writers': writers,
                          'actors': actors,
                          'genres': genres,
                          'studio': metadata['studio'],
                          'labels': labels,
                          'live': session['live'],
                          'channel_call_sign': media_info.get('channel_call_sign', ''),
                          'channel_identifier': media_info.get('channel_identifier', ''),
                          'channel_thumb': media_info.get('channel_thumb', '')
                          }

                # logger.debug("Tautulli ActivityProcessor :: Writing sessionKey %s session_history_metadata transaction..."
                #              % session['session_key'])
                self.db.upsert(table_name='session_history_metadata', key_dict=keys, value_dict=values)

            # Return the session row id when the session is successfully written to the database
            return session['id']

    def get_sessions(self, user_id=None, ip_address=None):
        query = 'SELECT * FROM sessions'
        args = []

        if str(user_id).isdigit():
            ip = ' GROUP BY ip_address' if ip_address else ''
            query += ' WHERE user_id = ?' + ip
            args.append(user_id)

        sessions = self.db.select(query, args)
        return sessions

    def get_session_by_key(self, session_key=None):
        if str(session_key).isdigit():
            session = self.db.select_single('SELECT * FROM sessions '
                                            'WHERE session_key = ? ',
                                            args=[session_key])
            if session:
                return session

        return None

    def get_session_by_id(self, session_id=None):
        if session_id:
            session = self.db.select_single('SELECT * FROM sessions '
                                            'WHERE session_id = ? ',
                                            args=[session_id])
            if session:
                return session

        return None

    def set_session_state(self, session_key=None, state=None, **kwargs):
        if str(session_key).isdigit():
            values = {}

            if state:
                values['state'] = state

            for k, v in kwargs.items():
                values[k] = v

            keys = {'session_key': session_key}
            result = self.db.upsert('sessions', values, keys)

            return result

        return None

    def delete_session(self, session_key=None, row_id=None):
        if str(session_key).isdigit():
            self.db.action('DELETE FROM sessions WHERE session_key = ?', [session_key])
        elif str(row_id).isdigit():
            self.db.action('DELETE FROM sessions WHERE id = ?', [row_id])

    def set_session_last_paused(self, session_key=None, timestamp=None):
        if str(session_key).isdigit():
            result = self.db.select('SELECT last_paused, paused_counter '
                                    'FROM sessions '
                                    'WHERE session_key = ?', args=[session_key])

            paused_counter = None
            for session in result:
                if session['last_paused']:
                    paused_offset = helpers.timestamp() - int(session['last_paused'])
                    if session['paused_counter']:
                        paused_counter = int(session['paused_counter']) + int(paused_offset)
                    else:
                        paused_counter = int(paused_offset)

            values = {'last_paused': timestamp}

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

    def set_temp_stopped(self):
        stopped_time = helpers.timestamp()
        self.db.action('UPDATE sessions SET stopped = ?', [stopped_time])

    def increment_write_attempts(self, session_key=None):
        if str(session_key).isdigit():
            session = self.get_session_by_key(session_key=session_key)
            self.db.action('UPDATE sessions SET write_attempts = ? WHERE session_key = ?',
                           [session['write_attempts'] + 1, session_key])

    def set_watched(self, session_key=None):
        self.db.action('UPDATE sessions SET watched = ?'
                       'WHERE session_key = ?',
                       [1, session_key])

    def write_continued_session(self, user_id=None, machine_id=None, media_type=None, stopped=None):
        keys = {'user_id': user_id, 'machine_id': machine_id, 'media_type': media_type}
        values = {'stopped': stopped}
        self.db.upsert(table_name='sessions_continued', key_dict=keys, value_dict=values)

    def is_initial_stream(self, user_id=None, machine_id=None, media_type=None, started=None):
        last_session = self.db.select_single('SELECT stopped '
                                             'FROM sessions_continued '
                                             'WHERE user_id = ? AND machine_id = ? AND media_type = ? '
                                             'ORDER BY stopped DESC',
                                             [user_id, machine_id, media_type])
        return int(started - last_session.get('stopped', 0) >= plexpy.CONFIG.NOTIFY_CONTINUED_SESSION_THRESHOLD)
