#  This file is part of PlexPy.
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


import re
import time
import arrow

from plexpy import logger, config, notifiers, database, helpers, plextv, pmsconnect
import plexpy


def notify(stream_data=None, notify_action=None):
    from plexpy import users, libraries
    
    if stream_data and notify_action:
        # Check if notifications enabled for user and library
        user_data = users.Users()
        user_details = user_data.get_details(user_id=stream_data['user_id'])

        library_data = libraries.Libraries()
        library_details = library_data.get_details(section_id=stream_data['section_id'])

        if not user_details['do_notify']:
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for user '%s' is disabled." % user_details['username'])
            return
        elif not library_details['do_notify']:
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
            return

        if (stream_data['media_type'] == 'movie' and plexpy.CONFIG.MOVIE_NOTIFY_ENABLE) \
            or (stream_data['media_type'] == 'episode' and plexpy.CONFIG.TV_NOTIFY_ENABLE):

            progress_percent = helpers.get_percent(stream_data['view_offset'], stream_data['duration'])

            for agent in notifiers.available_notification_agents():
                if agent['on_play'] and notify_action == 'play':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    # Set the notification state in the db
                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_stop'] and notify_action == 'stop' \
                    and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < plexpy.CONFIG.NOTIFY_WATCHED_PERCENT):
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_pause'] and notify_action == 'pause' \
                    and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99):
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_resume'] and notify_action == 'resume' \
                    and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99):
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_buffer'] and notify_action == 'buffer':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_watched'] and notify_action == 'watched':
                    # Get the current states for notifications from our db
                    notify_states = get_notify_state(session=stream_data)

                    # If there is nothing in the notify_log for our agent id but it is enabled we should notify
                    if not any(d['agent_id'] == agent['id'] for d in notify_states):
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1],
                                                    notify_action=notify_action,
                                                    script_args=notify_strings[2])

                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    else:
                        # Check in our notify log if the notification has already been sent
                        for notify_state in notify_states:
                            if not notify_state['on_watched'] and (notify_state['agent_id'] == agent['id']):
                                # Build and send notification
                                notify_strings = build_notify_text(session=stream_data, state=notify_action)
                                notifiers.send_notification(config_id=agent['id'],
                                                            subject=notify_strings[0],
                                                            body=notify_strings[1],
                                                            notify_action=notify_action,
                                                            script_args=notify_strings[2])

                                # Set the notification state in the db
                                set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

        elif (stream_data['media_type'] == 'track' and plexpy.CONFIG.MUSIC_NOTIFY_ENABLE):

            for agent in notifiers.available_notification_agents():
                if agent['on_play'] and notify_action == 'play':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    # Set the notification state in the db
                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_stop'] and notify_action == 'stop':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    # Set the notification state in the db
                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_pause'] and notify_action == 'pause':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    # Set the notification state in the db
                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_resume'] and notify_action == 'resume':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    # Set the notification state in the db
                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                elif agent['on_buffer'] and notify_action == 'buffer':
                    # Build and send notification
                    notify_strings = build_notify_text(session=stream_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                notify_action=notify_action,
                                                script_args=notify_strings[2])

                    # Set the notification state in the db
                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            #logger.debug(u"PlexPy NotificationHandler :: Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"PlexPy NotificationHandler :: Notify called but incomplete data received.")


