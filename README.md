
# DragonSync (WarDragon Edition)

A lightweight gateway that turns WarDragon’s drone detections into **Cursor on Target (CoT)** for TAK/ATAK, and (optionally) publishes per‑drone telemetry to **MQTT** for **Home Assistant**. This README focuses on the **WarDragon** kit where everything (drivers, sniffers, ZMQ monitor) is already set up—so you mostly just configure and run **DragonSync**.

---

## Features  

- **Remote ID Drone Detection:**  
   Uses [DroneID](https://github.com/alphafox02/DroneID) to detect Bluetooth Remote ID signals. Thanks to @bkerler for this fantastic tool. WiFi Remote ID is currently handled by an esp32.
- **DJI DroneID Detection:**
   Uses [Antsdr_DJI](https://github.com/alphafox02/antsdr_dji_droneid) to detect DJI DroneID signals.  
- **System Status Monitoring:**  
   `wardragon_monitor.py` gathers hardware status (via `lm-sensors`), GPS location, and serial number.  
- **CoT Generation:**  
   Converts system and drone data into CoT messages.  
- **ZMQ Support:**  
   Uses ZMQ for communication between components.  
- **TAK/ATAK Integration:**  
   Supports multicast for ATAK or direct TAK server connections.  

---

## Requirements  

### **Pre-installed on WarDragon Pro:**  
If running DragonSync on the WarDragon Pro kit, all dependencies are pre-configured, including hardware-specific sensors and GPS modules.

### **For Other Systems:**  
If you install DragonSync elsewhere, ensure the following:  

- **Python 3.x**  
- **lm-sensors**: Install via:  
   ```bash
   sudo apt update && sudo apt install lm-sensors
   ```  
- **gpsd** (GPS Daemon):  
   ```bash
   sudo apt install gpsd gpsd-clients
   ```  
- **USB GPS Module**: Ensure a working GPS connected to the system.  
- Other necessary Python packages (listed in the `requirements.txt` or as dependencies).  

---

## TL;DR

- WarDragon already runs the sniffers and the system monitor that feed ZMQ.
- You only need to edit **`config.ini`** in the DragonSync repo, then run `dragonsync.py`.
- Optional: enable MQTT + Home Assistant and/or Lattice export.
- When a drone times out, DragonSync marks it **offline** in HA, preserving last‑known position in history.

---

## How it Works (on WarDragon)

```
Sniffers (BLE RID / DJI)  --> ZMQ 4224 ----\
                                            --> DragonSync --> CoT: multicast or TAK server
WarDragon Monitor (GPS)    --> ZMQ 4225 ----/                 \-> MQTT (Home Assistant)
                                                               \-> Lattice (optional)
```

- **ZMQ 4224**: stream of decoded Remote ID / DJI frames.
- **ZMQ 4225**: WarDragon system/GPS info from `wardragon_monitor.py`.
- **DragonSync** merges streams, rate‑limits, and outputs:
  - **CoT** to ATAK/WinTAK via **multicast** _or_ **TAK server** (TCP/UDP, optional TLS).
  - **MQTT** (per‑drone JSON + HA discovery) for dashboards and a live map in Home Assistant.
  - **Lattice** export for Anduril Lattice, if configured.

---

## Quick Start (WarDragon)

1) **Clone/update DragonSync** on the WarDragon (sniffers/monitor are already there):
```bash
git clone https://github.com/alphafox02/DragonSync
cd DragonSync
pip3 install -r requirements.txt
```

2) **Edit `config.ini`** (see example below). Most defaults work out‑of‑the‑box on the kit.

3) **Run it**:
```bash
python3 dragonsync.py -c config.ini
```

4) (Optional) **Enable systemd service** so it starts on boot:
```bash
sudo systemctl enable dragonsync.service
sudo systemctl start dragonsync.service
journalctl -u dragonsync.service -f   # tail logs
```

> The WarDragon kit already includes sniffers and the ZMQ monitor; you do **not** need to run those manually unless you customized the setup.

---

## `config.ini` (WarDragon‑tuned example)

