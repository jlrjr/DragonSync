"""
MIT License

Copyright (c) 2025 cemaxecuter

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import ssl
import socket
import signal
import logging
import argparse
import datetime
import time
import threading
import tempfile
from typing import Optional, Dict, Any
import atexit
import os

import zmq
import json
try:
    from mqtt_sink import MqttSink
except Exception:
    MqttSink = None

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

from tak_client import TAKClient
from tak_udp_client import TAKUDPClient
from drone import Drone
from system_status import SystemStatus
from manager import DroneManager
from messaging import CotMessenger
from utils import load_config, validate_config, get_str, get_int, get_float, get_bool
from telemetry_parser import parse_drone_info

UA_TYPE_MAPPING = {
    0: 'No UA type defined',
    1: 'Aeroplane/Airplane (Fixed wing)',
    2: 'Helicopter or Multirotor',
    3: 'Gyroplane',
    4: 'VTOL (Vertical Take-Off and Landing)',
    5: 'Ornithopter',
    6: 'Glider',
    7: 'Kite',
    8: 'Free Balloon',
    9: 'Captive Balloon',
    10: 'Airship (Blimp)',
    11: 'Free Fall/Parachute',
    12: 'Rocket',
    13: 'Tethered powered aircraft',
    14: 'Ground Obstacle',
    15: 'Other type',
}

# Setup logging
def setup_logging(debug: bool):
    """Set up logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if debug else logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    ch.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(ch)

logger = logging.getLogger(__name__)

def setup_tls_context(tak_tls_p12: str, tak_tls_p12_pass: Optional[str], tak_tls_skip_verify: bool) -> Optional[ssl.SSLContext]:
    """Sets up the TLS context using the provided PKCS#12 file."""
    if not tak_tls_p12:
        return None

    try:
        with open(tak_tls_p12, 'rb') as p12_file:
            p12_data = p12_file.read()
    except OSError as err:
        logger.critical("Failed to read TAK server TLS PKCS#12 file: %s.", err)
        sys.exit(1)

    p12_pass = tak_tls_p12_pass.encode() if tak_tls_p12_pass else None

    try:
        key, cert, more_certs = pkcs12.load_key_and_certificates(p12_data, p12_pass)
    except Exception as err:
        logger.critical("Failed to load TAK server TLS PKCS#12: %s.", err)
        sys.exit(1)

    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption() if not p12_pass else serialization.BestAvailableEncryption(p12_pass)
    )
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    ca_bytes = b"".join(
        cert.public_bytes(serialization.Encoding.PEM) for cert in more_certs
    ) if more_certs else b""

    # Create temporary files and ensure they are deleted on exit
    key_temp = tempfile.NamedTemporaryFile(delete=False)
    cert_temp = tempfile.NamedTemporaryFile(delete=False)
    ca_temp = tempfile.NamedTemporaryFile(delete=False)

    key_temp.write(key_bytes)
    cert_temp.write(cert_bytes)
    ca_temp.write(ca_bytes)

    key_temp_path = key_temp.name
    cert_temp_path = cert_temp.name
    ca_temp_path = ca_temp.name

    key_temp.close()
    cert_temp.close()
    ca_temp.close()

    # Register cleanup
    atexit.register(os.unlink, key_temp_path)
    atexit.register(os.unlink, cert_temp_path)
    atexit.register(os.unlink, ca_temp_path)

    try:
        tls_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        tls_context.load_cert_chain(certfile=cert_temp_path, keyfile=key_temp_path, password=p12_pass)
        if ca_bytes:
            tls_context.load_verify_locations(cafile=ca_temp_path)
        if tak_tls_skip_verify:
            tls_context.check_hostname = False
            tls_context.verify_mode = ssl.CERT_NONE
    except Exception as e:
        logger.critical(f"Failed to set up TLS context: {e}")
        sys.exit(1)

    return tls_context

