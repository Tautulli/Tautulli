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

import plexpy
import database
import helpers
import logger
import plextv


def available_monitoring_actions():
    actions = [{'label': 'Movie Activity',
                'name': 'pms_monitor_movie',
                'description': 'Enable monitoring of movie streaming activity on this server.'
                },
               {'label': 'TV Show Activity',
                'name': 'pms_monitor_tv',
                'description': 'Enable monitoring of tv show streaming activity on this server.'
                },
               {'label': 'Music Activity',
                'name': 'pms_monitor_music',
                'description': 'Enable monitoring of music streaming activity on this server.'
                },
               {'label': 'Recently Added',
                'name': 'pms_monitor_recently_added',
                'description': 'Enable monitoring of recently added content on this server.'
                },
               {'label': 'Remote Access',
                'name': 'pms_monitor_remote_access',
                'description': 'Enable monitoring of remote access for this server.'
                },
               {'label': 'Server Updates',
                'name': 'pms_monitor_updates',
                'description': 'Enable monitoring of server updates for this server.'
                }
               ]

    return actions


def refresh_servers():
    logger.info(u"PlexPy Servers :: Requesting servers list refresh...")

    servers = get_servers()

    for server in servers:
        if server['id']:
            server_resources = plextv.get_server_resources(**server)
            server_id = set_server_config(server_id=server['id'], **server_resources)

    logger.info(u"PlexPy Servers :: Servers list refreshed.")
    return True



def get_servers(server_id=None, pms_identifier=None):
    default_server = [{'id': 0,
                       'pms_identifier': '',
                       'pms_name': '',
                       'pms_ip': '',
                       'pms_port': 32400,
                       'pms_url': '',
                       'pms_token': '',
                       'pms_presence': 0,
                       'pms_version': '',
                       'pms_platform': '',
                       'pms_logs_folder': '',
                       'pms_ssl': 0,
                       'pms_is_remote': 0,
                       'pms_is_cloud': 0,
                       'pms_monitor_movie': 1,
                       'pms_monitor_tv': 1,
                       'pms_monitor_music': 1,
                       'pms_monitor_recently_added': 0,
                       'pms_monitor_remote_access': 0,
                       'pms_monitor_updates': 0,
                       'pms_plexpass': 0,
                       'pms_update_channel': '',
                       'pms_update_distro': '',
                       'pms_update_distro_build': ''
                       }]

    if server_id and not str(server_id).isdigit():
        logger.error(u"PlexPy Servers :: Unable to retrieve server from database: invalid server_id %s." % server_id)
        return default_server

    where = ''
    args = []
    if str(server_id).isdigit():
        where = 'WHERE id = ?'
        args = [server_id]
    elif pms_identifier:
        where = 'WHERE pms_identifier = ?'
        args = [pms_identifier]

    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT * FROM servers %s' % where, args)

    return result or default_server


def delete_server(server_id=None):
    monitor_db = database.MonitorDatabase()

    if str(server_id).isdigit():
        logger.debug(u"PlexPy Servers :: Deleting server_id %s from the database." % server_id)
        result = monitor_db.action('DELETE FROM servers WHERE id = ?', [server_id])
        return True
    else:
        return False


def set_server_config(server_id=None, **kwargs):
    if str(server_id).isdigit():
        server_id = int(server_id)
    else:
        logger.error(u"PlexPy Servers :: Unable to set exisiting server: invalid server_id %s." % server_id)
        return False

    pms_identifier = kwargs.pop('pms_identifier', None)

    if not pms_identifier:
        logger.error(u"PlexPy Servers :: Unable to update server: no pms_identifier provided.")
        return False

    # Check if the server is already in the databse
    server = get_servers(pms_identifier=pms_identifier)[0]
    if server['id'] != server_id:
        logger.error(u"PlexPy Servers :: Unable to update server: server already in database.")
        return 'Server already exists'

    keys = {'id': server_id or None,
            'pms_identifier': pms_identifier}

    monitor_db = database.MonitorDatabase()
    try:
        trans_type = monitor_db.upsert(table_name='servers', key_dict=keys, value_dict=kwargs)
        if trans_type == 'insert':
            server_id = monitor_db.last_insert_id()
        logger.info(u"PlexPy Servers :: Updated server: %s (server_id %s)." % (kwargs.get('pms_name', 'Unknown'), server_id))
        blacklist_logger()
        return server_id
    except Exception as e:
        logger.warn(u"PlexPy Servers :: Unable to update server: %s." % e)
        return False
    

