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

import httpagentparser
import time

import plexpy
import common
import database
import datatables
import helpers
import logger
import plextv
import pmsconnect
import session


def refresh_users():
    logger.info(u"Tautulli Users :: Requesting users list refresh...")
    result = plextv.PlexTV().get_full_users_list()

    monitor_db = database.MonitorDatabase()
    user_data = Users()

    if result:
        for item in result:

            shared_libraries = ''
            user_tokens = user_data.get_tokens(user_id=item['user_id'])
            if user_tokens and user_tokens['server_token']:
                pms_connect = pmsconnect.PmsConnect(token=user_tokens['server_token'])
                library_details = pms_connect.get_server_children()

                if library_details:
                    shared_libraries = ';'.join(d['section_id'] for d in library_details['libraries_list'])
                else:
                    shared_libraries = ''

            control_value_dict = {"user_id": item['user_id']}
            new_value_dict = {"username": item['username'],
                              "thumb": item['thumb'],
                              "email": item['email'],
                              "is_home_user": item['is_home_user'],
                              "is_allow_sync": item['is_allow_sync'],
                              "is_restricted": item['is_restricted'],
                              "shared_libraries": shared_libraries,
                              "filter_all": item['filter_all'],
                              "filter_movies": item['filter_movies'],
                              "filter_tv": item['filter_tv'],
                              "filter_music": item['filter_music'],
                              "filter_photos": item['filter_photos']
                              }

            # Check if we've set a custom avatar if so don't overwrite it.
            if item['user_id']:
                avatar_urls = monitor_db.select('SELECT thumb, custom_avatar_url '
                                                'FROM users WHERE user_id = ?',
                                                [item['user_id']])
                if avatar_urls:
                    if not avatar_urls[0]['custom_avatar_url'] or \
                            avatar_urls[0]['custom_avatar_url'] == avatar_urls[0]['thumb']:
                        new_value_dict['custom_avatar_url'] = item['thumb']
                else:
                    new_value_dict['custom_avatar_url'] = item['thumb']

            monitor_db.upsert('users', new_value_dict, control_value_dict)

        logger.info(u"Tautulli Users :: Users list refreshed.")
        return True
    else:
        logger.warn(u"Tautulli Users :: Unable to refresh users list.")
        return False


