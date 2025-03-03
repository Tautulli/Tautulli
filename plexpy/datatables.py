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

import re

import plexpy
from plexpy import database
from plexpy import helpers
from plexpy import logger


class DataTables(object):
    """
    Server side processing for Datatables
    """

    def __init__(self):
        self.ssp_db = database.MonitorDatabase()

    def ssp_query(self,
                  table_name=None,
                  table_name_union=None,
                  columns=[],
                  columns_union=[],
                  custom_where=[],
                  custom_where_union=[],
                  group_by=[],
                  group_by_union=[],
                  join_types=[],
                  join_tables=[],
                  join_evals=[],
                  kwargs=None):

        if not table_name:
            logger.error('Tautulli DataTables :: No table name received.')
            return None

        # Fetch all our parameters
        if kwargs.get('json_data'):
            parameters = helpers.process_json_kwargs(json_kwargs=kwargs.get('json_data'))
        else:
            logger.error('Tautulli DataTables :: Parameters for Datatables must be sent as a serialised json object '
                         'named json_data.')
            return None

        extracted_columns = extract_columns(columns=columns)
        join = build_join(join_types, join_tables, join_evals)
        group = build_grouping(group_by)
        c_where, cw_args = build_custom_where(custom_where)
        order = build_order(parameters['order'],
                                 extracted_columns['column_named'],
                                 parameters['columns'])
        where, w_args = build_where(parameters['search']['value'],
                                         extracted_columns['column_named'],
                                         parameters['columns'])

        # Build union parameters
        if table_name_union:
            extracted_columns_union = extract_columns(columns=columns_union)
            group_u = build_grouping(group_by_union)
            c_where_u, cwu_args = build_custom_where(custom_where_union)
            union = 'UNION SELECT %s FROM %s %s %s' % (extracted_columns_union['column_string'],
                                                       table_name_union,
                                                       c_where_u,
                                                       group_u)
        else:
            union = ''
            cwu_args = []

        args = cw_args + cwu_args + w_args

        # Build the query
        query = 'SELECT * FROM (SELECT %s FROM %s %s %s %s %s) %s %s' \
                % (extracted_columns['column_string'], table_name, join, c_where, group, union, where, order)

        # logger.debug("Query: %s" % query)

        # Execute the query
        filtered = self.ssp_db.select(query, args=args)

        # Remove NULL rows
        filtered = [row for row in filtered if not all(v is None for v in row.values())]

        # Build grand totals
        totalcount = self.ssp_db.select('SELECT COUNT(id) as total_count from %s' % table_name)[0]['total_count']

        # Get draw counter
        draw_counter = int(parameters['draw'])

        # Paginate results
        result = filtered[parameters['start']:(parameters['start'] + parameters['length'])]

        output = {'result': result,
                  'draw': draw_counter,
                  'filteredCount': len(filtered),
                  'totalCount': totalcount}

        return output


def build_grouping(group_by=[]):
    # Build grouping
    group = ''

    for g in group_by:
        group += g + ', '
    if group:
        group = 'GROUP BY ' + group.rstrip(', ')

    return group


def build_join(join_types=[], join_tables=[], join_evals=[]):
    # Build join parameters
    join = ''

    for i, join_type in enumerate(join_types):
        if join_type.upper() == 'LEFT OUTER JOIN':
            join += 'LEFT OUTER JOIN %s ON %s = %s ' % (join_tables[i], join_evals[i][0], join_evals[i][1])
        elif join_type.upper() == 'JOIN' or join_type.upper() == 'INNER JOIN':
            join += 'JOIN %s ON %s = %s ' % (join_tables[i], join_evals[i][0], join_evals[i][1])

    return join


def build_custom_where(custom_where=[]):
    # Build custom where parameters
    c_where = ''
    args = []

    for w in custom_where:
        and_or = ' OR ' if w[0].endswith('OR') else ' AND '
        w[0] = w[0].rstrip(' OR')

        if isinstance(w[1], (list, tuple)) and len(w[1]):
            c_where += '('
            for w_ in w[1]:
                if w_ is None:
                    c_where += w[0] + ' IS NULL'
                elif str(w_).startswith('LIKE '):
                    c_where += w[0] + ' LIKE ?'
                    args.append(w_[5:])
                elif w[0].endswith('<') or w[0].endswith('>'):
                    c_where += w[0] + '= ?'
                    args.append(w_)
                else:
                    c_where += w[0] + ' = ?'
                    args.append(w_)
                c_where += ' OR '
            c_where = c_where.rstrip(' OR ') + ')' + and_or
        else:
            if w[1] is None:
                c_where += w[0] + ' IS NULL'
            elif str(w[1]).startswith('LIKE '):
                c_where += w[0] + ' LIKE ?'
                args.append(w[1][5:])
            elif w[0].endswith('<') or w[0].endswith('>'):
                c_where += w[0] + '= ?'
                args.append(w[1])
            else:
                c_where += w[0] + ' = ?'
                args.append(w[1])

            c_where += and_or

    if c_where:
        c_where = 'WHERE ' + c_where.rstrip(' AND ').rstrip(' OR ')

    return c_where, args


