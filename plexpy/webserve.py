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

import hashlib
import json
import os
import random
import shutil
import threading

import cherrypy
from cherrypy.lib.static import serve_file, serve_download
from cherrypy._cperror import NotFound

from hashing_passwords import make_hash
from mako.lookup import TemplateLookup
from mako import exceptions

import plexpy
import common
import config
import database
import datafactory
import graphs
import http_handler
import libraries
import log_reader
import logger
import notifiers
import plextv
import plexivity_import
import plexwatch_import
import pmsconnect
import users
import versioncheck
import web_socket
from plexpy.api import Api
from plexpy.api2 import API2
from plexpy.helpers import checked, addtoapi, get_ip, create_https_certificates, build_datatables_json
from plexpy.session import get_session_info, get_session_user_id, allow_session_user, allow_session_library
from plexpy.webauth import AuthController, requireAuth, member_of, name_is


def serve_template(templatename, **kwargs):
    interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), plexpy.CONFIG.INTERFACE)

    _hplookup = TemplateLookup(directories=[template_dir], default_filters=['unicode', 'h'])

    server_name = plexpy.CONFIG.PMS_NAME

    _session = get_session_info()

    try:
        template = _hplookup.get_template(templatename)
        return template.render(http_root=plexpy.HTTP_ROOT, server_name=server_name,
                               _session=_session, **kwargs)
    except:
        return exceptions.html_error_template().render()


