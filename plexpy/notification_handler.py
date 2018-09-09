﻿#  This file is part of Tautulli.
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


import arrow
import bleach
from collections import Counter, defaultdict
import hashlib
from itertools import groupby
import json
from operator import itemgetter
import os
import re
from string import Formatter
import threading
import time

import plexpy
import activity_processor
import common
import database
import datafactory
import libraries
import logger
import helpers
import notifiers
import plextv
import pmsconnect
import request
import users
from newsletter_handler import notify as notify_newsletter


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
                logger.exception(u"Tautulli NotificationHandler :: Notification thread exception: %s" % e)
                
        queue.task_done()

    logger.info(u"Tautulli NotificationHandler :: Notification thread exiting...")


def start_threads(num_threads=1):
    logger.info(u"Tautulli NotificationHandler :: Starting background notification handler ({} threads).".format(num_threads))
    for x in range(num_threads):
        thread = threading.Thread(target=process_queue)
        thread.daemon = True
        thread.start()


def add_notifier_each(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, manual_trigger=False, **kwargs):
    if not notify_action:
        logger.debug(u"Tautulli NotificationHandler :: Notify called but no action received.")
        return

    if notifier_id:
        # Send to a specific notifier regardless if it is enabled
        notifiers_enabled = notifiers.get_notifiers(notifier_id=notifier_id)
    else:
        # Check if any notification agents have notifications enabled for the action
        notifiers_enabled = notifiers.get_notifiers(notify_action=notify_action)

    if notifiers_enabled and not manual_trigger:
        # Check if notification conditions are satisfied
        conditions = notify_conditions(notify_action=notify_action,
                                       stream_data=stream_data,
                                       timeline_data=timeline_data)
    else:
        conditions = True

    if notifiers_enabled and (manual_trigger or conditions):
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
            logger.error(u"Tautulli NotificationHandler :: Failed to build notification parameters.")
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
                logger.debug(u"Tautulli NotificationHandler :: Custom notification conditions not satisfied, skipping notifier_id %s." % notifier['id'])

    # Add on_concurrent and on_newdevice to queue if action is on_play
    if notify_action == 'on_play':
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data.copy(), 'notify_action': 'on_concurrent'})
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data.copy(), 'notify_action': 'on_newdevice'})


def notify_conditions(notify_action=None, stream_data=None, timeline_data=None):
    # Activity notifications
    if stream_data:

        # Check if notifications enabled for user and library
        # user_data = users.Users()
        # user_details = user_data.get_details(user_id=stream_data['user_id'])
        #
        # library_data = libraries.Libraries()
        # library_details = library_data.get_details(section_id=stream_data['section_id'])

        # if not user_details['do_notify']:
        #     logger.debug(u"Tautulli NotificationHandler :: Notifications for user '%s' are disabled." % user_details['username'])
        #     return False
        #
        # elif not library_details['do_notify'] and notify_action not in ('on_concurrent', 'on_newdevice'):
        #     logger.debug(u"Tautulli NotificationHandler :: Notifications for library '%s' are disabled." % library_details['section_name'])
        #     return False

        if notify_action == 'on_concurrent':
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_current_activity()

            user_sessions = []
            if result:
                user_sessions = [s for s in result['sessions'] if s['user_id'] == stream_data['user_id']]

            if plexpy.CONFIG.NOTIFY_CONCURRENT_BY_IP:
                return len(Counter(s['ip_address'] for s in user_sessions)) >= plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD
            else:
                return len(user_sessions) >= plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD

        elif notify_action == 'on_newdevice':
            data_factory = datafactory.DataFactory()
            user_devices = data_factory.get_user_devices(user_id=stream_data['user_id'])
            return stream_data['machine_id'] not in user_devices

        elif stream_data['media_type'] in ('movie', 'episode', 'clip'):
            progress_percent = helpers.get_percent(stream_data['view_offset'], stream_data['duration'])
            
            if notify_action == 'on_stop':
                return (plexpy.CONFIG.NOTIFY_CONSECUTIVE or
                    (stream_data['media_type'] == 'movie' and progress_percent < plexpy.CONFIG.MOVIE_WATCHED_PERCENT) or 
                    (stream_data['media_type'] == 'episode' and progress_percent < plexpy.CONFIG.TV_WATCHED_PERCENT))
            
            elif notify_action == 'on_resume':
                return plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99

            # All other activity notify actions
            else:
                return True

        elif stream_data['media_type'] == 'track':
            return True

        else:
            return False

    # Recently Added notifications
    elif timeline_data:

        # Check if notifications enabled for library
        # library_data = libraries.Libraries()
        # library_details = library_data.get_details(section_id=timeline_data['section_id'])
        #
        # if not library_details['do_notify_created']:
        #     # logger.debug(u"Tautulli NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
        #     return False

        return True

    # Server notifications
    else:
        return True


