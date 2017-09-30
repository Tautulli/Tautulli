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
import helpers
import http_handler
import libraries
import log_reader
import logger
import mobile_app
import notification_handler
import notifiers
import plextv
import plexivity_import
import plexwatch_import
import pmsconnect
import users
import versioncheck
import web_socket
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
    def index(self, **kwargs):
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
    def home(self, **kwargs):
        config = {
            "home_sections": plexpy.CONFIG.HOME_SECTIONS,
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_type": plexpy.CONFIG.HOME_STATS_TYPE,
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "home_stats_recently_added_count": plexpy.CONFIG.HOME_STATS_RECENTLY_ADDED_COUNT,
            "pms_name": plexpy.CONFIG.PMS_NAME,
            "pms_use_bif": plexpy.CONFIG.PMS_USE_BIF,
            "update_show_changelog": plexpy.CONFIG.UPDATE_SHOW_CHANGELOG
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
                    elif s['video_decision'] == 'copy' or s['audio_decision'] == 'copy':
                        data['direct_stream'] += 1
                    else:
                        data['direct_play'] += 1

            return serve_template(templatename="current_activity_header.html", data=data)
        else:
            logger.warn(u"Unable to retrieve data for get_current_activity_header.")
            return serve_template(templatename="current_activity_header.html", data=None)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def terminate_session(self, session_id=None, message=None, **kwargs):
        """ Add a new notification agent.

            ```
            Required parameters:
                session_id (str):           The id of the session to terminate
                message (str):              A custom message to send to the client

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.terminate_session(session_id=session_id, message=message)

        if result:
            return {'result': 'success', 'message': 'Session terminated.'}
        else:
            return {'result': 'error', 'message': 'Failed to terminate session.'}

    @cherrypy.expose
    @requireAuth()
    def home_stats(self, time_range=30, stats_type=0, stats_count=5, **kwargs):
        data_factory = datafactory.DataFactory()
        stats_data = data_factory.get_home_stats(time_range=time_range,
                                                 stats_type=stats_type,
                                                 stats_count=stats_count)

        return serve_template(templatename="home_stats.html", title="Stats", data=stats_data)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def set_home_stats_config(self, time_range=None, stats_type=None, stats_count=None, recently_added_count=None, **kwargs):
        if time_range:
            plexpy.CONFIG.__setattr__('HOME_STATS_LENGTH', time_range)
            plexpy.CONFIG.write()
        if stats_type:
            plexpy.CONFIG.__setattr__('HOME_STATS_TYPE', stats_type)
            plexpy.CONFIG.write()
        if stats_count:
            plexpy.CONFIG.__setattr__('HOME_STATS_COUNT', stats_count)
            plexpy.CONFIG.write()
        if recently_added_count:
            plexpy.CONFIG.__setattr__('HOME_STATS_RECENTLY_ADDED_COUNT', recently_added_count)
            plexpy.CONFIG.write()

        return "Updated home stats config values."

    @cherrypy.expose
    @requireAuth()
    def library_stats(self, **kwargs):
        data_factory = datafactory.DataFactory()

        library_cards = plexpy.CONFIG.HOME_LIBRARY_CARDS

        stats_data = data_factory.get_library_stats(library_cards=library_cards)

        return serve_template(templatename="library_stats.html", title="Library Stats", data=stats_data)

    @cherrypy.expose
    @requireAuth()
    def get_recently_added(self, count='0', type='', **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(count=count, type=type)
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
    @addtoapi()
    def delete_temp_sessions(self, **kwargs):
        """ Flush out all of the temporary sessions in the database."""

        result = database.delete_sessions()

        if result:
            return {'result': 'success', 'message': 'Temporary sessions flushed.'}
        else:
            return {'result': 'error', 'message': 'Flush sessions failed.'}


    ##### Libraries #####

    @cherrypy.expose
    @requireAuth()
    def libraries(self, **kwargs):
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
    def library(self, section_id=None, **kwargs):
        if not allow_session_library(section_id):
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        config = {
            "get_file_sizes": plexpy.CONFIG.GET_FILE_SIZES,
            "get_file_sizes_hold": plexpy.CONFIG.GET_FILE_SIZES_HOLD
        }

        if section_id:
            try:
                library_data = libraries.Libraries()
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
        if section_id:
            library_data = libraries.Libraries()
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

        if section_id:
            try:
                library_data = libraries.Libraries()
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
    def library_watch_time_stats(self, section_id=None, **kwargs):
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
            logger.warn(u"Unable to retrieve data for library_watch_time_stats.")
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def library_user_stats(self, section_id=None, **kwargs):
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
            logger.warn(u"Unable to retrieve data for library_user_stats.")
            return serve_template(templatename="library_user_stats.html", data=None, title="Player Stats")

    @cherrypy.expose
    @requireAuth()
    def library_recently_watched(self, section_id=None, limit='10', **kwargs):
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
            logger.warn(u"Unable to retrieve data for library_recently_watched.")
            return serve_template(templatename="user_recently_watched.html", data=None, title="Recently Watched")

    @cherrypy.expose
    @requireAuth()
    def library_recently_added(self, section_id=None, limit='10', **kwargs):
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
            logger.warn(u"Unable to retrieve data for library_recently_added.")
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
    def get_media_info_file_sizes(self, section_id=None, rating_key=None, **kwargs):
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
    def get_library(self, section_id=None, **kwargs):
        """ Get a library's details.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section

            Optional parameters:
                None

            Returns:
                json:
                    {"child_count": null,
                     "count": 887,
                     "do_notify": 1,
                     "do_notify_created": 1,
                     "keep_history": 1,
                     "library_art": "/:/resources/movie-fanart.jpg",
                     "library_thumb": "/:/resources/movie.png",
                     "parent_count": null,
                     "section_id": 1,
                     "section_name": "Movies",
                     "section_type": "movie"
                     }
            ```
        """
        if section_id:
            library_data = libraries.Libraries()
            library_details = library_data.get_details(section_id=section_id)
            if library_details:
                return library_details
            else:
                logger.warn(u"Unable to retrieve data for get_library.")
        else:
            logger.warn(u"Library details requested but no section_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_library_watch_time_stats(self, section_id=None, **kwargs):
        """ Get a library's watch time statistics.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section

            Optional parameters:
                None

            Returns:
                json:
                    [{"query_days": 1,
                      "total_plays": 0,
                      "total_time": 0
                      },
                     {"query_days": 7,
                      "total_plays": 3,
                      "total_time": 15694
                      },
                     {"query_days": 30,
                      "total_plays": 35,
                      "total_time": 63054
                      },
                     {"query_days": 0,
                      "total_plays": 508,
                      "total_time": 1183080
                      }
                     ]
            ```
        """
        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_watch_time_stats(section_id=section_id)
            if result:
                return result
            else:
                logger.warn(u"Unable to retrieve data for get_library_watch_time_stats.")
        else:
            logger.warn(u"Library watch time stats requested but no section_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_library_user_stats(self, section_id=None, **kwargs):
        """ Get a library's user statistics.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section

            Optional parameters:
                None

            Returns:
                json:
                    [{"friendly_name": "Jon Snow",
                      "total_plays": 170,
                      "user_id": 133788,
                      "user_thumb": "https://plex.tv/users/k10w42309cynaopq/avatar"
                      },
                     {"platform_type": "DanyKhaleesi69",
                      "total_plays": 42,
                      "user_id": 8008135,
                      "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_user_stats(section_id=section_id)
            if result:
                return result
            else:
                logger.warn(u"Unable to retrieve data for get_library_user_stats.")
        else:
            logger.warn(u"Library user stats requested but no section_id received.")

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
    def delete_duplicate_libraries(self, **kwargs):
        library_data = libraries.Libraries()

        result = library_data.delete_duplicate_libraries()

        if result:
            return {'message': result}
        else:
            return {'message': 'Unable to delete duplicate libraries from the database.'}

    ##### Users #####

    @cherrypy.expose
    @requireAuth()
    def users(self, **kwargs):
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
    def user(self, user_id=None, **kwargs):
        if not allow_session_user(user_id):
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        if user_id:
            try:
                user_data = users.Users()
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
        if user_id:
            user_data = users.Users()
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

        if user_id:
            try:
                user_data = users.Users()
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
    def user_watch_time_stats(self, user=None, user_id=None, **kwargs):
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
            logger.warn(u"Unable to retrieve data for user_watch_time_stats.")
            return serve_template(templatename="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def user_player_stats(self, user=None, user_id=None, **kwargs):
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
            logger.warn(u"Unable to retrieve data for user_player_stats.")
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
    def get_user(self, user_id=None, **kwargs):
        """ Get a user's details.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                None

            Returns:
                json:
                    {"allow_guest": 1,
                     "deleted_user": 0,
                     "do_notify": 1,
                     "email": "Jon.Snow.1337@CastleBlack.com",
                     "friendly_name": "Jon Snow",
                     "is_allow_sync": 1,
                     "is_home_user": 1,
                     "is_restricted": 0,
                     "keep_history": 1,
                     "shared_libraries": ["10", "1", "4", "5", "15", "20", "2"],
                     "user_id": 133788,
                     "user_thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
                     "username": "LordCommanderSnow"
                     }
            ```
        """
        if user_id:
            user_data = users.Users()
            user_details = user_data.get_details(user_id=user_id)
            if user_details:
                return user_details
            else:
                logger.warn(u"Unable to retrieve data for get_user.")
        else:
            logger.warn(u"User details requested but no user_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_user_watch_time_stats(self, user_id=None, **kwargs):
        """ Get a user's watch time statistics.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                None

            Returns:
                json:
                    [{"query_days": 1,
                      "total_plays": 0,
                      "total_time": 0
                      },
                     {"query_days": 7,
                      "total_plays": 3,
                      "total_time": 15694
                      },
                     {"query_days": 30,
                      "total_plays": 35,
                      "total_time": 63054
                      },
                     {"query_days": 0,
                      "total_plays": 508,
                      "total_time": 1183080
                      }
                     ]
            ```
        """
        if user_id:
            user_data = users.Users()
            result = user_data.get_watch_time_stats(user_id=user_id)
            if result:
                return result
            else:
                logger.warn(u"Unable to retrieve data for get_user_watch_time_stats.")
        else:
            logger.warn(u"User watch time stats requested but no user_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_user_player_stats(self, user_id=None, **kwargs):
        """ Get a user's player statistics.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                None

            Returns:
                json:
                    [{"platform_type": "Chrome",
                      "player_name": "Plex Web (Chrome)",
                      "result_id": 1,
                      "total_plays": 170
                      },
                     {"platform_type": "Chromecast",
                      "player_name": "Chromecast",
                      "result_id": 2,
                      "total_plays": 42
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        if user_id:
            user_data = users.Users()
            result = user_data.get_player_stats(user_id=user_id)
            if result:
                return result
            else:
                logger.warn(u"Unable to retrieve data for get_user_player_stats.")
        else:
            logger.warn(u"User watch time stats requested but no user_id received.")

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
        if user_id:
            user_data = users.Users()
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
        if user_id:
            user_data = users.Users()
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
        if user_id:
            user_data = users.Users()
            delete_row = user_data.undelete(user_id=user_id)
            if delete_row:
                return {'message': delete_row}
        elif username:
            user_data = users.Users()
            delete_row = user_data.undelete(username=username)
            if delete_row:
                return {'message': delete_row}
        else:
            return {'message': 'no data received'}


    ##### History #####

    @cherrypy.expose
    @requireAuth()
    def history(self, **kwargs):
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
                        [{"date": 1462687607,
                          "duration": 263,
                          "friendly_name": "Mother of Dragons",
                          "full_title": "Game of Thrones - The Red Woman",
                          "grandparent_rating_key": 351,
                          "grandparent_title": "Game of Thrones",
                          "group_count": 1,
                          "group_ids": "1124",
                          "id": 1124,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "media_index": 17,
                          "media_type": "episode",
                          "parent_media_index": 7,
                          "parent_rating_key": 544,
                          "parent_title": "",
                          "paused_counter": 0,
                          "percent_complete": 84,
                          "platform": "Chrome",
                          "player": "Plex Web (Chrome)",
                          "rating_key": 4348,
                          "reference_id": 1123,
                          "session_key": null,
                          "started": 1462688107,
                          "state": null,
                          "stopped": 1462688370,
                          "thumb": "/library/metadata/4348/thumb/1462414561",
                          "title": "The Red Woman",
                          "transcode_decision": "transcode",
                          "user": "DanyKhaleesi69",
                          "user_id": 8008135,
                          "watched_status": 0,
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
    def get_stream_data(self, row_id=None, session_key=None, user=None, **kwargs):

        data_factory = datafactory.DataFactory()
        stream_data = data_factory.get_stream_details(row_id, session_key)

        return serve_template(templatename="stream_data.html", title="Stream Data", data=stream_data, user=user)

    @cherrypy.expose
    @requireAuth()
    def get_ip_address_details(self, ip_address=None, **kwargs):
        if not helpers.is_valid_ip(ip_address):
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
    def graphs(self, **kwargs):

        config = {
            "graph_type": plexpy.CONFIG.GRAPH_TYPE,
            "graph_days": plexpy.CONFIG.GRAPH_DAYS,
            "graph_months": plexpy.CONFIG.GRAPH_MONTHS,
            "graph_tab": plexpy.CONFIG.GRAPH_TAB,
            "music_logging_enable": plexpy.CONFIG.MUSIC_LOGGING_ENABLE
        }

        return serve_template(templatename="graphs.html", title="Graphs", config=config)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def set_graph_config(self, graph_type=None, graph_days=None, graph_months=None, graph_tab=None, **kwargs):
        if graph_type:
            plexpy.CONFIG.__setattr__('GRAPH_TYPE', graph_type)
            plexpy.CONFIG.write()
        if graph_days:
            plexpy.CONFIG.__setattr__('GRAPH_DAYS', graph_days)
            plexpy.CONFIG.write()
        if graph_months:
            plexpy.CONFIG.__setattr__('GRAPH_MONTHS', graph_months)
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
    def get_plays_per_month(self, time_range='12', y_axis='plays', user_id=None, **kwargs):
        """ Get graph data by month.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of months of data to return
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
        result = graph.get_total_plays_per_month(time_range=time_range, y_axis=y_axis, user_id=user_id)

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
    def sync(self, **kwargs):
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
    def logs(self, **kwargs):
        return serve_template(templatename="logs.html", title="Log")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_log(self, logfile='', **kwargs):
        json_data = helpers.process_json_kwargs(json_kwargs=kwargs.get('json_data'))
        log_level = kwargs.get('log_level', "")

        start = json_data['start']
        length = json_data['length']
        order_column = json_data['order'][0]['column']
        order_dir = json_data['order'][0]['dir']
        search_value = json_data['search']['value']
        sortcolumn = 0

        filt = []
        filtered = []
        fa = filt.append

        if logfile == "plexpy_api":
            filename = logger.FILENAME_API
        elif logfile == "plexpy_websocket":
            filename = logger.FILENAME_WEBSOCKET
        else:
            filename = logger.FILENAME

        with open(os.path.join(plexpy.CONFIG.LOG_DIR, filename)) as f:
            for l in f.readlines():
                try:
                    temp_loglevel_and_time = l.split(' - ', 1)
                    loglvl = temp_loglevel_and_time[1].split(' ::', 1)[0].strip()
                    msg = unicode(l.split(' : ', 1)[1].replace('\n', ''), 'utf-8')
                    fa([temp_loglevel_and_time[0], loglvl, msg])
                except IndexError:
                    # Add traceback message to previous msg.
                    tl = (len(filt) - 1)
                    n = len(l) - len(l.lstrip(' '))
                    l = '&nbsp;' * (2 * n) + l[n:]
                    filt[tl][2] += '<br>' + l
                    continue

        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if log_level in log_levels:
            log_levels = log_levels[log_levels.index(log_level)::]
            filtered = [row for row in filt if row[1] in log_levels]
        else:
            filtered = filt

        if search_value:
            filtered = [row for row in filtered for column in row if search_value.lower() in column.lower()]

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
    def get_plex_log(self, **kwargs):
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
        window = int(kwargs.get('window', plexpy.CONFIG.PMS_LOGS_LINE_CAP))
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
    def delete_logs(self, logfile='', **kwargs):
        if logfile == "plexpy_api":
            filename = logger.FILENAME_API
        elif logfile == "plexpy_websocket":
            filename = logger.FILENAME_WEBSOCKET
        else:
            filename = logger.FILENAME

        try:
            open(os.path.join(plexpy.CONFIG.LOG_DIR, filename), 'w').close()
            result = 'success'
            msg = 'Cleared the %s file.' % filename
            logger.info(msg)
        except Exception as e:
            result = 'error'
            msg = 'Failed to clear the %s file.' % filename
            logger.exception(u'Failed to clear the %s file: %s.' % (filename, e))

        return {'result': result, 'message': msg}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def toggleVerbose(self, **kwargs):
        plexpy.VERBOSE = not plexpy.VERBOSE
        logger.initLogger(console=not plexpy.QUIET,
                          log_dir=plexpy.CONFIG.LOG_DIR, verbose=plexpy.VERBOSE)
        logger.info(u"Verbose toggled, set to %s", plexpy.VERBOSE)
        logger.debug(u"If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "logs")

    @cherrypy.expose
    @requireAuth()
    def log_js_errors(self, page, message, file, line, **kwargs):
        """ Logs javascript errors from the web interface. """
        logger.error(u"WebUI :: /%s : %s. (%s:%s)" % (page.rpartition('/')[-1],
                                                      message,
                                                      file.rpartition('/')[-1].partition('?')[0],
                                                      line))
        return "js error logged."

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def logFile(self, **kwargs):
        try:
            with open(os.path.join(plexpy.CONFIG.LOG_DIR, logger.FILENAME), 'r') as f:
                return '<pre>%s</pre>' % f.read()
        except IOError as e:
            return "Log file not found."


    ##### Settings #####

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def settings(self, **kwargs):
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
            "history_table_activity": checked(plexpy.CONFIG.HISTORY_TABLE_ACTIVITY),
            "http_basic_auth": checked(plexpy.CONFIG.HTTP_BASIC_AUTH),
            "http_hash_password": checked(plexpy.CONFIG.HTTP_HASH_PASSWORD),
            "http_hashed_password": plexpy.CONFIG.HTTP_HASHED_PASSWORD,
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": http_password,
            "http_root": plexpy.CONFIG.HTTP_ROOT,
            "launch_browser": checked(plexpy.CONFIG.LAUNCH_BROWSER),
            "enable_https": checked(plexpy.CONFIG.ENABLE_HTTPS),
            "https_create_cert": checked(plexpy.CONFIG.HTTPS_CREATE_CERT),
            "https_cert": plexpy.CONFIG.HTTPS_CERT,
            "https_cert_chain": plexpy.CONFIG.HTTPS_CERT_CHAIN,
            "https_key": plexpy.CONFIG.HTTPS_KEY,
            "https_domain": plexpy.CONFIG.HTTPS_DOMAIN,
            "https_ip": plexpy.CONFIG.HTTPS_IP,
            "anon_redirect": plexpy.CONFIG.ANON_REDIRECT,
            "api_enabled": checked(plexpy.CONFIG.API_ENABLED),
            "api_key": plexpy.CONFIG.API_KEY,
            "update_db_interval": plexpy.CONFIG.UPDATE_DB_INTERVAL,
            "freeze_db": checked(plexpy.CONFIG.FREEZE_DB),
            "backup_days": plexpy.CONFIG.BACKUP_DAYS,
            "backup_dir": plexpy.CONFIG.BACKUP_DIR,
            "backup_interval": plexpy.CONFIG.BACKUP_INTERVAL,
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
            "week_start_monday": checked(plexpy.CONFIG.WEEK_START_MONDAY),
            "get_file_sizes": checked(plexpy.CONFIG.GET_FILE_SIZES),
            "grouping_global_history": checked(plexpy.CONFIG.GROUPING_GLOBAL_HISTORY),
            "grouping_user_history": checked(plexpy.CONFIG.GROUPING_USER_HISTORY),
            "grouping_charts": checked(plexpy.CONFIG.GROUPING_CHARTS),
            "monitor_pms_updates": checked(plexpy.CONFIG.MONITOR_PMS_UPDATES),
            "monitor_remote_access": checked(plexpy.CONFIG.MONITOR_REMOTE_ACCESS),
            "monitoring_interval": plexpy.CONFIG.MONITORING_INTERVAL,
            "refresh_libraries_interval": plexpy.CONFIG.REFRESH_LIBRARIES_INTERVAL,
            "refresh_libraries_on_startup": checked(plexpy.CONFIG.REFRESH_LIBRARIES_ON_STARTUP),
            "refresh_users_interval": plexpy.CONFIG.REFRESH_USERS_INTERVAL,
            "refresh_users_on_startup": checked(plexpy.CONFIG.REFRESH_USERS_ON_STARTUP),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "pms_is_remote": checked(plexpy.CONFIG.PMS_IS_REMOTE),
            "notify_consecutive": checked(plexpy.CONFIG.NOTIFY_CONSECUTIVE),
            "notify_upload_posters": checked(plexpy.CONFIG.NOTIFY_UPLOAD_POSTERS),
            "notify_recently_added_upgrade": checked(plexpy.CONFIG.NOTIFY_RECENTLY_ADDED_UPGRADE),
            "notify_group_recently_added_grandparent": checked(plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_GRANDPARENT),
            "notify_group_recently_added_parent": checked(plexpy.CONFIG.NOTIFY_GROUP_RECENTLY_ADDED_PARENT),
            "notify_concurrent_by_ip": checked(plexpy.CONFIG.NOTIFY_CONCURRENT_BY_IP),
            "notify_concurrent_threshold": plexpy.CONFIG.NOTIFY_CONCURRENT_THRESHOLD,
            "home_sections": json.dumps(plexpy.CONFIG.HOME_SECTIONS),
            "home_stats_cards": json.dumps(plexpy.CONFIG.HOME_STATS_CARDS),
            "home_library_cards": json.dumps(plexpy.CONFIG.HOME_LIBRARY_CARDS),
            "buffer_threshold": plexpy.CONFIG.BUFFER_THRESHOLD,
            "buffer_wait": plexpy.CONFIG.BUFFER_WAIT,
            "group_history_tables": checked(plexpy.CONFIG.GROUP_HISTORY_TABLES),
            "git_token": plexpy.CONFIG.GIT_TOKEN,
            "imgur_client_id": plexpy.CONFIG.IMGUR_CLIENT_ID,
            "cache_images": checked(plexpy.CONFIG.CACHE_IMAGES),
            "pms_version": plexpy.CONFIG.PMS_VERSION,
            "plexpy_auto_update": checked(plexpy.CONFIG.PLEXPY_AUTO_UPDATE),
            "git_branch": plexpy.CONFIG.GIT_BRANCH,
            "git_path": plexpy.CONFIG.GIT_PATH,
            "git_remote": plexpy.CONFIG.GIT_REMOTE,
            "movie_watched_percent": plexpy.CONFIG.MOVIE_WATCHED_PERCENT,
            "tv_watched_percent": plexpy.CONFIG.TV_WATCHED_PERCENT,
            "music_watched_percent": plexpy.CONFIG.MUSIC_WATCHED_PERCENT
        }

        return serve_template(templatename="settings.html", title="Settings", config=config, kwargs=kwargs)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "launch_browser", "enable_https", "https_create_cert", "api_enabled", "freeze_db", "check_github",
            "grouping_global_history", "grouping_user_history", "grouping_charts", "group_history_tables",
            "pms_use_bif", "pms_ssl", "pms_is_remote", "home_stats_type", "week_start_monday",
            "refresh_libraries_on_startup", "refresh_users_on_startup",
            "notify_consecutive", "notify_upload_posters", "notify_recently_added_upgrade",
            "notify_group_recently_added_grandparent", "notify_group_recently_added_parent",
            "monitor_pms_updates", "monitor_remote_access", "get_file_sizes", "log_blacklist", "http_hash_password",
            "allow_guest_access", "cache_images", "http_basic_auth", "notify_concurrent_by_ip",
            "history_table_activity", "plexpy_auto_update"
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
    def backup_config(self, **kwargs):
        """ Creates a manual backup of the plexpy.db file """

        result = config.make_backup()

        if result:
            return {'result': 'success', 'message': 'Config backup successful.'}
        else:
            return {'result': 'error', 'message': 'Config backup failed.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_configuration_table(self, **kwargs):
        return serve_template(templatename="configuration_table.html")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_scheduler_table(self, **kwargs):
        return serve_template(templatename="scheduler_table.html")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_server_update_params(self, **kwargs):
        plex_tv = plextv.PlexTV()
        plexpass = plex_tv.get_plexpass_status()
        return {'plexpass': plexpass,
                'pms_platform': common.PMS_PLATFORM_NAME_OVERRIDES.get(
                    plexpy.CONFIG.PMS_PLATFORM, plexpy.CONFIG.PMS_PLATFORM),
                'pms_update_channel': plexpy.CONFIG.PMS_UPDATE_CHANNEL,
                'pms_update_distro': plexpy.CONFIG.PMS_UPDATE_DISTRO,
                'pms_update_distro_build': plexpy.CONFIG.PMS_UPDATE_DISTRO_BUILD}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def backup_db(self, **kwargs):
        """ Creates a manual backup of the plexpy.db file """

        result = database.make_backup()

        if result:
            return {'result': 'success', 'message': 'Database backup successful.'}
        else:
            return {'result': 'error', 'message': 'Database backup failed.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def install_geoip_db(self, **kwargs):
        """ Downloads and installs the GeoLite2 database """

        result = helpers.install_geoip_db()

        if result:
            return {'result': 'success', 'message': 'GeoLite2 database installed successful.'}
        else:
            return {'result': 'error', 'message': 'GeoLite2 database install failed.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def uninstall_geoip_db(self, **kwargs):
        """ Uninstalls the GeoLite2 database """

        result = helpers.uninstall_geoip_db()

        if result:
            return {'result': 'success', 'message': 'GeoLite2 database uninstalled successfully.'}
        else:
            return {'result': 'error', 'message': 'GeoLite2 database uninstall failed.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_notifiers(self, notify_action=None, **kwargs):
        """ Get a list of configured notifiers.

            ```
            Required parameters:
                None

            Optional parameters:
                notify_action (str):        The notification action to filter out

            Returns:
                json:
                    [{"id": 1,
                      "agent_id": 13,
                      "agent_name": "telegram",
                      "agent_label": "Telegram",
                      "friendly_name": "",
                      "active": 1
                      }
                     ]
            ```
        """
        result = notifiers.get_notifiers(notify_action=notify_action)
        return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_notifiers_table(self, **kwargs):
        result = notifiers.get_notifiers()
        return serve_template(templatename="notifiers_table.html", notifiers_list=result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_notifier(self, notifier_id=None, **kwargs):
        """ Remove a notifier from the database.

            ```
            Required parameters:
                notifier_id (int):        The notifier to delete

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        result = notifiers.delete_notifier(notifier_id=notifier_id)
        if result:
            return {'result': 'success', 'message': 'Notifier deleted successfully.'}
        else:
            return {'result': 'error', 'message': 'Failed to delete notifier.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_notifier_config(self, notifier_id=None, **kwargs):
        """ Get the configuration for an existing notification agent.

            ```
            Required parameters:
                notifier_id (int):        The notifier config to retrieve

            Optional parameters:
                None

            Returns:
                json:
                    {"id": 1,
                     "agent_id": 13,
                     "agent_name": "telegram",
                     "agent_label": "Telegram",
                     "friendly_name": "",
                     "config": {"incl_poster": 0,
                                "html_support": 1,
                                "chat_id": "123456",
                                "bot_token": "13456789:fio9040NNo04jLEp-4S",
                                "incl_subject": 1,
                                "disable_web_preview": 0
                                },
                     "config_options": [{...}, ...]
                     "actions": {"on_play": 0,
                                 "on_stop": 0,
                                 ...
                                 },
                     "notify_text": {"on_play": {"subject": "...",
                                                 "body": "..."
                                                 }
                                     "on_stop": {"subject": "...",
                                                 "body": "..."
                                                 }
                                     ...
                                     }
                     }
            ```
        """
        result = notifiers.get_notifier_config(notifier_id=notifier_id)
        return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_notifier_config_modal(self, notifier_id=None, **kwargs):
        result = notifiers.get_notifier_config(notifier_id=notifier_id)

        if not result['custom_conditions']:
            result['custom_conditions'] = json.dumps([{'parameter': '', 'operator': '', 'value': ''}])

        if not result['custom_conditions_logic']:
            result['custom_conditions_logic'] = ''

        parameters = [
                {'name': param['name'], 'type': param['type'], 'value': param['value']}
                for category in common.NOTIFICATION_PARAMETERS for param in category['parameters']
            ]

        return serve_template(templatename="notifier_config.html", notifier=result, parameters=json.dumps(parameters))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def add_notifier_config(self, agent_id=None, **kwargs):
        """ Add a new notification agent.

            ```
            Required parameters:
                agent_id (int):           The notification agent to add

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        result = notifiers.add_notifier_config(agent_id=agent_id, **kwargs)

        if result:
            return {'result': 'success', 'message': 'Added notification agent.', 'notifier_id': result}
        else:
            return {'result': 'error', 'message': 'Failed to add notification agent.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def set_notifier_config(self, notifier_id=None, agent_id=None, **kwargs):
        """ Configure an exisitng notificaiton agent.

            ```
            Required parameters:
                notifier_id (int):        The notifier config to update
                agent_id (int):           The agent of the notifier

            Optional parameters:
                Pass all the config options for the agent with the agent prefix:
                    e.g. For Telegram: telegram_bot_token
                                       telegram_chat_id
                                       disable_web_preview
                                       html_support
                                       incl_poster
                                       incl_subject
                Notify actions with 'trigger_' prefix (trigger_on_play, trigger_on_stop, etc.),
                and notify text with 'text_' prefix (text_on_play_subject, text_on_play_body, etc.) are optional.

            Returns:
                None
            ```
        """
        result = notifiers.set_notifier_config(notifier_id=notifier_id, agent_id=agent_id, **kwargs)

        if result:
            return {'result': 'success', 'message': 'Added notification agent.'}
        else:
            return {'result': 'error', 'message': 'Failed to add notification agent.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_notify_text_preview(self, notify_action='', subject='', body='', agent_id=0, agent_name='', **kwargs):
        if str(agent_id).isdigit():
            agent_id = int(agent_id)

        text = []
        media_types = next((a['media_types'] for a in notifiers.available_notification_actions()
                            if a['name'] == notify_action), ())

        for media_type in media_types:
            test_subject, test_body = notification_handler.build_notify_text(subject=subject,
                                                                             body=body,
                                                                             notify_action=notify_action,
                                                                             parameters={'media_type': media_type},
                                                                             agent_id=agent_id,
                                                                             test=True)

            text.append({'media_type': media_type, 'subject': test_subject, 'body': test_body})

        return serve_template(templatename="notifier_text_preview.html", text=text, agent=agent_name)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_notifier_parameters(self, **kwargs):
        """ Get the list of available notification parameters.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {
                     }
            ```
        """
        parameters = [{'name': param['name'],
                       'type': param['type'],
                       'value': param['value']
                       }
                      for category in common.NOTIFICATION_PARAMETERS 
                      for param in category['parameters']]

        return parameters

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi("notify")
    def send_notification(self, notifier_id=None, subject='PlexPy', body='Test notification', notify_action='', **kwargs):
        """ Send a notification using PlexPy.

            ```
            Required parameters:
                notifier_id (int):      The ID number of the notification agent
                subject (str):          The subject of the message
                body (str):             The body of the message

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        test = 'test ' if notify_action == 'test' else ''

        if notifier_id:
            notifier = notifiers.get_notifier_config(notifier_id=notifier_id)
            
            if notifier:
                logger.debug(u"Sending %s%s notification." % (test, notifier['agent_name']))
                if notification_handler.notify(notifier_id=notifier_id,
                                               notify_action=notify_action,
                                               subject=subject,
                                               body=body,
                                               **kwargs):
                    return "Notification sent."
                else:
                    return "Notification failed."
            else:
                logger.debug(u"Unable to send %snotification, invalid notifier_id %s." % (test, notifier_id))
                return "Invalid notifier id %s." % notifier_id
        else:
            logger.debug(u"Unable to send %snotification, no notifier_id received." % test)
            return "No notifier id received."

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_browser_notifications(self, **kwargs):
        browser = notifiers.BROWSER()
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
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def facebookStep1(self, app_id='', app_secret='', redirect_uri='', **kwargs):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        facebook_notifier = notifiers.FACEBOOK()
        url = facebook_notifier._get_authorization(app_id=app_id,
                                                   app_secret=app_secret,
                                                   redirect_uri=redirect_uri)

        if url:
            return {'result': 'success', 'msg': 'Confirm Authorization. Check pop-up blocker if no response.', 'url': url}
        else:
            return {'result': 'error', 'msg': 'Failed to retrieve authorization url.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def facebookStep2(self, code='', **kwargs):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        facebook = notifiers.FACEBOOK()
        access_token = facebook._get_credentials(code)

        if access_token:
            return "Facebook authorization successful. PlexPy can send notification to Facebook. " \
                "Your Facebook access token is:" \
                "<pre>{0}</pre>You may close this page.".format(access_token)
        else:
            return "Failed to request authorization from Facebook. Check the PlexPy logs for details.<br />You may close this page."

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def facebook_retrieve_token(self, **kwargs):
        if plexpy.CONFIG.FACEBOOK_TOKEN == 'temp':
            return {'result': 'waiting'}
        elif plexpy.CONFIG.FACEBOOK_TOKEN:
            token = plexpy.CONFIG.FACEBOOK_TOKEN
            plexpy.CONFIG.FACEBOOK_TOKEN = ''
            return {'result': 'success', 'msg': 'Authorization successful.', 'access_token': token}
        else:
            return {'result': 'error', 'msg': 'Failed to request authorization.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def osxnotifyregister(self, app, **kwargs):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        from osxnotify import registerapp as osxnotify

        result, msg = osxnotify.registerapp(app)
        if result:
            osx_notify = notifiers.OSX()
            osx_notify.notify(subject='Registered', body='Success :-)', subtitle=result)
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
    def get_mobile_devices_table(self, **kwargs):
        result = mobile_app.get_mobile_devices()
        return serve_template(templatename="mobile_devices_table.html", devices_list=result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def verify_mobile_device(self, device_token='', cancel=False, **kwargs):
        if cancel == 'true':
            mobile_app.TEMP_DEVICE_TOKEN = None
            return {'result': 'error', 'message': 'Device registration cancelled.'}

        result = mobile_app.get_mobile_device_by_token(device_token)
        if result:
            mobile_app.TEMP_DEVICE_TOKEN = None
            return {'result': 'success', 'message': 'Device registered successfully.', 'data': result}
        else:
            return {'result': 'error', 'message': 'Device not registered.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_mobile_device(self, device_id=None, **kwargs):
        """ Remove a mobile device from the database.

            ```
            Required parameters:
                device_id (int):        The device to delete

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        result = mobile_app.delete_mobile_device(device_id=device_id)
        if result:
            return {'result': 'success', 'message': 'Device deleted successfully.'}
        else:
            return {'result': 'error', 'message': 'Failed to delete device.'}

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

        plex_tv = plextv.PlexTV(username=username, password=password)
        result = plex_tv.get_token()

        if result:
            return result['auth_token']
        else:
            logger.warn(u"Unable to retrieve Plex.tv token.")
            return None

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_plexpy_pms_token(self, username=None, password=None, force=False, **kwargs):
        """ Fetch a new Plex.tv token for PlexPy """
        if not username and not password:
            return None

        force = True if force == 'true' else False

        plex_tv = plextv.PlexTV(username=username, password=password)
        token = plex_tv.get_plexpy_pms_token(force=force)

        if token:
            return {'result': 'success', 'message': 'Authentication successful.', 'token': token}
        else:
            return {'result': 'error', 'message': 'Authentication failed.'}

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
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def generate_api_key(self, device=None, **kwargs):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info(u"New API key generated.")
        logger._BLACKLIST_WORDS.append(apikey)

        if device == 'true':
            mobile_app.TEMP_DEVICE_TOKEN = apikey

        return apikey

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def checkGithub(self, **kwargs):
        versioncheck.checkGithub()
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def do_state_change(self, signal, title, timer, **kwargs):
        message = title
        quote = self.random_arnold_quotes()
        plexpy.SIGNAL = signal

        if plexpy.CONFIG.HTTP_ROOT.strip('/'):
            new_http_root = '/' + plexpy.CONFIG.HTTP_ROOT.strip('/') + '/'
        else:
            new_http_root = '/'

        return serve_template(templatename="shutdown.html", signal=signal, title=title,
                              new_http_root=new_http_root, message=message, timer=timer, quote=quote)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def shutdown(self, **kwargs):
        return self.do_state_change('shutdown', 'Shutting Down', 15)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def restart(self, **kwargs):
        return self.do_state_change('restart', 'Restarting', 30)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def update(self, **kwargs):
        # Show changelog after updating
        plexpy.CONFIG.__setattr__('UPDATE_SHOW_CHANGELOG', 1)
        plexpy.CONFIG.write()
        return self.do_state_change('update', 'Updating', 120)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def checkout_git_branch(self, git_remote=None, git_branch=None, **kwargs):
        if git_branch == plexpy.CONFIG.GIT_BRANCH:
            logger.error(u"Already on the %s branch" % git_branch)
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")
        
        # Set the new git remote and branch
        plexpy.CONFIG.__setattr__('GIT_REMOTE', git_remote)
        plexpy.CONFIG.__setattr__('GIT_BRANCH', git_branch)
        plexpy.CONFIG.write()
        return self.do_state_change('checkout', 'Switching Git Branches', 120)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_changelog(self, latest_only=False, update_shown=False, **kwargs):
        latest_only = True if latest_only == 'true' else False
        # Set update changelog shown status
        if update_shown == 'true':
            plexpy.CONFIG.__setattr__('UPDATE_SHOW_CHANGELOG', 0)
            plexpy.CONFIG.write()
        return versioncheck.read_changelog(latest_only=latest_only)

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
            metadata = data_factory.get_metadata_details(rating_key=rating_key)
            if metadata:
                poster_info = data_factory.get_poster_info(metadata=metadata)
                metadata.update(poster_info)
        else:
            pms_connect = pmsconnect.PmsConnect()
            metadata = pms_connect.get_metadata_details(rating_key=rating_key)
            if metadata:
                data_factory = datafactory.DataFactory()
                poster_info = data_factory.get_poster_info(metadata=metadata)
                metadata.update(poster_info)

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
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi('notify_recently_added')
    def send_manual_on_created(self, notifier_id='', rating_key='', **kwargs):
        """ Send a recently added notification using PlexPy.

            ```
            Required parameters:
                rating_key (int):       The rating key for the media

            Optional parameters:
                notifier_id (int):      The ID number of the notification agent.
                                        The notification will send to all enabled notification agents if notifier id is not provided.

            Returns:
                json
                    {"result": "success",
                     "message": "Notification queued."
                    }
            ```
        """
        if rating_key:
            pms_connect = pmsconnect.PmsConnect()
            metadata = pms_connect.get_metadata_details(rating_key=rating_key)
            data = {'timeline_data': metadata, 'notify_action': 'on_created', 'manual_trigger': True}

            if metadata['media_type'] not in ('movie', 'episode', 'track'):
                children = pms_connect.get_item_children(rating_key=rating_key)
                child_keys = [child['rating_key'] for child in children['children_list'] if child['rating_key']]
                data['child_keys'] = child_keys

            if notifier_id:
                data['notifier_id'] = notifier_id

            plexpy.NOTIFY_QUEUE.put(data)
            return {'result': 'success', 'message': 'Notification queued.'}

        else:
            return {'result': 'error', 'message': 'Notification failed.'}

    @cherrypy.expose
    @requireAuth()
    def pms_image_proxy(self, **kwargs):
        """ See real_pms_image_proxy docs string"""

        refresh = False
        if kwargs.get('refresh'):
            refresh = False if get_session_user_id() else True

        kwargs['refresh'] = refresh

        return self.real_pms_image_proxy(**kwargs)

    @addtoapi('pms_image_proxy')
    def real_pms_image_proxy(self, img='', rating_key=None, width='0', height='0',
                             fallback=None, refresh=False, clip=False, **kwargs):
        """ Gets an image from the PMS and saves it to the image cache directory.

            ```
            Required parameters:
                img (str):              /library/metadata/153037/thumb/1462175060
                or
                rating_key (str):       54321

            Optional parameters:
                width (str):            150
                height (str):           255
                fallback (str):         "poster", "cover", "art"
                refresh (bool):         True or False whether to refresh the image cache

            Returns:
                None
            ```
        """
        if not img and not rating_key:
            logger.warn('No image input received.')
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

        clip = True if clip == 'true' else False

        try:
            if not plexpy.CONFIG.CACHE_IMAGES or refresh or 'indexes' in img:
                raise NotFound

            return serve_file(path=ffp, content_type='image/jpeg')

        except NotFound:
            # the image does not exist, download it from pms
            try:
                pms_connect = pmsconnect.PmsConnect()
                result = pms_connect.get_image(img, width, height, clip=clip)

                if result and result[0]:
                    cherrypy.response.headers['Content-type'] = result[1]
                    if plexpy.CONFIG.CACHE_IMAGES and 'indexes' not in img:
                        with open(ffp, 'wb') as f:
                            f.write(result[0])

                    return result[0]
                else:
                    raise Exception(u'PMS image request failed')

            except Exception as e:
                logger.warn(u'Failed to get image %s, falling back to %s.' % (img, fallback))
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
    def download_config(self, **kwargs):
        """ Download the PlexPy configuration file. """
        config_file = config.FILENAME

        try:
            plexpy.CONFIG.write()
        except:
            pass

        return serve_download(plexpy.CONFIG_FILE, name=config_file)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_database(self, **kwargs):
        """ Download the PlexPy database file. """
        database_file = database.FILENAME

        try:
            db = database.MonitorDatabase()
            db.connection.execute('begin immediate')
            shutil.copyfile(plexpy.DB_FILE, os.path.join(plexpy.CONFIG.CACHE_DIR, database_file))
            db.connection.rollback()
        except:
            pass

        return serve_download(os.path.join(plexpy.CONFIG.CACHE_DIR, database_file), name=database_file)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_log(self, logfile='', **kwargs):
        """ Download the PlexPy log file. """
        if logfile == "plexpy_api":
            filename = logger.FILENAME_API
            log = logger.logger
        elif logfile == "plexpy_websocket":
            filename = logger.FILENAME_WEBSOCKET
            log = logger.logger_api
        else:
            filename = logger.FILENAME
            log = logger.logger_websocket

        try:
            log.flush()
        except:
            pass

        return serve_download(os.path.join(plexpy.CONFIG.LOG_DIR, filename), name=filename)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_plex_log(self, **kwargs):
        """ Download the Plex log file. """
        log_type = kwargs.get('log_type', 'server')

        log_file = ""
        if plexpy.CONFIG.PMS_LOGS_FOLDER:
            if log_type == "server":
                log_file = 'Plex Media Server.log'
                log_file_path = os.path.join(plexpy.CONFIG.PMS_LOGS_FOLDER, log_file)
            elif log_type == "scanner":
                log_file = 'Plex Media Scanner.log'
                log_file_path = os.path.join(plexpy.CONFIG.PMS_LOGS_FOLDER, log_file)
        else:
            return "Plex log folder not set in the settings."


        if log_file and os.path.isfile(log_file_path):
            return serve_download(log_file_path, name=log_file)
        else:
            return "Plex %s log file not found." % log_type

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_image_cache(self, **kwargs):
        """ Delete and recreate the image cache directory. """
        return self.delete_cache(folder='images')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_cache(self, folder='', **kwargs):
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
    def delete_poster_url(self, rating_key='', **kwargs):

        data_factory = datafactory.DataFactory()
        result = data_factory.delete_poster_url(rating_key=rating_key)

        if result:
            return {'result': 'success', 'message': 'Deleted Imgur poster url.'}
        else:
            return {'result': 'error', 'message': 'Failed to delete Imgur poster url.'}


    ##### Search #####

    @cherrypy.expose
    @requireAuth()
    def search(self, query='', **kwargs):
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
    def get_metadata_details(self, rating_key='', **kwargs):
        """ Get the metadata for a media item.

            ```
            Required parameters:
                rating_key (str):       Rating key of the item

            Optional parameters:
                None

            Returns:
                json:
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
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        metadata = pms_connect.get_metadata_details(rating_key=rating_key)

        if metadata:
            return metadata
        else:
            logger.warn(u"Unable to retrieve data for get_metadata_details.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_recently_added")
    def get_recently_added_details(self, start='0', count='0', type='', section_id='', **kwargs):
        """ Get all items that where recelty added to plex.

            ```
            Required parameters:
                count (str):        Number of items to return

            Optional parameters:
                start (str):        The item number to start at
                type (str):         The media type: movie, show, artist
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
        result = pms_connect.get_recently_added_details(start=start, count=count, type=type, section_id=section_id)

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
        try:
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
        except Exception as e:
            logger.exception(u"Unable to retrieve data for get_activity: %s" % e)

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
        data_factory = datafactory.DataFactory()
        result = data_factory.get_home_stats(grouping=grouping,
                                             time_range=time_range,
                                             stats_type=stats_type,
                                             stats_count=stats_count)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_home_stats.")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi("arnold")
    def random_arnold_quotes(self, **kwargs):
        """ Get to the chopper! """
        import random
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
                      'Make it quick because my horse is getting tired.',
                      'What killed the dinosaurs? The Ice Age!',
                      'That\'s for sleeping with my wife!',
                      'Remember when I said I\'d kill you last... I lied!',
                      'You want to be a farmer? Here\'s a couple of acres',
                      'Now, this is the plan. Get your ass to Mars.',
                      'I just had a terrible thought... What if this is a dream?',
                      'Well, listen to this one: Rubber baby buggy bumpers!',
                      'Take your toy back to the carpet!',
                      'My name is John Kimble... And I love my car.',
                      'I eat Green Berets for breakfast.',
                      'Put that cookie down! NOW!'
                      ]

        return random.choice(quote_list)

    ### API ###

    @cherrypy.expose
    def api(self, *args, **kwargs):
        if args and 'v2' in args[0]:
            return API2()._api_run(**kwargs)
        else:
            return json.dumps(API2()._api_responds(result_type='error',
                                                   msg='Please use the /api/v2 endpoint.'))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_pms_update(self, **kwargs):
        """ Check for updates to the Plex Media Server.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {"update_available": true,
                     "platform": "Windows",
                     "release_date": "1473721409",
                     "version": "1.1.4.2757-24ffd60",
                     "requirements": "...",
                     "extra_info": "...",
                     "changelog_added": "...",
                     "changelog_fixed": "...",
                     "label": "Download",
                     "distro": "english",
                     "distro_build": "windows-i386",
                     "download_url": "https://downloads.plex.tv/...",
                     }
            ```
        """
        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plex_downloads()
        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_geoip_lookup(self, ip_address='', **kwargs):
        """ Get the geolocation info for an IP address. The GeoLite2 database must be installed.

            ```
            Required parameters:
                ip_address

            Optional parameters:
                None

            Returns:
                json:
                    {"continent": "North America",
                     "country": "United States",
                     "region": "California",
                     "city": "Mountain View",
                     "postal_code": "94035",
                     "timezone": "America/Los_Angeles",
                     "latitude": 37.386,
                     "longitude": -122.0838,
                     "accuracy": 1000
                     }
                json:
                    {"error": "The address 127.0.0.1 is not in the database."
                     }
            ```
        """
        geo_info = helpers.geoip_lookup(ip_address)
        if isinstance(geo_info, basestring):
            return {'error': geo_info}
        return geo_info

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_whois_lookup(self, ip_address='', **kwargs):
        """ Get the connection info for an IP address.

            ```
            Required parameters:
                ip_address

            Optional parameters:
                None

            Returns:
                json:
                    {"host": "google-public-dns-a.google.com",
                     "nets": [{"description": "Google Inc.",
                               "address": "1600 Amphitheatre Parkway",
                               "city": "Mountain View",
                               "state": "CA",
                               "postal_code": "94043",
                               "country": "United States",
                               ...
                               },
                               {...}
                              ]
                json:
                    {"host": "Not available",
                     "nets": [],
                     "error": "IPv4 address 127.0.0.1 is already defined as Loopback via RFC 1122, Section 3.2.1.3."
                     }
            ```
        """
        whois_info = helpers.whois_lookup(ip_address)
        return whois_info

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    def get_plexpy_url(self, **kwargs):
        if plexpy.CONFIG.ENABLE_HTTPS:
           scheme = 'https' 
        else:
           scheme = 'http'

        # Have to return some hostname if socket fails even if 127.0.0.1 won't work
        hostname = '127.0.0.1'

        if plexpy.CONFIG.HTTP_HOST == '0.0.0.0':
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.connect(('<broadcast>', 0))
                hostname = s.getsockname()[0]
            except socket.error:
                hostname = socket.gethostbyname(socket.gethostname())
        else:
            hostname = plexpy.CONFIG.HTTP_HOST

        if plexpy.CONFIG.HTTP_PORT not in (80, 443):
            port = ':' + str(plexpy.CONFIG.HTTP_PORT)
        else:
            port = ''

        if plexpy.CONFIG.HTTP_ROOT.strip('/'):
            root = '/' + plexpy.CONFIG.HTTP_ROOT.strip('/')
        else:
            root = ''

        return scheme + '://' + hostname + port + root