def notify_timeline(timeline_data=None, notify_action=None):
    if timeline_data and notify_action:
        for agent in notifiers.available_notification_agents():
            if agent['on_created'] and notify_action == 'created':
                # Build and send notification
                notify_strings = build_notify_text(timeline=timeline_data, state=notify_action)
                notifiers.send_notification(config_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            notify_action=notify_action,
                                            script_args=notify_strings[2])
                # Set the notification state in the db
                set_notify_state(session=timeline_data, state=notify_action, agent_info=agent)

    elif not timeline_data and notify_action:
        for agent in notifiers.available_notification_agents():
            if agent['on_extdown'] and notify_action == 'extdown':
                # Build and send notification
                notify_strings = build_server_notify_text(state=notify_action)
                notifiers.send_notification(config_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            notify_action=notify_action,
                                            script_args=notify_strings[2])
            if agent['on_intdown'] and notify_action == 'intdown':
                # Build and send notification
                notify_strings = build_server_notify_text(state=notify_action)
                notifiers.send_notification(config_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            notify_action=notify_action,
                                            script_args=notify_strings[2])
            if agent['on_extup'] and notify_action == 'extup':
                # Build and send notification
                notify_strings = build_server_notify_text(state=notify_action)
                notifiers.send_notification(config_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            notify_action=notify_action,
                                            script_args=notify_strings[2])
            if agent['on_intup'] and notify_action == 'intup':
                # Build and send notification
                notify_strings = build_server_notify_text(state=notify_action)
                notifiers.send_notification(config_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            notify_action=notify_action,
                                            script_args=notify_strings[2])
    else:
        logger.debug(u"PlexPy NotificationHandler :: Notify timeline called but incomplete data received.")


def get_notify_state(session):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT on_play, on_stop, on_pause, on_resume, on_buffer, on_watched, agent_id '
                               'FROM notify_log '
                               'WHERE session_key = ? '
                               'AND rating_key = ? '
                               'AND user = ? '
                               'ORDER BY id DESC',
                               args=[session['session_key'], session['rating_key'], session['user']])
    notify_states = []
    for item in result:
        notify_state = {'on_play': item['on_play'],
                        'on_stop': item['on_stop'],
                        'on_pause': item['on_pause'],
                        'on_resume': item['on_resume'],
                        'on_buffer': item['on_buffer'],
                        'on_watched': item['on_watched'],
                        'agent_id': item['agent_id']}
        notify_states.append(notify_state)

    return notify_states


def get_notify_state_timeline(timeline):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT on_created, agent_id '
                               'FROM notify_log '
                               'WHERE rating_key = ? '
                               'ORDER BY id DESC',
                               args=[timeline['rating_key']])
    notify_states = []
    for item in result:
        notify_state = {'on_created': item['on_created'],
                        'agent_id': item['agent_id']}
        notify_states.append(notify_state)

    return notify_states


def set_notify_state(session, state, agent_info):

    if session and state and agent_info:
        monitor_db = database.MonitorDatabase()

        if state == 'play':
            values = {'on_play': int(time.time())}
        elif state == 'stop':
            values = {'on_stop': int(time.time())}
        elif state == 'pause':
            values = {'on_pause': int(time.time())}
        elif state == 'resume':
            values = {'on_resume': int(time.time())}
        elif state == 'buffer':
            values = {'on_buffer': int(time.time())}
        elif state == 'watched':
            values = {'on_watched': int(time.time())}
        elif state == 'created':
            values = {'on_created': int(time.time())}
        else:
            return

        if state == 'created':
            keys = {'rating_key': session['rating_key'],
                    'agent_id': agent_info['id'],
                    'agent_name': agent_info['name']}
        else:
            keys = {'session_key': session['session_key'],
                    'rating_key': session['rating_key'],
                    'user_id': session['user_id'],
                    'user': session['user'],
                    'agent_id': agent_info['id'],
                    'agent_name': agent_info['name']}

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to set notify state.")