def notify_custom_conditions(notifier_id=None, parameters=None):
    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    custom_conditions_logic = notifier_config['custom_conditions_logic']
    custom_conditions = notifier_config['custom_conditions']

    if custom_conditions_logic or any(c for c in custom_conditions if c['value']):
        logger.debug(u"Tautulli NotificationHandler :: Checking custom notification conditions for notifier_id %s."
                     % notifier_id)

        logic_groups = None
        if custom_conditions_logic:
            try:
                # Parse and validate the custom conditions logic
                logic_groups = helpers.parse_condition_logic_string(custom_conditions_logic, len(custom_conditions))
            except ValueError as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to parse custom condition logic '%s': %s."
                             % (custom_conditions_logic, e))
                return False

        evaluated_conditions = [None]  # Set condition {0} to None

        for condition in custom_conditions:
            parameter = condition['parameter']
            operator = condition['operator']
            values = condition['value']
            parameter_type = condition['type']
            parameter_value = parameters.get(parameter, "")

            # Set blank conditions to True (skip)
            if not parameter or not operator or not values:
                evaluated_conditions.append(True)
                continue

            # Make sure the condition values is in a list
            if isinstance(values, basestring):
                values = [values]

            # Cast the condition values to the correct type
            try:
                if parameter_type == 'str':
                    values = [unicode(v).lower() for v in values]

                elif parameter_type == 'int':
                    values = [helpers.cast_to_int(v) for v in values]

                elif parameter_type == 'float':
                    values = [helpers.cast_to_float(v) for v in values]

            except ValueError as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to cast condition '%s', values '%s', to type '%s'."
                             % (parameter, values, parameter_type))
                return False

            # Cast the parameter value to the correct type
            try:
                if parameter_type == 'str':
                    parameter_value = unicode(parameter_value).lower()

                elif parameter_type == 'int':
                    parameter_value = helpers.cast_to_int(parameter_value)

                elif parameter_type == 'float':
                    parameter_value = helpers.cast_to_float(parameter_value)

            except ValueError as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to cast parameter '%s', value '%s', to type '%s'."
                             % (parameter, parameter_value, parameter_type))
                return False

            # Check each condition
            if operator == 'contains':
                evaluated_conditions.append(any(c in parameter_value for c in values))

            elif operator == 'does not contain':
                evaluated_conditions.append(all(c not in parameter_value for c in values))

            elif operator == 'is':
                evaluated_conditions.append(any(parameter_value == c for c in values))

            elif operator == 'is not':
                evaluated_conditions.append(all(parameter_value != c for c in values))

            elif operator == 'begins with':
                evaluated_conditions.append(parameter_value.startswith(tuple(values)))

            elif operator == 'ends with':
                evaluated_conditions.append(parameter_value.endswith(tuple(values)))

            elif operator == 'is greater than':
                evaluated_conditions.append(any(parameter_value > c for c in values))

            elif operator == 'is less than':
                evaluated_conditions.append(any(parameter_value < c for c in values))

            else:
                logger.warn(u"Tautulli NotificationHandler :: Invalid condition operator '%s'." % operator)
                evaluated_conditions.append(None)

        if logic_groups:
            # Format and evaluate the logic string
            try:
                evaluated_logic = helpers.eval_logic_groups_to_bool(logic_groups, evaluated_conditions)
            except Exception as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to evaluate custom condition logic: %s." % e)
                return False
        else:
            evaluated_logic = all(evaluated_conditions[1:])

        logger.debug(u"Tautulli NotificationHandler :: Custom condition evaluated to '{}'. Conditions: {}.".format(
            evaluated_logic, evaluated_conditions[1:]))

        return evaluated_logic

    return True


def notify(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, parameters=None, **kwargs):
    logger.info(u"Tautulli NotificationHandler :: Preparing notification for notifier_id %s." % notifier_id)

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
                                                       agent_id=notifier_config['agent_id'])

    # Set the notification state in the db
    notification_id = set_notify_state(session=stream_data or timeline_data,
                                       notifier=notifier_config,
                                       notify_action=notify_action,
                                       subject=subject,
                                       body=body,
                                       script_args=script_args)

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
        return True


def get_notify_state(session):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT timestamp, notify_action, notifier_id '
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
                        'notifier_id': item['notifier_id']}
        notify_states.append(notify_state)

    return notify_states


def get_notify_state_enabled(session, notify_action, notified=True):
    if notified:
        timestamp_where = 'AND timestamp IS NOT NULL'
    else:
        timestamp_where = 'AND timestamp IS NULL'

    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT id AS notifier_id, timestamp '
                               'FROM notifiers '
                               'LEFT OUTER JOIN ('
                               'SELECT timestamp, notifier_id '
                               'FROM notify_log '
                               'WHERE session_key = ? '
                               'AND rating_key = ? '
                               'AND user_id = ? '
                               'AND notify_action = ?) AS t ON notifiers.id = t.notifier_id '
                               'WHERE %s = 1 %s' % (notify_action, timestamp_where),
                               args=[session['session_key'], session['rating_key'], session['user_id'], notify_action])

    return result


