"""
FAA Remote ID lookup client.

Wraps the faa-rid-lookup library for dependency injection and testability.
Provides both local database and optional API fallback lookups.

MIT License
Copyright (c) 2025 DragonSync Contributors
"""

import logging
from typing import Optional, Protocol, Dict, Any

logger = logging.getLogger(__name__)

# Try to import the FAA RID lookup library
try:
    import sys
    import os
    # Add faa-rid-lookup to path
    rid_lookup_path = os.path.join(os.path.dirname(__file__), "../../faa-rid-lookup")
    if os.path.exists(rid_lookup_path):
        sys.path.insert(0, rid_lookup_path)

    from drone_serial_lookup import lookup_serial  # type: ignore
    FAA_LOOKUP_AVAILABLE = True
except (ImportError, FileNotFoundError) as e:
    logger.info("FAA RID lookup not available: %s", e)
    lookup_serial = None  # type: ignore
    FAA_LOOKUP_AVAILABLE = False


class RidClient(Protocol):
    """
    Protocol for FAA Remote ID lookup clients.

    This protocol defines the interface for RID lookups, allowing
    for dependency injection and easy mocking in tests.
    """

    def lookup(self, serial_number: str, use_api_fallback: bool = False) -> Dict[str, Any]:
        """
        Look up drone information by serial number.

        Args:
            serial_number: The drone serial number to look up
            use_api_fallback: Whether to use FAA API fallback if not found locally

        Returns:
            Dictionary containing:
                - found (bool): Whether the lookup succeeded
                - make (str): Manufacturer name (if found)
                - model (str): Model name (if found)
                - source (str): Source of data ('local', 'api', etc.)
                - rid_tracking (str): RID tracking number (if available)
                - status (str): RID status (if available)
        """
        ...

    def is_available(self) -> bool:
        """Check if RID lookup is available."""
        ...


class FaaRidClient:
    """
    Client for FAA Remote ID database lookups.

    Wraps the faa-rid-lookup library and provides a clean interface
    for drone serial number lookups. Supports both local database
    lookups and optional API fallback.

    Example:
        >>> client = FaaRidClient()
        >>> if client.is_available():
        ...     result = client.lookup("1581F12345678900")
        ...     if result['found']:
        ...         print(f"Make: {result['make']}, Model: {result['model']}")
    """

    def __init__(self):
        """Initialize the FAA RID client."""
        self.available = FAA_LOOKUP_AVAILABLE
        if not self.available:
            logger.warning("FAA RID lookup library not available")

    def is_available(self) -> bool:
        """
        Check if RID lookup is available.

        Returns:
            True if the faa-rid-lookup library is loaded and functional
        """
        return self.available

    def lookup(self, serial_number: str, use_api_fallback: bool = False) -> Dict[str, Any]:
        """
        Look up drone information by serial number.

        First tries the local FAA database. If not found and use_api_fallback
        is True, falls back to the FAA API (requires network).

        Args:
            serial_number: The drone serial number (e.g., "1581F12345678900")
            use_api_fallback: If True, query FAA API when not found locally

        Returns:
            Dictionary with lookup results:
                - found (bool): Whether the lookup succeeded
                - make (str): Manufacturer (e.g., "DJI")
                - model (str): Model (e.g., "Mavic 3")
                - source (str): 'local' or 'api'
                - rid_tracking (str): Optional tracking number
                - status (str): Optional registration status

        Example:
            >>> client = FaaRidClient()
            >>> result = client.lookup("1581F12345678900", use_api_fallback=False)
            >>> if result['found']:
            ...     print(f"{result['make']} {result['model']}")
        """
        if not self.available or not lookup_serial:
            return {
                "found": False,
                "error": "RID lookup not available"
            }

        if not serial_number:
            return {
                "found": False,
                "error": "Empty serial number"
            }

        try:
            # Call the faa-rid-lookup library
            result = lookup_serial(
                serial_number,
                use_api_fallback=use_api_fallback,
                add_to_db=use_api_fallback  # Add API results to local DB
            )

            # Normalize the result format
            if result and result.get("found"):
                return {
                    "found": True,
                    "make": result.get("make"),
                    "model": result.get("model"),
                    "source": result.get("source", "local"),
                    "rid_tracking": result.get("rid_tracking"),
                    "status": result.get("status"),
                }
            else:
                return {
                    "found": False,
                    "serial": serial_number
                }

        except FileNotFoundError as e:
            logger.debug("RID database file not found: %s", e)
            return {
                "found": False,
                "error": "Database not found"
            }
        except Exception as e:
            logger.error("RID lookup error for %s: %s", serial_number, e, exc_info=True)
            return {
                "found": False,
                "error": str(e)
            }

    def close(self) -> None:
        """Close the RID client (cleanup resources)."""
        # No resources to clean up for this client
        pass


class MockRidClient:
    """
    Mock RID client for testing.

    Returns predefined results based on serial number patterns.
    Useful for testing without requiring the actual FAA database.

    Example:
        >>> client = MockRidClient()
        >>> client.set_result("TEST123", {"found": True, "make": "DJI", "model": "Mini 2"})
        >>> result = client.lookup("TEST123")
        >>> assert result['make'] == "DJI"
    """

    def __init__(self):
        """Initialize the mock client with some default results."""
        self._results: Dict[str, Dict[str, Any]] = {
            # Default test data
            "DJI-TEST": {
                "found": True,
                "make": "DJI",
                "model": "Mavic 3",
                "source": "local"
            },
            "AUTEL-TEST": {
                "found": True,
                "make": "Autel",
                "model": "EVO II",
                "source": "local"
            },
        }

    def is_available(self) -> bool:
        """Mock client is always available."""
        return True

    def lookup(self, serial_number: str, use_api_fallback: bool = False) -> Dict[str, Any]:
        """
        Look up from mock data.

        Args:
            serial_number: Serial to look up
            use_api_fallback: Ignored in mock

        Returns:
            Predefined result or not found
        """
        result = self._results.get(serial_number, {"found": False})
        if use_api_fallback and not result.get("found"):
            # Simulate API fallback for certain patterns
            if "API" in serial_number:
                return {
                    "found": True,
                    "make": "Generic",
                    "model": "API Drone",
                    "source": "api"
                }
        return result.copy()

    def set_result(self, serial_number: str, result: Dict[str, Any]) -> None:
        """
        Set a mock result for a serial number.

        Args:
            serial_number: The serial to mock
            result: The result dictionary to return
        """
        self._results[serial_number] = result

    def close(self) -> None:
        """Close the mock client."""
        pass
