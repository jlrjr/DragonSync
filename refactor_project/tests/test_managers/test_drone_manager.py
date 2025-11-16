"""
Tests for DroneManager - manages fleet of drones.

Following TDD approach: write tests first, then implement.
"""

import pytest
import time
from refactor_project.models.drone import Drone
from refactor_project.managers.drone_manager import DroneManager


class TestDroneManagerBasics:
    """Test basic drone management operations"""

    def test_add_new_drone(self):
        """Should add a new drone to the manager"""
        manager = DroneManager()

        drone = Drone(
            id="test-drone-1",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        result = manager.add_or_update(drone)

        assert result is True, "Should return True when adding new drone"
        assert manager.get_count() == 1, "Should have 1 drone"
        assert manager.has_drone("test-drone-1"), "Should contain the drone"

    def test_get_drone(self):
        """Should retrieve a drone by ID"""
        manager = DroneManager()

        drone = Drone(
            id="test-drone-1",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )

        manager.add_or_update(drone)
        retrieved = manager.get("test-drone-1")

        assert retrieved is not None, "Should retrieve the drone"
        assert retrieved.id == "test-drone-1"
        assert retrieved.lat == 42.36

    def test_get_nonexistent_drone(self):
        """Should return None for nonexistent drone"""
        manager = DroneManager()

        result = manager.get("nonexistent")

        assert result is None, "Should return None for nonexistent drone"

    def test_update_existing_drone(self):
        """Should update an existing drone's telemetry"""
        manager = DroneManager()

        # Add initial drone
        drone1 = Drone(
            id="test-drone-1",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone1)

        # Update with new position
        drone2 = Drone(
            id="test-drone-1",  # Same ID
            lat=42.37,  # New position
            lon=-71.07,
            speed=15.0,  # New speed
            vspeed=2.0,
            alt=120.0,
            height=60.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test Drone",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-68
        )
        manager.add_or_update(drone2)

        assert manager.get_count() == 1, "Should still have 1 drone (updated, not added)"

        updated = manager.get("test-drone-1")
        assert updated.lat == 42.37, "Latitude should be updated"
        assert updated.speed == 15.0, "Speed should be updated"
        assert updated.prev_lat == 42.36, "Previous position should be stored"


class TestDroneManagerCapacity:
    """Test drone manager capacity limits"""

    def test_max_drones_limit(self):
        """Should enforce maximum drone capacity"""
        manager = DroneManager(max_drones=3)

        # Add 4 drones
        for i in range(4):
            drone = Drone(
                id=f"drone-{i}",
                lat=42.36 + i*0.01,
                lon=-71.06,
                speed=10.0,
                vspeed=1.0,
                alt=100.0,
                height=50.0,
                pilot_lat=42.36,
                pilot_lon=-71.06,
                description=f"Drone {i}",
                mac=f"AA:BB:CC:DD:EE:F{i}",
                rssi=-65
            )
            manager.add_or_update(drone)

        assert manager.get_count() == 3, "Should not exceed max_drones"
        assert not manager.has_drone("drone-0"), "Oldest drone should be evicted"
        assert manager.has_drone("drone-1"), "Second drone should remain"
        assert manager.has_drone("drone-2"), "Third drone should remain"
        assert manager.has_drone("drone-3"), "Newest drone should remain"

    def test_get_all_drones(self):
        """Should return list of all drones"""
        manager = DroneManager()

        for i in range(3):
            drone = Drone(
                id=f"drone-{i}",
                lat=42.36,
                lon=-71.06,
                speed=10.0,
                vspeed=1.0,
                alt=100.0,
                height=50.0,
                pilot_lat=42.36,
                pilot_lon=-71.06,
                description=f"Drone {i}",
                mac=f"AA:BB:CC:DD:EE:F{i}",
                rssi=-65
            )
            manager.add_or_update(drone)

        all_drones = manager.get_all()

        assert len(all_drones) == 3, "Should return all 3 drones"
        assert all(isinstance(d, Drone) for d in all_drones), "Should return Drone objects"


class TestDroneManagerTimeout:
    """Test drone timeout/stale detection"""

    def test_get_stale_drones(self):
        """Should identify drones that haven't updated recently"""
        manager = DroneManager()

        # Add drone 1 (will be stale)
        drone1 = Drone(
            id="stale-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Stale",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone1)

        # Wait a bit
        time.sleep(0.1)

        # Add drone 2 (fresh)
        drone2 = Drone(
            id="fresh-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Fresh",
            mac="BB:CC:DD:EE:FF:00",
            rssi=-65
        )
        manager.add_or_update(drone2)

        # Check for stale drones (0.05s timeout)
        stale = manager.get_stale_drones(timeout=0.05)

        assert len(stale) == 1, "Should find 1 stale drone"
        assert "stale-drone" in stale, "Stale drone should be identified"
        assert "fresh-drone" not in stale, "Fresh drone should not be stale"

    def test_remove_drone(self):
        """Should remove a drone from the manager"""
        manager = DroneManager()

        drone = Drone(
            id="test-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone)

        assert manager.get_count() == 1

        result = manager.remove("test-drone")

        assert result is True, "Should return True when removing existing drone"
        assert manager.get_count() == 0, "Should have 0 drones after removal"
        assert not manager.has_drone("test-drone"), "Drone should no longer exist"

    def test_remove_nonexistent_drone(self):
        """Should handle removing nonexistent drone gracefully"""
        manager = DroneManager()

        result = manager.remove("nonexistent")

        assert result is False, "Should return False when removing nonexistent drone"

    def test_cleanup_stale_drones(self):
        """Should remove all stale drones in one operation"""
        manager = DroneManager()

        # Add several drones
        for i in range(3):
            drone = Drone(
                id=f"drone-{i}",
                lat=42.36,
                lon=-71.06,
                speed=10.0,
                vspeed=1.0,
                alt=100.0,
                height=50.0,
                pilot_lat=42.36,
                pilot_lon=-71.06,
                description=f"Drone {i}",
                mac=f"AA:BB:CC:DD:EE:F{i}",
                rssi=-65
            )
            manager.add_or_update(drone)

        # Wait to make them stale
        time.sleep(0.1)

        # Cleanup with short timeout
        removed = manager.cleanup_stale(timeout=0.05)

        assert len(removed) == 3, "Should remove all 3 stale drones"
        assert manager.get_count() == 0, "Should have no drones after cleanup"
        assert "drone-0" in removed
        assert "drone-1" in removed
        assert "drone-2" in removed


class TestDroneManagerUpdateLogic:
    """Test update rate limiting and movement detection"""

    def test_should_send_update_rate_limit(self):
        """Should respect rate limiting for updates"""
        manager = DroneManager()

        drone = Drone(
            id="test-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone)

        # First check should allow update (never sent before)
        should_send = manager.should_send_update("test-drone", rate_limit=1.0)
        assert should_send is True, "Should allow first update"

        # Mark as sent
        manager.mark_sent("test-drone")

        # Immediate check should deny (within rate limit)
        should_send = manager.should_send_update("test-drone", rate_limit=1.0)
        assert should_send is False, "Should deny update within rate limit"

        # Wait for rate limit
        time.sleep(1.1)

        # Should allow update after rate limit
        should_send = manager.should_send_update("test-drone", rate_limit=1.0)
        assert should_send is True, "Should allow update after rate limit"

    def test_should_send_update_movement_threshold(self):
        """Should send update when drone moves significantly"""
        manager = DroneManager()

        # Add drone at initial position
        drone1 = Drone(
            id="test-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone1)
        manager.mark_sent("test-drone")

        # Update with small movement (< threshold)
        drone2 = Drone(
            id="test-drone",
            lat=42.360001,  # Very small change
            lon=-71.060001,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone2)

        # Should not send (small movement)
        should_send = manager.should_send_update(
            "test-drone",
            rate_limit=0.0,  # No rate limit
            movement_threshold=0.01  # 0.01 degree threshold
        )
        assert should_send is False, "Should not send for small movement"

        # Update with large movement (> threshold)
        drone3 = Drone(
            id="test-drone",
            lat=42.37,  # Significant change
            lon=-71.07,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone3)

        # Should send (large movement)
        should_send = manager.should_send_update(
            "test-drone",
            rate_limit=0.0,
            movement_threshold=0.01
        )
        assert should_send is True, "Should send for large movement"

    def test_mark_sent_updates_tracking(self):
        """Should update last_sent tracking when marked"""
        manager = DroneManager()

        drone = Drone(
            id="test-drone",
            lat=42.36,
            lon=-71.06,
            speed=10.0,
            vspeed=1.0,
            alt=100.0,
            height=50.0,
            pilot_lat=42.36,
            pilot_lon=-71.06,
            description="Test",
            mac="AA:BB:CC:DD:EE:FF",
            rssi=-65
        )
        manager.add_or_update(drone)

        # Get current state
        retrieved1 = manager.get("test-drone")
        initial_sent_time = retrieved1.last_sent_time

        time.sleep(0.05)

        # Mark as sent
        manager.mark_sent("test-drone")

        # Verify last_sent was updated
        retrieved2 = manager.get("test-drone")
        assert retrieved2.last_sent_time > initial_sent_time, "last_sent_time should be updated"
        assert retrieved2.last_sent_lat == drone.lat, "last_sent_lat should be stored"
        assert retrieved2.last_sent_lon == drone.lon, "last_sent_lon should be stored"
