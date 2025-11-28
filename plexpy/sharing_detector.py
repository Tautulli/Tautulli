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

import json
import time

import plexpy
from plexpy import database
from plexpy import helpers
from plexpy import logger


class SharingDetector(object):
    """Detect account sharing violations."""

    RULE_TYPES = ['simultaneous_locations', 'impossible_travel', 'device_velocity',
                  'concurrent_streams', 'geo_restriction']

    def check_all_rules(self, session):
        """Check all active rules against a session."""
        if not plexpy.CONFIG.SECURITY_SHARING_DETECTION:
            return []

        violations = []
        rules = self.get_active_rules(user_id=session.get('user_id'))

        for rule in rules:
            result = self.check_rule(rule, session)
            if result:
                violations.append(result)

        return violations

    def check_rule(self, rule, session):
        """Check a single rule against a session."""
        rule_type = rule.get('rule_type')
        params = json.loads(rule.get('params', '{}')) if rule.get('params') else {}

        if rule_type == 'simultaneous_locations':
            return self._check_simultaneous_locations(rule, session, params)
        elif rule_type == 'impossible_travel':
            return self._check_impossible_travel(rule, session, params)
        elif rule_type == 'device_velocity':
            return self._check_device_velocity(rule, session, params)
        elif rule_type == 'concurrent_streams':
            return self._check_concurrent_streams(rule, session, params)
        elif rule_type == 'geo_restriction':
            return self._check_geo_restriction(rule, session, params)

        return None

    def _check_simultaneous_locations(self, rule, session, params):
        """Check if user is streaming from multiple distant locations."""
        db = database.MonitorDatabase()
        user_id = session.get('user_id')
        min_distance = params.get('min_distance_km', 100)

        query = """SELECT session_key, ip_address, geo_latitude, geo_longitude
                   FROM sessions
                   WHERE user_id = ? AND state = 'playing'
                   AND session_key != ?"""
        other_sessions = db.select(query, [user_id, session.get('session_key', '')])

        current_lat = session.get('geo_latitude')
        current_lon = session.get('geo_longitude')

        if not current_lat or not current_lon:
            return None

        for other in other_sessions:
            other_lat = other.get('geo_latitude')
            other_lon = other.get('geo_longitude')

            if other_lat and other_lon:
                distance = helpers.calculate_distance(
                    current_lat, current_lon, other_lat, other_lon
                )
                if distance and distance > min_distance:
                    return self._create_violation(
                        rule=rule,
                        session=session,
                        severity='warning',
                        data={
                            'distance_km': round(distance, 2),
                            'other_session': other.get('session_key'),
                            'other_ip': other.get('ip_address')
                        }
                    )
        return None

    def _check_impossible_travel(self, rule, session, params):
        """Check for impossible travel speed between sessions."""
        db = database.MonitorDatabase()
        user_id = session.get('user_id')
        max_speed_kmh = params.get('max_speed_kmh', plexpy.CONFIG.SECURITY_IMPOSSIBLE_TRAVEL_SPEED)

        current_lat = session.get('geo_latitude')
        current_lon = session.get('geo_longitude')
        current_time = helpers.timestamp()

        if not current_lat or not current_lon:
            return None

        query = """SELECT started, stopped, geo_latitude, geo_longitude, ip_address
                   FROM session_history
                   WHERE user_id = ?
                   AND geo_latitude IS NOT NULL
                   AND geo_longitude IS NOT NULL
                   ORDER BY stopped DESC LIMIT 1"""
        result = db.select_single(query, [user_id])

        if not result:
            return None

        prev_lat = result.get('geo_latitude')
        prev_lon = result.get('geo_longitude')
        prev_time = result.get('stopped')

        if not prev_lat or not prev_lon or not prev_time:
            return None

        distance = helpers.calculate_distance(current_lat, current_lon, prev_lat, prev_lon)
        time_diff_hours = (current_time - prev_time) / 3600

        if time_diff_hours <= 0 or distance is None:
            return None

        speed = distance / time_diff_hours

        if speed > max_speed_kmh:
            return self._create_violation(
                rule=rule,
                session=session,
                severity='high',
                data={
                    'calculated_speed_kmh': round(speed, 2),
                    'distance_km': round(distance, 2),
                    'time_hours': round(time_diff_hours, 2),
                    'previous_ip': result.get('ip_address')
                }
            )
        return None

    def _check_device_velocity(self, rule, session, params):
        """Check for rapid switching between devices/IPs."""
        db = database.MonitorDatabase()
        user_id = session.get('user_id')
        max_unique = params.get('max_unique_ips', 5)
        time_window = params.get('time_window_hours', 24)

        cutoff = helpers.timestamp() - (time_window * 3600)

        query = """SELECT COUNT(DISTINCT ip_address) as unique_ips
                   FROM session_history
                   WHERE user_id = ? AND started > ?"""
        result = db.select_single(query, [user_id, cutoff])

        unique_count = result.get('unique_ips', 0) if result else 0

        if unique_count >= max_unique:
            return self._create_violation(
                rule=rule,
                session=session,
                severity='warning',
                data={
                    'unique_ips': unique_count,
                    'time_window_hours': time_window
                }
            )
        return None

    def _check_concurrent_streams(self, rule, session, params):
        """Check for too many concurrent streams."""
        db = database.MonitorDatabase()
        user_id = session.get('user_id')
        max_streams = params.get('max_streams', 3)

        query = """SELECT COUNT(*) as active_count
                   FROM sessions
                   WHERE user_id = ? AND state = 'playing'
                   AND session_key != ?"""
        result = db.select_single(query, [user_id, session.get('session_key', '')])

        active_count = result.get('active_count', 0) if result else 0

        if active_count >= max_streams:
            return self._create_violation(
                rule=rule,
                session=session,
                severity='warning',
                data={
                    'active_streams': active_count,
                    'max_allowed': max_streams
                }
            )
        return None

    def _check_geo_restriction(self, rule, session, params):
        """Check if stream is from allowed/blocked regions."""
        allowed_countries = params.get('allowed_countries', [])
        blocked_countries = params.get('blocked_countries', [])

        country = session.get('geo_country')

        if not country:
            return None

        if allowed_countries and country not in allowed_countries:
            return self._create_violation(
                rule=rule,
                session=session,
                severity='high',
                data={
                    'country': country,
                    'allowed_countries': allowed_countries
                }
            )

        if blocked_countries and country in blocked_countries:
            return self._create_violation(
                rule=rule,
                session=session,
                severity='high',
                data={
                    'country': country,
                    'blocked_countries': blocked_countries
                }
            )

        return None

    def _create_violation(self, rule, session, severity, data):
        """Create and log a violation."""
        violation = {
            'rule_id': rule.get('id'),
            'rule_type': rule.get('rule_type'),
            'rule_name': rule.get('name'),
            'user_id': session.get('user_id'),
            'session_key': session.get('session_key'),
            'severity': severity,
            'data': data
        }

        if plexpy.CONFIG.SECURITY_LOG_VIOLATIONS:
            self.log_violation(violation)

        return violation

    def log_violation(self, violation):
        """Log a violation to the database."""
        db = database.MonitorDatabase()

        try:
            db.action(
                "INSERT INTO sharing_violations "
                "(rule_id, rule_type, user_id, session_key, violation_data, severity, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [violation.get('rule_id'), violation.get('rule_type'),
                 violation.get('user_id'), violation.get('session_key'),
                 json.dumps(violation.get('data', {})), violation.get('severity'),
                 helpers.timestamp()]
            )
        except Exception as e:
            logger.error("Tautulli SharingDetector :: Error logging violation: %s" % e)

    def get_violations(self, user_id=None, rule_type=None, severity=None, limit=100):
        """Get violations from the database."""
        db = database.MonitorDatabase()

        query = "SELECT * FROM sharing_violations WHERE 1=1"
        args = []

        if user_id:
            query += " AND user_id = ?"
            args.append(user_id)
        if rule_type:
            query += " AND rule_type = ?"
            args.append(rule_type)
        if severity:
            query += " AND severity = ?"
            args.append(severity)

        query += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)

        return db.select(query, args)

    def get_active_rules(self, user_id=None):
        """Get active sharing rules."""
        db = database.MonitorDatabase()

        query = "SELECT * FROM sharing_rules WHERE is_active = 1"
        args = []

        if user_id:
            query += " AND (user_id IS NULL OR user_id = ?)"
            args.append(user_id)

        return db.select(query, args) if args else db.select(query)

    def add_rule(self, name, rule_type, params=None, user_id=None):
        """Add a new sharing detection rule."""
        if rule_type not in self.RULE_TYPES:
            logger.error("Tautulli SharingDetector :: Invalid rule type: %s" % rule_type)
            return None

        db = database.MonitorDatabase()

        try:
            db.action(
                "INSERT INTO sharing_rules (name, rule_type, params, user_id, is_active, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 1, ?, ?)",
                [name, rule_type, json.dumps(params) if params else None,
                 user_id, helpers.timestamp(), helpers.timestamp()]
            )
            return db.last_insert_id()
        except Exception as e:
            logger.error("Tautulli SharingDetector :: Error adding rule: %s" % e)
            return None

    def update_rule(self, rule_id, **kwargs):
        """Update an existing rule."""
        db = database.MonitorDatabase()

        allowed_fields = ['name', 'params', 'user_id', 'is_active']
        values = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not values:
            return False

        if 'params' in values and isinstance(values['params'], dict):
            values['params'] = json.dumps(values['params'])

        values['updated_at'] = helpers.timestamp()

        try:
            db.upsert('sharing_rules', values, {'id': rule_id})
            return True
        except Exception as e:
            logger.error("Tautulli SharingDetector :: Error updating rule: %s" % e)
            return False

    def delete_rule(self, rule_id):
        """Delete a rule."""
        db = database.MonitorDatabase()

        try:
            db.action("DELETE FROM sharing_rules WHERE id = ?", [rule_id])
            return True
        except Exception as e:
            logger.error("Tautulli SharingDetector :: Error deleting rule: %s" % e)
            return False

    def get_violation_stats(self, time_range_days=30):
        """Get violation statistics."""
        db = database.MonitorDatabase()
        cutoff = helpers.timestamp() - (time_range_days * 24 * 3600)

        stats = {
            'total': 0,
            'by_type': {},
            'by_severity': {},
            'by_user': {}
        }

        # Total count
        result = db.select_single(
            "SELECT COUNT(*) as count FROM sharing_violations WHERE created_at > ?",
            [cutoff]
        )
        stats['total'] = result.get('count', 0) if result else 0

        # By type
        results = db.select(
            "SELECT rule_type, COUNT(*) as count FROM sharing_violations "
            "WHERE created_at > ? GROUP BY rule_type",
            [cutoff]
        )
        for row in results:
            stats['by_type'][row['rule_type']] = row['count']

        # By severity
        results = db.select(
            "SELECT severity, COUNT(*) as count FROM sharing_violations "
            "WHERE created_at > ? GROUP BY severity",
            [cutoff]
        )
        for row in results:
            stats['by_severity'][row['severity']] = row['count']

        # By user (top 10)
        results = db.select(
            "SELECT user_id, COUNT(*) as count FROM sharing_violations "
            "WHERE created_at > ? GROUP BY user_id ORDER BY count DESC LIMIT 10",
            [cutoff]
        )
        for row in results:
            stats['by_user'][row['user_id']] = row['count']

        return stats


def run_scheduled_scan():
    """Run a scheduled scan of all active sessions for sharing violations.
    Called by APScheduler at the configured interval.
    """
    if not plexpy.CONFIG.SECURITY_ENABLED or not plexpy.CONFIG.SECURITY_SHARING_DETECTION:
        return

    logger.debug("Tautulli SharingDetector :: Running scheduled sharing detection scan")

    db = database.MonitorDatabase()
    detector = SharingDetector()

    # Get all active sessions
    query = """SELECT s.*, u.friendly_name
               FROM sessions s
               LEFT JOIN users u ON s.user_id = u.user_id
               WHERE s.state = 'playing'"""
    sessions = db.select(query)

    if not sessions:
        return

    violation_count = 0
    for session in sessions:
        violations = detector.check_all_rules(session)
        for violation in violations:
            detector.log_violation(violation)
            violation_count += 1

    if violation_count > 0:
        logger.info("Tautulli SharingDetector :: Found %d sharing violations in scheduled scan",
                    violation_count)
