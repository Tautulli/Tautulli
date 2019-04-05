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

import time
import requests
import socket

import plexpy
import activity_processor
import database
import helpers
import libraries
import logger
import notification_handler
from .config import bool_int


def check_active_sessions(server=None, ws_request=False):
    if server.WS and server.WS.WS_CONNECTION and server.WS.WS_CONNECTION.connected:
        with server.monitor_lock:
            session_list = server.PMSCONNECTION.get_current_activity()
            monitor_db = database.MonitorDatabase()
            monitor_process = activity_processor.ActivityProcessor(server)
            logger.debug(u"Tautulli Monitor :: %s: Checking for active streams." % server.CONFIG.PMS_NAME)

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
                                        logger.debug(u"Tautulli Monitor :: %s: Session %s paused."
                                                     % (server.CONFIG.PMS_NAME, stream['session_key']))

                                        plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_pause'})

                                    if session['state'] == 'playing' and stream['state'] == 'paused':
                                        logger.debug(u"Tautulli Monitor :: %s: Session %s resumed."
                                                     % (server.CONFIG.PMS_NAME, stream['session_key']))

                                        plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_resume'})

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
                                            logger.info(u"Tautulli Monitor :: %s: User '%s' has triggered a buffer warning."
                                                        % (server.CONFIG.PMS_NAME, stream['user']))
                                            # Set the buffer trigger time
                                            monitor_db.action('UPDATE sessions '
                                                              'SET buffer_last_triggered = strftime("%s","now") '
                                                              'WHERE session_key = ? AND rating_key = ?',
                                                              [stream['session_key'], stream['rating_key']])

                                            plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_buffer'})

                                        else:
                                            # Subsequent buffer notifications after wait time
                                            if int(time.time()) > buffer_values[0]['buffer_last_triggered'] + \
                                                    plexpy.CONFIG.BUFFER_WAIT:
                                                logger.info(u"Tautulli Monitor :: %s: User '%s' has triggered multiple buffer warnings."
                                                        % (server.CONFIG.PMS_NAME, stream['user']))
                                                # Set the buffer trigger time
                                                monitor_db.action('UPDATE sessions '
                                                                  'SET buffer_last_triggered = strftime("%s","now") '
                                                                  'WHERE session_key = ? AND rating_key = ?',
                                                                  [stream['session_key'], stream['rating_key']])

                                                plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_buffer'})

                                    logger.debug(u"Tautulli Monitor :: %s: Session %s is buffering. Count is now %s. Last triggered %s."
                                                 % (server.CONFIG.PMS_NAME, stream['session_key'],
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
                            logger.debug(u"Tautulli Monitor :: %s: Session %s stopped."
                                         % (server.CONFIG.PMS_NAME, stream['session_key']))

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
                                plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_watched'})

                            plexpy.NOTIFY_QUEUE.put({'stream_data': stream.copy(), 'notify_action': 'on_stop'})

                        # Write the item history on playback stop
                        row_id = monitor_process.write_session_history(session=stream)

                        if row_id:
                            # If session is written to the databaase successfully, remove the session from the session table
                            logger.debug(u"Tautulli Monitor :: %s: Removing sessionKey %s ratingKey %s from session queue"
                                         % (server.CONFIG.PMS_NAME, stream['session_key'], stream['rating_key']))
                            monitor_process.delete_session(row_id=row_id)
                        else:
                            stream['write_attempts'] += 1

                            if stream['write_attempts'] < plexpy.CONFIG.SESSION_DB_WRITE_ATTEMPTS:
                                logger.warn(u"Tautulli Monitor :: %s: Failed to write sessionKey %s ratingKey %s to the database. " \
                                            "Will try again on the next pass. Write attempt %s."
                                            % (server.CONFIG.PMS_NAME, stream['session_key'], stream['rating_key'],
                                               str(stream['write_attempts'])))
                                monitor_process.increment_write_attempts(session_key=stream['session_key'])
                            else:
                                logger.warn(u"Tautulli Monitor :: %s: Failed to write sessionKey %s ratingKey %s to the database. " \
                                            "Removing session from the database. Write attempt %s."
                                            % (server.CONFIG.PMS_NAME, stream['session_key'],
                                               stream['rating_key'], str(stream['write_attempts'])))
                                logger.debug(u"Tautulli Monitor :: %s: Removing sessionKey %s ratingKey %s from session queue"
                                             % (server.CONFIG.PMS_NAME, stream['session_key'], stream['rating_key']))
                                monitor_process.delete_session(session_key=stream['session_key'])

                # Process the newly received session data
                for session in media_container:
                    new_session = monitor_process.write_session(session)

                    if new_session:
                        logger.debug(u"Tautulli Monitor :: %s: Session %s started by user %s with ratingKey %s."
                                     % (server.CONFIG.PMS_NAME, session['session_key'], session['user_id'], session['rating_key']))

            else:
                logger.debug(u"Tautulli Monitor :: %s: Unable to read session list." % server.CONFIG.PMS_NAME)


def check_recently_added(server=None):
    if server.WS_CONNECTED and server.WS and server.WS.WS_CONNECTION and server.WS.WS_CONNECTION.connected:
        with server.monitor_lock:
            # add delay to allow for metadata processing
            delay = plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY
            time_threshold = int(time.time()) - delay
            time_interval = plexpy.CONFIG.MONITORING_INTERVAL

            recently_added_list = server.PMSCONNECTION.get_recently_added_details(count='10')

            library_data = libraries.Libraries()

            if recently_added_list:
                recently_added = recently_added_list['recently_added']
                monitor_db = database.MonitorDatabase()
                query = 'SELECT id FROM library_sections WHERE server_id = ? AND section_id = ?'

                for item in recently_added:
                    result = monitor_db.select(query, args=[item['server_id'], item['section_id']])
                    library_details = library_data.get_details(result[0]['id'])

                    if not library_details['do_notify_created']:
                        continue

                    metadata = []

                    if 0 < time_threshold - int(item['added_at']) <= time_interval:
                        if item['media_type'] == 'movie':
                            metadata = server.PMSCONNECTION.get_metadata_details(item['rating_key'])
                            if metadata:
                                metadata = [metadata]
                            else:
                                logger.error(u"Tautulli Monitor :: %s: Unable to retrieve metadata for rating_key %s" \
                                             % (server.CONFIG.PMS_NAME, str(item['rating_key'])))

                        else:
                            metadata = server.PMSCONNECTION.get_metadata_children_details(item['rating_key'])
                            if not metadata:
                                logger.error(u"Tautulli Monitor :: %s: Unable to retrieve children metadata for rating_key %s" \
                                             % (server.CONFIG.PMS_NAME, str(item['rating_key'])))

                    if metadata:

                        if not plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED:
                            for item in metadata:

                                if 0 < time_threshold - int(item['added_at']) <= time_interval:
                                    logger.debug(u"Tautulli Monitor :: %s: Library item %s added to Plex."
                                                 % (server.CONFIG.PMS_NAME, str(item['rating_key'])))

                                    plexpy.NOTIFY_QUEUE.put({'timeline_data': item.copy(), 'notify_action': 'on_created'})

                        else:
                            item = max(metadata, key=lambda x:x['added_at'])

                            if 0 < time_threshold - int(item['added_at']) <= time_interval:
                                if item['media_type'] == 'episode' or item['media_type'] == 'track':
                                    metadata = server.PMSCONNECTION.get_metadata_details(item['grandparent_rating_key'])

                                    if metadata:
                                        item = metadata
                                    else:
                                        logger.error(u"Tautulli Monitor :: %s: Unable to retrieve grandparent metadata for grandparent_rating_key %s" \
                                                     % (server.CONFIG.PMS_NAME, str(item['rating_key'])))

                                logger.debug(u"Tautulli Monitor :: %s: Library item %s added to Plex."
                                             % (server.CONFIG.PMS_NAME, str(item['rating_key'])))

                                # Check if any notification agents have notifications enabled
                                plexpy.NOTIFY_QUEUE.put({'timeline_data': item.copy(), 'notify_action': 'on_created'})


def connect_server(server=None, log=True, startup=False):

    if server.CONFIG.PMS_IS_CLOUD:
        if log:
            logger.info(u"Tautulli Monitor :: %s: Checking for Plex Cloud server status..." % server.CONFIG.PMS_NAME)

        status = plexpy.PLEXTV.get_cloud_server_status(server=server)

        if status is True:
            logger.info(u"Tautulli Monitor :: %s: Plex Cloud server is active." % server.CONFIG.PMS_NAME)
        elif status is False:
            if log:
                logger.info(u"Tautulli Monitor :: %s: Plex Cloud server is sleeping." % server.CONFIG.PMS_NAME)
        else:
            if log:
                logger.error(u"Tautulli Monitor :: %s: Failed to retrieve Plex Cloud server status." % server.CONFIG.PMS_NAME)

        if not status and startup:
            server.WS.on_disconnect()

    else:
        status = True

    if status:
        if log and not startup and not server.WS_CONNECTED and not server.server_shutdown and server.CONFIG.PMS_IS_ENABLED:
            logger.info(u"Tautulli Monitor :: %s: Attempting to reconnect Plex server..." % server.CONFIG.PMS_NAME)
            try:
                server.WS.start()
            except Exception as e:
                logger.error(u"Websocket :: %s: Unable to open connection: %s." % (server.CONFIG.PMS_NAME, e))


def check_server_access(server=None):
    if server.WS_CONNECTED and server.WS and server.WS.WS_CONNECTION and server.WS.WS_CONNECTION.connected:
        with server.monitor_lock:
            server_response = server.PMSCONNECTION.get_server_response()

            # Check for remote access
            if server_response:

                mapping_state = server_response['mapping_state']
                mapping_error = server_response['mapping_error']

                # Check if the port is mapped
                if not mapping_state == 'mapped':
                    server.ping_count += 1
                    logger.warn(u"Tautulli Monitor :: %s: Plex remote access port not mapped, ping attempt %s." \
                                % (server.CONFIG.PMS_NAME, str(server.ping_count)))
                # Check if the port is open
                elif mapping_error == 'unreachable':
                    server.ping_count += 1
                    logger.warn(u"Tautulli Monitor :: %s: Plex remote access port mapped, but mapping failed, ping attempt %s." \
                                % (server.CONFIG.PMS_NAME, str(server.ping_count)))
                # Reset external ping counter
                else:
                    if server.ping_count >= plexpy.CONFIG.REMOTE_ACCESS_PING_THRESHOLD:
                        logger.info(u"Tautulli Monitor :: %s: Plex remote access is back up." % server.CONFIG.PMS_NAME)
                        plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_extup', 'server_id': server.CONFIG.ID})
                    server.ping_count = 0
                    server.remote_access_status = True

            if server.ping_count == plexpy.CONFIG.REMOTE_ACCESS_PING_THRESHOLD:
                plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_extdown', 'server_id': server.CONFIG.ID})
                server.remote_access_status = False


def check_server_updates(server=None):
    if server.WS_CONNECTED and server.WS and server.WS.WS_CONNECTION and server.WS.WS_CONNECTION.connected:
        with server.monitor_lock:
            server_version = server.PMSCONNECTION.get_server_version()
            if server_version and server_version != server.CONFIG.PMS_VERSION:
                server.CONFIG.PMS_VERSION = server_version

            download_info = server.PMSCONNECTION.get_server_info()

            if download_info and download_info['update_available']:
                logger.info(u"Tautulli Monitor :: %s: PMS update available version: %s" % (server.CONFIG.PMS_NAME, download_info['version']))
                plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_pmsupdate', 'pms_download_info': download_info, 'server_id': server.CONFIG.ID})
                server.update_available = True
            else:
                server.update_available = False


def check_rclone_status(server, kwargs=None):
    """
    If rclone returns the PID, rclone is alive.
    Then copy a test file to a temporary directory accessing the test file thru the mount directory.
    returns:
        True  = Alive and well
        False = Not functioning
    """
    if kwargs:
        user = kwargs['rclone_user']
        password = kwargs['rclone_pass']
        testFile = kwargs['rclone_testfile']
        mountPath = kwargs['rclone_mountdir']
        tmpDir = kwargs['rclone_tmpdir']
        port = kwargs['rclone_port']
        ssl = bool_int(kwargs['rclone_ssl'])
        hostname = (kwargs['rclone_ssl_hostname'] if ssl else server.CONFIG.PMS_IP)
    else:
        user = server.CONFIG.RCLONE_USER
        password = server.CONFIG.RCLONE_PASS
        testFile = server.CONFIG.RCLONE_TESTFILE
        mountPath = server.CONFIG.RCLONE_MOUNTDIR
        tmpDir = server.CONFIG.RCLONE_TMPDIR
        port = server.CONFIG.RCLONE_PORT
        ssl = server.CONFIG.RCLONE_SSL
        hostname = (server.CONFIG.RCLONE_SSL_HOSTNAME if ssl else server.CONFIG.PMS_IP)

    scheme = ('https' if ssl else 'http')

    url = '{scheme}://{hostname}:{port}'.format(scheme=scheme,
                                                hostname=hostname,
                                                port=port)
    timeout = 10
    status = False
    try:
        """
          Test if we get back a pid.
        """
        uri = '/core/pid'
        response = requests.post(url + uri, timeout=timeout, auth=(user, password))
        if response.status_code == requests.codes.ok:
            if 'pid' in response.json():
                status = True

        """
          Copy the testfile from the mount path to the temp directory.
        """
        if status:
            status = False
            uri = '/operations/copyfile?srcFs=' + mountPath + \
                  '&srcRemote=' + testFile + \
                  '&dstFs=' + tmpDir + \
                  '&dstRemote=' + testFile
            response = requests.post(url + uri, timeout=timeout, auth=(user, password))
            if response.status_code == requests.codes.ok:
                status = True

        """
          Delete the testfile from the temp location.
        """
        if status:
            status = False
            uri = '/operations/deletefile?fs=' + tmpDir + '&remote=' + testFile
            response = requests.post(url + uri, timeout=timeout, auth=(user, password))
            if response.status_code == requests.codes.ok:
                status = True

        if status:
            if server.rclone_status == False:
                plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_rcloneup', 'server_id': server.CONFIG.ID})
        else:
            raise requests.exceptions.RequestException

    except requests.exceptions.RequestException as e:
        logger.debug(u"Tautulli Monitor :: %s: rClone mount not responding. %s" % (server.CONFIG.PMS_NAME, e))
        logger.debug(u"Tautulli Monitor :: %s: rClone uri: %s" % (server.CONFIG.PMS_NAME, uri))
        if server.rclone_status == True:
            plexpy.NOTIFY_QUEUE.put({'notify_action': 'on_rclonedown', 'server_id': server.CONFIG.ID})

    with server.monitor_lock:
        server.rclone_status = status
