#!/usr/bin/env python3
"""
Simple ZMQ Listener for Testing DragonSync Test Generator

Subscribes to ZMQ telemetry stream and displays received drone detection messages.
Use this to verify test_drone_generator.py is working without running DragonSync.

Usage:
    # Terminal 1: Start this listener
    python3 test_zmq_listener.py

    # Terminal 2: Run test generator
    python3 test_drone_generator.py --mode replay --loop
"""

import argparse
import json
import logging
import signal
import sys
import time
from typing import Dict, Any
import zmq

logger = logging.getLogger(__name__)


class ZmqTestListener:
    """Simple ZMQ subscriber for testing drone message generation."""

    def __init__(self, zmq_host: str = "127.0.0.1", zmq_port: int = 4224, verbose: bool = False):
        """
        Initialize ZMQ test listener.

        Args:
            zmq_host: ZMQ server host to connect to
            zmq_port: ZMQ telemetry port
            verbose: Show full message details
        """
        self.zmq_host = zmq_host
        self.zmq_port = zmq_port
        self.verbose = verbose
        self.running = False
        self.message_count = 0
        self.drone_ids = set()

        # Setup ZMQ subscriber
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://{zmq_host}:{zmq_port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")

        logger.info(f"ZMQ Test Listener connected to tcp://{zmq_host}:{zmq_port}")
        logger.info("Waiting for messages... (Press Ctrl+C to stop)")

    def extract_drone_info(self, message: Any) -> Dict[str, Any]:
        """
        Extract key information from a drone detection message.

        Args:
            message: ZMQ message (list of dicts)

        Returns:
            Dictionary with extracted drone info
        """
        info = {
            "drone_id": None,
            "id_type": None,
            "latitude": None,
            "longitude": None,
            "altitude": None,
            "speed": None,
            "heading": None,
            "frequency": None,
            "rssi": None,
            "mac": None,
            "pilot_lat": None,
            "pilot_lon": None,
            "home_lat": None,
            "home_lon": None,
            "operator_id": None,
            "description": None
        }

        if not isinstance(message, list):
            return info

        for item in message:
            if not isinstance(item, dict):
                continue

            # Basic ID
            if "Basic ID" in item:
                basic = item["Basic ID"]
                info["id_type"] = basic.get("id_type")
                info["drone_id"] = basic.get("id")
                info["mac"] = basic.get("MAC")
                info["rssi"] = basic.get("RSSI")

            # Location/Vector
            if "Location/Vector Message" in item:
                loc = item["Location/Vector Message"]
                info["latitude"] = loc.get("latitude")
                info["longitude"] = loc.get("longitude")
                info["altitude"] = loc.get("geodetic_altitude")
                info["speed"] = loc.get("speed")
                info["heading"] = loc.get("direction")

            # Frequency
            if "Frequency Message" in item:
                freq_msg = item["Frequency Message"]
                freq_hz = freq_msg.get("frequency")
                if freq_hz:
                    info["frequency"] = freq_hz / 1e9  # Convert to GHz for readability

            # Self-ID
            if "Self-ID Message" in item:
                info["description"] = item["Self-ID Message"].get("text")

            # System Message
            if "System Message" in item:
                sys_msg = item["System Message"]
                info["pilot_lat"] = sys_msg.get("latitude")
                info["pilot_lon"] = sys_msg.get("longitude")
                info["home_lat"] = sys_msg.get("home_lat")
                info["home_lon"] = sys_msg.get("home_lon")

            # Operator ID
            if "Operator ID Message" in item:
                op_msg = item["Operator ID Message"]
                info["operator_id"] = op_msg.get("operator_id")

        return info

    def format_summary(self, info: Dict[str, Any]) -> str:
        """
        Format drone info as a readable summary line.

        Args:
            info: Extracted drone information

        Returns:
            Formatted summary string
        """
        parts = []

        # Drone ID
        drone_id = info.get("drone_id", "Unknown")
        parts.append(f"ID: {drone_id}")

        # Position
        lat = info.get("latitude")
        lon = info.get("longitude")
        alt = info.get("altitude")
        if lat and lon:
            parts.append(f"Pos: ({lat:.6f}, {lon:.6f})")
        if alt:
            parts.append(f"Alt: {alt:.1f}m")

        # Speed/Heading
        speed = info.get("speed")
        heading = info.get("heading")
        if speed is not None:
            parts.append(f"Spd: {speed:.1f}m/s")
        if heading is not None:
            parts.append(f"Hdg: {heading}°")

        # Signal
        rssi = info.get("rssi")
        freq = info.get("frequency")
        if rssi is not None:
            parts.append(f"RSSI: {rssi}dBm")
        if freq:
            parts.append(f"Freq: {freq:.3f}GHz")

        # Pilot/Home
        pilot_lat = info.get("pilot_lat")
        pilot_lon = info.get("pilot_lon")
        if pilot_lat and pilot_lon:
            parts.append(f"Pilot: ({pilot_lat:.6f}, {pilot_lon:.6f})")

        home_lat = info.get("home_lat")
        home_lon = info.get("home_lon")
        if home_lat and home_lon:
            parts.append(f"Home: ({home_lat:.6f}, {home_lon:.6f})")

        # Description
        desc = info.get("description")
        if desc:
            parts.append(f'Desc: "{desc}"')

        return " | ".join(parts)

    def run(self):
        """Start listening for messages."""
        self.running = True
        start_time = time.time()

        try:
            while self.running:
                try:
                    # Non-blocking receive with timeout
                    if self.socket.poll(timeout=1000):  # 1 second timeout
                        message = self.socket.recv_json()
                        self.message_count += 1

                        # Extract drone info
                        info = self.extract_drone_info(message)
                        drone_id = info.get("drone_id")

                        if drone_id:
                            self.drone_ids.add(drone_id)

                        # Display message
                        print(f"\n[{self.message_count:04d}] {time.strftime('%H:%M:%S')}")
                        print(f"  {self.format_summary(info)}")

                        if self.verbose:
                            print(f"\n  Full message:")
                            print(f"  {json.dumps(message, indent=4)}")

                except zmq.Again:
                    # Timeout, no message received
                    pass
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to decode JSON message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
            self.print_summary(time.time() - start_time)

    def stop(self):
        """Stop the listener and cleanup."""
        self.running = False
        logger.info("\nStopping listener...")

        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()

    def print_summary(self, elapsed_time: float):
        """Print session summary statistics."""
        print("\n" + "=" * 60)
        print("SESSION SUMMARY")
        print("=" * 60)
        print(f"Duration:        {elapsed_time:.1f} seconds")
        print(f"Messages:        {self.message_count}")
        print(f"Unique Drones:   {len(self.drone_ids)}")

        if self.message_count > 0:
            print(f"Avg Rate:        {self.message_count / elapsed_time:.2f} msg/sec")

        if self.drone_ids:
            print(f"\nDetected Drone IDs:")
            for drone_id in sorted(self.drone_ids):
                print(f"  - {drone_id}")

        print("=" * 60)


def setup_logging(debug: bool):
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ZMQ Test Listener for DragonSync Test Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Listen on default port
  python3 test_zmq_listener.py

  # Listen with verbose output (show full messages)
  python3 test_zmq_listener.py --verbose

  # Connect to remote ZMQ publisher
  python3 test_zmq_listener.py --zmq-host 192.168.1.100

Usage Pattern:
  Terminal 1: python3 test_zmq_listener.py
  Terminal 2: python3 test_drone_generator.py --mode replay --loop
        """
    )

    parser.add_argument(
        "--zmq-host",
        type=str,
        default="127.0.0.1",
        help="ZMQ server host to connect to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--zmq-port",
        type=int,
        default=4224,
        help="ZMQ telemetry port (default: 4224)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full message details (JSON)"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    setup_logging(args.debug)

    # Create and run listener
    listener = ZmqTestListener(
        zmq_host=args.zmq_host,
        zmq_port=args.zmq_port,
        verbose=args.verbose
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received signal, stopping...")
        listener.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start listening
    listener.run()


if __name__ == "__main__":
    main()
