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

import base64
import csv
from io import open, BytesIO
import json
import linecache
import os
import shutil
import ssl as _ssl
import sys
import threading
import zipfile
from urllib.parse import urlencode

import cherrypy
from cherrypy.lib.static import serve_file, serve_fileobj, serve_download
from cherrypy._cperror import NotFound

from hashing_passwords import make_hash
from mako.lookup import TemplateLookup
import mako.template
import mako.exceptions

import certifi
import websocket

if sys.version_info >= (3, 6):
    import secrets

import plexpy
from plexpy import activity_pinger
from plexpy import activity_processor
from plexpy import common
from plexpy import config
from plexpy import database
from plexpy import datafactory
from plexpy import exporter
from plexpy import graphs
from plexpy import helpers
from plexpy import http_handler
from plexpy import libraries
from plexpy import log_reader
from plexpy import logger
from plexpy import newsletter_handler
from plexpy import newsletters
from plexpy import mobile_app
from plexpy import notification_handler
from plexpy import notifiers
from plexpy import plextv
from plexpy import plexivity_import
from plexpy import plexwatch_import
from plexpy import pmsconnect
from plexpy import users
from plexpy import versioncheck
from plexpy import web_socket
from plexpy import webstart
from plexpy.api2 import API2
from plexpy.helpers import checked, addtoapi, get_ip, create_https_certificates, build_datatables_json, sanitize_out
from plexpy.session import get_session_info, get_session_user_id, allow_session_user, allow_session_library
from plexpy.webauth import AuthController, requireAuth, member_of, check_auth, get_jwt_token
if common.PLATFORM == 'Windows':
    from plexpy import windows
elif common.PLATFORM == 'Darwin':
    from plexpy import macos


TEMPLATE_LOOKUP = None


def serve_template(template_name, **kwargs):
    global TEMPLATE_LOOKUP
    if TEMPLATE_LOOKUP is None:
        interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
        template_dir = os.path.join(str(interface_dir), plexpy.CONFIG.INTERFACE)
        TEMPLATE_LOOKUP = TemplateLookup(directories=[template_dir], default_filters=['unicode', 'h'],
                            error_handler=mako_error_handler)

    http_root = plexpy.HTTP_ROOT
    server_name = helpers.pms_name()
    cache_param = '?' + (plexpy.CURRENT_VERSION or common.RELEASE)

    _session = get_session_info()

    try:
        template = TEMPLATE_LOOKUP.get_template(template_name)
        return template.render(http_root=http_root, server_name=server_name, cache_param=cache_param,
                               _session=_session, **kwargs)
    except Exception as e:
        logger.exception("WebUI :: Mako template render error: %s" % e)
        return mako.exceptions.html_error_template().render()


def mako_error_handler(context, error):
    """Decorate tracebacks when Mako errors happen.
    Evil hack: walk the traceback frames, find compiled Mako templates,
    stuff their (transformed) source into linecache.cache.
    """
    rich_tb = mako.exceptions.RichTraceback(error)
    rich_iter = iter(rich_tb.traceback)
    tb = sys.exc_info()[-1]
    source = {}
    annotated = set()
    while tb is not None:
        cur_rich = next(rich_iter)
        f = tb.tb_frame
        co = f.f_code
        filename = co.co_filename
        lineno = tb.tb_lineno
        if filename.startswith('memory:'):
            lines = source.get(filename)
            if lines is None:
                info = mako.template._get_module_info(filename)
                lines = source[filename] = info.module_source.splitlines(True)
                linecache.cache[filename] = (None, None, lines, filename)
            if (filename, lineno) not in annotated:
                annotated.add((filename, lineno))
                extra = '    # {} line {} in {}:\n    # {}'.format(*cur_rich)
                lines[lineno - 1] += extra
        tb = tb.tb_next
    # Don't return False -- that will lose the actual Mako frame.  Instead
    # re-raise.
    raise


