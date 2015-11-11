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

from plexpy import logger, config, notifiers, database, helpers

import plexpy
import time


def notify(stream_data=None, notify_action=None):
    from plexpy import users
    
    if stream_data and notify_action:
        # Check if notifications enabled for user
        user_data = users.Users()
        user_details = user_data.get_user_friendly_name(user=stream_data['user'])

        if not user_details['do_notify']:
            return

        if stream_data['media_type'] == 'movie' or stream_data['media_type'] == 'episode':
            if plexpy.CONFIG.MOVIE_NOTIFY_ENABLE or plexpy.CONFIG.TV_NOTIFY_ENABLE:

                progress_percent = helpers.get_percent(stream_data['view_offset'], stream_data['duration'])

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_stop'] and notify_action == 'stop' \
                        and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < plexpy.CONFIG.NOTIFY_WATCHED_PERCENT):
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])

                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_pause'] and notify_action == 'pause' \
                        and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99):
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])

                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_resume'] and notify_action == 'resume' \
                        and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99):
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])

                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_buffer'] and notify_action == 'buffer':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])

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
                                                        body=notify_strings[1])
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
                                                                body=notify_strings[1])
                                    # Set the notification state in the db
                                    set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

        elif stream_data['media_type'] == 'track':
            if plexpy.CONFIG.MUSIC_NOTIFY_ENABLE:

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_stop'] and notify_action == 'stop':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_pause'] and notify_action == 'pause':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_resume'] and notify_action == 'resume':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

                    elif agent['on_buffer'] and notify_action == 'buffer':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state=notify_action, agent_info=agent)

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            logger.debug(u"PlexPy Notifier :: Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"PlexPy Notifier :: Notify called but incomplete data received.")


def notify_timeline(timeline_data=None, notify_action=None):
    if timeline_data and notify_action:
        for agent in notifiers.available_notification_agents():
            if agent['on_created'] and notify_action == 'created':
                if (plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_GRANDPARENT \
                    and (timeline_data['media_type'] == 'movie' or timeline_data['media_type'] == 'show' or timeline_data['media_type'] == 'artist')) \
                    or (not plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_GRANDPARENT \
                    and (timeline_data['media_type'] == 'movie' or timeline_data['media_type'] == 'episode' or timeline_data['media_type'] == 'track')):
                    # Build and send notification
                    notify_strings = build_notify_text(timeline=timeline_data, state=notify_action)
                    notifiers.send_notification(config_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1])
                    # Set the notification state in the db
                    set_notify_state(session=timeline_data, state=notify_action, agent_info=agent)
    else:
        logger.debug(u"PlexPy Notifier :: Notify timeline called but incomplete data received.")


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
        notify_state = {'on_play': item[0],
                        'on_stop': item[1],
                        'on_pause': item[2],
                        'on_resume': item[3],
                        'on_buffer': item[4],
                        'on_watched': item[5],
                        'agent_id': item[6]}
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
        notify_state = {'on_created': item[0],
                        'agent_id': item[1]}
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
        logger.error('PlexPy Notifier :: Unable to set notify state.')


