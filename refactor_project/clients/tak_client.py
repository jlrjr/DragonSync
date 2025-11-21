"""TAK TCP/TLS Client for sending CoT messages.

This client handles TCP/TLS connections to TAK servers with support for:
- Plain TCP (port 8087 typically)
- TLS/SSL with client certificates (port 8089 typically)
- Reconnection with exponential backoff
- Context manager for automatic cleanup
"""

import socket
import ssl
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TakClient:
    """Client for connecting to TAK server via TCP/TLS and sending CoT messages.

    Supports both plain TCP and TLS/SSL connections. For TLS, provide an ssl.SSLContext
    configured with client certificates if required by the server.

    Example:
        # Plain TCP
        client = TakClient('10.0.0.112', 8087)
        client.connect()
        client.send(cot_xml)
        client.close()

        # TLS with context manager
        context = ssl.create_default_context()
        context.load_cert_chain('client.pem', 'client-key.pem')
        with TakClient('10.0.0.112', 8089, ssl_context=context) as client:
            client.send(cot_xml)
    """

    def __init__(
        self,
        host: str,
        port: int,
        ssl_context: Optional[ssl.SSLContext] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 10.0
    ):
        """Initialize TAK client.

        Args:
            host: TAK server hostname or IP address.
            port: TAK server port (8087 for TCP, 8089 for TLS typically).
            ssl_context: Optional SSL context for TLS connections.
            max_retries: Maximum connection retry attempts.
            retry_delay: Initial delay between retries in seconds.
            timeout: Connection timeout in seconds.
        """
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish connection to TAK server.

        Raises:
            socket.timeout: If connection times out.
            ConnectionRefusedError: If connection is refused.
            OSError: For other connection errors.
        """
        logger.debug(f"Connecting to TAK server at {self.host}:{self.port}")

        # Create TCP connection
        self.sock = socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout
        )

        # Wrap with TLS if context provided
        if self.ssl_context:
            logger.debug("Wrapping socket with TLS")
            self.sock = self.ssl_context.wrap_socket(
                self.sock,
                server_hostname=self.host
            )

        logger.info(f"Connected to TAK server at {self.host}:{self.port}")

    def connect_with_retry(self) -> None:
        """Connect with retry logic and exponential backoff.

        Raises:
            ConnectionRefusedError: If all retry attempts fail.
            socket.timeout: If connection times out after all retries.
        """
        last_error = None
        delay = self.retry_delay

        for attempt in range(1, self.max_retries + 1):
            try:
                self.connect()
                logger.info(f"Connected on attempt {attempt}")
                return
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                last_error = e
                logger.warning(
                    f"Connection attempt {attempt}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries:
                    logger.debug(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        # All retries exhausted
        logger.error(f"Failed to connect after {self.max_retries} attempts")
        raise last_error

    def send(self, cot_xml: bytes) -> None:
        """Send CoT XML message to TAK server.

        Args:
            cot_xml: CoT XML message as bytes.

        Raises:
            RuntimeError: If not connected.
            BrokenPipeError: If connection is broken.
            OSError: For other send errors.
        """
        if not self.sock:
            raise RuntimeError("Not connected to TAK server")

        logger.debug(f"Sending {len(cot_xml)} bytes to TAK server")
        self.sock.sendall(cot_xml)
        logger.debug("CoT message sent successfully")

    def close(self) -> None:
        """Close connection to TAK server.

        Safe to call multiple times or when not connected.
        """
        if self.sock:
            try:
                logger.debug("Closing TAK server connection")
                self.sock.close()
            except OSError as e:
                logger.warning(f"Error closing socket: {e}")
            finally:
                self.sock = None

    def is_connected(self) -> bool:
        """Check if currently connected to TAK server.

        Returns:
            True if connected, False otherwise.
        """
        return self.sock is not None

    def __enter__(self):
        """Context manager entry - auto-connect."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto-close."""
        self.close()
        return False  # Don't suppress exceptions
