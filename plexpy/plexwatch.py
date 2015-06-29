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

from plexpy import logger, helpers, datatables, db
from xml.dom import minidom
import sys
if sys.version_info < (2, 7):
    from backport_collections import defaultdict, Counter
else:
    from collections import defaultdict, Counter
import datetime
import plexpy


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

        t = self.get_history_table_name()

        columns = [t + '.id',
                   '(case when plexpy_users.friendly_name is null then ' + t + '.user else plexpy_users.friendly_name end) as friendly_name',
                   t + '.time',
                   t + '.ip_address',
                   'COUNT(' + t + '.title) as plays',
                   t + '.user']
        try:
            query = data_tables.ssp_query(table_name=t,
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where='',
                                          group_by=(t + '.user'),
                                          join_type='LEFT OUTER JOIN',
                                          join_table='plexpy_users',
                                          join_evals=[t + '.user', 'plexpy_users.username'],
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
                   "friendly_name": item["friendly_name"],
                   "ip_address": item["ip_address"],
                   "thumb": thumb['user_thumb'],
                   "user": item["user"]
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

        t = self.get_history_table_name()

        columns = [t + '.time as last_seen',
                   t + '.user',
                   t + '.ip_address',
                   'COUNT(' + t + '.ip_address) as play_count',
                   t + '.platform',
                   t + '.title as last_watched'
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
                                          group_by=(t + '.ip_address'),
                                          join_type=None,
                                          join_table=None,
                                          join_evals=None,
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

        t = self.get_history_table_name()

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', "1")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        columns = [t + '.id',
                   t + '.time as date',
                   '(case when plexpy_users.friendly_name is null then ' + t + '.user else plexpy_users.friendly_name end) as friendly_name',
                   t + '.platform',
                   t + '.ip_address',
                   t + '.title',
                   t + '.time as started',
                   t + '.paused_counter',
                   t + '.stopped',
                   'round((julianday(datetime(' + t + '.stopped, "unixepoch", "localtime")) - \
                    julianday(datetime(' + t + '.time, "unixepoch", "localtime"))) * 86400) - \
                    (case when ' + t + '.paused_counter is null then 0 else ' + t + '.paused_counter end) as duration',
                   t + '.ratingKey as rating_key',
                   t + '.xml',
                   t + '.user',
                   t + '.grandparentRatingKey as grandparent_rating_key'
                   ]
        try:
            query = data_tables.ssp_query(table_name=t,
                                          columns=columns,
                                          start=start,
                                          length=length,
                                          order_column=int(order_column),
                                          order_dir=order_dir,
                                          search_value=search_value,
                                          search_regex=search_regex,
                                          custom_where=custom_where,
                                          group_by='',
                                          join_type='LEFT OUTER JOIN',
                                          join_table='plexpy_users',
                                          join_evals=[t + '.user', 'plexpy_users.username'],
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
                   "rating_key": item["rating_key"],
                   "duration": item["duration"],
                   "percent_complete": 0,
                   "xml": "",
                   "user": item["user"]
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
                        (self.get_history_table_name(), user, limit)
                xml = myDB.select(query)
            else:
                query = 'SELECT time, user, xml FROM %s ORDER BY time DESC LIMIT %s' % \
                        (self.get_history_table_name(), limit)
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
                        'FROM %s %s' % (self.get_history_table_name(), where)
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
                    'ORDER BY platform_count DESC' % (self.get_history_table_name(), user)
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
                    'ORDER BY id DESC LIMIT 1' % (self.get_history_table_name(), user)
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

        stats_queries = ["top_tv", "popular_tv", "top_users", "top_platforms"]
        home_stats = []

        for stat in stats_queries:
            if 'top_tv' in stat:
                top_tv = []
                try:
                    query = 'SELECT orig_title, COUNT(orig_title) as total_plays, grandparentRatingKey, MAX(time) as last_watch, xml ' \
                            'FROM %s ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                            'AND episode != "" ' \
                            'GROUP BY orig_title ' \
                            'ORDER BY total_plays DESC LIMIT 10' % (self.get_history_table_name(), time_range)
                    result = myDB.select(query)
                except:
                    logger.warn("Unable to open PlexWatch database.")
                    return None

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

            elif 'popular_tv' in stat:
                popular_tv = []
                try:
                    query = 'SELECT orig_title, COUNT(DISTINCT user) as users_watched, grandparentRatingKey, ' \
                            'MAX(time) as last_watch, xml, COUNT(id) as total_plays ' \
                            'FROM %s ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                            'AND episode != "" ' \
                            'GROUP BY orig_title ' \
                            'ORDER BY users_watched DESC, total_plays DESC LIMIT 10' % (self.get_history_table_name(), time_range)
                    result = myDB.select(query)
                except:
                    logger.warn("Unable to open PlexWatch database.")
                    return None

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
                               'users_watched': item[1],
                               'rating_key': item[2],
                               'last_play': item[3],
                               'total_plays': item[5],
                               'grandparent_thumb': grandparent_thumb
                               }
                        popular_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': popular_tv})

            elif 'top_users' in stat:
                top_users = []
                try:
                    s = self.get_history_table_name()
                    query = 'SELECT user, (case when friendly_name is null then user else friendly_name end) as friendly_name,' \
                            'COUNT(' + s + '.id) as total_plays, MAX(time) as last_watch ' \
                            'FROM ' + s + ' ' \
                            'LEFT OUTER JOIN plexpy_users ON ' + s + '.user = plexpy_users.username ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-' + time_range + ' days", "localtime") '\
                            'GROUP BY ' + s + '.user ' \
                            'ORDER BY total_plays DESC LIMIT 10'
                    result = myDB.select(query)
                except:
                    logger.warn("Unable to open PlexWatch database.")
                    return None

                for item in result:
                    thumb = self.get_user_gravatar_image(item[0])
                    row = {'user': item[0],
                           'friendly_name': item[1],
                           'total_plays': item[2],
                           'last_play': item[3],
                           'thumb': thumb['user_thumb']
                    }
                    top_users.append(row)

                home_stats.append({'stat_id': stat,
                                   'rows': top_users})

            elif 'top_platforms' in stat:
                top_platform = []

                try:
                    query = 'SELECT platform, COUNT(id) as total_plays, MAX(time) as last_watch, xml ' \
                            'FROM %s ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                            'GROUP BY platform ' \
                            'ORDER BY total_plays DESC' % (self.get_history_table_name(), time_range)
                    result = myDB.select(query)
                except:
                    logger.warn("Unable to open PlexWatch database.")
                    return None

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

        return home_stats

    def get_total_plays_per_day(self, time_range='30'):
        myDB = db.DBConnection()

        if not time_range.isdigit():
            time_range = '30'

        try:
            query = 'SELECT date(time, "unixepoch", "localtime") as date_played, ' \
                    'SUM(case when episode = "" then 0 else 1 end) as tv_count, ' \
                    'SUM(case when episode = "" then 1 else 0 end) as movie_count ' \
                    'FROM %s ' \
                    'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                    'GROUP BY date_played ' \
                    'ORDER BY time ASC' % (self.get_history_table_name(), time_range)

            result = myDB.select(query)
        except:
            logger.warn("Unable to open PlexWatch database.")
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
        myDB = db.DBConnection()

        if not time_range.isdigit():
            time_range = '30'

        query = 'SELECT strftime("%w", datetime(time, "unixepoch", "localtime")) as daynumber, ' \
                'case cast (strftime("%w", datetime(time, "unixepoch", "localtime")) as integer) ' \
                'when 0 then "Sunday" ' \
                'when 1 then "Monday" ' \
                'when 2 then "Tuesday" ' \
                'when 3 then "Wednesday" ' \
                'when 4 then "Thursday" ' \
                'when 5 then "Friday" ' \
                'else "Saturday" end as dayofweek, ' \
                'COUNT(id) as total_plays ' \
                'from ' + self.get_history_table_name() + ' ' + \
                'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                'datetime("now", "-' + time_range + ' days", "localtime") ' \
                'GROUP BY dayofweek ' \
                'ORDER BY daynumber'

        result = myDB.select(query)

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
        myDB = db.DBConnection()

        if not time_range.isdigit():
            time_range = '30'

        query = 'select strftime("%H", datetime(time, "unixepoch", "localtime")) as hourofday, ' \
                'COUNT(id) ' \
                'FROM ' + self.get_history_table_name() + ' ' + \
                'WHERE datetime(stopped, "unixepoch", "localtime") >= ' \
                'datetime("now", "-' + time_range + ' days", "localtime") ' \
                'GROUP BY hourofday ' \
                'ORDER BY hourofday'

        result = myDB.select(query)

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

    def set_user_friendly_name(self, user=None, friendly_name=None):
        if user and friendly_name:
            myDB = db.DBConnection()

            control_value_dict = {"username": user}
            new_value_dict = {"friendly_name": friendly_name}

            myDB.upsert('plexpy_users', new_value_dict, control_value_dict)

    def get_user_friendly_name(self, user=None):
        if user:
            myDB = db.DBConnection()

            query = 'select friendly_name FROM plexpy_users WHERE username = "%s"' % user
            result = myDB.select_single(query)

            return result

    # Taken from:
    # https://stackoverflow.com/questions/18066269/group-by-and-aggregate-the-values-of-a-list-of-dictionaries-in-python
    @staticmethod
    def group_and_sum_dataset(dataset, group_by_key, sum_value_keys, sort_by_key):

        container = defaultdict(Counter)

        for item in dataset:
            key = item[group_by_key]
            values = dict((k, item[k]) for k in sum_value_keys)
            container[key].update(values)

        new_dataset = [
            dict([(group_by_key, item[0])] + item[1].items())
            for item in container.items()
        ]
        new_dataset.sort(key=lambda item: item[sort_by_key], reverse=True)

        return new_dataset