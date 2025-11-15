"""
Domain models for DragonSync

Pure data models with minimal business logic:
- Drone: Drone telemetry data
- SystemStatus: WarDragon system status
- Location: Geographic location data types
- Telemetry: Base telemetry structures
"""

from .drone import Drone
from .system_status import SystemStatus
from .location import Location, GeoPoint, validate_latitude, validate_longitude
from .telemetry import TelemetryData, RemoteIdData

__all__ = [
    "Drone",
    "SystemStatus",
    "Location",
    "GeoPoint",
    "validate_latitude",
    "validate_longitude",
    "TelemetryData",
    "RemoteIdData",
]
