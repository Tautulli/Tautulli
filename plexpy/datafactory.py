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

from plexpy import logger, helpers, datatables_new, common, monitor
from xml.dom import minidom

import datetime
import plexpy


class DataFactory(object):
    """
    Retrieve and process data from the plexwatch database
    """

    def __init__(self):
        pass

    def get_user_list(self, start='', length='', kwargs=None):
        data_tables = datatables_new.DataTables()

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
        data_tables = datatables_new.DataTables()

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
                   t1 + '.player',
                   t1 + '.ip_address',
                   t2 + '.full_title',
                   t1 + '.started',
                   t1 + '.paused_counter',
                   t1 + '.stopped',
                   'round((julianday(datetime(' + t1 + '.stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(' + t1 + '.started, "unixepoch", "localtime"))) * 86400) - \
                    (CASE WHEN ' + t1 + '.paused_counter IS NULL THEN 0 ELSE ' + t1 + '.paused_counter END) as duration',
                   '((CASE WHEN ' + t1 + '.view_offset IS NULL THEN 0.0 ELSE ' + t1 + '.view_offset * 1.0 END) / \
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
                   "platform": item["player"],
                   "ip_address": item["ip_address"],
                   "title": item["full_title"],
                   "started": item["started"],
                   "paused_counter": item["paused_counter"],
                   "stopped": item["stopped"],
                   "duration": item["duration"],
                   "percent_complete": round(item["percent_complete"], 0),
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

    def set_user_friendly_name(self, user=None, friendly_name=None):
        if user:
            if friendly_name.strip() == '':
                friendly_name = None

            monitor_db = monitor.MonitorDatabase()

            control_value_dict = {"username": user}
            new_value_dict = {"friendly_name": friendly_name}
            try:
                monitor_db.upsert('users', new_value_dict, control_value_dict)
            except Exception, e:
                logger.debug(u"Uncaught exception %s" % e)

    def get_user_friendly_name(self, user=None):
        if user:
            try:
                monitor_db = monitor.MonitorDatabase()
                query = 'select friendly_name FROM users WHERE username = ?'
                result = monitor_db.select_single(query, args=[user])
                if result:
                    return result
                else:
                    return user
            except:
                return user

        return None
