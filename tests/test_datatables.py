import json

import pytest

from plexpy.datatables import (
    DataTables,
    build_custom_where,
    build_grouping,
    build_join,
    build_order,
    build_where,
    extract_columns,
)


# ---------------------------------------------------------------------------
# extract_columns
#
# Shapes mirror the real column list built in
# DataFactory.get_datatables_history: plain dotted names, "AS"-aliased
# function calls, and an "AS"-aliased CASE expression.
# ---------------------------------------------------------------------------

def test_extract_columns_realistic_mix():
    columns = [
        "session_history.reference_id",
        "session_history.id AS row_id",
        "MAX(started) AS date",
        "session_history.user_id",
        "(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE users.friendly_name END) AS friendly_name",
    ]

    result = extract_columns(columns=columns)

    assert result == {
        'column_string': ', '.join(columns),
        'column_literal': [
            "session_history.reference_id",
            "session_history.id",
            "MAX(started)",
            "session_history.user_id",
            "(CASE WHEN users.friendly_name IS NULL THEN users.username ELSE users.friendly_name END)",
        ],
        'column_named': ["reference_id", "row_id", "date", "user_id", "friendly_name"],
        'column_order': [
            "session_history.reference_id",
            "row_id",
            "date",
            "session_history.user_id",
            "friendly_name",
        ],
    }


def test_extract_columns_empty_list():
    # First unfiltered draw of a table with no columns configured is not a
    # real scenario, but ssp_query always passes a real (possibly empty
    # after caller-side filtering) list, never None.
    assert extract_columns(columns=[]) == {
        'column_string': '',
        'column_literal': [],
        'column_named': [],
        'column_order': [],
    }


# ---------------------------------------------------------------------------
# build_order
#
# columns = extracted_columns['column_named'] (the query's real column
# names). dt_columns = parameters['columns'] (the DataTables column
# config sent by the browser, each with a 'data' field).
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("order_param,dt_columns,columns,expected", [
    # Single column ascending.
    (
        [{"column": 0, "dir": "asc"}],
        [{"data": "date"}, {"data": "friendly_name"}],
        ["date", "friendly_name"],
        "ORDER BY date COLLATE NOCASE",
    ),
    # Single column descending.
    (
        [{"column": 1, "dir": "desc"}],
        [{"data": "date"}, {"data": "friendly_name"}],
        ["date", "friendly_name"],
        "ORDER BY friendly_name COLLATE NOCASE DESC",
    ),
    # Multi-column sort (shift-click a second column header).
    (
        [{"column": 0, "dir": "asc"}, {"column": 1, "dir": "desc"}],
        [{"data": "platform"}, {"data": "started"}],
        ["platform", "started"],
        "ORDER BY platform COLLATE NOCASE, started COLLATE NOCASE DESC",
    ),
])
def test_build_order(order_param, dt_columns, columns, expected):
    assert build_order(order_param, columns, dt_columns) == expected


def test_build_order_unmatched_column_name_is_dropped_silently():
    # 'watched_status' is a real dt_column in the history table config
    # (webserve.py) but it is a display-only field, not part of the SQL
    # query's column list, so it can never be sorted on. Sorting the rest
    # of the request must still work.
    order_param = [{"column": 0, "dir": "asc"}, {"column": 1, "dir": "desc"}]
    dt_columns = [{"data": "watched_status"}, {"data": "duration"}]
    columns = ["duration"]

    assert build_order(order_param, columns, dt_columns) == "ORDER BY duration COLLATE NOCASE DESC"


def test_build_order_no_order_is_first_draw():
    assert build_order([], ["date"], [{"data": "date"}]) == ""


# ---------------------------------------------------------------------------
# build_where (the global DataTables search box)
# ---------------------------------------------------------------------------

def test_build_where_searches_all_searchable_columns():
    columns = ["friendly_name", "ip_address", "platform", "date"]
    dt_columns = [
        {"data": "friendly_name", "searchable": True},
        {"data": "ip_address", "searchable": True},
        {"data": "platform", "searchable": True},
        {"data": "date", "searchable": False},
    ]

    where, args = build_where("chrome", columns, dt_columns)

    assert where == "WHERE friendly_name LIKE ? OR ip_address LIKE ? OR platform LIKE ?"
    assert args == ["%chrome%", "%chrome%", "%chrome%"]


