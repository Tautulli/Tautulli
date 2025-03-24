# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
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

import bleach
from collections import Counter, defaultdict
from functools import partial
import hashlib
from itertools import groupby
import json
from operator import itemgetter
import os
import re
from string import Formatter
import threading
from typing import Optional

import arrow
import musicbrainzngs

import plexpy
from plexpy import activity_processor
from plexpy import common
from plexpy import database
from plexpy import datafactory
from plexpy import logger
from plexpy import helpers
from plexpy import notifiers
from plexpy import pmsconnect
from plexpy import request
from plexpy.newsletter_handler import notify as notify_newsletter


def process_queue():
    queue = plexpy.NOTIFY_QUEUE
    while True:
        params = queue.get()
        
        if params is None:
            break
        elif params:
            try:
                if 'newsletter' in params:
                    notify_newsletter(**params)
                elif 'notification' in params:
                    notify(**params)
                else:
                    add_notifier_each(**params)
            except Exception as e:
                logger.exception("Tautulli NotificationHandler :: Notification thread exception: %s" % e)

        queue.task_done()

    logger.info("Tautulli NotificationHandler :: Notification thread exiting...")


def start_threads(num_threads=1):
    logger.info("Tautulli NotificationHandler :: Starting background notification handler ({} threads).".format(num_threads))
    for x in range(num_threads):
        thread = threading.Thread(target=process_queue)
        thread.daemon = True
        thread.start()


def add_notifier_each(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, manual_trigger=False, **kwargs):
    if not notify_action:
        logger.debug("Tautulli NotificationHandler :: Notify called but no action received.")
        return

    if notifier_id:
        # Send to a specific notifier regardless if it is enabled
        notifiers_enabled = notifiers.get_notifiers(notifier_id=notifier_id)
    else:
        # Check if any notification agents have notifications enabled for the action
        notifiers_enabled = notifiers.get_notifiers(notify_action=notify_action)

    if notifiers_enabled and not manual_trigger:
        logger.debug("Tautulli NotificationHandler :: Notifiers enabled for notify_action '%s'." % notify_action)

        # Check if notification conditions are satisfied
        conditions = notify_conditions(notify_action=notify_action,
                                       stream_data=stream_data,
                                       timeline_data=timeline_data,
                                       **kwargs)
    else:
        conditions = True

    if notifiers_enabled and (manual_trigger or conditions):
        if manual_trigger:
            logger.debug("Tautulli NotificationHandler :: Notifiers enabled for notify_action '%s' (manual trigger)." % notify_action)

        if stream_data or timeline_data:
            # Build the notification parameters
            parameters = build_media_notify_params(notify_action=notify_action,
                                                   session=stream_data,
                                                   timeline=timeline_data,
                                                   manual_trigger=manual_trigger,
                                                   **kwargs)
        else:
            # Build the notification parameters
            parameters = build_server_notify_params(notify_action=notify_action,
                                                    **kwargs)

        if not parameters:
            logger.error("Tautulli NotificationHandler :: Failed to build notification parameters.")
            return

        for notifier in notifiers_enabled:
            # Check custom user conditions
            if manual_trigger or notify_custom_conditions(notifier_id=notifier['id'], parameters=parameters):
                # Add each notifier to the queue
                data = {'notification': True,
                        'notifier_id': notifier['id'],
                        'notify_action': notify_action,
                        'stream_data': stream_data,
                        'timeline_data': timeline_data,
                        'parameters': parameters}
                data.update(kwargs)
                plexpy.NOTIFY_QUEUE.put(data)
            else:
                logger.debug("Tautulli NotificationHandler :: Custom notification conditions not satisfied, skipping notifier_id %s." % notifier['id'])

    # Add on_concurrent and on_newdevice to queue if action is on_play
    if notify_action == 'on_play':
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data.copy(), 'notify_action': 'on_concurrent'})
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data.copy(), 'notify_action': 'on_newdevice'})


def notify_conditions(notify_action=None, stream_data=None, timeline_data=None, **kwargs):
    logger.debug("Tautulli NotificationHandler :: Checking global notification conditions.")
    evaluated = False

    # Activity notifications
    if stream_data:
        # Check if notifications enabled for user and library
        # user_data = users.Users()
        # user_details = user_data.get_details(user_id=stream_data['user_id'])
        #
        # library_data = libraries.Libraries()
        # library_details = library_data.get_details(section_id=stream_data['section_id'])

        # if not user_details['do_notify']:
        #     logger.debug("Tautulli NotificationHandler :: Notifications for user '%s' are disabled." % user_details['username'])
        #     return False
        #
        # elif not library_details['do_notify'] and notify_action not in ('on_concurrent', 'on_newdevice'):
        #     logger.debug("Tautulli NotificationHandler :: Notifications for library '%s' are disabled." % library_details['section_name'])
        #     return False

        if notify_action == 'on_concurrent':
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_current_activity()

            user_sessions = []
            if result:
                user_sessions = [s for s in result['sessions'] if s['user_id'] == stream_data['user_id']]

            if plexpy.CONFIG.NOTIFY_CONCURRENT_BY_IP:
                ip_addresses = set()
                for s in user_sessions:
                    if helpers.ip_type(s['ip_address']) == 'IPv6':
                        ip_addresses.add(helpers.get_ipv6_network_address(s['ip_address']))
                    elif helpers.ip_type(s['ip_address']) == 'IPv4':
                        ip_addresses.add(s['ip_address'])
                evaluated = len(ip_addresses) >= plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD
            else:
                evaluated = len(user_sessions) >= plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD

        elif notify_action == 'on_newdevice':
            data_factory = datafactory.DataFactory()
            user_devices = data_factory.get_user_devices(user_id=stream_data['user_id'],
                                                         history_only=not plexpy.CONFIG.NOTIFY_NEW_DEVICE_INITIAL_ONLY)
            evaluated = stream_data['machine_id'] not in user_devices

        elif stream_data['media_type'] in ('movie', 'episode', 'clip'):
            progress_percent = helpers.get_percent(stream_data['view_offset'], stream_data['duration'])

            if notify_action == 'on_stop':
                evaluated = (plexpy.CONFIG.NOTIFY_CONSECUTIVE or
                    (stream_data['media_type'] == 'movie' and progress_percent < plexpy.CONFIG.MOVIE_WATCHED_PERCENT) or 
                    (stream_data['media_type'] == 'episode' and progress_percent < plexpy.CONFIG.TV_WATCHED_PERCENT))

            elif notify_action == 'on_resume':
                evaluated = plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99

            # All other activity notify actions
            else:
                evaluated = True

        elif stream_data['media_type'] == 'track':
            evaluated = True

        else:
            evaluated = False

    # Recently Added notifications
    elif timeline_data:

        # Check if notifications enabled for library
        # library_data = libraries.Libraries()
        # library_details = library_data.get_details(section_id=timeline_data['section_id'])
        #
        # if not library_details['do_notify_created']:
        #     # logger.debug("Tautulli NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
        #     return False

        evaluated = True

    elif notify_action == 'on_pmsupdate':
        evaluated = True
        if not plexpy.CONFIG.NOTIFY_SERVER_UPDATE_REPEAT:
            evaluated = not check_nofity_tag(notify_action=notify_action,
                                             tag=kwargs['pms_download_info']['version'])

    elif notify_action == 'on_plexpyupdate':
        evaluated = True
        if not plexpy.CONFIG.NOTIFY_PLEXPY_UPDATE_REPEAT:
            evaluated = not check_nofity_tag(notify_action=notify_action,
                                             tag=kwargs['plexpy_download_info']['tag_name'])

    # Server notifications
    else:
        evaluated = True

    logger.debug("Tautulli NotificationHandler :: Global notification conditions evaluated to '{}'.".format(evaluated))
    return evaluated


def notify_custom_conditions(notifier_id=None, parameters=None):
    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    custom_conditions_logic = notifier_config['custom_conditions_logic']
    custom_conditions = notifier_config['custom_conditions']

    if custom_conditions_logic or any(c for c in custom_conditions if c['value']):
        logger.debug("Tautulli NotificationHandler :: Checking custom notification conditions for notifier_id %s."
                     % notifier_id)

        logic_groups = None
        if custom_conditions_logic:
            try:
                # Parse and validate the custom conditions logic
                logic_groups = helpers.parse_condition_logic_string(custom_conditions_logic, len(custom_conditions))
            except ValueError as e:
                logger.error("Tautulli NotificationHandler :: Unable to parse custom condition logic '%s': %s."
                             % (custom_conditions_logic, e))
                return False

        evaluated_conditions = [None]  # Set condition {0} to None

        for i, condition in enumerate(custom_conditions):
            parameter = condition['parameter']
            operator = condition['operator']
            values = condition['value']
            parameter_type = condition['type']
            parameter_value = parameters.get(parameter, "")

            # Set blank conditions to True (skip)
            if not parameter or not operator or not values:
                evaluated = True
                evaluated_conditions.append(evaluated)
                logger.debug("Tautulli NotificationHandler :: {%s} Blank condition > %s" % (i+1, evaluated))
                continue

            # Make sure the condition values is in a list
            if not isinstance(values, list):
                values = [values]

            # Cast the condition values to the correct type
            try:
                if parameter_type == 'str':
                    values = ['' if v == '~' else str(v).strip().lower() for v in values]

                elif parameter_type == 'int':
                    values = [helpers.cast_to_int(v) for v in values]

                elif parameter_type == 'float':
                    values = [helpers.cast_to_float(v) for v in values]

                else:
                    raise ValueError

            except ValueError as e:
                logger.error("Tautulli NotificationHandler :: {%s} Unable to cast condition '%s', values '%s', to type '%s'."
                             % (i+1, parameter, values, parameter_type))
                return False

            # Cast the parameter value to the correct type
            try:
                if parameter_type == 'str':
                    parameter_value = str(parameter_value).strip().lower()

                elif parameter_type == 'int':
                    parameter_value = helpers.cast_to_int(parameter_value)

                elif parameter_type == 'float':
                    parameter_value = helpers.cast_to_float(parameter_value)

                else:
                    raise ValueError

            except ValueError as e:
                logger.error("Tautulli NotificationHandler :: {%s} Unable to cast parameter '%s', value '%s', to type '%s'."
                             % (i+1, parameter, parameter_value, parameter_type))
                return False

            # Check each condition
            if operator == 'contains':
                evaluated = any(c in parameter_value for c in values)

            elif operator == 'does not contain':
                evaluated = all(c not in parameter_value for c in values)

            elif operator == 'is':
                evaluated = any(parameter_value == c for c in values)

            elif operator == 'is not':
                evaluated = all(parameter_value != c for c in values)

            elif operator == 'begins with':
                evaluated = parameter_value.startswith(tuple(values))

            elif operator == 'does not begin with':
                evaluated = not parameter_value.startswith(tuple(values))

            elif operator == 'ends with':
                evaluated = parameter_value.endswith(tuple(values))

            elif operator == 'does not end with':
                evaluated = not parameter_value.endswith(tuple(values))

            elif operator == 'is greater than':
                evaluated = any(parameter_value > c for c in values)

            elif operator == 'is less than':
                evaluated = any(parameter_value < c for c in values)

            else:
                evaluated = None
                logger.warn("Tautulli NotificationHandler :: {%s} Invalid condition operator '%s' > %s."
                            % (i+1, operator, evaluated))

            evaluated_conditions.append(evaluated)
            logger.debug("Tautulli NotificationHandler :: {%s} %s | %s | %s > '%s' > %s"
                         % (i+1, parameter, operator, ' or '.join(["'%s'" % v for v in values]), parameter_value, evaluated))

        if logic_groups:
            # Format and evaluate the logic string
            try:
                evaluated_logic = helpers.eval_logic_groups_to_bool(logic_groups, evaluated_conditions)
                logger.debug("Tautulli NotificationHandler :: Condition logic: %s > %s"
                             % (custom_conditions_logic, evaluated_logic))
            except Exception as e:
                logger.error("Tautulli NotificationHandler :: Unable to evaluate custom condition logic: %s." % e)
                return False
        else:
            evaluated_logic = all(evaluated_conditions[1:])
            logger.debug("Tautulli NotificationHandler :: Condition logic [blank]: %s > %s"
                         % (' and '.join(['{%s}' % (i+1) for i in range(len(custom_conditions))]), evaluated_logic))

        logger.debug("Tautulli NotificationHandler :: Custom conditions evaluated to '{}'. Conditions: {}.".format(
            evaluated_logic, evaluated_conditions[1:]))

        return evaluated_logic

    return True


