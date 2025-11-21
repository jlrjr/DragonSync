"""Tests for Lattice Client (Anduril SDK wrapper)."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from refactor_project.clients.lattice_client import LatticeClient


class TestLatticeClientInitialization:
    """Test Lattice Client initialization."""

    def test_init_with_token(self):
        """Should initialize with token."""
        client = LatticeClient(token="test-token")
        assert client.token == "test-token"
        assert client.base_url is None
        assert client.sandbox_token is None

    def test_init_with_base_url(self):
        """Should initialize with custom base URL."""
        client = LatticeClient(token="test-token", base_url="https://custom.lattice.com")
        assert client.token == "test-token"
        assert client.base_url == "https://custom.lattice.com"

    def test_init_with_sandbox_token(self):
        """Should initialize with sandbox token."""
        client = LatticeClient(token="test-token", sandbox_token="sandbox-123")
        assert client.token == "test-token"
        assert client.sandbox_token == "sandbox-123"

    def test_init_stores_parameters(self):
        """Should store all initialization parameters."""
        client = LatticeClient(
            token="token-123",
            base_url="https://api.lattice.com",
            sandbox_token="sandbox-456"
        )
        assert client.token == "token-123"
        assert client.base_url == "https://api.lattice.com"
        assert client.sandbox_token == "sandbox-456"


class TestLatticeClientConnect:
    """Test Lattice Client connection."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_connect_creates_lattice_client(self, mock_lattice_class):
        """Should create Lattice SDK client on connect."""
        client = LatticeClient(token="test-token")
        client.connect()

        mock_lattice_class.assert_called_once_with(token="test-token")
        assert client._client is not None

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_connect_with_base_url(self, mock_lattice_class):
        """Should pass base_url to Lattice SDK."""
        client = LatticeClient(token="test-token", base_url="https://custom.com")
        client.connect()

        mock_lattice_class.assert_called_once_with(
            token="test-token",
            base_url="https://custom.com"
        )

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_connect_with_sandbox_token(self, mock_lattice_class):
        """Should configure sandbox token as header."""
        client = LatticeClient(token="test-token", sandbox_token="sandbox-123")
        client.connect()

        # Should pass headers with sandbox token
        call_kwargs = mock_lattice_class.call_args[1]
        assert 'headers' in call_kwargs
        assert call_kwargs['headers']['anduril-sandbox-authorization'] == 'Bearer sandbox-123'

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_connect_handles_sdk_not_installed(self, mock_lattice_class):
        """Should raise RuntimeError if Anduril SDK not installed."""
        mock_lattice_class.side_effect = ImportError("No module named 'anduril'")

        client = LatticeClient(token="test-token")

        with pytest.raises(RuntimeError, match="Anduril SDK not available"):
            client.connect()


class TestLatticeClientPublishEntity:
    """Test publishing entities to Lattice."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_publish_entity(self, mock_lattice_class):
        """Should publish entity with provided data."""
        mock_lattice_instance = MagicMock()
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()

        client.publish_entity(
            entity_id="drone-123",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=100.0
        )

        # Should call entities.publish_entity
        mock_lattice_instance.entities.publish_entity.assert_called_once()

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_publish_entity_passes_all_kwargs(self, mock_lattice_class):
        """Should pass all kwargs to SDK publish method."""
        mock_lattice_instance = MagicMock()
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()

        client.publish_entity(
            entity_id="test-123",
            latitude=10.0,
            longitude=20.0,
            altitude=30.0,
            entity_type="drone",
            callsign="TEST"
        )

        call_kwargs = mock_lattice_instance.entities.publish_entity.call_args[1]
        assert 'entity_id' in call_kwargs
        assert 'latitude' in call_kwargs
        assert call_kwargs['callsign'] == 'TEST'

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_publish_entity_requires_connection(self, mock_lattice_class):
        """Should raise error if not connected."""
        client = LatticeClient(token="test-token")

        with pytest.raises(RuntimeError, match="Not connected to Lattice"):
            client.publish_entity(entity_id="test", latitude=0, longitude=0)


class TestLatticeClientExpireEntity:
    """Test expiring entities in Lattice."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_expire_entity(self, mock_lattice_class):
        """Should expire entity by ID."""
        mock_lattice_instance = MagicMock()
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()

        client.expire_entity(entity_id="drone-123")

        # Should call entities.expire_entity or similar
        mock_lattice_instance.entities.expire_entity.assert_called_once_with(
            entity_id="drone-123"
        )

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_expire_entity_requires_connection(self, mock_lattice_class):
        """Should raise error if not connected."""
        client = LatticeClient(token="test-token")

        with pytest.raises(RuntimeError, match="Not connected to Lattice"):
            client.expire_entity(entity_id="test-123")


