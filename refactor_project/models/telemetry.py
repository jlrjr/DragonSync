"""
Base telemetry data structures for DragonSync.

Common telemetry structures used across parsers and models.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

import time
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class TelemetryData:
    """
    Base telemetry data from any source.

    Common fields present in all telemetry messages (drone, system, etc.).

    Attributes:
        source_id: Source identifier (serial, MAC-based ID, etc.)
        mac: MAC address of broadcasting device
        rssi: Received Signal Strength Indicator in dBm
        freq: Frequency in Hz or MHz (optional)
        timestamp: Unix timestamp when received
    """

    source_id: str
    mac: str
    rssi: int
    freq: Optional[float] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class RemoteIdData:
    """
    Remote ID telemetry data structure.

    Standardized structure for Remote ID broadcasts (WiFi, BLE, DJI).
    This is used by parsers to create Drone models.

    Attributes:
        ua_id: Unmanned Aircraft ID (serial number)
        ua_type: UA type index (0-15)
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        alt: Altitude above sea level in meters (HAE)
        speed: Horizontal speed in m/s
        vspeed: Vertical speed in m/s
        height: Height above ground level in meters (AGL)
        direction: Course/heading in degrees (0-360)
        operator_id: Operator ID string
        operator_lat: Operator latitude in decimal degrees
        operator_lon: Operator longitude in decimal degrees
        home_lat: Home point latitude in decimal degrees
        home_lon: Home point longitude in decimal degrees
        description: Drone description/name
    """

    # Required fields
    ua_id: str
    ua_type: int
    lat: float
    lon: float
    alt: float
    speed: float

    # Optional flight data
    vspeed: float = 0.0
    height: float = 0.0
    direction: Optional[float] = None

    # Optional operator/home data
    operator_id: str = ""
    operator_lat: float = 0.0
    operator_lon: float = 0.0
    home_lat: float = 0.0
    home_lon: float = 0.0
    description: str = ""
