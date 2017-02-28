﻿#  This file is part of PlexPy.
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


import arrow
import bleach
import os
import re
import threading
import time

import plexpy
import database
import datafactory
import libraries
import logger
import helpers
import notifiers
import plextv
import pmsconnect
import users

def notify(stream_data=None, notify_action=None):
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
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_stop'] and notify_action == 'stop' \
                    and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < plexpy.CONFIG.NOTIFY_WATCHED_PERCENT):
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_pause'] and notify_action == 'pause' \
                    and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99):
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_resume'] and notify_action == 'resume' \
                    and (plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99):
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_buffer'] and notify_action == 'buffer':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_watched'] and notify_action == 'watched':
                    # Get the current states for notifications from our db
                    notify_states = get_notify_state(session=stream_data)

                    # If there is nothing in the notify_log for our agent id but it is enabled we should notify
                    if not any(d['agent_id'] == agent['id'] and d['notify_action'] == notify_action for d in notify_states):
                        # Build and send notification
                        notify_strings, metadata = build_notify_text(session=stream_data,
                                                                     notify_action=notify_action,
                                                                     agent_id=agent['id'])

                        notifiers.send_notification(agent_id=agent['id'],
                                                    subject=notify_strings[0],
                                                    body=notify_strings[1],
                                                    script_args=notify_strings[2],
                                                    notify_action=notify_action,
                                                    metadata=metadata)

                        # Set the notification state in the db
                        set_notify_state(session=stream_data,
                                         notify_action=notify_action,
                                         agent_info=agent,
                                         notify_strings=notify_strings,
                                         metadata=metadata)

                elif agent['on_concurrent'] and notify_action == 'concurrent':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_newdevice'] and notify_action == 'newdevice':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

        elif (stream_data['media_type'] == 'track' and plexpy.CONFIG.MUSIC_NOTIFY_ENABLE):

            for agent in notifiers.available_notification_agents():
                if agent['on_play'] and notify_action == 'play':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_stop'] and notify_action == 'stop':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_pause'] and notify_action == 'pause':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_resume'] and notify_action == 'resume':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_buffer'] and notify_action == 'buffer':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_concurrent'] and notify_action == 'concurrent':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

                elif agent['on_newdevice'] and notify_action == 'newdevice':
                    # Build and send notification
                    notify_strings, metadata = build_notify_text(session=stream_data,
                                                                 notify_action=notify_action,
                                                                 agent_id=agent['id'])

                    notifiers.send_notification(agent_id=agent['id'],
                                                subject=notify_strings[0],
                                                body=notify_strings[1],
                                                script_args=notify_strings[2],
                                                notify_action=notify_action,
                                                metadata=metadata)

                    # Set the notification state in the db
                    set_notify_state(session=stream_data,
                                     notify_action=notify_action,
                                     agent_info=agent,
                                     notify_strings=notify_strings,
                                     metadata=metadata)

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
                notify_strings, metadata = build_notify_text(timeline=timeline_data,
                                                             notify_action=notify_action,
                                                             agent_id=agent['id'])

                notifiers.send_notification(agent_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            script_args=notify_strings[2],
                                            notify_action=notify_action,
                                            metadata=metadata)

                # Set the notification state in the db
                set_notify_state(session=timeline_data,
                                 notify_action=notify_action,
                                 agent_info=agent,
                                 notify_strings=notify_strings,
                                 metadata=metadata)

    elif not timeline_data and notify_action:
        for agent in notifiers.available_notification_agents():
            if agent['on_extdown'] and notify_action == 'extdown':
                # Build and send notification
                notify_strings = build_server_notify_text(notify_action=notify_action,
                                                          agent_id=agent['id'])

                notifiers.send_notification(agent_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            script_args=notify_strings[2],
                                            notify_action=notify_action)

                # Set the notification state in the db
                set_notify_state(notify_action=notify_action,
                                 agent_info=agent,
                                 notify_strings=notify_strings)

            if agent['on_intdown'] and notify_action == 'intdown':
                # Build and send notification
                notify_strings = build_server_notify_text(notify_action=notify_action,
                                                          agent_id=agent['id'])

                notifiers.send_notification(agent_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            script_args=notify_strings[2],
                                            notify_action=notify_action)

                # Set the notification state in the db
                set_notify_state(notify_action=notify_action,
                                 agent_info=agent,
                                 notify_strings=notify_strings)

            if agent['on_extup'] and notify_action == 'extup':
                # Build and send notification
                notify_strings = build_server_notify_text(notify_action=notify_action,
                                                          agent_id=agent['id'])

                notifiers.send_notification(agent_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            script_args=notify_strings[2],
                                            notify_action=notify_action)

                # Set the notification state in the db
                set_notify_state(notify_action=notify_action,
                                 agent_info=agent,
                                 notify_strings=notify_strings)

            if agent['on_intup'] and notify_action == 'intup':
                # Build and send notification
                notify_strings = build_server_notify_text(notify_action=notify_action,
                                                          agent_id=agent['id'])

                notifiers.send_notification(agent_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            script_args=notify_strings[2],
                                            notify_action=notify_action)

                # Set the notification state in the db
                set_notify_state(notify_action=notify_action,
                                 agent_info=agent,
                                 notify_strings=notify_strings)

            if agent['on_pmsupdate'] and notify_action == 'pmsupdate':
                # Build and send notification
                notify_strings = build_server_notify_text(notify_action=notify_action,
                                                          agent_id=agent['id'])

                notifiers.send_notification(agent_id=agent['id'],
                                            subject=notify_strings[0],
                                            body=notify_strings[1],
                                            script_args=notify_strings[2],
                                            notify_action=notify_action)

                # Set the notification state in the db
                set_notify_state(notify_action=notify_action,
                                 agent_info=agent,
                                 notify_strings=notify_strings)

    else:
        logger.debug(u"PlexPy NotificationHandler :: Notify timeline called but incomplete data received.")


