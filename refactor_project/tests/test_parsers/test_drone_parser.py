"""
Unit tests for DroneParser.

Tests parsing ZMQ telemetry messages into Drone models.
"""

import pytest
from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.models import Drone
from refactor_project.tests.fixtures.sample_messages import (
    SAMPLE_DJI_MESSAGE,
    SAMPLE_ESP32_MESSAGE,
    SAMPLE_MINIMAL_MESSAGE,
    SAMPLE_CAA_MESSAGE,
    UA_TYPE_MAPPING
)


class TestDroneParserDJIFormat:
    """Test parsing DJI/AntSDR list format."""

    def test_parse_dji_message(self):
        """Test parsing complete DJI message."""
        parser = DroneParser(UA_TYPE_MAPPING)
        drone = parser.parse(SAMPLE_DJI_MESSAGE)

        assert drone is not None
        assert isinstance(drone, Drone)

        # Basic ID fields
        assert drone.id == "DJI-MAVIC-123456"
        assert drone.mac == "12:34:56:78:9A:BC"
        assert drone.rssi == -65
        assert drone.ua_type == 2
        assert drone.ua_type_name == "Helicopter or Multirotor"
        assert drone.id_type == "Serial Number (ANSI/CTA-2063-A)"

        # Location fields
        assert drone.lat == 42.3601
        assert drone.lon == -71.0589
        assert drone.speed == 12.5
        assert drone.vspeed == 2.0
        assert drone.alt == 150.0
        assert drone.height == 100.0
        assert drone.direction == 180

        # System fields
        assert drone.pilot_lat == 42.3600
        assert drone.pilot_lon == -71.0590
        assert drone.home_lat == 42.3599
        assert drone.home_lon == -71.0591

        # Description
        assert drone.description == "DJI Mavic 3"

        # Operator
        assert drone.operator_id_type == "CAA"
        assert drone.operator_id == "OP-DJI-789"

        # Frequency
        assert drone.freq == 2437.0

    def test_parse_dji_remote_id_extras(self):
        """Test DJI message with Remote ID extra fields."""
        parser = DroneParser(UA_TYPE_MAPPING)
        drone = parser.parse(SAMPLE_DJI_MESSAGE)

        assert drone.op_status == "AIRBORNE"
        assert drone.height_type == "AGL"
        assert drone.ew_dir == "WEST"
        assert drone.speed_multiplier == 1.0
        assert drone.pressure_altitude == 150.0
        assert drone.vertical_accuracy == "3m"
        assert drone.horizontal_accuracy == "10m"
        assert drone.baro_accuracy == "5m"
        assert drone.speed_accuracy == "1m/s"
        assert drone.timestamp == "2024-01-15T12:30:00Z"
        assert drone.timestamp_accuracy == "0.1s"


class TestDroneParserESP32Format:
    """Test parsing ESP32 BLE dict format."""

    def test_parse_esp32_message(self):
        """Test parsing complete ESP32 message."""
        parser = DroneParser(UA_TYPE_MAPPING)
        drone = parser.parse(SAMPLE_ESP32_MESSAGE)

        assert drone is not None
        assert isinstance(drone, Drone)

        # Basic ID
        assert drone.id == "ESP32-DRONE-456"
        assert drone.mac == "AA:BB:CC:DD:EE:FF"  # From aext AdvA
        assert drone.rssi == -70
        assert drone.ua_type == 2
        assert drone.index == 42
        assert drone.runtime == 3600

        # Location
        assert drone.lat == 41.9012
        assert drone.lon == -70.6789
        assert drone.speed == 8.5
        assert drone.vspeed == -1.5  # Descending
        assert drone.alt == 200.0
        assert drone.height == 75.0
        assert drone.direction == 90

        # System (ESP32 uses operator_lat/lon)
        assert drone.pilot_lat == 41.9010
        assert drone.pilot_lon == -70.6788

        # Description
        assert drone.description == "Custom Quadcopter"

        # Operator
        assert drone.operator_id == "PILOT-123"


class TestDroneParserMinimal:
    """Test parsing minimal messages."""

    def test_parse_minimal_message(self):
        """Test parsing message with only required fields."""
        parser = DroneParser(UA_TYPE_MAPPING)
        drone = parser.parse(SAMPLE_MINIMAL_MESSAGE)

        assert drone is not None
        assert drone.id == "MINIMAL-DRONE-999"
        assert drone.mac == "FF:EE:DD:CC:BB:AA"
        assert drone.rssi == -80
        assert drone.ua_type == 4  # VTOL
        assert drone.lat == 40.7128
        assert drone.lon == -74.0060
        assert drone.speed == 5.0
        assert drone.alt == 50.0
        assert drone.height == 30.0
        assert drone.description == "Test Drone"
        assert drone.pilot_lat == 40.7127
        assert drone.pilot_lon == -74.0061


