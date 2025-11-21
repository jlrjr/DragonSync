"""MQTT Client for publishing messages to MQTT brokers.

This client wraps paho-mqtt to provide a simple interface for publishing
drone telemetry and other data to MQTT brokers, particularly for Home Assistant
integration via MQTT device trackers.
"""

import logging
import uuid
from typing import Optional
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MqttClient:
    """Client for connecting to MQTT broker and publishing messages.

    Supports authentication, TLS, QoS levels, and message retention.
    Designed for Home Assistant integration and general MQTT publishing.

    Example:
        # Basic usage
        client = MqttClient('127.0.0.1', 1883)
        client.connect()
        client.publish('dragonsync/drone1', '{"lat": 37.7, "lon": -122.4}')
        client.close()

        # With authentication and TLS
        client = MqttClient(
            '127.0.0.1', 8883,
            username='user', password='pass',
            use_tls=True, ca_certs='/path/to/ca.pem'
        )
        with client:
            client.publish('topic', 'payload', qos=1, retain=True)
    """

    def __init__(
        self,
        host: str,
        port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        ca_certs: Optional[str] = None,
        keepalive: int = 60
    ):
        """Initialize MQTT client.

        Args:
            host: MQTT broker hostname or IP address.
            port: MQTT broker port (1883 for plain, 8883 for TLS typically).
            client_id: Optional client ID (auto-generated if not provided).
            username: Optional username for authentication.
            password: Optional password for authentication.
            use_tls: Whether to use TLS/SSL.
            ca_certs: Path to CA certificates file for TLS.
            keepalive: Keepalive interval in seconds.
        """
        self.host = host
        self.port = port
        self.client_id = client_id or f"dragonsync-{uuid.uuid4().hex[:8]}"
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.ca_certs = ca_certs
        self.keepalive = keepalive
        self._client: Optional[mqtt.Client] = None
        self._connected = False

    def connect(self) -> None:
        """Connect to MQTT broker.

        Raises:
            ConnectionRefusedError: If connection is refused.
            Exception: For other connection errors.
        """
        logger.debug(f"Connecting to MQTT broker at {self.host}:{self.port}")

        # Create MQTT client instance
        self._client = mqtt.Client(client_id=self.client_id)

        # Set authentication if provided
        if self.username and self.password:
            logger.debug(f"Setting MQTT authentication for user: {self.username}")
            self._client.username_pw_set(self.username, self.password)

        # Configure TLS if enabled
        if self.use_tls:
            logger.debug("Configuring MQTT TLS")
            self._client.tls_set(ca_certs=self.ca_certs)

        # Connect to broker
        self._client.connect(self.host, self.port, self.keepalive)
        self._connected = True

        logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False
    ) -> None:
        """Publish message to MQTT topic.

        Args:
            topic: MQTT topic to publish to.
            payload: Message payload (string).
            qos: Quality of Service level (0, 1, or 2).
            retain: Whether to retain the message on the broker.

        Raises:
            RuntimeError: If not connected to broker.
        """
        if not self._client or not self._connected:
            raise RuntimeError("Not connected to MQTT broker")

        logger.debug(f"Publishing to topic '{topic}': {len(payload)} bytes")
        self._client.publish(topic, payload, qos=qos, retain=retain)
        logger.debug(f"Published to '{topic}' (QoS={qos}, retain={retain})")

    def close(self) -> None:
        """Disconnect from MQTT broker.

        Safe to call multiple times or when not connected.
        """
        if self._client and self._connected:
            try:
                logger.debug("Disconnecting from MQTT broker")
                self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting from MQTT broker: {e}")
            finally:
                self._connected = False
                self._client = None

    def is_connected(self) -> bool:
        """Check if currently connected to MQTT broker.

        Returns:
            True if connected, False otherwise.
        """
        return self._connected

    def __enter__(self):
        """Context manager entry - auto-connect."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto-close."""
        self.close()
        return False  # Don't suppress exceptions
