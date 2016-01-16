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
import plexpy


class Libraries(object):

    def __init__(self):
        pass

    def get_datatables_list(self, kwargs=None):
        data_tables = datatables.DataTables()

        custom_where = ['library_sections.deleted_section', 0]

        columns = ['library_sections.section_id',
                   'library_sections.section_name',
                   'library_sections.section_type',
                   'library_sections.count',
                   'library_sections.parent_count',
                   'library_sections.child_count',
                   'library_sections.thumb AS library_thumb',
                   'library_sections.custom_thumb_url AS custom_thumb',
                   'library_sections.art',
                   'COUNT(session_history.id) AS plays',
                   'MAX(session_history.started) AS last_accessed',
                   'session_history_metadata.full_title AS last_watched',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history.rating_key',
                   'session_history_media_info.video_decision',
                   'library_sections.do_notify',
                   'library_sections.do_notify_created',
                   'library_sections.keep_history'
                   ]
        try:
            query = data_tables.ssp_query(table_name='library_sections',
                                          columns=columns,
                                          custom_where=[custom_where],
                                          group_by=['library_sections.section_id'],
                                          join_types=['LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN'],
                                          join_tables=['session_history_metadata',
                                                       'session_history',
                                                       'session_history_media_info'],
                                          join_evals=[['session_history_metadata.section_id', 'library_sections.section_id'],
                                                      ['session_history_metadata.id', 'session_history.id'],
                                                      ['session_history_metadata.id', 'session_history_media_info.id']],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_list: %s." % e)
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

            if item['custom_thumb'] and item['custom_thumb'] != item['library_thumb']:
                library_thumb = item['custom_thumb']
            elif item['library_thumb']:
                library_thumb = item['library_thumb']
            else:
                library_thumb = common.DEFAULT_COVER_THUMB

            row = {'section_id': item['section_id'],
                   'section_name': item['section_name'],
                   'section_type': item['section_type'].capitalize(),
                   'count': item['count'],
                   'parent_count': item['parent_count'],
                   'child_count': item['child_count'],
                   'library_thumb': library_thumb,
                   'library_art': item['art'],
                   'plays': item['plays'],
                   'last_accessed': item['last_accessed'],
                   'last_watched': item['last_watched'],
                   'thumb': thumb,
                   'media_type': item['media_type'],
                   'rating_key': item['rating_key'],
                   'video_decision': item['video_decision'],
                   'do_notify': helpers.checked(item['do_notify']),
                   'do_notify_created': helpers.checked(item['do_notify_created']),
                   'keep_history': helpers.checked(item['keep_history'])
                   }

            rows.append(row)
        
        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }
        
        return dict

    def get_datatables_media_info(self, section_id=None, section_type=None, rating_key=None, kwargs=None):
        from plexpy import pmsconnect
        import json, os

        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': None,
                          'error': 'Unable to execute database query.'}

        if section_id and not str(section_id).isdigit():
            logger.warn(u"PlexPy Libraries :: Datatable media info called by invalid section_id provided.")
            return default_return
        elif rating_key and not str(rating_key).isdigit():
            logger.warn(u"PlexPy Libraries :: Datatable media info called by invalid rating_key provided.")
            return default_return

        rows = []
        if rating_key:
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info-%s_%s.json' % (section_id, rating_key))
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
                    library_count = len(rows)
            except IOError as e:
                #logger.debug(u"PlexPy Libraries :: No JSON file for rating_key %s." % rating_key)
                #logger.debug(u"PlexPy Libraries :: Refreshing data and creating new JSON file for rating_key %s." % rating_key)
                pass
        elif section_id:
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info-%s.json' % section_id)
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
                    library_count = len(rows)
            except IOError as e:
                #logger.debug(u"PlexPy Libraries :: No JSON file for library section_id %s." % section_id)
                #logger.debug(u"PlexPy Libraries :: Refreshing data and creating new JSON file for section_id %s." % section_id)
                pass

        if not rows:
            # Get the library details
            library_details = self.get_details(section_id=section_id)
            if library_details['section_id'] == None:
                logger.warn(u"PlexPy Libraries :: Library section_id %s not found." % section_id)
                return default_return

            if not section_type:
                section_type = library_details['section_type']

            # Get play counts from the database
            monitor_db = database.MonitorDatabase()

            if section_type == 'show' or section_type == 'artist':
                group_by = 'grandparent_rating_key'
            elif section_type == 'season' or section_type == 'album':
                group_by = 'parent_rating_key'
            else:
                group_by = 'rating_key'

            try:
                query = 'SELECT MAX(session_history.started) AS last_watched, COUNT(session_history.id) AS play_count, ' \
                        'session_history.rating_key, session_history.parent_rating_key, session_history.grandparent_rating_key ' \
                        'FROM session_history ' \
                        'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                        'WHERE session_history_metadata.section_id = ? ' \
                        'GROUP BY session_history.%s ' % group_by
                result = monitor_db.select(query, args=[section_id])
            except Exception as e:
                logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_datatables_media_info2: %s." % e)
                return default_return

            watched_list = {}
            for item in result:
                watched_list[str(item[group_by])] = {'last_watched': item['last_watched'],
                                                     'play_count': item['play_count']}

            # Get all library children items
            pms_connect = pmsconnect.PmsConnect()


            if rating_key:
                library_children = pms_connect.get_library_children(rating_key=rating_key,
                                                                    get_media_info=True)
            elif section_id:
                library_children = pms_connect.get_library_children(section_id=section_id,
                                                                    section_type=section_type,
                                                                    get_media_info=True)

            if library_children:
                library_count = library_children['library_count']
                children_list = library_children['childern_list']
            else:
                logger.warn(u"PlexPy Libraries :: Unable to get a list of library items.")
                return default_return
        
            rows = []
            for item in children_list:
                watched_item = watched_list.get(item['rating_key'], None)
                if watched_item:
                    last_watched = watched_item['last_watched']
                    play_count = watched_item['play_count']
                else:
                    last_watched = None
                    play_count = None

                row = {'section_id': library_details['section_id'],
                       'section_type': library_details['section_type'],
                       'added_at': item['added_at'],
                       'media_type': item['media_type'],
                       'rating_key': item['rating_key'],
                       'parent_rating_key': item['parent_rating_key'],
                       'grandparent_rating_key': item['grandparent_rating_key'],
                       'title': item['title'],
                       'year': item['year'],
                       'media_index': item['media_index'],
                       'parent_media_index': item['parent_media_index'],
                       'thumb': item['thumb'],
                       'container': item.get('container', ''),
                       'bitrate': item.get('bitrate', ''),
                       'video_codec': item.get('video_codec', ''),
                       'video_resolution': item.get('video_resolution', ''),
                       'video_framerate': item.get('video_framerate', ''),
                       'audio_codec': item.get('audio_codec', ''),
                       'audio_channels': item.get('audio_channels', ''),
                       'file_size': item.get('file_size', ''),
                       'last_watched': last_watched,
                       'play_count': play_count
                       }
                rows.append(row)

            if not rows:
                return default_return

            if rating_key:
                outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info-%s_%s.json' % (section_id, rating_key))
                with open(outFilePath, 'w') as outFile:
                    json.dump(rows, outFile)
            elif section_id:
                outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info-%s.json' % section_id)
                with open(outFilePath, 'w') as outFile:
                    json.dump(rows, outFile)
        
        results = []
        
        # Get datatables JSON data            
        if kwargs.get('json_data'):
            json_data = helpers.process_json_kwargs(json_kwargs=kwargs.get('json_data'))
            #print json_data

        # Search results
        search_value = json_data['search']['value'].lower()
        if search_value:
            searchable_columns = [d['data'] for d in json_data['columns'] if d['searchable']]
            for k,v in [row.iteritems() for row in rows]:
                if k in searchable_columns and search_value in v.lower():
                    results.append(row)
                    break
        else:
            results = rows

        filtered_count = len(results)

        # Sort results
        results = sorted(results, key=lambda k: k['title'])
        sort_order = json_data['order']
        for order in reversed(sort_order):
            sort_key = json_data['columns'][int(order['column'])]['data']
            reverse = True if order['dir'] == 'desc' else False
            if rating_key and sort_key == 'title':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k['media_index']), reverse=reverse)
            elif sort_key == 'file_size' or sort_key == 'bitrate':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k[sort_key]), reverse=reverse)
            else:
                results = sorted(results, key=lambda k: k[sort_key], reverse=reverse)

        # Paginate results
        results = results[json_data['start']:(json_data['start'] + json_data['length'])]

        ## Find some way to add total disk space used?

        dict = {'recordsFiltered': filtered_count,
                'recordsTotal': library_count,
                'data': results,
                'draw': int(json_data['draw'])
                }
        
        return dict

    def set_config(self, section_id=None, custom_thumb='', do_notify=1, keep_history=1, do_notify_created=1):
        if section_id:
            monitor_db = database.MonitorDatabase()

            key_dict = {'section_id': section_id}
            value_dict = {'custom_thumb_url': custom_thumb,
                          'do_notify': do_notify,
                          'do_notify_created': do_notify_created,
                          'keep_history': keep_history}
            try:
                monitor_db.upsert('library_sections', value_dict, key_dict)
            except:
                logger.warn(u"PlexPy Libraries :: Unable to execute database query for set_config: %s." % e)

    def get_details(self, section_id=None):
        from plexpy import pmsconnect

        monitor_db = database.MonitorDatabase()

        try:
            if section_id:
                query = 'SELECT section_id, section_name, section_type, count, parent_count, child_count, ' \
                        'thumb AS library_thumb, custom_thumb_url AS custom_thumb, art, ' \
                        'do_notify, do_notify_created, keep_history ' \
                        'FROM library_sections ' \
                        'WHERE section_id = ? '
                result = monitor_db.select(query, args=[section_id])
            else:
                result = []
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_details: %s." % e)
            result = []

        if result:
            library_details = {}
            for item in result:
                if item['custom_thumb'] and item['custom_thumb'] != item['library_thumb']:
                    library_thumb = item['custom_thumb']
                elif item['library_thumb']:
                    library_thumb = item['library_thumb']
                else:
                    library_thumb = common.DEFAULT_COVER_THUMB

                library_details = {'section_id': item['section_id'],
                                   'section_name': item['section_name'],
                                   'section_type': item['section_type'],
                                   'library_thumb': library_thumb,
                                   'library_art': item['art'],
                                   'count': item['count'],
                                   'parent_count': item['parent_count'],
                                   'child_count': item['child_count'],
                                   'do_notify': item['do_notify'],
                                   'do_notify_created': item['do_notify_created'],
                                   'keep_history': item['keep_history']
                                   }
            return library_details
        else:
            logger.warn(u"PlexPy Libraries :: Unable to retrieve library from local database. Requesting library list refresh.")
            # Let's first refresh the user list to make sure the user isn't newly added and not in the db yet
            try:
                if section_id:
                    # Refresh libraries
                    pmsconnect.refresh_libraries()
                    query = 'SELECT section_id, section_name, section_type, count, parent_count, child_count, ' \
                            'thumb AS library_thumb, custom_thumb_url AS custom_thumb, art, ' \
                            'do_notify, do_notify_created, keep_history ' \
                            'FROM library_sections ' \
                            'WHERE section_id = ? '
                    result = monitor_db.select(query, args=[section_id])
                else:
                    result = []
            except:
                logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_details: %s." % e)
                result = []

            if result:
                library_details = {}
                for item in result:
                    if item['custom_thumb'] and item['custom_thumb'] != item['library_thumb']:
                        library_thumb = item['custom_thumb']
                    elif item['library_thumb']:
                        library_thumb = item['library_thumb']
                    else:
                        library_thumb = common.DEFAULT_COVER_THUMB

                    library_details = {'section_id': item['section_id'],
                                       'section_name': item['section_name'],
                                       'section_type': item['section_type'],
                                       'library_thumb': library_thumb,
                                       'library_art': item['art'],
                                       'count': item['count'],
                                       'parent_count': item['parent_count'],
                                       'child_count': item['child_count'],
                                       'do_notify': item['do_notify'],
                                       'do_notify_created': item['do_notify_created'],
                                       'keep_history': item['keep_history']
                                       }
                return library_details
            else:
                # If there is no library data we must return something
                # Use "Local" user to retain compatibility with PlexWatch database value
                return {'section_id': None,
                        'section_name': 'Local',
                        'section_type': '',
                        'library_thumb': common.DEFAULT_COVER_THUMB,
                        'library_art': '',
                        'count': 0,
                        'parent_count': 0,
                        'child_count': 0,
                        'do_notify': 0,
                        'do_notify_created': 0,
                        'keep_history': 0
                        }

    def get_watch_time_stats(self, section_id=None):
        monitor_db = database.MonitorDatabase()

        time_queries = [1, 7, 30, 0]
        library_watch_time_stats = []

        for days in time_queries:
            try:
                if days > 0:
                    if str(section_id).isdigit():
                        query = 'SELECT (SUM(stopped - started) - ' \
                                'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                                'COUNT(session_history.id) AS total_plays ' \
                                'FROM session_history ' \
                                'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                                'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                                'AND section_id = ?' % days
                        result = monitor_db.select(query, args=[section_id])
                    else:
                        result = []
                else:
                    if str(section_id).isdigit():
                        query = 'SELECT (SUM(stopped - started) - ' \
                                'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                                'COUNT(session_history.id) AS total_plays ' \
                                'FROM session_history ' \
                                'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                                'WHERE section_id = ?'
                        result = monitor_db.select(query, args=[section_id])
                    else:
                        result = []
            except Exception as e:
                logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_watch_time_stats: %s." % e)
                result = []

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

    def get_user_stats(self, section_id=None):
        monitor_db = database.MonitorDatabase()

        user_stats = []

        try:
            if str(section_id).isdigit():
                query = 'SELECT (CASE WHEN users.friendly_name IS NULL THEN users.username ' \
                        'ELSE users.friendly_name END) AS user, users.user_id, users.thumb, COUNT(user) AS user_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                        'JOIN users ON users.user_id = session_history.user_id ' \
                        'WHERE section_id = ? ' \
                        'GROUP BY user ' \
                        'ORDER BY user_count DESC'
                result = monitor_db.select(query, args=[section_id])
            else:
                result = []
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_user_stats: %s." % e)
            result = []
        
        for item in result:
            row = {'user': item['user'],
                   'user_id': item['user_id'],
                   'thumb': item['thumb'],
                   'total_plays': item['user_count']
                   }
            user_stats.append(row)
        
        return user_stats

    def get_recently_watched(self, section_id=None, limit='10'):
        monitor_db = database.MonitorDatabase()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if str(section_id).isdigit():
                query = 'SELECT session_history.id, session_history.media_type, session_history.rating_key, session_history.parent_rating_key, ' \
                        'title, parent_title, grandparent_title, thumb, parent_thumb, grandparent_thumb, media_index, parent_media_index, ' \
                        'year, started, user ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'WHERE section_id = ? ' \
                        'GROUP BY (CASE WHEN session_history.media_type = "track" THEN session_history.parent_rating_key ' \
                        '   ELSE session_history.rating_key END) ' \
                        'ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[section_id, limit])
            else:
                result = []
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_recently_watched: %s." % e)
            result = []

        for row in result:
                if row['media_type'] == 'episode' and row['parent_thumb']:
                    thumb = row['parent_thumb']
                elif row['media_type'] == 'episode':
                    thumb = row['grandparent_thumb']
                else:
                    thumb = row['thumb']

                recent_output = {'row_id': row['id'],
                                 'media_type': row['media_type'],
                                 'rating_key': row['rating_key'],
                                 'title': row['title'],
                                 'parent_title': row['parent_title'],
                                 'grandparent_title': row['grandparent_title'],
                                 'thumb': thumb,
                                 'media_index': row['media_index'],
                                 'parent_media_index': row['parent_media_index'],
                                 'year': row['year'],
                                 'time': row['started'],
                                 'user': row['user']
                                 }
                recently_watched.append(recent_output)

        return recently_watched

    def get_sections(self):
        monitor_db = database.MonitorDatabase()

        try:
            query = 'SELECT section_id, section_name FROM library_sections WHERE deleted_section = 0'
            result = monitor_db.select(query=query)
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for get_sections: %s." % e)
            return None

        libraries = []
        for item in result:
            library = {'section_id': item['section_id'],
                       'section_name': item['section_name']
                       }
            libraries.append(library)

        return libraries

    def delete_all_history(self, section_id=None):
        monitor_db = database.MonitorDatabase()

        try:
            if section_id.isdigit():
                logger.info(u"PlexPy Libraries :: Deleting all history for library id %s from database." % section_id)
                session_history_media_info_del = \
                    monitor_db.action('DELETE FROM '
                                      'session_history_media_info '
                                      'WHERE session_history_media_info.id IN (SELECT session_history_media_info.id '
                                      'FROM session_history_media_info '
                                      'JOIN session_history_metadata ON session_history_media_info.id = session_history_metadata.id '
                                      'WHERE session_history_metadata.section_id = ?)', [section_id])
                session_history_del = \
                    monitor_db.action('DELETE FROM '
                                      'session_history '
                                      'WHERE session_history.id IN (SELECT session_history.id '
                                      'FROM session_history '
                                      'JOIN session_history_metadata ON session_history.id = session_history_metadata.id '
                                      'WHERE session_history_metadata.section_id = ?)', [section_id])
                session_history_metadata_del = \
                    monitor_db.action('DELETE FROM '
                                      'session_history_metadata '
                                      'WHERE session_history_metadata.section_id = ?', [section_id])

                return 'Deleted all items for section_id %s.' % section_id
            else:
                return 'Unable to delete items, section_id not valid.'
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for delete_all_history: %s." % e)

    def delete(self, section_id=None):
        monitor_db = database.MonitorDatabase()

        try:
            if section_id.isdigit():
                self.delete_all_history(section_id)
                logger.info(u"PlexPy Libraries :: Deleting library with id %s from database." % section_id)
                monitor_db.action('UPDATE library_sections SET deleted_section = 1 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET keep_history = 0 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET do_notify = 0 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET do_notify_created = 0 WHERE section_id = ?', [section_id])

                library_cards = plexpy.CONFIG.HOME_LIBRARY_CARDS
                if section_id in library_cards:
                    library_cards.remove(section_id)
                    plexpy.CONFIG.__setattr__('HOME_LIBRARY_CARDS', library_cards)
                    plexpy.CONFIG.write()

                return 'Deleted library with id %s.' % section_id
            else:
                return 'Unable to delete library, section_id not valid.'
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for delete: %s." % e)

    def undelete(self, section_id=None, section_name=None):
        monitor_db = database.MonitorDatabase()

        try:
            if section_id and section_id.isdigit():
                logger.info(u"PlexPy Libraries :: Re-adding library with id %s to database." % section_id)
                monitor_db.action('UPDATE library_sections SET deleted_section = 0 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET keep_history = 1 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET do_notify = 1 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET do_notify_created = 1 WHERE section_id = ?', [section_id])

                return 'Re-added library with id %s.' % section_id
            elif section_name:
                logger.info(u"PlexPy Libraries :: Re-adding library with name %s to database." % section_name)
                monitor_db.action('UPDATE library_sections SET deleted_section = 0 WHERE section_name = ?', [section_name])
                monitor_db.action('UPDATE library_sections SET keep_history = 1 WHERE section_name = ?', [section_name])
                monitor_db.action('UPDATE library_sections SET do_notify = 1 WHERE section_name = ?', [section_name])
                monitor_db.action('UPDATE library_sections SET do_notify_created = 1 WHERE section_name = ?', [section_name])

                return 'Re-added library with section_name %s.' % section_name
            else:
                return 'Unable to re-add library, section_id or section_name not valid.'
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for undelete: %s." % e)

    def update_section_ids(self):
        from plexpy import pmsconnect

        pms_connect = pmsconnect.PmsConnect()
        monitor_db = database.MonitorDatabase()

        try:
            query = 'SELECT id, rating_key FROM session_history_metadata WHERE section_id IS NULL'
            result = monitor_db.select(query=query)
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to execute database query for update_section_ids: %s." % e)
            return None

        for item in result:
            id = item['id']
            rating_key = item['rating_key']

            result = pms_connect.get_metadata_details(rating_key=rating_key)

            if result:
                metadata = result['metadata']

                section_keys = {'id': id}
                section_values = {'section_id': metadata['section_id']}

                monitor_db.upsert('session_history_metadata', key_dict=section_keys, value_dict=section_values)
            else:
                continue

        return True

    def delete_datatable_media_info_cache(self, section_id=None):
        import os

        try:
            if section_id.isdigit():
                [os.remove(os.path.join(plexpy.CONFIG.CACHE_DIR, f)) for f in os.listdir(plexpy.CONFIG.CACHE_DIR) 
                 if f.startswith('media_info-%s' % section_id) and f.endswith('.json')]

                logger.debug(u"PlexPy Libraries :: Deleted media info table cache for section_id %s." % section_id)
                return 'Deleted media info table cache for library with id %s.' % section_id
            else:
                return 'Unable to delete media info table cache, section_id not valid.'
        except Exception as e:
            logger.warn(u"PlexPy Libraries :: Unable to delete media info table cache: %s." % e)