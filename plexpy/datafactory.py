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

import json
import re

import plexpy
from plexpy import common
from plexpy import database
from plexpy import datatables
from plexpy import helpers
from plexpy import libraries
from plexpy import logger
from plexpy import pmsconnect
from plexpy import session
from plexpy import users

# Temporarily store update_metadata row ids in memory to prevent rating_key collisions
_UPDATE_METADATA_IDS = {
    'grandparent_rating_key_ids': set(),
    'parent_rating_key_ids': set(),
    'rating_key_ids': set()
}


# Cached get_total_duration results, invalidated when history changes
_TOTAL_DURATION_CACHE = {'version': -1, 'values': {}}


# Matches only the row that carries a group's date, so a scan of the
# started index yields one row per group in date order.
_HISTORY_GROUP_DATE = (
    "NOT EXISTS (SELECT 1 FROM session_history AS g "
    "WHERE g.reference_id = session_history.reference_id "
    "AND (g.started > session_history.started "
    "OR (g.started = session_history.started AND g.id > session_history.id)))"
)


# The draw inner joins the metadata table, so a history row without a
# metadata row is not a row of the draw. The bound reads the same set.
_HISTORY_BOUND_JOINS = (
    " JOIN session_history_metadata ON session_history_metadata.id = session_history.id"
)


# How far the scan may walk before it gives up. A filter the started
# index cannot serve never fills a page, so the scan would read the
# whole table for nothing. Raising this keeps the bound on rarer
# filters and costs more on filters that fill no page.
_HISTORY_BOUND_WINDOW = 25000


# The bound reads one row of a group and takes it to stand for the
# group. That holds only for a filter with the same answer for every row
# of the group. A group is consecutive plays of one item by one user, so
# these columns hold across it.
#
# Every other filter runs unbounded. started splits a group by
# definition. rating_key, guid and transcode_decision each vary within a
# group, because a live group spans programmes and a resumed play can
# change decision.
_HISTORY_GROUP_INVARIANT = (
    'session_history.user_id',
    'session_history.user',
    'session_history.section_id',
    'session_history.media_type',
    'session_history.reference_id',
    'media_type_live',
)


def build_history_page_bound(parameters, grouping, where, args):
    """Bound a history draw to the rows its page can hold.

    A draw groups every history row and orders every group to return one
    page, so both grow with the table. A draw ordered by date is a run of
    the started index, so the date of the last group the page holds
    bounds it. Read that date first and return it as a condition on the
    group key.

    Returns an empty list when the draw takes no bound. A search matches
    a row of any date, and an order on another column is not a run of the
    index.
    """
    order = parameters.get('order') or []
    columns = parameters.get('columns') or []
    if len(order) != 1 or (parameters.get('search') or {}).get('value'):
        return []

    column = helpers.cast_to_int(order[0].get('column'))
    if not 0 <= column < len(columns) or columns[column].get('data') != 'date':
        return []

    start = helpers.cast_to_int(parameters.get('start', 0))
    length = helpers.cast_to_int(parameters.get('length', -1))
    if length < 1:
        return []

    # Take as many groups as the page ends at. An activity row can sort
    # above a history row and push it down the page, never up it.
    descending = order[0].get('dir') == 'desc'
    scan_where = where
    if grouping:
        scan_where = (where + ' AND ' if where else 'WHERE ') + _HISTORY_GROUP_DATE
    else:
        scan_where = scan_where or 'WHERE 1'

    # Hold the walk to the window. Reading its edge is a run of the
    # started index on its own.
    scan_where += (" AND session_history.started %s (SELECT %s(started) FROM "
                   "(SELECT started FROM session_history ORDER BY started %s LIMIT %d))"
                   % ('>=' if descending else '<=',
                      'MIN' if descending else 'MAX',
                      'DESC' if descending else 'ASC', _HISTORY_BOUND_WINDOW))

    query = ("SELECT %s(started) AS cutoff, COUNT(*) AS found FROM "
             "(SELECT started FROM session_history %s %s ORDER BY started %s LIMIT ?)"
             % ('MIN' if descending else 'MAX', _HISTORY_BOUND_JOINS, scan_where,
                'DESC' if descending else 'ASC'))

    result = database.MonitorDatabase().select(query, args=args + [start + length])
    cutoff = result[0]['cutoff'] if result else None
    # A scan that stopped short ran out of window or out of table. Either
    # way the page holds every group it found.
    if cutoff is None or result[0]['found'] < start + length:
        return []

    if grouping:
        # A group holds rows either side of the cutoff, so bound the group
        # keys rather than the rows. The aggregates need the whole group.
        condition = ("session_history.reference_id IN "
                     "(SELECT reference_id FROM session_history %s %s started %s ?)"
                     % (_HISTORY_BOUND_JOINS, where + ' AND' if where else 'WHERE',
                        '>=' if descending else '<='))
        return [[condition, args + [cutoff]]]

    return [['session_history.started %s ?' % ('>=' if descending else '<='), cutoff]]



# An aggregate has no value until the rows are grouped, so it cannot
# appear in the WHERE that picks them.
_AGGREGATE = re.compile(r'\b(?:SUM|COUNT|MAX|MIN|GROUP_CONCAT)\s*\(', re.IGNORECASE)

# Shorter than this, a search term matches too much of the table for a
# bound to save the draw any work.
_HISTORY_SEARCH_MIN = 3

_SEARCH_JOINS = (
    ('users.', ' LEFT OUTER JOIN users ON session_history.user_id = users.user_id'),
    ('session_history_metadata.',
     ' JOIN session_history_metadata ON session_history.id = session_history_metadata.id'),
    ('session_history_media_info.',
     ' JOIN session_history_media_info ON session_history.id = session_history_media_info.id'),
)


def build_history_search_bound(parameters, grouping, columns):
    """Prune a searched history draw to the groups that can match it.

    A search is a LIKE on both ends, so no index bounds it by date. It
    still bounds by group. A group whose every row fails the search holds
    no row for the draw to return, so reading the matching group keys
    first leaves the join and the grouping to run over those alone.

    The bound names whole groups, so a group it keeps still aggregates
    over all of its rows.
    """
    search = (parameters.get('search') or {}).get('value')
    if not search:
        return []

    # The bound reads the whole table, which pays only while the term
    # matches few groups. A table searches on every keystroke, so the
    # first letters of a term match nearly everything.
    if len(search) < _HISTORY_SEARCH_MIN:
        return []

    extracted = datatables.extract_columns(columns=columns)
    literals = {name.lower(): literal for name, literal
                in zip(extracted['column_named'], extracted['column_literal'])}

    # The bound has to cover every column the draw's search covers. One
    # column short and it prunes a group the search would return.
    terms = []
    args = []
    for column in parameters.get('columns') or []:
        if not column.get('searchable'):
            continue
        name = column.get('data')
        if not name:
            # The draw searches this column by position, which the bound
            # cannot resolve to an expression.
            return []
        literal = literals.get(name.lower())
        if literal is None:
            # The draw drops a column it does not know, so drop it here.
            continue
        if _AGGREGATE.search(literal):
            # An aggregate has no value until the rows are grouped.
            return []
        terms.append('%s LIKE ?' % literal)
        args.append('%' + search + '%')

    if not terms:
        return []

    joins = ''.join(join for prefix, join in _SEARCH_JOINS
                    if any(prefix in term for term in terms))
    key = 'session_history.reference_id' if grouping else 'session_history.id'

    condition = ("%s IN (SELECT %s FROM session_history%s WHERE %s)"
                 % (key, key, joins, ' OR '.join(terms)))
    return [[condition, args]]


