"""
Unit tests for Telemetry base structures.

Common telemetry data structures.
"""

import pytest
import time
from refactor_project.models.telemetry import TelemetryData, RemoteIdData


class TestTelemetryData:
    """Test base TelemetryData class."""

    def test_telemetry_creation(self):
        """Test creating TelemetryData."""
        telem = TelemetryData(
            source_id="TEST-001",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        assert telem.source_id == "TEST-001"
        assert telem.mac == "AA:BB:CC:DD:EE:FF"
        assert telem.rssi == -65

    def test_telemetry_with_frequency(self):
        """Test TelemetryData with frequency."""
        telem = TelemetryData(
            source_id="TEST-002",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70,
            freq=2437.0
        )

        assert telem.freq == 2437.0

    def test_telemetry_timestamp(self):
        """Test timestamp is set on creation."""
        before = time.time()
        telem = TelemetryData(
            source_id="TEST-003",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-60
        )
        after = time.time()

        assert before <= telem.timestamp <= after

    def test_telemetry_default_frequency(self):
        """Test default frequency is None."""
        telem = TelemetryData(
            source_id="TEST-004",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        assert telem.freq is None


class TestRemoteIdData:
    """Test RemoteIdData structure."""

    def test_remote_id_basic(self):
        """Test basic RemoteIdData."""
        rid = RemoteIdData(
            ua_id="DRONE-123",
            ua_type=2,
            lat=42.3601,
            lon=-71.0589,
            alt=150.0,
            speed=12.5
        )

        assert rid.ua_id == "DRONE-123"
        assert rid.ua_type == 2
        assert rid.lat == 42.3601
        assert rid.lon == -71.0589
        assert rid.alt == 150.0
        assert rid.speed == 12.5

    def test_remote_id_with_operator(self):
        """Test RemoteIdData with operator info."""
        rid = RemoteIdData(
            ua_id="DRONE-456",
            ua_type=2,
            lat=42.3601,
            lon=-71.0589,
            alt=150.0,
            speed=12.5,
            operator_id="OP-789",
            operator_lat=42.3600,
            operator_lon=-71.0590
        )

        assert rid.operator_id == "OP-789"
        assert rid.operator_lat == 42.3600
        assert rid.operator_lon == -71.0590

    def test_remote_id_with_home(self):
        """Test RemoteIdData with home location."""
        rid = RemoteIdData(
            ua_id="DRONE-789",
            ua_type=4,
            lat=42.3601,
            lon=-71.0589,
            alt=150.0,
            speed=12.5,
            home_lat=42.3599,
            home_lon=-71.0591
        )

        assert rid.home_lat == 42.3599
        assert rid.home_lon == -71.0591

    def test_remote_id_defaults(self):
        """Test default values."""
        rid = RemoteIdData(
            ua_id="DRONE-000",
            ua_type=2,
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            speed=10.0
        )

        assert rid.vspeed == 0.0
        assert rid.height == 0.0
        assert rid.direction is None
        assert rid.operator_id == ""
        assert rid.operator_lat == 0.0
        assert rid.operator_lon == 0.0
        assert rid.home_lat == 0.0
        assert rid.home_lon == 0.0

    def test_remote_id_full_data(self):
        """Test RemoteIdData with all fields."""
        rid = RemoteIdData(
            ua_id="DRONE-FULL",
            ua_type=2,
            lat=42.3601,
            lon=-71.0589,
            alt=150.0,
            speed=12.5,
            vspeed=2.0,
            height=100.0,
            direction=180.0,
            operator_id="OP-FULL",
            operator_lat=42.3600,
            operator_lon=-71.0590,
            home_lat=42.3599,
            home_lon=-71.0591,
            description="Full Test Drone"
        )

        assert rid.vspeed == 2.0
        assert rid.height == 100.0
        assert rid.direction == 180.0
        assert rid.description == "Full Test Drone"


class TestTelemetryEdgeCases:
    """Test edge cases for telemetry types."""

    def test_weak_rssi(self):
        """Test with very weak RSSI."""
        telem = TelemetryData(
            source_id="WEAK",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-120
        )

        assert telem.rssi == -120

    def test_strong_rssi(self):
        """Test with very strong RSSI."""
        telem = TelemetryData(
            source_id="STRONG",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-20
        )

        assert telem.rssi == -20

    def test_high_frequency(self):
        """Test with high frequency (5GHz)."""
        telem = TelemetryData(
            source_id="5GHZ",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            freq=5800.0
        )

        assert telem.freq == 5800.0

    def test_remote_id_zero_speed(self):
        """Test RemoteIdData with zero speed (hovering)."""
        rid = RemoteIdData(
            ua_id="HOVER",
            ua_type=2,
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            speed=0.0,
            vspeed=0.0
        )

        assert rid.speed == 0.0
        assert rid.vspeed == 0.0

    def test_remote_id_negative_vspeed(self):
        """Test RemoteIdData descending (negative vspeed)."""
        rid = RemoteIdData(
            ua_id="DESCEND",
            ua_type=2,
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            speed=10.0,
            vspeed=-3.0
        )

        assert rid.vspeed == -3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