def set_notify_state(notifier, notify_action, subject='', body='', script_args='', session=None):

    if notifier and notify_action:
        monitor_db = database.MonitorDatabase()

        session = session or {}

        script_args = json.dumps(script_args) if script_args else None

        keys = {'timestamp': int(time.time()),
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

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
        return monitor_db.last_insert_id()
    else:
        logger.error(u"Tautulli NotificationHandler :: Unable to set notify state.")


def set_notify_success(notification_id):
    keys = {'id': notification_id}
    values = {'success': 1}

    monitor_db = database.MonitorDatabase()
    monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)


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
            session.update(json.loads(session['raw_stream_info']))
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

    child_metadata = grandchild_metadata = []
    for key in kwargs.pop('child_keys', []):
        child_metadata.append(pmsconnect.PmsConnect().get_metadata_details(rating_key=key))
    for key in kwargs.pop('grandchild_keys', []):
        grandchild_metadata.append(pmsconnect.PmsConnect().get_metadata_details(rating_key=key))

    # Session values
    session = session or {}

    ap = activity_processor.ActivityProcessor()
    sessions = ap.get_sessions()
    stream_count = len(sessions)
    user_sessions = ap.get_sessions(user_id=session.get('user_id'))
    user_stream_count = len(user_sessions)

    # Generate a combined transcode decision value
    if session.get('stream_video_decision', '') == 'transcode' or session.get('stream_audio_decision', '') == 'transcode':
        transcode_decision = 'Transcode'
    elif session.get('stream_video_decision', '') == 'copy' or session.get('stream_audio_decision', '') == 'copy':
        transcode_decision = 'Direct Stream'
    else:
        transcode_decision = 'Direct Play'

    if notify_action != 'on_play':
        stream_duration = int((time.time() -
                               helpers.cast_to_int(session.get('started', 0)) -
                               helpers.cast_to_int(session.get('paused_counter', 0))) / 60)
    else:
        stream_duration = 0

    view_offset = helpers.convert_milliseconds_to_minutes(session.get('view_offset', 0))
    duration = helpers.convert_milliseconds_to_minutes(notify_params['duration'])
    remaining_duration = duration - view_offset

    # Build Plex URL
    if notify_params['media_type'] == 'track':
        plex_web_rating_key = notify_params['parent_rating_key']
    else:
        plex_web_rating_key = notify_params['rating_key']

    notify_params['plex_url'] = '{web_url}#!/server/{pms_identifier}/details?key=%2Flibrary%2Fmetadata%2F{rating_key}'.format(
        web_url=plexpy.CONFIG.PMS_WEB_URL,
        pms_identifier=plexpy.CONFIG.PMS_IDENTIFIER,
        rating_key=plex_web_rating_key)

    # Get media IDs from guid and build URLs
    if 'imdb://' in notify_params['guid']:
        notify_params['imdb_id'] = notify_params['guid'].split('imdb://')[1].split('?')[0]
        notify_params['imdb_url'] = 'https://www.imdb.com/title/' + notify_params['imdb_id']
        notify_params['trakt_url'] = 'https://trakt.tv/search/imdb/' + notify_params['imdb_id']

    if 'thetvdb://' in notify_params['guid']:
        notify_params['thetvdb_id'] = notify_params['guid'].split('thetvdb://')[1].split('/')[0].split('?')[0]
        notify_params['thetvdb_url'] = 'https://thetvdb.com/?tab=series&id=' + notify_params['thetvdb_id']
        notify_params['trakt_url'] = 'https://trakt.tv/search/tvdb/' + notify_params['thetvdb_id'] + '?id_type=show'

    elif 'thetvdbdvdorder://' in notify_params['guid']:
        notify_params['thetvdb_id'] = notify_params['guid'].split('thetvdbdvdorder://')[1].split('/')[0].split('?')[0]
        notify_params['thetvdb_url'] = 'https://thetvdb.com/?tab=series&id=' + notify_params['thetvdb_id']
        notify_params['trakt_url'] = 'https://trakt.tv/search/tvdb/' + notify_params['thetvdb_id'] + '?id_type=show'

    if 'themoviedb://' in notify_params['guid']:
        if notify_params['media_type'] == 'movie':
            notify_params['themoviedb_id'] = notify_params['guid'].split('themoviedb://')[1].split('?')[0]
            notify_params['themoviedb_url'] = 'https://www.themoviedb.org/movie/' + notify_params['themoviedb_id']
            notify_params['trakt_url'] = 'https://trakt.tv/search/tmdb/' + notify_params['themoviedb_id'] + '?id_type=movie'

        elif notify_params['media_type'] in ('show', 'season', 'episode'):
            notify_params['themoviedb_id'] = notify_params['guid'].split('themoviedb://')[1].split('/')[0].split('?')[0]
            notify_params['themoviedb_url'] = 'https://www.themoviedb.org/tv/' + notify_params['themoviedb_id']
            notify_params['trakt_url'] = 'https://trakt.tv/search/tmdb/' + notify_params['themoviedb_id'] + '?id_type=show'

    if 'lastfm://' in notify_params['guid']:
        notify_params['lastfm_id'] = notify_params['guid'].split('lastfm://')[1].rsplit('/', 1)[0]
        notify_params['lastfm_url'] = 'https://www.last.fm/music/' + notify_params['lastfm_id']

    # Get TheMovieDB info
    if plexpy.CONFIG.THEMOVIEDB_LOOKUP:
        if notify_params.get('themoviedb_id'):
            themoveidb_json = get_themoviedb_info(rating_key=rating_key,
                                                  media_type=notify_params['media_type'],
                                                  themoviedb_id=notify_params['themoviedb_id'])

            if themoveidb_json.get('imdb_id'):
                notify_params['imdb_id'] = themoveidb_json['imdb_id']
                notify_params['imdb_url'] = 'https://www.imdb.com/title/' + themoveidb_json['imdb_id']

        elif notify_params.get('thetvdb_id') or notify_params.get('imdb_id'):
            if notify_params['media_type'] in ('episode', 'track'):
                lookup_key = notify_params['grandparent_rating_key']
            elif notify_params['media_type'] in ('season', 'album'):
                lookup_key = notify_params['parent_rating_key']
            else:
                lookup_key = rating_key

            themoviedb_info = lookup_themoviedb_by_id(rating_key=lookup_key,
                                                      thetvdb_id=notify_params.get('thetvdb_id'),
                                                      imdb_id=notify_params.get('imdb_id'))
            notify_params.update(themoviedb_info)

    # Get TVmaze info (for tv shows only)
    if plexpy.CONFIG.TVMAZE_LOOKUP:
        if notify_params['media_type'] in ('show', 'season', 'episode') and (notify_params.get('thetvdb_id') or notify_params.get('imdb_id')):
            if notify_params['media_type'] in ('episode', 'track'):
                lookup_key = notify_params['grandparent_rating_key']
            elif notify_params['media_type'] in ('season', 'album'):
                lookup_key = notify_params['parent_rating_key']
            else:
                lookup_key = rating_key

            tvmaze_info = lookup_tvmaze_by_id(rating_key=lookup_key,
                                              thetvdb_id=notify_params.get('thetvdb_id'),
                                              imdb_id=notify_params.get('imdb_id'))
            notify_params.update(tvmaze_info)

            if tvmaze_info.get('thetvdb_id'):
                notify_params['thetvdb_url'] = 'https://thetvdb.com/?tab=series&id=' + str(tvmaze_info['thetvdb_id'])
            if tvmaze_info.get('imdb_id'):
                notify_params['imdb_url'] = 'https://www.imdb.com/title/' + tvmaze_info['imdb_id']

    if notify_params['media_type'] in ('movie', 'show', 'artist'):
        poster_thumb = notify_params['thumb']
        poster_key = notify_params['rating_key']
        poster_title = notify_params['title']
    elif notify_params['media_type'] in ('season', 'album'):
        poster_thumb = notify_params['thumb'] or notify_params['parent_thumb']
        poster_key = notify_params['rating_key']
        poster_title = '%s - %s' % (notify_params['parent_title'],
                                    notify_params['title'])
    elif notify_params['media_type'] in ('episode', 'track'):
        poster_thumb = notify_params['parent_thumb'] or notify_params['grandparent_thumb']
        poster_key = notify_params['parent_rating_key']
        poster_title = '%s - %s' % (notify_params['grandparent_title'],
                                    notify_params['parent_title'])
    else:
        poster_thumb = ''
        poster_key = ''
        poster_title = ''

    img_service = helpers.get_img_service(include_self=True)
    if img_service not in (None, 'self-hosted'):
        img_info = get_img_info(img=poster_thumb, rating_key=poster_key, title=poster_title, fallback='poster')
        poster_info = {'poster_title': img_info['img_title'], 'poster_url': img_info['img_url']}
        notify_params.update(poster_info)
    elif img_service == 'self-hosted' and plexpy.CONFIG.HTTP_BASE_URL:
        img_hash = set_hash_image_info(img=poster_thumb, fallback='poster')
        poster_info = {'poster_title': poster_title,
                       'poster_url': plexpy.CONFIG.HTTP_BASE_URL + plexpy.HTTP_ROOT + 'image/' + img_hash}
        notify_params.update(poster_info)

    if ((manual_trigger or plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT)
        and notify_params['media_type'] in ('show', 'artist')):
        show_name = notify_params['title']
        episode_name = ''
        artist_name = notify_params['title']
        album_name = ''
        track_name = ''

        child_num = [helpers.cast_to_int(
            d['media_index']) for d in child_metadata if d['parent_rating_key'] == rating_key]
        num, num00 = format_group_index(child_num)
        season_num, season_num00 = num, num00

        episode_num, episode_num00 = '', ''
        track_num, track_num00 = '', ''

        child_count = len(child_num)
        grandchild_count = ''

    elif ((manual_trigger or plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_PARENT)
          and notify_params['media_type'] in ('season', 'album')):
        show_name = notify_params['parent_title']
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

        child_count = 1
        grandchild_count = len(grandchild_num)

    else:
        show_name = notify_params['grandparent_title']
        episode_name = notify_params['title']
        artist_name = notify_params['grandparent_title']
        album_name = notify_params['parent_title']
        track_name = notify_params['title']
        season_num = str(notify_params['parent_media_index']).zfill(1)
        season_num00 = str(notify_params['parent_media_index']).zfill(2)
        episode_num = str(notify_params['media_index']).zfill(1)
        episode_num00 = str(notify_params['media_index']).zfill(2)
        track_num = str(notify_params['media_index']).zfill(1)
        track_num00 = str(notify_params['media_index']).zfill(2)
        child_count = 1
        grandchild_count = 1

    critic_rating = ''
    if notify_params['rating_image'].startswith('rottentomatoes://') and notify_params['rating']:
        critic_rating = helpers.get_percent(notify_params['rating'], 10)

    audience_rating = ''
    if notify_params['audience_rating']:
        audience_rating = helpers.get_percent(notify_params['audience_rating'], 10)

    now = arrow.now()
    now_iso = now.isocalendar()

    available_params = {
        # Global paramaters
        'tautulli_version': common.RELEASE,
        'tautulli_remote': plexpy.CONFIG.GIT_REMOTE,
        'tautulli_branch': plexpy.CONFIG.GIT_BRANCH,
        'tautulli_commit': plexpy.CURRENT_VERSION,
        'server_name': plexpy.CONFIG.PMS_NAME,
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
        'datestamp': now.format(date_format),
        'timestamp': now.format(time_format),
        'unixtime': int(time.time()),
        'utctime': helpers.utc_now_iso(),
        # Stream parameters
        'streams': stream_count,
        'user_streams': user_stream_count,
        'user': notify_params['friendly_name'],
        'username': notify_params['user'],
        'device': notify_params['device'],
        'platform': notify_params['platform'],
        'product': notify_params['product'],
        'player': notify_params['player'],
        'ip_address': notify_params.get('ip_address', 'N/A'),
        'stream_duration': stream_duration,
        'stream_time': arrow.get(stream_duration * 60).format(duration_format),
        'remaining_duration': remaining_duration,
        'remaining_time': arrow.get(remaining_duration * 60).format(duration_format),
        'progress_duration': view_offset,
        'progress_time': arrow.get(view_offset * 60).format(duration_format),
        'progress_percent': helpers.get_percent(view_offset, duration),
        'transcode_decision': transcode_decision,
        'video_decision': notify_params['video_decision'],
        'audio_decision': notify_params['audio_decision'],
        'subtitle_decision': notify_params['subtitle_decision'],
        'quality_profile': notify_params['quality_profile'],
        'optimized_version': notify_params['optimized_version'],
        'optimized_version_profile': notify_params['optimized_version_profile'],
        'synced_version': notify_params['synced_version'],
        'live': notify_params['live'],
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
        'stream_video_framerate': notify_params['stream_video_framerate'],
        'stream_video_ref_frames': notify_params['stream_video_ref_frames'],
        'stream_video_resolution': notify_params['stream_video_resolution'],
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
        'title': notify_params['full_title'],
        'library_name': notify_params['library_name'],
        'show_name': show_name,
        'episode_name': episode_name,
        'artist_name': artist_name,
        'album_name': album_name,
        'track_name': track_name,
        'track_artist': notify_params['original_title'] or notify_params['grandparent_title'],
        'season_num': season_num,
        'season_num00': season_num00,
        'episode_num': episode_num,
        'episode_num00': episode_num00,
        'track_num': track_num,
        'track_num00': track_num00,
        'season_count': child_count,
        'episode_count': grandchild_count,
        'album_count': child_count,
        'track_count': grandchild_count,
        'year': notify_params['year'],
        'release_date': arrow.get(notify_params['originally_available_at']).format(date_format)
            if notify_params['originally_available_at'] else '',
        'air_date': arrow.get(notify_params['originally_available_at']).format(date_format)
            if notify_params['originally_available_at'] else '',
        'added_date': arrow.get(notify_params['added_at']).format(date_format)
            if notify_params['added_at'] else '',
        'updated_date': arrow.get(notify_params['updated_at']).format(date_format)
            if notify_params['updated_at'] else '',
        'last_viewed_date': arrow.get(notify_params['last_viewed_at']).format(date_format)
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
        'rating': notify_params['rating'],
        'critic_rating':  critic_rating,
        'audience_rating': audience_rating,
        'duration': duration,
        'poster_title': notify_params['poster_title'],
        'poster_url': notify_params['poster_url'],
        'plex_url': notify_params['plex_url'],
        'imdb_id': notify_params['imdb_id'],
        'imdb_url': notify_params['imdb_url'],
        'thetvdb_id': notify_params['thetvdb_id'],
        'thetvdb_url': notify_params['thetvdb_url'],
        'themoviedb_id': notify_params['themoviedb_id'],
        'themoviedb_url': notify_params['themoviedb_url'],
        'tvmaze_id': notify_params['tvmaze_id'],
        'tvmaze_url': notify_params['tvmaze_url'],
        'lastfm_url': notify_params['lastfm_url'],
        'trakt_url': notify_params['trakt_url'],
        'container': notify_params['container'],
        'bitrate': notify_params['bitrate'],
        'aspect_ratio': notify_params['aspect_ratio'],
        'video_codec': notify_params['video_codec'],
        'video_codec_level': notify_params['video_codec_level'],
        'video_bitrate': notify_params['video_bitrate'],
        'video_bit_depth': notify_params['video_bit_depth'],
        'video_framerate': notify_params['video_framerate'],
        'video_ref_frames': notify_params['video_ref_frames'],
        'video_resolution': notify_params['video_resolution'],
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
        'subtitle_codec': notify_params['subtitle_codec'],
        'subtitle_container': notify_params['subtitle_container'],
        'subtitle_format': notify_params['subtitle_format'],
        'subtitle_forced': notify_params['subtitle_forced'],
        'subtitle_location': notify_params['subtitle_location'],
        'subtitle_language': notify_params['subtitle_language'],
        'subtitle_language_code': notify_params['subtitle_language_code'],
        'file': notify_params['file'],
        'filename': os.path.basename(notify_params['file']),
        'file_size': helpers.humanFileSize(notify_params['file_size']),
        'indexes': notify_params['indexes'],
        'section_id': notify_params['section_id'],
        'rating_key': notify_params['rating_key'],
        'parent_rating_key': notify_params['parent_rating_key'],
        'grandparent_rating_key': notify_params['grandparent_rating_key'],
        'thumb': notify_params['thumb'],
        'parent_thumb': notify_params['parent_thumb'],
        'grandparent_thumb': notify_params['grandparent_thumb'],
        'poster_thumb': poster_thumb
        }

    return available_params


