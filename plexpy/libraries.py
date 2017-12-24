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

import json
import os

import plexpy
import common
import database
import datatables
import helpers
import logger
import plextv
import pmsconnect
import session


def refresh_libraries():
    logger.info(u"Tautulli Libraries :: Requesting libraries list refresh...")

    server_id = plexpy.CONFIG.PMS_IDENTIFIER
    if not server_id:
        logger.error(u"Tautulli Libraries :: No PMS identifier, cannot refresh libraries. Verify server in settings.")
        return

    library_sections = pmsconnect.PmsConnect().get_library_details()

    if library_sections:
        monitor_db = database.MonitorDatabase()

        library_keys = []
        new_keys = []

        for section in library_sections:
            section_keys = {'server_id': server_id,
                            'section_id': section['section_id']}
            section_values = {'server_id': server_id,
                              'section_id': section['section_id'],
                              'section_name': section['section_name'],
                              'section_type': section['section_type'],
                              'thumb': section['thumb'],
                              'art': section['art'],
                              'count': section['count'],
                              'parent_count': section.get('parent_count', None),
                              'child_count': section.get('child_count', None),
                              }

            result = monitor_db.upsert('library_sections', key_dict=section_keys, value_dict=section_values)

            library_keys.append(section['section_id'])

            if result == 'insert':
                new_keys.append(section['section_id'])

        if plexpy.CONFIG.HOME_LIBRARY_CARDS == ['first_run_wizard']:
            plexpy.CONFIG.__setattr__('HOME_LIBRARY_CARDS', library_keys)
            plexpy.CONFIG.write()
        else:
            new_keys = plexpy.CONFIG.HOME_LIBRARY_CARDS + new_keys
            plexpy.CONFIG.__setattr__('HOME_LIBRARY_CARDS', new_keys)
            plexpy.CONFIG.write()

        #if plexpy.CONFIG.UPDATE_SECTION_IDS == 1 or plexpy.CONFIG.UPDATE_SECTION_IDS == -1:
        #    # Start library section_id update on it's own thread
        #    threading.Thread(target=libraries.update_section_ids).start()

        #if plexpy.CONFIG.UPDATE_LABELS == 1 or plexpy.CONFIG.UPDATE_LABELS == -1:
        #    # Start library labels update on it's own thread
        #    threading.Thread(target=libraries.update_labels).start()

        logger.info(u"Tautulli Libraries :: Libraries list refreshed.")
        return True
    else:
        logger.warn(u"Tautulli Libraries :: Unable to refresh libraries list.")
        return False


def update_section_ids():
    plexpy.CONFIG.UPDATE_SECTION_IDS = -1

    monitor_db = database.MonitorDatabase()

    try:
        query = 'SELECT id, rating_key, grandparent_rating_key, media_type ' \
                'FROM session_history_metadata WHERE section_id IS NULL'
        history_results = monitor_db.select(query=query)
        query = 'SELECT section_id, section_type FROM library_sections'
        library_results = monitor_db.select(query=query)
    except Exception as e:
        logger.warn(u"Tautulli Libraries :: Unable to execute database query for update_section_ids: %s." % e)

        logger.warn(u"Tautulli Libraries :: Unable to update section_id's in database.")
        plexpy.CONFIG.UPDATE_SECTION_IDS = 1
        plexpy.CONFIG.write()
        return None

    if not history_results:
        plexpy.CONFIG.UPDATE_SECTION_IDS = 0
        plexpy.CONFIG.write()
        return None

    logger.debug(u"Tautulli Libraries :: Updating section_id's in database.")

    # Get rating_key: section_id mapping pairs
    key_mappings = {}

    pms_connect = pmsconnect.PmsConnect()
    for library in library_results:
        section_id = library['section_id']
        section_type = library['section_type']
        
        if section_type != 'photo':
            library_children = pms_connect.get_library_children_details(section_id=section_id,
                                                                        section_type=section_type)
            if library_children:
                children_list = library_children['childern_list']
                key_mappings.update({child['rating_key']:child['section_id'] for child in children_list})
            else:
                logger.warn(u"Tautulli Libraries :: Unable to get a list of library items for section_id %s." % section_id)

    error_keys = set()
    for item in history_results:
        rating_key = item['grandparent_rating_key'] if item['media_type'] != 'movie' else item['rating_key']
        section_id = key_mappings.get(str(rating_key), None)
        
        if section_id:
            try:
                section_keys = {'id': item['id']}
                section_values = {'section_id': section_id}
                monitor_db.upsert('session_history_metadata', key_dict=section_keys, value_dict=section_values)
            except:
                error_keys.add(item['rating_key'])
        else:
            error_keys.add(item['rating_key'])

    if error_keys:
        logger.info(u"Tautulli Libraries :: Updated all section_id's in database except for rating_keys: %s." %
                     ', '.join(str(key) for key in error_keys))
    else:
        logger.info(u"Tautulli Libraries :: Updated all section_id's in database.")

    plexpy.CONFIG.UPDATE_SECTION_IDS = 0
    plexpy.CONFIG.write()

    return True