def notify(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, parameters=None, **kwargs):
    logger.info("Tautulli NotificationHandler :: Preparing notification for notifier_id %s." % notifier_id)

    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    if not notifier_config:
        return

    if notify_action in ('test', 'api'):
        subject = kwargs.pop('subject', 'Tautulli')
        body = kwargs.pop('body', 'Test Notification')
        script_args = helpers.split_args(kwargs.pop('script_args', []))

    else:
        # Get the subject and body strings
        subject_string = notifier_config['notify_text'][notify_action]['subject']
        body_string = notifier_config['notify_text'][notify_action]['body']

        # Format the subject and body strings
        subject, body, script_args = build_notify_text(subject=subject_string,
                                                       body=body_string,
                                                       notify_action=notify_action,
                                                       parameters=parameters,
                                                       agent_id=notifier_config['agent_id'],
                                                       as_json=notifier_config['config'].get('as_json', False))

    # Set the notification state in the db
    notification_id = set_notify_state(session=stream_data or timeline_data,
                                       notifier=notifier_config,
                                       notify_action=notify_action,
                                       subject=subject,
                                       body=body,
                                       script_args=script_args,
                                       parameters=parameters)

    # Send the notification
    success = notifiers.send_notification(notifier_id=notifier_config['id'],
                                          subject=subject,
                                          body=body,
                                          script_args=script_args,
                                          notify_action=notify_action,
                                          notification_id=notification_id,
                                          parameters=parameters or {},
                                          **kwargs)

    if success:
        set_notify_success(notification_id)
        return notification_id


def get_notify_state(session):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select("SELECT timestamp, notify_action, notifier_id "
                               "FROM notify_log "
                               "WHERE session_key = ? "
                               "AND rating_key = ? "
                               "AND user_id = ? "
                               "ORDER BY id DESC",
                               args=[session['session_key'], session['rating_key'], session['user_id']])
    notify_states = []
    for item in result:
        notify_state = {'timestamp': item['timestamp'],
                        'notify_action': item['notify_action'],
                        'notifier_id': item['notifier_id']}
        notify_states.append(notify_state)

    return notify_states


def get_notify_state_enabled(session, notify_action, notified=True):
    if notified:
        timestamp_where = 'AND timestamp IS NOT NULL'
    else:
        timestamp_where = 'AND timestamp IS NULL'

    monitor_db = database.MonitorDatabase()
    result = monitor_db.select("SELECT id AS notifier_id, timestamp "
                               "FROM notifiers "
                               "LEFT OUTER JOIN ("
                               "SELECT timestamp, notifier_id "
                               "FROM notify_log "
                               "WHERE session_key = ? "
                               "AND rating_key = ? "
                               "AND user_id = ? "
                               "AND notify_action = ?) AS t ON notifiers.id = t.notifier_id "
                               "WHERE %s = 1 %s" % (notify_action, timestamp_where),
                               args=[session['session_key'], session['rating_key'], session['user_id'], notify_action])

    return result


def set_notify_state(notifier, notify_action, subject='', body='', script_args='', session=None, parameters=None):

    if notifier and notify_action:
        monitor_db = database.MonitorDatabase()

        session = session or {}

        script_args = json.dumps(script_args) if script_args else None

        keys = {'timestamp': helpers.timestamp(),
                'session_key': session.get('session_key', None),
                'rating_key': session.get('rating_key', None),
                'user_id': session.get('user_id', None),
                'notifier_id': notifier['id'],
                'agent_id': notifier['agent_id'],
                'notify_action': notify_action}

        values = {'parent_rating_key': session.get('parent_rating_key', None),
                  'grandparent_rating_key': session.get('grandparent_rating_key', None),
                  'user': session.get('user', None),
                  'agent_name': notifier['agent_name'],
                  'subject_text': subject,
                  'body_text': body,
                  'script_args': script_args}

        if notify_action == 'on_pmsupdate':
            values['tag'] = parameters['update_version']
        elif notify_action == 'on_plexpyupdate':
            values['tag'] = parameters['tautulli_update_version']

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
        return monitor_db.last_insert_id()
    else:
        logger.error("Tautulli NotificationHandler :: Unable to set notify state.")


def set_notify_success(notification_id):
    keys = {'id': notification_id}
    values = {'success': 1}

    monitor_db = database.MonitorDatabase()
    monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)


def check_nofity_tag(notify_action, tag):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select_single("SELECT * FROM notify_log "
                                      "WHERE notify_action = ? AND tag = ?",
                                      [notify_action, tag])
    return bool(result)


