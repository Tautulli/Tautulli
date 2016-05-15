#  This file is part of PlexPy.
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

import cherrypy

import common
import users


def get_session_info():
    """
    Returns the session info for the user session
    """
    from plexpy.webauth import SESSION_KEY

    _session = {'user_id': None,
                'user': None,
                'user_group': 'admin',
                'expiry': None}
    try:
        return cherrypy.session.get(SESSION_KEY, _session)
    except AttributeError as e:
        return _session

def get_session_user():
    """
    Returns the user_id for the current logged in session
    """
    _session = get_session_info()
    return _session['user'] if _session and _session['user'] else None

def get_session_user_id():
    """
    Returns the user_id for the current logged in session
    """
    _session = get_session_info()
    return str(_session['user_id']) if _session and _session['user_id'] else None

def get_session_shared_libraries():
    """
    Returns a tuple of section_id for the current logged in session
    """
    user_details = users.Users().get_details(user_id=get_session_user_id())
    return tuple(str(s) for s in user_details['shared_libraries'])

def get_session_library_filters():
    """
    Returns a dict of library filters for the current logged in session

        {'content_rating': ('PG', 'R')
         'labels': ('label1', label2')},

    """
    filters = users.Users().get_filters(user_id=get_session_user_id())
    return filters

def get_session_library_filters_type(filters, media_type=None):
    """
    Returns a dict of library filters for the current logged in session

        {'content_rating': ('PG', 'R')
         'labels': ('label1', label2')},

    """
    if media_type == 'movie':
        filters = filters.get('filter_movies', ())
    elif media_type == 'show' or media_type == 'season' or media_type == 'episode':
        filters = filters.get('filter_tv', ())
    elif media_type == 'artist' or media_type == 'album' or media_type == 'track':
        filters = filters.get('filter_music', ())
    elif media_type == 'photo' or media_type == 'photoAlbum' or media_type == 'picture':
        filters = filters.get('filter_photos', ())
    else:
        filters = filters.get('filter_all', ())

    content_rating = filters.get('content_rating', ())
    labels = filters.get('labels', ())

    return content_rating, tuple(f.lower() for f in labels)

def allow_session_user(user_id):
    """
    Returns True or False if the user_id is allowed for the current logged in session
    """
    session_user_id = get_session_user_id()
    if session_user_id and str(user_id) != session_user_id:
        return False
    return True

def allow_session_library(section_id):
    """
    Returns True or False if the section_id is allowed for the current logged in session
    """
    session_library_ids = get_session_shared_libraries()
    if session_library_ids and str(section_id) not in session_library_ids:
        return False
    return True

def friendly_name_to_username(list_of_dicts):
    """
    Reverts the friendly name back to the username of the current logged in session
    """
    session_user = get_session_user()
    session_user_id = get_session_user_id()
    
    if session_user_id:
        for d in list_of_dicts:
            if 'friendly_name' in d and d['friendly_name'] != session_user:
                d['friendly_name'] = session_user

    return list_of_dicts

def filter_session_info(list_of_dicts, filter_key=None):
    """
    Filters a list of dictionary items to only return the info for the current logged in session
    """
    session_user_id = get_session_user_id()
    
    if not session_user_id:
        return list_of_dicts

    session_library_ids = get_session_shared_libraries()
    session_library_filters = get_session_library_filters()

    list_of_dicts = friendly_name_to_username(list_of_dicts)

    if filter_key == 'user_id' and session_user_id:
        return [d for d in list_of_dicts if str(d.get('user_id','')) == session_user_id]

    elif filter_key == 'section_id' and session_library_ids:
        new_list_of_dicts = []

        for d in list_of_dicts:
            if str(d.get('section_id','')) not in session_library_ids:
                continue

            if d.get('media_type'):
                f_content_rating, f_labels = get_session_library_filters_type(session_library_filters,
                                                                              media_type=d['media_type'])

                d_content_rating = d.get('content_rating', '')
                d_labels = tuple(f.lower() for f in d.get('labels', ()))

                keep = False
                if not f_content_rating and not f_labels:
                    keep = True
                elif not f_content_rating and f_labels:
                    if set(d_labels).intersection(set(f_labels)):
                        keep = True
                elif f_content_rating and not f_labels:
                    if d_content_rating in f_content_rating:
                        keep = True
                elif f_content_rating and f_labels:
                    if d_content_rating in f_content_rating or set(d_labels).intersection(set(f_labels)):
                        keep = True

            if keep:
                new_list_of_dicts.append(d)

        return new_list_of_dicts

    return list_of_dicts

def mask_session_info(list_of_dicts, mask_metadata=True):
    """
    Masks user info in a list of dictionary items to only display info for the current logged in session
    """
    session_user_id = get_session_user_id()

    if not session_user_id:
        return list_of_dicts

    session_user = get_session_user()
    session_library_ids = get_session_shared_libraries()
    session_library_filters = get_session_library_filters()

    keys_to_mask = {'user_id': '',
                    'user': 'Plex User',
                    'friendly_name': 'Plex User',
                    'user_thumb': common.DEFAULT_USER_THUMB,
                    'ip_address': 'N/A',
                    'machine_id': '',
                    'player': 'Player'
                    }

    metadata_to_mask = {'media_index': '0',
                        'parent_media_index': '0',
                        'art': common.DEFAULT_ART,
                        'parent_thumb': common.DEFAULT_POSTER_THUMB,
                        'grandparent_thumb': common.DEFAULT_POSTER_THUMB,
                        'thumb': common.DEFAULT_POSTER_THUMB,
                        'bif_thumb': '',
                        'grandparent_title': 'Plex Media',
                        'parent_title': 'Plex Media',
                        'title': 'Plex Media',
                        'rating_key': '',
                        'parent_rating_key': '',
                        'grandparent_rating_key': '',
                        'year': '',
                        'last_played': 'Plex Media'
                        }

    list_of_dicts = friendly_name_to_username(list_of_dicts)

    for d in list_of_dicts:
        if session_user_id and not (str(d.get('user_id')) == session_user_id or d.get('user') == session_user):
            for k, v in keys_to_mask.iteritems():
                if k in d: d[k] = keys_to_mask[k]

        if not mask_metadata:
            continue

        if str(d.get('section_id','')) not in session_library_ids:
            for k, v in metadata_to_mask.iteritems():
                if k in d: d[k] = metadata_to_mask[k]
            continue

        media_type = d.get('media_type')
        if media_type:
            f_content_rating, f_labels = get_session_library_filters_type(session_library_filters,
                                                                      media_type=d['media_type'])

            d_content_rating = d.get('content_rating', '')
            d_labels = tuple(f.lower() for f in d.get('labels', ()))

            if not f_content_rating and not f_labels:
                continue
            elif not f_content_rating and f_labels:
                if set(d_labels).intersection(set(f_labels)):
                    continue
            elif f_content_rating and not f_labels:
                if d_content_rating in f_content_rating:
                    continue
            elif f_content_rating and f_labels:
                if d_content_rating in f_content_rating or set(d_labels).intersection(set(f_labels)):
                    continue

            for k, v in metadata_to_mask.iteritems():
                if k in d: d[k] = metadata_to_mask[k]

    return list_of_dicts