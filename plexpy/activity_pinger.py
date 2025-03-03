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

import plexpy
from plexpy import activity_handler
from plexpy import activity_processor
from plexpy import database
from plexpy import helpers
from plexpy import logger
from plexpy import notification_handler
from plexpy import plextv
from plexpy import pmsconnect
from plexpy import web_socket


monitor_lock = threading.Lock()
ext_ping_count = 0
ext_ping_error = None
int_ping_count = 0


def check_active_sessions(ws_request=False):

    with monitor_lock:
        monitor_db = database.MonitorDatabase()
        monitor_process = activity_processor.ActivityProcessor()
        db_streams = monitor_process.get_sessions()

        # Clear the metadata cache
        for stream in db_streams:
            activity_handler.delete_metadata_cache(stream['session_key'])

        pms_connect = pmsconnect.PmsConnect()
        session_list = pms_connect.get_current_activity()

        logger.debug("Tautulli Monitor :: Checking for active streams.")

        if session_list:
            media_container = session_list['sessions']

            # Check our temp table for what we must do with the new streams
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
                                    logger.debug("Tautulli Monitor :: Session %s paused." % stream['session_key'])

                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_pause'})

                                if session['state'] == 'playing' and stream['state'] == 'paused':
                                    logger.debug("Tautulli Monitor :: Session %s resumed." % stream['session_key'])

                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_resume'})

                                if session['state'] == 'error':
                                    logger.debug("Tautulli Monitor :: Session %s encountered an error." % stream['session_key'])

                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_error'})

                            if stream['state'] == 'paused' and not ws_request:
                                # The stream is still paused so we need to increment the paused_counter
                                # Using the set config parameter as the interval, probably not the most accurate but
                                # it will have to do for now. If it's a websocket request don't use this method.
                                paused_counter = int(stream['paused_counter']) + plexpy.CONFIG.MONITORING_INTERVAL
                                monitor_db.action("UPDATE sessions SET paused_counter = ? "
                                                  "WHERE session_key = ? AND rating_key = ?",
                                                  [paused_counter, stream['session_key'], stream['rating_key']])

                            if session['state'] == 'buffering' and plexpy.CONFIG.BUFFER_THRESHOLD > 0:
                                # The stream is buffering so we need to increment the buffer_count
                                # We're going just increment on every monitor ping,
                                # would be difficult to keep track otherwise
                                monitor_db.action("UPDATE sessions SET buffer_count = buffer_count + 1 "
                                                  "WHERE session_key = ? AND rating_key = ?",
                                                  [stream['session_key'], stream['rating_key']])

                                # Check the current buffer count and last buffer to determine if we should notify
                                buffer_values = monitor_db.select("SELECT buffer_count, buffer_last_triggered "
                                                                  "FROM sessions "
                                                                  "WHERE session_key = ? AND rating_key = ?",
                                                                  [stream['session_key'], stream['rating_key']])

                                if buffer_values[0]['buffer_count'] >= plexpy.CONFIG.BUFFER_THRESHOLD:
                                    # Push any notifications -
                                    # Push it on it's own thread so we don't hold up our db actions
                                    # Our first buffer notification
                                    if buffer_values[0]['buffer_count'] == plexpy.CONFIG.BUFFER_THRESHOLD:
                                        logger.info("Tautulli Monitor :: User '%s' has triggered a buffer warning."
                                                    % stream['user'])
                                        # Set the buffer trigger time
                                        monitor_db.action("UPDATE sessions "
                                                          "SET buffer_last_triggered = strftime('%s', 'now') "
                                                          "WHERE session_key = ? AND rating_key = ?",
                                                          [stream['session_key'], stream['rating_key']])

                                        plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_buffer'})

                                    else:
                                        # Subsequent buffer notifications after wait time
                                        if helpers.timestamp() > buffer_values[0]['buffer_last_triggered'] + \
                                                plexpy.CONFIG.BUFFER_WAIT:
                                            logger.info("Tautulli Monitor :: User '%s' has triggered multiple buffer warnings."
                                                    % stream['user'])
                                            # Set the buffer trigger time
                                            monitor_db.action("UPDATE sessions "
                                                              "SET buffer_last_triggered = strftime('%s', 'now') "
                                                              "WHERE session_key = ? AND rating_key = ?",
                                                              [stream['session_key'], stream['rating_key']])

                                            plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_buffer'})

                                logger.debug("Tautulli Monitor :: Session %s is buffering. Count is now %s. Last triggered %s."
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
                                    plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_watched'})

                else:
                    # The user has stopped playing a stream
                    if stream['state'] != 'stopped':
                        logger.debug("Tautulli Monitor :: Session %s stopped." % stream['session_key'])

                        if not stream['stopped']:
                            # Set the stream stop time
                            stream['stopped'] = helpers.timestamp()
                            monitor_db.action("UPDATE sessions SET stopped = ?, state = ? "
                                              "WHERE session_key = ? AND rating_key = ?",
                                              [stream['stopped'], 'stopped', stream['session_key'], stream['rating_key']])

                        progress_percent = helpers.get_percent(stream['view_offset'], stream['duration'])
                        notify_states = notification_handler.get_notify_state(session=stream)
                        if (stream['media_type'] == 'movie' and progress_percent >= plexpy.CONFIG.MOVIE_WATCHED_PERCENT or
                            stream['media_type'] == 'episode' and progress_percent >= plexpy.CONFIG.TV_WATCHED_PERCENT or
                            stream['media_type'] == 'track' and progress_percent >= plexpy.CONFIG.MUSIC_WATCHED_PERCENT) \
                            and not any(d['notify_action'] == 'on_watched' for d in notify_states):
                            plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_watched'})

                        plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_stop'})

                    # Write the item history on playback stop
                    row_id = monitor_process.write_session_history(session=stream)

                    if row_id:
                        # If session is written to the database successfully, remove the session from the session table
                        logger.debug("Tautulli Monitor :: Removing sessionKey %s ratingKey %s from session queue"
                                     % (stream['session_key'], stream['rating_key']))
                        monitor_process.delete_session(row_id=row_id)
                    else:
                        stream['write_attempts'] += 1

                        if stream['write_attempts'] < plexpy.CONFIG.SESSION_DB_WRITE_ATTEMPTS:
                            logger.warn("Tautulli Monitor :: Failed to write sessionKey %s ratingKey %s to the database. " \
                                        "Will try again on the next pass. Write attempt %s."
                                        % (stream['session_key'], stream['rating_key'], str(stream['write_attempts'])))
                            monitor_process.increment_write_attempts(session_key=stream['session_key'])
                        else:
                            logger.warn("Tautulli Monitor :: Failed to write sessionKey %s ratingKey %s to the database. " \
                                        "Removing session from the database. Write attempt %s."
                                        % (stream['session_key'], stream['rating_key'], str(stream['write_attempts'])))
                            logger.debug("Tautulli Monitor :: Removing sessionKey %s ratingKey %s from session queue"
                                         % (stream['session_key'], stream['rating_key']))
                            monitor_process.delete_session(session_key=stream['session_key'])

            # Process the newly received session data
            for session in media_container:
                new_session = monitor_process.write_session(session)

                if new_session:
                    logger.debug("Tautulli Monitor :: Session %s started by user %s (%s) with ratingKey %s (%s)%s."
                                 % (str(session['session_key']), str(session['user_id']), session['username'],
                                    str(session['rating_key']), session['full_title'], '[Live TV]' if session['live'] else ''))

        else:
            logger.debug("Tautulli Monitor :: Unable to read session list.")


def connect_server(log=True, startup=False):
    if plexpy.CONFIG.PMS_IS_CLOUD:
        if log:
            logger.info("Tautulli Monitor :: Checking for Plex Cloud server status...")

        plex_tv = plextv.PlexTV()
        status = plex_tv.get_cloud_server_status()

        if status is True:
            logger.info("Tautulli Monitor :: Plex Cloud server is active.")
        elif status is False:
            if log:
                logger.info("Tautulli Monitor :: Plex Cloud server is sleeping.")
        else:
            if log:
                logger.error("Tautulli Monitor :: Failed to retrieve Plex Cloud server status.")

        if not status and startup:
            web_socket.on_disconnect()

    else:
        status = True

    if status:
        if log and not startup:
            logger.info("Tautulli Monitor :: Attempting to reconnect Plex server...")

        try:
            web_socket.start_thread()
        except Exception as e:
            logger.error("Websocket :: Unable to open connection: %s." % e)


def check_server_updates():

    with monitor_lock:
        logger.info("Tautulli Monitor :: Checking for PMS updates...")

        plex_tv = plextv.PlexTV()
        download_info = plex_tv.get_plex_update()

        if download_info:
            logger.info("Tautulli Monitor :: Current PMS version: %s", plexpy.CONFIG.PMS_VERSION)

            if download_info['update_available']:
                logger.info("Tautulli Monitor :: PMS update available version: %s", download_info['version'])

                plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_pmsupdate', 'pms_download_info': download_info})

            else:
                logger.info("Tautulli Monitor :: No PMS update available.")
