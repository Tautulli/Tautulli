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

from plexpy import logger, config, notifiers, database

import plexpy
import time

def notify(stream_data=None, notify_action=None):
    from plexpy import datafactory
    
    if stream_data and notify_action:
        # Check if notifications enabled for user
        data_factory = datafactory.DataFactory()
        user_details = data_factory.get_user_friendly_name(user=stream_data['user'])

        if not user_details['do_notify']:
            return

        if stream_data['media_type'] == 'movie' or stream_data['media_type'] == 'episode':
            if plexpy.CONFIG.MOVIE_NOTIFY_ENABLE or plexpy.CONFIG.TV_NOTIFY_ENABLE:

                for agent in notifiers.available_notification_agents():
                    if agent['on_play'] and notify_action == 'play':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state='play', agent_info=agent)

                    elif agent['on_stop'] and notify_action == 'stop':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])

                        set_notify_state(session=stream_data, state='stop', agent_info=agent)

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
                            set_notify_state(session=stream_data, state='watched', agent_info=agent)

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
                                    set_notify_state(session=stream_data, state='watched', agent_info=agent)

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
                        set_notify_state(session=stream_data, state='play', agent_info=agent)

                    elif agent['on_stop'] and notify_action == 'stop':
                        # Build and send notification
                        notify_strings = build_notify_text(session=stream_data, state=notify_action)
                        notifiers.send_notification(config_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1])
                        # Set the notification state in the db
                        set_notify_state(session=stream_data, state='stop', agent_info=agent)

        elif stream_data['media_type'] == 'clip':
            pass
        else:
            logger.debug(u"PlexPy Notifier :: Notify called with unsupported media type.")
            pass
    else:
        logger.debug(u"PlexPy Notifier :: Notify called but incomplete data received.")

def get_notify_state(session):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT on_play, on_stop, on_watched, agent_id '
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
                        'on_watched': item[2],
                        'agent_id': item[3]}
        notify_states.append(notify_state)

    return notify_states

def set_notify_state(session, state, agent_info):

    if session and state and agent_info:
        monitor_db = database.MonitorDatabase()

        if state == 'play':
            values = {'on_play': int(time.time())}
        elif state == 'stop':
            values = {'on_stop': int(time.time())}
        elif state == 'watched':
            values = {'on_watched': int(time.time())}
        else:
            return

        keys = {'session_key': session['session_key'],
                'rating_key': session['rating_key'],
                'user_id': session['user_id'],
                'user': session['user'],
                'agent_id': agent_info['id'],
                'agent_name': agent_info['name']}

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
    else:
        logger.error('PlexPy Notifier :: Unable to set notify state.')

