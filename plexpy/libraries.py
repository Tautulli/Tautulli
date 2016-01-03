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


class Libraries(object):

    def __init__(self):
        pass

    def get_library_list(self, kwargs=None):
        data_tables = datatables.DataTables()

        columns = ['library_sections.section_id',
                   'library_sections.section_name',
                   'library_sections.section_type',
                   'library_sections.count as count',
                   'library_sections.parent_count',
                   'library_sections.child_count',
                   'library_sections.thumb AS library_thumb',
                   '(CASE WHEN library_sections.custom_thumb_url == library_sections.thumb \
                    THEN NULL ELSE custom_thumb_url END) AS custom_thumb',
                   'library_sections.art',
                   'COUNT(session_history.id) as plays',
                   'MAX(session_history.started) as last_accessed',
                   'session_history_metadata.full_title as last_watched',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history.rating_key',
                   'session_history_media_info.video_decision',
                   'library_sections.do_notify',
                   'library_sections.keep_history'
                   ]
        try:
            query = data_tables.ssp_query(table_name='library_sections',
                                          columns=columns,
                                          custom_where=[],
                                          group_by=['library_sections.section_id'],
                                          join_types=['LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN'],
                                          join_tables=['session_history_metadata',
                                                       'session_history',
                                                       'session_history_media_info'],
                                          join_evals=[['session_history_metadata.library_id', 'library_sections.section_id'],
                                                      ['session_history_metadata.id', 'session_history.id'],
                                                      ['session_history_metadata.id', 'session_history_media_info.id']],
                                          kwargs=kwargs)
        except:
            logger.warn("Unable to execute database query for get_library_list.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        result = query['result']
        
        rows = []
        for item in result:
            if item['media_type'] == 'episode' and item['parent_thumb']:
                thumb = item['parent_thumb']
            elif item['media_type'] == 'episode':
                thumb = item['grandparent_thumb']
            else:
                thumb = item['thumb']

            row = {'plays': item['plays'],
                   'last_accessed': item['last_accessed'],
                   'last_watched': item['last_watched'],
                   'thumb': thumb,
                   'media_type': item['media_type'],
                   'rating_key': item['rating_key'],
                   'video_decision': item['video_decision'],
                   'section_id': item['section_id'],
                   'section_name': item['section_name'],
                   'section_type': item['section_type'].capitalize(),
                   'count': item['count'],
                   'parent_count': item['parent_count'],
                   'library_thumb': item['library_thumb'],
                   'custom_thumb': item['custom_thumb'],
                   'library_art': item['art'],
                   'child_count': item['child_count'],
                   'do_notify': helpers.checked(item['do_notify']),
                   'keep_history': helpers.checked(item['keep_history'])
                   }

            rows.append(row)
        
        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
        }
        
        return dict

    def set_library_config(self, section_id=None, do_notify=1, keep_history=1, custom_thumb=''):
        if section_id:
            monitor_db = database.MonitorDatabase()

            key_dict = {'section_id': section_id}
            value_dict = {'do_notify': do_notify,
                          'keep_history': keep_history,
                          'custom_thumb_url': custom_thumb}
            try:
                monitor_db.upsert('library_sections', value_dict, key_dict)
            except:
                logger.warn("Unable to execute database query for set_user_friendly_name.")

    def get_library_details(self, section_id=None):
        from plexpy import pmsconnect

        monitor_db = database.MonitorDatabase()

        if section_id:
            query = 'SELECT section_id, section_name, section_type, count, parent_count, child_count, ' \
                    'thumb AS library_thumb, (CASE WHEN library_sections.custom_thumb_url == library_sections.thumb ' \
                    '    THEN NULL ELSE custom_thumb_url END) AS custom_thumb, art, do_notify, keep_history ' \
                    'FROM library_sections ' \
                    'WHERE section_id = ? '
            result = monitor_db.select(query, args=[section_id])
        else:
            result = None

        if result:
            library_details = {}
            for item in result:
                library_details = {'section_id': item['section_id'],
                                   'section_name': item['section_name'],
                                   'section_type': item['section_type'],
                                   'library_thumb': item['library_thumb'],
                                   'custom_thumb': item['custom_thumb'],
                                   'library_art': item['art'],
                                   'count': item['count'],
                                   'parent_count': item['parent_count'],
                                   'child_count': item['child_count'],
                                   'do_notify': item['do_notify'],
                                   'keep_history': item['keep_history']
                                   }
            return library_details
        else:
            logger.warn(u"PlexPy :: Unable to retrieve library from local database. Requesting library list refresh.")
            # Let's first refresh the user list to make sure the user isn't newly added and not in the db yet
            if section_id:
                # Refresh libraries
                pmsconnect.refresh_libraries()
                query = 'SELECT section_id, section_name, section_type, count, parent_count, child_count, ' \
                        'thumb AS library_thumb, (CASE WHEN library_sections.custom_thumb_url == library_sections.thumb ' \
                        '    THEN NULL ELSE custom_thumb_url END) AS custom_thumb, art, do_notify, keep_history ' \
                        'FROM library_sections ' \
                        'WHERE section_id = ? '
                result = monitor_db.select(query, args=[section_id])
            else:
                result = None

            if result:
                library_details = {}
                for item in result:

                    library_details = {'section_id': item['section_id'],
                                       'section_name': item['section_name'],
                                       'section_type': item['section_type'],
                                       'library_thumb': item['library_thumb'],
                                       'custom_thumb': item['custom_thumb'],
                                       'library_art': item['art'],
                                       'count': item['count'],
                                       'parent_count': item['parent_count'],
                                       'child_count': item['child_count'],
                                       'do_notify': item['do_notify'],
                                       'keep_history': item['keep_history']
                                       }
                return user_details
            else:
                # If there is no library data we must return something
                # Use "Local" user to retain compatibility with PlexWatch database value
                return {'section_id': None,
                        'section_name': '',
                        'section_type': '',
                        'library_thumb': '',
                        'custom_thumb': '',
                        'library_art': '',
                        'count': 0,
                        'parent_count': 0,
                        'child_count': 0,
                        'do_notify': 0,
                        'keep_history': 0
                        }

    def get_library_watch_time_stats(self, library_id=None):
        monitor_db = database.MonitorDatabase()

        time_queries = [1, 7, 30, 0]
        library_watch_time_stats = []

        for days in time_queries:
            if days > 0:
                if library_id:
                    query = 'SELECT (SUM(stopped - started) - ' \
                            'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                            'COUNT(session_history.id) AS total_plays ' \
                            'FROM session_history ' \
                            'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                            'AND library_id = ?' % days
                    result = monitor_db.select(query, args=[library_id])
            else:
                query = 'SELECT (SUM(stopped - started) - ' \
                        'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                        'COUNT(session_history.id) AS total_plays ' \
                        'FROM session_history ' \
                        'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                        'WHERE library_id = ?'
                result = monitor_db.select(query, args=[library_id])

            for item in result:
                if item['total_time']:
                    total_time = item['total_time']
                    total_plays = item['total_plays']
                else:
                    total_time = 0
                    total_plays = 0

                row = {'query_days': days,
                       'total_time': total_time,
                       'total_plays': total_plays
                       }

                library_watch_time_stats.append(row)

        return library_watch_time_stats

    def get_library_user_stats(self, library_id=None):
        monitor_db = database.MonitorDatabase()

        user_stats = []

        try:
            if library_id:
                query = 'SELECT (CASE WHEN users.friendly_name IS NULL THEN users.username ' \
                        'ELSE users.friendly_name END) AS user, users.user_id, users.thumb, COUNT(user) AS user_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                        'JOIN users ON users.user_id = session_history.user_id ' \
                        'WHERE library_id = ? ' \
                        'GROUP BY user ' \
                        'ORDER BY user_count DESC'
                result = monitor_db.select(query, args=[library_id])
        except:
            logger.warn("Unable to execute database query for get_library_user_stats.")
            return None
        
        for item in result:
            row = {'user': item['user'],
                   'user_id': item['user_id'],
                   'thumb': item['thumb'],
                   'total_plays': item['user_count']
                   }
            user_stats.append(row)
        
        return user_stats

    def delete_all_library_history(self, section_id=None):
        monitor_db = database.MonitorDatabase()

        if section_id.isdigit():
            logger.info(u"PlexPy Libraries :: Deleting all history for library id %s from database." % section_id)
            session_history_media_info_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history_media_info '
                                  'WHERE session_history_media_info.id IN (SELECT session_history_media_info.id '
                                  'FROM session_history_media_info '
                                  'JOIN session_history_metadata ON session_history_media_info.id = session_history_metadata.id '
                                  'WHERE session_history_metadata.library_id = ?)', [section_id])
            session_history_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history '
                                  'WHERE session_history.id IN (SELECT session_history.id '
                                  'FROM session_history '
                                  'JOIN session_history_metadata ON session_history.id = session_history_metadata.id '
                                  'WHERE session_history_metadata.library_id = ?)', [section_id])
            session_history_metadata_del = \
                monitor_db.action('DELETE FROM '
                                  'session_history_metadata '
                                  'WHERE session_history_metadata.library_id = ?', [section_id])

            return 'Deleted all items for library_id %s.' % section_id
        else:
            return 'Unable to delete items. Input library_id not valid.'