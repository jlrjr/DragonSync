"""
Unit tests for Location types.

Simple geographic coordinate types and utilities.
"""

import pytest
from refactor_project.models.location import Location, GeoPoint, validate_latitude, validate_longitude


class TestLocation:
    """Test Location dataclass."""

    def test_location_creation(self):
        """Test creating a Location."""
        loc = Location(lat=42.3601, lon=-71.0589, alt=100.0)

        assert loc.lat == 42.3601
        assert loc.lon == -71.0589
        assert loc.alt == 100.0

    def test_location_optional_altitude(self):
        """Test Location with optional altitude."""
        loc = Location(lat=42.3601, lon=-71.0589)

        assert loc.lat == 42.3601
        assert loc.lon == -71.0589
        assert loc.alt == 0.0  # Default

    def test_location_equality(self):
        """Test Location equality."""
        loc1 = Location(lat=42.0, lon=-71.0, alt=100.0)
        loc2 = Location(lat=42.0, lon=-71.0, alt=100.0)
        loc3 = Location(lat=43.0, lon=-71.0, alt=100.0)

        assert loc1 == loc2
        assert loc1 != loc3

    def test_location_to_tuple(self):
        """Test converting Location to tuple."""
        loc = Location(lat=42.3601, lon=-71.0589, alt=100.0)

        assert loc.to_tuple() == (42.3601, -71.0589, 100.0)

    def test_location_from_dict(self):
        """Test creating Location from dictionary."""
        data = {"lat": 42.3601, "lon": -71.0589, "alt": 150.0}
        loc = Location.from_dict(data)

        assert loc.lat == 42.3601
        assert loc.lon == -71.0589
        assert loc.alt == 150.0

    def test_location_from_dict_no_alt(self):
        """Test creating Location from dict without altitude."""
        data = {"lat": 42.3601, "lon": -71.0589}
        loc = Location.from_dict(data)

        assert loc.lat == 42.3601
        assert loc.lon == -71.0589
        assert loc.alt == 0.0


class TestGeoPoint:
    """Test GeoPoint (lat/lon only)."""

    def test_geopoint_creation(self):
        """Test creating a GeoPoint."""
        point = GeoPoint(lat=42.3601, lon=-71.0589)

        assert point.lat == 42.3601
        assert point.lon == -71.0589

    def test_geopoint_equality(self):
        """Test GeoPoint equality."""
        p1 = GeoPoint(lat=42.0, lon=-71.0)
        p2 = GeoPoint(lat=42.0, lon=-71.0)
        p3 = GeoPoint(lat=42.0, lon=-72.0)

        assert p1 == p2
        assert p1 != p3

    def test_geopoint_to_tuple(self):
        """Test converting GeoPoint to tuple."""
        point = GeoPoint(lat=42.3601, lon=-71.0589)

        assert point.to_tuple() == (42.3601, -71.0589)


class TestValidation:
    """Test coordinate validation functions."""

    def test_validate_latitude_valid(self):
        """Test validating valid latitudes."""
        assert validate_latitude(0.0) == True
        assert validate_latitude(42.3601) == True
        assert validate_latitude(-42.3601) == True
        assert validate_latitude(90.0) == True
        assert validate_latitude(-90.0) == True

    def test_validate_latitude_invalid(self):
        """Test validating invalid latitudes."""
        assert validate_latitude(91.0) == False
        assert validate_latitude(-91.0) == False
        assert validate_latitude(180.0) == False
        assert validate_latitude(-180.0) == False

    def test_validate_longitude_valid(self):
        """Test validating valid longitudes."""
        assert validate_longitude(0.0) == True
        assert validate_longitude(-71.0589) == True
        assert validate_longitude(71.0589) == True
        assert validate_longitude(180.0) == True
        assert validate_longitude(-180.0) == True

    def test_validate_longitude_invalid(self):
        """Test validating invalid longitudes."""
        assert validate_longitude(181.0) == False
        assert validate_longitude(-181.0) == False
        assert validate_longitude(360.0) == False
        assert validate_longitude(-360.0) == False


class TestLocationEdgeCases:
    """Test edge cases for Location types."""

    def test_location_at_equator_prime_meridian(self):
        """Test location at (0, 0)."""
        loc = Location(lat=0.0, lon=0.0, alt=0.0)

        assert loc.lat == 0.0
        assert loc.lon == 0.0
        assert loc.alt == 0.0

    def test_location_at_poles(self):
        """Test locations at poles."""
        north_pole = Location(lat=90.0, lon=0.0)
        south_pole = Location(lat=-90.0, lon=0.0)

        assert north_pole.lat == 90.0
        assert south_pole.lat == -90.0

    def test_location_at_date_line(self):
        """Test locations at international date line."""
        east = Location(lat=0.0, lon=180.0)
        west = Location(lat=0.0, lon=-180.0)

        assert east.lon == 180.0
        assert west.lon == -180.0

    def test_location_negative_altitude(self):
        """Test location below sea level."""
        loc = Location(lat=31.5, lon=35.5, alt=-430.0)  # Dead Sea

        assert loc.alt == -430.0

    def test_location_high_altitude(self):
        """Test high altitude location."""
        loc = Location(lat=27.9881, lon=86.9250, alt=8848.0)  # Mt Everest

        assert loc.alt == 8848.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
