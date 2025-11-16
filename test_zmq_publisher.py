#!/usr/bin/env python3
"""
ZMQ Test Publisher - Simulates drone telemetry streams for testing

This script publishes fake drone telemetry messages over ZMQ to simulate
what real WarDragon hardware would send. Use this for testing parsers
and data pipelines before hardware is available.

Usage:
    # Simple mode - send sample messages on loop
    python3 test_zmq_publisher.py

    # Custom port
    python3 test_zmq_publisher.py --port 5556

    # Simulate multiple drones
    python3 test_zmq_publisher.py --num-drones 5

    # Fast updates (every 0.1s instead of 1s)
    python3 test_zmq_publisher.py --interval 0.1

    # Send only DJI format messages
    python3 test_zmq_publisher.py --format dji

    # Simulate moving drones
    python3 test_zmq_publisher.py --simulate-movement
"""

import zmq
import json
import time
import random
import argparse
import sys
from datetime import datetime

# Sample drone data templates
DJI_DRONE_TEMPLATE = {
    "messages": [
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
}

ESP32_DRONE_TEMPLATE = {
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
    }
}

# Drone types from ASTM F3411 Remote ID spec
UA_TYPES = {
    0: "None/Undeclared",
    1: "Aeroplane",
    2: "Helicopter or Multirotor",
    3: "Gyroplane",
    4: "Hybrid Lift",
    5: "Ornithopter",
    6: "Glider",
    7: "Kite",
    8: "Free Balloon",
    9: "Captive Balloon",
    10: "Airship",
    11: "Free Fall/Parachute",
    12: "Rocket",
    13: "Tethered Powered Aircraft",
    14: "Ground Obstacle",
    15: "Other"
}