def build_notify_text(session=None, timeline=None, state=None):
    from plexpy import pmsconnect, helpers
    import re

    # Get the server name
    pms_connect = pmsconnect.PmsConnect()
    server_name = pms_connect.get_server_pref(pref='FriendlyName')
    # If friendly name is blank
    if not server_name:
        servers_info = pms_connect.get_servers_info()
        for server in servers_info:
            if server['machine_identifier'] == plexpy.CONFIG.PMS_IDENTIFIER:
                server_name = server['name']
                break

    # Get metadata feed for item
    if session:
        rating_key = session['rating_key']
    elif timeline:
        rating_key = timeline['rating_key']

    metadata_list = pms_connect.get_metadata_details(rating_key=rating_key)

    if metadata_list:
        metadata = metadata_list['metadata']
    else:
        logger.error(u"PlexPy Notifier :: Unable to retrieve metadata for rating_key %s" % str(rating_key))
        return []

    # Check for exclusion tags
    if metadata['media_type'] == 'episode':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile('<movie>[^>]+.</movie>|<music>[^>]+.</music>', re.IGNORECASE)
    elif metadata['media_type'] == 'movie':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile('<tv>[^>]+.</tv>|<music>[^>]+.</music>', re.IGNORECASE)
    elif metadata['media_type'] == 'track':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', re.IGNORECASE)
    else:
        pattern = None

    if metadata['media_type'] == 'episode' or metadata['media_type'] == 'movie' or metadata['media_type'] == 'track' \
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

    # Create a title
    if metadata['media_type'] == 'episode' or metadata['media_type'] == 'track':
        full_title = '%s - %s' % (metadata['grandparent_title'],
                                  metadata['title'])
    else:
        full_title = metadata['title']

    duration = helpers.convert_milliseconds_to_minutes(metadata['duration'])

    # Default values
    transcode_decision = ''
    stream_duration = 0
    view_offset = 0
    user = ''
    platform = ''
    player = ''
    ip_address = 'N/A'

    # Session values
    if session:
        # Generate a combined transcode decision value
        if session['video_decision']:
            if session['video_decision'] == 'transcode':
                transcode_decision = 'Transcode'
            elif session['video_decision'] == 'copy' or session['audio_decision'] == 'copy':
                transcode_decision = 'Direct Stream'
            else:
                transcode_decision = 'Direct Play'
        elif session['audio_decision']:
            if session['audio_decision'] == 'transcode':
                transcode_decision = 'Transcode'
            else:
                transcode_decision = 'Direct Play'

        if state != 'play':
            if session['paused_counter']:
                stream_duration = int((time.time() - helpers.cast_to_float(session['started']) -
                                       helpers.cast_to_float(session['paused_counter'])) / 60)
            else:
                stream_duration = int((time.time() - helpers.cast_to_float(session['started'])) / 60)

        view_offset = helpers.convert_milliseconds_to_minutes(session['view_offset'])
        user = session['friendly_name']
        platform = session['platform']
        player = session['player']
        ip_address = session['ip_address'] if session['ip_address'] != '' else 'N/A'

    progress_percent = helpers.get_percent(view_offset, duration)

    available_params = {'server_name': server_name,
                        'user': user,
                        'platform': platform,
                        'player': player,
                        'ip_address': ip_address,
                        'media_type': metadata['media_type'],
                        'title': full_title,
                        'show_name': metadata['grandparent_title'],
                        'episode_name': metadata['title'],
                        'artist_name': metadata['grandparent_title'],
                        'album_name': metadata['parent_title'],
                        'track_name': metadata['title'],
                        'season_num': metadata['parent_index'],
                        'season_num00': metadata['parent_index'].zfill(2),
                        'episode_num': metadata['index'],
                        'episode_num00': metadata['index'].zfill(2),
                        'transcode_decision': transcode_decision,
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
                        'duration': duration,
                        'stream_duration': stream_duration,
                        'remaining_duration': duration - view_offset,
                        'progress': view_offset,
                        'progress_percent': progress_percent
                        }

    # Default subject text
    subject_text = 'PlexPy (%s)' % server_name

    if state == 'play':
        # Default body text
        body_text = '%s (%s) is watching %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_start_subject and on_start_body:
            try:
                subject_text = unicode(on_start_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_start_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    elif state == 'stop':
        # Default body text
        body_text = '%s (%s) has stopped %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_stop_subject and on_stop_body:
            try:
                subject_text = unicode(on_stop_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_stop_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    elif state == 'pause':
        # Default body text
        body_text = '%s (%s) has paused %s' % (session['friendly_name'],
                                               session['player'],
                                               full_title)

        if on_pause_subject and on_pause_body:
            try:
                subject_text = unicode(on_pause_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_pause_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    elif state == 'resume':
        # Default body text
        body_text = '%s (%s) has resumed %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_resume_subject and on_resume_body:
            try:
                subject_text = unicode(on_resume_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_resume_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    elif state == 'buffer':
        # Default body text
        body_text = '%s (%s) is buffering %s' % (session['friendly_name'],
                                                 session['player'],
                                                 full_title)

        if on_buffer_subject and on_buffer_body:
            try:
                subject_text = unicode(on_buffer_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_buffer_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    elif state == 'watched':
        # Default body text
        body_text = '%s (%s) has watched %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_watched_subject and on_watched_body:
            try:
                subject_text = unicode(on_watched_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_watched_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    elif state == 'created':
        # Default body text
        body_text = '%s was recently added to Plex.' % full_title

        if on_created_subject and on_created_body:
            try:
                subject_text = unicode(on_created_subject).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_created_body).format(**available_params)
            except LookupError, e:
                logger.error(u"PlexPy Notifier :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    else:
        return None


def strip_tag(data):
    import re

    p = re.compile(r'<.*?>')
    return p.sub('', data)