def build_server_notify_params(notify_action=None, **kwargs):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','')

    update_channel = pmsconnect.PmsConnect().get_server_update_channel()

    pms_download_info = defaultdict(str, kwargs.pop('pms_download_info', {}))
    plexpy_download_info = defaultdict(str, kwargs.pop('plexpy_download_info', {}))

    now = arrow.now()
    now_iso = now.isocalendar()

    available_params = {
        # Global paramaters
        'tautulli_version': common.RELEASE,
        'tautulli_remote': plexpy.CONFIG.GIT_REMOTE,
        'tautulli_branch': plexpy.CONFIG.GIT_BRANCH,
        'tautulli_commit': plexpy.CURRENT_VERSION,
        'server_name': plexpy.CONFIG.PMS_NAME,
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
        'datestamp': now.format(date_format),
        'timestamp': now.format(time_format),
        'unixtime': int(time.time()),
        'utctime': helpers.utc_now_iso(),
        # Plex Media Server update parameters
        'update_version': pms_download_info['version'],
        'update_url': pms_download_info['download_url'],
        'update_release_date': arrow.get(pms_download_info['release_date']).format(date_format)
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
        'tautulli_update_tar': plexpy_download_info['tarball_url'],
        'tautulli_update_zip': plexpy_download_info['zipball_url'],
        'tautulli_update_commit': kwargs.pop('plexpy_update_commit', ''),
        'tautulli_update_behind': kwargs.pop('plexpy_update_behind', ''),
        'tautulli_update_changelog': plexpy_download_info['body']
        }

    return available_params