def build_order(order_param=[], columns=[], dt_columns=[]):
    # Build ordering
    order = ''

    for o in order_param:
        sort_order = ' COLLATE NOCASE'
        if o['dir'] == 'desc':
            sort_order += ' DESC'
        # We first see if a name was sent though for the column sort.
        if dt_columns[int(o['column'])]['data']:
            # We have a name, now check if it's a valid column name for our query
            # so we don't just inject a random value
            if any(d.lower() == dt_columns[int(o['column'])]['data'].lower()
                   for d in columns):
                order += dt_columns[int(o['column'])]['data'] + '%s, ' % sort_order
            else:
                # if we receive a bogus name, rather not sort at all.
                pass
        # If no name exists for the column, just use the column index to sort
        else:
            order += columns[int(o['column'])] + ', '

    if order:
        order = 'ORDER BY ' + order.rstrip(', ')

    return order


def build_where(search_param='', columns=[], dt_columns=[]):
    # Build where parameters
    where = ''
    args = []

    if search_param:
        for i, s in enumerate(dt_columns):
            if s['searchable']:
                # We first see if a name was sent though for the column search.
                if s['data']:
                    # We have a name, now check if it's a valid column name for our query
                    # so we don't just inject a random value
                    if any(d.lower() == s['data'].lower() for d in columns):
                        where += s['data'] + ' LIKE ? OR '
                        args.append('%' + search_param + '%')
                    else:
                        # if we receive a bogus name, rather not search at all.
                        pass
                # If no name exists for the column, just use the column index to search
                else:
                    where += columns[i] + ' LIKE ? OR '
                    args.append('%' + search_param + '%')
        if where:
            where = 'WHERE ' + where.rstrip(' OR ')

    return where, args


# This method extracts column data from our column list
# The first parameter is required, the match_columns parameter is optional and will cause the function to
# only return results if the value also exists in the match_columns 'data' field
def extract_columns(columns=None, match_columns=None):
    columns_string = ''
    columns_literal = []
    columns_named = []
    columns_order = []

    for column in columns:
        # We allow using "as" in column names for more complex sql functions.
        # This function breaks up the column to get all it's parts.
        as_search = re.compile(' as ', re.IGNORECASE)

        if re.search(as_search, column):
            column_named = re.split(as_search, column)[1].rpartition('.')[-1]
            column_literal = re.split(as_search, column)[0]
            column_order = re.split(as_search, column)[1]
            if match_columns:
                if any(d['data'].lower() == column_named.lower() for d in match_columns):
                    columns_string += column + ', '
                    columns_literal.append(column_literal)
                    columns_named.append(column_named)
                    columns_order.append(column_order)
            else:
                columns_string += column + ', '
                columns_literal.append(column_literal)
                columns_named.append(column_named)
                columns_order.append(column_order)
        else:
            column_named = column.rpartition('.')[-1]
            if match_columns:
                if any(d['data'].lower() == column_named.lower() for d in match_columns):
                    columns_string += column + ', '
                    columns_literal.append(column)
                    columns_named.append(column_named)
                    columns_order.append(column)
            else:
                columns_string += column + ', '
                columns_literal.append(column)
                columns_named.append(column_named)
                columns_order.append(column)

    columns_string = columns_string.rstrip(', ')

    # We return a dict of the column params
    # column_string is a comma separated list of the exact column variables received.
    # column_literal is the text before the "as" if we have an "as". Usually a function.
    # column_named is the text after the "as", if we have an "as". Any table prefix is also stripped off.
    #   We use this to match with columns received from the Datatables request.
    # column_order is the text after the "as", if we have an "as". Any table prefix is left intact.
    column_data = {'column_string': columns_string,
                   'column_literal': columns_literal,
                   'column_named': columns_named,
                   'column_order': columns_order
                   }

    return column_data