def test_build_where_unmatched_column_name_is_dropped_silently():
    columns = ["friendly_name"]
    dt_columns = [
        {"data": "friendly_name", "searchable": True},
        {"data": "nonexistent_col", "searchable": True},
    ]

    where, args = build_where("x", columns, dt_columns)

    assert where == "WHERE friendly_name LIKE ?"
    assert args == ["%x%"]


def test_build_where_no_search_value_is_first_draw():
    columns = ["friendly_name"]
    dt_columns = [{"data": "friendly_name", "searchable": True}]

    where, args = build_where("", columns, dt_columns)

    assert where == ""
    assert args == []


# ---------------------------------------------------------------------------
# build_custom_where
#
# Shapes taken directly from real callers: webserve.py's get_history
# builds ['col IN', [...]] / ['col LIKE', [...]] / ['col <', [...]] custom
# wheres from query args, and libraries.py/users.py filter deleted rows
# with plain scalar and NULL equality.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("custom_where,expected_where,expected_args", [
    ([], "", []),
    # Plain scalar equality (libraries.py: hide deleted sections).
    ([['library_sections.deleted_section', 0]], "WHERE library_sections.deleted_section = ?", [0]),
    # None value -> IS NULL (users.py: no session user restricts by user_id).
    ([['users.user_id', None]], "WHERE users.user_id IS NULL", []),
    # Single-value IN (webserve.py: ?user_id=1).
    ([['session_history.user_id IN', ['1']]], "WHERE session_history.user_id IN (?)", ['1']),
    ([['media_type_live IN', ['movie']]], "WHERE media_type_live IN (?)", ['movie']),
    # Multi-value IN (webserve.py: ?section_id=1,2,3).
    (
        [['session_history.section_id IN', ['1', '2', '3']]],
        "WHERE session_history.section_id IN (?,?,?)",
        ['1', '2', '3'],
    ),
    # LIKE against a single pattern (webserve.py: ?guid=<agent>).
    (
        [['session_history_metadata.guid LIKE', ['tt1%']]],
        "WHERE (session_history_metadata.guid LIKE ?)",
        ['tt1%'],
    ),
    # LIKE against multiple patterns, OR'd together (webserve.py: ?guid=a,b).
    (
        [['session_history_metadata.guid LIKE', ['tt1%', 'tt2%']]],
        "WHERE (session_history_metadata.guid LIKE ? OR session_history_metadata.guid LIKE ?)",
        ['tt1%', 'tt2%'],
    ),
    # Date range bounds (webserve.py: ?before=YYYY-MM-DD / ?after=YYYY-MM-DD).
    ([['started <', [1700000000]]], "WHERE (started <= ?)", [1700000000]),
    ([['started >', [1600000000]]], "WHERE (started >= ?)", [1600000000]),
])
def test_build_custom_where(custom_where, expected_where, expected_args):
    where, args = build_custom_where(custom_where)
    assert where == expected_where
    assert args == expected_args


def test_build_custom_where_ands_multiple_filters():
    # webserve.py get_history combines a user filter and a media_type
    # filter; both must hold (AND), each contributing its own IN clause.
    custom_where = [
        ['session_history.user_id IN', ['1']],
        ['media_type_live IN', ['movie']],
    ]

    where, args = build_custom_where(custom_where)

    assert where == "WHERE session_history.user_id IN (?) AND media_type_live IN (?)"
    assert args == ['1', 'movie']


def test_build_custom_where_rating_key_in_or_triple():
    # webserve.py get_history: a collection/playlist filter expands to a
    # rating key that could match the item itself, its parent, or its
    # grandparent, so the three IN clauses are OR'd rather than AND'd.
    rating_keys = ['100', '200']
    custom_where = [
        ['session_history_metadata.rating_key IN OR', rating_keys],
        ['session_history_metadata.parent_rating_key IN OR', rating_keys],
        ['session_history_metadata.grandparent_rating_key IN OR', rating_keys],
    ]

    where, args = build_custom_where(custom_where)

    assert where == (
        "WHERE session_history_metadata.rating_key IN (?,?) "
        "OR session_history_metadata.parent_rating_key IN (?,?) "
        "OR session_history_metadata.grandparent_rating_key IN (?,?)"
    )
    assert args == ['100', '200', '100', '200', '100', '200']