class TestLatticeClientClose:
    """Test Lattice Client close."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_close(self, mock_lattice_class):
        """Should close Lattice client."""
        mock_lattice_instance = MagicMock()
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()
        client.close()

        # Lattice SDK may not have explicit close, but should clear reference
        assert client._client is None

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_close_when_not_connected(self, mock_lattice_class):
        """Should handle close when not connected."""
        client = LatticeClient(token="test-token")
        # Should not raise error
        client.close()

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_close_handles_errors(self, mock_lattice_class):
        """Should handle errors during close gracefully."""
        mock_lattice_instance = MagicMock()
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()

        # Even if cleanup fails, should not raise
        client.close()
        assert client._client is None


class TestLatticeClientProperties:
    """Test Lattice Client properties."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_is_connected_false_initially(self, mock_lattice_class):
        """Should not be connected initially."""
        client = LatticeClient(token="test-token")
        assert not client.is_connected()

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_is_connected_true_after_connect(self, mock_lattice_class):
        """Should be connected after successful connect."""
        client = LatticeClient(token="test-token")
        client.connect()
        assert client.is_connected()

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_is_connected_false_after_close(self, mock_lattice_class):
        """Should not be connected after close."""
        client = LatticeClient(token="test-token")
        client.connect()
        client.close()
        assert not client.is_connected()


class TestLatticeClientContextManager:
    """Test Lattice Client as context manager."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_context_manager_auto_connect(self, mock_lattice_class):
        """Should auto-connect when entering context."""
        client = LatticeClient(token="test-token")

        with client as c:
            assert c is client
            assert client.is_connected()

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_context_manager_auto_close(self, mock_lattice_class):
        """Should auto-close when exiting context."""
        client = LatticeClient(token="test-token")

        with client:
            pass

        assert not client.is_connected()

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_context_manager_exception_still_closes(self, mock_lattice_class):
        """Should close even if exception occurs."""
        client = LatticeClient(token="test-token")

        try:
            with client:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert not client.is_connected()


class TestLatticeClientErrorHandling:
    """Test Lattice Client error handling."""

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_publish_entity_handles_errors(self, mock_lattice_class):
        """Should handle errors during publish."""
        mock_lattice_instance = MagicMock()
        mock_lattice_instance.entities.publish_entity.side_effect = Exception("API error")
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()

        with pytest.raises(Exception, match="API error"):
            client.publish_entity(entity_id="test", latitude=0, longitude=0)

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_expire_entity_handles_errors(self, mock_lattice_class):
        """Should handle errors during expire."""
        mock_lattice_instance = MagicMock()
        mock_lattice_instance.entities.expire_entity.side_effect = Exception("API error")
        mock_lattice_class.return_value = mock_lattice_instance

        client = LatticeClient(token="test-token")
        client.connect()

        with pytest.raises(Exception, match="API error"):
            client.expire_entity(entity_id="test-123")

    @patch('refactor_project.clients.lattice_client.Lattice')
    def test_connect_twice_uses_existing_lattice(self, mock_lattice_class):
        """Should reuse Lattice class on second connect."""
        client1 = LatticeClient(token="test-token-1")
        client1.connect()

        # Second client should use already-imported Lattice
        client2 = LatticeClient(token="test-token-2")
        client2.connect()

        # Should have been called twice (once per client)
        assert mock_lattice_class.call_count == 2