def build_media_notify_params(notify_action=None, session=None, timeline=None, manual_trigger=False, **kwargs):
    # Get time formats
    date_format = helpers.momentjs_to_arrow(plexpy.CONFIG.DATE_FORMAT)
    time_format = helpers.momentjs_to_arrow(plexpy.CONFIG.TIME_FORMAT)
    duration_format = helpers.momentjs_to_arrow(plexpy.CONFIG.TIME_FORMAT, duration=True)

    # Get metadata for the item
    if session:
        rating_key = session['rating_key']
    elif timeline:
        rating_key = timeline['rating_key']

    notify_params = defaultdict(str)
    if session:
        # Reload json from raw stream info
        if session.get('raw_stream_info'):
            raw_stream_info = json.loads(session['raw_stream_info'])
            # Don't overwrite id, session_key, stopped, view_offset
            raw_stream_info.pop('id', None)
            raw_stream_info.pop('session_key', None)
            raw_stream_info.pop('stopped', None)
            raw_stream_info.pop('view_offset', None)
            session.update(raw_stream_info)
        notify_params.update(session)

    if timeline:
        notify_params.update(timeline)

    ## TODO: Check list of media info items, currently only grabs first item
    media_info = media_part_info = {}
    if 'media_info' in notify_params and len(notify_params['media_info']) > 0:
        media_info = notify_params['media_info'][0]
        if 'parts' in media_info and len(media_info['parts']) > 0:
            parts = media_info.pop('parts')
            media_part_info = next((p for p in parts if p['selected']), parts[0])

    if 'streams' in media_part_info:
        streams = media_part_info.pop('streams')
        video_streams = [s for s in streams if s['type'] == '1']
        audio_streams = [s for s in streams if s['type'] == '2']
        subtitle_streams = [s for s in streams if s['type'] == '3']

        if video_streams:
            video_stream = next((s for s in video_streams if s['selected']), video_streams[0])
            media_part_info.update(video_stream)
        if audio_streams:
            audio_stream = next((s for s in audio_streams if s['selected']), audio_streams[0])
            media_part_info.update(audio_stream)
        if subtitle_streams:
            subtitle_stream = next((s for s in subtitle_streams if s['selected']), subtitle_streams[0])
            media_part_info.update(subtitle_stream)

    notify_params.update(media_info)
    notify_params.update(media_part_info)

    metadata = pmsconnect.PmsConnect().get_metadata_details(rating_key=rating_key)

    child_metadata = grandchild_metadata = []
    for key in kwargs.pop('child_keys', []):
        child = pmsconnect.PmsConnect().get_metadata_details(rating_key=key)
        if child:
            child_metadata.append(child)
    for key in kwargs.pop('grandchild_keys', []):
        grandchild = pmsconnect.PmsConnect().get_metadata_details(rating_key=key)
        if grandchild:
            grandchild_metadata.append(grandchild)

    # Session values
    session = session or {}

    ap = activity_processor.ActivityProcessor()
    sessions = ap.get_sessions()
    user_sessions = ap.get_sessions(user_id=session.get('user_id'))

    # Filter out the session_key from the database sessions for playback stopped events
    # to prevent race condition between the database and notifications
    if notify_action == 'on_stop':
        sessions = [s for s in sessions if str(s['session_key']) != notify_params['session_key']]
        user_sessions = [s for s in user_sessions if str(s['session_key']) != notify_params['session_key']]

    stream_count = len(sessions)
    user_stream_count = len(user_sessions)
    lan_streams = sum(1 for s in sessions if s['location'] == 'lan')
    wan_streams = stream_count - lan_streams

    lan_bandwidth = sum(helpers.cast_to_int(s['bandwidth']) for s in sessions if s['location'] == 'lan')
    wan_bandwidth = sum(helpers.cast_to_int(s['bandwidth']) for s in sessions if s['location'] != 'lan')
    total_bandwidth = lan_bandwidth + wan_bandwidth

    # Generate a combined transcode decision value
    if session.get('stream_video_decision', '') == 'transcode' or session.get('stream_audio_decision', '') == 'transcode':
        transcode_decision = 'Transcode'
    elif session.get('stream_video_decision', '') == 'copy' or session.get('stream_audio_decision', '') == 'copy':
        transcode_decision = 'Direct Stream'
    else:
        transcode_decision = 'Direct Play'
    transcode_decision_count = Counter(s['transcode_decision'] for s in sessions)
    user_transcode_decision_count = Counter(s['transcode_decision'] for s in user_sessions)

    if notify_action != 'on_play':
        stream_duration_sec = int(
            (
                helpers.timestamp()
                - helpers.cast_to_int(session.get('started', 0))
                - helpers.cast_to_int(session.get('paused_counter', 0))
            )
        )
        stream_duration = helpers.seconds_to_minutes(stream_duration_sec)
    else:
        stream_duration_sec = 0
        stream_duration = 0

    progress_duration_sec = helpers.convert_milliseconds_to_seconds(session.get('view_offset', 0))
    duration_sec = helpers.convert_milliseconds_to_seconds(notify_params['duration'])
    remaining_duration_sec = duration_sec - progress_duration_sec

    progress_duration = helpers.seconds_to_minutes(progress_duration_sec)
    duration = helpers.seconds_to_minutes(duration_sec)
    remaining_duration = duration - progress_duration

    # Build Plex URL
    if notify_params['media_type'] == 'track':
        plex_web_rating_key = notify_params['parent_rating_key']
    else:
        plex_web_rating_key = notify_params['rating_key']

    notify_params['plex_url'] = '{web_url}#!/server/{pms_identifier}/details?key=%2Flibrary%2Fmetadata%2F{rating_key}'.format(
        web_url=plexpy.CONFIG.PMS_WEB_URL,
        pms_identifier=plexpy.CONFIG.PMS_IDENTIFIER,
        rating_key=plex_web_rating_key)

    # Check external guids
    if notify_params['media_type'] == 'episode':
        guids = notify_params['grandparent_guids']
    elif notify_params['media_type'] == 'season':
        guids = notify_params['parent_guids']
    else:
        guids = notify_params['guids']

    for guid in guids:
        if 'imdb://' in guid:
            notify_params['imdb_id'] = guid.split('imdb://')[1]
        elif 'tmdb://' in guid:
            notify_params['themoviedb_id'] = guid.split('tmdb://')[1]
        elif 'tvdb://' in guid:
            notify_params['thetvdb_id'] = guid.split('tvdb://')[1]
        elif 'mbid://' in guid:
            notify_params['musicbrainz_id'] = guid.split('mbid://')[1]

    # Get media IDs from guid and build URLs
    if 'plex://' in notify_params['guid']:
        notify_params['plex_id'] = notify_params['guid'].split('plex://')[1].split('/')[1]

    if 'imdb://' in notify_params['guid'] or notify_params['imdb_id']:
        notify_params['imdb_id'] = notify_params['imdb_id'] or notify_params['guid'].split('imdb://')[1].split('?')[0]
        notify_params['imdb_url'] = 'https://www.imdb.com/title/' + notify_params['imdb_id']
        notify_params['trakt_url'] = 'https://trakt.tv/search/imdb/' + notify_params['imdb_id']

    if 'thetvdb://' in notify_params['guid'] or notify_params['thetvdb_id']:
        thetvdb_media_type = 'movie' if notify_params['media_type'] == 'movie' else 'series'
        notify_params['thetvdb_id'] = notify_params['thetvdb_id'] or notify_params['guid'].split('thetvdb://')[1].split('/')[0].split('?')[0]
        notify_params['thetvdb_url'] = f'https://thetvdb.com/dereferrer/{thetvdb_media_type}/{notify_params["thetvdb_id"]}'
        notify_params['trakt_url'] = 'https://trakt.tv/search/tvdb/' + notify_params['thetvdb_id'] + '?id_type=show'

    elif 'thetvdbdvdorder://' in notify_params['guid']:
        notify_params['thetvdb_id'] = notify_params['guid'].split('thetvdbdvdorder://')[1].split('/')[0].split('?')[0]
        notify_params['thetvdb_url'] = f'https://thetvdb.com/dereferrer/series/{notify_params["thetvdb_id"]}'
        notify_params['trakt_url'] = 'https://trakt.tv/search/tvdb/' + notify_params['thetvdb_id'] + '?id_type=show'

    if 'themoviedb://' in notify_params['guid'] or notify_params['themoviedb_id']:
        if notify_params['media_type'] == 'movie':
            notify_params['themoviedb_id'] = notify_params['themoviedb_id'] or notify_params['guid'].split('themoviedb://')[1].split('?')[0]
            notify_params['themoviedb_url'] = 'https://www.themoviedb.org/movie/' + notify_params['themoviedb_id']
            notify_params['trakt_url'] = 'https://trakt.tv/search/tmdb/' + notify_params['themoviedb_id'] + '?id_type=movie'

        elif notify_params['media_type'] in ('show', 'season', 'episode'):
            notify_params['themoviedb_id'] = notify_params['themoviedb_id'] or notify_params['guid'].split('themoviedb://')[1].split('/')[0].split('?')[0]
            notify_params['themoviedb_url'] = 'https://www.themoviedb.org/tv/' + notify_params['themoviedb_id']
            notify_params['trakt_url'] = 'https://trakt.tv/search/tmdb/' + notify_params['themoviedb_id'] + '?id_type=show'

    if 'lastfm://' in notify_params['guid']:
        notify_params['lastfm_id'] = '/'.join(notify_params['guid'].split('lastfm://')[1].split('?')[0].split('/')[:2])
        notify_params['lastfm_url'] = 'https://www.last.fm/music/' + notify_params['lastfm_id']

    if 'mbid://' in notify_params['guid'] or notify_params['musicbrainz_id']:
        if notify_params['media_type'] == 'artist':
            notify_params['musicbrainz_url'] = 'https://musicbrainz.org/artist/' + notify_params['musicbrainz_id']
        elif notify_params['media_type'] == 'album':
            notify_params['musicbrainz_url'] = 'https://musicbrainz.org/release/' + notify_params['musicbrainz_id']
        else:
            notify_params['musicbrainz_url'] = 'https://musicbrainz.org/track/' + notify_params['musicbrainz_id']

    if 'hama://' in notify_params['guid']:
        notify_params['anidb_id'] = notify_params['guid'].split('hama://')[1].split('/')[0].split('?')[0].split('-')[1]
        notify_params['anidb_url'] = 'https://anidb.net/anime/' + notify_params['anidb_id']

    # Get TheMovieDB info (for movies and tv only)
    if plexpy.CONFIG.THEMOVIEDB_LOOKUP and notify_params['media_type'] in ('movie', 'show', 'season', 'episode'):
        if notify_params.get('themoviedb_id'):
            if notify_params['media_type'] == 'episode':
                lookup_key = notify_params['grandparent_rating_key']
            elif notify_params['media_type'] == 'season':
                lookup_key = notify_params['parent_rating_key']
            else:
                lookup_key = rating_key

            themoveidb_json = get_themoviedb_info(rating_key=lookup_key,
                                                  media_type=notify_params['media_type'],
                                                  themoviedb_id=notify_params['themoviedb_id'])

            if themoveidb_json.get('imdb_id'):
                notify_params['imdb_id'] = themoveidb_json['imdb_id']
                notify_params['imdb_url'] = 'https://www.imdb.com/title/' + themoveidb_json['imdb_id']

        elif notify_params.get('thetvdb_id') or notify_params.get('imdb_id') or notify_params.get('plex_id'):
            if notify_params['media_type'] == 'episode':
                lookup_key = notify_params['grandparent_rating_key']
                lookup_title = notify_params['grandparent_title']
                lookup_year = notify_params['year']
                lookup_media_type = 'tv'
            elif notify_params['media_type'] == 'season':
                lookup_key = notify_params['parent_rating_key']
                lookup_title = notify_params['parent_title']
                lookup_year = notify_params['year']
                lookup_media_type = 'tv'
            else:
                lookup_key = rating_key
                lookup_title = notify_params['title']
                lookup_year = notify_params['year']
                lookup_media_type = 'tv' if notify_params['media_type'] == 'show' else 'movie'

            themoviedb_info = lookup_themoviedb_by_id(rating_key=lookup_key,
                                                      thetvdb_id=notify_params.get('thetvdb_id'),
                                                      imdb_id=notify_params.get('imdb_id'),
                                                      title=lookup_title,
                                                      year=lookup_year,
                                                      media_type=lookup_media_type)
            themoviedb_info.pop('rating_key', None)
            notify_params.update(themoviedb_info)

            if themoviedb_info.get('imdb_id'):
                notify_params['imdb_url'] = 'https://www.imdb.com/title/' + themoviedb_info['imdb_id']
            if themoviedb_info.get('themoviedb_id'):
                notify_params['trakt_url'] = 'https://trakt.tv/search/tmdb/{}?id_type={}'.format(
                    notify_params['themoviedb_id'], 'show' if lookup_media_type == 'tv' else 'movie')

    # Get TVmaze info (for tv shows only)
    if plexpy.CONFIG.TVMAZE_LOOKUP and notify_params['media_type'] in ('show', 'season', 'episode'):
        if notify_params.get('thetvdb_id') or notify_params.get('imdb_id') or notify_params.get('plex_id'):
            if notify_params['media_type'] == 'episode':
                lookup_key = notify_params['grandparent_rating_key']
                lookup_title = notify_params['grandparent_title']
            elif notify_params['media_type'] == 'season':
                lookup_key = notify_params['parent_rating_key']
                lookup_title = notify_params['parent_title']
            else:
                lookup_key = rating_key
                lookup_title = notify_params['title']

            tvmaze_info = lookup_tvmaze_by_id(rating_key=lookup_key,
                                              thetvdb_id=notify_params.get('thetvdb_id'),
                                              imdb_id=notify_params.get('imdb_id'),
                                              title=lookup_title)
            tvmaze_info.pop('rating_key', None)
            notify_params.update(tvmaze_info)

            if tvmaze_info.get('thetvdb_id'):
                notify_params['thetvdb_url'] = f'https://thetvdb.com/dereferrer/series/{tvmaze_info["thetvdb_id"]}'
                notify_params['trakt_url'] = 'https://trakt.tv/search/tvdb/{}' + str(notify_params['thetvdb_id']) + '?id_type=show'
            if tvmaze_info.get('imdb_id'):
                notify_params['imdb_url'] = 'https://www.imdb.com/title/' + tvmaze_info['imdb_id']
                notify_params['trakt_url'] = 'https://trakt.tv/search/imdb/' + notify_params['imdb_id']

    # Get MusicBrainz info (for music only)
    if plexpy.CONFIG.MUSICBRAINZ_LOOKUP and notify_params['media_type'] in ('artist', 'album', 'track'):
        artist = release = recording = tracks = tnum = None
        if notify_params['media_type'] == 'artist':
            musicbrainz_type = 'artist'
            artist = notify_params['title']
        elif notify_params['media_type'] == 'album':
            musicbrainz_type = 'release'
            artist = notify_params['parent_title']
            release = notify_params['title']
            tracks = notify_params['children_count']
        else:
            musicbrainz_type = 'recording'
            artist = notify_params['original_title'] or notify_params['grandparent_title']
            release = notify_params['parent_title']
            recording = notify_params['title']
            tracks = notify_params['children_count']
            tnum = notify_params['media_index']

        musicbrainz_info = lookup_musicbrainz_info(musicbrainz_type=musicbrainz_type, rating_key=rating_key,
                                                   artist=artist, release=release, recording=recording, tracks=tracks,
                                                   tnum=tnum)
        musicbrainz_info.pop('rating_key', None)
        notify_params.update(musicbrainz_info)

    if notify_params['media_type'] in ('movie', 'show', 'artist'):
        poster_thumb = notify_params['thumb']
        poster_key = notify_params['rating_key']
        poster_title = notify_params['title']
        plex_slug = notify_params['slug']
    elif notify_params['media_type'] in ('season', 'album'):
        poster_thumb = notify_params['thumb'] or notify_params['parent_thumb']
        poster_key = notify_params['rating_key']
        poster_title = '%s - %s' % (notify_params['parent_title'],
                                    notify_params['title'])
        plex_slug = notify_params['parent_slug']
    elif notify_params['media_type'] in ('episode', 'track'):
        poster_thumb = notify_params['parent_thumb'] or notify_params['grandparent_thumb']
        poster_key = notify_params['parent_rating_key']
        poster_title = '%s - %s' % (notify_params['grandparent_title'],
                                    notify_params['parent_title'])
        plex_slug = notify_params['grandparent_slug']
    elif notify_params['media_type'] == 'clip':
        if notify_params['extra_type']:
            poster_thumb = notify_params['art'].replace('/art', '/thumb') or notify_params['thumb']
        else:
            poster_thumb = notify_params['parent_thumb'] or notify_params['thumb']
        poster_key = notify_params['rating_key']
        poster_title = notify_params['title']
        plex_slug = notify_params['slug']
    else:
        poster_thumb = ''
        poster_key = ''
        poster_title = ''
        plex_slug = ''

    if notify_params['media_type'] == 'movie':
        plex_watch_url = f'https://watch.plex.tv/movie/{plex_slug}'
    elif notify_params['media_type'] in ('show', 'season', 'episode'):
        plex_watch_url = f'https://watch.plex.tv/show/{plex_slug}'
    else:
        plex_watch_url = ''

    img_service = helpers.get_img_service(include_self=True)
    fallback = 'poster-live' if notify_params['live'] else 'poster'
    if img_service not in (None, 'self-hosted'):
        img_info = get_img_info(img=poster_thumb, rating_key=poster_key, title=poster_title, fallback=fallback)
        poster_info = {'poster_title': img_info['img_title'], 'poster_url': img_info['img_url']}
        notify_params.update(poster_info)
    elif img_service == 'self-hosted' and plexpy.CONFIG.HTTP_BASE_URL:
        img_hash = set_hash_image_info(img=poster_thumb, fallback=fallback)
        poster_info = {'poster_title': poster_title,
                       'poster_url': plexpy.CONFIG.HTTP_BASE_URL + plexpy.HTTP_ROOT + 'image/' + img_hash}
        notify_params.update(poster_info)

    if ((manual_trigger or plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT)
        and notify_params['media_type'] in ('show', 'artist')):
        show_name = notify_params['title']
        season_name = ''
        episode_name = ''
        artist_name = notify_params['title']
        album_name = ''
        track_name = ''

        child_num = [helpers.cast_to_int(
            d['media_index']) for d in child_metadata if d['parent_rating_key'] == rating_key]
        num, num00 = format_group_index(child_num)
        season_num, season_num00 = num, num00

        episode_num, episode_num00 = '', ''
        disc_num, disc_num00 = '', ''
        track_num, track_num00 = '', ''

        child_count = len(child_num)
        grandchild_count = ''

        show_year = notify_params['year']

    elif ((manual_trigger or plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_PARENT)
          and notify_params['media_type'] in ('season', 'album')):
        show_name = notify_params['parent_title']
        season_name = notify_params['title']
        episode_name = ''
        artist_name = notify_params['parent_title']
        album_name = notify_params['title']
        track_name = ''

        season_num = str(notify_params['media_index']).zfill(1)
        season_num00 = str(notify_params['media_index']).zfill(2)

        grandchild_num = [helpers.cast_to_int(
            d['media_index']) for d in child_metadata if d['parent_rating_key'] == rating_key]
        num, num00 = format_group_index(grandchild_num)
        episode_num, episode_num00 = num, num00
        track_num, track_num00 = num, num00

        disc_num, disc_num00 = '', ''

        child_count = 1
        grandchild_count = len(grandchild_num)

        show_year = notify_params['parent_year']

    else:
        show_name = notify_params['grandparent_title']
        season_name = notify_params['parent_title']
        episode_name = notify_params['title']
        artist_name = notify_params['grandparent_title']
        album_name = notify_params['parent_title']
        track_name = notify_params['title']
        season_num = str(notify_params['parent_media_index']).zfill(1)
        season_num00 = str(notify_params['parent_media_index']).zfill(2)
        episode_num = str(notify_params['media_index']).zfill(1)
        episode_num00 = str(notify_params['media_index']).zfill(2)
        disc_num = str(notify_params['parent_media_index']).zfill(1)
        disc_num00 = str(notify_params['parent_media_index']).zfill(2)
        track_num = str(notify_params['media_index']).zfill(1)
        track_num00 = str(notify_params['media_index']).zfill(2)
        child_count = 1
        grandchild_count = 1
        show_year = notify_params['grandparent_year']

    rating = notify_params['rating'] or notify_params['audience_rating']

    critic_rating = ''
    if notify_params['rating_image'].startswith('rottentomatoes://') \
            and notify_params['rating']:
        critic_rating = helpers.get_percent(notify_params['rating'], 10)

    audience_rating = notify_params['audience_rating']
    if notify_params['audience_rating_image'].startswith(('rottentomatoes://', 'themoviedb://')) \
            and audience_rating:
        audience_rating = helpers.get_percent(notify_params['audience_rating'], 10)

    marker = kwargs.pop('marker', defaultdict(int))

    now = arrow.now()
    now_iso = now.isocalendar()

    available_params = {
        # Global parameters
        'tautulli_version': common.RELEASE,
        'tautulli_remote': plexpy.CONFIG.GIT_REMOTE,
        'tautulli_branch': plexpy.CONFIG.GIT_BRANCH,
        'tautulli_commit': plexpy.CURRENT_VERSION,
        'server_name': helpers.pms_name(),
        'server_ip': plexpy.CONFIG.PMS_IP,
        'server_port': plexpy.CONFIG.PMS_PORT,
        'server_url': plexpy.CONFIG.PMS_URL,
        'server_machine_id': plexpy.CONFIG.PMS_IDENTIFIER,
        'server_platform': plexpy.CONFIG.PMS_PLATFORM,
        'server_version': plexpy.CONFIG.PMS_VERSION,
        'action': notify_action.split('on_')[-1],
        'current_year': now.year,
        'current_month': now.month,
        'current_day': now.day,
        'current_hour': now.hour,
        'current_minute': now.minute,
        'current_second': now.second,
        'current_weekday': now_iso[2],
        'current_week': now_iso[1],
        'week_number': now_iso[1],  # Keep for backwards compatibility
        'datestamp': CustomArrow(now, date_format),
        'timestamp': CustomArrow(now, time_format),
        'unixtime': helpers.timestamp(),
        'utctime': helpers.utc_now_iso(),
        # Stream parameters
        'streams': stream_count,
        'lan_streams': lan_streams,
        'wan_streams': wan_streams,
        'direct_plays': transcode_decision_count['direct play'],
        'direct_streams': transcode_decision_count['copy'],
        'transcodes': transcode_decision_count['transcode'],
        'total_bandwidth': total_bandwidth,
        'lan_bandwidth': lan_bandwidth,
        'wan_bandwidth': wan_bandwidth,
        'user_streams': user_stream_count,
        'user_direct_plays': user_transcode_decision_count['direct play'],
        'user_direct_streams': user_transcode_decision_count['copy'],
        'user_transcodes': user_transcode_decision_count['transcode'],
        'user': notify_params['friendly_name'],
        'username': notify_params['user'],
        'user_email': notify_params['email'],
        'user_thumb': notify_params['user_thumb'],
        'device': notify_params['device'],
        'platform': notify_params['platform'],
        'platform_version': notify_params['platform_version'],
        'product': notify_params['product'],
        'product_version': notify_params['product_version'],
        'player': notify_params['player'],
        'ip_address': notify_params.get('ip_address', 'N/A'),
        'started_datestamp': CustomArrow(arrow.get(notify_params['started']), date_format) if notify_params['started'] else '',
        'started_timestamp': CustomArrow(arrow.get(notify_params['started']), time_format) if notify_params['started'] else '',
        'started_unixtime': notify_params['started'],
        'stopped_datestamp': CustomArrow(arrow.get(notify_params['stopped']), date_format) if notify_params['stopped'] else '',
        'stopped_timestamp': CustomArrow(arrow.get(notify_params['stopped']), time_format) if notify_params['stopped'] else '',
        'stopped_unixtime': notify_params['stopped'],
        'stream_duration': stream_duration,
        'stream_duration_sec': stream_duration_sec,
        'stream_time': CustomArrow(arrow.get(stream_duration_sec), duration_format),
        'remaining_duration': remaining_duration,
        'remaining_duration_sec': remaining_duration_sec,
        'remaining_time': CustomArrow(arrow.get(remaining_duration_sec), duration_format),
        'progress_duration': progress_duration,
        'progress_duration_sec': progress_duration_sec,
        'progress_time': CustomArrow(arrow.get(progress_duration_sec), duration_format),
        'progress_percent': helpers.get_percent(progress_duration_sec, duration_sec),
        'view_offset': session.get('view_offset', 0),
        'initial_stream': notify_params['initial_stream'],
        'transcode_decision': transcode_decision,
        'container_decision': notify_params['container_decision'],
        'video_decision': notify_params['video_decision'],
        'audio_decision': notify_params['audio_decision'],
        'subtitle_decision': notify_params['subtitle_decision'],
        'quality_profile': notify_params['quality_profile'],
        'optimized_version': notify_params['optimized_version'],
        'optimized_version_profile': notify_params['optimized_version_profile'],
        'synced_version': notify_params['synced_version'],
        'live': notify_params['live'],
        'marker_start': marker['start_time_offset'],
        'marker_end': marker['end_time_offset'],
        'credits_marker_first': helpers.cast_to_int(marker['first']),
        'credits_marker_final': helpers.cast_to_int(marker['final']),
        'channel_call_sign': notify_params['channel_call_sign'],
        'channel_id': notify_params['channel_id'],
        'channel_identifier': notify_params['channel_identifier'],
        'channel_title': notify_params['channel_title'],
        'channel_thumb': notify_params['channel_thumb'],
        'channel_vcn': notify_params['channel_vcn'],
        'secure': 'unknown' if notify_params['secure'] is None else notify_params['secure'],
        'relayed': notify_params['relayed'],
        'stream_local': notify_params['local'],
        'stream_location': notify_params['location'],
        'stream_bandwidth': notify_params['bandwidth'],
        'stream_container': notify_params['stream_container'],
        'stream_bitrate': notify_params['stream_bitrate'],
        'stream_aspect_ratio': notify_params['stream_aspect_ratio'],
        'stream_video_codec': notify_params['stream_video_codec'],
        'stream_video_codec_level': notify_params['stream_video_codec_level'],
        'stream_video_bitrate': notify_params['stream_video_bitrate'],
        'stream_video_bit_depth': notify_params['stream_video_bit_depth'],
        'stream_video_chroma_subsampling': notify_params['stream_video_chroma_subsampling'],
        'stream_video_color_primaries': notify_params['stream_video_color_primaries'],
        'stream_video_color_range': notify_params['stream_video_color_range'],
        'stream_video_color_space': notify_params['stream_video_color_space'],
        'stream_video_color_trc': notify_params['stream_video_color_trc'],
        'stream_video_dynamic_range': notify_params['stream_video_dynamic_range'],
        'stream_video_dovi_present': notify_params['stream_video_dovi_present'],
        'stream_video_dovi_level': notify_params['stream_video_dovi_level'],
        'stream_video_dovi_profile': notify_params['stream_video_dovi_profile'],
        'stream_video_framerate': notify_params['stream_video_framerate'],
        'stream_video_full_resolution': notify_params['stream_video_full_resolution'],
        'stream_video_ref_frames': notify_params['stream_video_ref_frames'],
        'stream_video_resolution': notify_params['stream_video_resolution'],
        'stream_video_scan_type': notify_params['stream_video_scan_type'],
        'stream_video_height': notify_params['stream_video_height'],
        'stream_video_width': notify_params['stream_video_width'],
        'stream_video_language': notify_params['stream_video_language'],
        'stream_video_language_code': notify_params['stream_video_language_code'],
        'stream_audio_bitrate': notify_params['stream_audio_bitrate'],
        'stream_audio_bitrate_mode': notify_params['stream_audio_bitrate_mode'],
        'stream_audio_codec': notify_params['stream_audio_codec'],
        'stream_audio_channels': notify_params['stream_audio_channels'],
        'stream_audio_channel_layout': notify_params['stream_audio_channel_layout'],
        'stream_audio_sample_rate': notify_params['stream_audio_sample_rate'],
        'stream_audio_language': notify_params['stream_audio_language'],
        'stream_audio_language_code': notify_params['stream_audio_language_code'],
        'stream_audio_profile': notify_params['stream_audio_profile'],
        'stream_subtitle_codec': notify_params['stream_subtitle_codec'],
        'stream_subtitle_container': notify_params['stream_subtitle_container'],
        'stream_subtitle_format': notify_params['stream_subtitle_format'],
        'stream_subtitle_forced': notify_params['stream_subtitle_forced'],
        'stream_subtitle_language': notify_params['stream_subtitle_language'],
        'stream_subtitle_language_code': notify_params['stream_subtitle_language_code'],
        'stream_subtitle_location': notify_params['stream_subtitle_location'],
        'transcode_container': notify_params['transcode_container'],
        'transcode_video_codec': notify_params['transcode_video_codec'],
        'transcode_video_width': notify_params['transcode_width'],
        'transcode_video_height': notify_params['transcode_height'],
        'transcode_audio_codec': notify_params['transcode_audio_codec'],
        'transcode_audio_channels': notify_params['transcode_audio_channels'],
        'transcode_hw_requested': notify_params['transcode_hw_requested'],
        'transcode_hw_decoding': notify_params['transcode_hw_decoding'],
        'transcode_hw_decode_codec': notify_params['transcode_hw_decode'],
        'transcode_hw_decode_title': notify_params['transcode_hw_decode_title'],
        'transcode_hw_encoding': notify_params['transcode_hw_encoding'],
        'transcode_hw_encode_codec': notify_params['transcode_hw_encode'],
        'transcode_hw_encode_title': notify_params['transcode_hw_encode_title'],
        'transcode_hw_full_pipeline': notify_params['transcode_hw_full_pipeline'],
        'session_key': notify_params['session_key'],
        'transcode_key': notify_params['transcode_key'],
        'session_id': notify_params['session_id'],
        'user_id': notify_params['user_id'],
        'machine_id': notify_params['machine_id'],
        # Source metadata parameters
        'media_type': notify_params['media_type'],
        'library_name': notify_params['library_name'],
        'title': notify_params['full_title'],
        'edition_title': notify_params['edition_title'],
        'show_name': show_name,
        'season_name': season_name,
        'episode_name': episode_name,
        'artist_name': artist_name,
        'album_name': album_name,
        'track_name': track_name,
        'track_artist': notify_params['original_title'] or notify_params['grandparent_title'],
        'season_num': season_num,
        'season_num00': season_num00,
        'episode_num': episode_num,
        'episode_num00': episode_num00,
        'disc_num': disc_num,
        'disc_num00': disc_num00,
        'track_num': track_num,
        'track_num00': track_num00,
        'season_count': child_count,
        'episode_count': grandchild_count,
        'album_count': child_count,
        'track_count': grandchild_count,
        'year': notify_params['year'],
        'show_year': show_year,
        'release_date': CustomArrow(arrow.get(notify_params['originally_available_at']), date_format)
            if notify_params['originally_available_at'] else '',
        'air_date': CustomArrow(arrow.get(notify_params['originally_available_at']), date_format)
            if notify_params['originally_available_at'] else '',
        'added_date': CustomArrow(arrow.get(int(notify_params['added_at'])), date_format)
            if notify_params['added_at'] else '',
        'updated_date': CustomArrow(arrow.get(int(notify_params['updated_at'])), date_format)
            if notify_params['updated_at'] else '',
        'last_viewed_date': CustomArrow(arrow.get(int(notify_params['last_viewed_at'])), date_format)
            if notify_params['last_viewed_at'] else '',
        'studio': notify_params['studio'],
        'content_rating': notify_params['content_rating'],
        'directors': ', '.join(notify_params['directors']),
        'writers': ', '.join(notify_params['writers']),
        'actors': ', '.join(notify_params['actors']),
        'genres': ', '.join(notify_params['genres']),
        'labels': ', '.join(notify_params['labels']),
        'collections': ', '.join(notify_params['collections']),
        'summary': notify_params['summary'],
        'tagline': notify_params['tagline'],
        'rating': rating,
        'critic_rating':  critic_rating,
        'audience_rating': audience_rating,
        'user_rating': notify_params['user_rating'],
        'duration': duration,
        'duration_sec': duration_sec,
        'duration_ms': notify_params['duration'],
        'duration_time': CustomArrow(arrow.get(duration_sec), duration_format),
        'poster_title': notify_params['poster_title'],
        'poster_url': notify_params['poster_url'],
        'plex_id': notify_params['plex_id'],
        'plex_url': notify_params['plex_url'],
        'plex_slug': plex_slug,
        'plex_watch_url': plex_watch_url,
        'imdb_id': notify_params['imdb_id'],
        'imdb_url': notify_params['imdb_url'],
        'thetvdb_id': notify_params['thetvdb_id'],
        'thetvdb_url': notify_params['thetvdb_url'],
        'themoviedb_id': notify_params['themoviedb_id'],
        'themoviedb_url': notify_params['themoviedb_url'],
        'tvmaze_id': notify_params['tvmaze_id'],
        'tvmaze_url': notify_params['tvmaze_url'],
        'musicbrainz_id': notify_params['musicbrainz_id'],
        'musicbrainz_url': notify_params['musicbrainz_url'],
        'anidb_id': notify_params['anidb_id'],
        'anidb_url': notify_params['anidb_url'],
        'lastfm_url': notify_params['lastfm_url'],
        'trakt_url': notify_params['trakt_url'],
        'container': notify_params['container'],
        'bitrate': notify_params['bitrate'],
        'aspect_ratio': notify_params['aspect_ratio'],
        'video_codec': notify_params['video_codec'],
        'video_codec_level': notify_params['video_codec_level'],
        'video_bitrate': notify_params['video_bitrate'],
        'video_bit_depth': notify_params['video_bit_depth'],
        'video_chroma_subsampling': notify_params['video_chroma_subsampling'],
        'video_color_primaries': notify_params['video_color_primaries'],
        'video_color_range': notify_params['video_color_range'],
        'video_color_space': notify_params['video_color_space'],
        'video_color_trc': notify_params['video_color_trc'],
        'video_dynamic_range': notify_params['video_dynamic_range'],
        'video_dovi_present': notify_params['video_dovi_present'],
        'video_dovi_level': notify_params['video_dovi_level'],
        'video_dovi_profile': notify_params['video_dovi_profile'],
        'video_framerate': notify_params['video_framerate'],
        'video_full_resolution': notify_params['video_full_resolution'],
        'video_ref_frames': notify_params['video_ref_frames'],
        'video_resolution': notify_params['video_resolution'],
        'video_scan_type': notify_params['video_scan_type'],
        'video_height': notify_params['height'],
        'video_width': notify_params['width'],
        'video_language': notify_params['video_language'],
        'video_language_code': notify_params['video_language_code'],
        'audio_bitrate': notify_params['audio_bitrate'],
        'audio_bitrate_mode': notify_params['audio_bitrate_mode'],
        'audio_codec': notify_params['audio_codec'],
        'audio_channels': notify_params['audio_channels'],
        'audio_channel_layout': notify_params['audio_channel_layout'],
        'audio_sample_rate': notify_params['audio_sample_rate'],
        'audio_language': notify_params['audio_language'],
        'audio_language_code': notify_params['audio_language_code'],
        'audio_profile': notify_params['audio_profile'],
        'subtitle_codec': notify_params['subtitle_codec'],
        'subtitle_container': notify_params['subtitle_container'],
        'subtitle_format': notify_params['subtitle_format'],
        'subtitle_forced': notify_params['subtitle_forced'],
        'subtitle_location': notify_params['subtitle_location'],
        'subtitle_language': notify_params['subtitle_language'],
        'subtitle_language_code': notify_params['subtitle_language_code'],
        'file': notify_params['file'],
        'filename': os.path.basename(notify_params['file'].replace('\\', os.sep)),
        'file_size': helpers.human_file_size(notify_params['file_size']),
        'file_size_bytes': notify_params['file_size'],
        'indexes': notify_params['indexes'],
        'guid': notify_params['guid'],
        'section_id': notify_params['section_id'],
        'rating_key': notify_params['rating_key'],
        'parent_rating_key': notify_params['parent_rating_key'],
        'grandparent_rating_key': notify_params['grandparent_rating_key'],
        'art': notify_params['art'],
        'thumb': notify_params['thumb'],
        'parent_thumb': notify_params['parent_thumb'],
        'grandparent_thumb': notify_params['grandparent_thumb'],
        'poster_thumb': poster_thumb
        }

    notify_params.update(available_params)
    return notify_params


