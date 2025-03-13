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

import json
import os
import time
from urllib.parse import quote, quote_plus, urlencode
from xml.dom.minidom import Node

import plexpy
from plexpy import activity_processor
from plexpy import common
from plexpy import helpers
from plexpy import http_handler
from plexpy import libraries
from plexpy import logger
from plexpy import plextv
from plexpy import session
from plexpy import users


def get_server_friendly_name():
    logger.info("Tautulli Pmsconnect :: Requesting name from server...")
    server_name = PmsConnect().get_server_pref(pref='FriendlyName')

    # If friendly name is blank
    if not server_name:
        servers_info = PmsConnect().get_servers_info()
        for server in servers_info:
            if server['machine_identifier'] == plexpy.CONFIG.PMS_IDENTIFIER:
                server_name = server['name']
                break

    if server_name and server_name != plexpy.CONFIG.PMS_NAME:
        plexpy.CONFIG.__setattr__('PMS_NAME', server_name)
        plexpy.CONFIG.write()
        logger.info("Tautulli Pmsconnect :: Server name retrieved.")

    return server_name


class PmsConnect(object):
    """
    Retrieve data from Plex Server
    """

    def __init__(self, url=None, token=None):
        self.url = url
        self.token = token

        if not self.url and plexpy.CONFIG.PMS_URL:
            self.url = plexpy.CONFIG.PMS_URL
        elif not self.url:
            self.url = 'http://{hostname}:{port}'.format(hostname=plexpy.CONFIG.PMS_IP,
                                                         port=plexpy.CONFIG.PMS_PORT)
        self.timeout = plexpy.CONFIG.PMS_TIMEOUT

        if not self.token:
            # Check if we should use the admin token, or the guest server token
            if session.get_session_user_id():
                user_data = users.Users()
                user_tokens = user_data.get_tokens(user_id=session.get_session_user_id())
                self.token = user_tokens['server_token']
            else:
                self.token = plexpy.CONFIG.PMS_TOKEN

        self.ssl_verify = plexpy.CONFIG.VERIFY_SSL_CERT

        self.request_handler = http_handler.HTTPHandler(urls=self.url,
                                                        token=self.token,
                                                        timeout=self.timeout,
                                                        ssl_verify=self.ssl_verify)

    def get_sessions(self, output_format=''):
        """
        Return current sessions.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/status/sessions'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_sessions_terminate(self, session_id='', reason=''):
        """
        Return current sessions.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/status/sessions/terminate?sessionId=%s&reason=%s' % (session_id, quote_plus(reason))
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    return_response=True)

        return request

    def get_metadata(self, rating_key='', output_format=''):
        """
        Return metadata for request item.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/metadata/' + rating_key + '?includeMarkers=1'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_epg_metadata(self, epg_key='', output_format=''):
        """
        Return epg metadata for request item.

        Parameters required:    epg_key { Plex key }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = epg_key
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format,
                                                    raise_errors=False)

        return request

    def get_metadata_children(self, rating_key='', collection=False, output_format=''):
        """
        Return metadata for children of the request item.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/{}/{}/children'.format(
            'collections' if collection else 'metadata', rating_key
        )
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_metadata_grandchildren(self, rating_key='', output_format=''):
        """
        Return metadata for graandchildren of the request item.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/metadata/' + rating_key + '/grandchildren'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_playlist_items(self, rating_key='', output_format=''):
        """
        Return metadata for items of the requested playlist.

        Parameters required:    rating_key { Plex ratingKey }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/playlists/' + rating_key + '/items'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_recently_added(self, start='0', count='0', output_format=''):
        """
        Return list of recently added items.

        Parameters required:    count { number of results to return }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/recentlyAdded?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s' % (start, count)
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_library_recently_added(self, section_id='', start='0', count='0', output_format=''):
        """
        Return list of recently added items.

        Parameters required:    count { number of results to return }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/sections/%s/recentlyAdded?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s' % (section_id, start, count)
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_children_list_related(self, rating_key='', output_format=''):
        """
        Return list of related children in requested collection item.

        Parameters required:    rating_key { ratingKey of parent }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/hubs/metadata/' + rating_key + '/related'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_childrens_list(self, rating_key='', output_format=''):
        """
        Return list of children in requested library item.

        Parameters required:    rating_key { ratingKey of parent }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/metadata/' + rating_key + '/allLeaves'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_server_list(self, output_format=''):
        """
        Return list of local servers.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/servers'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_server_prefs(self, output_format=''):
        """
        Return the local servers preferences.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/:/prefs'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_local_server_identity(self, output_format=''):
        """
        Return the local server identity.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/identity'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_libraries_list(self, output_format=''):
        """
        Return list of libraries on server.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/sections'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_library_list(self, section_id='', list_type='all', start=0, count=0, sort_type='',
                         label_key='', output_format=''):
        """
        Return list of items in library on server.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        start = 'X-Plex-Container-Start=' + str(start)
        count = 'X-Plex-Container-Size=' + str(count)
        label_key = '&label=' + label_key if label_key else ''

        uri = ('/library/sections/' + section_id + '/' + list_type + '?'
               + start + '&' + count + sort_type + label_key)
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def fetch_library_list(self, section_id='', list_type='all', count='', sort_type='',
                           label_key='', output_format=''):
        xml_head = []

        start = 0
        _count = int(count) if count else 100

        while True:
            library_data = self.get_library_list(
                section_id=str(section_id),
                list_type=list_type,
                start=start,
                count=_count,
                sort_type=sort_type,
                label_key=label_key,
                output_format=output_format
            )

            try:
                _xml_head = library_data.getElementsByTagName('MediaContainer')
                library_count = int(helpers.get_xml_attr(_xml_head[0], 'totalSize'))
                xml_head.extend(_xml_head)
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to parse XML for fetch_library_list: %s." % e)
                return xml_head

            start += _count

            if count or start >= library_count:
                break

        return xml_head

    def get_library_labels(self, section_id='', output_format=''):
        """
        Return list of labels for a library on server.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/library/sections/' + section_id + '/label'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_sync_item(self, sync_id='', output_format=''):
        """
        Return sync item details.

        Parameters required:    sync_id { unique sync id for item }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/sync/items/' + sync_id
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_sync_transcode_queue(self, output_format=''):
        """
        Return sync transcode queue.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/sync/transcodeQueue'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_search(self, query='', limit='', output_format=''):
        """
        Return search results.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/hubs/search?query=' + quote(query.encode('utf8')) + '&limit=' + limit + '&includeCollections=1'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_account(self, output_format=''):
        """
        Return account details.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/myplex/account'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def put_refresh_reachability(self):
        """
        Refresh Plex remote access port mapping.

        Optional parameters:    None

        Output: None
        """
        uri = '/myplex/refreshReachability'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='PUT')

        return request

    def put_updater(self, output_format=''):
        """
        Refresh updater status.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/updater/check?download=0'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='PUT',
                                                    output_format=output_format)

        return request

    def get_updater(self, output_format=''):
        """
        Return updater status.

        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/updater/status'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_hub_recently_added(self, start='0', count='0', media_type='', other_video=False, output_format=''):
        """
        Return Plex hub recently added.

        Parameters required:    start { item number to start from }
                                count { number of results to return }
                                media_type { str }
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        personal = '&personal=1' if other_video else ''
        uri = '/hubs/home/recentlyAdded?X-Plex-Container-Start=%s&X-Plex-Container-Size=%s&type=%s%s' \
              % (start, count, media_type, personal)
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_dvrs(self, output_format=''):
        """
        Return Plex dvrs.

        Parameters required:
        Optional parameters:    output_format { dict, json }

        Output: array
        """
        uri = '/livetv/dvrs'
        request = self.request_handler.make_request(uri=uri,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    def get_recently_added_details(self, start='0', count='0',  media_type='', section_id=''):
        """
        Return processed and validated list of recently added items.

        Parameters required:    count { number of results to return }

        Output: array
        """
        media_types = ('movie', 'show', 'artist', 'other_video')
        recents_list = []

        if media_type in media_types:
            other_video = False
            if media_type == 'movie':
                media_type = '1'
            elif media_type == 'show':
                media_type = '2'
            elif media_type == 'artist':
                media_type = '8'
            elif media_type == 'other_video':
                media_type = '1'
                other_video = True
            recent = self.get_hub_recently_added(start, count, media_type, other_video, output_format='xml')
        elif section_id:
            recent = self.get_library_recently_added(section_id, start, count, output_format='xml')
        else:
            for media_type in media_types:
                recents = self.get_recently_added_details(start, count, media_type)
                recents_list += recents['recently_added']

            output = {'recently_added': sorted(recents_list, key=lambda k: k['added_at'], reverse=True)[:int(count)]}
            return output

        try:
            xml_head = recent.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_recently_added: %s." % e)
            return {'recently_added': []}

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    output = {'recently_added': []}
                    return output

            recents_main = []
            if a.getElementsByTagName('Directory'):
                recents_main += a.getElementsByTagName('Directory')
            if a.getElementsByTagName('Video'):
                recents_main += a.getElementsByTagName('Video')

            for m in recents_main:
                directors = []
                writers = []
                actors = []
                genres = []
                labels = []
                collections = []
                guids = []

                if m.getElementsByTagName('Director'):
                    for director in m.getElementsByTagName('Director'):
                        directors.append(helpers.get_xml_attr(director, 'tag'))

                if m.getElementsByTagName('Writer'):
                    for writer in m.getElementsByTagName('Writer'):
                        writers.append(helpers.get_xml_attr(writer, 'tag'))

                if m.getElementsByTagName('Role'):
                    for actor in m.getElementsByTagName('Role'):
                        actors.append(helpers.get_xml_attr(actor, 'tag'))

                if m.getElementsByTagName('Genre'):
                    for genre in m.getElementsByTagName('Genre'):
                        genres.append(helpers.get_xml_attr(genre, 'tag'))

                if m.getElementsByTagName('Label'):
                    for label in m.getElementsByTagName('Label'):
                        labels.append(helpers.get_xml_attr(label, 'tag'))

                if m.getElementsByTagName('Collection'):
                    for collection in m.getElementsByTagName('Collection'):
                        collections.append(helpers.get_xml_attr(collection, 'tag'))

                if m.getElementsByTagName('Guid'):
                    for guid in m.getElementsByTagName('Guid'):
                        guids.append(helpers.get_xml_attr(guid, 'id'))

                recent_item = {'media_type': helpers.get_xml_attr(m, 'type'),
                               'section_id': helpers.get_xml_attr(m, 'librarySectionID'),
                               'library_name': helpers.get_xml_attr(m, 'librarySectionTitle'),
                               'rating_key': helpers.get_xml_attr(m, 'ratingKey'),
                               'parent_rating_key': helpers.get_xml_attr(m, 'parentRatingKey'),
                               'grandparent_rating_key': helpers.get_xml_attr(m, 'grandparentRatingKey'),
                               'title': helpers.get_xml_attr(m, 'title'),
                               'parent_title': helpers.get_xml_attr(m, 'parentTitle'),
                               'grandparent_title': helpers.get_xml_attr(m, 'grandparentTitle'),
                               'original_title': helpers.get_xml_attr(m, 'originalTitle'),
                               'sort_title': helpers.get_xml_attr(m, 'titleSort'),
                               'media_index': helpers.get_xml_attr(m, 'index'),
                               'parent_media_index': helpers.get_xml_attr(m, 'parentIndex'),
                               'studio': helpers.get_xml_attr(m, 'studio'),
                               'content_rating': helpers.get_xml_attr(m, 'contentRating'),
                               'summary': helpers.get_xml_attr(m, 'summary'),
                               'tagline': helpers.get_xml_attr(m, 'tagline'),
                               'rating': helpers.get_xml_attr(m, 'rating'),
                               'rating_image': helpers.get_xml_attr(m, 'ratingImage'),
                               'audience_rating': helpers.get_xml_attr(m, 'audienceRating'),
                               'audience_rating_image': helpers.get_xml_attr(m, 'audienceRatingImage'),
                               'user_rating': helpers.get_xml_attr(m, 'userRating'),
                               'duration': helpers.get_xml_attr(m, 'duration'),
                               'year': helpers.get_xml_attr(m, 'year'),
                               'thumb': helpers.get_xml_attr(m, 'thumb'),
                               'parent_thumb': helpers.get_xml_attr(m, 'parentThumb'),
                               'grandparent_thumb': helpers.get_xml_attr(m, 'grandparentThumb'),
                               'art': helpers.get_xml_attr(m, 'art'),
                               'banner': helpers.get_xml_attr(m, 'banner'),
                               'originally_available_at': helpers.get_xml_attr(m, 'originallyAvailableAt'),
                               'added_at': helpers.get_xml_attr(m, 'addedAt'),
                               'updated_at': helpers.get_xml_attr(m, 'updatedAt'),
                               'last_viewed_at': helpers.get_xml_attr(m, 'lastViewedAt'),
                               'guid': helpers.get_xml_attr(m, 'guid'),
                               'directors': directors,
                               'writers': writers,
                               'actors': actors,
                               'genres': genres,
                               'labels': labels,
                               'collections': collections,
                               'guids': guids,
                               'full_title': helpers.get_xml_attr(m, 'title'),
                               'child_count': helpers.get_xml_attr(m, 'childCount')
                               }

                recents_list.append(recent_item)

        output = {'recently_added': sorted(recents_list, key=lambda k: k['added_at'], reverse=True)}

        return output

    def get_metadata_details(self, rating_key='', sync_id='', plex_guid='', epg_key='', section_id='',
                             skip_cache=False, cache_key=None, return_cache=False, media_info=True):
        """
        Return processed and validated metadata list for requested item.

        Parameters required:    rating_key { Plex ratingKey }

        Output: array
        """
        metadata = {}

        if not skip_cache and cache_key:
            in_file_folder = os.path.join(plexpy.CONFIG.CACHE_DIR, 'session_metadata')
            in_file_path = os.path.join(in_file_folder, 'metadata-sessionKey-%s.json' % cache_key)

            if not os.path.exists(in_file_folder):
                os.mkdir(in_file_folder)

            try:
                with open(in_file_path, 'r') as inFile:
                    metadata = json.load(inFile)
            except (IOError, ValueError) as e:
                pass

            if metadata:
                _cache_time = metadata.pop('_cache_time', 0)
                # Return cached metadata if less than cache_seconds ago
                if return_cache or helpers.timestamp() - _cache_time <= plexpy.CONFIG.METADATA_CACHE_SECONDS:
                    return metadata

        if rating_key:
            metadata_xml = self.get_metadata(str(rating_key), output_format='xml')
        elif sync_id:
            metadata_xml = self.get_sync_item(str(sync_id), output_format='xml')
        elif plex_guid.startswith(('plex://movie', 'plex://episode')):
            rating_key = plex_guid.rsplit('/', 1)[-1]
            plextv_metadata = PmsConnect(url='https://metadata.provider.plex.tv', token=plexpy.CONFIG.PMS_TOKEN)
            metadata_xml = plextv_metadata.get_metadata(rating_key, output_format='xml')
        elif epg_key:
            metadata_xml = self.get_epg_metadata(epg_key, output_format='xml')
        else:
            return metadata

        try:
            xml_head = metadata_xml.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_metadata_details: %s." % e)
            return {}

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return metadata

            if a.getElementsByTagName('Directory'):
                metadata_main_list = a.getElementsByTagName('Directory')
            elif a.getElementsByTagName('Video'):
                metadata_main_list = a.getElementsByTagName('Video')
            elif a.getElementsByTagName('Track'):
                metadata_main_list = a.getElementsByTagName('Track')
            elif a.getElementsByTagName('Photo'):
                metadata_main_list = a.getElementsByTagName('Photo')
            elif a.getElementsByTagName('Playlist'):
                metadata_main_list = a.getElementsByTagName('Playlist')
            else:
                logger.debug("Tautulli Pmsconnect :: Metadata failed")
                return {}

            if sync_id and len(metadata_main_list) > 1:
                for metadata_main in metadata_main_list:
                    if helpers.get_xml_attr(metadata_main, 'ratingKey') == rating_key:
                        break
            else:
                metadata_main = metadata_main_list[0]

            metadata_type = helpers.get_xml_attr(metadata_main, 'type')
            if metadata_main.nodeName == 'Directory' and metadata_type == 'photo':
                metadata_type = 'photo_album'

            section_id = helpers.get_xml_attr(a, 'librarySectionID') or section_id
            library_name = helpers.get_xml_attr(a, 'librarySectionTitle')

            if not library_name and section_id:
                library_data = libraries.Libraries().get_details(section_id)
                library_name = library_data['section_name']

        directors = []
        writers = []
        actors = []
        genres = []
        labels = []
        collections = []
        guids = []
        markers = []

        if metadata_main.getElementsByTagName('Director'):
            for director in metadata_main.getElementsByTagName('Director'):
                directors.append(helpers.get_xml_attr(director, 'tag'))

        if metadata_main.getElementsByTagName('Writer'):
            for writer in metadata_main.getElementsByTagName('Writer'):
                writers.append(helpers.get_xml_attr(writer, 'tag'))

        if metadata_main.getElementsByTagName('Role'):
            for actor in metadata_main.getElementsByTagName('Role'):
                actors.append(helpers.get_xml_attr(actor, 'tag'))

        if metadata_main.getElementsByTagName('Genre'):
            for genre in metadata_main.getElementsByTagName('Genre'):
                genres.append(helpers.get_xml_attr(genre, 'tag'))

        if metadata_main.getElementsByTagName('Label'):
            for label in metadata_main.getElementsByTagName('Label'):
                labels.append(helpers.get_xml_attr(label, 'tag'))

        if metadata_main.getElementsByTagName('Collection'):
            for collection in metadata_main.getElementsByTagName('Collection'):
                collections.append(helpers.get_xml_attr(collection, 'tag'))

        if metadata_main.getElementsByTagName('Guid'):
            for guid in metadata_main.getElementsByTagName('Guid'):
                guids.append(helpers.get_xml_attr(guid, 'id'))

        if metadata_main.getElementsByTagName('Marker'):
            first = None
            for marker in metadata_main.getElementsByTagName('Marker'):
                marker_type = helpers.get_xml_attr(marker, 'type')
                if marker_type == 'credits':
                    first = bool(first is None)
                final = helpers.bool_true(helpers.get_xml_attr(marker, 'final'))
                markers.append({
                    'id': helpers.cast_to_int(helpers.get_xml_attr(marker, 'id')),
                    'type': marker_type,
                    'start_time_offset': helpers.cast_to_int(helpers.get_xml_attr(marker, 'startTimeOffset')),
                    'end_time_offset': helpers.cast_to_int(helpers.get_xml_attr(marker, 'endTimeOffset')),
                    'first': first if marker_type == 'credits' else None,
                    'final': final if marker_type == 'credits' else None
                })

        if metadata_type == 'movie':
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': [],
                        'grandparent_guids': [],
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'show':
            # Workaround for for duration sometimes reported in minutes for a show
            duration = helpers.get_xml_attr(metadata_main, 'duration')
            if duration.isdigit() and int(duration) < 1000:
                duration = str(int(duration) * 60 * 1000)

            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': duration,
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': [],
                        'grandparent_guids': [],
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'season':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            parent_guid = helpers.get_xml_attr(metadata_main, 'parentGuid')
            show_details = {}
            if plex_guid and parent_guid:
                show_details = self.get_metadata_details(plex_guid=parent_guid)
            elif epg_key and parent_guid:
                epg_key_root = epg_key.rsplit('/', maxsplit=1)[0]
                show_details = self.get_metadata_details(epg_key=f"{epg_key_root}/{quote_plus(parent_guid)}")
            elif not plex_guid and not epg_key and parent_rating_key:
                show_details = self.get_metadata_details(parent_rating_key)

            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': show_details.get('studio', ''),
                        'content_rating': show_details.get('content_rating', ''),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary') or show_details.get('summary', ''),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': show_details.get('duration', ''),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': show_details.get('year', ''),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb') or show_details.get('thumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': show_details.get('banner', ''),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': show_details.get('directors', []),
                        'writers': show_details.get('writers', []),
                        'actors': show_details.get('actors', []),
                        'genres': show_details.get('genres', []),
                        'labels': show_details.get('labels', []),
                        'collections': show_details.get('collections', []),
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': show_details.get('guids', []),
                        'grandparent_guids': [],
                        'full_title': '{} - {}'.format(helpers.get_xml_attr(metadata_main, 'parentTitle'),
                                                       helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'episode':
            grandparent_rating_key = helpers.get_xml_attr(metadata_main, 'grandparentRatingKey')
            grandparent_guid = helpers.get_xml_attr(metadata_main, 'grandparentGuid')
            show_details = {}
            if plex_guid and grandparent_guid:
                show_details = self.get_metadata_details(plex_guid=grandparent_guid)
            elif epg_key and grandparent_guid:
                epg_key_root = epg_key.rsplit('/', maxsplit=1)[0]
                show_details = self.get_metadata_details(epg_key=f"{epg_key_root}/{quote_plus(grandparent_guid)}")
            elif not plex_guid and grandparent_rating_key:
                show_details = self.get_metadata_details(grandparent_rating_key)

            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            parent_media_index = helpers.get_xml_attr(metadata_main, 'parentIndex')
            parent_thumb = helpers.get_xml_attr(metadata_main, 'parentThumb')
            season_details = self.get_metadata_details(parent_rating_key) if parent_rating_key else {}

            if not plex_guid and not epg_key and not parent_rating_key:
                # Try getting the parent_rating_key from the parent_thumb
                if parent_thumb.startswith('/library/metadata/'):
                    parent_rating_key = parent_thumb.split('/')[3]

                # Try getting the parent_rating_key from the grandparent's children
                if not parent_rating_key and grandparent_rating_key:
                    children_list = self.get_item_children(grandparent_rating_key)
                    parent_rating_key = next((c['rating_key'] for c in children_list['children_list']
                                              if c['media_index'] == parent_media_index), '')

            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': parent_rating_key,
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': parent_media_index,
                        'studio': show_details.get('studio', ''),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': season_details.get('year', ''),
                        'grandparent_year': show_details.get('year', ''),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': parent_thumb or show_details.get('thumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': show_details.get('banner', ''),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': show_details.get('actors', []),
                        'genres': show_details.get('genres', []),
                        'labels': show_details.get('labels', []),
                        'collections': show_details.get('collections', []),
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': season_details.get('guids', []),
                        'grandparent_guids': show_details.get('guids', []),
                        'full_title': '{} - {}'.format(helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                                                       helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'artist':
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': [],
                        'grandparent_guids': [],
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'album':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            artist_details = self.get_metadata_details(parent_rating_key) if parent_rating_key else {}
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary') or artist_details.get('summary', ''),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': artist_details.get('banner', ''),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': artist_details.get('guids', []),
                        'grandparent_guids': [],
                        'full_title': '{} - {}'.format(helpers.get_xml_attr(metadata_main, 'parentTitle'),
                                                       helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'track':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            album_details = self.get_metadata_details(parent_rating_key) if parent_rating_key else {}
            track_artist = helpers.get_xml_attr(metadata_main, 'originalTitle') or \
                           helpers.get_xml_attr(metadata_main, 'grandparentTitle')
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': album_details.get('year', ''),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': album_details.get('banner', ''),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': album_details.get('genres', []),
                        'labels': album_details.get('labels', []),
                        'collections': album_details.get('collections', []),
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': album_details.get('guids', []),
                        'grandparent_guids': album_details.get('parent_guids', []),
                        'full_title': '{} - {}'.format(helpers.get_xml_attr(metadata_main, 'title'),
                                                       track_artist),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'photo_album':
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': [],
                        'grandparent_guids': [],
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'photo':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            photo_album_details = self.get_metadata_details(parent_rating_key) if parent_rating_key else {}
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': photo_album_details.get('banner', ''),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': photo_album_details.get('genres', []),
                        'labels': photo_album_details.get('labels', []),
                        'collections': photo_album_details.get('collections', []),
                        'guids': [],
                        'markers': markers,
                        'parent_guids': photo_album_details.get('guids', []),
                        'grandparent_guids': [],
                        'full_title': '{} - {}'.format(helpers.get_xml_attr(metadata_main, 'parentTitle') or library_name,
                                                       helpers.get_xml_attr(metadata_main, 'title')),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'collection':
            metadata = {'media_type': metadata_type,
                        'sub_media_type': helpers.get_xml_attr(metadata_main, 'subtype'),
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'grandparent_year': helpers.get_xml_attr(metadata_main, 'grandparentYear'),
                        'min_year': helpers.get_xml_attr(metadata_main, 'minYear'),
                        'max_year': helpers.get_xml_attr(metadata_main, 'maxYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb').split('?')[0],
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'child_count': helpers.get_xml_attr(metadata_main, 'childCount'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': [],
                        'grandparent_guids': [],
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'childCount')),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1'),
                        'smart': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'smart'))
                        }

        elif metadata_type == 'playlist':
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'composite': helpers.get_xml_attr(metadata_main, 'composite'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'composite'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'children_count': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'leafCount')),
                        'smart': helpers.cast_to_int(helpers.get_xml_attr(metadata_main, 'smart')),
                        'playlist_type': helpers.get_xml_attr(metadata_main, 'playlistType'),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        elif metadata_type == 'clip':
            metadata = {'media_type': metadata_type,
                        'section_id': section_id,
                        'library_name': library_name,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'original_title': helpers.get_xml_attr(metadata_main, 'originalTitle'),
                        'sort_title': helpers.get_xml_attr(metadata_main, 'titleSort'),
                        'edition_title': helpers.get_xml_attr(metadata_main, 'editionTitle'),
                        'slug': helpers.get_xml_attr(metadata_main, 'slug'),
                        'parent_slug': helpers.get_xml_attr(metadata_main, 'parentSlug'),
                        'grandparent_slug': helpers.get_xml_attr(metadata_main, 'grandparentSlug'),
                        'media_index': helpers.get_xml_attr(metadata_main, 'index'),
                        'parent_media_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'rating_image': helpers.get_xml_attr(metadata_main, 'ratingImage'),
                        'audience_rating': helpers.get_xml_attr(metadata_main, 'audienceRating'),
                        'audience_rating_image': helpers.get_xml_attr(metadata_main, 'audienceRatingImage'),
                        'user_rating': helpers.get_xml_attr(metadata_main, 'userRating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'parent_year': helpers.get_xml_attr(metadata_main, 'parentYear'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'banner': helpers.get_xml_attr(metadata_main, 'banner'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'parent_guid': helpers.get_xml_attr(metadata_main, 'parentGuid'),
                        'grandparent_guid': helpers.get_xml_attr(metadata_main, 'grandparentGuid'),
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'collections': collections,
                        'guids': guids,
                        'markers': markers,
                        'parent_guids': [],
                        'grandparent_guids': [],
                        'full_title': helpers.get_xml_attr(metadata_main, 'title'),
                        'extra_type': helpers.get_xml_attr(metadata_main, 'extraType'),
                        'sub_type': helpers.get_xml_attr(metadata_main, 'subtype'),
                        'live': int(helpers.get_xml_attr(metadata_main, 'live') == '1')
                        }

        else:
            return metadata

        # Get additional metadata EPG provider
        epg_metadata = None
        if not epg_key and metadata['live']:
            metadata['section_id'] = common.LIVE_TV_SECTION_ID
            metadata['library_name'] = common.LIVE_TV_SECTION_NAME

            # Don't know the DVR key so need to try them all
            for dvr in self.get_dvrs_list():
                epg_metadata = self.get_metadata_details(epg_key=f"/{dvr['epg_identifier']}/metadata/{quote_plus(metadata['guid'])}", media_info=True)
                if epg_metadata:
                    metadata['epg_identifier'] = dvr['epg_identifier']
                    keys_to_update = [
                        'content_rating', 'summary', 'duration', 'guid',
                        'grandparent_title', 'grandparent_thumb', 'grandparent_guid',
                        'parent_title', 'parent_thumb', 'parent_guid'
                    ]
                    for key in keys_to_update:
                        metadata[key] = epg_metadata[key]
                    metadata['originally_available_at'] = helpers.timestamp_to_YMDHMS(epg_metadata['media_info'][0]['begins_at'], sep=True, ymd=True)
                    break
        # Get additional metadata from metadata.provider.plex.tv
        elif not plex_guid and metadata['live']:
            metadata['section_id'] = common.LIVE_TV_SECTION_ID
            metadata['library_name'] = common.LIVE_TV_SECTION_NAME

            plextv_metadata = self.get_metadata_details(plex_guid=metadata['guid'])
            if plextv_metadata:
                keys_to_update = ['summary', 'rating', 'thumb', 'grandparent_thumb', 'duration',
                                  'guid', 'grandparent_guid', 'genres']
                for key in keys_to_update:
                    metadata[key] = plextv_metadata[key]
                metadata['originally_available_at'] = helpers.iso_to_YMD(plextv_metadata['originally_available_at'])

        if metadata and media_info:
            medias = []
            media_items = metadata_main.getElementsByTagName('Media')
            for media in media_items:
                video_full_resolution_scan_type = ''

                parts = []
                part_items = media.getElementsByTagName('Part')
                for part in part_items:

                    streams = []
                    stream_items = part.getElementsByTagName('Stream')
                    for stream in stream_items:
                        if helpers.get_xml_attr(stream, 'streamType') == '1':
                            video_scan_type = helpers.get_xml_attr(stream, 'scanType')
                            video_full_resolution_scan_type = (video_full_resolution_scan_type or video_scan_type)

                            streams.append({'id': helpers.get_xml_attr(stream, 'id'),
                                            'type': helpers.get_xml_attr(stream, 'streamType'),
                                            'video_codec': helpers.get_xml_attr(stream, 'codec'),
                                            'video_codec_level': helpers.get_xml_attr(stream, 'level'),
                                            'video_bitrate': helpers.get_xml_attr(stream, 'bitrate'),
                                            'video_bit_depth': helpers.get_xml_attr(stream, 'bitDepth'),
                                            'video_chroma_subsampling': helpers.get_xml_attr(stream, 'chromaSubsampling'),
                                            'video_color_primaries': helpers.get_xml_attr(stream, 'colorPrimaries'),
                                            'video_color_range': helpers.get_xml_attr(stream, 'colorRange'),
                                            'video_color_space': helpers.get_xml_attr(stream, 'colorSpace'),
                                            'video_color_trc': helpers.get_xml_attr(stream, 'colorTrc'),
                                            'video_dynamic_range': self.get_dynamic_range(stream),
                                            'video_dovi_bl_present': int(helpers.get_xml_attr(stream, 'DOVIBLPresent') == '1'),
                                            'video_dovi_el_present': int(helpers.get_xml_attr(stream, 'DOVIELPresent') == '1'),
                                            'video_dovi_level': helpers.cast_to_int(helpers.get_xml_attr(stream, 'DOVILevel')),
                                            'video_dovi_present': int(helpers.get_xml_attr(stream, 'DOVIPresent') == '1'),
                                            'video_dovi_profile': helpers.cast_to_int(helpers.get_xml_attr(stream, 'DOVIProfile')),
                                            'video_dovi_rpu_present': int(helpers.get_xml_attr(stream, 'DOVIRPUPresent') == '1'),
                                            'video_dovi_version': helpers.cast_to_float(helpers.get_xml_attr(stream, 'DOVIVersion')),
                                            'video_frame_rate': helpers.get_xml_attr(stream, 'frameRate'),
                                            'video_ref_frames': helpers.get_xml_attr(stream, 'refFrames'),
                                            'video_height': helpers.get_xml_attr(stream, 'height'),
                                            'video_width': helpers.get_xml_attr(stream, 'width'),
                                            'video_language': helpers.get_xml_attr(stream, 'language'),
                                            'video_language_code': helpers.get_xml_attr(stream, 'languageCode'),
                                            'video_profile': helpers.get_xml_attr(stream, 'profile'),
                                            'video_scan_type': helpers.get_xml_attr(stream, 'scanType'),
                                            'selected': int(helpers.get_xml_attr(stream, 'selected') == '1')
                                            })

                        elif helpers.get_xml_attr(stream, 'streamType') == '2':
                            streams.append({'id': helpers.get_xml_attr(stream, 'id'),
                                            'type': helpers.get_xml_attr(stream, 'streamType'),
                                            'audio_codec': helpers.get_xml_attr(stream, 'codec'),
                                            'audio_bitrate': helpers.get_xml_attr(stream, 'bitrate'),
                                            'audio_bitrate_mode': helpers.get_xml_attr(stream, 'bitrateMode'),
                                            'audio_channels': helpers.get_xml_attr(stream, 'channels'),
                                            'audio_channel_layout': helpers.get_xml_attr(stream, 'audioChannelLayout'),
                                            'audio_sample_rate': helpers.get_xml_attr(stream, 'samplingRate'),
                                            'audio_language': helpers.get_xml_attr(stream, 'language'),
                                            'audio_language_code': helpers.get_xml_attr(stream, 'languageCode'),
                                            'audio_profile': helpers.get_xml_attr(stream, 'profile'),
                                            'selected': int(helpers.get_xml_attr(stream, 'selected') == '1')
                                            })

                        elif helpers.get_xml_attr(stream, 'streamType') == '3':
                            streams.append({'id': helpers.get_xml_attr(stream, 'id'),
                                            'type': helpers.get_xml_attr(stream, 'streamType'),
                                            'subtitle_codec': helpers.get_xml_attr(stream, 'codec'),
                                            'subtitle_container': helpers.get_xml_attr(stream, 'container'),
                                            'subtitle_format': helpers.get_xml_attr(stream, 'format'),
                                            'subtitle_forced': int(helpers.get_xml_attr(stream, 'forced') == '1'),
                                            'subtitle_location': 'external' if helpers.get_xml_attr(stream, 'key') else 'embedded',
                                            'subtitle_language': helpers.get_xml_attr(stream, 'language'),
                                            'subtitle_language_code': helpers.get_xml_attr(stream, 'languageCode'),
                                            'selected': int(helpers.get_xml_attr(stream, 'selected') == '1')
                                            })

                    parts.append({'id': helpers.get_xml_attr(part, 'id'),
                                  'file': helpers.get_xml_attr(part, 'file'),
                                  'file_size': helpers.get_xml_attr(part, 'size'),
                                  'indexes': int(helpers.get_xml_attr(part, 'indexes') == 'sd'),
                                  'streams': streams,
                                  'selected': int(helpers.get_xml_attr(part, 'selected') == '1')
                                  })

                video_resolution = helpers.get_xml_attr(media, 'videoResolution').lower().rstrip('ip')
                video_full_resolution = common.VIDEO_RESOLUTION_OVERRIDES.get(
                    video_resolution, video_resolution + (video_full_resolution_scan_type[:1] or 'p')
                )

                audio_channels = helpers.get_xml_attr(media, 'audioChannels')

                _media_info = {'id': helpers.get_xml_attr(media, 'id'),
                              'container': helpers.get_xml_attr(media, 'container'),
                              'bitrate': helpers.get_xml_attr(media, 'bitrate'),
                              'height': helpers.get_xml_attr(media, 'height'),
                              'width': helpers.get_xml_attr(media, 'width'),
                              'aspect_ratio': helpers.get_xml_attr(media, 'aspectRatio'),
                              'video_codec': helpers.get_xml_attr(media, 'videoCodec'),
                              'video_resolution': video_resolution,
                              'video_full_resolution': video_full_resolution,
                              'video_framerate': helpers.get_xml_attr(media, 'videoFrameRate'),
                              'video_profile': helpers.get_xml_attr(media, 'videoProfile'),
                              'audio_codec': helpers.get_xml_attr(media, 'audioCodec'),
                              'audio_channels': audio_channels,
                              'audio_channel_layout': common.AUDIO_CHANNELS.get(audio_channels, audio_channels),
                              'audio_profile': helpers.get_xml_attr(media, 'audioProfile'),
                              'optimized_version': int(helpers.get_xml_attr(media, 'proxyType') == '42'),
                              'channel_call_sign': helpers.get_xml_attr(media, 'channelCallSign'),
                              'channel_id': helpers.get_xml_attr(media, 'channelID'),
                              'channel_identifier': helpers.get_xml_attr(media, 'channelIdentifier'),
                              'channel_title': helpers.get_xml_attr(media, 'channelTitle'),
                              'channel_thumb': helpers.get_xml_attr(media, 'channelThumb'),
                              'channel_vcn': helpers.get_xml_attr(media, 'channelVcn'),
                              'protocol': helpers.get_xml_attr(media, 'protocol'),  # livetv
                              'begins_at': helpers.cast_to_int(helpers.get_xml_attr(media, 'beginsAt')),  # livetv
                              'ends_at': helpers.cast_to_int(helpers.get_xml_attr(media, 'endsAt')),  # livetv
                              'parts': parts
                              }

                if epg_metadata:
                    media_info_keys_to_update = [
                        'channel_id', 'channel_title', 'channel_vcn'
                    ]
                    for key in media_info_keys_to_update:
                        _media_info[key] = epg_metadata['media_info'][0][key]

                medias.append(_media_info)

            metadata['media_info'] = medias

        if metadata:
            if cache_key:
                metadata['_cache_time'] = helpers.timestamp()

                out_file_folder = os.path.join(plexpy.CONFIG.CACHE_DIR, 'session_metadata')
                out_file_path = os.path.join(out_file_folder, 'metadata-sessionKey-%s.json' % cache_key)

                if not os.path.exists(out_file_folder):
                    os.mkdir(out_file_folder)

                try:
                    with open(out_file_path, 'w') as outFile:
                        json.dump(metadata, outFile)
                except (IOError, ValueError) as e:
                    logger.error("Tautulli Pmsconnect :: Unable to create cache file for metadata (sessionKey %s): %s"
                                 % (cache_key, e))

            return metadata
        else:
            return metadata

    def get_metadata_children_details(self, rating_key='', get_children=False, media_type=None, section_id=None):
        """
        Return processed and validated metadata list for all children of requested item.

        Parameters required:    rating_key { Plex ratingKey }

        Output: array
        """
        if media_type == 'artist':
            sort_type = '&artist.id={}&type=9'.format(rating_key)
            xml_head = self.fetch_library_list(
                section_id=str(section_id),
                sort_type=sort_type,
                output_format='xml'
            )
        else:
            metadata = self.get_metadata_children(str(rating_key), output_format='xml')

            try:
                xml_head = metadata.getElementsByTagName('MediaContainer')
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_metadata_children: %s." % e)
                return []

        metadata_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return metadata_list

            if a.getElementsByTagName('Video'):
                metadata_main = a.getElementsByTagName('Video')
                for item in metadata_main:
                    child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                    metadata = self.get_metadata_details(str(child_rating_key))
                    if metadata:
                        metadata_list.append(metadata)

            elif a.getElementsByTagName('Track'):
                metadata_main = a.getElementsByTagName('Track')
                for item in metadata_main:
                    child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                    metadata = self.get_metadata_details(str(child_rating_key))
                    if metadata:
                        metadata_list.append(metadata)

            elif get_children and a.getElementsByTagName('Directory'):
                dir_main = a.getElementsByTagName('Directory')
                metadata_main = [d for d in dir_main if helpers.get_xml_attr(d, 'ratingKey')]
                for item in metadata_main:
                    child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                    metadata = self.get_metadata_children_details(str(child_rating_key), get_children)
                    if metadata:
                        metadata_list.extend(metadata)

        return metadata_list

    def get_library_metadata_details(self, section_id=''):
        """
        Return processed and validated metadata list for requested library.

        Parameters required:    section_id { Plex library key }

        Output: array
        """
        libraries_data = self.get_libraries_list(output_format='xml')

        try:
            xml_head = libraries_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_library_metadata_details: %s." % e)
            return []

        metadata_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    metadata_list = {'metadata': None}
                    return metadata_list

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
                for result in result_data:
                    key = helpers.get_xml_attr(result, 'key')
                    if key == section_id:
                        metadata = {'media_type': 'library',
                                    'section_id': helpers.get_xml_attr(result, 'key'),
                                    'library': helpers.get_xml_attr(result, 'type'),
                                    'title': helpers.get_xml_attr(result, 'title'),
                                    'art': helpers.get_xml_attr(result, 'art'),
                                    'thumb': helpers.get_xml_attr(result, 'thumb')
                                    }
                        if metadata['library'] == 'movie':
                            metadata['section_type'] = 'movie'
                        elif metadata['library'] == 'show':
                            metadata['section_type'] = 'episode'
                        elif metadata['library'] == 'artist':
                            metadata['section_type'] = 'track'

            metadata_list = {'metadata': metadata}

        return metadata_list

    def get_current_activity(self, skip_cache=False):
        """
        Return processed and validated session list.

        Output: array
        """
        session_data = self.get_sessions(output_format='xml')

        try:
            xml_head = session_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_current_activity: %s." % e)
            return []

        session_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    session_list = {'stream_count': '0',
                                    'sessions': []
                                    }
                    return session_list

            if a.getElementsByTagName('Track'):
                session_data = a.getElementsByTagName('Track')
                for session_ in session_data:
                    # Filter out background theme music sessions
                    if helpers.get_xml_attr(session_, 'guid').startswith('library://'):
                        continue
                    session_output = self.get_session_each(session_, skip_cache=skip_cache)
                    session_list.append(session_output)
            if a.getElementsByTagName('Video'):
                session_data = a.getElementsByTagName('Video')
                for session_ in session_data:
                    session_output = self.get_session_each(session_, skip_cache=skip_cache)
                    session_list.append(session_output)
            if a.getElementsByTagName('Photo'):
                session_data = a.getElementsByTagName('Photo')
                for session_ in session_data:
                    session_output = self.get_session_each(session_, skip_cache=skip_cache)
                    session_list.append(session_output)

        session_list = sorted(session_list, key=lambda k: k['session_key'])

        output = {'stream_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'sessions': session.mask_session_info(session_list)
                  }

        return output

    def get_session_each(self, session=None, skip_cache=False):
        """
        Return selected data from current sessions.
        This function processes and validates session data

        Parameters required:    session { the session dictionary }
        Output: dict
        """

        # Get the source media type
        media_type = helpers.get_xml_attr(session, 'type')
        rating_key = helpers.get_xml_attr(session, 'ratingKey')
        session_key = helpers.get_xml_attr(session, 'sessionKey')

        # Get the user details
        user_info = session.getElementsByTagName('User')[0]
        user_id = helpers.get_xml_attr(user_info, 'id')
        if user_id == '1':  # Admin user
            user_details = users.Users().get_details(user=helpers.get_xml_attr(user_info, 'title'))
        else:
            user_details = users.Users().get_details(user_id=user_id)

        # Get the player details
        player_info = session.getElementsByTagName('Player')[0]

        # Override platform names
        platform = helpers.get_xml_attr(player_info, 'platform')
        platform = common.PLATFORM_NAME_OVERRIDES.get(platform, platform)
        if not platform and helpers.get_xml_attr(player_info, 'product') == 'DLNA':
            platform = 'DLNA'

        platform_name = next((v for k, v in common.PLATFORM_NAMES.items() if k in platform.lower()), 'default')

        player_details = {'ip_address': helpers.get_xml_attr(player_info, 'address').split('::ffff:')[-1],
                          'ip_address_public': helpers.get_xml_attr(player_info, 'remotePublicAddress').split('::ffff:')[-1],
                          'device': helpers.get_xml_attr(player_info, 'device'),
                          'platform': platform,
                          'platform_name': platform_name,
                          'platform_version': helpers.get_xml_attr(player_info, 'platformVersion'),
                          'product': helpers.get_xml_attr(player_info, 'product'),
                          'product_version': helpers.get_xml_attr(player_info, 'version'),
                          'profile': helpers.get_xml_attr(player_info, 'profile'),
                          'player': helpers.get_xml_attr(player_info, 'title') or helpers.get_xml_attr(player_info, 'product'),
                          'machine_id': helpers.get_xml_attr(player_info, 'machineIdentifier'),
                          'state': helpers.get_xml_attr(player_info, 'state'),
                          'local': int(helpers.get_xml_attr(player_info, 'local') == '1'),
                          'relayed': helpers.get_xml_attr(player_info, 'relayed', default_return=None),
                          'secure': helpers.get_xml_attr(player_info, 'secure', default_return=None)
                          }

        # Get the session details
        if session.getElementsByTagName('Session'):
            session_info = session.getElementsByTagName('Session')[0]

            session_details = {'session_id': helpers.get_xml_attr(session_info, 'id'),
                               'bandwidth': helpers.get_xml_attr(session_info, 'bandwidth'),
                               'location': helpers.get_xml_attr(session_info, 'location')
                               }
        else:
            session_details = {'session_id': '',
                               'bandwidth': '',
                               'location': 'lan' if player_details['local'] else 'wan'
                               }

        # Check if using Plex Relay
        if player_details['relayed'] is None:
            player_details['relayed'] = int(session_details['location'] != 'lan' and
                                            player_details['ip_address_public'] == '127.0.0.1')

        else:
            player_details['relayed'] = helpers.cast_to_int(player_details['relayed'])

        # Check if secure connection
        if player_details['secure'] is not None:
            player_details['secure'] = int(player_details['secure'] == '1')

        # Get the transcode details
        if session.getElementsByTagName('TranscodeSession'):
            transcode_session = True

            transcode_info = session.getElementsByTagName('TranscodeSession')[0]

            transcode_progress = helpers.get_xml_attr(transcode_info, 'progress')
            transcode_speed = helpers.get_xml_attr(transcode_info, 'speed')
            transcode_min_offset = helpers.get_xml_attr(transcode_info, 'minOffsetAvailable')
            transcode_max_offset = helpers.get_xml_attr(transcode_info, 'maxOffsetAvailable')

            transcode_details = {'transcode_key': helpers.get_xml_attr(transcode_info, 'key'),
                                 'transcode_throttled': int(helpers.get_xml_attr(transcode_info, 'throttled') == '1'),
                                 'transcode_progress': int(round(helpers.cast_to_float(transcode_progress), 0)),
                                 'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                                 'transcode_audio_channels': helpers.get_xml_attr(transcode_info, 'audioChannels'),
                                 'transcode_audio_codec': helpers.get_xml_attr(transcode_info, 'audioCodec'),
                                 'transcode_video_codec': helpers.get_xml_attr(transcode_info, 'videoCodec'),
                                 'transcode_width': helpers.get_xml_attr(transcode_info, 'width'),  # Blank but keep for backwards compatibility
                                 'transcode_height': helpers.get_xml_attr(transcode_info, 'height'),  # Blank but keep backwards compatibility
                                 'transcode_container': helpers.get_xml_attr(transcode_info, 'container'),
                                 'transcode_protocol': helpers.get_xml_attr(transcode_info, 'protocol'),
                                 'transcode_min_offset_available': int(round(helpers.cast_to_float(transcode_min_offset), 0)),
                                 'transcode_max_offset_available': int(round(helpers.cast_to_float(transcode_max_offset), 0)),
                                 'transcode_hw_requested': int(helpers.get_xml_attr(transcode_info, 'transcodeHwRequested') == '1'),
                                 'transcode_hw_decode': helpers.get_xml_attr(transcode_info, 'transcodeHwDecoding'),
                                 'transcode_hw_decode_title': helpers.get_xml_attr(transcode_info, 'transcodeHwDecodingTitle'),
                                 'transcode_hw_encode': helpers.get_xml_attr(transcode_info, 'transcodeHwEncoding'),
                                 'transcode_hw_encode_title': helpers.get_xml_attr(transcode_info, 'transcodeHwEncodingTitle'),
                                 'transcode_hw_full_pipeline': int(helpers.get_xml_attr(transcode_info, 'transcodeHwFullPipeline') == '1'),
                                 'audio_decision': helpers.get_xml_attr(transcode_info, 'audioDecision'),
                                 'video_decision': helpers.get_xml_attr(transcode_info, 'videoDecision'),
                                 'subtitle_decision': helpers.get_xml_attr(transcode_info, 'subtitleDecision'),
                                 'throttled': '1' if helpers.get_xml_attr(transcode_info, 'throttled') == '1' else '0'  # Keep for backwards compatibility
                                 }
        else:
            transcode_session = False

            transcode_details = {'transcode_key': '',
                                 'transcode_throttled': 0,
                                 'transcode_progress': 0,
                                 'transcode_speed': '',
                                 'transcode_audio_channels': '',
                                 'transcode_audio_codec': '',
                                 'transcode_video_codec': '',
                                 'transcode_width': '',
                                 'transcode_height': '',
                                 'transcode_container': '',
                                 'transcode_protocol': '',
                                 'transcode_min_offset_available': 0,
                                 'transcode_max_offset_available': 0,
                                 'transcode_hw_requested': 0,
                                 'transcode_hw_decode': '',
                                 'transcode_hw_decode_title': '',
                                 'transcode_hw_encode': '',
                                 'transcode_hw_encode_title': '',
                                 'transcode_hw_full_pipeline': 0,
                                 'audio_decision': 'direct play',
                                 'video_decision': 'direct play',
                                 'subtitle_decision': '',
                                 'throttled': '0'  # Keep for backwards compatibility
                                 }

        # Check HW decoding/encoding
        transcode_details['transcode_hw_decoding'] = int(transcode_details['transcode_hw_decode'].lower() in common.HW_DECODERS)
        transcode_details['transcode_hw_encoding'] = int(transcode_details['transcode_hw_encode'].lower() in common.HW_ENCODERS)

        media_info_all = session.getElementsByTagName('Media')
        stream_media_info = next((m for m in media_info_all if helpers.get_xml_attr(m, 'selected') == '1'), media_info_all[0])
        part_info_all = stream_media_info.getElementsByTagName('Part')
        stream_media_parts_info = next((p for p in part_info_all if helpers.get_xml_attr(p, 'selected') == '1'), part_info_all[0])

        # Get the stream details
        video_stream_info = audio_stream_info = subtitle_stream_info = None
        for stream in stream_media_parts_info.getElementsByTagName('Stream'):
            if helpers.get_xml_attr(stream, 'streamType') == '1':
                if video_stream_info is None or helpers.get_xml_attr(stream, 'selected') == '1':
                    video_stream_info = stream

            elif helpers.get_xml_attr(stream, 'streamType') == '2':
                if audio_stream_info is None or helpers.get_xml_attr(stream, 'selected') == '1':
                    audio_stream_info = stream

            elif helpers.get_xml_attr(stream, 'streamType') == '3':
                if subtitle_stream_info is None or helpers.get_xml_attr(stream, 'selected') == '1':
                    subtitle_stream_info = stream

        video_id = audio_id = subtitle_id = None
        if video_stream_info:
            video_id = helpers.get_xml_attr(video_stream_info, 'id')
            video_details = {'stream_video_bitrate': helpers.get_xml_attr(video_stream_info, 'bitrate'),
                             'stream_video_bit_depth': helpers.get_xml_attr(video_stream_info, 'bitDepth'),
                             'stream_video_chroma_subsampling': helpers.get_xml_attr(video_stream_info, 'chromaSubsampling'),
                             'stream_video_codec': helpers.get_xml_attr(video_stream_info, 'codec'),
                             'stream_video_codec_level': helpers.get_xml_attr(video_stream_info, 'level'),
                             'stream_video_color_primaries': helpers.get_xml_attr(video_stream_info, 'colorPrimaries'),
                             'stream_video_color_range': helpers.get_xml_attr(video_stream_info, 'colorRange'),
                             'stream_video_color_space': helpers.get_xml_attr(video_stream_info, 'colorSpace'),
                             'stream_video_color_trc': helpers.get_xml_attr(video_stream_info, 'colorTrc'),
                             'stream_video_dynamic_range': self.get_dynamic_range(video_stream_info),
                             'stream_video_dovi_bl_present': int(helpers.get_xml_attr(video_stream_info, 'DOVIBLPresent') == '1'),
                             'stream_video_dovi_el_present': int(helpers.get_xml_attr(video_stream_info, 'DOVIELPresent') == '1'),
                             'stream_video_dovi_level': helpers.cast_to_int(helpers.get_xml_attr(video_stream_info, 'DOVILevel')),
                             'stream_video_dovi_present': int(helpers.get_xml_attr(video_stream_info, 'DOVIPresent') == '1'),
                             'stream_video_dovi_profile': helpers.cast_to_int(helpers.get_xml_attr(video_stream_info, 'DOVIProfile')),
                             'stream_video_dovi_rpu_present': int(helpers.get_xml_attr(video_stream_info, 'DOVIRPUPresent') == '1'),
                             'stream_video_dovi_version': helpers.cast_to_float(helpers.get_xml_attr(video_stream_info, 'DOVIVersion')),
                             'stream_video_height': helpers.get_xml_attr(video_stream_info, 'height'),
                             'stream_video_width': helpers.get_xml_attr(video_stream_info, 'width'),
                             'stream_video_ref_frames': helpers.get_xml_attr(video_stream_info, 'refFrames'),
                             'stream_video_language': helpers.get_xml_attr(video_stream_info, 'language'),
                             'stream_video_language_code': helpers.get_xml_attr(video_stream_info, 'languageCode'),
                             'stream_video_scan_type': helpers.get_xml_attr(video_stream_info, 'scanType'),
                             'stream_video_decision': helpers.get_xml_attr(video_stream_info, 'decision') or 'direct play'
                             }
        else:
            video_details = {'stream_video_bitrate': '',
                             'stream_video_bit_depth': '',
                             'stream_video_chroma_subsampling': '',
                             'stream_video_codec': '',
                             'stream_video_codec_level': '',
                             'stream_video_color_primaries': '',
                             'stream_video_color_range': '',
                             'stream_video_color_space': '',
                             'stream_video_color_trc': '',
                             'stream_video_dynamic_range': '',
                             'stream_video_height': '',
                             'stream_video_width': '',
                             'stream_video_ref_frames': '',
                             'stream_video_language': '',
                             'stream_video_language_code': '',
                             'stream_video_scan_type': '',
                             'stream_video_decision': ''
                             }

        if audio_stream_info:
            audio_id = helpers.get_xml_attr(audio_stream_info, 'id')
            stream_audio_channels = helpers.get_xml_attr(audio_stream_info, 'channels')
            stream_audio_channel_layouts_ = helpers.get_xml_attr(audio_stream_info, 'audioChannelLayout')
            audio_details = {'stream_audio_bitrate': helpers.get_xml_attr(audio_stream_info, 'bitrate'),
                             'stream_audio_bitrate_mode': helpers.get_xml_attr(audio_stream_info, 'bitrateMode'),
                             'stream_audio_channels': stream_audio_channels,
                             'stream_audio_channel_layout': stream_audio_channel_layouts_ or common.AUDIO_CHANNELS.get(
                                 stream_audio_channels, stream_audio_channels),
                             'stream_audio_codec': helpers.get_xml_attr(audio_stream_info, 'codec'),
                             'stream_audio_sample_rate': helpers.get_xml_attr(audio_stream_info, 'samplingRate'),
                             'stream_audio_channel_layout_': stream_audio_channel_layouts_,
                             'stream_audio_language': helpers.get_xml_attr(audio_stream_info, 'language'),
                             'stream_audio_language_code': helpers.get_xml_attr(audio_stream_info, 'languageCode'),
                             'stream_audio_profile': helpers.get_xml_attr(audio_stream_info, 'profile'),
                             'stream_audio_decision': helpers.get_xml_attr(audio_stream_info, 'decision') or 'direct play'
                             }
        else:
            audio_details = {'stream_audio_bitrate': '',
                             'stream_audio_bitrate_mode': '',
                             'stream_audio_channels': '',
                             'stream_audio_channel_layout': '',
                             'stream_audio_codec': '',
                             'stream_audio_sample_rate': '',
                             'stream_audio_channel_layout_': '',
                             'stream_audio_language': '',
                             'stream_audio_language_code': '',
                             'stream_audio_profile': '',
                             'stream_audio_decision': ''
                             }

        if subtitle_stream_info:
            subtitle_id = helpers.get_xml_attr(subtitle_stream_info, 'id')
            subtitle_selected = helpers.get_xml_attr(subtitle_stream_info, 'selected')
            subtitle_details = {'stream_subtitle_codec': helpers.get_xml_attr(subtitle_stream_info, 'codec'),
                                'stream_subtitle_container': helpers.get_xml_attr(subtitle_stream_info, 'container'),
                                'stream_subtitle_format': helpers.get_xml_attr(subtitle_stream_info, 'format'),
                                'stream_subtitle_forced': int(helpers.get_xml_attr(subtitle_stream_info, 'forced') == '1'),
                                'stream_subtitle_location': helpers.get_xml_attr(subtitle_stream_info, 'location'),
                                'stream_subtitle_language': helpers.get_xml_attr(subtitle_stream_info, 'language'),
                                'stream_subtitle_language_code': helpers.get_xml_attr(subtitle_stream_info, 'languageCode'),
                                'stream_subtitle_decision': helpers.get_xml_attr(subtitle_stream_info, 'decision') or transcode_details['subtitle_decision'],
                                'stream_subtitle_transient': int(helpers.get_xml_attr(subtitle_stream_info, 'transient') == '1')
                                }
        else:
            subtitle_selected = None
            subtitle_details = {'stream_subtitle_codec': '',
                                'stream_subtitle_container': '',
                                'stream_subtitle_format': '',
                                'stream_subtitle_forced': 0,
                                'stream_subtitle_location': '',
                                'stream_subtitle_language': '',
                                'stream_subtitle_language_code': '',
                                'stream_subtitle_decision': '',
                                'stream_subtitle_transient': 0
                                }

        # Get the bif thumbnail
        indexes = helpers.get_xml_attr(stream_media_parts_info, 'indexes')
        view_offset = helpers.get_xml_attr(session, 'viewOffset')
        if indexes == 'sd':
            part_id = helpers.get_xml_attr(stream_media_parts_info, 'id')
            bif_thumb = '/library/parts/{part_id}/indexes/sd/{view_offset}'.format(part_id=part_id, view_offset=view_offset)
        else:
            bif_thumb = ''

        if helpers.cast_to_int(video_details['stream_video_width']) >= 3840:
            stream_video_resolution = '4k'
        else:
            stream_video_resolution = helpers.get_xml_attr(stream_media_info, 'videoResolution').lower().rstrip('ip')

        stream_details = {'stream_container': helpers.get_xml_attr(stream_media_info, 'container'),
                          'stream_bitrate': helpers.get_xml_attr(stream_media_info, 'bitrate'),
                          'stream_aspect_ratio': helpers.get_xml_attr(stream_media_info, 'aspectRatio'),
                          'stream_video_framerate': helpers.get_xml_attr(stream_media_info, 'videoFrameRate'),
                          'stream_video_resolution': stream_video_resolution,
                          'stream_duration': helpers.get_xml_attr(stream_media_info, 'duration') or helpers.get_xml_attr(session, 'duration'),
                          'stream_container_decision': helpers.get_xml_attr(stream_media_parts_info, 'decision').replace('directplay', 'direct play'),
                          'optimized_version': int(helpers.get_xml_attr(stream_media_info, 'proxyType') == '42'),
                          'optimized_version_title': helpers.get_xml_attr(stream_media_info, 'title'),
                          'synced_version': 0,
                          'live': int(helpers.get_xml_attr(session, 'live') == '1'),
                          'live_uuid': helpers.get_xml_attr(stream_media_info, 'uuid'),
                          'indexes': int(indexes == 'sd'),
                          'bif_thumb': bif_thumb,
                          'subtitles': 1 if subtitle_id and subtitle_selected else 0
                          }

        # Get the source media info
        source_media_details = source_media_part_details = \
            source_video_details = source_audio_details = source_subtitle_details = {}

        if not helpers.get_xml_attr(session, 'ratingKey').isdigit():
            channel_stream = 1

            audio_channels = helpers.get_xml_attr(stream_media_info, 'audioChannels')
            metadata_details = {'media_type': media_type,
                                'section_id': helpers.get_xml_attr(session, 'librarySectionID'),
                                'library_name': helpers.get_xml_attr(session, 'librarySectionTitle'),
                                'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                                'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                                'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                                'title': helpers.get_xml_attr(session, 'title'),
                                'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                                'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                                'original_title': helpers.get_xml_attr(session, 'originalTitle'),
                                'sort_title': helpers.get_xml_attr(session, 'titleSort'),
                                'media_index': helpers.get_xml_attr(session, 'index'),
                                'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                                'studio': helpers.get_xml_attr(session, 'studio'),
                                'content_rating': helpers.get_xml_attr(session, 'contentRating'),
                                'summary': helpers.get_xml_attr(session, 'summary'),
                                'tagline': helpers.get_xml_attr(session, 'tagline'),
                                'rating': helpers.get_xml_attr(session, 'rating'),
                                'rating_image': helpers.get_xml_attr(session, 'ratingImage'),
                                'audience_rating': helpers.get_xml_attr(session, 'audienceRating'),
                                'audience_rating_image': helpers.get_xml_attr(session, 'audienceRatingImage'),
                                'user_rating': helpers.get_xml_attr(session, 'userRating'),
                                'duration': helpers.get_xml_attr(session, 'duration'),
                                'year': helpers.get_xml_attr(session, 'year'),
                                'thumb': helpers.get_xml_attr(session, 'thumb'),
                                'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                                'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                                'art': helpers.get_xml_attr(session, 'art'),
                                'banner': helpers.get_xml_attr(session, 'banner'),
                                'originally_available_at': helpers.get_xml_attr(session, 'originallyAvailableAt'),
                                'added_at': helpers.get_xml_attr(session, 'addedAt'),
                                'updated_at': helpers.get_xml_attr(session, 'updatedAt'),
                                'last_viewed_at': helpers.get_xml_attr(session, 'lastViewedAt'),
                                'guid': helpers.get_xml_attr(session, 'guid'),
                                'directors': [],
                                'writers': [],
                                'actors': [],
                                'genres': [],
                                'labels': [],
                                'full_title': helpers.get_xml_attr(session, 'title'),
                                'container': helpers.get_xml_attr(stream_media_info, 'container') \
                                             or helpers.get_xml_attr(stream_media_parts_info, 'container'),
                                'bitrate': helpers.get_xml_attr(stream_media_info, 'bitrate'),
                                'height': helpers.get_xml_attr(stream_media_info, 'height'),
                                'width': helpers.get_xml_attr(stream_media_info, 'width'),
                                'aspect_ratio': helpers.get_xml_attr(stream_media_info, 'aspectRatio'),
                                'video_codec': helpers.get_xml_attr(stream_media_info, 'videoCodec'),
                                'video_resolution': helpers.get_xml_attr(stream_media_info, 'videoResolution').lower(),
                                'video_full_resolution': helpers.get_xml_attr(stream_media_info, 'videoResolution').lower(),
                                'video_framerate': helpers.get_xml_attr(stream_media_info, 'videoFrameRate'),
                                'video_profile': helpers.get_xml_attr(stream_media_info, 'videoProfile'),
                                'audio_codec': helpers.get_xml_attr(stream_media_info, 'audioCodec'),
                                'audio_channels': audio_channels,
                                'audio_channel_layout': common.AUDIO_CHANNELS.get(audio_channels, audio_channels),
                                'audio_profile': helpers.get_xml_attr(stream_media_info, 'audioProfile'),
                                'channel_icon': helpers.get_xml_attr(session, 'sourceIcon'),
                                'channel_title': helpers.get_xml_attr(session, 'sourceTitle'),
                                'extra_type': helpers.get_xml_attr(session, 'extraType'),
                                'sub_type': helpers.get_xml_attr(session, 'subtype')
                                }
        else:
            channel_stream = 0

            media_id = helpers.get_xml_attr(stream_media_info, 'id')
            part_id = helpers.get_xml_attr(stream_media_parts_info, 'id')

            metadata_details = self.get_metadata_details(rating_key=rating_key,
                                                         skip_cache=skip_cache, cache_key=session_key)

            # Get the media info, fallback to first item if match id is not found
            source_medias = metadata_details.pop('media_info', [])
            source_media_details = next((m for m in source_medias if m['id'] == media_id), next((m for m in source_medias), {}))
            source_media_parts = source_media_details.pop('parts', [])
            source_media_part_details = next((p for p in source_media_parts if p['id'] == part_id), next((p for p in source_media_parts), {}))
            source_media_part_streams = source_media_part_details.pop('streams', [])

            source_video_details = {'id': '',
                                    'type': '',
                                    'video_codec': '',
                                    'video_codec_level': '',
                                    'video_bitrate': '',
                                    'video_bit_depth': '',
                                    'video_chroma_subsampling': '',
                                    'video_color_primaries': '',
                                    'video_color_range': '',
                                    'video_color_space': '',
                                    'video_color_trc': '',
                                    'video_dynamic_range': '',
                                    'video_frame_rate': '',
                                    'video_ref_frames': '',
                                    'video_height': '',
                                    'video_width': '',
                                    'video_language': '',
                                    'video_language_code': '',
                                    'video_scan_type': '',
                                    'video_profile': ''
                                    }
            source_audio_details = {'id': '',
                                    'type': '',
                                    'audio_codec': '',
                                    'audio_bitrate': '',
                                    'audio_bitrate_mode': '',
                                    'audio_channels': '',
                                    'audio_channel_layout': '',
                                    'audio_sample_rate': '',
                                    'audio_language': '',
                                    'audio_language_code': '',
                                    'audio_profile': ''
                                    }
            source_subtitle_details = {'id': '',
                                       'type': '',
                                       'subtitle_codec': '',
                                       'subtitle_container': '',
                                       'subtitle_format': '',
                                       'subtitle_forced': 0,
                                       'subtitle_location': '',
                                       'subtitle_language': '',
                                       'subtitle_language_code': ''
                                       }
            if video_id:
                source_video_details = next((p for p in source_media_part_streams if p['id'] == video_id),
                                            next((p for p in source_media_part_streams if p['type'] == '1'), source_video_details))
            if audio_id:
                source_audio_details = next((p for p in source_media_part_streams if p['id'] == audio_id),
                                            next((p for p in source_media_part_streams if p['type'] == '2'), source_audio_details))
            if subtitle_id:
                source_subtitle_details = next((p for p in source_media_part_streams if p['id'] == subtitle_id),
                                               next((p for p in source_media_part_streams if p['type'] == '3'), source_subtitle_details))

        # Override the thumb for clips
        if media_type == 'clip' and metadata_details.get('extra_type') and metadata_details['art']:
            metadata_details['thumb'] = metadata_details['art'].replace('/art', '/thumb')

        # Overrides for live sessions
        if stream_details['live'] and transcode_session:
            stream_details['stream_container_decision'] = 'transcode'
            stream_details['stream_container'] = transcode_details['transcode_container']

            video_details['stream_video_decision'] = transcode_details['video_decision']
            video_details['stream_video_codec'] = transcode_details['transcode_video_codec']

            audio_details['stream_audio_decision'] = transcode_details['audio_decision']
            audio_details['stream_audio_codec'] = transcode_details['transcode_audio_codec']
            audio_details['stream_audio_channels'] = transcode_details['transcode_audio_channels']
            audio_details['stream_audio_channel_layout'] = common.AUDIO_CHANNELS.get(
                transcode_details['transcode_audio_channels'], transcode_details['transcode_audio_channels'])

        # Generate a combined transcode decision value
        if video_details['stream_video_decision'] == 'transcode' or audio_details['stream_audio_decision'] == 'transcode':
            transcode_decision = 'transcode'
        elif video_details['stream_video_decision'] == 'copy' or audio_details['stream_audio_decision'] == 'copy':
            transcode_decision = 'copy'
        else:
            transcode_decision = 'direct play'

        stream_details['transcode_decision'] = transcode_decision
        stream_details['container_decision'] = stream_details['stream_container_decision']

        # Override * in audio codecs
        if audio_details['stream_audio_codec'] == '*':
            audio_details['stream_audio_codec'] = source_audio_details.get('audio_codec', '')
        if transcode_details['transcode_audio_codec'] == '*':
            transcode_details['transcode_audio_codec'] = source_audio_details.get('audio_codec', '')

        # Override * in video codecs
        if video_details['stream_video_codec'] == '*':
            video_details['stream_video_codec'] = source_video_details.get('video_codec', '')
        if transcode_details['transcode_video_codec'] == '*':
            transcode_details['transcode_video_codec'] = source_video_details.get('video_codec', '')

        if media_type in ('movie', 'episode', 'clip'):
            # Set the full resolution by combining stream_video_resolution and stream_video_scan_type
            stream_details['stream_video_full_resolution'] = common.VIDEO_RESOLUTION_OVERRIDES.get(
                stream_details['stream_video_resolution'],
                stream_details['stream_video_resolution'] + (video_details['stream_video_scan_type'][:1] or 'p'))

        # Get the quality profile
        if media_type in ('movie', 'episode', 'clip') and 'stream_bitrate' in stream_details:
            if video_details['stream_video_decision'] == 'transcode':
                synced_version_profile = ''

                stream_bitrate = helpers.cast_to_int(stream_details['stream_bitrate'])
                source_bitrate = helpers.cast_to_int(source_media_details.get('bitrate'))
                try:
                    quailtiy_bitrate = min(
                        b for b in common.VIDEO_QUALITY_PROFILES if stream_bitrate <= b <= source_bitrate)
                    quality_profile = common.VIDEO_QUALITY_PROFILES[quailtiy_bitrate]
                except ValueError:
                    quality_profile = 'Original'
            else:
                synced_version_profile = ''
                quality_profile = 'Original'

            if stream_details['optimized_version']:
                source_bitrate = helpers.cast_to_int(source_media_details.get('bitrate'))
                optimized_version_profile = '{} Mbps {}'.format(round(source_bitrate / 1000.0, 1),
                                                                source_media_details.get('video_full_resolution'))
            else:
                optimized_version_profile = ''

        elif media_type == 'track' and 'stream_bitrate' in stream_details:
            synced_version_profile = ''

            stream_bitrate = helpers.cast_to_int(stream_details['stream_bitrate'])
            source_bitrate = helpers.cast_to_int(source_media_details.get('bitrate'))
            try:
                quailtiy_bitrate = min(b for b in common.AUDIO_QUALITY_PROFILES if stream_bitrate <= b <= source_bitrate)
                quality_profile = common.AUDIO_QUALITY_PROFILES[quailtiy_bitrate]
            except ValueError:
                quality_profile = 'Original'

            optimized_version_profile = ''

        elif media_type == 'photo':
            quality_profile = 'Original'
            synced_version_profile = ''
            optimized_version_profile = ''

        else:
            quality_profile = 'Unknown'
            synced_version_profile = ''
            optimized_version_profile = ''

        # Entire session output (single dict for backwards compatibility)
        session_output = {'session_key': session_key,
                          'media_type': media_type,
                          'view_offset': view_offset,
                          'progress_percent': str(helpers.get_percent(view_offset, stream_details['stream_duration'])),
                          'quality_profile': quality_profile,
                          'synced_version_profile': synced_version_profile,
                          'optimized_version_profile': optimized_version_profile,
                          'user': user_details['username'],  # Keep for backwards compatibility
                          'channel_stream': channel_stream
                          }

        session_output.update(metadata_details)
        session_output.update(source_media_details)
        session_output.update(source_media_part_details)
        session_output.update(source_video_details)
        session_output.update(source_audio_details)
        session_output.update(source_subtitle_details)
        session_output.update(user_details)
        session_output.update(player_details)
        session_output.update(session_details)
        session_output.update(transcode_details)
        session_output.update(stream_details)
        session_output.update(video_details)
        session_output.update(audio_details)
        session_output.update(subtitle_details)

        return session_output

    def terminate_session(self, session_key='', session_id='', message=''):
        """
        Terminates a streaming session.
        """
        plex_tv = plextv.PlexTV()
        if not plex_tv.get_plexpass_status():
            msg = 'No Plex Pass subscription'
            logger.warn("Tautulli Pmsconnect :: Failed to terminate session: %s." % msg)
            return msg

        message = message.encode('utf-8') or 'The server owner has ended the stream.'

        ap = activity_processor.ActivityProcessor()

        if session_key:
            session = ap.get_session_by_key(session_key=session_key)
            if session and not session_id:
                session_id = session['session_id']

        elif session_id:
            session = ap.get_session_by_id(session_id=session_id)
            if session and not session_key:
                session_key = session['session_key']

        else:
            session = session_key = session_id = None

        if not session:
            msg = 'Invalid session_key (%s) or session_id (%s)' % (session_key, session_id)
            logger.warn("Tautulli Pmsconnect :: Failed to terminate session: %s." % msg)
            return msg

        if session_id:
            logger.info("Tautulli Pmsconnect :: Terminating session %s (session_id %s)." % (session_key, session_id))
            response = self.get_sessions_terminate(session_id=session_id, reason=message)
            return response.ok
        else:
            msg = 'Missing session_id'
            logger.warn("Tautulli Pmsconnect :: Failed to terminate session: %s." % msg)
            return msg

    def get_item_children(self, rating_key='', media_type=None, get_grandchildren=False):
        """
        Return processed and validated children list.

        Output: array
        """
        default_return = {'children_count': 0,
                          'children_list': []
                          }

        xml_head = []

        if media_type == 'playlist':
            children_data = self.get_playlist_items(rating_key, output_format='xml')
        elif media_type == 'collection':
            children_data = self.get_metadata_children(rating_key, collection=True, output_format='xml')
        elif get_grandchildren:
            children_data = self.get_metadata_grandchildren(rating_key, output_format='xml')
        elif media_type == 'artist':
            artist_metadata = self.get_metadata_details(rating_key)
            section_id = artist_metadata['section_id']
            sort_type = '&artist.id={}&type=9'.format(rating_key)
            xml_head = self.fetch_library_list(
                section_id=str(section_id),
                sort_type=sort_type,
                output_format='xml'
            )
        else:
            children_data = self.get_metadata_children(rating_key, output_format='xml')

        if not xml_head:
            try:
                xml_head = children_data.getElementsByTagName('MediaContainer')
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_item_children: %s." % e)
                return default_return

        children_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug("Tautulli Pmsconnect :: No children data.")
                    return default_return

            result_data = []

            for x in a.childNodes:
                if x.nodeType == Node.ELEMENT_NODE and x.tagName in ('Directory', 'Video', 'Track', 'Photo'):
                    result_data.append(x)

            if result_data:
                for m in result_data:
                    directors = []
                    writers = []
                    actors = []
                    genres = []
                    labels = []
                    collections = []

                    if m.getElementsByTagName('Director'):
                        for director in m.getElementsByTagName('Director'):
                            directors.append(helpers.get_xml_attr(director, 'tag'))

                    if m.getElementsByTagName('Writer'):
                        for writer in m.getElementsByTagName('Writer'):
                            writers.append(helpers.get_xml_attr(writer, 'tag'))

                    if m.getElementsByTagName('Role'):
                        for actor in m.getElementsByTagName('Role'):
                            actors.append(helpers.get_xml_attr(actor, 'tag'))

                    if m.getElementsByTagName('Genre'):
                        for genre in m.getElementsByTagName('Genre'):
                            genres.append(helpers.get_xml_attr(genre, 'tag'))

                    if m.getElementsByTagName('Label'):
                        for label in m.getElementsByTagName('Label'):
                            labels.append(helpers.get_xml_attr(label, 'tag'))

                    if m.getElementsByTagName('Collection'):
                        for collection in m.getElementsByTagName('Collection'):
                            collections.append(helpers.get_xml_attr(collection, 'tag'))

                    media_type = helpers.get_xml_attr(m, 'type')
                    if m.nodeName == 'Directory' and media_type == 'photo':
                        media_type = 'photo_album'

                    children_output = {'media_type': media_type,
                                       'section_id': helpers.get_xml_attr(a, 'librarySectionID'),
                                       'library_name': helpers.get_xml_attr(a, 'librarySectionTitle'),
                                       'rating_key': helpers.get_xml_attr(m, 'ratingKey'),
                                       'parent_rating_key': helpers.get_xml_attr(m, 'parentRatingKey'),
                                       'grandparent_rating_key': helpers.get_xml_attr(m, 'grandparentRatingKey'),
                                       'title': helpers.get_xml_attr(m, 'title'),
                                       'parent_title': helpers.get_xml_attr(m, 'parentTitle'),
                                       'grandparent_title': helpers.get_xml_attr(m, 'grandparentTitle'),
                                       'original_title': helpers.get_xml_attr(m, 'originalTitle'),
                                       'sort_title': helpers.get_xml_attr(m, 'titleSort'),
                                       'media_index': helpers.get_xml_attr(m, 'index'),
                                       'parent_media_index': helpers.get_xml_attr(m, 'parentIndex'),
                                       'studio': helpers.get_xml_attr(m, 'studio'),
                                       'content_rating': helpers.get_xml_attr(m, 'contentRating'),
                                       'summary': helpers.get_xml_attr(m, 'summary'),
                                       'tagline': helpers.get_xml_attr(m, 'tagline'),
                                       'rating': helpers.get_xml_attr(m, 'rating'),
                                       'rating_image': helpers.get_xml_attr(m, 'ratingImage'),
                                       'audience_rating': helpers.get_xml_attr(m, 'audienceRating'),
                                       'audience_rating_image': helpers.get_xml_attr(m, 'audienceRatingImage'),
                                       'user_rating': helpers.get_xml_attr(m, 'userRating'),
                                       'duration': helpers.get_xml_attr(m, 'duration'),
                                       'year': helpers.get_xml_attr(m, 'year'),
                                       'thumb': helpers.get_xml_attr(m, 'thumb'),
                                       'parent_thumb': helpers.get_xml_attr(m, 'parentThumb'),
                                       'grandparent_thumb': helpers.get_xml_attr(m, 'grandparentThumb'),
                                       'art': helpers.get_xml_attr(m, 'art'),
                                       'banner': helpers.get_xml_attr(m, 'banner'),
                                       'originally_available_at': helpers.get_xml_attr(m, 'originallyAvailableAt'),
                                       'added_at': helpers.get_xml_attr(m, 'addedAt'),
                                       'updated_at': helpers.get_xml_attr(m, 'updatedAt'),
                                       'last_viewed_at': helpers.get_xml_attr(m, 'lastViewedAt'),
                                       'guid': helpers.get_xml_attr(m, 'guid'),
                                       'directors': directors,
                                       'writers': writers,
                                       'actors': actors,
                                       'genres': genres,
                                       'labels': labels,
                                       'collections': collections,
                                       'full_title': helpers.get_xml_attr(m, 'title')
                                       }
                    children_list.append(children_output)

        output = {'children_count': helpers.cast_to_int(helpers.get_xml_attr(xml_head[0], 'size')),
                  'children_type': helpers.get_xml_attr(xml_head[0], 'viewGroup') or (children_list[0]['media_type'] if children_list else ''),
                  'title': helpers.get_xml_attr(xml_head[0], 'title2'),
                  'children_list': children_list
                  }

        return output

    def get_item_children_related(self, rating_key=''):
        """
        Return processed and validated children list.

        Output: array
        """
        children_data = self.get_children_list_related(rating_key, output_format='xml')

        try:
            xml_head = children_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_item_children_related: %s." % e)
            return []

        children_results_list = {'movie': [],
                                 'show': [],
                                 'season': [],
                                 'episode': [],
                                 'artist': [],
                                 'album': [],
                                 'track': [],
                                 }

        for a in xml_head:
            section_id = helpers.get_xml_attr(a, 'librarySectionID')
            hubs = a.getElementsByTagName('Hub')

            for h in hubs:
                size = helpers.get_xml_attr(h, 'size')
                media_type = helpers.get_xml_attr(h, 'type')
                title = helpers.get_xml_attr(h, 'title')
                hub_identifier = helpers.get_xml_attr(h, 'hubIdentifier')

                if size == '0' or not hub_identifier.startswith('collection.related') or \
                        media_type not in children_results_list:
                    continue

                result_data = []

                if h.getElementsByTagName('Video'):
                    result_data = h.getElementsByTagName('Video')
                if h.getElementsByTagName('Directory'):
                    result_data = h.getElementsByTagName('Directory')
                if h.getElementsByTagName('Track'):
                    result_data = h.getElementsByTagName('Track')

                for result in result_data:
                    children_output = {'section_id': section_id,
                                       'rating_key': helpers.get_xml_attr(result, 'ratingKey'),
                                       'parent_rating_key': helpers.get_xml_attr(result, 'parentRatingKey'),
                                       'media_index': helpers.get_xml_attr(result, 'index'),
                                       'title': helpers.get_xml_attr(result, 'title'),
                                       'parent_title': helpers.get_xml_attr(result, 'parentTitle'),
                                       'year': helpers.get_xml_attr(result, 'year'),
                                       'thumb': helpers.get_xml_attr(result, 'thumb'),
                                       'parent_thumb': helpers.get_xml_attr(a, 'thumb'),
                                       'duration': helpers.get_xml_attr(result, 'duration')
                                      }
                    children_results_list[media_type].append(children_output)

            output = {'results_count': sum(len(v) for k, v in children_results_list.items()),
                      'results_list': children_results_list,
                      }

            return output

    def get_servers_info(self):
        """
        Return the list of local servers.

        Output: array
        """
        recent = self.get_server_list(output_format='xml')

        try:
            xml_head = recent.getElementsByTagName('Server')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_server_list: %s." % e)
            return []

        server_info = []
        for a in xml_head:
            output = {"name": helpers.get_xml_attr(a, 'name'),
                      "machine_identifier": helpers.get_xml_attr(a, 'machineIdentifier'),
                      "host": helpers.get_xml_attr(a, 'host'),
                      "port": helpers.get_xml_attr(a, 'port'),
                      "version": helpers.get_xml_attr(a, 'version')
                      }

            server_info.append(output)

        return server_info

    def get_server_identity(self):
        """
        Return the local machine identity.

        Output: dict
        """
        identity = self.get_local_server_identity(output_format='xml')

        try:
            xml_head = identity.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_local_server_identity: %s." % e)
            return {}

        server_identity = {}
        for a in xml_head:
            server_identity = {"machine_identifier": helpers.get_xml_attr(a, 'machineIdentifier'),
                               "version": helpers.get_xml_attr(a, 'version')
                               }

        return server_identity

    def get_server_pref(self, pref=None):
        """
        Return a specified server preference.

        Parameters required:    pref { name of preference }

        Output: string
        """
        if pref:
            prefs = self.get_server_prefs(output_format='xml')

            try:
                xml_head = prefs.getElementsByTagName('Setting')
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_local_server_name: %s." % e)
                return ''

            pref_value = 'None'
            for a in xml_head:
                if helpers.get_xml_attr(a, 'id') == pref:
                    pref_value = helpers.get_xml_attr(a, 'value')
                    break

            return pref_value
        else:
            logger.debug("Tautulli Pmsconnect :: Server preferences queried but no parameter received.")
            return None

    def get_server_children(self):
        """
        Return processed and validated server libraries list.

        Output: array
        """
        libraries_data = self.get_libraries_list(output_format='xml')

        try:
            xml_head = libraries_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_libraries_list: %s." % e)
            return []

        libraries_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug("Tautulli Pmsconnect :: No libraries data.")
                    libraries_list = {'libraries_count': '0',
                                      'libraries_list': []
                                      }
                    return libraries_list

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
                for result in result_data:
                    libraries_output = {'section_id': helpers.get_xml_attr(result, 'key'),
                                        'section_type': helpers.get_xml_attr(result, 'type'),
                                        'section_name': helpers.get_xml_attr(result, 'title'),
                                        'agent': helpers.get_xml_attr(result, 'agent'),
                                        'thumb': helpers.get_xml_attr(result, 'thumb'),
                                        'art': helpers.get_xml_attr(result, 'art')
                                        }
                    libraries_list.append(libraries_output)

        output = {'libraries_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'title': helpers.get_xml_attr(xml_head[0], 'title1'),
                  'libraries_list': libraries_list
                  }

        return output

    def get_library_children_details(self, section_id='', section_type='', list_type='all', count='',
                                     rating_key='', label_key='', get_media_info=False):
        """
        Return processed and validated server library items list.

        Parameters required:    section_type { movie, show, episode, artist }
                                section_id { unique library key }

        Output: array
        """

        if section_type == 'movie':
            sort_type = '&type=1'
        elif section_type == 'show':
            sort_type = '&type=2'
        elif section_type == 'season':
            sort_type = '&type=3'
        elif section_type == 'episode':
            sort_type = '&type=4'
        elif section_type == 'artist':
            sort_type = '&type=8'
        elif section_type == 'album':
            sort_type = '&type=9'
        elif section_type == 'track':
            sort_type = '&type=10'
        elif section_type == 'photo':
            sort_type = ''
        elif section_type == 'photo_album':
            sort_type = '&type=14'
        elif section_type == 'picture':
            sort_type = '&type=13&clusterZoomLevel=1'
        elif section_type == 'clip':
            sort_type = '&type=12&clusterZoomLevel=1'
        else:
            sort_type = ''

        if str(rating_key).isdigit() and section_type != 'album':
            library_data = self.get_metadata_children(str(rating_key), output_format='xml')

            try:
                xml_head = library_data.getElementsByTagName('MediaContainer')
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_library_children_details: %s." % e)
                return []

        elif str(section_id).isdigit() or section_type == 'album':
            if section_type == 'album' and rating_key:
                sort_type += '&artist.id=' + str(rating_key)

            xml_head = self.fetch_library_list(
                section_id=str(section_id),
                list_type=list_type,
                count=count,
                sort_type=sort_type,
                label_key=label_key,
                output_format='xml'
            )

        else:
            logger.warn("Tautulli Pmsconnect :: get_library_children called by invalid section_id or rating_key provided.")
            return []


        library_count = '0'
        children_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug("Tautulli Pmsconnect :: No library data.")
                    children_list = {'library_count': '0',
                                     'children_list': []
                                     }
                    return children_list

            if rating_key:
                library_count = helpers.get_xml_attr(xml_head[0], 'size')
            else:
                library_count = helpers.get_xml_attr(xml_head[0], 'totalSize')

            # Get show/season info from xml_head

            item_main = []
            if a.getElementsByTagName('Directory'):
                dir_main = a.getElementsByTagName('Directory')
                item_main += [d for d in dir_main if helpers.get_xml_attr(d, 'ratingKey')]
            if a.getElementsByTagName('Video'):
                item_main += a.getElementsByTagName('Video')
            if a.getElementsByTagName('Track'):
                item_main += a.getElementsByTagName('Track')
            if a.getElementsByTagName('Photo'):
                item_main += a.getElementsByTagName('Photo')

            for item in item_main:
                media_type = helpers.get_xml_attr(item, 'type')
                if item.nodeName == 'Directory' and media_type == 'photo':
                    media_type = 'photo_album'

                item_info = {'section_id': helpers.get_xml_attr(a, 'librarySectionID'),
                             'media_type': media_type,
                             'rating_key': helpers.get_xml_attr(item, 'ratingKey'),
                             'parent_rating_key': helpers.get_xml_attr(item, 'parentRatingKey'),
                             'grandparent_rating_key': helpers.get_xml_attr(item, 'grandparentRatingKey'),
                             'title': helpers.get_xml_attr(item, 'title'),
                             'parent_title': helpers.get_xml_attr(item, 'parentTitle'),
                             'grandparent_title': helpers.get_xml_attr(item, 'grandparentTitle'),
                             'original_title': helpers.get_xml_attr(item, 'originalTitle'),
                             'sort_title': helpers.get_xml_attr(item, 'titleSort'),
                             'media_index': helpers.get_xml_attr(item, 'index'),
                             'parent_media_index': helpers.get_xml_attr(item, 'parentIndex'),
                             'year': helpers.get_xml_attr(item, 'year'),
                             'thumb': helpers.get_xml_attr(item, 'thumb'),
                             'parent_thumb': helpers.get_xml_attr(item, 'thumb'),
                             'grandparent_thumb': helpers.get_xml_attr(item, 'grandparentThumb'),
                             'added_at': helpers.get_xml_attr(item, 'addedAt')
                             }

                if get_media_info:
                    item_media = item.getElementsByTagName('Media')
                    for media in item_media:
                        media_info = {'container': helpers.get_xml_attr(media, 'container'),
                                      'bitrate': helpers.get_xml_attr(media, 'bitrate'),
                                      'video_codec': helpers.get_xml_attr(media, 'videoCodec'),
                                      'video_resolution': helpers.get_xml_attr(media, 'videoResolution').lower(),
                                      'video_framerate': helpers.get_xml_attr(media, 'videoFrameRate'),
                                      'audio_codec': helpers.get_xml_attr(media, 'audioCodec'),
                                      'audio_channels': helpers.get_xml_attr(media, 'audioChannels'),
                                      'file': helpers.get_xml_attr(media.getElementsByTagName('Part')[0], 'file'),
                                      'file_size': helpers.get_xml_attr(media.getElementsByTagName('Part')[0], 'size'),
                                      }
                        item_info.update(media_info)

                children_list.append(item_info)

        output = {'library_count': library_count,
                  'children_list': children_list
                  }

        return output

    def get_library_details(self):
        """
        Return processed and validated library statistics.

        Output: array
        """
        server_libraries = self.get_server_children()

        server_library_stats = []

        if server_libraries and server_libraries['libraries_count'] != '0':
            libraries_list = server_libraries['libraries_list']

            for library in libraries_list:
                section_type = library['section_type']
                section_id = library['section_id']
                children_list = self.get_library_children_details(section_id=section_id, section_type=section_type, count='1')

                if children_list:
                    library_stats = {'section_id': section_id,
                                     'section_name': library['section_name'],
                                     'section_type': section_type,
                                     'agent': library['agent'],
                                     'thumb': library['thumb'],
                                     'art': library['art'],
                                     'count': children_list['library_count'],
                                     'is_active': 1
                                     }

                    if section_type == 'show':
                        parent_list = self.get_library_children_details(section_id=section_id, section_type='season', count='1')
                        if parent_list:
                            parent_stats = {'parent_count': parent_list['library_count']}
                            library_stats.update(parent_stats)

                        child_list = self.get_library_children_details(section_id=section_id, section_type='episode', count='1')
                        if child_list:
                            child_stats = {'child_count': child_list['library_count']}
                            library_stats.update(child_stats)

                    if section_type == 'artist':
                        parent_list = self.get_library_children_details(section_id=section_id, section_type='album', count='1')
                        if parent_list:
                            parent_stats = {'parent_count': parent_list['library_count']}
                            library_stats.update(parent_stats)

                        child_list = self.get_library_children_details(section_id=section_id, section_type='track', count='1')
                        if child_list:
                            child_stats = {'child_count': child_list['library_count']}
                            library_stats.update(child_stats)

                    if section_type == 'photo':
                        parent_list = self.get_library_children_details(section_id=section_id, section_type='picture', count='1')
                        if parent_list:
                            parent_stats = {'parent_count': parent_list['library_count']}
                            library_stats.update(parent_stats)

                        child_list = self.get_library_children_details(section_id=section_id, section_type='clip', count='1')
                        if child_list:
                            child_stats = {'child_count': child_list['library_count']}
                            library_stats.update(child_stats)

                    server_library_stats.append(library_stats)

        return server_library_stats

    def get_library_label_details(self, section_id=''):
        labels_data = self.get_library_labels(section_id=str(section_id), output_format='xml')

        try:
            xml_head = labels_data.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_library_label_details: %s." % e)
            return None

        labels_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug("Tautulli Pmsconnect :: No labels data.")
                    return labels_list

            if a.getElementsByTagName('Directory'):
                labels_main = a.getElementsByTagName('Directory')
                for item in labels_main:
                    label = {'label_key': helpers.get_xml_attr(item, 'key'),
                             'label_title': helpers.get_xml_attr(item, 'title')
                             }
                    labels_list.append(label)

        return labels_list

    def get_image(self, img=None, width=1000, height=1500, opacity=None, background=None, blur=None,
                  img_format='png', clip=False, refresh=False, **kwargs):
        """
        Return image data as array.
        Array contains the image content type and image binary

        Parameters required:    img { Plex image location }
        Optional parameters:    width { the image width }
                                height { the image height }
                                opacity { the image opacity 0-100 }
                                background { the image background HEX }
                                blur { the image blur 0-100 }
        Output: array
        """

        width = width or 1000
        height = height or 1500

        if img:
            web_img = img.startswith('http')
            resource_img = img.startswith('/:/resources')

            if 'collection' in img and 'composite' in img:
                img = img.replace('composite', 'thumb')

            if refresh and not web_img and not resource_img:
                img_split = img.split('/')
                if img_split[-1].isdigit():
                    img = '/'.join(img_split[:-1])
                img = '{}/{}'.format(img.rstrip('/'), helpers.timestamp())

            if web_img:
                params = {'url': '%s' % img}
            elif clip:
                params = {'url': '%s&%s' % (img, urlencode({'X-Plex-Token': self.token}))}
            else:
                params = {'url': 'http://127.0.0.1:32400%s?%s' % (img, urlencode({'X-Plex-Token': self.token}))}

            params['width'] = width
            params['height'] = height
            params['format'] = img_format

            if opacity:
                params['opacity'] = opacity
            if background:
                params['background'] = background
            if blur:
                params['blur'] = blur

            uri = '/photo/:/transcode?%s' % urlencode(params)
            result = self.request_handler.make_request(uri=uri,
                                                       request_type='GET',
                                                       return_type=True)

            if result is None:
                return
            else:
                return result[0], result[1]

        else:
            logger.error("Tautulli Pmsconnect :: Image proxy queried but no input received.")

    def get_search_results(self, query='', limit=''):
        """
        Return processed list of search results.

        Output: array
        """
        search_results = self.get_search(query=query, limit=limit, output_format='xml')

        try:
            xml_head = search_results.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_search_result: %s." % e)
            return []

        search_results_list = {'movie': [],
                               'show': [],
                               'season': [],
                               'episode': [],
                               'artist': [],
                               'album': [],
                               'track': [],
                               'collection': []
                               }

        for a in xml_head:
            hubs = a.getElementsByTagName('Hub')

            for h in hubs:
                if helpers.get_xml_attr(h, 'size') == '0' or \
                    helpers.get_xml_attr(h, 'type') not in search_results_list:
                    continue

                if h.getElementsByTagName('Video'):
                    result_data = h.getElementsByTagName('Video')
                    for result in result_data:
                        rating_key = helpers.get_xml_attr(result, 'ratingKey')
                        metadata = self.get_metadata_details(rating_key=rating_key)
                        search_results_list[metadata['media_type']].append(metadata)

                if h.getElementsByTagName('Directory'):
                    result_data = h.getElementsByTagName('Directory')
                    for result in result_data:
                        rating_key = helpers.get_xml_attr(result, 'ratingKey')
                        metadata = self.get_metadata_details(rating_key=rating_key)
                        search_results_list[metadata['media_type']].append(metadata)

                        if metadata['media_type'] == 'show':
                            show_seasons = self.get_item_children(rating_key=metadata['rating_key'])
                            if show_seasons['children_count'] != 0:
                                for season in show_seasons['children_list']:
                                    if season['rating_key']:
                                        metadata = self.get_metadata_details(rating_key=season['rating_key'])
                                        search_results_list['season'].append(metadata)

                if h.getElementsByTagName('Track'):
                    result_data = h.getElementsByTagName('Track')
                    for result in result_data:
                        rating_key = helpers.get_xml_attr(result, 'ratingKey')
                        metadata = self.get_metadata_details(rating_key=rating_key)
                        search_results_list[metadata['media_type']].append(metadata)

        output = {'results_count': sum(len(s) for s in search_results_list.values()),
                  'results_list': search_results_list
                  }

        return output

    def get_rating_keys_list(self, rating_key='', media_type=''):
        """
        Return processed list of grandparent/parent/child rating keys.

        Output: array
        """

        if media_type == 'movie':
            key_list = {0: {'rating_key': int(rating_key)}}
            return key_list

        if media_type == 'artist' or media_type == 'album' or media_type == 'track':
            match_type = 'title'
        else:
            match_type = 'index'

        section_id = None
        library_name = None

        # get grandparent rating key
        if media_type == 'season' or media_type == 'album':
            try:
                metadata = self.get_metadata_details(rating_key=rating_key)
                title = metadata['parent_title']
                rating_key = metadata['parent_rating_key']
                section_id = metadata['section_id']
                library_name = metadata['library_name']
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to get parent_rating_key for get_rating_keys_list: %s." % e)
                return {}

        elif media_type == 'episode' or media_type == 'track':
            try:
                metadata = self.get_metadata_details(rating_key=rating_key)
                title = metadata['grandparent_title']
                rating_key = metadata['grandparent_rating_key']
                section_id = metadata['section_id']
                library_name = metadata['library_name']
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to get grandparent_rating_key for get_rating_keys_list: %s." % e)
                return {}

        elif media_type == 'show' or media_type == 'artist':
            try:
                metadata = self.get_metadata_details(rating_key=rating_key)
                title = metadata['title']
                section_id = metadata['section_id']
                library_name = metadata['library_name']
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to get grandparent_rating_key for get_rating_keys_list: %s." % e)
                return {}


        # get parent_rating_keys
        if media_type in ('artist', 'album', 'track'):
            sort_type = '&artist.id={}&type=9'.format(rating_key)
            xml_head = self.fetch_library_list(
                section_id=str(section_id),
                sort_type=sort_type,
                output_format='xml'
            )
        else:
            metadata = self.get_metadata_children(str(rating_key), output_format='xml')

            try:
                xml_head = metadata.getElementsByTagName('MediaContainer')
            except Exception as e:
                logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_rating_keys_list: %s." % e)
                return {}

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    return {}

            if a.getElementsByTagName('Directory'):
                parents_metadata = a.getElementsByTagName('Directory')
            else:
                parents_metadata = []

            parents = {}
            for item in parents_metadata:
                parent_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                parent_index = helpers.get_xml_attr(item, 'index')
                parent_title = helpers.get_xml_attr(item, 'title')

                if parent_rating_key:
                    # get rating_keys
                    metadata = self.get_metadata_children(str(parent_rating_key), output_format='xml')

                    try:
                        xml_head = metadata.getElementsByTagName('MediaContainer')
                    except Exception as e:
                        logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_rating_keys_list: %s." % e)
                        return {}

                    for a in xml_head:
                        if a.getAttribute('size'):
                            if a.getAttribute('size') == '0':
                                return {}

                        if a.getElementsByTagName('Video'):
                            children_metadata = a.getElementsByTagName('Video')
                        elif a.getElementsByTagName('Track'):
                            children_metadata = a.getElementsByTagName('Track')
                        else:
                            children_metadata = []

                        children = {}
                        for item in children_metadata:
                            child_rating_key = helpers.get_xml_attr(item, 'ratingKey')
                            child_index = helpers.get_xml_attr(item, 'index')
                            child_title = helpers.get_xml_attr(item, 'title')

                            if child_rating_key:
                                key = int(child_index) if child_index else child_title
                                children.update({key: {'rating_key': int(child_rating_key)}})

                    key = int(parent_index) if match_type == 'index' else str(parent_title).lower()
                    parents.update({key:
                                    {'rating_key': int(parent_rating_key),
                                     'children': children}
                                    })

        key = 0 if match_type == 'index' else str(title).lower()
        key_list = {key: {'rating_key': int(rating_key),
                          'children': parents},
                    'section_id': section_id,
                    'library_name': library_name
                    }

        return key_list

    def get_server_response(self):
        account_data = self.get_account(output_format='xml')

        try:
            xml_head = account_data.getElementsByTagName('MyPlex')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_server_response: %s." % e)
            return None

        server_response = {}

        for a in xml_head:
            server_response = {'mapping_state': helpers.get_xml_attr(a, 'mappingState'),
                               'mapping_error': helpers.get_xml_attr(a, 'mappingError'),
                               'sign_in_state': helpers.get_xml_attr(a, 'signInState'),
                               'public_address': helpers.get_xml_attr(a, 'publicAddress'),
                               'public_port': helpers.get_xml_attr(a, 'publicPort'),
                               'private_address': helpers.get_xml_attr(a, 'privateAddress'),
                               'private_port': helpers.get_xml_attr(a, 'privatePort')
                               }

            if server_response['mapping_state'] == 'unknown':
                server_response['reason'] = 'Plex remote access port mapping unknown'
            elif server_response['mapping_state'] not in ('mapped', 'waiting'):
                server_response['reason'] = 'Plex remote access port not mapped'
            elif server_response['mapping_error'] == 'unreachable':
                server_response['reason'] = 'Plex remote access port mapped, ' \
                                            'but the port is unreachable from Plex.tv'
            elif server_response['mapping_error'] == 'publisherror':
                server_response['reason'] = 'Plex remote access port mapped, ' \
                                            'but failed to publish the port to Plex.tv'
            else:
                server_response['reason'] = ''

        return server_response

    def get_update_staus(self):
        # Refresh the Plex updater status first
        self.put_updater()
        updater_status = self.get_updater(output_format='xml')

        try:
            xml_head = updater_status.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_update_staus: %s." % e)

            # Catch the malformed XML on certain PMX version.
            # XML parser helper returns empty list if there is an error parsing XML
            if updater_status == []:
                logger.warn("Plex API updater XML is broken on the current PMS version. Please update your PMS manually.")
                logger.info("Tautulli is unable to check for Plex updates. Disabling check for Plex updates.")

                # Disable check for Plex updates
                plexpy.CONFIG.MONITOR_PMS_UPDATES = 0
                plexpy.initialize_scheduler()
                plexpy.CONFIG.write()

            return {}

        updater_info = {}
        for a in xml_head:
            if a.getElementsByTagName('Release'):
                release = a.getElementsByTagName('Release')
                for item in release:
                    updater_info = {'can_install': helpers.get_xml_attr(a, 'canInstall'),
                                    'download_url': helpers.get_xml_attr(a, 'downloadURL'),
                                    'version': helpers.get_xml_attr(item, 'version'),
                                    'state': helpers.get_xml_attr(item, 'state'),
                                    'changelog': helpers.get_xml_attr(item, 'fixed')
                                    }

        return updater_info

    def set_server_version(self):
        identity = self.get_server_identity()
        version = identity.get('version', plexpy.CONFIG.PMS_VERSION)

        plexpy.CONFIG.__setattr__('PMS_VERSION', version)
        plexpy.CONFIG.write()

    def get_server_update_channel(self):
        if plexpy.CONFIG.PMS_UPDATE_CHANNEL == 'plex':
            update_channel_value = self.get_server_pref('ButlerUpdateChannel')

            if update_channel_value == '8':
                return 'beta'
            else:
                return 'public'

        return plexpy.CONFIG.PMS_UPDATE_CHANNEL

    @staticmethod
    def get_dynamic_range(stream):
        extended_display_title = helpers.get_xml_attr(stream, 'extendedDisplayTitle')
        bit_depth = helpers.cast_to_int(helpers.get_xml_attr(stream, 'bitDepth'))
        color_trc = helpers.get_xml_attr(stream, 'colorTrc')
        DOVI_profile = helpers.get_xml_attr(stream, 'DOVIProfile')

        HDR = bool(bit_depth > 8 and (color_trc == 'smpte2084' or color_trc == 'arib-std-b67'))
        DV = bool(DOVI_profile)

        if not HDR and not DV:
            return 'SDR'

        video_dynamic_range = []

        # HDR details got introduced with PMS version 1.25.6.5545
        if helpers.version_to_tuple(plexpy.CONFIG.PMS_VERSION) >= helpers.version_to_tuple('1.25.6.5545'):
            if 'Dolby Vision' in extended_display_title or 'DoVi' in extended_display_title:
                video_dynamic_range.append('Dolby Vision')
            if 'HLG' in extended_display_title:
                video_dynamic_range.append('HLG')
            if 'HDR10' in extended_display_title:
                video_dynamic_range.append('HDR10')
            elif 'HDR' in extended_display_title:
                video_dynamic_range.append('HDR')
        else:
            if DV:
                video_dynamic_range.append('Dolby Vision')
            elif HDR:
                # Exact HDR version needs PMS version 1.25.6.5545 or newer
                video_dynamic_range.append('HDR')

        if not video_dynamic_range:
            return 'SDR'
        return '/'.join(video_dynamic_range)

    def get_dvrs_list(self):
        dvrs_xml = self.get_dvrs(output_format='xml')

        try:
            xml_head = dvrs_xml.getElementsByTagName('MediaContainer')
        except Exception as e:
            logger.warn("Tautulli Pmsconnect :: Unable to parse XML for get_dvrs_list: %s." % e)

        dvrs_output = []

        for a in xml_head:
            dvrs = a.getElementsByTagName('Dvr')
            for dvr in dvrs:
                dvr_info = {
                    'key': helpers.get_xml_attr(dvr, 'key'),
                    'uuid': helpers.get_xml_attr(dvr, 'uuid'),
                    'language': helpers.get_xml_attr(dvr, 'language'),
                    'lineup_title': helpers.get_xml_attr(dvr, 'lineupTitle'),
                    'lineup': helpers.get_xml_attr(dvr, 'lineup'),
                    'country': helpers.get_xml_attr(dvr, 'country'),
                    'refreshedAt': helpers.get_xml_attr(dvr, 'refreshedAt'),
                    'epg_identifier': helpers.get_xml_attr(dvr, 'epgIdentifier')
                }
                dvrs_output.append(dvr_info)

        return dvrs_output
