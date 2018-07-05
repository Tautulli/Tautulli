﻿# This file is part of Tautulli.
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

import json
from itertools import groupby

import plexpy
import common
import database
import datatables
import helpers
import logger
import pmsconnect
import session


class DataFactory(object):
    """
    Retrieve and process data from the monitor database
    """

    def __init__(self):
        pass

    def get_datatables_history(self, kwargs=None, custom_where=None, grouping=None):
        data_tables = datatables.DataTables()

        if custom_where is None:
            custon_where = []

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        if session.get_session_user_id():
            session_user_id = str(session.get_session_user_id())
            added = False

            for c_where in custom_where:
                if 'user_id' in c_where[0]:
                    # This currently only works if c_where[1] is not a list or tuple
                    if str(c_where[1]) == session_user_id:
                        added = True
                        break
                    else:
                        c_where[1] = (c_where[1], session_user_id)
                        added = True

            if not added:
                custom_where.append(['session_history.user_id', session.get_session_user_id()])

        group_by = ['session_history.reference_id'] if grouping else ['session_history.id']

        columns = [
            'session_history.reference_id',
            'session_history.id',
            'MAX(started) AS date',
            'MIN(started) AS started',
            'MAX(stopped) AS stopped',
            'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ELSE 0 END) - \
             SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS duration',
            'SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS paused_counter',
            'session_history.user_id',
            'session_history.user',
            '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" \
             THEN users.username ELSE users.friendly_name END) AS friendly_name',
            'platform',
            'player',
            'ip_address',
            'session_history.media_type',
            'session_history_metadata.rating_key',
            'session_history_metadata.parent_rating_key',
            'session_history_metadata.grandparent_rating_key',
            'session_history_metadata.full_title',
            'session_history_metadata.title',
            'session_history_metadata.parent_title',
            'session_history_metadata.grandparent_title',
            'session_history_metadata.original_title',
            'session_history_metadata.year',
            'session_history_metadata.media_index',
            'session_history_metadata.parent_media_index',
            'session_history_metadata.thumb',
            'session_history_metadata.parent_thumb',
            'session_history_metadata.grandparent_thumb',
            'MAX((CASE WHEN (view_offset IS NULL OR view_offset = "") THEN 0.1 ELSE view_offset * 1.0 END) / \
             (CASE WHEN (session_history_metadata.duration IS NULL OR session_history_metadata.duration = "") \
             THEN 1.0 ELSE session_history_metadata.duration * 1.0 END) * 100) AS percent_complete',
            'session_history_media_info.transcode_decision',
            'COUNT(*) AS group_count',
            'GROUP_CONCAT(session_history.id) AS group_ids',
            'NULL AS state',
            'NULL AS session_key'
            ]

        if plexpy.CONFIG.HISTORY_TABLE_ACTIVITY:
            table_name_union = 'sessions'
            # Very hacky way to match the custom where parameters for the unioned table
            custom_where_union = [[c[0].split('.')[-1], c[1]] for c in custom_where]
            group_by_union = ['session_key']

            columns_union = [
                'NULL AS reference_id',
                'NULL AS id',
                'started AS date',
                'started',
                'stopped',
                'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ELSE (strftime("%s", "now") - started) END) - \
                 SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS duration',
                'SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS paused_counter',
                'user_id',
                'user',
                '(CASE WHEN friendly_name IS NULL OR TRIM(friendly_name) = "" \
                 THEN user ELSE friendly_name END) AS friendly_name',
                'platform',
                'player',
                'ip_address',
                'media_type',
                'rating_key',
                'parent_rating_key',
                'grandparent_rating_key',
                'full_title',
                'title',
                'parent_title',
                'grandparent_title',
                'original_title',
                'year',
                'media_index',
                'parent_media_index',
                'thumb',
                'parent_thumb',
                'grandparent_thumb',
                'MAX((CASE WHEN (view_offset IS NULL OR view_offset = "") THEN 0.1 ELSE view_offset * 1.0 END) / \
                 (CASE WHEN (duration IS NULL OR duration = "") \
                 THEN 1.0 ELSE duration * 1.0 END) * 100) AS percent_complete',
                'transcode_decision',
                'NULL AS group_count',
                'NULL AS group_ids',
                'state',
                'session_key'
                ]

        else:
            table_name_union = None
            custom_where_union = group_by_union = columns_union = []

        try:
            query = data_tables.ssp_query(table_name='session_history',
                                          table_name_union=table_name_union,
                                          columns=columns,
                                          columns_union=columns_union,
                                          custom_where=custom_where,
                                          custom_where_union=custom_where_union,
                                          group_by=group_by,
                                          group_by_union=group_by_union,
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
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_history: %s." % e)
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        history = query['result']

        filter_duration = 0
        total_duration = self.get_total_duration(custom_where=custom_where)

        watched_percent = {'movie': plexpy.CONFIG.MOVIE_WATCHED_PERCENT,
                           'episode': plexpy.CONFIG.TV_WATCHED_PERCENT,
                           'track': plexpy.CONFIG.MUSIC_WATCHED_PERCENT,
                           'photo': 0,
                           'clip': plexpy.CONFIG.TV_WATCHED_PERCENT
                           }

        rows = []
        for item in history:
            filter_duration += int(item['duration'])

            if item['media_type'] == 'episode' and item['parent_thumb']:
                thumb = item['parent_thumb']
            elif item['media_type'] == 'episode':
                thumb = item['grandparent_thumb']
            else:
                thumb = item['thumb']

            if item['percent_complete'] >= watched_percent[item['media_type']]:
                watched_status = 1
            elif item['percent_complete'] >= watched_percent[item['media_type']]/2:
                watched_status = 0.5
            else:
                watched_status = 0

            # Rename Mystery platform names
            platform = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])

            row = {'reference_id': item['reference_id'],
                   'id': item['id'],
                   'date': item['date'],
                   'started': item['started'],
                   'stopped': item['stopped'],
                   'duration': item['duration'],
                   'paused_counter': item['paused_counter'],
                   'user_id': item['user_id'],
                   'user': item['user'],
                   'friendly_name': item['friendly_name'],
                   'platform': platform,
                   'player': item['player'],
                   'ip_address': item['ip_address'],
                   'media_type': item['media_type'],
                   'rating_key': item['rating_key'],
                   'parent_rating_key': item['parent_rating_key'],
                   'grandparent_rating_key': item['grandparent_rating_key'],
                   'full_title': item['full_title'],
                   'title': item['parent_title'],
                   'parent_title': item['parent_title'],
                   'grandparent_title': item['grandparent_title'],
                   'original_title': item['original_title'],
                   'year': item['year'],
                   'media_index': item['media_index'],
                   'parent_media_index': item['parent_media_index'],
                   'thumb': thumb,
                   'transcode_decision': item['transcode_decision'],
                   'percent_complete': int(round(item['percent_complete'])),
                   'watched_status': watched_status,
                   'group_count': item['group_count'],
                   'group_ids': item['group_ids'],
                   'state': item['state'],
                   'session_key': item['session_key']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': session.friendly_name_to_username(rows),
                'draw': query['draw'],
                'filter_duration': helpers.human_duration(filter_duration, sig='dhm'),
                'total_duration': helpers.human_duration(total_duration, sig='dhm')
                }

        return dict

    def get_home_stats(self, grouping=None, time_range=None, stats_type=None, stats_count=None, stats_cards=None):
        monitor_db = database.MonitorDatabase()

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES
        if time_range is None:
            time_range = plexpy.CONFIG.HOME_STATS_LENGTH
        if stats_type is None:
            stats_type = plexpy.CONFIG.HOME_STATS_TYPE
        if stats_count is None:
            stats_count = plexpy.CONFIG.HOME_STATS_COUNT
        if stats_cards is None:
            stats_cards = plexpy.CONFIG.HOME_STATS_CARDS

        movie_watched_percent = plexpy.CONFIG.MOVIE_WATCHED_PERCENT
        tv_watched_percent = plexpy.CONFIG.TV_WATCHED_PERCENT
        music_watched_percent = plexpy.CONFIG.MUSIC_WATCHED_PERCENT

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'
        sort_type = 'total_duration' if helpers.cast_to_int(stats_type) == 1 else 'total_plays'

        home_stats = []

        for stat in stats_cards:
            if stat == 'top_movies':
                top_movies = []
                try:
                    query = 'SELECT t.id, t.full_title, t.rating_key, t.thumb, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, t.started, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) AS total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND session_history.media_type = "movie" ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.full_title ' \
                            'ORDER BY %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_movies: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['full_title'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'users_watched': '',
                           'rating_key': item['rating_key'],
                           'last_play': item['last_watch'],
                           'grandparent_thumb': '',
                           'thumb': item['thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'platform': '',
                           'row_id': item['id']
                           }
                    top_movies.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Watched Movies',
                                   'rows': session.mask_session_info(top_movies)})

            elif stat == 'popular_movies':
                popular_movies = []
                try:
                    query = 'SELECT t.id, t.full_title, t.rating_key, t.thumb, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, t.started, ' \
                            'COUNT(DISTINCT t.user_id) AS users_watched, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) as total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND session_history.media_type = "movie" ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.full_title ' \
                            'ORDER BY users_watched DESC, %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: popular_movies: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['full_title'],
                           'users_watched': item['users_watched'],
                           'rating_key': item['rating_key'],
                           'last_play': item['last_watch'],
                           'total_plays': item['total_plays'],
                           'grandparent_thumb': '',
                           'thumb': item['thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'row_id': item['id']
                           }
                    popular_movies.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Popular Movies',
                                   'rows': session.mask_session_info(popular_movies)})

            elif stat == 'top_tv':
                top_tv = []
                try:
                    query = 'SELECT t.id, t.grandparent_title, t.grandparent_rating_key, t.grandparent_thumb, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, t.started, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) AS total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND session_history.media_type = "episode" ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.grandparent_title ' \
                            'ORDER BY %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_tv: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['grandparent_title'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'users_watched': '',
                           'rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'row_id': item['id']
                           }
                    top_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Watched TV Shows',
                                   'rows': session.mask_session_info(top_tv)})

            elif stat == 'popular_tv':
                popular_tv = []
                try:
                    query = 'SELECT t.id, t.grandparent_title, t.grandparent_rating_key, t.grandparent_thumb, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, t.started, ' \
                            'COUNT(DISTINCT t.user_id) AS users_watched, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) as total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND session_history.media_type = "episode" ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.grandparent_title ' \
                            'ORDER BY users_watched DESC, %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: popular_tv: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['grandparent_title'],
                           'users_watched': item['users_watched'],
                           'rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'total_plays': item['total_plays'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'row_id': item['id']
                           }
                    popular_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Popular TV Shows',
                                   'rows': session.mask_session_info(popular_tv)})

            elif stat == 'top_music':
                top_music = []
                try:
                    query = 'SELECT t.id, t.grandparent_title, t.original_title, ' \
                            't.grandparent_rating_key, t.grandparent_thumb, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, t.started, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) AS total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND session_history.media_type = "track" ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.original_title, t.grandparent_title ' \
                            'ORDER BY %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_music: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['original_title'] or item['grandparent_title'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'users_watched': '',
                           'rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'row_id': item['id']
                           }
                    top_music.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Played Artists',
                                   'rows': session.mask_session_info(top_music)})

            elif stat == 'popular_music':
                popular_music = []
                try:
                    query = 'SELECT t.id, t.grandparent_title, t.original_title, ' \
                            't.grandparent_rating_key, t.grandparent_thumb, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, t.started, ' \
                            'COUNT(DISTINCT t.user_id) AS users_watched, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) as total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND session_history.media_type = "track" ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.original_title, t.grandparent_title ' \
                            'ORDER BY users_watched DESC, %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: popular_music: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['original_title'] or item['grandparent_title'],
                           'users_watched': item['users_watched'],
                           'rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'total_plays': item['total_plays'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'row_id': item['id']
                           }
                    popular_music.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Popular Artists',
                                   'rows': session.mask_session_info(popular_music)})

            elif stat == 'top_users':
                top_users = []
                try:
                    query = 'SELECT t.user, t.user_id, t.user_thumb, t.custom_thumb, t.started, ' \
                            '(CASE WHEN t.friendly_name IS NULL THEN t.username ELSE t.friendly_name END) ' \
                            '   AS friendly_name, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) AS total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d, users.thumb AS user_thumb, users.custom_avatar_url AS custom_thumb ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   LEFT OUTER JOIN users ON session_history.user_id = users.user_id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.user_id ' \
                            'ORDER BY %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_users: %s." % e)
                    return None

                for item in result:
                    if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                        user_thumb = item['custom_thumb']
                    elif item['user_thumb']:
                        user_thumb = item['user_thumb']
                    else:
                        user_thumb = common.DEFAULT_USER_THUMB

                    row = {'user': item['user'],
                           'user_id': item['user_id'],
                           'friendly_name': item['friendly_name'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'last_play': item['last_watch'],
                           'user_thumb': user_thumb,
                           'grandparent_thumb': '',
                           'art': '',
                           'users_watched': '',
                           'rating_key': '',
                           'title': '',
                           'platform': '',
                           'row_id': ''
                    }
                    top_users.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Active Users',
                                   'rows': session.mask_session_info(top_users, mask_metadata=False)})

            elif stat == 'top_platforms':
                top_platform = []

                try:
                    query = 'SELECT t.platform, t.started, ' \
                            'MAX(t.started) AS last_watch, COUNT(t.id) AS total_plays, SUM(t.d) AS total_duration ' \
                            'FROM (SELECT *, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - ' \
                            '       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) ' \
                            '       AS d ' \
                            '   FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '   GROUP BY %s) AS t ' \
                            'GROUP BY t.platform ' \
                            'ORDER BY %s DESC, started DESC ' \
                            'LIMIT %s ' % (time_range, group_by, sort_type, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_platforms: %s." % e)
                    return None

                for item in result:
                    # Rename Mystery platform names
                    platform = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])
                    platform_name = next((v for k, v in common.PLATFORM_NAMES.iteritems() if k in platform.lower()), 'default')

                    row = {'platform': item['platform'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'last_play': item['last_watch'],
                           'platform': platform,
                           'platform_name': platform_name,
                           'title': '',
                           'thumb': '',
                           'grandparent_thumb': '',
                           'art': '',
                           'users_watched': '',
                           'rating_key': '',
                           'user': '',
                           'friendly_name': '',
                           'row_id': ''
                           }
                    top_platform.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Active Platforms',
                                   'rows': session.mask_session_info(top_platform, mask_metadata=False)})

            elif stat == 'last_watched':
                last_watched = []
                try:
                    query = 'SELECT t.id, t.full_title, t.rating_key, t.thumb, t.grandparent_thumb, ' \
                            't.user, t.user_id, t.custom_avatar_url as user_thumb, t.player, t.section_id, ' \
                            't.art, t.media_type, t.content_rating, t.labels, ' \
                            '(CASE WHEN t.friendly_name IS NULL THEN t.username ELSE t.friendly_name END) ' \
                            '   AS friendly_name, ' \
                            'MAX(t.started) AS last_watch, ' \
                            '((CASE WHEN t.view_offset IS NULL THEN 0.1 ELSE t.view_offset * 1.0 END) / ' \
                            '   (CASE WHEN t.duration IS NULL THEN 1.0 ELSE t.duration * 1.0 END) * 100) ' \
                            '   AS percent_complete ' \
                            'FROM (SELECT * FROM session_history ' \
                            '   JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            '   LEFT OUTER JOIN users ON session_history.user_id = users.user_id ' \
                            '   WHERE datetime(session_history.stopped, "unixepoch", "localtime") ' \
                            '       >= datetime("now", "-%s days", "localtime") ' \
                            '       AND (session_history.media_type = "movie" ' \
                            '           OR session_history_metadata.media_type = "episode") ' \
                            '   GROUP BY %s) AS t ' \
                            'WHERE t.media_type == "movie" AND percent_complete >= %s ' \
                            '   OR t.media_type == "episode" AND percent_complete >= %s ' \
                            'GROUP BY t.id ' \
                            'ORDER BY last_watch DESC ' \
                            'LIMIT %s' % (time_range, group_by, movie_watched_percent, tv_watched_percent, stats_count)
                    result = monitor_db.select(query)
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: last_watched: %s." % e)
                    return None

                for item in result:
                    if not item['grandparent_thumb'] or item['grandparent_thumb'] == '':
                        thumb = item['thumb']
                    else:
                        thumb = item['grandparent_thumb']

                    row = {'row_id': item['id'],
                           'user': item['user'],
                           'friendly_name': item['friendly_name'],
                           'user_id': item['user_id'],
                           'user_thumb': item['user_thumb'],
                           'title': item['full_title'],
                           'rating_key': item['rating_key'],
                           'thumb': thumb,
                           'grandparent_thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'last_watch': item['last_watch'],
                           'player': item['player']
                           }
                    last_watched.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Recently Watched',
                                   'rows': session.mask_session_info(last_watched)})

            elif stat == 'most_concurrent':

                def calc_most_concurrent(title, result):
                    '''
                    Function to calculate most concurrent streams
                    Input: Stat title, SQLite query result
                    Output: Dict {title, count, started, stopped}
                    '''
                    times = []
                    for item in result:
                        times.append({'time': str(item['started']) + 'B', 'count': 1})
                        times.append({'time': str(item['stopped']) + 'A', 'count': -1})
                    times = sorted(times, key=lambda k: k['time']) 

                    count = 0
                    last_count = 0
                    last_start = ''
                    concurrent = {'title': title,
                                  'count': 0,
                                  'started': None,
                                  'stopped': None
                                  }

                    for d in times:
                        if d['count'] == 1:
                            count += d['count']
                            if count >= last_count:
                                last_start = d['time']
                        else:
                            if count >= last_count:
                                last_count = count
                                concurrent['count'] = count
                                concurrent['started'] = last_start[:-1]
                                concurrent['stopped'] = d['time'][:-1]
                            count += d['count']

                    return concurrent

                most_concurrent = []

                try:
                    base_query = 'SELECT session_history.started, session_history.stopped ' \
                                 'FROM session_history ' \
                                 'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                                 'WHERE datetime(stopped, "unixepoch", "localtime") ' \
                                 '>= datetime("now", "-%s days", "localtime") ' % time_range

                    title = 'Concurrent Streams'
                    query = base_query
                    result = monitor_db.select(query)
                    if result:
                        most_concurrent.append(calc_most_concurrent(title, result))

                    title = 'Concurrent Transcodes'
                    query = base_query \
                          + 'AND session_history_media_info.transcode_decision = "transcode" '
                    result = monitor_db.select(query)
                    if result:
                        most_concurrent.append(calc_most_concurrent(title, result))

                    title = 'Concurrent Direct Streams'
                    query = base_query \
                          + 'AND session_history_media_info.transcode_decision = "copy" '
                    result = monitor_db.select(query)
                    if result:
                        most_concurrent.append(calc_most_concurrent(title, result))

                    title = 'Concurrent Direct Plays'
                    query = base_query \
                          + 'AND session_history_media_info.transcode_decision = "direct play" '
                    result = monitor_db.select(query)
                    if result:
                        most_concurrent.append(calc_most_concurrent(title, result))
                except Exception as e:
                    logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_home_stats: most_concurrent: %s." % e)
                    return None

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Concurrent Streams',
                                   'rows': most_concurrent})

        return home_stats

    def get_library_stats(self, library_cards=[]):
        monitor_db = database.MonitorDatabase()

        if session.get_session_shared_libraries():
            library_cards = session.get_session_shared_libraries()

        if 'first_run_wizard' in library_cards:
            return None

        library_stats = []

        try:
            query = 'SELECT section_id, section_name, section_type, thumb AS library_thumb, ' \
                    'custom_thumb_url AS custom_thumb, art, count, parent_count, child_count ' \
                    'FROM library_sections ' \
                    'WHERE section_id IN (%s) ' \
                    'ORDER BY section_type, count DESC, parent_count DESC, child_count DESC ' % ','.join(library_cards)
            result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_library_stats: %s." % e)
            return None

        for item in result:
            if item['custom_thumb'] and item['custom_thumb'] != item['library_thumb']:
                library_thumb = item['custom_thumb']
            elif item['library_thumb']:
                library_thumb = item['library_thumb']
            else:
                library_thumb = common.DEFAULT_COVER_THUMB

            library = {'section_id': item['section_id'],
                       'section_name': item['section_name'],
                       'section_type': item['section_type'],
                       'thumb': library_thumb,
                       'art': item['art'],
                       'count': item['count'],
                       'child_count': item['parent_count'],
                       'grandchild_count': item['child_count']
                       }
            library_stats.append(library)

        library_stats = {k: list(v) for k, v in groupby(library_stats, key=lambda x: x['section_type'])}

        return library_stats

    def get_stream_details(self, row_id=None, session_key=None):
        monitor_db = database.MonitorDatabase()

        user_cond = ''
        table = 'session_history' if row_id else 'sessions'
        if session.get_session_user_id():
            user_cond = 'AND %s.user_id = %s ' % (table, session.get_session_user_id())

        if row_id:
            query = 'SELECT bitrate, video_resolution, ' \
                    'optimized_version, optimized_version_profile, optimized_version_title, ' \
                    'synced_version, synced_version_profile, ' \
                    'container, video_codec, video_bitrate, video_width, video_height, video_framerate, aspect_ratio, ' \
                    'audio_codec, audio_bitrate, audio_channels, subtitle_codec, ' \
                    'stream_bitrate, stream_video_resolution, quality_profile, stream_container_decision, stream_container, ' \
                    'stream_video_decision, stream_video_codec, stream_video_bitrate, stream_video_width, stream_video_height, ' \
                    'stream_video_framerate, ' \
                    'stream_audio_decision, stream_audio_codec, stream_audio_bitrate, stream_audio_channels, ' \
                    'subtitles, stream_subtitle_decision, stream_subtitle_codec, ' \
                    'transcode_hw_decoding, transcode_hw_encoding, ' \
                    'video_decision, audio_decision, transcode_decision, width, height, container, ' \
                    'transcode_container, transcode_video_codec, transcode_audio_codec, transcode_audio_channels, ' \
                    'transcode_width, transcode_height, ' \
                    'session_history_metadata.media_type, title, grandparent_title, original_title ' \
                    'FROM session_history_media_info ' \
                    'JOIN session_history ON session_history_media_info.id = session_history.id ' \
                    'JOIN session_history_metadata ON session_history_media_info.id = session_history_metadata.id ' \
                    'WHERE session_history_media_info.id = ? %s' % user_cond
            result = monitor_db.select(query, args=[row_id])
        elif session_key:
            query = 'SELECT bitrate, video_resolution, ' \
                    'optimized_version, optimized_version_profile, optimized_version_title, ' \
                    'synced_version, synced_version_profile, ' \
                    'container, video_codec, video_bitrate, video_width, video_height, video_framerate, aspect_ratio, ' \
                    'audio_codec, audio_bitrate, audio_channels, subtitle_codec, ' \
                    'stream_bitrate, stream_video_resolution, quality_profile, stream_container_decision, stream_container, ' \
                    'stream_video_decision, stream_video_codec, stream_video_bitrate, stream_video_width, stream_video_height, ' \
                    'stream_video_framerate, ' \
                    'stream_audio_decision, stream_audio_codec, stream_audio_bitrate, stream_audio_channels, ' \
                    'subtitles, stream_subtitle_decision, stream_subtitle_codec, ' \
                    'transcode_hw_decoding, transcode_hw_encoding, ' \
                    'video_decision, audio_decision, transcode_decision, width, height, container, ' \
                    'transcode_container, transcode_video_codec, transcode_audio_codec, transcode_audio_channels, ' \
                    'transcode_width, transcode_height, ' \
                    'media_type, title, grandparent_title, original_title ' \
                    'FROM sessions ' \
                    'WHERE session_key = ? %s' % user_cond
            result = monitor_db.select(query, args=[session_key])
        else:
            return None

        stream_output = {}

        for item in result:
            pre_tautulli = 0

            # For backwards compatibility. Pick one new Tautulli key to check and override with old values.
            if not item['stream_video_resolution']:
                item['stream_video_resolution'] = item['video_resolution']
                item['stream_container'] = item['transcode_container'] or item['container']
                item['stream_video_decision'] = item['video_decision']
                item['stream_video_codec'] = item['transcode_video_codec'] or item['video_codec']
                item['stream_video_width'] = item['transcode_width'] or item['width']
                item['stream_video_height'] = item['transcode_height'] or item['height']
                item['stream_audio_decision'] = item['audio_decision']
                item['stream_audio_codec'] = item['transcode_audio_codec'] or item['audio_codec']
                item['stream_audio_channels'] = item['transcode_audio_channels'] or item['audio_channels']
                item['video_width'] = item['width']
                item['video_height'] = item['height']
                pre_tautulli = 1

            stream_output = {'bitrate': item['bitrate'],
                             'video_resolution': item['video_resolution'],
                             'optimized_version': item['optimized_version'],
                             'optimized_version_profile': item['optimized_version_profile'],
                             'optimized_version_title': item['optimized_version_title'],
                             'synced_version': item['synced_version'],
                             'synced_version_profile': item['synced_version_profile'],
                             'container': item['container'],
                             'video_codec': item['video_codec'],
                             'video_bitrate': item['video_bitrate'],
                             'video_width': item['video_width'],
                             'video_height': item['video_height'],
                             'video_framerate': item['video_framerate'],
                             'aspect_ratio': item['aspect_ratio'],
                             'audio_codec': item['audio_codec'],
                             'audio_bitrate': item['audio_bitrate'],
                             'audio_channels': item['audio_channels'],
                             'subtitle_codec': item['subtitle_codec'],
                             'stream_bitrate': item['stream_bitrate'],
                             'stream_video_resolution': item['stream_video_resolution'],
                             'quality_profile': item['quality_profile'],
                             'stream_container_decision': item['stream_container_decision'],
                             'stream_container': item['stream_container'],
                             'stream_video_decision': item['stream_video_decision'],
                             'stream_video_codec': item['stream_video_codec'],
                             'stream_video_bitrate': item['stream_video_bitrate'],
                             'stream_video_width': item['stream_video_width'],
                             'stream_video_height': item['stream_video_height'],
                             'stream_video_framerate': item['stream_video_framerate'],
                             'stream_audio_decision': item['stream_audio_decision'],
                             'stream_audio_codec': item['stream_audio_codec'],
                             'stream_audio_bitrate': item['stream_audio_bitrate'],
                             'stream_audio_channels': item['stream_audio_channels'],
                             'subtitles': item['subtitles'],
                             'stream_subtitle_decision': item['stream_subtitle_decision'],
                             'stream_subtitle_codec': item['stream_subtitle_codec'],
                             'transcode_hw_decoding': item['transcode_hw_decoding'],
                             'transcode_hw_encoding': item['transcode_hw_encoding'],
                             'video_decision': item['video_decision'],
                             'audio_decision': item['audio_decision'],
                             'media_type': item['media_type'],
                             'title': item['title'],
                             'grandparent_title': item['grandparent_title'],
                             'original_title': item['original_title'],
                             'current_session': 1 if session_key else 0,
                             'pre_tautulli': pre_tautulli
                             }

        stream_output = {k: v or '' for k, v in stream_output.iteritems()}
        return stream_output

    def get_metadata_details(self, rating_key):
        monitor_db = database.MonitorDatabase()

        if rating_key:
            query = 'SELECT session_history_metadata.id, ' \
                    'session_history_metadata.rating_key, session_history_metadata.parent_rating_key, ' \
                    'session_history_metadata.grandparent_rating_key, session_history_metadata.title, ' \
                    'session_history_metadata.parent_title, session_history_metadata.grandparent_title, ' \
                    'session_history_metadata.original_title, session_history_metadata.full_title, ' \
                    'library_sections.section_name, ' \
                    'session_history_metadata.media_index, session_history_metadata.parent_media_index, ' \
                    'session_history_metadata.section_id, session_history_metadata.thumb, ' \
                    'session_history_metadata.parent_thumb, session_history_metadata.grandparent_thumb, ' \
                    'session_history_metadata.art, session_history_metadata.media_type, session_history_metadata.year, ' \
                    'session_history_metadata.originally_available_at, session_history_metadata.added_at, ' \
                    'session_history_metadata.updated_at, session_history_metadata.last_viewed_at, ' \
                    'session_history_metadata.content_rating, session_history_metadata.summary, ' \
                    'session_history_metadata.tagline, session_history_metadata.rating, session_history_metadata.duration, ' \
                    'session_history_metadata.guid, session_history_metadata.directors, session_history_metadata.writers, ' \
                    'session_history_metadata.actors, session_history_metadata.genres, session_history_metadata.studio, ' \
                    'session_history_metadata.labels, ' \
                    'session_history_media_info.container, session_history_media_info.bitrate, ' \
                    'session_history_media_info.video_codec, session_history_media_info.video_resolution, ' \
                    'session_history_media_info.video_framerate, session_history_media_info.audio_codec, ' \
                    'session_history_media_info.audio_channels ' \
                    'FROM session_history_metadata ' \
                    'JOIN library_sections ON session_history_metadata.section_id = library_sections.section_id ' \
                    'JOIN session_history_media_info ON session_history_metadata.id = session_history_media_info.id ' \
                    'WHERE session_history_metadata.rating_key = ? ' \
                    'ORDER BY session_history_metadata.id DESC ' \
                    'LIMIT 1'
            result = monitor_db.select(query=query, args=[rating_key])
        else:
            result = []

        metadata_list = []

        for item in result:
            directors = item['directors'].split(';') if item['directors'] else []
            writers = item['writers'].split(';') if item['writers'] else []
            actors = item['actors'].split(';') if item['actors'] else []
            genres = item['genres'].split(';') if item['genres'] else []
            labels = item['labels'].split(';') if item['labels'] else []

            media_info = [{'container': item['container'],
                           'bitrate': item['bitrate'],
                           'video_codec': item['video_codec'],
                           'video_resolution': item['video_resolution'],
                           'video_framerate': item['video_framerate'],
                           'audio_codec': item['audio_codec'],
                           'audio_channels': item['audio_channels']
                           }]

            metadata = {'media_type': item['media_type'],
                        'rating_key': item['rating_key'],
                        'parent_rating_key': item['parent_rating_key'],
                        'grandparent_rating_key': item['grandparent_rating_key'],
                        'grandparent_title': item['grandparent_title'],
                        'original_title': item['original_title'],
                        'parent_media_index': item['parent_media_index'],
                        'parent_title': item['parent_title'],
                        'media_index': item['media_index'],
                        'studio': item['studio'],
                        'title': item['title'],
                        'content_rating': item['content_rating'],
                        'summary': item['summary'],
                        'tagline': item['tagline'],
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
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'library_name': item['section_name'],
                        'section_id': item['section_id'],
                        'media_info': media_info
                        }
            metadata_list.append(metadata)

        filtered_metadata_list = session.filter_session_info(metadata_list, filter_key='section_id')
        
        if filtered_metadata_list:
            return filtered_metadata_list[0]
        else:
            return []

    def get_total_duration(self, custom_where=None):
        monitor_db = database.MonitorDatabase()

        # Split up custom wheres
        if custom_where:
            where = 'WHERE ' + ' AND '.join([w[0] + ' = "' + w[1] + '"' for w in custom_where])
        else:
            where = ''
        
        try:
            query = 'SELECT SUM(CASE WHEN stopped > 0 THEN (stopped - started) ELSE 0 END) - ' \
                    'SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS total_duration ' \
                    'FROM session_history ' \
                    'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                    'JOIN session_history_media_info ON session_history_media_info.id = session_history.id ' \
                    '%s ' % where
            result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_total_duration: %s." % e)
            return None

        total_duration = 0
        for item in result:
            total_duration = item['total_duration']

        return total_duration

    def get_session_ip(self, session_key=''):
        monitor_db = database.MonitorDatabase()

        ip_address = 'N/A'

        user_cond = ''
        if session.get_session_user_id():
            user_cond = 'AND user_id = %s ' % session.get_session_user_id()

        if session_key:
            try:
                query = 'SELECT ip_address FROM sessions WHERE session_key = %d %s' % (int(session_key), user_cond)
                result = monitor_db.select(query)
            except Exception as e:
                logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_session_ip: %s." % e)
                return ip_address
        else:
            return ip_address

        for item in result:
            ip_address = item['ip_address']

        return ip_address

    def get_img_info(self, img=None, rating_key=None, width=None, height=None,
                     opacity=None, background=None, blur=None, fallback=None,
                     order_by='', service=None):
        monitor_db = database.MonitorDatabase()

        img_info = []

        where_params = []
        args = []

        if img is not None:
            where_params.append('img')
            args.append(img)
        if rating_key is not None:
            where_params.append('rating_key')
            args.append(rating_key)
        if width is not None:
            where_params.append('width')
            args.append(width)
        if height is not None:
            where_params.append('height')
            args.append(height)
        if opacity is not None:
            where_params.append('opacity')
            args.append(opacity)
        if background is not None:
            where_params.append('background')
            args.append(background)
        if blur is not None:
            where_params.append('blur')
            args.append(blur)
        if fallback is not None:
            where_params.append('fallback')
            args.append(fallback)

        where = ''
        if where_params:
            where = 'WHERE ' + ' AND '.join([w + ' = ?' for w in where_params])

        if order_by:
            order_by = 'ORDER BY ' + order_by + ' DESC'

        if service == 'imgur':
            query = 'SELECT imgur_title AS img_title, imgur_url AS img_url FROM imgur_lookup ' \
                    'JOIN image_hash_lookup ON imgur_lookup.img_hash = image_hash_lookup.img_hash ' \
                    '%s %s' % (where, order_by)
        elif service == 'cloudinary':
            query = 'SELECT cloudinary_title AS img_title, cloudinary_url AS img_url FROM cloudinary_lookup ' \
                    'JOIN image_hash_lookup ON cloudinary_lookup.img_hash = image_hash_lookup.img_hash ' \
                    '%s %s' % (where, order_by)
        else:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_img_info: "
                        "service not provided.")
            return img_info

        try:
            img_info = monitor_db.select(query, args=args)
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_img_info: %s." % e)

        return img_info

    def set_img_info(self, img_hash=None, img_title=None, img_url=None, delete_hash=None, service=None):
        monitor_db = database.MonitorDatabase()

        keys = {'img_hash': img_hash}

        if service == 'imgur':
            table = 'imgur_lookup'
            values = {'imgur_title': img_title,
                      'imgur_url': img_url,
                      'delete_hash': delete_hash}
        elif service == 'cloudinary':
            table = 'cloudinary_lookup'
            values = {'cloudinary_title': img_title,
                      'cloudinary_url': img_url}
        else:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for set_img_info: "
                        "service not provided.")
            return

        monitor_db.upsert(table, key_dict=keys, value_dict=values)

    def delete_img_info(self, rating_key=None, service='', delete_all=False):
        monitor_db = database.MonitorDatabase()

        if not delete_all:
            service = helpers.get_img_service()

        if not rating_key and not delete_all:
            logger.error(u"Tautulli DataFactory :: Unable to delete hosted images: rating_key not provided.")
            return False

        where = ''
        args = []
        log_msg = ''
        if rating_key:
            where = 'WHERE rating_key = ?'
            args = [rating_key]
            log_msg = ' for rating_key %s' % rating_key

        if service.lower() == 'imgur':
            # Delete from Imgur
            query = 'SELECT imgur_title, delete_hash, fallback FROM imgur_lookup ' \
                    'JOIN image_hash_lookup ON imgur_lookup.img_hash = image_hash_lookup.img_hash %s' % where
            results = monitor_db.select(query, args=args)

            for imgur_info in results:
                if imgur_info['delete_hash']:
                    helpers.delete_from_imgur(delete_hash=imgur_info['delete_hash'],
                                              img_title=imgur_info['imgur_title'],
                                              fallback=imgur_info['fallback'])

            logger.info(u"Tautulli DataFactory :: Deleting Imgur info%s from the database."
                        % log_msg)
            result = monitor_db.action('DELETE FROM imgur_lookup WHERE img_hash '
                                       'IN (SELECT img_hash FROM image_hash_lookup %s)' % where,
                                       args)

        elif service.lower() == 'cloudinary':
            # Delete from Cloudinary
            query = 'SELECT cloudinary_title, rating_key, fallback FROM cloudinary_lookup ' \
                    'JOIN image_hash_lookup ON cloudinary_lookup.img_hash = image_hash_lookup.img_hash %s ' \
                    'GROUP BY rating_key' % where
            results = monitor_db.select(query, args=args)

            for cloudinary_info in results:
                helpers.delete_from_cloudinary(rating_key=cloudinary_info['rating_key'])

            logger.info(u"Tautulli DataFactory :: Deleting Cloudinary info%s from the database."
                        % log_msg)
            result = monitor_db.action('DELETE FROM cloudinary_lookup WHERE img_hash '
                                       'IN (SELECT img_hash FROM image_hash_lookup %s)' % where,
                                       args)

        else:
            logger.error(u"Tautulli DataFactory :: Unable to delete hosted images: invalid service '%s' provided."
                         % service)

        return service

    def get_poster_info(self, rating_key='', metadata=None, service=None):
        poster_key = ''
        if str(rating_key).isdigit():
            poster_key = rating_key
        elif metadata:
            if metadata['media_type'] in ('movie', 'show', 'artist', 'collection'):
                poster_key = metadata['rating_key']
            elif metadata['media_type'] in ('season', 'album'):
                poster_key = metadata['rating_key']
            elif metadata['media_type'] in ('episode', 'track'):
                poster_key = metadata['parent_rating_key']

        poster_info = {}

        if poster_key:
            service = service or helpers.get_img_service()

            if service:
                img_info = self.get_img_info(rating_key=poster_key,
                                             order_by='height',
                                             fallback='poster',
                                             service=service)
                if img_info:
                    poster_info = {'poster_title': img_info[0]['img_title'],
                                   'poster_url': img_info[0]['img_url'],
                                   'img_service': service.capitalize()}

        return poster_info

    def get_lookup_info(self, rating_key='', metadata=None):
        monitor_db = database.MonitorDatabase()

        lookup_key = ''
        if str(rating_key).isdigit():
            lookup_key = rating_key
        elif metadata:
            if metadata['media_type'] in ('movie', 'show', 'artist'):
                lookup_key = metadata['rating_key']
            elif metadata['media_type'] in ('season', 'album'):
                lookup_key = metadata['parent_rating_key']
            elif metadata['media_type'] in ('episode', 'track'):
                lookup_key = metadata['grandparent_rating_key']

        lookup_info = {'tvmaze_id': '',
                       'themoviedb_id': ''}

        if lookup_key:
            try:
                query = 'SELECT tvmaze_id FROM tvmaze_lookup ' \
                        'WHERE rating_key = ?'
                tvmaze_info = monitor_db.select_single(query, args=[lookup_key])
                if tvmaze_info:
                    lookup_info['tvmaze_id'] = tvmaze_info['tvmaze_id']

                query = 'SELECT themoviedb_id FROM themoviedb_lookup ' \
                        'WHERE rating_key = ?'
                themoviedb_info = monitor_db.select_single(query, args=[lookup_key])
                if themoviedb_info:
                    lookup_info['themoviedb_id'] = themoviedb_info['themoviedb_id']
            except Exception as e:
                logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_lookup_info: %s." % e)

        return lookup_info

    def delete_lookup_info(self, rating_key='', title=''):
        monitor_db = database.MonitorDatabase()

        if rating_key:
            logger.info(u"Tautulli DataFactory :: Deleting lookup info for '%s' (rating_key %s) from the database."
                        % (title, rating_key))
            result_tvmaze = monitor_db.action('DELETE FROM tvmaze_lookup WHERE rating_key = ?', [rating_key])
            result_themoviedb = monitor_db.action('DELETE FROM themoviedb_lookup WHERE rating_key = ?', [rating_key])
            return True if (result_tvmaze or result_themoviedb) else False

    def get_search_query(self, rating_key=''):
        monitor_db = database.MonitorDatabase()

        if rating_key:
            query = 'SELECT rating_key, parent_rating_key, grandparent_rating_key, title, parent_title, grandparent_title, ' \
                    'media_index, parent_media_index, year, media_type ' \
                    'FROM session_history_metadata ' \
                    'WHERE rating_key = ? ' \
                    'OR parent_rating_key = ? ' \
                    'OR grandparent_rating_key = ? ' \
                    'LIMIT 1'
            result = monitor_db.select(query=query, args=[rating_key, rating_key, rating_key])
        else:
            result = []

        query = {}
        query_string = None
        media_type = None

        for item in result:
            title = item['title']
            parent_title = item['parent_title']
            grandparent_title = item['grandparent_title']
            media_index = item['media_index']
            parent_media_index = item['parent_media_index']
            year = item['year']

            if str(item['rating_key']) == rating_key:
                query_string = item['title']
                media_type = item['media_type']

            elif str(item['parent_rating_key']) == rating_key:
                if item['media_type'] == 'episode':
                    query_string = item['grandparent_title']
                    media_type = 'season'
                elif item['media_type'] == 'track':
                    query_string = item['parent_title']
                    media_type = 'album'

            elif str(item['grandparent_rating_key']) == rating_key:
                if item['media_type'] == 'episode':
                    query_string = item['grandparent_title']
                    media_type = 'show'
                elif item['media_type'] == 'track':
                    query_string = item['grandparent_title']
                    media_type = 'artist'

        if query_string and media_type:
            query = {'query_string': query_string,
                     'title': title,
                     'parent_title': parent_title,
                     'grandparent_title': grandparent_title,
                     'media_index': media_index,
                     'parent_media_index': parent_media_index,
                     'year': year,
                     'media_type': media_type,
                     'rating_key': rating_key
                     }
        else:
            return None

        return query

    def get_rating_keys_list(self, rating_key='', media_type=''):
        monitor_db = database.MonitorDatabase()

        if media_type == 'movie':
            key_list = {0: {'rating_key': int(rating_key)}}
            return key_list

        if media_type == 'artist' or media_type == 'album' or media_type == 'track':
            match_type = 'title'
        else:
            match_type = 'index'

        # Get the grandparent rating key
        try:
            query = 'SELECT rating_key, parent_rating_key, grandparent_rating_key ' \
                    'FROM session_history_metadata ' \
                    'WHERE rating_key = ? ' \
                    'OR parent_rating_key = ? ' \
                    'OR grandparent_rating_key = ? ' \
                    'LIMIT 1'
            result = monitor_db.select(query=query, args=[rating_key, rating_key, rating_key])

            grandparent_rating_key = result[0]['grandparent_rating_key']

        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_rating_keys_list: %s." % e)
            return {}

        query = 'SELECT rating_key, parent_rating_key, grandparent_rating_key, title, parent_title, grandparent_title, ' \
                'media_index, parent_media_index ' \
                'FROM session_history_metadata ' \
                'WHERE {0} = ? ' \
                'GROUP BY {1} '

        # get grandparent_rating_keys
        grandparents = {}
        result = monitor_db.select(query=query.format('grandparent_rating_key', 'grandparent_rating_key'),
                                   args=[grandparent_rating_key])
        for item in result:
            # get parent_rating_keys
            parents = {}
            result = monitor_db.select(query=query.format('grandparent_rating_key', 'parent_rating_key'),
                                       args=[item['grandparent_rating_key']])
            for item in result:
                # get rating_keys
                children = {}
                result = monitor_db.select(query=query.format('parent_rating_key', 'rating_key'),
                                           args=[item['parent_rating_key']])
                for item in result:
                    key = item['media_index'] if item['media_index'] else item['title']
                    children.update({key: {'rating_key': item['rating_key']}})

                key = item['parent_media_index'] if match_type == 'index' else item['parent_title']
                parents.update({key:
                                {'rating_key': item['parent_rating_key'],
                                 'children': children}
                                })

            key = 0 if match_type == 'index' else item['grandparent_title']
            grandparents.update({key:
                                 {'rating_key': item['grandparent_rating_key'],
                                  'children': parents}
                                 })

        key_list = grandparents

        return key_list

    def delete_session_history_rows(self, row_id=None):
        monitor_db = database.MonitorDatabase()

        if row_id.isdigit():
            logger.info(u"Tautulli DataFactory :: Deleting row id %s from the session history database." % row_id)
            session_history_del = \
                monitor_db.action('DELETE FROM session_history WHERE id = ?', [row_id])
            session_history_media_info_del = \
                monitor_db.action('DELETE FROM session_history_media_info WHERE id = ?', [row_id])
            session_history_metadata_del = \
                monitor_db.action('DELETE FROM session_history_metadata WHERE id = ?', [row_id])

            return 'Deleted rows %s.' % row_id
        else:
            return 'Unable to delete rows. Input row not valid.'

    def update_metadata(self, old_key_list='', new_key_list='', media_type=''):
        pms_connect = pmsconnect.PmsConnect()
        monitor_db = database.MonitorDatabase()

        # function to map rating keys pairs
        def get_pairs(old, new):
            pairs = {}
            for k, v in old.iteritems():
                if k in new:
                    pairs.update({v['rating_key']: new[k]['rating_key']})
                    if 'children' in old[k]:
                        pairs.update(get_pairs(old[k]['children'], new[k]['children']))

            return pairs

        # map rating keys pairs
        mapping = {}
        if old_key_list and new_key_list:
            mapping = get_pairs(old_key_list, new_key_list)

        if mapping:
            logger.info(u"Tautulli DataFactory :: Updating metadata in the database.")
            for old_key, new_key in mapping.iteritems():
                metadata = pms_connect.get_metadata_details(new_key)

                if metadata:
                    if metadata['media_type'] == 'show' or metadata['media_type'] == 'artist':
                        # check grandparent_rating_key (2 tables)
                        monitor_db.action('UPDATE session_history SET grandparent_rating_key = ? WHERE grandparent_rating_key = ?', 
                                          [new_key, old_key])
                        monitor_db.action('UPDATE session_history_metadata SET grandparent_rating_key = ? WHERE grandparent_rating_key = ?', 
                                          [new_key, old_key])
                    elif metadata['media_type'] == 'season' or metadata['media_type'] == 'album':
                        # check parent_rating_key (2 tables)
                        monitor_db.action('UPDATE session_history SET parent_rating_key = ? WHERE parent_rating_key = ?', 
                                          [new_key, old_key])
                        monitor_db.action('UPDATE session_history_metadata SET parent_rating_key = ? WHERE parent_rating_key = ?', 
                                          [new_key, old_key])
                    else:
                        # check rating_key (2 tables)
                        monitor_db.action('UPDATE session_history SET rating_key = ? WHERE rating_key = ?', 
                                          [new_key, old_key])
                        monitor_db.action('UPDATE session_history_media_info SET rating_key = ? WHERE rating_key = ?', 
                                          [new_key, old_key])

                        # update session_history_metadata table
                        self.update_metadata_details(old_key, new_key, metadata)

            return 'Updated metadata in database.'
        else:
            return 'Unable to update metadata in database. No changes were made.'

    def update_metadata_details(self, old_rating_key='', new_rating_key='', metadata=None):

        if metadata:
            # Create full_title
            if metadata['media_type'] == 'episode':
                full_title = '%s - %s' % (metadata['grandparent_title'], metadata['title'])
            elif metadata['media_type'] == 'track':
                full_title = '%s - %s' % (metadata['title'],
                                          metadata['original_title'] or metadata['grandparent_title'])
            else:
                full_title = metadata['title']

            directors = ";".join(metadata['directors'])
            writers = ";".join(metadata['writers'])
            actors = ";".join(metadata['actors'])
            genres = ";".join(metadata['genres'])
            labels = ";".join(metadata['labels'])

            #logger.info(u"Tautulli DataFactory :: Updating metadata in the database for rating key: %s." % new_rating_key)
            monitor_db = database.MonitorDatabase()

            # Update the session_history_metadata table
            query = 'UPDATE session_history_metadata SET rating_key = ?, parent_rating_key = ?, ' \
                    'grandparent_rating_key = ?, title = ?, parent_title = ?, grandparent_title = ?, ' \
                    'original_title = ?, full_title = ?, ' \
                    'media_index = ?, parent_media_index = ?, section_id = ?, thumb = ?, parent_thumb = ?, ' \
                    'grandparent_thumb = ?, art = ?, media_type = ?, year = ?, originally_available_at = ?, ' \
                    'added_at = ?, updated_at = ?, last_viewed_at = ?, content_rating = ?, summary = ?, ' \
                    'tagline = ?, rating = ?, duration = ?, guid = ?, directors = ?, writers = ?, actors = ?, ' \
                    'genres = ?, studio = ?, labels = ? ' \
                    'WHERE rating_key = ?'

            args = [metadata['rating_key'], metadata['parent_rating_key'], metadata['grandparent_rating_key'],
                    metadata['title'], metadata['parent_title'], metadata['grandparent_title'],
                    metadata['original_title'], full_title,
                    metadata['media_index'], metadata['parent_media_index'], metadata['section_id'], metadata['thumb'],
                    metadata['parent_thumb'], metadata['grandparent_thumb'], metadata['art'], metadata['media_type'],
                    metadata['year'], metadata['originally_available_at'], metadata['added_at'], metadata['updated_at'],
                    metadata['last_viewed_at'], metadata['content_rating'], metadata['summary'], metadata['tagline'], 
                    metadata['rating'], metadata['duration'], metadata['guid'], directors, writers, actors, genres,
                    metadata['studio'], labels,
                    old_rating_key]

            monitor_db.action(query=query, args=args)

    def get_notification_log(self, kwargs=None):
        data_tables = datatables.DataTables()

        columns = ['notify_log.id',
                   'notify_log.timestamp',
                   'notify_log.session_key',
                   'notify_log.rating_key',
                   'notify_log.user_id',
                   'notify_log.user',
                   'notify_log.notifier_id',
                   'notify_log.agent_id',
                   'notify_log.agent_name',
                   'notify_log.notify_action',
                   'notify_log.subject_text',
                   'notify_log.body_text',
                   'notify_log.success'
                   ]
        try:
            query = data_tables.ssp_query(table_name='notify_log',
                                          columns=columns,
                                          custom_where=[],
                                          group_by=[],
                                          join_types=[],
                                          join_tables=[],
                                          join_evals=[],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_notification_log: %s." % e)
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        notifications = query['result']

        rows = []
        for item in notifications:
            if item['body_text']:
                body_text = item['body_text'].replace('\r\n', '<br />').replace('\n', '<br />')
            else:
                body_text = ''

            row = {'id': item['id'],
                   'timestamp': item['timestamp'],
                   'session_key': item['session_key'],
                   'rating_key': item['rating_key'],
                   'user_id': item['user_id'],
                   'user': item['user'],
                   'notifier_id': item['notifier_id'],
                   'agent_id': item['agent_id'],
                   'agent_name': item['agent_name'],
                   'notify_action': item['notify_action'],
                   'subject_text': item['subject_text'],
                   'body_text': body_text,
                   'success': item['success']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }

        return dict

    def delete_notification_log(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli DataFactory :: Clearing notification logs from database.")
            monitor_db.action('DELETE FROM notify_log')
            monitor_db.action('VACUUM')
            return True
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for delete_notification_log: %s." % e)
            return False

    def get_newsletter_log(self, kwargs=None):
        data_tables = datatables.DataTables()

        columns = ['newsletter_log.id',
                   'newsletter_log.timestamp',
                   'newsletter_log.newsletter_id',
                   'newsletter_log.agent_id',
                   'newsletter_log.agent_name',
                   'newsletter_log.notify_action',
                   'newsletter_log.subject_text',
                   'newsletter_log.body_text',
                   'newsletter_log.start_date',
                   'newsletter_log.end_date',
                   'newsletter_log.uuid',
                   'newsletter_log.success'
                   ]
        try:
            query = data_tables.ssp_query(table_name='newsletter_log',
                                          columns=columns,
                                          custom_where=[],
                                          group_by=[],
                                          join_types=[],
                                          join_tables=[],
                                          join_evals=[],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_newsletter_log: %s." % e)
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        newsletters = query['result']

        rows = []
        for item in newsletters:
            row = {'id': item['id'],
                   'timestamp': item['timestamp'],
                   'newsletter_id': item['newsletter_id'],
                   'agent_id': item['agent_id'],
                   'agent_name': item['agent_name'],
                   'notify_action': item['notify_action'],
                   'subject_text': item['subject_text'],
                   'body_text': item['body_text'],
                   'start_date': item['start_date'],
                   'end_date': item['end_date'],
                   'uuid': item['uuid'],
                   'success': item['success']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }

        return dict

    def delete_newsletter_log(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli DataFactory :: Clearing newsletter logs from database.")
            monitor_db.action('DELETE FROM newsletter_log')
            monitor_db.action('VACUUM')
            return True
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for delete_newsletter_log: %s." % e)
            return False

    def get_user_devices(self, user_id=''):
        monitor_db = database.MonitorDatabase()

        if user_id:
            try:
                query = 'SELECT machine_id FROM session_history WHERE user_id = ? GROUP BY machine_id'
                result = monitor_db.select(query=query, args=[user_id])
            except Exception as e:
                logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_user_devices: %s." % e)
                return []
        else:
            return []

        return [d['machine_id'] for d in result]

    def get_recently_added_item(self, rating_key=''):
        monitor_db = database.MonitorDatabase()

        if rating_key:
            try:
                query = 'SELECT * FROM recently_added WHERE rating_key = ?'
                result = monitor_db.select(query=query, args=[rating_key])
            except Exception as e:
                logger.warn(u"Tautulli DataFactory :: Unable to execute database query for get_recently_added_item: %s." % e)
                return []
        else:
            return []

        return result

    def set_recently_added_item(self, rating_key=''):
        monitor_db = database.MonitorDatabase()

        pms_connect = pmsconnect.PmsConnect()
        metadata = pms_connect.get_metadata_details(rating_key)

        keys = {'rating_key': metadata['rating_key']}

        values = {'added_at': metadata['added_at'],
                  'section_id': metadata['section_id'],
                  'parent_rating_key': metadata['parent_rating_key'],
                  'grandparent_rating_key': metadata['grandparent_rating_key'],
                  'media_type': metadata['media_type'],
                  'media_info': json.dumps(metadata['media_info'])
                  }

        try:
            monitor_db.upsert(table_name='recently_added', key_dict=keys, value_dict=values)
        except Exception as e:
            logger.warn(u"Tautulli DataFactory :: Unable to execute database query for set_recently_added_item: %s." % e)
            return False

        return True
