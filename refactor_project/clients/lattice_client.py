"""Lattice Client for publishing entities to Anduril Lattice platform.

This client wraps the Anduril SDK to provide a simple interface for publishing
drone telemetry and entity data to the Lattice Common Operating Picture (COP).
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Lattice will be imported at connect time to support mocking
Lattice = None  # type: ignore


class LatticeClient:
    """Client for connecting to Anduril Lattice and publishing entities.

    Wraps the Anduril SDK to provide entity publishing capabilities
    for the Lattice Common Operating Picture platform.

    Example:
        # Basic usage
        client = LatticeClient(token='your-token')
        client.connect()
        client.publish_entity(
            entity_id='drone-123',
            latitude=37.7,
            longitude=-122.4,
            altitude=100.0
        )
        client.close()

        # With context manager
        with LatticeClient(token='your-token') as client:
            client.publish_entity(entity_id='drone-1', latitude=0, longitude=0)
    """

    def __init__(
        self,
        token: str,
        base_url: Optional[str] = None,
        sandbox_token: Optional[str] = None
    ):
        """Initialize Lattice client.

        Args:
            token: Lattice API authentication token.
            base_url: Optional custom Lattice API base URL.
            sandbox_token: Optional sandbox authorization token.
        """
        self.token = token
        self.base_url = base_url
        self.sandbox_token = sandbox_token
        self._client: Optional[Any] = None

    def connect(self) -> None:
        """Connect to Lattice platform.

        Creates the Anduril SDK Lattice client instance.

        Raises:
            RuntimeError: If Anduril SDK is not installed or connection fails.
        """
        global Lattice

        logger.debug("Connecting to Lattice platform")

        try:
            # Try to import Lattice if not already available (allows mocking in tests)
            if Lattice is None:
                try:
                    from anduril import Lattice as LatticeSDK
                    Lattice = LatticeSDK
                except ImportError as e:
                    raise RuntimeError(
                        "Anduril SDK not available. Install with: pip install anduril"
                    ) from e

            # Build kwargs for Lattice client
            kwargs = {'token': self.token}

            if self.base_url:
                kwargs['base_url'] = self.base_url

            if self.sandbox_token:
                kwargs['headers'] = {
                    'anduril-sandbox-authorization': f'Bearer {self.sandbox_token}'
                }

            # Create Lattice SDK client
            self._client = Lattice(**kwargs)

            logger.info("Connected to Lattice platform")

        except RuntimeError:
            # Re-raise RuntimeError (SDK not available)
            raise
        except ImportError as e:
            # Handle ImportError from Lattice instantiation
            raise RuntimeError(
                "Anduril SDK not available. Install with: pip install anduril"
            ) from e
        except Exception as e:
            logger.error(f"Failed to connect to Lattice: {e}")
            raise

    def publish_entity(self, **entity_data: Any) -> None:
        """Publish entity to Lattice platform.

        Args:
            **entity_data: Entity data fields (entity_id, latitude, longitude, etc.)

        Raises:
            RuntimeError: If not connected to Lattice.
            Exception: If publish fails.
        """
        if not self._client:
            raise RuntimeError("Not connected to Lattice API")

        logger.debug(f"Publishing entity: {entity_data.get('entity_id', 'unknown')}")

        try:
            self._client.entities.publish_entity(**entity_data)
            logger.debug(f"Published entity {entity_data.get('entity_id')}")
        except Exception as e:
            logger.error(f"Failed to publish entity: {e}")
            raise

    def expire_entity(self, entity_id: str) -> None:
        """Expire (remove) entity from Lattice platform.

        Args:
            entity_id: Unique identifier of the entity to expire.

        Raises:
            RuntimeError: If not connected to Lattice.
            Exception: If expire fails.
        """
        if not self._client:
            raise RuntimeError("Not connected to Lattice API")

        logger.debug(f"Expiring entity: {entity_id}")

        try:
            self._client.entities.expire_entity(entity_id=entity_id)
            logger.debug(f"Expired entity {entity_id}")
        except Exception as e:
            logger.error(f"Failed to expire entity: {e}")
            raise

    def close(self) -> None:
        """Close the Lattice client connection.

        Safe to call multiple times or when not connected.
        """
        if self._client:
            try:
                logger.debug("Closing Lattice client")
                # Anduril SDK doesn't require explicit close
                # Just clear the reference
            except Exception as e:
                logger.warning(f"Error closing Lattice client: {e}")
            finally:
                self._client = None

    def is_connected(self) -> bool:
        """Check if currently connected to Lattice.

        Returns:
            True if connected, False otherwise.
        """
        return self._client is not None

    def __enter__(self):
        """Context manager entry - auto-connect."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto-close."""
        self.close()
        return False  # Don't suppress exceptions