def zmq_to_cot(
    zmq_host: str,
    zmq_port: int,
    zmq_status_port: Optional[int],
    tak_host: Optional[str] = None,
    tak_port: Optional[int] = None,
    tak_tls_context: Optional[ssl.SSLContext] = None,
    tak_protocol: Optional[str] = 'TCP',
    multicast_address: Optional[str] = None,
    multicast_port: Optional[int] = None,
    enable_multicast: bool = False,
    rate_limit: float = 1.0,
    max_drones: int = 30,
    inactivity_timeout: float = 60.0,
    multicast_interface: Optional[str] = None,
    multicast_ttl: int = 1,
    enable_receive: bool = False,
    lattice_sink: Optional[object] = None,
):
    """Main function to convert ZMQ messages to CoT and send to TAK server."""

    context = zmq.Context()
    telemetry_socket = context.socket(zmq.SUB)
    telemetry_socket.connect(f"tcp://{zmq_host}:{zmq_port}")
    telemetry_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    logger.debug(f"Connected to telemetry ZMQ socket at tcp://{zmq_host}:{zmq_port}")

    # Only create and connect the status_socket if zmq_status_port is provided
    if zmq_status_port:
        status_socket = context.socket(zmq.SUB)
        status_socket.connect(f"tcp://{zmq_host}:{zmq_status_port}")
        status_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.debug(f"Connected to status ZMQ socket at tcp://{zmq_host}:{zmq_status_port}")
    else:
        status_socket = None
        logger.debug("No ZMQ status port provided. Skipping status socket setup.")

    # Initialize TAK clients based on protocol
    tak_client = None
    tak_udp_client = None

    if tak_host and tak_port:
        if tak_protocol == 'TCP':
            tak_client = TAKClient(tak_host, tak_port, tak_tls_context)
            threading.Thread(target=tak_client.run_connect_loop, daemon=True).start()
        elif tak_protocol == 'UDP':
            tak_udp_client = TAKUDPClient(tak_host, tak_port)
        else:
            logger.critical(f"Unsupported TAK protocol: {tak_protocol}. Must be 'TCP' or 'UDP'.")
            sys.exit(1)

    # Initialize CotMessenger
    cot_messenger = CotMessenger(
        tak_client=tak_client,
        tak_udp_client=tak_udp_client,
        multicast_address=multicast_address,
        multicast_port=multicast_port,
        enable_multicast=enable_multicast,
        multicast_interface=multicast_interface,
        multicast_ttl=multicast_ttl,
        enable_receive=enable_receive
    )

    # Start receiver if enabled
    cot_messenger.start_receiver()

    # ---- Build sinks list (Lattice + MQTT) ----
    extra_sinks = []

    # Lattice (optional; already created above)
    if lattice_sink is not None:
        extra_sinks.append(lattice_sink)

    # MQTT sink (optional)
    mqtt_sink = None
    if config.get("mqtt_enabled"):
        if MqttSink is None:
            logger.critical("mqtt_enabled=true but mqtt_sink.py is missing or failed to import.")
        else:
            try:
                mqtt_sink = MqttSink(
                    host=config.get("mqtt_host", "127.0.0.1"),
                    port=int(config.get("mqtt_port", 1883)),
                    username=(config.get("mqtt_username") or None),
                    password=(config.get("mqtt_password") or None),
                    tls=bool(config.get("mqtt_tls", False)),
                    ca_file=(config.get("mqtt_ca_file") or None),
                    certfile=(config.get("mqtt_certfile") or None),
                    keyfile=(config.get("mqtt_keyfile") or None),
                    tls_insecure=bool(config.get("mqtt_tls_insecure", False)),

                    aggregate_topic=config.get("mqtt_topic", "wardragon/drones"),
                    retain_state=bool(config.get("mqtt_retain", True)),

                    per_drone_enabled=bool(config.get("mqtt_per_drone_enabled", False)),
                    per_drone_base=config.get("mqtt_per_drone_base", "wardragon/drone"),

                    ha_enabled=bool(config.get("mqtt_ha_enabled", False)),
                    ha_prefix=config.get("mqtt_ha_prefix", "homeassistant"),
                    ha_device_base=config.get("mqtt_ha_device_base", "wardragon_drone"),
                )
                extra_sinks.append(mqtt_sink)
                logger.info("MQTT sink enabled (aggregate=%s, per_drone=%s, HA=%s)",
                            config.get("mqtt_topic", "wardragon/drones"),
                            bool(config.get("mqtt_per_drone_enabled", False)),
                            bool(config.get("mqtt_ha_enabled", False)))
            except Exception as e:
                logger.exception("Failed to initialize MQTT sink: %s", e)

    # Initialize DroneManager with CotMessenger (no legacy MQTT args)
    drone_manager = DroneManager(
        max_drones=max_drones,
        rate_limit=rate_limit,
        inactivity_timeout=inactivity_timeout,
        cot_messenger=cot_messenger,
        extra_sinks=extra_sinks,
    )

    def signal_handler(sig, frame):
        """Handles signal interruptions for graceful shutdown."""
        logger.info("Interrupted by user")
        telemetry_socket.close()
        if status_socket:
            status_socket.close()
        if not context.closed:
            context.term()
        if tak_client:
            tak_client.close()
        if tak_udp_client:
            tak_udp_client.close()
        if cot_messenger:
            cot_messenger.close()
        if drone_manager:
            try:
                drone_manager.close()
            except Exception:
                pass
        logger.info("Cleaned up ZMQ resources")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    poller = zmq.Poller()
    poller.register(telemetry_socket, zmq.POLLIN)
    if status_socket:
        poller.register(status_socket, zmq.POLLIN)

    try:
        while True:
            try:
                socks = dict(poller.poll(timeout=1000))
            except zmq.error.ZMQError as e:
                # ETERM happens during shutdown; otherwise, log and keep going
                if e.errno == getattr(zmq, "ETERM", None):
                    break
                logger.exception(f"Poller error: {e}")
                time.sleep(0.5)
                continue
            if telemetry_socket in socks and socks[telemetry_socket] == zmq.POLLIN:
                try:
                    message = telemetry_socket.recv_json()
                except ValueError as e:
                    logger.warning(f"Telemetry JSON decode failed: {e}")
                    continue
                except Exception as e:
                    logger.exception(f"Telemetry recv failed: {e}")
                    continue
            
                try:
                    drone_info = parse_drone_info(message, UA_TYPE_MAPPING)
                except Exception as e:
                    logger.exception(f"parse_drone_info crashed; skipping message: {e}")
                    continue
            
                if not drone_info:
                    logger.debug("Parser returned no drone_info; skipping.")
                    continue

                # --- Updated logic for handling serial vs. CAA-only broadcasts ---
                if 'id' in drone_info:
                    if not drone_info['id'].startswith('drone-'):
                        drone_info['id'] = f"drone-{drone_info['id']}"
                        logger.debug(f"Ensured drone id with prefix: {drone_info['id']}")
                    else:
                        logger.debug(f"Drone id already has prefix: {drone_info['id']}")
                    drone_id = drone_info['id']

                    logger.debug(f"Drone detailts for id: {drone_id} - {drone_info}")

                    if drone_id in drone_manager.drone_dict:
                        drone = drone_manager.drone_dict[drone_id]
                        drone.update(
                            lat=drone_info.get('lat', 0.0),
                            lon=drone_info.get('lon', 0.0),
                            speed=drone_info.get('speed', 0.0),
                            vspeed=drone_info.get('vspeed', 0.0),
                            alt=drone_info.get('alt', 0.0),
                            height=drone_info.get('height', 0.0),
                            pilot_lat=drone_info.get('pilot_lat', 0.0),
                            pilot_lon=drone_info.get('pilot_lon', 0.0),
                            description=drone_info.get('description', ""),
                            mac=drone_info.get('mac', ""),
                            rssi=drone_info.get('rssi', 0),
                            home_lat=drone_info.get('home_lat', 0.0),
                            home_lon=drone_info.get('home_lon', 0.0),
                            id_type=drone_info.get('id_type', ""),
                            ua_type=drone_info.get('ua_type'),
                            ua_type_name=drone_info.get('ua_type_name', ""),
                            operator_id_type=drone_info.get('operator_id_type', ""),
                            operator_id=drone_info.get('operator_id', ""),
                            op_status=drone_info.get('op_status', ""),
                            height_type=drone_info.get('height_type', ""),
                            ew_dir=drone_info.get('ew_dir', ""),
                            direction=drone_info.get('direction'),
                            speed_multiplier=drone_info.get('speed_multiplier'),
                            pressure_altitude=drone_info.get('pressure_altitude'),
                            vertical_accuracy=drone_info.get('vertical_accuracy', ""),
                            horizontal_accuracy=drone_info.get('horizontal_accuracy', ""),
                            baro_accuracy=drone_info.get('baro_accuracy', ""),
                            speed_accuracy=drone_info.get('speed_accuracy', ""),
                            timestamp=drone_info.get('timestamp', ""),
                            timestamp_accuracy=drone_info.get('timestamp_accuracy', ""),
                            index=drone_info.get('index', 0),
                            runtime=drone_info.get('runtime', 0),
                            caa_id=drone_info.get('caa', ""),
                            freq=drone_info.get('freq')
                        )
                        logger.debug(f"Updated drone: {drone_id}")
                    else:
                        drone = Drone(
                            id=drone_info['id'],
                            lat=drone_info.get('lat', 0.0),
                            lon=drone_info.get('lon', 0.0),
                            speed=drone_info.get('speed', 0.0),
                            vspeed=drone_info.get('vspeed', 0.0),
                            alt=drone_info.get('alt', 0.0),
                            height=drone_info.get('height', 0.0),
                            pilot_lat=drone_info.get('pilot_lat', 0.0),
                            pilot_lon=drone_info.get('pilot_lon', 0.0),
                            description=drone_info.get('description', ""),
                            mac=drone_info.get('mac', ""),
                            rssi=drone_info.get('rssi', 0),
                            home_lat=drone_info.get('home_lat', 0.0),
                            home_lon=drone_info.get('home_lon', 0.0),
                            id_type=drone_info.get('id_type', ""),
                            ua_type=drone_info.get('ua_type'),
                            ua_type_name=drone_info.get('ua_type_name', ""),
                            operator_id_type=drone_info.get('operator_id_type', ""),
                            operator_id=drone_info.get('operator_id', ""),
                            op_status=drone_info.get('op_status', ""),
                            height_type=drone_info.get('height_type', ""),
                            ew_dir=drone_info.get('ew_dir', ""),
                            direction=drone_info.get('direction'),
                            speed_multiplier=drone_info.get('speed_multiplier'),
                            pressure_altitude=drone_info.get('pressure_altitude'),
                            vertical_accuracy=drone_info.get('vertical_accuracy', ""),
                            horizontal_accuracy=drone_info.get('horizontal_accuracy', ""),
                            baro_accuracy=drone_info.get('baro_accuracy', ""),
                            speed_accuracy=drone_info.get('speed_accuracy', ""),
                            timestamp=drone_info.get('timestamp', ""),
                            timestamp_accuracy=drone_info.get('timestamp_accuracy', ""),
                            index=drone_info.get('index', 0),
                            runtime=drone_info.get('runtime', 0),
                            caa_id=drone_info.get('caa', ""),
                            freq=drone_info.get('freq')
                        )
                        drone_manager.update_or_add_drone(drone_id, drone)
                        logger.debug(f"Added new drone: {drone_id}")
                else:
                    # No primary serial broadcast present (CAA-only)
                    if 'mac' in drone_info and drone_info['mac']:
                        updated = False
                        for d in drone_manager.drone_dict.values():
                            if d.mac == drone_info['mac']:
                                d.update(
                                    lat=drone_info.get('lat', 0.0),
                                    lon=drone_info.get('lon', 0.0),
                                    speed=drone_info.get('speed', 0.0),
                                    vspeed=drone_info.get('vspeed', 0.0),
                                    alt=drone_info.get('alt', 0.0),
                                    height=drone_info.get('height', 0.0),
                                    pilot_lat=drone_info.get('pilot_lat', 0.0),
                                    pilot_lon=drone_info.get('pilot_lon', 0.0),
                                    description=drone_info.get('description', ""),
                                    mac=drone_info.get('mac', ""),
                                    rssi=drone_info.get('rssi', 0),
                                    home_lat=drone_info.get('home_lat', 0.0),
                                    home_lon=drone_info.get('home_lon', 0.0),
                                    id_type=drone_info.get('id_type', ""),
                                    ua_type=drone_info.get('ua_type'),
                                    ua_type_name=drone_info.get('ua_type_name', ""),
                                    operator_id_type=drone_info.get('operator_id_type', ""),
                                    operator_id=drone_info.get('operator_id', ""),
                                    op_status=drone_info.get('op_status', ""),
                                    height_type=drone_info.get('height_type', ""),
                                    ew_dir=drone_info.get('ew_dir', ""),
                                    direction=drone_info.get('direction'),
                                    speed_multiplier=drone_info.get('speed_multiplier'),
                                    pressure_altitude=drone_info.get('pressure_altitude'),
                                    vertical_accuracy=drone_info.get('vertical_accuracy', ""),
                                    horizontal_accuracy=drone_info.get('horizontal_accuracy', ""),
                                    baro_accuracy=drone_info.get('baro_accuracy', ""),
                                    speed_accuracy=drone_info.get('speed_accuracy', ""),
                                    timestamp=drone_info.get('timestamp', ""),
                                    timestamp_accuracy=drone_info.get('timestamp_accuracy', ""),
                                    index=drone_info.get('index', 0),
                                    runtime=drone_info.get('runtime', 0),
                                    caa_id=drone_info.get('caa', ""),
                                    freq=drone_info.get('freq')
                                )
                                logger.debug(f"Updated existing drone with CAA info for MAC: {drone_info['mac']}")
                                updated = True
                                break
                        if not updated:
                            logger.debug(f"CAA-only message received for MAC {drone_info['mac']} but no matching drone record exists. Skipping for now.")
                    else:
                        logger.warning("CAA-only message received without a MAC. Skipping.")

            if status_socket and status_socket in socks and socks[status_socket] == zmq.POLLIN:
                try:
                    status_message = status_socket.recv_json()
                except ValueError as e:
                    logger.warning(f"Status JSON decode failed: {e}")
                    continue
                except Exception as e:
                    logger.exception(f"Status recv failed: {e}")
                    continue
            
                try:
                    serial_number = status_message.get('serial_number', 'unknown')
                    gps_data = status_message.get('gps_data', {})
                    lat = get_float(gps_data.get('latitude', 0.0))
                    lon = get_float(gps_data.get('longitude', 0.0))
                    alt = get_float(gps_data.get('altitude', 0.0))
                    speed = get_float(gps_data.get('speed', 0.0))
                    track = get_float(gps_data.get('track', 0.0))
            
                    system_stats = status_message.get('system_stats', {})
                    ant_sdr_temps = status_message.get('ant_sdr_temps', {})
                    pluto_temp = ant_sdr_temps.get('pluto_temp', 'N/A')
                    zynq_temp  = ant_sdr_temps.get('zynq_temp',  'N/A')
            
                    cpu_usage = get_float(system_stats.get('cpu_usage', 0.0))
                    memory = system_stats.get('memory', {})
                    memory_total = get_float(memory.get('total', 0.0)) / (1024 * 1024)
                    memory_available = get_float(memory.get('available', 0.0)) / (1024 * 1024)
                    disk = system_stats.get('disk', {})
                    disk_total = get_float(disk.get('total', 0.0)) / (1024 * 1024)
                    disk_used = get_float(disk.get('used', 0.0)) / (1024 * 1024)
                    temperature = get_float(system_stats.get('temperature', 0.0))
                    uptime = get_float(system_stats.get('uptime', 0.0))
            
                    if lat == 0.0 and lon == 0.0:
                        logger.warning("Latitude and longitude are missing or zero. Proceeding with [0.0, 0.0].")
            
                    system_status = SystemStatus(
                        serial_number=serial_number,
                        lat=lat, lon=lon, alt=alt, speed=speed, track=track,
                        cpu_usage=cpu_usage,
                        memory_total=memory_total, memory_available=memory_available,
                        disk_total=disk_total, disk_used=disk_used,
                        temperature=temperature, uptime=uptime,
                        pluto_temp=pluto_temp, zynq_temp=zynq_temp
                    )
                    cot_xml = system_status.to_cot_xml()
                except Exception as e:
                    logger.exception(f"Status handling failed: {e}")
                    continue
            
                try:
                    cot_messenger.send_cot(cot_xml)
                    logger.info("Sent CoT message to TAK/multicast.")
                except Exception as e:
                    logger.exception(f"send_cot(system) failed: {e}")
            
                if lattice_sink is not None:
                    try:
                        lattice_sink.publish_system(status_message)
                        #TODO: Add system_status to lattice sink system for health components
                        logger.debug(f"Published system status to Lattice: {status_message}")
                    except Exception as e:
                        logger.warning(f"Lattice publish_system failed: {e}")

                # Optional publish to MQTT sink if present
                if mqtt_sink is not None and hasattr(mqtt_sink, "publish_system"):
                    try:
                        mqtt_sink.publish_system(status_message)
                    except Exception as e:
                        logger.warning(f"MQTT publish_system failed: {e}")

            # Send drone updates via DroneManager
            try:
                drone_manager.send_updates()
            except Exception as e:
                logger.exception(f"send_updates failed (continuing): {e}")
    except KeyboardInterrupt:
        signal_handler(None, None)  # exits 0
    except Exception:
        logger.exception("Top-level error in zmq_to_cot — exiting for systemd restart")
        try:
            telemetry_socket.close(0)
        except Exception:
            pass
        try:
            if status_socket:
                status_socket.close(0)
        except Exception:
            pass
        try:
            if not context.closed:
                context.term()
        except Exception:
            pass
        # ensure sinks shut down
        try:
            if 'drone_manager' in locals() and drone_manager:
                drone_manager.close()
        except Exception:
            pass
        sys.exit(1)

