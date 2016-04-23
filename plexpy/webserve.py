﻿# This file is part of PlexPy.
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

from plexpy import logger, notifiers, plextv, pmsconnect, common, log_reader, \
    datafactory, graphs, users, libraries, database, web_socket
from plexpy.helpers import checked, addtoapi, get_ip, create_https_certificates

from mako.lookup import TemplateLookup
from mako import exceptions

import plexpy
import threading
import cherrypy
import hashlib
import random
import json
import os
from api2 import API2
from profilehooks import profile

try:
    # pylint:disable=E0611
    # ignore this error because we are catching the ImportError
    from collections import OrderedDict
    # pylint:enable=E0611
except ImportError:
    # Python 2.6.x fallback, from libs
    from ordereddict import OrderedDict


def serve_template(templatename, **kwargs):
    interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), plexpy.CONFIG.INTERFACE)

    _hplookup = TemplateLookup(directories=[template_dir], default_filters=['unicode', 'h'])

    server_name = plexpy.CONFIG.PMS_NAME

    try:
        template = _hplookup.get_template(templatename)
        return template.render(server_name=server_name, **kwargs)
    except:
        return exceptions.html_error_template().render()


class WebInterface(object):

    def __init__(self):
        self.interface_dir = os.path.join(str(plexpy.PROG_DIR), 'data/')

    @cherrypy.expose
    def index(self):
        if plexpy.CONFIG.FIRST_RUN_COMPLETE:
            raise cherrypy.HTTPRedirect("home")
        else:
            raise cherrypy.HTTPRedirect("welcome")


    ##### Welcome #####

    @cherrypy.expose
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
            "movie_notify_on_start": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_START),
            "tv_notify_on_start": checked(plexpy.CONFIG.TV_NOTIFY_ON_START),
            "music_notify_on_start": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_START),
            "movie_logging_enable": checked(plexpy.CONFIG.MOVIE_LOGGING_ENABLE),
            "tv_logging_enable": checked(plexpy.CONFIG.TV_LOGGING_ENABLE),
            "music_logging_enable": checked(plexpy.CONFIG.MUSIC_LOGGING_ENABLE),
            "logging_ignore_interval": plexpy.CONFIG.LOGGING_IGNORE_INTERVAL,
            "check_github": checked(plexpy.CONFIG.CHECK_GITHUB)
        }

        # The setup wizard just refreshes the page on submit so we must redirect to home if config set.
        if plexpy.CONFIG.FIRST_RUN_COMPLETE:
            plexpy.initialize_scheduler()
            raise cherrypy.HTTPRedirect("home")
        else:
            return serve_template(templatename="welcome.html", title="Welcome", config=config)

    @cherrypy.expose
    @addtoapi()
    def discover(self, token):
        """ Gets all your servers that are published to plextv

            Returns:
                json:
                    ```
                    [{"httpsRequired": "0",
                      "ip": "10.0.0.97",
                      "value": "10.0.0.97",
                      "label": "dude-PC",
                      "clientIdentifier": "1234",
                      "local": "1", "port": "32400"},
                      {"httpsRequired": "0",
                      "ip": "85.167.100.100",
                      "value": "85.167.100.100",
                      "label": "dude-PC",
                      "clientIdentifier": "1234",
                      "local": "0",
                      "port": "10294"}
                    ]
                    ```

        """
        # Need to set token so result doesn't return http 401
        plexpy.CONFIG.__setattr__('PMS_TOKEN', token)
        plexpy.CONFIG.write()

        plex_tv = plextv.PlexTV()
        servers = plex_tv.discover()

        if servers:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(servers)


    ##### Home #####

    @cherrypy.expose
    def home(self):
        config = {
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_cards": plexpy.CONFIG.HOME_STATS_CARDS,
            "home_library_cards": plexpy.CONFIG.HOME_LIBRARY_CARDS,
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER,
            "pms_name": plexpy.CONFIG.PMS_NAME
        }
        return serve_template(templatename="index.html", title="Home", config=config)

    @cherrypy.expose
    @addtoapi()
    def get_date_formats(self):
        """ Get the date and time formats used by plexpy """

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

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(formats)

    @cherrypy.expose
    def get_current_activity(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
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
    def get_current_activity_header(self, **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_current_activity()
        except:
            return serve_template(templatename="current_activity_header.html", data=None)

        if result:
            return serve_template(templatename="current_activity_header.html", data=result['stream_count'])
        else:
            logger.warn(u"Unable to retrieve data for get_current_activity_header.")
            return serve_template(templatename="current_activity_header.html", data=None)

    @cherrypy.expose
    def home_stats(self, **kwargs):
        data_factory = datafactory.DataFactory()

        grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES
        time_range = plexpy.CONFIG.HOME_STATS_LENGTH
        stats_type = plexpy.CONFIG.HOME_STATS_TYPE
        stats_count = plexpy.CONFIG.HOME_STATS_COUNT
        stats_cards = plexpy.CONFIG.HOME_STATS_CARDS
        notify_watched_percent = plexpy.CONFIG.NOTIFY_WATCHED_PERCENT

        stats_data = data_factory.get_home_stats(grouping=grouping,
                                                 time_range=time_range,
                                                 stats_type=stats_type,
                                                 stats_count=stats_count,
                                                 stats_cards=stats_cards,
                                                 notify_watched_percent=notify_watched_percent)

        return serve_template(templatename="home_stats.html", title="Stats", data=stats_data)

    @cherrypy.expose
    def library_stats(self, **kwargs):
        data_factory = datafactory.DataFactory()

        library_cards = plexpy.CONFIG.HOME_LIBRARY_CARDS

        stats_data = data_factory.get_library_stats(library_cards=library_cards)

        return serve_template(templatename="library_stats.html", title="Library Stats", data=stats_data)

    @cherrypy.expose
    def get_recently_added(self, count='0', **kwargs):

        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_recently_added_details(count=count)
        except IOError, e:
            return serve_template(templatename="recently_added.html", data=None)

        if result:
            return serve_template(templatename="recently_added.html", data=result['recently_added'])
        else:
            logger.warn(u"Unable to retrieve data for get_recently_added.")
            return serve_template(templatename="recently_added.html", data=None)

    @cherrypy.expose
    def delete_temp_sessions(self):

        result = database.delete_sessions()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': result})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})


    ##### Libraries #####

    @cherrypy.expose
    def libraries(self):
        config = {
            "update_section_ids": plexpy.CONFIG.UPDATE_SECTION_IDS
        }

        return serve_template(templatename="libraries.html", title="Libraries", config=config)

    @cherrypy.expose
    @addtoapi()
    def get_library_list(self, **kwargs):

        library_data = libraries.Libraries()
        library_list = library_data.get_datatables_list(kwargs=kwargs)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(library_list)

    @cherrypy.expose
    @addtoapi()
    def get_library_sections(self, **kwargs):
        """ Get the library sections from pms

            Returns:
                    json:
                        ```
                        [{"section_id": 1, "section_name": "Movies"},
                         {"section_id": 7, "section_name": "Music"},
                         {"section_id": 2, "section_name": "TV Shows"}
                        ]
                        ```

        """

        library_data = libraries.Libraries()
        result = library_data.get_sections()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_library_sections.")

    @cherrypy.expose
    @addtoapi() # should be added manually
    def refresh_libraries_list(self, **kwargs):
        threading.Thread(target=pmsconnect.refresh_libraries).start()
        logger.info(u"Manual libraries list refresh requested.")
        return True

    @cherrypy.expose
    def library(self, section_id=None):
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
    @addtoapi()
    def edit_library(self, section_id=None, **kwargs):
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

                status_message = "Successfully updated library."
                return status_message
            except:
                status_message = "Failed to update library."
                return status_message

    @cherrypy.expose
    def get_library_watch_time_stats(self, section_id=None, **kwargs):
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
    def get_library_user_stats(self, section_id=None, **kwargs):
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
    def get_library_recently_watched(self, section_id=None, limit='10', **kwargs):
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
    def get_library_recently_added(self, section_id=None, limit='10', **kwargs):
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
    @addtoapi()
    def get_library_media_info(self, section_id=None, section_type=None, rating_key=None, refresh='', **kwargs):

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

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(result)

    @cherrypy.expose
    @addtoapi()
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

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps({'success': result})

    @cherrypy.expose
    @addtoapi()
    def delete_all_library_history(self, section_id, **kwargs):
        library_data = libraries.Libraries()

        if section_id:
            delete_row = library_data.delete_all_history(section_id=section_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    @addtoapi()
    def delete_library(self, section_id, **kwargs):
        library_data = libraries.Libraries()

        if section_id:
            delete_row = library_data.delete(section_id=section_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    @addtoapi()
    def undelete_library(self, section_id=None, section_name=None, **kwargs):
        library_data = libraries.Libraries()

        if section_id:
            delete_row = library_data.undelete(section_id=section_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        elif section_name:
            delete_row = library_data.undelete(section_name=section_name)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    @addtoapi()
    def update_section_ids(self, **kwargs):

        logger.debug(u"Manual database section_id update called.")

        result = libraries.update_section_ids()

        if result:
            return "Updated all section_id's in database."
        else:
            return "Unable to update section_id's in database. See logs for details."

    @cherrypy.expose
    @addtoapi()
    def delete_datatable_media_info_cache(self, section_id, **kwargs):
        get_file_sizes_hold = plexpy.CONFIG.GET_FILE_SIZES_HOLD
        section_ids = set(get_file_sizes_hold['section_ids'])

        if section_id not in section_ids:
            if section_id:
                library_data = libraries.Libraries()
                delete_row = library_data.delete_datatable_media_info_cache(section_id=section_id)

                if delete_row:
                    cherrypy.response.headers['Content-type'] = 'application/json'
                    return json.dumps({'message': delete_row})
            else:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': 'no data received'})
        else:
            return json.dumps({'message': 'Cannot refresh library while getting file sizes.'})

    @cherrypy.expose
    def delete_duplicate_libraries(self):
        library_data = libraries.Libraries()

        result = library_data.delete_duplicate_libraries()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': result})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'Unable to delete duplicate libraries from the database.'})

    ##### Users #####

    @cherrypy.expose
    def users(self):
        return serve_template(templatename="users.html", title="Users")

    @cherrypy.expose
    @addtoapi()
    def get_user_list(self, **kwargs):

        user_data = users.Users()
        user_list = user_data.get_datatables_list(kwargs=kwargs)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(user_list)

    @cherrypy.expose
    @addtoapi()
    def refresh_users_list(self, **kwargs):
        """ Refresh a users list in a own thread """
        threading.Thread(target=plextv.refresh_users).start()
        logger.info(u"Manual users list refresh requested.")
        return True

    @cherrypy.expose
    def user(self, user_id=None):
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
    def edit_user(self, user_id=None, **kwargs):
        friendly_name = kwargs.get('friendly_name', '')
        custom_thumb = kwargs.get('custom_thumb', '')
        do_notify = kwargs.get('do_notify', 0)
        keep_history = kwargs.get('keep_history', 0)

        user_data = users.Users()
        if user_id:
            try:
                user_data.set_config(user_id=user_id,
                                     friendly_name=friendly_name,
                                     custom_thumb=custom_thumb,
                                     do_notify=do_notify,
                                     keep_history=keep_history)
                status_message = "Successfully updated user."
                return status_message
            except:
                status_message = "Failed to update user."
                return status_message

    @cherrypy.expose
    def get_user_watch_time_stats(self, user=None, user_id=None, **kwargs):
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
    def get_user_player_stats(self, user=None, user_id=None, **kwargs):
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
    def get_user_recently_watched(self, user=None, user_id=None, limit='10', **kwargs):
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
    def get_user_ips(self, user_id=None, **kwargs):

        user_data = users.Users()
        history = user_data.get_datatables_unique_ips(user_id=user_id, kwargs=kwargs)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(history)

    @cherrypy.expose
    def delete_all_user_history(self, user_id, **kwargs):
        user_data = users.Users()

        if user_id:
            delete_row = user_data.delete_all_history(user_id=user_id)
            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    def delete_user(self, user_id, **kwargs):
        user_data = users.Users()

        if user_id:
            delete_row = user_data.delete(user_id=user_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    def undelete_user(self, user_id=None, username=None, **kwargs):
        user_data = users.Users()

        if user_id:
            delete_row = user_data.undelete(user_id=user_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        elif username:
            delete_row = delete_user.undelete(username=username)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})


    ##### History #####

    @cherrypy.expose
    def history(self):
        return serve_template(templatename="history.html", title="History")

    @cherrypy.expose
    def get_history(self, user=None, user_id=None, grouping=0, **kwargs):

        if grouping == 'false':
            grouping = 0
        else:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        watched_percent = plexpy.CONFIG.NOTIFY_WATCHED_PERCENT

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
            if media_type != 'all':
               custom_where.append(['session_history.media_type', media_type])
        if 'transcode_decision' in kwargs:
            transcode_decision = kwargs.get('transcode_decision', "")
            if transcode_decision:
                custom_where.append(['session_history_media_info.transcode_decision', transcode_decision])

        data_factory = datafactory.DataFactory()
        history = data_factory.get_datatables_history(kwargs=kwargs, custom_where=custom_where, grouping=grouping, watched_percent=watched_percent)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(history)

    @cherrypy.expose
    def get_stream_data(self, row_id=None, user=None, **kwargs):

        data_factory = datafactory.DataFactory()
        stream_data = data_factory.get_stream_details(row_id)

        return serve_template(templatename="stream_data.html", title="Stream Data", data=stream_data, user=user)

    @cherrypy.expose
    def get_ip_address_details(self, ip_address=None, **kwargs):
        import socket

        try:
            socket.inet_aton(ip_address)
        except socket.error:
            ip_address = None

        return serve_template(templatename="ip_address_modal.html", title="IP Address Details", data=ip_address)

    @cherrypy.expose
    def delete_history_rows(self, row_id, **kwargs):
        data_factory = datafactory.DataFactory()

        if row_id:
            delete_row = data_factory.delete_session_history_rows(row_id=row_id)

            if delete_row:
                cherrypy.response.headers['Content-type'] = 'application/json'
                return json.dumps({'message': delete_row})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})


    ##### Graphs #####

    @cherrypy.expose
    def graphs(self):

        config = {
            "graph_type": plexpy.CONFIG.GRAPH_TYPE,
            "graph_days": plexpy.CONFIG.GRAPH_DAYS,
            "graph_tab": plexpy.CONFIG.GRAPH_TAB,
            "music_logging_enable": plexpy.CONFIG.MUSIC_LOGGING_ENABLE
        }

        return serve_template(templatename="graphs.html", title="Graphs", config=config)

    @cherrypy.expose
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
    @addtoapi()
    def get_plays_by_date(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_day(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_date.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_dayofweek(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_dayofweek(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_dayofweek.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_hourofday(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_hourofday(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_hourofday.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_per_month(self, y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_month(y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_per_month.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_top_10_platforms(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_top_10_platforms.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_top_10_users(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_top_10_users(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_top_10_users.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_stream_type(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_per_stream_type(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_stream_type.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_source_resolution(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_source_resolution(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_source_resolution.")

    @cherrypy.expose
    @addtoapi()
    def get_plays_by_stream_resolution(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_total_plays_by_stream_resolution(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_plays_by_stream_resolution.")

    @cherrypy.expose
    @addtoapi()
    def get_stream_type_by_top_10_users(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_users(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_stream_type_by_top_10_users.")

    @cherrypy.expose
    @addtoapi()
    def get_stream_type_by_top_10_platforms(self, time_range='30', y_axis='plays', **kwargs):

        graph = graphs.Graphs()
        result = graph.get_stream_type_by_top_10_platforms(time_range=time_range, y_axis=y_axis)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_stream_type_by_top_10_platforms.")

    @staticmethod
    def get_data_for_addedatmodal(t='date', filt=None, raw=False, *args, **kwargs):

        json_file = os.path.join(plexpy.CONFIG.CACHE_DIR, 'media_info_graphs.json')
        try:
            if filt and '-' in filt:
                y, m, d = filt.split('-')
                m = m.zfill(2)
                d = d.zfill(2)
                filt = '%s-%s-%s' % (y, m, d)

            # not in use atm
            """
            if t == 'day':
                t = 'day_name'
            elif t == 'month':
                t = 'month_name'
            """
            with open(json_file, 'r') as f:
                all_files = json.load(f)
                if raw:
                    return all_files

                filt = str(filt)
                return [item for item in all_files if str(item[t]) == filt]

        except Exception as e:
            logger.exception('Failed to fetch data for get data modal %s' % e)
            return []

    @cherrypy.expose
    def get_addedat_modal(self, *args, **kwargs):
        data = WebInterface.get_data_for_addedatmodal(t=kwargs['t'], filt=kwargs['start_date'])
        return serve_template(templatename="addedat_modal.html", title="Modal..",
                              date=kwargs['start_date'], dateformat=plexpy.CONFIG.DATE_FORMAT,
                              data=data, type=kwargs['t'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    @addtoapi()
    def get_data_by(self, **kwargs):

        g = graphs.Graphs.data_by(**kwargs)
        if g:
            if isinstance(g, list):
                # for the raw parameter
                return g
            # format for the damn charts.
            else:
                return {'categories': g['date'],
                        'series': [
                                {'data': g['episode'], 'name': 'TV'},
                                {'data': g['movie'], 'name': 'Movies'},
                                {'data': g['track'], 'name': 'Music'}

                            ]
                        }
        else:
            return []

    @cherrypy.expose
    @addtoapi()
    def refresh_get_data_by(self):
        """ Refresh cache file for graphs data by """

        x = pmsconnect.PmsConnect().make_meta_data_cache()
        return x


    @cherrypy.expose
    def history_table_modal(self, **kwargs):
        return serve_template(templatename="history_table_modal.html", title="History Data", data=kwargs)


    ##### Sync #####

    @cherrypy.expose
    def sync(self):
        return serve_template(templatename="sync.html", title="Synced Items")

    @cherrypy.expose
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

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(output)


    ##### Logs #####

    @cherrypy.expose
    def logs(self):
        return serve_template(templatename="logs.html", title="Log", lineList=plexpy.LOG_LIST)

    @cherrypy.expose
    def getLog(self, start=0, length=100, **kwargs):
        start = int(start)
        length = int(length)
        search_value = ""
        search_regex = ""
        order_column = 0
        order_dir = "desc"

        if 'order[0][dir]' in kwargs:
            order_dir = kwargs.get('order[0][dir]', "desc")

        if 'order[0][column]' in kwargs:
            order_column = kwargs.get('order[0][column]', "0")

        if 'search[value]' in kwargs:
            search_value = kwargs.get('search[value]', "")

        if 'search[regex]' in kwargs:
            search_regex = kwargs.get('search[regex]', "")

        filtered = []
        if search_value == "":
            filtered = plexpy.LOG_LIST[::]
        else:
            filtered = [row for row in plexpy.LOG_LIST for column in row if search_value.lower() in column.lower()]

        sortcolumn = 0
        if order_column == '1':
            sortcolumn = 2
        elif order_column == '2':
            sortcolumn = 1
        filtered.sort(key=lambda x: x[sortcolumn], reverse=order_dir == "desc")

        rows = filtered[start:(start + length)]
        rows = [[row[0], row[2], row[1]] for row in rows]

        return json.dumps({
            'recordsFiltered': len(filtered),
            'recordsTotal': len(plexpy.LOG_LIST),
            'data': rows,
        })

    @cherrypy.expose
    @addtoapi()
    def get_plex_log(self, window=1000, **kwargs):
        log_lines = []
        log_type = kwargs.get('log_type', 'server')

        try:
            log_lines = {'data': log_reader.get_log_tail(window=window, parsed=True, log_type=log_type)}
        except:
            logger.warn(u"Unable to retrieve Plex Logs.")

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(log_lines)

    @cherrypy.expose
    @addtoapi()
    def get_notification_log(self, **kwargs):
        data_factory = datafactory.DataFactory()
        notifications = data_factory.get_notification_log(kwargs=kwargs)

        cherrypy.response.headers['Content-type'] = 'application/json'
        return json.dumps(notifications)

    @cherrypy.expose
    @addtoapi()
    def clearNotifyLogs(self, **kwargs):
        data_factory = datafactory.DataFactory()
        result = data_factory.delete_notification_log()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': result})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    @cherrypy.expose
    def clearLogs(self):
        plexpy.LOG_LIST = []
        logger.info(u"Web logs cleared")
        raise cherrypy.HTTPRedirect("logs")

    @cherrypy.expose
    def toggleVerbose(self):
        plexpy.VERBOSE = not plexpy.VERBOSE
        logger.initLogger(console=not plexpy.QUIET,
                          log_dir=plexpy.CONFIG.LOG_DIR, verbose=plexpy.VERBOSE)
        logger.info(u"Verbose toggled, set to %s", plexpy.VERBOSE)
        logger.debug(u"If you read this message, debug logging is available")
        raise cherrypy.HTTPRedirect("logs")

    @cherrypy.expose
    def log_js_errors(self, page, message, file, line):
        """ Logs javascript errors from the web interface. """
        logger.error(u"WebUI :: /%s : %s. (%s:%s)" % (page.rpartition('/')[-1],
                                                    message,
                                                    file.rpartition('/')[-1].partition('?')[0],
                                                    line))
        return True

    @cherrypy.expose
    def logFile(self):
        try:
            with open(os.path.join(plexpy.CONFIG.LOG_DIR, 'plexpy.log'), 'r') as f:
                return '<pre>%s</pre>' % f.read()
        except IOError as e:
            return "Log file not found."


    ##### Settings #####

    @cherrypy.expose
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
            "http_host": plexpy.CONFIG.HTTP_HOST,
            "http_username": plexpy.CONFIG.HTTP_USERNAME,
            "http_port": plexpy.CONFIG.HTTP_PORT,
            "http_password": http_password,
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
            "tv_notify_on_start": checked(plexpy.CONFIG.TV_NOTIFY_ON_START),
            "movie_notify_on_start": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_START),
            "music_notify_on_start": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_START),
            "tv_notify_on_stop": checked(plexpy.CONFIG.TV_NOTIFY_ON_STOP),
            "movie_notify_on_stop": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_STOP),
            "music_notify_on_stop": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_STOP),
            "tv_notify_on_pause": checked(plexpy.CONFIG.TV_NOTIFY_ON_PAUSE),
            "movie_notify_on_pause": checked(plexpy.CONFIG.MOVIE_NOTIFY_ON_PAUSE),
            "music_notify_on_pause": checked(plexpy.CONFIG.MUSIC_NOTIFY_ON_PAUSE),
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
            "home_stats_length": plexpy.CONFIG.HOME_STATS_LENGTH,
            "home_stats_type": checked(plexpy.CONFIG.HOME_STATS_TYPE),
            "home_stats_count": plexpy.CONFIG.HOME_STATS_COUNT,
            "home_stats_cards": json.dumps(plexpy.CONFIG.HOME_STATS_CARDS),
            "home_library_cards": json.dumps(plexpy.CONFIG.HOME_LIBRARY_CARDS),
            "buffer_threshold": plexpy.CONFIG.BUFFER_THRESHOLD,
            "buffer_wait": plexpy.CONFIG.BUFFER_WAIT,
            "group_history_tables": checked(plexpy.CONFIG.GROUP_HISTORY_TABLES),
            "git_token": plexpy.CONFIG.GIT_TOKEN
        }

        return serve_template(templatename="settings.html", title="Settings", config=config)

    @cherrypy.expose
    def configUpdate(self, **kwargs):
        # Handle the variable config options. Note - keys with False values aren't getting passed

        checked_configs = [
            "launch_browser", "enable_https", "https_create_cert", "api_enabled", "freeze_db", "check_github",
            "grouping_global_history", "grouping_user_history", "grouping_charts", "pms_use_bif", "pms_ssl",
            "movie_notify_enable", "tv_notify_enable", "music_notify_enable", "monitoring_use_websocket",
            "tv_notify_on_start", "movie_notify_on_start", "music_notify_on_start",
            "tv_notify_on_stop", "movie_notify_on_stop", "music_notify_on_stop",
            "tv_notify_on_pause", "movie_notify_on_pause", "music_notify_on_pause",
            "refresh_libraries_on_startup", "refresh_users_on_startup",
            "ip_logging_enable", "movie_logging_enable", "tv_logging_enable", "music_logging_enable",
            "pms_is_remote", "home_stats_type", "group_history_tables", "notify_consecutive", "notify_upload_posters",
            "notify_recently_added", "notify_recently_added_grandparent",
            "monitor_pms_updates", "monitor_remote_access", "get_file_sizes", "log_blacklist"
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
                kwargs['http_password'] = plexpy.CONFIG.HTTP_PASSWORD

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

        # Remove config with 'hscard-' prefix and change home_stats_cards to list
        if kwargs.get('home_stats_cards', ''):
            for k in kwargs.keys():
                if k.startswith('hscard-'):
                    del kwargs[k]
            kwargs['home_stats_cards'] = kwargs['home_stats_cards'].split(',')

            if kwargs['home_stats_cards'] == ['first_run_wizard']:
                kwargs['home_stats_cards'] = plexpy.CONFIG.HOME_STATS_CARDS

        # Remove config with 'hlcard-' prefix and change home_library_cards to list
        if kwargs.get('home_library_cards', ''):
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

        raise cherrypy.HTTPRedirect("settings")

    @cherrypy.expose
    def get_scheduler_table(self, **kwargs):
        return serve_template(templatename="scheduler_table.html")

    @cherrypy.expose
    def backup_db(self):
        """ Creates a manual backup of the plexpy.db file """

        result = database.make_backup()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'Database backup successful.'})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'Database backup failed.'})

    @cherrypy.expose
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
    @addtoapi('notify')
    def test_notifier(self, agent_id=None, subject='PlexPy', body='Test notification', **kwargs):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"

        if agent_id.isdigit():
            agents = notifiers.available_notification_agents()
            for agent in agents:
                if int(agent_id) == agent['id']:
                    this_agent = agent
                    break
                else:
                    this_agent = None

            if this_agent:
                logger.debug(u"Sending test %s notification." % this_agent['name'])
                notifiers.send_notification(this_agent['id'], subject, body, 'test', **kwargs)
                return "Notification sent."
            else:
                logger.debug(u"Unable to send test notification, invalid notification agent ID %s." % agent_id)
                return "Invalid notification agent ID %s." % agent_id
        else:
            logger.debug(u"Unable to send test notification, no notification agent ID received.")
            return "No notification agent ID received."


    @cherrypy.expose
    def twitterStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        return tweet._get_authorization()

    @cherrypy.expose
    def twitterStep2(self, key):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        tweet = notifiers.TwitterNotifier()
        result = tweet._get_credentials(key)
        # logger.info(u"result: " + str(result))
        if result:
            return "Key verification successful"
        else:
            return "Unable to verify key"

    @cherrypy.expose
    def facebookStep1(self):
        cherrypy.response.headers['Cache-Control'] = "max-age=0,no-cache,no-store"
        facebook = notifiers.FacebookNotifier()
        return facebook._get_authorization()

    @cherrypy.expose
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
    @addtoapi()
    def get_plexwatch_export_data(self, database_path=None, table_name=None, import_ignore_interval=0, **kwargs):
        from plexpy import plexwatch_import

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

    @cherrypy.expose
    def plexwatch_import(self, **kwargs):
        return serve_template(templatename="plexwatch_import.html", title="Import PlexWatch Database")

    @cherrypy.expose
    def get_pms_token(self):

        token = plextv.PlexTV()
        result = token.get_token()

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve Plex.tv token.")
            return False

    @cherrypy.expose
    @addtoapi()
    def get_server_id(self, hostname=None, port=None, identifier=None, ssl=0, remote=0, **kwargs):
        from plexpy import http_handler

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
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(identifier)
        else:
            logger.warn('Unable to retrieve the PMS identifier.')
            return None

    @cherrypy.expose
    @addtoapi()
    def get_server_pref(self, pref=None, **kwargs):
        """ Return a specified server preference.

                Args:
                    pref(string): 'name of preference'

                Returns:
                    String: ''

        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_pref(pref=pref)

        if result:
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_pref.")

    @cherrypy.expose
    def generateAPI(self):
        apikey = hashlib.sha224(str(random.getrandbits(256))).hexdigest()[0:32]
        logger.info(u"New API key generated.")
        return apikey

    @cherrypy.expose
    def checkGithub(self):
        from plexpy import versioncheck

        versioncheck.checkGithub()
        raise cherrypy.HTTPRedirect("home")

    @cherrypy.expose
    def do_state_change(self, signal, title, timer):
        message = title
        quote = self.random_arnold_quotes()
        plexpy.SIGNAL = signal

        return serve_template(templatename="shutdown.html", title=title,
                              message=message, timer=timer, quote=quote)

    @cherrypy.expose
    def shutdown(self):
        return self.do_state_change('shutdown', 'Shutting Down', 15)

    @cherrypy.expose
    def restart(self):
        return self.do_state_change('restart', 'Restarting', 30)

    @cherrypy.expose
    def update(self):
        return self.do_state_change('update', 'Updating', 120)


    ##### Info #####

    @cherrypy.expose
    def info(self, rating_key=None, source=None, query=None, **kwargs):
        metadata = None

        config = {
            "pms_identifier": plexpy.CONFIG.PMS_IDENTIFIER
        }

        if source == 'history':
            data_factory = datafactory.DataFactory()
            metadata = data_factory.get_metadata_details(rating_key=rating_key)
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
            return serve_template(templatename="info.html", data=metadata, title="Info", config=config, source=source)
        else:
            return self.update_metadata(rating_key, query)

    @cherrypy.expose
    def get_item_children(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_item_children(rating_key)

        if result:
            return serve_template(templatename="info_children_list.html", data=result, title="Children List")
        else:
            logger.warn(u"Unable to retrieve data for get_item_children.")
            return serve_template(templatename="info_children_list.html", data=None, title="Children List")

    @cherrypy.expose
    def pms_image_proxy(self, img='', width='0', height='0', fallback=None, **kwargs):
        try:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_image(img, width, height)
            cherrypy.response.headers['Content-type'] = result[1]
            return result[0]
        except:
            logger.warn(u"Image proxy queried but errors occurred.")
            if fallback == 'poster':
                logger.info(u"Trying fallback image...")
                try:
                    fallback_image = open(self.interface_dir + common.DEFAULT_POSTER_THUMB, 'rb')
                    cherrypy.response.headers['Content-type'] = 'image/png'
                    return fallback_image
                except IOError, e:
                    logger.error(u"Unable to read fallback %s image: %s" % (fallback, e))
            elif fallback == 'cover':
                logger.info(u"Trying fallback image...")
                try:
                    fallback_image = open(self.interface_dir + common.DEFAULT_COVER_THUMB, 'rb')
                    cherrypy.response.headers['Content-type'] = 'image/png'
                    return fallback_image
                except IOError, e:
                    logger.error(u"Unable to read fallback  %s image: %s" % (fallback, e))

            return None

    @cherrypy.expose
    def delete_poster_url(self, poster_url=''):

        if poster_url:
            data_factory = datafactory.DataFactory()
            result = data_factory.delete_poster_url(poster_url=poster_url)
        else:
            result = None

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': result})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})


    ##### Search #####

    @cherrypy.expose
    def search(self, query=''):
        return serve_template(templatename="search.html", title="Search", query=query)

    @cherrypy.expose
    @addtoapi('search')
    def search_results(self, query, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_search_results(query)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for search_results.")

    @cherrypy.expose
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
    @addtoapi()
    def update_metadata_details(self, old_rating_key, new_rating_key, media_type, **kwargs):
        data_factory = datafactory.DataFactory()
        pms_connect = pmsconnect.PmsConnect()

        if new_rating_key:
            old_key_list = data_factory.get_rating_keys_list(rating_key=old_rating_key, media_type=media_type)
            new_key_list = pms_connect.get_rating_keys_list(rating_key=new_rating_key, media_type=media_type)

            result = data_factory.update_metadata(old_key_list=old_key_list,
                                                  new_key_list=new_key_list,
                                                  media_type=media_type)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': result})
        else:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps({'message': 'no data received'})

    # test code
    @cherrypy.expose
    @addtoapi()
    def get_new_rating_keys(self, rating_key='', media_type='', **kwargs):
        """
            Grap the new rating keys

            Args:
                rating_key(string): '',
                media_type(string): ''

            Returns:
                    json: ''

        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_rating_keys_list(rating_key=rating_key, media_type=media_type)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_new_rating_keys.")

    @cherrypy.expose
    @addtoapi()
    def get_old_rating_keys(self, rating_key='', media_type='', **kwargs):
        """
        Grap the old rating keys
        Args:
            rating_key(string): '',
            media_type(string): ''
        Returns:
                json: ''

        """

        data_factory = datafactory.DataFactory()
        result = data_factory.get_rating_keys_list(rating_key=rating_key, media_type=media_type)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_old_rating_keys.")


    @cherrypy.expose
    @addtoapi('get_sessions')
    def get_pms_sessions_json(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sessions('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_pms_sessions_json.")
            return False

    @cherrypy.expose
    @addtoapi('get_metadata')
    def get_metadata_json(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata(rating_key, 'json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_metadata_json.")

    @cherrypy.expose
    def get_metadata_xml(self, rating_key='', **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_metadata(rating_key)

        if result:
            cherrypy.response.headers['Content-type'] = 'application/xml'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_metadata_xml.")

    @cherrypy.expose
    @addtoapi('get_recently_added')
    def get_recently_added_json(self, count='0', **kwargs):
        """ Get all items that where recelty added to plex

            Args:
                count(string): Number of items

            Returns:
                dict: of all added items

        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_recently_added(count, 'json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_recently_added_json.")

    @cherrypy.expose
    @addtoapi()
    def get_friends_list(self, **kwargs):
        """ Gets the friends list of the server owner for plex.tv """

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_friends('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_friends_list.")

    @cherrypy.expose
    @addtoapi()
    def get_user_details(self, **kwargs):
        """ Get all details about a user from plextv """

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_user_details('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_user_details.")

    @cherrypy.expose
    @addtoapi()
    def get_server_list(self, **kwargs):
        """ Find all servers published on plextv"""

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_server_list('json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_list.")

    @cherrypy.expose
    @addtoapi()
    def get_sync_lists(self, machine_id='', **kwargs):

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_plextv_sync_lists(machine_id=machine_id, output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_sync_lists.")

    @cherrypy.expose
    @addtoapi()
    def get_servers(self, **kwargs):
        """ All servers

            Returns:
                    json:
                        ```
                        {"MediaContainer": {"@size": "1", "Server":
                            {"@name": "dude-PC",
                            "@host": "10.0.0.97",
                            "@address": "10.0.0.97",
                            "@port": "32400",
                            "@machineIdentifier": "1234",
                            "@version": "0.9.15.2.1663-7efd046"}}}
                        ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_list(output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_servers.")

    @cherrypy.expose
    @addtoapi()
    def get_servers_info(self, **kwargs):
        """ Grabs list of info about the servers

            Returns:
                    json:
                        ```
                        [{"port": "32400",
                          "host": "10.0.0.97",
                          "version": "0.9.15.2.1663-7efd046",
                          "name": "dude-PC",
                          "machine_identifier": "1234"
                          }
                        ]
                        ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_servers_info()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_servers_info.")

    @cherrypy.expose
    @addtoapi()
    def get_server_identity(self, **kwargs):
        """ Grabs info about the local server

            Returns:
                    json:
                        ```
                        [{"machine_identifier": "1234",
                          "version": "0.9.15.x.xxx-xxxxxxx"
                          }
                        ]
                        ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_server_identity()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_server_identity.")

    @cherrypy.expose
    @addtoapi()
    def get_server_friendly_name(self, **kwargs):

        result = pmsconnect.get_server_friendly_name()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_friendly_name.")

    @cherrypy.expose
    @addtoapi()
    def get_server_prefs(self, pref=None, **kwargs):

        if pref:
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_server_pref(pref=pref)
        else:
            result = None

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_server_prefs.")

    @cherrypy.expose
    @addtoapi()
    def get_activity(self, **kwargs):
        """ Return processed and validated session list.

            Returns:
                json:
                    ```
                    {stream_count: 1,
                     session: [{dict}]
                    }
                    ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_current_activity()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_activity.")

    @cherrypy.expose
    @addtoapi()
    def get_full_users_list(self, **kwargs):
        """ Get a list all users that has access to your server

            Returns:
                    json:
                        ```
                        [{"username": "Hellowlol", "user_id": "1345",
                          "thumb": "https://plex.tv/users/123aa/avatar",
                          "is_allow_sync": null,
                          "is_restricted": "0",
                          "is_home_user": "0",
                          "email": "John.Doe@email.com"}]
                        ```

        """

        plex_tv = plextv.PlexTV()
        result = plex_tv.get_full_users_list()

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return json.dumps(result)
        else:
            logger.warn(u"Unable to retrieve data for get_full_users_list.")

    @cherrypy.expose
    @addtoapi()
    def get_sync_item(self, sync_id, **kwargs):
        """ Return sync item details.

            Args:
                sync_id(string): unique sync id for item
                output_format(string, optional): 'xml/json'

            Returns:
                List:
                    ```
                    {"data": [
                                {"username": "username",
                                 "item_downloaded_percent_complete": 100,
                                 "user_id": "134",
                                 "failure": "",
                                 "title": "Some Movie",
                                 "total_size": "747195119",
                                 "root_title": "Movies",
                                 "music_bitrate": "128",
                                 "photo_quality": "49",
                                 "friendly_name": "username",
                                 "device_name": "Username iPad",
                                 "platform": "iOS",
                                 "state": "complete",
                                 "item_downloaded_count": "1",
                                 "content_type": "video",
                                 "metadata_type": "movie",
                                 "video_quality": "49",
                                 "item_count": "1",
                                 "rating_key": "59207",
                                 "item_complete_count": "1",
                                 "sync_id": "1234"}
                            ]
                    }
                    ```
        """

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sync_item(sync_id, output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_sync_item.")

    @cherrypy.expose
    @addtoapi()
    def get_sync_transcode_queue(self, **kwargs):

        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_sync_transcode_queue(output_format='json')

        if result:
            cherrypy.response.headers['Content-type'] = 'application/json'
            return result
        else:
            logger.warn(u"Unable to retrieve data for get_sync_transcode_queue.")

    @cherrypy.expose
    @addtoapi()
    def random_arnold_quotes(self, **kwargs):
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
            from plexpy.api import Api
            a = Api()
            a.checkParams(*args, **kwargs)
            return a.fetchData()

    @cherrypy.expose
    def check_pms_updater(self):
        pms_connect = pmsconnect.PmsConnect()
        result = pms_connect.get_update_staus()
        return json.dumps(result)