def update_labels():
    plexpy.CONFIG.UPDATE_LABELS = -1

    monitor_db = database.MonitorDatabase()

    try:
        query = 'SELECT section_id, section_type FROM library_sections'
        library_results = monitor_db.select(query=query)
    except Exception as e:
        logger.warn(u"Tautulli Libraries :: Unable to execute database query for update_labels: %s." % e)

        logger.warn(u"Tautulli Libraries :: Unable to update labels in database.")
        plexpy.CONFIG.UPDATE_LABELS = 1
        plexpy.CONFIG.write()
        return None

    if not library_results:
        plexpy.CONFIG.UPDATE_LABELS = 0
        plexpy.CONFIG.write()
        return None

    logger.debug(u"Tautulli Libraries :: Updating labels in database.")

    # Get rating_key: section_id mapping pairs
    key_mappings = {}

    pms_connect = pmsconnect.PmsConnect()
    for library in library_results:
        section_id = library['section_id']
        section_type = library['section_type']
        
        if section_type != 'photo':
            library_children = []
            library_labels = pms_connect.get_library_label_details(section_id=section_id)

            if library_labels:
                for label in library_labels:
                    library_children = pms_connect.get_library_children_details(section_id=section_id,
                                                                                section_type=section_type,
                                                                                label_key=label['label_key'])

                    if library_children:
                        children_list = library_children['childern_list']
                        # rating_key_list = [child['rating_key'] for child in children_list]

                        for rating_key in [child['rating_key'] for child in children_list]:
                            if key_mappings.get(rating_key):
                                key_mappings[rating_key].append(label['label_title'])
                            else:
                                key_mappings[rating_key] = [label['label_title']]

                    else:
                        logger.warn(u"Tautulli Libraries :: Unable to get a list of library items for section_id %s."
                                    % section_id)

    error_keys = set()
    for rating_key, labels in key_mappings.iteritems():
        try:
            labels = ';'.join(labels)
            monitor_db.action('UPDATE session_history_metadata SET labels = ? '
                              'WHERE rating_key = ? OR parent_rating_key = ? OR grandparent_rating_key = ? ',
                              args=[labels, rating_key, rating_key, rating_key])
        except:
            error_keys.add(rating_key)

    if error_keys:
        logger.info(u"Tautulli Libraries :: Updated all labels in database except for rating_keys: %s." %
                     ', '.join(str(key) for key in error_keys))
    else:
        logger.info(u"Tautulli Libraries :: Updated all labels in database.")

    plexpy.CONFIG.UPDATE_LABELS = 0
    plexpy.CONFIG.write()

    return True


