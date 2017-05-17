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


import arrow
import bleach
from itertools import groupby
import json
from operator import itemgetter
import os
import re
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
import users


def process_queue():
    queue = plexpy.NOTIFY_QUEUE
    while True:
        params = queue.get()
        
        if params is None:
            break
        elif params:
            try:
                if 'notifier_id' in params:
                    notify(**params)
                else:
                    add_notifier_each(**params)
            except Exception as e:
                logger.exception(u"PlexPy NotificationHandler :: Notification thread exception: %s" % e)
                
        queue.task_done()

    logger.info(u"PlexPy NotificationHandler :: Notification thread exiting...")


def start_threads(num_threads=1):
    logger.info(u"PlexPy NotificationHandler :: Starting background notification handler ({} threads).".format(num_threads))
    for x in range(num_threads):
        thread = threading.Thread(target=process_queue)
        thread.daemon = True
        thread.start()


def add_notifier_each(notify_action=None, stream_data=None, timeline_data=None, **kwargs):
    if not notify_action:
        logger.debug(u"PlexPy NotificationHandler :: Notify called but no action received.")
        return

    # Check if any notification agents have notifications enabled for the action
    notifiers_enabled = notifiers.get_notifiers(notify_action=notify_action)

    # Check on_watched for each notifier
    if notifiers_enabled and notify_action == 'on_watched':
        for n, notifier in enumerate(notifiers_enabled):
            if any(d['agent_id'] == notifier['agent_id'] and d['notify_action'] == notify_action
                   for d in get_notify_state(session=stream_data)):
                # Already notified on_watched, remove from notifier
                notifiers_enabled.pop(n)

    if notifiers_enabled:
        # Check if notification conditions are satisfied
        conditions = notify_conditions(notify_action=notify_action,
                                       stream_data=stream_data,
                                       timeline_data=timeline_data)

    if notifiers_enabled and conditions:
        if stream_data or timeline_data:
            # Build the notification parameters
            parameters = build_media_notify_params(notify_action=notify_action,
                                                   session=stream_data,
                                                   timeline=timeline_data,
                                                   **kwargs)
        else:
            # Build the notification parameters
            parameters = build_server_notify_params(notify_action=notify_action,
                                                    **kwargs)

        if not parameters:
            logger.error(u"PlexPy NotificationHandler :: Failed to build notification parameters.")
            return

        # Add each notifier to the queue
        for notifier in notifiers_enabled:
            data = {'notifier_id': notifier['id'],
                    'notify_action': notify_action,
                    'stream_data': stream_data,
                    'timeline_data': timeline_data,
                    'parameters': parameters}
            data.update(kwargs)
            plexpy.NOTIFY_QUEUE.put(data)

    # Add on_concurrent and on_newdevice to queue if action is on_play
    if notify_action == 'on_play':
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data, 'notify_action': 'on_concurrent'})
        plexpy.NOTIFY_QUEUE.put({'stream_data': stream_data, 'notify_action': 'on_newdevice'})


def notify_conditions(notifier=None, notify_action=None, stream_data=None, timeline_data=None):
    # Activity notifications
    if stream_data:

        # Check if notifications enabled for user and library
        user_data = users.Users()
        user_details = user_data.get_details(user_id=stream_data['user_id'])

        library_data = libraries.Libraries()
        library_details = library_data.get_details(section_id=stream_data['section_id'])

        if not user_details['do_notify']:
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for user '%s' is disabled." % user_details['username'])
            return False

        elif not library_details['do_notify'] and notify_action not in ('on_concurrent', 'on_newdevice'):
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
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
                return plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < plexpy.CONFIG.NOTIFY_WATCHED_PERCENT
            
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
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
            return False

        return True

    # Server notifications
    else:
        return True


def notify(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, parameters=None, **kwargs):
    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    if not notifier_config:
        return

    if notify_action == 'test':
        subject = kwargs.pop('subject', 'PlexPy')
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
        logger.error(u"PlexPy NotificationHandler :: Unable to set notify state.")


def set_notify_success(notification_id):
    keys = {'id': notification_id}
    values = {'success': 1}

    monitor_db = database.MonitorDatabase()
    monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)