def build_server_notify_params(notify_action=None, **kwargs):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','')

    update_channel = pmsconnect.PmsConnect().get_server_update_channel()

    pms_download_info = defaultdict(str, kwargs.pop('pms_download_info', {}))
    plexpy_download_info = defaultdict(str, kwargs.pop('plexpy_download_info', {}))
    remote_access_info = defaultdict(str, kwargs.pop('remote_access_info', {}))

    windows_exe = macos_pkg = ''
    if plexpy_download_info:
        release_assets = plexpy_download_info.get('assets', [])
        for asset in release_assets:
            if asset['content_type'] == 'application/vnd.microsoft.portable-executable':
                windows_exe = asset['browser_download_url']
            elif asset['content_type'] == 'application/vnd.apple.installer+xml':
                macos_pkg = asset['browser_download_url']

    now = arrow.now()
    now_iso = now.isocalendar()

    available_params = {
        # Global parameters
        'tautulli_version': common.RELEASE,
        'tautulli_remote': plexpy.CONFIG.GIT_REMOTE,
        'tautulli_branch': plexpy.CONFIG.GIT_BRANCH,
        'tautulli_commit': plexpy.CURRENT_VERSION,
        'server_name': helpers.pms_name(),
        'server_ip': plexpy.CONFIG.PMS_IP,
        'server_port': plexpy.CONFIG.PMS_PORT,
        'server_url': plexpy.CONFIG.PMS_URL,
        'server_platform': plexpy.CONFIG.PMS_PLATFORM,
        'server_version': plexpy.CONFIG.PMS_VERSION,
        'server_machine_id': plexpy.CONFIG.PMS_IDENTIFIER,
        'action': notify_action.split('on_')[-1],
        'current_year': now.year,
        'current_month': now.month,
        'current_day': now.day,
        'current_hour': now.hour,
        'current_minute': now.minute,
        'current_second': now.second,
        'current_weekday': now_iso[2],
        'current_week': now_iso[1],
        'week_number': now_iso[1],  # Keep for backwards compatibility
        'datestamp': CustomArrow(now, date_format),
        'timestamp': CustomArrow(now, time_format),
        'unixtime': helpers.timestamp(),
        'utctime': helpers.utc_now_iso(),
        # Plex remote access parameters
        'remote_access_mapping_state': remote_access_info['mapping_state'],
        'remote_access_mapping_error': remote_access_info['mapping_error'],
        'remote_access_public_address': remote_access_info['public_address'],
        'remote_access_public_port': remote_access_info['public_port'],
        'remote_access_private_address': remote_access_info['private_address'],
        'remote_access_private_port': remote_access_info['private_port'],
        'remote_access_reason': remote_access_info['reason'],
        # Plex Media Server update parameters
        'update_version': pms_download_info['version'],
        'update_url': pms_download_info['download_url'],
        'update_release_date': CustomArrow(arrow.get(pms_download_info['release_date']), date_format)
            if pms_download_info['release_date'] else '',
        'update_channel': 'Beta' if update_channel == 'beta' else 'Public',
        'update_platform': pms_download_info['platform'],
        'update_distro': pms_download_info['distro'],
        'update_distro_build': pms_download_info['build'],
        'update_requirements': pms_download_info['requirements'],
        'update_extra_info': pms_download_info['extra_info'],
        'update_changelog_added': pms_download_info['changelog_added'],
        'update_changelog_fixed': pms_download_info['changelog_fixed'],
        # Tautulli update parameters
        'tautulli_update_version': plexpy_download_info['tag_name'],
        'tautulli_update_release_url': plexpy_download_info['html_url'],
        'tautulli_update_exe': windows_exe,
        'tautulli_update_pkg': macos_pkg,
        'tautulli_update_tar': plexpy_download_info['tarball_url'],
        'tautulli_update_zip': plexpy_download_info['zipball_url'],
        'tautulli_update_commit': kwargs.pop('plexpy_update_commit', ''),
        'tautulli_update_behind': kwargs.pop('plexpy_update_behind', ''),
        'tautulli_update_changelog': plexpy_download_info['body']
        }

    return available_params


