"""
DragonSync - Drone Detection Gateway

A lightweight gateway that converts drone detections (Remote ID, DJI) and ADS-B 
aircraft data into Cursor on Target (CoT) messages for TAK/ATAK, with optional 
MQTT/Home Assistant and Lattice integration.
"""

__version__ = "2.0.0"
__author__ = "DragonSync Contributors"
__license__ = "Apache-2.0"

from dragonsync.core.models import Drone, Aircraft, SystemStatus, Position
from dragonsync.config.models import DragonSyncConfig

__all__ = [
    "Drone",
    "Aircraft", 
    "SystemStatus",
    "Position",
    "DragonSyncConfig",
]
