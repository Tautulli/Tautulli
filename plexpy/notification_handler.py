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


def process_queue():
    queue = plexpy.NOTIFY_QUEUE
    while True:
        params = queue.get()
        
        if params is None:
            break
        elif params:
            try:
                if 'notify' in params:
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
                data = {'notify': True,
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
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data, 'notify_action': 'on_concurrent'})
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data, 'notify_action': 'on_newdevice'})


def notify_conditions(notify_action=None, stream_data=None, timeline_data=None):
    # Activity notifications
    if stream_data:

        # Check if notifications enabled for user and library
        user_data = users.Users()
        user_details = user_data.get_details(user_id=stream_data['user_id'])

        library_data = libraries.Libraries()
        library_details = library_data.get_details(section_id=stream_data['section_id'])

        if not user_details['do_notify']:
            logger.debug(u"Tautulli NotificationHandler :: Notifications for user '%s' are disabled." % user_details['username'])
            return False

        elif not library_details['do_notify'] and notify_action not in ('on_concurrent', 'on_newdevice'):
            logger.debug(u"Tautulli NotificationHandler :: Notifications for library '%s' are disabled." % library_details['section_name'])
            return False

        if notify_action == 'on_concurrent':
            ap = activity_processor.ActivityProcessor()
            user_sessions = ap.get_sessions(user_id=stream_data['user_id'],
                                            ip_address=plexpy.CONFIG.NOTIFY_CONCURRENT_BY_IP)
            return len(user_sessions) >= plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD

        elif notify_action == 'on_newdevice':
            data_factory = datafactory.DataFactory()
            user_devices = data_factory.get_user_devices(user_id=stream_data['user_id'])
            return stream_data['machine_id'] not in user_devices

        elif stream_data['media_type'] == 'movie' or stream_data['media_type'] == 'episode':
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
        library_data = libraries.Libraries()
        library_details = library_data.get_details(section_id=timeline_data['section_id'])

        if not library_details['do_notify_created']:
            # logger.debug(u"Tautulli NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
            return False

        return True

    # Server notifications
    else:
        return True


def notify_custom_conditions(notifier_id=None, parameters=None):
    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    custom_conditions_logic = notifier_config['custom_conditions_logic']

    if custom_conditions_logic:
        logger.debug(u"Tautulli NotificationHandler :: Checking custom notification conditions for notifier_id %s." % notifier_id)

        custom_conditions = json.loads(notifier_config['custom_conditions'])
        
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

            # Set blank conditions to None
            if not parameter or not operator or not values:
                evaluated_conditions.append(None)
                continue

            # Make sure the condition values is in a list
            if isinstance(values, basestring):
                values = [values]

            # Cast the condition values to the correct type
            try:
                if parameter_type == 'str':
                    values = [unicode(v).lower() for v in values]

                elif parameter_type == 'int':
                    values = [int(v) for v in values]

                elif parameter_type == 'float':
                    values = [float(v) for v in values]
            
            except Exception as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to cast condition '%s' to type '%s'."
                             % (parameter, parameter_type))
                return False

            # Cast the parameter value to the correct type
            try:
                if parameter_type == 'str':
                    parameter_value = unicode(parameters[parameter]).lower()

                elif parameter_type == 'int':
                    parameter_value = int(parameters[parameter])

                elif parameter_type == 'float':
                    parameter_value = float(parameters[parameter])
            
            except Exception as e:
                logger.error(u"Tautulli NotificationHandler :: Unable to cast parameter '%s' to type '%s'."
                             % (parameter, parameter_type))
                return False

            # Check each condition
            if operator == 'contains':
                evaluated_conditions.append(any(c in parameter_value for c in values))

            elif operator == 'does not contain':
                evaluated_conditions.append(any(c not in parameter_value for c in values))

            elif operator == 'is':
                evaluated_conditions.append(any(parameter_value == c for c in values))

            elif operator == 'is not':
                evaluated_conditions.append(any(parameter_value != c for c in values))

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

        # Format and evaluate the logic string
        try:
            evaluated_logic = helpers.eval_logic_groups_to_bool(logic_groups, evaluated_conditions)
        except Exception as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to evaluate custom condition logic: %s." % e)
            return False

        logger.debug(u"Tautulli NotificationHandler :: Custom condition evaluated to '%s'." % str(evaluated_logic))
        return evaluated_logic

    return True