class BaseRedirect(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

    @cherrypy.expose
    def status(self, *args, **kwargs):
        path = '/' + '/'.join(args) if args else ''
        query = '?' + urlencode(kwargs) if kwargs else ''
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + 'status' + path + query)


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
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_ip": plexpy.CONFIG.PMS_IP,
            "pms_port": plexpy.CONFIG.PMS_PORT,
            "pms_ssl": plexpy.CONFIG.PMS_SSL,
            "pms_is_cloud": plexpy.CONFIG.PMS_IS_CLOUD,
            "pms_name": helpers.pms_name(),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL
        }

        # The setup wizard just refreshes the page on submit so we must redirect to home if config set.
        if plexpy.CONFIG.FIRST_RUN_COMPLETE:
            plexpy.initialize_scheduler()
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")
        else:
            return serve_template(template_name="welcome.html", title="Welcome", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def save_pms_token(self, token=None, client_id=None, **kwargs):
        if token is not None:
            plexpy.CONFIG.PMS_TOKEN = token
        if client_id is not None:
            plexpy.CONFIG.PMS_CLIENT_ID = client_id
        plexpy.CONFIG.write()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_server_list")
    def discover(self, include_cloud=True, all_servers=True, **kwargs):
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
        include_cloud = not (include_cloud == 'false')
        all_servers = not (all_servers == 'false')

        plex_tv = plextv.PlexTV()
        servers_list = plex_tv.discover(include_cloud=include_cloud,
                                        all_servers=all_servers)

        if servers_list:
            return servers_list


    ##### Home #####

    @cherrypy.expose
    @requireAuth()
    def home(self, **kwargs):
        config = {
            "home_sections": plexpy.CONFIG.HOME_SECTIONS,
            "home_refresh_interval": plexpy.CONFIG.HOME_REFRESH_INTERVAL,
            "pms_name": helpers.pms_name(),
            "pms_is_cloud": plexpy.CONFIG.PMS_IS_CLOUD,
            "update_show_changelog": plexpy.CONFIG.UPDATE_SHOW_CHANGELOG,
            "first_run_complete": plexpy.CONFIG.FIRST_RUN_COMPLETE
        }
        return serve_template(template_name="index.html", title="Home", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_date_formats(self, **kwargs):
        """ Get the date and time formats used by Tautulli.

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

        pms_connect = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
        result = pms_connect.get_current_activity()

        if result:
            return serve_template(template_name="current_activity.html", data=result)
        else:
            logger.warn("Unable to retrieve data for get_current_activity.")
            return serve_template(template_name="current_activity.html", data=None)

    @cherrypy.expose
    @requireAuth()
    def get_current_activity_instance(self, session_key=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
        result = pms_connect.get_current_activity()

        if result:
            session = next((s for s in result['sessions'] if s['session_key'] == session_key), None)
            return serve_template(template_name="current_activity_instance.html", session=session)
        else:
            return serve_template(template_name="current_activity_instance.html", session=None)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def terminate_session(self, session_key='', session_id='', message='', **kwargs):
        """ Stop a streaming session.

            ```
            Required parameters:
                session_key (int):          The session key of the session to terminate, OR
                session_id (str):           The session id of the session to terminate

            Optional parameters:
                message (str):              A custom message to send to the client

            Returns:
                None
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.terminate_session(session_key=session_key, session_id=session_id, message=message)

        if isinstance(result, str):
            return {'result': 'error', 'message': 'Failed to terminate session: {}.'.format(result)}
        elif result is True:
            return {'result': 'success', 'message': 'Session terminated.'}
        else:
            return {'result': 'error', 'message': 'Failed to terminate session.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def open_plex_xml(self, endpoint='', plextv=False, **kwargs):
        if helpers.bool_true(plextv):
            base_url = 'https://plex.tv'
        else:
            base_url = plexpy.CONFIG.PMS_URL_OVERRIDE or plexpy.CONFIG.PMS_URL

        if '{machine_id}' in endpoint:
            endpoint = endpoint.format(machine_id=plexpy.CONFIG.PMS_IDENTIFIER)

        url = base_url + endpoint + ('?' + urlencode(kwargs) if kwargs else '')
        return serve_template(template_name="xml_shortcut.html", title="Plex XML", url=url)

    @cherrypy.expose
    @requireAuth()
    def home_stats(self, time_range=30, stats_type='plays', stats_count=10, **kwargs):
        data_factory = datafactory.DataFactory()
        stats_data = data_factory.get_home_stats(time_range=time_range,
                                                 stats_type=stats_type,
                                                 stats_count=stats_count)

        return serve_template(template_name="home_stats.html", title="Stats", data=stats_data)

    @cherrypy.expose
    @requireAuth()
    def library_stats(self, **kwargs):
        data_factory = datafactory.DataFactory()

        library_cards = plexpy.CONFIG.HOME_LIBRARY_CARDS

        stats_data = data_factory.get_library_stats(library_cards=library_cards)

        return serve_template(template_name="library_stats.html", title="Library Stats", data=stats_data)

    @cherrypy.expose
    @requireAuth()
    def get_recently_added(self, count='0', media_type='', **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(count=count, media_type=media_type)
        except IOError as e:
            return serve_template(template_name="recently_added.html", data=None)

        if result and 'recently_added' in result:
            return serve_template(template_name="recently_added.html", data=result['recently_added'])
        else:
            logger.warn("Unable to retrieve data for get_recently_added.")
            return serve_template(template_name="recently_added.html", data=None)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def regroup_history(self, **kwargs):
        """ Regroup play history in the database."""

        threading.Thread(target=activity_processor.regroup_history).start()

        return {'result': 'success',
                'message': 'Regrouping play history started. Check the logs to monitor any problems.'}

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

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_recently_added(self, **kwargs):
        """ Flush out all of the recently added items in the database."""

        result = database.delete_recently_added()

        if result:
            return {'result': 'success', 'message': 'Recently added flushed.'}
        else:
            return {'result': 'error', 'message': 'Flush recently added failed.'}

    ##### Libraries #####

    @cherrypy.expose
    @requireAuth()
    def libraries(self, **kwargs):
        return serve_template(template_name="libraries.html", title="Libraries")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @sanitize_out()
    @addtoapi("get_libraries_table")
    def get_library_list(self, grouping=None, **kwargs):
        """ Get the data on the Tautulli libraries table.

            ```
            Required parameters:
                None

            Optional parameters:
                grouping (int):                 0 or 1
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
                          "do_notify": 1,
                          "do_notify_created": 1,
                          "duration": 1578037,
                          "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                          "histroy_row_id": 1128,
                          "is_active": 1,
                          "keep_history": 1,
                          "labels": [],
                          "last_accessed": 1462693216,
                          "last_played": "Game of Thrones - The Red Woman",
                          "library_art": "/:/resources/show-fanart.jpg",
                          "library_thumb": "/:/resources/show.png",
                          "live": 0,
                          "media_index": 1,
                          "media_type": "episode",
                          "originally_available_at": "2016-04-24",
                          "parent_count": 240,
                          "parent_media_index": 6,
                          "parent_title": "",
                          "plays": 772,
                          "rating_key": 153037,
                          "row_id": 1,
                          "section_id": 2,
                          "section_name": "TV Shows",
                          "section_type": "Show",
                          "server_id": "ds48g4r354a8v9byrrtr697g3g79w",
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

        grouping = helpers.bool_true(grouping, return_none=True)

        library_data = libraries.Libraries()
        library_list = library_data.get_datatables_list(kwargs=kwargs, grouping=grouping)

        return library_list

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @sanitize_out()
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
                    [{"section_id": 1, "section_name": "Movies", "section_type": "movie"},
                     {"section_id": 7, "section_name": "Music", "section_type": "artist"},
                     {"section_id": 2, "section_name": "TV Shows", "section_type": "show"},
                     {...}
                     ]
            ```
        """
        library_data = libraries.Libraries()
        result = library_data.get_sections()

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_library_sections.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def refresh_libraries_list(self, **kwargs):
        """ Manually refresh the libraries list. """
        logger.info("Manual libraries list refresh requested.")
        result = libraries.refresh_libraries()

        if result:
            return {'result': 'success', 'message': 'Libraries list refreshed.'}
        else:
            return {'result': 'error', 'message': 'Unable to refresh libraries list.'}

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
                logger.warn("Unable to retrieve library details for section_id %s " % section_id)
                return serve_template(template_name="library.html", title="Library", data=None, config=config)
        else:
            logger.debug("Library page requested but no section_id received.")
            return serve_template(template_name="library.html", title="Library", data=None, config=config)

        return serve_template(template_name="library.html", title="Library", data=library_details, config=config)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def edit_library_dialog(self, section_id=None, **kwargs):
        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_details(section_id=section_id)
            status_message = ''
        else:
            result = None
            status_message = 'An error occurred.'

        return serve_template(template_name="edit_library.html", title="Edit Library",
                              data=result, server_id=plexpy.CONFIG.PMS_IDENTIFIER, status_message=status_message)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def edit_library(self, section_id=None, **kwargs):
        """ Update a library section on Tautulli.

            ```
            Required parameters:
                section_id (str):           The id of the Plex library section
                custom_thumb (str):         The URL for the custom library thumbnail
                custom_art (str):           The URL for the custom library background art
                keep_history (int):         0 or 1

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        custom_thumb = kwargs.get('custom_thumb', '')
        custom_art = kwargs.get('custom_art', '')
        do_notify = kwargs.get('do_notify', 0)
        do_notify_created = kwargs.get('do_notify_created', 0)
        keep_history = kwargs.get('keep_history', 0)

        if section_id:
            try:
                library_data = libraries.Libraries()
                library_data.set_config(section_id=section_id,
                                        custom_thumb=custom_thumb,
                                        custom_art=custom_art,
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
            return serve_template(template_name="user_watch_time_stats.html", data=None, title="Watch Stats")

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_watch_time_stats(section_id=section_id)
        else:
            result = None

        if result:
            return serve_template(template_name="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            logger.warn("Unable to retrieve data for library_watch_time_stats.")
            return serve_template(template_name="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def library_user_stats(self, section_id=None, **kwargs):
        if not allow_session_library(section_id):
            return serve_template(template_name="library_user_stats.html", data=None, title="Player Stats")

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_user_stats(section_id=section_id)
        else:
            result = None

        if result:
            return serve_template(template_name="library_user_stats.html", data=result, title="Player Stats")
        else:
            logger.warn("Unable to retrieve data for library_user_stats.")
            return serve_template(template_name="library_user_stats.html", data=None, title="Player Stats")

    @cherrypy.expose
    @requireAuth()
    def library_recently_watched(self, section_id=None, limit='10', **kwargs):
        if not allow_session_library(section_id):
            return serve_template(template_name="user_recently_watched.html", data=None, title="Recently Watched")

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_recently_watched(section_id=section_id, limit=limit)
        else:
            result = None

        if result:
            return serve_template(template_name="user_recently_watched.html", data=result, title="Recently Watched")
        else:
            logger.warn("Unable to retrieve data for library_recently_watched.")
            return serve_template(template_name="user_recently_watched.html", data=None, title="Recently Watched")

    @cherrypy.expose
    @requireAuth()
    def library_recently_added(self, section_id=None, limit='10', **kwargs):
        if not allow_session_library(section_id):
            return serve_template(template_name="library_recently_added.html", data=None, title="Recently Added")

        if section_id:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(section_id=section_id, count=limit)
        else:
            result = None

        if result and result['recently_added']:
            return serve_template(template_name="library_recently_added.html", data=result['recently_added'], title="Recently Added")
        else:
            logger.warn("Unable to retrieve data for library_recently_added.")
            return serve_template(template_name="library_recently_added.html", data=None, title="Recently Added")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_library_media_info(self, section_id=None, section_type=None, rating_key=None, refresh='', **kwargs):
        """ Get the data on the Tautulli media info tables.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section, OR
                rating_key (str):               The grandparent or parent rating key

            Optional parameters:
                section_type (str):             "movie", "show", "artist", "photo"
                order_column (str):             "added_at", "sort_title", "container", "bitrate", "video_codec",
                                                "video_resolution", "video_framerate", "audio_codec", "audio_channels",
                                                "file_size", "last_played", "play_count"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Thrones"
                refresh (str):                  "true" to refresh the media info table

            Returns:
                json:
                    {"draw": 1,
                     "last_refreshed": 1678734670,
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
                          "sort_title": "Game of Thrones",
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
            # Alias 'title' to 'sort_title'
            if kwargs.get('order_column') == 'title':
                kwargs['order_column'] = 'sort_title'

            # TODO: Find some one way to automatically get the columns
            dt_columns = [("added_at", True, False),
                          ("sort_title", True, True),
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
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "sort_title")

        if helpers.bool_true(refresh):
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
    @requireAuth()
    @addtoapi("get_collections_table")
    def get_collections_list(self, section_id=None, **kwargs):
        """ Get the data on the Tautulli collections tables.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section

            Optional parameters:
                None

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 5,
                     "data":
                        [...]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("titleSort", True, True),
                          ("collectionMode", True, True),
                          ("collectionSort", True, True),
                          ("childCount", True, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "titleSort")

        result = libraries.get_collections_list(section_id=section_id, **kwargs)

        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi("get_playlists_table")
    def get_playlists_list(self, section_id=None, user_id=None, **kwargs):
        """ Get the data on the Tautulli playlists tables.

            ```
            Required parameters:
                section_id (str):               The section id of the Plex library, OR
                user_id (str):                  The user id of the Plex user

            Optional parameters:
                None

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 5,
                     "data":
                        [...]
                     }
            ```
        """
        # Check if datatables json_data was received.
        # If not, then build the minimal amount of json data for a query
        if not kwargs.get('json_data'):
            # TODO: Find some one way to automatically get the columns
            dt_columns = [("title", True, True),
                          ("leafCount", True, True),
                          ("duration", True, True)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "title")

        result = libraries.get_playlists_list(section_id=section_id,
                                              user_id=user_id,
                                              **kwargs)

        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_media_info_file_sizes(self, section_id=None, rating_key=None, **kwargs):
        get_file_sizes_hold = plexpy.CONFIG.GET_FILE_SIZES_HOLD
        section_ids = set(get_file_sizes_hold['section_ids'])
        rating_keys = set(get_file_sizes_hold['rating_keys'])

        section_id = helpers.cast_to_int(section_id)
        rating_key = helpers.cast_to_int(rating_key)

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
    def get_library(self, section_id=None, include_last_accessed=False, **kwargs):
        """ Get a library's details.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section

            Optional parameters:
                include_last_accessed (bool):   True to include the last_accessed value for the library.

            Returns:
                json:
                    {"child_count": null,
                     "count": 887,
                     "deleted_section": 0,
                     "do_notify": 1,
                     "do_notify_created": 1,
                     "is_active": 1,
                     "keep_history": 1,
                     "last_accessed": 1462693216,
                     "library_art": "/:/resources/movie-fanart.jpg",
                     "library_thumb": "/:/resources/movie.png",
                     "parent_count": null,
                     "row_id": 1,
                     "section_id": 1,
                     "section_name": "Movies",
                     "section_type": "movie",
                     "server_id": "ds48g4r354a8v9byrrtr697g3g79w"
                     }
            ```
        """
        include_last_accessed = helpers.bool_true(include_last_accessed)
        if section_id:
            library_data = libraries.Libraries()
            library_details = library_data.get_details(section_id=section_id,
                                                       include_last_accessed=include_last_accessed)
            if library_details:
                return library_details
            else:
                logger.warn("Unable to retrieve data for get_library.")
                return library_details
        else:
            logger.warn("Library details requested but no section_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_library_watch_time_stats(self, section_id=None, grouping=None, query_days=None, **kwargs):
        """ Get a library's watch time statistics.

            ```
            Required parameters:
                section_id (str):       The id of the Plex library section

            Optional parameters:
                grouping (int):         0 or 1
                query_days (str):       Comma separated days, e.g. "1,7,30,0"

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
        grouping = helpers.bool_true(grouping, return_none=True)

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_watch_time_stats(section_id=section_id, grouping=grouping,
                                                       query_days=query_days)
            if result:
                return result
            else:
                logger.warn("Unable to retrieve data for get_library_watch_time_stats.")
                return result
        else:
            logger.warn("Library watch time stats requested but no section_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_library_user_stats(self, section_id=None, grouping=None, **kwargs):
        """ Get a library's user statistics.

            ```
            Required parameters:
                section_id (str):       The id of the Plex library section

            Optional parameters:
                grouping (int):         0 or 1

            Returns:
                json:
                    [{"friendly_name": "Jon Snow",
                      "total_plays": 170,
                      "total_time": 349618,
                      "user_id": 133788,
                      "user_thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
                      "username": "LordCommanderSnow"
                      },
                     {"friendly_name": "DanyKhaleesi69",
                      "total_plays": 42,
                      "total_time": 50185,
                      "user_id": 8008135,
                      "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar",
                      "username: "DanyKhaleesi69"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        if section_id:
            library_data = libraries.Libraries()
            result = library_data.get_user_stats(section_id=section_id, grouping=grouping)
            if result:
                return result
            else:
                logger.warn("Unable to retrieve data for get_library_user_stats.")
                return result
        else:
            logger.warn("Library user stats requested but no section_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_all_library_history(self, server_id=None, section_id=None, row_ids=None, **kwargs):
        """ Delete all Tautulli history for a specific library.

            ```
            Required parameters:
                server_id (str):        The Plex server identifier of the library section
                section_id (str):       The id of the Plex library section

            Optional parameters:
                row_ids (str):          Comma separated row ids to delete, e.g. "2,3,8"

            Returns:
                None
            ```
        """
        if (server_id and section_id) or row_ids:
            library_data = libraries.Libraries()
            success = library_data.delete(server_id=server_id, section_id=section_id, row_ids=row_ids, purge_only=True)
            if success:
                return {'result': 'success', 'message': 'Deleted library history.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete library(s) history.'}
        else:
            return {'result': 'error', 'message': 'No server id and section id or row ids received.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_library(self, server_id=None, section_id=None, row_ids=None, **kwargs):
        """ Delete a library section from Tautulli. Also erases all history for the library.

            ```
            Required parameters:
                server_id (str):        The Plex server identifier of the library section
                section_id (str):       The id of the Plex library section

            Optional parameters:
                row_ids (str):          Comma separated row ids to delete, e.g. "2,3,8"

            Returns:
                None
            ```
        """
        if (server_id and section_id) or row_ids:
            library_data = libraries.Libraries()
            success = library_data.delete(server_id=server_id, section_id=section_id, row_ids=row_ids)
            if success:
                return {'result': 'success', 'message': 'Deleted library.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete library(s).'}
        else:
            return {'result': 'error', 'message': 'No server id and section id or row ids received.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def undelete_library(self, section_id=None, section_name=None, **kwargs):
        """ Restore a deleted library section to Tautulli.

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
        result = library_data.undelete(section_id=section_id, section_name=section_name)
        if result:
            if section_id:
                msg ='section_id %s' % section_id
            elif section_name:
                msg = 'section_name %s' % section_name
            return {'result': 'success', 'message': 'Re-added library with %s.' % msg}
        return {'result': 'error', 'message': 'Unable to re-add library. Invalid section_id or section_name.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_media_info_cache(self, section_id, **kwargs):
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
                delete_row = library_data.delete_media_info_cache(section_id=section_id)

                if delete_row:
                    return {'message': delete_row}
            else:
                return {'message': 'no data received'}
        else:
            return {'message': 'Cannot delete media info cache while getting file sizes.'}

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
        return serve_template(template_name="users.html", title="Users")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @sanitize_out()
    @addtoapi("get_users_table")
    def get_user_list(self, grouping=None, **kwargs):
        """ Get the data on Tautulli users table.

            ```
            Required parameters:
                None

            Optional parameters:
                grouping (int):                 0 or 1
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
                        [{"allow_guest": 1,
                          "do_notify": 1,
                          "duration": 2998290,
                          "email": "Jon.Snow.1337@CastleBlack.com",
                          "friendly_name": "Jon Snow",
                          "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                          "history_row_id": 1121,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "is_active": 1,
                          "keep_history": 1,
                          "last_played": "Game of Thrones - The Red Woman",
                          "last_seen": 1462591869,
                          "live": 0,
                          "media_index": 1,
                          "media_type": "episode",
                          "originally_available_at": "2016-04-24",
                          "parent_media_index": 6,
                          "parent_title": "",
                          "platform": "Chrome",
                          "player": "Plex Web (Chrome)",
                          "plays": 487,
                          "rating_key": 153037,
                          "row_id": 1,
                          "thumb": "/library/metadata/153036/thumb/1462175062",
                          "title": "Jon Snow",
                          "transcode_decision": "transcode",
                          "user_id": 133788,
                          "user_thumb": "https://plex.tv/users/568gwwoib5t98a3a/avatar",
                          "username": "LordCommanderSnow",
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
                          ("username", True, True),
                          ("title", True, True),
                          ("email", True, True),
                          ("last_seen", True, False),
                          ("ip_address", True, True),
                          ("platform", True, True),
                          ("player", True, True),
                          ("last_played", True, False),
                          ("plays", True, False),
                          ("duration", True, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "friendly_name")

        grouping = helpers.bool_true(grouping, return_none=True)

        user_data = users.Users()
        user_list = user_data.get_datatables_list(kwargs=kwargs, grouping=grouping)

        return user_list

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def refresh_users_list(self, **kwargs):
        """ Manually refresh the users list. """
        logger.info("Manual users list refresh requested.")
        result = users.refresh_users()

        if result:
            return {'result': 'success', 'message': 'Users list refreshed.'}
        else:
            return {'result': 'error', 'message': 'Unable to refresh users list.'}

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
                logger.warn("Unable to retrieve user details for user_id %s " % user_id)
                return serve_template(template_name="user.html", title="User", data=None)
        else:
            logger.debug("User page requested but no user_id received.")
            return serve_template(template_name="user.html", title="User", data=None)

        return serve_template(template_name="user.html", title="User", data=user_details)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def edit_user_dialog(self, user=None, user_id=None, **kwargs):
        if user_id:
            user_data = users.Users()
            result = user_data.get_details(user_id=user_id)
            status_message = ''
        else:
            result = None
            status_message = 'An error occurred.'

        return serve_template(template_name="edit_user.html", title="Edit User", data=result, status_message=status_message)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def edit_user(self, user_id=None, **kwargs):
        """ Update a user on Tautulli.

            ```
            Required parameters:
                user_id (str):              The id of the Plex user
                friendly_name(str):         The friendly name of the user
                custom_thumb (str):         The URL for the custom user thumbnail
                keep_history (int):         0 or 1
                allow_guest (int):          0 or 1

            Optional parameters:
                None

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
            return serve_template(template_name="user_watch_time_stats.html", data=None, title="Watch Stats")

        if user_id or user:
            user_data = users.Users()
            result = user_data.get_watch_time_stats(user_id=user_id)
        else:
            result = None

        if result:
            return serve_template(template_name="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            logger.warn("Unable to retrieve data for user_watch_time_stats.")
            return serve_template(template_name="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def user_player_stats(self, user=None, user_id=None, **kwargs):
        if not allow_session_user(user_id):
            return serve_template(template_name="user_player_stats.html", data=None, title="Player Stats")

        if user_id or user:
            user_data = users.Users()
            result = user_data.get_player_stats(user_id=user_id)
        else:
            result = None

        if result:
            return serve_template(template_name="user_player_stats.html", data=result, title="Player Stats")
        else:
            logger.warn("Unable to retrieve data for user_player_stats.")
            return serve_template(template_name="user_player_stats.html", data=None, title="Player Stats")

    @cherrypy.expose
    @requireAuth()
    def get_user_recently_watched(self, user=None, user_id=None, limit='10', **kwargs):
        if not allow_session_user(user_id):
            return serve_template(template_name="user_recently_watched.html", data=None, title="Recently Watched")

        if user_id or user:
            user_data = users.Users()
            result = user_data.get_recently_watched(user_id=user_id, limit=limit)
        else:
            result = None

        if result:
            return serve_template(template_name="user_recently_watched.html", data=result, title="Recently Watched")
        else:
            logger.warn("Unable to retrieve data for get_user_recently_watched.")
            return serve_template(template_name="user_recently_watched.html", data=None, title="Recently Watched")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @sanitize_out()
    @addtoapi()
    def get_user_ips(self, user_id=None, **kwargs):
        """ Get the data on Tautulli users IP table.

            ```
            Required parameters:
                user_id (str):                  The id of the Plex user

            Optional parameters:
                order_column (str):             "last_seen", "first_seen", "ip_address", "platform",
                                                "player", "last_played", "play_count"
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
                          "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                          "id": 1121,
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "last_played": "Game of Thrones - The Red Woman",
                          "last_seen": 1462591869,
                          "first_seen": 1583968210,
                          "live": 0,
                          "media_index": 1,
                          "media_type": "episode",
                          "originally_available_at": "2016-04-24",
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
                          ("first_seen", True, False),
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
    @sanitize_out()
    @addtoapi()
    def get_user_logins(self, user_id=None, **kwargs):
        """ Get the data on Tautulli user login table.

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
                          "current": false,
                          "expiry": "2021-06-30 18:48:03",
                          "friendly_name": "Jon Snow",
                          "host": "http://plexpy.castleblack.com",
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "os": "Mac OS X",
                          "row_id": 1,
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

        jwt_token = get_jwt_token()

        user_data = users.Users()
        history = user_data.get_datatables_user_login(user_id=user_id,
                                                      jwt_token=jwt_token,
                                                      kwargs=kwargs)

        return history

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def logout_user_session(self, row_ids=None, **kwargs):
        """ Logout Tautulli user sessions.

            ```
            Required parameters:
                row_ids (str):          Comma separated row ids to sign out, e.g. "2,3,8"

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        user_data = users.Users()
        result = user_data.clear_user_login_token(row_ids=row_ids)

        if result:
            return {'result': 'success', 'message': 'Users session logged out.'}
        else:
            return {'result': 'error', 'message': 'Unable to logout user session.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_user(self, user_id=None, include_last_seen=False, **kwargs):
        """ Get a user's details.

            ```
            Required parameters:
                user_id (str):              The id of the Plex user

            Optional parameters:
                include_last_seen (bool):   True to include the last_seen value for the user.

            Returns:
                json:
                    {"allow_guest": 1,
                     "deleted_user": 0,
                     "do_notify": 1,
                     "email": "Jon.Snow.1337@CastleBlack.com",
                     "friendly_name": "Jon Snow",
                     "is_active": 1,
                     "is_admin": 0,
                     "is_allow_sync": 1,
                     "is_home_user": 1,
                     "is_restricted": 0,
                     "keep_history": 1,
                     "last_seen": 1462591869,
                     "row_id": 1,
                     "shared_libraries": ["10", "1", "4", "5", "15", "20", "2"],
                     "user_id": 133788,
                     "user_thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
                     "username": "LordCommanderSnow"
                     }
            ```
        """
        include_last_seen = helpers.bool_true(include_last_seen)
        if user_id:
            user_data = users.Users()
            user_details = user_data.get_details(user_id=user_id,
                                                 include_last_seen=include_last_seen)
            if user_details:
                return user_details
            else:
                logger.warn("Unable to retrieve data for get_user.")
                return user_details
        else:
            logger.warn("User details requested but no user_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_user_watch_time_stats(self, user_id=None, grouping=None, query_days=None, **kwargs):
        """ Get a user's watch time statistics.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                grouping (int):         0 or 1
                query_days (str):       Comma separated days, e.g. "1,7,30,0"

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
        grouping = helpers.bool_true(grouping, return_none=True)

        if user_id:
            user_data = users.Users()
            result = user_data.get_watch_time_stats(user_id=user_id, grouping=grouping, query_days=query_days)
            if result:
                return result
            else:
                logger.warn("Unable to retrieve data for get_user_watch_time_stats.")
                return result
        else:
            logger.warn("User watch time stats requested but no user_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_user_player_stats(self, user_id=None, grouping=None, **kwargs):
        """ Get a user's player statistics.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                grouping (int):         0 or 1

            Returns:
                json:
                    [{"platform": "Chrome",
                      "platform_name": "chrome",
                      "player_name": "Plex Web (Chrome)",
                      "result_id": 1,
                      "total_plays": 170,
                      "total_time": 349618
                      },
                     {"platform": "Chromecast",
                      "platform_name": "chromecast",
                      "player_name": "Chromecast",
                      "result_id": 2,
                      "total_plays": 42,
                      "total_time": 50185
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        if user_id:
            user_data = users.Users()
            result = user_data.get_player_stats(user_id=user_id, grouping=grouping)
            if result:
                return result
            else:
                logger.warn("Unable to retrieve data for get_user_player_stats.")
                return result
        else:
            logger.warn("User watch time stats requested but no user_id received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_all_user_history(self, user_id=None, row_ids=None, **kwargs):
        """ Delete all Tautulli history for a specific user.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                row_ids (str):          Comma separated row ids to delete, e.g. "2,3,8"

            Returns:
                None
            ```
        """
        if user_id or row_ids:
            user_data = users.Users()
            success = user_data.delete(user_id=user_id, row_ids=row_ids, purge_only=True)
            if success:
                return {'result': 'success', 'message': 'Deleted user history.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete user(s) history.'}
        else:
            return {'result': 'error', 'message': 'No user id or row ids received.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_user(self, user_id=None, row_ids=None, **kwargs):
        """ Delete a user from Tautulli. Also erases all history for the user.

            ```
            Required parameters:
                user_id (str):          The id of the Plex user

            Optional parameters:
                row_ids (str):          Comma separated row ids to delete, e.g. "2,3,8"

            Returns:
                None
            ```
        """
        if user_id or row_ids:
            user_data = users.Users()
            success = user_data.delete(user_id=user_id, row_ids=row_ids)
            if success:
                return {'result': 'success', 'message': 'Deleted user.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete user(s).'}
        else:
            return {'result': 'error', 'message': 'No user id or row ids received.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def undelete_user(self, user_id=None, username=None, **kwargs):
        """ Restore a deleted user to Tautulli.

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
        result = user_data.undelete(user_id=user_id, username=username)
        if result:
            if user_id:
                msg ='user_id %s' % user_id
            elif username:
                msg = 'username %s' % username
            return {'result': 'success', 'message': 'Re-added user with %s.' % msg}
        return {'result': 'error', 'message': 'Unable to re-add user. Invalid user_id or username.'}


    ##### History #####

    @cherrypy.expose
    @requireAuth()
    def history(self, **kwargs):
        config = {
            "database_is_importing": database.IS_IMPORTING,
        }

        return serve_template(template_name="history.html", title="History", config=config)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @sanitize_out()
    @addtoapi()
    def get_history(self, user=None, user_id=None, grouping=None, include_activity=None, **kwargs):
        """ Get the Tautulli history.

            ```
            Required parameters:
                None

            Optional parameters:
                grouping (int):                 0 or 1
                include_activity (int):         0 or 1
                user (str):                     "Jon Snow"
                user_id (int):                  133788
                rating_key (int):               4348
                parent_rating_key (int):        544
                grandparent_rating_key (int):   351
                start_date (str):               History for the exact date, "YYYY-MM-DD"
                before (str):                   History before and including the date, "YYYY-MM-DD"
                after (str):                    History after and including the date, "YYYY-MM-DD"
                section_id (int):               2
                media_type (str):               "movie", "episode", "track", "live", "collection", "playlist"
                transcode_decision (str):       "direct play", "copy", "transcode",
                guid (str):                     Plex guid for an item, e.g. "com.plexapp.agents.thetvdb://121361/6/1"
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
                          "friendly_name": "Mother of Dragons",
                          "full_title": "Game of Thrones - The Red Woman",
                          "grandparent_rating_key": 351,
                          "grandparent_title": "Game of Thrones",
                          "original_title": "",
                          "group_count": 1,
                          "group_ids": "1124",
                          "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                          "ip_address": "xxx.xxx.xxx.xxx",
                          "live": 0,
                          "location": "wan",
                          "machine_id": "lmd93nkn12k29j2lnm",
                          "media_index": 17,
                          "media_type": "episode",
                          "originally_available_at": "2016-04-24",
                          "parent_media_index": 7,
                          "parent_rating_key": 544,
                          "parent_title": "",
                          "paused_counter": 0,
                          "percent_complete": 84,
                          "platform": "Windows",
                          "play_duration": 263,
                          "product": "Plex for Windows",
                          "player": "Castle-PC",
                          "rating_key": 4348,
                          "reference_id": 1123,
                          "relayed": 0,
                          "row_id": 1124,
                          "secure": 1,
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
                          ("product", True, True),
                          ("player", True, True),
                          ("full_title", True, True),
                          ("started", True, False),
                          ("paused_counter", True, False),
                          ("stopped", True, False),
                          ("duration", True, False),
                          ("watched_status", False, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "date")

        grouping = helpers.bool_true(grouping, return_none=True)
        include_activity = helpers.bool_true(include_activity, return_none=True)

        custom_where = []
        if user_id:
            user_id = helpers.split_strip(user_id)
            if user_id:
                custom_where.append(['session_history.user_id', user_id])
        elif user:
            user = helpers.split_strip(user)
            if user:
                custom_where.append(['session_history.user', user])
        if 'rating_key' in kwargs:
            if kwargs.get('media_type') in ('collection', 'playlist') and kwargs.get('rating_key'):
                pms_connect = pmsconnect.PmsConnect()
                result = pms_connect.get_item_children(rating_key=kwargs.pop('rating_key'), media_type=kwargs.pop('media_type'))
                rating_keys = [child['rating_key'] for child in result['children_list']]
                custom_where.append(['session_history_metadata.rating_key OR', rating_keys])
                custom_where.append(['session_history_metadata.parent_rating_key OR', rating_keys])
                custom_where.append(['session_history_metadata.grandparent_rating_key OR', rating_keys])
            else:
                rating_key = helpers.split_strip(kwargs.pop('rating_key', ''))
                if rating_key:
                    custom_where.append(['session_history.rating_key', rating_key])
        if 'parent_rating_key' in kwargs:
            rating_key = helpers.split_strip(kwargs.pop('parent_rating_key', ''))
            if rating_key:
                custom_where.append(['session_history.parent_rating_key', rating_key])
        if 'grandparent_rating_key' in kwargs:
            rating_key = helpers.split_strip(kwargs.pop('grandparent_rating_key', ''))
            if rating_key:
                custom_where.append(['session_history.grandparent_rating_key', rating_key])
        if 'start_date' in kwargs:
            start_date = helpers.split_strip(kwargs.pop('start_date', ''))
            if start_date:
                custom_where.append(["strftime('%Y-%m-%d', datetime(started, 'unixepoch', 'localtime'))", start_date])
        if 'before' in kwargs:
            before = helpers.split_strip(kwargs.pop('before', ''))
            if before:
                custom_where.append(["strftime('%Y-%m-%d', datetime(started, 'unixepoch', 'localtime')) <", before])
        if 'after' in kwargs:
            after = helpers.split_strip(kwargs.pop('after', ''))
            if after:
                custom_where.append(["strftime('%Y-%m-%d', datetime(started, 'unixepoch', 'localtime')) >", after])
        if 'reference_id' in kwargs:
            reference_id = helpers.split_strip(kwargs.pop('reference_id', ''))
            if reference_id:
                custom_where.append(['session_history.reference_id', reference_id])
        if 'section_id' in kwargs:
            section_id = helpers.split_strip(kwargs.pop('section_id', ''))
            if section_id:
                custom_where.append(['session_history.section_id', section_id])
        if 'media_type' in kwargs:
            media_type = helpers.split_strip(kwargs.pop('media_type', ''))
            if media_type and 'all' not in media_type:
                custom_where.append(['media_type_live', media_type])
        if 'transcode_decision' in kwargs:
            transcode_decision = helpers.split_strip(kwargs.pop('transcode_decision', ''))
            if transcode_decision and 'all' not in transcode_decision:
                custom_where.append(['session_history_media_info.transcode_decision', transcode_decision])
        if 'guid' in kwargs:
            guid = helpers.split_strip(kwargs.pop('guid', '').split('?')[0])
            if guid:
                custom_where.append(['session_history_metadata.guid', ['LIKE ' + g + '%' for g in guid]])

        data_factory = datafactory.DataFactory()
        history = data_factory.get_datatables_history(kwargs=kwargs, custom_where=custom_where,
                                                      grouping=grouping, include_activity=include_activity)

        return history

    @cherrypy.expose
    @requireAuth()
    def get_stream_data(self, row_id=None, session_key=None, user=None, **kwargs):

        data_factory = datafactory.DataFactory()
        stream_data = data_factory.get_stream_details(row_id, session_key)

        return serve_template(template_name="stream_data.html", title="Stream Data", data=stream_data, user=user)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi('get_stream_data')
    def get_stream_data_api(self, row_id=None, session_key=None, **kwargs):
        """ Get the stream details from history or current stream.

            ```
            Required parameters:
                row_id (int):       The row ID number for the history item, OR
                session_key (int):  The session key of the current stream

            Optional parameters:
                None

            Returns:
                json:
                    {"aspect_ratio": "2.35",
                     "audio_bitrate": 231,
                     "audio_channels": 6,
                     "audio_language": "English",
                     "audio_language_code": "eng",
                     "audio_codec": "aac",
                     "audio_decision": "transcode",
                     "bitrate": 2731,
                     "container": "mp4",
                     "current_session": "",
                     "grandparent_title": "",
                     "media_type": "movie",
                     "optimized_version": "",
                     "optimized_version_profile": "",
                     "optimized_version_title": "",
                     "original_title": "",
                     "pre_tautulli": "",
                     "quality_profile": "1.5 Mbps 480p",
                     "stream_audio_bitrate": 203,
                     "stream_audio_channels": 2,
                     "stream_audio_language": "English",
                     "stream_audio_language_code", "eng",
                     "stream_audio_codec": "aac",
                     "stream_audio_decision": "transcode",
                     "stream_bitrate": 730,
                     "stream_container": "mkv",
                     "stream_container_decision": "transcode",
                     "stream_subtitle_codec": "",
                     "stream_subtitle_decision": "",
                     "stream_video_bitrate": 527,
                     "stream_video_codec": "h264",
                     "stream_video_decision": "transcode",
                     "stream_video_dynamic_range": "SDR",
                     "stream_video_framerate": "24p",
                     "stream_video_height": 306,
                     "stream_video_resolution": "SD",
                     "stream_video_width": 720,
                     "subtitle_codec": "",
                     "subtitles": "",
                     "synced_version": "",
                     "synced_version_profile": "",
                     "title": "Frozen",
                     "transcode_hw_decoding": "",
                     "transcode_hw_encoding": "",
                     "video_bitrate": 2500,
                     "video_codec": "h264",
                     "video_decision": "transcode",
                     "video_dynamic_range": "SDR",
                     "video_framerate": "24p",
                     "video_height": 816,
                     "video_resolution": "1080",
                     "video_width": 1920
                     }
            ```
        """
        # For backwards compatibility
        if 'id' in kwargs:
            row_id = kwargs['id']

        data_factory = datafactory.DataFactory()
        stream_data = data_factory.get_stream_details(row_id, session_key)

        return stream_data

    @cherrypy.expose
    @requireAuth()
    def get_ip_address_details(self, ip_address=None, **kwargs):
        if not helpers.is_valid_ip(ip_address):
            ip_address = None

        public = helpers.is_public_ip(ip_address)

        return serve_template(template_name="ip_address_modal.html", title="IP Address Details",
                              data=ip_address, public=public, kwargs=kwargs)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("delete_history")
    def delete_history_rows(self, row_ids=None, **kwargs):
        """ Delete history rows from Tautulli.

            ```
            Required parameters:
                row_ids (str):          Comma separated row ids to delete, e.g. "65,110,2,3645"

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        data_factory = datafactory.DataFactory()

        if row_ids:
            success = database.delete_session_history_rows(row_ids=row_ids)

            if success:
                return {'result': 'success', 'message': 'Deleted history.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete history.'}
        else:
            return {'result': 'error', 'message': 'No row ids received.'}


    ##### Graphs #####

    @cherrypy.expose
    @requireAuth()
    def graphs(self, **kwargs):
        return serve_template(template_name="graphs.html", title="Graphs")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @sanitize_out()
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
    def get_plays_by_date(self, time_range='30', user_id=None, y_axis='plays', grouping=None, **kwargs):
        """ Get graph data by date.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

            Returns:
                json:
                    {"categories":
                        ["YYYY-MM-DD", "YYYY-MM-DD", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]},
                         {"name": "Live TV", "data": [...]}
                         ]
                     }
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_day(time_range=time_range,
                                               y_axis=y_axis,
                                               user_id=user_id,
                                               grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_date.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_dayofweek(self, time_range='30', user_id=None, y_axis='plays', grouping=None, **kwargs):
        """ Get graph data by day of the week.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

            Returns:
                json:
                    {"categories":
                        ["Sunday", "Monday", "Tuesday", ..., "Saturday"]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]},
                         {"name": "Live TV", "data": [...]}
                         ]
                     }
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_dayofweek(time_range=time_range,
                                                     y_axis=y_axis,
                                                     user_id=user_id,
                                                     grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_dayofweek.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_hourofday(self, time_range='30', user_id=None, y_axis='plays', grouping=None, **kwargs):
        """ Get graph data by hour of the day.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

            Returns:
                json:
                    {"categories":
                        ["00", "01", "02", ..., "23"]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]},
                         {"name": "Live TV", "data": [...]}
                         ]
                     }
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_hourofday(time_range=time_range,
                                                     y_axis=y_axis,
                                                     user_id=user_id,
                                                     grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_hourofday.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_per_month(self, time_range='12', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by month.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of months of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

            Returns:
                json:
                    {"categories":
                        ["Jan 2016", "Feb 2016", "Mar 2016", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]},
                         {"name": "Live TV", "data": [...]}
                         ]
                     }
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_month(time_range=time_range,
                                                 y_axis=y_axis,
                                                 user_id=user_id,
                                                 grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_per_month.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by top 10 platforms.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

            Returns:
                json:
                    {"categories":
                        ["iOS", "Android", "Chrome", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]},
                         {"name": "Live TV", "data": [...]}
                         ]
                     }
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_platforms(time_range=time_range,
                                                           y_axis=y_axis,
                                                           user_id=user_id,
                                                           grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_top_10_platforms.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by top 10 users.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

            Returns:
                json:
                    {"categories":
                        ["Jon Snow", "DanyKhaleesi69", "A Girl", ...]
                     "series":
                        [{"name": "Movies", "data": [...]}
                         {"name": "TV", "data": [...]},
                         {"name": "Music", "data": [...]},
                         {"name": "Live TV", "data": [...]}
                         ]
                     }
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_users(time_range=time_range,
                                                       y_axis=y_axis,
                                                       user_id=user_id,
                                                       grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_top_10_users.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_stream_type(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by stream type by date.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

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
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_stream_type(time_range=time_range,
                                                       y_axis=y_axis,
                                                       user_id=user_id,
                                                       grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_stream_type.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_concurrent_streams_by_stream_type(self, time_range='30', user_id=None, **kwargs):
        """ Get graph data for concurrent streams by stream type by date.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                user_id (str):          Comma separated list of user id to filter the data

            Returns:
                json:
                    {"categories":
                        ["YYYY-MM-DD", "YYYY-MM-DD", ...]
                     "series":
                        [{"name": "Direct Play", "data": [...]}
                         {"name": "Direct Stream", "data": [...]},
                         {"name": "Transcode", "data": [...]},
                         {"name": "Max. Concurrent Streams", "data":  [...]}
                         ]
                     }
            ```
        """

        graph = graphs.Graphs()
        result = graph.get_total_concurrent_streams_per_stream_type(time_range=time_range, user_id=user_id)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_concurrent_streams_by_stream_type.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_source_resolution(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by source resolution.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

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
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_source_resolution(time_range=time_range,
                                                            y_axis=y_axis,
                                                            user_id=user_id,
                                                            grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_source_resolution.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_plays_by_stream_resolution(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by stream resolution.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

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
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_stream_resolution(time_range=time_range,
                                                            y_axis=y_axis,
                                                            user_id=user_id,
                                                            grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_plays_by_stream_resolution.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by stream type by top 10 users.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

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
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_users(time_range=time_range,
                                                       y_axis=y_axis,
                                                       user_id=user_id,
                                                       grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_stream_type_by_top_10_users.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays', user_id=None, grouping=None, **kwargs):
        """ Get graph data by stream type by top 10 platforms.

            ```
            Required parameters:
                None

            Optional parameters:
                time_range (str):       The number of days of data to return
                y_axis (str):           "plays" or "duration"
                user_id (str):          Comma separated list of user id to filter the data
                grouping (int):         0 or 1

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
        grouping = helpers.bool_true(grouping, return_none=True)

        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_platforms(time_range=time_range,
                                                           y_axis=y_axis,
                                                           user_id=user_id,
                                                           grouping=grouping)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_stream_type_by_top_10_platforms.")
            return result

    @cherrypy.expose
    @requireAuth()
    def history_table_modal(self, **kwargs):
        if kwargs.get('user_id') and not allow_session_user(kwargs['user_id']):
            return serve_template(template_name="history_table_modal.html", title="History Data", data=None)

        return serve_template(template_name="history_table_modal.html", title="History Data", data=kwargs)


    ##### Sync #####

    @cherrypy.expose
    @requireAuth()
    def sync(self, **kwargs):
        return serve_template(template_name="sync.html", title="Synced Items")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @sanitize_out()
    @requireAuth()
    def get_sync(self, machine_id=None, user_id=None, **kwargs):
        if user_id == 'null':
            user_id = None

        if get_session_user_id():
            user_id = get_session_user_id()

        plex_tv = plextv.PlexTV(token=plexpy.CONFIG.PMS_TOKEN)
        result = plex_tv.get_synced_items(machine_id=machine_id, user_id_filter=user_id)

        if result:
            output = {"data": result}
        else:
            logger.warn("Unable to retrieve data for get_sync.")
            output = {"data": []}

        return output

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("delete_synced_item")
    def delete_sync_rows(self, client_id=None, sync_id=None, **kwargs):
        """ Delete a synced item from a device.

            ```
            Required parameters:
                client_id (str):        The client ID of the device to delete from
                sync_id (str):          The sync ID of the synced item

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        if client_id and sync_id:
            plex_tv = plextv.PlexTV()
            delete_row = plex_tv.delete_sync(client_id=client_id, sync_id=sync_id)
            if delete_row:
                return {'result': 'success', 'message': 'Synced item deleted successfully.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete synced item.'}
        else:
            return {'result': 'error', 'message': 'Missing client ID and sync ID.'}


    ##### Logs #####
    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def logs(self, **kwargs):
        plex_log_files = log_reader.list_plex_logs()
        return serve_template(template_name="logs.html", title="Log", plex_log_files=plex_log_files)

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

        if logfile == "tautulli_api":
            filename = logger.FILENAME_API
        elif logfile == "plex_websocket":
            filename = logger.FILENAME_PLEX_WEBSOCKET
        else:
            filename = logger.FILENAME

        with open(os.path.join(plexpy.CONFIG.LOG_DIR, filename), 'r', encoding='utf-8') as f:
            for l in f.readlines():
                try:
                    temp_loglevel_and_time = l.split(' - ', 1)
                    loglvl = temp_loglevel_and_time[1].split(' ::', 1)[0].strip()
                    msg = helpers.sanitize(l.split(' : ', 1)[1].replace('\n', ''))
                    fa([temp_loglevel_and_time[0], loglvl, msg])
                except IndexError:
                    # Add traceback message to previous msg.
                    tl = (len(filt) - 1)
                    n = len(l) - len(l.lstrip(' '))
                    ll = '&nbsp;' * (2 * n) + helpers.sanitize(l[n:])
                    filt[tl][2] += '<br>' + ll
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
    def get_plex_log(self, logfile='', **kwargs):
        """ Get the PMS logs.

            ```
            Required parameters:
                None

            Optional parameters:
                window (int):           The number of tail lines to return
                logfile (int):          The name of the Plex log file,
                                        e.g. "Plex Media Server", "Plex Media Scanner"

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
        if kwargs.get('log_type'):
            logfile = 'Plex Media ' + kwargs['log_type'].capitalize()

        window = int(kwargs.get('window', plexpy.CONFIG.PMS_LOGS_LINE_CAP))

        try:
            return {'data': log_reader.get_log_tail(window=window, parsed=True, log_file=logfile)}
        except:
            logger.warn("Unable to retrieve Plex log file '%'." % logfile)
            return []

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @sanitize_out()
    @addtoapi()
    def get_notification_log(self, **kwargs):
        """ Get the data on the Tautulli notification logs table.

            ```
            Required parameters:
                None

            Optional parameters:
                order_column (str):             "timestamp", "notifier_id", "agent_name", "notify_action",
                                                "subject_text", "body_text",
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
                          "agent_name": "telegram",
                          "body_text": "DanyKhaleesi69 started playing The Red Woman.",
                          "id": 1000,
                          "notify_action": "on_play",
                          "rating_key": 153037,
                          "session_key": 147,
                          "subject_text": "Tautulli (Winterfell-Server)",
                          "success": 1,
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
                          ("notifier_id", True, True),
                          ("agent_name", True, True),
                          ("notify_action", True, True),
                          ("subject_text", True, True),
                          ("body_text", True, True)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "timestamp")

        data_factory = datafactory.DataFactory()
        notification_logs = data_factory.get_notification_log(kwargs=kwargs)

        return notification_logs

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @sanitize_out()
    @addtoapi()
    def get_newsletter_log(self, **kwargs):
        """ Get the data on the Tautulli newsletter logs table.

            ```
            Required parameters:
                None

            Optional parameters:
                order_column (str):             "timestamp", "newsletter_id", "agent_name", "notify_action",
                                                "subject_text", "start_date", "end_date", "uuid"
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
                        [{"agent_id": 0,
                          "agent_name": "recently_added",
                          "end_date": "2018-03-18",
                          "id": 7,
                          "newsletter_id": 1,
                          "notify_action": "on_cron",
                          "start_date": "2018-03-05",
                          "subject_text": "Recently Added to Plex (Winterfell-Server)! (2018-03-18)",
                          "success": 1,
                          "timestamp": 1462253821,
                          "uuid": "7fe4g65i"
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
                          ("newsletter_id", True, True),
                          ("agent_name", True, True),
                          ("notify_action", True, True),
                          ("subject_text", True, True),
                          ("body_text", True, True),
                          ("start_date", True, True),
                          ("end_date", True, True),
                          ("uuid", True, True)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "timestamp")

        data_factory = datafactory.DataFactory()
        newsletter_logs = data_factory.get_newsletter_log(kwargs=kwargs)

        return newsletter_logs

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_notification_log(self, **kwargs):
        """ Delete the Tautulli notification logs.

            ```
            Required parameters:
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
    def delete_newsletter_log(self, **kwargs):
        """ Delete the Tautulli newsletter logs.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        data_factory = datafactory.DataFactory()
        result = data_factory.delete_newsletter_log()
        res = 'success' if result else 'error'
        msg = 'Cleared newsletter logs.' if result else 'Failed to clear newsletter logs.'

        return {'result': res, 'message': msg}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_login_log(self, **kwargs):
        """ Delete the Tautulli login logs.

            ```
            Required parameters:
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
        if logfile == "tautulli_api":
            filename = logger.FILENAME_API
        elif logfile == "plex_websocket":
            filename = logger.FILENAME_PLEX_WEBSOCKET
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
            logger.exception('Failed to clear the %s file: %s.' % (filename, e))

        return {'result': result, 'message': msg}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def toggleVerbose(self, **kwargs):
        plexpy.VERBOSE = not plexpy.VERBOSE

        plexpy.CONFIG.VERBOSE_LOGS = plexpy.VERBOSE
        plexpy.CONFIG.write()

        logger.initLogger(console=not plexpy.QUIET, log_dir=plexpy.CONFIG.LOG_DIR, verbose=plexpy.VERBOSE)
        logger.info("Verbose toggled, set to %s", plexpy.VERBOSE)
        logger.debug("If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "logs")

    @cherrypy.expose
    @requireAuth()
    def log_js_errors(self, page, message, file, line, **kwargs):
        """ Logs javascript errors from the web interface. """
        logger.error("WebUI :: /%s : %s. (%s:%s)" % (page.rpartition('/')[-1],
                                                      message,
                                                      file.rpartition('/')[-1].partition('?')[0],
                                                      line))
        return "js error logged."

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def logFile(self, logfile='', **kwargs):
        if logfile == "tautulli_api":
            filename = logger.FILENAME_API
        elif logfile == "plex_websocket":
            filename = logger.FILENAME_PLEX_WEBSOCKET
        else:
            filename = logger.FILENAME

        try:
            with open(os.path.join(plexpy.CONFIG.LOG_DIR, filename), 'r', encoding='utf-8') as f:
                return '<pre>%s</pre>' % f.read()
        except IOError as e:
            return "Log file not found."


    ##### Settings #####

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def settings(self, **kwargs):
        settings_dict = {}

        for setting in config.SETTINGS:
            settings_dict[setting.lower()] = getattr(plexpy.CONFIG, setting)

        for setting in config.CHECKED_SETTINGS:
            settings_dict[setting.lower()] = checked(getattr(plexpy.CONFIG, setting))

        # Initialise blank passwords so we do not expose them in the html forms
        # but users are still able to clear them
        if plexpy.CONFIG.HTTP_PASSWORD != '':
            settings_dict['http_password'] = '    '
        else:
            settings_dict['http_password'] = ''

        for key in ('home_sections', 'home_stats_cards', 'home_library_cards'):
            settings_dict[key] = json.dumps(settings_dict[key])

        return serve_template(template_name="settings.html", title="Settings", config=settings_dict)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        # Check if we should refresh our data
        first_run = False
        startup_changed = False
        server_changed = False
        reschedule = False
        https_changed = False
        refresh_libraries = False
        refresh_users = False

        # First run from the setup wizard
        if kwargs.pop('first_run', None):
            first_run = True
            server_changed = True

        if not first_run:
            for checked_config in config.CHECKED_SETTINGS:
                checked_config = checked_config.lower()
                if checked_config not in kwargs:
                    # checked items should be zero or one. if they were not sent then the item was not checked
                    kwargs[checked_config] = 0
                else:
                    kwargs[checked_config] = 1

        # If http password exists in config, do not overwrite when blank value received
        if kwargs.get('http_password') == '    ':
            del kwargs['http_password']
        else:
            if kwargs.get('http_password', '') != '':
                kwargs['http_password'] = make_hash(kwargs['http_password'])
            # Flag to refresh JWT uuid to log out clients
            kwargs['jwt_update_secret'] = True and not first_run

        for plain_config, use_config in [(x[4:], x) for x in kwargs if x.startswith('use_')]:
            # the use prefix is fairly nice in the html, but does not match the actual config
            kwargs[plain_config] = kwargs[use_config]
            del kwargs[use_config]

        if kwargs.get('launch_startup') != plexpy.CONFIG.LAUNCH_STARTUP or \
                kwargs.get('launch_browser') != plexpy.CONFIG.LAUNCH_BROWSER:
            startup_changed = True

        # If we change any monitoring settings, make sure we reschedule tasks.
        if kwargs.get('check_github') != plexpy.CONFIG.CHECK_GITHUB or \
                kwargs.get('check_github_interval') != str(plexpy.CONFIG.CHECK_GITHUB_INTERVAL) or \
                kwargs.get('refresh_libraries_interval') != str(plexpy.CONFIG.REFRESH_LIBRARIES_INTERVAL) or \
                kwargs.get('refresh_users_interval') != str(plexpy.CONFIG.REFRESH_USERS_INTERVAL) or \
                kwargs.get('pms_update_check_interval') != str(plexpy.CONFIG.PMS_UPDATE_CHECK_INTERVAL) or \
                kwargs.get('monitor_pms_updates') != plexpy.CONFIG.MONITOR_PMS_UPDATES or \
                kwargs.get('pms_url_manual') != plexpy.CONFIG.PMS_URL_MANUAL or \
                kwargs.get('backup_interval') != str(plexpy.CONFIG.BACKUP_INTERVAL):
            reschedule = True

        # If we change the SSL setting for PMS or PMS remote setting, make sure we grab the new url.
        if kwargs.get('pms_ssl') != str(plexpy.CONFIG.PMS_SSL) or \
                kwargs.get('pms_url_manual') != plexpy.CONFIG.PMS_URL_MANUAL:
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
            for k in list(kwargs.keys()):
                if k.startswith('hsec-'):
                    del kwargs[k]
            kwargs['home_sections'] = kwargs['home_sections'].split(',')

        # Remove config with 'hscard-' prefix and change home_stats_cards to list
        if kwargs.get('home_stats_cards'):
            for k in list(kwargs.keys()):
                if k.startswith('hscard-'):
                    del kwargs[k]
            kwargs['home_stats_cards'] = kwargs['home_stats_cards'].split(',')

        # Remove config with 'hlcard-' prefix and change home_library_cards to list
        if kwargs.get('home_library_cards'):
            for k in list(kwargs.keys()):
                if k.startswith('hlcard-'):
                    del kwargs[k]
            kwargs['home_library_cards'] = kwargs['home_library_cards'].split(',')

        # If we change the server, make sure we grab the new url and refresh libraries and users lists.
        if kwargs.pop('server_changed', None) or server_changed:
            server_changed = True
            refresh_users = True
            refresh_libraries = True

        # If we change the authentication settings, make sure we refresh the users lists.
        if kwargs.pop('auth_changed', None):
            refresh_users = True

        all_settings = config.SETTINGS + config.CHECKED_SETTINGS
        kwargs = {k: v for k, v in kwargs.items() if k.upper() in all_settings}

        if first_run:
            kwargs['first_run_complete'] = 1

        plexpy.CONFIG.process_kwargs(kwargs)

        # Write the config
        plexpy.CONFIG.write()

        # Enable or disable system startup
        if startup_changed:
            if common.PLATFORM == 'Windows':
                windows.set_startup()
            elif common.PLATFORM == 'Darwin':
                macos.set_startup()

        # Get new server URLs for SSL communications and get new server friendly name
        if server_changed:
            plextv.get_server_resources()
            if plexpy.WS_CONNECTED:
                web_socket.reconnect()

        # If first run, start websocket
        if first_run:
            webstart.restart()
            activity_pinger.connect_server(log=True, startup=True)

        # Reconfigure scheduler if intervals changed
        if reschedule:
            plexpy.initialize_scheduler()

        # Generate a new HTTPS certificate
        if https_changed:
            create_https_certificates(plexpy.CONFIG.HTTPS_CERT, plexpy.CONFIG.HTTPS_KEY)

        # Refresh users table if our server IP changes.
        if refresh_libraries:
            threading.Thread(target=libraries.refresh_libraries).start()

        # Refresh users table if our server IP changes.
        if refresh_users:
            threading.Thread(target=users.refresh_users).start()

        return {'result': 'success', 'message': 'Settings saved.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def check_pms_token(self, **kwargs):
        plex_tv = plextv.PlexTV()
        response = plex_tv.get_plextv_resources(return_response=True)
        if not response.ok:
            cherrypy.response.status = 401

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_pms_downloads(self, update_channel, **kwargs):
        plex_tv = plextv.PlexTV()
        downloads = plex_tv.get_plex_downloads(update_channel=update_channel)
        return downloads

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_server_resources(self, **kwargs):
        return plextv.get_server_resources(return_server=True, **kwargs)

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
        return serve_template(template_name="configuration_table.html")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_scheduler_table(self, **kwargs):
        return serve_template(template_name="scheduler_table.html")

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_queue_modal(self, queue=None, **kwargs):
        return serve_template(template_name="queue_modal.html", queue=queue)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_server_update_params(self, **kwargs):
        plex_tv = plextv.PlexTV()
        plexpass = plex_tv.get_plexpass_status()

        update_channel = pmsconnect.PmsConnect().get_server_update_channel()

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
        return serve_template(template_name="notifiers_table.html", notifiers_list=result)

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
        result = notifiers.get_notifier_config(notifier_id=notifier_id, mask_passwords=True)
        return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_notifier_config_modal(self, notifier_id=None, **kwargs):
        result = notifiers.get_notifier_config(notifier_id=notifier_id, mask_passwords=True)

        parameters = [
                {'name': param['name'], 'type': param['type'], 'value': param['value']}
                for category in common.NOTIFICATION_PARAMETERS for param in category['parameters']
            ]

        return serve_template(template_name="notifier_config.html", notifier=result, parameters=parameters)

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
        """ Configure an existing notification agent.

            ```
            Required parameters:
                notifier_id (int):        The notifier config to update
                agent_id (int):           The agent of the notifier

            Optional parameters:
                Pass all the config options for the agent with the agent prefix:
                    e.g. For Telegram: telegram_bot_token
                                       telegram_chat_id
                                       telegram_disable_web_preview
                                       telegram_html_support
                                       telegram_incl_poster
                                       telegram_incl_subject
                Notify actions (int):  0 or 1,
                    e.g. on_play, on_stop, etc.
                Notify text (str):
                    e.g. on_play_subject, on_play_body, etc.

            Returns:
                None
            ```
        """
        result = notifiers.set_notifier_config(notifier_id=notifier_id, agent_id=agent_id, **kwargs)

        if result:
            return {'result': 'success', 'message': 'Saved notification agent.'}
        else:
            return {'result': 'error', 'message': 'Failed to save notification agent.'}

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

        return serve_template(template_name="notifier_text_preview.html", text=text, agent=agent_name)

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
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def send_notification(self, notifier_id=None, subject='Tautulli', body='Test notification', notify_action='', **kwargs):
        """ Send a notification using Tautulli.

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
                logger.debug("Sending %s%s notification." % (test, notifier['agent_label']))
                notification_handler.add_notifier_each(notifier_id=notifier_id,
                                                       notify_action=notify_action,
                                                       subject=subject,
                                                       body=body,
                                                       manual_trigger=True,
                                                       **kwargs)
                return {'result': 'success', 'message': 'Notification queued.'}
            else:
                logger.debug("Unable to send %snotification, invalid notifier_id %s." % (test, notifier_id))
                return {'result': 'error', 'message': 'Invalid notifier id %s.' % notifier_id}
        else:
            logger.debug("Unable to send %snotification, no notifier_id received." % test)
            return {'result': 'error', 'message': 'No notifier id received.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_browser_notifications(self, **kwargs):
        result = notifiers.get_browser_notifications()

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
    def facebook_auth(self, app_id='', app_secret='', redirect_uri='', **kwargs):
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
    def facebook_redirect(self, code='', **kwargs):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        facebook = notifiers.FACEBOOK()
        access_token = facebook._get_credentials(code)

        if access_token:
            return "Facebook authorization successful. Tautulli can send notification to Facebook. " \
                "Your Facebook access token is:" \
                "<pre>{0}</pre>You may close this page.".format(access_token)
        else:
            return "Failed to request authorization from Facebook. Check the Tautulli logs for details.<br />You may close this page."

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
            # logger.info("Registered %s, to re-register a different app, delete this app first" % result)
        else:
            logger.warn(msg)
        return msg

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def zapier_test_hook(self, zapier_hook='', **kwargs):
        success = notifiers.ZAPIER(config={'hook': zapier_hook})._test_hook()
        if success:
            return {'result': 'success', 'msg': 'Test Zapier webhook sent.'}
        else:
            return {'result': 'error', 'msg': 'Failed to send test Zapier webhook.'}

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
        return serve_template(template_name="mobile_devices_table.html", devices_list=result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def verify_mobile_device(self, device_token='', cancel=False, **kwargs):
        if helpers.bool_true(cancel):
            mobile_app.set_temp_device_token(device_token, remove=True)
            return {'result': 'error', 'message': 'Device registration cancelled.'}

        result = mobile_app.get_temp_device_token(device_token)
        if result is True:
            mobile_app.set_temp_device_token(device_token, remove=True)
            return {'result': 'success', 'message': 'Device registered successfully.', 'data': result}
        else:
            return {'result': 'error', 'message': 'Device not registered.'}


    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_mobile_device_config_modal(self, mobile_device_id=None, **kwargs):
        result = mobile_app.get_mobile_device_config(mobile_device_id=mobile_device_id)

        return serve_template(template_name="mobile_device_config.html", device=result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def set_mobile_device_config(self, mobile_device_id=None, **kwargs):
        """ Configure an existing notification agent.

            ```
            Required parameters:
                mobile_device_id (int):        The mobile device config to update

            Optional parameters:
                friendly_name (str):           A friendly name to identify the mobile device

            Returns:
                None
            ```
        """
        result = mobile_app.set_mobile_device_config(mobile_device_id=mobile_device_id, **kwargs)

        if result:
            return {'result': 'success', 'message': 'Saved mobile device.'}
        else:
            return {'result': 'error', 'message': 'Failed to save mobile device.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_mobile_device(self, mobile_device_id=None, device_id=None, **kwargs):
        """ Remove a mobile device from the database.

            ```
            Required parameters:
                mobile_device_id (int):        The mobile device database id to delete, OR
                device_id (str):               The unique device identifier for the mobile device

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        result = mobile_app.delete_mobile_device(mobile_device_id=mobile_device_id,
                                                 device_id=device_id)
        if result:
            return {'result': 'success', 'message': 'Deleted mobile device.'}
        else:
            return {'result': 'error', 'message': 'Failed to delete device.'}

    @cherrypy.config(**{'response.timeout': 3600})
    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def import_database(self, app=None, database_file=None, database_path=None, method=None, backup=False,
                        table_name=None, import_ignore_interval=0, **kwargs):
        """ Import a Tautulli, PlexWatch, or Plexivity database into Tautulli.

            ```
            Required parameters:
                app (str):                      "tautulli" or "plexwatch" or "plexivity"
                database_file (file):           The database file to import (multipart/form-data)
                or
                database_path (str):            The full path to the database file to import
                method (str):                   For Tautulli only, "merge" or "overwrite"
                table_name (str):               For PlexWatch or Plexivity only, "processed" or "grouped"


            Optional parameters:
                backup (bool):                  For Tautulli only, true or false whether to backup
                                                the current database before importing
                import_ignore_interval (int):   For PlexWatch or Plexivity only, the minimum number
                                                of seconds for a stream to import

            Returns:
                json:
                    {"result": "success",
                     "message": "Database import has started. Check the logs to monitor any problems."
                     }
            ```
        """
        if not app:
            return {'result': 'error', 'message': 'No app specified for import'}

        if database_path:
            database_file_name = os.path.basename(database_path)
            database_cache_path = os.path.join(plexpy.CONFIG.CACHE_DIR, database_file_name + '.import.db')
            logger.info("Received database file '%s' for import. Saving to cache: %s",
                        database_file_name, database_cache_path)
            database_path = shutil.copyfile(database_path, database_cache_path)

        elif database_file:
            database_path = os.path.join(plexpy.CONFIG.CACHE_DIR, database_file.filename + '.import.db')
            logger.info("Received database file '%s' for import. Saving to cache: %s",
                        database_file.filename, database_path)
            with open(database_path, 'wb') as f:
                while True:
                    data = database_file.file.read(8192)
                    if not data:
                        break
                    f.write(data)

        if not database_path:
            return {'result': 'error', 'message': 'No database specified for import'}

        if app.lower() == 'tautulli':
            db_check_msg = database.validate_database(database=database_path)
            if db_check_msg == 'success':
                threading.Thread(target=database.import_tautulli_db,
                                 kwargs={'database': database_path,
                                         'method': method,
                                         'backup': helpers.bool_true(backup)}).start()
                return {'result': 'success',
                        'message': 'Database import has started. Check the logs to monitor any problems.'}
            else:
                if database_file:
                    helpers.delete_file(database_path)
                return {'result': 'error', 'message': db_check_msg}

        elif app.lower() == 'plexwatch':
            db_check_msg = plexwatch_import.validate_database(database_file=database_path,
                                                              table_name=table_name)
            if db_check_msg == 'success':
                threading.Thread(target=plexwatch_import.import_from_plexwatch,
                                 kwargs={'database_file': database_path,
                                         'table_name': table_name,
                                         'import_ignore_interval': import_ignore_interval}).start()
                return {'result': 'success',
                        'message': 'Database import has started. Check the logs to monitor any problems.'}
            else:
                if database_file:
                    helpers.delete_file(database_path)
                return {'result': 'error', 'message': db_check_msg}

        elif app.lower() == 'plexivity':
            db_check_msg = plexivity_import.validate_database(database_file=database_path,
                                                              table_name=table_name)
            if db_check_msg == 'success':
                threading.Thread(target=plexivity_import.import_from_plexivity,
                                 kwargs={'database_file': database_path,
                                         'table_name': table_name,
                                         'import_ignore_interval': import_ignore_interval}).start()
                return {'result': 'success',
                        'message': 'Database import has started. Check the logs to monitor any problems.'}
            else:
                if database_file:
                    helpers.delete_file(database_path)
                return {'result': 'error', 'message': db_check_msg}

        else:
            return {'result': 'error', 'message': 'App not recognized for import'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def import_config(self, config_file=None, config_path=None, backup=False, **kwargs):
        """ Import a Tautulli config file.

            ```
            Required parameters:
                config_file (file):             The config file to import (multipart/form-data)
                or
                config_path (str):              The full path to the config file to import


            Optional parameters:
                backup (bool):                  true or false whether to backup
                                                the current config before importing

            Returns:
                json:
                    {"result": "success",
                     "message": "Config import has started. Check the logs to monitor any problems. "
                                "Tautulli will restart automatically."
                     }
            ```
        """
        if database.IS_IMPORTING:
            return {'result': 'error',
                    'message': 'Database import is in progress. Please wait until it is finished to import a config.'}

        if config_file:
            config_path = os.path.join(plexpy.CONFIG.CACHE_DIR, config_file.filename + '.import.ini')
            logger.info("Received config file '%s' for import. Saving to cache '%s'.",
                        config_file.filename, config_path)
            with open(config_path, 'wb') as f:
                while True:
                    data = config_file.file.read(8192)
                    if not data:
                        break
                    f.write(data)

        if not config_path:
            return {'result': 'error', 'message': 'No config specified for import'}

        config.set_import_thread(config=config_path, backup=helpers.bool_true(backup))

        return {'result': 'success',
                'message': 'Config import has started. Check the logs to monitor any problems. '
                           'Tautulli will restart automatically.'}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def import_database_tool(self, app=None, **kwargs):
        if app == 'tautulli':
            return serve_template(template_name="app_import.html", title="Import Tautulli Database", app="Tautulli")
        elif app == 'plexwatch':
            return serve_template(template_name="app_import.html", title="Import PlexWatch Database", app="PlexWatch")
        elif app == 'plexivity':
            return serve_template(template_name="app_import.html", title="Import Plexivity Database", app="Plexivity")

        logger.warn("No app specified for import.")
        return

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def import_config_tool(self, **kwargs):
        return serve_template(template_name="config_import.html", title="Import Tautulli Configuration")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def browse_path(self, key=None, path=None, filter_ext=''):
        if key:
            path = base64.b64decode(key).decode('UTF-8')
        if not path:
            path = plexpy.DATA_DIR

        data = helpers.browse_path(path=path, filter_ext=filter_ext)
        if data:
            return {'result': 'success', 'path': path, 'data': data}
        else:
            return {'result': 'error', 'message': 'Invalid path.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_server_id(self, hostname=None, port=None, identifier=None, ssl=0, manual=0,
                      get_url=False, test_websocket=False, **kwargs):
        """ Get the PMS server identifier.

            ```
            Required parameters:
                hostname (str):     'localhost' or '192.160.0.10'
                port (int):         32400

            Optional parameters:
                ssl (int):          0 or 1
                remote (int):       0 or 1

            Returns:
                json:
                    {'identifier': '08u2phnlkdshf890bhdlksghnljsahgleikjfg9t'}
            ```
        """
        ssl = helpers.bool_true(ssl)

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

            # Fallback to checking /identity endpoint if the server is unpublished
            # Cannot set SSL settings on the PMS if unpublished so 'http' is okay
            if not identifier:
                scheme = 'https' if ssl else 'http'
                url = '{scheme}://{hostname}:{port}'.format(scheme=scheme, hostname=hostname, port=port)
                uri = '/identity'

                request_handler = http_handler.HTTPHandler(urls=url,
                                                           ssl_verify=False)
                request = request_handler.make_request(uri=uri,
                                                       request_type='GET',
                                                       output_format='xml')
                if request:
                    xml_head = request.getElementsByTagName('MediaContainer')[0]
                    identifier = xml_head.getAttribute('machineIdentifier')

        result = {'identifier': identifier}

        if identifier:
            if helpers.bool_true(get_url):
                server = self.get_server_resources(pms_ip=hostname,
                                                   pms_port=port,
                                                   pms_ssl=ssl,
                                                   pms_url_manual=manual,
                                                   pms_identifier=identifier)
                result['url'] = server['pms_url']
                result['ws'] = None

                if helpers.bool_true(test_websocket):
                    # Quick test websocket connection
                    ws_url = result['url'].replace('http', 'ws', 1) + '/:/websockets/notifications'
                    header = ['X-Plex-Token: %s' % plexpy.CONFIG.PMS_TOKEN]
                    # Enforce SSL as needed
                    if ssl:
                        secure = 'secure '
                        if plexpy.CONFIG.VERIFY_SSL_CERT:
                            sslopt = {'ca_certs': certifi.where()}
                        else:
                            sslopt = {'cert_reqs': _ssl.CERT_NONE}
                    else:
                        secure = ''
                        sslopt = None

                    logger.debug("Testing %swebsocket connection..." % secure)
                    try:
                        test_ws = websocket.create_connection(ws_url, header=header, sslopt=sslopt)
                        test_ws.close()
                        logger.debug("Websocket connection test successful.")
                        result['ws'] = True
                    except (websocket.WebSocketException, IOError, Exception) as e:
                        logger.error("Websocket connection test failed: %s" % e)
                        result['ws'] = False

            return result
        else:
            logger.warn('Unable to retrieve the PMS identifier.')
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_server_info(self, **kwargs):
        """ Get the PMS server information.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {"pms_identifier": "08u2phnlkdshf890bhdlksghnljsahgleikjfg9t",
                     "pms_ip": "10.10.10.1",
                     "pms_is_remote": 0,
                     "pms_name": "Winterfell-Server",
                     "pms_platform": "Windows",
                     "pms_plexpass": 1,
                     "pms_port": 32400,
                     "pms_ssl": 0,
                     "pms_url": "http://10.10.10.1:32400",
                     "pms_url_manual": 0,
                     "pms_version": "1.20.0.3133-fede5bdc7"
                    }
            ```
        """
        server = plextv.get_server_resources(return_info=True)
        server.pop('pms_is_cloud', None)
        return server

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
            logger.warn("Unable to retrieve data for get_server_pref.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def generate_api_key(self, device=None, **kwargs):
        apikey = ''
        while not apikey or apikey == plexpy.CONFIG.API_KEY or mobile_app.get_mobile_device_by_token(device_token=apikey):
            if sys.version_info >= (3, 6):
                apikey = secrets.token_urlsafe(24)
            else:
                apikey = plexpy.generate_uuid()

        logger.info("New API key generated.")
        logger._BLACKLIST_WORDS.add(apikey)

        if helpers.bool_true(device):
            mobile_app.set_temp_device_token(apikey, add=True)

        return apikey

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def update_check(self, **kwargs):
        """ Check for Tautulli updates.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json
                    {"result": "success",
                     "update": true,
                     "message": "An update for Tautulli is available."
                    }
            ```
        """
        versioncheck.check_update()

        if plexpy.UPDATE_AVAILABLE is None:
            update = {'result': 'error',
                      'update': None,
                      'message': 'You are running an unknown version of Tautulli.'
                      }

        elif plexpy.UPDATE_AVAILABLE == 'release':
            update = {'result': 'success',
                      'update': True,
                      'release': True,
                      'message': 'A new release (%s) of Tautulli is available.' % plexpy.LATEST_RELEASE,
                      'current_release': plexpy.common.RELEASE,
                      'latest_release': plexpy.LATEST_RELEASE,
                      'release_url': helpers.anon_url(
                          'https://github.com/%s/%s/releases/tag/%s'
                          % (plexpy.CONFIG.GIT_USER,
                             plexpy.CONFIG.GIT_REPO,
                             plexpy.LATEST_RELEASE))
                      }

        elif plexpy.UPDATE_AVAILABLE == 'commit':
            update = {'result': 'success',
                      'update': True,
                      'release': False,
                      'message': 'A newer version of Tautulli is available.',
                      'current_version': plexpy.CURRENT_VERSION,
                      'latest_version': plexpy.LATEST_VERSION,
                      'commits_behind': plexpy.COMMITS_BEHIND,
                      'compare_url': helpers.anon_url(
                          'https://github.com/%s/%s/compare/%s...%s'
                          % (plexpy.CONFIG.GIT_USER,
                             plexpy.CONFIG.GIT_REPO,
                             plexpy.CURRENT_VERSION,
                             plexpy.LATEST_VERSION))
                      }

        else:
            update = {'result': 'success',
                      'update': False,
                      'message': 'Tautulli is up to date.'
                      }

        if plexpy.DOCKER or plexpy.SNAP or plexpy.FROZEN:
            update['install_type'] = plexpy.INSTALL_TYPE

        return update

    def do_state_change(self, signal, title, timer, **kwargs):
        message = title
        quote = self.random_arnold_quotes()
        if signal:
            plexpy.SIGNAL = signal

        if plexpy.CONFIG.HTTP_ROOT.strip('/'):
            new_http_root = '/' + plexpy.CONFIG.HTTP_ROOT.strip('/') + '/'
        else:
            new_http_root = '/'

        return serve_template(template_name="shutdown.html", signal=signal, title=title,
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
        if plexpy.DOCKER or plexpy.SNAP:
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")

        # Show changelog after updating
        plexpy.CONFIG.UPDATE_SHOW_CHANGELOG = 1
        plexpy.CONFIG.write()
        return self.do_state_change('update', 'Updating', 120)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def checkout_git_branch(self, git_remote=None, git_branch=None, **kwargs):
        if git_branch == plexpy.CONFIG.GIT_BRANCH:
            logger.error("Already on the %s branch" % git_branch)
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT + "home")

        # Set the new git remote and branch
        plexpy.CONFIG.GIT_REMOTE = git_remote
        plexpy.CONFIG.GIT_BRANCH = git_branch
        plexpy.CONFIG.write()
        return self.do_state_change('checkout', 'Switching Git Branches', 120)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def reset_git_install(self, **kwargs):
        return self.do_state_change('reset', 'Resetting to {}'.format(common.RELEASE), 120)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def restart_import_config(self, **kwargs):
        if config.IMPORT_THREAD:
            config.IMPORT_THREAD.start()
        return self.do_state_change(None, 'Importing a Config', 15)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_changelog(self, latest_only=False, since_prev_release=False, update_shown=False, **kwargs):
        latest_only = helpers.bool_true(latest_only)
        since_prev_release = helpers.bool_true(since_prev_release)

        if since_prev_release and plexpy.PREV_RELEASE == common.RELEASE:
            latest_only = True
            since_prev_release = False

        # Set update changelog shown status
        if helpers.bool_true(update_shown):
            plexpy.CONFIG.UPDATE_SHOW_CHANGELOG = 0
            plexpy.CONFIG.write()

        return versioncheck.read_changelog(latest_only=latest_only, since_prev_release=since_prev_release)

    ##### Info #####

    @cherrypy.expose
    @requireAuth()
    def info(self, rating_key=None, guid=None, source=None, section_id=None, user_id=None, **kwargs):
        if rating_key and not str(rating_key).isdigit():
            raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

        metadata = None

        config = {
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_web_url": plexpy.CONFIG.PMS_WEB_URL
        }

        if user_id:
            user_data = users.Users()
            user_info = user_data.get_details(user_id=user_id)
        else:
            user_info = {}

        # Try to get metadata from the Plex server first
        if rating_key:
            pms_connect = pmsconnect.PmsConnect()
            metadata = pms_connect.get_metadata_details(rating_key=rating_key, section_id=section_id)

        # If the item is not found on the Plex server, get the metadata from history
        if not metadata and source == 'history':
            data_factory = datafactory.DataFactory()
            metadata = data_factory.get_metadata_details(rating_key=rating_key, guid=guid)

        if metadata:
            data_factory = datafactory.DataFactory()
            poster_info = data_factory.get_poster_info(metadata=metadata)
            metadata.update(poster_info)
            lookup_info = data_factory.get_lookup_info(metadata=metadata)
            metadata.update(lookup_info)

        if metadata:
            if metadata['section_id'] and not allow_session_library(metadata['section_id']):
                raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)

            return serve_template(template_name="info.html", metadata=metadata, title="Info",
                                  config=config, source=source, user_info=user_info)
        else:
            if get_session_user_id():
                raise cherrypy.HTTPRedirect(plexpy.HTTP_ROOT)
            else:
                return self.update_metadata(rating_key)

    @cherrypy.expose
    @requireAuth()
    def get_item_children(self, rating_key='', media_type=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_item_children(rating_key=rating_key, media_type=media_type)

        if result:
            return serve_template(template_name="info_children_list.html", data=result,
                                  media_type=media_type, title="Children List")
        else:
            logger.warn("Unable to retrieve data for get_item_children.")
            return serve_template(template_name="info_children_list.html", data=None, title="Children List")

    @cherrypy.expose
    @requireAuth()
    def get_item_children_related(self, rating_key='', title='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_item_children_related(rating_key=rating_key)

        if result:
            return serve_template(template_name="info_collection_list.html", data=result, title=title)
        else:
            return serve_template(template_name="info_collection_list.html", data=None, title=title)

    @cherrypy.expose
    @requireAuth()
    def item_watch_time_stats(self, rating_key=None, guid=None, media_type=None, **kwargs):
        if rating_key or guid:
            item_data = datafactory.DataFactory()
            result = item_data.get_watch_time_stats(rating_key=rating_key, guid=guid, media_type=media_type)
        else:
            result = None

        if result:
            return serve_template(template_name="user_watch_time_stats.html", data=result, title="Watch Stats")
        else:
            logger.warn("Unable to retrieve data for item_watch_time_stats.")
            return serve_template(template_name="user_watch_time_stats.html", data=None, title="Watch Stats")

    @cherrypy.expose
    @requireAuth()
    def item_user_stats(self, rating_key=None, guid=None, media_type=None, **kwargs):
        if rating_key or guid:
            item_data = datafactory.DataFactory()
            result = item_data.get_user_stats(rating_key=rating_key, guid=guid, media_type=media_type)
        else:
            result = None

        if result:
            return serve_template(template_name="library_user_stats.html", data=result, title="Player Stats")
        else:
            logger.warn("Unable to retrieve data for item_user_stats.")
            return serve_template(template_name="library_user_stats.html", data=None, title="Player Stats")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_item_watch_time_stats(self, rating_key=None, media_type=None, grouping=None, query_days=None, **kwargs):
        """  Get the watch time stats for the media item.

            ```
            Required parameters:
                rating_key (str):       Rating key of the item

            Optional parameters:
                media_type (str):       Media type of the item (only required for a collection)
                grouping (int):         0 or 1
                query_days (str):       Comma separated days, e.g. "1,7,30,0"

            Returns:
                json:
                    [
                        {
                            "query_days": 1,
                            "total_time": 0,
                            "total_plays": 0
                        },
                        {
                            "query_days": 7,
                            "total_time": 0,
                            "total_plays": 0
                        },
                        {
                            "query_days": 30,
                            "total_time": 0,
                            "total_plays": 0
                        },
                        {
                            "query_days": 0,
                            "total_time": 57776,
                            "total_plays": 13
                        }
                    ]
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        if rating_key:
            item_data = datafactory.DataFactory()
            result = item_data.get_watch_time_stats(rating_key=rating_key,
                                                    media_type=media_type,
                                                    grouping=grouping,
                                                    query_days=query_days)
            if result:
                return result
            else:
                logger.warn("Unable to retrieve data for get_item_watch_time_stats.")
                return result
        else:
            logger.warn("Item watch time stats requested but no rating_key received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_item_user_stats(self, rating_key=None, media_type=None, grouping=None, **kwargs):
        """  Get the user stats for the media item.

            ```
            Required parameters:
                rating_key (str):       Rating key of the item

            Optional parameters:
                media_type (str):       Media type of the item (only required for a collection)
                grouping (int):         0 or 1

            Returns:
                json:
                    [
                        {
                            "friendly_name": "Jon Snow",
                            "user_id": 1601089,
                            "user_thumb": "",
                            "username": "jsnow@thewinteriscoming.com",
                            "total_plays": 6,
                            "total_time": 28743
                        },
                        {
                            "friendly_name": "DanyKhaleesi69",
                            "user_id": 8008135,
                            "user_thumb": "",
                            "username": "DanyKhaleesi69",
                            "total_plays": 5,
                            "total_time": 18583
                        }
                    ]
            ```
        """
        grouping = helpers.bool_true(grouping, return_none=True)

        if rating_key:
            item_data = datafactory.DataFactory()
            result = item_data.get_user_stats(rating_key=rating_key,
                                              media_type=media_type,
                                              grouping=grouping)
            if result:
                return result
            else:
                logger.warn("Unable to retrieve data for get_item_user_stats.")
                return result
        else:
            logger.warn("Item user stats requested but no rating_key received.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_children_metadata")
    def get_children_metadata_details(self, rating_key='', media_type=None, **kwargs):
        """ Get the metadata for the children of a media item.

            ```
            Required parameters:
                rating_key (str):       Rating key of the item
                media_type (str):       Media type of the item

            Optional parameters:
                None

            Returns:
                json:
                    {"children_count": 9,
                     "children_type": "season",
                     "title": "Game of Thrones",
                     "children_list": [
                         {...},
                         {"actors": [],
                          "added_at": "1403553078",
                          "art": "/library/metadata/1219/art/1562110346",
                          "audience_rating": "",
                          "audience_rating_image": "",
                          "banner": "",
                          "collections": [],
                          "content_rating": "",
                          "directors": [],
                          "duration": "",
                          "full_title": "Season 1"
                          "genres": [],
                          "grandparent_rating_key": "",
                          "grandparent_thumb": "",
                          "grandparent_title": "",
                          "guid": "com.plexapp.agents.thetvdb://121361/1?lang=en",
                          "labels": [],
                          "last_viewed_at": "1589992348",
                          "library_name": "TV Shows",
                          "media_index": "1",
                          "media_type": "season",
                          "original_title": "",
                          "originally_available_at": "",
                          "parent_media_index": "1",
                          "parent_rating_key": "1219",
                          "parent_thumb": "/library/metadata/1219/thumb/1562110346",
                          "parent_title": "Game of Thrones",
                          "rating": "",
                          "rating_image": "",
                          "rating_key": "1220",
                          "section_id": "2",
                          "sort_title": "",
                          "studio": "",
                          "summary": "",
                          "tagline": "",
                          "thumb": "/library/metadata/1220/thumb/1602176313",
                          "title": "Season 1",
                          "updated_at": "1602176313",
                          "user_rating": "",
                          "writers": [],
                          "year": ""
                          },
                          {...},
                          {...}
                         ]
                     }
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        metadata = pms_connect.get_item_children(rating_key=rating_key,
                                                 media_type=media_type)

        if metadata:
            return metadata
        else:
            logger.warn("Unable to retrieve data for get_children_metadata_details.")
            return metadata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi('notify_recently_added')
    def send_manual_on_created(self, notifier_id='', rating_key='', **kwargs):
        """ Send a recently added notification using Tautulli.

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
    def pms_image_proxy(self, **kwargs):
        """ See real_pms_image_proxy docs string"""

        refresh = False
        if kwargs.get('refresh') or 'no-cache' in cherrypy.request.headers.get('Cache-Control', ''):
            refresh = False if get_session_user_id() else True

        kwargs['refresh'] = refresh

        return self.real_pms_image_proxy(**kwargs)

    @addtoapi('pms_image_proxy')
    def real_pms_image_proxy(self, img=None, rating_key=None, width=750, height=1000,
                             opacity=100, background='000000', blur=0, img_format='png',
                             fallback=None, refresh=False, clip=False, **kwargs):
        """ Gets an image from the PMS and saves it to the image cache directory.

            ```
            Required parameters:
                img (str):              /library/metadata/153037/thumb/1462175060
                or
                rating_key (str):       54321

            Optional parameters:
                width (str):            300
                height (str):           450
                opacity (str):          25
                background (str):       Hex color, e.g. 282828
                blur (str):             3
                img_format (str):       png
                fallback (str):         "poster", "cover", "art", "poster-live", "art-live", "art-live-full", "user"
                refresh (bool):         True or False whether to refresh the image cache
                return_hash (bool):     True or False to return the self-hosted image hash instead of the image

            Returns:
                None
            ```
        """
        cherrypy.response.headers['Cache-Control'] = 'max-age=2592000'  # 30 days

        if isinstance(img, str) and img.startswith('interfaces/default/images'):
            fp = os.path.join(plexpy.PROG_DIR, 'data', img)
            return serve_file(path=fp, content_type='image/png')

        if not img and not rating_key:
            if fallback in common.DEFAULT_IMAGES:
                fbi = common.DEFAULT_IMAGES[fallback]
                fp = os.path.join(plexpy.PROG_DIR, 'data', fbi)
                return serve_file(path=fp, content_type='image/png')
            logger.warn('No image input received.')
            return

        return_hash = helpers.bool_true(kwargs.get('return_hash'))

        if rating_key and not img:
            if fallback and fallback.startswith('art'):
                img = '/library/metadata/{}/art'.format(rating_key)
            else:
                img = '/library/metadata/{}/thumb'.format(rating_key)

        if img and not img.startswith('http'):
            parts = 5
            if img.startswith('/playlists'):
                parts -= 1
            rating_key_idx = parts - 2
            parts += int('composite' in img)
            img_split = img.split('/')
            img = '/'.join(img_split[:parts])
            img_rating_key = img_split[rating_key_idx]
            if rating_key != img_rating_key:
                rating_key = img_rating_key

        img_hash = notification_handler.set_hash_image_info(
            img=img, rating_key=rating_key, width=width, height=height,
            opacity=opacity, background=background, blur=blur, fallback=fallback,
            add_to_db=return_hash)

        if return_hash:
            return {'img_hash': img_hash}

        fp = '{}.{}'.format(img_hash, img_format)  # we want to be able to preview the thumbs
        c_dir = os.path.join(plexpy.CONFIG.CACHE_DIR, 'images')
        ffp = os.path.join(c_dir, fp)

        if not os.path.exists(c_dir):
            os.mkdir(c_dir)

        clip = helpers.bool_true(clip)

        try:
            if not plexpy.CONFIG.CACHE_IMAGES or refresh or 'indexes' in img:
                raise NotFound

            return serve_file(path=ffp, content_type='image/png')

        except NotFound:
            # the image does not exist, download it from pms
            try:
                pms_connect = pmsconnect.PmsConnect()
                pms_connect.request_handler._silent = True
                result = pms_connect.get_image(img=img,
                                               width=width,
                                               height=height,
                                               opacity=opacity,
                                               background=background,
                                               blur=blur,
                                               img_format=img_format,
                                               clip=clip,
                                               refresh=refresh)

                if result and result[0]:
                    cherrypy.response.headers['Content-type'] = result[1]
                    if plexpy.CONFIG.CACHE_IMAGES and 'indexes' not in img:
                        with open(ffp, 'wb') as f:
                            f.write(result[0])

                    return result[0]
                else:
                    raise Exception('PMS image request failed')

            except Exception as e:
                logger.warn("Failed to get image %s, falling back to %s." % (img, fallback))
                cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
                if fallback in common.DEFAULT_IMAGES:
                    fbi = common.DEFAULT_IMAGES[fallback]
                    fp = os.path.join(plexpy.PROG_DIR, 'data', fbi)
                    return serve_file(path=fp, content_type='image/png')
                elif fallback:
                    return self.real_pms_image_proxy(
                        img=fallback, rating_key=None, width=width, height=height,
                        opacity=opacity, background=background, blur=blur, img_format=img_format,
                        fallback=None, refresh=refresh, clip=clip, **kwargs)

    @cherrypy.expose
    def image(self, *args, **kwargs):
        if args:
            cherrypy.response.headers['Cache-Control'] = 'max-age=3600'  # 1 hour

            if len(args) >= 2 and args[0] == 'images':
                resource_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/default/')
                try:
                    return serve_file(path=os.path.join(resource_dir, *args), content_type='image/png')
                except NotFound:
                    return

            img_hash = args[0].split('.')[0]

            if img_hash in common.DEFAULT_IMAGES:
                fbi = common.DEFAULT_IMAGES[img_hash]
                fp = os.path.join(plexpy.PROG_DIR, 'data', fbi)
                return serve_file(path=fp, content_type='image/png')

            img_info = notification_handler.get_hash_image_info(img_hash=img_hash)

            if img_info:
                kwargs.update(img_info)
                return self.real_pms_image_proxy(refresh=True, **kwargs)

        return

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_config(self, **kwargs):
        """ Download the Tautulli configuration file. """
        config_file = config.FILENAME
        config_copy = os.path.join(plexpy.CONFIG.CACHE_DIR, config_file)

        try:
            plexpy.CONFIG.write()
            shutil.copyfile(plexpy.CONFIG_FILE, config_copy)
        except:
            pass

        try:
            cfg = config.Config(config_copy)
            for key in config._DO_NOT_DOWNLOAD_KEYS:
                setattr(cfg, key, '')
            cfg.write()
        except:
            cherrypy.response.status = 500
            return 'Error downloading config. Check the logs.'

        return serve_download(config_copy, name=config_file)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_database(self, **kwargs):
        """ Download the Tautulli database file. """
        database_file = database.FILENAME
        database_copy = os.path.join(plexpy.CONFIG.CACHE_DIR, database_file)

        try:
            db = database.MonitorDatabase()
            db.connection.execute('begin immediate')
            shutil.copyfile(plexpy.DB_FILE, database_copy)
            db.connection.rollback()
        except:
            pass

        # Remove tokens
        db = database.MonitorDatabase(database_copy)
        try:
            db.action('UPDATE users SET user_token = NULL, server_token = NULL')
        except:
            logger.error('Failed to remove tokens from downloaded database.')
            cherrypy.response.status = 500
            return 'Error downloading database. Check the logs.'

        return serve_download(database_copy, name=database_file)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_log(self, logfile='', **kwargs):
        """ Download the Tautulli log file.

            ```
            Required parameters:
                None

            Optional parameters:
                logfile (str):          The name of the Tautulli log file,
                                        "tautulli", "tautulli_api", "plex_websocket"

            Returns:
                download
            ```
        """
        if logfile == "tautulli_api":
            filename = logger.FILENAME_API
            log = logger.logger_api
        elif logfile == "plex_websocket":
            filename = logger.FILENAME_PLEX_WEBSOCKET
            log = logger.logger_plex_websocket
        else:
            filename = logger.FILENAME
            log = logger.logger

        try:
            log.flush()
        except:
            pass

        return serve_download(os.path.join(plexpy.CONFIG.LOG_DIR, filename), name=filename)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_plex_log(self, logfile='', **kwargs):
        """ Download the Plex log file.

            ```
            Required parameters:
                None

            Optional parameters:
                logfile (int):          The name of the Plex log file,
                                        e.g. "Plex Media Server", "Plex Media Scanner"

            Returns:
                download
            ```
        """
        if not plexpy.CONFIG.PMS_LOGS_FOLDER:
            return "Plex log folder not set in the settings."

        if kwargs.get('log_type'):
            logfile = 'Plex Media ' + kwargs['log_type'].capitalize()

        log_file = (logfile or 'Plex Media Server') + '.log'
        log_file_path = os.path.join(plexpy.CONFIG.PMS_LOGS_FOLDER, log_file)

        if log_file and os.path.isfile(log_file_path):
            log_file_name = os.path.basename(log_file_path)
            return serve_download(log_file_path, name=log_file_name)
        else:
            return "Plex log file '%s' not found." % log_file

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
            logger.exception('Failed to delete %s: %s.' % (cache_dir, e))
            return {'result': result, 'message': msg}

        try:
            os.makedirs(cache_dir)
        except OSError as e:
            result = 'error'
            msg = 'Failed to make %s.' % cache_dir
            logger.exception('Failed to create %s: %s.' % (cache_dir, e))
            return {'result': result, 'message': msg}

        logger.info(msg)
        return {'result': result, 'message': msg}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_hosted_images(self, rating_key='', service='', delete_all=False, **kwargs):
        """ Delete the images uploaded to image hosting services.

            ```
            Required parameters:
                None

            Optional parameters:
                rating_key (int):       1234
                                        (Note: Must be the movie, show, season, artist, or album rating key)
                service (str):          'imgur' or 'cloudinary'
                delete_all (bool):      'true' to delete all images form the service

            Returns:
                json:
                    {"result": "success",
                     "message": "Deleted hosted images from Imgur."}
            ```
        """

        delete_all = helpers.bool_true(delete_all)

        data_factory = datafactory.DataFactory()
        result = data_factory.delete_img_info(rating_key=rating_key, service=service, delete_all=delete_all)

        if result:
            return {'result': 'success', 'message': 'Deleted hosted images from %s.' % result.capitalize()}
        else:
            return {'result': 'error', 'message': 'Failed to delete hosted images.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_lookup_info(self, rating_key='', service='', delete_all=False, **kwargs):
        """ Delete the 3rd party API lookup info.

            ```
            Required parameters:
                None

            Optional parameters:
                rating_key (int):       1234
                                        (Note: Must be the movie, show, artist, album, or track rating key)
                service (str):          'themoviedb' or 'tvmaze' or 'musicbrainz'
                delete_all (bool):      'true' to delete all images form the service

            Returns:
                json:
                    {"result": "success",
                     "message": "Deleted lookup info."}
            ```
        """

        data_factory = datafactory.DataFactory()
        result = data_factory.delete_lookup_info(rating_key=rating_key, service=service, delete_all=delete_all)

        if result:
            return {'result': 'success', 'message': 'Deleted lookup info.'}
        else:
            return {'result': 'error', 'message': 'Failed to delete lookup info.'}


    ##### Search #####

    @cherrypy.expose
    @requireAuth()
    def search(self, query='', **kwargs):
        return serve_template(template_name="search.html", title="Search", query=query)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi('search')
    def search_results(self, query='', limit='', **kwargs):
        """ Get search results from the PMS.

            ```
            Required parameters:
                query (str):        The query string to search for

            Optional parameters:
                limit (int):        The maximum number of items to return per media type

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
        result = pms_connect.get_search_results(query=query, limit=limit)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for search_results.")
            return result

    @cherrypy.expose
    @requireAuth()
    def get_search_results_children(self, query='', limit='', media_type=None, season_index=None, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_search_results(query=query, limit=limit)

        if media_type:
            result['results_list'] = {media_type: result['results_list'][media_type]}
        if media_type == 'season' and season_index:
            result['results_list']['season'] = [season for season in result['results_list']['season']
                                                if season['media_index'] == season_index]

        if result:
            return serve_template(template_name="info_search_results_list.html", data=result, title="Search Result List")
        else:
            logger.warn("Unable to retrieve data for get_search_results_children.")
            return serve_template(template_name="info_search_results_list.html", data=None, title="Search Result List")


    ##### Update Metadata #####

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def update_metadata(self, rating_key=None, query=None, update=False, **kwargs):
        query_string = query
        update = helpers.bool_true(update)

        data_factory = datafactory.DataFactory()
        query = data_factory.get_search_query(rating_key=rating_key)
        if query and query_string:
            query['query_string'] = query_string

        if query:
            return serve_template(template_name="update_metadata.html", query=query, update=update, title="Info")
        else:
            logger.warn("Unable to retrieve data for update_metadata.")
            return serve_template(template_name="update_metadata.html", query=query, update=update, title="Info")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def update_metadata_details(self, old_rating_key, new_rating_key, media_type, single_update=False, **kwargs):
        """ Update the metadata in the Tautulli database by matching rating keys.
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
        single_update = helpers.bool_true(single_update)

        if new_rating_key:
            data_factory = datafactory.DataFactory()
            pms_connect = pmsconnect.PmsConnect()

            old_key_list = data_factory.get_rating_keys_list(rating_key=old_rating_key, media_type=media_type)
            new_key_list = pms_connect.get_rating_keys_list(rating_key=new_rating_key, media_type=media_type)

            result = data_factory.update_metadata(old_key_list=old_key_list,
                                                  new_key_list=new_key_list,
                                                  media_type=media_type,
                                                  single_update=single_update)

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
            logger.warn("Unable to retrieve data for get_new_rating_keys.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_old_rating_keys(self, rating_key='', media_type='', **kwargs):
        """ Get a list of old rating keys from the Tautulli database for all of the item's parent/children.

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
            logger.warn("Unable to retrieve data for get_old_rating_keys.")
            return result

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
            logger.warn("Unable to retrieve data for get_pms_sessions_json.")
            return False

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_metadata")
    def get_metadata_details(self, rating_key='', sync_id='', **kwargs):
        """ Get the metadata for a media item.

            ```
            Required parameters:
                rating_key (str):       Rating key of the item, OR
                sync_id (str):          Sync ID of a synced item

            Optional parameters:
                None

            Returns:
                json:
                    {"actors": [
                        "Emilia Clarke",
                        "Lena Headey",
                        "Sophie Turner",
                        "Kit Harington",
                        "Peter Dinklage",
                        "Nikolaj Coster-Waldau",
                        "Maisie Williams",
                        "Iain Glen",
                        "John Bradley",
                        "Alfie Allen"
                     ],
                     "added_at": "1461572396",
                     "art": "/library/metadata/1219/art/1462175063",
                     "audience_rating": "7.4",
                     "audience_rating_image": "themoviedb://image.rating",
                     "banner": "/library/metadata/1219/banner/1462175063",
                     "collections": [],
                     "content_rating": "TV-MA",
                     "directors": [
                        "Jeremy Podeswa"
                     ],
                     "duration": "2998290",
                     "edition_title": "",
                     "full_title": "Game of Thrones - The Red Woman",
                     "genres": [
                        "Action/Adventure",
                        "Drama",
                        "Fantasy",
                        "Romance"
                     ],
                     "grandparent_guid": "plex://show/5d9c086c46115600200aa2fe",
                     "grandparent_guids": [
                         "imdb://tt0944947",
                         "tmdb://1399",
                         "tvdb://121361"
                     ],
                     "grandparent_rating_key": "1219",
                     "grandparent_slug": "game-of-thrones",
                     "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
                     "grandparent_title": "Game of Thrones",
                     "grandparent_year": "2011",
                     "guid": "plex://episode/5d9c1276e9d5a1001f4ff2fa",
                     "guids": [
                         "imdb://tt3658014",
                         "tmdb://1156503",
                         "tvdb://5469015"
                     ],
                     "labels": [],
                     "last_viewed_at": "1462165717",
                     "library_name": "TV Shows",
                     "live": 0,
                     "markers": [
                        {
                             "id": 908,
                             "type": "credits",
                             "start_time_offset": 2923863,
                             "end_time_offset": 2998197,
                             "first": true,
                             "final": true
                        },
                        {
                             "id": 908,
                             "type": "intro",
                             "start_time_offset": 1622,
                             "end_time_offset": 109135,
                             "first": null,
                             "final": null
                        }
                     ],
                     "media_index": "1",
                     "media_info": [
                         {
                             "aspect_ratio": "1.78",
                             "audio_channel_layout": "5.1",
                             "audio_channels": "6",
                             "audio_codec": "ac3",
                             "audio_profile": "",
                             "bitrate": "10617",
                             "channel_call_sign": "",
                             "channel_id": "",
                             "channel_identifier": "",
                             "channel_title": "",
                             "channel_thumb": "",
                             "channel_vcn": "",
                             "container": "mkv",
                             "height": "1078",
                             "id": "257925",
                             "optimized_version": 0,
                             "parts": [
                                 {
                                     "file": "/media/TV Shows/Game of Thrones/Season 06/Game of Thrones - S06E01 - The Red Woman.mkv",
                                     "file_size": "3979115377",
                                     "id": "274169",
                                     "indexes": 1,
                                     "streams": [
                                         {
                                             "id": "511663",
                                             "type": "1",
                                             "video_bit_depth": "8",
                                             "video_bitrate": "10233",
                                             "video_codec": "h264",
                                             "video_codec_level": "41",
                                             "video_color_primaries": "",
                                             "video_color_range": "tv",
                                             "video_color_space": "bt709",
                                             "video_color_trc": "",
                                             "video_dynamic_range": "SDR",
                                             "video_dovi_bl_present": 0,
                                             "video_dovi_el_present": 0,
                                             "video_dovi_level": 0,
                                             "video_dovi_present": 0,
                                             "video_dovi_profile": 0,
                                             "video_dovi_rpu_present": 0,
                                             "video_dovi_version": 0,
                                             "video_frame_rate": "23.976",
                                             "video_height": "1078",
                                             "video_language": "",
                                             "video_language_code": "",
                                             "video_profile": "high",
                                             "video_ref_frames": "4",
                                             "video_scan_type": "progressive",
                                             "video_width": "1920",
                                             "selected": 0
                                         },
                                         {
                                             "audio_bitrate": "384",
                                             "audio_bitrate_mode": "",
                                             "audio_channel_layout": "5.1(side)",
                                             "audio_channels": "6",
                                             "audio_codec": "ac3",
                                             "audio_language": "",
                                             "audio_language_code": "",
                                             "audio_profile": "",
                                             "audio_sample_rate": "48000",
                                             "id": "511664",
                                             "type": "2",
                                             "selected": 1
                                         },
                                         {
                                             "id": "511953",
                                             "subtitle_codec": "srt",
                                             "subtitle_container": "",
                                             "subtitle_forced": 0,
                                             "subtitle_format": "srt",
                                             "subtitle_language": "English",
                                             "subtitle_language_code": "eng",
                                             "subtitle_location": "external",
                                             "type": "3",
                                             "selected": 1
                                         }
                                     ]
                                 }
                             ],
                             "video_codec": "h264",
                             "video_framerate": "24p",
                             "video_full_resolution": "1080p",
                             "video_profile": "high",
                             "video_resolution": "1080",
                             "width": "1920"
                         }
                     ],
                     "media_type": "episode",
                     "original_title": "",
                     "originally_available_at": "2016-04-24",
                     "parent_guid": "plex://season/602e67e61d3358002c4120f7",
                     "parent_guids": [
                         "tvdb://651357"
                     ],
                     "parent_media_index": "6",
                     "parent_rating_key": "153036",
                     "parent_slug": "game-of-thrones",
                     "parent_thumb": "/library/metadata/153036/thumb/1462175062",
                     "parent_title": "Season 6",
                     "parent_year": "2016",
                     "rating": "",
                     "rating_image": "",
                     "rating_key": "153037",
                     "section_id": "2",
                     "slug": "game-of-thrones",
                     "sort_title": "Red Woman",
                     "studio": "Revolution Sun Studios",
                     "summary": "The fate of Jon Snow is revealed. Daenerys meets a strong man. Cersei sees her daughter once again.",
                     "tagline": "",
                     "thumb": "/library/metadata/153037/thumb/1462175060",
                     "title": "The Red Woman",
                     "updated_at": "1462175060",
                     "user_rating": "9.0",
                     "writers": [
                        "David Benioff",
                        "D. B. Weiss"
                     ],
                     "year": "2016"
                     }
            ```
        """
        pms_connect = pmsconnect.PmsConnect()
        metadata = pms_connect.get_metadata_details(rating_key=rating_key,
                                                    sync_id=sync_id)

        if metadata:
            return metadata
        else:
            logger.warn("Unable to retrieve data for get_metadata_details.")
            return metadata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_recently_added")
    def get_recently_added_details(self, start='0', count='0', media_type='', section_id='', **kwargs):
        """ Get all items that where recently added to plex.

            ```
            Required parameters:
                count (str):        Number of items to return

            Optional parameters:
                start (str):        The item number to start at
                media_type (str):   The media type: movie, show, artist
                section_id (str):   The id of the Plex library section

            Returns:
                json:
                    {"recently_added":
                        [{"actors": [
                             "Kit Harington",
                             "Emilia Clarke",
                             "Isaac Hempstead-Wright",
                             "Maisie Williams",
                             "Liam Cunningham",
                          ],
                          "added_at": "1461572396",
                          "art": "/library/metadata/1219/art/1462175063",
                          "audience_rating": "8",
                          "audience_rating_image": "rottentomatoes://image.rating.upright",
                          "banner": "/library/metadata/1219/banner/1462175063",
                          "directors": [
                             "Jeremy Podeswa"
                          ],
                          "duration": "2998290",
                          "full_title": "Game of Thrones - The Red Woman",
                          "genres": [
                             "Adventure",
                             "Drama",
                             "Fantasy"
                          ],
                          "grandparent_rating_key": "1219",
                          "grandparent_thumb": "/library/metadata/1219/thumb/1462175063",
                          "grandparent_title": "Game of Thrones",
                          "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                          "guids": [],
                          "labels": [],
                          "last_viewed_at": "1462165717",
                          "library_name": "TV Shows",
                          "media_index": "1",
                          "media_type": "episode",
                          "original_title": "",
                          "originally_available_at": "2016-04-24",
                          "parent_media_index": "6",
                          "parent_rating_key": "153036",
                          "parent_thumb": "/library/metadata/153036/thumb/1462175062",
                          "parent_title": "",
                          "rating": "7.8",
                          "rating_image": "rottentomatoes://image.rating.ripe",
                          "rating_key": "153037",
                          "section_id": "2",
                          "sort_title": "Red Woman",
                          "studio": "HBO",
                          "summary": "Jon Snow is dead. Daenerys meets a strong man. Cersei sees her daughter again.",
                          "tagline": "",
                          "thumb": "/library/metadata/153037/thumb/1462175060",
                          "title": "The Red Woman",
                          "user_rating": "9.0",
                          "updated_at": "1462175060",
                          "writers": [
                             "David Benioff",
                             "D. B. Weiss"
                          ],
                          "year": "2016"
                          },
                         {...},
                         {...}
                         ]
                     }
            ```
        """
        # For backwards compatibility
        if 'type' in kwargs:
            media_type = kwargs['type']

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_recently_added_details(start=start, count=count, media_type=media_type, section_id=section_id)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_recently_added_details.")
            return result

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
            logger.warn("Unable to retrieve data for get_friends_list.")

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
            logger.warn("Unable to retrieve data for get_user_details.")

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
            logger.warn("Unable to retrieve data for get_server_list.")

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
            logger.warn("Unable to retrieve data for get_sync_lists.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def get_servers(self, **kwargs):
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_list(output_format='json')

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_servers.")

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
            logger.warn("Unable to retrieve data for get_servers_info.")
            return result

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
            logger.warn("Unable to retrieve data for get_server_identity.")
            return result

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
            logger.warn("Unable to retrieve data for get_server_friendly_name.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_activity(self, session_key=None, session_id=None, **kwargs):
        """ Get the current activity on the PMS.

            ```
            Required parameters:
                None

            Optional parameters:
                session_key (int):    Session key for the session info to return, OR
                session_id (str):     Session ID for the session info to return

            Returns:
                json:
                    {"lan_bandwidth": 25318,
                     "sessions": [
                         {
                             "actors": [
                                 "Kit Harington",
                                 "Emilia Clarke",
                                 "Isaac Hempstead-Wright",
                                 "Maisie Williams",
                                 "Liam Cunningham",
                             ],
                             "added_at": "1461572396",
                             "allow_guest": 1,
                             "art": "/library/metadata/1219/art/1503306930",
                             "aspect_ratio": "1.78",
                             "audience_rating": "",
                             "audience_rating_image": "rottentomatoes://image.rating.upright",
                             "audio_bitrate": "384",
                             "audio_bitrate_mode": "",
                             "audio_channel_layout": "5.1(side)",
                             "audio_channels": "6",
                             "audio_codec": "ac3",
                             "audio_decision": "direct play",
                             "audio_language": "",
                             "audio_language_code": "",
                             "audio_profile": "",
                             "audio_sample_rate": "48000",
                             "bandwidth": "25318",
                             "banner": "/library/metadata/1219/banner/1503306930",
                             "bif_thumb": "/library/parts/274169/indexes/sd/1000",
                             "bitrate": "10617",
                             "channel_call_sign": "",
                             "channel_id": "",
                             "channel_identifier": "",
                             "channel_stream": 0,
                             "channel_title": "",
                             "channel_thumb": "",
                             "channel_vcn": "",
                             "children_count": "",
                             "collections": [],
                             "container": "mkv",
                             "container_decision": "direct play",
                             "content_rating": "TV-MA",
                             "deleted_user": 0,
                             "device": "Windows",
                             "directors": [
                                 "Jeremy Podeswa"
                             ],
                             "do_notify": 0,
                             "duration": "2998272",
                             "email": "Jon.Snow.1337@CastleBlack.com",
                             "file": "/media/TV Shows/Game of Thrones/Season 06/Game of Thrones - S06E01 - The Red Woman.mkv",
                             "file_size": "3979115377",
                             "friendly_name": "Jon Snow",
                             "full_title": "Game of Thrones - The Red Woman",
                             "genres": [
                                 "Adventure",
                                 "Drama",
                                 "Fantasy"
                             ],
                             "grandparent_guid": "com.plexapp.agents.thetvdb://121361?lang=en",
                             "grandparent_rating_key": "1219",
                             "grandparent_thumb": "/library/metadata/1219/thumb/1503306930",
                             "grandparent_title": "Game of Thrones",
                             "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                             "height": "1078",
                             "id": "",
                             "indexes": 1,
                             "ip_address": "10.10.10.1",
                             "ip_address_public": "64.123.23.111",
                             "is_admin": 1,
                             "is_allow_sync": 1,
                             "is_home_user": 1,
                             "is_restricted": 0,
                             "keep_history": 1,
                             "labels": [],
                             "last_viewed_at": "1462165717",
                             "library_name": "TV Shows",
                             "live": 0,
                             "live_uuid": "",
                             "local": "1",
                             "location": "lan",
                             "machine_id": "lmd93nkn12k29j2lnm",
                             "media_index": "1",
                             "media_type": "episode",
                             "optimized_version": 0,
                             "optimized_version_profile": "",
                             "optimized_version_title": "",
                             "original_title": "",
                             "originally_available_at": "2016-04-24",
                             "parent_guid": "com.plexapp.agents.thetvdb://121361/6?lang=en",
                             "parent_media_index": "6",
                             "parent_rating_key": "153036",
                             "parent_thumb": "/library/metadata/153036/thumb/1503889210",
                             "parent_title": "Season 6",
                             "platform": "Plex Media Player",
                             "platform_name": "plex",
                             "platform_version": "2.4.1.787-54a020cd",
                             "player": "Castle-PC",
                             "product": "Plex Media Player",
                             "product_version": "3.35.2",
                             "profile": "Konvergo",
                             "progress_percent": "0",
                             "quality_profile": "Original",
                             "rating": "7.8",
                             "rating_image": "rottentomatoes://image.rating.ripe",
                             "rating_key": "153037",
                             "relay": 0,
                             "section_id": "2",
                             "secure": 1,
                             "session_id": "helf15l3rxgw01xxe0jf3l3d",
                             "session_key": "27",
                             "shared_libraries": [
                                 "10",
                                 "1",
                                 "4",
                                 "5",
                                 "15",
                                 "20",
                                 "2"
                             ],
                             "sort_title": "Red Woman",
                             "state": "playing",
                             "stream_aspect_ratio": "1.78",
                             "stream_audio_bitrate": "384",
                             "stream_audio_bitrate_mode": "",
                             "stream_audio_channel_layout": "5.1(side)",
                             "stream_audio_channel_layout_": "5.1(side)",
                             "stream_audio_channels": "6",
                             "stream_audio_codec": "ac3",
                             "stream_audio_decision": "direct play",
                             "stream_audio_language": "",
                             "stream_audio_language_code": "",
                             "stream_audio_profile": "",
                             "stream_audio_sample_rate": "48000",
                             "stream_bitrate": "10617",
                             "stream_container": "mkv",
                             "stream_container_decision": "direct play",
                             "stream_duration": "2998272",
                             "stream_subtitle_codec": "",
                             "stream_subtitle_container": "",
                             "stream_subtitle_decision": "",
                             "stream_subtitle_forced": 0,
                             "stream_subtitle_format": "",
                             "stream_subtitle_language": "",
                             "stream_subtitle_language_code": "",
                             "stream_subtitle_location": "",
                             "stream_video_bit_depth": "8",
                             "stream_video_bitrate": "10233",
                             "stream_video_chroma_subsampling": "4:2:0",
                             "stream_video_codec": "h264",
                             "stream_video_codec_level": "41",
                             "stream_video_color_primaries": "",
                             "stream_video_color_range": "tv",
                             "stream_video_color_space": "bt709",
                             "stream_video_color_trc": "",
                             "stream_video_decision": "direct play",
                             "stream_video_dynamic_range": "SDR",
                             "stream_video_framerate": "24p",
                             "stream_video_full_resolution": "1080p",
                             "stream_video_height": "1078",
                             "stream_video_language": "",
                             "stream_video_language_code": "",
                             "stream_video_ref_frames": "4",
                             "stream_video_resolution": "1080",
                             "stream_video_scan_type": "progressive",
                             "stream_video_width": "1920",
                             "studio": "HBO",
                             "subtitle_codec": "",
                             "subtitle_container": "",
                             "subtitle_decision": "",
                             "subtitle_forced": 0,
                             "subtitle_format": "",
                             "subtitle_language": "",
                             "subtitle_language_code": "",
                             "subtitle_location": "",
                             "subtitles": 0,
                             "summary": "Jon Snow is dead. Daenerys meets a strong man. Cersei sees her daughter again.",
                             "synced_version": 0,
                             "synced_version_profile": "",
                             "tagline": "",
                             "throttled": "0",
                             "thumb": "/library/metadata/153037/thumb/1503889207",
                             "title": "The Red Woman",
                             "transcode_audio_channels": "",
                             "transcode_audio_codec": "",
                             "transcode_container": "",
                             "transcode_decision": "direct play",
                             "transcode_height": "",
                             "transcode_hw_decode": "",
                             "transcode_hw_decode_title": "",
                             "transcode_hw_decoding": 0,
                             "transcode_hw_encode": "",
                             "transcode_hw_encode_title": "",
                             "transcode_hw_encoding": 0,
                             "transcode_hw_full_pipeline": 0,
                             "transcode_hw_requested": 0,
                             "transcode_key": "",
                             "transcode_max_offset_available": 0,
                             "transcode_min_offset_available": 0,
                             "transcode_progress": 0,
                             "transcode_protocol": "",
                             "transcode_speed": "",
                             "transcode_throttled": 0,
                             "transcode_video_codec": "",
                             "transcode_width": "",
                             "type": "",
                             "updated_at": "1503889207",
                             "user": "LordCommanderSnow",
                             "user_id": 133788,
                             "user_rating": "",
                             "user_thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
                             "username": "LordCommanderSnow",
                             "video_bit_depth": "8",
                             "video_bitrate": "10233",
                             "video_chroma_subsampling": "4:2:0",
                             "video_codec": "h264",
                             "video_codec_level": "41",
                             "video_color_primaries": "",
                             "video_color_range": "tv",
                             "video_color_space": "bt709",
                             "video_color_trc": ",
                             "video_decision": "direct play",
                             "video_dynamic_range": "SDR",
                             "video_frame_rate": "23.976",
                             "video_framerate": "24p",
                             "video_full_resolution": "1080p",
                             "video_height": "1078",
                             "video_language": "",
                             "video_language_code": "",
                             "video_profile": "high",
                             "video_ref_frames": "4",
                             "video_resolution": "1080",
                             "video_scan_type": "progressive",
                             "video_width": "1920",
                             "view_offset": "1000",
                             "width": "1920",
                             "writers": [
                                 "David Benioff",
                                 "D. B. Weiss"
                             ],
                             "year": "2016"
                         }
                     ],
                     "stream_count": "1",
                     "stream_count_direct_play": 1,
                     "stream_count_direct_stream": 0,
                     "stream_count_transcode": 0,
                     "total_bandwidth": 25318,
                     "wan_bandwidth": 0
                     }
            ```
        """
        try:
            pms_connect = pmsconnect.PmsConnect(token=plexpy.CONFIG.PMS_TOKEN)
            result = pms_connect.get_current_activity()

            if result:
                if session_key:
                    return next((s for s in result['sessions'] if s['session_key'] == session_key), {})
                if session_id:
                    return next((s for s in result['sessions'] if s['session_id'] == session_id), {})

                counts = {'stream_count_direct_play': 0,
                          'stream_count_direct_stream': 0,
                          'stream_count_transcode': 0,
                          'total_bandwidth': 0,
                          'lan_bandwidth': 0,
                          'wan_bandwidth': 0}

                for s in result['sessions']:
                    if s['transcode_decision'] == 'transcode':
                        counts['stream_count_transcode'] += 1
                    elif s['transcode_decision'] == 'copy':
                        counts['stream_count_direct_stream'] += 1
                    else:
                        counts['stream_count_direct_play'] += 1

                    counts['total_bandwidth'] += helpers.cast_to_int(s['bandwidth'])
                    if s['location'] == 'lan':
                        counts['lan_bandwidth'] += helpers.cast_to_int(s['bandwidth'])
                    else:
                        counts['wan_bandwidth'] += helpers.cast_to_int(s['bandwidth'])

                result.update(counts)

                return result
            else:
                logger.warn("Unable to retrieve data for get_activity.")
                return {}
        except Exception as e:
            logger.exception("Unable to retrieve data for get_activity: %s" % e)

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
                      "is_active": 1,
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
            logger.warn("Unable to retrieve data for get_full_libraries_list.")
            return result

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
                    [{"allow_guest": 1,
                      "do_notify": 1,
                      "email": "Jon.Snow.1337@CastleBlack.com",
                      "filter_all": "",
                      "filter_movies": "",
                      "filter_music": "",
                      "filter_photos": "",
                      "filter_tv": "",
                      "is_active": 1,
                      "is_admin": 0,
                      "is_allow_sync": 1,
                      "is_home_user": 1,
                      "is_restricted": 0,
                      "keep_history": 1,
                      "row_id": 1,
                      "shared_libraries": ["1", "2", "3"],
                      "thumb": "https://plex.tv/users/k10w42309cynaopq/avatar",
                      "user_id": "133788",
                      "username": "Jon Snow"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        user_data = users.Users()
        result = user_data.get_users()

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_full_users_list.")
            return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @sanitize_out()
    @addtoapi()
    def get_synced_items(self, machine_id='', user_id='', **kwargs):
        """ Get a list of synced items on the PMS.

            ```
            Required parameters:
                None

            Optional parameters:
                machine_id (str):       The PMS identifier
                user_id (str):          The id of the Plex user

            Returns:
                json:
                    [{"audio_bitrate": "192",
                      "client_id": "95434se643fsf24f-com-plexapp-android",
                      "content_type": "video",
                      "device_name": "Tyrion's iPad",
                      "failure": "",
                      "item_complete_count": "1",
                      "item_count": "1",
                      "item_downloaded_count": "1",
                      "item_downloaded_percent_complete": 100,
                      "metadata_type": "movie",
                      "photo_quality": "74",
                      "platform": "iOS",
                      "rating_key": "154092",
                      "root_title": "Movies",
                      "state": "complete",
                      "sync_id": "11617019",
                      "sync_media_type": null,
                      "sync_title": "Deadpool",
                      "total_size": "560718134",
                      "user": "DrukenDwarfMan",
                      "user_id": "696969",
                      "username": "DrukenDwarfMan",
                      "video_bitrate": "4000"
                      "video_quality": "100"
                      },
                     {...},
                     {...}
                     ]
            ```
        """
        plex_tv = plextv.PlexTV()
        result = plex_tv.get_synced_items(machine_id=machine_id, user_id_filter=user_id)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_synced_items.")
            return result

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
            logger.warn("Unable to retrieve data for get_sync_transcode_queue.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_home_stats(self, grouping=None, time_range=30, stats_type='plays',
                       stats_start=0, stats_count=10, stat_id='',
                       section_id=None, user_id=None, before=None, after=None, **kwargs):
        """ Get the homepage watch statistics.

            ```
            Required parameters:
                None

            Optional parameters:
                grouping (int):         0 or 1
                time_range (int):       The time range to calculate statistics, 30
                stats_type (str):       'plays' or 'duration'
                stats_start (int)       The row number of the stat item to start at, 0
                stats_count (int):      The number of stat items to return, 5
                stat_id (str):          A single stat to return, 'top_movies', 'popular_movies',
                                        'top_tv', 'popular_tv', 'top_music', 'popular_music', 'top_libraries',
                                        'top_users', 'top_platforms', 'last_watched', 'most_concurrent'
                section_id (int):       The id of the Plex library section
                user_id (int):          The id of the Plex user
                before (str):           Stats before and including the date, "YYYY-MM-DD"
                after (str):            Stats after and including the date, "YYYY-MM-DD"

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
                          "guid": "com.plexapp.agents.thetvdb://121361/6/1?lang=en",
                          "labels": [],
                          "last_play": 1462380698,
                          "live": 0,
                          "media_type": "episode",
                          "platform": "",
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
                     {"stat_id": "top_libraries",
                      "stat_type": "total_plays",
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
        # For backwards compatibility
        if stats_type in (0, "0"):
            stats_type = 'plays'
        elif stats_type in (1, '1'):
            stats_type = 'duration'

        grouping = helpers.bool_true(grouping, return_none=True)

        data_factory = datafactory.DataFactory()
        result = data_factory.get_home_stats(grouping=grouping,
                                             time_range=time_range,
                                             stats_type=stats_type,
                                             stats_start=stats_start,
                                             stats_count=stats_count,
                                             stat_id=stat_id,
                                             section_id=section_id,
                                             user_id=user_id,
                                             before=before,
                                             after=after)

        if result:
            return result
        else:
            logger.warn("Unable to retrieve data for get_home_stats.")
            return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi("arnold")
    def random_arnold_quotes(self, **kwargs):
        """ Get to the chopper! """
        import random
        quote_list = ['To crush your enemies, see them driven before you, and to hear the lamentation of their women!',
                      'Your clothes, give them to me, now!',
                      'Do it!',
                      'If it bleeds, we can kill it.',
                      'See you at the party Richter!',
                      'Let off some steam, Bennett.',
                      'I\'ll be back.',
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
                      'You want to be a farmer? Here\'s a couple of acres.',
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
            cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
            return json.dumps(API2()._api_responds(result_type='error',
                                                   msg='Please use the /api/v2 endpoint.')).encode('utf-8')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_tautulli_info(self, **kwargs):
        """ Get info about the Tautulli server.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {"tautulli_install_type": "git",
                     "tautulli_version": "v2.8.1",
                     "tautulli_branch": "master",
                     "tautulli_commit": "2410eb33805aaac4bd1c5dad0f71e4f15afaf742",
                     "tautulli_platform": "Windows",
                     "tautulli_platform_release": "10",
                     "tautulli_platform_version": "10.0.19043",
                     "tautulli_platform_linux_distro": "",
                     "tautulli_platform_device_name": "Winterfell-Server",
                     "tautulli_python_version": "3.10.0"
                     }
            ```
        """
        return plexpy.get_tautulli_info()

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
        result = plex_tv.get_plex_update()
        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth()
    @addtoapi()
    def get_geoip_lookup(self, ip_address='', **kwargs):
        """ Get the geolocation info for an IP address.

            ```
            Required parameters:
                ip_address

            Optional parameters:
                None

            Returns:
                json:
                    {"city": "Mountain View",
                     "code": "US",
                     "continent": "NA",
                     "country": "United States",
                     "latitude": 37.386,
                     "longitude": -122.0838,
                     "postal_code": "94035",
                     "region": "California",
                     "timezone": "America/Los_Angeles",
                     "accuracy": null
                     }
            ```
        """
        message = ''
        if not ip_address:
            message = 'No IP address provided.'
        elif not helpers.is_valid_ip(ip_address):
            message = 'Invalid IP address provided: %s' % ip_address

        if message:
            return {'result': 'error', 'message': message}

        plex_tv = plextv.PlexTV()
        geo_info = plex_tv.get_geoip_lookup(ip_address)
        if geo_info:
            return {'result': 'success', 'data': geo_info}
        return {'result': 'error', 'message': 'Failed to lookup GeoIP info for address: %s' % ip_address}

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
    @requireAuth(member_of("admin"))
    def get_plexpy_url(self, **kwargs):
        return helpers.get_plexpy_url()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_newsletters(self, **kwargs):
        """ Get a list of configured newsletters.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    [{"id": 1,
                      "agent_id": 0,
                      "agent_name": "recently_added",
                      "agent_label": "Recently Added",
                      "friendly_name": "",
                      "cron": "0 0 * * 1",
                      "active": 1
                      }
                     ]
            ```
        """
        result = newsletters.get_newsletters()
        return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_newsletters_table(self, **kwargs):
        result = newsletters.get_newsletters()
        return serve_template(template_name="newsletters_table.html", newsletters_list=result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_newsletter(self, newsletter_id=None, **kwargs):
        """ Remove a newsletter from the database.

            ```
            Required parameters:
                newsletter_id (int):        The newsletter to delete

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        result = newsletters.delete_newsletter(newsletter_id=newsletter_id)
        if result:
            return {'result': 'success', 'message': 'Newsletter deleted successfully.'}
        else:
            return {'result': 'error', 'message': 'Failed to delete newsletter.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_newsletter_config(self, newsletter_id=None, **kwargs):
        """ Get the configuration for an existing notification agent.

            ```
            Required parameters:
                newsletter_id (int):        The newsletter config to retrieve

            Optional parameters:
                None

            Returns:
                json:
                    {"id": 1,
                     "agent_id": 0,
                     "agent_name": "recently_added",
                     "agent_label": "Recently Added",
                     "friendly_name": "",
                     "id_name": "",
                     "cron": "0 0 * * 1",
                     "active": 1,
                     "subject": "Recently Added to {server_name}! ({end_date})",
                     "body": "View the newsletter here: {newsletter_url}",
                     "message": "",
                     "config": {"custom_cron": 0,
                                "filename": "newsletter_{newsletter_uuid}.html",
                                "formatted": 1,
                                "incl_libraries": ["1", "2"],
                                "notifier_id": 1,
                                "save_only": 0,
                                "time_frame": 7,
                                "time_frame_units": "days"
                                },
                     "email_config": {...},
                     "config_options": [{...}, ...],
                     "email_config_options": [{...}, ...]
                     }
            ```
        """
        result = newsletters.get_newsletter_config(newsletter_id=newsletter_id, mask_passwords=True)
        return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def get_newsletter_config_modal(self, newsletter_id=None, **kwargs):
        result = newsletters.get_newsletter_config(newsletter_id=newsletter_id, mask_passwords=True)
        return serve_template(template_name="newsletter_config.html", newsletter=result)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def add_newsletter_config(self, agent_id=None, **kwargs):
        """ Add a new notification agent.

            ```
            Required parameters:
                agent_id (int):           The newsletter type to add

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        result = newsletters.add_newsletter_config(agent_id=agent_id, **kwargs)

        if result:
            return {'result': 'success', 'message': 'Added newsletter.', 'newsletter_id': result}
        else:
            return {'result': 'error', 'message': 'Failed to add newsletter.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def set_newsletter_config(self, newsletter_id=None, agent_id=None, **kwargs):
        """ Configure an existing newsletter agent.

            ```
            Required parameters:
                newsletter_id (int):    The newsletter config to update
                agent_id (int):         The newsletter type of the newsletter

            Optional parameters:
                Pass all the config options for the agent with the 'newsletter_config_' and 'newsletter_email_' prefix.

            Returns:
                None
            ```
        """
        result = newsletters.set_newsletter_config(newsletter_id=newsletter_id,
                                                   agent_id=agent_id,
                                                   **kwargs)

        if result:
            return {'result': 'success', 'message': 'Saved newsletter.'}
        else:
            return {'result': 'error', 'message': 'Failed to save newsletter.'}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    def send_newsletter(self, newsletter_id=None, subject='', body='', message='', notify_action='', **kwargs):
        """ Send a newsletter using Tautulli.

            ```
            Required parameters:
                newsletter_id (int):      The ID number of the newsletter

            Optional parameters:
                None

            Returns:
                None
            ```
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        test = 'test ' if notify_action == 'test' else ''

        if newsletter_id:
            newsletter = newsletters.get_newsletter_config(newsletter_id=newsletter_id)

            if newsletter:
                logger.debug("Sending %s%s newsletter." % (test, newsletter['agent_label']))
                newsletter_handler.add_newsletter_each(newsletter_id=newsletter_id,
                                                       notify_action=notify_action,
                                                       subject=subject,
                                                       body=body,
                                                       message=message,
                                                        **kwargs)
                return {'result': 'success', 'message': 'Newsletter queued.'}
            else:
                logger.debug("Unable to send %snewsletter, invalid newsletter_id %s." % (test, newsletter_id))
                return {'result': 'error', 'message': 'Invalid newsletter id %s.' % newsletter_id}
        else:
            logger.debug("Unable to send %snotification, no newsletter_id received." % test)
            return {'result': 'error', 'message': 'No newsletter id received.'}

    @cherrypy.expose
    def newsletter(self, *args, **kwargs):
        request_uri = cherrypy.request.wsgi_environ['REQUEST_URI']
        if plexpy.CONFIG.NEWSLETTER_AUTH == 2:
            redirect_uri = request_uri.replace('/newsletter', '/newsletter_auth')
            raise cherrypy.HTTPRedirect(redirect_uri)

        elif plexpy.CONFIG.NEWSLETTER_AUTH == 1 and plexpy.CONFIG.NEWSLETTER_PASSWORD:
            if len(args) >= 2 and args[0] == 'image':
                return self.newsletter_auth(*args, **kwargs)
            elif kwargs.pop('key', None) == plexpy.CONFIG.NEWSLETTER_PASSWORD:
                return self.newsletter_auth(*args, **kwargs)
            else:
                return serve_template(template_name="newsletter_auth.html",
                                      title="Newsletter Login",
                                      uri=request_uri)

        else:
            return self.newsletter_auth(*args, **kwargs)

    @cherrypy.expose
    @requireAuth()
    def newsletter_auth(self, *args, **kwargs):
        if args:
            # Keep this for backwards compatibility for images through /newsletter/image
            if len(args) >= 2 and args[0] == 'image':
                if args[1] == 'images':
                    resource_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/default/')
                    try:
                        return serve_file(path=os.path.join(resource_dir, *args[1:]), content_type='image/png')
                    except NotFound:
                        return

                return self.image(args[1])

            if len(args) >= 2 and args[0] == 'id':
                newsletter_id_name = args[1]
                newsletter_uuid = None
            else:
                newsletter_id_name = None
                newsletter_uuid = args[0]

            newsletter = newsletter_handler.get_newsletter(newsletter_uuid=newsletter_uuid,
                                                           newsletter_id_name=newsletter_id_name)
            return newsletter

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def newsletter_preview(self, **kwargs):
        kwargs['preview'] = 'true'
        return serve_template(template_name="newsletter_preview.html",
                              title="Newsletter",
                              kwargs=kwargs)

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def real_newsletter(self, newsletter_id=None, start_date=None, end_date=None,
                        preview=False, raw=False, **kwargs):
        if newsletter_id and newsletter_id != 'None':
            newsletter = newsletters.get_newsletter_config(newsletter_id=newsletter_id)

            if newsletter:
                newsletter_agent = newsletters.get_agent_class(newsletter_id=newsletter_id,
                                                               newsletter_id_name=newsletter['id_name'],
                                                               agent_id=newsletter['agent_id'],
                                                               config=newsletter['config'],
                                                               start_date=start_date,
                                                               end_date=end_date,
                                                               subject=newsletter['subject'],
                                                               body=newsletter['body'],
                                                               message=newsletter['message'])
                preview = helpers.bool_true(preview)
                raw = helpers.bool_true(raw)

                if raw:
                    cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
                    return json.dumps(newsletter_agent.raw_data(preview=preview)).encode('utf-8')

                return newsletter_agent.generate_newsletter(preview=preview)

            logger.error("Failed to retrieve newsletter: Invalid newsletter_id %s" % newsletter_id)
            return "Failed to retrieve newsletter: invalid newsletter_id parameter"

        logger.error("Failed to retrieve newsletter: Missing newsletter_id parameter.")
        return "Failed to retrieve newsletter: missing newsletter_id parameter"

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def support(self, **kwargs):
        return serve_template(template_name="support.html", title="Support")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @addtoapi()
    def status(self, *args, **kwargs):
        """ Get the current status of Tautulli.

            ```
            Required parameters:
                None

            Optional parameters:
                check (str):        database

            Returns:
                json:
                    {"result": "success",
                     "message": "Ok",
                     }
            ```
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        status = {'result': 'success', 'message': 'Ok'}

        if args or kwargs:
            if not cherrypy.request.path_info == '/api/v2' and plexpy.AUTH_ENABLED:
                cherrypy.request.config['auth.require'] = []
                check_auth()

            if 'database' in (args[:1] or kwargs.get('check')):
                result = database.integrity_check()
                status.update(result)
                if result['integrity_check'] == 'ok':
                    status['message'] = 'Database ok'
                else:
                    status['result'] = 'error'
                    status['message'] = 'Database not ok'

        return status

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @addtoapi()
    def server_status(self, *args, **kwargs):
        """ Get the current status of Tautulli's connection to the Plex server.

            ```
            Required parameters:
                None

            Optional parameters:
                None

            Returns:
                json:
                    {"result": "success",
                     "connected": true,
                     }
            ```
        """
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        status = {'result': 'success', 'connected': plexpy.PLEX_SERVER_UP}

        return status

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi("get_exports_table")
    def get_export_list(self, section_id=None, user_id=None, rating_key=None, **kwargs):
        """ Get the data on the Tautulli export tables.

            ```
            Required parameters:
                section_id (str):               The id of the Plex library section, OR
                user_id (str):                  The id of the Plex user, OR
                rating_key (str):               The rating key of the exported item

            Optional parameters:
                order_column (str):             "added_at", "sort_title", "container", "bitrate", "video_codec",
                                                "video_resolution", "video_framerate", "audio_codec", "audio_channels",
                                                "file_size", "last_played", "play_count"
                order_dir (str):                "desc" or "asc"
                start (int):                    Row to start from, 0
                length (int):                   Number of items to return, 25
                search (str):                   A string to search for, "Thrones"

            Returns:
                json:
                    {"draw": 1,
                     "recordsTotal": 10,
                     "recordsFiltered": 3,
                     "data":
                        [{"timestamp": 1602823644,
                          "art_level": 0,
                          "complete": 1,
                          "custom_fields": "",
                          "exists": true,
                          "export_id": 42,
                          "exported_items": 28,
                          "file_format": "json",
                          "file_size": 57793562,
                          "filename": null,
                          "individual_files": 1,
                          "logo_level": 0,
                          "media_info_level": 1,
                          "media_type": "collection",
                          "media_type_title": "Collection",
                          "metadata_level": 1,
                          "rating_key": null,
                          "section_id": 1,
                          "thumb_level": 2,
                          "title": "Library - Movies - Collection [1]",
                          "total_items": 28,
                          "user_id": null
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
                          ("media_type_title", True, True),
                          ("rating_key", True, True),
                          ("title", True, True),
                          ("file_format", True, True),
                          ("metadata_level", True, True),
                          ("media_info_level", True, True),
                          ("custom_fields", True, True),
                          ("file_size", True, False),
                          ("complete", True, False)]
            kwargs['json_data'] = build_datatables_json(kwargs, dt_columns, "timestamp")

        result = exporter.get_export_datatable(section_id=section_id,
                                               user_id=user_id,
                                               rating_key=rating_key,
                                               kwargs=kwargs)

        return result

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def export_metadata_modal(self, section_id=None, user_id=None, rating_key=None,
                              media_type=None, sub_media_type=None,
                              export_type=None, **kwargs):
        file_formats = exporter.Export.FILE_FORMATS

        if media_type == 'photo_album':
            media_type = 'photoalbum'

        return serve_template(template_name="export_modal.html", title="Export Metadata",
                              section_id=section_id, user_id=user_id, rating_key=rating_key,
                              media_type=media_type, sub_media_type=sub_media_type,
                              export_type=export_type, file_formats=file_formats)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def get_export_fields(self, media_type=None, sub_media_type=None, **kwargs):
        """ Get a list of available custom export fields.

            ```
            Required parameters:
                media_type (str):          The media type of the fields to return

            Optional parameters:
                sub_media_type (str):      The child media type for
                                           collections (movie, show, artist, album, photoalbum),
                                           or playlists (video, audio, photo)

            Returns:
                json:
                    {"metadata_fields":
                        [{"field": "addedAt", "level": 1},
                         ...
                         ],
                     "media_info_fields":
                        [{"field": "media.aspectRatio", "level": 1},
                         ...
                         ]
                    }
            ```
        """
        custom_fields = exporter.get_custom_fields(media_type=media_type,
                                                   sub_media_type=sub_media_type)

        return custom_fields

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def export_metadata(self, section_id=None, user_id=None, rating_key=None, file_format='csv',
                        metadata_level=1, media_info_level=1,
                        thumb_level=0, art_level=0, logo_level=0,
                        custom_fields='', export_type='all', individual_files=False, **kwargs):
        """ Export library or media metadata to a file

            ```
            Required parameters:
                section_id (int):          The section id of the library items to export, OR
                user_id (int):             The user id of the playlist items to export, OR
                rating_key (int):          The rating key of the media item to export

            Optional parameters:
                file_format (str):         csv (default), json, xml, or m3u
                metadata_level (int):      The level of metadata to export (default 1)
                media_info_level (int):    The level of media info to export (default 1)
                thumb_level (int):         The level of poster/cover images to export (default 0)
                art_level (int):           The level of background artwork images to export (default 0)
                logo_level (int):          The level of logo images to export (default 0)
                custom_fields (str):       Comma separated list of custom fields to export
                                           in addition to the export level selected
                export_type (str):         'collection' or 'playlist' for library/user export,
                                           otherwise default to all library items
                individual_files (bool):   Export each item as an individual file for library/user export.

            Returns:
                json:
                    {"export_id": 1}
            ```
        """
        individual_files = helpers.bool_true(individual_files)
        result = exporter.Export(section_id=section_id,
                                 user_id=user_id,
                                 rating_key=rating_key,
                                 file_format=file_format,
                                 metadata_level=metadata_level,
                                 media_info_level=media_info_level,
                                 thumb_level=thumb_level,
                                 art_level=art_level,
                                 logo_level=logo_level,
                                 custom_fields=custom_fields,
                                 export_type=export_type,
                                 individual_files=individual_files).export()

        if isinstance(result, int):
            return {'result': 'success', 'message': 'Metadata export has started.', 'export_id': result}
        else:
            return {'result': 'error', 'message': result}

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def view_export(self, export_id=None, **kwargs):
        """ Download an exported metadata file

            ```
            Required parameters:
                export_id (int):          The row id of the exported file to view

            Optional parameters:
                None

            Returns:
                download
            ```
        """
        result = exporter.get_export(export_id=export_id)

        if result and result['complete'] == 1 and result['exists'] and not result['individual_files']:
            filepath = exporter.get_export_filepath(result['title'], result['timestamp'], result['filename'])

            if result['file_format'] == 'csv':
                with open(filepath, 'r', encoding='utf-8') as infile:
                    reader = csv.DictReader(infile)
                    table = '<table><tr><th>' + \
                            '</th><th>'.join(reader.fieldnames) + \
                            '</th></tr><tr>' + \
                            '</tr><tr>'.join(
                                '<td>' + '</td><td>'.join(row.values()) + '</td>' for row in reader) + \
                            '</tr></table>'
                    style = '<style>' \
                            'body {margin: 0;}' \
                            'table {border-collapse: collapse; overflow-y: auto; height: 100px;} ' \
                            'th {position: sticky; top: 0; background: #ddd; box-shadow: inset 1px 1px #000, 0 1px #000;}' \
                            'td {box-shadow: inset 1px -1px #000;}' \
                            'th, td {padding: 3px; white-space: nowrap;}' \
                            '</style>'
                return '{style}<pre>{table}</pre>'.format(style=style, table=table)

            elif result['file_format'] == 'json':
                return serve_file(filepath, name=result['filename'], content_type='application/json;charset=UTF-8')

            elif result['file_format'] == 'xml':
                return serve_file(filepath, name=result['filename'], content_type='application/xml;charset=UTF-8')

            elif result['file_format'] == 'm3u':
                return serve_file(filepath, name=result['filename'], content_type='text/plain;charset=UTF-8')

        else:
            if result and result.get('complete') == 0:
                msg = 'Export is still being processed.'
            elif result and result.get('complete') == -1:
                msg = 'Export failed to process.'
            elif result and not result.get('exists'):
                msg = 'Export file does not exist.'
            else:
                msg = 'Invalid export_id provided.'
            cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
            return json.dumps({'result': 'error', 'message': msg}).encode('utf-8')

    @cherrypy.expose
    @requireAuth(member_of("admin"))
    @addtoapi()
    def download_export(self, export_id=None, **kwargs):
        """ Download an exported metadata file

            ```
            Required parameters:
                export_id (int):          The row id of the exported file to download

            Optional parameters:
                None

            Returns:
                download
            ```
        """
        result = exporter.get_export(export_id=export_id)

        if result and result['complete'] == 1 and result['exists']:
            if result['thumb_level'] or result['art_level'] or result['logo_level'] or result['individual_files']:
                directory = exporter.format_export_directory(result['title'], result['timestamp'])
                dirpath = exporter.get_export_dirpath(directory)
                zip_filename = '{}.zip'.format(directory)

                buffer = BytesIO()
                temp_zip = zipfile.ZipFile(buffer, 'w')
                helpers.zipdir(dirpath, temp_zip)
                temp_zip.close()

                return serve_fileobj(buffer.getvalue(), content_type='application/zip',
                                     disposition='attachment', name=zip_filename)

            else:
                filepath = exporter.get_export_filepath(result['title'], result['timestamp'], result['filename'])
                return serve_download(filepath, name=result['filename'])

        else:
            if result and result.get('complete') == 0:
                msg = 'Export is still being processed.'
            elif result and result.get('complete') == -1:
                msg = 'Export failed to process.'
            elif result and not result.get('exists'):
                msg = 'Export file does not exist.'
            else:
                msg = 'Invalid export_id provided.'
            cherrypy.response.headers['Content-Type'] = 'application/json;charset=UTF-8'
            return json.dumps({'result': 'error', 'message': msg}).encode('utf-8')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @requireAuth(member_of("admin"))
    @addtoapi()
    def delete_export(self, export_id=None, delete_all=False, **kwargs):
        """ Delete exports from Tautulli.

            ```
            Required parameters:
                export_id (int):          The row id of the exported file to delete

            Optional parameters:
                delete_all (bool):        'true' to delete all exported files

            Returns:
                None
            ```
        """
        if helpers.bool_true(delete_all):
            result = exporter.delete_all_exports()
            if result:
                return {'result': 'success', 'message': 'All exports deleted successfully.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete all exports.'}

        else:
            result = exporter.delete_export(export_id=export_id)
            if result:
                return {'result': 'success', 'message': 'Export deleted successfully.'}
            else:
                return {'result': 'error', 'message': 'Failed to delete export.'}


    @cherrypy.expose
    @requireAuth(member_of("admin"))
    def exporter_docs(self, **kwargs):
        return '<pre>' + exporter.build_export_docs() + '</pre>'
