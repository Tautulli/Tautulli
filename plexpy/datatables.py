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

# TODO: Implement with sqlite3 directly instead of using db class

from plexpy import logger, helpers, db

import re


class DataTables(object):
    """
    Server side processing for Datatables
    """

    def __init__(self):
        self.ssp_db = db.DBConnection()

    def ssp_query(self, table_name,
                  columns=[],
                  start=0,
                  length=0,
                  order_column=0,
                  order_dir='asc',
                  search_value='',
                  search_regex='',
                  custom_where='',
                  group_by='',
                  kwargs=None):

        parameters = self.process_kwargs(kwargs)

        if group_by != '':
            grouping = True
        else:
            grouping = False

        column_data = self.extract_columns(columns)
        where = self.construct_where(column_data, search_value, grouping, parameters)
        order = self.construct_order(column_data, order_column, order_dir, parameters)

        # TODO: custom_where is ugly and causes issues with reported total results
        if custom_where != '':
            where += 'AND (' + custom_where + ')'

        if grouping:
            query = 'SELECT * FROM (SELECT %s FROM %s GROUP BY %s) %s %s' \
                    % (column_data['column_string'], table_name, group_by,
                       where, order)
        else:
            query = 'SELECT %s FROM %s %s %s' \
                    % (column_data['column_string'], table_name, where,
                       order)

        filtered = self.ssp_db.select(query)
        if search_value == '':
            totalcount = len(filtered)
        else:
            totalcount = self.ssp_db.select('SELECT COUNT(*) from %s' % table_name)[0][0]

        # logger.debug(u"Query string: %s" % query)

        result = filtered[start:(start + length)]
        output = {'result': result,
                  'filteredCount': len(filtered),
                  'totalCount': totalcount}

        return output

    @staticmethod
    def construct_order(column_data, order_column, order_dir, parameters=None):
        order = ''
        if parameters:
            for parameter in parameters:
                if parameter['data'] != '':
                    if int(order_column) == parameters.index(parameter):
                        if parameter['data'] in column_data['column_named'] and parameter['orderable'] == 'true':
                            order = 'ORDER BY %s COLLATE NOCASE %s' % (parameter['data'], order_dir)
                        logger.debug(u"order string %s " % order)
                else:
                    order = 'ORDER BY %s COLLATE NOCASE %s' % (column_data['column_named'][order_column], order_dir)
                    logger.debug(u"order string (NO param received) %s " % order)
        return order

    @staticmethod
    def construct_where(column_data, search_value='', grouping=False, parameters=None):
        if search_value != '':
            where = 'WHERE '
            if parameters:
                for column in column_data['column_named']:
                    search_skip = False
                    for parameter in parameters:
                        if column in parameter['data']:
                            if parameter['searchable'] == 'true':
                                logger.debug(u"Column %s is searchable." % column)
                                where += column + ' LIKE "%' + search_value + '%" OR '
                                search_skip = True
                            else:
                                logger.debug(u"Column %s is NOT searchable." % column)
                                search_skip = True

                    if not search_skip:
                        where += column + ' LIKE "%' + search_value + '%" OR '
            else:
                for column in column_data['column_named']:
                    where += column + ' LIKE "%' + search_value + '%" OR '

            # TODO: This will break the query if all parameters are excluded
            where = where[:-4]

            return where
        else:
            return ''

    @staticmethod
    def extract_columns(columns=[]):
        columns_string = ''
        columns_literal = []
        columns_named = []

        for column in columns:
            columns_string += column
            columns_string += ', '
            # TODO: make this case insensitive
            if ' as ' in column:
                columns_literal.append(column.rpartition(' as ')[0])
                columns_named.append(column.rpartition(' as ')[-1])
            else:
                columns_literal.append(column)
                columns_named.append(column)

        columns_string = columns_string[:-2]

        column_data = {'column_string': columns_string,
                       'column_literal': columns_literal,
                       'column_named': columns_named
                       }

        return column_data

    # TODO: Fix this method. Should not break if kwarg list is not sorted.
    @staticmethod
    def process_kwargs(kwargs):

        column_parameters = []

        for kwarg in sorted(kwargs):
            if re.search(r"\[(\w+)\]", kwarg) and kwarg[:7] == 'columns':
                parameters = re.findall(r"\[(\w+)\]", kwarg)
                array_index = ''
                for parameter in parameters:
                    pass_complete = False
                    if parameter.isdigit():
                        array_index = parameter
                    if parameter == 'data':
                        data = kwargs.get('columns[' + array_index + '][data]', "")
                    if parameter == 'orderable':
                        orderable = kwargs.get('columns[' + array_index + '][orderable]', "")
                    if parameter == 'searchable':
                        searchable = kwargs.get('columns[' + array_index + '][searchable]', "")
                        pass_complete = True
                    if pass_complete:
                        row = {'index': int(array_index),
                               'data': data,
                               'searchable': searchable,
                               'orderable': orderable}
                        column_parameters.append(row)

        return sorted(column_parameters, key=lambda i: i['index'])