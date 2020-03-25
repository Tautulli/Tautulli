# -*- coding: utf-8 -*-

# This file is part of Tautulli.
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

from __future__ import unicode_literals
from future.builtins import str
from future.builtins import range
from future.builtins import object

import datetime

import plexpy
if plexpy.PYTHON_VERSION < 3:
    import common
    import database
    import logger
    import libraries
    import session
else:
    from plexpy import common
    from plexpy import database
    from plexpy import logger
    from plexpy import libraries
    from plexpy import session


class Graphs(object):

    def __init__(self):
        pass

    def get_total_plays_per_day(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(live) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'GROUP BY date(started, "unixepoch", "localtime"), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT date(started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN live = 1 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_day: %s." % e)
            return None

        # create our date range as some days may not have any data
        # but we still want to display them
        base = datetime.date.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(0, int(time_range))]

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for date_item in sorted(date_list):
            date_string = date_item.strftime('%Y-%m-%d')
            categories.append(date_string)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if date_string == item['date_played']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_dayofweek(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

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
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(live) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'GROUP BY strftime("%%w", datetime(started, "unixepoch", "localtime")), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % (group_by, time_range, user_cond)

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
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN live = 1 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s' \
                        'GROUP BY dayofweek ' \
                        'ORDER BY daynumber' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_dayofweek: %s." % e)
            return None

        if plexpy.CONFIG.WEEK_START_MONDAY:
            days_list = ['Monday', 'Tuesday', 'Wednesday',
                         'Thursday', 'Friday', 'Saturday', 'Sunday']
        else:
            days_list = ['Sunday', 'Monday', 'Tuesday', 'Wednesday',
                         'Thursday', 'Friday', 'Saturday']

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for day_item in days_list:
            categories.append(day_item)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if day_item == item['dayofweek']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_hourofday(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(live) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'GROUP BY strftime("%%H", datetime(started, "unixepoch", "localtime")) , %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT strftime("%%H", datetime(started, "unixepoch", "localtime")) AS hourofday, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN live = 1 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") %s' \
                        'GROUP BY hourofday ' \
                        'ORDER BY hourofday' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_hourofday: %s." % e)
            return None

        hours_list = ['00', '01', '02', '03', '04', '05',
                      '06', '07', '08', '09', '10', '11',
                      '12', '13', '14', '15', '16', '17',
                      '18', '19', '20', '21', '22', '23']

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for hour_item in hours_list:
            categories.append(hour_item)
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if hour_item == item['hourofday']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_month(self, time_range='12', y_axis='plays', user_id=None, grouping=None):
        if not time_range.isdigit():
            time_range = '12'

        monitor_db = database.MonitorDatabase()

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(live) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")), %s) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s months", "localtime") %s' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT %s' % (group_by, time_range, user_cond, time_range)

                result = monitor_db.select(query)
            else:
                query = 'SELECT strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) AS datestring, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN live = 1 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS live_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id) ' \
                        'AS session_history ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s months", "localtime") %s' \
                        'GROUP BY strftime("%%Y-%%m", datetime(started, "unixepoch", "localtime")) ' \
                        'ORDER BY datestring DESC LIMIT %s' % (time_range, user_cond, time_range)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_month: %s." % e)
            return None

        # create our date range as some months may not have any data
        # but we still want to display them
        dt_today = datetime.date.today()
        dt = dt_today
        month_range = [dt]
        for n in range(int(time_range)-1):
            if not ((dt_today.month-n) % 12)-1:
                dt = datetime.date(dt.year-1, 12, 1)
            else:
                dt = datetime.date(dt.year, dt.month-1, 1)
            month_range.append(dt)

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for dt in sorted(month_range):
            date_string = dt.strftime('%Y-%m')
            categories.append(dt.strftime('%b %Y'))
            series_1_value = 0
            series_2_value = 0
            series_3_value = 0
            series_4_value = 0
            for item in result:
                if date_string == item['datestring']:
                    series_1_value = item['tv_count']
                    series_2_value = item['movie_count']
                    series_3_value = item['music_count']
                    series_4_value = item['live_count']
                    break
                else:
                    series_1_value = 0
                    series_2_value = 0
                    series_3_value = 0
                    series_4_value = 0

            series_1.append(series_1_value)
            series_2.append(series_2_value)
            series_3.append(series_3_value)
            series_4.append(series_4_value)

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(live) AS live_count, ' \
                        'COUNT(id) AS total_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'GROUP BY %s) ' \
                        'AS session_history ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT platform, ' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN live = 1 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS live_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id) ' \
                        'AS session_history ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_top_10_platforms: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        for item in result:
            categories.append(common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform']))
            series_1.append(item['tv_count'])
            series_2.append(item['movie_count'])
            series_3.append(item['music_count'])
            series_4.append(item['live_count'])

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 THEN 1 ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 THEN 1 ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 THEN 1 ELSE 0 END) AS music_count, ' \
                        'SUM(live) AS live_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'GROUP BY %s) ' \
                        'AS session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN media_type = "episode" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS tv_count, ' \
                        'SUM(CASE WHEN media_type = "movie" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS movie_count, ' \
                        'SUM(CASE WHEN media_type = "track" AND live = 0 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS music_count, ' \
                        'SUM(CASE WHEN live = 1 AND stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS live_count, ' \
                        'SUM(CASE WHEN stopped > 0 THEN (stopped - started) ' \
                        ' - (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) AS total_duration ' \
                        'FROM (SELECT * FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id) ' \
                        'AS session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime")) %s' \
                        'GROUP BY session_history.user_id ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_top_10_users: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []
        series_4 = []

        session_user_id = session.get_session_user_id()

        for item in result:
            if session_user_id:
                categories.append(item['username'] if str(item['user_id']) == session_user_id else 'Plex User')
            else:
                categories.append(item['friendly_name'])
            series_1.append(item['tv_count'])
            series_2.append(item['movie_count'])
            series_3.append(item['music_count'])
            series_4.append(item['live_count'])

        series_1_output = {'name': 'TV',
                           'data': series_1}
        series_2_output = {'name': 'Movies',
                           'data': series_2}
        series_3_output = {'name': 'Music',
                           'data': series_3}
        series_4_output = {'name': 'Live TV',
                           'data': series_4}

        series_output = []
        if libraries.has_library_type('show'):
            series_output.append(series_1_output)
        if libraries.has_library_type('movie'):
            series_output.append(series_2_output)
        if libraries.has_library_type('artist'):
            series_output.append(series_3_output)
        if libraries.has_library_type('live'):
            series_output.append(series_4_output)

        output = {'categories': categories,
                  'series': series_output}
        return output

    def get_total_plays_per_stream_type(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT date(session_history.started, "unixepoch", "localtime") AS date_played, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count ' \
                        'FROM (SELECT * FROM session_history ' \
                        'GROUP BY date(session_history.started, "unixepoch", "localtime"), %s) ' \
                        'AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % (group_by, time_range, user_cond)

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
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s' \
                        'GROUP BY date_played ' \
                        'ORDER BY started ASC' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_per_stream_type: %s." % e)
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

    def get_total_plays_by_source_resolution(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT session_history_media_info.video_full_resolution AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT session_history_media_info.video_full_resolution AS resolution,' \
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
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_source_resolution: %s." % e)
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

    def get_total_plays_by_stream_resolution(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        '(CASE WHEN session_history_media_info.stream_video_full_resolution IS NULL THEN ' \
                        '(CASE WHEN session_history_media_info.video_decision = "transcode" THEN ' \
                        '(CASE ' \
                        'WHEN session_history_media_info.transcode_height <= 360 THEN "SD" ' \
                        'WHEN session_history_media_info.transcode_height <= 480 THEN "480" ' \
                        'WHEN session_history_media_info.transcode_height <= 576 THEN "576" ' \
                        'WHEN session_history_media_info.transcode_height <= 720 THEN "720" ' \
                        'WHEN session_history_media_info.transcode_height <= 1080 THEN "1080" ' \
                        'WHEN session_history_media_info.transcode_height <= 1440 THEN "QHD" ' \
                        'WHEN session_history_media_info.transcode_height <= 2160 THEN "4k" ' \
                        'ELSE "unknown" END) ELSE session_history_media_info.video_full_resolution END) ' \
                        'ELSE session_history_media_info.stream_video_full_resolution END) AS resolution, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" '\
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_count DESC ' \
                        'LIMIT 10' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        '(CASE WHEN session_history_media_info.stream_video_full_resolution IS NULL THEN ' \
                        '(CASE WHEN session_history_media_info.video_decision = "transcode" THEN ' \
                        '(CASE ' \
                        'WHEN session_history_media_info.transcode_height <= 360 THEN "SD" ' \
                        'WHEN session_history_media_info.transcode_height <= 480 THEN "480" ' \
                        'WHEN session_history_media_info.transcode_height <= 576 THEN "576" ' \
                        'WHEN session_history_media_info.transcode_height <= 720 THEN "720" ' \
                        'WHEN session_history_media_info.transcode_height <= 1080 THEN "1080" ' \
                        'WHEN session_history_media_info.transcode_height <= 1440 THEN "QHD" ' \
                        'WHEN session_history_media_info.transcode_height <= 2160 THEN "4k" ' \
                        'ELSE "unknown" END) ELSE session_history_media_info.video_full_resolution END) ' \
                        'ELSE session_history_media_info.stream_video_full_resolution END) AS resolution, ' \
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
                        'WHERE (datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime")) AND ' \
                        '(session_history.media_type = "episode" OR session_history.media_type = "movie") %s' \
                        'GROUP BY resolution ' \
                        'ORDER BY total_duration DESC ' \
                        'LIMIT 10' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_total_plays_by_stream_resolution: %s." % e)
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

    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

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
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_count DESC LIMIT 10' % (group_by, time_range, user_cond)

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
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s' \
                        'GROUP BY platform ' \
                        'ORDER BY total_duration DESC LIMIT 10' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_stream_type_by_top_10_platforms: %s." % e)
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

    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, grouping=None):
        monitor_db = database.MonitorDatabase()

        if not time_range.isdigit():
            time_range = '30'

        user_cond = ''
        if session.get_session_user_id() and user_id and user_id != str(session.get_session_user_id()):
            user_cond = 'AND session_history.user_id = %s ' % session.get_session_user_id()
        elif user_id and user_id.isdigit():
            user_cond = 'AND session_history.user_id = %s ' % user_id

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if y_axis == 'plays':
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "direct play" ' \
                        'THEN 1 ELSE 0 END) AS dp_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "copy" ' \
                        'THEN 1 ELSE 0 END) AS ds_count, ' \
                        'SUM(CASE WHEN session_history_media_info.transcode_decision = "transcode" ' \
                        'THEN 1 ELSE 0 END) AS tc_count, ' \
                        'COUNT(session_history.id) AS total_count ' \
                        'FROM (SELECT * FROM session_history GROUP BY %s) AS session_history ' \
                        'JOIN users ON session_history.user_id = users.user_id ' \
                        'JOIN session_history_media_info ON session_history.id = session_history_media_info.id ' \
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s' \
                        'GROUP BY username ' \
                        'ORDER BY total_count DESC LIMIT 10' % (group_by, time_range, user_cond)

                result = monitor_db.select(query)
            else:
                query = 'SELECT ' \
                        'users.user_id, users.username, ' \
                        '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        ' THEN users.username ELSE users.friendly_name END) AS friendly_name,' \
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
                        'WHERE datetime(started, "unixepoch", "localtime") >= ' \
                        'datetime("now", "-%s days", "localtime") AND ' \
                        '(session_history.media_type = "episode" OR ' \
                        'session_history.media_type = "movie" OR ' \
                        'session_history.media_type = "track") %s' \
                        'GROUP BY username ' \
                        'ORDER BY total_duration DESC LIMIT 10' % (time_range, user_cond)

                result = monitor_db.select(query)
        except Exception as e:
            logger.warn("Tautulli Graphs :: Unable to execute database query for get_stream_type_by_top_10_users: %s." % e)
            return None

        categories = []
        series_1 = []
        series_2 = []
        series_3 = []

        session_user_id = session.get_session_user_id()

        for item in result:
            if session_user_id:
                categories.append(item['username'] if str(item['user_id']) == session_user_id else 'Plex User')
            else:
                categories.append(item['friendly_name'])
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