def build_notify_text(subject='', body='', notify_action=None, parameters=None, agent_id=None, test=False, as_json=False):
    # Default subject and body text
    if agent_id == 15:
        default_subject = default_body = ''
    else:
        default_action = next((a for a in notifiers.available_notification_actions() if a['name'] == notify_action), {})
        default_subject = default_action.get('subject', '')
        default_body = default_action.get('body', '')

    # Make sure subject and body text are strings
    if not isinstance(subject, str):
        logger.error("Tautulli NotificationHandler :: Invalid subject text. Using fallback.")
        subject = default_subject
    if not isinstance(body, str):
        logger.error("Tautulli NotificationHandler :: Invalid body text. Using fallback.")
        body = default_body

    media_type = parameters.get('media_type')

    all_tags = r'<movie>.*?</movie>|' \
        '<show>.*?</show>|<season>.*?</season>|<episode>.*?</episode>|' \
        '<artist>.*?</artist>|<album>.*?</album>|<track>.*?</track>'

    # Check for exclusion tags
    if media_type == 'movie':
        pattern = re.compile(all_tags.replace('<movie>.*?</movie>', '<movie>|</movie>'), re.IGNORECASE | re.DOTALL)
    elif media_type == 'show':
        pattern = re.compile(all_tags.replace('<show>.*?</show>', '<show>|</show>'), re.IGNORECASE | re.DOTALL)
    elif media_type == 'season':
        pattern = re.compile(all_tags.replace('<season>.*?</season>', '<season>|</season>'), re.IGNORECASE | re.DOTALL)
    elif media_type == 'episode':
        pattern = re.compile(all_tags.replace('<episode>.*?</episode>', '<episode>|</episode>'), re.IGNORECASE | re.DOTALL)
    elif media_type == 'artist':
        pattern = re.compile(all_tags.replace('<artist>.*?</artist>', '<artist>|</artist>'), re.IGNORECASE | re.DOTALL)
    elif media_type == 'album':
        pattern = re.compile(all_tags.replace('<album>.*?</album>', '<album>|</album>'), re.IGNORECASE | re.DOTALL)
    elif media_type == 'track':
        pattern = re.compile(all_tags.replace('<track>.*?</track>', '<track>|</track>'), re.IGNORECASE | re.DOTALL)
    else:
        pattern = re.compile(all_tags, re.IGNORECASE | re.DOTALL)

    # Remove the unwanted tags and strip any unmatch tags too.
    subject = strip_tag(re.sub(pattern, '', subject), agent_id).strip(' \t\n\r')
    body = strip_tag(re.sub(pattern, '', body), agent_id).strip(' \t\n\r')
    script_args = []

    if test:
        return subject, body

    str_formatter = partial(str_format, parameters=parameters)

    if agent_id == 15:
        try:
            script_args = [str_formatter(arg) for arg in helpers.split_args(subject)]
        except LookupError as e:
            logger.error("Tautulli NotificationHandler :: Unable to parse parameter %s in script argument. Using fallback." % e)
            script_args = []
        except Exception as e:
            logger.exception("Tautulli NotificationHandler :: Unable to parse custom script arguments: %s. Using fallback." % e)
            script_args = []

    elif agent_id == 25 or as_json:
        agent = 'MQTT' if agent_id == 23 else 'webhook'
        if subject:
            try:
                subject = json.loads(subject)
            except ValueError as e:
                logger.error("Tautulli NotificationHandler :: Unable to parse custom %s json header data: %s. Using fallback." % (agent, e))
                subject = ''
        if subject:
            try:
                subject = json.dumps(helpers.traverse_map(subject, str_formatter))
            except LookupError as e:
                logger.error("Tautulli NotificationHandler :: Unable to parse parameter %s in %s header data. Using fallback." % (e, agent))
                subject = ''
            except Exception as e:
                logger.exception("Tautulli NotificationHandler :: Unable to parse custom %s header data: %s. Using fallback." % (agent, e))
                subject = ''

        if body:
            try:
                body = json.loads(body)
            except ValueError as e:
                logger.error("Tautulli NotificationHandler :: Unable to parse custom webhook json body data: %s. Using fallback." % e)
                body = ''
        if body:
            try:
                body = json.dumps(helpers.traverse_map(body, str_formatter))
            except LookupError as e:
                logger.error("Tautulli NotificationHandler :: Unable to parse parameter %s in webhook body data. Using fallback." % e)
                body = ''
            except Exception as e:
                logger.exception("Tautulli NotificationHandler :: Unable to parse custom webhook body data: %s. Using fallback." % e)
                body = ''

    else:
        try:
            subject = str_formatter(subject)
        except LookupError as e:
            logger.error("Tautulli NotificationHandler :: Unable to parse parameter %s in notification subject. Using fallback." % e)
            subject = str(default_subject).format(**parameters)
        except Exception as e:
            logger.exception("Tautulli NotificationHandler :: Unable to parse custom notification subject: %s. Using fallback." % e)
            subject = str(default_subject).format(**parameters)

        try:
            body = str_formatter(body)
        except LookupError as e:
            logger.error("Tautulli NotificationHandler :: Unable to parse parameter %s in notification body. Using fallback." % e)
            body = str(default_body).format(**parameters)
        except Exception as e:
            logger.exception("Tautulli NotificationHandler :: Unable to parse custom notification body: %s. Using fallback." % e)
            body = str(default_body).format(**parameters)

    return subject, body, script_args


