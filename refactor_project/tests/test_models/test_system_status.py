"""
Unit tests for the SystemStatus model.

Following TDD approach - these tests define the expected behavior.
"""

import pytest
import time
from refactor_project.models.system_status import SystemStatus


class TestSystemStatusInitialization:
    """Test SystemStatus model initialization."""

    def test_system_status_minimal_initialization(self):
        """Test SystemStatus with required fields only."""
        status = SystemStatus(
            serial_number="WD-12345",
            lat=42.3601,
            lon=-71.0589,
            alt=100.0
        )

        assert status.id == "wardragon-WD-12345"
        assert status.serial_number == "WD-12345"
        assert status.lat == 42.3601
        assert status.lon == -71.0589
        assert status.alt == 100.0

    def test_system_status_full_initialization(self):
        """Test SystemStatus with all fields."""
        status = SystemStatus(
            serial_number="WD-67890",
            lat=42.3601,
            lon=-71.0589,
            alt=100.0,
            cpu_usage=45.5,
            memory_total=8192.0,
            memory_available=4096.0,
            disk_total=256000.0,
            disk_used=128000.0,
            temperature=55.0,
            uptime=86400.0,
            pluto_temp="65.0",
            zynq_temp="70.0",
            speed=5.5,
            track=180.0
        )

        assert status.cpu_usage == 45.5
        assert status.memory_total == 8192.0
        assert status.memory_available == 4096.0
        assert status.disk_total == 256000.0
        assert status.disk_used == 128000.0
        assert status.temperature == 55.0
        assert status.uptime == 86400.0
        assert status.pluto_temp == "65.0"
        assert status.zynq_temp == "70.0"
        assert status.speed == 5.5
        assert status.track == 180.0

    def test_system_status_defaults(self):
        """Test default values are set correctly."""
        status = SystemStatus(
            serial_number="WD-00000",
            lat=0.0,
            lon=0.0,
            alt=0.0
        )

        # Check defaults
        assert status.cpu_usage == 0.0
        assert status.memory_total == 0.0
        assert status.memory_available == 0.0
        assert status.disk_total == 0.0
        assert status.disk_used == 0.0
        assert status.temperature == 0.0
        assert status.uptime == 0.0
        assert status.pluto_temp == "N/A"
        assert status.zynq_temp == "N/A"
        assert status.speed == 0.0
        assert status.track == 0.0

    def test_system_status_id_generation(self):
        """Test ID is generated from serial number."""
        status = SystemStatus(
            serial_number="TEST-123",
            lat=42.0,
            lon=-71.0,
            alt=100.0
        )

        assert status.id == "wardragon-TEST-123"

    def test_system_status_timestamp_on_creation(self):
        """Test that timestamp is set on creation."""
        before = time.time()
        status = SystemStatus(
            serial_number="WD-TS",
            lat=42.0,
            lon=-71.0,
            alt=100.0
        )
        after = time.time()

        assert before <= status.last_update_time <= after


class TestSystemStatusUpdate:
    """Test SystemStatus update method."""

    def test_update_location(self):
        """Test updating GPS location."""
        status = SystemStatus(
            serial_number="WD-UPDATE",
            lat=42.0,
            lon=-71.0,
            alt=100.0
        )

        status.update(
            lat=43.0,
            lon=-72.0,
            alt=150.0
        )

        assert status.lat == 43.0
        assert status.lon == -72.0
        assert status.alt == 150.0

    def test_update_hardware_metrics(self):
        """Test updating hardware metrics."""
        status = SystemStatus(
            serial_number="WD-HW",
            lat=42.0,
            lon=-71.0,
            alt=100.0
        )

        status.update(
            cpu_usage=75.0,
            memory_available=2048.0,
            disk_used=150000.0,
            temperature=60.0
        )

        assert status.cpu_usage == 75.0
        assert status.memory_available == 2048.0
        assert status.disk_used == 150000.0
        assert status.temperature == 60.0

    def test_update_gps_speed_track(self):
        """Test updating GPS speed and track."""
        status = SystemStatus(
            serial_number="WD-GPS",
            lat=42.0,
            lon=-71.0,
            alt=100.0
        )

        status.update(speed=10.5, track=270.0)

        assert status.speed == 10.5
        assert status.track == 270.0

    def test_update_timestamp(self):
        """Test that last_update_time is updated."""
        status = SystemStatus(
            serial_number="WD-TIME",
            lat=42.0,
            lon=-71.0,
            alt=100.0
        )

        initial_time = status.last_update_time
        time.sleep(0.01)  # Small delay

        status.update(lat=42.1)

        assert status.last_update_time > initial_time


class TestSystemStatusFields:
    """Test specific SystemStatus field behaviors."""

    def test_temperature_fields(self):
        """Test temperature field storage."""
        status = SystemStatus(
            serial_number="WD-TEMP",
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            temperature=55.0,
            pluto_temp="65.5",
            zynq_temp="70.2"
        )

        assert status.temperature == 55.0
        assert status.pluto_temp == "65.5"
        assert status.zynq_temp == "70.2"

    def test_memory_fields(self):
        """Test memory field storage."""
        status = SystemStatus(
            serial_number="WD-MEM",
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            memory_total=16384.0,
            memory_available=8192.0
        )

        assert status.memory_total == 16384.0
        assert status.memory_available == 8192.0

    def test_disk_fields(self):
        """Test disk field storage."""
        status = SystemStatus(
            serial_number="WD-DISK",
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            disk_total=512000.0,
            disk_used=256000.0
        )

        assert status.disk_total == 512000.0
        assert status.disk_used == 256000.0


class TestSystemStatusEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_values(self):
        """Test with all zero values."""
        status = SystemStatus(
            serial_number="WD-ZERO",
            lat=0.0,
            lon=0.0,
            alt=0.0,
            cpu_usage=0.0,
            temperature=0.0,
            speed=0.0,
            track=0.0
        )

        assert status.lat == 0.0
        assert status.cpu_usage == 0.0
        assert status.temperature == 0.0

    def test_negative_altitude(self):
        """Test with negative altitude (below sea level)."""
        status = SystemStatus(
            serial_number="WD-NEG",
            lat=42.0,
            lon=-71.0,
            alt=-50.0
        )

        assert status.alt == -50.0

    def test_high_cpu_usage(self):
        """Test with high CPU usage."""
        status = SystemStatus(
            serial_number="WD-CPU",
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            cpu_usage=99.9
        )

        assert status.cpu_usage == 99.9

    def test_large_uptime(self):
        """Test with large uptime value (30 days)."""
        uptime_30_days = 30 * 24 * 60 * 60  # 2,592,000 seconds
        status = SystemStatus(
            serial_number="WD-UPTIME",
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            uptime=uptime_30_days
        )

        assert status.uptime == uptime_30_days

    def test_na_temperature_strings(self):
        """Test N/A temperature strings."""
        status = SystemStatus(
            serial_number="WD-NA",
            lat=42.0,
            lon=-71.0,
            alt=100.0,
            pluto_temp="N/A",
            zynq_temp="N/A"
        )

        assert status.pluto_temp == "N/A"
        assert status.zynq_temp == "N/A"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
