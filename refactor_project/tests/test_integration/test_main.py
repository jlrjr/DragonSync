"""
Integration tests for main.py - End-to-end testing of DragonSync components.

Tests the full flow: ZMQ → Parser → Manager → CoT Generator → Sinks
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from refactor_project.main import DragonSyncApp, initialize_clients, initialize_sinks
from refactor_project.config.config_loader import DragonSyncConfig, ZmqConfig, TakConfig, MqttConfig, LatticeConfig, AdsbConfig


class TestInitializeClients:
    """Test client initialization from configuration."""

    def test_initialize_clients_with_tak_only(self):
        """Test TAK client initialization."""
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=False),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False)
        )

        with patch('refactor_project.main.TakClient') as mock_tak:
            mock_client = MagicMock()
            mock_tak.return_value = mock_client

            clients = initialize_clients(config)

            assert 'tak' in clients
            mock_client.connect.assert_called_once()

    def test_initialize_clients_with_mqtt_only(self):
        """Test MQTT client initialization."""
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host=None, port=None, protocol=None),
            mqtt=MqttConfig(enabled=True, host="127.0.0.1", port=1883),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False)
        )

        with patch('refactor_project.main.MqttClient') as mock_mqtt:
            mock_client = MagicMock()
            mock_mqtt.return_value = mock_client

            clients = initialize_clients(config)

            assert 'mqtt' in clients
            mock_client.connect.assert_called_once()

    def test_initialize_clients_with_lattice_only(self):
        """Test Lattice client initialization."""
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host=None, port=None, protocol=None),
            mqtt=MqttConfig(enabled=False),
            lattice=LatticeConfig(enabled=True, token="test-token", base_url="https://test.anduril.cloud"),
            adsb=AdsbConfig(enabled=False),
        )

        with patch('refactor_project.main.LatticeClient') as mock_lattice:
            mock_client = MagicMock()
            mock_lattice.return_value = mock_client

            clients = initialize_clients(config)

            assert 'lattice' in clients
            mock_lattice.assert_called_once_with(
                token="test-token",
                base_url="https://test.anduril.cloud",
                sandbox_token=None
            )

    def test_initialize_clients_with_all(self):
        """Test initialization of all clients."""
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=True, host="127.0.0.1", port=1883),
            lattice=LatticeConfig(enabled=True, token="test-token", base_url="https://test.anduril.cloud"),
            adsb=AdsbConfig(enabled=False),
        )

        with patch('refactor_project.main.TakClient') as mock_tak, \
             patch('refactor_project.main.MqttClient') as mock_mqtt, \
             patch('refactor_project.main.LatticeClient') as mock_lattice:

            # Setup mocks
            for mock_cls in [mock_tak, mock_mqtt, mock_lattice]:
                mock_client = MagicMock()
                mock_cls.return_value = mock_client

            clients = initialize_clients(config)

            assert 'tak' in clients
            assert 'mqtt' in clients
            assert 'lattice' in clients

    def test_initialize_clients_handles_connection_errors(self):
        """Test that connection errors are handled gracefully."""
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=False),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False),
        )

        with patch('refactor_project.main.TakClient') as mock_tak:
            mock_client = MagicMock()
            mock_client.connect.side_effect = ConnectionError("Connection refused")
            mock_tak.return_value = mock_client

            clients = initialize_clients(config)

            # Should not raise, should return empty dict
            assert 'tak' not in clients


class TestInitializeSinks:
    """Test sink initialization from clients."""

    def test_initialize_sinks_with_tak(self):
        """Test TAK sink initialization."""
        mock_tak_client = MagicMock()
        clients = {'tak': mock_tak_client}
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=False),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False),
        )

        sinks = initialize_sinks(clients, config)

        assert len(sinks) == 1
        assert sinks[0].__class__.__name__ == 'TakSink'

    def test_initialize_sinks_with_mqtt(self):
        """Test MQTT sink initialization."""
        mock_mqtt_client = MagicMock()
        clients = {'mqtt': mock_mqtt_client}
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host=None, port=None, protocol=None),
            mqtt=MqttConfig(enabled=True, host="127.0.0.1", port=1883, topic="test/topic"),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False),
        )

        sinks = initialize_sinks(clients, config)

        assert len(sinks) == 1
        assert sinks[0].__class__.__name__ == 'MqttSink'

    def test_initialize_sinks_with_all(self):
        """Test initialization of all sinks."""
        clients = {
            'tak': MagicMock(),
            'mqtt': MagicMock(),
            'lattice': MagicMock()
        }
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=True, host="127.0.0.1", port=1883),
            lattice=LatticeConfig(enabled=True, token="test-token", base_url="https://test.anduril.cloud"),
            adsb=AdsbConfig(enabled=False),
        )

        sinks = initialize_sinks(clients, config)

        assert len(sinks) == 3
        sink_types = [s.__class__.__name__ for s in sinks]
        assert 'TakSink' in sink_types
        assert 'MqttSink' in sink_types
        assert 'LatticeSink' in sink_types


class TestDragonSyncApp:
    """Test DragonSync application orchestration."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=4225),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=False),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False),
            rate_limit=3.0,
            max_drones=30,
            inactivity_timeout=60.0
        )

    @pytest.fixture
    def app(self, config):
        """Create DragonSync app instance."""
        return DragonSyncApp(config)

    def test_app_initialization(self, app):
        """Test app initializes with correct config."""
        assert app.config is not None
        assert app.running is False
        assert app.parser is None
        assert app.manager is None
        assert app.cot_generator is None

    @patch('refactor_project.main.initialize_clients')
    @patch('refactor_project.main.initialize_sinks')
    @patch('refactor_project.main.zmq.Context')
    def test_app_setup(self, mock_zmq_context, mock_init_sinks, mock_init_clients, app):
        """Test app setup initializes all components."""
        # Setup mocks
        mock_init_clients.return_value = {'tak': MagicMock()}
        mock_init_sinks.return_value = [MagicMock()]

        mock_context = MagicMock()
        mock_socket = MagicMock()
        mock_context.socket.return_value = mock_socket
        mock_zmq_context.return_value = mock_context

        # Setup app
        app.setup()

        # Verify components initialized
        assert app.parser is not None
        assert app.cot_generator is not None
        assert app.manager is not None
        assert len(app.sinks) == 1
        assert app.telemetry_socket is not None

    @patch('refactor_project.main.zmq.Context')
    def test_process_telemetry_message(self, mock_zmq_context, app):
        """Test processing a telemetry message end-to-end."""
        # Setup app components
        with patch('refactor_project.main.initialize_clients') as mock_init_clients, \
             patch('refactor_project.main.initialize_sinks') as mock_init_sinks:

            mock_sink = MagicMock()
            mock_init_clients.return_value = {}
            mock_init_sinks.return_value = [mock_sink]

            mock_context = MagicMock()
            mock_socket = MagicMock()
            mock_context.socket.return_value = mock_socket
            mock_zmq_context.return_value = mock_context

            app.setup()

            # Create sample ZMQ message (DJI format - must match parser expectations)
            import json
            message = json.dumps([
                {
                    "MAC": "AA:BB:CC:DD:EE:FF",
                    "RSSI": -50,
                    "Basic ID": {
                        "ua_type": 2,
                        "id_type": "Serial Number",
                        "id": "TEST123",
                        "MAC": "AA:BB:CC:DD:EE:FF",
                        "RSSI": -50
                    }
                },
                {
                    "Location/Vector Message": {
                        "latitude": 42.3601,
                        "longitude": -71.0589,
                        "speed": 15.5,
                        "vert_speed": 2.0,
                        "geodetic_altitude": 150.0,
                        "height_agl": 50.0,
                        "direction": 90
                    }
                },
                {
                    "Self-ID Message": {
                        "text": "Test Drone"
                    }
                },
                {
                    "System Message": {
                        "latitude": 42.3600,
                        "longitude": -71.0590
                    }
                }
            ]).encode()

            # Process message
            app.process_telemetry_message(message)

            # Verify drone was added to manager
            assert len(app.manager.get_all()) == 1

            # Verify CoT was published to sink
            assert mock_sink.publish_cot_event.called

    def test_should_send_update_rate_limiting(self, app):
        """Test rate limiting for drone updates."""
        app.rate_limit = 3.0
        app.last_sent = {}

        from refactor_project.models.drone import Drone
        drone = Drone(
            id="TEST123",
            mac="AA:BB:CC:DD:EE:FF",
            lat=42.3601,
            lon=-71.0589,
            speed=15.0,
            vspeed=2.0,
            alt=150.0,
            height=50.0,
            pilot_lat=42.3600,
            pilot_lon=-71.0590,
            description="Test Drone",
            rssi=-50
        )

        # First update should send
        assert app.should_send_update(drone) is True
        app.last_sent[drone.id] = time.time()

        # Immediate second update should not send
        assert app.should_send_update(drone) is False

        # After rate limit expires, should send
        app.last_sent[drone.id] = time.time() - 4.0
        assert app.should_send_update(drone) is True

    @patch('refactor_project.main.zmq.Context')
    def test_cleanup_stale_drones(self, mock_zmq_context, app):
        """Test stale drone cleanup."""
        with patch('refactor_project.main.initialize_clients') as mock_init_clients, \
             patch('refactor_project.main.initialize_sinks') as mock_init_sinks:

            mock_sink = MagicMock()
            mock_init_clients.return_value = {}
            mock_init_sinks.return_value = [mock_sink]

            mock_context = MagicMock()
            mock_socket = MagicMock()
            mock_context.socket.return_value = mock_socket
            mock_zmq_context.return_value = mock_context

            app.setup()

            # Add a drone
            from refactor_project.models.drone import Drone
            drone = Drone(
                id="TEST123",
                mac="AA:BB:CC:DD:EE:FF",
                lat=42.3601,
                lon=-71.0589,
                speed=15.0,
                vspeed=2.0,
                alt=150.0,
                height=50.0,
                pilot_lat=42.3600,
                pilot_lon=-71.0590,
                description="Test Drone",
                rssi=-50
            )
            app.manager.add_or_update(drone)

            # Set last_update_time to old timestamp
            app.manager._drones["TEST123"].last_update_time = time.time() - 120  # 2 minutes ago

            # Cleanup stale drones
            app.cleanup_stale_drones()

            # Verify drone was removed
            assert len(app.manager.get_all()) == 0

            # Verify mark_inactive was called on sink
            mock_sink.mark_inactive.assert_called_once_with("TEST123")

    @patch('refactor_project.main.zmq.Context')
    def test_shutdown(self, mock_zmq_context, app):
        """Test graceful shutdown."""
        with patch('refactor_project.main.initialize_clients') as mock_init_clients, \
             patch('refactor_project.main.initialize_sinks') as mock_init_sinks:

            mock_client = MagicMock()
            mock_sink = MagicMock()
            mock_init_clients.return_value = {'tak': mock_client}
            mock_init_sinks.return_value = [mock_sink]

            mock_context = MagicMock()
            mock_socket = MagicMock()
            mock_context.socket.return_value = mock_socket
            mock_zmq_context.return_value = mock_context

            app.setup()
            app.shutdown()

            # Verify cleanup
            assert app.running is False
            mock_socket.close.assert_called()
            mock_context.term.assert_called()
            mock_sink.close.assert_called()
            mock_client.close.assert_called()


