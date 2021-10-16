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
from future.builtins import next
from future.builtins import object

import json
import os
from datetime import datetime, timedelta

import plexpy
if plexpy.PYTHON2:
    import common
    import database
    import datatables
    import helpers
    import logger
    import plextv
    import pmsconnect
    import session
    import users
    from plex import Plex
else:
    from plexpy import common
    from plexpy import database
    from plexpy import datatables
    from plexpy import helpers
    from plexpy import logger
    from plexpy import plextv
    from plexpy import pmsconnect
    from plexpy import session
    from plexpy import users
    from plexpy.plex import Plex


def refresh_libraries():
    logger.info("Tautulli Libraries :: Requesting libraries list refresh...")

    server_id = plexpy.CONFIG.PMS_IDENTIFIER
    if not server_id:
        logger.error("Tautulli Libraries :: No PMS identifier, cannot refresh libraries. Verify server in settings.")
        return

    library_sections = pmsconnect.PmsConnect().get_library_details()

    if library_sections:
        monitor_db = database.MonitorDatabase()

        library_keys = []
        new_keys = []

        # Keep track of section_id to update is_active status
        section_ids = [common.LIVE_TV_SECTION_ID]  # Live TV library always considered active

        for section in library_sections:
            section_ids.append(helpers.cast_to_int(section['section_id']))

            section_keys = {'server_id': server_id,
                            'section_id': section['section_id']}
            section_values = {'server_id': server_id,
                              'section_id': section['section_id'],
                              'section_name': section['section_name'],
                              'section_type': section['section_type'],
                              'agent': section['agent'],
                              'thumb': section['thumb'],
                              'art': section['art'],
                              'count': section['count'],
                              'parent_count': section.get('parent_count', None),
                              'child_count': section.get('child_count', None),
                              'is_active': section['is_active']
                              }

            result = monitor_db.upsert('library_sections', key_dict=section_keys, value_dict=section_values)

            library_keys.append(section['section_id'])

            if result == 'insert':
                new_keys.append(section['section_id'])

        add_live_tv_library(refresh=True)

        query = 'UPDATE library_sections SET is_active = 0 WHERE server_id != ? OR ' \
                'section_id NOT IN ({})'.format(', '.join(['?'] * len(section_ids)))
        monitor_db.action(query=query, args=[plexpy.CONFIG.PMS_IDENTIFIER] + section_ids)

        if plexpy.CONFIG.HOME_LIBRARY_CARDS == ['first_run_wizard']:
            plexpy.CONFIG.__setattr__('HOME_LIBRARY_CARDS', library_keys)
            plexpy.CONFIG.write()
        else:
            new_keys = plexpy.CONFIG.HOME_LIBRARY_CARDS + new_keys
            plexpy.CONFIG.__setattr__('HOME_LIBRARY_CARDS', new_keys)
            plexpy.CONFIG.write()

        logger.info("Tautulli Libraries :: Libraries list refreshed.")
        return True
    else:
        logger.warn("Tautulli Libraries :: Unable to refresh libraries list.")
        return False


def add_live_tv_library(refresh=False):
    monitor_db = database.MonitorDatabase()
    result = monitor_db.select_single('SELECT * FROM library_sections '
                                      'WHERE section_id = ? and server_id = ?',
                                      [common.LIVE_TV_SECTION_ID, plexpy.CONFIG.PMS_IDENTIFIER])

    if result and not refresh or not result and refresh:
        return

    if not refresh:
        logger.info("Tautulli Libraries :: Adding Live TV library to the database.")

    section_keys = {'server_id': plexpy.CONFIG.PMS_IDENTIFIER,
                    'section_id': common.LIVE_TV_SECTION_ID}
    section_values = {'server_id': plexpy.CONFIG.PMS_IDENTIFIER,
                      'section_id': common.LIVE_TV_SECTION_ID,
                      'section_name': common.LIVE_TV_SECTION_NAME,
                      'section_type': 'live',
                      'thumb': common.DEFAULT_LIVE_TV_THUMB,
                      'art': common.DEFAULT_LIVE_TV_ART_FULL,
                      'is_active': 1
                      }

    result = monitor_db.upsert('library_sections', key_dict=section_keys, value_dict=section_values)


def has_library_type(section_type):
    monitor_db = database.MonitorDatabase()
    query = 'SELECT * FROM library_sections WHERE section_type = ? AND deleted_section = 0'
    args = [section_type]
    result = monitor_db.select_single(query=query, args=args)
    return bool(result)


