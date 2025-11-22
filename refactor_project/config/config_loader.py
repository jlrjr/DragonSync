"""Configuration loader for DragonSync.

Loads configuration from INI files with environment variable overrides.
Provides validation and type-safe access to configuration values.
"""

import os
import configparser
from dataclasses import dataclass, field, asdict
from typing import Optional, List
from pathlib import Path


@dataclass
class ZmqConfig:
    """ZMQ connection configuration."""

    host: str = "127.0.0.1"
    port: int = 4224
    status_port: int = 4225


@dataclass
class TakConfig:
    """TAK server configuration."""

    host: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None  # 'tcp' or 'udp'
    tls_p12: Optional[str] = None
    tls_p12_pass: Optional[str] = None
    tls_skip_verify: bool = True

    # Multicast configuration
    multicast_enabled: bool = True
    multicast_addr: str = "239.2.3.1"
    multicast_port: int = 6969
    multicast_interface: str = "0.0.0.0"
    multicast_ttl: int = 1


@dataclass
class MqttConfig:
    """MQTT broker configuration."""

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 1883
    topic: str = "wardragon/drones"

    # Per-drone topics
    per_drone_enabled: bool = False
    per_drone_base: str = "wardragon/drone"

    # Home Assistant
    ha_enabled: bool = False
    ha_prefix: str = "homeassistant"
    ha_device_base: str = "wardragon_drone"

    # Authentication
    username: Optional[str] = None
    password: Optional[str] = None

    # TLS
    tls: bool = False
    ca_file: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    tls_insecure: bool = False

    # Message options
    retain: bool = True


@dataclass
class LatticeConfig:
    """Lattice/Anduril configuration."""

    enabled: bool = False
    token: Optional[str] = None
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    sandbox_token: Optional[str] = None
    source_name: str = "DragonSync"
    drone_rate: float = 1.0
    wd_rate: float = 0.2


@dataclass
class AdsbConfig:
    """ADS-B / dump1090 configuration."""

    enabled: bool = False
    json_url: str = "http://127.0.0.1:8080/?all_with_pos"
    uid_prefix: str = "adsb-"
    cot_stale: int = 15
    rate_limit: float = 3.0
    min_alt: int = 0
    max_alt: int = 0


