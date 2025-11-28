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

"""Pytest fixtures for Tautulli tests.

This module provides common fixtures used across test modules.
Individual test modules may define their own mocks for module-level isolation.
"""

import pytest


@pytest.fixture
def sample_session():
    """Provide a sample session dict for testing.

    Returns:
        dict: A sample playback session with geolocation data.
    """
    return {
        'session_key': 'abc123',
        'user_id': 12345,
        'ip_address': '192.168.1.100',
        'geo_latitude': 40.7128,
        'geo_longitude': -74.0060,
        'geo_city': 'New York',
        'geo_region': 'NY',
        'geo_country': 'US',
        'state': 'playing'
    }


@pytest.fixture
def sample_rule():
    """Provide a sample sharing rule dict for testing.

    Returns:
        dict: A sample sharing detection rule.
    """
    return {
        'id': 1,
        'name': 'Test Rule',
        'rule_type': 'simultaneous_locations',
        'params': '{"min_distance_km": 100}',
        'user_id': None,
        'is_active': 1
    }


@pytest.fixture
def sample_violation():
    """Provide a sample violation dict for testing.

    Returns:
        dict: A sample sharing violation record.
    """
    return {
        'rule_id': 1,
        'rule_type': 'simultaneous_locations',
        'rule_name': 'Test Rule',
        'user_id': 12345,
        'session_key': 'abc123',
        'severity': 'warning',
        'data': {'distance_km': 500.0}
    }
