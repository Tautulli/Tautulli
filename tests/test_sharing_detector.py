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

"""Tests for plexpy.sharing_detector module.

These tests are isolated from the main Tautulli application by mocking
all external dependencies before importing the module.
"""

import json
import sys
import os
import types
import pytest
from unittest.mock import MagicMock, patch


class MockConfig:
    """Mock configuration for sharing detector tests."""

    SECURITY_ENABLED = True
    SECURITY_SHARING_DETECTION = True
    SECURITY_LOG_VIOLATIONS = True
    SECURITY_IMPOSSIBLE_TRAVEL_SPEED = 1000


# Create a proper mock package structure
mock_plexpy = types.ModuleType('plexpy')
mock_plexpy.__path__ = []  # Make it a package
mock_plexpy.CONFIG = MockConfig()

mock_database = types.ModuleType('plexpy.database')
mock_database.MonitorDatabase = MagicMock()

mock_helpers = types.ModuleType('plexpy.helpers')
mock_helpers.timestamp = MagicMock(return_value=1700000000)
mock_helpers.calculate_distance = MagicMock(return_value=500.0)

mock_logger = types.ModuleType('plexpy.logger')
mock_logger.debug = MagicMock()
mock_logger.info = MagicMock()
mock_logger.error = MagicMock()

# Clear any existing plexpy modules to avoid conflicts
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('plexpy'):
        del sys.modules[mod_name]

# Install mock modules
sys.modules['plexpy'] = mock_plexpy
sys.modules['plexpy.database'] = mock_database
sys.modules['plexpy.helpers'] = mock_helpers
sys.modules['plexpy.logger'] = mock_logger

# Add parent directory to path so we can import sharing_detector
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import the module under test - use importlib to force reload
import importlib.util
spec = importlib.util.spec_from_file_location(
    "plexpy.sharing_detector",
    os.path.join(project_root, "plexpy", "sharing_detector.py")
)
sharing_detector_module = importlib.util.module_from_spec(spec)
sys.modules['plexpy.sharing_detector'] = sharing_detector_module
spec.loader.exec_module(sharing_detector_module)

