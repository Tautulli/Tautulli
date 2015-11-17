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

from plexpy import logger, pmsconnect, notification_handler, database, helpers, activity_processor

import threading
import plexpy
import time

monitor_lock = threading.Lock()
ping_count = 0


def check_active_sessions(ws_request=False):

    with monitor_lock:
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()
        monitor_db = database.MonitorDatabase()
        monitor_process = activity_processor.ActivityProcessor()
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
                                           'transcode_audio_channels, transcode_width, transcode_height, '
                                           'paused_counter, last_paused '
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

                            if stream['state'] == 'paused' and not ws_request:
                                # The stream is still paused so we need to increment the paused_counter
                                # Using the set config parameter as the interval, probably not the most accurate but
                                # it will have to do for now. If it's a websocket request don't use this method.
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
                            if session['view_offset'] and session['duration'] and session['state'] != 'buffering':
                                if helpers.get_percent(session['view_offset'],
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
                    monitor_process.write_session_history(session=stream)

            # Process the newly received session data
            for session in media_container:
                monitor_process.write_session(session)
        else:
            logger.debug(u"PlexPy Monitor :: Unable to read session list.")
            

def check_recently_added():

    with monitor_lock:
        # add delay to allow for metadata processing
        delay = plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY
        time_threshold = int(time.time()) - delay
        time_interval = plexpy.CONFIG.MONITORING_INTERVAL

        pms_connect = pmsconnect.PmsConnect()
        recently_added_list = pms_connect.get_recently_added_details(count='10')

        if recently_added_list:
            recently_added = recently_added_list['recently_added']

            for item in recently_added:
                if item['media_type'] == 'movie':
                    metadata_list = pms_connect.get_metadata_details(item['rating_key'])
                    if metadata_list:
                        metadata = [metadata_list['metadata']]
                    else:
                        logger.error(u"PlexPy Monitor :: Unable to retrieve metadata for rating_key %s" \
                                        % str(item['rating_key']))

                else:
                    metadata_list = pms_connect.get_metadata_children_details(item['rating_key'])
                    if metadata_list:
                        metadata = metadata_list['metadata']
                    else:
                        logger.error(u"PlexPy Monitor :: Unable to retrieve children metadata for rating_key %s" \
                                        % str(item['rating_key']))

                if metadata:
                    if not plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_GRANDPARENT:
                        for item in metadata:
                            if 0 < int(item['added_at']) - time_threshold <= time_interval:
                                # Fire off notifications
                                threading.Thread(target=notification_handler.notify_timeline,
                                                 kwargs=dict(timeline_data=item, notify_action='created')).start()
                    
                    else:
                        item = max(metadata, key=lambda x:x['added_at'])

                        if 0 < int(item['added_at']) - time_threshold <= time_interval:
                            if item['media_type'] == 'episode' or item['media_type'] == 'track':
                                metadata_list = pms_connect.get_metadata_details(item['grandparent_rating_key'])

                                if metadata_list:
                                    item = metadata_list['metadata']
                                else:
                                    logger.error(u"PlexPy Monitor :: Unable to retrieve grandparent metadata for grandparent_rating_key %s" \
                                                    % str(item['rating_key']))

                            # Fire off notifications
                            threading.Thread(target=notification_handler.notify_timeline,
                                             kwargs=dict(timeline_data=item, notify_action='created')).start()


def check_server_response():

    with monitor_lock:
        pms_connect = pmsconnect.PmsConnect()
        response = pms_connect.get_server_response()
        global ping_count
        
        if not response:
            ping_count += 1
            logger.warn(u"PlexPy Monitor :: Unable to get a response from the server, ping attempt %s." % str(ping_count))

            if ping_count == 3:
                # Fire off notifications
                threading.Thread(target=notification_handler.notify_timeline,
                                 kwargs=dict(notify_action='down')).start()
        else:
            ping_count = 0