class Users(object):

    def __init__(self):
        pass

    def get_datatables_list(self, kwargs=None):
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': 'null',
                          'error': 'Unable to execute database query.'}

        data_tables = datatables.DataTables()

        custom_where = [['users.deleted_user', 0]]

        if session.get_session_user_id():
            custom_where.append(['users.user_id', session.get_session_user_id()])

        if kwargs.get('user_id'):
            custom_where.append(['users.user_id', kwargs.get('user_id')])

        columns = ['users.user_id',
                   '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" \
                    THEN users.username ELSE users.friendly_name END) AS friendly_name',
                   'users.thumb AS user_thumb',
                   'users.custom_avatar_url AS custom_thumb',
                   'COUNT(session_history.id) AS plays',
                   'SUM(CASE WHEN session_history.stopped > 0 THEN (session_history.stopped - session_history.started) \
                    ELSE 0 END) - SUM(CASE WHEN session_history.paused_counter IS NULL THEN 0 ELSE \
                    session_history.paused_counter END) AS duration',
                   'MAX(session_history.started) AS last_seen',
                   'MAX(session_history.id) AS id',
                   'session_history_metadata.full_title AS last_played',
                   'session_history.ip_address',
                   'session_history.platform',
                   'session_history.player',
                   'session_history.rating_key',
                   'session_history_metadata.media_type',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.parent_title',
                   'session_history_metadata.year',
                   'session_history_metadata.media_index',
                   'session_history_metadata.parent_media_index',
                   'session_history_media_info.transcode_decision',
                   'users.do_notify as do_notify',
                   'users.keep_history as keep_history',
                   'users.allow_guest as allow_guest'
                   ]
        try:
            query = data_tables.ssp_query(table_name='users',
                                          columns=columns,
                                          custom_where=custom_where,
                                          group_by=['users.user_id'],
                                          join_types=['LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN',
                                                      'LEFT OUTER JOIN'],
                                          join_tables=['session_history',
                                                       'session_history_metadata',
                                                       'session_history_media_info'],
                                          join_evals=[['session_history.user_id', 'users.user_id'],
                                                      ['session_history.id', 'session_history_metadata.id'],
                                                      ['session_history.id', 'session_history_media_info.id']],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_list: %s." % e)
            return default_return

        users = query['result']

        rows = []
        for item in users:
            if item['media_type'] == 'episode' and item['parent_thumb']:
                thumb = item['parent_thumb']
            elif item['media_type'] == 'episode':
                thumb = item['grandparent_thumb']
            else:
                thumb = item['thumb']

            if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                user_thumb = item['custom_thumb']
            elif item['user_thumb']:
                user_thumb = item['user_thumb']
            else:
                user_thumb = common.DEFAULT_USER_THUMB

            # Rename Mystery platform names
            platform = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])

            row = {'user_id': item['user_id'],
                   'friendly_name': item['friendly_name'],
                   'user_thumb': user_thumb,
                   'plays': item['plays'],
                   'duration': item['duration'],
                   'last_seen': item['last_seen'],
                   'last_played': item['last_played'],
                   'id': item['id'],
                   'ip_address': item['ip_address'],
                   'platform': platform,
                   'player': item['player'],
                   'rating_key': item['rating_key'],
                   'media_type': item['media_type'],
                   'thumb': thumb,
                   'parent_title': item['parent_title'],
                   'year': item['year'],
                   'media_index': item['media_index'],
                   'parent_media_index': item['parent_media_index'],
                   'transcode_decision': item['transcode_decision'],
                   'do_notify': helpers.checked(item['do_notify']),
                   'keep_history': helpers.checked(item['keep_history']),
                   'allow_guest': helpers.checked(item['allow_guest'])
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': session.friendly_name_to_username(rows),
                'draw': query['draw']
                }

        return dict

    def get_datatables_unique_ips(self, user_id=None, kwargs=None):
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': 'null',
                          'error': 'Unable to execute database query.'}

        if not session.allow_session_user(user_id):
            return default_return

        data_tables = datatables.DataTables()

        custom_where = ['users.user_id', user_id]

        columns = ['session_history.id',
                   'session_history.started AS last_seen',
                   'session_history.ip_address',
                   'COUNT(session_history.id) AS play_count',
                   'session_history.platform',
                   'session_history.player',
                   'session_history.rating_key',
                   'session_history_metadata.full_title AS last_played',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history_metadata.parent_title',
                   'session_history_metadata.year',
                   'session_history_metadata.media_index',
                   'session_history_metadata.parent_media_index',
                   'session_history_media_info.transcode_decision',
                   'session_history.user',
                   'session_history.user_id as custom_user_id',
                   '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" \
                    THEN users.username ELSE users.friendly_name END) AS friendly_name'
                   ]

        try:
            query = data_tables.ssp_query(table_name='session_history',
                                          columns=columns,
                                          custom_where=[custom_where],
                                          group_by=['ip_address'],
                                          join_types=['JOIN',
                                                      'JOIN',
                                                      'JOIN'],
                                          join_tables=['users',
                                                       'session_history_metadata',
                                                       'session_history_media_info'],
                                          join_evals=[['session_history.user_id', 'users.user_id'],
                                                      ['session_history.id', 'session_history_metadata.id'],
                                                      ['session_history.id', 'session_history_media_info.id']],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_unique_ips: %s." % e)
            return default_return

        results = query['result']

        rows = []
        for item in results:
            if item["media_type"] == 'episode' and item["parent_thumb"]:
                thumb = item["parent_thumb"]
            elif item["media_type"] == 'episode':
                thumb = item["grandparent_thumb"]
            else:
                thumb = item["thumb"]

            # Rename Mystery platform names
            platform = common.PLATFORM_NAME_OVERRIDES.get(item["platform"], item["platform"])

            row = {'id': item['id'],
                   'last_seen': item['last_seen'],
                   'ip_address': item['ip_address'],
                   'play_count': item['play_count'],
                   'platform': platform,
                   'player': item['player'],
                   'last_played': item['last_played'],
                   'rating_key': item['rating_key'],
                   'thumb': thumb,
                   'media_type': item['media_type'],
                   'parent_title': item['parent_title'],
                   'year': item['year'],
                   'media_index': item['media_index'],
                   'parent_media_index': item['parent_media_index'],
                   'transcode_decision': item['transcode_decision'],
                   'friendly_name': item['friendly_name'],
                   'user_id': item['custom_user_id']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': session.friendly_name_to_username(rows),
                'draw': query['draw']
                }

        return dict

    def set_config(self, user_id=None, friendly_name='', custom_thumb='', do_notify=1, keep_history=1, allow_guest=1):
        if str(user_id).isdigit():
            monitor_db = database.MonitorDatabase()

            key_dict = {'user_id': user_id}
            value_dict = {'friendly_name': friendly_name,
                          'custom_avatar_url': custom_thumb,
                          'do_notify': do_notify,
                          'keep_history': keep_history,
                          'allow_guest': allow_guest
                          }
            try:
                monitor_db.upsert('users', value_dict, key_dict)
            except Exception as e:
                logger.warn(u"Tautulli Users :: Unable to execute database query for set_config: %s." % e)

    def get_details(self, user_id=None, user=None, email=None):
        default_return = {'user_id': 0,
                          'username': 'Local',
                          'friendly_name': 'Local',
                          'user_thumb': common.DEFAULT_USER_THUMB,
                          'email': '',
                          'is_home_user': 0,
                          'is_allow_sync': 0,
                          'is_restricted': 0,
                          'do_notify': 0,
                          'keep_history': 1,
                          'allow_guest': 0,
                          'deleted_user': 0,
                          'shared_libraries': ()
                          }

        if user_id is None and not user and not email:
            return default_return

        def get_user_details(user_id=user_id, user=user, email=email):
            monitor_db = database.MonitorDatabase()

            try:
                if str(user_id).isdigit():
                    query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                            'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history, deleted_user, ' \
                            'allow_guest, shared_libraries ' \
                            'FROM users ' \
                            'WHERE user_id = ? '
                    result = monitor_db.select(query, args=[user_id])
                elif user:
                    query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                            'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history, deleted_user, ' \
                            'allow_guest, shared_libraries ' \
                            'FROM users ' \
                            'WHERE username = ? COLLATE NOCASE '
                    result = monitor_db.select(query, args=[user])
                elif email:
                    query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                            'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history, deleted_user, ' \
                            'allow_guest, shared_libraries ' \
                            'FROM users ' \
                            'WHERE email = ? COLLATE NOCASE '
                    result = monitor_db.select(query, args=[email])
                else:
                    result = []
            except Exception as e:
                logger.warn(u"Tautulli Users :: Unable to execute database query for get_details: %s." % e)
                result = []

            user_details = {}
            if result:
                for item in result:
                    if session.get_session_user_id():
                        friendly_name = session.get_session_user()
                    elif item['friendly_name']:
                        friendly_name = item['friendly_name']
                    else:
                        friendly_name = item['username']

                    if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                        user_thumb = item['custom_thumb']
                    elif item['user_thumb']:
                        user_thumb = item['user_thumb']
                    else:
                        user_thumb = common.DEFAULT_USER_THUMB

                    shared_libraries = tuple(item['shared_libraries'].split(';')) if item['shared_libraries'] else ()

                    user_details = {'user_id': item['user_id'],
                                    'username': item['username'],
                                    'friendly_name': friendly_name,
                                    'user_thumb': user_thumb,
                                    'email': item['email'],
                                    'is_home_user': item['is_home_user'],
                                    'is_allow_sync': item['is_allow_sync'],
                                    'is_restricted': item['is_restricted'],
                                    'do_notify': item['do_notify'],
                                    'keep_history': item['keep_history'],
                                    'deleted_user': item['deleted_user'],
                                    'allow_guest': item['allow_guest'],
                                    'shared_libraries': shared_libraries
                                    }
            return user_details

        user_details = get_user_details(user_id=user_id, user=user)

        if user_details:
            return user_details

        else:
            logger.warn(u"Tautulli Users :: Unable to retrieve user %s from database. Requesting user list refresh."
                        % user_id if user_id else user)
            # Let's first refresh the user list to make sure the user isn't newly added and not in the db yet
            refresh_users()

            user_details = get_user_details(user_id=user_id, user=user)

            if user_details:
                return user_details

            else:
                logger.warn(u"Tautulli Users :: Unable to retrieve user %s from database. Returning 'Local' user."
                            % user_id if user_id else user)
                # If there is no user data we must return something
                # Use "Local" user to retain compatibility with PlexWatch database value
                return default_return

    def get_watch_time_stats(self, user_id=None):
        if not session.allow_session_user(user_id):
            return []

        monitor_db = database.MonitorDatabase()

        time_queries = [1, 7, 30, 0]
        user_watch_time_stats = []

        for days in time_queries:
            try:
                if days > 0:
                    if str(user_id).isdigit():
                        query = 'SELECT (SUM(stopped - started) - ' \
                                '   SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                                'COUNT(id) AS total_plays ' \
                                'FROM session_history ' \
                                'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                                'AND user_id = ?' % days
                        result = monitor_db.select(query, args=[user_id])
                    else:
                        result = []
                else:
                    if str(user_id).isdigit():
                        query = 'SELECT (SUM(stopped - started) - ' \
                                '   SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                                'COUNT(id) AS total_plays ' \
                                'FROM session_history ' \
                                'WHERE user_id = ?'
                        result = monitor_db.select(query, args=[user_id])
                    else:
                        result = []
            except Exception as e:
                logger.warn(u"Tautulli Users :: Unable to execute database query for get_watch_time_stats: %s." % e)
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

                user_watch_time_stats.append(row)

        return user_watch_time_stats

    def get_player_stats(self, user_id=None):
        if not session.allow_session_user(user_id):
            return []

        monitor_db = database.MonitorDatabase()

        player_stats = []
        result_id = 0

        try:
            if str(user_id).isdigit():
                query = 'SELECT player, COUNT(player) as player_count, platform ' \
                        'FROM session_history ' \
                        'WHERE user_id = ? ' \
                        'GROUP BY player ' \
                        'ORDER BY player_count DESC'
                result = monitor_db.select(query, args=[user_id])
            else:
                result = []
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_player_stats: %s." % e)
            result = []

        for item in result:
            # Rename Mystery platform names
            platform = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])
            platform_name = next((v for k, v in common.PLATFORM_NAMES.iteritems() if k in platform.lower()), 'default')

            row = {'player_name': item['player'],
                   'platform': platform,
                   'platform_name': platform_name,
                   'total_plays': item['player_count'],
                   'result_id': result_id
                   }
            player_stats.append(row)
            result_id += 1

        return player_stats

    def get_recently_watched(self, user_id=None, limit='10'):
        if not session.allow_session_user(user_id):
            return []

        monitor_db = database.MonitorDatabase()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if str(user_id).isdigit():
                query = 'SELECT session_history.id, session_history.media_type, ' \
                        'session_history.rating_key, session_history.parent_rating_key, session_history.grandparent_rating_key, ' \
                        'title, parent_title, grandparent_title, thumb, parent_thumb, grandparent_thumb, media_index, parent_media_index, ' \
                        'year, started, user ' \
                        'FROM session_history_metadata ' \
                        'JOIN session_history ON session_history_metadata.id = session_history.id ' \
                        'WHERE user_id = ? ' \
                        'GROUP BY (CASE WHEN session_history.media_type = "track" THEN session_history.parent_rating_key ' \
                        '   ELSE session_history.rating_key END) ' \
                        'ORDER BY started DESC LIMIT ?'
                result = monitor_db.select(query, args=[user_id, limit])
            else:
                result = []
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_recently_watched: %s." % e)
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
                                 'thumb': thumb,
                                 'media_index': row['media_index'],
                                 'parent_media_index': row['parent_media_index'],
                                 'year': row['year'],
                                 'time': row['started'],
                                 'user': row['user']
                                 }
                recently_watched.append(recent_output)

        return recently_watched

    def delete_all_history(self, user_id=None):
        monitor_db = database.MonitorDatabase()

        try:
            if str(user_id).isdigit():
                logger.info(u"Tautulli Users :: Deleting all history for user id %s from database." % user_id)
                session_history_media_info_del = \
                    monitor_db.action('DELETE FROM '
                                      'session_history_media_info '
                                      'WHERE session_history_media_info.id IN (SELECT session_history_media_info.id '
                                      'FROM session_history_media_info '
                                      'JOIN session_history ON session_history_media_info.id = session_history.id '
                                      'WHERE session_history.user_id = ?)', [user_id])
                session_history_metadata_del = \
                    monitor_db.action('DELETE FROM '
                                      'session_history_metadata '
                                      'WHERE session_history_metadata.id IN (SELECT session_history_metadata.id '
                                      'FROM session_history_metadata '
                                      'JOIN session_history ON session_history_metadata.id = session_history.id '
                                      'WHERE session_history.user_id = ?)', [user_id])
                session_history_del = \
                    monitor_db.action('DELETE FROM '
                                      'session_history '
                                      'WHERE session_history.user_id = ?', [user_id])

                return 'Deleted all items for user_id %s.' % user_id
            else:
                return 'Unable to delete items. Input user_id not valid.'
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for delete_all_history: %s." % e)

    def delete(self, user_id=None):
        monitor_db = database.MonitorDatabase()

        try:
            if str(user_id).isdigit():
                self.delete_all_history(user_id)
                logger.info(u"Tautulli Users :: Deleting user with id %s from database." % user_id)
                monitor_db.action('UPDATE users SET deleted_user = 1 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET keep_history = 0 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET do_notify = 0 WHERE user_id = ?', [user_id])

                return 'Deleted user with id %s.' % user_id
            else:
                return 'Unable to delete user, user_id not valid.'
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for delete: %s." % e)

    def undelete(self, user_id=None, username=None):
        monitor_db = database.MonitorDatabase()

        try:
            if user_id and str(user_id).isdigit():
                logger.info(u"Tautulli Users :: Re-adding user with id %s to database." % user_id)
                monitor_db.action('UPDATE users SET deleted_user = 0 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET keep_history = 1 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET do_notify = 1 WHERE user_id = ?', [user_id])

                return 'Re-added user with id %s.' % user_id
            elif username:
                logger.info(u"Tautulli Users :: Re-adding user with username %s to database." % username)
                monitor_db.action('UPDATE users SET deleted_user = 0 WHERE username = ?', [username])
                monitor_db.action('UPDATE users SET keep_history = 1 WHERE username = ?', [username])
                monitor_db.action('UPDATE users SET do_notify = 1 WHERE username = ?', [username])

                return 'Re-added user with username %s.' % username
            else:
                return 'Unable to re-add user, user_id or username not valid.'
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for undelete: %s." % e)

    # Keep method for PlexWatch/Plexivity import
    def get_user_id(self, user=None):
        if user:
            try:
                monitor_db = database.MonitorDatabase()
                query = 'SELECT user_id FROM users WHERE username = ?'
                result = monitor_db.select_single(query, args=[user])
                if result:
                    return result['user_id']
                else:
                    return None
            except:
                return None

        return None

    def get_user_names(self, kwargs=None):
        monitor_db = database.MonitorDatabase()
        
        user_cond = ''
        if session.get_session_user_id():
            user_cond = 'AND user_id = %s ' % session.get_session_user_id()

        try:
            query = 'SELECT user_id, ' \
                    '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" \
                    THEN users.username ELSE users.friendly_name END) AS friendly_name ' \
                    'FROM users ' \
                    'WHERE deleted_user = 0 %s' % user_cond

            result = monitor_db.select(query)
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_user_names: %s." % e)
            return None
        
        return session.friendly_name_to_username(result)
    
    def get_tokens(self, user_id=None):
        if user_id:
            try:
                monitor_db = database.MonitorDatabase()
                query = 'SELECT allow_guest, user_token, server_token FROM users ' \
                        'WHERE user_id = ? AND deleted_user = 0'
                result = monitor_db.select_single(query, args=[user_id])
                if result:
                    tokens = {'allow_guest': result['allow_guest'],
                              'user_token': result['user_token'],
                              'server_token': result['server_token']
                              }
                    return tokens
                else:
                    return None
            except:
                return None

        return None

    def get_filters(self, user_id=None):
        import urlparse

        if not user_id:
            return {}

        try:
            monitor_db = database.MonitorDatabase()
            query = 'SELECT filter_all, filter_movies, filter_tv, filter_music, filter_photos FROM users ' \
                    'WHERE user_id = ?'
            result = monitor_db.select_single(query, args=[user_id])
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_filters: %s." % e)
            result = {}

        filters_list = {}
        for k, v in result.iteritems():
            filters = {}
                
            for f in v.split('|'):
                if 'contentRating=' in f or 'label=' in f:
                    filters.update(dict(urlparse.parse_qsl(f)))
                        
            filters['content_rating'] = tuple(f for f in filters.pop('contentRating', '').split(',') if f)
            filters['labels'] = tuple(f for f in filters.pop('label', '').split(',') if f)

            filters_list[k] = filters

        return filters_list

    def set_user_login(self, user_id=None, user=None, user_group=None, ip_address=None, host=None, user_agent=None, success=0):

        if user_id is None or str(user_id).isdigit():
            monitor_db = database.MonitorDatabase()

            keys = {'timestamp': int(time.time()),
                    'user_id': user_id}

            values = {'user': user,
                      'user_group': user_group,
                      'ip_address': ip_address,
                      'host': host,
                      'user_agent': user_agent,
                      'success': success}

            try:
                monitor_db.upsert(table_name='user_login', key_dict=keys, value_dict=values)
            except Exception as e:
                logger.warn(u"Tautulli Users :: Unable to execute database query for set_login_log: %s." % e)

    def get_datatables_user_login(self, user_id=None, kwargs=None):
        default_return = {'recordsFiltered': 0,
                          'recordsTotal': 0,
                          'draw': 0,
                          'data': 'null',
                          'error': 'Unable to execute database query.'}

        if not session.allow_session_user(user_id):
            return default_return

        data_tables = datatables.DataTables()

        if session.get_session_user_id():
            custom_where = [['user_login.user_id', session.get_session_user_id()]]
        else:
            custom_where = [['user_login.user_id', user_id]] if user_id else []

        columns = ['user_login.timestamp',
                   'user_login.user_id',
                   'user_login.user',
                   'user_login.user_group',
                   'user_login.ip_address',
                   'user_login.host',
                   'user_login.user_agent',
                   'user_login.success',
                   '(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = "" \
                    THEN users.username ELSE users.friendly_name END) AS friendly_name'
                   ]

        try:
            query = data_tables.ssp_query(table_name='user_login',
                                          columns=columns,
                                          custom_where=custom_where,
                                          group_by=[],
                                          join_types=['LEFT OUTER JOIN'],
                                          join_tables=['users'],
                                          join_evals=[['user_login.user_id', 'users.user_id']],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for get_datatables_user_login: %s." % e)
            return default_return

        results = query['result']

        rows = []
        for item in results:
            (os, browser) = httpagentparser.simple_detect(item['user_agent'])

            row = {'timestamp': item['timestamp'],
                   'user_id': item['user_id'],
                   'user_group': item['user_group'],
                   'ip_address': item['ip_address'],
                   'host': item['host'],
                   'user_agent': item['user_agent'],
                   'os': os,
                   'browser': browser,
                   'success': item['success'],
                   'friendly_name': item['friendly_name'] or item['user']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': session.friendly_name_to_username(rows),
                'draw': query['draw']
                }

        return dict

    def delete_login_log(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info(u"Tautulli Users :: Clearing login logs from database.")
            monitor_db.action('DELETE FROM user_login')
            monitor_db.action('VACUUM')
            return True
        except Exception as e:
            logger.warn(u"Tautulli Users :: Unable to execute database query for delete_login_log: %s." % e)
            return False