"""
Drone telemetry parser.

Parses ZMQ drone telemetry messages into Drone models.
Supports DJI/AntSDR and ESP32 BLE Remote ID formats.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

from typing import Any, Dict, Optional
import logging

from refactor_project.parsers.base_parser import BaseParser
from refactor_project.models import Drone

logger = logging.getLogger(__name__)


class DroneParser(BaseParser):
    """
    Parser for drone Remote ID telemetry.

    Supports two message formats:
    1. DJI/AntSDR: List of message dictionaries
    2. ESP32 BLE: Single dictionary

    Both formats contain Remote ID messages as specified in ASTM F3411.
    """

    def __init__(self, ua_type_mapping: Dict[int, str]):
        """
        Initialize DroneParser.

        Args:
            ua_type_mapping: Mapping of UA type codes (0-15) to human-readable names
        """
        self.ua_type_mapping = ua_type_mapping

    def parse(self, message: Any) -> Optional[Drone]:
        """
        Parse ZMQ drone telemetry message into Drone model.

        Args:
            message: Raw ZMQ message (list or dict)

        Returns:
            Drone model instance, or None if parsing fails
        """
        if not self.validate(message):
            return None

        try:
            # Extract fields from message
            drone_data = self._extract_fields(message)

            if not drone_data:
                logger.debug("No drone data extracted from message")
                return None

            # Validate required fields
            if not self._has_required_fields(drone_data):
                logger.debug("Missing required fields in message")
                return None

            # Create Drone model
            return self._create_drone(drone_data)

        except Exception as e:
            logger.error(f"Error parsing drone message: {e}", exc_info=True)
            return None

    def validate(self, message: Any) -> bool:
        """
        Validate message format.

        Args:
            message: Raw message

        Returns:
            True if message is valid format (list or dict)
        """
        return isinstance(message, (list, dict))

    def _extract_fields(self, message: Any) -> Dict[str, Any]:
        """
        Extract drone fields from message.

        Handles both DJI list format and ESP32 dict format.

        Args:
            message: Raw message (list or dict)

        Returns:
            Dictionary of extracted fields
        """
        drone_data: Dict[str, Any] = {}

        if isinstance(message, list):
            drone_data = self._parse_dji_format(message)
        elif isinstance(message, dict):
            drone_data = self._parse_esp32_format(message)

        return drone_data

    def _parse_dji_format(self, messages: list) -> Dict[str, Any]:
        """
        Parse DJI/AntSDR list of message dictionaries.

        Args:
            messages: List of message dicts

        Returns:
            Dictionary of extracted fields
        """
        data: Dict[str, Any] = {}

        for item in messages:
            if not isinstance(item, dict):
                logger.warning("Unexpected item type in message list")
                continue

            # Top-level fields
            if 'MAC' in item:
                data['mac'] = item['MAC']
            if 'RSSI' in item:
                data['rssi'] = item['RSSI']

            # Basic ID
            if 'Basic ID' in item:
                self._extract_basic_id(item['Basic ID'], data)

            # Location/Vector Message
            if 'Location/Vector Message' in item:
                self._extract_location(item['Location/Vector Message'], data)

            # Self-ID Message
            if 'Self-ID Message' in item:
                data['description'] = item['Self-ID Message'].get('text', "")

            # System Message
            if 'System Message' in item:
                self._extract_system(item['System Message'], data)

            # Operator ID Message
            if 'Operator ID Message' in item:
                op = item['Operator ID Message']
                data['operator_id_type'] = op.get('operator_id_type', "")
                data['operator_id'] = op.get('operator_id', "")

            # Frequency Message (DJI-specific)
            if 'Frequency Message' in item:
                freq_obj = item['Frequency Message']
                freq = freq_obj.get('frequency')
                data['freq'] = self._get_float(freq, None)

        return data

    def _parse_esp32_format(self, message: dict) -> Dict[str, Any]:
        """
        Parse ESP32 BLE dictionary format.

        Args:
            message: Message dictionary

        Returns:
            Dictionary of extracted fields
        """
        data: Dict[str, Any] = {}

        # ESP32-specific index/runtime
        data['index'] = message.get('index', 0)
        data['runtime'] = message.get('runtime', 0)

        # AUX_ADV_IND (BLE advertising)
        if "AUX_ADV_IND" in message:
            if "rssi" in message["AUX_ADV_IND"]:
                data['rssi'] = message["AUX_ADV_IND"]["rssi"]

        # Extract MAC from aext/AdvA
        if 'aext' in message and 'AdvA' in message['aext']:
            # Format: "AA:BB:CC:DD:EE:FF 00:11:22:33:44:55"
            adva = message['aext']['AdvA'].split()[0]
            data['mac'] = adva

        # Basic ID
        if 'Basic ID' in message:
            self._extract_basic_id(message['Basic ID'], data)

        # Location/Vector Message
        if 'Location/Vector Message' in message:
            self._extract_location(message['Location/Vector Message'], data)

        # Self-ID Message
        if 'Self-ID Message' in message:
            data['description'] = message['Self-ID Message'].get('text', "")

        # System Message (ESP32 uses operator_lat/lon)
        if 'System Message' in message:
            sysm = message['System Message']
            data['pilot_lat'] = self._get_float(sysm.get('operator_lat', 0.0))
            data['pilot_lon'] = self._get_float(sysm.get('operator_lon', 0.0))
            # ESP32 usually lacks home_lat/home_lon

        # Operator ID Message
        if 'Operator ID Message' in message:
            op = message['Operator ID Message']
            data['operator_id_type'] = op.get('operator_id_type', "")
            data['operator_id'] = op.get('operator_id', "")

        # Frequency Message
        if 'Frequency Message' in message:
            freq_obj = message['Frequency Message']
            freq = freq_obj.get('frequency')
            data['freq'] = self._get_float(freq, None)

        return data

    def _extract_basic_id(self, basic: dict, data: dict) -> None:
        """Extract fields from Basic ID message."""
        # UA type
        raw_ua = basic.get('ua_type')
        ua_code, ua_name = self._ua_code_and_name(raw_ua)
        data['ua_type'] = ua_code
        data['ua_type_name'] = ua_name

        # ID type and value
        id_type = basic.get('id_type', "")
        data['id_type'] = id_type

        # MAC and RSSI (may override top-level)
        if 'MAC' in basic:
            data['mac'] = basic['MAC']
        if 'RSSI' in basic:
            data['rssi'] = basic['RSSI']

        # ID field depends on type
        if id_type == 'Serial Number (ANSI/CTA-2063-A)':
            data['id'] = basic.get('id', 'unknown')
        elif id_type == 'CAA Assigned Registration ID':
            data['caa_id'] = basic.get('id', 'unknown')

    def _extract_location(self, loc: dict, data: dict) -> None:
        """Extract fields from Location/Vector Message."""
        data['lat'] = self._get_float(loc.get('latitude', 0.0))
        data['lon'] = self._get_float(loc.get('longitude', 0.0))
        data['speed'] = self._get_float(loc.get('speed', 0.0))
        data['vspeed'] = self._get_float(loc.get('vert_speed', 0.0))
        data['alt'] = self._get_float(loc.get('geodetic_altitude', 0.0))
        data['height'] = self._get_float(loc.get('height_agl', 0.0))

        # Remote ID extras
        data['op_status'] = loc.get('op_status', "")
        data['height_type'] = loc.get('height_type', "")
        data['ew_dir'] = loc.get('ew_dir_segment', "")
        data['direction'] = self._get_int(loc.get('direction'), None)

        # Parse multipliers/altitudes that may have units
        speed_mult = str(loc.get('speed_multiplier', "0")).split()[0]
        data['speed_multiplier'] = self._get_float(speed_mult)

        pressure_alt = str(loc.get('pressure_altitude', "0")).split()[0]
        data['pressure_altitude'] = self._get_float(pressure_alt)

        # Accuracies
        data['vertical_accuracy'] = loc.get('vertical_accuracy', "")
        data['horizontal_accuracy'] = loc.get('horizontal_accuracy', "")
        data['baro_accuracy'] = loc.get('baro_accuracy', "")
        data['speed_accuracy'] = loc.get('speed_accuracy', "")
        data['timestamp'] = loc.get('timestamp', "")
        data['timestamp_accuracy'] = loc.get('timestamp_accuracy', "")

    def _extract_system(self, sysm: dict, data: dict) -> None:
        """Extract fields from System Message (DJI format)."""
        data['pilot_lat'] = self._get_float(sysm.get('latitude', 0.0))
        data['pilot_lon'] = self._get_float(sysm.get('longitude', 0.0))
        data['home_lat'] = self._get_float(sysm.get('home_lat', 0.0))
        data['home_lon'] = self._get_float(sysm.get('home_lon', 0.0))

    def _ua_code_and_name(self, raw_ua: Any) -> tuple:
        """
        Convert raw UA type to (code, name) tuple.

        Args:
            raw_ua: Raw UA type value (int or string)

        Returns:
            Tuple of (code: int|None, name: str)
        """
        ua_code = None

        if raw_ua is not None:
            try:
                ua_code = int(raw_ua)
            except (TypeError, ValueError):
                # Try name lookup
                ua_code = next(
                    (k for k, v in self.ua_type_mapping.items()
                     if v.lower() == str(raw_ua).lower()),
                    None
                )

        # Validate code is in mapping
        if ua_code not in self.ua_type_mapping:
            ua_code = None

        ua_name = self.ua_type_mapping.get(ua_code, 'Unknown')
        return ua_code, ua_name

    def _has_required_fields(self, data: dict) -> bool:
        """
        Check if data has minimum required fields for Drone.

        Args:
            data: Extracted drone data

        Returns:
            True if required fields present
        """
        # Must have ID (either 'id' or use MAC as fallback)
        has_id = 'id' in data or 'caa_id' in data or 'mac' in data

        # Must have basic location
        has_location = all(k in data for k in ['lat', 'lon', 'speed', 'alt', 'height'])

        # Must have telemetry basics
        has_telemetry = 'mac' in data and 'rssi' in data

        return has_id and has_location and has_telemetry

    def _create_drone(self, data: dict) -> Drone:
        """
        Create Drone model from extracted data.

        Args:
            data: Dictionary of extracted fields

        Returns:
            Drone model instance
        """
        # Determine drone ID
        drone_id = data.get('id') or data.get('caa_id') or f"drone-{data.get('mac', 'unknown')}"

        # Create Drone with all available fields
        return Drone(
            id=drone_id,
            lat=data.get('lat', 0.0),
            lon=data.get('lon', 0.0),
            speed=data.get('speed', 0.0),
            vspeed=data.get('vspeed', 0.0),
            alt=data.get('alt', 0.0),
            height=data.get('height', 0.0),
            pilot_lat=data.get('pilot_lat', 0.0),
            pilot_lon=data.get('pilot_lon', 0.0),
            description=data.get('description', ""),
            mac=data.get('mac', ""),
            rssi=data.get('rssi', 0),
            home_lat=data.get('home_lat', 0.0),
            home_lon=data.get('home_lon', 0.0),
            id_type=data.get('id_type', ""),
            ua_type=data.get('ua_type'),
            ua_type_name=data.get('ua_type_name', ""),
            operator_id_type=data.get('operator_id_type', ""),
            operator_id=data.get('operator_id', ""),
            op_status=data.get('op_status', ""),
            height_type=data.get('height_type', ""),
            ew_dir=data.get('ew_dir', ""),
            direction=data.get('direction'),
            speed_multiplier=data.get('speed_multiplier'),
            pressure_altitude=data.get('pressure_altitude'),
            vertical_accuracy=data.get('vertical_accuracy', ""),
            horizontal_accuracy=data.get('horizontal_accuracy', ""),
            baro_accuracy=data.get('baro_accuracy', ""),
            speed_accuracy=data.get('speed_accuracy', ""),
            timestamp=data.get('timestamp', ""),
            timestamp_accuracy=data.get('timestamp_accuracy', ""),
            index=data.get('index', 0),
            runtime=data.get('runtime', 0),
            caa_id=data.get('caa_id', ""),
            freq=data.get('freq'),
        )

    @staticmethod
    def _get_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
