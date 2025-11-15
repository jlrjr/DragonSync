"""
Unit tests for the Drone model.

Following TDD approach - these tests define the expected behavior.
"""

import pytest
import time
from refactor_project.models.drone import Drone


class TestDroneInitialization:
    """Test Drone model initialization."""

    def test_drone_minimal_initialization(self):
        """Test Drone can be created with minimal required fields."""
        drone = Drone(
            id="TEST-DRONE-123",
            lat=42.3601,
            lon=-71.0589,
            speed=12.5,
            vspeed=2.0,
            alt=150.0,
            height=100.0,
            pilot_lat=42.3600,
            pilot_lon=-71.0590,
            description="Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        assert drone.id == "TEST-DRONE-123"
        assert drone.lat == 42.3601
        assert drone.lon == -71.0589
        assert drone.speed == 12.5
        assert drone.vspeed == 2.0
        assert drone.alt == 150.0
        assert drone.height == 100.0
        assert drone.pilot_lat == 42.3600
        assert drone.pilot_lon == -71.0590
        assert drone.description == "Test Drone"
        assert drone.mac == "AA:BB:CC:DD:EE:FF"
        assert drone.rssi == -65

    def test_drone_full_initialization(self):
        """Test Drone with all optional fields."""
        drone = Drone(
            id="TEST-DRONE-456",
            lat=42.3601,
            lon=-71.0589,
            speed=12.5,
            vspeed=2.0,
            alt=150.0,
            height=100.0,
            pilot_lat=42.3600,
            pilot_lon=-71.0590,
            description="Full Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            home_lat=42.3599,
            home_lon=-71.0591,
            id_type="SERIAL",
            ua_type=2,
            ua_type_name="Multirotor",
            operator_id_type="CAA",
            operator_id="OP-123",
            op_status="AIRBORNE",
            direction=180.0,
            freq=2437.0,
            caa_id="CAA-456"
        )

        assert drone.home_lat == 42.3599
        assert drone.home_lon == -71.0591
        assert drone.id_type == "SERIAL"
        assert drone.ua_type == 2
        assert drone.ua_type_name == "Multirotor"
        assert drone.operator_id == "OP-123"
        assert drone.direction == 180.0
        assert drone.freq == 2437.0

    def test_drone_defaults(self):
        """Test default values are set correctly."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        # Check defaults
        assert drone.home_lat == 0.0
        assert drone.home_lon == 0.0
        assert drone.id_type == ""
        assert drone.ua_type is None
        assert drone.ua_type_name == ""
        assert drone.direction is None
        assert drone.freq is None

    def test_drone_timestamp_on_creation(self):
        """Test that timestamps are set on creation."""
        before = time.time()
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )
        after = time.time()

        assert before <= drone.last_update_time <= after
        assert drone.last_sent_time == 0.0
        assert drone.last_sent_lat == 42.0
        assert drone.last_sent_lon == -71.0


class TestDroneUpdate:
    """Test Drone update method."""

    def test_update_basic_fields(self):
        """Test updating basic telemetry fields."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        # Store previous position
        prev_lat = drone.lat
        prev_lon = drone.lon

        # Update position
        drone.update(
            lat=43.0,
            lon=-72.0,
            speed=15.0,
            vspeed=2.5,
            alt=200.0,
            height=75.0,
            pilot_lat=43.0,
            pilot_lon=-72.0,
            description="Updated",
            mac="BB:BB:CC:DD:EE:FF",
            rssi=-65
        )

        # Check updated values
        assert drone.lat == 43.0
        assert drone.lon == -72.0
        assert drone.speed == 15.0
        assert drone.vspeed == 2.5
        assert drone.alt == 200.0
        assert drone.height == 75.0
        assert drone.rssi == -65

        # Check previous position stored
        assert drone.prev_lat == prev_lat
        assert drone.prev_lon == prev_lon

    def test_update_optional_fields(self):
        """Test updating optional fields."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        drone.update(
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70,
            ua_type=2,
            ua_type_name="Multirotor",
            operator_id="OP-789",
            direction=270.0,
            freq=5800.0
        )

        assert drone.ua_type == 2
        assert drone.ua_type_name == "Multirotor"
        assert drone.operator_id == "OP-789"
        assert drone.direction == 270.0
        assert drone.freq == 5800.0

    def test_update_timestamp(self):
        """Test that last_update_time is updated."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        initial_time = drone.last_update_time
        time.sleep(0.01)  # Small delay

        drone.update(
            lat=43.0,
            lon=-72.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=43.0,
            pilot_lon=-72.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        assert drone.last_update_time > initial_time


class TestDroneFields:
    """Test specific drone field behaviors."""

    def test_frequency_storage(self):
        """Test frequency field storage."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70,
            freq=2437.0
        )

        assert drone.freq == 2437.0

    def test_position_tracking(self):
        """Test that previous position is tracked."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        # Initially no previous position
        assert drone.prev_lat is None
        assert drone.prev_lon is None

        # After update, previous position stored
        drone.update(
            lat=43.0,
            lon=-72.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=43.0,
            pilot_lon=-72.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        assert drone.prev_lat == 42.0
        assert drone.prev_lon == -71.0

    def test_all_remote_id_fields(self):
        """Test all Remote ID specific fields."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70,
            height_type="AGL",
            ew_dir="WEST",
            speed_multiplier=1.5,
            pressure_altitude=150.0,
            vertical_accuracy="3m",
            horizontal_accuracy="10m",
            baro_accuracy="5m",
            speed_accuracy="1m/s",
            timestamp="2023-01-01T12:00:00Z",
            timestamp_accuracy="0.1s",
            index=5,
            runtime=120
        )

        assert drone.height_type == "AGL"
        assert drone.ew_dir == "WEST"
        assert drone.speed_multiplier == 1.5
        assert drone.pressure_altitude == 150.0
        assert drone.vertical_accuracy == "3m"
        assert drone.horizontal_accuracy == "10m"
        assert drone.index == 5
        assert drone.runtime == 120


class TestDroneEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_coordinates(self):
        """Test drone at zero coordinates (valid but unusual)."""
        drone = Drone(
            id="TEST",
            lat=0.0,
            lon=0.0,
            speed=0.0,
            vspeed=0.0,
            alt=0.0,
            height=0.0,
            pilot_lat=0.0,
            pilot_lon=0.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        assert drone.lat == 0.0
        assert drone.lon == 0.0

    def test_negative_altitude(self):
        """Test drone with negative altitude (below sea level)."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=-50.0,
            height=10.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-70
        )

        assert drone.alt == -50.0

    def test_extreme_rssi_values(self):
        """Test with extreme RSSI values."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-120  # Very weak signal
        )

        assert drone.rssi == -120

    def test_empty_strings(self):
        """Test with empty string fields."""
        drone = Drone(
            id="TEST",
            lat=42.0,
            lon=-71.0,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.0,
            pilot_lon=-71.0,
            description="",  # Empty description
            mac="",  # Empty MAC
            rssi=-70
        )

        assert drone.description == ""
        assert drone.mac == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
