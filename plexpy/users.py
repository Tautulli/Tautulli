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

    def get_user_list(self, kwargs=None):
        data_tables = datatables.DataTables()

        custom_where = ['users.deleted_user', 0]

        columns = ['session_history.id',
                   'users.user_id as user_id',
                   'users.custom_avatar_url as user_thumb',
                   '(case when users.friendly_name is null then users.username else \
                    users.friendly_name end) as friendly_name',
                   'MAX(session_history.started) as last_seen',
                   'session_history.ip_address as ip_address',
                   'COUNT(session_history.id) as plays',
                   'session_history.platform as platform',
                   'session_history.player as player',
                   'session_history_metadata.full_title as last_watched',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history.rating_key as rating_key',
                   'session_history_media_info.video_decision',
                   'users.username as user',
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
        except:
            logger.warn("Unable to execute database query.")
            return {'recordsFiltered': 0,
                    'recordsTotal': 0,
                    'draw': 0,
                    'data': 'null',
                    'error': 'Unable to execute database query.'}

        users = query['result']

        rows = []
        for item in users:
            if item["media_type"] == 'episode' and item["parent_thumb"]:
                thumb = item["parent_thumb"]
            elif item["media_type"] == 'episode':
                thumb = item["grandparent_thumb"]
            else:
                thumb = item["thumb"]

            if not item['user_thumb'] or item['user_thumb'] == '':
                user_thumb = common.DEFAULT_USER_THUMB
            else:
                user_thumb = item['user_thumb']

            # Rename Mystery platform names
            platform = common.PLATFORM_NAME_OVERRIDES.get(item["platform"], item["platform"])

            # Sanitize player name
            player = helpers.sanitize(item["player"])

            row = {"id": item['id'],
                   "plays": item['plays'],
                   "last_seen": item['last_seen'],
                   "friendly_name": item['friendly_name'],
                   "ip_address": item['ip_address'],
                   "platform": platform,
                   "player": player,
                   "last_watched": item['last_watched'],
                   "thumb": thumb,
                   "media_type": item['media_type'],
                   "rating_key": item['rating_key'],
                   "video_decision": item['video_decision'],
                   "user_thumb": user_thumb,
                   "user": item["user"],
                   "user_id": item['user_id'],
                   "do_notify": helpers.checked(item['do_notify']),
                   "keep_history": helpers.checked(item['keep_history'])
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
        }

        return dict

    def get_user_unique_ips(self, kwargs=None, custom_where=None):
        data_tables = datatables.DataTables()

        # Change custom_where column name due to ambiguous column name after JOIN
        custom_where[0][0] = 'custom_user_id' if custom_where[0][0] == 'user_id' else custom_where[0][0]

        columns = ['session_history.id',
                   'session_history.started as last_seen',
                   'session_history.ip_address as ip_address',
                   'COUNT(session_history.id) as play_count',
                   'session_history.platform as platform',
                   'session_history.player as player',
                   'session_history_metadata.full_title as last_watched',
                   'session_history_metadata.thumb',
                   'session_history_metadata.parent_thumb',
                   'session_history_metadata.grandparent_thumb',
                   'session_history_metadata.media_type',
                   'session_history.rating_key as rating_key',
                   'session_history_media_info.video_decision',
                   'session_history.user as user',
                   'session_history.user_id as custom_user_id',
                   '(case when users.friendly_name is null then users.username else \
                    users.friendly_name end) as friendly_name'
                   ]

        try:
            query = data_tables.ssp_query(table_name='session_history',
                                          columns=columns,
                                          custom_where=custom_where,
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
        except:
            logger.warn("Unable to execute database query.")
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

            # Sanitize player name
            player = helpers.sanitize(item["player"])

            row = {"id": item['id'],
                   "last_seen": item['last_seen'],
                   "ip_address": item['ip_address'],
                   "play_count": item['play_count'],
                   "platform": platform,
                   "player": player,
                   "last_watched": item['last_watched'],
                   "thumb": thumb,
                   "media_type": item['media_type'],
                   "rating_key": item['rating_key'],
                   "video_decision": item['video_decision'],
                   "friendly_name": item['friendly_name']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
        }

        return dict

    # TODO: The getter and setter for this needs to become a config getter/setter for more than just friendlyname
    def set_user_friendly_name(self, user=None, user_id=None, friendly_name=None, do_notify=0, keep_history=1):
        if user_id:
            if friendly_name.strip() == '':
                friendly_name = None

            monitor_db = database.MonitorDatabase()

            control_value_dict = {"user_id": user_id}
            new_value_dict = {"friendly_name": friendly_name,
                              "do_notify": do_notify,
                              "keep_history": keep_history}
            try:
                monitor_db.upsert('users', new_value_dict, control_value_dict)
            except Exception, e:
                logger.debug(u"Uncaught exception %s" % e)
        if user:
            if friendly_name.strip() == '':
                friendly_name = None

            monitor_db = database.MonitorDatabase()

            control_value_dict = {"username": user}
            new_value_dict = {"friendly_name": friendly_name,
                              "do_notify": do_notify,
                              "keep_history": keep_history}
            try:
                monitor_db.upsert('users', new_value_dict, control_value_dict)
            except Exception, e:
                logger.debug(u"Uncaught exception %s" % e)

    def set_user_profile_url(self, user=None, user_id=None, profile_url=None):
        if user_id:
            if profile_url.strip() == '':
                profile_url = None

            monitor_db = database.MonitorDatabase()

            control_value_dict = {"user_id": user_id}
            new_value_dict = {"custom_avatar_url": profile_url}
            try:
                monitor_db.upsert('users', new_value_dict, control_value_dict)
            except Exception, e:
                logger.debug(u"Uncaught exception %s" % e)
        if user:
            if profile_url.strip() == '':
                profile_url = None

            monitor_db = database.MonitorDatabase()

            control_value_dict = {"username": user}
            new_value_dict = {"custom_avatar_url": profile_url}
            try:
                monitor_db.upsert('users', new_value_dict, control_value_dict)
            except Exception, e:
                logger.debug(u"Uncaught exception %s" % e)

    def get_user_friendly_name(self, user=None, user_id=None):
        if user_id:
            monitor_db = database.MonitorDatabase()
            query = 'select username, ' \
                    '(CASE WHEN friendly_name IS NULL THEN username ELSE friendly_name END),' \
                    'do_notify, keep_history, custom_avatar_url as thumb ' \
                    'FROM users WHERE user_id = ?'
            result = monitor_db.select(query, args=[user_id])
            if result:
                user_detail = {'user_id': user_id,
                               'user': result[0][0],
                               'friendly_name': result[0][1],
                               'thumb': result[0][4],
                               'do_notify': helpers.checked(result[0][2]),
                               'keep_history': helpers.checked(result[0][3])
                               }
                return user_detail
            else:
                user_detail = {'user_id': user_id,
                               'user': '',
                               'friendly_name': '',
                               'do_notify': '',
                               'thumb': '',
                               'keep_history': ''}
                return user_detail
        elif user:
            monitor_db = database.MonitorDatabase()
            query = 'select user_id, ' \
                    '(CASE WHEN friendly_name IS NULL THEN username ELSE friendly_name END),' \
                    'do_notify, keep_history, custom_avatar_url as thumb  ' \
                    'FROM users WHERE username = ?'
            result = monitor_db.select(query, args=[user])
            if result:
                user_detail = {'user_id': result[0][0],
                               'user': user,
                               'friendly_name': result[0][1],
                               'thumb': result[0][4],
                               'do_notify': helpers.checked(result[0][2]),
                               'keep_history': helpers.checked(result[0][3])}
                return user_detail
            else:
                user_detail = {'user_id': None,
                               'user': user,
                               'friendly_name': '',
                               'do_notify': '',
                               'thumb': '',
                               'keep_history': ''}
                return user_detail

        return None

    def get_user_id(self, user=None):
        if user:
            try:
                monitor_db = database.MonitorDatabase()
                query = 'select user_id FROM users WHERE username = ?'
                result = monitor_db.select_single(query, args=[user])
                if result:
                    return result
                else:
                    return None
            except:
                return None

        return None

    def get_user_details(self, user=None, user_id=None):
        from plexpy import plextv

        monitor_db = database.MonitorDatabase()

        if user:
            query = 'SELECT user_id, username, friendly_name, email, ' \
                    'custom_avatar_url as thumb, is_home_user, is_allow_sync, is_restricted, do_notify ' \
                    'FROM users ' \
                    'WHERE username = ? ' \
                    'UNION ALL ' \
                    'SELECT null, user, null, null, null, null, null, null, null ' \
                    'FROM session_history ' \
                    'WHERE user = ? ' \
                    'GROUP BY user ' \
                    'LIMIT 1'
            result = monitor_db.select(query, args=[user, user])
        elif user_id:
            query = 'SELECT user_id, username, friendly_name, email, ' \
                    'custom_avatar_url as thumb, is_home_user, is_allow_sync, is_restricted, do_notify ' \
                    'FROM users ' \
                    'WHERE user_id = ? ' \
                    'UNION ALL ' \
                    'SELECT user_id, user, null, null, null, null, null, null, null ' \
                    'FROM session_history ' \
                    'WHERE user_id = ? ' \
                    'GROUP BY user ' \
                    'LIMIT 1'
            result = monitor_db.select(query, args=[user_id, user_id])
        else:
            result = None

        if result:
            user_details = {}
            for item in result:
                if not item['friendly_name']:
                    friendly_name = item['username']
                else:
                    friendly_name = item['friendly_name']
                if not item['thumb'] or item['thumb'] == '':
                    user_thumb = common.DEFAULT_USER_THUMB
                else:
                    user_thumb = item['thumb']

                user_details = {"user_id": item['user_id'],
                                "username": item['username'],
                                "friendly_name": friendly_name,
                                "email": item['email'],
                                "thumb": user_thumb,
                                "is_home_user": item['is_home_user'],
                                "is_allow_sync": item['is_allow_sync'],
                                "is_restricted": item['is_restricted'],
                                "do_notify": item['do_notify']
                                }
            return user_details
        else:
            logger.warn(u"PlexPy :: Unable to retrieve user from local database. Requesting user list refresh.")
            # Let's first refresh the user list to make sure the user isn't newly added and not in the db yet
            if user:
                # Refresh users
                plextv.refresh_users()
                query = 'SELECT user_id, username, friendly_name, email, ' \
                        'custom_avatar_url as thumb, is_home_user, is_allow_sync, is_restricted, do_notify ' \
                        'FROM users ' \
                        'WHERE username = ? ' \
                        'UNION ALL ' \
                        'SELECT null, user, null, null, null, null, null, null, null ' \
                        'FROM session_history ' \
                        'WHERE user = ? ' \
                        'GROUP BY user ' \
                        'LIMIT 1'
                result = monitor_db.select(query, args=[user, user])
            elif user_id:
                # Refresh users
                plextv.refresh_users()
                query = 'SELECT user_id, username, friendly_name, email, ' \
                        'custom_avatar_url as thumb, is_home_user, is_allow_sync, is_restricted, do_notify ' \
                        'FROM users ' \
                        'WHERE user_id = ? ' \
                        'UNION ALL ' \
                        'SELECT user_id, user, null, null, null, null, null, null, null ' \
                        'FROM session_history ' \
                        'WHERE user_id = ? ' \
                        'GROUP BY user ' \
                        'LIMIT 1'
                result = monitor_db.select(query, args=[user_id, user_id])
            else:
                result = None

            if result:
                user_details = {}
                for item in result:
                    if not item['friendly_name']:
                        friendly_name = item['username']
                    else:
                        friendly_name = item['friendly_name']
                    if not item['thumb'] or item['thumb'] == '':
                        user_thumb = common.DEFAULT_USER_THUMB
                    else:
                        user_thumb = item['thumb']

                    user_details = {"user_id": item['user_id'],
                                    "username": item['username'],
                                    "friendly_name": friendly_name,
                                    "email": item['email'],
                                    "thumb": user_thumb,
                                    "is_home_user": item['is_home_user'],
                                    "is_allow_sync": item['is_allow_sync'],
                                    "is_restricted": item['is_restricted'],
                                    "do_notify": item['do_notify']
                                    }
                return user_details
            else:
                # If there is no user data we must return something
                # Use "Local" user to retain compatibility with PlexWatch database value
                return {"user_id": None,
                        "username": 'Local',
                        "friendly_name": 'Local',
                        "email": '',
                        "thumb": '',
                        "is_home_user": 0,
                        "is_allow_sync": 0,
                        "is_restricted": 0,
                        "do_notify": 0
                        }

    def get_user_watch_time_stats(self, user=None, user_id=None):
        monitor_db = database.MonitorDatabase()

        time_queries = [1, 7, 30, 0]
        user_watch_time_stats = []

        for days in time_queries:
            if days > 0:
                if user_id:
                    query = 'SELECT (SUM(stopped - started) - ' \
                            'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                            'COUNT(id) AS total_plays ' \
                            'FROM session_history ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                            'AND user_id = ?' % days
                    result = monitor_db.select(query, args=[user_id])
                elif user:
                    query = 'SELECT (SUM(stopped - started) - ' \
                            'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                            'COUNT(id) AS total_plays ' \
                            'FROM session_history ' \
                            'WHERE datetime(stopped, "unixepoch", "localtime") >= datetime("now", "-%s days", "localtime") ' \
                            'AND user = ?' % days
                    result = monitor_db.select(query, args=[user])
            else:
                query = 'SELECT (SUM(stopped - started) - ' \
                        'SUM(CASE WHEN paused_counter is null THEN 0 ELSE paused_counter END)) as total_time, ' \
                        'COUNT(id) AS total_plays ' \
                        'FROM session_history ' \
                        'WHERE user = ?'
                result = monitor_db.select(query, args=[user])

            for item in result:
                if item[0]:
                    total_time = item[0]
                    total_plays = item[1]
                else:
                    total_time = 0
                    total_plays = 0

                row = {'query_days': days,
                       'total_time': total_time,
                       'total_plays': total_plays
                       }

                user_watch_time_stats.append(row)

        return user_watch_time_stats

    def get_user_player_stats(self, user=None, user_id=None):
        monitor_db = database.MonitorDatabase()

        player_stats = []
        result_id = 0

        try:
            if user_id:
                query = 'SELECT player, COUNT(player) as player_count, platform ' \
                        'FROM session_history ' \
                        'WHERE user_id = ? ' \
                        'GROUP BY player ' \
                        'ORDER BY player_count DESC'
                result = monitor_db.select(query, args=[user_id])
            else:
                query = 'SELECT player, COUNT(player) as player_count, platform ' \
                        'FROM session_history ' \
                        'WHERE user = ? ' \
                        'GROUP BY player ' \
                        'ORDER BY player_count DESC'
                result = monitor_db.select(query, args=[user])
        except:
            logger.warn("Unable to execute database query.")
            return None

        for item in result:
            # Rename Mystery platform names
            platform_type = common.PLATFORM_NAME_OVERRIDES.get(item[2], item[2])

            # Sanitize player name
            player = helpers.sanitize(item[0])

            row = {'player_name': player,
                   'platform_type': platform_type,
                   'total_plays': item[1],
                   'result_id': result_id
                   }
            player_stats.append(row)
            result_id += 1

        return player_stats