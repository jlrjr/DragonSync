"""
Domain models for DragonSync

Pure data models with minimal business logic:
- Drone: Drone telemetry data
- SystemStatus: WarDragon system status
- Location: Geographic location data types
- Telemetry: Base telemetry structures
"""

from .drone import Drone

__all__ = ["Drone"]
