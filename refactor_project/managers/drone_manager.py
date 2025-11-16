"""
DroneManager - Manages a fleet of drones with timeout and rate limiting.

Responsibilities:
- Track active drones (CRUD operations)
- Detect stale/timed-out drones
- Rate limiting for updates
- Movement detection
- Capacity management (max drones)

This is pure business logic - no I/O, no CoT generation, no sinks.
Those responsibilities are handled in later phases.
"""

import time
import math
from collections import deque, OrderedDict
from typing import Optional, List, Dict
import logging

from refactor_project.models.drone import Drone

logger = logging.getLogger(__name__)


class DroneManager:
    """
    Manages a collection of drones with capacity limits and timeout detection.

    Features:
    - Add/update/remove/query drones
    - Maximum drone capacity (FIFO eviction)
    - Stale drone detection (timeout-based)
    - Update rate limiting logic
    - Movement threshold detection
    """

    def __init__(self, max_drones: int = 30):
        """
        Initialize DroneManager.

        Args:
            max_drones: Maximum number of drones to track (default: 30)
        """
        self.max_drones = max_drones
        self._drones: OrderedDict[str, Drone] = OrderedDict()
        self._drone_order: deque[str] = deque(maxlen=max_drones)

    def add_or_update(self, drone: Drone) -> bool:
        """
        Add a new drone or update an existing one.

        If the drone exists, updates its telemetry data.
        If new and at capacity, evicts the oldest drone.

        Args:
            drone: Drone instance to add or update

        Returns:
            True if operation succeeded
        """
        drone_id = drone.id

        if drone_id in self._drones:
            # Update existing drone
            existing = self._drones[drone_id]

            # Store previous position for movement detection
            existing.prev_lat = existing.lat
            existing.prev_lon = existing.lon

            # Update all telemetry fields
            existing.update(
                lat=drone.lat,
                lon=drone.lon,
                speed=drone.speed,
                vspeed=drone.vspeed,
                alt=drone.alt,
                height=drone.height,
                pilot_lat=drone.pilot_lat,
                pilot_lon=drone.pilot_lon,
                description=drone.description,
                mac=drone.mac,
                rssi=drone.rssi,
                home_lat=drone.home_lat,
                home_lon=drone.home_lon,
                id_type=drone.id_type,
                ua_type=drone.ua_type,
                ua_type_name=drone.ua_type_name,
                operator_id_type=drone.operator_id_type,
                operator_id=drone.operator_id,
                op_status=drone.op_status,
                direction=drone.direction,
                caa_id=drone.caa_id,
                freq=drone.freq,
            )

            logger.debug(f"Updated drone: {drone_id}")
            return True

        else:
            # Add new drone
            if len(self._drones) >= self.max_drones:
                # Evict oldest drone
                oldest_id = self._drone_order.popleft()
                self._drones.pop(oldest_id, None)
                logger.debug(f"Evicted oldest drone: {oldest_id}")

            # Add to tracking
            self._drones[drone_id] = drone
            self._drone_order.append(drone_id)

            # Initialize last_sent tracking
            drone.last_sent_time = 0.0
            drone.last_sent_lat = drone.lat
            drone.last_sent_lon = drone.lon

            logger.debug(f"Added new drone: {drone_id}")
            return True

    def get(self, drone_id: str) -> Optional[Drone]:
        """
        Retrieve a drone by ID.

        Args:
            drone_id: Drone identifier

        Returns:
            Drone instance if found, None otherwise
        """
        return self._drones.get(drone_id)

    def has_drone(self, drone_id: str) -> bool:
        """
        Check if a drone exists in the manager.

        Args:
            drone_id: Drone identifier

        Returns:
            True if drone exists, False otherwise
        """
        return drone_id in self._drones

    def get_all(self) -> List[Drone]:
        """
        Get all active drones.

        Returns:
            List of all Drone instances
        """
        return list(self._drones.values())

    def get_count(self) -> int:
        """
        Get the number of tracked drones.

        Returns:
            Number of active drones
        """
        return len(self._drones)

    def remove(self, drone_id: str) -> bool:
        """
        Remove a drone from tracking.

        Args:
            drone_id: Drone identifier

        Returns:
            True if drone was removed, False if not found
        """
        if drone_id not in self._drones:
            return False

        # Remove from dict
        self._drones.pop(drone_id, None)

        # Remove from order tracking
        try:
            self._drone_order.remove(drone_id)
        except ValueError:
            pass

        logger.debug(f"Removed drone: {drone_id}")
        return True

    def get_stale_drones(self, timeout: float) -> List[str]:
        """
        Identify drones that haven't been updated recently.

        Args:
            timeout: Timeout in seconds

        Returns:
            List of drone IDs that are stale
        """
        now = time.time()
        stale = []

        for drone_id, drone in self._drones.items():
            age = now - drone.last_update_time
            if age > timeout:
                stale.append(drone_id)
                logger.debug(f"Drone {drone_id} is stale (age: {age:.2f}s)")

        return stale

    def should_send_update(
        self,
        drone_id: str,
        rate_limit: float = 1.0,
        movement_threshold: float = 0.0
    ) -> bool:
        """
        Determine if an update should be sent for a drone.

        Checks both rate limiting and movement threshold.

        Args:
            drone_id: Drone identifier
            rate_limit: Minimum seconds between updates (default: 1.0)
            movement_threshold: Minimum position change in degrees (default: 0.0)

        Returns:
            True if update should be sent, False otherwise
        """
        drone = self._drones.get(drone_id)
        if not drone:
            return False

        now = time.time()

        # Check rate limit
        time_since_last_sent = now - drone.last_sent_time
        if time_since_last_sent < rate_limit:
            return False

        # Check movement threshold if specified
        if movement_threshold > 0:
            delta_lat = drone.lat - drone.last_sent_lat
            delta_lon = drone.lon - drone.last_sent_lon
            movement = math.hypot(delta_lat, delta_lon)

            if movement < movement_threshold:
                return False

        return True

    def mark_sent(self, drone_id: str) -> bool:
        """
        Mark a drone's update as sent (updates last_sent tracking).

        Args:
            drone_id: Drone identifier

        Returns:
            True if drone was found and updated, False otherwise
        """
        drone = self._drones.get(drone_id)
        if not drone:
            return False

        drone.last_sent_time = time.time()
        drone.last_sent_lat = drone.lat
        drone.last_sent_lon = drone.lon

        return True

    def cleanup_stale(self, timeout: float) -> List[str]:
        """
        Remove all stale drones and return their IDs.

        Convenience method that combines get_stale_drones() and remove().

        Args:
            timeout: Timeout in seconds

        Returns:
            List of drone IDs that were removed
        """
        stale_ids = self.get_stale_drones(timeout)

        for drone_id in stale_ids:
            self.remove(drone_id)

        if stale_ids:
            logger.info(f"Cleaned up {len(stale_ids)} stale drones")

        return stale_ids
