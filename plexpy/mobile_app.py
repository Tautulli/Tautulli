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

import plexpy
import database
import helpers
import logger


def get_mobile_devices(device_id=None, device_token=None):
    where = where_id = where_token = ''
    args = []

    if device_id or device_token:
        where = 'WHERE '
        if device_id:
            where_id += 'device_id = ?'
            args.append(device_id)
        if device_token:
            where_token = 'device_token = ?'
            args.append(device_token)
        where += ' AND '.join([w for w in [where_id, where_token] if w])

    monitor_db = database.MonitorDatabase()
    result = monitor_db.select('SELECT * FROM mobile_devices %s' % where, args=args)

    return result


def delete_mobile_device(device_id=None):
    monitor_db = database.MonitorDatabase()

    if device_id:
        logger.debug(u"PlexPy Notifiers :: Deleting device_id %s from the database." % device_id)
        result = monitor_db.action('DELETE FROM mobile_devices WHERE device_id = ?', args=[device_id])
        return True
    else:
        return False

