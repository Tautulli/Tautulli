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

from plexpy import logger, helpers, request, datatables, config, db
from xml.dom import minidom
# from collections import defaultdict, Counter

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
        try:
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
        except:
            logger.warn("Unable to open PlexWatch database.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'data': 'null'},

        users = query['result']

        rows = []
        for item in users:
            thumb = self.get_user_gravatar_image(item['user'])

            row = {"plays": item['plays'],
                   "time": item['time'],
                   "user": item["user"],
                   "ip_address": item["ip_address"],
                   "thumb": thumb['user_thumb']
                   }

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

        columns = ['time as last_seen',
                   'ip_address',
                   'COUNT(ip_address) as play_count',
                   'platform',
                   'user',
                   'orig_title as last_watched'
                   ]

        try:
            query = data_tables.ssp_query(table_name=self.get_user_table_name(),
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where=custom_where,
                                          group_by='ip_address',
                                          kwargs=kwargs)
        except:
            logger.warn("Unable to open PlexWatch database.")
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
        try:
            query = data_tables.ssp_query(table_name=self.get_history_table_name(),
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where=custom_where,
                                          group_by='',
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

    """
    Validate xml keys to make sure they exist and return their attribute value, return blank value is none found
    """
    @staticmethod
    def get_xml_attr(xml_key, attribute, return_bool=False, default_return=''):
        if xml_key.getAttribute(attribute):
            if return_bool:
                return True
            else:
                return xml_key.getAttribute(attribute)
        else:
            if return_bool:
                return False
            else:
                return default_return

    def get_stream_details(self, row_id=None):
        myDB = db.DBConnection()

        if row_id:
            query = 'SELECT xml from %s where id = %s' % (self.get_history_table_name(), row_id)
            xml = myDB.select_single(query)
            xml_data = helpers.latinToAscii(xml)
        else:
            return None

        try:
            xml_parse = minidom.parseString(xml_data)
        except:
            logger.warn("Error parsing XML for Plex stream data.")
            return None

        xml_head = xml_parse.getElementsByTagName('opt')
        if not xml_head:
            logger.warn("Error parsing XML for Plex stream data.")
            return None

        stream_output = {}

        for a in xml_head:
            media_type = self.get_xml_attr(a, 'type')
            title = self.get_xml_attr(a, 'title')
            grandparent_title = self.get_xml_attr(a, 'grandparentTitle')

            if a.getElementsByTagName('TranscodeSession'):
                transcode_data = a.getElementsByTagName('TranscodeSession')
                for transcode_session in transcode_data:
                    transcode_video_dec = self.get_xml_attr(transcode_session, 'videoDecision')
                    transcode_video_codec = self.get_xml_attr(transcode_session, 'videoCodec')
                    transcode_height = self.get_xml_attr(transcode_session, 'height')
                    transcode_width = self.get_xml_attr(transcode_session, 'width')
                    transcode_audio_dec = self.get_xml_attr(transcode_session, 'audioDecision')
                    transcode_audio_codec = self.get_xml_attr(transcode_session, 'audioCodec')
                    transcode_audio_channels = self.get_xml_attr(transcode_session, 'audioChannels')
            else:
                transcode_data = a.getElementsByTagName('Media')
                for transcode_session in transcode_data:
                    transcode_video_dec = 'direct play'
                    transcode_video_codec = self.get_xml_attr(transcode_session, 'videoCodec')
                    transcode_height = self.get_xml_attr(transcode_session, 'height')
                    transcode_width = self.get_xml_attr(transcode_session, 'width')
                    transcode_audio_dec = 'direct play'
                    transcode_audio_codec = self.get_xml_attr(transcode_session, 'audioCodec')
                    transcode_audio_channels = self.get_xml_attr(transcode_session, 'audioChannels')

            if a.getElementsByTagName('Media'):
                stream_data = a.getElementsByTagName('Media')
                for stream_item in stream_data:
                    stream_output = {'container': self.get_xml_attr(stream_item, 'container'),
                                     'bitrate': self.get_xml_attr(stream_item, 'bitrate'),
                                     'video_resolution': self.get_xml_attr(stream_item, 'videoResolution'),
                                     'width': self.get_xml_attr(stream_item, 'width'),
                                     'height': self.get_xml_attr(stream_item, 'height'),
                                     'aspect_ratio': self.get_xml_attr(stream_item, 'aspectRatio'),
                                     'video_framerate': self.get_xml_attr(stream_item, 'videoFrameRate'),
                                     'video_codec': self.get_xml_attr(stream_item, 'videoCodec'),
                                     'audio_codec': self.get_xml_attr(stream_item, 'audioCodec'),
                                     'audio_channels': self.get_xml_attr(stream_item, 'audioChannels'),
                                     'transcode_video_dec': transcode_video_dec,
                                     'transcode_video_codec': transcode_video_codec,
                                     'transcode_height': transcode_height,
                                     'transcode_width': transcode_width,
                                     'transcode_audio_dec': transcode_audio_dec,
                                     'transcode_audio_codec': transcode_audio_codec,
                                     'transcode_audio_channels': transcode_audio_channels,
                                     'media_type': media_type,
                                     'title': title,
                                     'grandparent_title': grandparent_title
                                     }

        return stream_output

    def get_recently_watched(self, user=None, limit='10'):
        myDB = db.DBConnection()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if user:
                query = 'SELECT time, user, xml FROM %s WHERE user = "%s" ORDER BY time DESC LIMIT %s' % \
                        (self.get_user_table_name(), user, limit)
                xml = myDB.select(query)
            else:
                query = 'SELECT time, user, xml FROM %s ORDER BY time DESC LIMIT %s' % \
                        (self.get_user_table_name(), limit)
                xml = myDB.select(query)
        except:
            logger.warn("Unable to open PlexWatch database.")
            return None

        for row in xml:
            xml_data = helpers.latinToAscii(row[2])
            try:
                xml_parse = minidom.parseString(xml_data)
            except:
                logger.warn("Error parsing XML for Plex stream data.")
                return None

            xml_head = xml_parse.getElementsByTagName('opt')
            if not xml_head:
                logger.warn("Error parsing XML for Plex stream data.")
                return None

            for a in xml_head:
                if self.get_xml_attr(a, 'type') == 'episode':
                    thumb = self.get_xml_attr(a, 'parentThumb')
                else:
                    thumb = self.get_xml_attr(a, 'thumb')

                recent_output = {'type': self.get_xml_attr(a, 'type'),
                                 'rating_key': self.get_xml_attr(a, 'ratingKey'),
                                 'title': self.get_xml_attr(a, 'title'),
                                 'thumb': thumb,
                                 'index': self.get_xml_attr(a, 'index'),
                                 'parentIndex': self.get_xml_attr(a, 'parentIndex'),
                                 'year': self.get_xml_attr(a, 'year'),
                                 'time': row[0],
                                 'user': row[1]
                                 }
                recently_watched.append(recent_output)

        return recently_watched

    def get_user_watch_time_stats(self, user=None):
        myDB = db.DBConnection()

        time_queries = [1, 7, 30, 0]
        user_watch_time_stats = []

        for days in time_queries:
            if days > 0:
                where = 'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'AND user = "%s"' % (days, user)
            else:
                where = 'WHERE user = "%s"' % user

            try:
                query = 'SELECT (SUM(stopped - time) - SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                        'COUNT(id) AS total_plays ' \
                        'FROM %s %s' % (self.get_user_table_name(), where)
                result = myDB.select(query)
            except:
                logger.warn("Unable to open PlexWatch database.")
                return None

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
        myDB = db.DBConnection()

        platform_stats = []
        result_id = 0

        try:
            query = 'SELECT platform, COUNT(platform) as platform_count, xml ' \
                    'FROM %s ' \
                    'WHERE user = "%s" ' \
                    'GROUP BY platform ' \
                    'ORDER BY platform_count DESC' % (self.get_user_table_name(), user)
            result = myDB.select(query)
        except:
            logger.warn("Unable to open PlexWatch database.")
            return None

        for item in result:
            xml_data = helpers.latinToAscii(item[2])

            try:
                xml_parse = minidom.parseString(xml_data)
            except:
                logger.warn("Error parsing XML for Plex stream data.")
                return None

            xml_head = xml_parse.getElementsByTagName('Player')
            if not xml_head:
                logger.warn("Error parsing XML for Plex stream data.")
                return None

            for a in xml_head:
                platform_type = self.get_xml_attr(a, 'platform')

            row = {'platform_name': item[0],
                   'platform_type': platform_type,
                   'total_plays': item[1],
                   'result_id': result_id
                   }
            platform_stats.append(row)
            result_id += 1

        return platform_stats

    def get_user_gravatar_image(self, user=None):
        myDB = db.DBConnection()
        user_info = None

        try:
            query = 'SELECT xml ' \
                    'FROM %s ' \
                    'WHERE user = "%s" ' \
                    'ORDER BY id DESC LIMIT 1' % (self.get_user_table_name(), user)
            result = myDB.select_single(query)
        except:
            logger.warn("Unable to open PlexWatch database.")
            return None

        xml_data = helpers.latinToAscii(result)

        try:
            xml_parse = minidom.parseString(xml_data)
        except:
            logger.warn("Error parsing XML for Plexwatch Database.")
            return None

        xml_head = xml_parse.getElementsByTagName('User')
        if not xml_head:
            logger.warn("Error parsing XML for Plexwatch Database.")
            return None

        for a in xml_head:
            user_id = self.get_xml_attr(a, 'id')
            user_thumb = self.get_xml_attr(a, 'thumb')

            user_info = {'user_id': user_id,
                         'user_thumb': user_thumb}

        return user_info

    def get_home_stats(self, time_range='30'):
        myDB = db.DBConnection()

        if not time_range.isdigit():
            time_range = '30'

        stats_queries = ["top_tv", "top_users", "top_platforms"]
        home_stats = []

        for stat in stats_queries:
            if 'top_tv' in stat:
                top_tv = []
                query = 'SELECT orig_title, COUNT(orig_title) as total_plays, grandparentRatingKey, MAX(time) as last_watch, xml ' \
                        'FROM %s ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'AND episode != "" ' \
                        'GROUP BY orig_title ' \
                        'ORDER BY total_plays DESC LIMIT 10' % (self.get_user_table_name(), time_range)
                result = myDB.select(query)

                for item in result:
                    xml_data = helpers.latinToAscii(item[4])

                    try:
                        xml_parse = minidom.parseString(xml_data)
                    except:
                        logger.warn("Error parsing XML for Plexwatch database.")
                        return None

                    xml_head = xml_parse.getElementsByTagName('opt')
                    if not xml_head:
                        logger.warn("Error parsing XML for Plexwatch database.")
                        return None

                    for a in xml_head:
                        grandparent_thumb = self.get_xml_attr(a, 'grandparentThumb')

                        row = {'orig_title': item[0],
                               'total_plays': item[1],
                               'rating_key': item[2],
                               'last_play': item[3],
                               'grandparent_thumb': grandparent_thumb
                               }
                        top_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_tv})

            elif 'top_users' in stat:
                top_users = []
                query = 'SELECT user, COUNT(id) as total_plays, MAX(time) as last_watch ' \
                        'FROM %s ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY user ' \
                        'ORDER BY total_plays DESC LIMIT 10' % (self.get_user_table_name(), time_range)
                result = myDB.select(query)

                for item in result:
                    thumb = self.get_user_gravatar_image(item[0])
                    row = {'user': item[0],
                           'total_plays': item[1],
                           'last_play': item[2],
                           'thumb': thumb['user_thumb']
                    }
                    top_users.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_users})
            '''
            elif 'top_platforms' in stat:
                top_platform = []
                query = 'SELECT platform, COUNT(id) as total_plays, MAX(time) as last_watch, xml ' \
                        'FROM %s ' \
                        'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                        'GROUP BY platform ' \
                        'ORDER BY total_plays DESC' % (self.get_user_table_name(), time_range)
                result = myDB.select(query)

                for item in result:
                    xml_data = helpers.latinToAscii(item[3])

                    try:
                        xml_parse = minidom.parseString(xml_data)
                    except:
                        logger.warn("Error parsing XML for Plexwatch database.")
                        return None

                    xml_head = xml_parse.getElementsByTagName('Player')
                    if not xml_head:
                        logger.warn("Error parsing XML for Plexwatch database.")
                        return None

                    for a in xml_head:
                        platform_type = self.get_xml_attr(a, 'platform')

                        row = {'platform': item[0],
                               'total_plays': item[1],
                               'last_play': item[2],
                               'platform_type': platform_type
                               }
                        top_platform.append(row)

                top_platform_aggr = self.group_and_sum_dataset(
                    top_platform, 'platform_type', ['total_plays'], 'total_plays')

                home_stats.append({'stat_id': stat,
                                   'rows': top_platform_aggr})
            '''
        return home_stats

    # Taken from:
    # https://stackoverflow.com/questions/18066269/group-by-and-aggregate-the-values-of-a-list-of-dictionaries-in-python
    '''
    @staticmethod
    def group_and_sum_dataset(dataset, group_by_key, sum_value_keys, sort_by_key):

        container = defaultdict(Counter)

        for item in dataset:
            key = item[group_by_key]
            values = {k: item[k] for k in sum_value_keys}
            container[key].update(values)

        new_dataset = [
            dict([(group_by_key, item[0])] + item[1].items())
            for item in container.items()
        ]
        new_dataset.sort(key=lambda item: item[sort_by_key], reverse=True)

        return new_dataset
    '''