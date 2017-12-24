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

import threading
import time

import plexpy
import activity_processor
import database
import helpers
import libraries
import logger
import notification_handler
import notifiers
import plextv
import pmsconnect
import web_socket


monitor_lock = threading.Lock()
ext_ping_count = 0
int_ping_count = 0


def check_active_sessions(ws_request=False):

    with monitor_lock:
        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()
        monitor_db = database.MonitorDatabase()
        monitor_process = activity_processor.ActivityProcessor()
        logger.debug(u"Tautulli Monitor :: Checking for active streams.")

        if session_list:
            media_container = session_list['sessions']

            # Check our temp table for what we must do with the new streams
            db_streams = monitor_process.get_sessions()
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
                                    logger.debug(u"Tautulli Monitor :: Session %s paused." % stream['session_key'])

                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_pause'})

                                if session['state'] == 'playing' and stream['state'] == 'paused':
                                    logger.debug(u"Tautulli Monitor :: Session %s resumed." % stream['session_key'])

                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_resume'})

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
                                        logger.info(u"Tautulli Monitor :: User '%s' has triggered a buffer warning."
                                                    % stream['user'])
                                        # Set the buffer trigger time
                                        monitor_db.action('UPDATE sessions '
                                                          'SET buffer_last_triggered = strftime("%s","now") '
                                                          'WHERE session_key = ? AND rating_key = ?',
                                                          [stream['session_key'], stream['rating_key']])

                                        plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_buffer'})

                                    else:
                                        # Subsequent buffer notifications after wait time
                                        if int(time.time()) > buffer_values[0]['buffer_last_triggered'] + \
                                                plexpy.CONFIG.BUFFER_WAIT:
                                            logger.info(u"Tautulli Monitor :: User '%s' has triggered multiple buffer warnings."
                                                    % stream['user'])
                                            # Set the buffer trigger time
                                            monitor_db.action('UPDATE sessions '
                                                              'SET buffer_last_triggered = strftime("%s","now") '
                                                              'WHERE session_key = ? AND rating_key = ?',
                                                              [stream['session_key'], stream['rating_key']])

                                            plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_buffer'})

                                logger.debug(u"Tautulli Monitor :: Session %s is buffering. Count is now %s. Last triggered %s."
                                             % (stream['session_key'],
                                                buffer_values[0]['buffer_count'],
                                                buffer_values[0]['buffer_last_triggered']))

                            # Check if the user has reached the offset in the media we defined as the "watched" percent
                            # Don't trigger if state is buffer as some clients push the progress to the end when
                            # buffering on start.
                            if session['state'] != 'buffering':
                                progress_percent = helpers.get_percent(session['view_offset'], session['duration'])
                                notify_states = notification_handler.get_notify_state(session=session)
                                if (session['media_type'] == 'movie' and progress_percent >= plexpy.CONFIG.MOVIE_WATCHED_PERCENT or
                                    session['media_type'] == 'episode' and progress_percent >= plexpy.CONFIG.TV_WATCHED_PERCENT or
                                    session['media_type'] == 'track' and progress_percent >= plexpy.CONFIG.MUSIC_WATCHED_PERCENT) \
                                    and not any(d['notify_action'] == 'on_watched' for d in notify_states):
                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_watched'})

                else:
                    # The user has stopped playing a stream
                    if stream['state'] != 'stopped':
                        logger.debug(u"Tautulli Monitor :: Session %s stopped." % stream['session_key'])

                        if not stream['stopped']:
                            # Set the stream stop time
                            stream['stopped'] = int(time.time())
                            monitor_db.action('UPDATE sessions SET stopped = ?, state = ? '
                                              'WHERE session_key = ? AND rating_key = ?',
                                              [stream['stopped'], 'stopped', stream['session_key'], stream['rating_key']])

                        progress_percent = helpers.get_percent(stream['view_offset'], stream['duration'])
                        notify_states = notification_handler.get_notify_state(session=stream)
                        if (stream['media_type'] == 'movie' and progress_percent >= plexpy.CONFIG.MOVIE_WATCHED_PERCENT or
                            stream['media_type'] == 'episode' and progress_percent >= plexpy.CONFIG.TV_WATCHED_PERCENT or
                            stream['media_type'] == 'track' and progress_percent >= plexpy.CONFIG.MUSIC_WATCHED_PERCENT) \
                            and not any(d['notify_action'] == 'on_watched' for d in notify_states):
                            plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_watched'})

                        plexpy.NOTIFY_QUEUE.put({'stream_data': stream, 'notify_action': 'on_stop'})

                    # Write the item history on playback stop
                    success = monitor_process.write_session_history(session=stream)
                    
                    if success:
                        # If session is written to the databaase successfully, remove the session from the session table
                        logger.debug(u"Tautulli Monitor :: Removing sessionKey %s ratingKey %s from session queue"
                                     % (stream['session_key'], stream['rating_key']))
                        monitor_db.action('DELETE FROM sessions WHERE session_key = ? AND rating_key = ?',
                                          [stream['session_key'], stream['rating_key']])
                    else:
                        stream['write_attempts'] += 1

                        if stream['write_attempts'] < plexpy.CONFIG.SESSION_DB_WRITE_ATTEMPTS:
                            logger.warn(u"Tautulli Monitor :: Failed to write sessionKey %s ratingKey %s to the database. " \
                                        "Will try again on the next pass. Write attempt %s."
                                        % (stream['session_key'], stream['rating_key'], str(stream['write_attempts'])))
                            monitor_db.action('UPDATE sessions SET write_attempts = ? '
                                              'WHERE session_key = ? AND rating_key = ?',
                                              [stream['write_attempts'], stream['session_key'], stream['rating_key']])
                        else:
                            logger.warn(u"Tautulli Monitor :: Failed to write sessionKey %s ratingKey %s to the database. " \
                                        "Removing session from the database. Write attempt %s."
                                        % (stream['session_key'], stream['rating_key'], str(stream['write_attempts'])))
                            logger.debug(u"Tautulli Monitor :: Removing sessionKey %s ratingKey %s from session queue"
                                         % (stream['session_key'], stream['rating_key']))
                            monitor_db.action('DELETE FROM sessions WHERE session_key = ? AND rating_key = ?',
                                              [stream['session_key'], stream['rating_key']])


            # Process the newly received session data
            for session in media_container:
                new_session = monitor_process.write_session(session)

                if new_session:
                    logger.debug(u"Tautulli Monitor :: Session %s started by user %s with ratingKey %s."
                                 % (session['session_key'], session['user_id'], session['rating_key']))

        else:
            logger.debug(u"Tautulli Monitor :: Unable to read session list.")


