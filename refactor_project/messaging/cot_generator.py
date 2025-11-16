"""
CoT (Cursor on Target) Generator - Creates TAK-compliant XML messages.

Generates CoT XML messages following modern standards:
- MIL-STD-2525 compliant type codes
- Modern UAV/drone designators (-Q suffix)
- Timezone-aware timestamps
- Accurate CE/LE from Remote ID data
- Proper XML escaping

References:
- MITRE CoT Developer's Guide
- MIL-STD-2525: Common Warfighting Symbology
- TAK Product Center specifications
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

from refactor_project.models.drone import Drone

logger = logging.getLogger(__name__)


# Modern UAV/drone type codes (MIL-STD-2525 compliant)
# Format: a-affiliation-dimension-function
# -Q suffix = Unmanned/Drone (military)
# -q suffix = Unmanned/Drone (civilian)
MODERN_UA_TYPE_TO_COT = {
    0: 'a-u-A-M-H-Q',   # No type → default to rotary drone
    1: 'a-u-A-M-F-Q',   # Fixed wing → military fixed unmanned
    2: 'a-u-A-M-H-Q',   # Multirotor → military rotary unmanned
    3: 'a-u-A-M-H-Q',   # Gyroplane → rotary drone
    4: 'a-u-A-M-H-Q',   # VTOL → rotary drone
    5: 'a-u-A-C-F-q',   # Ornithopter → civilian fixed (lowercase)
    6: 'a-u-A-C-F-q',   # Glider → civilian fixed
    7: 'b-m-p-s-m',     # Kite → surface marker
    8: 'b-m-p-s-m',     # Balloon → surface marker
    9: 'b-m-p-s-m',     # Captive balloon → surface marker
    10: 'b-m-p-s-m',    # Airship → surface marker
    11: 'b-m-p-s-m',    # Parachute → surface marker
    12: 'b-m-p-s-m',    # Rocket → surface marker
    13: 'b-m-p-s-m',    # Tethered aircraft → surface marker
    14: 'b-m-p-s-m',    # Ground obstacle → surface marker
    15: 'a-u-A-M-H-Q',  # Other → default to rotary drone
}

# Legacy type codes (for backwards compatibility)
LEGACY_UA_TYPE_TO_COT = {
    1: 'a-f-A-f',       # Fixed wing
    2: 'a-u-A-M-H-R',   # Multirotor
    3: 'a-u-A-M-H-R',   # Gyroplane
    4: 'a-u-A-M-H-R',   # VTOL
    5: 'a-f-A-f',       # Ornithopter
    6: 'a-f-A-f',       # Glider
    7: 'b-m-p-s-m',     # Kite
    8: 'b-m-p-s-m',     # Balloon
    9: 'b-m-p-s-m',     # Captive balloon
    10: 'b-m-p-s-m',    # Airship
    11: 'b-m-p-s-m',    # Parachute
    12: 'b-m-p-s-m',    # Rocket
    13: 'b-m-p-s-m',    # Tethered aircraft
    14: 'b-m-p-s-m',    # Ground obstacle
    15: 'b-m-p-s-m',    # Other
}


class CotGenerator:
    """
    Generates Cursor on Target (CoT) XML messages compliant with TAK standards.

    Features:
    - Modern MIL-STD-2525 type codes with drone designators (-Q suffix)
    - Timezone-aware timestamps (Python 3.12+ compatible)
    - Accurate CE/LE parsed from Remote ID data
    - Configurable stale times
    - Proper XML escaping
    - Three event types: drone, pilot, home

    Example:
        >>> generator = CotGenerator(default_stale_seconds=30.0)
        >>> drone_xml = generator.generate_drone_event(drone)
        >>> pilot_xml = generator.generate_pilot_event(drone)
    """

    def __init__(
        self,
        default_stale_seconds: float = 60.0,
        default_ce: float = 35.0,
        default_le: float = 999999.0,
        version: str = "2.0",
        use_modern_types: bool = True
    ):
        """
        Initialize CoT generator.

        Args:
            default_stale_seconds: Default stale time in seconds (default: 60)
            default_ce: Default circular error in meters (default: 35.0 for GPS)
            default_le: Default linear error in meters (default: 999999 = unknown)
            version: CoT version string (default: "2.0")
            use_modern_types: Use modern -Q suffix type codes (default: True)
        """
        self.default_stale_seconds = default_stale_seconds
        self.default_ce = default_ce
        self.default_le = default_le
        self.version = version
        self.use_modern_types = use_modern_types

    def generate_drone_event(
        self,
        drone: Drone,
        stale_seconds: Optional[float] = None
    ) -> bytes:
        """
        Generate CoT XML for drone main event.

        Args:
            drone: Drone model instance
            stale_seconds: Override default stale time

        Returns:
            UTF-8 encoded XML bytes
        """
        now = datetime.now(timezone.utc)
        stale_offset = stale_seconds if stale_seconds is not None else self.default_stale_seconds
        stale = now + timedelta(seconds=stale_offset)

        # Determine CoT type from UA type
        cot_type = self._get_cot_type(drone.ua_type)

        # Create event element
        event = ET.Element('event')
        event.set('version', self.version)
        event.set('uid', drone.id)
        event.set('type', cot_type)
        event.set('time', self._format_timestamp(now))
        event.set('start', self._format_timestamp(now))
        event.set('stale', self._format_timestamp(stale))
        event.set('how', 'm-g')  # GPS-derived

        # Create point element
        point = ET.SubElement(event, 'point')
        point.set('lat', str(drone.lat))
        point.set('lon', str(drone.lon))
        point.set('hae', str(drone.alt))
        point.set('ce', str(self._get_ce(drone)))
        point.set('le', str(self._get_le(drone)))

        # Create detail element
        detail = ET.SubElement(event, 'detail')

        # Contact/callsign
        contact = ET.SubElement(detail, 'contact')
        contact.set('callsign', drone.id)

        # Precision location
        prec = ET.SubElement(detail, 'precisionlocation')
        prec.set('geopointsrc', 'gps')
        prec.set('altsrc', 'gps')

        # Track element (for moving entities)
        if drone.direction is not None or drone.speed > 0:
            track = ET.SubElement(detail, 'track')
            track.set('course', str(drone.direction if drone.direction is not None else 0.0))
            track.set('speed', str(drone.speed))

        # Remarks with telemetry details
        remarks_text = self._build_drone_remarks(drone)
        remarks = ET.SubElement(detail, 'remarks')
        remarks.text = remarks_text

        # Color (yellow for drones)
        color = ET.SubElement(detail, 'color')
        color.set('argb', '-256')  # Yellow

        # Convert to bytes
        xml_bytes = ET.tostring(event, encoding='UTF-8', xml_declaration=True)

        logger.debug("Generated drone CoT for '%s'", drone.id)
        return xml_bytes

    def generate_pilot_event(
        self,
        drone: Drone,
        stale_seconds: Optional[float] = None
    ) -> bytes:
        """
        Generate CoT XML for pilot location.

        Args:
            drone: Drone model instance
            stale_seconds: Override default stale time

        Returns:
            UTF-8 encoded XML bytes, or empty bytes if no pilot location
        """
        # Skip if no pilot location
        if drone.pilot_lat == 0.0 and drone.pilot_lon == 0.0:
            logger.debug("Skipping pilot CoT for '%s' (no pilot location)", drone.id)
            return b''

        # Skip for alert drones
        if drone.id == "drone-alert":
            logger.debug("Skipping pilot CoT for 'drone-alert'")
            return b''

        now = datetime.now(timezone.utc)
        stale_offset = stale_seconds if stale_seconds is not None else self.default_stale_seconds
        stale = now + timedelta(seconds=stale_offset)

        # Generate UID from drone ID
        base_id = drone.id.replace('drone-', '', 1) if drone.id.startswith('drone-') else drone.id
        uid = f'pilot-{base_id}'

        # Create event element
        event = ET.Element('event')
        event.set('version', self.version)
        event.set('uid', uid)
        event.set('type', 'b-m-p-s-m')  # Surface marker (person)
        event.set('time', self._format_timestamp(now))
        event.set('start', self._format_timestamp(now))
        event.set('stale', self._format_timestamp(stale))
        event.set('how', 'm-g')

        # Create point element
        point = ET.SubElement(event, 'point')
        point.set('lat', str(drone.pilot_lat))
        point.set('lon', str(drone.pilot_lon))
        point.set('hae', str(drone.alt))  # Use drone alt as approximation
        point.set('ce', str(self.default_ce))
        point.set('le', str(self.default_le))

        # Create detail element
        detail = ET.SubElement(event, 'detail')

        # Contact
        contact = ET.SubElement(detail, 'contact')
        contact.set('callsign', uid)

        # Precision location
        prec = ET.SubElement(detail, 'precisionlocation')
        prec.set('geopointsrc', 'gps')
        prec.set('altsrc', 'gps')

        # User icon (person)
        usericon = ET.SubElement(detail, 'usericon')
        usericon.set('iconsetpath', 'com.atakmap.android.maps.public/Civilian/Person.png')

        # Remarks
        remarks = ET.SubElement(detail, 'remarks')
        remarks.text = f'Pilot location for drone {drone.id}'

        # Convert to bytes
        xml_bytes = ET.tostring(event, encoding='UTF-8', xml_declaration=True)

        logger.debug("Generated pilot CoT for '%s'", drone.id)
        return xml_bytes

    def generate_home_event(
        self,
        drone: Drone,
        stale_seconds: Optional[float] = None
    ) -> bytes:
        """
        Generate CoT XML for home point location.

        Args:
            drone: Drone model instance
            stale_seconds: Override default stale time

        Returns:
            UTF-8 encoded XML bytes, or empty bytes if no home location
        """
        # Skip if no home location
        if drone.home_lat == 0.0 and drone.home_lon == 0.0:
            logger.debug("Skipping home CoT for '%s' (no home location)", drone.id)
            return b''

        # Skip for alert drones
        if drone.id == "drone-alert":
            logger.debug("Skipping home CoT for 'drone-alert'")
            return b''

        now = datetime.now(timezone.utc)
        stale_offset = stale_seconds if stale_seconds is not None else self.default_stale_seconds
        stale = now + timedelta(seconds=stale_offset)

        # Generate UID from drone ID
        base_id = drone.id.replace('drone-', '', 1) if drone.id.startswith('drone-') else drone.id
        uid = f'home-{base_id}'

        # Create event element
        event = ET.Element('event')
        event.set('version', self.version)
        event.set('uid', uid)
        event.set('type', 'b-m-p-s-m')  # Surface marker
        event.set('time', self._format_timestamp(now))
        event.set('start', self._format_timestamp(now))
        event.set('stale', self._format_timestamp(stale))
        event.set('how', 'm-g')

        # Create point element
        point = ET.SubElement(event, 'point')
        point.set('lat', str(drone.home_lat))
        point.set('lon', str(drone.home_lon))
        point.set('hae', str(drone.alt))  # Use drone alt as approximation
        point.set('ce', str(self.default_ce))
        point.set('le', str(self.default_le))

        # Create detail element
        detail = ET.SubElement(event, 'detail')

        # Contact
        contact = ET.SubElement(detail, 'contact')
        contact.set('callsign', uid)

        # Precision location
        prec = ET.SubElement(detail, 'precisionlocation')
        prec.set('geopointsrc', 'gps')
        prec.set('altsrc', 'gps')

        # User icon (house)
        usericon = ET.SubElement(detail, 'usericon')
        usericon.set('iconsetpath', 'com.atakmap.android.maps.public/Civilian/House.png')

        # Remarks
        remarks = ET.SubElement(detail, 'remarks')
        remarks.text = f'Home point for drone {drone.id}'

        # Convert to bytes
        xml_bytes = ET.tostring(event, encoding='UTF-8', xml_declaration=True)

        logger.debug("Generated home CoT for '%s'", drone.id)
        return xml_bytes

    def _get_cot_type(self, ua_type: Optional[int]) -> str:
        """
        Get CoT type code from UA type.

        Args:
            ua_type: UA type code (0-15)

        Returns:
            CoT type string (e.g., 'a-u-A-M-H-Q')
        """
        if ua_type is None:
            ua_type = 2  # Default to multirotor

        if self.use_modern_types:
            return MODERN_UA_TYPE_TO_COT.get(ua_type, 'a-u-A-M-H-Q')
        else:
            return LEGACY_UA_TYPE_TO_COT.get(ua_type, 'a-u-A-M-H-R')

    def _get_ce(self, drone: Drone) -> float:
        """
        Get Circular Error (horizontal accuracy) in meters.

        Parses Remote ID horizontal_accuracy if available,
        otherwise uses default.

        Args:
            drone: Drone instance

        Returns:
            CE value in meters
        """
        if hasattr(drone, 'horizontal_accuracy') and drone.horizontal_accuracy:
            parsed = self._parse_accuracy(drone.horizontal_accuracy)
            if parsed is not None:
                return parsed

        return self.default_ce

    def _get_le(self, drone: Drone) -> float:
        """
        Get Linear Error (vertical accuracy) in meters.

        Parses Remote ID vertical_accuracy if available,
        otherwise uses default.

        Args:
            drone: Drone instance

        Returns:
            LE value in meters
        """
        if hasattr(drone, 'vertical_accuracy') and drone.vertical_accuracy:
            parsed = self._parse_accuracy(drone.vertical_accuracy)
            if parsed is not None:
                return parsed

        return self.default_le

    def _parse_accuracy(self, accuracy_str: str) -> Optional[float]:
        """
        Parse accuracy string like '10m' or '3.5m' to float.

        Args:
            accuracy_str: Accuracy string from Remote ID

        Returns:
            Numeric accuracy value, or None if unable to parse
        """
        if not accuracy_str:
            return None

        # Extract numeric value from strings like "10m", "3.5m", "< 3m", etc.
        match = re.search(r'(\d+\.?\d*)', accuracy_str)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None

        return None

    def _format_timestamp(self, dt: datetime) -> str:
        """
        Format datetime as ISO 8601 with Z suffix.

        Args:
            dt: Datetime instance (must be timezone-aware)

        Returns:
            ISO 8601 formatted string with Z suffix
        """
        # Convert to ISO format and replace +00:00 with Z
        return dt.isoformat().replace('+00:00', 'Z')

    def _build_drone_remarks(self, drone: Drone) -> str:
        """
        Build remarks text with drone telemetry details.

        Args:
            drone: Drone instance

        Returns:
            Human-readable remarks string
        """
        parts = []

        # MAC and RSSI
        parts.append(f"MAC: {drone.mac}, RSSI: {drone.rssi}dBm")

        # ID type
        if drone.id_type:
            parts.append(f"ID Type: {drone.id_type}")

        # UA type
        if drone.ua_type is not None:
            ua_type_str = f"{drone.ua_type_name} ({drone.ua_type})" if drone.ua_type_name else str(drone.ua_type)
            parts.append(f"UA Type: {ua_type_str}")

        # Operator
        if drone.operator_id:
            parts.append(f"Operator ID: [{drone.operator_id_type}: {drone.operator_id}]")

        # Telemetry
        parts.append(f"Speed: {drone.speed} m/s")
        parts.append(f"Vert Speed: {drone.vspeed} m/s")
        parts.append(f"Altitude: {drone.alt} m")
        parts.append(f"AGL: {drone.height} m")

        if drone.direction is not None:
            parts.append(f"Course: {drone.direction}°")

        # Frequency (if available)
        if hasattr(drone, 'freq') and drone.freq:
            freq_mhz = drone.freq / 1e6 if drone.freq > 1e5 else drone.freq
            parts.append(f"Freq: ~{freq_mhz:.1f} MHz")

        return "; ".join(parts)
