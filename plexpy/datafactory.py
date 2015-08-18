# This file is part of PlexPy.
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

from plexpy import logger, datatables, common, database, helpers

import datetime


class DataFactory(object):
    """
    Retrieve and process data from the monitor database
    """

    def __init__(self):
        pass

    def get_history(self, kwargs=None, custom_where=None):
        data_tables = datatables.DataTables()

        columns = ['session_history.id',
                   'session_history.started as date',
                   '(CASE WHEN users.friendly_name IS NULL THEN session_history'
                   '.user ELSE users.friendly_name END) as friendly_name',
                   'session_history.player',
                   'session_history.ip_address',
                   'session_history_metadata.full_title as full_title',
                   'session_history.started',
                   'session_history.paused_counter',
                   'session_history.stopped',
                   'round((julianday(datetime(session_history.stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(session_history.started, "unixepoch", "localtime"))) * 86400) - \
                    (CASE WHEN session_history.paused_counter IS NULL THEN 0 \
                    ELSE session_history.paused_counter END) as duration',
                   '((CASE WHEN session_history.view_offset IS NULL THEN 0.1 ELSE \
                    session_history.view_offset * 1.0 END) / \
                   (CASE WHEN session_history_metadata.duration IS NULL THEN 1.0 ELSE \
                    session_history_metadata.duration * 1.0 END) * 100) as percent_complete',
                   'session_history.grandparent_rating_key as grandparent_rating_key',
                   'session_history.rating_key as rating_key',
                   'session_history.user',
                   'session_history_metadata.media_type',
                   'session_history_media_info.video_decision',
                   'session_history.user_id as user_id'
                   ]
        try:
            query = data_tables.ssp_query(table_name='session_history',
                                          columns=columns,
                                          custom_where=custom_where,
                                          group_by=[],
                                          join_types=['LEFT OUTER JOIN',
                                                      'JOIN',
                                                      'JOIN'],
                                          join_tables=['users',
                                                       'session_history_metadata',
                                                       'session_history_media_info'],
                                          join_evals=[['session_history.user_id', 'users.user_id'],
                                                      ['session_history.id', 'session_history_metadata.id'],
                                                      ['session_history.id', 'session_history_media_info.id']],
                                          kwargs=kwargs)
        except:
            logger.warn("Unable to execute database query.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        history = query['result']

        rows = []
        for item in history:
            row = {"id": item['id'],
                   "date": item['date'],
                   "friendly_name": item['friendly_name'],
                   "player": item["player"],
                   "ip_address": item["ip_address"],
                   "full_title": item["full_title"],
                   "started": item["started"],
                   "paused_counter": item["paused_counter"],
                   "stopped": item["stopped"],
                   "duration": item["duration"],
                   "percent_complete": item["percent_complete"],
                   "grandparent_rating_key": item["grandparent_rating_key"],
                   "rating_key": item["rating_key"],
                   "user": item["user"],
                   "media_type": item["media_type"],
                   "video_decision": item["video_decision"],
                   "user_id": item["user_id"]
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
        }

        return dict

    def get_home_stats(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        # This actually determines the output order in the home page
        stats_queries = ["top_tv", "popular_tv", "top_movies", "top_users", "top_platforms"]
        home_stats = []

        for stat in stats_queries:
            if 'top_tv' in stat:
                top_tv = []
                try:
                    query = 'SELECT session_history_metadata.id, ' \
                            'session_history_metadata.grandparent_title, ' \
                            'COUNT(session_history_metadata.grandparent_title) as total_plays, ' \
                            'session_history_metadata.grandparent_rating_key, ' \
                            'MAX(session_history.started) as last_watch,' \
                            'session_history_metadata.grandparent_thumb ' \
                            'FROM session_history_metadata ' \
                            'JOIN session_history on session_history_metadata.id = session_history.id ' \
                            'WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '>= datetime("now", "-%s days", "localtime") ' \
                            'AND session_history_metadata.media_type = "episode" ' \
                            'GROUP BY session_history_metadata.grandparent_title ' \
                            'ORDER BY total_plays DESC LIMIT 10' % time_range
                    result = monitor_db.select(query)
                except:
                    logger.warn("Unable to execute database query.")
                    return None

                for item in result:
                    row = {'title': item[1],
                           'total_plays': item[2],
                           'users_watched': '',
                           'rating_key': item[3],
                           'last_play': item[4],
                           'grandparent_thumb': item[5],
                           'thumb': '',
                           'user': '',
                           'friendly_name': '',
                           'platform_type': '',
                           'platform': '',
                           'row_id': item[0]
                           }
                    top_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_tv})

            elif 'top_movies' in stat:
                top_movies = []
                try:
                    query = 'SELECT session_history_metadata.id, ' \
                            'session_history_metadata.full_title, ' \
                            'COUNT(session_history_metadata.full_title) as total_plays, ' \
                            'session_history_metadata.rating_key, ' \
                            'MAX(session_history.started) as last_watch,' \
                            'session_history_metadata.thumb ' \
                            'FROM session_history_metadata ' \
                            'JOIN session_history on session_history_metadata.id = session_history.id ' \
                            'WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '>= datetime("now", "-%s days", "localtime") ' \
                            'AND session_history_metadata.media_type = "movie" ' \
                            'GROUP BY session_history_metadata.full_title ' \
                            'ORDER BY total_plays DESC LIMIT 10' % time_range
                    result = monitor_db.select(query)
                except:
                    logger.warn("Unable to execute database query.")
                    return None

                for item in result:
                    row = {'title': item[1],
                           'total_plays': item[2],
                           'users_watched': '',
                           'rating_key': item[3],
                           'last_play': item[4],
                           'grandparent_thumb': '',
                           'thumb': item[5],
                           'user': '',
                           'friendly_name': '',
                           'platform_type': '',
                           'platform': '',
                           'row_id': item[0]
                           }
                    top_movies.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_movies})

            elif 'popular_tv' in stat:
                popular_tv = []
                try:
                    query = 'SELECT session_history_metadata.id, ' \
                            'session_history_metadata.grandparent_title, ' \
                            'COUNT(DISTINCT session_history.user_id) as users_watched, ' \
                            'session_history_metadata.grandparent_rating_key, ' \
                            'MAX(session_history.started) as last_watch, ' \
                            'COUNT(session_history.id) as total_plays, ' \
                            'session_history_metadata.grandparent_thumb ' \
                            'FROM session_history_metadata ' \
                            'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                            'WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '>= datetime("now", "-%s days", "localtime") ' \
                            'AND session_history_metadata.media_type = "episode" ' \
                            'GROUP BY session_history_metadata.grandparent_title ' \
                            'ORDER BY users_watched DESC, total_plays DESC ' \
                            'LIMIT 10' % time_range
                    result = monitor_db.select(query)
                except:
                    logger.warn("Unable to execute database query.")
                    return None

                for item in result:
                    row = {'title': item[1],
                           'users_watched': item[2],
                           'rating_key': item[3],
                           'last_play': item[4],
                           'total_plays': item[5],
                           'grandparent_thumb': item[6],
                           'thumb': '',
                           'user': '',
                           'friendly_name': '',
                           'platform_type': '',
                           'platform': '',
                           'row_id': item[0]
                           }
                    popular_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': popular_tv})

            elif 'top_users' in stat:
                top_users = []
                try:
                    query = 'SELECT session_history.user, ' \
                            '(case when users.friendly_name is null then session_history.user else ' \
                            'users.friendly_name end) as friendly_name,' \
                            'COUNT(session_history.id) as total_plays, ' \
                            'MAX(session_history.started) as last_watch, ' \
                            'users.custom_avatar_url as thumb, ' \
                            'users.user_id ' \
                            'FROM session_history ' \
                            'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                            'LEFT OUTER JOIN users ON session_history.user_id = users.user_id ' \
                            'WHERE datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                            'datetime("now", "-%s days", "localtime") '\
                            'GROUP BY session_history.user_id ' \
                            'ORDER BY total_plays DESC LIMIT 10' % time_range
                    result = monitor_db.select(query)
                except:
                    logger.warn("Unable to execute database query.")
                    return None

                for item in result:
                    if not item[4] or item[4] == '':
                        user_thumb = common.DEFAULT_USER_THUMB
                    else:
                        user_thumb = item[4]

                    row = {'user': item[0],
                           'user_id': item[5],
                           'friendly_name': item[1],
                           'total_plays': item[2],
                           'last_play': item[3],
                           'thumb': user_thumb,
                           'grandparent_thumb': '',
                           'users_watched': '',
                           'rating_key': '',
                           'title': '',
                           'platform_type': '',
                           'platform': '',
                           'row_id': ''
                    }
                    top_users.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_users})

            elif 'top_platforms' in stat:
                top_platform = []

                try:
                    query = 'SELECT session_history.platform, ' \
                            'COUNT(session_history.id) as total_plays, ' \
                            'MAX(session_history.started) as last_watch ' \
                            'FROM session_history ' \
                            'WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '>= datetime("now", "-%s days", "localtime") ' \
                            'GROUP BY session_history.platform ' \
                            'ORDER BY total_plays DESC' % time_range
                    result = monitor_db.select(query)
                except:
                    logger.warn("Unable to execute database query.")
                    return None

                for item in result:
                    row = {'platform': item[0],
                           'total_plays': item[1],
                           'last_play': item[2],
                           'platform_type': item[0],
                           'title': '',
                           'thumb': '',
                           'grandparent_thumb': '',
                           'users_watched': '',
                           'rating_key': '',
                           'user': '',
                           'friendly_name': '',
                           'row_id': ''
                           }
                    top_platform.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_platform})

        return home_stats

    def get_stream_details(self, row_id=None):
        monitor_db = database.MonitorDatabase()

        if row_id:
            query = 'SELECT container, bitrate, video_resolution, width, height, aspect_ratio, video_framerate, ' \
                    'video_codec, audio_codec, audio_channels, video_decision, transcode_video_codec, transcode_height, ' \
                    'transcode_width, audio_decision, transcode_audio_codec, transcode_audio_channels, media_type, ' \
                    'title, grandparent_title ' \
                    'from session_history_media_info ' \
                    'join session_history_metadata on session_history_media_info.id = session_history_metadata.id ' \
                    'where session_history_media_info.id = ?'
            result = monitor_db.select(query, args=[row_id])
        else:
            return None

        print result
        stream_output = {}

        for item in result:
            stream_output = {'container': item[0],
                             'bitrate': item[1],
                             'video_resolution': item[2],
                             'width': item[3],
                             'height': item[4],
                             'aspect_ratio': item[5],
                             'video_framerate': item[6],
                             'video_codec': item[7],
                             'audio_codec': item[8],
                             'audio_channels': item[9],
                             'transcode_video_dec': item[10],
                             'transcode_video_codec': item[11],
                             'transcode_height': item[12],
                             'transcode_width': item[13],
                             'transcode_audio_dec': item[14],
                             'transcode_audio_codec': item[15],
                             'transcode_audio_channels': item[16],
                             'media_type': item[17],
                             'title': item[18],
                             'grandparent_title': item[19]
                             }

        return stream_output

    def get_recently_watched(self, user=None, user_id=None, limit='10'):
        monitor_db = database.MonitorDatabase()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if user_id:
                query = 'SELECT session_history.id, session_history.media_type, session_history.rating_key, title, ' \
                        'grandparent_title, thumb, parent_thumb, media_index, parent_media_index, year, started, user ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'WHERE user_id = ? AND session_history.media_type != "track" ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[user_id, limit])
            elif user:
                query = 'SELECT session_history.id, session_history.media_type, session_history.rating_key, title, ' \
                        'grandparent_title, thumb, parent_thumb, media_index, parent_media_index, year, started, user ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'WHERE user = ? AND session_history.media_type != "track" ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[user, limit])
            else:
                query = 'SELECT session_history.id, session_history.media_type, session_history.rating_key, title, ' \
                        'grandparent_title, thumb, parent_thumb, media_index, parent_media_index, year, started, user ' \
                        'FROM session_history_metadata WHERE session_history.media_type != "track"' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[limit])
        except:
            logger.warn("Unable to execute database query.")
            return None

        for row in result:
                if row[1] == 'episode':
                    thumb = row[6]
                else:
                    thumb = row[5]

                recent_output = {'row_id': row[0],
                                 'type': row[1],
                                 'rating_key': row[2],
                                 'title': row[3],
                                 'parent_title': row[4],
                                 'thumb': thumb,
                                 'index': row[7],
                                 'parent_index': row[8],
                                 'year': row[9],
                                 'time': row[10],
                                 'user': row[11]
                                 }
                recently_watched.append(recent_output)

        return recently_watched

    def get_metadata_details(self, row_id):
        monitor_db = database.MonitorDatabase()

        if row_id:
            query = 'SELECT rating_key, parent_rating_key, grandparent_rating_key, title, parent_title, grandparent_title, ' \
                    'full_title, media_index, parent_media_index, thumb, parent_thumb, grandparent_thumb, art, media_type, ' \
                    'year, originally_available_at, added_at, updated_at, last_viewed_at, content_rating, summary, rating, ' \
                    'duration, guid, directors, writers, actors, genres, studio ' \
                    'FROM session_history_metadata ' \
                    'WHERE id = ?'
            result = monitor_db.select(query=query, args=[row_id])
        else:
            result = []

        metadata = {}
        for item in result:
            directors = item['directors'].split(';')
            writers = item['writers'].split(';')
            actors = item['actors'].split(';')
            genres = item['genres'].split(';')

            metadata = {'type': item['media_type'],
                        'rating_key': item['rating_key'],
                        'grandparent_title': item['grandparent_title'],
                        'parent_index': item['parent_media_index'],
                        'parent_title': item['parent_title'],
                        'index': item['media_index'],
                        'studio': item['studio'],
                        'title': item['title'],
                        'content_rating': item['content_rating'],
                        'summary': item['summary'],
                        'rating': item['rating'],
                        'duration': item['duration'],
                        'year': item['year'],
                        'thumb': item['thumb'],
                        'parent_thumb': item['parent_thumb'],
                        'grandparent_thumb': item['grandparent_thumb'],
                        'art': item['art'],
                        'originally_available_at': item['originally_available_at'],
                        'added_at': item['added_at'],
                        'updated_at': item['updated_at'],
                        'last_viewed_at': item['last_viewed_at'],
                        'guid': item['guid'],
                        'writers': writers,
                        'directors': directors,
                        'genres': genres,
                        'actors': actors
                        }

        return metadata

    def delete_session_history_rows(self, row_id=None):
        monitor_db = database.MonitorDatabase()

        if row_id.isdigit():
            logger.info(u"PlexPy DataFactory :: Deleting row id %s from the session history database." % row_id)
            session_history_del = \
                monitor_db.action('DELETE FROM session_history WHERE id = ?', [row_id])
            session_history_media_info_del = \
                monitor_db.action('DELETE FROM session_history_media_info WHERE id = ?', [row_id])
            session_history_metadata_del = \
                monitor_db.action('DELETE FROM session_history_metadata WHERE id = ?', [row_id])

            return 'Deleted rows %s.' % row_id
        else:
            return 'Unable to delete rows. Input row not valid.'

    def delete_all_user_history(self, user_id=None):
        monitor_db = database.MonitorDatabase()

        if user_id.isdigit():
            logger.info(u"PlexPy DataFactory :: Deleting all history for user id %s from database." % user_id)
            session_history_media_info_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history_media_info '
                                  'WHERE session_history_media_info.id IN (SELECT session_history_media_info.id '
                                  'FROM session_history_media_info '
                                  'JOIN session_history ON session_history_media_info.id = session_history.id '
                                  'WHERE session_history.user_id = ?)', [user_id])
            session_history_metadata_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history_metadata '
                                  'WHERE session_history_metadata.id IN (SELECT session_history_metadata.id '
                                  'FROM session_history_metadata '
                                  'JOIN session_history ON session_history_metadata.id = session_history.id '
                                  'WHERE session_history.user_id = ?)', [user_id])
            session_history_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history '
                                  'WHERE session_history.user_id = ?', [user_id])

            return 'Deleted all items for user_id %s.' % user_id
        else:
            return 'Unable to delete items. Input user_id not valid.'
