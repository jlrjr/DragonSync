"""Tests for ConfigLoader."""

import os
import tempfile
import pytest
from pathlib import Path
from refactor_project.config.config_loader import (
    ConfigLoader,
    DragonSyncConfig,
    ZmqConfig,
    TakConfig,
    MqttConfig,
    LatticeConfig,
    AdsbConfig,
)


class TestConfigDataclasses:
    """Test configuration dataclasses."""

    def test_zmq_config_defaults(self):
        """Should create ZmqConfig with defaults."""
        config = ZmqConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 4224
        assert config.status_port == 4225

    def test_zmq_config_custom(self):
        """Should create ZmqConfig with custom values."""
        config = ZmqConfig(host="192.168.1.1", port=5000, status_port=5001)
        assert config.host == "192.168.1.1"
        assert config.port == 5000
        assert config.status_port == 5001

    def test_tak_config_defaults(self):
        """Should create TakConfig with defaults."""
        config = TakConfig()
        assert config.host is None
        assert config.port is None
        assert config.protocol is None
        assert config.multicast_enabled is True
        assert config.multicast_addr == "239.2.3.1"
        assert config.multicast_port == 6969

    def test_mqtt_config_defaults(self):
        """Should create MqttConfig with defaults."""
        config = MqttConfig()
        assert config.enabled is False
        assert config.host == "127.0.0.1"
        assert config.port == 1883
        assert config.retain is True

    def test_lattice_config_defaults(self):
        """Should create LatticeConfig with defaults."""
        config = LatticeConfig()
        assert config.enabled is False
        assert config.source_name == "DragonSync"
        assert config.drone_rate == 1.0