def build_notify_text(subject='', body='', notify_action=None, parameters=None, agent_id=None, test=False):
    # Default subject and body text
    if agent_id == 15:
        default_subject = default_body = ''
    else:
        default_action = next((a for a in notifiers.available_notification_actions() if a['name'] == notify_action), {})
        default_subject = default_action.get('subject', '')
        default_body = default_action.get('body', '')

    # Make sure subject and body text are strings
    if not isinstance(subject, basestring):
        logger.error(u"Tautulli NotificationHandler :: Invalid subject text. Using fallback.")
        subject = default_subject
    if not isinstance(body, basestring):
        logger.error(u"Tautulli NotificationHandler :: Invalid body text. Using fallback.")
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

    custom_formatter = CustomFormatter()

    if agent_id == 15:
        try:
            script_args = [custom_formatter.format(arg, **parameters) for arg in helpers.split_args(subject)]
        except LookupError as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse parameter %s in script argument. Using fallback." % e)
            script_args = []
        except Exception as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse custom script arguments: %s. Using fallback." % e)
            script_args = []

    elif agent_id == 25:
        if body:
            try:
                body = json.loads(body)
            except ValueError as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to parse custom webhook json data: %s. Using fallback." % e)
                body = ''

        if body:
            def str_format(s):
                if isinstance(s, basestring):
                    return custom_formatter.format(unicode(s), **parameters)
                return s

            try:
                body = json.dumps(helpers.traverse_map(body, str_format))
            except LookupError as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to parse parameter %s in webhook data. Using fallback." % e)
                body = ''
            except Exception as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to parse custom webhook data: %s. Using fallback." % e)
                body = ''

    else:
        try:
            subject = custom_formatter.format(unicode(subject), **parameters)
        except LookupError as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse parameter %s in notification subject. Using fallback." % e)
            subject = unicode(default_subject).format(**parameters)
        except Exception as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse custom notification subject: %s. Using fallback." % e)
            subject = unicode(default_subject).format(**parameters)

        try:
            body = custom_formatter.format(unicode(body), **parameters)
        except LookupError as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse parameter %s in notification body. Using fallback." % e)
            body = unicode(default_body).format(**parameters)
        except Exception as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse custom notification body: %s. Using fallback." % e)
            body = unicode(default_body).format(**parameters)

    return subject, body, script_args


