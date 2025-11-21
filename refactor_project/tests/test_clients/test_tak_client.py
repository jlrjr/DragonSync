"""Tests for TAK TCP/TLS Client."""

import pytest
import socket
import ssl
from unittest.mock import Mock, MagicMock, patch, call
from refactor_project.clients.tak_client import TakClient


class TestTakClientInitialization:
    """Test TAK client initialization."""

    def test_init_with_required_params(self):
        """Should initialize with host and port."""
        client = TakClient(host='10.0.0.112', port=8089)
        assert client.host == '10.0.0.112'
        assert client.port == 8089
        assert client.sock is None  # Not connected yet

    def test_init_with_ssl_context(self):
        """Should accept SSL context."""
        mock_context = Mock(spec=ssl.SSLContext)
        client = TakClient(host='10.0.0.112', port=8089, ssl_context=mock_context)
        assert client.ssl_context is mock_context

    def test_init_without_ssl_context(self):
        """Should work without SSL context (plain TCP)."""
        client = TakClient(host='10.0.0.112', port=8087)  # Unencrypted port
        assert client.ssl_context is None


class TestTakClientConnection:
    """Test TAK client connection logic."""

    @patch('socket.create_connection')
    def test_connect_plain_tcp(self, mock_create_conn):
        """Should connect via plain TCP when no SSL context."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()

        mock_create_conn.assert_called_once_with(('10.0.0.112', 8087), timeout=10)
        assert client.sock is mock_socket

    @patch('socket.create_connection')
    def test_connect_with_ssl(self, mock_create_conn):
        """Should wrap socket with SSL when context provided."""
        mock_socket = MagicMock()
        mock_ssl_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        mock_context = MagicMock(spec=ssl.SSLContext)
        mock_context.wrap_socket.return_value = mock_ssl_socket

        client = TakClient(host='10.0.0.112', port=8089, ssl_context=mock_context)
        client.connect()

        mock_create_conn.assert_called_once()
        mock_context.wrap_socket.assert_called_once_with(
            mock_socket, server_hostname='10.0.0.112'
        )
        assert client.sock is mock_ssl_socket

    @patch('socket.create_connection')
    def test_connect_timeout(self, mock_create_conn):
        """Should handle connection timeout."""
        mock_create_conn.side_effect = socket.timeout("Connection timed out")

        client = TakClient(host='10.0.0.112', port=8089)

        with pytest.raises(socket.timeout):
            client.connect()

    @patch('socket.create_connection')
    def test_connect_refused(self, mock_create_conn):
        """Should handle connection refused."""
        mock_create_conn.side_effect = ConnectionRefusedError("Connection refused")

        client = TakClient(host='10.0.0.112', port=8089)

        with pytest.raises(ConnectionRefusedError):
            client.connect()


class TestTakClientSend:
    """Test sending CoT messages."""

    def test_send_requires_connection(self):
        """Should raise error if not connected."""
        client = TakClient(host='10.0.0.112', port=8089)

        with pytest.raises(RuntimeError, match="Not connected"):
            client.send(b'<event>test</event>')

    @patch('socket.create_connection')
    def test_send_cot_xml(self, mock_create_conn):
        """Should send CoT XML bytes."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()

        cot_xml = b'<event version="2.0">test</event>'
        client.send(cot_xml)

        mock_socket.sendall.assert_called_once_with(cot_xml)

    @patch('socket.create_connection')
    def test_send_handles_broken_pipe(self, mock_create_conn):
        """Should handle broken pipe error."""
        mock_socket = MagicMock()
        mock_socket.sendall.side_effect = BrokenPipeError("Broken pipe")
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()

        with pytest.raises(BrokenPipeError):
            client.send(b'<event>test</event>')

    @patch('socket.create_connection')
    def test_send_multiple_messages(self, mock_create_conn):
        """Should send multiple CoT messages."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()

        cot1 = b'<event uid="test1">data</event>'
        cot2 = b'<event uid="test2">data</event>'
        cot3 = b'<event uid="test3">data</event>'

        client.send(cot1)
        client.send(cot2)
        client.send(cot3)

        assert mock_socket.sendall.call_count == 3
        mock_socket.sendall.assert_has_calls([
            call(cot1),
            call(cot2),
            call(cot3)
        ])


class TestTakClientClose:
    """Test connection cleanup."""

    @patch('socket.create_connection')
    def test_close(self, mock_create_conn):
        """Should close socket connection."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()
        client.close()

        mock_socket.close.assert_called_once()
        assert client.sock is None

    def test_close_when_not_connected(self):
        """Should handle close when not connected."""
        client = TakClient(host='10.0.0.112', port=8087)

        # Should not raise error
        client.close()

    @patch('socket.create_connection')
    def test_close_handles_errors(self, mock_create_conn):
        """Should handle errors during close gracefully."""
        mock_socket = MagicMock()
        mock_socket.close.side_effect = OSError("Socket error")
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()

        # Should not raise error
        client.close()
        assert client.sock is None


