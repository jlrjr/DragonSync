"""
Geographic location types for DragonSync.

Simple types for representing geographic coordinates.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

from typing import Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class GeoPoint:
    """
    Represents a geographic point (latitude/longitude only).

    Attributes:
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
    """

    lat: float
    lon: float

    def to_tuple(self) -> Tuple[float, float]:
        """Convert to (lat, lon) tuple."""
        return (self.lat, self.lon)


@dataclass
class Location:
    """
    Represents a full geographic location with altitude.

    Attributes:
        lat: Latitude in decimal degrees (-90 to 90)
        lon: Longitude in decimal degrees (-180 to 180)
        alt: Altitude above sea level in meters (HAE), defaults to 0.0
    """

    lat: float
    lon: float
    alt: float = 0.0

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to (lat, lon, alt) tuple."""
        return (self.lat, self.lon, self.alt)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        """
        Create Location from dictionary.

        Args:
            data: Dictionary with 'lat', 'lon', and optionally 'alt' keys

        Returns:
            Location instance
        """
        return cls(
            lat=data["lat"],
            lon=data["lon"],
            alt=data.get("alt", 0.0)
        )


def validate_latitude(lat: float) -> bool:
    """
    Validate latitude is in valid range.

    Args:
        lat: Latitude in decimal degrees

    Returns:
        True if valid (-90 to 90), False otherwise
    """
    return -90.0 <= lat <= 90.0


def validate_longitude(lon: float) -> bool:
    """
    Validate longitude is in valid range.

    Args:
        lon: Longitude in decimal degrees

    Returns:
        True if valid (-180 to 180), False otherwise
    """
    return -180.0 <= lon <= 180.0
