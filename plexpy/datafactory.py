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

from plexpy import logger, datatables, common, database

import datetime


class DataFactory(object):
    """
    Retrieve and process data from the plexwatch database
    """

    def __init__(self):
        pass

    def get_user_list(self, start='', length='', kwargs=None):
        data_tables = datatables.DataTables()

        start = int(start)
        length = int(length)
        filtered = []
        totalcount = 0
        search_value = ""
        search_regex = ""
        order_column = 1
        order_dir = "desc"

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', 1)

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        t1 = 'session_history'
        t2 = 'session_history_metadata'
        t3 = 'users'

        columns = [t1 + '.id',
                   '(case when users.friendly_name is null then ' + t1 +
                   '.user else users.friendly_name end) as friendly_name',
                   t1 + '.started',
                   t1 + '.ip_address',
                   'COUNT(' + t1 + '.rating_key) as plays',
                   t1 + '.user',
                   t1 + '.user_id',
                   'users.thumb as thumb']
        try:
            query = data_tables.ssp_query(table_name=t1,
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where='',
                                          group_by=(t1 + '.user'),
                                          join_type=['LEFT OUTER JOIN'],
                                          join_table=['users'],
                                          join_evals=[[t1 + '.user', 'users.username']],
                                          kwargs=kwargs)
        except:
            logger.warn("Unable to open session_history table.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'data': 'null'},

        users = query['result']

        rows = []
        for item in users:
            if not item['thumb'] or item['thumb'] == '':
                user_thumb = common.DEFAULT_USER_THUMB
            else:
                user_thumb = item['thumb']

            row = {"plays": item['plays'],
                   "time": item['started'],
                   "friendly_name": item["friendly_name"],
                   "ip_address": item["ip_address"],
                   "thumb": user_thumb,
                   "user": item["user"],
                   "user_id": item['user_id']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
        }

        return dict

    def get_history(self, start='', length='', kwargs=None, custom_where=''):
        data_tables = datatables.DataTables()

        start = int(start)
        length = int(length)
        filtered = []
        totalcount = 0
        search_value = ""
        search_regex = ""
        order_column = 1
        order_dir = "desc"

        t1 = 'session_history'
        t2 = 'session_history_metadata'
        t3 = 'users'
        t4 = 'session_history_media_info'

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', "1")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        columns = [t1 + '.id',
                   t1 + '.started as date',
                   '(CASE WHEN users.friendly_name IS NULL THEN ' + t1 +
                   '.user ELSE users.friendly_name END) as friendly_name',
                   t1 + '.player as platform',
                   t1 + '.ip_address',
                   t2 + '.full_title as title',
                   t1 + '.started',
                   t1 + '.paused_counter',
                   t1 + '.stopped',
                   'round((julianday(datetime(' + t1 + '.stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(' + t1 + '.started, "unixepoch", "localtime"))) * 86400) - \
                    (CASE WHEN ' + t1 + '.paused_counter IS NULL THEN 0 ELSE ' + t1 + '.paused_counter END) as duration',
                   '((CASE WHEN ' + t1 + '.view_offset IS NULL THEN 0.1 ELSE ' + t1 + '.view_offset * 1.0 END) / \
                   (CASE WHEN ' + t2 + '.duration IS NULL THEN 1.0 ELSE ' + t2 + '.duration * 1.0 END) * 100) as percent_complete',
                   t1 + '.grandparent_rating_key as grandparent_rating_key',
                   t1 + '.rating_key as rating_key',
                   t1 + '.user',
                   t2 + '.media_type',
                   t4 + '.video_decision'
                   ]
        try:
            query = data_tables.ssp_query(table_name=t1,
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where=custom_where,
                                          group_by='',
                                          join_type=['JOIN', 'JOIN', 'JOIN'],
                                          join_table=[t3, t2, t4],
                                          join_evals=[[t1 + '.user_id', t3 + '.user_id'],
                                                      [t1 + '.id', t2 + '.id'],
                                                      [t1 + '.id', t4 + '.id']],
                                          kwargs=kwargs)
        except:
            logger.warn("Unable to open PlexWatch database.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'data': 'null'},

        history = query['result']

        rows = []
        # NOTE: We are adding in a blank xml field in order enable the Datatables "searchable" parameter
        for item in history:
            row = {"id": item['id'],
                   "date": item['date'],
                   "friendly_name": item['friendly_name'],
                   "platform": item["platform"],
                   "ip_address": item["ip_address"],
                   "title": item["title"],
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
                   }

            if item['paused_counter'] > 0:
                row['paused_counter'] = item['paused_counter']
            else:
                row['paused_counter'] = 0

            if item['started']:
                if item['stopped'] > 0:
                    stopped = item['stopped']
                else:
                    stopped = 0
                if item['paused_counter'] > 0:
                    paused_counter = item['paused_counter']
                else:
                    paused_counter = 0

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
        }

        return dict

    def get_user_unique_ips(self, start='', length='', kwargs=None, custom_where=''):
        data_tables = datatables.DataTables()

        start = int(start)
        length = int(length)
        filtered = []
        totalcount = 0
        search_value = ""
        search_regex = ""
        order_column = 0
        order_dir = "desc"

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', 1)

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        columns = ['session_history.started as last_seen',
                   'session_history.ip_address as ip_address',
                   'COUNT(session_history.ip_address) as play_count',
                   'session_history.player as platform',
                   'session_history_metadata.full_title as last_watched',
                   'session_history.user as user'
                   ]

        try:
            query = data_tables.ssp_query(table_name='session_history',
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where=custom_where,
                                          group_by='session_history.ip_address',
                                          join_type=['JOIN'],
                                          join_table=['session_history_metadata'],
                                          join_evals=[['session_history.id', 'session_history_metadata.id']],
                                          kwargs=kwargs)
        except:
            logger.warn("Unable to execute database query.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'data': 'null'},

        results = query['result']

        rows = []
        for item in results:
            row = {"last_seen": item['last_seen'],
                   "ip_address": item['ip_address'],
                   "play_count": item['play_count'],
                   "platform": item['platform'],
                   "last_watched": item['last_watched']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
        }

        return dict

    def set_user_friendly_name(self, user=None, friendly_name=None):
        if user:
            if friendly_name.strip() == '':
                friendly_name = None

            monitor_db = database.MonitorDatabase()

            control_value_dict = {"username": user}
            new_value_dict = {"friendly_name": friendly_name}
            try:
                monitor_db.upsert('users', new_value_dict, control_value_dict)
            except Exception, e:
                logger.debug(u"Uncaught exception %s" % e)

    def get_user_friendly_name(self, user=None):
        if user:
            try:
                monitor_db = database.MonitorDatabase()
                query = 'select friendly_name FROM users WHERE username = ?'
                result = monitor_db.select_single(query, args=[user])
                if result:
                    return result
                else:
                    return user
            except:
                return user

        return None

    def get_user_id(self, user=None):
        if user:
            try:
                monitor_db = database.MonitorDatabase()
                query = 'select user_id FROM users WHERE username = ?'
                result = monitor_db.select_single(query, args=[user])
                if result:
                    return result
                else:
                    return None
            except:
                return None

        return None

    def get_user_details(self, user=None, user_id=None):
        try:
            monitor_db = database.MonitorDatabase()

            if user:
                query = 'SELECT user_id, username, friendly_name, email, ' \
                        'thumb, is_home_user, is_allow_sync, is_restricted ' \
                        'FROM users ' \
                        'WHERE username = ? ' \
                        'UNION ALL ' \
                        'SELECT null, user, null, null, null, null, null, null ' \
                        'FROM session_history ' \
                        'WHERE user = ? ' \
                        'GROUP BY user ' \
                        'LIMIT 1'
                result = monitor_db.select(query, args=[user, user])
            elif user_id:
                query = 'SELECT user_id, username, friendly_name, email, thumb, ' \
                        'is_home_user, is_allow_sync, is_restricted FROM users WHERE user_id = ? LIMIT 1'
                result = monitor_db.select(query, args=[user_id])
            if result:
                for item in result:
                    if not item['friendly_name']:
                        friendly_name = item['username']
                    else:
                        friendly_name = item['friendly_name']
                    if not item['thumb'] or item['thumb'] == '':
                        user_thumb = common.DEFAULT_USER_THUMB
                    else:
                        user_thumb = item['thumb']

                    user_details = {"user_id": item['user_id'],
                                    "username": item['username'],
                                    "friendly_name": friendly_name,
                                    "email": item['email'],
                                    "thumb": user_thumb,
                                    "is_home_user": item['is_home_user'],
                                    "is_allow_sync": item['is_allow_sync'],
                                    "is_restricted": item['is_restricted']
                                    }
                return user_details
            else:
                return None
        except:
            return None

        return None

    def get_home_stats(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        stats_queries = ["top_tv", "popular_tv", "top_users", "top_platforms"]
        home_stats = []

        for stat in stats_queries:
            if 'top_tv' in stat:
                top_tv = []
                try:
                    query = 'SELECT session_history_metadata.grandparent_title, ' \
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
                    row = {'title': item[0],
                           'total_plays': item[1],
                           'users_watched': '',
                           'rating_key': item[2],
                           'last_play': item[3],
                           'grandparent_thumb': item[4],
                           'thumb': '',
                           'user': '',
                           'friendly_name': '',
                           'platform_type': '',
                           'platform': ''
                           }
                    top_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_tv})

            elif 'popular_tv' in stat:
                popular_tv = []
                try:
                    query = 'SELECT session_history_metadata.grandparent_title, ' \
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
                    row = {'title': item[0],
                           'users_watched': item[1],
                           'rating_key': item[2],
                           'last_play': item[3],
                           'total_plays': item[4],
                           'grandparent_thumb': item[5],
                           'thumb': '',
                           'user': '',
                           'friendly_name': '',
                           'platform_type': '',
                           'platform': ''
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
                            'users.thumb ' \
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
                           'friendly_name': item[1],
                           'total_plays': item[2],
                           'last_play': item[3],
                           'thumb': user_thumb,
                           'grandparent_thumb': '',
                           'users_watched': '',
                           'rating_key': '',
                           'title': '',
                           'platform_type': '',
                           'platform': ''
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
                           'friendly_name': ''
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

    def get_recently_watched(self, user=None, limit='10'):
        monitor_db = database.MonitorDatabase()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if user:
                query = 'SELECT session_history.media_type, session_history.rating_key, title, thumb, parent_thumb, ' \
                        'media_index, parent_media_index, year, started, user ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'WHERE user = ? ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[user, limit])
            else:
                query = 'SELECT session_history.media_type, session_history.rating_key, title, thumb, parent_thumb, ' \
                        'media_index, parent_media_index, year, started, user ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[limit])
        except:
            logger.warn("Unable to execute database query.")
            return None

        for row in result:
                if row[0] == 'episode':
                    thumb = row[4]
                else:
                    thumb = row[3]

                recent_output = {'type': row[0],
                                 'rating_key': row[1],
                                 'title': row[2],
                                 'thumb': thumb,
                                 'index': row[5],
                                 'parentIndex': row[6],
                                 'year': row[7],
                                 'time': row[8],
                                 'user': row[9]
                                 }
                recently_watched.append(recent_output)

        return recently_watched

    def get_user_watch_time_stats(self, user=None):
        monitor_db = database.MonitorDatabase()

        time_queries = [1, 7, 30, 0]
        user_watch_time_stats = []

        for days in time_queries:
            if days > 0:
                query = 'SELECT (SUM(stopped - started) - ' \
                        'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                        'COUNT(id) AS total_plays ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'AND user = ?' % days
                result = monitor_db.select(query, args=[user])
            else:
                query = 'SELECT (SUM(stopped - started) - ' \
                        'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                        'COUNT(id) AS total_plays ' \
                        'FROM session_history ' \
                        'WHERE user = ?'
                result = monitor_db.select(query, args=[user])

            for item in result:
                if item[0]:
                    total_time = item[0]
                    total_plays = item[1]
                else:
                    total_time = 0
                    total_plays = 0

                row = {'query_days': days,
                       'total_time': total_time,
                       'total_plays': total_plays
                       }

                user_watch_time_stats.append(row)

        return user_watch_time_stats

    def get_user_platform_stats(self, user=None):
        monitor_db = database.MonitorDatabase()

        platform_stats = []
        result_id = 0

        try:
            query = 'SELECT player, COUNT(player) as player_count, platform ' \
                    'FROM session_history ' \
                    'WHERE user = ? ' \
                    'GROUP BY player ' \
                    'ORDER BY player_count DESC'
            result = monitor_db.select(query, args=[user])
        except:
            logger.warn("Unable to execute database query.")
            return None

        for item in result:
            row = {'platform_name': item[0],
                   'platform_type': item[2],
                   'total_plays': item[1],
                   'result_id': result_id
                   }
            platform_stats.append(row)
            result_id += 1

        return platform_stats

    def get_total_plays_per_day(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        try:
            query = 'SELECT date(started, "unixepoch", "localtime") as date_played, ' \
                    'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                    'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count ' \
                    'FROM session_history ' \
                    'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                    'GROUP BY date_played ' \
                    'ORDER BY started ASC' % time_range

            result = monitor_db.select(query)
        except:
            logger.warn("Unable to execute database query.")
            return None

        # create our date range as some days may not have any data
        # but we still want to display them
        base = datetime.date.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(0, int(time_range))]

        categories = []
        series_1 = []
        series_2 = []

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            for item in result:
                if date_string == item[0]:
                    series_1_value = item[1]
                    series_2_value = item[2]
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output]}
        return output

    def get_total_plays_per_dayofweek(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        query = 'SELECT strftime("%w", datetime(started, "unixepoch", "localtime")) as daynumber, ' \
                'case cast (strftime("%w", datetime(started, "unixepoch", "localtime")) as integer) ' \
                'when 0 then "Sunday" ' \
                'when 1 then "Monday" ' \
                'when 2 then "Tuesday" ' \
                'when 3 then "Wednesday" ' \
                'when 4 then "Thursday" ' \
                'when 5 then "Friday" ' \
                'else "Saturday" end as dayofweek, ' \
                'COUNT(id) as total_plays ' \
                'from session_history ' \
                'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                'datetime("now", "-' + time_range + ' days", "localtime") ' \
                'GROUP BY dayofweek ' \
                'ORDER BY daynumber'

        result = monitor_db.select(query)

        days_list = ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday']

        categories = []
        series_1 = []

        for day_item in days_list:
            categories.append(day_item)
            series_1_value = 0
            for item in result:
                if day_item == item[1]:
                    series_1_value = item[2]
                    break
                else:
                    series_1_value = 0

            series_1.append(series_1_value)

        series_1_output = {'name': 'Total plays',
                           'data': series_1}

        output = {'categories': categories,
                  'series': [series_1_output]}
        return output

    def get_total_plays_per_hourofday(self, time_range='30'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        query = 'select strftime("%H", datetime(started, "unixepoch", "localtime")) as hourofday, ' \
                'COUNT(id) ' \
                'FROM session_history ' \
                'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                'datetime("now", "-' + time_range + ' days", "localtime") ' \
                'GROUP BY hourofday ' \
                'ORDER BY hourofday'

        result = monitor_db.select(query)

        hours_list = ['00','01','02','03','04','05',
                      '06','07','08','09','10','11',
                      '12','13','14','15','16','17',
                      '18','19','20','21','22','23']

        categories = []
        series_1 = []

        for hour_item in hours_list:
            categories.append(hour_item)
            series_1_value = 0
            for item in result:
                if hour_item == item[0]:
                    series_1_value = item[1]
                    break
                else:
                    series_1_value = 0

            series_1.append(series_1_value)

        series_1_output = {'name': 'Total plays',
                           'data': series_1}

        output = {'categories': categories,
                  'series': [series_1_output]}
        return output