class TestConfigLoader:
    """Test ConfigLoader."""

    def create_temp_config(self, content: str) -> str:
        """Create a temporary config file and return its path."""
        fd, path = tempfile.mkstemp(suffix=".ini", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path

    def test_load_minimal_config(self):
        """Should load minimal valid config."""
        content = """[SETTINGS]
zmq_host = 127.0.0.1
zmq_port = 4224
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.zmq.host == "127.0.0.1"
            assert config.zmq.port == 4224
            assert config.zmq.status_port == 4225  # default
        finally:
            os.unlink(config_path)

    def test_load_full_config(self):
        """Should load complete config with all sections."""
        content = """[SETTINGS]
zmq_host = 192.168.1.100
zmq_port = 5000
zmq_status_port = 5001

tak_host = tak.example.com
tak_port = 8089
tak_protocol = tcp
enable_multicast = false

mqtt_enabled = true
mqtt_host = mqtt.example.com
mqtt_port = 1883
mqtt_topic = drones/all

lattice_enabled = true
lattice_token = secret-token
lattice_base_url = https://lattice.example.com

rate_limit = 5.0
max_drones = 50
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()

            # ZMQ
            assert config.zmq.host == "192.168.1.100"
            assert config.zmq.port == 5000

            # TAK
            assert config.tak.host == "tak.example.com"
            assert config.tak.port == 8089
            assert config.tak.protocol == "tcp"
            assert config.tak.multicast_enabled is False

            # MQTT
            assert config.mqtt.enabled is True
            assert config.mqtt.host == "mqtt.example.com"
            assert config.mqtt.topic == "drones/all"

            # Lattice
            assert config.lattice.enabled is True
            assert config.lattice.token == "secret-token"

            # Operational
            assert config.rate_limit == 5.0
            assert config.max_drones == 50
        finally:
            os.unlink(config_path)

    def test_load_with_booleans(self):
        """Should correctly parse boolean values."""
        content = """[SETTINGS]
enable_multicast = true
mqtt_enabled = false
mqtt_retain = true
tak_tls_skip_verify = false
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.tak.multicast_enabled is True
            assert config.mqtt.enabled is False
            assert config.mqtt.retain is True
            assert config.tak.tls_skip_verify is False
        finally:
            os.unlink(config_path)

    def test_load_with_empty_values(self):
        """Should handle empty config values as None."""
        content = """[SETTINGS]
tak_host =
tak_port =
mqtt_username =
lattice_token =
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.tak.host is None
            assert config.tak.port is None
            assert config.mqtt.username is None
            assert config.lattice.token is None
        finally:
            os.unlink(config_path)

    def test_load_with_floats(self):
        """Should parse float values correctly."""
        content = """[SETTINGS]
rate_limit = 3.5
inactivity_timeout = 120.0
lattice_drone_rate = 2.5
lattice_wd_rate = 0.5
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.rate_limit == 3.5
            assert config.inactivity_timeout == 120.0
            assert config.lattice.drone_rate == 2.5
            assert config.lattice.wd_rate == 0.5
        finally:
            os.unlink(config_path)

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError):
            loader = ConfigLoader("/nonexistent/config.ini")
            loader.load()

    def test_invalid_config_format(self):
        """Should raise error for invalid INI format."""
        content = "This is not valid INI format"
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            # Should not raise during init
            with pytest.raises(Exception):  # Could be various parsing errors
                loader.load()
        finally:
            os.unlink(config_path)


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides."""

    def create_temp_config(self, content: str) -> str:
        """Create a temporary config file and return its path."""
        fd, path = tempfile.mkstemp(suffix=".ini", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path

    def test_env_override_zmq_host(self, monkeypatch):
        """Should override ZMQ host from environment."""
        content = """[SETTINGS]
zmq_host = 127.0.0.1
"""
        config_path = self.create_temp_config(content)
        try:
            monkeypatch.setenv("DRAGONSYNC_ZMQ_HOST", "10.0.0.1")
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.zmq.host == "10.0.0.1"
        finally:
            os.unlink(config_path)

    def test_env_override_tak_host(self, monkeypatch):
        """Should override TAK host from environment."""
        content = """[SETTINGS]
tak_host = original.host
"""
        config_path = self.create_temp_config(content)
        try:
            monkeypatch.setenv("DRAGONSYNC_TAK_HOST", "new.host")
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.tak.host == "new.host"
        finally:
            os.unlink(config_path)

    def test_env_override_mqtt_enabled(self, monkeypatch):
        """Should override MQTT enabled from environment."""
        content = """[SETTINGS]
mqtt_enabled = false
"""
        config_path = self.create_temp_config(content)
        try:
            monkeypatch.setenv("DRAGONSYNC_MQTT_ENABLED", "true")
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.mqtt.enabled is True
        finally:
            os.unlink(config_path)

    def test_env_override_lattice_token(self, monkeypatch):
        """Should override Lattice token from environment."""
        content = """[SETTINGS]
lattice_token = old-token
"""
        config_path = self.create_temp_config(content)
        try:
            monkeypatch.setenv("DRAGONSYNC_LATTICE_TOKEN", "new-token")
            loader = ConfigLoader(config_path)
            config = loader.load()

            assert config.lattice.token == "new-token"
        finally:
            os.unlink(config_path)


class TestConfigValidation:
    """Test configuration validation."""

    def create_temp_config(self, content: str) -> str:
        """Create a temporary config file and return its path."""
        fd, path = tempfile.mkstemp(suffix=".ini", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path

    def test_validate_valid_config(self):
        """Should pass validation for valid config."""
        content = """[SETTINGS]
zmq_host = 127.0.0.1
zmq_port = 4224
rate_limit = 3.0
max_drones = 30
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()
            errors = config.validate()

            assert len(errors) == 0
        finally:
            os.unlink(config_path)

    def test_validate_invalid_port(self):
        """Should detect invalid port numbers."""
        content = """[SETTINGS]
zmq_port = 99999
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()
            errors = config.validate()

            assert len(errors) > 0
            assert any("port" in err.lower() for err in errors)
        finally:
            os.unlink(config_path)

    def test_validate_invalid_rate_limit(self):
        """Should detect invalid rate limit."""
        content = """[SETTINGS]
rate_limit = -1.0
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()
            errors = config.validate()

            assert len(errors) > 0
            assert any("rate" in err.lower() for err in errors)
        finally:
            os.unlink(config_path)

    def test_validate_mqtt_enabled_without_host(self):
        """Should detect MQTT enabled but missing host."""
        content = """[SETTINGS]
mqtt_enabled = true
mqtt_host =
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()
            errors = config.validate()

            assert len(errors) > 0
            assert any("mqtt" in err.lower() and "host" in err.lower() for err in errors)
        finally:
            os.unlink(config_path)


class TestConfigToDict:
    """Test configuration serialization to dict."""

    def create_temp_config(self, content: str) -> str:
        """Create a temporary config file and return its path."""
        fd, path = tempfile.mkstemp(suffix=".ini", text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        return path

    def test_to_dict(self):
        """Should convert config to dictionary."""
        content = """[SETTINGS]
zmq_host = 127.0.0.1
zmq_port = 4224
tak_host = tak.example.com
mqtt_enabled = true
"""
        config_path = self.create_temp_config(content)
        try:
            loader = ConfigLoader(config_path)
            config = loader.load()
            config_dict = config.to_dict()

            assert isinstance(config_dict, dict)
            assert "zmq" in config_dict
            assert "tak" in config_dict
            assert "mqtt" in config_dict
            assert config_dict["zmq"]["host"] == "127.0.0.1"
            assert config_dict["tak"]["host"] == "tak.example.com"
        finally:
            os.unlink(config_path)
