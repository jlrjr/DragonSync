"""
Unit tests for core data models.

Tests Position, Drone, Aircraft, and SystemStatus models.
"""

import pytest
from datetime import datetime, timedelta
from dragonsync.core.models import (
    Position,
    Drone,
    Aircraft,
    SystemStatus,
    DroneType,
    AircraftCategory,
)


class TestPosition:
    """Test Position model"""
    
    def test_position_creation(self):
        """Test basic position creation"""
        pos = Position(
            latitude=42.3601,
            longitude=-71.0589,
            altitude=50.0
        )
        assert pos.latitude == 42.3601
        assert pos.longitude == -71.0589
        assert pos.altitude == 50.0
        assert isinstance(pos.timestamp, datetime)
    
    def test_position_validation_latitude(self):
        """Test latitude validation"""
        with pytest.raises(ValueError, match="Invalid latitude"):
            Position(latitude=91.0, longitude=0.0, altitude=0.0)
        
        with pytest.raises(ValueError, match="Invalid latitude"):
            Position(latitude=-91.0, longitude=0.0, altitude=0.0)
    
    def test_position_validation_longitude(self):
        """Test longitude validation"""
        with pytest.raises(ValueError, match="Invalid longitude"):
            Position(latitude=0.0, longitude=181.0, altitude=0.0)
        
        with pytest.raises(ValueError, match="Invalid longitude"):
            Position(latitude=0.0, longitude=-181.0, altitude=0.0)
    
    def test_position_to_dict(self):
        """Test position serialization"""
        pos = Position(
            latitude=42.0,
            longitude=-71.0,
            altitude=100.0,
            accuracy_horizontal=5.0,
            accuracy_vertical=10.0
        )
        data = pos.to_dict()
        
        assert data["latitude"] == 42.0
        assert data["longitude"] == -71.0
        assert data["altitude"] == 100.0
        assert data["accuracy_horizontal"] == 5.0
        assert data["accuracy_vertical"] == 10.0
        assert "timestamp" in data


class TestDrone:
    """Test Drone model"""
    
    def test_drone_creation(self):
        """Test basic drone creation"""
        pos = Position(42.0, -71.0, 50.0)
        drone = Drone(
            id="AA:BB:CC:DD:EE:FF",
            drone_type=DroneType.REMOTE_ID_BLE,
            position=pos,
            speed=12.5,
            heading=180.0
        )
        
        assert drone.id == "AA:BB:CC:DD:EE:FF"
        assert drone.drone_type == DroneType.REMOTE_ID_BLE
        assert drone.position == pos
        assert drone.speed == 12.5
        assert drone.heading == 180.0
    
    def test_drone_update(self):
        """Test drone update method"""
        pos = Position(42.0, -71.0, 50.0)
        drone = Drone(
            id="test-drone",
            drone_type=DroneType.DJI,
            position=pos
        )
        
        original_timestamp = drone.last_updated
        
        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)
        
        drone.update(speed=15.0, heading=90.0)
        
        assert drone.speed == 15.0
        assert drone.heading == 90.0
        assert drone.last_updated > original_timestamp
    
    def test_drone_update_immutable_fields(self):
        """Test that update doesn't change id or first_seen"""
        pos = Position(42.0, -71.0, 50.0)
        drone = Drone(
            id="test-drone",
            drone_type=DroneType.DJI,
            position=pos
        )
        
        original_id = drone.id
        original_first_seen = drone.first_seen
        
        drone.update(id="new-id", first_seen=datetime.utcnow())
        
        assert drone.id == original_id
        assert drone.first_seen == original_first_seen
    
    def test_drone_age_seconds(self):
        """Test age calculation"""
        pos = Position(42.0, -71.0, 50.0)
        drone = Drone(
            id="test-drone",
            drone_type=DroneType.REMOTE_ID_BLE,
            position=pos
        )
        
        # Age should be very small (just created)
        assert drone.age_seconds() < 1.0
    
    def test_drone_to_dict(self):
        """Test drone serialization"""
        pos = Position(42.0, -71.0, 50.0)
        pilot_pos = Position(42.001, -71.001, 5.0)
        
        drone = Drone(
            id="test-drone",
            drone_type=DroneType.REMOTE_ID_WIFI,
            position=pos,
            pilot_position=pilot_pos,
            speed=10.0,
            rssi=-65.0
        )
        
        data = drone.to_dict()
        
        assert data["id"] == "test-drone"
        assert data["drone_type"] == "remote_id_wifi"
        assert "position" in data
        assert data["pilot_position"] is not None
        assert data["speed"] == 10.0
        assert data["rssi"] == -65.0


class TestAircraft:
    """Test Aircraft model"""
    
    def test_aircraft_creation(self):
        """Test basic aircraft creation"""
        pos = Position(42.0, -71.0, 10000.0)
        aircraft = Aircraft(
            hex="a12345",
            position=pos,
            callsign="UAL123",
            speed=450.0,
            heading=280.0
        )
        
        assert aircraft.hex == "a12345"
        assert aircraft.callsign == "UAL123"
        assert aircraft.speed == 450.0
    
    def test_aircraft_update(self):
        """Test aircraft update method"""
        pos = Position(42.0, -71.0, 10000.0)
        aircraft = Aircraft(hex="abc123", position=pos)
        
        original_timestamp = aircraft.last_updated
        
        import time
        time.sleep(0.01)
        
        aircraft.update(callsign="TEST", squawk="7700")
        
        assert aircraft.callsign == "TEST"
        assert aircraft.squawk == "7700"
        assert aircraft.last_updated > original_timestamp
    
    def test_aircraft_on_ground(self):
        """Test on_ground flag"""
        pos = Position(42.0, -71.0, 0.0)
        aircraft = Aircraft(
            hex="ground1",
            position=pos,
            on_ground=True
        )
        
        assert aircraft.on_ground is True
    
    def test_aircraft_to_dict(self):
        """Test aircraft serialization"""
        pos = Position(42.0, -71.0, 5000.0)
        aircraft = Aircraft(
            hex="test123",
            position=pos,
            callsign="TEST",
            category=AircraftCategory.SMALL,
            squawk="1200"
        )
        
        data = aircraft.to_dict()
        
        assert data["hex"] == "test123"
        assert data["callsign"] == "TEST"
        assert data["category"] == AircraftCategory.SMALL.value
        assert data["squawk"] == "1200"


class TestSystemStatus:
    """Test SystemStatus model"""
    
    def test_system_status_creation(self):
        """Test basic system status creation"""
        pos = Position(42.0, -71.0, 5.0)
        status = SystemStatus(
            serial_number="WD-12345",
            position=pos,
            temperature=45.0,
            cpu_usage=35.2
        )
        
        assert status.serial_number == "WD-12345"
        assert status.temperature == 45.0
        assert status.cpu_usage == 35.2
    
    def test_system_status_to_dict(self):
        """Test system status serialization"""
        pos = Position(42.0, -71.0, 5.0)
        status = SystemStatus(
            serial_number="WD-TEST",
            position=pos,
            temperature=50.0,
            cpu_usage=40.0,
            memory_usage=60.0
        )
        
        data = status.to_dict()
        
        assert data["serial_number"] == "WD-TEST"
        assert data["temperature"] == 50.0
        assert data["cpu_usage"] == 40.0
        assert data["memory_usage"] == 60.0
        assert "position" in data
