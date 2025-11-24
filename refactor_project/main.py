#!/usr/bin/env python3
"""
DragonSync Refactored - Main Entry Point

This is the main entry point for the refactored DragonSync application.
It wires together all components using dependency injection and runs the
main event loop.

Architecture:
    Input: ZMQ sockets (drone telemetry + system status)
    ↓
    Parsing: DroneParser → Drone objects
    ↓
    Management: DroneManager (state, rate limiting, timeouts)
    ↓
    Messaging: CotGenerator → CoT XML (universal format)
    ↓
    Output: Sinks (TAK, MQTT, Lattice) → Clients (network I/O)

Usage:
    python3 main.py --config config.ini
    python3 main.py --config config.ini --debug
"""

import sys
import signal
import logging
import argparse
import time
import ssl
from typing import List, Optional
from pathlib import Path

import zmq

# Import refactored components
from refactor_project.config.config_loader import ConfigLoader, DragonSyncConfig
from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.managers.drone_manager import DroneManager
from refactor_project.messaging.cot_generator import CotGenerator
from refactor_project.sinks.base_sink import BaseSink
from refactor_project.sinks.tak_sink import TakSink
from refactor_project.sinks.mqtt_sink import MqttSink
from refactor_project.sinks.lattice_sink import LatticeSink
from refactor_project.clients.tak_client import TakClient
from refactor_project.clients.mqtt_client import MqttClient
from refactor_project.clients.lattice_client import LatticeClient
from refactor_project.models.drone import Drone

logger = logging.getLogger(__name__)

# UA Type mapping for Remote ID
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


