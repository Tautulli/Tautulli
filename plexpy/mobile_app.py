# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
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

from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str

import time

import plexpy
if plexpy.PYTHON_VERSION < 3:
    import database
    import logger
else:
    from plexpy import database
    from plexpy import logger


TEMP_DEVICE_TOKEN = None


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

    db = database.MonitorDatabase()
    result = db.select('SELECT * FROM mobile_devices %s' % where, args=args)

    return result


def get_mobile_device_by_token(device_token=None):
    if not device_token:
        return None

    return get_mobile_devices(device_token=device_token)


def add_mobile_device(device_id=None, device_name=None, device_token=None, friendly_name=None):
    db = database.MonitorDatabase()

    keys = {'device_id': device_id}
    values = {'device_name': device_name,
              'device_token': device_token}

    if friendly_name:
        values['friendly_name'] = friendly_name

    try:
        result = db.upsert(table_name='mobile_devices', key_dict=keys, value_dict=values)
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to register mobile device in the database: %s." % e)
        return

    if result == 'insert':
        logger.info("Tautulli MobileApp :: Registered mobile device '%s' in the database." % device_name)
    else:
        logger.debug("Tautulli MobileApp :: Re-registered mobile device '%s' in the database." % device_name)

    return True


def get_mobile_device_config(mobile_device_id=None):
    if str(mobile_device_id).isdigit():
        mobile_device_id = int(mobile_device_id)
    else:
        logger.error("Tautulli MobileApp :: Unable to retrieve mobile device config: invalid mobile_device_id %s." % mobile_device_id)
        return None

    db = database.MonitorDatabase()
    result = db.select_single('SELECT * FROM mobile_devices WHERE id = ?',
                              args=[mobile_device_id])

    return result


def set_mobile_device_config(mobile_device_id=None, **kwargs):
    if str(mobile_device_id).isdigit():
        mobile_device_id = int(mobile_device_id)
    else:
        logger.error("Tautulli MobileApp :: Unable to set exisiting mobile device: invalid mobile_device_id %s." % mobile_device_id)
        return False

    keys = {'id': mobile_device_id}
    values = {}

    if kwargs.get('friendly_name'):
        values['friendly_name'] = kwargs['friendly_name']

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='mobile_devices', key_dict=keys, value_dict=values)
        logger.info("Tautulli MobileApp :: Updated mobile device agent: mobile_device_id %s." % mobile_device_id)
        return True
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Unable to update mobile device: %s." % e)
        return False


def delete_mobile_device(mobile_device_id=None):
    db = database.MonitorDatabase()

    if mobile_device_id:
        logger.debug("Tautulli MobileApp :: Deleting device_id %s from the database." % mobile_device_id)
        result = db.action('DELETE FROM mobile_devices WHERE id = ?', args=[mobile_device_id])
        return True
    else:
        return False


def set_last_seen(device_token=None):
    db = database.MonitorDatabase()

    last_seen = int(time.time())

    try:
        result = db.action('UPDATE mobile_devices SET last_seen = ? WHERE device_token = ?',
                           args=[last_seen, device_token])
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to set last_seen time for device: %s." % e)
        return


def blacklist_logger():
    devices = get_mobile_devices()
    for d in devices:
        logger.blacklist_config(d)
