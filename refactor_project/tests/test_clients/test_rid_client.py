"""
Unit tests for the FAA RID client.

Tests the RID client wrapper and mock client functionality.
"""

import pytest

# Import directly from module to avoid __init__.py dependencies
from refactor_project.clients.rid_client import FaaRidClient, MockRidClient, RidClient


class TestMockRidClient:
    """Test the MockRidClient for testing purposes."""

    def test_mock_client_is_available(self):
        """Test that mock client is always available."""
        client = MockRidClient()
        assert client.is_available() is True

    def test_mock_client_predefined_results(self):
        """Test mock client returns predefined results."""
        client = MockRidClient()

        # Test DJI predefined result
        result = client.lookup("DJI-TEST")
        assert result["found"] is True
        assert result["make"] == "DJI"
        assert result["model"] == "Mavic 3"
        assert result["source"] == "local"

        # Test Autel predefined result
        result = client.lookup("AUTEL-TEST")
        assert result["found"] is True
        assert result["make"] == "Autel"
        assert result["model"] == "EVO II"

    def test_mock_client_not_found(self):
        """Test mock client returns not found for unknown serials."""
        client = MockRidClient()
        result = client.lookup("UNKNOWN-SERIAL")
        assert result["found"] is False

    def test_mock_client_set_result(self):
        """Test setting custom mock results."""
        client = MockRidClient()

        custom_result = {
            "found": True,
            "make": "Parrot",
            "model": "Anafi",
            "source": "local"
        }

        client.set_result("CUSTOM-123", custom_result)
        result = client.lookup("CUSTOM-123")

        assert result["found"] is True
        assert result["make"] == "Parrot"
        assert result["model"] == "Anafi"

    def test_mock_client_api_fallback_simulation(self):
        """Test mock client simulates API fallback for certain patterns."""
        client = MockRidClient()

        # Simulate API fallback for serial with "API" in it
        result = client.lookup("API-TEST-12345", use_api_fallback=True)
        assert result["found"] is True
        assert result["source"] == "api"
        assert result["make"] == "Generic"

    def test_mock_client_close(self):
        """Test mock client can be closed without error."""
        client = MockRidClient()
        client.close()  # Should not raise

    def test_mock_client_multiple_lookups(self):
        """Test mock client can handle multiple lookups."""
        client = MockRidClient()

        result1 = client.lookup("DJI-TEST")
        result2 = client.lookup("AUTEL-TEST")
        result3 = client.lookup("DJI-TEST")  # Same as first

        assert result1["make"] == "DJI"
        assert result2["make"] == "Autel"
        assert result3["make"] == "DJI"

    def test_mock_client_empty_serial(self):
        """Test mock client with empty serial number."""
        client = MockRidClient()
        result = client.lookup("")
        assert result["found"] is False


class TestFaaRidClient:
    """Test the real FAA RID client (if available)."""

    def test_faa_client_initialization(self):
        """Test FAA client can be initialized."""
        client = FaaRidClient()
        assert client is not None

    def test_faa_client_availability_check(self):
        """Test checking if FAA lookup is available."""
        client = FaaRidClient()
        # Just check it returns a boolean, might be True or False
        # depending on whether faa-rid-lookup is installed
        assert isinstance(client.is_available(), bool)

    def test_faa_client_empty_serial(self):
        """Test FAA client with empty serial number."""
        client = FaaRidClient()
        result = client.lookup("")

        assert result["found"] is False
        assert "error" in result

    def test_faa_client_lookup_when_unavailable(self):
        """Test lookup when FAA library is not available."""
        client = FaaRidClient()

        # Force unavailability
        original_available = client.available
        client.available = False

        result = client.lookup("TEST123")
        assert result["found"] is False
        assert "error" in result

        # Restore
        client.available = original_available

    def test_faa_client_close(self):
        """Test FAA client can be closed without error."""
        client = FaaRidClient()
        client.close()  # Should not raise

    def test_faa_client_lookup_returns_dict(self):
        """Test that lookup always returns a dictionary."""
        client = FaaRidClient()

        # Even with a fake serial, should return a dict
        result = client.lookup("FAKE-SERIAL-123456")
        assert isinstance(result, dict)
        assert "found" in result


class TestRidClientProtocol:
    """Test that both clients conform to the RidClient protocol."""

    def test_mock_client_conforms_to_protocol(self):
        """Test MockRidClient implements RidClient protocol."""
        client: RidClient = MockRidClient()

        # Should have required methods
        assert hasattr(client, 'lookup')
        assert hasattr(client, 'is_available')
        assert callable(client.lookup)
        assert callable(client.is_available)

    def test_faa_client_conforms_to_protocol(self):
        """Test FaaRidClient implements RidClient protocol."""
        client: RidClient = FaaRidClient()

        # Should have required methods
        assert hasattr(client, 'lookup')
        assert hasattr(client, 'is_available')
        assert callable(client.lookup)
        assert callable(client.is_available)

    def test_protocol_lookup_signature(self):
        """Test that lookup method works with protocol signature."""
        client: RidClient = MockRidClient()

        # Should accept serial_number and optional use_api_fallback
        result = client.lookup("TEST", use_api_fallback=False)
        assert isinstance(result, dict)

        result = client.lookup("TEST", use_api_fallback=True)
        assert isinstance(result, dict)

    def test_protocol_is_available_signature(self):
        """Test that is_available method works with protocol signature."""
        client: RidClient = MockRidClient()
        available = client.is_available()
        assert isinstance(available, bool)


class TestRidClientIntegration:
    """Integration tests for RID client usage patterns."""

    def test_client_usage_pattern(self):
        """Test typical usage pattern with mock client."""
        client: RidClient = MockRidClient()

        # Check if available
        if not client.is_available():
            pytest.skip("RID client not available")

        # Perform lookup
        result = client.lookup("DJI-TEST")

        # Process results
        if result["found"]:
            assert "make" in result
            assert "model" in result
        else:
            assert result["found"] is False

    def test_client_with_context_manager_pattern(self):
        """Test using client with try/finally pattern."""
        client = MockRidClient()

        try:
            result = client.lookup("DJI-TEST")
            assert result["found"] is True
        finally:
            client.close()

    def test_multiple_clients_independent(self):
        """Test that multiple client instances are independent."""
        client1 = MockRidClient()
        client2 = MockRidClient()

        # Modify one client's results
        client1.set_result("CUSTOM", {"found": True, "make": "Custom1"})
        client2.set_result("CUSTOM", {"found": True, "make": "Custom2"})

        result1 = client1.lookup("CUSTOM")
        result2 = client2.lookup("CUSTOM")

        assert result1["make"] == "Custom1"
        assert result2["make"] == "Custom2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
