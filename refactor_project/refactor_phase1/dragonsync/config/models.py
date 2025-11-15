"""
Configuration data models for DragonSync.

These dataclasses represent the configuration structure, providing
type safety and validation.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ZMQConfig:
    """ZMQ input configuration"""
    host: str = "127.0.0.1"
    drone_port: int = 4224  # Drone telemetry stream
    status_port: int = 4225  # System status stream


@dataclass
class TAKServerConfig:
    """TAK Server connection configuration"""
    enabled: bool = False
    host: str = ""
    port: int = 8089
    protocol: str = "tcp"  # "tcp" or "udp"
    
    # TLS settings
    tls_p12_path: Optional[str] = None
    tls_password: Optional[str] = None
    skip_verify: bool = True  # For self-signed certs in dev


@dataclass
class TAKMulticastConfig:
    """TAK Multicast configuration (for ATAK on local network)"""
    enabled: bool = True
    address: str = "239.2.3.1"
    port: int = 6969
    interface: str = "0.0.0.0"
    ttl: int = 1  # Multicast TTL


@dataclass
class MQTTConfig:
    """MQTT and Home Assistant configuration"""
    enabled: bool = False
    
    # MQTT broker settings
    host: str = "127.0.0.1"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    
    # TLS settings
    tls: bool = False
    ca_file: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None
    tls_insecure: bool = False
    
    # Topic configuration
    topic: str = "wardragon/drones"
    per_drone_enabled: bool = True
    per_drone_base: str = "wardragon/drone"
    
    # Home Assistant discovery
    ha_enabled: bool = True
    ha_prefix: str = "homeassistant"
    ha_device_base: str = "wardragon_drone"


@dataclass
class LatticeConfig:
    """Anduril Lattice API configuration"""
    enabled: bool = False
    
    token: Optional[str] = None
    sandbox_token: Optional[str] = None
    
    # Either provide full base_url OR just endpoint (will prefix https://)
    base_url: Optional[str] = None
    endpoint: Optional[str] = None
    
    source_name: str = "DragonSync"
    
    # Update rates (Hz)
    drone_rate: float = 1.0  # Updates per second for drones
    wd_rate: float = 0.2  # Updates per second for WarDragon status


@dataclass
class ADSBConfig:
    """ADS-B/UAT configuration (readsb integration)"""
    enabled: bool = False
    
    json_url: str = "http://127.0.0.1:8080/?all_with_pos"
    poll_interval: float = 1.0  # Seconds between polls
    
    # Altitude filters (feet, 0 = disabled)
    min_altitude: int = 0
    max_altitude: int = 0


@dataclass
class RuntimeConfig:
    """Runtime behavior configuration"""
    rate_limit: float = 3.0  # Minimum seconds between updates per drone
    max_drones: int = 30  # Maximum tracked drones
    inactivity_timeout: float = 60.0  # Seconds before marking drone inactive
    
    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL


@dataclass
class GPSConfig:
    """GPS configuration"""
    use_static: bool = False
    static_lat: float = 0.0
    static_lon: float = 0.0
    static_alt: float = 0.0
    
    # GPSD connection (if not using static)
    gpsd_host: str = "127.0.0.1"
    gpsd_port: int = 2947


@dataclass
class DragonSyncConfig:
    """
    Master configuration container.
    
    Contains all subsystem configurations.
    """
    zmq: ZMQConfig = field(default_factory=ZMQConfig)
    tak_server: TAKServerConfig = field(default_factory=TAKServerConfig)
    tak_multicast: TAKMulticastConfig = field(default_factory=TAKMulticastConfig)
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    lattice: LatticeConfig = field(default_factory=LatticeConfig)
    adsb: ADSBConfig = field(default_factory=ADSBConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    gps: GPSConfig = field(default_factory=GPSConfig)
    
    def has_outputs(self) -> bool:
        """Check if at least one output is enabled"""
        return (
            self.tak_multicast.enabled
            or self.tak_server.enabled
            or self.mqtt.enabled
            or self.lattice.enabled
        )