class DroneSimulator:
    """Simulates a single drone with realistic movement"""

    def __init__(self, drone_id, lat, lon, alt, format_type="dji"):
        self.drone_id = drone_id
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.format_type = format_type
        self.mac = self._generate_mac()
        self.speed = random.uniform(5.0, 15.0)
        self.heading = random.uniform(0, 360)
        self.vspeed = random.uniform(-2.0, 2.0)
        self.ua_type = random.choice([1, 2, 3, 6])
        self.rssi = random.randint(-85, -50)

    def _generate_mac(self):
        """Generate random MAC address"""
        return ":".join([f"{random.randint(0, 255):02X}" for _ in range(6)])

    def update_position(self, time_delta=1.0):
        """Update drone position simulating movement"""
        # Simple movement model: move in current heading
        # 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 111 km * cos(lat)
        import math

        distance_km = self.speed * time_delta / 1000.0  # speed in m/s
        lat_delta = (distance_km / 111.0) * math.cos(math.radians(self.heading))
        lon_delta = (distance_km / (111.0 * math.cos(math.radians(self.lat)))) * math.sin(math.radians(self.heading))

        self.lat += lat_delta
        self.lon += lon_delta
        self.alt += self.vspeed * time_delta

        # Keep altitude reasonable
        if self.alt > 400:
            self.vspeed = -abs(self.vspeed)
        elif self.alt < 10:
            self.vspeed = abs(self.vspeed)

        # Occasionally change heading
        if random.random() < 0.1:
            self.heading += random.uniform(-30, 30)
            self.heading = self.heading % 360

        # Vary RSSI slightly
        self.rssi += random.randint(-3, 3)
        self.rssi = max(-95, min(-40, self.rssi))

    def generate_message(self):
        """Generate ZMQ message in appropriate format"""
        if self.format_type == "dji":
            return self._generate_dji_message()
        else:
            return self._generate_esp32_message()

    def _generate_dji_message(self):
        """Generate DJI/AntSDR format message (list)"""
        return [
            {
                "MAC": self.mac,
                "RSSI": self.rssi,
                "Basic ID": {
                    "ua_type": self.ua_type,
                    "id_type": "Serial Number (ANSI/CTA-2063-A)",
                    "id": self.drone_id,
                    "MAC": self.mac,
                    "RSSI": self.rssi
                }
            },
            {
                "Location/Vector Message": {
                    "latitude": round(self.lat, 6),
                    "longitude": round(self.lon, 6),
                    "speed": round(self.speed, 1),
                    "vert_speed": round(self.vspeed, 1),
                    "geodetic_altitude": round(self.alt, 1),
                    "height_agl": round(self.alt * 0.7, 1),
                    "op_status": "AIRBORNE",
                    "height_type": "AGL",
                    "direction": int(self.heading),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            },
            {
                "Self-ID Message": {
                    "text": f"Simulated Drone {self.drone_id}"
                }
            },
            {
                "System Message": {
                    "latitude": round(self.lat - 0.001, 6),
                    "longitude": round(self.lon - 0.001, 6),
                    "home_lat": round(self.lat - 0.001, 6),
                    "home_lon": round(self.lon - 0.001, 6)
                }
            }
        ]

    def _generate_esp32_message(self):
        """Generate ESP32 BLE format message (dict)"""
        return {
            "index": random.randint(1, 1000),
            "runtime": int(time.time()),
            "AUX_ADV_IND": {
                "rssi": self.rssi
            },
            "aext": {
                "AdvA": f"{self.mac} 00:11:22:33:44:55"
            },
            "Basic ID": {
                "ua_type": self.ua_type,
                "id_type": "Serial Number (ANSI/CTA-2063-A)",
                "id": self.drone_id,
                "MAC": self.mac,
                "RSSI": self.rssi
            },
            "Location/Vector Message": {
                "latitude": round(self.lat, 6),
                "longitude": round(self.lon, 6),
                "speed": round(self.speed, 1),
                "vert_speed": round(self.vspeed, 1),
                "geodetic_altitude": round(self.alt, 1),
                "height_agl": round(self.alt * 0.7, 1),
                "op_status": "AIRBORNE",
                "direction": int(self.heading),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="ZMQ Test Publisher - Simulate drone telemetry streams"
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='ZMQ bind address (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5555,
        help='ZMQ port (default: 5555)'
    )
    parser.add_argument(
        '--num-drones',
        type=int,
        default=3,
        help='Number of drones to simulate (default: 3)'
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=1.0,
        help='Update interval in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--format',
        choices=['dji', 'esp32', 'mixed'],
        default='mixed',
        help='Message format: dji, esp32, or mixed (default: mixed)'
    )
    parser.add_argument(
        '--simulate-movement',
        action='store_true',
        help='Simulate realistic drone movement'
    )
    parser.add_argument(
        '--random-errors',
        action='store_true',
        help='Occasionally send malformed messages to test error handling'
    )
    parser.add_argument(
        '--lat',
        type=float,
        default=42.3601,
        help='Starting latitude (default: 42.3601 - Boston)'
    )
    parser.add_argument(
        '--lon',
        type=float,
        default=-71.0589,
        help='Starting longitude (default: -71.0589 - Boston)'
    )

    return parser.parse_args()

def main():
    """Main publisher loop"""
    args = parse_args()

    print("🚁 ZMQ Drone Telemetry Publisher")
    print("=" * 70)
    print(f"   Binding to: tcp://{args.host}:{args.port}")
    print(f"   Simulating: {args.num_drones} drone(s)")
    print(f"   Format: {args.format}")
    print(f"   Interval: {args.interval}s")
    print(f"   Movement: {'Yes' if args.simulate_movement else 'No (static)'}")
    print(f"   Random Errors: {'Yes' if args.random_errors else 'No'}")
    print(f"   Starting Position: {args.lat}, {args.lon}")
    print("=" * 70)
    print()
    print("📡 Publishing messages... (Ctrl+C to stop)")
    print()

    # Setup ZMQ publisher
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://{args.host}:{args.port}")

    # Give subscribers time to connect
    time.sleep(0.5)

    # Create simulated drones
    drones = []
    for i in range(args.num_drones):
        # Spread drones around starting position
        lat = args.lat + random.uniform(-0.01, 0.01)
        lon = args.lon + random.uniform(-0.01, 0.01)
        alt = random.uniform(50, 200)

        # Determine format
        if args.format == "mixed":
            format_type = random.choice(["dji", "esp32"])
        else:
            format_type = args.format

        drone_id = f"SIM-DRONE-{i+1:03d}"
        drone = DroneSimulator(drone_id, lat, lon, alt, format_type)
        drones.append(drone)

        print(f"✅ Created: {drone_id} ({format_type.upper()} format) at ({lat:.6f}, {lon:.6f})")

    print()
    print("📤 Publishing telemetry...")
    print()

    message_count = 0
    error_count = 0
    start_time = time.time()

    try:
        while True:
            # Send messages for each drone
            for drone in drones:
                # Update position if movement enabled
                if args.simulate_movement:
                    drone.update_position(args.interval)

                # Generate and send message
                message = drone.generate_message()

                # Occasionally send malformed message if random errors enabled
                if args.random_errors and random.random() < 0.05:
                    message = {"error": "malformed", "data": None}
                    error_count += 1

                # Publish to ZMQ
                socket.send_json(message)
                message_count += 1

                # Print status every 10th message
                if message_count % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = message_count / elapsed if elapsed > 0 else 0
                    print(f"📊 Sent: {message_count} messages ({rate:.1f}/sec) | Errors: {error_count}", end='\r')

            # Wait before next update
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping publisher...")

    finally:
        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print("📊 Final Statistics")
        print("=" * 70)
        print(f"   Runtime: {elapsed:.1f}s")
        print(f"   Messages Sent: {message_count}")
        print(f"   Malformed Messages: {error_count}")
        print(f"   Average Rate: {message_count/elapsed:.1f} messages/sec")
        print(f"   Drones Simulated: {len(drones)}")
        print("=" * 70)

        socket.close()
        context.term()
        print("\n✅ Publisher stopped cleanly")

if __name__ == "__main__":
    main()
