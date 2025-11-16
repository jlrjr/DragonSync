"""
Business logic and orchestration

Managers coordinate between parsers, models, and sinks:
- DroneManager: Drone collection management
- RateLimiter: Rate limiting logic
- TimeoutManager: Inactivity timeout handling
"""

from refactor_project.managers.drone_manager import DroneManager

__all__ = ["DroneManager"]