def notify(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, parameters=None, **kwargs):
    # Double check again if the notification has already been sent
    if stream_data and \
        any(d['notifier_id'] == notifier_id and d['notify_action'] == notify_action
            for d in get_notify_state(session=stream_data)):
        # Return if the notification has already been sent
        return

    logger.info(u"Tautulli NotificationHandler :: Preparing notifications for notifier_id %s." % notifier_id)

    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    if not notifier_config:
        return

    if notify_action == 'test':
        subject = kwargs.pop('subject', 'Tautulli')
        body = kwargs.pop('body', 'Test Notification')
        script_args = kwargs.pop('script_args', [])
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
                                       notify_action=notify_action,
                                       notifier=notifier_config,
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


def set_notify_state(notify_action, notifier, subject, body, script_args, session=None):

    if notify_action and notifier:
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
        logger.error(u"Tautulli NotificationHandler :: Unable to retrieve server uptime.")
        server_uptime = 'N/A'

    # Get metadata for the item
    if session:
        rating_key = session['rating_key']
    elif timeline:
        rating_key = timeline['rating_key']

    pms_connect = pmsconnect.PmsConnect()
    metadata = pms_connect.get_metadata_details(rating_key=rating_key)

    if not metadata:
        logger.error(u"Tautulli NotificationHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))
        return None

    ## TODO: Check list of media info items, currently only grabs first item
    media_info = media_part_info = {}
    if 'media_info' in metadata and len(metadata['media_info']) > 0:
        media_info = metadata['media_info'][0]
        if 'parts' in media_info and len(media_info['parts']) > 0:
            media_part_info = media_info.pop('parts')[0]

    stream_video = stream_audio = stream_subtitle = False
    if 'streams' in media_part_info:
        for stream in media_part_info.pop('streams'):
            if not stream_video and stream['type'] == '1':
                media_part_info.update(stream)
                stream_video = True
            if not stream_audio and stream['type'] == '2':
                media_part_info.update(stream)
                stream_audio = True
            if not stream_subtitle and stream['type'] == '3':
                media_part_info.update(stream)
                stream_subtitle = True

    child_metadata = grandchild_metadata = []
    for key in kwargs.pop('child_keys', []):
        child_metadata.append(pms_connect.get_metadata_details(rating_key=key))
    for key in kwargs.pop('grandchild_keys', []):
        grandchild_metadata.append(pms_connect.get_metadata_details(rating_key=key))

    # Session values
    session = session or {}

    ap = activity_processor.ActivityProcessor()
    sessions = ap.get_sessions()
    stream_count = len(sessions)
    user_sessions = ap.get_sessions(user_id=session.get('user_id'))
    user_stream_count = len(user_sessions)

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
    remaining_duration = duration - view_offset

    # Build Plex URL
    metadata['plex_url'] = '{web_url}#!/server/{pms_identifier}/details?key=%2Flibrary%2Fmetadata%2F{rating_key}'.format(
        web_url=plexpy.CONFIG.PMS_WEB_URL or 'https://app.plex.tv/desktop',
        pms_identifier=plexpy.CONFIG.PMS_IDENTIFIER,
        rating_key=rating_key)

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

        elif metadata['media_type'] in ('show', 'season', 'episode'):
            metadata['themoviedb_id'] = metadata['guid'].split('themoviedb://')[1].split('/')[0]
            metadata['themoviedb_url'] = 'https://www.themoviedb.org/tv/' + metadata['themoviedb_id']
            metadata['trakt_url'] = 'https://trakt.tv/search/tmdb/' + metadata['themoviedb_id'] + '?id_type=show'

    if 'lastfm://' in metadata['guid']:
        metadata['lastfm_id'] = metadata['guid'].split('lastfm://')[1].rsplit('/', 1)[0]
        metadata['lastfm_url'] = 'https://www.last.fm/music/' + metadata['lastfm_id']

    # Get TheMovieDB info
    if plexpy.CONFIG.THEMOVIEDB_LOOKUP:
        if metadata.get('themoviedb_id'):
            themoveidb_json = get_themoviedb_info(rating_key=rating_key,
                                                  media_type=metadata['media_type'],
                                                  themoviedb_id=metadata['themoviedb_id'])

            if themoveidb_json.get('imdb_id'):
                metadata['imdb_id'] = themoveidb_json['imdb_id']
                metadata['imdb_url'] = 'https://www.imdb.com/title/' + themoveidb_json['imdb_id']

        elif metadata.get('thetvdb_id') or metadata.get('imdb_id'):
            themoviedb_info = lookup_themoviedb_by_id(rating_key=rating_key,
                                                      thetvdb_id=metadata.get('thetvdb_id'),
                                                      imdb_id=metadata.get('imdb_id'))
            metadata.update(themoviedb_info)

    # Get TVmaze info (for tv shows only)
    if plexpy.CONFIG.TVMAZE_LOOKUP:
        if metadata['media_type'] in ('show', 'season', 'episode') and (metadata.get('thetvdb_id') or metadata.get('imdb_id')):
            tvmaze_info = lookup_tvmaze_by_id(rating_key=rating_key,
                                              thetvdb_id=metadata.get('thetvdb_id'),
                                              imdb_id=metadata.get('imdb_id'))
            metadata.update(tvmaze_info)

            if tvmaze_info.get('thetvdb_id'):
                metadata['thetvdb_url'] = 'https://thetvdb.com/?tab=series&id=' + str(tvmaze_info['thetvdb_id'])
            if tvmaze_info.get('imdb_id'):
                metadata['imdb_url'] = 'https://www.imdb.com/title/' + tvmaze_info['imdb_id']

    if metadata['media_type'] in ('movie', 'show', 'artist'):
        poster_thumb = metadata['thumb']
        poster_key = metadata['rating_key']
        poster_title = metadata['title']
    elif metadata['media_type'] in ('season', 'album'):
        poster_thumb = metadata['thumb'] or metadata['parent_thumb']
        poster_key = metadata['rating_key']
        poster_title = '%s - %s' % (metadata['parent_title'],
                                    metadata['title'])
    elif metadata['media_type'] in ('episode', 'track'):
        poster_thumb = metadata['parent_thumb'] or metadata['grandparent_thumb']
        poster_key = metadata['parent_rating_key']
        poster_title = '%s - %s' % (metadata['grandparent_title'],
                                    metadata['parent_title'])
    else:
        poster_thumb = ''

    if plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS:
        poster_info = get_poster_info(poster_thumb=poster_thumb, poster_key=poster_key, poster_title=poster_title)
        metadata.update(poster_info)

    if ((manual_trigger or plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT)
        and metadata['media_type'] in ('show', 'artist')):
        show_name = metadata['title']
        episode_name = ''
        artist_name = metadata['title']
        album_name = ''
        track_name = ''

        num, num00 = format_group_index([helpers.cast_to_int(d['media_index'])
                                        for d in child_metadata if d['parent_rating_key'] == rating_key])
        season_num, season_num00 = num, num00

        episode_num, episode_num00 = '', ''
        track_num, track_num00 = '', ''

    elif ((manual_trigger or plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_PARENT)
          and metadata['media_type'] in ('season', 'album')):
        show_name = metadata['parent_title']
        episode_name = ''
        artist_name = metadata['parent_title']
        album_name = metadata['title']
        track_name = ''
        season_num = metadata['media_index'].zfill(1)
        season_num00 = metadata['media_index'].zfill(2)

        num, num00 = format_group_index([helpers.cast_to_int(d['media_index'])
                                        for d in child_metadata if d['parent_rating_key'] == rating_key])
        episode_num, episode_num00 = num, num00
        track_num, track_num00 = num, num00

    else:
        show_name = metadata['grandparent_title']
        episode_name = metadata['title']
        artist_name = metadata['grandparent_title']
        album_name = metadata['parent_title']
        track_name = metadata['title']
        season_num = metadata['parent_media_index'].zfill(1)
        season_num00 = metadata['parent_media_index'].zfill(2)
        episode_num = metadata['media_index'].zfill(1)
        episode_num00 = metadata['media_index'].zfill(2)
        track_num = metadata['media_index'].zfill(1)
        track_num00 = metadata['media_index'].zfill(2)

    available_params = {# Global paramaters
                        'plexpy_version': common.VERSION_NUMBER,
                        'plexpy_branch': plexpy.CONFIG.GIT_BRANCH,
                        'plexpy_commit': plexpy.CURRENT_VERSION,
                        'server_name': server_name,
                        'server_uptime': server_uptime,
                        'server_version': server_times.get('version',''),
                        'action': notify_action.split('on_')[-1],
                        'datestamp': arrow.now().format(date_format),
                        'timestamp': arrow.now().format(time_format),
                        # Stream parameters
                        'streams': stream_count,
                        'user_streams': user_stream_count,
                        'user': session.get('friendly_name',''),
                        'username': session.get('user',''),
                        'device': session.get('device',''),
                        'platform': session.get('platform',''),
                        'product': session.get('product',''),
                        'player': session.get('player',''),
                        'ip_address': session.get('ip_address','N/A'),
                        'stream_duration': stream_duration,
                        'stream_time': arrow.get(stream_duration * 60).format(duration_format),
                        'remaining_duration': remaining_duration,
                        'remaining_time': arrow.get(remaining_duration * 60).format(duration_format),
                        'progress_duration': view_offset,
                        'progress_time': arrow.get(view_offset * 60).format(duration_format),
                        'progress_percent': helpers.get_percent(view_offset, duration),
                        'transcode_decision': transcode_decision,
                        'video_decision': session.get('video_decision',''),
                        'audio_decision': session.get('audio_decision',''),
                        'subtitle_decision': session.get('subtitle_decision',''),
                        'quality_profile': session.get('quality_profile',''),
                        'optimized_version': session.get('optimized_version',''),
                        'optimized_version_profile': session.get('optimized_version_profile',''),
                        'stream_local': session.get('local', ''),
                        'stream_location': session.get('location', ''),
                        'stream_bandwidth': session.get('bandwidth', ''),
                        'stream_container': session.get('stream_container', ''),
                        'stream_bitrate': session.get('stream_bitrate', ''),
                        'stream_aspect_ratio': session.get('stream_aspect_ratio', ''),
                        'stream_video_codec': session.get('stream_video_codec', ''),
                        'stream_video_codec_level': session.get('stream_video_codec_level', ''),
                        'stream_video_bitrate': session.get('stream_video_bitrate', ''),
                        'stream_video_bit_depth': session.get('stream_video_bit_depth', ''),
                        'stream_video_framerate': session.get('stream_video_framerate', ''),
                        'stream_video_ref_frames': session.get('stream_video_ref_frames', ''),
                        'stream_video_resolution': session.get('stream_video_resolution', ''),
                        'stream_video_height': session.get('stream_video_height', ''),
                        'stream_video_width': session.get('stream_video_width', ''),
                        'stream_video_language': session.get('stream_video_language', ''),
                        'stream_video_language_code': session.get('stream_video_language_code', ''),
                        'stream_audio_bitrate': session.get('stream_audio_bitrate', ''),
                        'stream_audio_bitrate_mode': session.get('stream_audio_bitrate_mode', ''),
                        'stream_audio_codec': session.get('stream_audio_codec', ''),
                        'stream_audio_channels': session.get('stream_audio_channels', ''),
                        'stream_audio_channel_layout': session.get('stream_audio_channel_layout', ''),
                        'stream_audio_sample_rate': session.get('stream_audio_sample_rate', ''),
                        'stream_audio_language': session.get('stream_audio_language', ''),
                        'stream_audio_language_code': session.get('stream_audio_language_code', ''),
                        'stream_subtitle_codec': session.get('stream_subtitle_codec', ''),
                        'stream_subtitle_container': session.get('stream_subtitle_container', ''),
                        'stream_subtitle_format': session.get('stream_subtitle_format', ''),
                        'stream_subtitle_forced': session.get('stream_subtitle_forced', ''),
                        'stream_subtitle_language': session.get('stream_subtitle_language', ''),
                        'stream_subtitle_language_code': session.get('stream_subtitle_language_code', ''),
                        'stream_subtitle_location': session.get('stream_subtitle_location', ''),
                        'transcode_container': session.get('transcode_container',''),
                        'transcode_video_codec': session.get('transcode_video_codec',''),
                        'transcode_video_width': session.get('transcode_width',''),
                        'transcode_video_height': session.get('transcode_height',''),
                        'transcode_audio_codec': session.get('transcode_audio_codec',''),
                        'transcode_audio_channels': session.get('transcode_audio_channels',''),
                        'transcode_hw_requested': session.get('transcode_hw_requested',''),
                        'transcode_hw_decode': session.get('transcode_hw_decode',''),
                        'transcode_hw_decode_title': session.get('transcode_hw_decode_title',''),
                        'transcode_hw_encode': session.get('transcode_hw_encode',''),
                        'transcode_hw_encode_title': session.get('transcode_hw_encode_title',''),
                        'transcode_hw_full_pipeline': session.get('transcode_hw_full_pipeline',''),
                        'session_key': session.get('session_key',''),
                        'transcode_key': session.get('transcode_key',''),
                        'session_id': session.get('session_id',''),
                        'user_id': session.get('user_id',''),
                        'machine_id': session.get('machine_id',''),
                        # Source metadata parameters
                        'media_type': metadata['media_type'],
                        'title': metadata['full_title'],
                        'library_name': metadata['library_name'],
                        'show_name': show_name,
                        'episode_name': episode_name,
                        'artist_name': artist_name,
                        'album_name': album_name,
                        'track_name': track_name,
                        'season_num': season_num,
                        'season_num00': season_num00,
                        'episode_num': episode_num,
                        'episode_num00': episode_num00,
                        'track_num': track_num,
                        'track_num00': track_num00,
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
                        'audience_rating': helpers.get_percent(metadata['audience_rating'], 10) or '',
                        'duration': duration,
                        'poster_title': metadata.get('poster_title',''),
                        'poster_url': metadata.get('poster_url',''),
                        'plex_url': metadata.get('plex_url',''),
                        'imdb_id': metadata.get('imdb_id',''),
                        'imdb_url': metadata.get('imdb_url',''),
                        'thetvdb_id': metadata.get('thetvdb_id',''),
                        'thetvdb_url': metadata.get('thetvdb_url',''),
                        'themoviedb_id': metadata.get('themoviedb_id',''),
                        'themoviedb_url': metadata.get('themoviedb_url',''),
                        'tvmaze_id': metadata.get('tvmaze_id',''),
                        'tvmaze_url': metadata.get('tvmaze_url',''),
                        'lastfm_url': metadata.get('lastfm_url',''),
                        'trakt_url': metadata.get('trakt_url',''),
                        'container': session.get('container', media_info.get('container','')),
                        'bitrate': session.get('bitrate', media_info.get('bitrate','')),
                        'aspect_ratio': session.get('aspect_ratio', media_info.get('aspect_ratio','')),
                        'video_codec': session.get('video_codec', media_part_info.get('video_codec','')),
                        'video_codec_level': session.get('video_codec_level', media_part_info.get('video_codec_level','')),
                        'video_bitrate': session.get('video_bitrate', media_part_info.get('video_bitrate','')),
                        'video_bit_depth': session.get('video_bit_depth', media_part_info.get('video_bit_depth','')),
                        'video_framerate': session.get('video_framerate', media_info.get('video_framerate','')),
                        'video_ref_frames': session.get('video_ref_frames', media_part_info.get('video_ref_frames','')),
                        'video_resolution': session.get('video_resolution', media_info.get('video_resolution','')),
                        'video_height': session.get('height', media_info.get('height','')),
                        'video_width': session.get('width', media_info.get('width','')),
                        'video_language': session.get('video_language', media_part_info.get('video_language','')),
                        'video_language_code': session.get('video_language_code', media_part_info.get('video_language_code','')),
                        'audio_bitrate': session.get('audio_bitrate', media_part_info.get('audio_bitrate','')),
                        'audio_bitrate_mode': session.get('audio_bitrate_mode', media_part_info.get('audio_bitrate_mode','')),
                        'audio_codec': session.get('audio_codec', media_part_info.get('audio_codec','')),
                        'audio_channels': session.get('audio_channels', media_part_info.get('audio_channels','')),
                        'audio_channel_layout': session.get('audio_channel_layout', media_part_info.get('audio_channel_layout','')),
                        'audio_sample_rate': session.get('audio_sample_rate', media_part_info.get('audio_sample_rate','')),
                        'audio_language': session.get('audio_language', media_part_info.get('audio_language','')),
                        'audio_language_code': session.get('audio_language_code', media_part_info.get('audio_language_code','')),
                        'subtitle_codec': session.get('subtitle_codec', media_part_info.get('subtitle_codec','')),
                        'subtitle_container': session.get('subtitle_container', media_part_info.get('subtitle_container','')),
                        'subtitle_format': session.get('subtitle_format', media_part_info.get('subtitle_format','')),
                        'subtitle_forced': session.get('subtitle_forced', media_part_info.get('subtitle_forced','')),
                        'subtitle_location': session.get('subtitle_location', media_part_info.get('subtitle_location','')),
                        'subtitle_language': session.get('subtitle_language', media_part_info.get('subtitle_language','')),
                        'subtitle_language_code': session.get('subtitle_language_code', media_part_info.get('subtitle_language_code','')),
                        'file': media_part_info.get('file',''),
                        'file_size': helpers.humanFileSize(media_part_info.get('file_size','')),
                        'indexes': media_part_info.get('indexes',''),
                        'section_id': metadata['section_id'],
                        'rating_key': metadata['rating_key'],
                        'parent_rating_key': metadata['parent_rating_key'],
                        'grandparent_rating_key': metadata['grandparent_rating_key'],
                        'thumb': metadata['thumb'],
                        'parent_thumb': metadata['parent_thumb'],
                        'grandparent_thumb': metadata['grandparent_thumb'],
                        'poster_thumb': poster_thumb
                        }

    return available_params


def build_server_notify_params(notify_action=None, **kwargs):
    # Get time formats
    date_format = plexpy.CONFIG.DATE_FORMAT.replace('Do','')
    time_format = plexpy.CONFIG.TIME_FORMAT.replace('Do','')

    # Get the server name
    server_name = plexpy.CONFIG.PMS_NAME

    # Get the server uptime
    plex_tv = plextv.PlexTV()
    server_times = plex_tv.get_server_times()

    pms_download_info = kwargs.pop('pms_download_info', {})
    plexpy_download_info = kwargs.pop('plexpy_download_info', {})

    if server_times:
        updated_at = server_times['updated_at']
        server_uptime = helpers.human_duration(int(time.time() - helpers.cast_to_int(updated_at)))
    else:
        logger.error(u"Tautulli NotificationHandler :: Unable to retrieve server uptime.")
        server_uptime = 'N/A'

    available_params = {# Global paramaters
                        'plexpy_version': common.VERSION_NUMBER,
                        'plexpy_branch': plexpy.CONFIG.GIT_BRANCH,
                        'plexpy_commit': plexpy.CURRENT_VERSION,
                        'server_name': server_name,
                        'server_uptime': server_uptime,
                        'server_version': server_times.get('version',''),
                        'action': notify_action.split('on_')[-1],
                        'datestamp': arrow.now().format(date_format),
                        'timestamp': arrow.now().format(time_format),
                        # Plex Media Server update parameters
                        'update_version': pms_download_info.get('version',''),
                        'update_url': pms_download_info.get('download_url',''),
                        'update_release_date': arrow.get(pms_download_info.get('release_date','')).format(date_format)
                            if pms_download_info.get('release_date','') else '',
                        'update_channel': 'Plex Pass' if plexpy.CONFIG.PMS_UPDATE_CHANNEL == 'plexpass' else 'Public',
                        'update_platform': pms_download_info.get('platform',''),
                        'update_distro': pms_download_info.get('distro',''),
                        'update_distro_build': pms_download_info.get('build',''),
                        'update_requirements': pms_download_info.get('requirements',''),
                        'update_extra_info': pms_download_info.get('extra_info',''),
                        'update_changelog_added': pms_download_info.get('changelog_added',''),
                        'update_changelog_fixed': pms_download_info.get('changelog_fixed',''),
                        # Tautulli update parameters
                        'plexpy_update_version': plexpy_download_info.get('tag_name', ''),
                        'plexpy_update_tar': plexpy_download_info.get('tarball_url', ''),
                        'plexpy_update_zip': plexpy_download_info.get('zipball_url', ''),
                        'plexpy_update_commit': kwargs.pop('plexpy_update_commit', ''),
                        'plexpy_update_behind': kwargs.pop('plexpy_update_behind', ''),
                        'plexpy_update_changelog': plexpy_download_info.get('body', '')
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

    if test:
        return subject, body

    custom_formatter = CustomFormatter()

    if agent_id == 15:
        try:
            script_args = [custom_formatter.format(unicode(arg), **parameters) for arg in subject.split()]
        except LookupError as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse field %s in script argument. Using fallback." % e)
            script_args = []
        except Exception as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to parse custom script arguments: %s. Using fallback." % e)
            script_args = []
    else:
        script_args = []

    try:
        subject = custom_formatter.format(unicode(subject), **parameters)
    except LookupError as e:
        logger.error(u"Tautulli NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
        subject = unicode(default_subject).format(**parameters)
    except Exception as e:
        logger.error(u"Tautulli NotificationHandler :: Unable to parse custom notification subject: %s. Using fallback." % e)
        subject = unicode(default_subject).format(**parameters)

    try:
        body = custom_formatter.format(unicode(body), **parameters)
    except LookupError as e:
        logger.error(u"Tautulli NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
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


def get_poster_info(poster_thumb, poster_key, poster_title):
    # Try to retrieve poster info from the database
    data_factory = datafactory.DataFactory()
    poster_info = data_factory.get_poster_info(rating_key=poster_key)

    # If no previous poster info
    if not poster_info and poster_thumb:
        try:
            thread_name = str(threading.current_thread().ident)
            poster_file = os.path.join(plexpy.CONFIG.CACHE_DIR, 'cache-poster-%s' % thread_name)

            # Retrieve the poster from Plex and cache to file
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_image(img=poster_thumb)
            if result and result[0]:
                with open(poster_file, 'wb') as f:
                    f.write(result[0])
            else:
                raise Exception(u'PMS image request failed')

            # Upload poster_thumb to Imgur and get link
            poster_url = helpers.uploadToImgur(poster_file, poster_title)

            if poster_url:
                # Create poster info
                poster_info = {'poster_title': poster_title, 'poster_url': poster_url}

                # Save the poster url in the database
                data_factory.set_poster_url(rating_key=poster_key, poster_title=poster_title, poster_url=poster_url)

            # Delete the cached poster
            os.remove(poster_file)
        except Exception as e:
            logger.error(u"Tautulli NotificationHandler :: Unable to retrieve poster for rating_key %s: %s." % (str(metadata['rating_key']), e))

    return poster_info


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

    else:
        if err_msg:
            logger.error(u"Tautulli NotificationHandler :: {}".format(err_msg))

        if req_msg:
            logger.debug(u"Tautulli NotificationHandler :: Request response: {}".format(req_msg))

    return themoviedb_json


class CustomFormatter(Formatter):
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
            pattern = re.compile(r'\[(\d*):?(\d*)\]')
            if re.match(pattern, format_spec):  # slice
                items = [x.strip() for x in unicode(value).split(',')]
                slice_start, slice_end = re.search(pattern, format_spec).groups()
                slice_start = max(int(slice_start), 0) if slice_start else None
                slice_end = min(int(slice_end), len(items)) if slice_end else None
                return ', '.join(items[slice_start:slice_end])
            else:
                return value
        else:
            return super(CustomFormatter, self).format_field(value, format_spec)
