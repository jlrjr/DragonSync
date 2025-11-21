"""Tests for MQTT Client."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from refactor_project.clients.mqtt_client import MqttClient


class TestMqttClientInitialization:
    """Test MQTT client initialization."""

    def test_init_with_required_params(self):
        """Should initialize with host and port."""
        client = MqttClient(host='127.0.0.1', port=1883)
        assert client.host == '127.0.0.1'
        assert client.port == 1883
        assert client.client_id is not None  # Auto-generated

    def test_init_with_client_id(self):
        """Should accept custom client ID."""
        client = MqttClient(host='127.0.0.1', port=1883, client_id='dragonsync-test')
        assert client.client_id == 'dragonsync-test'

    def test_init_with_auth(self):
        """Should accept username and password."""
        client = MqttClient(
            host='127.0.0.1',
            port=1883,
            username='user',
            password='pass'
        )
        assert client.username == 'user'
        assert client.password == 'pass'

    def test_init_with_tls(self):
        """Should accept TLS parameters."""
        client = MqttClient(
            host='127.0.0.1',
            port=8883,
            use_tls=True,
            ca_certs='/path/to/ca.pem'
        )
        assert client.use_tls is True
        assert client.ca_certs == '/path/to/ca.pem'


class TestMqttClientConnection:
    """Test MQTT client connection."""

    @patch('paho.mqtt.client.Client')
    def test_connect(self, mock_mqtt):
        """Should connect to MQTT broker."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()

        mock_instance.connect.assert_called_once_with('127.0.0.1', 1883, 60)

    @patch('paho.mqtt.client.Client')
    def test_connect_with_auth(self, mock_mqtt):
        """Should set username/password when provided."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(
            host='127.0.0.1',
            port=1883,
            username='user',
            password='pass'
        )
        client.connect()

        mock_instance.username_pw_set.assert_called_once_with('user', 'pass')
        mock_instance.connect.assert_called_once()

    @patch('paho.mqtt.client.Client')
    def test_connect_with_tls(self, mock_mqtt):
        """Should configure TLS when enabled."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(
            host='127.0.0.1',
            port=8883,
            use_tls=True,
            ca_certs='/path/to/ca.pem'
        )
        client.connect()

        mock_instance.tls_set.assert_called_once_with(ca_certs='/path/to/ca.pem')
        mock_instance.connect.assert_called_once()

    @patch('paho.mqtt.client.Client')
    def test_connect_handles_error(self, mock_mqtt):
        """Should handle connection errors."""
        mock_instance = MagicMock()
        mock_instance.connect.side_effect = ConnectionRefusedError("Connection refused")
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)

        with pytest.raises(ConnectionRefusedError):
            client.connect()


class TestMqttClientPublish:
    """Test MQTT publishing."""

    @patch('paho.mqtt.client.Client')
    def test_publish_message(self, mock_mqtt):
        """Should publish message to topic."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()
        client.publish('test/topic', 'test payload')

        mock_instance.publish.assert_called_once_with(
            'test/topic',
            'test payload',
            qos=0,
            retain=False
        )

    @patch('paho.mqtt.client.Client')
    def test_publish_with_qos(self, mock_mqtt):
        """Should publish with specified QoS."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()
        client.publish('test/topic', 'payload', qos=1)

        mock_instance.publish.assert_called_once_with(
            'test/topic',
            'payload',
            qos=1,
            retain=False
        )

    @patch('paho.mqtt.client.Client')
    def test_publish_with_retain(self, mock_mqtt):
        """Should publish with retain flag."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()
        client.publish('test/topic', 'payload', retain=True)

        mock_instance.publish.assert_called_once_with(
            'test/topic',
            'payload',
            qos=0,
            retain=True
        )

    @patch('paho.mqtt.client.Client')
    def test_publish_requires_connection(self, mock_mqtt):
        """Should raise error if not connected."""
        client = MqttClient(host='127.0.0.1', port=1883)

        with pytest.raises(RuntimeError, match="Not connected"):
            client.publish('test/topic', 'payload')

    @patch('paho.mqtt.client.Client')
    def test_publish_multiple_messages(self, mock_mqtt):
        """Should publish multiple messages."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()

        client.publish('topic1', 'payload1')
        client.publish('topic2', 'payload2')
        client.publish('topic3', 'payload3')

        assert mock_instance.publish.call_count == 3


class TestMqttClientClose:
    """Test MQTT client cleanup."""

    @patch('paho.mqtt.client.Client')
    def test_close(self, mock_mqtt):
        """Should disconnect and cleanup."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()
        client.close()

        mock_instance.disconnect.assert_called_once()

    @patch('paho.mqtt.client.Client')
    def test_close_when_not_connected(self, mock_mqtt):
        """Should handle close when not connected."""
        client = MqttClient(host='127.0.0.1', port=1883)

        # Should not raise error
        client.close()

    @patch('paho.mqtt.client.Client')
    def test_close_handles_errors(self, mock_mqtt):
        """Should handle errors during close gracefully."""
        mock_instance = MagicMock()
        mock_instance.disconnect.side_effect = Exception("Disconnect error")
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()

        # Should not raise error
        client.close()


class TestMqttClientContextManager:
    """Test context manager support."""

    @patch('paho.mqtt.client.Client')
    def test_context_manager_auto_connect(self, mock_mqtt):
        """Should auto-connect when used as context manager."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        with MqttClient(host='127.0.0.1', port=1883) as client:
            mock_instance.connect.assert_called_once()

    @patch('paho.mqtt.client.Client')
    def test_context_manager_auto_close(self, mock_mqtt):
        """Should auto-close when exiting context."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        with MqttClient(host='127.0.0.1', port=1883) as client:
            pass

        mock_instance.disconnect.assert_called_once()

    @patch('paho.mqtt.client.Client')
    def test_context_manager_exception_still_closes(self, mock_mqtt):
        """Should close even if exception occurs."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        with pytest.raises(ValueError):
            with MqttClient(host='127.0.0.1', port=1883) as client:
                raise ValueError("Test error")

        mock_instance.disconnect.assert_called_once()


class TestMqttClientProperties:
    """Test client properties and state."""

    def test_is_connected_false_initially(self):
        """Should report not connected initially."""
        client = MqttClient(host='127.0.0.1', port=1883)
        assert not client.is_connected()

    @patch('paho.mqtt.client.Client')
    def test_is_connected_true_after_connect(self, mock_mqtt):
        """Should report connected after successful connect."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()

        assert client.is_connected()

    @patch('paho.mqtt.client.Client')
    def test_is_connected_false_after_close(self, mock_mqtt):
        """Should report not connected after close."""
        mock_instance = MagicMock()
        mock_mqtt.return_value = mock_instance

        client = MqttClient(host='127.0.0.1', port=1883)
        client.connect()
        client.close()

        assert not client.is_connected()