class TestTakClientReconnection:
    """Test reconnection logic with backoff."""

    @patch('socket.create_connection')
    @patch('time.sleep')
    def test_reconnect_after_disconnect(self, mock_sleep, mock_create_conn):
        """Should reconnect after disconnect."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()
        client.close()
        client.connect()

        assert mock_create_conn.call_count == 2

    @patch('socket.create_connection')
    @patch('time.sleep')
    def test_connect_with_retry(self, mock_sleep, mock_create_conn):
        """Should retry connection on failure."""
        # Fail twice, then succeed
        mock_socket = MagicMock()
        mock_create_conn.side_effect = [
            ConnectionRefusedError("Refused"),
            ConnectionRefusedError("Refused"),
            mock_socket
        ]

        client = TakClient(host='10.0.0.112', port=8087, max_retries=3, retry_delay=1.0)
        client.connect_with_retry()

        assert mock_create_conn.call_count == 3
        assert mock_sleep.call_count == 2
        assert client.sock is mock_socket

    @patch('socket.create_connection')
    @patch('time.sleep')
    def test_connect_retry_exhausted(self, mock_sleep, mock_create_conn):
        """Should raise error after max retries."""
        mock_create_conn.side_effect = ConnectionRefusedError("Refused")

        client = TakClient(host='10.0.0.112', port=8087, max_retries=3, retry_delay=1.0)

        with pytest.raises(ConnectionRefusedError):
            client.connect_with_retry()

        assert mock_create_conn.call_count == 3
        assert mock_sleep.call_count == 2


class TestTakClientContextManager:
    """Test context manager support."""

    @patch('socket.create_connection')
    def test_context_manager_auto_connect(self, mock_create_conn):
        """Should auto-connect when used as context manager."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        with TakClient(host='10.0.0.112', port=8087) as client:
            assert client.sock is mock_socket

    @patch('socket.create_connection')
    def test_context_manager_auto_close(self, mock_create_conn):
        """Should auto-close when exiting context."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        with TakClient(host='10.0.0.112', port=8087) as client:
            pass

        mock_socket.close.assert_called_once()

    @patch('socket.create_connection')
    def test_context_manager_exception_still_closes(self, mock_create_conn):
        """Should close even if exception occurs."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        with pytest.raises(ValueError):
            with TakClient(host='10.0.0.112', port=8087) as client:
                raise ValueError("Test error")

        mock_socket.close.assert_called_once()


class TestTakClientProperties:
    """Test client properties and state."""

    def test_is_connected_false_initially(self):
        """Should report not connected initially."""
        client = TakClient(host='10.0.0.112', port=8087)
        assert not client.is_connected()

    @patch('socket.create_connection')
    def test_is_connected_true_after_connect(self, mock_create_conn):
        """Should report connected after successful connect."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()

        assert client.is_connected()

    @patch('socket.create_connection')
    def test_is_connected_false_after_close(self, mock_create_conn):
        """Should report not connected after close."""
        mock_socket = MagicMock()
        mock_create_conn.return_value = mock_socket

        client = TakClient(host='10.0.0.112', port=8087)
        client.connect()
        client.close()

        assert not client.is_connected()
