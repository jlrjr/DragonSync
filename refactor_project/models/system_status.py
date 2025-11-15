"""
SystemStatus model for WarDragon system telemetry.

This module contains the pure data model for WarDragon system status.
CoT generation logic has been extracted to the messaging module.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

import time
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SystemStatus:
    """
    Represents WarDragon system status and GPS telemetry.

    This is a pure data model containing system metrics and GPS data.
    CoT XML generation has been moved to the messaging module.

    Attributes:
        serial_number: WarDragon serial number
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        alt: Altitude above sea level in meters (HAE)

        cpu_usage: CPU usage percentage (0-100)
        memory_total: Total memory in MB
        memory_available: Available memory in MB
        disk_total: Total disk space in MB
        disk_used: Used disk space in MB
        temperature: System temperature in Celsius
        uptime: System uptime in seconds
        pluto_temp: PlutoSDR temperature (string with unit)
        zynq_temp: Zynq FPGA temperature (string with unit)
        speed: GPS speed in m/s
        track: GPS track/course in degrees (0-360)

        id: Generated UID (wardragon-{serial_number})
        last_update_time: Unix timestamp of last update
    """

    # Required fields
    serial_number: str
    lat: float
    lon: float
    alt: float

    # Optional hardware metrics
    cpu_usage: float = 0.0
    memory_total: float = 0.0
    memory_available: float = 0.0
    disk_total: float = 0.0
    disk_used: float = 0.0
    temperature: float = 0.0
    uptime: float = 0.0
    pluto_temp: str = "N/A"
    zynq_temp: str = "N/A"

    # GPS-provided fields
    speed: float = 0.0
    track: float = 0.0

    # Computed/tracking fields
    id: str = field(init=False)
    last_update_time: float = field(init=False)

    def __post_init__(self):
        """Initialize computed fields after dataclass init."""
        self.id = f"wardragon-{self.serial_number}"
        self.last_update_time = time.time()

    def update(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        alt: Optional[float] = None,
        cpu_usage: Optional[float] = None,
        memory_total: Optional[float] = None,
        memory_available: Optional[float] = None,
        disk_total: Optional[float] = None,
        disk_used: Optional[float] = None,
        temperature: Optional[float] = None,
        uptime: Optional[float] = None,
        pluto_temp: Optional[str] = None,
        zynq_temp: Optional[str] = None,
        speed: Optional[float] = None,
        track: Optional[float] = None,
    ) -> None:
        """
        Update system status data.

        Only updates fields that are provided (not None).
        Updates last_update_time to current time.

        Args:
            lat: New latitude
            lon: New longitude
            alt: New altitude
            cpu_usage: New CPU usage percentage
            memory_total: New total memory
            memory_available: New available memory
            disk_total: New total disk space
            disk_used: New used disk space
            temperature: New system temperature
            uptime: New uptime
            pluto_temp: New PlutoSDR temperature
            zynq_temp: New Zynq temperature
            speed: New GPS speed
            track: New GPS track/course
        """
        if lat is not None:
            self.lat = lat
        if lon is not None:
            self.lon = lon
        if alt is not None:
            self.alt = alt
        if cpu_usage is not None:
            self.cpu_usage = cpu_usage
        if memory_total is not None:
            self.memory_total = memory_total
        if memory_available is not None:
            self.memory_available = memory_available
        if disk_total is not None:
            self.disk_total = disk_total
        if disk_used is not None:
            self.disk_used = disk_used
        if temperature is not None:
            self.temperature = temperature
        if uptime is not None:
            self.uptime = uptime
        if pluto_temp is not None:
            self.pluto_temp = pluto_temp
        if zynq_temp is not None:
            self.zynq_temp = zynq_temp
        if speed is not None:
            self.speed = speed
        if track is not None:
            self.track = track

        self.last_update_time = time.time()