def blacklist_logger():
    monitor_db = database.MonitorDatabase()
    servers = monitor_db.select('SELECT pms_identifier, pms_token FROM servers')

    blacklist = []

    for s in servers:
        if s['pms_identifier']:
            blacklist.append(s['pms_identifier'])
        if s['pms_token']:
            blacklist.append(s['pms_token'])

    logger._BLACKLIST_WORDS.update(blacklist)


def upgrade_config_to_db():
    # Set flag first in case something fails we don't want to keep re-adding the server
    plexpy.CONFIG.__setattr__('UPDATE_SERVERS_DB', 0)
    plexpy.CONFIG.write()

    # Make sure there is a valid server in the config file
    if not plexpy.CONFIG.PMS_IDENTIFIER:
        return

    logger.info(u"PlexPy Servers :: Upgrading to new servers system...")

    logger.info(u"PlexPy Servers :: Adding pms_identifier to existing tables.")
    monitor_db = database.MonitorDatabase()
    monitor_db.action('UPDATE notify_log SET pms_identifier = ?', [plexpy.CONFIG.PMS_IDENTIFIER])
    monitor_db.action('UPDATE poster_urls SET pms_identifier = ?', [plexpy.CONFIG.PMS_IDENTIFIER])
    monitor_db.action('UPDATE session_history SET pms_identifier = ?', [plexpy.CONFIG.PMS_IDENTIFIER])
    monitor_db.action('UPDATE sessions SET pms_identifier = ?', [plexpy.CONFIG.PMS_IDENTIFIER])
    monitor_db.action('UPDATE users SET pms_identifier = ?', [plexpy.CONFIG.PMS_IDENTIFIER])


    keys = {'id': None}
    values = {'pms_identifier': plexpy.CONFIG.PMS_IDENTIFIER,
              'pms_name': plexpy.CONFIG.PMS_NAME,
              'pms_ip': plexpy.CONFIG.PMS_IP,
              'pms_port': plexpy.CONFIG.PMS_PORT,
              'pms_url': plexpy.CONFIG.PMS_URL,
              'pms_token': plexpy.CONFIG.PMS_TOKEN,
              'pms_version': plexpy.CONFIG.PMS_VERSION,
              'pms_platform': plexpy.CONFIG.PMS_PLATFORM,
              'pms_logs_folder': plexpy.CONFIG.PMS_LOGS_FOLDER,
              'pms_ssl': plexpy.CONFIG.PMS_SSL,
              'pms_is_remote': plexpy.CONFIG.PMS_IS_REMOTE,
              'pms_monitor_movie': plexpy.CONFIG.MOVIE_LOGGING_ENABLE,
              'pms_monitor_tv': plexpy.CONFIG.TV_LOGGING_ENABLE,
              'pms_monitor_music': plexpy.CONFIG.MUSIC_LOGGING_ENABLE,
              'pms_monitor_recently_added': plexpy.CONFIG.NOTIFY_RECENTLY_ADDED,
              'pms_monitor_remote_access': plexpy.CONFIG.MONITOR_REMOTE_ACCESS,
              'pms_monitor_updates': plexpy.CONFIG.MONITOR_PMS_UPDATES,
              'pms_plexpass': plexpy.CONFIG.PMS_PLEXPASS,
              'pms_update_channel': plexpy.CONFIG.PMS_UPDATE_CHANNEL,
              'pms_update_distro': plexpy.CONFIG.PMS_UPDATE_DISTRO,
              'pms_update_distro_build': plexpy.CONFIG.PMS_UPDATE_DISTRO_BUILD
              }

    try:
        server_id = set_server_config(server_id=0, **values)
        return server_id
    except Exception as e:
        logger.warn(u"PlexPy Servers :: Unable to add existing server to database: %s." % e)
        return False