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

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

try:
    import paho.mqtt.client as mqtt
except Exception as e:
    mqtt = None  # type: ignore

_log = logging.getLogger(__name__)


class MqttSink:
    """
    Generic MQTT sink with optional Home Assistant discovery.

    Exposed methods (used by DroneManager):
      - publish_drone(drone_obj)
      - publish_pilot(drone_id, lat, lon, alt=0.0)
      - publish_home(drone_id, lat, lon, alt=0.0)
      - close()

    Features:
      - Aggregate JSON publish to a single topic (optional)
      - Per-drone JSON publish to `<per_drone_base>/<drone_id>` (optional)
      - HA discovery (optional):
          * rich per-drone sensors (lat/lon/alt/speed/etc.)
          * a device_tracker per drone for a clean Map dot
      - Lightweight in-memory state cache so pilot/home updates merge cleanly.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls: bool = False,
        ca_file: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        tls_insecure: bool = False,
        client_id: Optional[str] = None,
        keepalive: int = 60,
        qos: int = 0,
        # Aggregate / per-drone topics
        aggregate_topic: Optional[str] = "wardragon/drones",
        per_drone_enabled: bool = False,
        per_drone_base: str = "wardragon/drone",
        retain_state: bool = True,
        # Home Assistant
        ha_enabled: bool = False,
        ha_prefix: str = "homeassistant",
        ha_device_base: str = "wardragon_drone",
    ) -> None:
        if mqtt is None:
            raise RuntimeError("paho-mqtt not installed but required for MqttSink")

        self.qos = int(qos)
        self.retain_state = bool(retain_state)

        self.aggregate_topic = aggregate_topic or None
        self.per_drone_enabled = bool(per_drone_enabled)
        self.per_drone_base = per_drone_base.strip().strip("/")

        self.ha_enabled = bool(ha_enabled)
        self.ha_prefix = ha_prefix.strip().strip("/")
        self.ha_device_base = ha_device_base.strip()

        self._seen_for_ha: set[str] = set()
        self._state_cache: Dict[str, Dict[str, Any]] = {}

        # --- MQTT client setup ---
        self.client = mqtt.Client(client_id=client_id, clean_session=True)  # type: ignore
        try:
            self.client.enable_logger(_log)  # paho >= 1.6
        except Exception:
            pass

        if username is not None:
            self.client.username_pw_set(username, password)

        if tls:
            try:
                self.client.tls_set(
                    ca_certs=ca_file,
                    certfile=certfile,
                    keyfile=keyfile,
                )
                self.client.tls_insecure_set(bool(tls_insecure))
            except Exception as e:
                _log.critical("MqttSink TLS configuration failed: %s", e)
                raise

        # NOTE: on_connect repushes HA discovery + last known state for determinism after restarts
        def _on_connect(c, u, flags, rc, props=None):
            if rc == 0:
                _log.info("MqttSink connected to %s:%s", host, port)
                try:
                    # Clear discovery-guard so we advertise again on reconnect
                    self._seen_for_ha.clear()
                    # Re-publish HA discovery and last state for all cached drones
                    if self.ha_enabled and self.per_drone_enabled and self._state_cache:
                        for drone_id, state in self._state_cache.items():
                            st = self._per_drone_topic(drone_id)
                            try:
                                self._publish_ha_device_tracker(drone_id, st, state)
                                self._publish_ha_sensors(drone_id, st, state)
                            except Exception as e:
                                _log.warning("Reconnect HA discovery failed for %s: %s", drone_id, e)
                            # Re-publish the most recent per-drone state (retained)
                            try:
                                payload = json.dumps(state, default=_json_default)
                                info = self.client.publish(st, payload, qos=self.qos, retain=self.retain_state)
                                self._warn_if_publish_failed(info)
                            except Exception as e:
                                _log.warning("Reconnect per-drone state publish failed for %s: %s", drone_id, e)
                except Exception as e:
                    _log.warning("on_connect refresh failed: %s", e)
            else:
                _log.warning("MqttSink connect rc=%s", rc)

        def _on_disconnect(c, u, rc, props=None):
            _log.info("MqttSink disconnected rc=%s", rc)

        self.client.on_connect = _on_connect
        self.client.on_disconnect = _on_disconnect

        try:
            self.client.connect(host, int(port), keepalive=keepalive)
            self.client.loop_start()
            # best-effort wait for connection (if supported)
            is_conn = getattr(self.client, "is_connected", None)
            deadline = time.time() + 3.0
            while callable(is_conn) and not self.client.is_connected() and time.time() < deadline:
                time.sleep(0.05)
        except Exception as e:
            _log.critical("MqttSink failed to connect: %s", e)
            raise

    # ────────────────────────────────────────────────
    # Public API used by DroneManager
    # ────────────────────────────────────────────────

    def publish_drone(self, d: Any) -> None:
        """Publish full drone state (aggregate + per-drone), HA discovery once."""
        drone_id = str(_get_attr(d, "id", "unknown")) or "unknown"

        # Build a clean, JSON-friendly dict
        payload = self._drone_to_state(d)

        # Update cache & publish
        self._merge_and_publish(drone_id, payload)

        # HA discovery (once per drone) — requires per-drone topics
        if self.ha_enabled and self.per_drone_enabled and drone_id not in self._seen_for_ha:
            try:
                state_topic = self._per_drone_topic(drone_id)
                # device_tracker for clean Map dot
                self._publish_ha_device_tracker(drone_id, state_topic, payload)
                # rich sensors for telemetry dashboards
                self._publish_ha_sensors(drone_id, state_topic, payload)
                self._seen_for_ha.add(drone_id)
            except Exception as e:
                _log.warning("HA discovery failed for %s: %s", drone_id, e)

    def publish_pilot(self, drone_id: str, lat: float, lon: float, alt: float = 0.0) -> None:
        """Merge pilot fields into the per-drone state and republish (if enabled)."""
        drone_id = str(drone_id)
        if drone_id.startswith("pilot-"):
            drone_id = drone_id[len("pilot-") :]

        patch = {
            "pilot_lat": _f(lat),
            "pilot_lon": _f(lon),
            "pilot_alt": _f(alt),
        }
        self._merge_and_publish(drone_id, patch)

    def publish_home(self, drone_id: str, lat: float, lon: float, alt: float = 0.0) -> None:
        """Merge home fields into the per-drone state and republish (if enabled)."""
        drone_id = str(drone_id)
        if drone_id.startswith("home-"):
            drone_id = drone_id[len("home-") :]

        patch = {
            "home_lat": _f(lat),
            "home_lon": _f(lon),
            "home_alt": _f(alt),
        }
        self._merge_and_publish(drone_id, patch)

    def close(self) -> None:
        """Stop MQTT loop and disconnect cleanly."""
        try:
            self.client.loop_stop()
        except Exception as e:
            _log.warning("MqttSink loop_stop error: %s", e)
        try:
            self.client.disconnect()
        except Exception as e:
            _log.warning("MqttSink disconnect error: %s", e)

    # ────────────────────────────────────────────────
    # Internals
    # ────────────────────────────────────────────────

    def _merge_and_publish(self, drone_id: str, patch: Dict[str, Any]) -> None:
        """
        Merge fields into cache and publish to aggregate/per-drone as configured.
        """
        cur = self._state_cache.get(drone_id, {})
        cur.update(patch)
        cur["id"] = drone_id
        self._state_cache[drone_id] = cur

        # Aggregate stream (single topic, all drones as independent messages)
        if self.aggregate_topic:
            try:
                payload = json.dumps(cur, default=_json_default)
                info = self.client.publish(self.aggregate_topic, payload, qos=self.qos, retain=self.retain_state)
                self._warn_if_publish_failed(info)
            except Exception as e:
                _log.warning("Aggregate publish failed for %s: %s", drone_id, e)

        # Per-drone state (required for HA sensors/device_tracker)
        if self.per_drone_enabled:
            try:
                topic = self._per_drone_topic(drone_id)
                payload = json.dumps(cur, default=_json_default)
                info = self.client.publish(topic, payload, qos=self.qos, retain=self.retain_state)
                self._warn_if_publish_failed(info)
            except Exception as e:
                _log.warning("Per-drone publish failed for %s: %s", drone_id, e)

    def _warn_if_publish_failed(self, info) -> None:
        try:
            rc = getattr(info, "rc", None)
            if rc is not None and rc != mqtt.MQTT_ERR_SUCCESS:  # type: ignore
                _log.warning("MQTT publish returned rc=%s", rc)
        except Exception:
            pass

    def _per_drone_topic(self, drone_id: str) -> str:
        return f"{self.per_drone_base}/{drone_id}"

    def _drone_to_state(self, d: Any) -> Dict[str, Any]:
        """
        Convert the Drone object (or dict) into a compact, JSON-friendly state dict.
        """
        def g(name, default=None):
            return _get_attr(d, name, default)

        # freq: allow Hz or MHz; keep raw and also include computed MHz for convenience
        freq = g("freq", None)
        freq_mhz = _fmt_freq_mhz(freq)

        # Optional horizontal accuracy (meters) if your parser provides it
        horiz_acc = g("horizontal_accuracy", 0)

        state = {
            "id": g("id", "unknown"),
            "description": g("description", ""),

            # existing keys used elsewhere
            "lat": _f(g("lat", 0.0)),
            "lon": _f(g("lon", 0.0)),

            # HA device_tracker attributes for map placement
            "latitude": _f(g("lat", 0.0)),
            "longitude": _f(g("lon", 0.0)),
            "gps_accuracy": _f(horiz_acc),

            "alt": _f(g("alt", 0.0)),
            "height": _f(g("height", 0.0)),
            "speed": _f(g("speed", 0.0)),
            "vspeed": _f(g("vspeed", 0.0)),
            "direction": _f(g("direction", 0.0)),
            "rssi": _f(g("rssi", 0.0)),
            "pilot_lat": _f(g("pilot_lat", 0.0)),
            "pilot_lon": _f(g("pilot_lon", 0.0)),
            "home_lat": _f(g("home_lat", 0.0)),
            "home_lon": _f(g("home_lon", 0.0)),
            "mac": g("mac", ""),
            "id_type": g("id_type", ""),
            "ua_type": g("ua_type", None),
            "ua_type_name": g("ua_type_name", ""),
            "operator_id_type": g("operator_id_type", ""),
            "operator_id": g("operator_id", ""),
            "op_status": g("op_status", ""),
            "height_type": g("height_type", ""),
            "ew_dir": g("ew_dir", ""),
            "timestamp": g("timestamp", ""),
            "index": g("index", 0),
            "runtime": g("runtime", 0),
            # radio
            "freq": freq,
            "freq_mhz": freq_mhz,
        }
        return state

    # ─────────────────────────── Home Assistant discovery ─────────────────────────

    def _publish_ha_sensors(self, drone_id: str, state_topic: str, sample: Dict[str, Any]) -> None:
        """
        Rich per-drone sensors (lat/lon/alt/speed/etc.) — mirrors your ZMQ script style.
        """
        base_unique = f"{self.ha_device_base}_{drone_id}"
        device = {
            "identifiers": [f"{self.ha_device_base}:{drone_id}"],
            "name": f"{drone_id}",                 # clean label: just the ID
            "model": sample.get("description") or "Remote ID",
        }

        def sensor(uid_suffix: str, name: str, template: str, unit: Optional[str] = None,
                   device_class: Optional[str] = None, icon: Optional[str] = None):
            uid = f"{base_unique}_{uid_suffix}"
            topic = f"{self.ha_prefix}/sensor/{uid}/config"
            payload = {
                "name": name,
                "state_topic": state_topic,
                "unique_id": uid,
                "device": device,
                "value_template": template,
            }
            if unit:
                payload["unit_of_measurement"] = unit
            if device_class:
                payload["device_class"] = device_class
            if icon:
                payload["icon"] = icon
            self.client.publish(topic, json.dumps(payload), qos=self.qos, retain=True)

        # Core kinematics / position
        sensor("lat", "Latitude", "{{ value_json.lat | default(0) | float }}", "°", icon="mdi:map-marker")
        sensor("lon", "Longitude", "{{ value_json.lon | default(0) | float }}", "°", icon="mdi:map-marker")
        sensor("alt", "Altitude", "{{ value_json.alt | default(0) | float }}", "m", device_class="distance", icon="mdi:map-marker-distance")
        sensor("speed", "Speed", "{{ value_json.speed | default(0) | float }}", "m/s", device_class="speed", icon="mdi:speedometer")
        sensor("vspeed", "Vertical Speed", "{{ value_json.vspeed | default(0) | float }}", "m/s", icon="mdi:axis-z-arrow")
        sensor("height", "AGL", "{{ value_json.height | default(0) | float }}", "m", icon="mdi:altimeter")
        sensor("dir", "Course", "{{ value_json.direction | default(0) | float }}", "°", icon="mdi:compass")

        # Pilot/Home
        sensor("pilot_lat", "Pilot Latitude", "{{ value_json.pilot_lat | default(0) | float }}", "°", icon="mdi:account")
        sensor("pilot_lon", "Pilot Longitude", "{{ value_json.pilot_lon | default(0) | float }}", "°", icon="mdi:account")
        sensor("home_lat", "Home Latitude", "{{ value_json.home_lat | default(0) | float }}", "°", icon="mdi:home")
        sensor("home_lon", "Home Longitude", "{{ value_json.home_lon | default(0) | float }}", "°", icon="mdi:home")

        # Radio / link (safe default for None)
        sensor("rssi", "Signal (RSSI)", "{{ value_json.rssi | default(0) | float }}", "dBm", device_class="signal_strength", icon="mdi:wifi")
        sensor("freq", "Radio Freq (MHz)", "{{ value_json.freq_mhz | float(0) }}", "MHz", icon="mdi:radio-tower")

        # Metadata (non-numeric; leave device_class empty)
        sensor("ua_type", "UA Type", "{{ value_json.ua_type_name | default('') }}", icon="mdi:airplane")
        sensor("op_id", "Operator ID", "{{ value_json.operator_id | default('') }}", icon="mdi:id-card")

        # Primary label-only sensor for the device page
        sensor("main", "Drone", "{{ value_json.description | default('Drone') }}", icon="mdi:drone")

    def _publish_ha_device_tracker(self, drone_id: str, attr_topic: str, sample: Dict[str, Any]) -> None:
        """
        Minimal HA discovery for a map dot: one MQTT device_tracker per drone.
        We publish 'not_home' on a small /state topic, and the attributes (lat/lon/etc.)
        live on the per-drone JSON topic.
        """
        base_unique = f"{self.ha_device_base}_{drone_id}"
        device = {
            "identifiers": [f"{self.ha_device_base}:{drone_id}"],
            "name": f"{drone_id}",                 # clean label
            "model": sample.get("description") or "Remote ID",
        }
        cfg_topic = f"{self.ha_prefix}/device_tracker/{base_unique}/config"
        state_topic = f"{attr_topic}/state"

        payload = {
            "name": f"{drone_id}",
            "unique_id": base_unique,
            "device": device,
            "source_type": "gps",
            "state_topic": state_topic,           # textual state (we set 'not_home')
            "json_attributes_topic": attr_topic,  # lat/lon/etc. are attributes
            "icon": "mdi:drone",
        }
        # Retain discovery + default state
        self.client.publish(cfg_topic, json.dumps(payload), qos=self.qos, retain=True)
        self.client.publish(state_topic, "not_home", qos=self.qos, retain=True)


# ────────────────────────────────────────────────
# Small helpers
# ────────────────────────────────────────────────

def _get_attr(obj: Any, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _f(x) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _fmt_freq_mhz(freq: Any) -> Optional[float]:
    try:
        f = float(freq)
    except Exception:
        return None
    if f > 1e5:  # looks like Hz
        f = f / 1e6
    return round(f, 3)

def _json_default(o):
    try:
        return str(o)
    except Exception:
        return None
