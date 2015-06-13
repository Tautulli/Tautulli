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

from plexpy import db, cache, versioncheck, logger, helpers

import plexpy
import json
from xml.dom import minidom

cmd_list = ['getHistory', 'getLogs', 'getVersion', 'checkGithub', 'shutdown', 'restart', 'update']


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

    def _getHistory(self, iDisplayStart=0, iDisplayLength=100, sSearch="", iSortCol_0='0', sSortDir_0='asc', **kwargs):
        iDisplayStart = int(iDisplayStart)
        iDisplayLength = int(iDisplayLength)
        filtered = []
        totalcount = 0
        myDB = db.DBConnection()
        db_table = db.DBConnection().get_history_table_name()

        sortcolumn = 'time'
        sortbyhavepercent = False
        if iSortCol_0 == '1':
            sortcolumn = 'user'
        if iSortCol_0 == '2':
            sortcolumn = 'platform'
        elif iSortCol_0 == '3':
            sortcolumn = 'ip_address'
        elif iSortCol_0 == '4':
            sortcolumn = 'title'
        elif iSortCol_0 == '5':
            sortcolumn = 'time'
        elif iSortCol_0 == '6':
            sortcolumn = 'paused_counter'
        elif iSortCol_0 == '7':
            sortcolumn = 'stopped'
        elif iSortCol_0 == '8':
            sortbyhavepercent = True

        if sSearch == "":
            query = 'SELECT * from %s order by %s COLLATE NOCASE %s' % (db_table, sortcolumn, sSortDir_0)
            filtered = myDB.select(query)
            totalcount = len(filtered)
        else:
            query = 'SELECT * from ' + db_table + ' WHERE user LIKE "%' + sSearch + \
                    '%" OR title LIKE "%' + sSearch + '%"' + 'ORDER BY %s COLLATE NOCASE %s' % (sortcolumn, sSortDir_0)
            filtered = myDB.select(query)
            totalcount = myDB.select('SELECT COUNT(*) from processed')[0][0]

        history = filtered[iDisplayStart:(iDisplayStart + iDisplayLength)]
        rows = []
        for item in history:
            row = {"date": item['time'],
                      "user": item["user"],
                      "platform": item["platform"],
                      "ip_address": item["ip_address"],
                      "title": item["title"],
                      "started": item["time"],
                      "paused": item["paused_counter"],
                      "stopped": item["stopped"],
                      "duration": "",
                      "percent_complete": 0,
                      }

            if item['paused_counter'] > 0:
                row['paused'] = item['paused_counter']
            else:
                row['paused'] = 0

            if item['time']:
                if item['stopped'] > 0:
                    stopped = item['stopped']
                else:
                    stopped = 0
                if item['paused_counter'] > 0:
                    paused_counter = item['paused_counter']
                else:
                    paused_counter = 0

                row['duration'] = stopped - item['time'] + paused_counter

            try:
                xml_parse = minidom.parseString(helpers.latinToAscii(item['xml']))
            except IOError, e:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            xml_head = xml_parse.getElementsByTagName('opt')
            if not xml_head:
                logger.warn("Error parsing XML in PlexWatch db: %s" % e)

            for s in xml_head:
                if s.getAttribute('duration') and s.getAttribute('viewOffset'):
                    view_offset = helpers.cast_to_float(s.getAttribute('viewOffset'))
                    duration = helpers.cast_to_float(s.getAttribute('duration'))
                    if duration > 0:
                        row['percent_complete'] = (view_offset / duration)*100
                    else:
                        row['percent_complete'] = 0

            rows.append(row)

        dict = {'iTotalDisplayRecords': len(filtered),
                'iTotalRecords': totalcount,
                'aaData': rows,
                }
        self.data = json.dumps(dict)
        #cherrypy.response.headers['Content-type'] = 'application/json'

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
