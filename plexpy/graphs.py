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
import plexpy
import pmsconnect
import datetime
import json
import operator
import os
import time


class Graphs(object):

    def __init__(self):
        pass

    def get_total_plays_per_day(self, time_range='30', y_axis='plays'):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        try:
            if y_axis == 'plays':
                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_per_day: %s." % e)
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
                if date_string == item['date_played']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
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

        try:
            if y_axis == 'plays':
                query = 'SELECT strftime("%%w", datetime(started, "unixepoch", "localtime")) AS daynumber, ' \
                        '(CASE CAST(strftime("%%w", datetime(started, "unixepoch", "localtime")) AS INTEGER) ' \
                        'WHEN 0 THEN "Sunday" ' \
                        'WHEN 1 THEN "Monday" ' \
                        'WHEN 2 THEN "Tuesday" ' \
                        'WHEN 3 THEN "Wednesday" ' \
                        'WHEN 4 THEN "Thursday" ' \
                        'WHEN 5 THEN "Friday" ' \
                        'ELSE "Saturday" END) AS dayofweek, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT strftime("%%w", datetime(started, "unixepoch", "localtime")) AS daynumber, ' \
                        '(CASE CAST(strftime("%%w", datetime(started, "unixepoch", "localtime")) AS INTEGER) ' \
                        'WHEN 0 THEN "Sunday" ' \
                        'WHEN 1 THEN "Monday" ' \
                        'WHEN 2 THEN "Tuesday" ' \
                        'WHEN 3 THEN "Wednesday" ' \
                        'WHEN 4 THEN "Thursday" ' \
                        'WHEN 5 THEN "Friday" ' \
                        'ELSE "Saturday" END) AS dayofweek, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_per_dayofweek: %s." % e)
            return None

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
                if day_item == item['dayofweek']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
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

        try:
            if y_axis == 'plays':
                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_per_hourofday: %s." % e)
            return None

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
                if hour_item == item['hourofday']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
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

        try:
            if y_axis == 'plays':
                query = 'SELECT strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-12 months", "localtime") ' \
                        'GROUP BY strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT 12'

                result = monitor_db.select(query)
            else:
                query = 'SELECT strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count ' \
                        'FROM session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-12 months", "localtime") ' \
                        'GROUP BY strftime("%Y-%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT 12'

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_per_month: %s." % e)
            return None

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

            categories.append(dt.strftime('%b %Y').decode(plexpy.SYS_ENCODING, 'replace'))
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            for item in result:
                if date_string == item['datestring']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
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

        try:
            if y_axis == 'plays':
                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count, ' \
                        'COUNT(id) AS total_count ' \
                        'FROM session_history ' \
                        'WHERE (datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) ' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'WHERE (datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) ' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_by_top_10_platforms: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform']))
            series_1.append(item['tv_count'])
            series_2.append(item['movie_count'])
            series_3.append(item['music_count'])

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

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        '(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN media_type = "episode" THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" THEN 1 ELSE 0 END) AS music_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) ' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        '(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN media_type = "episode" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) ' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_by_top_10_users: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item['friendly_name'])
            series_1.append(item['tv_count'])
            series_2.append(item['movie_count'])
            series_3.append(item['music_count'])

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
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") ' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") ' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_per_stream_type: %s." % e)
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
                if date_string == item['date_played']:
                    series_1_value = item['dp_count']
                    series_2_value = item['ds_count']
                    series_3_value = item['tc_count']
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

        try:
            if y_axis == 'plays':
                query = 'SELECT session_history_media_info.video_resolution AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT session_history_media_info.video_resolution AS resolution,' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_by_source_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item['resolution'])
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

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

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        '(CASE WHEN session_history_media_info.video_decision = "transcode" THEN ' \
                        '(CASE ' \
                        'WHEN session_history_media_info.transcode_height <= 360 THEN "sd" ' \
                        'WHEN session_history_media_info.transcode_height <= 480 THEN "480" ' \
                        'WHEN session_history_media_info.transcode_height <= 576 THEN "576" ' \
                        'WHEN session_history_media_info.transcode_height <= 720 THEN "720" ' \
                        'WHEN session_history_media_info.transcode_height <= 1080 THEN "1080" ' \
                        'WHEN session_history_media_info.transcode_height <= 1440 THEN "QHD" ' \
                        'WHEN session_history_media_info.transcode_height <= 2160 THEN "4K" ' \
                        'ELSE "unknown" END) ELSE session_history_media_info.video_resolution END) AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" '\
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        '(CASE WHEN session_history_media_info.video_decision = "transcode" THEN ' \
                        '(CASE ' \
                        'WHEN session_history_media_info.transcode_height <= 360 THEN "sd" ' \
                        'WHEN session_history_media_info.transcode_height <= 480 THEN "480" ' \
                        'WHEN session_history_media_info.transcode_height <= 576 THEN "576" ' \
                        'WHEN session_history_media_info.transcode_height <= 720 THEN "720" ' \
                        'WHEN session_history_media_info.transcode_height <= 1080 THEN "1080" ' \
                        'WHEN session_history_media_info.transcode_height <= 1440 THEN "QHD" ' \
                        'WHEN session_history_media_info.transcode_height <= 2160 THEN "4K" ' \
                        'ELSE "unknown" END) ELSE session_history_media_info.video_resolution END) AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(session_history.stopped, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") ' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_total_plays_by_stream_resolution: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item['resolution'])
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

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

        try:
            if y_axis == 'plays':
                query = 'SELECT session_history.platform AS platform, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC LIMIT 10' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT session_history.platform AS platform, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN session_history.stopped > 0 ' \
                        'THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC LIMIT 10' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_stream_type_by_top_10_platforms: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform']))
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

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

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        '(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE users.friendly_name END) AS username, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                        'GROUP BY username ' \
                        'ORDER BY total_count DESC LIMIT 10' % time_range

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        '(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE users.friendly_name END) AS username, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'AND session_history.stopped > 0 THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tc_count, ' \
                        'SUM(CASE WHEN session_history.stopped > 0 ' \
                        'THEN (session_history.stopped - session_history.started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(session_history.started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR session_history.media_type = "track") ' \
                        'GROUP BY username ' \
                        'ORDER BY total_duration DESC LIMIT 10' % time_range

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"PlexPy Graphs :: Unable to execute database query for get_stream_type_by_top_10_users: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        for item in result:
            categories.append(item['username'])
            series_1.append(item['dp_count'])
            series_2.append(item['ds_count'])
            series_3.append(item['tc_count'])

        series_1_output = {'name': 'Direct Play',
                           'data': series_1}
        series_2_output = {'name': 'Direct Stream',
                           'data': series_2}
        series_3_output = {'name': 'Transcode',
                           'data': series_3}

        output = {'categories': categories,
                  'series': [series_1_output, series_2_output, series_3_output]}

        return output

    @staticmethod
    def data_by(time_range='30', t='month', refresh=False, **kwargs):

        """ Filter all files from plex

            Args:
                time_range(string, optional): ''
                t(string): 'raw, day, date, month, hour'

            Returns:
                dict:
                    ```
                    {'date': [t], 'movies': [ints], 'track': [ints], 'episode': [ints]}
                    ```


        """
        # Placeholders
        all_files = None
        limit = None
        movie_list = []
        episode_list = []
        track_list = []
        match_list = []

        json_file = os.path.join(plexpy.CONFIG.CACHE_DIR, 'media_info_graphs.json')

        try:

            with open(json_file, 'r') as f:
                all_files = json.load(f)
        except Exception as e:
            logger.exception('Failed to read %s %s' % (json_file, e))
            return []

        # Used for debugging
        if t == 'raw':
            return all_files

        base = datetime.datetime.now().date()

        if isinstance(time_range, basestring):
            time_range = int(time_range)

        # Make list with the correct matches
        if t == 'hour':
            match_list = [d.hour for d in helpers.get_time_range('hours', n=-24, raw=True)]

        elif t == 'day':
            # dayofweek
            match_list = [d.weekday() for d in helpers.get_time_range('days', n=-7, raw=True)]

        # A time range
        elif t == 'date':
            if time_range:
                ndays = -time_range

            else:
                # Grab the oldest mediafile in plex
                oldest_file = sorted(all_files, key=operator.itemgetter('date'))[0]['date']
                start_date_ob = datetime.datetime.strptime(oldest_file, '%Y-%m-%d').date()
                delta = base - start_date_ob
                ndays = delta.days
                ndays = -ndays

            match_list = [str(d.date()) for d in helpers.get_time_range('days', n=ndays, raw=True)]

        elif t == 'month':
            match_list = helpers.get_time_range('months', n=-12)

        # for speed, works with unicode but takes longer time
        t = str(t)

        # limit the all files..
        if time_range and t != 'month':
            limit = [str(d.date()) for d in helpers.get_time_range('days', n=-time_range, raw=True)]
        else:
            limit = [str(d.date()) for d in helpers.get_time_range('days', n=-365, raw=True)]

        if limit:
            all_files = [z for z in all_files if z['date'] in limit]

        for d in match_list:
            ms = 0
            es = 0
            ts = 0
            for i in all_files:
                if d == i[t]:
                    if i['type'] == 'episode':
                        es += i['size']
                    elif i['type'] == 'movie':
                        ms += i['size']
                    elif i['type'] == 'track':
                        ts += i['size']
            movie_list.append(ms)
            episode_list.append(es)
            track_list.append(ts)

        # Add the correct date_type_list..
        if t == 'month':
            date_type_list = helpers.get_time_range('months', n=-12, format='MMMM YYYY')
        elif t == 'day':
            # correnct we have all the correct days, but we
            date_type_list = helpers.get_time_range('days', n=-7, format='dddd')
        elif t == 'hour':
            date_type_list = helpers.get_time_range('hours', n=-24, format='HH')
        elif t == 'date':
            date_type_list = [str(d.date()) for d in helpers.get_time_range('days', n=-time_range, raw=True)]

        return {'date': date_type_list, 'movie': movie_list, 'track': track_list, 'episode': episode_list}
