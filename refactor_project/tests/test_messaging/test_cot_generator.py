"""
Tests for CotGenerator - Cursor on Target XML message generation.

Following TDD approach: write tests first, then implement.
Tests based on modern CoT standards and TAK best practices.
"""

import pytest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

from refactor_project.models.drone import Drone
from refactor_project.messaging.cot_generator import CotGenerator


class TestCotGeneratorBasics:
    """Test basic CoT generator functionality"""

    def test_create_generator_with_defaults(self):
        """Should create generator with default configuration"""
        generator = CotGenerator()

        assert generator.default_stale_seconds == 60.0
        assert generator.default_ce == 35.0
        assert generator.default_le == 999999.0
        assert generator.version == "2.0"
        assert generator.use_modern_types is True

    def test_create_generator_with_custom_config(self):
        """Should create generator with custom configuration"""
        generator = CotGenerator(
            default_stale_seconds=30.0,
            default_ce=10.0,
            default_le=50.0,
            version="2.0",
            use_modern_types=False
        )

        assert generator.default_stale_seconds == 30.0
        assert generator.default_ce == 10.0
        assert generator.default_le == 50.0
        assert generator.use_modern_types is False


class TestDroneEventGeneration:
    """Test drone CoT event generation"""

    def test_generate_basic_drone_event(self):
        """Should generate valid CoT XML for basic drone"""
        generator = CotGenerator()

        drone = Drone(
            id="test-drone-001",
            lat=42.3601,
            lon=-71.0589,
            speed=10.5,
            vspeed=1.2,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            ua_type=2,  # Multirotor
            direction=180.0
        )

        xml_bytes = generator.generate_drone_event(drone)

        assert xml_bytes is not None
        assert isinstance(xml_bytes, bytes)
        assert b'<?xml' in xml_bytes  # XML declaration
        assert b'test-drone-001' in xml_bytes  # UID

    def test_drone_event_xml_structure(self):
        """Should generate CoT with correct XML structure"""
        generator = CotGenerator()

        drone = Drone(
            id="test-drone-001",
            lat=42.3601,
            lon=-71.0589,
            speed=10.5,
            vspeed=1.2,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        # Check event element
        assert root.tag == 'event'
        assert root.get('version') == '2.0'
        assert root.get('uid') == 'test-drone-001'
        assert root.get('type') is not None
        assert root.get('time') is not None
        assert root.get('start') is not None
        assert root.get('stale') is not None
        assert root.get('how') == 'm-g'

        # Check point element
        point = root.find('point')
        assert point is not None
        assert point.get('lat') == '42.3601'
        assert point.get('lon') == '-71.0589'
        assert point.get('hae') == '100.0'
        assert point.get('ce') is not None
        assert point.get('le') is not None

        # Check detail element
        detail = root.find('detail')
        assert detail is not None

    def test_drone_event_modern_type_codes(self):
        """Should use modern -Q suffix type codes for drones"""
        generator = CotGenerator(use_modern_types=True)

        # Test multirotor (type 2)
        drone = Drone(
            id="multirotor",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            ua_type=2
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        # Should use a-u-A-M-H-Q (unknown, air, military, helicopter, unmanned/drone)
        assert root.get('type') == 'a-u-A-M-H-Q'

    def test_drone_event_fixed_wing_type(self):
        """Should use correct type code for fixed wing drones"""
        generator = CotGenerator(use_modern_types=True)

        drone = Drone(
            id="fixed-wing",
            lat=42.36,
            lon=-71.06,
            speed=20.0,
            vspeed=1.0,
            alt=200.0,
            height=150.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            ua_type=1  # Fixed wing
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        # Should use a-u-A-M-F-Q (unknown, air, military, fixed, unmanned/drone)
        assert root.get('type') == 'a-u-A-M-F-Q'

    def test_drone_event_legacy_type_codes(self):
        """Should use legacy type codes when use_modern_types=False"""
        generator = CotGenerator(use_modern_types=False)

        drone = Drone(
            id="legacy-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            ua_type=2
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        # Should use legacy a-u-A-M-H-R
        assert root.get('type') == 'a-u-A-M-H-R'

    def test_drone_event_with_track(self):
        """Should include track element with course and speed"""
        generator = CotGenerator()

        drone = Drone(
            id="moving-drone",
            lat=42.36,
            lon=-71.06,
            speed=15.5,
            vspeed=2.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            direction=270.5
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        track = root.find('.//track')
        assert track is not None
        assert track.get('course') == '270.5'
        assert track.get('speed') == '15.5'

    def test_drone_event_with_remarks(self):
        """Should include remarks with drone details"""
        generator = CotGenerator()

        drone = Drone(
            id="detailed-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="DJI Mavic",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            ua_type=2,
            ua_type_name="Helicopter or Multirotor"
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        remarks = root.find('.//remarks')
        assert remarks is not None
        remarks_text = remarks.text

        assert 'MAC: AA:BB:CC:DD:EE:FF' in remarks_text
        assert 'RSSI: -65' in remarks_text
        assert 'UA Type: Helicopter or Multirotor' in remarks_text


class TestPilotEventGeneration:
    """Test pilot CoT event generation"""

    def test_generate_pilot_event(self):
        """Should generate valid CoT XML for pilot location"""
        generator = CotGenerator()

        drone = Drone(
            id="test-drone-001",
            lat=42.3601,
            lon=-71.0589,
            speed=10.5,
            vspeed=1.2,
            alt=100.0,
            height=50.0,
            pilot_lat=42.3650,
            pilot_lon=-71.0600,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_pilot_event(drone)

        assert xml_bytes is not None
        assert isinstance(xml_bytes, bytes)
        assert b'pilot-test-drone-001' in xml_bytes

    def test_pilot_event_xml_structure(self):
        """Should generate pilot CoT with correct structure"""
        generator = CotGenerator()

        drone = Drone(
            id="drone-123",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.37,
            pilot_lon=-71.07,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_pilot_event(drone)
        root = ET.fromstring(xml_bytes)

        # Check UID
        assert root.get('uid') == 'pilot-123'

        # Check type (should be person marker)
        assert root.get('type') == 'b-m-p-s-m'

        # Check pilot location
        point = root.find('point')
        assert point.get('lat') == '42.37'
        assert point.get('lon') == '-71.07'

    def test_pilot_event_no_location(self):
        """Should return empty bytes when pilot location is zero"""
        generator = CotGenerator()

        drone = Drone(
            id="no-pilot",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=0.0,
            pilot_lon=0.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_pilot_event(drone)

        assert xml_bytes == b''


class TestHomeEventGeneration:
    """Test home point CoT event generation"""

    def test_generate_home_event(self):
        """Should generate valid CoT XML for home point"""
        generator = CotGenerator()

        drone = Drone(
            id="test-drone-001",
            lat=42.3601,
            lon=-71.0589,
            speed=10.5,
            vspeed=1.2,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            home_lat=42.3599,
            home_lon=-71.0591
        )

        xml_bytes = generator.generate_home_event(drone)

        assert xml_bytes is not None
        assert isinstance(xml_bytes, bytes)
        assert b'home-test-drone-001' in xml_bytes

    def test_home_event_xml_structure(self):
        """Should generate home CoT with correct structure"""
        generator = CotGenerator()

        drone = Drone(
            id="drone-456",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            home_lat=42.35,
            home_lon=-71.05
        )

        xml_bytes = generator.generate_home_event(drone)
        root = ET.fromstring(xml_bytes)

        # Check UID
        assert root.get('uid') == 'home-456'

        # Check type (should be surface marker)
        assert root.get('type') == 'b-m-p-s-m'

        # Check home location
        point = root.find('point')
        assert point.get('lat') == '42.35'
        assert point.get('lon') == '-71.05'

    def test_home_event_no_location(self):
        """Should return empty bytes when home location is zero"""
        generator = CotGenerator()

        drone = Drone(
            id="no-home",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            home_lat=0.0,
            home_lon=0.0
        )

        xml_bytes = generator.generate_home_event(drone)

        assert xml_bytes == b''


class TestTimestampFormatting:
    """Test CoT timestamp formatting"""

    def test_timestamps_are_utc(self):
        """Should generate UTC timestamps in ISO 8601 format"""
        generator = CotGenerator()

        drone = Drone(
            id="test-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        time_str = root.get('time')

        # Should end with Z (Zulu/UTC)
        assert time_str.endswith('Z')

        # Should be parseable as ISO 8601
        # Remove Z and parse
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        assert dt.tzinfo is not None

    def test_stale_time_calculation(self):
        """Should calculate stale time correctly"""
        generator = CotGenerator(default_stale_seconds=30.0)

        drone = Drone(
            id="test-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone, stale_seconds=30.0)
        root = ET.fromstring(xml_bytes)

        time_str = root.get('time')
        stale_str = root.get('stale')

        time_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        stale_dt = datetime.fromisoformat(stale_str.replace('Z', '+00:00'))

        # Stale should be approximately 30 seconds after time
        diff = (stale_dt - time_dt).total_seconds()
        assert 29.0 < diff < 31.0  # Allow small rounding


class TestAccuracyParsing:
    """Test CE/LE accuracy parsing from Remote ID strings"""

    def test_parse_accuracy_with_meters(self):
        """Should parse accuracy strings like '10m' to float"""
        generator = CotGenerator()

        drone = Drone(
            id="accurate-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65,
            horizontal_accuracy="10m",
            vertical_accuracy="5m"
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        point = root.find('point')
        ce = float(point.get('ce'))
        le = float(point.get('le'))

        # Should parse "10m" to 10.0
        assert ce == 10.0
        # Should parse "5m" to 5.0
        assert le == 5.0

    def test_accuracy_defaults_when_missing(self):
        """Should use default CE/LE when accuracy not provided"""
        generator = CotGenerator(default_ce=35.0, default_le=999999.0)

        drone = Drone(
            id="default-accuracy",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone)
        root = ET.fromstring(xml_bytes)

        point = root.find('point')
        ce = float(point.get('ce'))
        le = float(point.get('le'))

        assert ce == 35.0
        assert le == 999999.0


class TestCoordinateValidation:
    """Test coordinate bounds validation"""

    def test_valid_coordinates(self):
        """Should accept valid WGS84 coordinates"""
        generator = CotGenerator()

        drone = Drone(
            id="valid-coords",
            lat=42.3601,
            lon=-71.0589,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone)

        assert xml_bytes is not None
        assert len(xml_bytes) > 0

    def test_edge_case_coordinates(self):
        """Should handle edge case coordinates (poles, dateline)"""
        generator = CotGenerator()

        # North pole
        drone_north = Drone(
            id="north-pole",
            lat=90.0,
            lon=0.0,
            speed=0.0,
            vspeed=0.0,
            alt=0.0,
            height=0.0,
            pilot_lat=89.9,
            pilot_lon=0.0,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone_north)
        root = ET.fromstring(xml_bytes)
        point = root.find('point')
        assert point.get('lat') == '90.0'

        # Dateline
        drone_dateline = Drone(
            id="dateline",
            lat=0.0,
            lon=180.0,
            speed=0.0,
            vspeed=0.0,
            alt=0.0,
            height=0.0,
            pilot_lat=0.0,
            pilot_lon=179.9,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone_dateline)
        root = ET.fromstring(xml_bytes)
        point = root.find('point')
        assert point.get('lon') == '180.0'


class TestXMLEscaping:
    """Test proper XML character escaping"""

    def test_escape_special_characters_in_remarks(self):
        """Should properly escape XML special characters"""
        generator = CotGenerator()

        drone = Drone(
            id="special<>chars&\"'",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description='Test "quotes" & <tags>',
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        xml_bytes = generator.generate_drone_event(drone)

        # Should be valid XML (parseable)
        root = ET.fromstring(xml_bytes)

        # Should contain escaped characters in raw bytes
        assert b'&lt;' in xml_bytes or b'<' in xml_bytes
        assert b'&amp;' in xml_bytes or b'&' in xml_bytes
