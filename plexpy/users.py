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

from plexpy import logger, datatables, common, database, helpers


class Users(object):

    def __init__(self):
        pass

    def get_datatables_list(self, kwargs=None):
        data_tables = datatables.DataTables()

        custom_where = ['users.deleted_user', 0]

        columns = ['users.user_id',
                   'users.username',
                   'users.friendly_name',
                   'users.thumb AS user_thumb',
                   'users.custom_avatar_url AS custom_thumb',
                   'COUNT(session_history.id) AS plays',
                   'MAX(session_history.started) AS last_seen',
                   'session_history_metadata.full_title AS last_watched',
                   'session_history.ip_address',
                   'session_history.platform',
                   'session_history.player',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history.rating_key',
                   'session_history_media_info.video_decision',
                   'users.do_notify as do_notify',
                   'users.keep_history as keep_history'
                   ]
        try:
            query = data_tables.ssp_query(table_name='users',
                                          columns=columns,
                                          custom_where=[custom_where],
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
            logger.warn(u"PlexPy Users :: Unable to execute database query for get_list: %s." % e)
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        users = query['result']

        rows = []
        for item in users:
            if item['friendly_name']:
                friendly_name = item['friendly_name']
            else:
                friendly_name = item['username']
                
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
                   'username': item['username'],
                   'friendly_name': item['friendly_name'],
                   'user_thumb': user_thumb,
                   'plays': item['plays'],
                   'last_seen': item['last_seen'],
                   'last_watched': item['last_watched'],
                   'ip_address': item['ip_address'],
                   'platform': platform,
                   'player': item['player'],
                   'thumb': thumb,
                   'media_type': item['media_type'],
                   'rating_key': item['rating_key'],
                   'video_decision': item['video_decision'],
                   'do_notify': helpers.checked(item['do_notify']),
                   'keep_history': helpers.checked(item['keep_history'])
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }

        return dict

    def get_datatables_unique_ips(self, user_id=None, kwargs=None):
        data_tables = datatables.DataTables()

        custom_where = ['users.user_id', user_id]

        columns = ['session_history.id',
                   'session_history.started AS last_seen',
                   'session_history.ip_address',
                   'COUNT(session_history.id) AS play_count',
                   'session_history.platform',
                   'session_history.player',
                   'session_history_metadata.full_title AS last_watched',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history.rating_key',
                   'session_history_media_info.video_decision',
                   'session_history.user',
                   'session_history.user_id as custom_user_id',
                   '(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE \
                    users.friendly_name END) AS friendly_name'
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
            logger.warn(u"PlexPy Users :: Unable to execute database query for get_unique_ips: %s." % e)
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

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
                   'last_watched': item['last_watched'],
                   'thumb': thumb,
                   'media_type': item['media_type'],
                   'rating_key': item['rating_key'],
                   'video_decision': item['video_decision'],
                   'friendly_name': item['friendly_name']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }

        return dict

    def set_config(self, user_id=None, friendly_name='', custom_thumb='', do_notify=1, keep_history=1):
        if str(user_id).isdigit():
            monitor_db = database.MonitorDatabase()

            key_dict = {'user_id': user_id}
            value_dict = {'friendly_name': friendly_name,
                          'custom_avatar_url': custom_thumb,
                          'do_notify': do_notify,
                          'keep_history': keep_history}
            try:
                monitor_db.upsert('users', value_dict, key_dict)
            except Exception as e:
                logger.warn(u"PlexPy Users :: Unable to execute database query for set_config: %s." % e)

    def get_details(self, user_id=None, user=None):
        from plexpy import plextv

        monitor_db = database.MonitorDatabase()
        
        try:
            if str(user_id).isdigit():
                query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                        'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history ' \
                        'FROM users ' \
                        'WHERE user_id = ? '
                result = monitor_db.select(query, args=[user_id])
            elif user:
                query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                        'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history ' \
                        'FROM users ' \
                        'WHERE username = ? '
                result = monitor_db.select(query, args=[user])
            else:
                result = []
        except Exception as e:
            logger.warn(u"PlexPy Users :: Unable to execute database query for get_details: %s." % e)
            result = []

        if result:
            user_details = {}
            for item in result:
                if item['friendly_name']:
                    friendly_name = item['friendly_name']
                else:
                    friendly_name = item['username']

                if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                    user_thumb = item['custom_thumb']
                elif item['user_thumb']:
                    user_thumb = item['user_thumb']
                else:
                    user_thumb = common.DEFAULT_USER_THUMB

                user_details = {'user_id': item['user_id'],
                                'username': item['username'],
                                'friendly_name': friendly_name,
                                'user_thumb': user_thumb,
                                'email': item['email'],
                                'is_home_user': item['is_home_user'],
                                'is_allow_sync': item['is_allow_sync'],
                                'is_restricted': item['is_restricted'],
                                'do_notify': item['do_notify'],
                                'keep_history': item['keep_history']
                                }
            return user_details
        else:
            logger.warn(u"PlexPy Users :: Unable to retrieve user from local database. Requesting user list refresh.")
            # Let's first refresh the user list to make sure the user isn't newly added and not in the db yet
            try:
                if str(user_id).isdigit():
                    # Refresh users
                    plextv.refresh_users()
                    query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                            'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history ' \
                            'FROM users ' \
                            'WHERE user_id = ? '
                    result = monitor_db.select(query, args=[user_id])
                elif user:
                    query = 'SELECT user_id, username, friendly_name, thumb AS user_thumb, custom_avatar_url AS custom_thumb, ' \
                            'email, is_home_user, is_allow_sync, is_restricted, do_notify, keep_history ' \
                            'FROM users ' \
                            'WHERE username = ? '
                    result = monitor_db.select(query, args=[user])
                else:
                    result = []
            except Exception as e:
                logger.warn(u"PlexPy Users :: Unable to execute database query for get_details: %s." % e)
                result = []

            if result:
                user_details = {}
                for item in result:
                    if item['friendly_name']:
                        friendly_name = item['friendly_name']
                    else:
                        friendly_name = item['username']

                    if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                        user_thumb = item['custom_thumb']
                    elif item['user_thumb']:
                        user_thumb = item['user_thumb']
                    else:
                        user_thumb = common.DEFAULT_USER_THUMB

                    user_details = {'user_id': item['user_id'],
                                    'username': item['username'],
                                    'friendly_name': friendly_name,
                                    'user_thumb': user_thumb,
                                    'email': item['email'],
                                    'is_home_user': item['is_home_user'],
                                    'is_allow_sync': item['is_allow_sync'],
                                    'is_restricted': item['is_restricted'],
                                    'do_notify': item['do_notify'],
                                    'keep_history': item['keep_history']
                                    }
                return user_details
            else:
                # If there is no user data we must return something
                # Use "Local" user to retain compatibility with PlexWatch database value
                return {'user_id': None,
                        'username': 'Local',
                        'friendly_name': 'Local',
                        'user_thumb': common.DEFAULT_USER_THUMB,
                        'email': '',
                        'is_home_user': 0,
                        'is_allow_sync': 0,
                        'is_restricted': 0,
                        'do_notify': 0,
                        'keep_history': 0
                        }

    def get_watch_time_stats(self, user_id=None):
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
                logger.warn(u"PlexPy Users :: Unable to execute database query for get_watch_time_stats: %s." % e)
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
            logger.warn(u"PlexPy Users :: Unable to execute database query for get_player_stats: %s." % e)
            result = []

        for item in result:
            # Rename Mystery platform names
            platform_type = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])

            row = {'player_name': item['player'],
                   'platform_type': platform_type,
                   'total_plays': item['player_count'],
                   'result_id': result_id
                   }
            player_stats.append(row)
            result_id += 1

        return player_stats

    def get_recently_watched(self, user_id=None, limit='10'):
        monitor_db = database.MonitorDatabase()
        recently_watched = []

        if not limit.isdigit():
            limit = '10'

        try:
            if str(user_id).isdigit():
                query = 'SELECT session_history.id, session_history.media_type, session_history.rating_key, session_history.parent_rating_key, ' \
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
            logger.warn(u"PlexPy Users :: Unable to execute database query for get_recently_watched: %s." % e)
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
                logger.info(u"PlexPy DataFactory :: Deleting all history for user id %s from database." % user_id)
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
            logger.warn(u"PlexPy Users :: Unable to execute database query for delete_all_history: %s." % e)

    def delete(self, user_id=None):
        monitor_db = database.MonitorDatabase()

        try:
            if str(user_id).isdigit():
                self.delete_all_history(user_id)
                logger.info(u"PlexPy DataFactory :: Deleting user with id %s from database." % user_id)
                monitor_db.action('UPDATE users SET deleted_user = 1 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET keep_history = 0 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET do_notify = 0 WHERE user_id = ?', [user_id])

                return 'Deleted user with id %s.' % user_id
            else:
                return 'Unable to delete user, user_id not valid.'
        except Exception as e:
            logger.warn(u"PlexPy Users :: Unable to execute database query for delete: %s." % e)

    def undelete(self, user_id=None, username=None):
        monitor_db = database.MonitorDatabase()

        try:
            if user_id and str(user_id).isdigit():
                logger.info(u"PlexPy DataFactory :: Re-adding user with id %s to database." % user_id)
                monitor_db.action('UPDATE users SET deleted_user = 0 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET keep_history = 1 WHERE user_id = ?', [user_id])
                monitor_db.action('UPDATE users SET do_notify = 1 WHERE user_id = ?', [user_id])

                return 'Re-added user with id %s.' % user_id
            elif username:
                logger.info(u"PlexPy DataFactory :: Re-adding user with username %s to database." % username)
                monitor_db.action('UPDATE users SET deleted_user = 0 WHERE username = ?', [username])
                monitor_db.action('UPDATE users SET keep_history = 1 WHERE username = ?', [username])
                monitor_db.action('UPDATE users SET do_notify = 1 WHERE username = ?', [username])

                return 'Re-added user with username %s.' % username
            else:
                return 'Unable to re-add user, user_id or username not valid.'
        except Exception as e:
            logger.warn(u"PlexPy Users :: Unable to execute database query for undelete: %s." % e)

    # Keep method for PlexWatch import
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