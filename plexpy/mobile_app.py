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

import hashlib
import requests
import threading
import time

import plexpy
from plexpy import database
from plexpy import helpers
from plexpy import logger


_ONESIGNAL_APP_ID = '3b4b666a-d557-4b92-acdf-e2c8c4b95357'
_ONESIGNAL_DISABLED = 'onesignal-disabled'
_PUSH_DISABLED = 'push-disabled'

_REVALIDATE_INTERVAL = 2  # seconds; the relay rate limits /v1/validate per client IP

TEMP_DEVICE_TOKENS = {}


def relay_device_id(push_token):
    """
    Return the identifier the relay records and Tautulli Remote shows on its
    data dump page. The push token itself is blacklisted from the logs.
    """
    if not push_token or push_token == _PUSH_DISABLED:
        return 'none'
    return hashlib.sha256(push_token.encode()).hexdigest()[:16]


def set_temp_device_token(token=None, remove=False, add=False, success=False):
    global TEMP_DEVICE_TOKENS

    if token in TEMP_DEVICE_TOKENS and success:
        if isinstance(TEMP_DEVICE_TOKENS[token], threading.Timer):
            TEMP_DEVICE_TOKENS[token].cancel()
        TEMP_DEVICE_TOKENS[token] = True

    elif token in TEMP_DEVICE_TOKENS and remove:
        if isinstance(TEMP_DEVICE_TOKENS[token], threading.Timer):
            TEMP_DEVICE_TOKENS[token].cancel()
        del TEMP_DEVICE_TOKENS[token]

    elif token not in TEMP_DEVICE_TOKENS and add:
        invalidate_time = 5 * 60  # 5 minutes
        TEMP_DEVICE_TOKENS[token] = threading.Timer(invalidate_time, set_temp_device_token, args=[token, True])
        TEMP_DEVICE_TOKENS[token].start()
        logger._BLACKLIST_WORDS.add(token)


def get_temp_device_token(token=None):
    return TEMP_DEVICE_TOKENS.get(token)


def get_mobile_devices(device_id=None, device_token=None):
    where = where_id = where_token = ''
    args = []

    if device_id or device_token:
        where = "WHERE "
        if device_id:
            where_id += "device_id = ?"
            args.append(device_id)
        if device_token:
            where_token = "device_token = ?"
            args.append(device_token)
        where += " AND ".join([w for w in [where_id, where_token] if w])

    db = database.MonitorDatabase()
    result = db.select("SELECT * FROM mobile_devices %s" % where, args=args)

    return result


def get_mobile_device_by_token(device_token=None):
    if not device_token:
        return None

    return get_mobile_devices(device_token=device_token)


def add_mobile_device(device_id=None, device_name=None, device_token=None,
                      platform=None, version=None, friendly_name=None, onesignal_id=None,
                      push_token=None):
    db = database.MonitorDatabase()

    keys = {'device_id': device_id}
    values = {'device_name': device_name,
              'device_token': device_token,
              'platform': platform,
              'version': version,
              'onesignal_id': onesignal_id,
              'push_token': push_token}

    if friendly_name:
        values['friendly_name'] = friendly_name

    try:
        result = db.upsert(table_name='mobile_devices', key_dict=keys, value_dict=values)
        blacklist_logger()
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to register mobile device in the database: %s." % e)
        return

    if result == 'insert':
        logger.info("Tautulli MobileApp :: Registered mobile device '%s' in the database." % device_name)
    else:
        logger.info("Tautulli MobileApp :: Re-registered mobile device '%s' in the database." % device_name)

    set_last_seen(device_token=device_token)
    threading.Thread(target=set_official, args=[device_id, onesignal_id, push_token]).start()
    return True


def get_mobile_device_config(mobile_device_id=None):
    if str(mobile_device_id).isdigit():
        mobile_device_id = int(mobile_device_id)
    else:
        logger.error("Tautulli MobileApp :: Unable to retrieve mobile device config: invalid mobile_device_id %s." % mobile_device_id)
        return None

    db = database.MonitorDatabase()
    result = db.select_single("SELECT * FROM mobile_devices WHERE id = ?",
                              args=[mobile_device_id])

    if result['onesignal_id'] == _ONESIGNAL_DISABLED:
        result['onesignal_id'] = ''

    if result['push_token'] == _PUSH_DISABLED:
        result['push_token'] = ''

    result['relay_device_id'] = relay_device_id(result['push_token']) if result['push_token'] else ''

    return result


def set_mobile_device_config(mobile_device_id=None, **kwargs):
    if str(mobile_device_id).isdigit():
        mobile_device_id = int(mobile_device_id)
    else:
        logger.error("Tautulli MobileApp :: Unable to set existing mobile device: invalid mobile_device_id %s." % mobile_device_id)
        return False

    keys = {'id': mobile_device_id}
    values = {'friendly_name': kwargs.get('friendly_name', '')}

    db = database.MonitorDatabase()
    try:
        db.upsert(table_name='mobile_devices', key_dict=keys, value_dict=values)
        logger.info("Tautulli MobileApp :: Updated mobile device agent: mobile_device_id %s." % mobile_device_id)
        blacklist_logger()
        return True
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Unable to update mobile device: %s." % e)
        return False