def build_media_notify_params(notify_action=None, session=None, timeline=None, **kwargs):
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

    # Get metadata for the item
    if session:
        rating_key = session['rating_key']
    elif timeline:
        rating_key = timeline['rating_key']

    pms_connect = pmsconnect.PmsConnect()
    metadata = pms_connect.get_metadata_details(rating_key=rating_key)

    if not metadata:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))
        return None

    ## TODO: Check list of media info items, currently only grabs first item
    media_info = media_part_info = {}
    if 'media_info' in metadata and len(metadata['media_info']) > 0:
        media_info = metadata['media_info'][0]
        if 'parts' in media_info and len(media_info['parts']) > 0:
            media_part_info = media_info['parts'][0]

    stream_video = stream_audio = stream_subtitle = False
    if 'streams' in media_part_info:
        for stream in media_part_info['streams']:
            if not stream_video and stream['type'] == '1':
                media_part_info.update(stream)
            if not stream_audio and stream['type'] == '2':
                media_part_info.update(stream)
            if not stream_subtitle and stream['type'] == '3':
                media_part_info.update(stream)

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
    metadata['plex_url'] = 'https://app.plex.tv/web/app#!/server/{0}/details?key=%2Flibrary%2Fmetadata%2F{1}'.format(
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

        elif metadata['media_type'] in ('show', 'season', 'episode'):
            metadata['themoviedb_id'] = metadata['guid'].split('themoviedb://')[1].split('/')[0]
            metadata['themoviedb_url'] = 'https://www.themoviedb.org/tv/' + metadata['themoviedb_id']
            metadata['trakt_url'] = 'https://trakt.tv/search/tmdb/' + metadata['themoviedb_id'] + '?id_type=show'

    if 'lastfm://' in metadata['guid']:
        metadata['lastfm_id'] = metadata['guid'].split('lastfm://')[1].rsplit('/', 1)[0]
        metadata['lastfm_url'] = 'https://www.last.fm/music/' + metadata['lastfm_id']

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

    if plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT and metadata['media_type'] in ('show', 'artist'):
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

    elif plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_PARENT and metadata['media_type'] in ('season', 'album'):
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
                        'transcode_hardware': session.get('transcode_hardware',''),
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
                        'lastfm_url': metadata.get('lastfm_url',''),
                        'trakt_url': metadata.get('trakt_url',''),
                        'container': session.get('container', media_info.get('container','')),
                        'bitrate': session.get('bitrate', media_info.get('bitrate','')),
                        'aspect_ratio': session.get('aspect_ratio', media_info.get('aspect_ratio','')),
                        'video_codec': session.get('video_codec', media_info.get('video_codec','')),
                        'video_codec_level': session.get('video_codec_level', media_info.get('video_codec_level','')),
                        'video_bitrate': session.get('video_bitrate', media_info.get('video_bitrate','')),
                        'video_bit_depth': session.get('video_bit_depth', media_info.get('video_bit_depth','')),
                        'video_framerate': session.get('video_framerate', media_info.get('video_framerate','')),
                        'video_ref_frames': session.get('video_ref_frames', media_info.get('video_ref_frames','')),
                        'video_resolution': session.get('video_resolution', media_info.get('video_resolution','')),
                        'video_height': session.get('height', media_info.get('height','')),
                        'video_width': session.get('width', media_info.get('width','')),
                        'video_language': session.get('video_language', media_info.get('video_language','')),
                        'video_language_code': session.get('video_language_code', media_info.get('video_language_code','')),
                        'audio_bitrate': session.get('audio_bitrate', media_info.get('audio_bitrate','')),
                        'audio_bitrate_mode': session.get('audio_bitrate_mode', media_info.get('audio_bitrate_mode','')),
                        'audio_codec': session.get('audio_codec', media_info.get('audio_codec','')),
                        'audio_channels': session.get('audio_channels', media_info.get('audio_channels','')),
                        'audio_channel_layout': session.get('audio_channel_layout', media_info.get('audio_channel_layout','')),
                        'audio_sample_rate': session.get('audio_sample_rate', media_info.get('audio_sample_rate','')),
                        'audio_language': session.get('audio_language', media_info.get('audio_language','')),
                        'audio_language_code': session.get('audio_language_code', media_info.get('audio_language_code','')),
                        'subtitle_codec': session.get('subtitle_codec', media_info.get('subtitle_codec','')),
                        'subtitle_container': session.get('subtitle_container', media_info.get('subtitle_container','')),
                        'subtitle_format': session.get('subtitle_format', media_info.get('subtitle_format','')),
                        'subtitle_forced': session.get('subtitle_forced', media_info.get('subtitle_forced','')),
                        'subtitle_location': session.get('subtitle_location', media_info.get('subtitle_location','')),
                        'subtitle_language': session.get('subtitle_language', media_info.get('subtitle_language','')),
                        'subtitle_language_code': session.get('subtitle_language_code', media_info.get('subtitle_language_code','')),
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
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve server uptime.")
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
                        # PlexPy update parameters
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
        logger.error(u"PlexPy NotificationHandler :: Invalid subject text. Using fallback.")
        subject = default_subject
    if not isinstance(body, basestring):
        logger.error(u"PlexPy NotificationHandler :: Invalid body text. Using fallback.")
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

    if agent_id == 15:
        try:
            script_args = [unicode(arg).format(**parameters) for arg in subject.split()]
        except LookupError as e:
            logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in script argument. Using fallback." % e)
            script_args = []
        except Exception as e:
            logger.error(u"PlexPy NotificationHandler :: Unable to parse custom script arguments: %s. Using fallback." % e)
            script_args = []
    else:
        script_args = []

    try:
        subject = unicode(subject).format(**parameters)
    except LookupError as e:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
        subject = unicode(default_subject).format(**parameters)
    except Exception as e:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject: %s. Using fallback." % e)
        subject = unicode(default_subject).format(**parameters)

    try:
        body = unicode(body).format(**parameters)
    except LookupError as e:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
        body = unicode(default_body).format(**parameters)
    except Exception as e:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body: %s. Using fallback." % e)
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

            # Create poster info
            poster_info = {'poster_title': poster_title, 'poster_url': poster_url}

            # Save the poster url in the database
            data_factory.set_poster_url(rating_key=poster_key, poster_title=poster_title, poster_url=poster_url)

            # Delete the cached poster
            os.remove(poster_file)
        except Exception as e:
            logger.error(u"PlexPy Notifier :: Unable to retrieve poster for rating_key %s: %s." % (str(metadata['rating_key']), e))

    return poster_info