def build_notify_text(session, state):
    from plexpy import pmsconnect, helpers
    import re

    # Get the server name
    pms_connect = pmsconnect.PmsConnect()
    server_name = pms_connect.get_server_pref(pref='FriendlyName')

    # Get metadata feed for item
    metadata = pms_connect.get_metadata_details(rating_key=session['rating_key'])

    if metadata:
        item_metadata = metadata['metadata']
    else:
        logger.error(u"PlexPy Notifier :: Unable to retrieve metadata for rating_key %s" % str(session['rating_key']))
        return []

    # TODO: There must be a better way to do this. Laziness.
    # Check for exclusion tags
    if session['media_type'] == 'episode':
        on_start_subject = strip_tag(re.sub('<movie>[^>]+.</movie>|<music>[^>]+.</music>', '',
                                            plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT))
        on_start_body = strip_tag(re.sub('<movie>[^>]+.</movie>|<music>[^>]+.</music>', '',
                                         plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT))
        on_stop_subject = strip_tag(re.sub('<movie>[^>]+.</movie>|<music>[^>]+.</music>', '',
                                           plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT))
        on_stop_body = strip_tag(re.sub('<movie>[^>]+.</movie>|<music>[^>]+.</music>', '',
                                        plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT))
        on_watched_subject = strip_tag(re.sub('<movie>[^>]+.</movie>|<music>[^>]+.</music>', '',
                                              plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT))
        on_watched_body = strip_tag(re.sub('<movie>[^>]+.</movie>|<music>[^>]+.</music>', '',
                                           plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT))
    elif session['media_type'] == 'movie':
        on_start_subject = strip_tag(re.sub('<tv>[^>]+.</tv>|<music>[^>]+.</music>', '',
                                            plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT))
        on_start_body = strip_tag(re.sub('<tv>[^>]+.</tv>|<music>[^>]+.</music>', '',
                                         plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT))
        on_stop_subject = strip_tag(re.sub('<tv>[^>]+.</tv>|<music>[^>]+.</music>', '',
                                           plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT))
        on_stop_body = strip_tag(re.sub('<tv>[^>]+.</tv>|<music>[^>]+.</music>', '',
                                        plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT))
        on_watched_subject = strip_tag(re.sub('<tv>[^>]+.</tv>|<music>[^>]+.</music>', '',
                                              plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT))
        on_watched_body = strip_tag(re.sub('<tv>[^>]+.</tv>|<music>[^>]+.</music>', '',
                                           plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT))
    elif session['media_type'] == 'track':
        on_start_subject = strip_tag(re.sub('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', '',
                                            plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT))
        on_start_body = strip_tag(re.sub('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', '',
                                         plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT))
        on_stop_subject = strip_tag(re.sub('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', '',
                                           plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT))
        on_stop_body = strip_tag(re.sub('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', '',
                                        plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT))
        on_watched_subject = strip_tag(re.sub('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', '',
                                              plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT))
        on_watched_body = strip_tag(re.sub('<tv>[^>]+.</tv>|<movie>[^>]+.</movie>', '',
                                           plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT))
    else:
        on_start_subject = plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT
        on_start_body = plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT
        on_stop_subject = plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT
        on_stop_body = plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT
        on_watched_subject = plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT
        on_watched_body = plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT

    # Create a title
    if session['media_type'] == 'episode':
        full_title = '%s - %s' % (session['grandparent_title'],
                                  session['title'])
    elif session['media_type'] == 'track':
        full_title = '%s - %s' % (session['grandparent_title'],
                                  session['title'])
    else:
        full_title = session['title']

    # Generate a combined transcode decision value
    if session['video_decision']:
        if session['video_decision'] == 'transcode':
            transcode_decision = 'Transcode'
        elif session['video_decision'] == 'copy' or session['audio_decision'] == 'copy':
            transcode_decision = 'Direct Stream'
        else:
            transcode_decision = 'Direct Play'
    else:
        if session['audio_decision'] == 'transcode':
            transcode_decision = 'Transcode'
        else:
            transcode_decision = 'Direct Play'

    duration = helpers.convert_milliseconds_to_minutes(item_metadata['duration'])
    view_offset = helpers.convert_milliseconds_to_minutes(session['view_offset'])

    progress_percent = helpers.get_percent(view_offset, duration)

    available_params = {'server_name': server_name,
                        'user': session['friendly_name'],
                        'player': session['player'],
                        'title': full_title,
                        'show_name': item_metadata['grandparent_title'],
                        'episode_name': item_metadata['title'],
                        'platform': session['platform'],
                        'media_type': session['media_type'],
                        'transcode_decision': transcode_decision,
                        'year': item_metadata['year'],
                        'studio': item_metadata['studio'],
                        'content_rating': item_metadata['content_rating'],
                        'summary': item_metadata['summary'],
                        'season_num': item_metadata['parent_index'],
                        'episode_num': item_metadata['index'],
                        'album_name': item_metadata['parent_title'],
                        'rating': item_metadata['rating'],
                        'duration': duration,
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
                subject_text = on_start_subject.format(**available_params)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using default.")

            try:
                body_text = on_start_body.format(**available_params)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using default.")

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
                subject_text = on_stop_subject.format(**available_params)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using default.")

            try:
                body_text = on_stop_body.format(**available_params)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using default.")

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
                subject_text = on_watched_subject.format(**available_params)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification subject. Using default.")

            try:
                body_text = on_watched_body.format(**available_params)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using default.")

            return [subject_text, body_text]
        else:
            return [subject_text, body_text]
    else:
        return None

def strip_tag(data):
    import re

    p = re.compile(r'<.*?>')
    return p.sub('', data)