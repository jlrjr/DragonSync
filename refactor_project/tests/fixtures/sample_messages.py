"""
Sample ZMQ telemetry messages for testing parsers.

Real-world message formats from DJI and ESP32 Remote ID broadcasts.
"""

# DJI/AntSDR Format - List of message dictionaries
SAMPLE_DJI_MESSAGE = [
    {
        "MAC": "12:34:56:78:9A:BC",
        "RSSI": -65,
        "Basic ID": {
            "ua_type": 2,
            "id_type": "Serial Number (ANSI/CTA-2063-A)",
            "id": "DJI-MAVIC-123456",
            "MAC": "12:34:56:78:9A:BC",
            "RSSI": -65
        }
    },
    {
        "Location/Vector Message": {
            "latitude": 42.3601,
            "longitude": -71.0589,
            "speed": 12.5,
            "vert_speed": 2.0,
            "geodetic_altitude": 150.0,
            "height_agl": 100.0,
            "op_status": "AIRBORNE",
            "height_type": "AGL",
            "ew_dir_segment": "WEST",
            "direction": 180,
            "speed_multiplier": "1.0",
            "pressure_altitude": "150.0 m",
            "vertical_accuracy": "3m",
            "horizontal_accuracy": "10m",
            "baro_accuracy": "5m",
            "speed_accuracy": "1m/s",
            "timestamp": "2024-01-15T12:30:00Z",
            "timestamp_accuracy": "0.1s"
        }
    },
    {
        "Self-ID Message": {
            "text": "DJI Mavic 3"
        }
    },
    {
        "System Message": {
            "latitude": 42.3600,
            "longitude": -71.0590,
            "home_lat": 42.3599,
            "home_lon": -71.0591
        }
    },
    {
        "Operator ID Message": {
            "operator_id_type": "CAA",
            "operator_id": "OP-DJI-789"
        }
    },
    {
        "Frequency Message": {
            "frequency": 2437.0
        }
    }
]

# ESP32 BLE Format - Single dictionary
SAMPLE_ESP32_MESSAGE = {
    "index": 42,
    "runtime": 3600,
    "AUX_ADV_IND": {
        "rssi": -70
    },
    "aext": {
        "AdvA": "AA:BB:CC:DD:EE:FF 00:11:22:33:44:55"
    },
    "Basic ID": {
        "ua_type": 2,
        "id_type": "Serial Number (ANSI/CTA-2063-A)",
        "id": "ESP32-DRONE-456",
        "MAC": "AA:BB:CC:DD:EE:FF",
        "RSSI": -70
    },
    "Location/Vector Message": {
        "latitude": 41.9012,
        "longitude": -70.6789,
        "speed": 8.5,
        "vert_speed": -1.5,
        "geodetic_altitude": 200.0,
        "height_agl": 75.0,
        "op_status": "LANDING",
        "height_type": "MSL",
        "ew_dir_segment": "EAST",
        "direction": 90,
        "speed_multiplier": "1.5",
        "pressure_altitude": "200.0",
        "vertical_accuracy": "5m",
        "horizontal_accuracy": "15m",
        "baro_accuracy": "7m",
        "speed_accuracy": "2m/s",
        "timestamp": "2024-01-15T14:45:00Z",
        "timestamp_accuracy": "0.2s"
    },
    "Self-ID Message": {
        "text": "Custom Quadcopter"
    },
    "System Message": {
        "operator_lat": 41.9010,
        "operator_lon": -70.6788
    },
    "Operator ID Message": {
        "operator_id_type": "SERIAL",
        "operator_id": "PILOT-123"
    }
}

# Minimal message - just basics required
SAMPLE_MINIMAL_MESSAGE = [
    {
        "MAC": "FF:EE:DD:CC:BB:AA",
        "RSSI": -80,
        "Basic ID": {
            "ua_type": 4,
            "id_type": "Serial Number (ANSI/CTA-2063-A)",
            "id": "MINIMAL-DRONE-999"
        }
    },
    {
        "Location/Vector Message": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "speed": 5.0,
            "vert_speed": 0.5,
            "geodetic_altitude": 50.0,
            "height_agl": 30.0
        }
    },
    {
        "Self-ID Message": {
            "text": "Test Drone"
        }
    },
    {
        "System Message": {
            "latitude": 40.7127,
            "longitude": -74.0061,
            "home_lat": 0.0,
            "home_lon": 0.0
        }
    }
]

# CAA ID format
SAMPLE_CAA_MESSAGE = [
    {
        "MAC": "11:22:33:44:55:66",
        "RSSI": -75,
        "Basic ID": {
            "ua_type": 2,
            "id_type": "CAA Assigned Registration ID",
            "id": "CAA-UK-54321",
            "MAC": "11:22:33:44:55:66",
            "RSSI": -75
        }
    },
    {
        "Location/Vector Message": {
            "latitude": 51.5074,
            "longitude": -0.1278,
            "speed": 15.0,
            "vert_speed": 3.0,
            "geodetic_altitude": 100.0,
            "height_agl": 80.0
        }
    },
    {
        "Self-ID Message": {
            "text": "UK Registered Drone"
        }
    },
    {
        "System Message": {
            "latitude": 51.5073,
            "longitude": -0.1279,
            "home_lat": 51.5072,
            "home_lon": -0.1280
        }
    }
]

# UA type mapping (from legacy code)
UA_TYPE_MAPPING = {
    0: 'No UA type defined',
    1: 'Aeroplane/Airplane (Fixed wing)',
    2: 'Helicopter or Multirotor',
    3: 'Gyroplane',
    4: 'VTOL (Vertical Take-Off and Landing)',
    5: 'Ornithopter',
    6: 'Glider',
    7: 'Kite',
    8: 'Free Balloon',
    9: 'Captive Balloon',
    10: 'Airship (Blimp)',
    11: 'Free Fall/Parachute',
    12: 'Rocket',
    13: 'Tethered powered aircraft',
    14: 'Ground Obstacle',
    15: 'Other type',
}