class Libraries(object):

    def __init__(self):
        pass

    def get_datatables_list(self, kwargs=None):
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': 'null',
                          'error': 'Unable to execute database query.'}

        data_tables = datatables.DataTables()

        custom_where = [['library_sections.deleted_section', 0]]

        if session.get_session_shared_libraries():
            custom_where.append(['library_sections.section_id', session.get_session_shared_libraries()])

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
                   'SUM(CASE WHEN session_history.stopped > 0 THEN (session_history.stopped - session_history.started) \
                    ELSE 0 END) - SUM(CASE WHEN session_history.paused_counter IS NULL THEN 0 ELSE \
                    session_history.paused_counter END) AS duration',
                   'MAX(session_history.started) AS last_accessed',
                   'MAX(session_history.id) AS id',
                   'session_history_metadata.full_title AS last_played',
                   'session_history.rating_key',
                   'session_history_metadata.media_type',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.parent_title',
                   'session_history_metadata.year',
                   'session_history_metadata.media_index',
                   'session_history_metadata.parent_media_index',
                   'session_history_metadata.content_rating',
                   'session_history_metadata.labels',
                   'library_sections.do_notify',
                   'library_sections.do_notify_created',
                   'library_sections.keep_history'
                   ]
        try:
            query = data_tables.ssp_query(table_name='library_sections',
                                          columns=columns,
                                          custom_where=custom_where,
                                          group_by=['library_sections.server_id', 'library_sections.section_id'],
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
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_list: %s." % e)
            return default_return

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
                   'section_type': item['section_type'],
                   'count': item['count'],
                   'parent_count': item['parent_count'],
                   'child_count': item['child_count'],
                   'library_thumb': library_thumb,
                   'library_art': item['art'],
                   'plays': item['plays'],
                   'duration': item['duration'],
                   'last_accessed': item['last_accessed'],
                   'id': item['id'],
                   'last_played': item['last_played'],
                   'rating_key': item['rating_key'],
                   'media_type': item['media_type'],
                   'thumb': thumb,
                   'parent_title': item['parent_title'],
                   'year': item['year'],
                   'media_index': item['media_index'],
                   'parent_media_index': item['parent_media_index'],
                   'content_rating': item['content_rating'],
                   'labels': item['labels'].split(';') if item['labels'] else (),
                   'do_notify': helpers.checked(item['do_notify']),
                   'do_notify_created': helpers.checked(item['do_notify_created']),
                   'keep_history': helpers.checked(item['keep_history'])
                   }

            rows.append(row)
        
        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': session.mask_session_info(rows),
                'draw': query['draw']
                }
        
        return dict

    def get_datatables_media_info(self, section_id=None, section_type=None, rating_key=None, refresh=False, kwargs=None):
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': 'null',
                          'error': 'Unable to execute database query.'}

        if not session.allow_session_library(section_id):
            return default_return
        
        if section_id and not str(section_id).isdigit():
            logger.warn(u"Tautulli Libraries :: Datatable media info called but invalid section_id provided.")
            return default_return
        elif rating_key and not str(rating_key).isdigit():
            logger.warn(u"Tautulli Libraries :: Datatable media info called but invalid rating_key provided.")
            return default_return
        elif not section_id and not rating_key:
            logger.warn(u"Tautulli Libraries :: Datatable media info called but no input provided.")
            return default_return

        # Get the library details
        library_details = self.get_details(section_id=section_id)
        if library_details['section_id'] == None:
            logger.debug(u"Tautulli Libraries :: Library section_id %s not found." % section_id)
            return default_return

        if not section_type:
            section_type = library_details['section_type']

        # Get play counts from the database
        monitor_db = database.MonitorDatabase()

        if plexpy.CONFIG.GROUP_HISTORY_TABLES:
            count_by = 'reference_id'
        else:
            count_by = 'id'

        if section_type == 'show' or section_type == 'artist':
            group_by = 'grandparent_rating_key'
        elif section_type == 'season' or section_type == 'album':
            group_by = 'parent_rating_key'
        else:
            group_by = 'rating_key'

        try:
            query = 'SELECT MAX(session_history.started) AS last_played, COUNT(DISTINCT session_history.%s) AS play_count, ' \
                    'session_history.rating_key, session_history.parent_rating_key, session_history.grandparent_rating_key ' \
                    'FROM session_history ' \
                    'JOIN session_history_metadata ON session_history.id = session_history_metadata.id ' \
                    'WHERE session_history_metadata.section_id = ? ' \
                    'GROUP BY session_history.%s ' % (count_by, group_by)
            result = monitor_db.select(query, args=[section_id])
        except Exception as e:
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_datatables_media_info2: %s." % e)
            return default_return

        watched_list = {}
        for item in result:
            watched_list[str(item[group_by])] = {'last_played': item['last_played'],
                                                 'play_count': item['play_count']}

        rows = []
        # Import media info cache from json file
        if rating_key:
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s-%s.json' % (section_id, rating_key))
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
                    library_count = len(rows)
            except IOError as e:
                #logger.debug(u"Tautulli Libraries :: No JSON file for rating_key %s." % rating_key)
                #logger.debug(u"Tautulli Libraries :: Refreshing data and creating new JSON file for rating_key %s." % rating_key)
                pass
        elif section_id:
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
                    library_count = len(rows)
            except IOError as e:
                #logger.debug(u"Tautulli Libraries :: No JSON file for library section_id %s." % section_id)
                #logger.debug(u"Tautulli Libraries :: Refreshing data and creating new JSON file for section_id %s." % section_id)
                pass

        # If no cache was imported, get all library children items
        cached_items = {d['rating_key']: d['file_size'] for d in rows} if not refresh else {}

        if refresh or not rows:
            pms_connect = pmsconnect.PmsConnect()

            if rating_key:
                library_children = pms_connect.get_library_children_details(rating_key=rating_key,
                                                                            get_media_info=True)
            elif section_id:
                library_children = pms_connect.get_library_children_details(section_id=section_id,
                                                                            section_type=section_type,
                                                                            get_media_info=True)
            if library_children:
                library_count = library_children['library_count']
                children_list = library_children['childern_list']
            else:
                logger.warn(u"Tautulli Libraries :: Unable to get a list of library items.")
                return default_return
            
            new_rows = []
            for item in children_list:
                ## TODO: Check list of media info items, currently only grabs first item

                cached_file_size = cached_items.get(item['rating_key'], None)
                file_size = cached_file_size if cached_file_size else item.get('file_size', '')

                row = {'section_id': library_details['section_id'],
                       'section_type': library_details['section_type'],
                       'added_at': item['added_at'],
                       'media_type': item['media_type'],
                       'rating_key': item['rating_key'],
                       'parent_rating_key': item['parent_rating_key'],
                       'grandparent_rating_key': item['grandparent_rating_key'],
                       'title': item['title'],
                       'sort_title': item['sort_title'] or item['title'],
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
                       'file_size': file_size
                       }
                new_rows.append(row)

            rows = new_rows
            if not rows:
                return default_return

            # Cache the media info to a json file
            if rating_key:
                try:
                    outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s-%s.json' % (section_id, rating_key))
                    with open(outFilePath, 'w') as outFile:
                        json.dump(rows, outFile)
                except IOError as e:
                    logger.debug(u"Tautulli Libraries :: Unable to create cache file for rating_key %s." % rating_key)
            elif section_id:
                try:
                    outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                    with open(outFilePath, 'w') as outFile:
                        json.dump(rows, outFile)
                except IOError as e:
                    logger.debug(u"Tautulli Libraries :: Unable to create cache file for section_id %s." % section_id)

        # Update the last_played and play_count
        for item in rows:
            watched_item = watched_list.get(item['rating_key'], None)
            if watched_item:
                item['last_played'] = watched_item['last_played']
                item['play_count'] = watched_item['play_count']
            else:
                item['last_played'] = None
                item['play_count'] = None

        results = []
        
        # Get datatables JSON data            
        if kwargs.get('json_data'):
            json_data = helpers.process_json_kwargs(json_kwargs=kwargs.get('json_data'))
            #print json_data

        # Search results
        search_value = json_data['search']['value'].lower()
        if search_value:
            searchable_columns = [d['data'] for d in json_data['columns'] if d['searchable']]
            for row in rows:
                for k,v in row.iteritems():
                    if k in searchable_columns and search_value in v.lower():
                        results.append(row)
                        break
        else:
            results = rows

        filtered_count = len(results)

        # Sort results
        results = sorted(results, key=lambda k: k['sort_title'])
        sort_order = json_data['order']
        for order in reversed(sort_order):
            sort_key = json_data['columns'][int(order['column'])]['data']
            reverse = True if order['dir'] == 'desc' else False
            if rating_key and sort_key == 'sort_title':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k['media_index']), reverse=reverse)
            elif sort_key == 'file_size' or sort_key == 'bitrate':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k[sort_key]), reverse=reverse)
            elif sort_key == 'video_resolution':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k[sort_key].replace('4k', '2160p').rstrip('p')), reverse=reverse)
            else:
                results = sorted(results, key=lambda k: k[sort_key], reverse=reverse)

        total_file_size = sum([helpers.cast_to_int(d['file_size']) for d in results])

        # Paginate results
        results = results[json_data['start']:(json_data['start'] + json_data['length'])]

        filtered_file_size = sum([helpers.cast_to_int(d['file_size']) for d in results])

        dict = {'recordsFiltered': filtered_count,
                'recordsTotal': library_count,
                'data': results,
                'draw': int(json_data['draw']),
                'filtered_file_size': filtered_file_size,
                'total_file_size': total_file_size
                }
        
        return dict

    def get_media_info_file_sizes(self, section_id=None, rating_key=None):
        if not session.allow_session_library(section_id):
            return False
        
        if section_id and not str(section_id).isdigit():
            logger.warn(u"Tautulli Libraries :: Datatable media info file size called but invalid section_id provided.")
            return False
        elif rating_key and not str(rating_key).isdigit():
            logger.warn(u"Tautulli Libraries :: Datatable media info file size called but invalid rating_key provided.")
            return False

        # Get the library details
        library_details = self.get_details(section_id=section_id)
        if library_details['section_id'] == None:
            logger.debug(u"Tautulli Libraries :: Library section_id %s not found." % section_id)
            return False
        if library_details['section_type'] == 'photo':
            return False

        rows = []
        # Import media info cache from json file
        if rating_key:
            #logger.debug(u"Tautulli Libraries :: Getting file sizes for rating_key %s." % rating_key)
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s-%s.json' % (section_id, rating_key))
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
            except IOError as e:
                #logger.debug(u"Tautulli Libraries :: No JSON file for rating_key %s." % rating_key)
                #logger.debug(u"Tautulli Libraries :: Refreshing data and creating new JSON file for rating_key %s." % rating_key)
                pass
        elif section_id:
            logger.debug(u"Tautulli Libraries :: Getting file sizes for section_id %s." % section_id)
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
            except IOError as e:
                #logger.debug(u"Tautulli Libraries :: No JSON file for library section_id %s." % section_id)
                #logger.debug(u"Tautulli Libraries :: Refreshing data and creating new JSON file for section_id %s." % section_id)
                pass

        # Get the total file size for each item
        pms_connect = pmsconnect.PmsConnect()

        for item in rows:
            if item['rating_key'] and not item['file_size']:
                file_size = 0
            
                metadata = pms_connect.get_metadata_children_details(rating_key=item['rating_key'],
                                                                     get_children=True)

                for child_metadata in metadata:
                    ## TODO: Check list of media info items, currently only grabs first item
                    media_info = media_part_info = {}
                    if 'media_info' in child_metadata and len(child_metadata['media_info']) > 0:
                        media_info = child_metadata['media_info'][0]
                        if 'parts' in media_info and len (media_info['parts']) > 0:
                            media_part_info = media_info['parts'][0]

                    file_size += helpers.cast_to_int(media_part_info.get('file_size', 0))

                item['file_size'] = file_size

        # Cache the media info to a json file
        if rating_key:
            try:
                outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s-%s.json' % (section_id, rating_key))
                with open(outFilePath, 'w') as outFile:
                    json.dump(rows, outFile)
            except IOError as e:
                logger.debug(u"Tautulli Libraries :: Unable to create cache file with file sizes for rating_key %s." % rating_key)
        elif section_id:
            try:
                outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                with open(outFilePath, 'w') as outFile:
                    json.dump(rows, outFile)
            except IOError as e:
                logger.debug(u"Tautulli Libraries :: Unable to create cache file with file sizes for section_id %s." % section_id)

        if rating_key:
            #logger.debug(u"Tautulli Libraries :: File sizes updated for rating_key %s." % rating_key)
            pass
        elif section_id:
            logger.debug(u"Tautulli Libraries :: File sizes updated for section_id %s." % section_id)

        return True
    
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
            except Exception as e:
                logger.warn(u"Tautulli Libraries :: Unable to execute database query for set_config: %s." % e)

    def get_details(self, section_id=None):
        default_return = {'section_id': 0,
                          'section_name': 'Local',
                          'section_type': '',
                          'library_thumb': common.DEFAULT_COVER_THUMB,
                          'library_art': '',
                          'count': 0,
                          'parent_count': 0,
                          'child_count': 0,
                          'do_notify': 0,
                          'do_notify_created': 0,
                          'keep_history': 1
                          }

        if not section_id:
            return default_return

        def get_library_details(section_id=section_id):
            monitor_db = database.MonitorDatabase()

            try:
                if str(section_id).isdigit():
                    query = 'SELECT section_id, section_name, section_type, count, parent_count, child_count, ' \
                            'thumb AS library_thumb, custom_thumb_url AS custom_thumb, art, ' \
                            'do_notify, do_notify_created, keep_history ' \
                            'FROM library_sections ' \
                            'WHERE section_id = ? '
                    result = monitor_db.select(query, args=[section_id])
                else:
                    result = []
            except Exception as e:
                logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_details: %s." % e)
                result = []

            library_details = {}
            if result:
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

        library_details = get_library_details(section_id=section_id)

        if library_details:
            return library_details

        else:
            logger.warn(u"Tautulli Libraries :: Unable to retrieve library %s from database. Requesting library list refresh."
                        % section_id)
            # Let's first refresh the libraries list to make sure the library isn't newly added and not in the db yet
            pmsconnect.refresh_libraries()

            library_details = get_library_details(section_id=section_id)

            if library_details:
                return library_details
            
            else:
                logger.warn(u"Tautulli Users :: Unable to retrieve library %s from database. Returning 'Local' library."
                            % section_id)
                # If there is no library data we must return something
                return default_return

    def get_watch_time_stats(self, section_id=None):
        if not session.allow_session_library(section_id):
            return []

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
                logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_watch_time_stats: %s." % e)
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
        if not session.allow_session_library(section_id):
            return []

        monitor_db = database.MonitorDatabase()

        user_stats = []

        try:
            if str(section_id).isdigit():
                query = 'SELECT (CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        'THEN users.username ELSE users.friendly_name END) AS friendly_name, ' \
                        'users.user_id, users.thumb, COUNT(user) AS user_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                        'JOIN users ON users.user_id = session_history.user_id ' \
                        'WHERE section_id = ? ' \
                        'GROUP BY users.user_id ' \
                        'ORDER BY user_count DESC'
                result = monitor_db.select(query, args=[section_id])
            else:
                result = []
        except Exception as e:
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_user_stats: %s." % e)
            result = []
        
        for item in result:
            row = {'friendly_name': item['friendly_name'],
                   'user_id': item['user_id'],
                   'user_thumb': item['thumb'],
                   'total_plays': item['user_count']
                   }
            user_stats.append(row)
        
        return session.mask_session_info(user_stats, mask_metadata=False)

    def get_recently_watched(self, section_id=None, limit='10'):
        if not session.allow_session_library(section_id):
            return []

        monitor_db = database.MonitorDatabase()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if str(section_id).isdigit():
                query = 'SELECT session_history.id, session_history.media_type, ' \
                        'session_history.rating_key, session_history.parent_rating_key, session_history.grandparent_rating_key, ' \
                        'title, parent_title, grandparent_title, thumb, parent_thumb, grandparent_thumb, media_index, parent_media_index, ' \
                        'year, started, user, content_rating, labels, section_id ' \
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
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_recently_watched: %s." % e)
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
                                 'parent_rating_key': row['parent_rating_key'],
                                 'grandparent_rating_key': row['grandparent_rating_key'],
                                 'title': row['title'],
                                 'parent_title': row['parent_title'],
                                 'grandparent_title': row['grandparent_title'],
                                 'thumb': thumb,
                                 'media_index': row['media_index'],
                                 'parent_media_index': row['parent_media_index'],
                                 'year': row['year'],
                                 'time': row['started'],
                                 'user': row['user'],
                                 'section_id': row['section_id'],
                                 'content_rating': row['content_rating'],
                                 'labels': row['labels'].split(';') if row['labels'] else (),
                                 }
                recently_watched.append(recent_output)

        return session.mask_session_info(recently_watched)

    def get_sections(self):
        monitor_db = database.MonitorDatabase()

        try:
            query = 'SELECT section_id, section_name FROM library_sections WHERE deleted_section = 0'
            result = monitor_db.select(query=query)
        except Exception as e:
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for get_sections: %s." % e)
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
                logger.info(u"Tautulli Libraries :: Deleting all history for library id %s from database." % section_id)
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
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for delete_all_history: %s." % e)

    def delete(self, section_id=None):
        monitor_db = database.MonitorDatabase()

        try:
            if section_id.isdigit():
                self.delete_all_history(section_id)
                logger.info(u"Tautulli Libraries :: Deleting library with id %s from database." % section_id)
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
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for delete: %s." % e)

    def undelete(self, section_id=None, section_name=None):
        monitor_db = database.MonitorDatabase()

        try:
            if section_id and section_id.isdigit():
                logger.info(u"Tautulli Libraries :: Re-adding library with id %s to database." % section_id)
                monitor_db.action('UPDATE library_sections SET deleted_section = 0 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET keep_history = 1 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET do_notify = 1 WHERE section_id = ?', [section_id])
                monitor_db.action('UPDATE library_sections SET do_notify_created = 1 WHERE section_id = ?', [section_id])

                return 'Re-added library with id %s.' % section_id
            elif section_name:
                logger.info(u"Tautulli Libraries :: Re-adding library with name %s to database." % section_name)
                monitor_db.action('UPDATE library_sections SET deleted_section = 0 WHERE section_name = ?', [section_name])
                monitor_db.action('UPDATE library_sections SET keep_history = 1 WHERE section_name = ?', [section_name])
                monitor_db.action('UPDATE library_sections SET do_notify = 1 WHERE section_name = ?', [section_name])
                monitor_db.action('UPDATE library_sections SET do_notify_created = 1 WHERE section_name = ?', [section_name])

                return 'Re-added library with section_name %s.' % section_name
            else:
                return 'Unable to re-add library, section_id or section_name not valid.'
        except Exception as e:
            logger.warn(u"Tautulli Libraries :: Unable to execute database query for undelete: %s." % e)

    def delete_datatable_media_info_cache(self, section_id=None):
        import os

        try:
            if section_id.isdigit():
                [os.remove(os.path.join(plexpy.CONFIG.CACHE_DIR, f)) for f in os.listdir(plexpy.CONFIG.CACHE_DIR) 
                 if f.startswith('media_info-%s' % section_id) and f.endswith('.json')]

                logger.debug(u"Tautulli Libraries :: Deleted media info table cache for section_id %s." % section_id)
                return 'Deleted media info table cache for library with id %s.' % section_id
            else:
                return 'Unable to delete media info table cache, section_id not valid.'
        except Exception as e:
            logger.warn(u"Tautulli Libraries :: Unable to delete media info table cache: %s." % e)

    def delete_duplicate_libraries(self):
        monitor_db = database.MonitorDatabase()

        # Refresh the PMS_URL to make sure the server_id is updated
        plextv.get_server_resources()

        server_id = plexpy.CONFIG.PMS_IDENTIFIER

        try:
            logger.debug(u"Tautulli Libraries :: Deleting libraries where server_id does not match %s." % server_id)
            monitor_db.action('DELETE FROM library_sections WHERE server_id != ?', [server_id])

            return 'Deleted duplicate libraries from the database.'
        except Exception as e:
            logger.warn(u"Tautulli Libraries :: Unable to delete duplicate libraries: %s." % e)