# Configuration and Execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZMQ to CoT converter.")
    parser.add_argument("-c", "--config", type=str, help="Path to config file", default="config.ini")
    parser.add_argument("--zmq-host", help="ZMQ server host")
    parser.add_argument("--zmq-port", type=int, help="ZMQ server port for telemetry")
    parser.add_argument("--zmq-status-port", type=int, help="ZMQ server port for system status")
    parser.add_argument("--tak-host", type=str, help="TAK server hostname or IP address (optional)")
    parser.add_argument("--tak-port", type=int, help="TAK server port (optional)")
    parser.add_argument("--tak-protocol", type=str, choices=['TCP', 'UDP'], help="TAK server communication protocol (TCP or UDP)")
    parser.add_argument("--tak-tls-p12", type=str, help="Path to TAK server TLS PKCS#12 file (optional, for TCP)")
    parser.add_argument("--tak-tls-p12-pass", type=str, help="Password for TAK server TLS PKCS#12 file (optional, for TCP)")
    parser.add_argument("--tak-tls-skip-verify", action="store_true", help="(UNSAFE) Disable TLS server verification")
    parser.add_argument("--tak-multicast-addr", type=str, help="TAK multicast address (optional)")
    parser.add_argument("--tak-multicast-port", type=int, help="TAK multicast port (optional)")
    parser.add_argument("--enable-multicast", action="store_true", help="Enable sending to multicast address")
    parser.add_argument("--tak-multicast-interface", type=str, help="Multicast interface (IP or name) to use for sending multicast")
    parser.add_argument("--multicast-ttl", type=int, help="TTL for multicast packets (default: 1)")
    parser.add_argument("--enable-receive", action="store_true", help="Enable receiving multicast CoT messages")
    parser.add_argument("--rate-limit", type=float, help="Rate limit for sending CoT messages (seconds)")
    parser.add_argument("--max-drones", type=int, help="Maximum number of drones to track simultaneously")
    parser.add_argument("--inactivity-timeout", type=float, help="Time in seconds before a drone is considered inactive")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--mqtt-enabled", action="store_true", default=None,
                    help="Enable MQTT publishing of drone JSON (overrides config if set)")
    parser.add_argument("--mqtt-host", type=str, help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, help="MQTT broker port")
    parser.add_argument("--mqtt-topic", type=str, help="MQTT topic for drone messages")
    parser.add_argument("--mqtt-username", type=str, help="MQTT username")
    parser.add_argument("--mqtt-password", type=str, help="MQTT password")
    parser.add_argument("--mqtt-tls", action="store_true", help="Enable MQTT TLS")
    parser.add_argument("--mqtt-ca-file", type=str, help="Path to CA file for MQTT TLS")
    parser.add_argument("--mqtt-certfile", type=str, help="Path to client certificate for MQTT TLS (optional)")
    parser.add_argument("--mqtt-keyfile", type=str, help="Path to client key for MQTT TLS (optional)")
    parser.add_argument("--mqtt-tls-insecure", action="store_true", help="(UNSAFE) Skip MQTT TLS hostname/chain verification")
    parser.add_argument("--mqtt-retain", action="store_true", default=None,
                        help="Retain published state topics (default: true if unset)")
    parser.add_argument("--mqtt-per-drone-enabled", action="store_true", default=None,
                        help="Publish one message per drone to base/<drone_id>")
    parser.add_argument("--mqtt-per-drone-base", type=str,
                        help="Base topic for per-drone messages (default: wardragon/drone)")
    parser.add_argument("--mqtt-ha-enabled", action="store_true", default=None,
                        help="Enable Home Assistant MQTT Discovery")
    parser.add_argument("--mqtt-ha-prefix", type=str,
                        help="HA discovery prefix (default: homeassistant)")
    parser.add_argument("--mqtt-ha-device-base", type=str,
                        help="Base used for HA device unique_id (default: wardragon_drone)")
    # ---- Lattice (optional) ----
    parser.add_argument("--lattice-enabled", action="store_true", help="Enable publishing to Lattice")
    parser.add_argument("--lattice-token", type=str, help="Lattice environment token (or env LATTICE_TOKEN / ENVIRONMENT_TOKEN)")
    parser.add_argument("--lattice-base-url", type=str, help="Full base URL, e.g. https://lattice-XXXX.env.sandboxes.developer.anduril.com (or env LATTICE_BASE_URL)")
    parser.add_argument("--lattice-endpoint", type=str, help="Endpoint host only (no scheme) to build base_url, e.g. lattice-XXXX.env.sandboxes.developer.anduril.com (or env LATTICE_ENDPOINT)")
    parser.add_argument("--lattice-sandbox-token", type=str, help="Sandboxes Bearer token (or env SANDBOXES_TOKEN / LATTICE_SANDBOX_TOKEN)")
    parser.add_argument("--lattice-source-name", type=str, help="Provenance source name (or env LATTICE_SOURCE_NAME)")
    parser.add_argument("--lattice-drone-rate", type=float, help="Drone publish rate to Lattice (Hz)")
    parser.add_argument("--lattice-wd-rate", type=float, help="WarDragon publish rate to Lattice (Hz)")
    args = parser.parse_args()

    # Load config file if provided
    config_values = {}
    if args.config:
        config_values = load_config(args.config)

    setup_logging(args.debug)
    logger.info("Starting ZMQ to CoT converter with log level: %s", "DEBUG" if args.debug else "INFO")

    # Retrieve 'tak_host' and 'tak_port' with precedence
    tak_host = args.tak_host if args.tak_host is not None else get_str(config_values.get("tak_host"))
    tak_port = args.tak_port if args.tak_port is not None else get_int(config_values.get("tak_port"), None)

    if tak_host and tak_port:
        # Fetch the raw protocol value from command-line or config
        tak_protocol_raw = args.tak_protocol if args.tak_protocol is not None else config_values.get("tak_protocol")
        # Use get_str to sanitize the input, defaulting to "TCP" if necessary
        tak_protocol_sanitized = get_str(tak_protocol_raw, "TCP")
        # Convert to uppercase
        tak_protocol = tak_protocol_sanitized.upper()
    else:
        # If TAK host and port are not provided, set tak_protocol to None
        tak_protocol = None
        logger.info("TAK host and port not provided. 'tak_protocol' will be ignored.")

    tak_multicast_interface = args.tak_multicast_interface if args.tak_multicast_interface is not None else get_str(config_values.get("tak_multicast_interface"))

    # Assign configuration values, giving precedence to command-line arguments
    config = {
        "zmq_host": args.zmq_host if args.zmq_host is not None else get_str(config_values.get("zmq_host", "127.0.0.1")),
        "zmq_port": args.zmq_port if args.zmq_port is not None else get_int(config_values.get("zmq_port"), 4224),
        "zmq_status_port": args.zmq_status_port if args.zmq_status_port is not None else get_int(config_values.get("zmq_status_port"), None),
        "tak_host": tak_host,
        "tak_port": tak_port,
        "tak_protocol": tak_protocol,
        "tak_tls_p12": args.tak_tls_p12 if args.tak_tls_p12 is not None else get_str(config_values.get("tak_tls_p12")),
        "tak_tls_p12_pass": args.tak_tls_p12_pass if args.tak_tls_p12_pass is not None else get_str(config_values.get("tak_tls_p12_pass")),
        "tak_tls_skip_verify": args.tak_tls_skip_verify if args.tak_tls_skip_verify else get_bool(config_values.get("tak_tls_skip_verify"), False),
        "tak_multicast_addr": args.tak_multicast_addr if args.tak_multicast_addr is not None else get_str(config_values.get("tak_multicast_addr")),
        "tak_multicast_port": args.tak_multicast_port if args.tak_multicast_port is not None else get_int(config_values.get("tak_multicast_port"), None),
        "enable_multicast": args.enable_multicast or get_bool(config_values.get("enable_multicast"), False),
        "rate_limit": args.rate_limit if args.rate_limit is not None else get_float(config_values.get("rate_limit", 1.0)),
        "max_drones": args.max_drones if args.max_drones is not None else get_int(config_values.get("max_drones", 30)),
        "inactivity_timeout": args.inactivity_timeout if args.inactivity_timeout is not None else get_float(config_values.get("inactivity_timeout", 60.0)),
        "tak_multicast_interface": tak_multicast_interface,
        "multicast_ttl": args.multicast_ttl if args.multicast_ttl is not None else get_int(config_values.get("multicast_ttl", 1)),
        "enable_receive": args.enable_receive or get_bool(config_values.get("enable_receive", False)),
        "mqtt_enabled": args.mqtt_enabled if hasattr(args, "mqtt_enabled") and args.mqtt_enabled is not None else get_bool(config_values.get("mqtt_enabled", False)),
        "mqtt_host": args.mqtt_host if hasattr(args, "mqtt_host") and args.mqtt_host is not None else get_str(config_values.get("mqtt_host", "127.0.0.1")),
        "mqtt_port": args.mqtt_port if hasattr(args, "mqtt_port") and args.mqtt_port is not None else get_int(config_values.get("mqtt_port", 1883)),
        "mqtt_topic": args.mqtt_topic if hasattr(args, "mqtt_topic") and args.mqtt_topic is not None else get_str(config_values.get("mqtt_topic", "wardragon/drones")),
        "mqtt_username": args.mqtt_username if hasattr(args, "mqtt_username") and args.mqtt_username is not None else get_str(config_values.get("mqtt_username")),
        "mqtt_password": args.mqtt_password if hasattr(args, "mqtt_password") and args.mqtt_password is not None else get_str(config_values.get("mqtt_password")),
        "mqtt_tls": args.mqtt_tls if hasattr(args, "mqtt_tls") and args.mqtt_tls is not None else get_bool(config_values.get("mqtt_tls", False)),
        "mqtt_ca_file": args.mqtt_ca_file if hasattr(args, "mqtt_ca_file") and args.mqtt_ca_file is not None else get_str(config_values.get("mqtt_ca_file")),
        "mqtt_certfile": args.mqtt_certfile if hasattr(args, "mqtt_certfile") and args.mqtt_certfile is not None else get_str(config_values.get("mqtt_certfile")),
        "mqtt_keyfile": args.mqtt_keyfile if hasattr(args, "mqtt_keyfile") and args.mqtt_keyfile is not None else get_str(config_values.get("mqtt_keyfile")),
        "mqtt_tls_insecure": args.mqtt_tls_insecure if hasattr(args, "mqtt_tls_insecure") and args.mqtt_tls_insecure is not None else get_bool(config_values.get("mqtt_tls_insecure", False)),
        "mqtt_retain": args.mqtt_retain if hasattr(args, "mqtt_retain") and args.mqtt_retain is not None else get_bool(config_values.get("mqtt_retain", True)),
        "mqtt_per_drone_enabled": args.mqtt_per_drone_enabled if hasattr(args, "mqtt_per_drone_enabled") and args.mqtt_per_drone_enabled is not None else get_bool(config_values.get("mqtt_per_drone_enabled", False)),
        "mqtt_per_drone_base": args.mqtt_per_drone_base if hasattr(args, "mqtt_per_drone_base") and args.mqtt_per_drone_base is not None else get_str(config_values.get("mqtt_per_drone_base", "wardragon/drone")),
        "mqtt_ha_enabled": args.mqtt_ha_enabled if hasattr(args, "mqtt_ha_enabled") and args.mqtt_ha_enabled is not None else get_bool(config_values.get("mqtt_ha_enabled", False)),
        "mqtt_ha_prefix": args.mqtt_ha_prefix if hasattr(args, "mqtt_ha_prefix") and args.mqtt_ha_prefix is not None else get_str(config_values.get("mqtt_ha_prefix", "homeassistant")),
        "mqtt_ha_device_base": args.mqtt_ha_device_base if hasattr(args, "mqtt_ha_device_base") and args.mqtt_ha_device_base is not None else get_str(config_values.get("mqtt_ha_device_base", "wardragon_drone")),

        # ---- Lattice (optional) config block ----
        "lattice_enabled": args.lattice_enabled or get_bool(config_values.get("lattice_enabled"), False),
        # Environment (Authorization) token
        "lattice_token": args.lattice_token if args.lattice_token is not None else (
            os.getenv("LATTICE_TOKEN") or os.getenv("ENVIRONMENT_TOKEN") or get_str(config_values.get("lattice_token"))
        ),
        # Prefer full base URL if provided
        "lattice_base_url": args.lattice_base_url if args.lattice_base_url is not None else (
            os.getenv("LATTICE_BASE_URL") or get_str(config_values.get("lattice_base_url"))
        ),
        # Or endpoint host to build base_url
        "lattice_endpoint": args.lattice_endpoint if args.lattice_endpoint is not None else (
            os.getenv("LATTICE_ENDPOINT") or get_str(config_values.get("lattice_endpoint"))
        ),
        # Sandboxes token for anduril-sandbox-authorization
        "lattice_sandbox_token": args.lattice_sandbox_token if args.lattice_sandbox_token is not None else (
            os.getenv("SANDBOXES_TOKEN") or os.getenv("LATTICE_SANDBOX_TOKEN") or get_str(config_values.get("lattice_sandbox_token"))
        ),
        "lattice_source_name": args.lattice_source_name if args.lattice_source_name is not None else (
            os.getenv("LATTICE_SOURCE_NAME") or get_str(config_values.get("lattice_source_name", "DragonSync"))
        ),
        "lattice_drone_rate": args.lattice_drone_rate if args.lattice_drone_rate is not None else get_float(config_values.get("lattice_drone_rate", 1.0)),
        "lattice_wd_rate": args.lattice_wd_rate if args.lattice_wd_rate is not None else get_float(config_values.get("lattice_wd_rate", 0.2)),
    }

    
    # Validate configuration
    try:
        validate_config(config)
    except ValueError as ve:
        logger.critical(f"Configuration Error: {ve}")
        sys.exit(1)

    # Setup TLS context only if tak_protocol is set (which implies tak_host and tak_port are provided)
    tak_tls_context = setup_tls_context(
        tak_tls_p12=config["tak_tls_p12"],
        tak_tls_p12_pass=config["tak_tls_p12_pass"],
        tak_tls_skip_verify=config["tak_tls_skip_verify"]
    ) if config["tak_protocol"] == 'TCP' and config["tak_tls_p12"] else None

    # ---- Optional Lattice sink construction (import-protected) ----
    lattice_sink = None
    if config["lattice_enabled"]:
        try:
            from lattice_sink import LatticeSink  # local helper that wraps the Lattice SDK
        except Exception as e:
            logger.warning(f"Lattice enabled, but lattice_sink import failed: {e}")
            LatticeSink = None  # type: ignore
        if "LatticeSink" in locals() and LatticeSink is not None:
            token = (config.get("lattice_token") or "").strip()
            if not token:
                logger.warning("Lattice enabled, but no environment token provided (set --lattice-token or env LATTICE_TOKEN/ENVIRONMENT_TOKEN). Disabling.")
            else:
                try:
                    # Resolve base_url
                    base_url = (config.get("lattice_base_url") or "").strip()
                    if not base_url:
                        endpoint = (config.get("lattice_endpoint") or "").strip()
                        if endpoint:
                            base_url = endpoint if endpoint.startswith(("http://", "https://")) else f"https://{endpoint}"
                    sb = (config.get("lattice_sandbox_token") or "").strip()
                    env_tok_len = len(token)
                    sb_tok_len = len(sb)
                    logger.debug(f"Lattice base_url resolved: {base_url!r}, env_token_len={env_tok_len}, sandbox_token_len={sb_tok_len}")
                    lattice_sink = LatticeSink(
                        token=token,
                        base_url=base_url or None,
                        drone_hz=config.get("lattice_drone_rate", 1.0),
                        wardragon_hz=config.get("lattice_wd_rate", 0.2),
                        source_name=config.get("lattice_source_name", "DragonSync"),
                        sandbox_token=sb or None,
                    )
                    logger.info("Lattice sink enabled.")
                except Exception as e:
                    logger.exception(f"Failed to initialize Lattice sink: {e}")

    zmq_to_cot(
        zmq_host=config["zmq_host"],
        zmq_port=config["zmq_port"],
        zmq_status_port=config["zmq_status_port"],
        tak_host=config["tak_host"],
        tak_port=config["tak_port"],
        tak_tls_context=tak_tls_context,
        tak_protocol=config["tak_protocol"],
        multicast_address=config["tak_multicast_addr"],
        multicast_port=config["tak_multicast_port"],
        enable_multicast=config["enable_multicast"],
        rate_limit=config["rate_limit"],
        max_drones=config["max_drones"],
        inactivity_timeout=config["inactivity_timeout"],
        multicast_interface=config["tak_multicast_interface"],
        multicast_ttl=config["multicast_ttl"],
        enable_receive=config["enable_receive"],
        lattice_sink=lattice_sink,
    )
