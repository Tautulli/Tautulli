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

from plexpy import common


def get_session_info():
    """
    Returns the session info for the user session
    """
    from plexpy.webauth import SESSION_KEY

    if cherrypy.config.get('tools.auth.on'):
        _session = cherrypy.session.get(SESSION_KEY)
        if _session:
            return _session

    return {'user_id': None,
            'user': None,
            'user_group': 'admin',
            'user_libraries': None,
            'expiry': None}

def get_session_user():
    """
    Returns the user_id for the current logged in session
    """
    _session = get_session_info()
    return _session['user']

def get_session_user_id():
    """
    Returns the user_id for the current logged in session
    """
    _session = get_session_info()
    return str(_session['user_id']) if _session['user_id'] else None

def get_session_libraries():
    """
    Returns a tuple of section_id for the current logged in session
    """
    _session = get_session_info()
    return _session['user_libraries']

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
    session_library_ids = get_session_libraries()
    if session_library_ids and str(section_id) not in session_library_ids:
        return False
    return True

def filter_session_info(list_of_dicts, filter_key=None):
    """
    Filters a list of dictionary items to only return the info for the current logged in session
    """
    session_user_id = get_session_user_id()
    session_library_ids = get_session_libraries()

    list_of_dicts = friendly_name_to_username(list_of_dicts)

    if filter_key == 'user_id' and session_user_id:
        return [d for d in list_of_dicts if str(d.get('user_id','')) == session_user_id]

    elif filter_key == 'section_id' and session_library_ids:
        return [d for d in list_of_dicts if str(d.get('section_id','')) in session_library_ids]

    return list_of_dicts

def mask_session_info(list_of_dicts, mask_metadata=True):
    """
    Masks user info in a list of dictionary items to only display info for the current logged in session
    """
    session_user = get_session_user()
    session_user_id = get_session_user_id()
    session_library_ids = get_session_libraries()

    keys_to_mask = {'user_id': '',
                    'user': 'Plex User',
                    'friendly_name': 'Plex User',
                    'user_thumb': common.DEFAULT_USER_THUMB,
                    'ip_address': 'N/A',
                    'machine_id': '',
                    'player': 'Player'
                    }

    metadata_to_mask = {'media_index': '',
                        'parent_media_index': '',
                        'art': common.DEFAULT_ART,
                        'parent_thumb': common.DEFAULT_POSTER_THUMB,
                        'grandparent_thumb': common.DEFAULT_POSTER_THUMB,
                        'thumb': common.DEFAULT_POSTER_THUMB,
                        'bif_thumb': '',
                        'grandparent_title': '',
                        'parent_title': '',
                        'title': '',
                        'rating_key': '',
                        'parent_rating_key': '',
                        'grandparent_rating_key': '',
                        'year': ''
                        }

    list_of_dicts = friendly_name_to_username(list_of_dicts)

    for d in list_of_dicts:
        if session_user_id and not (str(d.get('user_id')) == session_user_id or d.get('user') == session_user):
            for k, v in keys_to_mask.iteritems():
                if k in d: d[k] = keys_to_mask[k]

        if mask_metadata and session_library_ids and str(d.get('section_id','')) not in session_library_ids:
            for k, v in metadata_to_mask.iteritems():
                if k in d: d[k] = metadata_to_mask[k]

    return list_of_dicts

def friendly_name_to_username(list_of_dicts):
    """
    Reverts the friendly name back to the username of the current logged in session
    """
    session_user = get_session_user()

    for d in list_of_dicts:
        if 'friendly_name' in d and d['friendly_name'] != session_user:
            d['friendly_name'] = session_user

    return list_of_dicts