def get_collections(section_id=None):
    plex = Plex(token=session.get_session_user_token())
    library = plex.get_library(section_id)

    if library.type not in ('movie', 'show', 'artist'):
        return []

    collections = library.collections()

    collections_list = []
    for collection in collections:
        collection_mode = collection.collectionMode
        if collection_mode is None:
            collection_mode = -1

        collection_sort = collection.collectionSort
        if collection_sort is None:
            collection_sort = 0

        collection_dict = {
            'addedAt': helpers.datetime_to_iso(collection.addedAt),
            'art': collection.art,
            'childCount': collection.childCount,
            'collectionMode': collection_mode,
            'collectionPublished': collection.collectionPublished,
            'collectionSort': collection_sort,
            'contentRating': collection.contentRating,
            'guid': collection.guid,
            'librarySectionID': collection.librarySectionID,
            'librarySectionTitle': collection.librarySectionTitle,
            'maxYear': collection.maxYear,
            'minYear': collection.minYear,
            'ratingKey': collection.ratingKey,
            'smart': collection.smart,
            'subtype': collection.subtype,
            'summary': collection.summary,
            'thumb': collection.thumb,
            'title': collection.title,
            'titleSort': collection.titleSort or collection.title,
            'type': collection.type,
            'updatedAt': helpers.datetime_to_iso(collection.updatedAt)
        }
        collections_list.append(collection_dict)

    return collections_list


def get_collections_list(section_id=None, **kwargs):
    if not section_id:
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': []}
        return default_return

    collections = get_collections(section_id=section_id)

    # Get datatables JSON data
    json_data = helpers.process_json_kwargs(json_kwargs=kwargs['json_data'])

    search_cols = ['title']

    sort_keys = {
        'collectionMode': {
            -1: 'Library Default',
            0: 'Hide collection',
            1: 'Hide items in this collection',
            2: 'Show this collection and its items'
        },
        'collectionSort': {
            0: 'Release date',
            1: 'Alphabetical',
            2: 'Custom'
        }
    }

    results = helpers.process_datatable_rows(
        collections, json_data, default_sort='titleSort',
        search_cols=search_cols, sort_keys=sort_keys)

    data = {
        'recordsFiltered': results['filtered_count'],
        'recordsTotal': results['total_count'],
        'data': results['results'],
        'draw': int(json_data['draw'])
    }

    return data


def get_playlists(section_id=None, user_id=None):
    if user_id and not session.get_session_user_id():
        user_tokens = users.Users().get_tokens(user_id=user_id)
        plex_token = user_tokens['server_token']
    else:
        plex_token = session.get_session_user_token()

    if not plex_token:
        return []

    plex = Plex(token=plex_token)

    if user_id:
        playlists = plex.PlexServer.playlists()
    else:
        library = plex.get_library(section_id)
        playlists = library.playlists()

    playlists_list = []
    for playlist in playlists:
        playlist_dict = {
            'addedAt': helpers.datetime_to_iso(playlist.addedAt),
            'composite': playlist.composite,
            'duration': playlist.duration,
            'guid': playlist.guid,
            'leafCount': playlist.leafCount,
            'librarySectionID': section_id,
            'playlistType': playlist.playlistType,
            'ratingKey': playlist.ratingKey,
            'smart': playlist.smart,
            'summary': playlist.summary,
            'title': playlist.title,
            'type': playlist.type,
            'updatedAt': helpers.datetime_to_iso(playlist.updatedAt),
            'userID': user_id
        }
        playlists_list.append(playlist_dict)

    return playlists_list


def get_playlists_list(section_id=None, user_id=None, **kwargs):
    if not section_id and not user_id:
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': []}
        return default_return

    playlists = get_playlists(section_id=section_id, user_id=user_id)

    # Get datatables JSON data
    json_data = helpers.process_json_kwargs(json_kwargs=kwargs['json_data'])

    results = helpers.process_datatable_rows(
        playlists, json_data, default_sort='title')

    data = {
        'recordsFiltered': results['filtered_count'],
        'recordsTotal': results['total_count'],
        'data': results['results'],
        'draw': int(json_data['draw'])
    }

    return data


