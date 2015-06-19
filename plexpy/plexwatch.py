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

from plexpy import logger, helpers, request, datatables, config

from xml.dom import minidom
import plexpy
import json


class PlexWatch(object):
    """
    Retrieve and process data from the plexwatch database
    """

    def __init__(self):
        pass

    @staticmethod
    def get_history_table_name():

        if plexpy.CONFIG.GROUPING_GLOBAL_HISTORY:
            return "grouped"
        else:
            return "processed"

    @staticmethod
    def get_user_table_name():

        if plexpy.CONFIG.GROUPING_USER_HISTORY:
            return "grouped"
        else:
            return "processed"

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

        columns = ['user',
                   'time',
                   'ip_address',
                   'COUNT(title) as plays']

        query = data_tables.ssp_query(table_name=self.get_user_table_name(),
                                      columns=columns,
                                      start=start,
                                      length=length,
                                      order_column=int(order_column),
                                      order_dir=order_dir,
                                      search_value=search_value,
                                      search_regex=search_regex,
                                      custom_where='',
                                      group_by='user',
                                      kwargs=kwargs)

        users = query['result']

        rows = []
        for item in users:
            row = {"plays": item['plays'],
                   "time": item['time'],
                   "user": item["user"],
                   "ip_address": item["ip_address"]
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
        }

        return dict

    def get_history(self, start='', length='', kwargs=None):
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
            order_column = kwargs.get('order[0][column]', "1")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        columns = ['id',
                   'time as date',
                   'user',
                   'platform',
                   'ip_address',
                   'title',
                   'time as started',
                   'paused_counter',
                   'stopped',
                   'ratingKey as rating_key',
                   'xml',
                   'round((julianday(datetime(stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(time, "unixepoch", "localtime"))) * 86400) - \
                    (case when paused_counter is null then 0 else paused_counter end) as duration'
                   ]

        query = data_tables.ssp_query(table_name=self.get_history_table_name(),
                                      columns=columns,
                                      start=start,
                                      length=length,
                                      order_column=int(order_column),
                                      order_dir=order_dir,
                                      search_value=search_value,
                                      search_regex=search_regex,
                                      custom_where='',
                                      group_by='',
                                      kwargs=kwargs)

        history = query['result']

        rows = []
        # NOTE: We are adding in a blank xml field in order enable the Datatables "searchable" parameter
        for item in history:
            row = {"id": item['id'],
                   "date": item['date'],
                   "user": item["user"],
                   "platform": item["platform"],
                   "ip_address": item["ip_address"],
                   "title": item["title"],
                   "started": item["started"],
                   "paused_counter": item["paused_counter"],
                   "stopped": item["stopped"],
                   "rating_key": item["rating_key"],
                   "duration": item["duration"],
                   "percent_complete": 0,
                   "xml": ""}

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

            try:
                xml_parse = minidom.parseString(helpers.latinToAscii(item['xml']))
            except IOError, e:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            xml_head = xml_parse.getElementsByTagName('opt')
            if not xml_head:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            for s in xml_head:
                if s.getAttribute('duration') and s.getAttribute('viewOffset'):
                    view_offset = helpers.cast_to_float(s.getAttribute('viewOffset'))
                    duration = helpers.cast_to_float(s.getAttribute('duration'))
                    if duration > 0:
                        row['percent_complete'] = (view_offset / duration) * 100
                    else:
                        row['percent_complete'] = 0

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
        }

        return dict