def delete_mobile_device(mobile_device_id=None, device_id=None):
    db = database.MonitorDatabase()

    if mobile_device_id:
        logger.debug("Tautulli MobileApp :: Deleting mobile_device_id %s from the database." % mobile_device_id)
        result = db.action("DELETE FROM mobile_devices WHERE id = ?", args=[mobile_device_id])
        return True
    elif device_id:
        logger.debug("Tautulli MobileApp :: Deleting device_id %s from the database." % device_id)
        result = db.action("DELETE FROM mobile_devices WHERE device_id = ?", args=[device_id])
        return True
    else:
        return False


def set_official(device_id, onesignal_id, push_token=None):
    db = database.MonitorDatabase()

    # Newer app versions register a push token; older ones only send a OneSignal ID.
    if push_token:
        official = validate_push_token(push_token=push_token)
    else:
        official = validate_onesignal_id(onesignal_id=onesignal_id)

    # An indeterminate result says nothing about the token, so don't let it
    # clear a device that has already validated.
    where = "WHERE device_id = ?"
    if official == -1:
        where += " AND coalesce(official, 0) != 1"

    try:
        result = db.action("UPDATE mobile_devices "
                           "SET official = ? "
                           "%s" % where,
                           args=[official, device_id])
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to set official flag: %s." % e)
        return


def set_official_from_delivery(device, official):
    if device['official'] == official:
        return

    db = database.MonitorDatabase()

    try:
        db.action("UPDATE mobile_devices SET official = ? WHERE device_id = ?",
                  args=[official, device['device_id']])
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to set official flag for device %s: %s."
                    % (relay_device_id(device['push_token']), e))


def set_last_seen(device_token=None):
    db = database.MonitorDatabase()
    last_seen = helpers.timestamp()

    try:
        result = db.action("UPDATE mobile_devices SET last_seen = ? WHERE device_token = ?",
                           args=[last_seen, device_token])
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to set last_seen time for device: %s." % e)
        return


def validate_onesignal_id(onesignal_id):
    if onesignal_id is None:
        return 0
    elif onesignal_id == _ONESIGNAL_DISABLED:
        return 2

    headers = {'Content-Type': 'application/json'}

    logger.info("Tautulli MobileApp :: Validating OneSignal ID")
    try:
        r = requests.get(f'https://api.onesignal.com/apps/{_ONESIGNAL_APP_ID}/subscriptions/{onesignal_id}/user/identity', headers=headers)
        status_code = r.status_code
        logger.info("Tautulli MobileApp :: OneSignal ID validation returned status code %s", status_code)
        return int(status_code == 200)
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to validate OneSignal ID: %s." % e)
        return -1


def validate_push_token(push_token):
    if push_token == _PUSH_DISABLED:
        return 2

    payload = {'token': push_token}

    device_id = relay_device_id(push_token)

    logger.info("Tautulli MobileApp :: Validating push token for device %s", device_id)
    try:
        # A 307 or 308 would re-post the push token to wherever Location points.
        r = requests.post(f"{plexpy.CONFIG.REMOTE_APP_PUSH_URL.rstrip('/')}/v1/validate",
                          json=payload, timeout=10,
                          allow_redirects=False)
        status_code = r.status_code
        logger.info("Tautulli MobileApp :: Push token validation for device %s returned status code %s",
                    device_id, status_code)
        if status_code == 200:
            return 1
        elif status_code == 410:
            return 0
        # Anything else (rate limited, relay or FCM outage) says nothing about
        # the token itself, so do not mark the device as invalid.
        return -1
    except Exception as e:
        logger.warn("Tautulli MobileApp :: Failed to validate push token for device %s: %s." % (device_id, e))
        return -1


def validates_remotely(device):
    if device['push_token']:
        return device['push_token'] != _PUSH_DISABLED
    return bool(device['onesignal_id']) and device['onesignal_id'] != _ONESIGNAL_DISABLED


def revalidate_devices():
    # Runs on every startup; threaded so a blocked host cannot hold up boot.
    threading.Thread(target=_revalidate_devices).start()


def _revalidate_devices():
    # Re-validating a healthy device risks the relay's per-IP limit on
    # /v1/validate, and a device that opted out has no registration to check.
    devices = [d for d in get_mobile_devices() if d['official'] != 1 and validates_remotely(d)]

    if not devices:
        return

    logger.info("Tautulli MobileApp :: Validating %s mobile device registration(s).", len(devices))

    for device in devices:
        set_official(device['device_id'], device['onesignal_id'], device['push_token'])
        time.sleep(_REVALIDATE_INTERVAL)


def blacklist_logger():
    devices = get_mobile_devices()
    for d in devices:
        logger.blacklist_config(d)
