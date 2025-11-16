"""
Telemetry parsing and data extraction

Parsers convert raw ZMQ messages into domain models:
- BaseParser: Abstract base parser interface
- DroneParser: Drone telemetry parsing
- SystemParser: System status parsing
"""

from .base_parser import BaseParser
from .drone_parser import DroneParser

__all__ = ["BaseParser", "DroneParser"]
