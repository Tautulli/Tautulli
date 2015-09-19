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

from plexpy import logger, helpers, users, http_handler
from urlparse import urlparse

import plexpy


class PmsConnect(object):
    """
    Retrieve data from Plex Server
    """

    def __init__(self):
        if plexpy.CONFIG.PMS_URL:
            url_parsed = urlparse(plexpy.CONFIG.PMS_URL)
            hostname = url_parsed.hostname
            port = url_parsed.port
            self.protocol = url_parsed.scheme
        else:
            hostname = plexpy.CONFIG.PMS_IP
            port = plexpy.CONFIG.PMS_PORT
            self.protocol = 'http'

        self.request_handler = http_handler.HTTPHandler(host=hostname,
                                                        port=port,
                                                        token=plexpy.CONFIG.PMS_TOKEN)

    """
    Return current sessions.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_sessions(self, output_format=''):
        uri = '/status/sessions'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return metadata for request item.

    Parameters required:    rating_key { Plex ratingKey }
    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_metadata(self, rating_key='', output_format=''):
        uri = '/library/metadata/' + rating_key
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return list of recently added items.

    Parameters required:    count { number of results to return }
    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_recently_added(self, count='0', output_format=''):
        uri = '/library/recentlyAdded?X-Plex-Container-Start=0&X-Plex-Container-Size=' + count
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return list of children in requested library item.

    Parameters required:    rating_key { ratingKey of parent }
    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_children_list(self, rating_key='', output_format=''):
        uri = '/library/metadata/' + rating_key + '/children'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)
        
        return request

    """
    Return list of local servers.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_server_list(self, output_format=''):
        uri = '/servers'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return the local servers preferences.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_server_prefs(self, output_format=''):
        uri = '/:/prefs'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return the local server identity.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_local_server_identity(self, output_format=''):
        uri = '/identity'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return list of libraries on server.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_libraries_list(self, output_format=''):
        uri = '/library/sections'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return list of items in library on server.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_library_list(self, section_key='', list_type='all', count='0', sort_type='', output_format=''):
        uri = '/library/sections/' + section_key + '/' + list_type +'?X-Plex-Container-Start=0&X-Plex-Container-Size=' + count + sort_type
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return sync item details.

    Parameters required:    sync_id { unique sync id for item }
    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_sync_item(self, sync_id=None, output_format=''):
        uri = '/sync/items/' + sync_id
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return sync transcode queue.

    Optional parameters:    output_format { dict, json }

    Output: array
    """
    def get_sync_transcode_queue(self, output_format=''):
        uri = '/sync/transcodeQueue'
        request = self.request_handler.make_request(uri=uri,
                                                    proto=self.protocol,
                                                    request_type='GET',
                                                    output_format=output_format)

        return request

    """
    Return processed and validated list of recently added items.

    Parameters required:    count { number of results to return }

    Output: array
    """
    def get_recently_added_details(self, count='0'):
        recent = self.get_recently_added(count, output_format='xml')

        try:
            xml_head = recent.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_recently_added.")
            return []

        recents_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    output = {'recently_added': []}
                    return output

            if a.getElementsByTagName('Directory'):
                recents_main = a.getElementsByTagName('Directory')
                for item in recents_main:
                    recent_type = helpers.get_xml_attr(item, 'type')
                    recent_items = {'type': recent_type,
                                    'rating_key': helpers.get_xml_attr(item, 'ratingKey'),
                                    'title': helpers.get_xml_attr(item, 'title'),
                                    'parent_title': helpers.get_xml_attr(item, 'parentTitle'),
                                    'thumb': helpers.get_xml_attr(item, 'thumb'),
                                    'added_at': helpers.get_xml_attr(item, 'addedAt')
                                    }
                    recents_list.append(recent_items)

            if a.getElementsByTagName('Video'):
                recents_main = a.getElementsByTagName('Video')
                for item in recents_main:
                    recent_type = helpers.get_xml_attr(item, 'type')

                    if recent_type == 'movie':
                        recent_items = {'type': recent_type,
                                        'rating_key': helpers.get_xml_attr(item, 'ratingKey'),
                                        'title': helpers.get_xml_attr(item, 'title'),
                                        'parent_title': helpers.get_xml_attr(item, 'parentTitle'),
                                        'year': helpers.get_xml_attr(item, 'year'),
                                        'thumb': helpers.get_xml_attr(item, 'thumb'),
                                        'added_at': helpers.get_xml_attr(item, 'addedAt')
                                        }
                        recents_list.append(recent_items)
                    else:
                        pass

        output = {'recently_added': sorted(recents_list, key=lambda k: k['added_at'], reverse=True)}
        return output

    """
    Return processed and validated metadata list for requested item.

    Parameters required:    rating_key { Plex ratingKey }

    Output: array
    """
    def get_metadata_details(self, rating_key=''):
        metadata = self.get_metadata(str(rating_key), output_format='xml')

        try:
            xml_head = metadata.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_metadata.")
            return []

        metadata_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') != '1':
                    metadata_list = {'metadata': None}
                    return metadata_list

            if a.getElementsByTagName('Directory'):
                metadata_main = a.getElementsByTagName('Directory')[0]
                metadata_type = helpers.get_xml_attr(metadata_main, 'type')
            elif a.getElementsByTagName('Video'):
                metadata_main = a.getElementsByTagName('Video')[0]
                metadata_type = helpers.get_xml_attr(metadata_main, 'type')
            elif a.getElementsByTagName('Track'):
                metadata_main = a.getElementsByTagName('Track')[0]
                metadata_type = helpers.get_xml_attr(metadata_main, 'type')
            else:
                logger.debug(u"Metadata failed")

        genres = []
        actors = []
        writers = []
        directors = []

        if metadata_main.getElementsByTagName('Genre'):
            for genre in metadata_main.getElementsByTagName('Genre'):
                genres.append(helpers.get_xml_attr(genre, 'tag'))

        if metadata_main.getElementsByTagName('Role'):
            for actor in metadata_main.getElementsByTagName('Role'):
                actors.append(helpers.get_xml_attr(actor, 'tag'))

        if metadata_main.getElementsByTagName('Writer'):
            for writer in metadata_main.getElementsByTagName('Writer'):
                writers.append(helpers.get_xml_attr(writer, 'tag'))

        if metadata_main.getElementsByTagName('Director'):
            for director in metadata_main.getElementsByTagName('Director'):
                directors.append(helpers.get_xml_attr(director, 'tag'))

        if metadata_type == 'show':
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'writers': writers,
                        'directors': directors,
                        'genres': genres,
                        'actors': actors
                        }
            metadata_list = {'metadata': metadata}
        elif metadata_type == 'season':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            show_details = self.get_metadata_details(parent_rating_key)
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': show_details['metadata']['summary'],
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': show_details['metadata']['duration'],
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'genres': genres,
                        'actors': actors,
                        'writers': writers,
                        'directors': directors
                        }
            metadata_list = {'metadata': metadata}
        elif metadata_type == 'episode':
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'writers': writers,
                        'directors': directors,
                        'genres': genres,
                        'actors': actors
                        }
            metadata_list = {'metadata': metadata}
        elif metadata_type == 'movie':
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'genres': genres,
                        'actors': actors,
                        'writers': writers,
                        'directors': directors
                        }
            metadata_list = {'metadata': metadata}
        elif metadata_type == 'artist':
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'writers': writers,
                        'directors': directors,
                        'genres': genres,
                        'actors': actors
                        }
            metadata_list = {'metadata': metadata}
        elif metadata_type == 'album':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            artist_details = self.get_metadata_details(parent_rating_key)
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': artist_details['metadata']['summary'],
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': helpers.get_xml_attr(metadata_main, 'year'),
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'genres': genres,
                        'actors': actors,
                        'writers': writers,
                        'directors': directors
                        }
            metadata_list = {'metadata': metadata}
        elif metadata_type == 'track':
            parent_rating_key = helpers.get_xml_attr(metadata_main, 'parentRatingKey')
            album_details = self.get_metadata_details(parent_rating_key)
            metadata = {'type': metadata_type,
                        'rating_key': helpers.get_xml_attr(metadata_main, 'ratingKey'),
                        'parent_rating_key': helpers.get_xml_attr(metadata_main, 'parentRatingKey'),
                        'grandparent_rating_key': helpers.get_xml_attr(metadata_main, 'grandparentRatingKey'),
                        'grandparent_title': helpers.get_xml_attr(metadata_main, 'grandparentTitle'),
                        'parent_index': helpers.get_xml_attr(metadata_main, 'parentIndex'),
                        'parent_title': helpers.get_xml_attr(metadata_main, 'parentTitle'),
                        'index': helpers.get_xml_attr(metadata_main, 'index'),
                        'studio': helpers.get_xml_attr(metadata_main, 'studio'),
                        'title': helpers.get_xml_attr(metadata_main, 'title'),
                        'content_rating': helpers.get_xml_attr(metadata_main, 'contentRating'),
                        'summary': helpers.get_xml_attr(metadata_main, 'summary'),
                        'tagline': helpers.get_xml_attr(metadata_main, 'tagline'),
                        'rating': helpers.get_xml_attr(metadata_main, 'rating'),
                        'duration': helpers.get_xml_attr(metadata_main, 'duration'),
                        'year': album_details['metadata']['year'],
                        'thumb': helpers.get_xml_attr(metadata_main, 'thumb'),
                        'parent_thumb': helpers.get_xml_attr(metadata_main, 'parentThumb'),
                        'grandparent_thumb': helpers.get_xml_attr(metadata_main, 'grandparentThumb'),
                        'art': helpers.get_xml_attr(metadata_main, 'art'),
                        'originally_available_at': helpers.get_xml_attr(metadata_main, 'originallyAvailableAt'),
                        'added_at': helpers.get_xml_attr(metadata_main, 'addedAt'),
                        'updated_at': helpers.get_xml_attr(metadata_main, 'updatedAt'),
                        'last_viewed_at': helpers.get_xml_attr(metadata_main, 'lastViewedAt'),
                        'guid': helpers.get_xml_attr(metadata_main, 'guid'),
                        'genres': genres,
                        'actors': actors,
                        'writers': writers,
                        'directors': directors
                        }
            metadata_list = {'metadata': metadata}
        else:
            return None

        return metadata_list

    """
    Return processed and validated session list.

    Output: array
    """
    def get_current_activity(self):
        session_data = self.get_sessions(output_format='xml')

        try:
            xml_head = session_data.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_sessions.")
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
                session_type = 'track'
                for session in session_data:
                    session_output = self.get_session_each(session_type, session)
                    session_list.append(session_output)
            if a.getElementsByTagName('Video'):
                session_data = a.getElementsByTagName('Video')
                session_type = 'video'
                for session in session_data:
                    session_output = self.get_session_each(session_type, session)
                    session_list.append(session_output)
            if a.getElementsByTagName('Photo'):
                session_data = a.getElementsByTagName('Photo')
                session_type = 'photo'
                for session in session_data:
                    session_output = self.get_session_each(session_type, session)
                    session_list.append(session_output)

        output = {'stream_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'sessions': session_list
                  }

        return output

    """
    Return selected data from current sessions.
    This function processes and validates session data

    Parameters required:    stream_type { track or video }
                            session { the session dictionary }
    Output: dict
    """
    def get_session_each(self, stream_type='', session=None):
        session_output = None
        user_data = users.Users()

        if stream_type == 'track':
            media_info = session.getElementsByTagName('Media')[0]
            audio_decision = 'direct play'
            audio_channels = helpers.get_xml_attr(media_info, 'audioChannels')
            audio_codec = helpers.get_xml_attr(media_info, 'audioCodec')
            container = helpers.get_xml_attr(media_info, 'container')
            bitrate = helpers.get_xml_attr(media_info, 'bitrate')
            duration = helpers.get_xml_attr(media_info, 'duration')
            progress = helpers.get_xml_attr(session, 'viewOffset')

            if session.getElementsByTagName('TranscodeSession'):
                transcode_session = session.getElementsByTagName('TranscodeSession')[0]
                throttled = helpers.get_xml_attr(transcode_session, 'throttled')
                transcode_progress = helpers.get_xml_attr(transcode_session, 'progress')
                transcode_speed = helpers.get_xml_attr(transcode_session, 'speed')
                audio_decision = helpers.get_xml_attr(transcode_session, 'audioDecision')
                transcode_audio_channels = helpers.get_xml_attr(transcode_session, 'audioChannels')
                transcode_audio_codec = helpers.get_xml_attr(transcode_session, 'audioCodec')
                transcode_container = helpers.get_xml_attr(transcode_session, 'container')
                transcode_protocol = helpers.get_xml_attr(transcode_session, 'protocol')
                duration = helpers.get_xml_attr(transcode_session, 'duration')
            else:
                throttled = '0'
                transcode_progress = '0'
                transcode_speed = ''
                transcode_audio_channels = ''
                transcode_audio_codec = ''
                transcode_container = ''
                transcode_protocol = ''

            user_details = user_data.get_user_details(
                user=helpers.get_xml_attr(session.getElementsByTagName('User')[0], 'title'))

            if helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier').endswith('_Track'):
                machine_id = helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier')[:-6]
            else:
                machine_id = helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier')

            session_output = {'session_key': helpers.get_xml_attr(session, 'sessionKey'),
                              'media_index': helpers.get_xml_attr(session, 'index'),
                              'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                              'art': helpers.get_xml_attr(session, 'art'),
                              'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                              'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                              'thumb': helpers.get_xml_attr(session, 'thumb'),
                              'bif_thumb': '',
                              'user': user_details['username'],
                              'user_id': user_details['user_id'],
                              'friendly_name': user_details['friendly_name'],
                              'user_thumb': user_details['thumb'],
                              'player': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'title'),
                              'platform': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'platform'),
                              'machine_id': machine_id,
                              'state': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'state'),
                              'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                              'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                              'title': helpers.get_xml_attr(session, 'title'),
                              'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                              'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                              'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                              'throttled': throttled,
                              'transcode_progress': transcode_progress,
                              'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                              'audio_decision': audio_decision,
                              'audio_channels': audio_channels,
                              'audio_codec': audio_codec,
                              'video_decision': '',
                              'video_codec': '',
                              'height': '',
                              'width': '',
                              'container': container,
                              'bitrate': bitrate,
                              'video_resolution': '',
                              'video_framerate': '',
                              'aspect_ratio': '',
                              'transcode_audio_channels': transcode_audio_channels,
                              'transcode_audio_codec': transcode_audio_codec,
                              'transcode_video_codec': '',
                              'transcode_width': '',
                              'transcode_height': '',
                              'transcode_container': transcode_container,
                              'transcode_protocol': transcode_protocol,
                              'duration': duration,
                              'progress': progress,
                              'progress_percent': str(helpers.get_percent(progress, duration)),
                              'type': 'track',
                              'indexes': 0
                              }

        elif stream_type == 'video':
            media_info = session.getElementsByTagName('Media')[0]
            audio_decision = 'direct play'
            audio_channels = helpers.get_xml_attr(media_info, 'audioChannels')
            audio_codec = helpers.get_xml_attr(media_info, 'audioCodec')
            video_decision = 'direct play'
            video_codec = helpers.get_xml_attr(media_info, 'videoCodec')
            container = helpers.get_xml_attr(media_info, 'container')
            bitrate = helpers.get_xml_attr(media_info, 'bitrate')
            video_resolution = helpers.get_xml_attr(media_info, 'videoResolution')
            video_framerate = helpers.get_xml_attr(media_info, 'videoFrameRate')
            aspect_ratio = helpers.get_xml_attr(media_info, 'aspectRatio')
            width = helpers.get_xml_attr(media_info, 'width')
            height = helpers.get_xml_attr(media_info, 'height')
            duration = helpers.get_xml_attr(media_info, 'duration')
            progress = helpers.get_xml_attr(session, 'viewOffset')

            if session.getElementsByTagName('TranscodeSession'):
                transcode_session = session.getElementsByTagName('TranscodeSession')[0]
                throttled = helpers.get_xml_attr(transcode_session, 'throttled')
                transcode_progress = helpers.get_xml_attr(transcode_session, 'progress')
                transcode_speed = helpers.get_xml_attr(transcode_session, 'speed')
                audio_decision = helpers.get_xml_attr(transcode_session, 'audioDecision')
                transcode_audio_channels = helpers.get_xml_attr(transcode_session, 'audioChannels')
                transcode_audio_codec = helpers.get_xml_attr(transcode_session, 'audioCodec')
                video_decision = helpers.get_xml_attr(transcode_session, 'videoDecision')
                transcode_video_codec = helpers.get_xml_attr(transcode_session, 'videoCodec')
                transcode_width = helpers.get_xml_attr(transcode_session, 'width')
                transcode_height = helpers.get_xml_attr(transcode_session, 'height')
                transcode_container = helpers.get_xml_attr(transcode_session, 'container')
                transcode_protocol = helpers.get_xml_attr(transcode_session, 'protocol')
            else:
                throttled = '0'
                transcode_progress = '0'
                transcode_speed = ''
                transcode_audio_channels = ''
                transcode_audio_codec = ''
                transcode_video_codec = ''
                transcode_width = ''
                transcode_height = ''
                transcode_container = ''
                transcode_protocol = ''

            media_info = session.getElementsByTagName('Media')[0]
            if media_info.getElementsByTagName('Part'):
                indexes = helpers.get_xml_attr(media_info.getElementsByTagName('Part')[0], 'indexes')
                part_id = helpers.get_xml_attr(media_info.getElementsByTagName('Part')[0], 'id')
                if indexes == 'sd':
                    bif_thumb = '/library/parts/' + part_id + '/indexes/sd/' + progress
                else:
                    bif_thumb = ''
            else:
                indexes = ''
                bif_thumb = ''

            if plexpy.CONFIG.PMS_USE_BIF and indexes == 'sd':
                use_indexes = 1
            else:
                use_indexes = 0

            user_details = user_data.get_user_details(
                user=helpers.get_xml_attr(session.getElementsByTagName('User')[0], 'title'))

            if helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier').endswith('_Video'):
                machine_id = helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier')[:-6]
            else:
                machine_id = helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier')

            if helpers.get_xml_attr(session, 'type') == 'episode':
                session_output = {'session_key': helpers.get_xml_attr(session, 'sessionKey'),
                                  'media_index': helpers.get_xml_attr(session, 'index'),
                                  'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                                  'art': helpers.get_xml_attr(session, 'art'),
                                  'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                                  'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                                  'thumb': helpers.get_xml_attr(session, 'thumb'),
                                  'bif_thumb': bif_thumb,
                                  'user': user_details['username'],
                                  'user_id': user_details['user_id'],
                                  'friendly_name': user_details['friendly_name'],
                                  'user_thumb': user_details['thumb'],
                                  'player': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'title'),
                                  'platform': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'platform'),
                                  'machine_id': machine_id,
                                  'state': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'state'),
                                  'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                                  'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                                  'title': helpers.get_xml_attr(session, 'title'),
                                  'year': helpers.get_xml_attr(session, 'year'),
                                  'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                                  'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                                  'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                                  'throttled': throttled,
                                  'transcode_progress': transcode_progress,
                                  'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                                  'audio_decision': audio_decision,
                                  'audio_channels': audio_channels,
                                  'audio_codec': audio_codec,
                                  'video_decision': video_decision,
                                  'video_codec': video_codec,
                                  'height': height,
                                  'width': width,
                                  'container': container,
                                  'bitrate': bitrate,
                                  'video_resolution': video_resolution,
                                  'video_framerate': video_framerate,
                                  'aspect_ratio': aspect_ratio,
                                  'transcode_audio_channels': transcode_audio_channels,
                                  'transcode_audio_codec': transcode_audio_codec,
                                  'transcode_video_codec': transcode_video_codec,
                                  'transcode_width': transcode_width,
                                  'transcode_height': transcode_height,
                                  'transcode_container': transcode_container,
                                  'transcode_protocol': transcode_protocol,
                                  'duration': duration,
                                  'progress': progress,
                                  'progress_percent': str(helpers.get_percent(progress, duration)),
                                  'indexes': use_indexes
                                  }
                if helpers.get_xml_attr(session, 'ratingKey').isdigit():
                    session_output['type'] = helpers.get_xml_attr(session, 'type')
                else:
                    session_output['type'] = 'clip'

            elif helpers.get_xml_attr(session, 'type') == 'movie':
                session_output = {'session_key': helpers.get_xml_attr(session, 'sessionKey'),
                                  'media_index': helpers.get_xml_attr(session, 'index'),
                                  'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                                  'art': helpers.get_xml_attr(session, 'art'),
                                  'thumb': helpers.get_xml_attr(session, 'thumb'),
                                  'bif_thumb': bif_thumb,
                                  'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                                  'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                                  'user': user_details['username'],
                                  'user_id': user_details['user_id'],
                                  'friendly_name': user_details['friendly_name'],
                                  'user_thumb': user_details['thumb'],
                                  'player': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'title'),
                                  'platform': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'platform'),
                                  'machine_id': machine_id,
                                  'state': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'state'),
                                  'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                                  'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                                  'title': helpers.get_xml_attr(session, 'title'),
                                  'year': helpers.get_xml_attr(session, 'year'),
                                  'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                                  'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                                  'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                                  'throttled': throttled,
                                  'transcode_progress': transcode_progress,
                                  'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                                  'audio_decision': audio_decision,
                                  'audio_channels': audio_channels,
                                  'audio_codec': audio_codec,
                                  'video_decision': video_decision,
                                  'video_codec': video_codec,
                                  'height': height,
                                  'width': width,
                                  'container': container,
                                  'bitrate': bitrate,
                                  'video_resolution': video_resolution,
                                  'video_framerate': video_framerate,
                                  'aspect_ratio': aspect_ratio,
                                  'transcode_audio_channels': transcode_audio_channels,
                                  'transcode_audio_codec': transcode_audio_codec,
                                  'transcode_video_codec': transcode_video_codec,
                                  'transcode_width': transcode_width,
                                  'transcode_height': transcode_height,
                                  'transcode_container': transcode_container,
                                  'transcode_protocol': transcode_protocol,
                                  'duration': duration,
                                  'progress': progress,
                                  'progress_percent': str(helpers.get_percent(progress, duration)),
                                  'indexes': use_indexes
                                  }
                if helpers.get_xml_attr(session, 'ratingKey').isdigit():
                    session_output['type'] = helpers.get_xml_attr(session, 'type')
                else:
                    session_output['type'] = 'clip'

            elif helpers.get_xml_attr(session, 'type') == 'clip':
                session_output = {'session_key': helpers.get_xml_attr(session, 'sessionKey'),
                                  'media_index': helpers.get_xml_attr(session, 'index'),
                                  'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                                  'art': helpers.get_xml_attr(session, 'art'),
                                  'thumb': helpers.get_xml_attr(session, 'thumb'),
                                  'bif_thumb': bif_thumb,
                                  'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                                  'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                                  'user': user_details['username'],
                                  'user_id': user_details['user_id'],
                                  'friendly_name': user_details['friendly_name'],
                                  'user_thumb': user_details['thumb'],
                                  'player': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'title'),
                                  'platform': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'platform'),
                                  'machine_id': machine_id,
                                  'state': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'state'),
                                  'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                                  'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                                  'title': helpers.get_xml_attr(session, 'title'),
                                  'year': helpers.get_xml_attr(session, 'year'),
                                  'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                                  'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                                  'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                                  'throttled': throttled,
                                  'transcode_progress': transcode_progress,
                                  'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                                  'audio_decision': audio_decision,
                                  'audio_channels': audio_channels,
                                  'audio_codec': audio_codec,
                                  'video_decision': video_decision,
                                  'video_codec': video_codec,
                                  'height': height,
                                  'width': width,
                                  'container': container,
                                  'bitrate': bitrate,
                                  'video_resolution': video_resolution,
                                  'video_framerate': video_framerate,
                                  'aspect_ratio': aspect_ratio,
                                  'transcode_audio_channels': transcode_audio_channels,
                                  'transcode_audio_codec': transcode_audio_codec,
                                  'transcode_video_codec': transcode_video_codec,
                                  'transcode_width': transcode_width,
                                  'transcode_height': transcode_height,
                                  'transcode_container': transcode_container,
                                  'transcode_protocol': transcode_protocol,
                                  'duration': duration,
                                  'progress': progress,
                                  'progress_percent': str(helpers.get_percent(progress, duration)),
                                  'type': helpers.get_xml_attr(session, 'type'),
                                  'indexes': 0
                                  }

        elif stream_type == 'photo':
            media_info = session.getElementsByTagName('Media')[0]
            video_decision = 'direct play'
            container = helpers.get_xml_attr(media_info, 'container')
            aspect_ratio = helpers.get_xml_attr(media_info, 'aspectRatio')
            width = helpers.get_xml_attr(media_info, 'width')
            height = helpers.get_xml_attr(media_info, 'height')

            if session.getElementsByTagName('TranscodeSession'):
                transcode_session = session.getElementsByTagName('TranscodeSession')[0]
                throttled = helpers.get_xml_attr(transcode_session, 'throttled')
                transcode_progress = helpers.get_xml_attr(transcode_session, 'progress')
                transcode_speed = helpers.get_xml_attr(transcode_session, 'speed')
                video_decision = helpers.get_xml_attr(transcode_session, 'videoDecision')
                transcode_video_codec = helpers.get_xml_attr(transcode_session, 'videoCodec')
                transcode_width = helpers.get_xml_attr(transcode_session, 'width')
                transcode_height = helpers.get_xml_attr(transcode_session, 'height')
                transcode_container = helpers.get_xml_attr(transcode_session, 'container')
                transcode_protocol = helpers.get_xml_attr(transcode_session, 'protocol')
            else:
                throttled = '0'
                transcode_progress = '0'
                transcode_speed = ''
                transcode_video_codec = ''
                transcode_width = ''
                transcode_height = ''
                transcode_container = ''
                transcode_protocol = ''

            user_details = user_data.get_user_details(
                user=helpers.get_xml_attr(session.getElementsByTagName('User')[0], 'title'))

            if helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier').endswith('_Photo'):
                machine_id = helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier')[:-6]
            else:
                machine_id = helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'machineIdentifier')

            session_output = {'session_key': helpers.get_xml_attr(session, 'sessionKey'),
                              'media_index': helpers.get_xml_attr(session, 'index'),
                              'parent_media_index': helpers.get_xml_attr(session, 'parentIndex'),
                              'art': helpers.get_xml_attr(session, 'art'),
                              'parent_thumb': helpers.get_xml_attr(session, 'parentThumb'),
                              'grandparent_thumb': helpers.get_xml_attr(session, 'grandparentThumb'),
                              'thumb': helpers.get_xml_attr(session, 'thumb'),
                              'bif_thumb': '',
                              'user': user_details['username'],
                              'user_id': user_details['user_id'],
                              'friendly_name': user_details['friendly_name'],
                              'user_thumb': user_details['thumb'],
                              'player': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'title'),
                              'platform': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'platform'),
                              'machine_id': machine_id,
                              'state': helpers.get_xml_attr(session.getElementsByTagName('Player')[0], 'state'),
                              'grandparent_title': helpers.get_xml_attr(session, 'grandparentTitle'),
                              'parent_title': helpers.get_xml_attr(session, 'parentTitle'),
                              'title': helpers.get_xml_attr(session, 'title'),
                              'year': helpers.get_xml_attr(session, 'year'),
                              'rating_key': helpers.get_xml_attr(session, 'ratingKey'),
                              'parent_rating_key': helpers.get_xml_attr(session, 'parentRatingKey'),
                              'grandparent_rating_key': helpers.get_xml_attr(session, 'grandparentRatingKey'),
                              'throttled': throttled,
                              'transcode_progress': transcode_progress,
                              'transcode_speed': str(round(helpers.cast_to_float(transcode_speed), 1)),
                              'audio_decision': '',
                              'audio_channels': '',
                              'audio_codec': '',
                              'video_decision': video_decision,
                              'video_codec': '',
                              'height': height,
                              'width': width,
                              'container': container,
                              'bitrate': '',
                              'video_resolution': '',
                              'video_framerate': '',
                              'aspect_ratio': aspect_ratio,
                              'transcode_audio_channels': '',
                              'transcode_audio_codec': '',
                              'transcode_video_codec': transcode_video_codec,
                              'transcode_width': transcode_width,
                              'transcode_height': transcode_height,
                              'transcode_container': transcode_container,
                              'transcode_protocol': transcode_protocol,
                              'duration': '',
                              'progress': '',
                              'progress_percent': '100',
                              'type': 'photo',
                              'indexes': 0
                              }

        else:
            logger.warn(u"No known stream types found in session list.")

        return session_output

    """
    Return processed and validated children list.

    Output: array
    """
    def get_item_children(self, rating_key=''):
        children_data = self.get_children_list(rating_key, output_format='xml')

        try:
            xml_head = children_data.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_children_list.")
            return []

        children_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"No children data.")
                    children_list = {'children_count': '0',
                                     'children_list': []
                                     }
                    return parent_list

            result_data = []

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
            if a.getElementsByTagName('Video'):
                result_data = a.getElementsByTagName('Video')
            if a.getElementsByTagName('Track'):
                result_data = a.getElementsByTagName('Track')

            if result_data:
                for result in result_data:
                    children_output = {'rating_key': helpers.get_xml_attr(result, 'ratingKey'),
                                       'index': helpers.get_xml_attr(result, 'index'),
                                       'title': helpers.get_xml_attr(result, 'title'),
                                       'thumb': helpers.get_xml_attr(result, 'thumb'),
                                       'parent_thumb': helpers.get_xml_attr(a, 'thumb'),
                                       'duration': helpers.get_xml_attr(result, 'duration')
                                      }
                    children_list.append(children_output)


        output = {'children_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'children_type': helpers.get_xml_attr(xml_head[0], 'viewGroup'),
                  'title': helpers.get_xml_attr(xml_head[0], 'title2'),
                  'children_list': children_list
                  }

        return output

    """
    Return the list of local servers.

    Output: array
    """
    def get_servers_info(self):
        recent = self.get_server_list(output_format='xml')

        try:
            xml_head = recent.getElementsByTagName('Server')
        except:
            logger.warn("Unable to parse XML for get_server_list.")
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

    """
    Return the local machine identity.

    Output: dict
    """
    def get_server_identity(self):
        identity = self.get_local_server_identity(output_format='xml')

        try:
            xml_head = identity.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_local_server_identity.")
            return []

        server_identity = {}
        for a in xml_head:
            server_identity = {"machine_identifier": helpers.get_xml_attr(a, 'machineIdentifier'),
                               "version": helpers.get_xml_attr(a, 'version')
                               }

        return server_identity

    """
    Return a specified server preference.

    Parameters required:    pref { name of preference }

    Output: string
    """
    def get_server_pref(self, pref=None):
        if pref:
            prefs = self.get_server_prefs(output_format='xml')

            try:
                xml_head = prefs.getElementsByTagName('Setting')
            except:
                logger.warn("Unable to parse XML for get_local_server_name.")
                return ''

            pref_value = 'None'
            for a in xml_head:
                if helpers.get_xml_attr(a, 'id') == pref:
                    pref_value = helpers.get_xml_attr(a, 'value')
                    break

            return pref_value
        else:
            logger.debug(u"Server preferences queried but no parameter received.")
            return None

    """
    Return processed and validated server libraries list.

    Output: array
    """
    def get_server_children(self):
        libraries_data = self.get_libraries_list(output_format='xml')

        try:
            xml_head = libraries_data.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_libraries_list.")
            return []

        libraries_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"No libraries data.")
                    libraries_list = {'libraries_count': '0',
                                      'libraries_list': []
                                      }
                    return libraries_list

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
                for result in result_data:
                    libraries_output = {'key': helpers.get_xml_attr(result, 'key'),
                                        'type': helpers.get_xml_attr(result, 'type'),
                                        'title': helpers.get_xml_attr(result, 'title'),
                                        'thumb': helpers.get_xml_attr(result, 'thumb')
                                        }
                    libraries_list.append(libraries_output)

        output = {'libraries_count': helpers.get_xml_attr(xml_head[0], 'size'),
                  'title': helpers.get_xml_attr(xml_head[0], 'title1'),
                  'libraries_list': libraries_list
                  }
        
        return output

    """
    Return processed and validated server library items list.

    Parameters required:    library_type { movie, show, episode, artist }
                            section_key { unique library key }

    Output: array
    """
    def get_library_children(self, library_type='', section_key='', list_type='all', sort_type = ''):

        # Currently only grab the library with 1 items so 'size' is not 0
        count = '1'

        if library_type == 'movie':
            sort_type = '&type=1'
        elif library_type == 'show':
            sort_type = '&type=2'
        elif library_type == 'episode':
            sort_type = '&type=4'
        elif library_type == 'album':
            list_type = 'albums'

        library_data = self.get_library_list(section_key, list_type, count, sort_type, output_format='xml')
        
        try:
            xml_head = library_data.getElementsByTagName('MediaContainer')
        except:
            logger.warn("Unable to parse XML for get_library_children.")
            return []

        library_list = []

        for a in xml_head:
            if a.getAttribute('size'):
                if a.getAttribute('size') == '0':
                    logger.debug(u"No library data.")
                    library_list = {'library_count': '0',
                                    'library_list': []
                                    }
                    return library_list

            if a.getElementsByTagName('Directory'):
                result_data = a.getElementsByTagName('Directory')
                for result in result_data:
                    library_output = {'key': helpers.get_xml_attr(result, 'key'),
                                      'type': helpers.get_xml_attr(result, 'type'),
                                      'title': helpers.get_xml_attr(result, 'title'),
                                      'thumb': helpers.get_xml_attr(result, 'thumb')
                                      }
                    library_list.append(library_output)

        output = {'library_count': helpers.get_xml_attr(xml_head[0], 'totalSize'),
                  'count_type': helpers.get_xml_attr(xml_head[0], 'title2'),
                  'library_list': library_list
                  }

        return output

    """
    Return processed and validated library statistics.

    Output: array
    """
    def get_library_stats(self, library_cards=''):
        server_libraries = self.get_server_children()

        library_keys = library_cards.split(', ')

        server_library_stats = []

        if server_libraries['libraries_count'] != '0':
            libraries_list = server_libraries['libraries_list']

            for library in libraries_list:
                library_type = library['type']
                section_key = library['key']
                if section_key in library_keys:
                    library_list = self.get_library_children(library_type, section_key)
                else:
                    continue

                if library_list['library_count'] != '0':
                    library_stats = {'title': library['title'],
                                     'thumb': library['thumb'],
                                     'count': library_list['library_count'],
                                     'count_type': library_list['count_type']
                                     }

                    if library_type == 'show':
                        episode_list = self.get_library_children(library_type='episode', section_key=section_key)
                        episode_stats = {'episode_count': episode_list['library_count'],
                                         'episode_count_type': 'All Episodes'
                                         }
                        library_stats.update(episode_stats)

                    if library_type == 'artist':
                        album_list = self.get_library_children(library_type='album', section_key=section_key)
                        album_stats = {'album_count': album_list['library_count'],
                                       'album_count_type': 'All Albums'
                                       }
                        library_stats.update(album_stats)

                    server_library_stats.append({'type': library_type,
                                                 'rows': library_stats})

        return server_library_stats

    """
    Return image data as array.
    Array contains the image content type and image binary

    Parameters required:    img { Plex image location }
    Optional parameters:    width { the image width }
                            height { the image height }
    Output: array
    """
    def get_image(self, img=None, width=None, height=None):
        if img:
            if width.isdigit() and height.isdigit():
                uri = '/photo/:/transcode?url=http://127.0.0.1:32400' + img + '&width=' + width + '&height=' + height
            else:
                uri = '/photo/:/transcode?url=http://127.0.0.1:32400' + img

            request, content_type = self.request_handler.make_request(uri=uri,
                                                                      proto=self.protocol,
                                                                      request_type='GET',
                                                                      return_type=True)

            return [request, content_type]
        else:
            logger.error("Image proxy queries but no input received.")
            return None