def strip_tag(data, agent_id=None):
    # Substitute temporary tokens for < and > in parameter prefix and suffix
    data = re.sub(r'{.+?}', lambda m: m.group().replace('<', '%temp_lt_token%').replace('>', '%temp_gt_token%'), data)

    if agent_id == 7:
        # Allow tags b, i, u, a[href], font[color] for Pushover
        whitelist = {'b': [],
                     'i': [],
                     'u': [],
                     'a': ['href'],
                     'font': ['color']}
        data = bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)

    elif agent_id == 13:
        # Allow tags for Telegram
        # https://core.telegram.org/bots/api#html-style
        whitelist = {'b': [], 'strong': [],
                     'i': [], 'em': [],
                     'u': [], 'ins': [],
                     's': [], 'strike': [], 'del': [],
                     'span': ['class'], 'tg-spoiler': [],
                     'a': ['href'],
                     'tg-emoji': ['emoji-id'],
                     'code': ['class'],
                     'pre': [],
                     'blockquote': ['expandable'],
        }
        data = bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)

    elif agent_id in (10, 14, 20, 25):
        # Don't remove tags for Email, Slack, Discord, and Webhook
        pass

    else:
        whitelist = {}
        data = bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)

    # Resubstitute temporary tokens for < and > in parameter prefix and suffix
    return data.replace('%temp_lt_token%', '<').replace('%temp_gt_token%', '>')