def get_notify_state(session):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT timestamp, notify_action, agent_id '
                               'FROM notify_log '
                               'WHERE session_key = ? '
                               'AND rating_key = ? '
                               'AND user_id = ? '
                               'ORDER BY id DESC',
                               args=[session['session_key'], session['rating_key'], session['user_id']])
    notify_states = []
    for item in result:
        notify_state = {'timestamp': item['timestamp'],
                        'notify_action': item['notify_action'],
                        'agent_id': item['agent_id']}
        notify_states.append(notify_state)

    return notify_states


def set_notify_state(notify_action, agent_info, notify_strings, session=None, metadata=None):

    if notify_action and agent_info:
        monitor_db = database.MonitorDatabase()

        session = session or {}
        metadata = metadata or {}

        if notify_strings[2]:
            script_args = '[' + ', '.join(notify_strings[2]) + ']'
        else:
            script_args = None

        keys = {'timestamp': int(time.time()),
                'session_key': session.get('session_key', None),
                'rating_key': session.get('rating_key', None),
                'user_id': session.get('user_id', None),
                'agent_id': agent_info['id'],
                'notify_action': notify_action}

        values = {'parent_rating_key': session.get('parent_rating_key', None),
                  'grandparent_rating_key': session.get('grandparent_rating_key', None),
                  'user': session.get('user', None),
                  'agent_name': agent_info['name'],
                  'subject_text': notify_strings[0],
                  'body_text': notify_strings[1],
                  'script_args': script_args,
                  'poster_url': metadata.get('poster_url', None)}

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to set notify state.")


