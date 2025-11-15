"""
Pytest configuration and shared fixtures

This file contains pytest fixtures that are available to all tests.
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, MagicMock


@pytest.fixture
def sample_drone_data() -> Dict[str, Any]:
    """Sample drone telemetry data for testing."""
    return {
        "id": "TEST-DRONE-123",
        "lat": 42.3601,
        "lon": -71.0589,
        "alt": 150.0,
        "height": 100.0,
        "speed": 12.5,
        "vspeed": 2.0,
        "pilot_lat": 42.3600,
        "pilot_lon": -71.0590,
        "home_lat": 42.3600,
        "home_lon": -71.0590,
        "description": "Test Drone",
        "mac": "AA:BB:CC:DD:EE:FF",
        "rssi": -65,
        "ua_type": 2,
        "ua_type_name": "Multirotor",
    }


@pytest.fixture
def sample_zmq_message() -> Dict[str, Any]:
    """Sample ZMQ message as received from drone detector."""
    return {
        "BasicID": {
            "UAID": "TEST-DRONE-123",
            "UAType": 2,
            "IDType": 3
        },
        "LocationVector": {
            "Latitude": 42.3601,
            "Longitude": -71.0589,
            "GeodeticAltitude": 150.0,
            "Height": 100.0,
            "Speed": 12.5,
            "VertSpeed": 2.0,
            "Direction": 180
        },
        "System": {
            "OperatorLatitude": 42.3600,
            "OperatorLongitude": -71.0590,
            "AreaCount": 1,
            "AreaRadius": 100,
            "Classification": 1
        },
        "SelfID": {
            "Description": "Test Drone"
        },
        "OperatorID": {
            "OperatorID": "OPERATOR-123",
            "OperatorIDType": 0
        },
        "MAC": "AA:BB:CC:DD:EE:FF",
        "RSSI": -65,
        "freq": 2437
    }


@pytest.fixture
def mock_cot_messenger() -> Mock:
    """Mock CotMessenger for testing."""
    messenger = Mock()
    messenger.send_cot = Mock(return_value=True)
    return messenger


@pytest.fixture
def mock_sink() -> Mock:
    """Mock sink for testing."""
    sink = Mock()
    sink.publish_drone = Mock()
    sink.publish_pilot = Mock()
    sink.publish_home = Mock()
    sink.mark_inactive = Mock()
    sink.close = Mock()
    return sink


@pytest.fixture
def mock_tak_client() -> Mock:
    """Mock TAK client for testing."""
    client = Mock()
    client.send_cot = Mock(return_value=True)
    client.is_connected = Mock(return_value=True)
    client.close = Mock()
    return client


@pytest.fixture
def mock_mqtt_client() -> Mock:
    """Mock MQTT client for testing."""
    client = Mock()
    client.publish = Mock()
    client.is_connected = Mock(return_value=True)
    client.subscribe = Mock()
    client.close = Mock()
    return client


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "SETTINGS": {
            "zmq_host": "127.0.0.1",
            "zmq_port": "4224",
            "zmq_status_port": "4225",
            "rate_limit": "3.0",
            "max_drones": "30",
            "inactivity_timeout": "60.0",
            "enable_multicast": "true",
            "tak_multicast_addr": "239.2.3.1",
            "tak_multicast_port": "6969",
            "mqtt_enabled": "false",
            "lattice_enabled": "false",
        }
    }


# Test helper functions

def assert_valid_cot_xml(xml_string: str) -> None:
    """Assert that a string is valid CoT XML."""
    assert xml_string.startswith("<?xml")
    assert "<event" in xml_string
    assert "</event>" in xml_string
    assert "version=\"2.0\"" in xml_string


def create_test_drone(**kwargs):
    """
    Helper to create a test Drone instance.

    This will be updated once we have the Drone model refactored.
    """
    # Placeholder - will be implemented when Drone model is ready
    pass