def format_group_index(group_keys):
    group_keys = sorted(group_keys)

    num = []
    num00 = []

    for k, g in groupby(enumerate(group_keys), lambda i_x: i_x[0]-i_x[1]):
        group = list(map(itemgetter(1), g))
        g_min, g_max = min(group), max(group)

        if g_min == g_max:
            num.append('{0:01d}'.format(g_min))
            num00.append('{0:02d}'.format(g_min))
        else:
            num.append('{0:01d}-{1:01d}'.format(g_min, g_max))
            num00.append('{0:02d}-{1:02d}'.format(g_min, g_max))

    return ','.join(num) or '0', ','.join(num00) or '00'


def get_img_info(img=None, rating_key=None, title='', width=1000, height=1500,
                 opacity=100, background='000000', blur=0, fallback=None):
    img_info = {'img_title': '', 'img_url': ''}

    if not rating_key and not img:
        return img_info

    if rating_key and not img:
        if fallback and fallback.startswith('art'):
            img = '/library/metadata/{}/art'.format(rating_key)
        else:
            img = '/library/metadata/{}/thumb'.format(rating_key)

    if img.startswith('/library/metadata'):
        img_split = img.split('/')
        img = '/'.join(img_split[:5])
        img_rating_key = img_split[3]
        if rating_key != img_rating_key:
            rating_key = img_rating_key

    service = helpers.get_img_service()

    if service is None:
        return img_info

    elif service == 'cloudinary':
        if fallback == 'cover':
            w, h = 1000, 1000
        elif fallback and fallback.startswith('art'):
            w, h = 1920, 1080
        else:
            w, h = 1000, 1500

        image_info = {'img': img,
                      'rating_key': rating_key,
                      'width': w,
                      'height': h,
                      'opacity': 100,
                      'background': '000000',
                      'blur': 0,
                      'fallback': fallback}

    else:
        image_info = {'img': img,
                      'rating_key': rating_key,
                      'width': width,
                      'height': height,
                      'opacity': opacity,
                      'background': background,
                      'blur': blur,
                      'fallback': fallback}

    # Try to retrieve poster info from the database
    data_factory = datafactory.DataFactory()
    database_img_info = data_factory.get_img_info(service=service, **image_info)

    if database_img_info:
        img_info = database_img_info[0]

    elif not database_img_info and img:
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_image(refresh=True, **image_info)

        if result and result[0]:
            img_url = delete_hash = ''

            if service == 'imgur':
                img_url, delete_hash = helpers.upload_to_imgur(img_data=result[0],
                                                               img_title=title,
                                                               rating_key=rating_key,
                                                               fallback=fallback)
            elif service == 'cloudinary':
                img_url = helpers.upload_to_cloudinary(img_data=result[0],
                                                       img_title=title,
                                                       rating_key=rating_key,
                                                       fallback=fallback)

            if img_url:
                img_hash = set_hash_image_info(**image_info)
                data_factory.set_img_info(img_hash=img_hash,
                                          img_title=title,
                                          img_url=img_url,
                                          delete_hash=delete_hash,
                                          service=service)

                img_info = {'img_title': title, 'img_url': img_url}

    if img_info['img_url'] and service == 'cloudinary':
        # Transform image using Cloudinary
        image_info = {'rating_key': rating_key,
                      'width': width,
                      'height': height,
                      'opacity': opacity,
                      'background': background,
                      'blur': blur,
                      'fallback': fallback,
                      'img_title': title}

        transformed_url = helpers.cloudinary_transform(**image_info)
        if transformed_url:
            img_info['img_url'] = transformed_url

    return img_info


def set_hash_image_info(img=None, rating_key=None, width=750, height=1000,
                        opacity=100, background='000000', blur=0, fallback=None,
                        add_to_db=True):
    if not rating_key and not img:
        return fallback

    if rating_key and not img:
        if fallback and fallback.startswith('art'):
            img = '/library/metadata/{}/art'.format(rating_key)
        else:
            img = '/library/metadata/{}/thumb'.format(rating_key)

    if img.startswith('/library/metadata'):
        img_split = img.split('/')
        img = '/'.join(img_split[:5])
        img_rating_key = img_split[3]
        if rating_key != img_rating_key:
            rating_key = img_rating_key

    img_string = '{}.{}.{}.{}.{}.{}.{}.{}'.format(
        plexpy.CONFIG.PMS_UUID, img, rating_key, width, height, opacity, background, blur, fallback)
    img_hash = hashlib.sha256(img_string.encode('utf-8')).hexdigest()

    if add_to_db:
        keys = {'img_hash': img_hash}
        values = {'img': img,
                  'rating_key': rating_key,
                  'width': width,
                  'height': height,
                  'opacity': opacity,
                  'background': background,
                  'blur': blur,
                  'fallback': fallback}

        db = database.MonitorDatabase()
        db.upsert('image_hash_lookup', key_dict=keys, value_dict=values)

    return img_hash


def get_hash_image_info(img_hash=None):
    db = database.MonitorDatabase()
    query = "SELECT * FROM image_hash_lookup WHERE img_hash = ?"
    result = db.select_single(query, args=[img_hash])
    return result