def build_notify_text(session=None, timeline=None, notify_action=None, agent_id=None):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','')
    duration_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','').replace('a','').replace('A','')

    # Get the server name
    server_name = plexpy.CONFIG.PMS_NAME

    # Get the server uptime
    plex_tv = plextv.PlexTV()
    server_times = plex_tv.get_server_times()

    if server_times:
        updated_at = server_times['updated_at']
        server_uptime = helpers.human_duration(int(time.time() - helpers.cast_to_int(updated_at)))
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

    current_activity = pms_connect.get_current_activity()
    sessions = current_activity.get('sessions', [])
    stream_count = current_activity.get('stream_count', '')
    user_stream_count = sum(1 for d in sessions if d['user_id'] == session['user_id']) if session else ''

    if metadata_list:
        metadata = metadata_list['metadata']
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))
        return [None, None, None], None

    # Check for exclusion tags
    if metadata['media_type'] == 'movie':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile(r'<movie>|</movie>|<tv>.*?</tv>|<music>.*?</music>', re.IGNORECASE | re.DOTALL)
    elif metadata['media_type'] == 'show' or metadata['media_type'] == 'episode':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile(r'<movie>.*?</movie>|<tv>|</tv>|<music>.*?</music>', re.IGNORECASE | re.DOTALL)
    elif metadata['media_type'] == 'artist' or metadata['media_type'] == 'track':
        # Regex pattern to remove the text in the tags we don't want
        pattern = re.compile(r'<movie>.*?</movie>|<tv>.*?</tv>|<music>|</music>', re.IGNORECASE | re.DOTALL)
    else:
        pattern = None

    if metadata['media_type'] == 'movie' \
        or metadata['media_type'] == 'show' or metadata['media_type'] == 'episode' \
        or metadata['media_type'] == 'artist' or metadata['media_type'] == 'track' \
        and pattern:
        # Remove the unwanted tags and strip any unmatch tags too.
        on_start_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT), agent_id)
        on_start_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT), agent_id)
        on_stop_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT), agent_id)
        on_stop_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT), agent_id)
        on_pause_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT), agent_id)
        on_pause_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT), agent_id)
        on_resume_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT), agent_id)
        on_resume_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT), agent_id)
        on_buffer_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT), agent_id)
        on_buffer_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT), agent_id)
        on_watched_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT), agent_id)
        on_watched_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT), agent_id)
        on_created_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_CREATED_SUBJECT_TEXT), agent_id)
        on_created_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_CREATED_BODY_TEXT), agent_id)
        on_concurrent_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_CONCURRENT_SUBJECT_TEXT), agent_id)
        on_concurrent_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_CONCURRENT_BODY_TEXT), agent_id)
        on_newdevice_subject = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_NEWDEVICE_SUBJECT_TEXT), agent_id)
        on_newdevice_body = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_ON_NEWDEVICE_BODY_TEXT), agent_id)
        script_args_text = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT), agent_id)
    else:
        on_start_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT, agent_id)
        on_start_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT, agent_id)
        on_stop_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT, agent_id)
        on_stop_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT, agent_id)
        on_pause_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT, agent_id)
        on_pause_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT, agent_id)
        on_resume_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT, agent_id)
        on_resume_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT, agent_id)
        on_buffer_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT, agent_id)
        on_buffer_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT, agent_id)
        on_watched_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT, agent_id)
        on_watched_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT, agent_id)
        on_created_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_CREATED_SUBJECT_TEXT, agent_id)
        on_created_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_CREATED_BODY_TEXT, agent_id)
        on_concurrent_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_CONCURRENT_SUBJECT_TEXT, agent_id)
        on_concurrent_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_CONCURRENT_BODY_TEXT, agent_id)
        on_newdevice_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_NEWDEVICE_SUBJECT_TEXT, agent_id)
        on_newdevice_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_NEWDEVICE_BODY_TEXT, agent_id)
        script_args_text = strip_tag(plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT, agent_id)

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
    
    if notify_action != 'play':
        stream_duration = int((time.time() -
                               helpers.cast_to_int(session.get('started', 0)) -
                               helpers.cast_to_int(session.get('paused_counter', 0))) / 60)
    else:
        stream_duration = 0

    view_offset = helpers.convert_milliseconds_to_minutes(session.get('view_offset', 0))
    duration = helpers.convert_milliseconds_to_minutes(metadata['duration'])
    progress_percent = helpers.get_percent(view_offset, duration)
    remaining_duration = duration - view_offset

    # Build Plex URL
    #metadata['plex_url'] = 'https://app.plex.tv/web/app#!/server/{0}/details/%2Flibrary%2Fmetadata%2F{1}'.format(
    metadata['plex_url'] = 'https://app.plex.tv/web/app#!/server/{0}/details?get=%2Flibrary%2Fmetadata%2F{1}'.format(
        plexpy.CONFIG.PMS_IDENTIFIER, str(rating_key))

    # Get media IDs from guid and build URLs
    if 'imdb://' in metadata['guid']:
        metadata['imdb_id'] = metadata['guid'].split('imdb://')[1].split('?')[0]
        metadata['imdb_url'] = 'https://www.imdb.com/title/' + metadata['imdb_id']
        metadata['trakt_url'] = 'https://trakt.tv/search/imdb/' + metadata['imdb_id']

    if 'thetvdb://' in metadata['guid']:
        metadata['thetvdb_id'] = metadata['guid'].split('thetvdb://')[1].split('/')[0]
        metadata['thetvdb_url'] = 'https://thetvdb.com/?tab=series&id=' + metadata['thetvdb_id']
        metadata['trakt_url'] = 'https://trakt.tv/search/tvdb/' + metadata['thetvdb_id'] + '?id_type=show'

    elif 'thetvdbdvdorder://' in metadata['guid']:
        metadata['thetvdb_id'] = metadata['guid'].split('thetvdbdvdorder://')[1].split('/')[0]
        metadata['thetvdb_url'] = 'https://thetvdb.com/?tab=series&id=' + metadata['thetvdb_id']
        metadata['trakt_url'] = 'https://trakt.tv/search/tvdb/' + metadata['thetvdb_id'] + '?id_type=show'

    if 'themoviedb://' in metadata['guid']:
        if metadata['media_type'] == 'movie':
            metadata['themoviedb_id'] = metadata['guid'].split('themoviedb://')[1].split('?')[0]
            metadata['themoviedb_url'] = 'https://www.themoviedb.org/movie/' + metadata['themoviedb_id']
            metadata['trakt_url'] = 'https://trakt.tv/search/tmdb/' + metadata['themoviedb_id'] + '?id_type=movie'

        elif metadata['media_type'] == 'show' or metadata['media_type'] == 'episode':
            metadata['themoviedb_id'] = metadata['guid'].split('themoviedb://')[1].split('/')[0]
            metadata['themoviedb_url'] = 'https://www.themoviedb.org/tv/' + metadata['themoviedb_id']
            metadata['trakt_url'] = 'https://trakt.tv/search/tmdb/' + metadata['themoviedb_id'] + '?id_type=show'

    if 'lastfm://' in metadata['guid']:
        metadata['lastfm_id'] = metadata['guid'].split('lastfm://')[1].rsplit('/', 1)[0]
        metadata['lastfm_url'] = 'https://www.last.fm/music/' + metadata['lastfm_id']

    if metadata['media_type'] == 'movie' or metadata['media_type'] == 'show' or metadata['media_type'] == 'artist':
        thumb = metadata['thumb']
        poster_key = metadata['rating_key']
        poster_title = metadata['title']
    elif metadata['media_type'] == 'episode':
        thumb = metadata['grandparent_thumb']
        poster_key = metadata['grandparent_rating_key']
        poster_title = metadata['grandparent_title']
    elif metadata['media_type'] == 'track':
        thumb = metadata['parent_thumb']
        poster_key = metadata['parent_rating_key']
        poster_title = metadata['parent_title']
    else:
        thumb = None

    if plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS and thumb:
        # Try to retrieve a poster_url from the database
        data_factory = datafactory.DataFactory()
        poster_url = data_factory.get_poster_url(rating_key=poster_key)

        # If no previous poster_url
        if not poster_url and plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS:
            try:
                thread_name = str(threading.current_thread().ident)
                poster_file = os.path.join(plexpy.CONFIG.CACHE_DIR, 'cache-poster-%s' % thread_name)

                # Retrieve the poster from Plex and cache to file
                result = pms_connect.get_image(img=thumb)
                if result and result[0]:
                    with open(poster_file, 'wb') as f:
                        f.write(result[0])
                else:
                    raise Exception(u'PMS image request failed')

                # Upload thumb to Imgur and get link
                poster_url = helpers.uploadToImgur(poster_file, poster_title)

                # Delete the cached poster
                os.remove(poster_file)
            except Exception as e:
                logger.error(u"PlexPy Notifier :: Unable to retrieve poster for rating_key %s: %s." % (str(rating_key), e))

        metadata['poster_url'] = poster_url

    # Fix metadata params for notify recently added grandparent
    if notify_action == 'created' and plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_GRANDPARENT:
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
                        'server_version': server_times.get('version',''),
                        'action': notify_action.title(),
                        'datestamp': arrow.now().format(date_format),
                        'timestamp': arrow.now().format(time_format),
                        # Stream parameters
                        'streams': stream_count,
                        'user_streams': user_stream_count,
                        'user': session.get('friendly_name',''),
                        'username': session.get('user',''),
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
                        'transcode_key': session.get('transcode_key',''),
                        'user_id': session.get('user_id',''),
                        'machine_id': session.get('machine_id',''),
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
                        'release_date': arrow.get(metadata['originally_available_at']).format(date_format)
                            if metadata['originally_available_at'] else '',
                        'air_date': arrow.get(metadata['originally_available_at']).format(date_format)
                            if metadata['originally_available_at'] else '',
                        'added_date': arrow.get(metadata['added_at']).format(date_format)
                            if metadata['added_at'] else '',
                        'updated_date': arrow.get(metadata['updated_at']).format(date_format)
                            if metadata['updated_at'] else '',
                        'last_viewed_date': arrow.get(metadata['last_viewed_at']).format(date_format)
                            if metadata['last_viewed_at'] else '',
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
                        'poster_url': metadata.get('poster_url',''),
                        'plex_url': metadata.get('plex_url',''),
                        'imdb_id': metadata.get('imdb_id',''),
                        'imdb_url': metadata.get('imdb_url',''),
                        'thetvdb_id': metadata.get('thetvdb_id',''),
                        'thetvdb_url': metadata.get('thetvdb_url',''),
                        'themoviedb_id': metadata.get('themoviedb_id',''),
                        'themoviedb_url': metadata.get('themoviedb_url',''),
                        'lastfm_url': metadata.get('lastfm_url',''),
                        'trakt_url': metadata.get('trakt_url',''),
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
            logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in script argument. Using fallback." % e)
        except Exception as e:
            logger.error(u"PlexPy NotificationHandler :: Unable to parse custom script arguments %s. Using fallback." % e)

    if notify_action == 'play':
        # Default body text
        body_text = '%s (%s) started playing %s' % (session['friendly_name'],
                                                    session['player'],
                                                    full_title)

        if on_start_subject and on_start_body:
            try:
                subject_text = unicode(on_start_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_start_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'stop':
        # Default body text
        body_text = '%s (%s) has stopped %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_stop_subject and on_stop_body:
            try:
                subject_text = unicode(on_stop_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_stop_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'pause':
        # Default body text
        body_text = '%s (%s) has paused %s' % (session['friendly_name'],
                                               session['player'],
                                               full_title)

        if on_pause_subject and on_pause_body:
            try:
                subject_text = unicode(on_pause_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_pause_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'resume':
        # Default body text
        body_text = '%s (%s) has resumed %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_resume_subject and on_resume_body:
            try:
                subject_text = unicode(on_resume_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_resume_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'buffer':
        # Default body text
        body_text = '%s (%s) is buffering %s' % (session['friendly_name'],
                                                 session['player'],
                                                 full_title)

        if on_buffer_subject and on_buffer_body:
            try:
                subject_text = unicode(on_buffer_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_buffer_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'watched':
        # Default body text
        body_text = '%s (%s) has watched %s' % (session['friendly_name'],
                                                session['player'],
                                                full_title)

        if on_watched_subject and on_watched_body:
            try:
                subject_text = unicode(on_watched_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_watched_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'created':
        # Default body text
        body_text = '%s was recently added to Plex.' % full_title

        if on_created_subject and on_created_body:
            try:
                subject_text = unicode(on_created_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_created_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'concurrent':
        # Default body text
        body_text = '%s has %s concurrent streams.' % (session['friendly_name'],
                                                         user_stream_count)

        if on_concurrent_subject and on_concurrent_body:
            try:
                subject_text = unicode(on_concurrent_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_concurrent_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    elif notify_action == 'newdevice':
        # Default body text
        body_text = '%s is streaming from a new device: %s.' % (session['friendly_name'],
                                                                session['player'])

        if on_newdevice_subject and on_newdevice_body:
            try:
                subject_text = unicode(on_newdevice_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_newdevice_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args], metadata
        else:
            return [subject_text, body_text, script_args], metadata
    else:
        return [None, None, None], None


def build_server_notify_text(notify_action=None, agent_id=None):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','')

    # Get the server name
    server_name = plexpy.CONFIG.PMS_NAME

    # Get the server uptime
    plex_tv = plextv.PlexTV()
    server_times = plex_tv.get_server_times()

    update_status = {}
    if notify_action == 'pmsupdate':
        update_status = plex_tv.get_plex_downloads()

    if server_times:
        updated_at = server_times['updated_at']
        server_uptime = helpers.human_duration(int(time.time() - helpers.cast_to_int(updated_at)))
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve server uptime.")
        server_uptime = 'N/A'

    pattern = re.compile(r'<movie>.*?</movie>|<tv>.*?</tv>|<music>.*?</music>', re.IGNORECASE | re.DOTALL)

    on_extdown_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_EXTDOWN_SUBJECT_TEXT, agent_id)
    on_extdown_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_EXTDOWN_BODY_TEXT, agent_id)
    on_intdown_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_INTDOWN_SUBJECT_TEXT, agent_id)
    on_intdown_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_INTDOWN_BODY_TEXT, agent_id)
    on_extup_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_EXTUP_SUBJECT_TEXT, agent_id)
    on_extup_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_EXTUP_BODY_TEXT, agent_id)
    on_intup_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_INTUP_SUBJECT_TEXT, agent_id)
    on_intup_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_INTUP_BODY_TEXT, agent_id)
    on_pmsupdate_subject = strip_tag(plexpy.CONFIG.NOTIFY_ON_PMSUPDATE_SUBJECT_TEXT, agent_id)
    on_pmsupdate_body = strip_tag(plexpy.CONFIG.NOTIFY_ON_PMSUPDATE_BODY_TEXT, agent_id)
    script_args_text = strip_tag(re.sub(pattern, '', plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT), agent_id)

    available_params = {# Global paramaters
                        'server_name': server_name,
                        'server_uptime': server_uptime,
                        'server_version': server_times.get('version',''),
                        'action': notify_action.title(),
                        'datestamp': arrow.now().format(date_format),
                        'timestamp': arrow.now().format(time_format),
                        # Update parameters
                        'update_version': update_status.get('version',''),
                        'update_url': update_status.get('download_url',''),
                        'update_release_date': arrow.get(update_status.get('release_date','')).format(date_format)
                            if update_status.get('release_date','') else '',
                        'update_channel': 'Plex Pass' if plexpy.CONFIG.PMS_UPDATE_CHANNEL == 'plexpass' else 'Public',
                        'update_platform': update_status.get('platform',''),
                        'update_distro': update_status.get('distro',''),
                        'update_distro_build': update_status.get('build',''),
                        'update_requirements': update_status.get('requirements',''),
                        'update_extra_info': update_status.get('extra_info',''),
                        'update_changelog_added': update_status.get('changelog_added',''),
                        'update_changelog_fixed': update_status.get('changelog_fixed','')}

    # Default text
    subject_text = 'PlexPy (%s)' % server_name

    # Default scripts args
    script_args = []

    if script_args_text:
        try:
            script_args = [unicode(arg).format(**available_params) for arg in script_args_text.split()]
        except LookupError as e:
            logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in script argument. Using fallback." % e)
        except Exception as e:
            logger.error(u"PlexPy NotificationHandler :: Unable to parse custom script arguments %s. Using fallback." % e)

    if notify_action == 'extdown':
        # Default body text
        body_text = 'The Plex Media Server remote access is down.'

        if on_extdown_subject and on_extdown_body:
            try:
                subject_text = unicode(on_extdown_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_extdown_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy Notifier :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]

    elif notify_action == 'intdown':
        # Default body text
        body_text = 'The Plex Media Server is down.'

        if on_intdown_subject and on_intdown_body:
            try:
                subject_text = unicode(on_intdown_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_intdown_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    if notify_action == 'extup':
        # Default body text
        body_text = 'The Plex Media Server remote access is back up.'

        if on_extup_subject and on_extup_body:
            try:
                subject_text = unicode(on_extup_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_extup_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]
    elif notify_action == 'intup':
        # Default body text
        body_text = 'The Plex Media Server is back up.'

        if on_intup_subject and on_intup_body:
            try:
                subject_text = unicode(on_intup_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_intup_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]

    elif notify_action == 'pmsupdate':
        # Default body text
        body_text = 'An update is available for the Plex Media Server (version %s).' % available_params['update_version']

        if on_pmsupdate_subject and on_pmsupdate_body:
            try:
                subject_text = unicode(on_pmsupdate_subject).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")

            try:
                body_text = unicode(on_pmsupdate_body).format(**available_params)
            except LookupError as e:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
            except:
                logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")

            return [subject_text, body_text, script_args]
        else:
            return [subject_text, body_text, script_args]

    else:
        return None


def strip_tag(data, agent_id=None):

    if agent_id == 7:
        # Allow tags b, i, u, a[href], font[color] for Pushover
        whitelist = {'b': [],
                     'i': [],
                     'u': [],
                     'a': ['href'],
                     'font': ['color']}
        return bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)

    elif agent_id == 10:
        # Don't remove tags for email
        return data

    elif agent_id == 13:
        # Allow tags b, i, code, pre, a[href] for Telegram
        whitelist = {'b': [],
                     'i': [],
                     'code': [],
                     'pre': [],
                     'a': ['href']}
        return bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)

    else:
        whitelist = {}
        return bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)