def strip_tag(data, agent_id=None):

    if agent_id == 7:
        # Allow tags b, i, u, a[href], font[color] for Pushover
        whitelist = {'b': [],
                     'i': [],
                     'u': [],
                     'a': ['href'],
                     'font': ['color']}
        return bleach.clean(data, tags=whitelist.keys(), attributes=whitelist, strip=True)

    elif agent_id in (10, 14, 20):
        # Don't remove tags for Email, Slack, and Discord
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


def format_group_index(group_keys):
    group_keys = sorted(group_keys)

    num = []
    num00 = []

    for k, g in groupby(enumerate(group_keys), lambda (i, x): i-x):
        group = map(itemgetter(1), g)
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
        if fallback == 'art':
            img = '/library/metadata/{}/art'.format(rating_key)
        else:
            img = '/library/metadata/{}/thumb'.format(rating_key)

    img_split = img.split('/')
    img = '/'.join(img_split[:5])
    rating_key = rating_key or img_split[3]

    service = helpers.get_img_service()

    if service is None:
        return img_info

    elif service == 'cloudinary':
        if fallback == 'cover':
            w, h = 1000, 1000
        elif fallback == 'art':
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
        if fallback == 'art':
            img = '/library/metadata/{}/art'.format(rating_key)
        else:
            img = '/library/metadata/{}/thumb'.format(rating_key)

    img_split = img.split('/')
    img = '/'.join(img_split[:5])
    rating_key = rating_key or img_split[3]

    img_string = '{}.{}.{}.{}.{}.{}.{}.{}'.format(
        plexpy.CONFIG.PMS_UUID, img, rating_key, width, height, opacity, background, blur, fallback)
    img_hash = hashlib.sha256(img_string).hexdigest()

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
    query = 'SELECT * FROM image_hash_lookup WHERE img_hash = ?'
    result = db.select_single(query, args=[img_hash])
    return result