```ini
[SETTINGS]

# ZMQ inputs (WarDragon defaults)
zmq_host = 127.0.0.1
zmq_port = 4224          # Drone telemetry stream
zmq_status_port = 4225   # WarDragon monitor (GPS, system)

# TAK Server output (optional). If blank, TAK server is disabled.
tak_host =
tak_port =
tak_protocol =           # "tcp" or "udp"
tak_tls_p12 =
tak_tls_p12_pass =
tak_tls_skip_verify = true

# Multicast CoT to ATAK (simple zero‑server option)
enable_multicast = true
tak_multicast_addr = 239.2.3.1
tak_multicast_port = 6969
tak_multicast_interface = 0.0.0.0
multicast_ttl = 1

# Runtime behavior
rate_limit = 3.0         # min seconds between sends per drone
max_drones = 30
inactivity_timeout = 60.0
enable_receive = false

# MQTT / Home Assistant (optional)
mqtt_enabled = false
mqtt_host = 127.0.0.1
mqtt_port = 1883
mqtt_topic = wardragon/drones

mqtt_username =
mqtt_password =
mqtt_tls = false
mqtt_ca_file =
mqtt_certfile =
mqtt_keyfile =
mqtt_tls_insecure = false

# Needed for HA auto‑discovery (per‑drone topics)
per_drone_enabled = true
per_drone_base = wardragon/drone
ha_enabled = true
ha_prefix = homeassistant
ha_device_base = wardragon_drone

# Lattice (optional)
lattice_enabled = false
lattice_token =
# Either a full base URL:
lattice_base_url =
# or just the endpoint host (https:// will be prefixed):
lattice_endpoint =
lattice_sandbox_token =
lattice_source_name = DragonSync
lattice_drone_rate = 1.0
lattice_wd_rate = 0.2
```

**Notes**
- For ATAK on the same LAN/VPN, multicast is easiest (`enable_multicast=true`). In ATAK, add a Network feed for the same group/port.
- For a TAK server, fill `tak_host`, `tak_port`, and `tak_protocol`. Add TLS fields if required by your server.
- For **Home Assistant**, set `mqtt_enabled=true`, `per_drone_enabled=true`, and `ha_enabled=true`. DragonSync will auto‑create entities.

---

## Home Assistant (MQTT)

### Broker
On the same machine as HA:
```bash
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
# Optional user:
# sudo mosquitto_passwd -c /etc/mosquitto/passwd dragonsync
# and in /etc/mosquitto/conf.d/local.conf:
#   allow_anonymous false
#   password_file /etc/mosquitto/passwd
#   listener 1883 0.0.0.0
# sudo systemctl restart mosquitto
```

### Entities created by DragonSync
- **Device trackers**: `drone-<id>` (main dot), `pilot-<id-tail>`, `home-<id-tail>` (if pilot/home known).
- **Sensors**: lat/lon/alt/speed/vspeed/course/AGL/RSSI/freq_mhz/etc.

**Behavior on timeout**: when a drone stops updating for `inactivity_timeout`, DragonSync marks the trackers **offline** (hidden on the map) but **keeps last‑known location in HA history**.

**Verify MQTT traffic**
```bash
mosquitto_sub -h 127.0.0.1 -t 'homeassistant/#' -v
mosquitto_sub -h 127.0.0.1 -t 'wardragon/#' -v
```

---

## Static GPS (if no live GPS)

If the kit doesn’t have GPS lock (or you’re indoors), set a fixed location with `gps.ini` next to `dragonsync.py`:

```ini
[gps]
# If use_static_gps is true, use the values below as fixed position
use_static_gps = true
static_lat = 39.1234
static_lon = -77.5678
static_alt = 220
```

`wardragon_monitor.py` will use GPSD if available; otherwise it falls back to `gps.ini`.

---

## TAK / ATAK Output

### Multicast (no server)
- Use `enable_multicast=true` with the group/port above.
- In ATAK: add a “Network” multicast feed to the same address/port.
- Ensure your network allows multicast (IGMP snooping/firewall rules).

### TAK Server (unicast)
- Set `tak_host`, `tak_port`, `tak_protocol` (`tcp` or `udp`).
- For TLS servers, set `tak_tls_p12` and `tak_tls_p12_pass`.
- You can use `tak_tls_skip_verify=true` for testing self‑signed certs (turn off in production).

---

## Lattice (optional)

Enable with `lattice_enabled=true` and set either `lattice_base_url` or `lattice_endpoint` plus `lattice_token`.  
`lattice_drone_rate`/`lattice_wd_rate` control update rates (Hz).

---

## Tips & Troubleshooting

- **No dots in ATAK (multicast)**: same VLAN/VPN, Wireshark `udp.port==6969`, check switch IGMP snooping.
- **No entities in HA**: ensure `mqtt_enabled=true`, `per_drone_enabled=true`, `ha_enabled=true`. Watch `homeassistant/#` for discovery messages.
- **Template warnings in HA**: DragonSync uses resilient templates (e.g., `| float(0)`), so you should not see float/None errors. If you customized templates, prefer `| float(0)`.
- **Entities don’t disappear**: your DragonSync `DroneManager` should call `mark_inactive(drone_id)` on timeout (the WarDragon repo includes this). That sets HA trackers to **offline** while preserving history.
- **TAK TLS**: verify `.p12` path/password; try `tak_tls_skip_verify=true` for dev.

---

## License

MIT © 2025 cemaxecuter

