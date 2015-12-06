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

from plexpy import logger, helpers, database

import re


class DataTables(object):
    """
    Server side processing for Datatables
    """

    def __init__(self):
        self.ssp_db = database.MonitorDatabase()

    def ssp_query(self,
                  table_name=None,
                  columns=[],
                  custom_where=[],
                  group_by=[],
                  join_types=[],
                  join_tables=[],
                  join_evals=[],
                  kwargs=None):

        if not table_name:
            logger.error('PlexPy DataTables :: No table name received.')
            return None

        # Set default variable values
        parameters = {}
        args = []
        group = ''
        order = ''
        where = ''
        join = ''
        c_where = ''

        # Fetch all our parameters
        if kwargs.get('json_data'):
            parameters = helpers.process_json_kwargs(json_kwargs=kwargs.get('json_data'))
        else:
            logger.error('PlexPy DataTables :: Parameters for Datatables must be sent as a serialised json object '
                         'named json_data.')
            return None

        dt_columns = parameters['columns']
        extracted_columns = self.extract_columns(columns=columns)

        # Build grouping
        if group_by:
            for g in group_by:
                group += g + ', '
            if group:
                grouping = True
                group = 'GROUP BY ' + group.rstrip(', ')
        else:
            grouping = False

        # Build join parameters
        if join_types:
            counter = 0
            for join_type in join_types:
                if join_type.upper() == 'LEFT OUTER JOIN':
                    join_item = 'LEFT OUTER JOIN %s ON %s = %s ' % \
                                (join_tables[counter], join_evals[counter][0], join_evals[counter][1])
                elif join_type.upper() == 'JOIN' or join_type.upper() == 'INNER JOIN':
                    join_item = 'JOIN %s ON %s = %s ' % \
                                (join_tables[counter], join_evals[counter][0], join_evals[counter][1])
                else:
                    join_item = ''

                counter += 1
                join += join_item

        # Build custom where parameters
        if custom_where:
            for w in custom_where:
                c_where += w[0] + ' = ? AND '

                # The order of our args changes if we are grouping
                #if grouping:
                #    args.insert(0, w[1])
                #else:
                #    args.append(w[1])

                # My testing shows that order of args doesn't change
                args.append(w[1])

            if c_where:
                c_where = 'WHERE ' + c_where.rstrip(' AND ')

        # Build ordering
        for o in parameters['order']:
            sort_order = ' COLLATE NOCASE'
            if o['dir'] == 'desc':
                sort_order = ' COLLATE NOCASE DESC'
            # We first see if a name was sent though for the column sort.
            if dt_columns[int(o['column'])]['data']:
                # We have a name, now check if it's a valid column name for our query
                # so we don't just inject a random value
                if any(d.lower() == dt_columns[int(o['column'])]['data'].lower()
                       for d in extracted_columns['column_named']):
                    order += dt_columns[int(o['column'])]['data'] + '%s' % sort_order
                else:
                    # if we receive a bogus name, rather not sort at all.
                    pass
            # If no name exists for the column, just use the column index to sort
            else:
                order += extracted_columns['column_named'][int(o['column'])]

            order += ', '

        if order:
            order = 'ORDER BY ' + order.rstrip(', ')

        # Build where parameters
        if parameters['search']['value']:
            counter = 0
            for s in parameters['columns']:
                if s['searchable']:
                    # We first see if a name was sent though for the column search.
                    if s['data']:
                        # We have a name, now check if it's a valid column name for our query
                        # so we don't just inject a random value
                        if any(d.lower() == s['data'].lower() for d in extracted_columns['column_named']):
                            where += s['data'] + ' LIKE ? OR '
                            args.append('%' + parameters['search']['value'] + '%')
                        else:
                            # if we receive a bogus name, rather not search at all.
                            pass
                    # If no name exists for the column, just use the column index to search
                    else:
                        where += extracted_columns['column_named'][counter] + ' LIKE ? OR '
                        args.append('%' + parameters['search']['value'] + '%')

                counter += 1

            if where:
                where = 'WHERE ' + where.rstrip(' OR ')

        # Build our queries
        if grouping:
            if c_where == '':
                query = 'SELECT * FROM (SELECT %s FROM %s %s %s) %s %s' \
                        % (extracted_columns['column_string'], table_name, join, group,
                           where, order)
            else:
                query = 'SELECT * FROM (SELECT %s FROM %s %s %s %s) %s %s' \
                        % (extracted_columns['column_string'], table_name, join, c_where, group,
                           where, order)
        else:
            if c_where == '':
                query = 'SELECT %s FROM %s %s %s %s' \
                        % (extracted_columns['column_string'], table_name, join, where,
                           order)
            else:
                query = 'SELECT * FROM (SELECT %s FROM %s %s %s %s) %s' \
                        % (extracted_columns['column_string'], table_name, join, where,
                           order, c_where)

        # logger.debug(u"Query: %s" % query)

        # Execute the query
        filtered = self.ssp_db.select(query, args=args)

        # Build grand totals
        totalcount = self.ssp_db.select('SELECT COUNT(id) as total_count from %s' % table_name)[0]['total_count']

        # Get draw counter
        draw_counter = int(parameters['draw'])

        # Paginate results
        result = filtered[parameters['start']:(parameters['start'] + parameters['length'])]

        # Sanitize on the way out
        result = [{k: helpers.sanitize(v) if isinstance(v, basestring) else v for k, v in row.iteritems()}
                  for row in result]

        output = {'result': result,
                  'draw': draw_counter,
                  'filteredCount': len(filtered),
                  'totalCount': totalcount}

        return output

    # This method extracts column data from our column list
    # The first parameter is required, the match_columns parameter is optional and will cause the function to
    # only return results if the value also exists in the match_columns 'data' field
    @staticmethod
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
        # column_string is a comma seperated list of the exact column variables received.
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
