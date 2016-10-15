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
        if params:
            if 'notifier_id' in params:
                notify(**params)
            else:
                add_notifier_each(**params)
        queue.task_done()


def start_threads(num_threads=1):
    logger.info(u"PlexPy NotificationHandler :: Starting background notification handler.")
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
    if stream_data:
        # Check if notifications enabled for user and library
        user_data = users.Users()
        user_details = user_data.get_details(user_id=stream_data['user_id'])

        library_data = libraries.Libraries()
        library_details = library_data.get_details(section_id=stream_data['section_id'])

        if not user_details['do_notify']:
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for user '%s' is disabled." % user_details['username'])
            return False
        elif not library_details['do_notify']:
            # logger.debug(u"PlexPy NotificationHandler :: Notifications for library '%s' is disabled." % library_details['section_name'])
            return False

        if (stream_data['media_type'] == 'movie' and plexpy.CONFIG.MOVIE_NOTIFY_ENABLE) \
            or (stream_data['media_type'] == 'episode' and plexpy.CONFIG.TV_NOTIFY_ENABLE):

            progress_percent = helpers.get_percent(stream_data['view_offset'], stream_data['duration'])

            ap = activity_processor.ActivityProcessor()
            user_sessions = ap.get_sessions(user_id=stream_data['user_id'],
                                            ip_address=plexpy.CONFIG.NOTIFY_CONCURRENT_BY_IP)

            data_factory = datafactory.DataFactory()
            user_devices = data_factory.get_user_devices(user_id=stream_data['user_id'])

            conditions = \
                {'on_stop': plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < plexpy.CONFIG.NOTIFY_WATCHED_PERCENT,
                 'on_resume': plexpy.CONFIG.NOTIFY_CONSECUTIVE or progress_percent < 99,
                 'on_concurrent': len(user_sessions) >= plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD,
                 'on_newdevice': stream_data['machine_id'] not in user_devices
                 }

            return conditions.get(notify_action, True)

        elif (stream_data['media_type'] == 'track' and plexpy.CONFIG.MUSIC_NOTIFY_ENABLE):
            return True
        else:
            return False
    elif timeline_data:
        return True
    else:
        return True


def notify(notifier_id=None, notify_action=None, stream_data=None, timeline_data=None, parameters=None, **kwargs):
    notifier_config = notifiers.get_notifier_config(notifier_id=notifier_id)

    if not notifier_config:
        return

    # Get the subject and body strings
    subject_string = notifier_config['notify_text'][notify_action]['subject']
    body_string = notifier_config['notify_text'][notify_action]['body']

    # Format the subject and body strings
    subject, body = build_notify_text(subject=subject_string,
                                      body=body_string,
                                      notify_action=notify_action,
                                      parameters=parameters,
                                      agent_id=notifier_config['agent_id'])

    # Send the notification
    notifiers.send_notification(notifier_id=notifier_config['id'],
                                subject=subject,
                                body=body,
                                notify_action=notify_action,
                                parameters=parameters)

    # Set the notification state in the db
    set_notify_state(session=stream_data or timeline_data,
                     notify_action=notify_action,
                     notifier=notifier_config,
                     subject=subject,
                     body=body,
                     parameters=parameters)


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