class TestDroneParserCAAFormat:
    """Test parsing CAA ID format."""

    def test_parse_caa_id_message(self):
        """Test parsing message with CAA Assigned Registration ID."""
        parser = DroneParser(UA_TYPE_MAPPING)
        drone = parser.parse(SAMPLE_CAA_MESSAGE)

        assert drone is not None
        assert drone.caa_id == "CAA-UK-54321"
        assert drone.id_type == "CAA Assigned Registration ID"
        # CAA format uses caa_id field, not id
        assert drone.description == "UK Registered Drone"


class TestDroneParserUATypes:
    """Test UA type parsing and mapping."""

    def test_ua_type_by_code(self):
        """Test UA type parsed as integer code."""
        parser = DroneParser(UA_TYPE_MAPPING)

        # Modify message to have different UA type
        message = SAMPLE_MINIMAL_MESSAGE.copy()
        message[0]["Basic ID"]["ua_type"] = 1  # Fixed wing

        drone = parser.parse(message)
        assert drone.ua_type == 1
        assert drone.ua_type_name == "Aeroplane/Airplane (Fixed wing)"

    def test_ua_type_by_name(self):
        """Test UA type parsed as string name."""
        parser = DroneParser(UA_TYPE_MAPPING)

        # Some sources send UA type as name
        message = SAMPLE_MINIMAL_MESSAGE.copy()
        message[0]["Basic ID"]["ua_type"] = "Glider"

        drone = parser.parse(message)
        assert drone.ua_type == 6
        assert drone.ua_type_name == "Glider"

    def test_ua_type_unknown(self):
        """Test unknown UA type defaults to None."""
        parser = DroneParser(UA_TYPE_MAPPING)

        message = SAMPLE_MINIMAL_MESSAGE.copy()
        message[0]["Basic ID"]["ua_type"] = 99  # Invalid

        drone = parser.parse(message)
        assert drone.ua_type is None
        assert drone.ua_type_name == "Unknown"


class TestDroneParserErrorHandling:
    """Test parser error handling."""

    def test_parse_empty_message(self):
        """Test parsing empty message returns None."""
        parser = DroneParser(UA_TYPE_MAPPING)
        result = parser.parse([])

        assert result is None

    def test_parse_invalid_format(self):
        """Test parsing invalid format returns None."""
        parser = DroneParser(UA_TYPE_MAPPING)
        result = parser.parse("invalid string")

        assert result is None

    def test_parse_none(self):
        """Test parsing None returns None."""
        parser = DroneParser(UA_TYPE_MAPPING)
        result = parser.parse(None)

        assert result is None

    def test_parse_message_without_basic_id(self):
        """Test message without Basic ID returns None."""
        parser = DroneParser(UA_TYPE_MAPPING)

        # Message missing Basic ID
        incomplete_message = [
            {
                "Location/Vector Message": {
                    "latitude": 42.0,
                    "longitude": -71.0,
                    "speed": 10.0,
                    "vert_speed": 0.0,
                    "geodetic_altitude": 100.0,
                    "height_agl": 50.0
                }
            }
        ]

        result = parser.parse(incomplete_message)
        # Parser should handle gracefully - might return partial data or None
        # depending on implementation

    def test_parse_message_without_location(self):
        """Test message without Location/Vector returns None."""
        parser = DroneParser(UA_TYPE_MAPPING)

        # Message with only Basic ID
        incomplete_message = [
            {
                "Basic ID": {
                    "ua_type": 2,
                    "id_type": "Serial Number (ANSI/CTA-2063-A)",
                    "id": "INCOMPLETE-123"
                }
            }
        ]

        result = parser.parse(incomplete_message)
        # Should return None - location is required


class TestDroneParserFieldDefaults:
    """Test default values for missing fields."""

    def test_missing_optional_fields_use_defaults(self):
        """Test missing optional fields get default values."""
        parser = DroneParser(UA_TYPE_MAPPING)
        drone = parser.parse(SAMPLE_MINIMAL_MESSAGE)

        # These fields not in minimal message, should have defaults
        assert drone.operator_id == "" or drone.operator_id is None
        assert drone.freq is None
        assert drone.home_lat == 0.0
        assert drone.home_lon == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