@dataclass
class DragonSyncConfig:
    """Complete DragonSync configuration."""

    # Configuration sections
    zmq: ZmqConfig = field(default_factory=ZmqConfig)
    tak: TakConfig = field(default_factory=TakConfig)
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    lattice: LatticeConfig = field(default_factory=LatticeConfig)
    adsb: AdsbConfig = field(default_factory=AdsbConfig)

    # Operational parameters
    rate_limit: float = 3.0
    max_drones: int = 30
    inactivity_timeout: float = 60.0
    enable_receive: bool = False

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []

        # Validate ZMQ ports
        if not (1 <= self.zmq.port <= 65535):
            errors.append(f"Invalid ZMQ port: {self.zmq.port}")
        if not (1 <= self.zmq.status_port <= 65535):
            errors.append(f"Invalid ZMQ status port: {self.zmq.status_port}")

        # Validate TAK configuration
        if self.tak.port is not None:
            if not (1 <= self.tak.port <= 65535):
                errors.append(f"Invalid TAK port: {self.tak.port}")
        if self.tak.protocol and self.tak.protocol not in ('tcp', 'udp'):
            errors.append(f"Invalid TAK protocol: {self.tak.protocol}")
        if not (1 <= self.tak.multicast_port <= 65535):
            errors.append(f"Invalid multicast port: {self.tak.multicast_port}")

        # Validate MQTT configuration
        if self.mqtt.enabled:
            if not self.mqtt.host:
                errors.append("MQTT enabled but host not specified")
        if self.mqtt.port and not (1 <= self.mqtt.port <= 65535):
            errors.append(f"Invalid MQTT port: {self.mqtt.port}")

        # Validate Lattice configuration
        if self.lattice.enabled:
            if not self.lattice.token:
                errors.append("Lattice enabled but token not specified")

        # Validate operational parameters
        if self.rate_limit < 0:
            errors.append(f"Invalid rate_limit: {self.rate_limit}")
        if self.max_drones < 1:
            errors.append(f"Invalid max_drones: {self.max_drones}")
        if self.inactivity_timeout < 0:
            errors.append(f"Invalid inactivity_timeout: {self.inactivity_timeout}")

        return errors

    def to_dict(self) -> dict:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration.
        """
        return asdict(self)


class ConfigLoader:
    """Loads DragonSync configuration from INI file with env var overrides."""

    # Environment variable prefix
    ENV_PREFIX = "DRAGONSYNC_"

    def __init__(self, config_path: str):
        """Initialize config loader.

        Args:
            config_path: Path to INI configuration file.
        """
        self.config_path = Path(config_path)

    def load(self) -> DragonSyncConfig:
        """Load configuration from file with environment overrides.

        Returns:
            DragonSyncConfig instance.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            Exception: If config file is invalid.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # Parse INI file
        parser = configparser.ConfigParser()
        parser.read(self.config_path)

        if 'SETTINGS' not in parser:
            raise ValueError("Config file missing [SETTINGS] section")

        settings = parser['SETTINGS']

        # Load ZMQ configuration
        zmq = ZmqConfig(
            host=self._get_str(settings, 'zmq_host', '127.0.0.1'),
            port=self._get_int(settings, 'zmq_port', 4224),
            status_port=self._get_int(settings, 'zmq_status_port', 4225),
        )

        # Load TAK configuration
        tak = TakConfig(
            host=self._get_str(settings, 'tak_host'),
            port=self._get_int(settings, 'tak_port'),
            protocol=self._get_str(settings, 'tak_protocol'),
            tls_p12=self._get_str(settings, 'tak_tls_p12'),
            tls_p12_pass=self._get_str(settings, 'tak_tls_p12_pass'),
            tls_skip_verify=self._get_bool(settings, 'tak_tls_skip_verify', True),
            multicast_enabled=self._get_bool(settings, 'enable_multicast', True),
            multicast_addr=self._get_str(settings, 'tak_multicast_addr', '239.2.3.1'),
            multicast_port=self._get_int(settings, 'tak_multicast_port', 6969),
            multicast_interface=self._get_str(settings, 'tak_multicast_interface', '0.0.0.0'),
            multicast_ttl=self._get_int(settings, 'multicast_ttl', 1),
        )

        # Load MQTT configuration
        mqtt = MqttConfig(
            enabled=self._get_bool(settings, 'mqtt_enabled', False),
            host=self._get_str(settings, 'mqtt_host', '127.0.0.1'),
            port=self._get_int(settings, 'mqtt_port', 1883),
            topic=self._get_str(settings, 'mqtt_topic', 'wardragon/drones'),
            per_drone_enabled=self._get_bool(settings, 'mqtt_per_drone_enabled', False),
            per_drone_base=self._get_str(settings, 'mqtt_per_drone_base', 'wardragon/drone'),
            ha_enabled=self._get_bool(settings, 'mqtt_ha_enabled', False),
            ha_prefix=self._get_str(settings, 'mqtt_ha_prefix', 'homeassistant'),
            ha_device_base=self._get_str(settings, 'mqtt_ha_device_base', 'wardragon_drone'),
            username=self._get_str(settings, 'mqtt_username'),
            password=self._get_str(settings, 'mqtt_password'),
            tls=self._get_bool(settings, 'mqtt_tls', False),
            ca_file=self._get_str(settings, 'mqtt_ca_file'),
            certfile=self._get_str(settings, 'mqtt_certfile'),
            keyfile=self._get_str(settings, 'mqtt_keyfile'),
            tls_insecure=self._get_bool(settings, 'mqtt_tls_insecure', False),
            retain=self._get_bool(settings, 'mqtt_retain', True),
        )

        # Load Lattice configuration
        lattice = LatticeConfig(
            enabled=self._get_bool(settings, 'lattice_enabled', False),
            token=self._get_str(settings, 'lattice_token'),
            base_url=self._get_str(settings, 'lattice_base_url'),
            endpoint=self._get_str(settings, 'lattice_endpoint'),
            sandbox_token=self._get_str(settings, 'lattice_sandbox_token'),
            source_name=self._get_str(settings, 'lattice_source_name', 'DragonSync'),
            drone_rate=self._get_float(settings, 'lattice_drone_rate', 1.0),
            wd_rate=self._get_float(settings, 'lattice_wd_rate', 0.2),
        )

        # Load ADS-B configuration
        adsb = AdsbConfig(
            enabled=self._get_bool(settings, 'adsb_enabled', False),
            json_url=self._get_str(settings, 'adsb_json_url', 'http://127.0.0.1:8080/?all_with_pos'),
            uid_prefix=self._get_str(settings, 'adsb_uid_prefix', 'adsb-'),
            cot_stale=self._get_int(settings, 'adsb_cot_stale', 15),
            rate_limit=self._get_float(settings, 'adsb_rate_limit', 3.0),
            min_alt=self._get_int(settings, 'adsb_min_alt', 0),
            max_alt=self._get_int(settings, 'adsb_max_alt', 0),
        )

        # Load operational parameters
        rate_limit = self._get_float(settings, 'rate_limit', 3.0)
        max_drones = self._get_int(settings, 'max_drones', 30)
        inactivity_timeout = self._get_float(settings, 'inactivity_timeout', 60.0)
        enable_receive = self._get_bool(settings, 'enable_receive', False)

        return DragonSyncConfig(
            zmq=zmq,
            tak=tak,
            mqtt=mqtt,
            lattice=lattice,
            adsb=adsb,
            rate_limit=rate_limit,
            max_drones=max_drones,
            inactivity_timeout=inactivity_timeout,
            enable_receive=enable_receive,
        )

    def _get_str(self, settings: configparser.SectionProxy, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get string value with environment variable override.

        Args:
            settings: ConfigParser section.
            key: Configuration key.
            default: Default value if not found.

        Returns:
            String value or None.
        """
        # Check environment variable first
        env_key = f"{self.ENV_PREFIX}{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value if env_value.strip() else None

        # Get from config file
        value = settings.get(key, default)
        if value is None:
            return None

        # Return None for empty strings
        value = value.strip()
        return value if value else None

    def _get_int(self, settings: configparser.SectionProxy, key: str, default: Optional[int] = None) -> Optional[int]:
        """Get integer value with environment variable override.

        Args:
            settings: ConfigParser section.
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Integer value or None.
        """
        str_value = self._get_str(settings, key)
        if str_value is None:
            return default

        try:
            return int(str_value)
        except ValueError:
            return default

    def _get_float(self, settings: configparser.SectionProxy, key: str, default: float = 0.0) -> float:
        """Get float value with environment variable override.

        Args:
            settings: ConfigParser section.
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Float value.
        """
        str_value = self._get_str(settings, key)
        if str_value is None:
            return default

        try:
            return float(str_value)
        except ValueError:
            return default

    def _get_bool(self, settings: configparser.SectionProxy, key: str, default: bool = False) -> bool:
        """Get boolean value with environment variable override.

        Args:
            settings: ConfigParser section.
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Boolean value.
        """
        str_value = self._get_str(settings, key)
        if str_value is None:
            return default

        # Parse boolean from string
        return str_value.lower() in ('true', '1', 'yes', 'on')
