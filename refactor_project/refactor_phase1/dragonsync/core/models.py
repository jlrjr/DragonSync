"""
Core data models for DragonSync.

These models represent the domain objects (Drone, Aircraft, SystemStatus)
with no external dependencies - pure Python dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class DroneType(Enum):
    """Type of drone detection"""
    REMOTE_ID_BLE = "remote_id_ble"
    REMOTE_ID_WIFI = "remote_id_wifi"
    DJI = "dji"
    UNKNOWN = "unknown"


class AircraftCategory(Enum):
    """ADS-B aircraft categories (emitter category)"""
    NO_INFO = 0
    LIGHT = 1
    SMALL = 2
    LARGE = 3
    HIGH_VORTEX = 4
    HEAVY = 5
    HIGH_PERFORMANCE = 6
    ROTORCRAFT = 7


@dataclass
class Position:
    """
    Geographic position with metadata.
    
    Attributes:
        latitude: Degrees, -90 to +90
        longitude: Degrees, -180 to +180
        altitude: Meters above mean sea level (MSL)
        timestamp: UTC timestamp when position was recorded
        accuracy_horizontal: Circular Error Probable (CE) in meters
        accuracy_vertical: Linear Error Probable (LE) in meters
    """
    latitude: float
    longitude: float
    altitude: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    accuracy_horizontal: Optional[float] = None  # CE in meters
    accuracy_vertical: Optional[float] = None    # LE in meters
    
    def __post_init__(self) -> None:
        """Validate position data"""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": self.altitude,
            "timestamp": self.timestamp.isoformat(),
            "accuracy_horizontal": self.accuracy_horizontal,
            "accuracy_vertical": self.accuracy_vertical,
        }


@dataclass
class Drone:
    """
    Drone detection data model.
    
    Represents a single drone detected via Remote ID (BLE/WiFi) or DJI protocols.
    """
    id: str  # Unique identifier (MAC address, serial number, etc)
    drone_type: DroneType
    position: Position
    
    # Optional telemetry
    speed: Optional[float] = None  # m/s ground speed
    heading: Optional[float] = None  # degrees true north (0-359)
    vertical_speed: Optional[float] = None  # m/s (positive = climbing)
    rssi: Optional[float] = None  # Signal strength in dBm
    frequency: Optional[float] = None  # MHz
    
    # Remote ID specific fields
    pilot_position: Optional[Position] = None
    home_position: Optional[Position] = None
    
    # Metadata
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, **kwargs: Any) -> None:
        """
        Update drone data and refresh timestamp.
        
        Args:
            **kwargs: Fields to update (must be existing attributes)
        """
        self.last_updated = datetime.utcnow()
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ('id', 'first_seen'):
                setattr(self, key, value)
    
    def age_seconds(self) -> float:
        """Return age of last update in seconds"""
        return (datetime.utcnow() - self.last_updated).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "drone_type": self.drone_type.value,
            "position": self.position.to_dict(),
            "speed": self.speed,
            "heading": self.heading,
            "vertical_speed": self.vertical_speed,
            "rssi": self.rssi,
            "frequency": self.frequency,
            "pilot_position": self.pilot_position.to_dict() if self.pilot_position else None,
            "home_position": self.home_position.to_dict() if self.home_position else None,
            "first_seen": self.first_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class Aircraft:
    """
    ADS-B aircraft data model.
    
    Represents aircraft detected via ADS-B or UAT (978 MHz).
    """
    hex: str  # ICAO 24-bit address (hex string)
    position: Position
    
    # Identification
    callsign: Optional[str] = None
    registration: Optional[str] = None
    
    # Telemetry
    speed: Optional[float] = None  # m/s ground speed
    heading: Optional[float] = None  # degrees true north
    vertical_rate: Optional[float] = None  # m/s (positive = climbing)
    
    # ADS-B specific
    squawk: Optional[str] = None  # 4-digit transponder code
    category: Optional[AircraftCategory] = None
    on_ground: bool = False
    
    # Metadata
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def update(self, **kwargs: Any) -> None:
        """Update aircraft data and refresh timestamp"""
        self.last_updated = datetime.utcnow()
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ('hex', 'first_seen'):
                setattr(self, key, value)
    
    def age_seconds(self) -> float:
        """Return age of last update in seconds"""
        return (datetime.utcnow() - self.last_updated).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "hex": self.hex,
            "callsign": self.callsign,
            "registration": self.registration,
            "position": self.position.to_dict(),
            "speed": self.speed,
            "heading": self.heading,
            "vertical_rate": self.vertical_rate,
            "squawk": self.squawk,
            "category": self.category.value if self.category else None,
            "on_ground": self.on_ground,
            "first_seen": self.first_seen.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class SystemStatus:
    """
    WarDragon system status.
    
    Contains information about the WarDragon platform itself.
    """
    serial_number: str
    position: Position
    
    # Hardware metrics
    temperature: Optional[float] = None  # Celsius
    cpu_usage: Optional[float] = None  # Percentage 0-100
    memory_usage: Optional[float] = None  # Percentage 0-100
    disk_usage: Optional[float] = None  # Percentage 0-100
    
    # Software version info
    software_version: Optional[str] = None
    
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "serial_number": self.serial_number,
            "position": self.position.to_dict(),
            "temperature": self.temperature,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
            "software_version": self.software_version,
            "last_updated": self.last_updated.isoformat(),
        }
