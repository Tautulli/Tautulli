#  This file is part of PlexPy.
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

#####################################
## Stolen from Sick-Beard's db.py  ##
#####################################

from __future__ import with_statement

import os
import sqlite3

import plexpy

from plexpy import logger


def dbFilename(filename):

    return os.path.join(plexpy.DATA_DIR, filename)


def getCacheSize():
    #this will protect against typecasting problems produced by empty string and None settings
    if not plexpy.CONFIG.CACHE_SIZEMB:
        #sqlite will work with this (very slowly)
        return 0
    return int(plexpy.CONFIG.CACHE_SIZEMB)


class DBConnection:

    def __init__(self):

        self.filename = plexpy.CONFIG.PLEXWATCH_DATABASE
        #self.connection = sqlite3.connect(dbFilename(plexpy.CONFIG.PLEXWATCH_DATABASE), timeout=20)
        self.connection = sqlite3.connect(plexpy.CONFIG.PLEXWATCH_DATABASE, timeout=20)
        #don't wait for the disk to finish writing
        self.connection.execute("PRAGMA synchronous = OFF")
        #journal disabled since we never do rollbacks
        self.connection.execute("PRAGMA journal_mode = %s" % plexpy.CONFIG.JOURNAL_MODE)
        #64mb of cache memory,probably need to make it user configurable
        self.connection.execute("PRAGMA cache_size=-%s" % (getCacheSize() * 1024))
        self.connection.row_factory = sqlite3.Row

    def action(self, query, args=None):

        if query is None:
            return

        sqlResult = None

        try:
            with self.connection as c:
                if args is None:
                    sqlResult = c.execute(query)
                else:
                    sqlResult = c.execute(query, args)

        except sqlite3.OperationalError, e:
            if "unable to open database file" in e.message or "database is locked" in e.message:
                logger.warn('Database Error: %s', e)
            else:
                logger.error('Database error: %s', e)
                raise

        except sqlite3.DatabaseError, e:
            logger.error('Fatal Error executing %s :: %s', query, e)
            raise

        return sqlResult

    def select(self, query, args=None):

        sqlResults = self.action(query, args).fetchall()

        if sqlResults is None or sqlResults == [None]:
            return []

        return sqlResults

    def select_single(self, query, args=None):

        sqlResult = self.action(query, args).fetchone()[0]

        if sqlResult is None or sqlResult == "":
            return ""

        return sqlResult

    def get_history_table_name(self):

        if plexpy.CONFIG.GROUPING_GLOBAL_HISTORY:
            return "grouped"
        else:
            return "processed"

    def get_user_table_name(self):

        if plexpy.CONFIG.GROUPING_USER_HISTORY:
            return "grouped"
        else:
            return "processed"

    def upsert(self, tableName, valueDict, keyDict):

        changesBefore = self.connection.total_changes

        genParams = lambda myDict: [x + " = ?" for x in myDict.keys()]

        update_query = "UPDATE " + tableName + " SET " + ", ".join(genParams(valueDict)) + " WHERE " + " AND ".join(genParams(keyDict))

        self.action(update_query, valueDict.values() + keyDict.values())

        if self.connection.total_changes == changesBefore:
            insert_query = (
                "INSERT INTO " + tableName + " (" + ", ".join(valueDict.keys() + keyDict.keys()) + ")" +
                " VALUES (" + ", ".join(["?"] * len(valueDict.keys() + keyDict.keys())) + ")"
            )
            try:
                self.action(insert_query, valueDict.values() + keyDict.values())
            except sqlite3.IntegrityError:
                logger.info('Queries failed: %s and %s', update_query, insert_query)