class Libraries(object):

    def __init__(self):
        pass

    def get_datatables_list(self, kwargs=None, grouping=None):
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': []}

        data_tables = datatables.DataTables()

        custom_where = [['library_sections.deleted_section', 0]]

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        if session.get_session_shared_libraries():
            custom_where.append(['library_sections.section_id', session.get_session_shared_libraries()])

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        columns = ['library_sections.id AS row_id',
                   'library_sections.server_id',
                   'library_sections.section_id',
                   'library_sections.section_name',
                   'library_sections.section_type',
                   'library_sections.count',
                   'library_sections.parent_count',
                   'library_sections.child_count',
                   'library_sections.thumb AS library_thumb',
                   'library_sections.custom_thumb_url AS custom_thumb',
                   'library_sections.art AS library_art',
                   'library_sections.custom_art_url AS custom_art',
                   'COUNT(DISTINCT %s) AS plays' % group_by,
                   'SUM(CASE WHEN session_history.stopped > 0 THEN (session_history.stopped - session_history.started) \
                    ELSE 0 END) - SUM(CASE WHEN session_history.paused_counter IS NULL THEN 0 ELSE \
                    session_history.paused_counter END) AS duration',
                   'MAX(session_history.started) AS last_accessed',
                   'MAX(session_history.id) AS history_row_id',
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
                   'session_history_metadata.live',
                   'session_history_metadata.added_at',
                   'session_history_metadata.originally_available_at',
                   'session_history_metadata.guid',
                   'library_sections.do_notify',
                   'library_sections.do_notify_created',
                   'library_sections.keep_history',
                   'library_sections.is_active'
                   ]
        try:
            query = data_tables.ssp_query(table_name='library_sections',
                                          columns=columns,
                                          custom_where=custom_where,
                                          group_by=['library_sections.server_id', 'library_sections.section_id'],
                                          join_types=['LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN'],
                                          join_tables=['session_history',
                                                       'session_history_metadata',
                                                       'session_history_media_info'],
                                          join_evals=[['session_history.section_id', 'library_sections.section_id'],
                                                      ['session_history.id', 'session_history_metadata.id'],
                                                      ['session_history.id', 'session_history_media_info.id']],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_list: %s." % e)
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

            if item['custom_art'] and item['custom_art'] != item['library_art']:
                library_art = item['custom_art']
            else:
                library_art = item['library_art']

            row = {'row_id': item['row_id'],
                   'server_id': item['server_id'],
                   'section_id': item['section_id'],
                   'section_name': item['section_name'],
                   'section_type': item['section_type'],
                   'count': item['count'],
                   'parent_count': item['parent_count'],
                   'child_count': item['child_count'],
                   'library_thumb': library_thumb,
                   'library_art': library_art,
                   'plays': item['plays'],
                   'duration': item['duration'],
                   'last_accessed': item['last_accessed'],
                   'history_row_id': item['history_row_id'],
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
                   'live': item['live'],
                   'originally_available_at': item['originally_available_at'],
                   'guid': item['guid'],
                   'do_notify': helpers.checked(item['do_notify']),
                   'do_notify_created': helpers.checked(item['do_notify_created']),
                   'keep_history': helpers.checked(item['keep_history']),
                   'is_active': item['is_active']
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
                          'data': [],
                          'filtered_file_size': 0,
                          'total_file_size': 0}

        if not session.allow_session_library(section_id):
            return default_return

        if section_id and not str(section_id).isdigit():
            logger.warn("Tautulli Libraries :: Datatable media info called but invalid section_id provided.")
            return default_return
        elif rating_key and not str(rating_key).isdigit():
            logger.warn("Tautulli Libraries :: Datatable media info called but invalid rating_key provided.")
            return default_return
        elif not section_id and not rating_key:
            logger.warn("Tautulli Libraries :: Datatable media info called but no input provided.")
            return default_return

        # Get the library details
        library_details = self.get_details(section_id=section_id)
        if library_details['section_id'] == None:
            logger.debug("Tautulli Libraries :: Library section_id %s not found." % section_id)
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
            query = 'SELECT MAX(started) AS last_played, COUNT(DISTINCT %s) AS play_count, ' \
                    'rating_key, parent_rating_key, grandparent_rating_key ' \
                    'FROM session_history ' \
                    'WHERE section_id = ? ' \
                    'GROUP BY %s ' % (count_by, group_by)
            result = monitor_db.select(query, args=[section_id])
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_datatables_media_info2: %s." % e)
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
                #logger.debug("Tautulli Libraries :: No JSON file for rating_key %s." % rating_key)
                #logger.debug("Tautulli Libraries :: Refreshing data and creating new JSON file for rating_key %s." % rating_key)
                pass
        elif section_id:
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
                    library_count = len(rows)
            except IOError as e:
                #logger.debug("Tautulli Libraries :: No JSON file for library section_id %s." % section_id)
                #logger.debug("Tautulli Libraries :: Refreshing data and creating new JSON file for section_id %s." % section_id)
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
                children_list = library_children['children_list']
            else:
                logger.warn("Tautulli Libraries :: Unable to get a list of library items.")
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
                    logger.debug("Tautulli Libraries :: Unable to create cache file for rating_key %s." % rating_key)
            elif section_id:
                try:
                    outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                    with open(outFilePath, 'w') as outFile:
                        json.dump(rows, outFile)
                except IOError as e:
                    logger.debug("Tautulli Libraries :: Unable to create cache file for section_id %s." % section_id)

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
            searchable_columns = [d['data'] for d in json_data['columns'] if d['searchable']] + ['title']
            for row in rows:
                for k,v in row.items():
                    if k in searchable_columns and search_value in v.lower():
                        results.append(row)
                        break
        else:
            results = rows

        filtered_count = len(results)

        # Sort results
        results = sorted(results, key=lambda k: k['sort_title'].lower())
        sort_order = json_data['order']
        for order in reversed(sort_order):
            sort_key = json_data['columns'][int(order['column'])]['data']
            reverse = True if order['dir'] == 'desc' else False
            if rating_key and sort_key == 'sort_title':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k['media_index']), reverse=reverse)
            elif sort_key in ('file_size', 'bitrate', 'added_at', 'last_played', 'play_count'):
                results = sorted(results, key=lambda k: helpers.cast_to_int(k[sort_key]), reverse=reverse)
            elif sort_key == 'video_resolution':
                results = sorted(results, key=lambda k: helpers.cast_to_int(k[sort_key].replace('4k', '2160p').rstrip('p')), reverse=reverse)
            else:
                results = sorted(results, key=lambda k: k[sort_key].lower(), reverse=reverse)

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
            logger.warn("Tautulli Libraries :: Datatable media info file size called but invalid section_id provided.")
            return False
        elif rating_key and not str(rating_key).isdigit():
            logger.warn("Tautulli Libraries :: Datatable media info file size called but invalid rating_key provided.")
            return False

        # Get the library details
        library_details = self.get_details(section_id=section_id)
        if library_details['section_id'] == None:
            logger.debug("Tautulli Libraries :: Library section_id %s not found." % section_id)
            return False
        if library_details['section_type'] == 'photo':
            return False

        rows = []
        # Import media info cache from json file
        if rating_key:
            #logger.debug("Tautulli Libraries :: Getting file sizes for rating_key %s." % rating_key)
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s-%s.json' % (section_id, rating_key))
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
            except IOError as e:
                #logger.debug("Tautulli Libraries :: No JSON file for rating_key %s." % rating_key)
                #logger.debug("Tautulli Libraries :: Refreshing data and creating new JSON file for rating_key %s." % rating_key)
                pass
        elif section_id:
            logger.debug("Tautulli Libraries :: Getting file sizes for section_id %s." % section_id)
            try:
                inFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                with open(inFilePath, 'r') as inFile:
                    rows = json.load(inFile)
            except IOError as e:
                #logger.debug("Tautulli Libraries :: No JSON file for library section_id %s." % section_id)
                #logger.debug("Tautulli Libraries :: Refreshing data and creating new JSON file for section_id %s." % section_id)
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
                            media_part_info = next((p for p in media_info['parts'] if p['selected']),
                                                   media_info['parts'][0])

                    file_size += helpers.cast_to_int(media_part_info.get('file_size', 0))

                item['file_size'] = file_size

        # Cache the media info to a json file
        if rating_key:
            try:
                outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s-%s.json' % (section_id, rating_key))
                with open(outFilePath, 'w') as outFile:
                    json.dump(rows, outFile)
            except IOError as e:
                logger.debug("Tautulli Libraries :: Unable to create cache file with file sizes for rating_key %s." % rating_key)
        elif section_id:
            try:
                outFilePath = os.path.join(plexpy.CONFIG.CACHE_DIR,'media_info_%s.json' % section_id)
                with open(outFilePath, 'w') as outFile:
                    json.dump(rows, outFile)
            except IOError as e:
                logger.debug("Tautulli Libraries :: Unable to create cache file with file sizes for section_id %s." % section_id)

        if rating_key:
            #logger.debug("Tautulli Libraries :: File sizes updated for rating_key %s." % rating_key)
            pass
        elif section_id:
            logger.debug("Tautulli Libraries :: File sizes updated for section_id %s." % section_id)

        return True
    def set_config(self, section_id=None, custom_thumb='', custom_art='',
                   do_notify=1, keep_history=1, do_notify_created=1):
        if section_id:
            monitor_db = database.MonitorDatabase()

            key_dict = {'section_id': section_id}
            value_dict = {'custom_thumb_url': custom_thumb,
                          'custom_art_url': custom_art,
                          'do_notify': do_notify,
                          'do_notify_created': do_notify_created,
                          'keep_history': keep_history}
            try:
                monitor_db.upsert('library_sections', value_dict, key_dict)
            except Exception as e:
                logger.warn("Tautulli Libraries :: Unable to execute database query for set_config: %s." % e)

    def get_details(self, section_id=None, server_id=None, include_last_accessed=False):
        default_return = {'row_id': 0,
                          'server_id': '',
                          'section_id': 0,
                          'section_name': 'Local',
                          'section_type': '',
                          'library_thumb': common.DEFAULT_COVER_THUMB,
                          'library_art': '',
                          'count': 0,
                          'parent_count': 0,
                          'child_count': 0,
                          'is_active': 1,
                          'do_notify': 0,
                          'do_notify_created': 0,
                          'keep_history': 1,
                          'deleted_section': 0,
                          'last_accessed': None,
                          }

        if not section_id:
            return default_return

        if server_id is None:
            server_id = plexpy.CONFIG.PMS_IDENTIFIER

        library_details = self.get_library_details(section_id=section_id, server_id=server_id,
                                                   include_last_accessed=include_last_accessed)

        if library_details:
            return library_details

        else:
            logger.warn("Tautulli Libraries :: Unable to retrieve library %s from database. Requesting library list refresh."
                        % section_id)
            # Let's first refresh the libraries list to make sure the library isn't newly added and not in the db yet
            refresh_libraries()

            library_details = self.get_library_details(section_id=section_id, server_id=server_id,
                                                       include_last_accessed=include_last_accessed)

            if library_details:
                return library_details

            else:
                logger.warn("Tautulli Users :: Unable to retrieve library %s from database. Returning 'Local' library."
                            % section_id)
                # If there is no library data we must return something
                return default_return

    def get_library_details(self, section_id=None, server_id=None, include_last_accessed=False):
        if server_id is None:
            server_id = plexpy.CONFIG.PMS_IDENTIFIER

        last_accessed = 'NULL'
        join = ''
        if include_last_accessed:
            last_accessed = 'MAX(session_history.started)'
            join = 'LEFT OUTER JOIN session_history ON library_sections.section_id = session_history.section_id ' \

        monitor_db = database.MonitorDatabase()

        try:
            if str(section_id).isdigit():
                where = 'library_sections.section_id = ?'
                args = [section_id]
            else:
                raise Exception('Missing section_id')

            query = 'SELECT library_sections.id AS row_id, server_id, library_sections.section_id, ' \
                    'section_name, section_type, ' \
                    'count, parent_count, child_count, ' \
                    'library_sections.thumb AS library_thumb, custom_thumb_url AS custom_thumb, ' \
                    'library_sections.art AS library_art, ' \
                    'custom_art_url AS custom_art, is_active, ' \
                    'do_notify, do_notify_created, keep_history, deleted_section, %s AS last_accessed ' \
                    'FROM library_sections %s ' \
                    'WHERE %s AND server_id = ? ' % (last_accessed, join, where)
            result = monitor_db.select(query, args=args + [server_id])
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_library_details: %s." % e)
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

                if item['custom_art'] and item['custom_art'] != item['library_art']:
                    library_art = item['custom_art']
                else:
                    library_art = item['library_art']

                library_details = {'row_id': item['row_id'],
                                   'server_id': item['server_id'],
                                   'section_id': item['section_id'],
                                   'section_name': item['section_name'],
                                   'section_type': item['section_type'],
                                   'library_thumb': library_thumb,
                                   'library_art': library_art,
                                   'count': item['count'],
                                   'parent_count': item['parent_count'],
                                   'child_count': item['child_count'],
                                   'is_active': item['is_active'],
                                   'do_notify': item['do_notify'],
                                   'do_notify_created': item['do_notify_created'],
                                   'keep_history': item['keep_history'],
                                   'deleted_section': item['deleted_section'],
                                   'last_accessed': item['last_accessed']
                                   }
        return library_details

    def get_watch_time_stats(self, section_id=None, grouping=None, query_days=None):
        if not session.allow_session_library(section_id):
            return []

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        if query_days and query_days is not None:
            query_days = map(helpers.cast_to_int, str(query_days).split(','))
        else:
            query_days = [1, 7, 30, 0]

        timestamp = helpers.timestamp()

        monitor_db = database.MonitorDatabase()

        library_watch_time_stats = []

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        for days in query_days:
            timestamp_query = timestamp - days * 24 * 60 * 60

            try:
                if days > 0:
                    if str(section_id).isdigit():
                        query = 'SELECT (SUM(stopped - started) - ' \
                                'SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, ' \
                                'COUNT(DISTINCT %s) AS total_plays ' \
                                'FROM session_history ' \
                                'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                                'WHERE stopped >= %s ' \
                                'AND section_id = ?' % (group_by, timestamp_query)
                        result = monitor_db.select(query, args=[section_id])
                    else:
                        result = []
                else:
                    if str(section_id).isdigit():
                        query = 'SELECT (SUM(stopped - started) - ' \
                                'SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, ' \
                                'COUNT(DISTINCT %s) AS total_plays ' \
                                'FROM session_history ' \
                                'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                                'WHERE section_id = ?' % group_by
                        result = monitor_db.select(query, args=[section_id])
                    else:
                        result = []
            except Exception as e:
                logger.warn("Tautulli Libraries :: Unable to execute database query for get_watch_time_stats: %s." % e)
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

    def get_user_stats(self, section_id=None, grouping=None):
        if not session.allow_session_library(section_id):
            return []

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        monitor_db = database.MonitorDatabase()

        user_stats = []

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        try:
            if str(section_id).isdigit():
                query = 'SELECT (CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" ' \
                        'THEN users.username ELSE users.friendly_name END) AS friendly_name, ' \
                        'users.user_id, users.username, users.thumb, users.custom_avatar_url AS custom_thumb, ' \
                        'COUNT(DISTINCT %s) AS user_count ' \
                        'FROM session_history ' \
                        'JOIN session_history_metadata ON session_history_metadata.id = session_history.id ' \
                        'JOIN users ON users.user_id = session_history.user_id ' \
                        'WHERE section_id = ? ' \
                        'GROUP BY users.user_id ' \
                        'ORDER BY user_count DESC' % group_by
                result = monitor_db.select(query, args=[section_id])
            else:
                result = []
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_user_stats: %s." % e)
            result = []

        for item in result:
            if item['custom_thumb'] and item['custom_thumb'] != item['thumb']:
                user_thumb = item['custom_thumb']
            elif item['thumb']:
                user_thumb = item['thumb']
            else:
                user_thumb = common.DEFAULT_USER_THUMB

            row = {'friendly_name': item['friendly_name'],
                   'user_id': item['user_id'],
                   'user_thumb': user_thumb,
                   'username': item['username'],
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
                query = 'SELECT session_history.id, session_history.media_type, guid, ' \
                        'session_history.rating_key, session_history.parent_rating_key, session_history.grandparent_rating_key, ' \
                        'title, parent_title, grandparent_title, original_title, ' \
                        'thumb, parent_thumb, grandparent_thumb, media_index, parent_media_index, ' \
                        'year, originally_available_at, added_at, live, started, user, content_rating, labels, section_id ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'WHERE section_id = ? ' \
                        'GROUP BY session_history.rating_key ' \
                        'ORDER BY MAX(started) DESC LIMIT ?'
                result = monitor_db.select(query, args=[section_id, limit])
            else:
                result = []
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_recently_watched: %s." % e)
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
                                 'original_title': row['original_title'],
                                 'thumb': thumb,
                                 'media_index': row['media_index'],
                                 'parent_media_index': row['parent_media_index'],
                                 'year': row['year'],
                                 'originally_available_at': row['originally_available_at'],
                                 'live': row['live'],
                                 'guid': row['guid'],
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
            query = 'SELECT section_id, section_name, section_type, agent ' \
                    'FROM library_sections WHERE deleted_section = 0'
            result = monitor_db.select(query=query)
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_sections: %s." % e)
            return None

        libraries = []
        for item in result:
            library = {'section_id': item['section_id'],
                       'section_name': item['section_name'],
                       'section_type': item['section_type'],
                       'agent': item['agent']
                       }
            libraries.append(library)

        return libraries

    def delete(self, server_id=None, section_id=None, row_ids=None, purge_only=False):
        monitor_db = database.MonitorDatabase()

        if row_ids and row_ids is not None:
            row_ids = list(map(helpers.cast_to_int, row_ids.split(',')))

            # Get the section_ids corresponding to the row_ids
            result = monitor_db.select('SELECT server_id, section_id FROM library_sections '
                                       'WHERE id IN ({})'.format(','.join(['?'] * len(row_ids))), row_ids)

            success = []
            for library in result:
                success.append(self.delete(server_id=library['server_id'], section_id=library['section_id'],
                                           purge_only=purge_only))
            return all(success)

        elif str(section_id).isdigit():
            server_id = server_id or plexpy.CONFIG.PMS_IDENTIFIER
            if server_id == plexpy.CONFIG.PMS_IDENTIFIER:
                delete_success = database.delete_library_history(section_id=section_id)
            else:
                logger.warn("Tautulli Libraries :: Library history not deleted for library section_id %s "
                            "because library server_id %s does not match Plex server identifier %s."
                            % (section_id, server_id, plexpy.CONFIG.PMS_IDENTIFIER))
                delete_success = True

            if purge_only:
                return delete_success
            else:
                logger.info("Tautulli Libraries :: Deleting library with server_id %s and section_id %s from database."
                            % (server_id, section_id))
                try:
                    monitor_db.action('UPDATE library_sections '
                                      'SET deleted_section = 1, keep_history = 0, do_notify = 0, do_notify_created = 0 '
                                      'WHERE server_id = ? AND section_id = ?', [server_id, section_id])
                    return delete_success
                except Exception as e:
                    logger.warn("Tautulli Libraries :: Unable to execute database query for delete: %s." % e)

        else:
            return False

    def undelete(self, section_id=None, section_name=None):
        monitor_db = database.MonitorDatabase()

        try:
            if section_id and section_id.isdigit():
                query = 'SELECT * FROM library_sections WHERE section_id = ?'
                result = monitor_db.select(query=query, args=[section_id])
                if result:
                    logger.info("Tautulli Libraries :: Re-adding library with id %s to database." % section_id)
                    monitor_db.action('UPDATE library_sections '
                                      'SET deleted_section = 0, keep_history = 1, do_notify = 1, do_notify_created = 1 '
                                      'WHERE section_id = ?',
                                      [section_id])
                    return True
                else:
                    return False

            elif section_name:
                query = 'SELECT * FROM library_sections WHERE section_name = ?'
                result = monitor_db.select(query=query, args=[section_name])
                if result:
                    logger.info("Tautulli Libraries :: Re-adding library with name %s to database." % section_name)
                    monitor_db.action('UPDATE library_sections '
                                      'SET deleted_section = 0, keep_history = 1, do_notify = 1, do_notify_created = 1 '
                                      'WHERE section_name = ?',
                                      [section_name])
                    return True
                else:
                    return False

        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for undelete: %s." % e)

    def delete_media_info_cache(self, section_id=None):
        import os

        try:
            if section_id.isdigit():
                [os.remove(os.path.join(plexpy.CONFIG.CACHE_DIR, f)) for f in os.listdir(plexpy.CONFIG.CACHE_DIR)
                 if f.startswith('media_info_%s' % section_id) and f.endswith('.json')]

                logger.debug("Tautulli Libraries :: Deleted media info table cache for section_id %s." % section_id)
                return 'Deleted media info table cache for library with id %s.' % section_id
            else:
                return 'Unable to delete media info table cache, section_id not valid.'
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to delete media info table cache: %s." % e)

    def delete_duplicate_libraries(self):
        monitor_db = database.MonitorDatabase()

        # Refresh the PMS_URL to make sure the server_id is updated
        plextv.get_server_resources()

        server_id = plexpy.CONFIG.PMS_IDENTIFIER

        try:
            logger.debug("Tautulli Libraries :: Deleting libraries where server_id does not match %s." % server_id)
            monitor_db.action('DELETE FROM library_sections WHERE server_id != ?', [server_id])

            return 'Deleted duplicate libraries from the database.'
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to delete duplicate libraries: %s." % e)
