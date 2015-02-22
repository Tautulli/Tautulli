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

from plexpy import db, updater, cache, versioncheck, logger

import plexpy
import json

cmd_list = ['getLogs', 'getVersion', 'checkGithub', 'shutdown', 'restart', 'update']


class Api(object):

    def __init__(self):

        self.apikey = None
        self.cmd = None
        self.id = None

        self.kwargs = None

        self.data = None

        self.callback = None

    def checkParams(self, *args, **kwargs):

        if not plexpy.CONFIG.API_ENABLED:
            self.data = 'API not enabled'
            return
        if not plexpy.CONFIG.API_KEY:
            self.data = 'API key not generated'
            return
        if len(plexpy.CONFIG.API_KEY) != 32:
            self.data = 'API key not generated correctly'
            return

        if 'apikey' not in kwargs:
            self.data = 'Missing api key'
            return

        if kwargs['apikey'] != plexpy.CONFIG.API_KEY:
            self.data = 'Incorrect API key'
            return
        else:
            self.apikey = kwargs.pop('apikey')

        if 'cmd' not in kwargs:
            self.data = 'Missing parameter: cmd'
            return

        if kwargs['cmd'] not in cmd_list:
            self.data = 'Unknown command: %s' % kwargs['cmd']
            return
        else:
            self.cmd = kwargs.pop('cmd')

        self.kwargs = kwargs
        self.data = 'OK'

    def fetchData(self):

        if self.data == 'OK':
            logger.info('Recieved API command: %s', self.cmd)
            methodToCall = getattr(self, "_" + self.cmd)
            methodToCall(**self.kwargs)
            if 'callback' not in self.kwargs:
                if isinstance(self.data, basestring):
                    return self.data
                else:
                    return json.dumps(self.data)
            else:
                self.callback = self.kwargs['callback']
                self.data = json.dumps(self.data)
                self.data = self.callback + '(' + self.data + ');'
                return self.data
        else:
            return self.data

    def _dic_from_query(self, query):

        myDB = db.DBConnection()
        rows = myDB.select(query)

        rows_as_dic = []

        for row in rows:
            row_as_dic = dict(zip(row.keys(), row))
            rows_as_dic.append(row_as_dic)

        return rows_as_dic

    def _getLogs(self, **kwargs):
        pass

    def _getVersion(self, **kwargs):
        self.data = {
            'git_path': plexpy.CONFIG.GIT_PATH,
            'install_type': plexpy.INSTALL_TYPE,
            'current_version': plexpy.CURRENT_VERSION,
            'latest_version': plexpy.LATEST_VERSION,
            'commits_behind': plexpy.COMMITS_BEHIND,
        }

    def _checkGithub(self, **kwargs):
        versioncheck.checkGithub()
        self._getVersion()

    def _shutdown(self, **kwargs):
        plexpy.SIGNAL = 'shutdown'

    def _restart(self, **kwargs):
        plexpy.SIGNAL = 'restart'

    def _update(self, **kwargs):
        plexpy.SIGNAL = 'update'