class WebInterface(object):

    auth = AuthController()

    def __init__(self):
        self.interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/')

    @cherrypy.expose
    @requireAuth()
    def index(self):
        if plexpy.CONFIG.FIRST_RUN_COMPLETE:
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")
        else:
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "welcome")


    ##### Welcome #####

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def welcome(self, **kwargs):
        config = {
            "launch_browser": checked(plexpy.CONFIG.LAUNCH_BROWSER),
            "refresh_users_on_startup": checked(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "refresh_libraries_on_startup": checked(plexpy.CONFIG.REFRESH_LIBRARIES_ON_STARTUP),
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_is_remote": checked(plexpy.CONFIG.PMS_IS_REMOTE),
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "pms_ssl": checked(plexpy.CONFIG.PMS_SSL),
            "pms_uuid": plexpy.CONFIG.PMS_UUID,
            "movie_notify_enable": checked(plexpy.CONFIG.MOVIE_NOTIFY_ENABLE),
            "tv_notify_enable": checked(plexpy.CONFIG.TV_NOTIFY_ENABLE),
            "music_notify_enable": checked(plexpy.CONFIG.MUSIC_NOTIFY_ENABLE),
            "movie_logging_enable": checked(plexpy.CONFIG.MOVIE_LOGGING_ENABLE),
            "tv_logging_enable": checked(plexpy.CONFIG.TV_LOGGING_ENABLE),
            "music_logging_enable": checked(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "check_github": checked(plexpy.CONFIG.CHECK_GITHUB),
            "log_blacklist": checked(plexpy.CONFIG.LOG_BLACKLIST),
            "cache_images": checked(plexpy.CONFIG.CACHE_IMAGES)
        }

        # The setup wizard just refreshes the page on submit so we must redirect to home if config set.
        if plexpy.CONFIG.FIRST_RUN_COMPLETE:
            plexpy.initialize_scheduler()
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")
        else:
            return serve_template(templatename="welcome.html", title="Welcome", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_server_list")
    def discover(self, token=None, **kwargs):
        """ Get all your servers that are published to Plex.tv.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"clientIdentifier": "ds48g4r354a8v9byrrtr697g3g79w",
                      "httpsRequired": "0",
                      "ip": "xxx.xxx.xxx.xxx",
                      "label": "Winterfell-Server",
                      "local": "1",
                      "port": "32400",
                      "value": "xxx.xxx.xxx.xxx"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        if token:
            # Need to set token so result doesn't return http 401
            plexpy.CONFIG.__setattr__('PMS_TOKEN', token)
            plexpy.CONFIG.write()

        plex_tv = plextv.PlexTV()
        servers = plex_tv.discover()

        if servers:
            return servers


    ##### Home #####

    @cherrypy.expose
    @requireAuth()
    def home(self):
        config = {
            "home_sections": plexpy.CONFIG.HOME_SECTIONS,
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_cards": plexpy.CONFIG.HOME_STATS_CARDS,
            "home_library_cards": plexpy.CONFIG.HOME_LIBRARY_CARDS,
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_name": plexpy.CONFIG.PMS_NAME
        }
        return serve_template(templatename="index.html", title="Home", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_date_formats(self, **kwargs):
        """ Get the date and time formats used by PlexPy.

             ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {"date_format": "YYYY-MM-DD",
                     "time_format": "HH:mm",
                     }
            ```
        """
        if plexpy.CONFIG.DATE_FORMAT:
            date_format = plexpy.CONFIG.DATE_FORMAT
        else:
            date_format = 'YYYY-MM-DD'
        if plexpy.CONFIG.TIME_FORMAT:
            time_format = plexpy.CONFIG.TIME_FORMAT
        else:
            time_format = 'HH:mm'

        formats = {'date_format': date_format,
                   'time_format': time_format}

        return formats

    @cherrypy.expose
    @requireAuth()
    def get_current_activity(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
            result = pms_connect.get_current_activity()

            data_factory = datafactory.DataFactory()
            for session in result['sessions']:
                if not session['ip_address']:
                    ip_address = data_factory.get_session_ip(session['session_key'])
                    session['ip_address'] = ip_address

        except:
            return serve_template(templatename="current_activity.html", data=None)

        if result:
            return serve_template(templatename="current_activity.html", data=result)
        else:
            logger.warn(u"Unable to retrieve data for get_current_activity.")
            return serve_template(templatename="current_activity.html", data=None)

    @cherrypy.expose
    @requireAuth()
    def get_current_activity_instance(self, **kwargs):

        return serve_template(templatename="current_activity_instance.html", data=kwargs)

    @cherrypy.expose
    @requireAuth()
    def get_current_activity_header(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
            result = pms_connect.get_current_activity()
        except:
            return serve_template(templatename="current_activity_header.html", data=None)

        if result:
            data = {'stream_count': result['stream_count'],
                    'direct_play': 0,
                    'direct_stream': 0,
                    'transcode': 0}
            for s in result['sessions']:
                if s['media_type'] == 'track':
                    if s['audio_decision'] == 'transcode':
                        data['transcode'] += 1
                    elif s['audio_decision'] == 'copy':
                        data['direct_stream'] += 1
                    else:
                        data['direct_play'] += 1
                else:
                    if s['video_decision'] == 'transcode' or s['audio_decision'] == 'transcode':
                        data['transcode'] += 1
                    elif s['video_decision'] == 'direct copy' or s['audio_decision'] == 'copy play':
                        data['direct_stream'] += 1
                    else:
                        data['direct_play'] += 1

            return serve_template(templatename="current_activity_header.html", data=data)
        else:
            logger.warn(u"Unable to retrieve data for get_current_activity_header.")
            return serve_template(templatename="current_activity_header.html", data=None)

    @cherrypy.expose
    @requireAuth()
    def home_stats(self, **kwargs):
        grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES
        time_range = plexpy.CONFIG.HOME_STATS_LENGTH
        stats_type = plexpy.CONFIG.HOME_STATS_TYPE
        stats_count = plexpy.CONFIG.HOME_STATS_COUNT
        stats_cards = plexpy.CONFIG.HOME_STATS_CARDS
        notify_watched_percent = plexpy.CONFIG.NOTIFY_WATCHED_PERCENT

        data_factory = datafactory.DataFactory()
        stats_data = data_factory.get_home_stats(grouping=grouping,
                                                 time_range=time_range,
                                                 stats_type=stats_type,
                                                 stats_count=stats_count,
                                                 stats_cards=stats_cards,
                                                 notify_watched_percent=notify_watched_percent)

        return serve_template(templatename="home_stats.html", title="Stats", data=stats_data)

    @cherrypy.expose
    @requireAuth()
    def library_stats(self, **kwargs):
        data_factory = datafactory.DataFactory()

        library_cards = plexpy.CONFIG.HOME_LIBRARY_CARDS

        stats_data = data_factory.get_library_stats(library_cards=library_cards)

        return serve_template(templatename="library_stats.html", title="Library Stats", data=stats_data)

    @cherrypy.expose
    @requireAuth()
    def get_recently_added(self, count='0', **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(count=count)
        except IOError as e:
            return serve_template(templatename="recently_added.html", data=None)

        if result:
            return serve_template(templatename="recently_added.html", data=result['recently_added'])
        else:
            logger.warn(u"Unable to retrieve data for get_recently_added.")
            return serve_template(templatename="recently_added.html", data=None)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def delete_temp_sessions(self):

        result = database.delete_sessions()

        if result:
            return {'message': result}
        else:
            return {'message': 'no data received'}


    ##### Libraries #####

    @cherrypy.expose
    @requireAuth()
    def libraries(self):
        config = {
            "update_section_ids": plexpy.CONFIG.UPDATE_SECTION_IDS
        }

        return serve_template(templatename="libraries.html", title="Libraries", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi("get_libraries_table")
    def get_library_list(self, **kwargs):
        """ Get the data on the PlexPy libraries table.

            ```
            Required parameters:
                None

            Optional parameters:
                order_column (str):             "library_thumb", "section_name", "section_type", "count", "parent_count",
                                                "child_count", "last_accessed", "last_played", "plays", "duration"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Movies"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 10,
                     "recordsFiltered": 10,
                     "data":
                        [{"child_count": 3745,
                          "content_rating": "TV-MA",
                          "count": 62,
                          "do_notify": "Checked",
                          "do_notify_created": "Checked",
                          "duration": 1578037,
                          "id": 1128,
                          "keep_history": "Checked",
                          "labels": [],
                          "last_accessed": 1462693216,
                          "last_played": "Game of Thrones - The Red Woman",
                          "library_art": "/:/resources/show-fanart.jpg",
                          "library_thumb": "",
                          "media_index": 1,
                          "media_type": "episode",
                          "parent_count": 240,
                          "parent_media_index": 6,
                          "parent_title": "",
                          "plays": 772,
                          "rating_key": 153037,
                          "section_id": 2,
                          "section_name": "TV Shows",
                          "section_type": "Show",
                          "thumb": "/library/metadata/153036/thumb/1462175062",
                          "year": 2016
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("library_thumb", False, False),
                          ("section_name", True, True),
                          ("section_type", True, True),
                          ("count", True, True),
                          ("parent_count", True, True),
                          ("child_count", True, True),
                          ("last_accessed", True, False),
                          ("last_played", True, True),
                          ("plays", True, False),
                          ("duration", True, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "section_name")

        library_data = libraries.Libraries()
        library_list = library_data.get_datatables_list(kwargs=kwargs)

        return library_list

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_library_names")
    def get_library_sections(self, **kwargs):
        """ Get a list of library sections and ids on the PMS.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"section_id": 1, "section_name": "Movies"},
                     {"section_id": 7, "section_name": "Music"},
                     {"section_id": 2, "section_name": "TV Shows"},
                     {...}
                     ]
            ```
        """
        library_data = libraries.Libraries()
        result = library_data.get_sections()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_library_sections.")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def refresh_libraries_list(self, **kwargs):
        """ Refresh the libraries list on it's own thread. """
        threading.Thread(target=pmsconnect.refresh_libraries).start()
        logger.info(u"Manual libraries list refresh requested.")
        return True

    @cherrypy.expose
    @requireAuth()
    def library(self, section_id=None):
        if not allow_session_library(section_id):
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        config = {
            "get_file_sizes": plexpy.CONFIG.GET_FILE_SIZES,
            "get_file_sizes_hold": plexpy.CONFIG.GET_FILE_SIZES_HOLD
        }

        library_data = libraries.Libraries()
        if section_id:
            try:
                library_details = library_data.get_details(section_id=section_id)
            except:
                logger.warn(u"Unable to retrieve library details for section_id %s " % section_id)
                return serve_template(templatename="library.html", title="Library", data=None, config=config)
        else:
            logger.debug(u"Library page requested but no section_id received.")
            return serve_template(templatename="library.html", title="Library", data=None, config=config)

        return serve_template(templatename="library.html", title="Library", data=library_details, config=config)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def edit_library_dialog(self, section_id=None, **kwargs):
        library_data = libraries.Libraries()
        if section_id:
            result = library_data.get_details(section_id=section_id)
            status_message = ''
        else:
            result = None
            status_message = 'An error occured.'

        return serve_template(templatename="edit_library.html", title="Edit Library", data=result, status_message=status_message)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def edit_library(self, section_id=None, **kwargs):
        """ Update a library section on PlexPy.

            ```
            Required parameters:
                section_id (str):           The id of the Plex library section

            Optional parameters:
                custom_thumb (str):         The URL for the custom library thumbnail
                do_notify (int):            0 or 1
                do_notify_created (int):    0 or 1
                keep_history (int):         0 or 1

            Returns:
                None
            ```
        """
        custom_thumb = kwargs.get('custom_thumb', '')
        do_notify = kwargs.get('do_notify', 0)
        do_notify_created = kwargs.get('do_notify_created', 0)
        keep_history = kwargs.get('keep_history', 0)

        library_data = libraries.Libraries()
        if section_id:
            try:
                library_data.set_config(section_id=section_id,
                                        custom_thumb=custom_thumb,
                                        do_notify=do_notify,
                                        do_notify_created=do_notify_created,
                                        keep_history=keep_history)

                return "Successfully updated library."
            except:
                return "Failed to update library."

    @cherrypy.expose
    @requireAuth()
    def get_library_watch_time_stats(self, section_id=None, **kwargs):
        if not allow_session_library(section_id):
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_watch_time_stats(section_id=section_id)
        else:
            result = None

        if result:
            return serve_template(templatename="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            logger.warn(u"Unable to retrieve data for get_library_watch_time_stats.")
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def get_library_user_stats(self, section_id=None, **kwargs):
        if not allow_session_library(section_id):
            return serve_template(templatename="library_user_stats.html", data=None, title="Player Stats")

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_user_stats(section_id=section_id)
        else:
            result = None

        if result:
            return serve_template(templatename="library_user_stats.html", data=result, title="Player Stats")
        else:
            logger.warn(u"Unable to retrieve data for get_library_user_stats.")
            return serve_template(templatename="library_user_stats.html", data=None, title="Player Stats")

    @cherrypy.expose
    @requireAuth()
    def get_library_recently_watched(self, section_id=None, limit='10', **kwargs):
        if not allow_session_library(section_id):
            return serve_template(templatename="user_recently_watched.html", data=None, title="Recently Watched")

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_recently_watched(section_id=section_id, limit=limit)
        else:
            result = None

        if result:
            return serve_template(templatename="user_recently_watched.html", data=result, title="Recently Watched")
        else:
            logger.warn(u"Unable to retrieve data for get_library_recently_watched.")
            return serve_template(templatename="user_recently_watched.html", data=None, title="Recently Watched")

    @cherrypy.expose
    @requireAuth()
    def get_library_recently_added(self, section_id=None, limit='10', **kwargs):
        if not allow_session_library(section_id):
            return serve_template(templatename="library_recently_added.html", data=None, title="Recently Added")

        if section_id:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(section_id=section_id, count=limit)
        else:
            result = None

        if result:
            return serve_template(templatename="library_recently_added.html", data=result['recently_added'], title="Recently Added")
        else:
            logger.warn(u"Unable to retrieve data for get_library_recently_added.")
            return serve_template(templatename="library_recently_added.html", data=None, title="Recently Added")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_library_media_info(self, section_id=None, section_type=None, rating_key=None, refresh='', **kwargs):
        """ Get the data on the PlexPy media info tables.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section, OR
                rating_key (str):               The grandparent or parent rating key

            Optional parameters:
                section_type (str):             "movie", "show", "artist", "photo"
                order_column (str):             "added_at", "title", "container", "bitrate", "video_codec",
                                                "video_resolution", "video_framerate", "audio_codec", "audio_channels",
                                                "file_size", "last_played", "play_count"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Thrones"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 82,
                     "recordsFiltered": 82,
                     "filtered_file_size": 2616760056742,
                     "total_file_size": 2616760056742,
                     "data":
                        [{"added_at": "1403553078",
                          "audio_channels": "",
                          "audio_codec": "",
                          "bitrate": "",
                          "container": "",
                          "file_size": 253660175293,
                          "grandparent_rating_key": "",
                          "last_played": 1462380698,
                          "media_index": "1",
                          "media_type": "show",
                          "parent_media_index": "",
                          "parent_rating_key": "",
                          "play_count": 15,
                          "rating_key": "1219",
                          "section_id": 2,
                          "section_type": "show",
                          "thumb": "/library/metadata/1219/thumb/1436265995",
                          "title": "Game of Thrones",
                          "video_codec": "",
                          "video_framerate": "",
                          "video_resolution": "",
                          "year": "2011"
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("added_at", True, False),
                          ("title", True, True),
                          ("container", True, True),
                          ("bitrate", True, True),
                          ("video_codec", True, True),
                          ("video_resolution", True, True),
                          ("video_framerate", True, True),
                          ("audio_codec", True, True),
                          ("audio_channels", True, True),
                          ("file_size", True, False),
                          ("last_played", True, False),
                          ("play_count", True, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "title")

        if refresh == 'true':
            refresh = True
        else:
            refresh = False

        library_data = libraries.Libraries()
        result = library_data.get_datatables_media_info(section_id=section_id,
                                                        section_type=section_type,
                                                        rating_key=rating_key,
                                                        refresh=refresh,
                                                        kwargs=kwargs)

        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_media_info_file_sizes(self, section_id=None, rating_key=None):
        get_file_sizes_hold = plexpy.CONFIG.GET_FILE_SIZES_HOLD
        section_ids = set(get_file_sizes_hold['section_ids'])
        rating_keys = set(get_file_sizes_hold['rating_keys'])

        if (section_id and section_id not in section_ids) or (rating_key and rating_key not in rating_keys):
            if section_id:
                section_ids.add(section_id)
            elif rating_key:
                rating_keys.add(rating_key)
            plexpy.CONFIG.GET_FILE_SIZES_HOLD = {'section_ids': list(section_ids), 'rating_keys': list(rating_keys)}

            library_data = libraries.Libraries()
            result = library_data.get_media_info_file_sizes(section_id=section_id,
                                                            rating_key=rating_key)

            if section_id:
                section_ids.remove(section_id)
            elif rating_key:
                rating_keys.remove(rating_key)
            plexpy.CONFIG.GET_FILE_SIZES_HOLD = {'section_ids': list(section_ids), 'rating_keys': list(rating_keys)}
        else:
            result = False

        return {'success': result}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_all_library_history(self, section_id, **kwargs):
        """ Delete all PlexPy history for a specific library.

            ```
            Required parameters:
                section_id (str):       The id of the Plex library section

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        library_data = libraries.Libraries()

        if section_id:
            delete_row = library_data.delete_all_history(section_id=section_id)

            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_library(self, section_id, **kwargs):
        """ Delete a library section from PlexPy. Also erases all history for the library.

            ```
            Required parameters:
                section_id (str):       The id of the Plex library section

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        library_data = libraries.Libraries()

        if section_id:
            delete_row = library_data.delete(section_id=section_id)

            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def undelete_library(self, section_id=None, section_name=None, **kwargs):
        """ Restore a deleted library section to PlexPy.

            ```
            Required parameters:
                section_id (str):       The id of the Plex library section
                section_name (str):     The name of the Plex library section

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        library_data = libraries.Libraries()

        if section_id:
            delete_row = library_data.undelete(section_id=section_id)

            if delete_row:
                return {'message': delete_row}
        elif section_name:
            delete_row = library_data.undelete(section_name=section_name)

            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def update_section_ids(self, **kwargs):

        logger.debug(u"Manual database section_id update called.")

        result = libraries.update_section_ids()

        if result:
            return "Updated all section_id's in database."
        else:
            return "Unable to update section_id's in database. See logs for details."

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_datatable_media_info_cache(self, section_id, **kwargs):
        """ Delete the media info table cache for a specific library.

            ```
            Required parameters:
                section_id (str):       The id of the Plex library section

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        get_file_sizes_hold = plexpy.CONFIG.GET_FILE_SIZES_HOLD
        section_ids = set(get_file_sizes_hold['section_ids'])

        if section_id not in section_ids:
            if section_id:
                library_data = libraries.Libraries()
                delete_row = library_data.delete_datatable_media_info_cache(section_id=section_id)

                if delete_row:
                    return {'message': delete_row}
            else:
                return {'message': 'no data received'}
        else:
            return {'message': 'Cannot refresh library while getting file sizes.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def delete_duplicate_libraries(self):
        library_data = libraries.Libraries()

        result = library_data.delete_duplicate_libraries()

        if result:
            return {'message': result}
        else:
            return {'message': 'Unable to delete duplicate libraries from the database.'}

    ##### Users #####

    @cherrypy.expose
    @requireAuth()
    def users(self):
        return serve_template(templatename="users.html", title="Users")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi("get_users_table")
    def get_user_list(self, **kwargs):
        """ Get the data on PlexPy users table.

            ```
            Required parameters:
                None

            Optional parameters:
                order_column (str):             "user_thumb", "friendly_name", "last_seen", "ip_address", "platform",
                                                "player", "last_played", "plays", "duration"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Jon Snow"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 10,
                     "recordsFiltered": 10,
                     "data":
                        [{"allow_guest": "Checked",
                          "do_notify": "Checked",
                          "duration": 2998290,
                          "friendly_name": "Jon Snow",
                          "id": 1121,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "keep_history": "Checked",
                          "last_played": "Game of Thrones - The Red Woman",
                          "last_seen": 1462591869,
                          "media_index": 1,
                          "media_type": "episode",
                          "parent_media_index": 6,
                          "parent_title": "",
                          "platform": "Chrome",
                          "player": "Plex Web (Chrome)",
                          "plays": 487,
                          "rating_key": 153037,
                          "thumb": "/library/metadata/153036/thumb/1462175062",
                          "transcode_decision": "transcode",
                          "user_id": 133788,
                          "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar",
                          "year": 2016
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("user_thumb", False, False),
                          ("friendly_name", True, True),
                          ("last_seen", True, False),
                          ("ip_address", True, True),
                          ("platform", True, True),
                          ("player", True, True),
                          ("last_played", True, False),
                          ("plays", True, False),
                          ("duration", True, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "friendly_name")

        user_data = users.Users()
        user_list = user_data.get_datatables_list(kwargs=kwargs)

        return user_list

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def refresh_users_list(self, **kwargs):
        """ Refresh the users list on it's own thread. """
        threading.Thread(target=plextv.refresh_users).start()
        logger.info(u"Manual users list refresh requested.")
        return True

    @cherrypy.expose
    @requireAuth()
    def user(self, user_id=None):
        if not allow_session_user(user_id):
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        user_data = users.Users()
        if user_id:
            try:
                user_details = user_data.get_details(user_id=user_id)
            except:
                logger.warn(u"Unable to retrieve user details for user_id %s " % user_id)
                return serve_template(templatename="user.html", title="User", data=None)
        else:
            logger.debug(u"User page requested but no user_id received.")
            return serve_template(templatename="user.html", title="User", data=None)

        return serve_template(templatename="user.html", title="User", data=user_details)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def edit_user_dialog(self, user=None, user_id=None, **kwargs):
        user_data = users.Users()
        if user_id:
            result = user_data.get_details(user_id=user_id)
            status_message = ''
        else:
            result = None
            status_message = 'An error occured.'

        return serve_template(templatename="edit_user.html", title="Edit User", data=result, status_message=status_message)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def edit_user(self, user_id=None, **kwargs):
        """ Update a user on PlexPy.

            ```
            Required parameters:
                user_id (str):              The id of the Plex user

            Optional paramters:
                friendly_name(str):         The friendly name of the user
                custom_thumb (str):         The URL for the custom user thumbnail
                do_notify (int):            0 or 1
                do_notify_created (int):    0 or 1
                keep_history (int):         0 or 1

            Returns:
                None
            ```
        """
        friendly_name = kwargs.get('friendly_name', '')
        custom_thumb = kwargs.get('custom_thumb', '')
        do_notify = kwargs.get('do_notify', 0)
        keep_history = kwargs.get('keep_history', 0)
        allow_guest = kwargs.get('allow_guest', 0)

        user_data = users.Users()
        if user_id:
            try:
                user_data.set_config(user_id=user_id,
                                     friendly_name=friendly_name,
                                     custom_thumb=custom_thumb,
                                     do_notify=do_notify,
                                     keep_history=keep_history,
                                     allow_guest=allow_guest)
                status_message = "Successfully updated user."
                return status_message
            except:
                status_message = "Failed to update user."
                return status_message

    @cherrypy.expose
    @requireAuth()
    def get_user_watch_time_stats(self, user=None, user_id=None, **kwargs):
        if not allow_session_user(user_id):
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

        if user_id or user:
            user_data = users.Users()
            result = user_data.get_watch_time_stats(user_id=user_id)
        else:
            result = None

        if result:
            return serve_template(templatename="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            logger.warn(u"Unable to retrieve data for get_user_watch_time_stats.")
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def get_user_player_stats(self, user=None, user_id=None, **kwargs):
        if not allow_session_user(user_id):
            return serve_template(templatename="user_player_stats.html", data=None, title="Player Stats")

        if user_id or user:
            user_data = users.Users()
            result = user_data.get_player_stats(user_id=user_id)
        else:
            result = None

        if result:
            return serve_template(templatename="user_player_stats.html", data=result, title="Player Stats")
        else:
            logger.warn(u"Unable to retrieve data for get_user_player_stats.")
            return serve_template(templatename="user_player_stats.html", data=None, title="Player Stats")

    @cherrypy.expose
    @requireAuth()
    def get_user_recently_watched(self, user=None, user_id=None, limit='10', **kwargs):
        if not allow_session_user(user_id):
            return serve_template(templatename="user_recently_watched.html", data=None, title="Recently Watched")

        if user_id or user:
            user_data = users.Users()
            result = user_data.get_recently_watched(user_id=user_id, limit=limit)
        else:
            result = None

        if result:
            return serve_template(templatename="user_recently_watched.html", data=result, title="Recently Watched")
        else:
            logger.warn(u"Unable to retrieve data for get_user_recently_watched.")
            return serve_template(templatename="user_recently_watched.html", data=None, title="Recently Watched")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_user_ips(self, user_id=None, **kwargs):
        """ Get the data on PlexPy users IP table.

            ```
            Required parameters:
                user_id (str):                  The id of the Plex user

            Optional parameters:
                order_column (str):             "last_seen", "ip_address", "platform", "player",
                                                "last_played", "play_count"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "xxx.xxx.xxx.xxx"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 2344,
                     "recordsFiltered": 10,
                     "data":
                        [{"friendly_name": "Jon Snow",
                          "id": 1121,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "last_played": "Game of Thrones - The Red Woman",
                          "last_seen": 1462591869,
                          "media_index": 1,
                          "media_type": "episode",
                          "parent_media_index": 6,
                          "parent_title": "",
                          "platform": "Chrome",
                          "play_count": 149,
                          "player": "Plex Web (Chrome)",
                          "rating_key": 153037,
                          "thumb": "/library/metadata/153036/thumb/1462175062",
                          "transcode_decision": "transcode",
                          "user_id": 133788,
                          "year": 2016
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("last_seen", True, False),
                          ("ip_address", True, True),
                          ("platform", True, True),
                          ("player", True, True),
                          ("last_played", True, True),
                          ("play_count", True, True)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "last_seen")

        user_data = users.Users()
        history = user_data.get_datatables_unique_ips(user_id=user_id, kwargs=kwargs)

        return history

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_user_logins(self, user_id=None, **kwargs):
        """ Get the data on PlexPy user login table.

            ```
            Required parameters:
                user_id (str):                  The id of the Plex user

            Optional parameters:
                order_column (str):             "date", "time", "ip_address", "host", "os", "browser"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "xxx.xxx.xxx.xxx"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 2344,
                     "recordsFiltered": 10,
                     "data":
                        [{"browser": "Safari 7.0.3",
                          "friendly_name": "Jon Snow",
                          "host": "http://plexpy.castleblack.com",
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "os": "Mac OS X",
                          "timestamp": 1462591869,
                          "user": "LordCommanderSnow",
                          "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
                          "user_group": "guest",
                          "user_id": 133788
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("timestamp", True, False),
                          ("ip_address", True, True),
                          ("host", True, True),
                          ("os", True, True),
                          ("browser", True, True)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "timestamp")

        user_data = users.Users()
        history = user_data.get_datatables_user_login(user_id=user_id, kwargs=kwargs)

        return history

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_all_user_history(self, user_id, **kwargs):
        """ Delete all PlexPy history for a specific user.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        user_data = users.Users()

        if user_id:
            delete_row = user_data.delete_all_history(user_id=user_id)
            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_user(self, user_id, **kwargs):
        """ Delete a user from PlexPy. Also erases all history for the user.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        user_data = users.Users()

        if user_id:
            delete_row = user_data.delete(user_id=user_id)

            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def undelete_user(self, user_id=None, username=None, **kwargs):
        """ Restore a deleted user to PlexPy.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user
                username (str):         The username of the Plex user

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        user_data = users.Users()

        if user_id:
            delete_row = user_data.undelete(user_id=user_id)

            if delete_row:
                return {'message': delete_row}
        elif username:
            delete_row = user_data.undelete(username=username)

            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}


    ##### History #####

    @cherrypy.expose
    @requireAuth()
    def history(self):
        return serve_template(templatename="history.html", title="History")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_history(self, user=None, user_id=None, grouping=None, **kwargs):
        """ Get the PlexPy history.

            ```
            Required parameters:
                None

            Optional parameters:
                grouping (int):                 0 or 1
                user (str):                     "Jon Snow"
                user_id (int):                  133788
                rating_key (int):               4348
                parent_rating_key (int):        544
                grandparent_rating_key (int):   351
                start_date (str):               "YYYY-MM-DD"
                section_id (int):               2
                media_type (str):               "movie", "episode", "track"
                transcode_decision (str):       "direct play", "copy", "transcode",
                order_column (str):             "date", "friendly_name", "ip_address", "platform", "player",
                                                "full_title", "started", "paused_counter", "stopped", "duration"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Thrones"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 1000,
                     "recordsFiltered": 250,
                     "total_duration": "42 days 5 hrs 18 mins",
                     "filter_duration": "10 hrs 12 mins",
                     "data":
                        [{"year": 2016,
                          "paused_counter": 0,
                          "player": "Plex Web (Chrome)",
                          "parent_rating_key": 544,
                          "parent_title": "",
                          "duration": 263,
                          "transcode_decision": "transcode",
                          "rating_key": 4348,
                          "user_id": 8008135,
                          "thumb": "/library/metadata/4348/thumb/1462414561",
                          "id": 1124,
                          "platform": "Chrome",
                          "media_type": "episode",
                          "grandparent_rating_key": 351,
                          "started": 1462688107,
                          "full_title": "Game of Thrones - The Red Woman",
                          "reference_id": 1123,
                          "date": 1462687607,
                          "percent_complete": 84,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "group_ids": "1124",
                          "media_index": 17,
                          "friendly_name": "Mother of Dragons",
                          "watched_status": 0,
                          "group_count": 1,
                          "stopped": 1462688370,
                          "parent_media_index": 7,
                          "user": "DanyKhaleesi69"
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("date", True, False),
                          ("friendly_name", True, True),
                          ("ip_address", True, True),
                          ("platform", True, True),
                          ("player", True, True),
                          ("full_title", True, True),
                          ("started", True, False),
                          ("paused_counter", True, False),
                          ("stopped", True, False),
                          ("duration", True, False),
                          ("watched_status", False, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "date")

        if grouping and str(grouping).isdigit():
            grouping = int(grouping)
        elif grouping == 'false':
            grouping = 0

        custom_where = []
        if user_id:
            custom_where.append(['session_history.user_id', user_id])
        elif user:
            custom_where.append(['session_history.user', user])
        if 'rating_key' in kwargs:
            rating_key = kwargs.get('rating_key', "")
            custom_where.append(['session_history.rating_key', rating_key])
        if 'parent_rating_key' in kwargs:
            rating_key = kwargs.get('parent_rating_key', "")
            custom_where.append(['session_history.parent_rating_key', rating_key])
        if 'grandparent_rating_key' in kwargs:
            rating_key = kwargs.get('grandparent_rating_key', "")
            custom_where.append(['session_history.grandparent_rating_key', rating_key])
        if 'start_date' in kwargs:
            start_date = kwargs.get('start_date', "")
            custom_where.append(['strftime("%Y-%m-%d", datetime(started, "unixepoch", "localtime"))', start_date])
        if 'reference_id' in kwargs:
            reference_id = kwargs.get('reference_id', "")
            custom_where.append(['session_history.reference_id', reference_id])
        if 'section_id' in kwargs:
            section_id = kwargs.get('section_id', "")
            custom_where.append(['session_history_metadata.section_id', section_id])
        if 'media_type' in kwargs:
            media_type = kwargs.get('media_type', "")
            if media_type:
                custom_where.append(['session_history.media_type', media_type])
        if 'transcode_decision' in kwargs:
            transcode_decision = kwargs.get('transcode_decision', "")
            if transcode_decision:
                custom_where.append(['session_history_media_info.transcode_decision', transcode_decision])

        data_factory = datafactory.DataFactory()
        history = data_factory.get_datatables_history(kwargs=kwargs, custom_where=custom_where, grouping=grouping)

        return history

    @cherrypy.expose
    @requireAuth()
    def get_stream_data(self, row_id=None, user=None, **kwargs):

        data_factory = datafactory.DataFactory()
        stream_data = data_factory.get_stream_details(row_id)

        return serve_template(templatename="stream_data.html", title="Stream Data", data=stream_data, user=user)

    @cherrypy.expose
    @requireAuth()
    def get_ip_address_details(self, ip_address=None, **kwargs):
        import socket

        try:
            socket.inet_aton(ip_address)
        except socket.error:
            ip_address = None

        return serve_template(templatename="ip_address_modal.html", title="IP Address Details", data=ip_address)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def delete_history_rows(self, row_id, **kwargs):
        data_factory = datafactory.DataFactory()

        if row_id:
            delete_row = data_factory.delete_session_history_rows(row_id=row_id)

            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}


    ##### Graphs #####

    @cherrypy.expose
    @requireAuth()
    def graphs(self):

        config = {
            "graph_type": plexpy.CONFIG.GRAPH_TYPE,
            "graph_days": plexpy.CONFIG.GRAPH_DAYS,
            "graph_tab": plexpy.CONFIG.GRAPH_TAB,
            "music_logging_enable": plexpy.CONFIG.MUSIC_LOGGING_ENABLE
        }

        return serve_template(templatename="graphs.html", title="Graphs", config=config)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def set_graph_config(self, graph_type=None, graph_days=None, graph_tab=None):
        if graph_type:
            plexpy.CONFIG.__setattr__('GRAPH_TYPE', graph_type)
            plexpy.CONFIG.write()
        if graph_days:
            plexpy.CONFIG.__setattr__('GRAPH_DAYS', graph_days)
            plexpy.CONFIG.write()
        if graph_tab:
            plexpy.CONFIG.__setattr__('GRAPH_TAB', graph_tab)
            plexpy.CONFIG.write()

        return "Updated graphs config values."

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_user_names(self, **kwargs):
        """ Get a list of all user and user ids.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"friendly_name": "Jon Snow", "user_id": 133788},
                     {"friendly_name": "DanyKhaleesi69", "user_id": 8008135},
                     {"friendly_name": "Tyrion Lannister", "user_id": 696969},
                     {...},
                    ]
            ```
        """
        user_data = users.Users()
        user_names = user_data.get_user_names(kwargs=kwargs)

        return user_names

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_date(self, time_range='30', user_id=None, y_axis='plays', **kwargs):
        """ Get graph data by date.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["YYYY-MM-DD", "YYYY-MM-DD", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_per_day(time_range=time_range, user_id=user_id, y_axis=y_axis)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_date.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_dayofweek(self, time_range='30', user_id=None, y_axis='plays', **kwargs):
        """ Get graph data by day of the week.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["Sunday", "Monday", "Tuesday", ..., "Saturday"]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_per_dayofweek(time_range=time_range, user_id=user_id, y_axis=y_axis)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_dayofweek.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_hourofday(self, time_range='30', user_id=None, y_axis='plays', **kwargs):
        """ Get graph data by hour of the day.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["00", "01", "02", ..., "23"]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_per_hourofday(time_range=time_range, user_id=user_id, y_axis=y_axis)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_hourofday.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_per_month(self, y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by month.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["Jan 2016", "Feb 2016", "Mar 2016", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_per_month(y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_per_month.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by top 10 platforms.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["iOS", "Android", "Chrome", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_platforms(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_top_10_platforms.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by top 10 users.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["Jon Snow", "DanyKhaleesi69", "A Girl", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_users(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_top_10_users.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_stream_type(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by stream type by date.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["YYYY-MM-DD", "YYYY-MM-DD", ...]
                     "series":
                        [{"name": "Direct Play", "data": [...]}
                         {"name": "Direct Stream", "data": [...]},
                         {"name": "Transcode", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_per_stream_type(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_stream_type.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_source_resolution(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by source resolution.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["720", "1080", "sd", ...]
                     "series":
                        [{"name": "Direct Play", "data": [...]}
                         {"name": "Direct Stream", "data": [...]},
                         {"name": "Transcode", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_by_source_resolution(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_source_resolution.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_stream_resolution(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by stream resolution.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["720", "1080", "sd", ...]
                     "series":
                        [{"name": "Direct Play", "data": [...]}
                         {"name": "Direct Stream", "data": [...]},
                         {"name": "Transcode", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_total_plays_by_stream_resolution(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_stream_resolution.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by stream type by top 10 users.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["Jon Snow", "DanyKhaleesi69", "A Girl", ...]
                     "series":
                        [{"name": "Direct Play", "data": [...]}
                         {"name": "Direct Stream", "data": [...]},
                         {"name": "Transcode", "data": [...]}
                        ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_users(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_stream_type_by_top_10_users.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by stream type by top 10 platforms.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          The user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["iOS", "Android", "Chrome", ...]
                     "series":
                        [{"name": "Direct Play", "data": [...]}
                         {"name": "Direct Stream", "data": [...]},
                         {"name": "Transcode", "data": [...]}
                         ]
                     }
            ```
        """
        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_platforms(time_range=time_range, y_axis=y_axis, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_stream_type_by_top_10_platforms.")

    @cherrypy.expose
    @requireAuth()
    def history_table_modal(self, **kwargs):
        if kwargs.get('user_id') and not allow_session_user(kwargs['user_id']):
            return serve_template(templatename="history_table_modal.html", title="History Data", data=None)

        return serve_template(templatename="history_table_modal.html", title="History Data", data=kwargs)


    ##### Sync #####

    @cherrypy.expose
    @requireAuth()
    def sync(self):
        return serve_template(templatename="sync.html", title="Synced Items")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    def get_sync(self, machine_id=None, user_id=None, **kwargs):

        if not machine_id:
            machine_id = plexpy.CONFIG.PMS_IDENTIFIER

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_synced_items(machine_id=machine_id, user_id=user_id)

        if result:
            output = {"data": result}
        else:
            logger.warn(u"Unable to retrieve data for get_sync.")
            output = {"data": []}

        return output


    ##### Logs #####
    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def logs(self):
        return serve_template(templatename="logs.html", title="Log")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def getLog(self, start=0, length=100, **kwargs):
        start = int(start)
        length = int(length)
        order_dir = kwargs.get('order[0][dir]', "desc")
        order_column = kwargs.get('order[0][column]', "0")
        search_value = kwargs.get('search[value]', "")
        search_regex = kwargs.get('search[regex]', "") # Remove?
        sortcolumn = 0

        filt = []
        filtered = []
        fa = filt.append
        with open(os.path.join(plexpy.CONFIG.LOG_DIR, logger.FILENAME)) as f:
            for l in f.readlines():
                try:
                    temp_loglevel_and_time = l.split(' - ', 1)
                    loglvl = temp_loglevel_and_time[1].split(' ::', 1)[0].strip()
                    msg = l.split(' : ', 1)[1].replace('\n', '')
                    fa([temp_loglevel_and_time[0], loglvl, msg])
                except IndexError:
                    # Add traceback message to previous msg.
                    tl = (len(filt) - 1)
                    n = len(l) - len(l.lstrip(' '))
                    l = '&nbsp;' * (2 * n) + l[n:]
                    filt[tl][2] += '<br>' + l
                    continue

        if search_value == '':
            filtered = filt
        else:
            filtered = [row for row in filt for column in row if search_value.lower() in column.lower()]

        if order_column == '1':
            sortcolumn = 2
        elif order_column == '2':
            sortcolumn = 1

        filtered.sort(key=lambda x: x[sortcolumn])

        if order_dir == 'desc':
            filtered = filtered[::-1]

        rows = filtered[start:(start + length)]

        return json.dumps({
            'recordsFiltered': len(filtered),
            'recordsTotal': len(filt),
            'data': rows,
        })

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_plex_log(self, window=1000, **kwargs):
        """ Get the PMS logs.

            ```
            Required parameters:
                None

            Optional parameters:
                window (int):           The number of tail lines to return
                log_type (str):         "server" or "scanner"

            Returns:
                json:
                    [["May 08, 2016 09:35:37",
                      "DEBUG",
                      "Auth: Came in with a super-token, authorization succeeded."
                      ],
                     [...],
                     [...]
                     ]
            ```
        """
        log_lines = []
        log_type = kwargs.get('log_type', 'server')

        try:
            log_lines = {'data': log_reader.get_log_tail(window=window, parsed=True, log_type=log_type)}
        except:
            logger.warn(u"Unable to retrieve Plex Logs.")

        return log_lines

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_notification_log(self, **kwargs):
        """ Get the data on the PlexPy notification logs table.

            ```
            Required parameters:
                None

            Optional parameters:
                order_column (str):             "timestamp", "agent_name", "notify_action",
                                                "subject_text", "body_text", "script_args"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Telegram"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 1039,
                     "recordsFiltered": 163,
                     "data":
                        [{"agent_id": 13,
                          "agent_name": "Telegram",
                          "body_text": "Game of Thrones - S06E01 - The Red Woman [Transcode].",
                          "id": 1000,
                          "notify_action": "play",
                          "poster_url": "http://i.imgur.com/ZSqS8Ri.jpg",
                          "rating_key": 153037,
                          "script_args": "[]",
                          "session_key": 147,
                          "subject_text": "PlexPy (Winterfell-Server)",
                          "timestamp": 1462253821,
                          "user": "DanyKhaleesi69",
                          "user_id": 8008135
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("timestamp", True, True),
                          ("agent_name", True, True),
                          ("notify_action", True, True),
                          ("subject_text", True, True),
                          ("body_text", True, True),
                          ("script_args", True, True)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "timestamp")

        data_factory = datafactory.DataFactory()
        notifications = data_factory.get_notification_log(kwargs=kwargs)

        return notifications

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_notification_log(self, **kwargs):
        """ Delete the PlexPy notification logs.

            ```
            Required paramters:
                None

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        data_factory = datafactory.DataFactory()
        result = data_factory.delete_notification_log()
        res = 'success' if result else 'error'
        msg = 'Cleared notification logs.' if result else 'Failed to clear notification logs.'

        return {'result': res, 'message': msg}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_login_log(self, **kwargs):
        """ Delete the PlexPy login logs.

            ```
            Required paramters:
                None

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        user_data = users.Users()
        result = user_data.delete_login_log()
        res = 'success' if result else 'error'
        msg = 'Cleared login logs.' if result else 'Failed to clear login logs.'

        return {'result': res, 'message': msg}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def delete_logs(self):
        log_file = logger.FILENAME
        try:
            open(os.path.join(plexpy.CONFIG.LOG_DIR, log_file), 'w').close()
            result = 'success'
            msg = 'Cleared the %s file.' % log_file
            logger.info(msg)
        except Exception as e:
            result = 'error'
            msg = 'Failed to clear the %s file.' % log_file
            logger.exception(u'Failed to clear the %s file: %s.' % (log_file, e))

        return {'result': result, 'message': msg}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def toggleVerbose(self):
        plexpy.VERBOSE = not plexpy.VERBOSE
        logger.initLogger(console=not plexpy.QUIET,
                          log_dir=plexpy.CONFIG.LOG_DIR, verbose=plexpy.VERBOSE)
        logger.info(u"Verbose toggled, set to %s", plexpy.VERBOSE)
        logger.debug(u"If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "logs")

    @cherrypy.expose
    @requireAuth()
    def log_js_errors(self, page, message, file, line):
        """ Logs javascript errors from the web interface. """
        logger.error(u"WebUI :: /%s : %s. (%s:%s)" % (page.rpartition('/')[-1],
                                                      message,
                                                      file.rpartition('/')[-1].partition('?')[0],
                                                      line))
        return "js error logged."

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def logFile(self):
        try:
            with open(os.path.join(plexpy.CONFIG.LOG_DIR, logger.FILENAME), 'r') as f:
                return '<pre>%s</pre>' % f.read()
        except IOError as e:
            return "Log file not found."


    ##### Settings #####

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def settings(self):
        interface_dir = os.path.join(plexpy.PROG_DIR, 'data/interfaces/')
        interface_list = [name for name in os.listdir(interface_dir) if
                          os.path.isdir(os.path.join(interface_dir, name))]

        # Initialise blank passwords so we do not expose them in the html forms
        # but users are still able to clear them
        if plexpy.CONFIG.HTTP_PASSWORD != '':
            http_password = '    '
        else:
            http_password = ''

        config = {
            "allow_guest_access": checked(plexpy.CONFIG.ALLOW_GUEST_ACCESS),
            "http_basic_auth": checked(plexpy.CONFIG.HTTP_BASIC_AUTH),
            "http_hash_password": checked(plexpy.CONFIG.HTTP_HASH_PASSWORD),
            "http_hashed_password": plexpy.CONFIG.HTTP_HASHED_PASSWORD,
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": http_password,
            "http_root": plexpy.CONFIG.HTTP_ROOT,
            "http_proxy": checked(plexpy.CONFIG.HTTP_PROXY),
            "launch_browser": checked(plexpy.CONFIG.LAUNCH_BROWSER),
            "enable_https": checked(plexpy.CONFIG.ENABLE_HTTPS),
            "https_create_cert": checked(plexpy.CONFIG.HTTPS_CREATE_CERT),
            "https_cert": plexpy.CONFIG.HTTPS_CERT,
            "https_key": plexpy.CONFIG.HTTPS_KEY,
            "https_domain": plexpy.CONFIG.HTTPS_DOMAIN,
            "https_ip": plexpy.CONFIG.HTTPS_IP,
            "anon_redirect": plexpy.CONFIG.ANON_REDIRECT,
            "api_enabled": checked(plexpy.CONFIG.API_ENABLED),
            "api_key": plexpy.CONFIG.API_KEY,
            "update_db_interval": plexpy.CONFIG.UPDATE_DB_INTERVAL,
            "freeze_db": checked(plexpy.CONFIG.FREEZE_DB),
            "backup_dir": plexpy.CONFIG.BACKUP_DIR,
            "cache_dir": plexpy.CONFIG.CACHE_DIR,
            "log_dir": plexpy.CONFIG.LOG_DIR,
            "log_blacklist": checked(plexpy.CONFIG.LOG_BLACKLIST),
            "check_github": checked(plexpy.CONFIG.CHECK_GITHUB),
            "interface_list": interface_list,
            "cache_sizemb": plexpy.CONFIG.CACHE_SIZEMB,
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_logs_folder": plexpy.CONFIG.PMS_LOGS_FOLDER,
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_token": plexpy.CONFIG.PMS_TOKEN,
            "pms_ssl": checked(plexpy.CONFIG.PMS_SSL),
            "pms_use_bif": checked(plexpy.CONFIG.PMS_USE_BIF),
            "pms_uuid": plexpy.CONFIG.PMS_UUID,
            "date_format": plexpy.CONFIG.DATE_FORMAT,
            "time_format": plexpy.CONFIG.TIME_FORMAT,
            "get_file_sizes": checked(plexpy.CONFIG.GET_FILE_SIZES),
            "grouping_global_history": checked(plexpy.CONFIG.GROUPING_GLOBAL_HISTORY),
            "grouping_user_history": checked(plexpy.CONFIG.GROUPING_USER_HISTORY),
            "grouping_charts": checked(plexpy.CONFIG.GROUPING_CHARTS),
            "movie_notify_enable": checked(plexpy.CONFIG.MOVIE_NOTIFY_ENABLE),
            "tv_notify_enable": checked(plexpy.CONFIG.TV_NOTIFY_ENABLE),
            "music_notify_enable": checked(plexpy.CONFIG.MUSIC_NOTIFY_ENABLE),
            "monitor_pms_updates": checked(plexpy.CONFIG.MONITOR_PMS_UPDATES),
            "monitor_remote_access": checked(plexpy.CONFIG.MONITOR_REMOTE_ACCESS),
            "monitoring_interval": plexpy.CONFIG.MONITORING_INTERVAL,
            "monitoring_use_websocket": checked(plexpy.CONFIG.MONITORING_USE_WEBSOCKET),
            "refresh_libraries_interval": plexpy.CONFIG.REFRESH_LIBRARIES_INTERVAL,
            "refresh_libraries_on_startup": checked(plexpy.CONFIG.REFRESH_LIBRARIES_ON_STARTUP),
            "refresh_users_interval": plexpy.CONFIG.REFRESH_USERS_INTERVAL,
            "refresh_users_on_startup": checked(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "ip_logging_enable": checked(plexpy.CONFIG.IP_LOGGING_ENABLE),
            "movie_logging_enable": checked(plexpy.CONFIG.MOVIE_LOGGING_ENABLE),
            "tv_logging_enable": checked(plexpy.CONFIG.TV_LOGGING_ENABLE),
            "music_logging_enable": checked(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "pms_is_remote": checked(plexpy.CONFIG.PMS_IS_REMOTE),
            "notify_consecutive": checked(plexpy.CONFIG.NOTIFY_CONSECUTIVE),
            "notify_upload_posters": checked(plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS),
            "notify_recently_added": checked(plexpy.CONFIG.NOTIFY_RECENTLY_ADDED),
            "notify_recently_added_grandparent": checked(plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_GRANDPARENT),
            "notify_recently_added_delay": plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_DELAY,
            "notify_watched_percent": plexpy.CONFIG.NOTIFY_WATCHED_PERCENT,
            "notify_on_start_subject_text": plexpy.CONFIG.NOTIFY_ON_START_SUBJECT_TEXT,
            "notify_on_start_body_text": plexpy.CONFIG.NOTIFY_ON_START_BODY_TEXT,
            "notify_on_stop_subject_text": plexpy.CONFIG.NOTIFY_ON_STOP_SUBJECT_TEXT,
            "notify_on_stop_body_text": plexpy.CONFIG.NOTIFY_ON_STOP_BODY_TEXT,
            "notify_on_pause_subject_text": plexpy.CONFIG.NOTIFY_ON_PAUSE_SUBJECT_TEXT,
            "notify_on_pause_body_text": plexpy.CONFIG.NOTIFY_ON_PAUSE_BODY_TEXT,
            "notify_on_resume_subject_text": plexpy.CONFIG.NOTIFY_ON_RESUME_SUBJECT_TEXT,
            "notify_on_resume_body_text": plexpy.CONFIG.NOTIFY_ON_RESUME_BODY_TEXT,
            "notify_on_buffer_subject_text": plexpy.CONFIG.NOTIFY_ON_BUFFER_SUBJECT_TEXT,
            "notify_on_buffer_body_text": plexpy.CONFIG.NOTIFY_ON_BUFFER_BODY_TEXT,
            "notify_on_watched_subject_text": plexpy.CONFIG.NOTIFY_ON_WATCHED_SUBJECT_TEXT,
            "notify_on_watched_body_text": plexpy.CONFIG.NOTIFY_ON_WATCHED_BODY_TEXT,
            "notify_on_created_subject_text": plexpy.CONFIG.NOTIFY_ON_CREATED_SUBJECT_TEXT,
            "notify_on_created_body_text": plexpy.CONFIG.NOTIFY_ON_CREATED_BODY_TEXT,
            "notify_on_extdown_subject_text": plexpy.CONFIG.NOTIFY_ON_EXTDOWN_SUBJECT_TEXT,
            "notify_on_extdown_body_text": plexpy.CONFIG.NOTIFY_ON_EXTDOWN_BODY_TEXT,
            "notify_on_intdown_subject_text": plexpy.CONFIG.NOTIFY_ON_INTDOWN_SUBJECT_TEXT,
            "notify_on_intdown_body_text": plexpy.CONFIG.NOTIFY_ON_INTDOWN_BODY_TEXT,
            "notify_on_extup_subject_text": plexpy.CONFIG.NOTIFY_ON_EXTUP_SUBJECT_TEXT,
            "notify_on_extup_body_text": plexpy.CONFIG.NOTIFY_ON_EXTUP_BODY_TEXT,
            "notify_on_intup_subject_text": plexpy.CONFIG.NOTIFY_ON_INTUP_SUBJECT_TEXT,
            "notify_on_intup_body_text": plexpy.CONFIG.NOTIFY_ON_INTUP_BODY_TEXT,
            "notify_on_pmsupdate_subject_text": plexpy.CONFIG.NOTIFY_ON_PMSUPDATE_SUBJECT_TEXT,
            "notify_on_pmsupdate_body_text": plexpy.CONFIG.NOTIFY_ON_PMSUPDATE_BODY_TEXT,
            "notify_scripts_args_text": plexpy.CONFIG.NOTIFY_SCRIPTS_ARGS_TEXT,
            "home_sections": json.dumps(plexpy.CONFIG.HOME_SECTIONS),
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_type": checked(plexpy.CONFIG.HOME_STATS_TYPE),
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "home_stats_cards": json.dumps(plexpy.CONFIG.HOME_STATS_CARDS),
            "home_library_cards": json.dumps(plexpy.CONFIG.HOME_LIBRARY_CARDS),
            "buffer_threshold": plexpy.CONFIG.BUFFER_THRESHOLD,
            "buffer_wait": plexpy.CONFIG.BUFFER_WAIT,
            "group_history_tables": checked(plexpy.CONFIG.GROUP_HISTORY_TABLES),
            "git_token": plexpy.CONFIG.GIT_TOKEN,
            "imgur_client_id": plexpy.CONFIG.IMGUR_CLIENT_ID,
            "cache_images": checked(plexpy.CONFIG.CACHE_IMAGES)
        }

        return serve_template(templatename="settings.html", title="Settings", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "launch_browser", "enable_https", "https_create_cert", "api_enabled", "freeze_db", "check_github",
            "grouping_global_history", "grouping_user_history", "grouping_charts", "group_history_tables",
            "pms_use_bif", "pms_ssl", "pms_is_remote", "home_stats_type",
            "movie_notify_enable", "tv_notify_enable", "music_notify_enable", "monitoring_use_websocket",
            "refresh_libraries_on_startup", "refresh_users_on_startup",
            "ip_logging_enable", "movie_logging_enable", "tv_logging_enable", "music_logging_enable",
            "notify_consecutive", "notify_upload_posters", "notify_recently_added", "notify_recently_added_grandparent",
            "monitor_pms_updates", "monitor_remote_access", "get_file_sizes", "log_blacklist", "http_hash_password",
            "allow_guest_access", "cache_images", "http_proxy", "http_basic_auth"
        ]
        for checked_config in checked_configs:
            if checked_config not in kwargs:
                # checked items should be zero or one. if they were not sent then the item was not checked
                kwargs[checked_config] = 0
            else:
                kwargs[checked_config] = 1

        # If http password exists in config, do not overwrite when blank value received
        if kwargs.get('http_password'):
            if kwargs['http_password'] == '    ' and plexpy.CONFIG.HTTP_PASSWORD != '':
                if kwargs.get('http_hash_password') and not plexpy.CONFIG.HTTP_HASHED_PASSWORD:
                    kwargs['http_password'] = make_hash(plexpy.CONFIG.HTTP_PASSWORD)
                    kwargs['http_hashed_password'] = 1
                else:
                    kwargs['http_password'] = plexpy.CONFIG.HTTP_PASSWORD

            elif kwargs['http_password'] and kwargs.get('http_hash_password'):
                kwargs['http_password'] = make_hash(kwargs['http_password'])
                kwargs['http_hashed_password'] = 1

            elif not kwargs.get('http_hash_password'):
                kwargs['http_hashed_password'] = 0
        else:
            kwargs['http_hashed_password'] = 0

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        # Check if we should refresh our data
        server_changed = False
        reschedule = False
        https_changed = False
        refresh_libraries = False
        refresh_users = False

        # If we change any monitoring settings, make sure we reschedule tasks.
        if kwargs.get('check_github') != plexpy.CONFIG.CHECK_GITHUB or \
            kwargs.get('monitoring_interval') != str(plexpy.CONFIG.MONITORING_INTERVAL) or \
            kwargs.get('refresh_libraries_interval') != str(plexpy.CONFIG.REFRESH_LIBRARIES_INTERVAL) or \
            kwargs.get('refresh_users_interval') != str(plexpy.CONFIG.REFRESH_USERS_INTERVAL) or \
            kwargs.get('notify_recently_added') != plexpy.CONFIG.NOTIFY_RECENTLY_ADDED or \
            kwargs.get('monitor_pms_updates') != plexpy.CONFIG.MONITOR_PMS_UPDATES or \
            kwargs.get('monitor_remote_access') != plexpy.CONFIG.MONITOR_REMOTE_ACCESS:
            reschedule = True

        # If we change the SSL setting for PMS or PMS remote setting, make sure we grab the new url.
        if kwargs.get('pms_ssl') != plexpy.CONFIG.PMS_SSL or \
            kwargs.get('pms_is_remote') != plexpy.CONFIG.PMS_IS_REMOTE:
            server_changed = True

        # If we change the HTTPS setting, make sure we generate a new certificate.
        if kwargs.get('enable_https') and kwargs.get('https_create_cert'):
            if kwargs.get('https_domain') != plexpy.CONFIG.HTTPS_DOMAIN or \
                kwargs.get('https_ip') != plexpy.CONFIG.HTTPS_IP or \
                kwargs.get('https_cert') != plexpy.CONFIG.HTTPS_CERT or \
                kwargs.get('https_key') != plexpy.CONFIG.HTTPS_KEY:
                https_changed = True

        # Remove config with 'hsec-' prefix and change home_sections to list
        if kwargs.get('home_sections'):
            for k in kwargs.keys():
                if k.startswith('hsec-'):
                    del kwargs[k]
            kwargs['home_sections'] = kwargs['home_sections'].split(',')

        # Remove config with 'hscard-' prefix and change home_stats_cards to list
        if kwargs.get('home_stats_cards'):
            for k in kwargs.keys():
                if k.startswith('hscard-'):
                    del kwargs[k]
            kwargs['home_stats_cards'] = kwargs['home_stats_cards'].split(',')

            if kwargs['home_stats_cards'] == ['first_run_wizard']:
                kwargs['home_stats_cards'] = plexpy.CONFIG.HOME_STATS_CARDS

        # Remove config with 'hlcard-' prefix and change home_library_cards to list
        if kwargs.get('home_library_cards'):
            for k in kwargs.keys():
                if k.startswith('hlcard-'):
                    del kwargs[k]
            kwargs['home_library_cards'] = kwargs['home_library_cards'].split(',')

            if kwargs['home_library_cards'] == ['first_run_wizard']:
                refresh_libraries = True

        # If we change the server, make sure we grab the new url and refresh libraries and users lists.
        if kwargs.get('server_changed'):
            del kwargs['server_changed']
            server_changed = True
            refresh_users = True
            refresh_libraries = True

        plexpy.CONFIG.process_kwargs(kwargs)

        # Write the config
        plexpy.CONFIG.write()

        # Get new server URLs for SSL communications and get new server friendly name
        if server_changed:
            plextv.get_real_pms_url()
            pmsconnect.get_server_friendly_name()
            web_socket.reconnect()

        # Reconfigure scheduler if intervals changed
        if reschedule:
            plexpy.initialize_scheduler()

        # Generate a new HTTPS certificate
        if https_changed:
            create_https_certificates(plexpy.CONFIG.HTTPS_CERT, plexpy.CONFIG.HTTPS_KEY)

        # Refresh users table if our server IP changes.
        if refresh_libraries:
            threading.Thread(target=pmsconnect.refresh_libraries).start()

        # Refresh users table if our server IP changes.
        if refresh_users:
            threading.Thread(target=plextv.refresh_users).start()

        return {'result': 'success', 'message': 'Settings saved.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def backup_config(self):
        """ Creates a manual backup of the plexpy.db file """

        result = config.make_backup()

        if result:
            return {'result': 'success', 'message': 'Config backup successful.'}
        else:
            return {'result': 'error', 'message': 'Config backup failed.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_scheduler_table(self, **kwargs):
        return serve_template(templatename="scheduler_table.html")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def backup_db(self):
        """ Creates a manual backup of the plexpy.db file """

        result = database.make_backup()

        if result:
            return {'result': 'success', 'message': 'Database backup successful.'}
        else:
            return {'result': 'error', 'message': 'Database backup failed.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_notification_agent_config(self, agent_id, **kwargs):
        if agent_id.isdigit():
            config = notifiers.get_notification_agent_config(agent_id=agent_id)
            agents = notifiers.available_notification_agents()
            for agent in agents:
                if int(agent_id) == agent['id']:
                    this_agent = agent
                    break
                else:
                    this_agent = None
        else:
            return None

        checkboxes = {'email_tls': checked(plexpy.CONFIG.EMAIL_TLS)}

        return serve_template(templatename="notification_config.html", title="Notification Configuration",
                              agent=this_agent, data=config, checkboxes=checkboxes)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_notification_agent_triggers(self, agent_id, **kwargs):
        if agent_id.isdigit():
            agents = notifiers.available_notification_agents()
            for agent in agents:
                if int(agent_id) == agent['id']:
                    this_agent = agent
                    break
                else:
                    this_agent = None
        else:
            return None

        return serve_template(templatename="notification_triggers_modal.html", title="Notification Triggers",
                              data=this_agent)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi("notify")
    def send_notification(self, agent_id=None, subject='PlexPy', body='Test notification', notify_action=None, **kwargs):
        """ Send a notification using PlexPy.

            ```
            Required parameters:
                agent_id(str):          The id of the notification agent to use
                subject(str):           The subject of the message
                body(str):              The body of the message

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        test = 'test ' if notify_action == 'test' else ''

        if agent_id.isdigit():
            agents = notifiers.available_notification_agents()
            for agent in agents:
                if int(agent_id) == agent['id']:
                    this_agent = agent
                    break
                else:
                    this_agent = None

            if this_agent:
                logger.debug(u"Sending %s%s notification." % (test, this_agent['name']))
                if notifiers.send_notification(this_agent['id'], subject, body, notify_action, **kwargs):
                    return "Notification sent."
                else:
                    return "Notification failed."
            else:
                logger.debug(u"Unable to send %snotification, invalid notification agent id %s." % (test, agent_id))
                return "Invalid notification agent id %s." % agent_id
        else:
            logger.debug(u"Unable to send %snotification, no notification agent id received." % test)
            return "No notification agent id received."

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_browser_notifications(self, **kwargs):
        browser = notifiers.Browser()
        result = browser.get_notifications()

        if result:
            notifications = result['notifications']
            if notifications:
                return notifications
            else:
                return None
        else:
            logger.warn('Unable to retrieve browser notifications.')
            return None

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def facebookStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        facebook = notifiers.FacebookNotifier()
        return facebook._get_authorization()

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def facebookStep2(self, code):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        facebook = notifiers.FacebookNotifier()
        result = facebook._get_credentials(code)
        # logger.info(u"result: " + str(result))
        if result:
            return "Key verification successful, PlexPy can send notification to Facebook. You may close this page now."
        else:
            return "Unable to verify key"

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def osxnotifyregister(self, app):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        from osxnotify import registerapp as osxnotify

        result, msg = osxnotify.registerapp(app)
        if result:
            osx_notify = notifiers.OSX_NOTIFY()
            osx_notify.notify('Registered', result, 'Success :-)')
            # logger.info(u"Registered %s, to re-register a different app, delete this app first" % result)
        else:
            logger.warn(msg)
        return msg

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def set_notification_config(self, **kwargs):

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        plexpy.CONFIG.process_kwargs(kwargs)

        # Write the config
        plexpy.CONFIG.write()

        cherrypy.response.status = 200

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def import_database(self, app=None, database_path=None, table_name=None, import_ignore_interval=0, **kwargs):
        """ Import a PlexWatch or Plexivity database into PlexPy.

            ```
            Required parameters:
                app (str):                      "plexwatch" or "plexivity"
                database_path (str):            The full path to the plexwatch database file
                table_name (str):               "processed" or "grouped"

            Optional parameters:
                import_ignore_interval (int):   The minimum number of seconds for a stream to import

            Returns:
                None
            ```
        """
        if not app:
            return 'No app specified for import'

        if app.lower() == 'plexwatch':
            db_check_msg = plexwatch_import.validate_database(database=database_path,
                                                              table_name=table_name)
            if db_check_msg == 'success':
                threading.Thread(target=plexwatch_import.import_from_plexwatch,
                                 kwargs={'database': database_path,
                                         'table_name': table_name,
                                         'import_ignore_interval': import_ignore_interval}).start()
                return 'Import has started. Check the PlexPy logs to monitor any problems.'
            else:
                return db_check_msg
        elif app.lower() == 'plexivity':
            db_check_msg = plexivity_import.validate_database(database=database_path,
                                                              table_name=table_name)
            if db_check_msg == 'success':
                threading.Thread(target=plexivity_import.import_from_plexivity,
                                 kwargs={'database': database_path,
                                         'table_name': table_name,
                                         'import_ignore_interval': import_ignore_interval}).start()
                return 'Import has started. Check the PlexPy logs to monitor any problems.'
            else:
                return db_check_msg
        else:
            return 'App not recognized for import'

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def import_database_tool(self, app=None, **kwargs):
        if app == 'plexwatch':
            return serve_template(templatename="app_import.html", title="Import PlexWatch Database", app="PlexWatch")
        elif app == 'plexivity':
            return serve_template(templatename="app_import.html", title="Import Plexivity Database", app="Plexivity")

        logger.warn(u"No app specified for import.")
        return

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_pms_token(self, username=None, password=None, **kwargs):
        """ Get the user's Plex token used for PlexPy.

            ```
            Required parameters:
                username (str):     The Plex.tv username
                password (str):     The Plex.tv password

            Optional parameters:
                None

            Returns:
                string:             The Plex token used for PlexPy
            ```
        """
        if not username and not password:
            return None

        token = plextv.PlexTV(username=username, password=password)
        result = token.get_token()

        if result:
            return result['auth_token']
        else:
            logger.warn(u"Unable to retrieve Plex.tv token.")
            return None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_server_id(self, hostname=None, port=None, identifier=None, ssl=0, remote=0, **kwargs):
        """ Get the PMS server identifier.

            ```
            Required parameters:
                hostname (str):     'localhost' or '192.160.0.10'
                port (int):         32400

            Optional parameters:
                ssl (int):          0 or 1
                remote (int):       0 or 1

            Returns:
                string:             The unique PMS identifier
            ```
        """
        # Attempt to get the pms_identifier from plex.tv if the server is published
        # Works for all PMS SSL settings
        if not identifier and hostname and port:
            plex_tv = plextv.PlexTV()
            servers = plex_tv.discover()
            ip_address = get_ip(hostname)

            for server in servers:
                if (server['ip'] == hostname or server['ip'] == ip_address) and server['port'] == port:
                    identifier = server['clientIdentifier']
                    break

            # Fallback to checking /identity endpoint is server is unpublished
            # Cannot set SSL settings on the PMS if unpublished so 'http' is okay
            if not identifier:
                request_handler = http_handler.HTTPHandler(host=hostname,
                                                           port=port,
                                                           token=None)
                uri = '/identity'
                request = request_handler.make_request(uri=uri,
                                                       proto='http',
                                                       request_type='GET',
                                                       output_format='xml',
                                                       no_token=True,
                                                       timeout=10)
                if request:
                    xml_head = request.getElementsByTagName('MediaContainer')[0]
                    identifier = xml_head.getAttribute('machineIdentifier')

        if identifier:
            return identifier
        else:
            logger.warn('Unable to retrieve the PMS identifier.')
            return None

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_server_pref(self, pref=None, **kwargs):
        """ Get a specified PMS server preference.

            ```
            Required parameters:
                pref (str):         Name of preference

            Returns:
                string:             Value of preference
            ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_pref(pref=pref)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_pref.")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def generateAPI(self):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info(u"New API key generated.")
        return apikey

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def checkGithub(self):
        versioncheck.checkGithub()
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def do_state_change(self, signal, title, timer):
        message = title
        quote = self.random_arnold_quotes()
        plexpy.SIGNAL = signal

        return serve_template(templatename="shutdown.html", title=title,
                              message=message, timer=timer, quote=quote)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def shutdown(self):
        return self.do_state_change('shutdown', 'Shutting Down', 15)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def restart(self):
        return self.do_state_change('restart', 'Restarting', 30)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def update(self):
        return self.do_state_change('update', 'Updating', 120)


    ##### Info #####

    @cherrypy.expose
    @requireAuth()
    def info(self, rating_key=None, source=None, query=None, **kwargs):
        metadata = None

        config = {
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER
        }

        if source == 'history':
            data_factory = datafactory.DataFactory()
            result = data_factory.get_metadata_details(rating_key=rating_key)
            if result:
                metadata = result['metadata']
                poster_url = data_factory.get_poster_url(metadata=metadata)
                metadata['poster_url'] = poster_url
        else:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_metadata_details(rating_key=rating_key, get_media_info=True)
            if result:
                metadata = result['metadata']
                data_factory = datafactory.DataFactory()
                poster_url = data_factory.get_poster_url(metadata=metadata)
                metadata['poster_url'] = poster_url

        if metadata:
            if metadata['section_id'] and not allow_session_library(metadata['section_id']):
                raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

            return serve_template(templatename="info.html", data=metadata, title="Info", config=config, source=source)
        else:
            if get_session_user_id():
                raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)
            else:
                return self.update_metadata(rating_key, query)

    @cherrypy.expose
    @requireAuth()
    def get_item_children(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_item_children(rating_key)

        if result:
            return serve_template(templatename="info_children_list.html", data=result, title="Children List")
        else:
            logger.warn(u"Unable to retrieve data for get_item_children.")
            return serve_template(templatename="info_children_list.html", data=None, title="Children List")

    @cherrypy.expose
    @requireAuth()
    def pms_image_proxy(self, img='', rating_key=None, width='0', height='0', fallback=None, **kwargs):
        """ Gets an image from the PMS and saves it to the image cache directory. """

        if not img and not rating_key:
            logger.error('No image input received.')
            return

        if rating_key and not img:
            img = '/library/metadata/%s/thumb/1337' % rating_key

        img_string = img.rsplit('/', 1)[0] if '/library/metadata' in img else img
        img_string += '%s%s' % (width, height)
        fp = hashlib.md5(img_string).hexdigest()
        fp += '.jpg'  # we want to be able to preview the thumbs
        c_dir = os.path.join(plexpy.CONFIG.CACHE_DIR, 'images')
        ffp = os.path.join(c_dir, fp)

        if not os.path.exists(c_dir):
            os.mkdir(c_dir)

        try:
            if 'indexes' in img:
                raise NotFound
            return serve_file(path=ffp, content_type='image/jpeg')

        except NotFound:
            # the image does not exist, download it from pms
            try:
                pms_connect = pmsconnect.PmsConnect()
                result = pms_connect.get_image(img, width, height)

                if result and result[0]:
                    cherrypy.response.headers['Content-type'] = result[1]
                    if plexpy.CONFIG.CACHE_IMAGES and 'indexes' not in img:
                        with open(ffp, 'wb') as f:
                            f.write(result[0])

                    return result[0]
                else:
                    raise Exception(u'PMS image request failed')

            except Exception as e:
                logger.exception(u'Failed to get image %s, falling back to %s.' % (img, fallback))
                fbi = None
                if fallback == 'poster':
                    fbi = common.DEFAULT_POSTER_THUMB
                elif fallback == 'cover':
                    fbi = common.DEFAULT_COVER_THUMB
                elif fallback == 'art':
                    fbi = common.DEFAULT_ART

                if fbi:
                    fp = os.path.join(plexpy.PROG_DIR, 'data', fbi)
                    return serve_file(path=fp, content_type='image/png')


    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_log(self):
        """ Download the PlexPy log file. """
        log_file = logger.FILENAME
        try:
            logger.logger.flush()
        except:
            pass

        return serve_download(os.path.join(plexpy.CONFIG.LOG_DIR, log_file), name=log_file)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_image_cache(self):
        """ Delete and recreate the image cache directory. """
        return self.delete_cache(folder='images')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_cache(self, folder=''):
        """ Delete and recreate the cache directory. """
        cache_dir = os.path.join(plexpy.CONFIG.CACHE_DIR, folder)
        result = 'success'
        msg = 'Cleared the %scache.' % (folder + ' ' if folder else '')
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
        except OSError as e:
            result = 'error'
            msg = 'Failed to delete %s.' % cache_dir
            logger.exception(u'Failed to delete %s: %s.' % (cache_dir, e))
            return {'result': result, 'message': msg}

        try:
            os.makedirs(cache_dir)
        except OSError as e:
            result = 'error'
            msg = 'Failed to make %s.' % cache_dir
            logger.exception(u'Failed to create %s: %s.' % (cache_dir, e))
            return {'result': result, 'message': msg}

        logger.info(msg)
        return {'result': result, 'message': msg}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def delete_poster_url(self, poster_url=''):

        if poster_url:
            data_factory = datafactory.DataFactory()
            result = data_factory.delete_poster_url(poster_url=poster_url)
        else:
            result = None

        if result:
            return {'message': result}
        else:
            return {'message': 'no data received'}


    ##### Search #####

    @cherrypy.expose
    @requireAuth()
    def search(self, query=''):
        return serve_template(templatename="search.html", title="Search", query=query)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi('search')
    def search_results(self, query, **kwargs):
        """ Get search results from the PMS.

            ```
            Required parameters:
                query (str):        The query string to search for

            Returns:
                json:
                    {"results_count": 69,
                     "results_list":
                        {"movie":
                            [{...},
                             {...},
                             ]
                         },
                        {"episode":
                            [{...},
                             {...},
                             ]
                         },
                        {...}
                     }
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_search_results(query)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for search_results.")

    @cherrypy.expose
    @requireAuth()
    def get_search_results_children(self, query, media_type=None, season_index=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_search_results(query)

        if media_type:
            result['results_list'] = {media_type: result['results_list'][media_type]}
        if media_type == 'season' and season_index:
            result['results_list']['season'] = [season for season in result['results_list']['season']
                                                if season['media_index'] == season_index]

        if result:
            return serve_template(templatename="info_search_results_list.html", data=result, title="Search Result List")
        else:
            logger.warn(u"Unable to retrieve data for get_search_results_children.")
            return serve_template(templatename="info_search_results_list.html", data=None, title="Search Result List")


    ##### Update Metadata #####

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def update_metadata(self, rating_key=None, query=None, update=False, **kwargs):
        query_string = query
        update = True if update == 'True' else False

        data_factory = datafactory.DataFactory()
        query = data_factory.get_search_query(rating_key=rating_key)
        if query and query_string:
            query['query_string'] = query_string

        if query:
            return serve_template(templatename="update_metadata.html", query=query, update=update, title="Info")
        else:
            logger.warn(u"Unable to retrieve data for update_metadata.")
            return serve_template(templatename="update_metadata.html", query=query, update=update, title="Info")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def update_metadata_details(self, old_rating_key, new_rating_key, media_type, **kwargs):
        """ Update the metadata in the PlexPy database by matching rating keys.
            Also updates all parents or children of the media item if it is a show/season/episode
            or artist/album/track.

            ```
            Required parameters:
                old_rating_key (str):       12345
                new_rating_key (str):       54321
                media_type (str):           "movie", "show", "season", "episode", "artist", "album", "track"

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        if new_rating_key:
            data_factory = datafactory.DataFactory()
            pms_connect = pmsconnect.PmsConnect()

            old_key_list = data_factory.get_rating_keys_list(rating_key=old_rating_key, media_type=media_type)
            new_key_list = pms_connect.get_rating_keys_list(rating_key=new_rating_key, media_type=media_type)

            result = data_factory.update_metadata(old_key_list=old_key_list,
                                                  new_key_list=new_key_list,
                                                  media_type=media_type)

        if result:
            return {'message': result}
        else:
            return {'message': 'no data received'}

    # test code
    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_new_rating_keys(self, rating_key='', media_type='', **kwargs):
        """ Get a list of new rating keys for the PMS of all of the item's parent/children.

            ```
            Required parameters:
                rating_key (str):       '12345'
                media_type (str):       "movie", "show", "season", "episode", "artist", "album", "track"

            Optional parameters:
                None

            Returns:
                json:
                    {}
            ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_rating_keys_list(rating_key=rating_key, media_type=media_type)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_new_rating_keys.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_old_rating_keys(self, rating_key='', media_type='', **kwargs):
        """ Get a list of old rating keys from the PlexPy database for all of the item's parent/children.

            ```
            Required parameters:
                rating_key (str):       '12345'
                media_type (str):       "movie", "show", "season", "episode", "artist", "album", "track"

            Optional parameters:
                None

            Returns:
                json:
                    {}
            ```
        """

        data_factory = datafactory.DataFactory()
        result = data_factory.get_rating_keys_list(rating_key=rating_key, media_type=media_type)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_old_rating_keys.")


    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_pms_sessions_json(self, **kwargs):
        """ Get all the current sessions. """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sessions('json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_pms_sessions_json.")
            return False

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_metadata")
    def get_metadata_details(self, rating_key='', media_info=False, **kwargs):
        """ Get the metadata for a media item.

            ```
            Required parameters:
                rating_key (str):       Rating key of the item
                media_info (bool):      True or False wheter to get media info

            Optional parameters:
                None

            Returns:
                json:
                    {"metadata":
                        {"actors": [
                            "Kit Harington",
                            "Emilia Clarke",
                            "Isaac Hempstead-Wright",
                            "Maisie Williams",
                            "Liam Cunningham",
                         ],
                         "added_at": "1461572396",
                         "art": "/library/metadata/1219/art/1462175063",
                         "content_rating": "TV-MA",
                         "directors": [
                            "Jeremy Podeswa"
                         ],
                         "duration": "2998290",
                         "genres": [
                            "Adventure",
                            "Drama",
                            "Fantasy"
                         ],
                         "grandparent_rating_key": "1219",
                         "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
                         "grandparent_title": "Game of Thrones",
                         "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                         "labels": [],
                         "last_viewed_at": "1462165717",
                         "library_name": "TV Shows",
                         "media_index": "1",
                         "media_type": "episode",
                         "originally_available_at": "2016-04-24",
                         "parent_media_index": "6",
                         "parent_rating_key": "153036",
                         "parent_thumb": "/library/metadata/153036/thumb/1462175062",
                         "parent_title": "",
                         "rating": "7.8",
                         "rating_key": "153037",
                         "section_id": "2",
                         "studio": "HBO",
                         "summary": "Jon Snow is dead. Daenerys meets a strong man. Cersei sees her daughter again.",
                         "tagline": "",
                         "thumb": "/library/metadata/153037/thumb/1462175060",
                         "title": "The Red Woman",
                         "updated_at": "1462175060",
                         "writers": [
                            "David Benioff",
                            "D. B. Weiss"
                         ],
                         "year": "2016"
                         }
                     }
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata_details(rating_key=rating_key, get_media_info=media_info)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_metadata_details.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_recently_added")
    def get_recently_added_details(self, start='0', count='0', section_id='', **kwargs):
        """ Get all items that where recelty added to plex.

            ```
            Required parameters:
                count (str):        Number of items to return

            Optional parameters:
                start (str):        The item number to start at
                section_id (str):   The id of the Plex library section

            Returns:
                json:
                    {"recently_added":
                        [{"added_at": "1461572396",
                          "grandparent_rating_key": "1219",
                          "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
                          "grandparent_title": "Game of Thrones",
                          "library_name": "",
                          "media_index": "1",
                          "media_type": "episode",
                          "parent_media_index": "6",
                          "parent_rating_key": "153036",
                          "parent_thumb": "/library/metadata/153036/thumb/1462175062",
                          "parent_title": "",
                          "rating_key": "153037",
                          "section_id": "2",
                          "thumb": "/library/metadata/153037/thumb/1462175060",
                          "title": "The Red Woman",
                          "year": "2016"
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_recently_added_details(start=start, count=count, section_id=section_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_recently_added_details.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_friends_list(self, **kwargs):
        """ Get the friends list of the server owner for Plex.tv. """

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_friends('json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_friends_list.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_user_details(self, **kwargs):
        """ Get all details about a the server's owner from Plex.tv. """

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_user_details('json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_user_details.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_server_list(self, **kwargs):
        """ Find all servers published on Plex.tv """

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_server_list('json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_list.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_sync_lists(self, machine_id='', **kwargs):
        """ Get all items that are currently synced from the PMS. """
        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_sync_lists(machine_id=machine_id, output_format='json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_sync_lists.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_servers(self, **kwargs):
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_list(output_format='json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_servers.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_servers_info(self, **kwargs):
        """ Get info about the PMS.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"port": "32400",
                      "host": "10.0.0.97",
                      "version": "0.9.15.2.1663-7efd046",
                      "name": "Winterfell-Server",
                      "machine_identifier": "ds48g4r354a8v9byrrtr697g3g79w"
                      }
                     ]
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_servers_info()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_servers_info.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_server_identity(self, **kwargs):
        """ Get info about the local server.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"machine_identifier": "ds48g4r354a8v9byrrtr697g3g79w",
                      "version": "0.9.15.x.xxx-xxxxxxx"
                      }
                     ]
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_identity()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_identity.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_server_friendly_name(self, **kwargs):
        """ Get the name of the PMS.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                string:     "Winterfell-Server"
            ```
        """
        result = pmsconnect.get_server_friendly_name()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_friendly_name.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_activity(self, **kwargs):
        """ Get the current activity on the PMS.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {"stream_count": 3,
                     "session":
                        [{"art": "/library/metadata/1219/art/1462175063",
                          "aspect_ratio": "1.78",
                          "audio_channels": "6",
                          "audio_codec": "ac3",
                          "audio_decision": "transcode",
                          "bif_thumb": "/library/parts/274169/indexes/sd/",
                          "bitrate": "10617",
                          "container": "mkv",
                          "content_rating": "TV-MA",
                          "duration": "2998290",
                          "friendly_name": "Mother of Dragons",
                          "grandparent_rating_key": "1219",
                          "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
                          "grandparent_title": "Game of Thrones",
                          "height": "1078",
                          "indexes": 1,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "labels": [],
                          "machine_id": "83f189w617623ccs6a1lqpby",
                          "media_index": "1",
                          "media_type": "episode",
                          "parent_media_index": "6",
                          "parent_rating_key": "153036",
                          "parent_thumb": "/library/metadata/153036/thumb/1462175062",
                          "parent_title": "",
                          "platform": "Chrome",
                          "player": "Plex Web (Chrome)",
                          "progress_percent": "0",
                          "rating_key": "153037",
                          "section_id": "2",
                          "session_key": "291",
                          "state": "playing",
                          "throttled": "1",
                          "thumb": "/library/metadata/153037/thumb/1462175060",
                          "title": "The Red Woman",
                          "transcode_audio_channels": "2",
                          "transcode_audio_codec": "aac",
                          "transcode_container": "mkv",
                          "transcode_height": "1078",
                          "transcode_key": "tiv5p524wcupe8nxegc26s9k9",
                          "transcode_progress": 2,
                          "transcode_protocol": "http",
                          "transcode_speed": "0.0",
                          "transcode_video_codec": "h264",
                          "transcode_width": "1920",
                          "user": "DanyKhaleesi69",
                          "user_id": 8008135,
                          "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar",
                          "video_codec": "h264",
                          "video_decision": "copy",
                          "video_framerate": "24p",
                          "video_resolution": "1080",
                          "view_offset": "",
                          "width": "1920",
                          "year": "2016"
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        pms_connect = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
        result = pms_connect.get_current_activity()

        if result:
            data_factory = datafactory.DataFactory()
            for session in result['sessions']:
                if not session['ip_address']:
                    ip_address = data_factory.get_session_ip(session['session_key'])
                    session['ip_address'] = ip_address

            return result
        else:
            logger.warn(u"Unable to retrieve data for get_activity.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_libraries")
    def get_full_libraries_list(self, **kwargs):
        """ Get a list of all libraries on your server.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"art": "/:/resources/show-fanart.jpg",
                      "child_count": "3745",
                      "count": "62",
                      "parent_count": "240",
                      "section_id": "2",
                      "section_name": "TV Shows",
                      "section_type": "show",
                      "thumb": "/:/resources/show.png"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_library_details()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_full_libraries_list.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_users")
    def get_full_users_list(self, **kwargs):
        """ Get a list of all users that have access to your server.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"email": "Jon.Snow.1337@CastleBlack.com",
                      "filter_all": "",
                      "filter_movies": "",
                      "filter_music": "",
                      "filter_photos": "",
                      "filter_tv": "",
                      "is_allow_sync": null,
                      "is_home_user": "1",
                      "is_restricted": "0",
                      "thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
                      "user_id": "133788",
                      "username": "Jon Snow"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        plex_tv = plextv.PlexTV()
        result = plex_tv.get_full_users_list()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_full_users_list.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_synced_items(self, machine_id='', user_id='', **kwargs):
        """ Get a list of synced items on the PMS.

            ```
            Required parameters:
                machine_id (str):       The PMS identifier

            Optional parameters:
                user_id (str):          The id of the Plex user

            Returns:
                json:
                    [{"content_type": "video",
                      "device_name": "Tyrion's iPad",
                      "failure": "",
                      "friendly_name": "Tyrion Lannister",
                      "item_complete_count": "0",
                      "item_count": "1",
                      "item_downloaded_count": "0",
                      "item_downloaded_percent_complete": 0,
                      "metadata_type": "movie",
                      "music_bitrate": "192",
                      "photo_quality": "74",
                      "platform": "iOS",
                      "rating_key": "154092",
                      "root_title": "Deadpool",
                      "state": "pending",
                      "sync_id": "11617019",
                      "title": "Deadpool",
                      "total_size": "0",
                      "user_id": "696969",
                      "username": "DrukenDwarfMan",
                      "video_quality": "60"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        plex_tv = plextv.PlexTV()
        result = plex_tv.get_synced_items(machine_id=machine_id, user_id=user_id)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_synced_items.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_sync_transcode_queue(self, **kwargs):
        """ Return details for currently syncing items. """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sync_transcode_queue(output_format='json')

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_sync_transcode_queue.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_home_stats(self, grouping=0, time_range='30', stats_type=0, stats_count='5', **kwargs):
        """ Get the homepage watch statistics.

            ```
            Required parameters:
                None

            Optional parameters:
                grouping (int):         0 or 1
                time_range (str):       The time range to calculate statistics, '30'
                stats_type (int):       0 for plays, 1 for duration
                stats_count (str):      The number of top items to list, '5'

            Returns:
                json:
                    [{"stat_id": "top_movies",
                      "stat_type": "total_plays",
                      "rows": [{...}]
                      },
                     {"stat_id": "popular_movies",
                      "rows": [{...}]
                      },
                     {"stat_id": "top_tv",
                      "stat_type": "total_plays",
                      "rows":
                        [{"content_rating": "TV-MA",
                          "friendly_name": "",
                          "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
                          "labels": [],
                          "last_play": 1462380698,
                          "media_type": "episode",
                          "platform": "",
                          "platform_type": "",
                          "rating_key": 1219,
                          "row_id": 1116,
                          "section_id": 2,
                          "thumb": "",
                          "title": "Game of Thrones",
                          "total_duration": 213302,
                          "total_plays": 69,
                          "user": "",
                          "users_watched": ""
                          },
                         {...},
                         {...}
                         ]
                      },
                     {"stat_id": "popular_tv",
                      "rows": [{...}]
                      },
                     {"stat_id": "top_music",
                      "stat_type": "total_plays",
                      "rows": [{...}]
                      },
                     {"stat_id": "popular_music",
                      "rows": [{...}]
                      },
                     {"stat_id": "last_watched",
                      "rows": [{...}]
                      },
                     {"stat_id": "top_users",
                      "stat_type": "total_plays",
                      "rows": [{...}]
                      },
                     {"stat_id": "top_platforms",
                      "stat_type": "total_plays",
                      "rows": [{...}]
                      },
                     {"stat_id": "most_concurrent",
                      "rows": [{...}]
                      }
                     ]
            ```
        """
        stats_cards = plexpy.CONFIG.HOME_STATS_CARDS
        notify_watched_percent = plexpy.CONFIG.NOTIFY_WATCHED_PERCENT

        data_factory = datafactory.DataFactory()
        result = data_factory.get_home_stats(grouping=grouping,
                                             time_range=time_range,
                                             stats_type=stats_type,
                                             stats_count=stats_count,
                                             stats_cards=stats_cards,
                                             notify_watched_percent=notify_watched_percent)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_home_stats.")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi("arnold")
    def random_arnold_quotes(self, **kwargs):
        """ Get to the chopper! """
        from random import randint
        quote_list = ['To crush your enemies, see them driven before you, and to hear the lamentation of their women!',
                      'Your clothes, give them to me, now!',
                      'Do it!',
                      'If it bleeds, we can kill it',
                      'See you at the party Richter!',
                      'Let off some steam, Bennett',
                      'I\'ll be back',
                      'Get to the chopper!',
                      'Hasta La Vista, Baby!',
                      'It\'s not a tumor!',
                      'Dillon, you son of a bitch!',
                      'Benny!! Screw you!!',
                      'Stop whining! You kids are soft. You lack discipline.',
                      'Nice night for a walk.',
                      'Stick around!',
                      'I need your clothes, your boots and your motorcycle.',
                      'No, it\'s not a tumor. It\'s not a tumor!',
                      'I LIED!',
                      'Are you Sarah Connor?',
                      'I\'m a cop you idiot!',
                      'Come with me if you want to live.',
                      'Who is your daddy and what does he do?',
                      'Oh, cookies! I can\'t wait to toss them.',
                      'Can you hurry up. My horse is getting tired.',
                      'What killed the dinosaurs? The Ice Age!',
                      'That\'s for sleeping with my wife!',
                      'Remember when I said I’d kill you last... I lied!',
                      'You want to be a farmer? Here\'s a couple of acres',
                      'Now, this is the plan. Get your ass to Mars.',
                      'I just had a terrible thought... What if this is a dream?'
                      ]

        random_number = randint(0, len(quote_list) - 1)
        return quote_list[int(random_number)]

    ### API ###

    @cherrypy.expose
    def api(self, *args, **kwargs):
        if args and 'v2' in args[0]:
            return API2()._api_run(**kwargs)
        else:
            a = Api()
            a.checkParams(*args, **kwargs)
            return a.fetchData()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def check_pms_updater(self):
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_update_staus()
        return result