def update_libraries_db_notify():
    logger.info(u"Tautulli Libraries :: Upgrading library notification toggles...")

    # Set flag first in case something fails we don't want to keep re-adding the notifiers
    plexpy.CONFIG.__setattr__('UPDATE_LIBRARIES_DB_NOTIFY', 0)
    plexpy.CONFIG.write()

    libraries = Libraries()
    sections = libraries.get_sections()

    for section in sections:
        section_details = libraries.get_details(section['section_id'])
        
        if (section_details['do_notify'] == 1 and 
                (section_details['section_type'] == 'movie' and not plexpy.CONFIG.MOVIE_NOTIFY_ENABLE) or
                (section_details['section_type'] == 'show' and not plexpy.CONFIG.TV_NOTIFY_ENABLE) or
                (section_details['section_type'] == 'artist' and not plexpy.CONFIG.MUSIC_NOTIFY_ENABLE)):
            do_notify = 0
        else:
            do_notify = section_details['do_notify']

        if (section_details['keep_history'] == 1 and 
                (section_details['section_type'] == 'movie' and not plexpy.CONFIG.MOVIE_LOGGING_ENABLE) or
                (section_details['section_type'] == 'show' and not plexpy.CONFIG.TV_LOGGING_ENABLE) or
                (section_details['section_type'] == 'artist' and not plexpy.CONFIG.MUSIC_LOGGING_ENABLE)):
            keep_history = 0
        else:
            keep_history = section_details['keep_history']

        libraries.set_config(section_id=section_details['section_id'],
                                custom_thumb=section_details['library_thumb'],
                                do_notify=do_notify,
                                keep_history=keep_history,
                                do_notify_created=section_details['do_notify_created'])