@pytest.mark.parametrize("second_filter,expected_where,expected_args", [
    # Plain scalar equality following an IN clause.
    (
        ['session_history.user_id', '1'],
        "WHERE media_type_live IN (?) AND session_history.user_id = ?",
        ['live', '1'],
    ),
    # None value -> IS NULL, following an IN clause.
    (
        ['session_history.user_id', None],
        "WHERE media_type_live IN (?) AND session_history.user_id IS NULL",
        ['live'],
    ),
    # List value without an "IN" suffix on the column name (datafactory.py
    # get_history appends ['session_history.user_id', [user_id]] this way,
    # after the media_type/other filters are already in custom_where).
    (
        ['session_history.user_id', ['1']],
        "WHERE media_type_live IN (?) AND (session_history.user_id = ?)",
        ['live', '1'],
    ),
])
def test_build_custom_where_keeps_earlier_clause_when_combined(second_filter, expected_where, expected_args):
    # c_where/args must accumulate across filters, not get overwritten by
    # the last one; the leading IN clause must survive whatever follows it.
    custom_where = [['media_type_live IN', ['live']], second_filter]

    where, args = build_custom_where(custom_where)

    assert where == expected_where
    assert args == expected_args


# ---------------------------------------------------------------------------
# build_grouping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("group_by,expected", [
    (None, ""),
    ([], ""),
    (['session_history.reference_id'], "GROUP BY session_history.reference_id"),
    (['session_history.id'], "GROUP BY session_history.id"),
    (['users.user_id'], "GROUP BY users.user_id"),
    (
        ['library_sections.server_id', 'library_sections.section_id'],
        "GROUP BY library_sections.server_id, library_sections.section_id",
    ),
])
def test_build_grouping(group_by, expected):
    assert build_grouping(group_by) == expected


# ---------------------------------------------------------------------------
# build_join
# ---------------------------------------------------------------------------

def test_build_join_no_joins_is_ungrouped_table():
    assert build_join([], [], []) == ""


def test_build_join_single_left_outer_join():
    # users.py get_watch_time_stats: user_login LEFT OUTER JOIN users.
    join = build_join(
        join_types=['LEFT OUTER JOIN'],
        join_tables=['users'],
        join_evals=[['user_login.user_id', 'users.user_id']],
    )

    assert join == "LEFT OUTER JOIN users ON user_login.user_id = users.user_id "


def test_build_join_mixed_left_outer_and_inner():
    # datafactory.py get_datatables_history: one LEFT OUTER JOIN (a user may
    # have been deleted) plus two required JOINs.
    join = build_join(
        join_types=['LEFT OUTER JOIN', 'JOIN', 'JOIN'],
        join_tables=['users', 'session_history_metadata', 'session_history_media_info'],
        join_evals=[
            ['session_history.user_id', 'users.user_id'],
            ['session_history.id', 'session_history_metadata.id'],
            ['session_history.id', 'session_history_media_info.id'],
        ],
    )

    assert join == (
        "LEFT OUTER JOIN users ON session_history.user_id = users.user_id "
        "JOIN session_history_metadata ON session_history.id = session_history_metadata.id "
        "JOIN session_history_media_info ON session_history.id = session_history_media_info.id "
    )


# ---------------------------------------------------------------------------
# DataTables.ssp_query
# ---------------------------------------------------------------------------

def test_ssp_query_drops_all_null_left_join_rows(app_db):
    # datafactory.py get_history: session_history LEFT OUTER JOIN users, since
    # a session's user may have since been deleted. When the query selects
    # only the joined table's columns, an unmatched session comes back as a
    # row of all NULLs and must be dropped, while a matched row survives.
    app_db.action("INSERT INTO users (user_id, username) VALUES (?, ?)", [1, 'alice'])
    app_db.action("INSERT INTO session_history (user_id) VALUES (?)", [1])
    app_db.action("INSERT INTO session_history (user_id) VALUES (?)", [999])

    kwargs = {'json_data': json.dumps({
        'draw': 1,
        'start': 0,
        'length': 10,
        'search': {'value': ''},
        'order': [],
        'columns': [
            {'data': 'user_id', 'searchable': True},
            {'data': 'username', 'searchable': True},
        ],
    })}

    output = DataTables().ssp_query(
        table_name='session_history',
        columns=['users.user_id', 'users.username'],
        join_types=['LEFT OUTER JOIN'],
        join_tables=['users'],
        join_evals=[['session_history.user_id', 'users.user_id']],
        kwargs=kwargs,
    )

    # filteredCount is the SQL COUNT(*) OVER () taken before the NULL-row
    # removal below, so it still counts both rows; only 'result' reflects
    # the drop.
    assert output['result'] == [{'user_id': 1, 'username': 'alice'}]
    assert output['filteredCount'] == 2
    assert output['totalCount'] == 2
