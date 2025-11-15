"""
Configuration loader for DragonSync.

Loads configuration from INI files and environment variables.
"""

import configparser
import os
from pathlib import Path
from typing import Optional, Any, Dict

from dragonsync.config.models import (
    DragonSyncConfig,
    ZMQConfig,
    TAKServerConfig,
    TAKMulticastConfig,
    MQTTConfig,
    LatticeConfig,
    ADSBConfig,
    RuntimeConfig,
    GPSConfig,
)


class ConfigLoader:
    """Load DragonSync configuration from various sources"""
    
    @staticmethod
    def from_ini(path: str) -> DragonSyncConfig:
        """
        Load configuration from INI file.
        
        Args:
            path: Path to config.ini file
            
        Returns:
            DragonSyncConfig object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is malformed
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        parser = configparser.ConfigParser()
        parser.read(config_path)
        
        # Helper to safely get values
        def get_str(section: str, key: str, default: str = "") -> str:
            if section in parser and key in parser[section]:
                return parser[section][key].strip()
            return default
        
        def get_int(section: str, key: str, default: int = 0) -> int:
            value = get_str(section, key)
            if value:
                try:
                    return int(value)
                except ValueError:
                    return default
            return default
        
        def get_float(section: str, key: str, default: float = 0.0) -> float:
            value = get_str(section, key)
            if value:
                try:
                    return float(value)
                except ValueError:
                    return default
            return default
        
        def get_bool(section: str, key: str, default: bool = False) -> bool:
            value = get_str(section, key).lower()
            if value in ('true', '1', 'yes', 'on'):
                return True
            elif value in ('false', '0', 'no', 'off'):
                return False
            return default
        
        # Parse each section
        section = "SETTINGS"  # Main section in existing config.ini
        
        # ZMQ Config
        zmq = ZMQConfig(
            host=get_str(section, "zmq_host", "127.0.0.1"),
            drone_port=get_int(section, "zmq_port", 4224),
            status_port=get_int(section, "zmq_status_port", 4225),
        )
        
        # TAK Server Config
        tak_server = TAKServerConfig(
            enabled=bool(get_str(section, "tak_host")),  # Enabled if host provided
            host=get_str(section, "tak_host", ""),
            port=get_int(section, "tak_port", 8089),
            protocol=get_str(section, "tak_protocol", "tcp"),
            tls_p12_path=get_str(section, "tak_tls_p12") or None,
            tls_password=get_str(section, "tak_tls_p12_pass") or None,
            skip_verify=get_bool(section, "tak_tls_skip_verify", True),
        )
        
        # TAK Multicast Config
        tak_multicast = TAKMulticastConfig(
            enabled=get_bool(section, "enable_multicast", True),
            address=get_str(section, "tak_multicast_addr", "239.2.3.1"),
            port=get_int(section, "tak_multicast_port", 6969),
            interface=get_str(section, "tak_multicast_interface", "0.0.0.0"),
            ttl=get_int(section, "multicast_ttl", 1),
        )
        
        # MQTT Config
        mqtt = MQTTConfig(
            enabled=get_bool(section, "mqtt_enabled", False),
            host=get_str(section, "mqtt_host", "127.0.0.1"),
            port=get_int(section, "mqtt_port", 1883),
            username=get_str(section, "mqtt_username") or None,
            password=get_str(section, "mqtt_password") or None,
            tls=get_bool(section, "mqtt_tls", False),
            ca_file=get_str(section, "mqtt_ca_file") or None,
            certfile=get_str(section, "mqtt_certfile") or None,
            keyfile=get_str(section, "mqtt_keyfile") or None,
            tls_insecure=get_bool(section, "mqtt_tls_insecure", False),
            topic=get_str(section, "mqtt_topic", "wardragon/drones"),
            per_drone_enabled=get_bool(section, "per_drone_enabled", True),
            per_drone_base=get_str(section, "per_drone_base", "wardragon/drone"),
            ha_enabled=get_bool(section, "ha_enabled", True),
            ha_prefix=get_str(section, "ha_prefix", "homeassistant"),
            ha_device_base=get_str(section, "ha_device_base", "wardragon_drone"),
        )
        
        # Lattice Config
        lattice = LatticeConfig(
            enabled=get_bool(section, "lattice_enabled", False),
            token=get_str(section, "lattice_token") or None,
            sandbox_token=get_str(section, "lattice_sandbox_token") or None,
            base_url=get_str(section, "lattice_base_url") or None,
            endpoint=get_str(section, "lattice_endpoint") or None,
            source_name=get_str(section, "lattice_source_name", "DragonSync"),
            drone_rate=get_float(section, "lattice_drone_rate", 1.0),
            wd_rate=get_float(section, "lattice_wd_rate", 0.2),
        )
        
        # ADS-B Config
        adsb = ADSBConfig(
            enabled=get_bool(section, "adsb_enabled", False),
            json_url=get_str(section, "adsb_json_url", "http://127.0.0.1:8080/?all_with_pos"),
            poll_interval=get_float(section, "adsb_poll_interval", 1.0),
            min_altitude=get_int(section, "adsb_min_alt", 0),
            max_altitude=get_int(section, "adsb_max_alt", 0),
        )
        
        # Runtime Config
        runtime = RuntimeConfig(
            rate_limit=get_float(section, "rate_limit", 3.0),
            max_drones=get_int(section, "max_drones", 30),
            inactivity_timeout=get_float(section, "inactivity_timeout", 60.0),
            log_level=get_str(section, "log_level", "INFO"),
        )
        
        # GPS Config (check for gps.ini or use static values from config)
        gps_section = "gps"
        gps = GPSConfig(
            use_static=get_bool(gps_section, "use_static_gps", False),
            static_lat=get_float(gps_section, "static_lat", 0.0),
            static_lon=get_float(gps_section, "static_lon", 0.0),
            static_alt=get_float(gps_section, "static_alt", 0.0),
            gpsd_host=get_str(gps_section, "gpsd_host", "127.0.0.1"),
            gpsd_port=get_int(gps_section, "gpsd_port", 2947),
        )
        
        return DragonSyncConfig(
            zmq=zmq,
            tak_server=tak_server,
            tak_multicast=tak_multicast,
            mqtt=mqtt,
            lattice=lattice,
            adsb=adsb,
            runtime=runtime,
            gps=gps,
        )
    
    @staticmethod
    def from_env() -> DragonSyncConfig:
        """
        Load configuration from environment variables.
        
        Useful for containerized deployments (12-factor app style).
        Environment variables use format: DRAGONSYNC_<SECTION>_<KEY>
        
        Example: DRAGONSYNC_ZMQ_HOST=192.168.1.100
        """
        def get_env(key: str, default: Any = None) -> Optional[str]:
            return os.getenv(f"DRAGONSYNC_{key}", default)
        
        # This is a skeleton - expand as needed
        zmq = ZMQConfig(
            host=get_env("ZMQ_HOST", "127.0.0.1"),
            drone_port=int(get_env("ZMQ_DRONE_PORT", "4224")),
            status_port=int(get_env("ZMQ_STATUS_PORT", "4225")),
        )
        
        # Add other sections as needed...
        
        return DragonSyncConfig(zmq=zmq)