def setup_logging(debug: bool = False) -> None:
    """Configure logging for the application.

    Args:
        debug: If True, set logging level to DEBUG, otherwise INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_ssl_context(
    p12_path: Optional[str],
    p12_password: Optional[str],
    skip_verify: bool = False
) -> Optional[ssl.SSLContext]:
    """Load SSL context from PKCS#12 certificate file.

    Args:
        p12_path: Path to PKCS#12 (.p12 or .pfx) file.
        p12_password: Password for the PKCS#12 file.
        skip_verify: If True, disable certificate verification (insecure).

    Returns:
        SSL context if TLS is configured, None otherwise.
    """
    if not p12_path:
        return None

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.backends import default_backend

        # Read PKCS#12 file
        with open(p12_path, 'rb') as f:
            p12_data = f.read()

        # Parse PKCS#12
        password = p12_password.encode() if p12_password else None
        private_key, certificate, ca_certs = pkcs12.load_key_and_certificates(
            p12_data, password, default_backend()
        )

        # Create SSL context
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        if skip_verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            logger.warning("TLS certificate verification disabled (insecure)")

        # TODO: Load cert chain into context
        # This requires converting cryptography objects to PEM and loading
        # For now, return basic context
        logger.info(f"Loaded SSL context from {p12_path}")
        return context

    except Exception as e:
        logger.error(f"Failed to load SSL context: {e}")
        return None


def initialize_clients(config: DragonSyncConfig) -> dict:
    """Initialize network clients based on configuration.

    Args:
        config: DragonSync configuration.

    Returns:
        Dictionary of initialized clients {'tak': TakClient, 'mqtt': MqttClient, ...}
    """
    clients = {}

    # TAK Client (TCP/TLS)
    if config.tak.host and config.tak.port:
        ssl_context = load_ssl_context(
            config.tak.tls_p12,
            config.tak.tls_p12_pass,
            config.tak.tls_skip_verify
        )

        tak_client = TakClient(
            host=config.tak.host,
            port=config.tak.port,
            ssl_context=ssl_context
        )

        try:
            tak_client.connect()
            clients['tak'] = tak_client
            logger.info(f"Connected to TAK server at {config.tak.host}:{config.tak.port}")
        except Exception as e:
            logger.error(f"Failed to connect to TAK server: {e}")

    # MQTT Client
    if config.mqtt.enabled and config.mqtt.host:
        mqtt_client = MqttClient(
            host=config.mqtt.host,
            port=config.mqtt.port or 1883,
            username=config.mqtt.username,
            password=config.mqtt.password,
            tls_enabled=config.mqtt.tls or False,
            ca_file=config.mqtt.ca_file
        )

        try:
            mqtt_client.connect()
            clients['mqtt'] = mqtt_client
            logger.info(f"Connected to MQTT broker at {config.mqtt.host}:{config.mqtt.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

    # Lattice Client
    if config.lattice.enabled and config.lattice.token:
        lattice_client = LatticeClient(
            token=config.lattice.token,
            base_url=config.lattice.base_url,
            sandbox_token=config.lattice.sandbox_token
        )

        clients['lattice'] = lattice_client
        logger.info("Initialized Lattice client")

    return clients


def initialize_sinks(clients: dict, config: DragonSyncConfig) -> List[BaseSink]:
    """Initialize output sinks with client dependencies.

    Args:
        clients: Dictionary of initialized clients.
        config: DragonSync configuration.

    Returns:
        List of initialized sinks.
    """
    sinks = []

    # TAK Sink
    if 'tak' in clients:
        tak_sink = TakSink(client=clients['tak'])
        sinks.append(tak_sink)
        logger.info("Initialized TAK sink")

    # MQTT Sink
    if 'mqtt' in clients and config.mqtt.enabled:
        mqtt_sink = MqttSink(
            client=clients['mqtt'],
            topic_prefix=config.mqtt.topic or "wardragon/drones"
        )
        sinks.append(mqtt_sink)
        logger.info("Initialized MQTT sink")

    # Lattice Sink
    if 'lattice' in clients and config.lattice.enabled:
        lattice_sink = LatticeSink(client=clients['lattice'])
        sinks.append(lattice_sink)
        logger.info("Initialized Lattice sink")

    return sinks


class DragonSyncApp:
    """Main DragonSync application orchestrator."""

    def __init__(self, config: DragonSyncConfig):
        """Initialize DragonSync application.

        Args:
            config: DragonSync configuration.
        """
        self.config = config
        self.running = False

        # Components (initialized in setup())
        self.parser: Optional[DroneParser] = None
        self.manager: Optional[DroneManager] = None
        self.cot_generator: Optional[CotGenerator] = None
        self.sinks: List[BaseSink] = []
        self.clients: dict = {}

        # ZMQ components
        self.zmq_context: Optional[zmq.Context] = None
        self.telemetry_socket: Optional[zmq.Socket] = None
        self.status_socket: Optional[zmq.Socket] = None

        # Rate limiting for drone updates
        self.rate_limit = config.rate_limit or 3.0
        self.last_sent: dict[str, float] = {}  # drone_id -> last_sent_time

        # Movement threshold for updates (in meters)
        self.movement_threshold = 10.0  # meters

    def setup(self) -> None:
        """Initialize all components with dependency injection."""
        logger.info("Setting up DragonSync components...")

        # Initialize clients
        self.clients = initialize_clients(self.config)

        # Initialize sinks (depends on clients)
        self.sinks = initialize_sinks(self.clients, self.config)

        if not self.sinks:
            logger.warning("No sinks initialized - CoT messages will not be sent")

        # Initialize parser
        self.parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
        logger.info("Initialized drone parser")

        # Initialize CoT generator
        self.cot_generator = CotGenerator(
            default_stale_seconds=300.0,  # 5 minutes
            use_modern_types=True
        )
        logger.info("Initialized CoT generator")

        # Initialize drone manager
        max_drones = self.config.max_drones or 30
        self.manager = DroneManager(max_drones=max_drones)
        logger.info(f"Initialized drone manager (max: {max_drones} drones)")

        # Initialize ZMQ sockets
        self.setup_zmq()

        logger.info("DragonSync setup complete")

    def setup_zmq(self) -> None:
        """Set up ZMQ sockets for telemetry and status."""
        self.zmq_context = zmq.Context()

        # Telemetry socket (port 4224)
        zmq_host = self.config.zmq.host or "127.0.0.1"
        zmq_port = self.config.zmq.port or 4224

        self.telemetry_socket = self.zmq_context.socket(zmq.SUB)
        self.telemetry_socket.connect(f"tcp://{zmq_host}:{zmq_port}")
        self.telemetry_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"Connected to telemetry ZMQ at tcp://{zmq_host}:{zmq_port}")

        # Status socket (port 4225) - optional
        if self.config.zmq.status_port:
            self.status_socket = self.zmq_context.socket(zmq.SUB)
            self.status_socket.connect(f"tcp://{zmq_host}:{self.config.zmq.status_port}")
            self.status_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Connected to status ZMQ at tcp://{zmq_host}:{self.config.zmq.status_port}")

    def should_send_update(self, drone: Drone) -> bool:
        """Check if drone update should be sent based on rate limiting and movement.

        Args:
            drone: Drone to check.

        Returns:
            True if update should be sent.
        """
        now = time.time()
        drone_id = drone.id

        # Check rate limiting
        if drone_id in self.last_sent:
            elapsed = now - self.last_sent[drone_id]
            if elapsed < self.rate_limit:
                return False

        # Check movement threshold (if we have previous position)
        if drone.prev_lat and drone.prev_lon:
            import math
            # Simple distance calculation (approximation)
            lat_diff = (drone.lat - drone.prev_lat) * 111320  # meters per degree
            lon_diff = (drone.lon - drone.prev_lon) * 111320 * math.cos(math.radians(drone.lat))
            distance = math.sqrt(lat_diff**2 + lon_diff**2)

            if distance < self.movement_threshold and elapsed < self.rate_limit * 2:
                return False

        return True

    def process_telemetry_message(self, message_data: bytes) -> None:
        """Process a telemetry message from ZMQ.

        Args:
            message_data: Raw ZMQ message data.
        """
        try:
            # Decode JSON message
            import json
            try:
                message = json.loads(message_data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Failed to decode ZMQ message: {e}")
                return

            # Parse message to Drone object
            drone = self.parser.parse(message)
            if not drone:
                return

            # Update drone manager
            self.manager.add_or_update(drone)

            # Check if we should send update
            if not self.should_send_update(drone):
                return

            # Record send time
            self.last_sent[drone.id] = time.time()

            # Generate CoT XML
            cot_xml = self.cot_generator.generate_drone_event(drone)

            # Publish to all sinks
            for sink in self.sinks:
                try:
                    sink.publish_cot_event(cot_xml)
                except Exception as e:
                    logger.error(f"Failed to publish to {sink.__class__.__name__}: {e}")

            logger.debug(f"Processed drone {drone.id} ({drone.description or 'Unknown'})")

        except Exception as e:
            logger.error(f"Error processing telemetry message: {e}", exc_info=True)

    def cleanup_stale_drones(self) -> None:
        """Remove stale drones based on inactivity timeout."""
        timeout = self.config.inactivity_timeout or 60.0
        stale_drone_ids = self.manager.get_stale_drones(timeout)

        for drone_id in stale_drone_ids:
            # Mark inactive in sinks
            for sink in self.sinks:
                try:
                    sink.mark_inactive(drone_id)
                except Exception as e:
                    logger.error(f"Failed to mark drone {drone_id} inactive: {e}")

            # Remove from manager
            self.manager.remove(drone_id)
            logger.info(f"Removed stale drone: {drone_id}")

    def run(self) -> None:
        """Run the main event loop."""
        logger.info("Starting DragonSync main event loop...")
        self.running = True

        last_cleanup = time.time()
        cleanup_interval = 10.0  # seconds

        try:
            while self.running:
                # Check for telemetry messages (non-blocking)
                try:
                    message = self.telemetry_socket.recv(flags=zmq.NOBLOCK)
                    self.process_telemetry_message(message)
                except zmq.Again:
                    # No message available
                    pass

                # Periodic cleanup of stale drones
                now = time.time()
                if now - last_cleanup > cleanup_interval:
                    self.cleanup_stale_drones()
                    last_cleanup = now

                # Small sleep to prevent CPU spinning
                time.sleep(0.01)

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Gracefully shutdown all components."""
        logger.info("Shutting down DragonSync...")
        self.running = False

        # Close ZMQ sockets
        if self.telemetry_socket:
            self.telemetry_socket.close()
        if self.status_socket:
            self.status_socket.close()
        if self.zmq_context:
            self.zmq_context.term()

        # Close sinks
        for sink in self.sinks:
            try:
                sink.close()
            except Exception as e:
                logger.error(f"Error closing sink: {e}")

        # Close clients
        for name, client in self.clients.items():
            try:
                client.close()
                logger.info(f"Closed {name} client")
            except Exception as e:
                logger.error(f"Error closing {name} client: {e}")

        logger.info("DragonSync shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DragonSync - Drone detection gateway for TAK servers"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.ini',
        help='Path to configuration file (default: config.ini)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(debug=args.debug)

    logger.info("=" * 60)
    logger.info("DragonSync Refactored v2.0.0")
    logger.info("=" * 60)

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        config = ConfigLoader.load(str(config_path))
        logger.info(f"Loaded configuration from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Validate configuration
    errors = ConfigLoader.validate(config)
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Initialize and run application
    app = DragonSyncApp(config)

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        app.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Setup and run
    app.setup()
    app.run()


if __name__ == '__main__':
    main()
