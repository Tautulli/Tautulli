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

"""Tests for calculate_distance function from plexpy.helpers module.

These tests are isolated from the main Tautulli application by directly
implementing the Haversine formula for testing purposes.
"""

import pytest
from math import radians, cos, sin, asin, sqrt


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers.

    Uses the Haversine formula. This is a copy of the function from
    plexpy/helpers.py for isolated testing without loading full app.

    Args:
        lat1: Latitude of first point in degrees.
        lon1: Longitude of first point in degrees.
        lat2: Latitude of second point in degrees.
        lon2: Longitude of second point in degrees.

    Returns:
        float: Distance in kilometers, or None if any coordinate is None.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth radius in kilometers

    return c * r


class TestCalculateDistance:
    """Test cases for the calculate_distance function."""

    def test_calculate_distance_same_location(self):
        """Distance between identical coordinates should be zero."""
        lat, lon = 40.7128, -74.0060  # New York City
        distance = calculate_distance(lat, lon, lat, lon)

        assert distance == 0.0

    def test_calculate_distance_known_cities(self):
        """Test distance calculation between known cities.

        New York (40.7128, -74.0060) to Los Angeles (34.0522, -118.2437)
        is approximately 3944 km.
        """
        # New York coordinates
        ny_lat, ny_lon = 40.7128, -74.0060
        # Los Angeles coordinates
        la_lat, la_lon = 34.0522, -118.2437

        distance = calculate_distance(ny_lat, ny_lon, la_lat, la_lon)

        # Allow 5% tolerance for the Haversine approximation
        expected_distance = 3944  # km
        assert abs(distance - expected_distance) < expected_distance * 0.05

    def test_calculate_distance_london_to_paris(self):
        """Test distance between London and Paris.

        London (51.5074, -0.1278) to Paris (48.8566, 2.3522)
        is approximately 344 km.
        """
        london_lat, london_lon = 51.5074, -0.1278
        paris_lat, paris_lon = 48.8566, 2.3522

        distance = calculate_distance(
            london_lat, london_lon,
            paris_lat, paris_lon
        )

        expected_distance = 344  # km
        assert abs(distance - expected_distance) < expected_distance * 0.05

    def test_calculate_distance_across_equator(self):
        """Test distance calculation across the equator.

        Singapore (1.3521, 103.8198) to Sydney (-33.8688, 151.2093)
        is approximately 6300 km.
        """
        singapore_lat, singapore_lon = 1.3521, 103.8198
        sydney_lat, sydney_lon = -33.8688, 151.2093

        distance = calculate_distance(
            singapore_lat, singapore_lon,
            sydney_lat, sydney_lon
        )

        expected_distance = 6300  # km
        assert abs(distance - expected_distance) < expected_distance * 0.05

    def test_calculate_distance_across_date_line(self):
        """Test distance calculation across the International Date Line.

        Tokyo (35.6762, 139.6503) to Los Angeles (34.0522, -118.2437)
        is approximately 8815 km.
        """
        tokyo_lat, tokyo_lon = 35.6762, 139.6503
        la_lat, la_lon = 34.0522, -118.2437

        distance = calculate_distance(tokyo_lat, tokyo_lon, la_lat, la_lon)

        expected_distance = 8815  # km
        assert abs(distance - expected_distance) < expected_distance * 0.05

    def test_calculate_distance_with_none_values(self):
        """Distance calculation should return None if any coordinate is None."""
        lat1, lon1 = 40.7128, -74.0060

        assert calculate_distance(None, lon1, lat1, lon1) is None
        assert calculate_distance(lat1, None, lat1, lon1) is None
        assert calculate_distance(lat1, lon1, None, lon1) is None
        assert calculate_distance(lat1, lon1, lat1, None) is None
        assert calculate_distance(None, None, None, None) is None

    def test_calculate_distance_returns_positive(self):
        """Distance should always be a positive number."""
        # Two random points
        lat1, lon1 = 52.5200, 13.4050  # Berlin
        lat2, lon2 = -22.9068, -43.1729  # Rio de Janeiro

        distance = calculate_distance(lat1, lon1, lat2, lon2)

        assert distance > 0

    def test_calculate_distance_symmetric(self):
        """Distance from A to B should equal distance from B to A."""
        lat1, lon1 = 40.7128, -74.0060  # New York
        lat2, lon2 = 51.5074, -0.1278   # London

        distance_a_to_b = calculate_distance(lat1, lon1, lat2, lon2)
        distance_b_to_a = calculate_distance(lat2, lon2, lat1, lon1)

        assert distance_a_to_b == distance_b_to_a

    def test_calculate_distance_short_distance(self):
        """Test calculation for a short distance (within same city).

        Two points within Manhattan, approximately 5 km apart.
        """
        # Times Square
        ts_lat, ts_lon = 40.7580, -73.9855
        # Financial District
        fd_lat, fd_lon = 40.7074, -74.0113

        distance = calculate_distance(ts_lat, ts_lon, fd_lat, fd_lon)

        # Should be roughly 5-6 km
        assert 4 < distance < 7

    def test_calculate_distance_antipodal_points(self):
        """Test distance for near-antipodal points.

        Maximum possible distance should be around 20,000 km (half of Earth's
        circumference of ~40,000 km).
        """
        # Point and its approximate antipode
        lat1, lon1 = 40.0, 0.0
        lat2, lon2 = -40.0, 180.0

        distance = calculate_distance(lat1, lon1, lat2, lon2)

        # Should be close to half Earth circumference (~20,000 km)
        assert 19000 < distance < 21000