def lookup_tvmaze_by_id(rating_key=None, thetvdb_id=None, imdb_id=None):
    db = database.MonitorDatabase()

    try:
        query = 'SELECT imdb_id, tvmaze_id, tvmaze_url FROM tvmaze_lookup ' \
                'WHERE rating_key = ?'
        tvmaze_info = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn(u"Tautulli NotificationHandler :: Unable to execute database query for lookup_tvmaze_by_tvdb_id: %s." % e)
        return {}

    if not tvmaze_info:
        tvmaze_info = {}

        if thetvdb_id:
            logger.debug(u"Tautulli NotificationHandler :: Looking up TVmaze info for thetvdb_id '{}'.".format(thetvdb_id))
        else:
            logger.debug(u"Tautulli NotificationHandler :: Looking up TVmaze info for imdb_id '{}'.".format(imdb_id))

        params = {'thetvdb': thetvdb_id} if thetvdb_id else {'imdb': imdb_id}
        response, err_msg, req_msg = request.request_response2('http://api.tvmaze.com/lookup/shows', params=params)

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

            tvmaze_info.pop('tvmaze_json')

        else:
            if err_msg:
                logger.error(u"Tautulli NotificationHandler :: {}".format(err_msg))

            if req_msg:
                logger.debug(u"Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return tvmaze_info


def lookup_themoviedb_by_id(rating_key=None, thetvdb_id=None, imdb_id=None):
    db = database.MonitorDatabase()

    try:
        query = 'SELECT thetvdb_id, imdb_id, themoviedb_id, themoviedb_url FROM themoviedb_lookup ' \
                'WHERE rating_key = ?'
        themoviedb_info = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn(u"Tautulli NotificationHandler :: Unable to execute database query for lookup_themoviedb_by_imdb_id: %s." % e)
        return {}

    if not themoviedb_info:
        themoviedb_info = {}

        if thetvdb_id:
            logger.debug(u"Tautulli NotificationHandler :: Looking up The Movie Database info for thetvdb_id '{}'.".format(thetvdb_id))
        else:
            logger.debug(u"Tautulli NotificationHandler :: Looking up The Movie Database info for imdb_id '{}'.".format(imdb_id))

        params = {'api_key': plexpy.CONFIG.THEMOVIEDB_APIKEY,
                  'external_source': 'tvdb_id' if thetvdb_id else 'imdb_id'
                  }
        response, err_msg, req_msg = request.request_response2('https://api.themoviedb.org/3/find/{}'.format(thetvdb_id or imdb_id), params=params)

        if response and not err_msg:
            themoviedb_find_json = response.json()
            if themoviedb_find_json.get('tv_results'):
                themoviedb_id = themoviedb_find_json['tv_results'][0]['id']
            elif themoviedb_find_json.get('movie_results'):
                themoviedb_id = themoviedb_find_json['movie_results'][0]['id']
            else:
                themoviedb_id = ''

            if themoviedb_id:
                media_type = 'tv' if thetvdb_id else 'movie'
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

                themoviedb_info.pop('themoviedb_json')

        else:
            if err_msg:
                logger.error(u"Tautulli NotificationHandler :: {}".format(err_msg))

            if req_msg:
                logger.debug(u"Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return themoviedb_info


def get_themoviedb_info(rating_key=None, media_type=None, themoviedb_id=None):
    if media_type in ('show', 'season', 'episode'):
        media_type = 'tv'

    db = database.MonitorDatabase()

    try:
        query = 'SELECT themoviedb_json FROM themoviedb_lookup ' \
                'WHERE rating_key = ?'
        result = db.select_single(query, args=[rating_key])
    except Exception as e:
        logger.warn(u"Tautulli NotificationHandler :: Unable to execute database query for get_themoviedb_info: %s." % e)
        return {}

    if result:
        try:
            return json.loads(result['themoviedb_json'])
        except:
            pass

    themoviedb_json = {}

    logger.debug(u"Tautulli NotificationHandler :: Looking up The Movie Database info for themoviedb_id '{}'.".format(themoviedb_id))

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

    else:
        if err_msg:
            logger.error(u"Tautulli NotificationHandler :: {}".format(err_msg))

        if req_msg:
            logger.debug(u"Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return themoviedb_json


class CustomFormatter(Formatter):
    def __init__(self, default='{{{0}}}', default_format_spec='{{{0}:{1}}}'):
        self.default = default
        self.default_format_spec = default_format_spec

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        elif conversion == 's':
            return str(value)
        elif conversion == 'r':
            return repr(value)
        elif conversion == 'u':  # uppercase
            return unicode(value).upper()
        elif conversion == 'l':  # lowercase
            return unicode(value).lower()
        elif conversion == 'c':  # capitalize
            return unicode(value).title()
        else:
            return value

    def format_field(self, value, format_spec):
        if format_spec.startswith('[') and format_spec.endswith(']'):
            pattern = re.compile(r'\[(-?\d*):?(-?\d*)\]')
            if re.match(pattern, format_spec):  # slice
                items = [x.strip() for x in unicode(value).split(',')]
                slice_start, slice_end = re.search(pattern, format_spec).groups()
                slice_start = helpers.cast_to_int(slice_start) or None
                slice_end = helpers.cast_to_int(slice_end) or None
                return ', '.join(items[slice(slice_start, slice_end)])
            else:
                return value
        else:
            try:
                return super(CustomFormatter, self).format_field(value, format_spec)
            except ValueError:
                return self.default_format_spec.format(value[1:-1], format_spec)

    def get_value(self, key, args, kwargs):
        if isinstance(key, basestring):
            return kwargs.get(key, self.default.format(key))
        else:
            return super(CustomFormatter, self).get_value(key, args, kwargs)
