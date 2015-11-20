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

from plexpy import logger, database, helpers, common

import datetime


class Graphs(object):

    def __init__(self):
        pass

    def get_total_plays_per_day(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        try:
            if y_axis == 'plays':
                query = 'SELECT date(started, "unixepoch", "localtime") as date_played, ' \
                        'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                        'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count, ' \
                        'SUM(case when media_type = "track" then 1 else 0 end) as music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT date(started, "unixepoch", "localtime") as date_played, ' \
                        'SUM(case when media_type = "episode" and stopped > 0 then (stopped - started) ' \
                        ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tv_duration, ' \
                        'SUM(case when media_type = "movie" and stopped > 0 then (stopped - started) ' \
                        ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as movie_duration, ' \
                        'SUM(case when media_type = "track" and stopped > 0 then (stopped - started) ' \
                        ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as music_duration ' \
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
        series_3 = []

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if date_string == item[0]:
                    series_1_value = item[1]
                    series_2_value = item[2]
                    series_3_value = item[3]
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_per_dayofweek(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT strftime("%w", datetime(started, "unixepoch", "localtime")) as daynumber, ' \
                    'case cast (strftime("%w", datetime(started, "unixepoch", "localtime")) as integer) ' \
                    'when 0 then "Sunday" ' \
                    'when 1 then "Monday" ' \
                    'when 2 then "Tuesday" ' \
                    'when 3 then "Wednesday" ' \
                    'when 4 then "Thursday" ' \
                    'when 5 then "Friday" ' \
                    'else "Saturday" end as dayofweek, ' \
                    'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                    'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count, ' \
                    'SUM(case when media_type = "track" then 1 else 0 end) as music_count ' \
                    'FROM session_history ' \
                    'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") ' \
                    'GROUP BY dayofweek ' \
                    'ORDER BY daynumber'

            result = monitor_db.select(query)
        else:
            query = 'SELECT strftime("%w", datetime(started, "unixepoch", "localtime")) as daynumber, ' \
                    'case cast (strftime("%w", datetime(started, "unixepoch", "localtime")) as integer) ' \
                    'when 0 then "Sunday" ' \
                    'when 1 then "Monday" ' \
                    'when 2 then "Tuesday" ' \
                    'when 3 then "Wednesday" ' \
                    'when 4 then "Thursday" ' \
                    'when 5 then "Friday" ' \
                    'else "Saturday" end as dayofweek, ' \
                    'SUM(case when media_type = "episode" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tv_duration, ' \
                    'SUM(case when media_type = "movie" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as movie_duration, ' \
                    'SUM(case when media_type = "track" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as music_duration ' \
                    'FROM session_history ' \
                    'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") ' \
                    'GROUP BY dayofweek ' \
                    'ORDER BY daynumber'

            result = monitor_db.select(query)

        days_list = ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday']

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for day_item in days_list:
            categories.append(day_item)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if day_item == item[1]:
                    series_1_value = item[2]
                    series_2_value = item[3]
                    series_3_value = item[4]
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_per_hourofday(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'select strftime("%H", datetime(started, "unixepoch", "localtime")) as hourofday, ' \
                    'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                    'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count, ' \
                    'SUM(case when media_type = "track" then 1 else 0 end) as music_count ' \
                    'FROM session_history ' \
                    'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") ' \
                    'GROUP BY hourofday ' \
                    'ORDER BY hourofday'

            result = monitor_db.select(query)
        else:
            query = 'select strftime("%H", datetime(started, "unixepoch", "localtime")) as hourofday, ' \
                    'SUM(case when media_type = "episode" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tv_duration, ' \
                    'SUM(case when media_type = "movie" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as movie_duration, ' \
                    'SUM(case when media_type = "track" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as music_duration ' \
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
        series_2 = []
        series_3 = []

        for hour_item in hours_list:
            categories.append(hour_item)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if hour_item == item[0]:
                    series_1_value = item[1]
                    series_2_value = item[2]
                    series_3_value = item[3]
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_per_month(self, y_axis='plays'):
        import time as time

        monitor_db = database.MonitorDatabase()
        if y_axis == 'plays':
            query = 'SELECT strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) as datestring, ' \
                    'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                    'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count, ' \
                    'SUM(case when media_type = "track" then 1 else 0 end) as music_count ' \
                    'FROM session_history ' \
                    'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-12 months", "localtime") ' \
                    'GROUP BY strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) ' \
                    'ORDER BY datestring DESC LIMIT 12'

            result = monitor_db.select(query)
        else:
            query = 'SELECT strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) as datestring, ' \
                    'SUM(case when media_type = "episode" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tv_duration, ' \
                    'SUM(case when media_type = "movie" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as movie_duration, ' \
                    'SUM(case when media_type = "track" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as music_duration ' \
                    'FROM session_history ' \
                    'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-12 months", "localtime") ' \
                    'GROUP BY strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) ' \
                    'ORDER BY datestring DESC LIMIT 12'

            result = monitor_db.select(query)

        # create our date range as some months may not have any data
        # but we still want to display them
        x = 12
        base = time.localtime()
        month_range = [time.localtime(
            time.mktime((base.tm_year, base.tm_mon - n, 1, 0, 0, 0, 0, 0, 0))) for n in range(x)]

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for month_item in sorted(month_range):
            dt = datetime.datetime(*month_item[:6])
            date_string = dt.strftime('%Y-%m')

            categories.append(dt.strftime('%b %Y'))
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if date_string == item[0]:
                    series_1_value = item[1]
                    series_2_value = item[2]
                    series_3_value = item[3]
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_by_top_10_platforms(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT platform, ' \
                    'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                    'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count, ' \
                    'SUM(case when media_type = "track" then 1 else 0 end) as music_count, ' \
                    'COUNT(id) as total_count ' \
                    'FROM session_history ' \
                    'WHERE (datetime(stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) ' \
                    'GROUP BY platform ' \
                    'ORDER BY total_count DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)
        else:
            query = 'SELECT platform, ' \
                    'SUM(case when media_type = "episode" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tv_duration, ' \
                    'SUM(case when media_type = "movie" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as movie_duration, ' \
                    'SUM(case when media_type = "track" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as music_duration, ' \
                    'SUM(case when stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as total_duration ' \
                    'FROM session_history ' \
                    'WHERE (datetime(stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) ' \
                    'GROUP BY platform ' \
                    'ORDER BY total_duration DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item[0], item[0]))
            series_1.append(item[1])
            series_2.append(item[2])
            series_3.append(item[3])

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_by_top_10_users(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT ' \
                    '(case when users.friendly_name is null then users.username else ' \
                    'users.friendly_name end) as friendly_name,' \
                    'SUM(case when media_type = "episode" then 1 else 0 end) as tv_count, ' \
                    'SUM(case when media_type = "movie" then 1 else 0 end) as movie_count, ' \
                    'SUM(case when media_type = "track" then 1 else 0 end) as music_count, ' \
                    'COUNT(session_history.id) as total_count ' \
                    'FROM session_history ' \
                    'JOIN users on session_history.user_id = users.user_id ' \
                    'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) ' \
                    'GROUP BY session_history.user_id ' \
                    'ORDER BY total_count DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)
        else:
            query = 'SELECT ' \
                    '(case when users.friendly_name is null then users.username else ' \
                    'users.friendly_name end) as friendly_name,' \
                    'SUM(case when media_type = "episode" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tv_duration, ' \
                    'SUM(case when media_type = "movie" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as movie_duration, ' \
                    'SUM(case when media_type = "track" and stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as music_duration, ' \
                    'SUM(case when stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as total_duration ' \
                    'FROM session_history ' \
                    'JOIN users on session_history.user_id = users.user_id ' \
                    'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) ' \
                    'GROUP BY session_history.user_id ' \
                    'ORDER BY total_duration DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item[0])
            series_1.append(item[1])
            series_2.append(item[2])
            series_3.append(item[3])

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_per_stream_type(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        try:
            if y_axis == 'plays':
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") as date_played, ' \
                        'SUM(case when session_history_media_info.video_decision = "direct play" ' \
                        'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play") ' \
                        'then 1 else 0 end) as dp_count, ' \
                        'SUM(case when session_history_media_info.video_decision = "copy" ' \
                        'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy") ' \
                        'then 1 else 0 end) as ds_count, ' \
                        'SUM(case when session_history_media_info.video_decision = "transcode" ' \
                        'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode") ' \
                        'then 1 else 0 end) as tc_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") as date_played, ' \
                        'SUM(case when (session_history_media_info.video_decision = "direct play" ' \
                        'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play")) ' \
                        'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                        ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as dp_duration, ' \
                        'SUM(case when (session_history_media_info.video_decision = "copy" ' \
                        'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy")) ' \
                        'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                        ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as ds_duration, ' \
                        'SUM(case when (session_history_media_info.video_decision = "transcode" ' \
                        'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode")) ' \
                        'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                        ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tc_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
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
        series_3 = []

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if date_string == item[0]:
                    series_1_value = item[1]
                    series_2_value = item[2]
                    series_3_value = item[3]
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_by_source_resolution(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT session_history_media_info.video_resolution AS resolution, ' \
                    'SUM(case when session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play") ' \
                    'then 1 else 0 end) as dp_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy") ' \
                    'then 1 else 0 end) as ds_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode") ' \
                    'then 1 else 0 end) as tc_count, ' \
                    'COUNT(session_history.id) as total_count ' \
                    'FROM session_history ' \
                    'JOIN session_history_media_info on session_history.id = session_history_media_info.id ' \
                    'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                    'GROUP BY resolution ' \
                    'ORDER BY total_count DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)
        else:
            query = 'SELECT session_history_media_info.video_resolution AS resolution,' \
                    'SUM(case when (session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as dp_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as ds_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tc_duration, ' \
                    'SUM(case when stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as total_duration ' \
                    'FROM session_history ' \
                    'JOIN session_history_media_info on session_history.id = session_history_media_info.id ' \
                    'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                    'GROUP BY resolution ' \
                    'ORDER BY total_duration DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item[0])
            series_1.append(item[1])
            series_2.append(item[2])
            series_3.append(item[3])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_total_plays_by_stream_resolution(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT ' \
                    '(case when session_history_media_info.video_decision = "transcode" then ' \
                    '(case ' \
                    'when session_history_media_info.transcode_height <= 360 then "sd" ' \
                    'when session_history_media_info.transcode_height <= 480 then "480" ' \
                    'when session_history_media_info.transcode_height <= 576 then "576" ' \
                    'when session_history_media_info.transcode_height <= 720 then "720" ' \
                    'when session_history_media_info.transcode_height <= 1080 then "1080" ' \
                    'when session_history_media_info.transcode_height <= 1440 then "QHD" ' \
                    'when session_history_media_info.transcode_height <= 2160 then "4K" ' \
                    'else "unknown" end) else session_history_media_info.video_resolution end) as resolution, ' \
                    'SUM(case when session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play") ' \
                    'then 1 else 0 end) as dp_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy") ' \
                    'then 1 else 0 end) as ds_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode") ' \
                    'then 1 else 0 end) as tc_count, ' \
                    'COUNT(session_history.id) as total_count ' \
                    'FROM session_history ' \
                    'JOIN session_history_media_info on session_history.id = session_history_media_info.id ' \
                    'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                    'GROUP BY resolution ' \
                    'ORDER BY total_count DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)
        else:
            query = 'SELECT ' \
                    '(case when session_history_media_info.video_decision = "transcode" then ' \
                    '(case ' \
                    'when session_history_media_info.transcode_height <= 360 then "sd" ' \
                    'when session_history_media_info.transcode_height <= 480 then "480" ' \
                    'when session_history_media_info.transcode_height <= 576 then "576" ' \
                    'when session_history_media_info.transcode_height <= 720 then "720" ' \
                    'when session_history_media_info.transcode_height <= 1080 then "1080" ' \
                    'when session_history_media_info.transcode_height <= 1440 then "QHD" ' \
                    'when session_history_media_info.transcode_height <= 2160 then "4K" ' \
                    'else "unknown" end) else session_history_media_info.video_resolution end) as resolution, ' \
                    'SUM(case when (session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as dp_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as ds_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tc_duration, ' \
                    'SUM(case when stopped > 0 then (stopped - started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as total_duration ' \
                    'FROM session_history ' \
                    'JOIN session_history_media_info on session_history.id = session_history_media_info.id ' \
                    'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime")) AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                    'GROUP BY resolution ' \
                    'ORDER BY total_duration DESC ' \
                    'LIMIT 10'

            result = monitor_db.select(query)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item[0])
            series_1.append(item[1])
            series_2.append(item[2])
            series_3.append(item[3])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}
        return output

    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT ' \
                    'session_history.platform as platform, ' \
                    'SUM(case when session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play") ' \
                    'then 1 else 0 end) as dp_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy") ' \
                    'then 1 else 0 end) as ds_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode") ' \
                    'then 1 else 0 end) as tc_count, ' \
                    'COUNT(session_history.id) as total_count ' \
                    'FROM session_history ' \
                    'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                    'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                    'GROUP BY platform ' \
                    'ORDER BY total_count DESC LIMIT 10'

            result = monitor_db.select(query)
        else:
            query = 'SELECT ' \
                    'session_history.platform as platform, ' \
                    'SUM(case when (session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as dp_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as ds_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tc_duration, ' \
                    'SUM(case when session_history.stopped > 0 ' \
                    'then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as total_duration ' \
                    'FROM session_history ' \
                    'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                    'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                    'GROUP BY platform ' \
                    'ORDER BY total_duration DESC LIMIT 10'

            result = monitor_db.select(query)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item[0], item[0]))
            series_1.append(item[1])
            series_2.append(item[2])
            series_3.append(item[3])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}

        return output

    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        if y_axis == 'plays':
            query = 'SELECT ' \
                    'CASE WHEN users.friendly_name is null then users.username else users.friendly_name end as username, ' \
                    'SUM(case when session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play") ' \
                    'then 1 else 0 end) as dp_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy") ' \
                    'then 1 else 0 end) as ds_count, ' \
                    'SUM(case when session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode") ' \
                    'then 1 else 0 end) as tc_count, ' \
                    'COUNT(session_history.id) as total_count ' \
                    'FROM session_history ' \
                    'JOIN users ON session_history.user_id = users.user_id ' \
                    'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                    'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                    'GROUP BY username ' \
                    'ORDER BY total_count DESC LIMIT 10'

            result = monitor_db.select(query)
        else:
            query = 'SELECT ' \
                    'CASE WHEN users.friendly_name is null then users.username else users.friendly_name end as username, ' \
                    'SUM(case when (session_history_media_info.video_decision = "direct play" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "direct play")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as dp_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "copy" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "copy")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as ds_duration, ' \
                    'SUM(case when (session_history_media_info.video_decision = "transcode" ' \
                    'or (session_history_media_info.video_decision = "" and session_history_media_info.audio_decision = "transcode")) ' \
                    'and session_history.stopped > 0 then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as tc_duration, ' \
                    'SUM(case when session_history.stopped > 0 ' \
                    'then (session_history.stopped - session_history.started) ' \
                    ' - (case when paused_counter is NULL then 0 else paused_counter end) else 0 end) as total_duration ' \
                    'FROM session_history ' \
                    'JOIN users ON session_history.user_id = users.user_id ' \
                    'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                    'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                    'datetime("now", "-' + time_range + ' days", "localtime") AND ' \
                    '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                    'GROUP BY username ' \
                    'ORDER BY total_duration DESC LIMIT 10'

            result = monitor_db.select(query)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item[0])
            series_1.append(item[1])
            series_2.append(item[2])
            series_3.append(item[3])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}

        return output