def lookup_tvmaze_by_id(rating_key=None, thetvdb_id=None, imdb_id=None, title=None):
    db = database.MonitorDatabase()

    try:
        query = "SELECT imdb_id, tvmaze_id, tvmaze_url FROM tvmaze_lookup " \
                "WHERE rating_key = ?"
        tvmaze_info = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn("Tautulli NotificationHandler :: Unable to execute database query for lookup_tvmaze_by_tvdb_id: %s." % e)
        return {}

    if not tvmaze_info:
        tvmaze_info = {}

        if thetvdb_id:
            logger.debug("Tautulli NotificationHandler :: Looking up TVmaze info for thetvdb_id '{}'.".format(thetvdb_id))
        elif imdb_id:
            logger.debug("Tautulli NotificationHandler :: Looking up TVmaze info for imdb_id '{}'.".format(imdb_id))
        else:
            logger.debug("Tautulli NotificationHandler :: Looking up TVmaze info for '{}'.".format(title))

        if thetvdb_id or imdb_id:
            params = {'thetvdb': thetvdb_id} if thetvdb_id else {'imdb': imdb_id}
            response, err_msg, req_msg = request.request_response2(
                'http://api.tvmaze.com/lookup/shows', params=params)
        elif title:
            params = {'q': title}
            response, err_msg, req_msg = request.request_response2(
                'https://api.tvmaze.com/singlesearch/shows', params=params)
        else:
            return tvmaze_info

        if response and not err_msg:
            tvmaze_json = response.json()
            thetvdb_id = tvmaze_json.get('externals', {}).get('thetvdb', '')
            imdb_id = tvmaze_json.get('externals', {}).get('imdb', '')
            tvmaze_id = tvmaze_json.get('id', '')
            tvmaze_url = tvmaze_json.get('url', '')

            keys = {'tvmaze_id': tvmaze_id}
            tvmaze_info = {'rating_key': rating_key,
                           'thetvdb_id': thetvdb_id,
                           'imdb_id': imdb_id,
                           'tvmaze_url': tvmaze_url,
                           'tvmaze_json': json.dumps(tvmaze_json)}
            db.upsert(table_name='tvmaze_lookup', key_dict=keys, value_dict=tvmaze_info)

            tvmaze_info.update(keys)
            tvmaze_info.pop('tvmaze_json')

        else:
            if err_msg:
                logger.error("Tautulli NotificationHandler :: {}".format(err_msg))

            if req_msg:
                logger.debug("Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return tvmaze_info


def lookup_themoviedb_by_id(rating_key=None, thetvdb_id=None, imdb_id=None, title=None, year=None, media_type=None):
    db = database.MonitorDatabase()

    try:
        query = "SELECT thetvdb_id, imdb_id, themoviedb_id, themoviedb_url FROM themoviedb_lookup " \
                "WHERE rating_key = ?"
        themoviedb_info = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn("Tautulli NotificationHandler :: Unable to execute database query for lookup_themoviedb_by_imdb_id: %s." % e)
        return {}

    if not themoviedb_info:
        themoviedb_info = {}

        if thetvdb_id:
            logger.debug("Tautulli NotificationHandler :: Looking up The Movie Database info for thetvdb_id '{}'.".format(thetvdb_id))
        elif imdb_id:
            logger.debug("Tautulli NotificationHandler :: Looking up The Movie Database info for imdb_id '{}'.".format(imdb_id))
        else:
            logger.debug("Tautulli NotificationHandler :: Looking up The Movie Database info for '{} ({})'.".format(title, year))

        params = {'api_key': plexpy.CONFIG.THEMOVIEDB_APIKEY}

        if thetvdb_id or imdb_id:
            params['external_source'] = 'tvdb_id' if thetvdb_id else 'imdb_id'
            response, err_msg, req_msg = request.request_response2(
                'https://api.themoviedb.org/3/find/{}'.format(thetvdb_id or imdb_id), params=params)
        elif title and year and media_type:
            params['query'] = title
            params['year'] = year
            response, err_msg, req_msg = request.request_response2(
                'https://api.themoviedb.org/3/search/{}'.format(media_type), params=params)
        else:
            return themoviedb_info

        if response and not err_msg:
            themoviedb_find_json = response.json()
            if themoviedb_find_json.get('tv_results'):
                themoviedb_id = themoviedb_find_json['tv_results'][0]['id']
            elif themoviedb_find_json.get('movie_results'):
                themoviedb_id = themoviedb_find_json['movie_results'][0]['id']
            elif themoviedb_find_json.get('results'):
                themoviedb_id = themoviedb_find_json['results'][0]['id']
            else:
                themoviedb_id = ''

            if themoviedb_id:
                themoviedb_url = 'https://www.themoviedb.org/{}/{}'.format(media_type, themoviedb_id)
                themoviedb_json = get_themoviedb_info(rating_key=rating_key,
                                                      media_type=media_type,
                                                      themoviedb_id=themoviedb_id)

                keys = {'themoviedb_id': themoviedb_id}
                themoviedb_info = {'rating_key': rating_key,
                                   'thetvdb_id': thetvdb_id,
                                   'imdb_id': imdb_id or themoviedb_json.get('imdb_id'),
                                   'themoviedb_url': themoviedb_url,
                                   'themoviedb_json': json.dumps(themoviedb_json)
                                   }

                db.upsert(table_name='themoviedb_lookup', key_dict=keys, value_dict=themoviedb_info)

                themoviedb_info.update(keys)
                themoviedb_info.pop('themoviedb_json')

        else:
            if err_msg:
                logger.error("Tautulli NotificationHandler :: {}".format(err_msg))

            if req_msg:
                logger.debug("Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return themoviedb_info


def get_themoviedb_info(rating_key=None, media_type=None, themoviedb_id=None):
    if media_type in ('show', 'season', 'episode'):
        media_type = 'tv'

    db = database.MonitorDatabase()

    try:
        query = "SELECT themoviedb_json FROM themoviedb_lookup " \
                "WHERE rating_key = ?"
        result = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn("Tautulli NotificationHandler :: Unable to execute database query for get_themoviedb_info: %s." % e)
        return {}

    if result:
        try:
            return json.loads(result['themoviedb_json'])
        except:
            pass

    themoviedb_json = {}

    logger.debug("Tautulli NotificationHandler :: Looking up The Movie Database info for themoviedb_id '{}'.".format(themoviedb_id))

    params = {'api_key': plexpy.CONFIG.THEMOVIEDB_APIKEY}
    response, err_msg, req_msg = request.request_response2('https://api.themoviedb.org/3/{}/{}'.format(media_type, themoviedb_id), params=params)

    if response and not err_msg:
        themoviedb_json = response.json()
        themoviedb_id = themoviedb_json['id']
        themoviedb_url = 'https://www.themoviedb.org/{}/{}'.format(media_type, themoviedb_id)

        keys = {'themoviedb_id': themoviedb_id}
        themoviedb_info = {'rating_key': rating_key,
                           'imdb_id': themoviedb_json.get('imdb_id'),
                           'themoviedb_url': themoviedb_url,
                           'themoviedb_json': json.dumps(themoviedb_json)
                           }

        db.upsert(table_name='themoviedb_lookup', key_dict=keys, value_dict=themoviedb_info)

        themoviedb_info.update(keys)

    else:
        if err_msg:
            logger.error("Tautulli NotificationHandler :: {}".format(err_msg))

        if req_msg:
            logger.debug("Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return themoviedb_json


def lookup_musicbrainz_info(musicbrainz_type=None, rating_key=None, artist=None, release=None, recording=None,
                            tracks=None, tnum=None):
    db = database.MonitorDatabase()

    try:
        query = "SELECT musicbrainz_id, musicbrainz_url, musicbrainz_type FROM musicbrainz_lookup " \
                "WHERE rating_key = ?"
        musicbrainz_info = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn("Tautulli NotificationHandler :: Unable to execute database query for lookup_musicbrainz: %s." % e)
        return {}

    if not musicbrainz_info:
        musicbrainzngs.set_useragent(
            common.PRODUCT,
            common.RELEASE,
            "https://tautulli.com",
        )

        if musicbrainz_type == 'artist':
            logger.debug("Tautulli NotificationHandler :: Looking up MusicBrainz info for "
                         "{} '{}'.".format(musicbrainz_type, artist))
            result = musicbrainzngs.search_artists(artist=artist, strict=True, limit=1)
            if result['artist-list']:
                musicbrainz_info = result['artist-list'][0]

        elif musicbrainz_type == 'release':
            logger.debug("Tautulli NotificationHandler :: Looking up MusicBrainz info for "
                         "{} '{} - {}'.".format(musicbrainz_type, artist, release))
            result = musicbrainzngs.search_releases(artist=artist, release=release, tracks=tracks,
                                                    strict=True, limit=1)
            if result['release-list']:
                musicbrainz_info = result['release-list'][0]

        elif musicbrainz_type == 'recording':
            logger.debug("Tautulli NotificationHandler :: Looking up MusicBrainz info for "
                         "{} '{} - {} - {}'.".format(musicbrainz_type, artist, release, recording))
            result = musicbrainzngs.search_recordings(artist=artist, release=release, recording=recording,
                                                      tracks=tracks, tnum=tnum,
                                                      strict=True, limit=1)
            if result['recording-list']:
                musicbrainz_info = result['recording-list'][0]

        if musicbrainz_info:
            musicbrainz_id = musicbrainz_info['id']
            musicbrainz_url = 'https://musicbrainz.org/' + musicbrainz_type + '/' + musicbrainz_id

            keys = {'musicbrainz_id': musicbrainz_id}
            musicbrainz_info = {'rating_key': rating_key,
                                'musicbrainz_url': musicbrainz_url,
                                'musicbrainz_type': musicbrainz_type,
                                'musicbrainz_json': json.dumps(musicbrainz_info)}
            db.upsert(table_name='musicbrainz_lookup', key_dict=keys, value_dict=musicbrainz_info)

            musicbrainz_info.update(keys)
            musicbrainz_info.pop('musicbrainz_json')

        else:
            logger.warn("Tautulli NotificationHandler :: No match found on MusicBrainz.")

    return musicbrainz_info


def str_format(s, parameters):
    custom_formatter = CustomFormatter()
    if isinstance(s, str):
        return custom_formatter.format(str(s), **parameters)
    return s


def str_eval(field_name, kwargs):
    field_name = field_name.strip('`')
    allowed_names = {
        'bool': bool,
        'divmod': helpers.helper_divmod,
        'float': helpers.cast_to_float,
        'int': helpers.cast_to_int,
        'len': helpers.helper_len,
        'round': helpers.helper_round,
        'str': str
    }
    allowed_names.update(kwargs)
    code = compile(field_name, '<string>', 'eval')
    for name in code.co_names:
        if name not in allowed_names:
            raise NameError('Use of {name} not allowed'.format(name=name))
    return eval(code, {'__builtins__': {}}, allowed_names)


class CustomFormatter(Formatter):
    def __init__(self, default='{{{0}}}'):
        self.default = default
        self.eval_regex = re.compile(r'`.*?`')
        self.eval_replace_regex = re.compile(r'{.*(`.*?`).*}')
        self.eval_replace = {
            ':': '%%colon%%',
            '!': '%%exclamation%%'
        }

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        elif conversion == 's':
            return str(value)
        elif conversion == 'r':
            return repr(value)
        elif conversion == 'u':  # uppercase
            return str(value).upper()
        elif conversion == 'l':  # lowercase
            return str(value).lower()
        elif conversion == 'c':  # capitalize
            return str(value).title()
        else:
            return value

    def format_field(self, value, format_spec):
        if format_spec.startswith('[') and format_spec.endswith(']'):
            pattern = re.compile(r'\[(?P<start>-?\d*)(?P<slice>:?)(?P<end>-?\d*)\]')
            match = re.match(pattern, format_spec)
            if value and match:
                groups = match.groupdict()
                items = [x.strip() for x in str(value).split(',')]
                start = groups['start'] or None
                end = groups['end'] or None
                if start is not None:
                    start = helpers.cast_to_int(start)
                if end is not None:
                    end = helpers.cast_to_int(end)
                if not groups['slice']:
                    end = start + 1
                value = ', '.join(items[slice(start, end)])
            return value
        else:
            try:
                return super(CustomFormatter, self).format_field(value, format_spec)
            except ValueError:
                return value

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, self.default.format(key))
        else:
            return super(CustomFormatter, self).get_value(key, args, kwargs)

    def parse(self, format_string):
        # Replace characters in eval expression
        for match in re.findall(self.eval_replace_regex, format_string):
            replaced = match
            for k, v in self.eval_replace.items():
                replaced = replaced.replace(k, v)
            format_string = format_string.replace(match, replaced)

        parsed = super(CustomFormatter, self).parse(format_string)

        for literal_text, field_name, format_spec, conversion in parsed:
            # Restore characters in eval expression
            if field_name:
                for k, v in self.eval_replace.items():
                    field_name = field_name.replace(v, k)

            real_format_string = ''
            if field_name:
                real_format_string += field_name
            if conversion:
                real_format_string += '!' + conversion
            if format_spec:
                real_format_string += ':' + format_spec

            prefix = None
            suffix = None

            matches = re.findall(self.eval_regex, real_format_string)
            temp_format_string = re.sub(self.eval_regex, '{}', real_format_string)

            prefix_split = temp_format_string.split('<')
            if len(prefix_split) == 2:
                prefix = prefix_split[0].replace('\\n', '\n')
                temp_format_string = prefix_split[1]

            suffix_split = temp_format_string.split('>')
            if len(suffix_split) == 2:
                suffix = suffix_split[1].replace('\\n', '\n')
                temp_format_string = suffix_split[0]

            if prefix or suffix:
                real_format_string = '{' + temp_format_string.format(*matches) + '}'
                _, field_name, format_spec, conversion, _, _ = next(self.parse(real_format_string))

            yield literal_text, field_name, format_spec, conversion, prefix, suffix

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth,
                 auto_arg_index=0):
        if recursion_depth < 0:
            raise ValueError('Max string recursion exceeded')
        result = []
        for literal_text, field_name, format_spec, conversion, prefix, suffix in self.parse(format_string):
            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if field_name is not None:
                # this is some markup, find the object and do
                #  the formatting

                # handle arg indexing when empty field_names are given.
                if field_name == '':
                    if auto_arg_index is False:
                        raise ValueError('cannot switch from manual field '
                                         'specification to automatic field '
                                         'numbering')
                    field_name = str(auto_arg_index)
                    auto_arg_index += 1
                elif field_name.isdigit():
                    if auto_arg_index:
                        raise ValueError('cannot switch from manual field '
                                         'specification to automatic field '
                                         'numbering')
                    # disable auto arg incrementing, if it gets
                    # used later on, then an exception will be raised
                    auto_arg_index = False

                if plexpy.CONFIG.NOTIFY_TEXT_EVAL and field_name.startswith('`') and field_name.endswith('`'):
                    try:
                        obj = str_eval(field_name, kwargs)
                        used_args.add(field_name)
                    except (SyntaxError, NameError, ValueError, TypeError) as e:
                        logger.error("Tautulli NotificationHandler :: Failed to evaluate notification text %s: %s.",
                                     field_name, e)
                        obj = field_name
                else:
                    # given the field_name, find the object it references
                    #  and the argument it came from
                    obj, arg_used = self.get_field(field_name, args, kwargs)
                    used_args.add(arg_used)

                # do any conversion on the resulting object
                obj = self.convert_field(obj, conversion)

                # expand the format spec, if needed
                format_spec, auto_arg_index = self._vformat(
                    format_spec, args, kwargs,
                    used_args, recursion_depth-1,
                    auto_arg_index=auto_arg_index)

                # format the object and append to the result
                formatted_field = self.format_field(obj, format_spec)
                if formatted_field:
                    if prefix:
                        result.append(prefix)
                    result.append(formatted_field)
                    if suffix:
                        result.append(suffix)
                # result.append(self.format_field(obj, format_spec))

        return ''.join(result), auto_arg_index


class CustomArrow:
    def __init__(self, arrow_value: arrow.arrow.Arrow, default_format: Optional[str] = None):
        self.arrow_value = arrow_value
        self.default_format = default_format

    def __format__(self, formatstr: str) -> str:
        if len(formatstr) > 0:
            return self.arrow_value.format(formatstr)

        if self.default_format is not None:
            return self.__format__(self.default_format)
    
        return str(self.arrow_value)

    def __str__(self) -> str:
        return self.__format__('')
