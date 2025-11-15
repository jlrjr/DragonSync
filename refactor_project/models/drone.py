"""
Drone telemetry data model.

This module contains the pure data model for drone telemetry.
CoT generation logic has been extracted to the messaging module.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

import time
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Drone:
    """
    Represents drone telemetry data from Remote ID broadcasts.

    This is a pure data model containing telemetry fields and basic
    update logic. CoT XML generation has been moved to the messaging module.

    Attributes:
        id: Unique drone identifier (serial number or MAC-based)
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        speed: Horizontal speed in m/s
        vspeed: Vertical speed in m/s
        alt: Altitude above sea level in meters (HAE)
        height: Height above ground level in meters (AGL)
        pilot_lat: Pilot latitude in decimal degrees
        pilot_lon: Pilot longitude in decimal degrees
        description: Drone description/name
        mac: MAC address of the broadcasting device
        rssi: Received Signal Strength Indicator in dBm

        home_lat: Home point latitude (optional)
        home_lon: Home point longitude (optional)
        id_type: Type of ID (SERIAL, MAC, etc.)
        ua_type: UA type index (0-15, maps to drone types)
        ua_type_name: Human-readable UA type name
        operator_id_type: Operator ID type
        operator_id: Operator ID value
        op_status: Operational status
        height_type: Height type (AGL, etc.)
        ew_dir: East/West direction
        direction: Course/heading in degrees (0-360)
        speed_multiplier: Speed multiplier (protocol specific)
        pressure_altitude: Pressure altitude in meters
        vertical_accuracy: Vertical accuracy descriptor
        horizontal_accuracy: Horizontal accuracy descriptor
        baro_accuracy: Barometric accuracy descriptor
        speed_accuracy: Speed accuracy descriptor
        timestamp: Timestamp from drone
        timestamp_accuracy: Timestamp accuracy descriptor
        index: Message index
        runtime: Runtime in seconds
        caa_id: CAA registration ID
        freq: Frequency in Hz (or MHz if < 1e5)

        last_update_time: Unix timestamp of last update
        last_sent_time: Unix timestamp of last CoT send
        last_sent_lat: Latitude when last CoT was sent
        last_sent_lon: Longitude when last CoT was sent
        prev_lat: Previous latitude (for bearing calculation)
        prev_lon: Previous longitude (for bearing calculation)
        last_keepalive_time: Unix timestamp of last keepalive
    """

    # Required fields
    id: str
    lat: float
    lon: float
    speed: float
    vspeed: float
    alt: float
    height: float
    pilot_lat: float
    pilot_lon: float
    description: str
    mac: str
    rssi: int

    # Optional fields with defaults
    home_lat: float = 0.0
    home_lon: float = 0.0
    id_type: str = ""
    ua_type: Optional[int] = None
    ua_type_name: str = ""
    operator_id_type: str = ""
    operator_id: str = ""
    op_status: str = ""
    height_type: str = ""
    ew_dir: str = ""
    direction: Optional[float] = None
    speed_multiplier: Optional[float] = None
    pressure_altitude: Optional[float] = None
    vertical_accuracy: str = ""
    horizontal_accuracy: str = ""
    baro_accuracy: str = ""
    speed_accuracy: str = ""
    timestamp: str = ""
    timestamp_accuracy: str = ""
    index: int = 0
    runtime: int = 0
    caa_id: str = ""
    freq: Optional[float] = None

    # Tracking fields (set by __post_init__)
    last_update_time: float = field(init=False)
    last_sent_time: float = field(init=False, default=0.0)
    last_sent_lat: float = field(init=False)
    last_sent_lon: float = field(init=False)
    prev_lat: Optional[float] = field(init=False, default=None)
    prev_lon: Optional[float] = field(init=False, default=None)
    last_keepalive_time: float = field(init=False, default=0.0)

    def __post_init__(self):
        """Initialize tracking fields after dataclass init."""
        self.last_update_time = time.time()
        self.last_sent_lat = self.lat
        self.last_sent_lon = self.lon

    def update(
        self,
        lat: float,
        lon: float,
        speed: float,
        vspeed: float,
        alt: float,
        height: float,
        pilot_lat: float,
        pilot_lon: float,
        description: str,
        mac: str,
        rssi: int,
        home_lat: float = 0.0,
        home_lon: float = 0.0,
        id_type: str = "",
        ua_type: Optional[int] = None,
        ua_type_name: str = "",
        operator_id_type: str = "",
        operator_id: str = "",
        op_status: str = "",
        height_type: str = "",
        ew_dir: str = "",
        direction: Optional[float] = None,
        speed_multiplier: Optional[float] = None,
        pressure_altitude: Optional[float] = None,
        vertical_accuracy: str = "",
        horizontal_accuracy: str = "",
        baro_accuracy: str = "",
        speed_accuracy: str = "",
        timestamp: str = "",
        timestamp_accuracy: str = "",
        index: int = 0,
        runtime: int = 0,
        caa_id: str = "",
        freq: Optional[float] = None,
    ) -> None:
        """
        Update drone telemetry data.

        Stores previous position and updates all telemetry fields.
        Updates last_update_time to current time.

        Args:
            lat: New latitude
            lon: New longitude
            speed: New horizontal speed
            vspeed: New vertical speed
            alt: New altitude
            height: New height AGL
            pilot_lat: New pilot latitude
            pilot_lon: New pilot longitude
            description: New description
            mac: New MAC address
            rssi: New RSSI value
            ... (all other optional parameters)
        """
        # Store previous position for bearing calculations
        self.prev_lat = self.lat
        self.prev_lon = self.lon

        # Update core telemetry
        self.lat = lat
        self.lon = lon
        self.speed = speed
        self.vspeed = vspeed
        self.alt = alt
        self.height = height
        self.pilot_lat = pilot_lat
        self.pilot_lon = pilot_lon
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.description = description
        self.mac = mac
        self.rssi = rssi
        self.index = index
        self.runtime = runtime
        self.id_type = id_type

        # Update UA type if provided
        if ua_type is not None:
            self.ua_type = ua_type
        if ua_type_name:
            self.ua_type_name = ua_type_name

        # Update Remote ID extras if provided
        if operator_id_type:
            self.operator_id_type = operator_id_type
        if operator_id:
            self.operator_id = operator_id
        if op_status:
            self.op_status = op_status
        if height_type:
            self.height_type = height_type
        if ew_dir:
            self.ew_dir = ew_dir
        if direction is not None:
            self.direction = direction
        if speed_multiplier is not None:
            self.speed_multiplier = speed_multiplier
        if pressure_altitude is not None:
            self.pressure_altitude = pressure_altitude
        if vertical_accuracy:
            self.vertical_accuracy = vertical_accuracy
        if horizontal_accuracy:
            self.horizontal_accuracy = horizontal_accuracy
        if baro_accuracy:
            self.baro_accuracy = baro_accuracy
        if speed_accuracy:
            self.speed_accuracy = speed_accuracy
        if timestamp:
            self.timestamp = timestamp
        if timestamp_accuracy:
            self.timestamp_accuracy = timestamp_accuracy
        if caa_id:
            self.caa_id = caa_id
        if freq is not None:
            self.freq = freq

        # Update timestamp
        self.last_update_time = time.time()
