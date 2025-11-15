"""
Configuration validator for DragonSync.

Validates configuration and returns helpful error messages.
"""

from pathlib import Path
from typing import List
from dragonsync.config.models import DragonSyncConfig


class ConfigValidator:
    """Validate DragonSync configuration"""
    
    @staticmethod
    def validate(config: DragonSyncConfig) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors: List[str] = []
        
        # Check that at least one output is enabled
        if not config.has_outputs():
            errors.append(
                "No outputs enabled! Enable at least one: "
                "TAK multicast, TAK server, MQTT, or Lattice"
            )
        
        # Validate ZMQ config
        if not (1024 <= config.zmq.drone_port <= 65535):
            errors.append(f"Invalid ZMQ drone port: {config.zmq.drone_port}")
        if not (1024 <= config.zmq.status_port <= 65535):
            errors.append(f"Invalid ZMQ status port: {config.zmq.status_port}")
        
        # Validate TAK Server config
        if config.tak_server.enabled:
            if not config.tak_server.host:
                errors.append("TAK server enabled but no host specified")
            if not (1 <= config.tak_server.port <= 65535):
                errors.append(f"Invalid TAK server port: {config.tak_server.port}")
            if config.tak_server.protocol not in ("tcp", "udp"):
                errors.append(
                    f"Invalid TAK protocol: {config.tak_server.protocol} "
                    "(must be 'tcp' or 'udp')"
                )
            
            # Check TLS files exist if specified
            if config.tak_server.tls_p12_path:
                p12_path = Path(config.tak_server.tls_p12_path)
                if not p12_path.exists():
                    errors.append(f"TAK TLS P12 file not found: {config.tak_server.tls_p12_path}")
        
        # Validate TAK Multicast config
        if config.tak_multicast.enabled:
            if not (1 <= config.tak_multicast.port <= 65535):
                errors.append(f"Invalid multicast port: {config.tak_multicast.port}")
            if not (1 <= config.tak_multicast.ttl <= 255):
                errors.append(f"Invalid multicast TTL: {config.tak_multicast.ttl}")
        
        # Validate MQTT config
        if config.mqtt.enabled:
            if not config.mqtt.host:
                errors.append("MQTT enabled but no host specified")
            if not (1 <= config.mqtt.port <= 65535):
                errors.append(f"Invalid MQTT port: {config.mqtt.port}")
            
            # Check TLS files if TLS enabled
            if config.mqtt.tls:
                if config.mqtt.ca_file:
                    ca_path = Path(config.mqtt.ca_file)
                    if not ca_path.exists():
                        errors.append(f"MQTT CA file not found: {config.mqtt.ca_file}")
                if config.mqtt.certfile:
                    cert_path = Path(config.mqtt.certfile)
                    if not cert_path.exists():
                        errors.append(f"MQTT cert file not found: {config.mqtt.certfile}")
                if config.mqtt.keyfile:
                    key_path = Path(config.mqtt.keyfile)
                    if not key_path.exists():
                        errors.append(f"MQTT key file not found: {config.mqtt.keyfile}")
        
        # Validate Lattice config
        if config.lattice.enabled:
            if not config.lattice.token and not config.lattice.sandbox_token:
                errors.append("Lattice enabled but no token specified")
            if not config.lattice.base_url and not config.lattice.endpoint:
                errors.append("Lattice enabled but no base_url or endpoint specified")
            if config.lattice.drone_rate <= 0:
                errors.append(f"Invalid Lattice drone rate: {config.lattice.drone_rate}")
            if config.lattice.wd_rate <= 0:
                errors.append(f"Invalid Lattice wd_rate: {config.lattice.wd_rate}")
        
        # Validate ADS-B config
        if config.adsb.enabled:
            if not config.adsb.json_url:
                errors.append("ADS-B enabled but no json_url specified")
            if config.adsb.poll_interval <= 0:
                errors.append(f"Invalid ADS-B poll interval: {config.adsb.poll_interval}")
            if config.adsb.min_altitude < 0:
                errors.append(f"Invalid ADS-B min_altitude: {config.adsb.min_altitude}")
            if config.adsb.max_altitude < 0:
                errors.append(f"Invalid ADS-B max_altitude: {config.adsb.max_altitude}")
            if (config.adsb.max_altitude > 0 and 
                config.adsb.min_altitude > config.adsb.max_altitude):
                errors.append(
                    f"ADS-B min_altitude ({config.adsb.min_altitude}) "
                    f"greater than max_altitude ({config.adsb.max_altitude})"
                )
        
        # Validate Runtime config
        if config.runtime.rate_limit < 0:
            errors.append(f"Invalid rate_limit: {config.runtime.rate_limit}")
        if config.runtime.max_drones <= 0:
            errors.append(f"Invalid max_drones: {config.runtime.max_drones}")
        if config.runtime.inactivity_timeout <= 0:
            errors.append(f"Invalid inactivity_timeout: {config.runtime.inactivity_timeout}")
        if config.runtime.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            errors.append(f"Invalid log_level: {config.runtime.log_level}")
        
        # Validate GPS config
        if config.gps.use_static:
            if not (-90 <= config.gps.static_lat <= 90):
                errors.append(f"Invalid static GPS latitude: {config.gps.static_lat}")
            if not (-180 <= config.gps.static_lon <= 180):
                errors.append(f"Invalid static GPS longitude: {config.gps.static_lon}")
        
        return errors
