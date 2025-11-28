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

from ipaddress import ip_address, ip_network
import time

import plexpy
from plexpy import database
from plexpy import helpers
from plexpy import logger


class IPBlacklist(object):

    def __init__(self):
        pass

    def is_blacklisted(self, ip_addr):
        """Check if an IP address is blacklisted."""
        if not plexpy.CONFIG.SECURITY_BLACKLIST_ENABLED:
            return False

        if not ip_addr:
            return False

        db = database.MonitorDatabase()

        # Check exact match first
        query = """SELECT id, ip_address, ip_type, reason, expires_at
                   FROM ip_blacklist
                   WHERE is_active = 1
                   AND (expires_at IS NULL OR expires_at > ?)"""
        results = db.select(query, [helpers.timestamp()])

        for row in results:
            if self._ip_matches(ip_addr, row['ip_address'], row['ip_type']):
                return {
                    'id': row['id'],
                    'ip_address': row['ip_address'],
                    'reason': row['reason']
                }

        return False

    def _ip_matches(self, ip_addr, blacklist_ip, ip_type):
        """Check if IP matches blacklist entry."""
        try:
            if ip_type == 'range':
                network = ip_network(blacklist_ip, strict=False)
                return ip_address(ip_addr) in network
            else:
                return ip_addr == blacklist_ip
        except (ValueError, TypeError):
            return False

    def add_to_blacklist(self, ip_addr, reason=None, ip_type='single',
                         expires_at=None, created_by=None):
        """Add an IP address to the blacklist."""
        db = database.MonitorDatabase()

        values = {
            'ip_address': ip_addr,
            'ip_type': ip_type,
            'reason': reason,
            'created_at': helpers.timestamp(),
            'created_by': created_by,
            'expires_at': expires_at,
            'is_active': 1
        }

        try:
            db.upsert('ip_blacklist', values, {'ip_address': ip_addr})
            logger.info("Tautulli Blacklist :: Added IP %s to blacklist. Reason: %s" %
                        (ip_addr, reason))
            return True
        except Exception as e:
            logger.error("Tautulli Blacklist :: Error adding IP to blacklist: %s" % e)
            return False

    def remove_from_blacklist(self, ip_addr=None, blacklist_id=None):
        """Remove an IP address from the blacklist."""
        db = database.MonitorDatabase()

        try:
            if blacklist_id:
                db.action("DELETE FROM ip_blacklist WHERE id = ?", [blacklist_id])
            elif ip_addr:
                db.action("DELETE FROM ip_blacklist WHERE ip_address = ?", [ip_addr])
            logger.info("Tautulli Blacklist :: Removed IP from blacklist")
            return True
        except Exception as e:
            logger.error("Tautulli Blacklist :: Error removing IP from blacklist: %s" % e)
            return False

    def get_blacklist(self, include_expired=False):
        """Get all blacklisted IPs."""
        db = database.MonitorDatabase()

        if include_expired:
            query = "SELECT * FROM ip_blacklist ORDER BY created_at DESC"
            results = db.select(query)
        else:
            query = """SELECT * FROM ip_blacklist
                       WHERE is_active = 1
                       AND (expires_at IS NULL OR expires_at > ?)
                       ORDER BY created_at DESC"""
            results = db.select(query, [helpers.timestamp()])

        return results

    def update_blacklist_entry(self, blacklist_id, **kwargs):
        """Update a blacklist entry."""
        db = database.MonitorDatabase()

        allowed_fields = ['ip_address', 'ip_type', 'reason', 'expires_at', 'is_active']
        values = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not values:
            return False

        try:
            db.upsert('ip_blacklist', values, {'id': blacklist_id})
            return True
        except Exception as e:
            logger.error("Tautulli Blacklist :: Error updating blacklist entry: %s" % e)
            return False

    def log_blocked_stream(self, session_key, user_id, ip_addr, reason,
                           block_type='blacklist', violation_id=None):
        """Log a blocked stream attempt."""
        db = database.MonitorDatabase()

        values = {
            'session_key': session_key,
            'user_id': user_id,
            'ip_address': ip_addr,
            'reason': reason,
            'block_type': block_type,
            'violation_id': violation_id,
            'created_at': helpers.timestamp()
        }

        try:
            db.action(
                "INSERT INTO blocked_streams "
                "(session_key, user_id, ip_address, reason, block_type, violation_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [values['session_key'], values['user_id'], values['ip_address'],
                 values['reason'], values['block_type'], values['violation_id'],
                 values['created_at']]
            )
            return True
        except Exception as e:
            logger.error("Tautulli Blacklist :: Error logging blocked stream: %s" % e)
            return False

    def get_blocked_streams(self, user_id=None, limit=100):
        """Get blocked stream log."""
        db = database.MonitorDatabase()

        if user_id:
            query = """SELECT * FROM blocked_streams
                       WHERE user_id = ?
                       ORDER BY created_at DESC LIMIT ?"""
            results = db.select(query, [user_id, limit])
        else:
            query = """SELECT * FROM blocked_streams
                       ORDER BY created_at DESC LIMIT ?"""
            results = db.select(query, [limit])

        return results