def build_notify_text(session=None, timeline=None, state=None):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','').replace('zz','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','').replace('zz','')
    duration_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','').replace('zz','').replace('a','').replace('A','')

    # Get the server name
    server_name = plexpy.CONFIG.PMS_NAME

    # Get the server uptime
    plex_tv = plextv.PlexTV()
    server_times = plex_tv.get_server_times()

    if server_times:
        updated_at = server_times[0]['updated_at']
        server_uptime = helpers.human_duration(int(time.time() - helpers.cast_to_float(updated_at)))
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve server uptime.")
        server_uptime = 'N/A'

    # Get metadata feed for item
    if session:
        rating_key = session['rating_key']
    elif timeline:
        rating_key = timeline['rating_key']

    pms_connect = pmsconnect.PmsConnect()
    metadata_list = pms_connect.get_metadata_details(rating_key=rating_key)

    stream_count = pms_connect.get_current_activity().get('stream_count', '')

    if metadata_list:
        metadata = metadata_list['metadata']
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))
        return []

    # Check for exclusion tags
    if metadata['media_type'] == 'movie':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile('\n*<tv>[^>]+.</tv>\n*|\n*<music>[^>]+.</music>\n*', re.IGNORECASE | re.DOTALL)
    elif metadata['media_type'] == 'show' or metadata['media_type'] == 'episode':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile('\n*<movie>[^>]+.</movie>\n*|\n*?<music>[^>]+.</music>\n*', re.IGNORECASE | re.DOTALL)
    elif metadata['media_type'] == 'artist' or metadata['media_type'] == 'track':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile('\n*<tv>[^>]+.</tv>\n*|\n*<movie>[^>]+.</movie>\n*', re.IGNORECASE | re.DOTALL)
    else:
        pattern = None

    if metadata['media_type'] == 'movie' \
        or metadata['media_type'] == 'show' or metadata['media_type'] == 'episode' \
        or metadata['media_type'] == 'artist' or metadata['media_type'] == 'track' \
        and pattern:
        # Remove the unwanted tags and strip any unmatch tags too.
        on_start_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT))
        on_start_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT))
        on_stop_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT))
        on_stop_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT))
        on_pause_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT))
        on_pause_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT))
        on_resume_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT))
        on_resume_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT))
        on_buffer_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT))
        on_buffer_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT))
        on_watched_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT))
        on_watched_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT))
        on_created_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_CREATED_SUBJECT_TEXT))
        on_created_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_CREATED_BODY_TEXT))
        script_args_text = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT))
    else:
        on_start_subject = plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT
        on_start_body = plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT
        on_stop_subject = plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT
        on_stop_body = plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT
        on_pause_subject = plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT
        on_pause_body = plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT
        on_resume_subject = plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT
        on_resume_body = plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT
        on_buffer_subject = plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT
        on_buffer_body = plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT
        on_watched_subject = plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT
        on_watched_body = plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT
        on_created_subject = plexpy.CONFIG.NOTIFY_ON_CREATED_SUBJECT_TEXT
        on_created_body = plexpy.CONFIG.NOTIFY_ON_CREATED_BODY_TEXT
        script_args_text = plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT

    # Create a title
    if metadata['media_type'] == 'episode' or metadata['media_type'] == 'track':
        full_title = '%s - %s' % (metadata['grandparent_title'],
                                  metadata['title'])
    else:
        full_title = metadata['title']

    # Session values
    if session is None:
        session = {}

    # Generate a combined transcode decision value
    if session.get('video_decision','') == 'transcode' or session.get('audio_decision','') == 'transcode':
        transcode_decision = 'Transcode'
    elif session.get('video_decision','') == 'copy' or session.get('audio_decision','') == 'copy':
        transcode_decision = 'Direct Stream'
    else:
        transcode_decision = 'Direct Play'
    
    if state != 'play':
        stream_duration = helpers.convert_seconds_to_minutes(
                            time.time() - 
                            helpers.cast_to_float(session.get('started', 0)) -
                            helpers.cast_to_float(session.get('paused_counter', 0)))
    else:
        stream_duration = 0

    view_offset = helpers.convert_milliseconds_to_minutes(session.get('view_offset', 0))
    duration = helpers.convert_milliseconds_to_minutes(metadata['duration'])
    progress_percent = helpers.get_percent(view_offset, duration)
    remaining_duration = duration - view_offset

    # Fix metadata params for notify recently added grandparent
    if state == 'created' and plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_GRANDPARENT:
        show_name = metadata['title']
        episode_name = ''
        artist_name = metadata['title']
        album_name = ''
        track_name = ''
    else:
        show_name = metadata['grandparent_title']
        episode_name = metadata['title']
        artist_name = metadata['grandparent_title']
        album_name = metadata['parent_title']
        track_name = metadata['title']

    available_params = {# Global paramaters
                        'server_name': server_name,
                        'server_uptime': server_uptime,
                        'action': state.title(),
                        'datestamp': arrow.now().format(date_format),
                        'timestamp': arrow.now().format(time_format),
                        # Stream parameters
                        'streams': stream_count,
                        'user': session.get('friendly_name',''),
                        'platform': session.get('platform',''),
                        'player': session.get('player',''),
                        'ip_address': session.get('ip_address','N/A'),
                        'stream_duration': stream_duration,
                        'stream_time': arrow.get(stream_duration * 60).format(duration_format),
                        'remaining_duration': remaining_duration,
                        'remaining_time': arrow.get(remaining_duration * 60).format(duration_format),
                        'progress_duration': view_offset,
                        'progress_time': arrow.get(view_offset * 60).format(duration_format),
                        'progress_percent': progress_percent,
                        'container': session.get('container',''),
                        'video_codec': session.get('video_codec',''),
                        'video_bitrate': session.get('bitrate',''),
                        'video_width': session.get('width',''),
                        'video_height': session.get('height',''),
                        'video_resolution': session.get('video_resolution',''),
                        'video_framerate': session.get('video_framerate',''),
                        'aspect_ratio': session.get('aspect_ratio',''),
                        'audio_codec': session.get('audio_codec',''),
                        'audio_channels': session.get('audio_channels',''),
                        'transcode_decision': transcode_decision,
                        'video_decision': session.get('video_decision','').title(),
                        'audio_decision': session.get('audio_decision','').title(),
                        'transcode_container': session.get('transcode_container',''),
                        'transcode_video_codec': session.get('transcode_video_codec',''),
                        'transcode_video_width': session.get('transcode_width',''),
                        'transcode_video_height': session.get('transcode_height',''),
                        'transcode_audio_codec': session.get('transcode_audio_codec',''),
                        'transcode_audio_channels': session.get('transcode_audio_channels',''),
                        'session_key': session.get('session_key',''),
                        'user_id': session.get('user_id',''),
                        # Metadata parameters
                        'media_type': metadata['media_type'],
                        'title': full_title,
                        'library_name': metadata['library_name'],
                        'show_name': show_name,
                        'episode_name': episode_name,
                        'artist_name': artist_name,
                        'album_name': album_name,
                        'track_name': track_name,
                        'season_num': metadata['parent_media_index'].zfill(1),
                        'season_num00': metadata['parent_media_index'].zfill(2),
                        'episode_num': metadata['media_index'].zfill(1),
                        'episode_num00': metadata['media_index'].zfill(2),
                        'track_num': metadata['media_index'].zfill(1),
                        'track_num00': metadata['media_index'].zfill(2),
                        'year': metadata['year'],
                        'studio': metadata['studio'],
                        'content_rating': metadata['content_rating'],
                        'directors': ', '.join(metadata['directors']),
                        'writers': ', '.join(metadata['writers']),
                        'actors': ', '.join(metadata['actors']),
                        'genres': ', '.join(metadata['genres']),
                        'summary': metadata['summary'],
                        'tagline': metadata['tagline'],
                        'rating': metadata['rating'],
                        'duration': metadata['duration'],
                        'section_id': metadata['section_id'],
                        'rating_key': metadata['rating_key'],
                        'parent_rating_key': metadata['parent_rating_key'],
                        'grandparent_rating_key': metadata['grandparent_rating_key']
                        }

    # Default subject text
    subject_text = 'PlexPy (%s)' % server_name

    # Default scripts args
    script_args = []

    if script_args_text:
        try:
            script_args = [unicode(arg).format(**available_params) for arg in script_args_text.split()]
        except LookupError as e:
            logger.error(u"PlexPy Notifier :: Unable to parse field %s in script argument. Using fallback." % e)
        except Exception as e:
            logger.error(u"PlexPy Notifier :: Unable to parse custom script arguments %s. Using fallback." % e)

    if state == 'play':
        # Default body text
        body_text = '%s (%s) started playing %s' % (session['friendly_name'],
                                                    session['player'],
                                                    full_title)

        if on_start_subject and on_start_body:
            try:
                subject_text = unicode(on_start_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_start_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'stop':
        # Default body text
        body_text = '%s (%s) has stopped %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_stop_subject and on_stop_body:
            try:
                subject_text = unicode(on_stop_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_stop_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'pause':
        # Default body text
        body_text = '%s (%s) has paused %s' % (session['friendly_name'],
                                               session['player'],
                                               full_title)

        if on_pause_subject and on_pause_body:
            try:
                subject_text = unicode(on_pause_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_pause_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'resume':
        # Default body text
        body_text = '%s (%s) has resumed %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_resume_subject and on_resume_body:
            try:
                subject_text = unicode(on_resume_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_resume_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'buffer':
        # Default body text
        body_text = '%s (%s) is buffering %s' % (session['friendly_name'],
                                                 session['player'],
                                                 full_title)

        if on_buffer_subject and on_buffer_body:
            try:
                subject_text = unicode(on_buffer_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_buffer_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'watched':
        # Default body text
        body_text = '%s (%s) has watched %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_watched_subject and on_watched_body:
            try:
                subject_text = unicode(on_watched_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_watched_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'created':
        # Default body text
        body_text = '%s was recently added to Plex.' % full_title

        if on_created_subject and on_created_body:
            try:
                subject_text = unicode(on_created_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_created_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    else:
        return None


def build_server_notify_text(state=None):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','').replace('zz','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','').replace('zz','')

    # Get the server name
    server_name = plexpy.CONFIG.PMS_NAME

    # Get the server uptime
    plex_tv = plextv.PlexTV()
    server_times = plex_tv.get_server_times()

    if server_times:
        updated_at = server_times[0]['updated_at']
        server_uptime = helpers.human_duration(int(time.time() - helpers.cast_to_float(updated_at)))
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve server uptime.")
        server_uptime = 'N/A'

    on_extdown_subject = plexpy.CONFIG.NOTIFY_ON_EXTDOWN_SUBJECT_TEXT
    on_extdown_body = plexpy.CONFIG.NOTIFY_ON_EXTDOWN_BODY_TEXT
    on_intdown_subject = plexpy.CONFIG.NOTIFY_ON_INTDOWN_SUBJECT_TEXT
    on_intdown_body = plexpy.CONFIG.NOTIFY_ON_INTDOWN_BODY_TEXT
    on_extup_subject = plexpy.CONFIG.NOTIFY_ON_EXTUP_SUBJECT_TEXT
    on_extup_body = plexpy.CONFIG.NOTIFY_ON_EXTUP_BODY_TEXT
    on_intup_subject = plexpy.CONFIG.NOTIFY_ON_INTUP_SUBJECT_TEXT
    on_intup_body = plexpy.CONFIG.NOTIFY_ON_INTUP_BODY_TEXT
    script_args_text = plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT

    available_params = {# Global paramaters
                        'server_name': server_name,
                        'server_uptime': server_uptime,
                        'action': state.title(),
                        'datestamp': arrow.now().format(date_format),
                        'timestamp': arrow.now().format(time_format)}

    # Default text
    subject_text = 'PlexPy (%s)' % server_name

    # Default scripts args
    script_args = []

    if script_args_text:
        try:
            script_args = [unicode(arg).format(**available_params) for arg in script_args_text.split()]
        except LookupError as e:
            logger.error(u"PlexPy Notifier :: Unable to parse field %s in script argument. Using fallback." % e)
        except Exception as e:
            logger.error(u"PlexPy Notifier :: Unable to parse custom script arguments %s. Using fallback." % e)

    if state == 'extdown':
        # Default body text
        body_text = 'The Plex Media Server remote access is down.'

        if on_extdown_subject and on_extdown_body:
            try:
                subject_text = unicode(on_extdown_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_extdown_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]

    elif state == 'intdown':
        # Default body text
        body_text = 'The Plex Media Server is down.'

        if on_intdown_subject and on_intdown_body:
            try:
                subject_text = unicode(on_intdown_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_intdown_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    if state == 'extup':
        # Default body text
        body_text = 'The Plex Media Server remote access is back up.'

        if on_extup_subject and on_extup_body:
            try:
                subject_text = unicode(on_extup_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_extup_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif state == 'intup':
        # Default body text
        body_text = 'The Plex Media Server is back up.'

        if on_intup_subject and on_intup_body:
            try:
                subject_text = unicode(on_intup_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_intup_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]

    else:
        return None


def strip_tag(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)