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

import plexpy
if plexpy.PYTHON2:
    import pmsconnect
else:
    from plexpy import pmsconnect

pmsServers = []
totalServers = 0

class ServerManger(object):
    """
    Return list of cached servers

    Output: array of servers

    """
    def get_server_list(self):
        global totalServers
        global pmsServers
        if totalServers != 0 :
            return pmsServers
        for server in pmsconnect.PmsConnect().get_servers_info():
            url = 'http://{hostname}:{port}'.format(hostname=server["host"], port=server["port"])
            pmsServers.append(pmsconnect.PmsConnect(server['machine_identifier'], url=url))
        totalServers = len(pmsServers)
        return pmsServers
    
    """
    Return server by id or None

    Output: PmsConnect

    """
    def get_server(self, server_id):
        if server_id is not None:
            global pmsServers
            for server in pmsServers:
                if server_id == server.server_id:
                    return server
            for server in pmsconnect.PmsConnect().get_servers_info():
                if server['machine_identifier'] == server_id:
                    url = 'http://{hostname}:{port}'.format(hostname=server["host"], port=server["port"])
                    new = pmsconnect.PmsConnect(server_id, url=url)
                    pmsServers.append(new)
                    return new
        return None