def set_notify_state(notify_action, notifier, subject, body, session=None, parameters=None):

    if notify_action and notifier:
        monitor_db = database.MonitorDatabase()

        session = session or {}
        parameters = parameters or {}

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
                  'poster_url': parameters.get('poster_url', None)}

        monitor_db.upsert(table_name='notify_log', key_dict=keys, value_dict=values)
    else:
        logger.error(u"PlexPy NotificationHandler :: Unable to set notify state.")


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
    metadata = pms_connect.get_metadata_details(rating_key=rating_key, get_media_info=True)

    if not metadata:
        logger.error(u"PlexPy NotificationHandler :: Unable to retrieve metadata for rating_key %s" % str(rating_key))
        return None

    child_metadata = grandchild_metadata = []
    for key in kwargs.pop('child_keys', []):
        child_metadata.append(pms_connect.get_metadata_details(rating_key=key))
    for key in kwargs.pop('grandchild_keys', []):
        grandchild_metadata.append(pms_connect.get_metadata_details(rating_key=key))

    ap = activity_processor.ActivityProcessor()
    sessions = ap.get_sessions()
    stream_count = len(sessions)
    user_sessions = ap.get_sessions(user_id=session['user_id'])
    user_stream_count = len(user_sessions)

    # Session values
    session = session or {}

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
    metadata['plex_url'] = 'https://app.plex.tv/web/app#!/server/{0}/details/%2Flibrary%2Fmetadata%2F{1}'.format(
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

    if plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS:
        metadata['poster_url'] = upload_poster(metadata=metadata)

    # Create a title
    if metadata['media_type'] == 'episode' or metadata['media_type'] == 'track':
        full_title = '%s - %s' % (metadata['grandparent_title'],
                                  metadata['title'])
    elif metadata['media_type'] == 'season' or metadata['media_type'] == 'album':
        full_title = '%s - %s' % (metadata['parent_title'],
                                  metadata['title'])
    else:
        full_title = metadata['title']

    # Fix metadata params for grouped recently added
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

    if notify_action == 'on_created' and plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED and metadata['media_type'] != 'movie':
        if metadata['media_type'] == 'episode' or metadata['media_type'] == 'track':
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

        elif metadata['media_type'] == 'season' or metadata['media_type'] == 'album':
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

        elif metadata['media_type'] == 'show' or metadata['media_type'] == 'artist':
            show_name = metadata['title']
            episode_name = ''
            artist_name = metadata['title']
            album_name = ''
            track_name = ''

            num, num00 = format_group_index([helpers.cast_to_int(d['media_index'])
                                            for d in child_metadata if d['parent_rating_key'] == rating_key])
            season_num, season_num00 = num, num00

            num, num00 = format_group_index([helpers.cast_to_int(d['media_index'])
                                            for d in grandchild_metadata if d['grandparent_rating_key'] == rating_key])
            episode_num, episode_num00 = num, num00
            track_num, track_num00 = num, num00

        else:
            pass

    available_params = {# Global paramaters
                        'plexpy_version': common.VERSION_NUMBER,
                        'plexpy_branch': plexpy.CONFIG.GIT_BRANCH,
                        'plexpy_commit': plexpy.CURRENT_VERSION,
                        'server_name': server_name,
                        'server_uptime': server_uptime,
                        'server_version': server_times.get('version',''),
                        'action': notify_action.split('on_')[-1].title(),
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
                        'container': session.get('container', metadata.get('container','')),
                        'video_codec': session.get('video_codec', metadata.get('video_codec','')),
                        'video_bitrate': session.get('bitrate', metadata.get('bitrate','')),
                        'video_width': session.get('width', metadata.get('width','')),
                        'video_height': session.get('height', metadata.get('height','')),
                        'video_resolution': session.get('video_resolution', metadata.get('video_resolution','')),
                        'video_framerate': session.get('video_framerate', metadata.get('video_framerate','')),
                        'aspect_ratio': session.get('aspect_ratio', metadata.get('aspect_ratio','')),
                        'audio_codec': session.get('audio_codec', metadata.get('audio_codec','')),
                        'audio_channels': session.get('audio_channels', metadata.get('audio_channels','')),
                        'title': full_title,
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
                        'file': metadata.get('file',''),
                        'file_size': helpers.humanFileSize(metadata.get('file_size','')),
                        'section_id': metadata['section_id'],
                        'rating_key': metadata['rating_key'],
                        'parent_rating_key': metadata['parent_rating_key'],
                        'grandparent_rating_key': metadata['grandparent_rating_key']
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
                        'action': notify_action.split('on_')[-1].title(),
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


def build_notify_text(subject='', body='', notify_action=None, parameters=None, agent_id=None):
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
        pattern = None

    if pattern:
        # Remove the unwanted tags and strip any unmatch tags too.
        subject = strip_tag(re.sub(pattern, '', subject), agent_id)
        body = strip_tag(re.sub(pattern, '', body), agent_id)
    else:
        subject = strip_tag(subject, agent_id)
        body = strip_tag(body, agent_id)

    # Default subject and body text
    default_action = next((a for a in notifiers.available_notification_actions() if a['name'] == notify_action), {})
    default_subject = default_action.get('subject', '')
    default_body = default_action.get('body', '')

    try:
        subject = unicode(subject).format(**parameters)
    except LookupError as e:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification subject. Using fallback." % e)
        subject = unicode(default_subject).format(**parameters)
    except:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification subject. Using fallback.")
        subject = unicode(default_subject).format(**parameters)

    try:
        body = unicode(body).format(**parameters)
    except LookupError as e:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse field %s in notification body. Using fallback." % e)
        subject = unicode(default_body).format(**parameters)
    except:
        logger.error(u"PlexPy NotificationHandler :: Unable to parse custom notification body. Using fallback.")
        subject = unicode(default_body).format(**parameters)

    return subject, body


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
    num = []
    num00 = []

    for k, g in groupby(enumerate(group_keys), lambda (i, x): i-x):
        group = map(itemgetter(1), g)

        if len(group) > 1:
            num.append('{0}-{1}'.format(str(min(group)).zfill(1), str(max(group)).zfill(1)))
            num00.append('{0}-{1}'.format(str(min(group)).zfill(2), str(max(group)).zfill(2)))
        else:
            num.append(str(group[0]).zfill(1))
            num00.append(str(group[0]).zfill(2))

    return ','.join(sorted(num)) or '0', ','.join(sorted(num00)) or '00'


def upload_poster(metadata):
    if metadata['media_type'] in ('movie', 'show', 'season', 'artist', 'album'):
        thumb = metadata['thumb']
        poster_key = metadata['rating_key']
        poster_title = metadata['title']
    elif metadata['media_type'] in ('season', 'album'):
        thumb = metadata['thumb']
        poster_key = metadata['rating_key']
        poster_title = '%s - %s' % (metadata['parent_title'],
                                    metadata['title'])
    elif metadata['media_type'] in ('episode', 'track'):
        thumb = metadata['parent_thumb']
        poster_key = metadata['parent_rating_key']
        poster_title = '%s - %s' % (metadata['grandparent_title'],
                                    metadata['parent_title'])
    else:
        thumb = None

    poster_url = ''

    if thumb:
        # Try to retrieve a poster_url from the database
        data_factory = datafactory.DataFactory()
        poster_url = data_factory.get_poster_url(rating_key=poster_key)

        # If no previous poster_url
        if not poster_url:
            try:
                thread_name = str(threading.current_thread().ident)
                poster_file = os.path.join(plexpy.CONFIG.CACHE_DIR, 'cache-poster-%s' % thread_name)

                # Retrieve the poster from Plex and cache to file
                pms_connect = pmsconnect.PmsConnect()
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

    return poster_url