class DataFactory(object):
    """
    Retrieve and process data from the monitor database
    """

    def __init__(self):
        pass

    def get_datatables_history(self, kwargs=None, custom_where=None, grouping=None, include_activity=None,
                               include_archived=False):
        data_tables = datatables.DataTables()

        if custom_where is None:
            custom_where = []

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        if include_activity is None:
            include_activity = plexpy.CONFIG.HISTORY_TABLE_ACTIVITY

        # The sessions table has no reference_id, so a draw filtered by
        # group key holds no live session. Drop the union rather than
        # filter a table on a column it does not have. This is the child
        # table of an expanded history row.
        if any(c[0].startswith('session_history.reference_id') for c in custom_where):
            include_activity = False

        # A guest session may only ever read its own rows. Append the
        # session user as its own ANDed clause. Merging it into a caller's
        # user_id clause turned the filter into user_id IN (asked, session),
        # which widened the result to the asked-for user instead of
        # narrowing it to the session user.
        if session.get_session_user_id():
            custom_where.append(['session_history.user_id', [session.get_session_user_id()]])

        # A named user's rows show even when that user is archived, the same
        # as the graphs. The guest session above names its own user.
        user_columns = ('session_history.user_id', 'session_history.user_id IN', 'session_history.user IN')
        if not include_archived and not any(c[0] in user_columns for c in custom_where):
            # Added before the union where clause is derived from custom_where below
            archived_user_ids = users.Users().get_archived_user_ids()
            if archived_user_ids:
                custom_where.append(['session_history.user_id NOT IN', archived_user_ids])

        # A named library's rows show even when that library is archived.
        if not include_archived and not any(c[0] == 'session_history.section_id IN' for c in custom_where):
            archived_section_ids = libraries.Libraries().get_archived_section_ids()
            if archived_section_ids:
                custom_where.append(['session_history.section_id NOT IN', archived_section_ids])

        group_by = ['session_history.reference_id'] if grouping else ['session_history.id']

        columns = [
            "session_history.reference_id",
            "session_history.id AS row_id",
            "MAX(started) AS date",
            "MIN(started) AS started",
            "MAX(stopped) AS stopped",
            "SUM(CASE WHEN stopped > 0 THEN (stopped - started) ELSE 0 END) - \
             SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS play_duration",
            "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS paused_counter",
            "session_history.view_offset",
            "session_history.user_id",
            "session_history.user",
            "(CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = '' \
             THEN users.username ELSE users.friendly_name END) AS friendly_name",
            "users.thumb AS user_thumb",
            "users.custom_avatar_url AS custom_thumb",
            "users.is_archived AS user_is_archived",
            "(SELECT MAX(is_archived) FROM library_sections "
            "WHERE library_sections.section_id = session_history.section_id) AS library_is_archived",
            "platform",
            "product",
            "player",
            "ip_address",
            "machine_id",
            "location",
            "secure",
            "relayed",
            "session_history.media_type",
            "(CASE WHEN session_history.live = 1 THEN 'live' ELSE session_history.media_type END) \
             AS media_type_live",
            "session_history_metadata.rating_key",
            "session_history_metadata.parent_rating_key",
            "session_history_metadata.grandparent_rating_key",
            "session_history_metadata.full_title",
            "session_history_metadata.title",
            "session_history_metadata.parent_title",
            "session_history_metadata.grandparent_title",
            "session_history_metadata.original_title",
            "session_history_metadata.year",
            "session_history_metadata.media_index",
            "session_history_metadata.parent_media_index",
            "session_history_metadata.thumb",
            "session_history_metadata.parent_thumb",
            "session_history_metadata.grandparent_thumb",
            "session_history.live",
            "session_history_metadata.added_at",
            "session_history_metadata.originally_available_at",
            "session_history_metadata.guid",
            "MAX((CASE WHEN (view_offset IS NULL OR view_offset = '') THEN 0.1 ELSE view_offset * 1.0 END) / \
             (CASE WHEN (session_history_metadata.duration IS NULL OR session_history_metadata.duration = '') \
             THEN 1.0 ELSE session_history_metadata.duration * 1.0 END) * 100) AS percent_complete",
            "session_history_metadata.duration",
            "session_history_metadata.marker_credits_first",
            "session_history_metadata.marker_credits_final",
            "session_history.transcode_decision",
            "COUNT(*) AS group_count",
            "GROUP_CONCAT(session_history.id) AS group_ids",
            "NULL AS state",
            "NULL AS session_key"
            ]

        if include_activity:
            table_name_union = 'sessions'
            # Very hacky way to match the custom where parameters for the unioned table
            custom_where_union = [[c[0].split('.')[-1], c[1]] for c in custom_where]
            group_by_union = ['session_key']

            columns_union = [
                "NULL AS reference_id",
                "NULL AS row_id",
                "started AS date",
                "started",
                "stopped",
                "SUM(CASE WHEN stopped > 0 THEN (stopped - started) ELSE (strftime('%s', 'now') - started) END) - \
                 SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS play_duration",
                "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS paused_counter",
                "view_offset",
                "user_id",
                "user",
                "(CASE WHEN friendly_name IS NULL OR TRIM(friendly_name) = '' \
                 THEN user ELSE friendly_name END) AS friendly_name",
                "NULL AS user_thumb",
                "NULL AS custom_thumb",
                "(SELECT is_archived FROM users WHERE users.user_id = sessions.user_id) AS user_is_archived",
                "(SELECT MAX(is_archived) FROM library_sections "
                "WHERE library_sections.section_id = sessions.section_id) AS library_is_archived",
                "platform",
                "product",
                "player",
                "ip_address",
                "machine_id",
                "location",
                "secure",
                "relayed",
                "media_type",
                "(CASE WHEN live = 1 THEN 'live' ELSE media_type END) AS media_type_live",
                "rating_key",
                "parent_rating_key",
                "grandparent_rating_key",
                "full_title",
                "title",
                "parent_title",
                "grandparent_title",
                "original_title",
                "year",
                "media_index",
                "parent_media_index",
                "thumb",
                "parent_thumb",
                "grandparent_thumb",
                "live",
                "added_at",
                "originally_available_at",
                "guid",
                "MAX((CASE WHEN (view_offset IS NULL OR view_offset = '') THEN 0.1 ELSE view_offset * 1.0 END) / \
                 (CASE WHEN (duration IS NULL OR duration = '') \
                 THEN 1.0 ELSE duration * 1.0 END) * 100) AS percent_complete",
                "duration",
                "NULL AS marker_credits_first",
                "NULL AS marker_credits_final",
                "transcode_decision",
                "NULL AS group_count",
                "NULL AS group_ids",
                "state",
                "session_key"
                ]

        else:
            table_name_union = None
            custom_where_union = group_by_union = columns_union = []

        # Cheap filtered count for draws without a search filter: the 1:1
        # joins cannot change the group count, so count the group keys on
        # the base tables directly instead of materializing the joined,
        # grouped result a second time. Joins are added back only for
        # filters that reference the side tables (same pattern as
        # get_total_duration).
        media_type_live_case = ("(CASE WHEN session_history.live = 1 "
                                "THEN 'live' ELSE session_history.media_type END)")
        count_join_tables = set()
        for c_where in custom_where:
            if 'session_history_metadata.' in c_where[0]:
                count_join_tables.add('session_history_metadata')
            elif 'session_history_media_info.' in c_where[0]:
                count_join_tables.add('session_history_media_info')
        count_joins = ''.join('JOIN %s ON %s.id = session_history.id ' % (t, t)
                              for t in count_join_tables)
        # media_type_live is an output alias of the draw. The queries below
        # pick their own columns, so they name the expression instead.
        count_where, count_args = datatables.build_custom_where(
            [[media_type_live_case + c[0][len('media_type_live'):]
              if c[0].startswith('media_type_live') else c[0], c[1]]
             for c in custom_where])

        history_count = ("SELECT c FROM (SELECT COUNT(DISTINCT %s) AS c "
                         "FROM session_history %s%s)"
                         % (group_by[0], count_joins, count_where))

        if include_activity:
            sessions_alias = ", (CASE WHEN live = 1 THEN 'live' ELSE media_type END) AS media_type_live"
            sessions_where, sessions_args = datatables.build_custom_where(
                [[c[0].split('.')[-1], c[1]] for c in custom_where])
            sessions_count = ("SELECT c FROM (SELECT COUNT(DISTINCT session_key) AS c%s "
                              "FROM sessions %s)" % (sessions_alias, sessions_where))
            filtered_count_query = 'SELECT (%s) + (%s) AS filtered_count' % (history_count, sessions_count)
            filtered_count_args = count_args + sessions_args
        else:
            filtered_count_query = 'SELECT (%s) AS filtered_count' % history_count
            filtered_count_args = count_args

        # An OR-joined filter takes no bound, because ANDing one on would
        # bind to the last term alone. Only one bound ever applies, since
        # a search is what stops the page bound.
        try:
            # Reading a bound parses json_data and queries the database,
            # so it belongs with the draw it serves.
            draw = helpers.process_json_kwargs(json_kwargs=kwargs.get('json_data'))
            page_bound = search_bound = []
            if not any(c[0].endswith(' OR') for c in custom_where):
                # An ungrouped draw returns rows, not groups, so any
                # filter bounds it.
                groupwise = not grouping or all(
                    any(c[0].startswith(column) for column in _HISTORY_GROUP_INVARIANT)
                    for c in custom_where)
                if groupwise:
                    page_bound = build_history_page_bound(
                        draw, grouping, count_where, count_args)
                search_bound = build_history_search_bound(draw, grouping, columns)

            query = data_tables.ssp_query(table_name='session_history',
                                          table_name_union=table_name_union,
                                          columns=columns,
                                          columns_union=columns_union,
                                          custom_where=custom_where + page_bound + search_bound,
                                          custom_where_union=custom_where_union,
                                          group_by=group_by,
                                          group_by_union=group_by_union,
                                          join_types=['LEFT OUTER JOIN',
                                                      'JOIN'],
                                          join_tables=['users',
                                                       'session_history_metadata'],
                                          join_evals=[['session_history.user_id', 'users.user_id'],
                                                      ['session_history.id', 'session_history_metadata.id']],
                                          filtered_count_query=filtered_count_query,
                                          filtered_count_args=filtered_count_args,
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_history: %s." % e)
            return

        history = query['result']

        filter_duration = 0
        total_duration = self.get_total_duration(custom_where=custom_where)

        watched_percent = {'movie': plexpy.CONFIG.MOVIE_WATCHED_PERCENT,
                           'episode': plexpy.CONFIG.TV_WATCHED_PERCENT,
                           'track': plexpy.CONFIG.MUSIC_WATCHED_PERCENT,
                           'photo': 0,
                           'clip': plexpy.CONFIG.TV_WATCHED_PERCENT
                           }

        rows = []

        users_lookup = {}

        for item in history:
            if item['state']:
                # Get user thumb from database for current activity
                if not users_lookup:
                    # Cache user lookup
                    users_lookup = {u['user_id']: u['thumb'] for u in users.Users().get_users()}

                item['user_thumb'] = users_lookup.get(item['user_id'])

            filter_duration += helpers.cast_to_int(item['play_duration'])

            if item['media_type'] == 'episode' and item['parent_thumb']:
                thumb = item['parent_thumb']
            elif item['media_type'] == 'episode':
                thumb = item['grandparent_thumb']
            else:
                thumb = item['thumb']

            if item['live']:
                item['percent_complete'] = 100
            elif item['percent_complete'] is None:
                # A metadata duration of 0 makes the SQL percent
                # expression divide by zero and yield NULL
                item['percent_complete'] = 0

            # A sessions row written by an older version can have no media_type
            base_watched_value = watched_percent.get(item['media_type'], 0) / 4.0

            if item['live'] or helpers.check_watched(
                item['media_type'], item['view_offset'], item['duration'],
                item['marker_credits_first'], item['marker_credits_final']
            ):
                watched_status = 1
            elif item['percent_complete'] >= base_watched_value * 3.0:
                watched_status = 0.75
            elif item['percent_complete'] >= base_watched_value * 2.0:
                watched_status = 0.50
            elif item['percent_complete'] >= base_watched_value:
                watched_status = 0.25
            else:
                watched_status = 0

            # Rename Mystery platform names
            platform = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])

            if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                user_thumb = item['custom_thumb']
            elif item['user_thumb']:
                user_thumb = item['user_thumb']
            else:
                user_thumb = common.DEFAULT_USER_THUMB

            row = {'reference_id': item['reference_id'],
                   'row_id': item['row_id'],
                   'id': item['row_id'],
                   'date': item['date'],
                   'started': item['started'],
                   'stopped': item['stopped'],
                   'duration': item['play_duration'],  # Keep for backwards compatibility
                   'play_duration': item['play_duration'],
                   'paused_counter': item['paused_counter'],
                   'user_id': item['user_id'],
                   'user': item['user'],
                   'friendly_name': item['friendly_name'],
                   'user_thumb': user_thumb,
                   'user_is_archived': item['user_is_archived'],
                   'library_is_archived': item['library_is_archived'],
                   'platform': platform,
                   'product': item['product'],
                   'player': item['player'],
                   'ip_address': item['ip_address'],
                   'live': item['live'],
                   'machine_id': item['machine_id'],
                   'location': item['location'],
                   'secure': item['secure'],
                   'relayed': item['relayed'],
                   'media_type': item['media_type'],
                   'rating_key': item['rating_key'],
                   'parent_rating_key': item['parent_rating_key'],
                   'grandparent_rating_key': item['grandparent_rating_key'],
                   'full_title': item['full_title'],
                   'title': item['title'],
                   'parent_title': item['parent_title'],
                   'grandparent_title': item['grandparent_title'],
                   'original_title': item['original_title'],
                   'year': item['year'],
                   'media_index': item['media_index'],
                   'parent_media_index': item['parent_media_index'],
                   'thumb': thumb,
                   'originally_available_at': item['originally_available_at'],
                   'guid': item['guid'],
                   'transcode_decision': item['transcode_decision'],
                   'percent_complete': int(round(item['percent_complete'])),
                   'watched_status': watched_status,
                   'group_count': item['group_count'],
                   'group_ids': item['group_ids'],
                   'state': item['state'],
                   'session_key': item['session_key']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': session.friendly_name_to_username(rows),
                'draw': query['draw'],
                'filter_duration': helpers.human_duration(filter_duration, units='s'),
                'total_duration': helpers.human_duration(total_duration, units='s')
                }

        return dict

    def get_home_stats(self, grouping=None, time_range=30, stats_type='plays',
                       stats_start=0, stats_count=10, stat_id='', stats_cards=None,
                       section_id=None, user_id=None, before=None, after=None, include_archived=False):
        monitor_db = database.MonitorDatabase()

        time_range = helpers.cast_to_int(time_range)

        stats_start = helpers.cast_to_int(stats_start)
        stats_count = helpers.cast_to_int(stats_count)
        if stat_id:
            stats_cards = [stat_id]
        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES
        if stats_cards is None:
            stats_cards = plexpy.CONFIG.HOME_STATS_CARDS

        where_timeframe = ''
        where_timeframe_args = []
        if before:
            where_timeframe += "AND session_history.started <= ? "
            before_timestamp = helpers.YMD_to_timestamp(before)
            where_timeframe_args.append(before_timestamp)
            if not after:
                after = helpers.YMD_to_timestamp(before) - time_range * 24 * 60 * 60
                where_timeframe += "AND session_history.stopped >= ? "
                where_timeframe_args.append(after)
        if after:
            where_timeframe += "AND session_history.started >= ? "
            after_timestamp = helpers.YMD_to_timestamp(after)
            where_timeframe_args.append(after_timestamp)
            if not before:
                before = helpers.YMD_to_timestamp(after) + time_range * 24 * 60 * 60
                where_timeframe += "AND session_history.stopped <= ? "
                where_timeframe_args.append(before)
        if not (before and after):
            timestamp = helpers.timestamp() - time_range * 24 * 60 * 60
            where_timeframe += "AND session_history.stopped >= ? "
            where_timeframe_args.append(timestamp)

        where_id = ''
        where_id_args = []
        if section_id:
            where_id += 'AND session_history.section_id = ? '
            where_id_args.append(section_id)
        elif not include_archived:
            where_id += libraries.archived_library_cond()
        if user_id:
            where_id += 'AND session_history.user_id = ? '
            where_id_args.append(user_id)
        elif not include_archived:
            where_id += users.archived_user_cond()

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'
        sort_type = 'total_duration' if stats_type == 'duration' else 'total_plays'

        home_stats = []

        # Each top/popular card pair aggregates the same rows and differs
        # only in ordering, so the (superset) query runs once per media
        # type without LIMIT and each card sorts and slices in Python
        stats_start = helpers.cast_to_int(stats_start)
        stats_count = helpers.cast_to_int(stats_count)
        pair_cache = {}

        def _pair_rows(media_type, identity_columns, outer_group_by, extra_inner_columns=''):
            if media_type not in pair_cache:
                query = "SELECT %s, " \
                        "COUNT(DISTINCT sh.user_id) AS users_watched, " \
                        "MAX(sh.started) AS last_watch, COUNT(sh.id) AS total_plays, SUM(sh.d) AS total_duration " \
                        "FROM (SELECT id, media_type, section_id, started, user_id%s, " \
                        "       SUM(CASE WHEN stopped > 0 THEN (stopped - started) - " \
                        "       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) " \
                        "       AS d " \
                        "   FROM session_history " \
                        "   WHERE session_history.media_type = '%s' %s %s " \
                        "   GROUP BY %s) AS sh " \
                        "JOIN session_history_metadata AS shm ON shm.id = sh.id " \
                        "GROUP BY %s " % (identity_columns, extra_inner_columns, media_type,
                                          where_timeframe, where_id, group_by, outer_group_by)
                pair_cache[media_type] = monitor_db.select(
                    query, args=where_timeframe_args + where_id_args)
            return pair_cache[media_type]

        def _top_slice(rows):
            rows = sorted(rows, key=lambda k: (-(k[sort_type] or 0), -(k['started'] or 0)))
            return rows[stats_start:stats_start + stats_count]

        def _popular_slice(rows):
            rows = sorted(rows, key=lambda k: (-(k['users_watched'] or 0),
                                               -(k[sort_type] or 0), -(k['started'] or 0)))
            return rows[stats_start:stats_start + stats_count]

        _movie_pair = ("sh.id, shm.full_title, shm.year, sh.rating_key, shm.thumb, "
                       "sh.section_id, shm.art, sh.media_type, shm.content_rating, shm.rating, "
                       "shm.labels, sh.started, shm.live, shm.guid",
                       "shm.full_title, shm.year",
                       ", rating_key")
        _tv_pair = ("sh.id, shm.grandparent_title, sh.grandparent_rating_key, "
                    "shm.grandparent_thumb, sh.section_id, "
                    "shm.year, sh.rating_key, shm.art, sh.media_type, "
                    "shm.content_rating, shm.rating, shm.labels, sh.started, shm.live, shm.guid",
                    "shm.grandparent_title",
                    ", grandparent_rating_key, rating_key")
        _music_pair = ("sh.id, shm.grandparent_title, shm.original_title, shm.year, "
                       "sh.grandparent_rating_key, shm.grandparent_thumb, sh.section_id, "
                       "shm.art, sh.media_type, shm.content_rating, shm.rating, shm.labels, "
                       "sh.started, shm.live, shm.guid",
                       "shm.original_title, shm.grandparent_title",
                       ", grandparent_rating_key")

        for stat in stats_cards:
            if stat == 'top_movies':
                top_movies = []
                try:
                    result = _top_slice(_pair_rows('movie', *_movie_pair))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_movies: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['full_title'],
                           'year': item['year'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'users_watched': '',
                           'rating_key': item['rating_key'],
                           'grandparent_rating_key': '',
                           'last_play': item['last_watch'],
                           'grandparent_thumb': '',
                           'thumb': item['thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    top_movies.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Watched Movies',
                                   'rows': session.mask_session_info(top_movies)})

            elif stat == 'popular_movies':
                popular_movies = []
                try:
                    result = _popular_slice(_pair_rows('movie', *_movie_pair))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: popular_movies: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['full_title'],
                           'year': item['year'],
                           'users_watched': item['users_watched'],
                           'rating_key': item['rating_key'],
                           'grandparent_rating_key': '',
                           'last_play': item['last_watch'],
                           'total_plays': item['total_plays'],
                           'grandparent_thumb': '',
                           'thumb': item['thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    popular_movies.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Popular Movies',
                                   'rows': session.mask_session_info(popular_movies)})

            elif stat == 'top_tv':
                top_tv = []
                try:
                    result = _top_slice(_pair_rows('episode', *_tv_pair))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_tv: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['grandparent_title'],
                           'year': item['year'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'users_watched': '',
                           'rating_key': item['rating_key'] if item['live'] else item['grandparent_rating_key'],
                           'grandparent_rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    top_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Watched TV Shows',
                                   'rows': session.mask_session_info(top_tv)})

            elif stat == 'popular_tv':
                popular_tv = []
                try:
                    result = _popular_slice(_pair_rows('episode', *_tv_pair))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: popular_tv: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['grandparent_title'],
                           'year': item['year'],
                           'users_watched': item['users_watched'],
                           'rating_key': item['rating_key'] if item['live'] else item['grandparent_rating_key'],
                           'grandparent_rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'total_plays': item['total_plays'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    popular_tv.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Popular TV Shows',
                                   'rows': session.mask_session_info(popular_tv)})

            elif stat == 'top_music':
                top_music = []
                try:
                    result = _top_slice(_pair_rows('track', *_music_pair))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_music: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['original_title'] or item['grandparent_title'],
                           'year': item['year'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'users_watched': '',
                           'rating_key': item['grandparent_rating_key'],
                           'grandparent_rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    top_music.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Played Artists',
                                   'rows': session.mask_session_info(top_music)})

            elif stat == 'popular_music':
                popular_music = []
                try:
                    result = _popular_slice(_pair_rows('track', *_music_pair))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: popular_music: %s." % e)
                    return None

                for item in result:
                    row = {'title': item['original_title'] or item['grandparent_title'],
                           'year': item['year'],
                           'users_watched': item['users_watched'],
                           'rating_key': item['grandparent_rating_key'],
                           'grandparent_rating_key': item['grandparent_rating_key'],
                           'last_play': item['last_watch'],
                           'total_plays': item['total_plays'],
                           'grandparent_thumb': item['grandparent_thumb'],
                           'thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'user': '',
                           'friendly_name': '',
                           'platform': '',
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    popular_music.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Popular Artists',
                                   'rows': session.mask_session_info(popular_music)})

            elif stat == 'top_libraries':
                top_libraries = []
                try:
                    query = "SELECT sh.id, shm.title, shm.grandparent_title, shm.full_title, shm.year, " \
                            "shm.media_index, shm.parent_media_index, " \
                            "sh.rating_key, shm.grandparent_rating_key, shm.thumb, shm.grandparent_thumb, " \
                            "sh.user, sh.user_id, sh.player, sh.section_id, " \
                            "shm.art, sh.media_type, shm.content_rating, shm.labels, shm.live, shm.guid, " \
                            "ls.section_name, ls.section_type, " \
                            "ls.thumb AS library_thumb, ls.custom_thumb_url AS custom_thumb, " \
                            "ls.art AS library_art, ls.custom_art_url AS custom_art, " \
                            "sh.started, " \
                            "MAX(sh.started) AS last_watch, COUNT(sh.id) AS total_plays, SUM(sh.d) AS total_duration " \
                            "FROM (SELECT id, media_type, player, rating_key, section_id, started, user, user_id, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - " \
                            "       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) " \
                            "       AS d " \
                            "   FROM session_history " \
                            "   WHERE %s %s " \
                            "   GROUP BY %s) AS sh " \
                            "JOIN session_history_metadata AS shm ON shm.id = sh.id " \
                            "LEFT OUTER JOIN (SELECT * FROM library_sections WHERE deleted_section = 0) " \
                            "   AS ls ON sh.section_id = ls.section_id " \
                            "GROUP BY sh.section_id " \
                            "ORDER BY %s DESC, sh.started DESC " \
                            "LIMIT %s OFFSET %s " % (where_timeframe[4:], where_id, group_by, sort_type, stats_count, stats_start)
                    result = monitor_db.select(query, args=where_timeframe_args + where_id_args)
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_libraries: %s." % e)
                    return None

                for item in result:
                    if item['custom_thumb'] and item['custom_thumb'] != item['library_thumb']:
                        library_thumb = item['custom_thumb']
                    elif item['library_thumb']:
                        library_thumb = item['library_thumb']
                    else:
                        library_thumb = common.DEFAULT_COVER_THUMB

                    if item['custom_art'] and item['custom_art'] != item['library_art']:
                        library_art = item['custom_art']
                    elif item['library_art'] == common.DEFAULT_LIVE_TV_ART_FULL:
                        library_art = common.DEFAULT_LIVE_TV_ART
                    else:
                        library_art = item['library_art']

                    if not item['grandparent_thumb'] or item['grandparent_thumb'] == '':
                        thumb = item['thumb']
                    else:
                        thumb = item['grandparent_thumb']

                    row = {
                        'total_plays': item['total_plays'],
                        'total_duration': item['total_duration'],
                        'section_type': item['section_type'],
                        'section_name': item['section_name'],
                        'section_id': item['section_id'],
                        'last_play': item['last_watch'],
                        'library_thumb': library_thumb,
                        'library_art': library_art,
                        'thumb': thumb,
                        'grandparent_thumb': item['grandparent_thumb'],
                        'art': item['art'],
                        'user': '',
                        'friendly_name': '',
                        'users_watched': '',
                        'platform': '',
                        'title': item['full_title'],
                        'grandparent_title': item['grandparent_title'],
                        'grandchild_title': item['title'],
                        'year': item['year'],
                        'media_index': item['media_index'],
                        'parent_media_index': item['parent_media_index'],
                        'rating_key': item['rating_key'],
                        'grandparent_rating_key': item['grandparent_rating_key'],
                        'media_type': item['media_type'],
                        'content_rating': item['content_rating'],
                        'labels': item['labels'].split(';') if item['labels'] else (),
                        'live': item['live'],
                        'guid': item['guid'],
                        'row_id': item['id']
                    }
                    top_libraries.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Active Libraries',
                                   'rows': session.mask_session_info(top_libraries)})

            elif stat == 'top_users':
                top_users = []
                try:
                    query = "SELECT sh.id, shm.title, shm.grandparent_title, shm.full_title, shm.year, " \
                            "shm.media_index, shm.parent_media_index, " \
                            "sh.rating_key, shm.grandparent_rating_key, shm.thumb, shm.grandparent_thumb, " \
                            "sh.user, sh.user_id, sh.player, sh.section_id, " \
                            "shm.art, sh.media_type, shm.content_rating, shm.labels, shm.live, shm.guid, " \
                            "u.thumb AS user_thumb, u.custom_avatar_url AS custom_thumb, " \
                            "sh.started, " \
                            "(CASE WHEN u.friendly_name IS NULL OR TRIM(u.friendly_name) = ''" \
                            "   THEN u.username ELSE u.friendly_name END) " \
                            "   AS friendly_name, " \
                            "MAX(sh.started) AS last_watch, COUNT(sh.id) AS total_plays, SUM(sh.d) AS total_duration " \
                            "FROM (SELECT id, media_type, player, rating_key, section_id, started, user, user_id, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - " \
                            "       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) " \
                            "       AS d " \
                            "   FROM session_history " \
                            "   WHERE %s %s " \
                            "   GROUP BY %s) AS sh " \
                            "JOIN session_history_metadata AS shm ON shm.id = sh.id " \
                            "LEFT OUTER JOIN users AS u ON sh.user_id = u.user_id " \
                            "GROUP BY sh.user_id " \
                            "ORDER BY %s DESC, sh.started DESC " \
                            "LIMIT %s OFFSET %s " % (where_timeframe[4:], where_id, group_by, sort_type, stats_count, stats_start)
                    result = monitor_db.select(query, args=where_timeframe_args + where_id_args)
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_users: %s." % e)
                    return None

                for item in result:
                    if item['custom_thumb'] and item['custom_thumb'] != item['user_thumb']:
                        user_thumb = item['custom_thumb']
                    elif item['user_thumb']:
                        user_thumb = item['user_thumb']
                    else:
                        user_thumb = common.DEFAULT_USER_THUMB

                    if not item['grandparent_thumb'] or item['grandparent_thumb'] == '':
                        thumb = item['thumb']
                    else:
                        thumb = item['grandparent_thumb']

                    row = {'user': item['user'],
                           'user_id': item['user_id'],
                           'friendly_name': item['friendly_name'],
                           'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'last_play': item['last_watch'],
                           'user_thumb': user_thumb,
                           'thumb': thumb,
                           'grandparent_thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'users_watched': '',
                           'platform': '',
                           'title': item['full_title'],
                           'grandparent_title': item['grandparent_title'],
                           'grandchild_title': item['title'],
                           'year': item['year'],
                           'media_index': item['media_index'],
                           'parent_media_index': item['parent_media_index'],
                           'rating_key': item['rating_key'],
                           'grandparent_rating_key': item['grandparent_rating_key'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'live': item['live'],
                           'guid': item['guid'],
                           'row_id': item['id']
                           }
                    top_users.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Active Users',
                                   'rows': session.mask_session_info(top_users)})

            elif stat == 'top_platforms':
                top_platform = []

                try:
                    query = "SELECT sh.platform, sh.started, " \
                            "MAX(sh.started) AS last_watch, COUNT(sh.id) AS total_plays, SUM(sh.d) AS total_duration " \
                            "FROM (SELECT id, platform, started, SUM(CASE WHEN stopped > 0 THEN (stopped - started) - " \
                            "       (CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) ELSE 0 END) " \
                            "       AS d " \
                            "   FROM session_history " \
                            "   WHERE %s %s " \
                            "   GROUP BY %s) AS sh " \
                            "GROUP BY sh.platform " \
                            "ORDER BY %s DESC, sh.started DESC " \
                            "LIMIT %s OFFSET %s " % (where_timeframe[4:], where_id, group_by, sort_type, stats_count, stats_start)
                    result = monitor_db.select(query, args=where_timeframe_args + where_id_args)
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: top_platforms: %s." % e)
                    return None

                for item in result:
                    # Rename Mystery platform names
                    platform = common.PLATFORM_NAME_OVERRIDES.get(item['platform'], item['platform'])
                    platform_name = next((v for k, v in common.PLATFORM_NAMES.items() if k in platform.lower()), 'default')

                    row = {'total_plays': item['total_plays'],
                           'total_duration': item['total_duration'],
                           'last_play': item['last_watch'],
                           'platform': platform,
                           'platform_name': platform_name,
                           'title': '',
                           'thumb': '',
                           'grandparent_thumb': '',
                           'art': '',
                           'users_watched': '',
                           'rating_key': '',
                           'grandparent_rating_key': '',
                           'user': '',
                           'friendly_name': '',
                           'row_id': ''
                           }
                    top_platform.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_type': sort_type,
                                   'stat_title': 'Most Active Platforms',
                                   'rows': session.mask_session_info(top_platform, mask_metadata=False)})

            elif stat == 'last_watched':

                movie_watched_percent = plexpy.CONFIG.MOVIE_WATCHED_PERCENT
                tv_watched_percent = plexpy.CONFIG.TV_WATCHED_PERCENT

                if plexpy.CONFIG.WATCHED_MARKER == 1:
                    watched_threshold = (
                        "(CASE WHEN shm.marker_credits_final IS NULL "
                        "THEN sh._duration * (CASE WHEN sh.media_type = 'movie' THEN %d ELSE %d END) / 100.0 "
                        "ELSE shm.marker_credits_final END) "
                        "AS watched_threshold"
                    ) % (movie_watched_percent, tv_watched_percent)
                    watched_where = "_view_offset >= watched_threshold"
                elif plexpy.CONFIG.WATCHED_MARKER == 2:
                    watched_threshold = (
                        "(CASE WHEN shm.marker_credits_first IS NULL "
                        "THEN sh._duration * (CASE WHEN sh.media_type = 'movie' THEN %d ELSE %d END) / 100.0 "
                        "ELSE shm.marker_credits_first END) "
                        "AS watched_threshold"
                    ) % (movie_watched_percent, tv_watched_percent)
                    watched_where = "_view_offset >= watched_threshold"
                elif plexpy.CONFIG.WATCHED_MARKER == 3:
                    watched_threshold = (
                        "MIN("
                        "(CASE WHEN shm.marker_credits_first IS NULL "
                        "THEN sh._duration * (CASE WHEN sh.media_type = 'movie' THEN %d ELSE %d END) / 100.0 "
                        "ELSE shm.marker_credits_first END), "
                        "sh._duration * (CASE WHEN sh.media_type = 'movie' THEN %d ELSE %d END) / 100.0) "
                        "AS watched_threshold"
                    ) % (movie_watched_percent, tv_watched_percent, movie_watched_percent, tv_watched_percent)
                    watched_where = "_view_offset >= watched_threshold"
                else:
                    watched_threshold = "NULL AS watched_threshold"
                    watched_where = (
                        "sh.media_type == 'movie' AND percent_complete >= %d "
                        "OR sh.media_type == 'episode' AND percent_complete >= %d"
                    ) % (movie_watched_percent, tv_watched_percent)

                last_watched = []
                try:
                    query = "SELECT sh.id, shm.title, shm.grandparent_title, shm.full_title, shm.year, " \
                            "shm.media_index, shm.parent_media_index, sh.rating_key, " \
                            "shm.grandparent_rating_key, shm.thumb, shm.grandparent_thumb, sh.user, " \
                            "sh.user_id, u.custom_avatar_url as user_thumb, sh.player, sh.section_id, " \
                            "shm.art, sh.media_type, shm.content_rating, shm.rating, shm.labels, " \
                            "shm.live, shm.guid, " \
                            "(CASE WHEN u.friendly_name IS NULL OR TRIM(u.friendly_name) = ''" \
                            "   THEN u.username ELSE u.friendly_name END) " \
                            "   AS friendly_name, " \
                            "MAX(sh.started) AS last_watch, sh._view_offset, sh._duration, " \
                            "(sh._view_offset / sh._duration * 100) AS percent_complete, " \
                            "%s " \
                            "FROM (SELECT session_history.id, session_history.rating_key, session_history.user, " \
                            "   session_history.user_id, session_history.player, session_history.section_id, " \
                            "   session_history.media_type, session_history.started, MAX(session_history.id), " \
                            "   (CASE WHEN view_offset IS NULL THEN 0.1 ELSE view_offset * 1.0 END) AS _view_offset, " \
                            "   (CASE WHEN duration IS NULL THEN 1.0 ELSE duration * 1.0 END) AS _duration " \
                            "   FROM session_history " \
                            "   JOIN session_history_metadata ON session_history_metadata.id = session_history.id " \
                            "   WHERE (session_history.media_type = 'movie' " \
                            "           OR session_history.media_type = 'episode') %s %s " \
                            "   GROUP BY %s) AS sh " \
                            "JOIN session_history_metadata AS shm ON shm.id = sh.id " \
                            "LEFT OUTER JOIN users AS u ON sh.user_id = u.user_id " \
                            "WHERE %s " \
                            "GROUP BY sh.id " \
                            "ORDER BY last_watch DESC " \
                            "LIMIT %s OFFSET %s" % (watched_threshold,
                                                    where_timeframe, where_id, group_by, watched_where,
                                                    stats_count, stats_start)
                    result = monitor_db.select(query, args=where_timeframe_args + where_id_args)
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: last_watched: %s." % e)
                    return None

                for item in result:
                    if not item['grandparent_thumb'] or item['grandparent_thumb'] == '':
                        thumb = item['thumb']
                    else:
                        thumb = item['grandparent_thumb']

                    row = {'row_id': item['id'],
                           'user': item['user'],
                           'friendly_name': item['friendly_name'],
                           'user_id': item['user_id'],
                           'user_thumb': item['user_thumb'],
                           'title': item['full_title'],
                           'grandparent_title': item['grandparent_title'],
                           'grandchild_title': item['title'],
                           'year': item['year'],
                           'media_index': item['media_index'],
                           'parent_media_index': item['parent_media_index'],
                           'rating_key': item['rating_key'],
                           'grandparent_rating_key': item['grandparent_rating_key'],
                           'thumb': thumb,
                           'grandparent_thumb': item['grandparent_thumb'],
                           'art': item['art'],
                           'section_id': item['section_id'],
                           'media_type': item['media_type'],
                           'content_rating': item['content_rating'],
                           'rating': item['rating'],
                           'labels': item['labels'].split(';') if item['labels'] else (),
                           'last_watch': item['last_watch'],
                           'live': item['live'],
                           'guid': item['guid'],
                           'player': item['player']
                           }
                    last_watched.append(row)

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Recently Watched',
                                   'rows': session.mask_session_info(last_watched)})

            elif stat == 'most_concurrent':

                def calc_most_concurrent(title, times):
                    '''
                    Function to calculate most concurrent streams
                    Input: Stat title, list of start/stop events
                    Output: Dict {title, count, started, stopped}
                    '''
                    times = sorted(times, key=lambda k: k['time'])

                    count = 0
                    last_count = 0
                    last_start = ''
                    concurrent = {'title': title,
                                  'count': 0,
                                  'started': None,
                                  'stopped': None
                                  }

                    for d in times:
                        if d['count'] == 1:
                            count += d['count']
                            if count >= last_count:
                                last_start = d['time']
                        else:
                            if count >= last_count:
                                last_count = count
                                concurrent['count'] = count
                                concurrent['started'] = last_start[:-1]
                                concurrent['stopped'] = d['time'][:-1]
                            count += d['count']

                    return concurrent

                most_concurrent = []

                try:
                    # One pass over the window instead of four filtered
                    # scans of the same rows
                    query = "SELECT sh.started, sh.stopped, shmi.transcode_decision " \
                            "FROM session_history AS sh " \
                            "JOIN session_history_media_info AS shmi ON sh.id = shmi.id " \
                            "WHERE %s %s " % (where_timeframe[4:].replace('session_history.', 'sh.'),
                                              '' if include_archived else
                                              users.archived_user_cond(column='sh.user_id') +
                                              libraries.archived_library_cond(column='sh.section_id'))
                    result = monitor_db.select(query, args=where_timeframe_args)

                    categories = {'Concurrent Streams': None,
                                  'Concurrent Transcodes': 'transcode',
                                  'Concurrent Direct Streams': 'copy',
                                  'Concurrent Direct Plays': 'direct play'
                                  }
                    events = {title: [] for title in categories}

                    for item in result:
                        start_event = {'time': str(item['started']) + 'B', 'count': 1}
                        stop_event = {'time': str(item['stopped']) + 'A', 'count': -1}
                        for title, decision in categories.items():
                            if decision is None or item['transcode_decision'] == decision:
                                events[title].append(start_event)
                                events[title].append(stop_event)

                    for title in categories:
                        if events[title]:
                            most_concurrent.append(calc_most_concurrent(title, events[title]))
                except Exception as e:
                    logger.warn("Tautulli DataFactory :: Unable to execute database query for get_home_stats: most_concurrent: %s." % e)
                    return None

                home_stats.append({'stat_id': stat,
                                   'stat_title': 'Most Concurrent Streams',
                                   'rows': most_concurrent})

        if stat_id and home_stats:
            return home_stats[0]
        return home_stats

    def get_library_stats(self, library_cards=None, include_archived=False):
        if library_cards is None:
            library_cards = []

        monitor_db = database.MonitorDatabase()

        if session.get_session_shared_libraries():
            library_cards = session.get_session_shared_libraries()

        library_stats = []

        try:
            cards_in = ",".join(["?"] * len(library_cards))

            # Find the most recent history row id per section first
            # (served by the (section_id, started) index), then join the
            # wide metadata table for only those few rows. The old form
            # joined every history row of every displayed section to the
            # metadata table just to keep one MAX(started) row per
            # section, on every home page render.
            last_watched = monitor_db.select(
                "SELECT section_id, id AS last_id, MAX(started) "
                "FROM session_history "
                "WHERE section_id IN (%s) %s"
                "GROUP BY section_id" % (cards_in, '' if include_archived else users.archived_user_cond(column='user_id')),
                args=library_cards)
            last_ids = [row['last_id'] for row in last_watched]

            history_by_section = {}
            if last_ids:
                # LEFT JOIN like the old combined query: an orphaned
                # history row without metadata still contributes its
                # session_history fields to the library card
                history_rows = monitor_db.select(
                    "SELECT sh.section_id, sh.id, shm.title, shm.grandparent_title, shm.full_title, shm.year, "
                    "shm.media_index, shm.parent_media_index, "
                    "sh.rating_key, shm.grandparent_rating_key, shm.thumb, shm.grandparent_thumb, "
                    "sh.user, sh.user_id, sh.player, "
                    "shm.art, sh.media_type, shm.content_rating, shm.labels, shm.live, shm.guid, "
                    "sh.started AS last_watch "
                    "FROM session_history AS sh "
                    "LEFT OUTER JOIN session_history_metadata AS shm ON sh.id = shm.id "
                    "WHERE sh.id IN (%s)" % ",".join(["?"] * len(last_ids)),
                    args=last_ids)
                history_by_section = {row['section_id']: row for row in history_rows}

            sections = monitor_db.select(
                "SELECT section_id, section_name, section_type, thumb AS library_thumb, "
                "custom_thumb_url AS custom_thumb, art AS library_art, custom_art_url AS custom_art, "
                "count, parent_count, child_count "
                "FROM library_sections "
                "WHERE section_id IN (%s) AND deleted_section = 0 %s"
                "ORDER BY section_type, count DESC, parent_count DESC, child_count DESC"
                % (cards_in, '' if include_archived else "AND is_archived = 0 "),
                args=library_cards)

            history_defaults = {'id': None, 'title': None, 'grandparent_title': None, 'full_title': None,
                                'year': None, 'media_index': None, 'parent_media_index': None,
                                'rating_key': None, 'grandparent_rating_key': None, 'thumb': None,
                                'grandparent_thumb': None, 'user': None, 'user_id': None, 'player': None,
                                'art': None, 'media_type': None, 'content_rating': None, 'labels': None,
                                'live': None, 'guid': None, 'last_watch': None}

            result = []
            for section in sections:
                row = dict(section)
                row.update(history_by_section.get(section['section_id'], history_defaults))
                result.append(row)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_library_stats: %s." % e)
            return None

        for item in result:
            if item['custom_thumb'] and item['custom_thumb'] != item['library_thumb']:
                library_thumb = item['custom_thumb']
            elif item['library_thumb']:
                library_thumb = item['library_thumb']
            else:
                library_thumb = common.DEFAULT_COVER_THUMB

            if item['custom_art'] and item['custom_art'] != item['library_art']:
                library_art = item['custom_art']
            else:
                library_art = item['library_art']

            if not item['grandparent_thumb'] or item['grandparent_thumb'] == '':
                thumb = item['thumb']
            else:
                thumb = item['grandparent_thumb']

            library = {'section_id': item['section_id'],
                       'section_name': item['section_name'],
                       'section_type': item['section_type'],
                       'library_thumb': library_thumb,
                       'library_art': library_art,
                       'count': item['count'],
                       'child_count': item['parent_count'],
                       'grandchild_count': item['child_count'],
                       'thumb': thumb or '',
                       'grandparent_thumb': item['grandparent_thumb'] or '',
                       'art': item['art'] or '',
                       'title': item['full_title'],
                       'grandparent_title': item['grandparent_title'],
                       'grandchild_title': item['title'],
                       'year': item['year'],
                       'media_index': item['media_index'],
                       'parent_media_index': item['parent_media_index'],
                       'rating_key': item['rating_key'],
                       'grandparent_rating_key': item['grandparent_rating_key'],
                       'media_type': item['media_type'],
                       'content_rating': item['content_rating'],
                       'labels': item['labels'].split(';') if item['labels'] else (),
                       'live': item['live'],
                       'guid': item['guid'],
                       'row_id': item['id']
                       }
            library_stats.append(library)

        library_stats = session.mask_session_info(library_stats)
        library_stats = helpers.group_by_keys(library_stats, 'section_type')

        return library_stats

    def get_watch_time_stats(self, rating_key=None, guid=None, media_type=None, grouping=None, query_days=None,
                             include_archived=False):
        if rating_key is None and guid is None:
            return []

        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        if query_days and query_days is not None:
            query_days = map(helpers.cast_to_int, str(query_days).split(','))
        else:
            query_days = [1, 7, 30, 0]

        timestamp = helpers.timestamp()

        monitor_db = database.MonitorDatabase()

        item_watch_time_stats = []

        section_ids = set()

        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        if media_type in ('collection', 'playlist'):
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_item_children(rating_key=rating_key, media_type=media_type)
            rating_keys = [child['rating_key'] for child in result['children_list']]
        else:
            rating_keys = [rating_key]

        rating_keys_arg = ','.join(['?'] * len(rating_keys))
        archived_cond = '' if include_archived else users.archived_user_cond() + libraries.archived_library_cond()

        for days in query_days:
            timestamp_query = timestamp - days * 24 * 60 * 60

            try:
                if days > 0:
                    if str(rating_key).isdigit():
                        query = "SELECT (SUM(stopped - started) - " \
                                "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, " \
                                "COUNT(DISTINCT %s) AS total_plays, section_id " \
                                "FROM session_history " \
                                "WHERE stopped >= ? " \
                                "AND (session_history.grandparent_rating_key IN (%s) " \
                                "OR session_history.parent_rating_key IN (%s) " \
                                "OR session_history.rating_key IN (%s)) %s" % (
                                    group_by, rating_keys_arg, rating_keys_arg, rating_keys_arg, archived_cond
                                )
                        
                        result = monitor_db.select(query, args=[timestamp_query] + rating_keys * 3)
                    elif guid:
                        query = "SELECT (SUM(stopped - started) - " \
                                "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, " \
                                "COUNT(DISTINCT %s) AS total_plays, section_id " \
                                "FROM session_history " \
                                "JOIN session_history_metadata ON session_history_metadata.id = session_history.id " \
                                "WHERE stopped >= ? " \
                                "AND session_history_metadata.guid = ? %s" % (group_by, archived_cond)

                        result = monitor_db.select(query, args=[timestamp_query, guid])
                    else:
                        result = []
                else:
                    if str(rating_key).isdigit():
                        query = "SELECT (SUM(stopped - started) - " \
                                "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, " \
                                "COUNT(DISTINCT %s) AS total_plays, section_id " \
                                "FROM session_history " \
                                "WHERE (session_history.grandparent_rating_key IN (%s) " \
                                "OR session_history.parent_rating_key IN (%s) " \
                                "OR session_history.rating_key IN (%s)) %s" % (
                                    group_by, rating_keys_arg, rating_keys_arg, rating_keys_arg, archived_cond
                                )
                        
                        result = monitor_db.select(query, args=rating_keys * 3)
                    elif guid:
                        query = "SELECT (SUM(stopped - started) - " \
                                "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, " \
                                "COUNT(DISTINCT %s) AS total_plays, section_id " \
                                "FROM session_history " \
                                "JOIN session_history_metadata ON session_history_metadata.id = session_history.id " \
                                "WHERE session_history_metadata.guid = ? %s" % (group_by, archived_cond)

                        result = monitor_db.select(query, args=[guid])
                    else:
                        result = []
            except Exception as e:
                logger.warn("Tautulli Libraries :: Unable to execute database query for get_watch_time_stats: %s." % e)
                result = []

            for item in result:
                section_ids.add(item['section_id'])

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

                item_watch_time_stats.append(row)

        if any(not session.allow_session_library(section_id) for section_id in section_ids):
            return []

        return item_watch_time_stats

    def get_user_stats(self, rating_key=None, guid=None, media_type=None, grouping=None, include_archived=False):
        if grouping is None:
            grouping = plexpy.CONFIG.GROUP_HISTORY_TABLES

        monitor_db = database.MonitorDatabase()

        user_stats = []

        section_ids = set()
        
        group_by = 'session_history.reference_id' if grouping else 'session_history.id'

        if media_type in ('collection', 'playlist'):
            pms_connect = pmsconnect.PmsConnect()
            result = pms_connect.get_item_children(rating_key=rating_key, media_type=media_type)
            rating_keys = [child['rating_key'] for child in result['children_list']]
        else:
            rating_keys = [rating_key]

        rating_keys_arg = ','.join(['?'] * len(rating_keys))
        archived_cond = '' if include_archived else users.archived_user_cond() + libraries.archived_library_cond()

        try:
            if str(rating_key).isdigit():
                query = "SELECT (CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = '' " \
                        "THEN users.username ELSE users.friendly_name END) AS friendly_name, " \
                        "users.user_id, users.username, users.thumb, users.custom_avatar_url AS custom_thumb, " \
                        "COUNT(DISTINCT %s) AS total_plays, (SUM(stopped - started) - " \
                        "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, " \
                        "section_id " \
                        "FROM session_history " \
                        "JOIN users ON users.user_id = session_history.user_id " \
                        "WHERE (session_history.grandparent_rating_key IN (%s) " \
                        "OR session_history.parent_rating_key IN (%s) " \
                        "OR session_history.rating_key IN (%s)) %s" \
                        "GROUP BY users.user_id " \
                        "ORDER BY total_plays DESC, total_time DESC" % (
                            group_by, rating_keys_arg, rating_keys_arg, rating_keys_arg, archived_cond
                        )

                result = monitor_db.select(query, args=rating_keys * 3)
            elif guid:
                query = "SELECT (CASE WHEN users.friendly_name IS NULL OR TRIM(users.friendly_name) = '' " \
                        "THEN users.username ELSE users.friendly_name END) AS friendly_name, " \
                        "users.user_id, users.username, users.thumb, users.custom_avatar_url AS custom_thumb, " \
                        "COUNT(DISTINCT %s) AS total_plays, (SUM(stopped - started) - " \
                        "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END)) AS total_time, " \
                        "section_id " \
                        "FROM session_history " \
                        "JOIN session_history_metadata ON session_history_metadata.id = session_history.id " \
                        "JOIN users ON users.user_id = session_history.user_id " \
                        "WHERE session_history_metadata.guid = ? %s" \
                        "GROUP BY users.user_id " \
                        "ORDER BY total_plays DESC, total_time DESC" % (group_by, archived_cond)

                result = monitor_db.select(query, args=[guid])
            else:
                result = []
        except Exception as e:
            logger.warn("Tautulli Libraries :: Unable to execute database query for get_user_stats: %s." % e)
            result = []

        for item in result:
            section_ids.add(item['section_id'])

            if item['custom_thumb'] and item['custom_thumb'] != item['thumb']:
                user_thumb = item['custom_thumb']
            elif item['thumb']:
                user_thumb = item['thumb']
            else:
                user_thumb = common.DEFAULT_USER_THUMB

            row = {'friendly_name': item['friendly_name'],
                   'user_id': item['user_id'],
                   'user_thumb': user_thumb,
                   'username': item['username'],
                   'total_plays': item['total_plays'],
                   'total_time': item['total_time']
                   }
            user_stats.append(row)

        if any(not session.allow_session_library(section_id) for section_id in section_ids):
            return []

        return session.mask_session_info(user_stats, mask_metadata=False)

    def get_stream_details(self, row_id=None, session_key=None):
        monitor_db = database.MonitorDatabase()

        user_cond = ''
        table = 'session_history' if row_id else 'sessions'
        if session.get_session_user_id():
            user_cond = "AND %s.user_id = %s " % (table, session.get_session_user_id())

        if row_id:
            query = "SELECT bitrate, video_full_resolution, " \
                    "optimized_version, optimized_version_profile, optimized_version_title, " \
                    "synced_version, synced_version_profile, " \
                    "container, video_codec, video_bitrate, video_width, video_height, video_framerate, " \
                    "video_dynamic_range, aspect_ratio, " \
                    "audio_codec, audio_bitrate, audio_channels, audio_language, audio_language_code, " \
                    "subtitle_codec, subtitle_forced, subtitle_language, " \
                    "stream_bitrate, stream_video_full_resolution, quality_profile, stream_container_decision, stream_container, " \
                    "stream_video_decision, stream_video_codec, stream_video_bitrate, stream_video_width, stream_video_height, " \
                    "stream_video_framerate, stream_video_dynamic_range, " \
                    "stream_audio_decision, stream_audio_codec, stream_audio_bitrate, stream_audio_channels, " \
                    "stream_audio_language, stream_audio_language_code, " \
                    "subtitles, stream_subtitle_decision, stream_subtitle_codec, stream_subtitle_forced, stream_subtitle_language, " \
                    "transcode_hw_decoding, transcode_hw_encoding, " \
                    "video_decision, audio_decision, transcode_decision, width, height, container, " \
                    "transcode_container, transcode_video_codec, transcode_audio_codec, transcode_audio_channels, " \
                    "transcode_width, transcode_height, " \
                    "session_history_metadata.media_type, title, grandparent_title, original_title " \
                    "FROM session_history_media_info " \
                    "JOIN session_history ON session_history_media_info.id = session_history.id " \
                    "JOIN session_history_metadata ON session_history_media_info.id = session_history_metadata.id " \
                    "WHERE session_history_media_info.id = ? %s" % user_cond
            result = monitor_db.select(query, args=[row_id])
        elif session_key:
            query = "SELECT bitrate, video_full_resolution, " \
                    "optimized_version, optimized_version_profile, optimized_version_title, " \
                    "synced_version, synced_version_profile, " \
                    "container, video_codec, video_bitrate, video_width, video_height, video_framerate, " \
                    "video_dynamic_range, aspect_ratio, " \
                    "audio_codec, audio_bitrate, audio_channels, audio_language, audio_language_code, " \
                    "subtitle_codec, subtitle_forced, subtitle_language, " \
                    "stream_bitrate, stream_video_full_resolution, quality_profile, stream_container_decision, stream_container, " \
                    "stream_video_decision, stream_video_codec, stream_video_bitrate, stream_video_width, stream_video_height, " \
                    "stream_video_framerate, stream_video_dynamic_range, " \
                    "stream_audio_decision, stream_audio_codec, stream_audio_bitrate, stream_audio_channels, " \
                    "stream_audio_language, stream_audio_language_code, " \
                    "subtitles, stream_subtitle_decision, stream_subtitle_codec, stream_subtitle_forced, stream_subtitle_language, " \
                    "transcode_hw_decoding, transcode_hw_encoding, " \
                    "video_decision, audio_decision, transcode_decision, width, height, container, " \
                    "transcode_container, transcode_video_codec, transcode_audio_codec, transcode_audio_channels, " \
                    "transcode_width, transcode_height, " \
                    "media_type, title, grandparent_title, original_title " \
                    "FROM sessions " \
                    "WHERE session_key = ? %s" % user_cond
            result = monitor_db.select(query, args=[session_key])
        else:
            return None

        stream_output = {}

        for item in result:
            pre_tautulli = 0

            # For backwards compatibility. Pick one new Tautulli key to check and override with old values.
            if not item['stream_container']:
                item['stream_video_full_resolution'] = item['video_full_resolution']
                item['stream_container'] = item['transcode_container'] or item['container']
                item['stream_video_decision'] = item['video_decision']
                item['stream_video_codec'] = item['transcode_video_codec'] or item['video_codec']
                item['stream_video_width'] = item['transcode_width'] or item['width']
                item['stream_video_height'] = item['transcode_height'] or item['height']
                item['stream_audio_decision'] = item['audio_decision']
                item['stream_audio_codec'] = item['transcode_audio_codec'] or item['audio_codec']
                item['stream_audio_channels'] = item['transcode_audio_channels'] or item['audio_channels']
                item['video_width'] = item['width']
                item['video_height'] = item['height']
                pre_tautulli = 1

            stream_output = {'bitrate': item['bitrate'],
                             'video_full_resolution': common.VIDEO_RESOLUTION_OVERRIDES.get(
                                 item['video_full_resolution'], item['video_full_resolution']),
                             'optimized_version': item['optimized_version'],
                             'optimized_version_profile': item['optimized_version_profile'],
                             'optimized_version_title': item['optimized_version_title'],
                             'synced_version': item['synced_version'],
                             'synced_version_profile': item['synced_version_profile'],
                             'container': item['container'],
                             'video_codec': item['video_codec'],
                             'video_bitrate': item['video_bitrate'],
                             'video_width': item['video_width'],
                             'video_height': item['video_height'],
                             'video_framerate': item['video_framerate'],
                             'video_dynamic_range': item['video_dynamic_range'],
                             'aspect_ratio': item['aspect_ratio'],
                             'audio_codec': item['audio_codec'],
                             'audio_bitrate': item['audio_bitrate'],
                             'audio_channels': item['audio_channels'],
                             'audio_language': item['audio_language'],
                             'audio_language_code': item['audio_language_code'],
                             'subtitle_codec': item['subtitle_codec'],
                             'subtitle_forced': item['subtitle_forced'],
                             'subtitle_language': item['subtitle_language'],
                             'stream_bitrate': item['stream_bitrate'],
                             'stream_video_full_resolution': common.VIDEO_RESOLUTION_OVERRIDES.get(
                                 item['stream_video_full_resolution'], item['stream_video_full_resolution']),
                             'quality_profile': item['quality_profile'],
                             'stream_container_decision': item['stream_container_decision'],
                             'stream_container': item['stream_container'],
                             'stream_video_decision': item['stream_video_decision'],
                             'stream_video_codec': item['stream_video_codec'],
                             'stream_video_bitrate': item['stream_video_bitrate'],
                             'stream_video_width': item['stream_video_width'],
                             'stream_video_height': item['stream_video_height'],
                             'stream_video_framerate': item['stream_video_framerate'],
                             'stream_video_dynamic_range': item['stream_video_dynamic_range'],
                             'stream_audio_decision': item['stream_audio_decision'],
                             'stream_audio_codec': item['stream_audio_codec'],
                             'stream_audio_bitrate': item['stream_audio_bitrate'],
                             'stream_audio_channels': item['stream_audio_channels'],
                             'stream_audio_language': item['stream_audio_language'],
                             'stream_audio_language_code': item['stream_audio_language_code'],
                             'subtitles': item['subtitles'],
                             'stream_subtitle_decision': item['stream_subtitle_decision'],
                             'stream_subtitle_codec': item['stream_subtitle_codec'],
                             'stream_subtitle_forced': item['stream_subtitle_forced'],
                             'stream_subtitle_language': item['stream_subtitle_language'],
                             'transcode_hw_decoding': item['transcode_hw_decoding'],
                             'transcode_hw_encoding': item['transcode_hw_encoding'],
                             'video_decision': item['video_decision'],
                             'audio_decision': item['audio_decision'],
                             'media_type': item['media_type'],
                             'title': item['title'],
                             'grandparent_title': item['grandparent_title'],
                             'original_title': item['original_title'],
                             'current_session': 1 if session_key else 0,
                             'pre_tautulli': pre_tautulli
                             }

        stream_output = {k: v or '' for k, v in stream_output.items()}
        return stream_output

    def get_metadata_details(self, rating_key='', guid=''):
        monitor_db = database.MonitorDatabase()

        if rating_key or guid:
            if guid:
                where = "session_history_metadata.guid LIKE ?"
                args = [guid.split('?')[0] + '%']  # SQLite LIKE wildcard
            else:
                where = "session_history_metadata.rating_key = ?"
                args = [rating_key]

            query = "SELECT session_history.section_id, session_history_metadata.id, " \
                    "session_history_metadata.rating_key, session_history_metadata.parent_rating_key, " \
                    "session_history_metadata.grandparent_rating_key, session_history_metadata.title, " \
                    "session_history_metadata.parent_title, session_history_metadata.grandparent_title, " \
                    "session_history_metadata.original_title, session_history_metadata.full_title, " \
                    "library_sections.section_name, " \
                    "session_history_metadata.media_index, session_history_metadata.parent_media_index, " \
                    "session_history_metadata.thumb, " \
                    "session_history_metadata.parent_thumb, session_history_metadata.grandparent_thumb, " \
                    "session_history_metadata.art, session_history_metadata.media_type, session_history_metadata.year, " \
                    "session_history_metadata.originally_available_at, session_history_metadata.added_at, " \
                    "session_history_metadata.updated_at, session_history_metadata.last_viewed_at, " \
                    "session_history_metadata.content_rating, session_history_metadata.summary, " \
                    "session_history_metadata.tagline, session_history_metadata.rating, session_history_metadata.duration, " \
                    "session_history_metadata.guid, session_history_metadata.directors, session_history_metadata.writers, " \
                    "session_history_metadata.actors, session_history_metadata.genres, session_history_metadata.studio, " \
                    "session_history_metadata.labels, " \
                    "session_history_media_info.container, session_history_media_info.bitrate, " \
                    "session_history_media_info.video_codec, session_history_media_info.video_resolution, " \
                    "session_history_media_info.video_full_resolution, " \
                    "session_history_media_info.video_framerate, session_history_media_info.audio_codec, " \
                    "session_history_media_info.audio_channels, session_history_metadata.live, " \
                    "session_history_metadata.channel_call_sign, session_history_metadata.channel_id, " \
                    "session_history_metadata.channel_identifier, session_history_metadata.channel_title, " \
                    "session_history_metadata.channel_thumb, session_history_metadata.channel_vcn " \
                    "FROM session_history_metadata " \
                    "JOIN library_sections ON session_history.section_id = library_sections.section_id " \
                    "JOIN session_history ON session_history_metadata.id = session_history.id " \
                    "JOIN session_history_media_info ON session_history_metadata.id = session_history_media_info.id " \
                    "WHERE %s " \
                    "ORDER BY session_history_metadata.id DESC " \
                    "LIMIT 1" % where
            result = monitor_db.select(query=query, args=args)
        else:
            result = []

        metadata_list = []

        for item in result:
            directors = item['directors'].split(';') if item['directors'] else []
            writers = item['writers'].split(';') if item['writers'] else []
            actors = item['actors'].split(';') if item['actors'] else []
            genres = item['genres'].split(';') if item['genres'] else []
            labels = item['labels'].split(';') if item['labels'] else []

            media_info = [{'container': item['container'],
                           'bitrate': item['bitrate'],
                           'video_codec': item['video_codec'],
                           'video_resolution': item['video_resolution'],
                           'video_full_resolution': common.VIDEO_RESOLUTION_OVERRIDES.get(
                               item['video_full_resolution'], item['video_full_resolution']),
                           'video_framerate': item['video_framerate'],
                           'audio_codec': item['audio_codec'],
                           'audio_channels': item['audio_channels'],
                           'channel_call_sign': item['channel_call_sign'],
                           'channel_id': item['channel_id'],
                           'channel_identifier': item['channel_identifier'],
                           'channel_title': item['channel_title'],
                           'channel_thumb': item['channel_thumb'],
                           'channel_vcn': item['channel_vcn']
                           }]

            metadata = {'media_type': item['media_type'],
                        'rating_key': item['rating_key'],
                        'parent_rating_key': item['parent_rating_key'],
                        'grandparent_rating_key': item['grandparent_rating_key'],
                        'grandparent_title': item['grandparent_title'],
                        'original_title': item['original_title'],
                        'parent_media_index': item['parent_media_index'],
                        'parent_title': item['parent_title'],
                        'media_index': item['media_index'],
                        'studio': item['studio'],
                        'title': item['title'],
                        'full_title': item['full_title'],
                        'content_rating': item['content_rating'],
                        'summary': item['summary'],
                        'tagline': item['tagline'],
                        'rating': item['rating'],
                        'duration': item['duration'],
                        'year': item['year'],
                        'thumb': item['thumb'],
                        'parent_thumb': item['parent_thumb'],
                        'grandparent_thumb': item['grandparent_thumb'],
                        'art': item['art'],
                        'originally_available_at': item['originally_available_at'],
                        'added_at': item['added_at'],
                        'updated_at': item['updated_at'],
                        'last_viewed_at': item['last_viewed_at'],
                        'guid': item['guid'],
                        'directors': directors,
                        'writers': writers,
                        'actors': actors,
                        'genres': genres,
                        'labels': labels,
                        'library_name': item['section_name'],
                        'section_id': item['section_id'],
                        'live': item['live'],
                        'media_info': media_info
                        }
            metadata_list.append(metadata)

        filtered_metadata_list = session.filter_session_info(metadata_list, filter_key='section_id')

        if filtered_metadata_list:
            return filtered_metadata_list[0]
        else:
            return []

    def get_total_duration(self, custom_where=None):
        if custom_where is None:
            custom_where = []

        # The totals only change when history is written; every history
        # table draw re-requested them (a full-table aggregate on the
        # default view)
        cache_key = str(custom_where)
        if _TOTAL_DURATION_CACHE['version'] == database.history_version:
            if cache_key in _TOTAL_DURATION_CACHE['values']:
                return _TOTAL_DURATION_CACHE['values'][cache_key]
        else:
            _TOTAL_DURATION_CACHE['version'] = database.history_version
            _TOTAL_DURATION_CACHE['values'] = {}

        monitor_db = database.MonitorDatabase()

        join_tables = set()
        media_type_live = ''

        for c_where in custom_where:
            if 'session_history_metadata.' in c_where[0]:
                join_tables.add('session_history_metadata')
            elif 'session_history_media_info.' in c_where[0]:
                join_tables.add('session_history_media_info')
            elif c_where[0].startswith('media_type_live'):
                media_type_live = (
                    ", (CASE WHEN session_history.live = 1 THEN 'live' ELSE session_history.media_type END) "
                    "AS media_type_live"
                )

        joins = ''
        for table in join_tables:
            joins += f"JOIN {table} ON {table}.id = session_history.id "

        where, args = datatables.build_custom_where(custom_where=custom_where)

        try:
            query = "SELECT SUM(CASE WHEN stopped > 0 THEN (stopped - started) ELSE 0 END) - " \
                    "SUM(CASE WHEN paused_counter IS NULL THEN 0 ELSE paused_counter END) AS total_duration %s " \
                    "FROM session_history %s %s" % (media_type_live, joins, where)
            result = monitor_db.select(query, args=args)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_total_duration: %s." % e)
            return None

        total_duration = 0
        for item in result:
            total_duration = item['total_duration']

        _TOTAL_DURATION_CACHE['values'][cache_key] = total_duration

        return total_duration

    def get_session_ip(self, session_key=''):
        monitor_db = database.MonitorDatabase()

        ip_address = 'N/A'

        user_cond = ''
        if session.get_session_user_id():
            user_cond = 'AND user_id = %s ' % session.get_session_user_id()

        if session_key:
            try:
                query = "SELECT ip_address FROM sessions WHERE session_key = %d %s" % (int(session_key), user_cond)
                result = monitor_db.select(query)
            except Exception as e:
                logger.warn("Tautulli DataFactory :: Unable to execute database query for get_session_ip: %s." % e)
                return ip_address
        else:
            return ip_address

        for item in result:
            ip_address = item['ip_address']

        return ip_address

    def get_img_info(self, img=None, rating_key=None, width=None, height=None,
                     opacity=None, background=None, blur=None, fallback=None,
                     order_by='', service=None):
        monitor_db = database.MonitorDatabase()

        img_info = []

        where_params = []
        args = []

        if img is not None:
            where_params.append('img')
            args.append(img)
        if rating_key is not None:
            where_params.append('rating_key')
            args.append(rating_key)
        if width is not None:
            where_params.append('width')
            args.append(width)
        if height is not None:
            where_params.append('height')
            args.append(height)
        if opacity is not None:
            where_params.append('opacity')
            args.append(opacity)
        if background is not None:
            where_params.append('background')
            args.append(background)
        if blur is not None:
            where_params.append('blur')
            args.append(blur)
        if fallback is not None:
            where_params.append('fallback')
            args.append(fallback)

        where = ''
        if where_params:
            where = "WHERE " + " AND ".join([w + " = ?" for w in where_params])

        if order_by:
            order_by = "ORDER BY " + order_by + " DESC"

        if service == 'imgur':
            query = "SELECT imgur_title AS img_title, imgur_url AS img_url FROM imgur_lookup " \
                    "JOIN image_hash_lookup ON imgur_lookup.img_hash = image_hash_lookup.img_hash " \
                    "%s %s" % (where, order_by)
        elif service == 'cloudinary':
            query = "SELECT cloudinary_title AS img_title, cloudinary_url AS img_url FROM cloudinary_lookup " \
                    "JOIN image_hash_lookup ON cloudinary_lookup.img_hash = image_hash_lookup.img_hash " \
                    "%s %s" % (where, order_by)
        else:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_img_info: "
                        "service not provided.")
            return img_info

        try:
            img_info = monitor_db.select(query, args=args)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_img_info: %s." % e)

        return img_info

    def set_img_info(self, img_hash=None, img_title=None, img_url=None, delete_hash=None, service=None):
        monitor_db = database.MonitorDatabase()

        keys = {'img_hash': img_hash}

        if service == 'imgur':
            table = 'imgur_lookup'
            values = {'imgur_title': img_title,
                      'imgur_url': img_url,
                      'delete_hash': delete_hash}
        elif service == 'cloudinary':
            table = 'cloudinary_lookup'
            values = {'cloudinary_title': img_title,
                      'cloudinary_url': img_url}
        else:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for set_img_info: "
                        "service not provided.")
            return

        monitor_db.upsert(table, key_dict=keys, value_dict=values)

    def delete_img_info(self, rating_key=None, service='', delete_all=False):
        monitor_db = database.MonitorDatabase()

        if not delete_all:
            service = service or helpers.get_img_service()

        if not rating_key and not delete_all:
            logger.error("Tautulli DataFactory :: Unable to delete hosted images: rating_key not provided.")
            return False

        where = ''
        args = []
        log_msg = ''
        if rating_key:
            where = "WHERE rating_key = ?"
            args = [rating_key]
            log_msg = ' for rating_key %s' % rating_key

        if service.lower() == 'imgur':
            # Delete from Imgur
            query = "SELECT imgur_title, delete_hash, fallback FROM imgur_lookup " \
                    "JOIN image_hash_lookup ON imgur_lookup.img_hash = image_hash_lookup.img_hash %s" % where
            results = monitor_db.select(query, args=args)

            for imgur_info in results:
                if imgur_info['delete_hash']:
                    helpers.delete_from_imgur(delete_hash=imgur_info['delete_hash'],
                                              img_title=imgur_info['imgur_title'],
                                              fallback=imgur_info['fallback'])

            logger.info("Tautulli DataFactory :: Deleting Imgur info%s from the database."
                        % log_msg)
            monitor_db.action("DELETE FROM imgur_lookup WHERE img_hash "
                              "IN (SELECT img_hash FROM image_hash_lookup %s)" % where,
                              args)
            return service

        elif service.lower() == 'cloudinary':
            # Delete from Cloudinary
            query = "SELECT cloudinary_title, rating_key, fallback FROM cloudinary_lookup " \
                    "JOIN image_hash_lookup ON cloudinary_lookup.img_hash = image_hash_lookup.img_hash %s " \
                    "GROUP BY rating_key" % where
            results = monitor_db.select(query, args=args)

            if delete_all:
                helpers.delete_from_cloudinary(delete_all=delete_all)
            else:
                for cloudinary_info in results:
                    helpers.delete_from_cloudinary(rating_key=cloudinary_info['rating_key'])

            logger.info("Tautulli DataFactory :: Deleting Cloudinary info%s from the database."
                        % log_msg)
            monitor_db.action("DELETE FROM cloudinary_lookup WHERE img_hash "
                              "IN (SELECT img_hash FROM image_hash_lookup %s)" % where,
                              args)
            return service

        else:
            logger.error("Tautulli DataFactory :: Unable to delete hosted images: invalid service '%s' provided."
                         % service)
            return None

    def get_poster_info(self, rating_key='', metadata=None, service=None):
        poster_key = ''
        if str(rating_key).isdigit():
            poster_key = rating_key
        elif metadata:
            if metadata['media_type'] in ('movie', 'show', 'artist', 'collection'):
                poster_key = metadata['rating_key']
            elif metadata['media_type'] in ('season', 'album'):
                poster_key = metadata['rating_key']
            elif metadata['media_type'] in ('episode', 'track'):
                poster_key = metadata['parent_rating_key']

        poster_info = {}

        if poster_key:
            service = service or helpers.get_img_service()

            if service:
                img_info = self.get_img_info(rating_key=poster_key,
                                             order_by='height',
                                             fallback='poster',
                                             service=service)
                if img_info:
                    poster_info = {'poster_title': img_info[0]['img_title'],
                                   'poster_url': img_info[0]['img_url'],
                                   'img_service': service.capitalize()}

        return poster_info

    def get_lookup_info(self, rating_key='', metadata=None):
        monitor_db = database.MonitorDatabase()

        lookup_key = ''
        if str(rating_key).isdigit():
            lookup_key = rating_key
        elif metadata:
            if metadata['media_type'] in ('movie', 'show', 'artist', 'album', 'track'):
                lookup_key = metadata['rating_key']
            elif metadata['media_type'] == 'season':
                lookup_key = metadata['parent_rating_key']
            elif metadata['media_type'] == 'episode':
                lookup_key = metadata['grandparent_rating_key']

        lookup_info = {'tvmaze_id': '',
                       'themoviedb_id': '',
                       'musizbrainz_id': ''}

        if lookup_key:
            try:
                query = 'SELECT tvmaze_id FROM tvmaze_lookup ' \
                        'WHERE rating_key = ?'
                tvmaze_info = monitor_db.select_single(query, args=[lookup_key])
                if tvmaze_info:
                    lookup_info['tvmaze_id'] = tvmaze_info['tvmaze_id']

                query = 'SELECT themoviedb_id FROM themoviedb_lookup ' \
                        'WHERE rating_key = ?'
                themoviedb_info = monitor_db.select_single(query, args=[lookup_key])
                if themoviedb_info:
                    lookup_info['themoviedb_id'] = themoviedb_info['themoviedb_id']

                query = 'SELECT musicbrainz_id FROM musicbrainz_lookup ' \
                        'WHERE rating_key = ?'
                musicbrainz_info = monitor_db.select_single(query, args=[lookup_key])
                if musicbrainz_info:
                    lookup_info['musicbrainz_id'] = musicbrainz_info['musicbrainz_id']

            except Exception as e:
                logger.warn("Tautulli DataFactory :: Unable to execute database query for get_lookup_info: %s." % e)

        return lookup_info

    def delete_lookup_info(self, rating_key='', service='', delete_all=False):
        if not rating_key and not delete_all:
            logger.error("Tautulli DataFactory :: Unable to delete lookup info: rating_key not provided.")
            return False

        monitor_db = database.MonitorDatabase()

        if rating_key:
            logger.info("Tautulli DataFactory :: Deleting lookup info for rating_key %s from the database."
                        % rating_key)
            result_themoviedb = monitor_db.action("DELETE FROM themoviedb_lookup WHERE rating_key = ?", [rating_key])
            result_tvmaze = monitor_db.action("DELETE FROM tvmaze_lookup WHERE rating_key = ?", [rating_key])
            result_musicbrainz = monitor_db.action("DELETE FROM musicbrainz_lookup WHERE rating_key = ?", [rating_key])
            return bool(result_themoviedb or result_tvmaze or result_musicbrainz)
        elif service and delete_all:
            if service.lower() in ('themoviedb', 'tvmaze', 'musicbrainz'):
                logger.info("Tautulli DataFactory :: Deleting all lookup info for '%s' from the database."
                            % service)
                result = monitor_db.action("DELETE FROM %s_lookup" % service.lower())
                return bool(result)
            else:
                logger.error("Tautulli DataFactory :: Unable to delete lookup info: invalid service '%s' provided."
                             % service)

    def get_search_query(self, rating_key=''):
        monitor_db = database.MonitorDatabase()

        if rating_key:
            query = "SELECT rating_key, parent_rating_key, grandparent_rating_key, title, parent_title, grandparent_title, " \
                    "media_index, parent_media_index, year, media_type " \
                    "FROM session_history_metadata " \
                    "WHERE rating_key = ? " \
                    "OR parent_rating_key = ? " \
                    "OR grandparent_rating_key = ? " \
                    "LIMIT 1"
            result = monitor_db.select(query=query, args=[rating_key, rating_key, rating_key])
        else:
            result = []

        query = {}
        query_string = None
        media_type = None

        for item in result:
            title = item['title']
            parent_title = item['parent_title']
            grandparent_title = item['grandparent_title']
            media_index = item['media_index']
            parent_media_index = item['parent_media_index']
            year = item['year']

            if str(item['rating_key']) == rating_key:
                query_string = item['title']
                media_type = item['media_type']

            elif str(item['parent_rating_key']) == rating_key:
                if item['media_type'] == 'episode':
                    query_string = item['grandparent_title']
                    media_type = 'season'
                elif item['media_type'] == 'track':
                    query_string = item['parent_title']
                    media_type = 'album'

            elif str(item['grandparent_rating_key']) == rating_key:
                if item['media_type'] == 'episode':
                    query_string = item['grandparent_title']
                    media_type = 'show'
                elif item['media_type'] == 'track':
                    query_string = item['grandparent_title']
                    media_type = 'artist'

        if query_string and media_type:
            query = {'query_string': query_string,
                     'title': title,
                     'parent_title': parent_title,
                     'grandparent_title': grandparent_title,
                     'media_index': media_index,
                     'parent_media_index': parent_media_index,
                     'year': year,
                     'media_type': media_type,
                     'rating_key': rating_key
                     }
        else:
            return None

        return query

    def get_rating_keys_list(self, rating_key='', media_type=''):
        monitor_db = database.MonitorDatabase()

        if media_type == 'movie':
            key_list = {0: {'rating_key': int(rating_key)}}
            return key_list

        if media_type == 'artist' or media_type == 'album' or media_type == 'track':
            match_type = 'title'
        else:
            match_type = 'index'

        # Get the grandparent rating key
        try:
            query = "SELECT rating_key, parent_rating_key, grandparent_rating_key " \
                    "FROM session_history_metadata " \
                    "WHERE rating_key = ? " \
                    "OR parent_rating_key = ? " \
                    "OR grandparent_rating_key = ? " \
                    "LIMIT 1"
            result = monitor_db.select(query=query, args=[rating_key, rating_key, rating_key])

            grandparent_rating_key = result[0]['grandparent_rating_key']

        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_rating_keys_list: %s." % e)
            return {}

        query = "SELECT rating_key, parent_rating_key, grandparent_rating_key, title, parent_title, grandparent_title, " \
                "media_index, parent_media_index " \
                "FROM session_history_metadata " \
                "WHERE {0} = ? " \
                "GROUP BY {1} " \
                "ORDER BY {1} DESC "

        # get grandparent_rating_keys
        grandparents = {}
        grandparent_results = monitor_db.select(
            query=query.format('grandparent_rating_key', 'grandparent_rating_key'),
            args=[grandparent_rating_key])
        for grandparent_item in grandparent_results:
            # get parent_rating_keys
            parents = {}
            parent_results = monitor_db.select(
                query=query.format('grandparent_rating_key', 'parent_rating_key'),
                args=[grandparent_item['grandparent_rating_key']])
            for parent_item in parent_results:
                # get rating_keys
                children = {}
                child_results = monitor_db.select(
                    query=query.format('parent_rating_key', 'rating_key'),
                    args=[parent_item['parent_rating_key']])
                for child_item in child_results:
                    key = child_item['media_index'] if child_item['media_index'] else str(child_item['title']).lower()
                    children.update({key: {'rating_key': child_item['rating_key']}})

                key = parent_item['parent_media_index'] if match_type == 'index' else str(parent_item['parent_title']).lower()
                parents.update({key:
                                {'rating_key': parent_item['parent_rating_key'],
                                 'children': children}
                                })

            key = 0 if match_type == 'index' else str(grandparent_item['grandparent_title']).lower()
            grandparents.update({key:
                                 {'rating_key': grandparent_item['grandparent_rating_key'],
                                  'children': parents}
                                 })

        key_list = grandparents

        return key_list

    def update_metadata(self, old_key_list='', new_key_list='', media_type='', single_update=False):
        pms_connect = pmsconnect.PmsConnect()
        monitor_db = database.MonitorDatabase()

        # function to map rating keys pairs
        def get_pairs(old, new):
            pairs = {}
            for k, v in old.items():
                if k in new:
                    pairs.update({v['rating_key']: new[k]['rating_key']})
                    if 'children' in old[k]:
                        pairs.update(get_pairs(old[k]['children'], new[k]['children']))

            return pairs

        # map rating keys pairs
        mapping = {}
        if old_key_list and new_key_list:
            mapping = get_pairs(old_key_list, new_key_list)

        if mapping:
            logger.info("Tautulli DataFactory :: Updating metadata in the database.")

            global _UPDATE_METADATA_IDS
            if single_update:
                _UPDATE_METADATA_IDS = {
                    'grandparent_rating_key_ids': set(),
                    'parent_rating_key_ids': set(),
                    'rating_key_ids': set()
                }

            for old_key, new_key in mapping.items():
                metadata = pms_connect.get_metadata_details(new_key)

                if metadata:
                    logger.debug("Tautulli DataFactory :: Mapping for rating_key %s -> %s (%s)",
                                 old_key, new_key, metadata['media_type'])

                    if metadata['media_type'] == 'show' or metadata['media_type'] == 'artist':
                        # check grandparent_rating_key (2 tables)
                        query = (
                            "SELECT id FROM session_history "
                            "WHERE grandparent_rating_key = ? "
                        )
                        args = [old_key]

                        if _UPDATE_METADATA_IDS['grandparent_rating_key_ids']:
                            query += "AND id NOT IN (%s)" % ",".join(_UPDATE_METADATA_IDS['grandparent_rating_key_ids'])

                        ids = [str(row['id']) for row in monitor_db.select(query, args)]
                        if ids:
                            _UPDATE_METADATA_IDS['grandparent_rating_key_ids'].update(ids)
                        else:
                            continue

                        monitor_db.action(
                            "UPDATE session_history SET grandparent_rating_key = ? "
                            "WHERE id IN (%s)" % ",".join(ids),
                            [new_key]
                        )
                        monitor_db.action(
                            "UPDATE session_history_metadata SET grandparent_rating_key = ? "
                            "WHERE id IN (%s)" % ",".join(ids),
                            [new_key]
                        )

                    elif metadata['media_type'] == 'season' or metadata['media_type'] == 'album':
                        # check parent_rating_key (2 tables)
                        query = (
                            "SELECT id FROM session_history "
                            "WHERE parent_rating_key = ? "
                        )
                        args = [old_key]

                        if _UPDATE_METADATA_IDS['parent_rating_key_ids']:
                            query += "AND id NOT IN (%s)" % ",".join(_UPDATE_METADATA_IDS['parent_rating_key_ids'])

                        ids = [str(row['id']) for row in monitor_db.select(query, args)]
                        if ids:
                            _UPDATE_METADATA_IDS['parent_rating_key_ids'].update(ids)
                        else:
                            continue

                        monitor_db.action(
                            "UPDATE session_history SET parent_rating_key = ? "
                            "WHERE id IN (%s)" % ",".join(ids),
                            [new_key]
                        )
                        monitor_db.action(
                            "UPDATE session_history_metadata SET parent_rating_key = ? "
                            "WHERE id IN (%s)" % ",".join(ids),
                            [new_key]
                        )

                    else:
                        # check rating_key (2 tables)
                        query = (
                            "SELECT id FROM session_history "
                            "WHERE rating_key = ? "
                        )
                        args = [old_key]

                        if _UPDATE_METADATA_IDS['rating_key_ids']:
                            query += "AND id NOT IN (%s)" % ",".join(_UPDATE_METADATA_IDS['rating_key_ids'])

                        ids = [str(row['id']) for row in monitor_db.select(query, args)]
                        if ids:
                            _UPDATE_METADATA_IDS['rating_key_ids'].update(ids)
                        else:
                            continue

                        monitor_db.action(
                            "UPDATE session_history SET rating_key = ? "
                            "WHERE id IN (%s)" % ",".join(ids),
                            [new_key]
                        )
                        monitor_db.action(
                            "UPDATE session_history_media_info SET rating_key = ? "
                            "WHERE id IN (%s)" % ",".join(ids),
                            [new_key]
                        )

                        # update session_history_metadata table
                        self.update_metadata_details(old_key, new_key, metadata, ids)

            return 'Updated metadata in database.'
        else:
            return 'Unable to update metadata in database. No changes were made.'

    def update_metadata_details(self, old_rating_key='', new_rating_key='', metadata=None, ids=None):

        if metadata:
            # Create full_title
            if metadata['media_type'] == 'episode':
                full_title = '%s - %s' % (metadata['grandparent_title'], metadata['title'])
            elif metadata['media_type'] == 'track':
                full_title = '%s - %s' % (metadata['title'],
                                          metadata['original_title'] or metadata['grandparent_title'])
            else:
                full_title = metadata['title']

            directors = ";".join(metadata['directors'])
            writers = ";".join(metadata['writers'])
            actors = ";".join(metadata['actors'])
            genres = ";".join(metadata['genres'])
            labels = ";".join(metadata['labels'])

            logger.debug("Tautulli DataFactory :: Updating metadata in the database for rating_key %s -> %s.",
                         old_rating_key, new_rating_key)

            monitor_db = database.MonitorDatabase()

            query = "UPDATE session_history SET section_id = ? " \
                    "WHERE id IN (%s)" % ",".join(ids)
            args = [metadata['section_id']]
            monitor_db.action(query=query, args=args)

            # Update the session_history_metadata table
            query = "UPDATE session_history_metadata SET rating_key = ?, parent_rating_key = ?, " \
                    "grandparent_rating_key = ?, title = ?, parent_title = ?, grandparent_title = ?, " \
                    "original_title = ?, full_title = ?, " \
                    "media_index = ?, parent_media_index = ?, thumb = ?, parent_thumb = ?, " \
                    "grandparent_thumb = ?, art = ?, media_type = ?, year = ?, originally_available_at = ?, " \
                    "added_at = ?, updated_at = ?, last_viewed_at = ?, content_rating = ?, summary = ?, " \
                    "tagline = ?, rating = ?, duration = ?, guid = ?, directors = ?, writers = ?, actors = ?, " \
                    "genres = ?, studio = ?, labels = ? " \
                    "WHERE id IN (%s)" % ",".join(ids)

            args = [metadata['rating_key'], metadata['parent_rating_key'], metadata['grandparent_rating_key'],
                    metadata['title'], metadata['parent_title'], metadata['grandparent_title'],
                    metadata['original_title'], full_title,
                    metadata['media_index'], metadata['parent_media_index'], metadata['thumb'],
                    metadata['parent_thumb'], metadata['grandparent_thumb'], metadata['art'], metadata['media_type'],
                    metadata['year'], metadata['originally_available_at'], metadata['added_at'], metadata['updated_at'],
                    metadata['last_viewed_at'], metadata['content_rating'], metadata['summary'], metadata['tagline'],
                    metadata['rating'], metadata['duration'], metadata['guid'], directors, writers, actors, genres,
                    metadata['studio'], labels]

            monitor_db.action(query=query, args=args)

    def get_notification_log(self, kwargs=None):
        data_tables = datatables.DataTables()

        columns = ["notify_log.id",
                   "notify_log.timestamp",
                   "notify_log.session_key",
                   "notify_log.rating_key",
                   "notify_log.user_id",
                   "notify_log.user",
                   "notify_log.notifier_id",
                   "notify_log.agent_id",
                   "notify_log.agent_name",
                   "notify_log.notify_action",
                   "notify_log.subject_text",
                   "notify_log.body_text",
                   "notify_log.success"
                   ]
        try:
            query = data_tables.ssp_query(table_name='notify_log',
                                          columns=columns,
                                          custom_where=[],
                                          group_by=[],
                                          join_types=[],
                                          join_tables=[],
                                          join_evals=[],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_notification_log: %s." % e)
            return

        notifications = query['result']

        rows = []
        for item in notifications:
            if item['body_text']:
                body_text = item['body_text'].replace('\r\n', '<br />').replace('\n', '<br />')
            else:
                body_text = ''

            row = {'id': item['id'],
                   'timestamp': item['timestamp'],
                   'session_key': item['session_key'],
                   'rating_key': item['rating_key'],
                   'user_id': item['user_id'],
                   'user': item['user'],
                   'notifier_id': item['notifier_id'],
                   'agent_id': item['agent_id'],
                   'agent_name': item['agent_name'],
                   'notify_action': item['notify_action'],
                   'subject_text': item['subject_text'],
                   'body_text': body_text,
                   'success': item['success']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }

        return dict

    def delete_notification_log(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info("Tautulli DataFactory :: Clearing notification logs from database.")
            monitor_db.action("DELETE FROM notify_log")
            monitor_db.action("VACUUM")
            return True
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for delete_notification_log: %s." % e)
            return False

    def get_newsletter_log(self, kwargs=None):
        data_tables = datatables.DataTables()

        columns = ["newsletter_log.id",
                   "newsletter_log.timestamp",
                   "newsletter_log.newsletter_id",
                   "newsletter_log.agent_id",
                   "newsletter_log.agent_name",
                   "newsletter_log.notify_action",
                   "newsletter_log.subject_text",
                   "newsletter_log.body_text",
                   "newsletter_log.start_date",
                   "newsletter_log.end_date",
                   "newsletter_log.uuid",
                   "newsletter_log.success"
                   ]
        try:
            query = data_tables.ssp_query(table_name='newsletter_log',
                                          columns=columns,
                                          custom_where=[],
                                          group_by=[],
                                          join_types=[],
                                          join_tables=[],
                                          join_evals=[],
                                          kwargs=kwargs)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for get_newsletter_log: %s." % e)
            return

        newsletters = query['result']

        rows = []
        for item in newsletters:
            row = {'id': item['id'],
                   'timestamp': item['timestamp'],
                   'newsletter_id': item['newsletter_id'],
                   'agent_id': item['agent_id'],
                   'agent_name': item['agent_name'],
                   'notify_action': item['notify_action'],
                   'subject_text': item['subject_text'],
                   'body_text': item['body_text'],
                   'start_date': item['start_date'],
                   'end_date': item['end_date'],
                   'uuid': item['uuid'],
                   'success': item['success']
                   }

            rows.append(row)

        dict = {'recordsFiltered': query['filteredCount'],
                'recordsTotal': query['totalCount'],
                'data': rows,
                'draw': query['draw']
                }

        return dict

    def delete_newsletter_log(self):
        monitor_db = database.MonitorDatabase()

        try:
            logger.info("Tautulli DataFactory :: Clearing newsletter logs from database.")
            monitor_db.action("DELETE FROM newsletter_log")
            monitor_db.action("VACUUM")
            return True
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for delete_newsletter_log: %s." % e)
            return False

    def get_user_devices(self, user_id='', history_only=True):
        monitor_db = database.MonitorDatabase()

        if user_id is not None and user_id != '':
            if history_only:
                query = "SELECT machine_id FROM session_history " \
                        "WHERE user_id = ? " \
                        "GROUP BY machine_id"
                args = [user_id]
            else:
                # Filter each arm before the UNION so the indexes on
                # user_id are used; the old form deduplicated the whole
                # tables' (user_id, machine_id) projection in a temp
                # B-tree before filtering
                query = "SELECT machine_id FROM session_history WHERE user_id = ? " \
                        "UNION " \
                        "SELECT machine_id FROM sessions_continued WHERE user_id = ?"
                args = [user_id, user_id]

            try:
                result = monitor_db.select(query=query, args=args)
            except Exception as e:
                logger.warn("Tautulli DataFactory :: Unable to execute database query for get_user_devices: %s." % e)
                return []
        else:
            return []

        return [d['machine_id'] for d in result]

    def get_recently_added_item(self, rating_key=''):
        monitor_db = database.MonitorDatabase()

        if rating_key:
            try:
                query = "SELECT * FROM recently_added WHERE rating_key = ?"
                result = monitor_db.select(query=query, args=[rating_key])
            except Exception as e:
                logger.warn("Tautulli DataFactory :: Unable to execute database query for get_recently_added_item: %s." % e)
                return []
        else:
            return []

        return result

    def set_recently_added_item(self, rating_key=''):
        monitor_db = database.MonitorDatabase()

        pms_connect = pmsconnect.PmsConnect()
        metadata = pms_connect.get_metadata_details(rating_key)

        keys = {'rating_key': metadata['rating_key']}

        values = {'added_at': metadata['added_at'],
                  'section_id': metadata['section_id'],
                  'parent_rating_key': metadata['parent_rating_key'],
                  'grandparent_rating_key': metadata['grandparent_rating_key'],
                  'media_type': metadata['media_type'],
                  'media_info': json.dumps(metadata['media_info'])
                  }

        try:
            monitor_db.upsert(table_name='recently_added', key_dict=keys, value_dict=values)
        except Exception as e:
            logger.warn("Tautulli DataFactory :: Unable to execute database query for set_recently_added_item: %s." % e)
            return False

        return True