SharingDetector = sharing_detector_module.SharingDetector
run_scheduled_scan = sharing_detector_module.run_scheduled_scan


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset mock states before each test."""
    mock_plexpy.CONFIG.SECURITY_ENABLED = True
    mock_plexpy.CONFIG.SECURITY_SHARING_DETECTION = True
    mock_plexpy.CONFIG.SECURITY_LOG_VIOLATIONS = True
    mock_helpers.timestamp.return_value = 1700000000
    mock_helpers.calculate_distance.return_value = 500.0
    yield


@pytest.fixture
def mock_db():
    """Create a fresh mock database for each test."""
    db = MagicMock()
    db.select.return_value = []
    db.select_single.return_value = None
    db.action.return_value = True
    db.last_insert_id.return_value = 1
    mock_database.MonitorDatabase.return_value = db
    return db


@pytest.fixture
def detector():
    """Create a SharingDetector instance for testing."""
    return SharingDetector()


class TestCheckAllRules:
    """Test the check_all_rules method."""

    def test_returns_empty_when_detection_disabled(self, detector, mock_db):
        """Should return empty list when sharing detection is disabled."""
        mock_plexpy.CONFIG.SECURITY_SHARING_DETECTION = False

        session = {'user_id': 123, 'session_key': 'abc'}
        violations = detector.check_all_rules(session)

        assert violations == []

    def test_returns_violations_from_rules(self, detector, mock_db):
        """Should return violations when rules are triggered."""
        # Mock get_active_rules to return a test rule
        mock_db.select.return_value = [{
            'id': 1,
            'name': 'Test Rule',
            'rule_type': 'geo_restriction',
            'params': json.dumps({'blocked_countries': ['RU']})
        }]

        session = {
            'user_id': 123,
            'session_key': 'abc',
            'geo_country': 'RU'
        }

        violations = detector.check_all_rules(session)

        # Should have one violation for blocked country
        assert len(violations) == 1
        assert violations[0]['rule_type'] == 'geo_restriction'


class TestCheckRule:
    """Test check_rule dispatching."""

    @pytest.mark.parametrize("rule_type,handler", [
        ('simultaneous_locations', '_check_simultaneous_locations'),
        ('impossible_travel', '_check_impossible_travel'),
        ('device_velocity', '_check_device_velocity'),
        ('concurrent_streams', '_check_concurrent_streams'),
        ('geo_restriction', '_check_geo_restriction'),
    ])
    def test_routes_to_correct_handler(self, detector, rule_type, handler):
        """check_rule dispatches to type-specific handler."""
        with patch.object(detector, handler, return_value=None) as mock_handler:
            rule = {'id': 1, 'rule_type': rule_type, 'params': '{}'}
            detector.check_rule(rule, {'user_id': 123})
            mock_handler.assert_called_once()

    def test_returns_none_for_unknown_rule_type(self, detector, mock_db):
        """Unknown rule types return None."""
        rule = {'id': 1, 'rule_type': 'unknown_type', 'params': '{}'}
        assert detector.check_rule(rule, {'user_id': 123}) is None


class TestCheckSimultaneousLocations:
    """Test the _check_simultaneous_locations method."""

    def test_returns_none_without_coordinates(self, detector, mock_db):
        """Should return None if current session has no coordinates."""
        rule = {'id': 1, 'rule_type': 'simultaneous_locations'}
        session = {
            'user_id': 123,
            'session_key': 'abc',
            'geo_latitude': None,
            'geo_longitude': None
        }
        params = {'min_distance_km': 100}

        result = detector._check_simultaneous_locations(rule, session, params)

        assert result is None

    def test_returns_none_when_no_other_sessions(self, detector, mock_db):
        """Should return None if no other sessions exist."""
        mock_db.select.return_value = []

        rule = {'id': 1, 'rule_type': 'simultaneous_locations'}
        session = {
            'user_id': 123,
            'session_key': 'abc',
            'geo_latitude': 40.7128,
            'geo_longitude': -74.0060
        }
        params = {'min_distance_km': 100}

        result = detector._check_simultaneous_locations(rule, session, params)

        assert result is None

    def test_returns_violation_for_distant_sessions(self, detector, mock_db):
        """Should return violation when sessions are far apart."""
        # Mock another session that's far away
        mock_db.select.return_value = [{
            'session_key': 'xyz',
            'ip_address': '10.0.0.1',
            'geo_latitude': 34.0522,
            'geo_longitude': -118.2437
        }]
        # Distance > min_distance_km (500 > 100)
        mock_helpers.calculate_distance.return_value = 500.0

        rule = {
            'id': 1,
            'name': 'Test',
            'rule_type': 'simultaneous_locations'
        }
        session = {
            'user_id': 123,
            'session_key': 'abc',
            'geo_latitude': 40.7128,
            'geo_longitude': -74.0060
        }
        params = {'min_distance_km': 100}

        result = detector._check_simultaneous_locations(rule, session, params)

        assert result is not None
        assert result['rule_type'] == 'simultaneous_locations'
        assert result['data']['distance_km'] == 500.0


class TestCheckGeoRestriction:
    """Test the _check_geo_restriction method."""

    def test_returns_none_without_country(self, detector, mock_db):
        """Should return None if session has no country."""
        rule = {'id': 1, 'rule_type': 'geo_restriction'}
        session = {'user_id': 123, 'geo_country': None}
        params = {'allowed_countries': ['US']}

        result = detector._check_geo_restriction(rule, session, params)

        assert result is None

    def test_returns_none_when_country_allowed(self, detector, mock_db):
        """Should return None when country is in allowed list."""
        rule = {'id': 1, 'rule_type': 'geo_restriction'}
        session = {'user_id': 123, 'geo_country': 'US'}
        params = {'allowed_countries': ['US', 'CA', 'GB']}

        result = detector._check_geo_restriction(rule, session, params)

        assert result is None

    def test_returns_violation_for_disallowed_country(self, detector, mock_db):
        """Should return violation when country is not in allowed list."""
        rule = {'id': 1, 'name': 'Geo', 'rule_type': 'geo_restriction'}
        session = {
            'user_id': 123,
            'session_key': 'abc',
            'geo_country': 'RU'
        }
        params = {'allowed_countries': ['US', 'CA', 'GB']}

        result = detector._check_geo_restriction(rule, session, params)

        assert result is not None
        assert result['severity'] == 'high'
        assert result['data']['country'] == 'RU'

    def test_returns_violation_for_blocked_country(self, detector, mock_db):
        """Should return violation when country is in blocked list."""
        rule = {'id': 1, 'name': 'Geo', 'rule_type': 'geo_restriction'}
        session = {
            'user_id': 123,
            'session_key': 'abc',
            'geo_country': 'CN'
        }
        params = {'blocked_countries': ['CN', 'RU']}

        result = detector._check_geo_restriction(rule, session, params)

        assert result is not None
        assert result['severity'] == 'high'
        assert result['data']['country'] == 'CN'

    def test_returns_none_when_country_not_blocked(self, detector, mock_db):
        """Should return None when country is not in blocked list."""
        rule = {'id': 1, 'rule_type': 'geo_restriction'}
        session = {'user_id': 123, 'geo_country': 'US'}
        params = {'blocked_countries': ['CN', 'RU']}

        result = detector._check_geo_restriction(rule, session, params)

        assert result is None


class TestCheckConcurrentStreams:
    """Test concurrent streams detection."""

    def test_under_limit_no_violation(self, detector, mock_db):
        """Under limit returns None (no violation)."""
        mock_db.select_single.return_value = {'active_count': 2}

        rule = {'id': 1, 'rule_type': 'concurrent_streams'}
        session = {'user_id': 123, 'session_key': 'abc'}
        params = {'max_streams': 3}

        assert detector._check_concurrent_streams(rule, session, params) is None

    def test_at_limit_triggers_violation(self, detector, mock_db):
        """At limit (other_streams >= max) triggers violation."""
        mock_db.select_single.return_value = {'active_count': 3}

        rule = {'id': 1, 'name': 'Streams', 'rule_type': 'concurrent_streams'}
        session = {'user_id': 123, 'session_key': 'abc'}
        params = {'max_streams': 3}

        result = detector._check_concurrent_streams(rule, session, params)
        assert result is not None
        assert result['data']['active_streams'] == 3

    def test_over_limit_triggers_violation(self, detector, mock_db):
        """Over limit triggers violation with correct data."""
        mock_db.select_single.return_value = {'active_count': 5}

        rule = {'id': 1, 'name': 'Streams', 'rule_type': 'concurrent_streams'}
        session = {'user_id': 123, 'session_key': 'abc'}
        params = {'max_streams': 3}

        result = detector._check_concurrent_streams(rule, session, params)
        assert result['data']['active_streams'] == 5
        assert result['data']['max_allowed'] == 3


class TestCheckDeviceVelocity:
    """Test the _check_device_velocity method."""

    def test_returns_none_when_under_threshold(self, detector, mock_db):
        """Should return None when unique IPs is under threshold."""
        mock_db.select_single.return_value = {'unique_ips': 3}

        rule = {'id': 1, 'rule_type': 'device_velocity'}
        session = {'user_id': 123}
        params = {'max_unique_ips': 5, 'time_window_hours': 24}

        result = detector._check_device_velocity(rule, session, params)

        assert result is None

    def test_returns_violation_when_over_threshold(self, detector, mock_db):
        """Should return violation when unique IPs exceeds threshold."""
        mock_db.select_single.return_value = {'unique_ips': 7}

        rule = {'id': 1, 'name': 'Velocity', 'rule_type': 'device_velocity'}
        session = {'user_id': 123, 'session_key': 'abc'}
        params = {'max_unique_ips': 5, 'time_window_hours': 24}

        result = detector._check_device_velocity(rule, session, params)

        assert result is not None
        assert result['data']['unique_ips'] == 7


class TestAddRule:
    """Test the add_rule method."""

    def test_rejects_invalid_rule_type(self, detector, mock_db):
        """Should return None for invalid rule types."""
        result = detector.add_rule(
            name='Test',
            rule_type='invalid_type',
            params={}
        )

        assert result is None

    def test_accepts_valid_rule_type(self, detector, mock_db):
        """Should add rule and return ID for valid rule types."""
        result = detector.add_rule(
            name='Test Rule',
            rule_type='simultaneous_locations',
            params={'min_distance_km': 100}
        )

        assert result == 1  # mock returns 1 for last_insert_id
        mock_db.action.assert_called_once()


class TestDeleteRule:
    """Test the delete_rule method."""

    def test_deletes_rule_successfully(self, detector, mock_db):
        """Should return True when rule is deleted."""
        result = detector.delete_rule(rule_id=1)

        assert result is True
        mock_db.action.assert_called()


class TestGetViolations:
    """Test the get_violations method."""

    def test_returns_violations_with_filters(self, detector, mock_db):
        """Should query database with provided filters."""
        mock_db.select.return_value = [
            {'id': 1, 'rule_type': 'geo_restriction'}
        ]

        result = detector.get_violations(
            user_id=123,
            rule_type='geo_restriction',
            severity='high',
            limit=50
        )

        assert len(result) == 1
        mock_db.select.assert_called()


class TestCreateViolation:
    """Test the _create_violation method."""

    def test_creates_violation_dict(self, detector, mock_db):
        """Should create properly structured violation dict."""
        rule = {'id': 1, 'rule_type': 'test', 'name': 'Test Rule'}
        session = {'user_id': 123, 'session_key': 'abc'}
        data = {'test_key': 'test_value'}

        result = detector._create_violation(
            rule=rule,
            session=session,
            severity='warning',
            data=data
        )

        assert result['rule_id'] == 1
        assert result['rule_type'] == 'test'
        assert result['rule_name'] == 'Test Rule'
        assert result['user_id'] == 123
        assert result['session_key'] == 'abc'
        assert result['severity'] == 'warning'
        assert result['data'] == data


class TestRunScheduledScan:
    """Test the run_scheduled_scan function."""

    def test_exits_early_when_security_disabled(self, mock_db):
        """Should return early if security features are disabled."""
        mock_plexpy.CONFIG.SECURITY_ENABLED = False

        run_scheduled_scan()

        # Should exit early without calling database

    def test_exits_early_when_detection_disabled(self, mock_db):
        """Should return early if sharing detection is disabled."""
        mock_plexpy.CONFIG.SECURITY_SHARING_DETECTION = False

        run_scheduled_scan()

        # Should exit early without processing

    def test_processes_active_sessions(self, mock_db):
        """Should check rules for each active session."""
        # Return sessions from database
        mock_db.select.return_value = [
            {'user_id': 1, 'session_key': 'a', 'state': 'playing'},
            {'user_id': 2, 'session_key': 'b', 'state': 'playing'}
        ]

        run_scheduled_scan()

        # Should query for active sessions
        mock_db.select.assert_called()