def check_recently_added():

    with monitor_lock:
        # add delay to allow for metadata processing
        delay = plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY
        time_threshold = int(time.time()) - delay
        time_interval = plexpy.CONFIG.MONITORING_INTERVAL

        pms_connect = pmsconnect.PmsConnect()
        recently_added_list = pms_connect.get_recently_added_details(count='10')

        library_data = libraries.Libraries()
        if recently_added_list:
            recently_added = recently_added_list['recently_added']

            for item in recently_added:
                library_details = library_data.get_details(section_id=item['section_id'])

                if not library_details['do_notify_created']:
                    continue

                metadata = []
                
                if 0 < time_threshold - int(item['added_at']) <= time_interval:
                    if item['media_type'] == 'movie':
                        metadata = pms_connect.get_metadata_details(item['rating_key'])
                        if metadata:
                            metadata = [metadata]
                        else:
                            logger.error(u"Tautulli Monitor :: Unable to retrieve metadata for rating_key %s" \
                                         % str(item['rating_key']))

                    else:
                        metadata = pms_connect.get_metadata_children_details(item['rating_key'])
                        if not metadata:
                            logger.error(u"Tautulli Monitor :: Unable to retrieve children metadata for rating_key %s" \
                                         % str(item['rating_key']))

                if metadata:

                    if not plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED:
                        for item in metadata:

                            library_details = library_data.get_details(section_id=item['section_id'])

                            if 0 < time_threshold - int(item['added_at']) <= time_interval:
                                logger.debug(u"Tautulli Monitor :: Library item %s added to Plex." % str(item['rating_key']))

                                plexpy.NOTIFY_QUEUE.put({'timeline_data': item, 'notify_action': 'on_created'})
                    
                    else:
                        item = max(metadata, key=lambda x:x['added_at'])

                        if 0 < time_threshold - int(item['added_at']) <= time_interval:
                            if item['media_type'] == 'episode' or item['media_type'] == 'track':
                                metadata = pms_connect.get_metadata_details(item['grandparent_rating_key'])

                                if metadata:
                                    item = metadata
                                else:
                                    logger.error(u"Tautulli Monitor :: Unable to retrieve grandparent metadata for grandparent_rating_key %s" \
                                                 % str(item['rating_key']))

                            logger.debug(u"Tautulli Monitor :: Library item %s added to Plex." % str(item['rating_key']))

                            # Check if any notification agents have notifications enabled
                            plexpy.NOTIFY_QUEUE.put({'timeline_data': item, 'notify_action': 'on_created'})


def check_server_response():
    logger.info(u"Tautulli Monitor :: Attempting to reconnect Plex server...")
    try:
        web_socket.start_thread()
    except:
        logger.warn(u"Websocket :: Unable to open connection.")


def check_server_access():
    with monitor_lock:
        pms_connect = pmsconnect.PmsConnect()
        server_response = pms_connect.get_server_response()

        global ext_ping_count

        # Check for remote access
        if server_response:

            mapping_state = server_response['mapping_state']
            mapping_error = server_response['mapping_error']

            # Check if the port is mapped
            if not mapping_state == 'mapped':
                ext_ping_count += 1
                logger.warn(u"Tautulli Monitor :: Plex remote access port not mapped, ping attempt %s." \
                            % str(ext_ping_count))
            # Check if the port is open
            elif mapping_error == 'unreachable':
                ext_ping_count += 1
                logger.warn(u"Tautulli Monitor :: Plex remote access port mapped, but mapping failed, ping attempt %s." \
                            % str(ext_ping_count))
            # Reset external ping counter
            else:
                if ext_ping_count >= plexpy.CONFIG.REMOTE_ACCESS_PING_THRESHOLD:
                    logger.info(u"Tautulli Monitor :: Plex remote access is back up.")

                    plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_extup'})

                ext_ping_count = 0

        if ext_ping_count == plexpy.CONFIG.REMOTE_ACCESS_PING_THRESHOLD:
            plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_extdown'})


def check_server_updates():

    with monitor_lock:
        logger.info(u"Tautulli Monitor :: Checking for PMS updates...")

        plex_tv = plextv.PlexTV()
        download_info = plex_tv.get_plex_downloads()

        if download_info:
            logger.info(u"Tautulli Monitor :: Current PMS version: %s", plexpy.CONFIG.PMS_VERSION)

            if download_info['update_available']:
                logger.info(u"Tautulli Monitor :: PMS update available version: %s", download_info['version'])

                plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_pmsupdate', 'pms_download_info': download_info})

            else:
                logger.info(u"Tautulli Monitor :: No PMS update available.")