class TestEndToEnd:
    """End-to-end integration tests."""

    @patch('refactor_project.main.zmq.Context')
    def test_zmq_to_sink_flow(self, mock_zmq_context):
        """Test complete flow from ZMQ message to sink output."""
        # Create config
        config = DragonSyncConfig(
            zmq=ZmqConfig(host="127.0.0.1", port=4224, status_port=None),
            tak=TakConfig(host="10.0.0.112", port=8087, protocol="tcp"),
            mqtt=MqttConfig(enabled=False),
            lattice=LatticeConfig(enabled=False),
            adsb=AdsbConfig(enabled=False),
            rate_limit=0.1,
            max_drones=10
        )

        app = DragonSyncApp(config)

        with patch('refactor_project.main.initialize_clients') as mock_init_clients, \
             patch('refactor_project.main.initialize_sinks') as mock_init_sinks:

            mock_sink = MagicMock()
            mock_init_clients.return_value = {}
            mock_init_sinks.return_value = [mock_sink]

            mock_context = MagicMock()
            mock_socket = MagicMock()
            mock_context.socket.return_value = mock_socket
            mock_zmq_context.return_value = mock_context

            app.setup()

            # Simulate ZMQ messages (DJI format)
            import json
            messages = [
                json.dumps([
                    {
                        "MAC": f"AA:BB:CC:DD:EE:{i:02X}",
                        "RSSI": -50,
                        "Basic ID": {
                            "ua_type": 2,
                            "id_type": "Serial Number",
                            "id": f"DRONE{i}",
                            "MAC": f"AA:BB:CC:DD:EE:{i:02X}",
                            "RSSI": -50
                        }
                    },
                    {
                        "Location/Vector Message": {
                            "latitude": 42.3601 + i * 0.001,
                            "longitude": -71.0589 + i * 0.001,
                            "speed": 15.5,
                            "vert_speed": 2.0,
                            "geodetic_altitude": 150.0 + i * 10,
                            "height_agl": 50.0,
                            "direction": 90
                        }
                    },
                    {
                        "Self-ID Message": {
                            "text": f"Test Drone {i}"
                        }
                    },
                    {
                        "System Message": {
                            "latitude": 42.3600 + i * 0.001,
                            "longitude": -71.0590 + i * 0.001
                        }
                    }
                ]).encode()
                for i in range(5)
            ]

            # Process messages
            for msg in messages:
                app.process_telemetry_message(msg)

            # Verify results
            assert len(app.manager.get_all()) == 5
            assert mock_sink.publish_cot_event.call_count == 5

            # Verify CoT XML was generated
            for call_args in mock_sink.publish_cot_event.call_args_list:
                cot_xml = call_args[0][0]
                assert isinstance(cot_xml, bytes)
                assert b'<event' in cot_xml
                # Check that CoT contains drone UID (generated from MAC or ID)
                assert b'uid="' in cot_xml
