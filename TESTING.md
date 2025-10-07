# Testing the DragonSync Test Generator

Quick reference for testing the test drone generator without TAK or other services running.

## Prerequisites

Ensure you have Python dependencies:
```bash
pip3 install pyzmq
```

## Test Methods (No TAK/DragonSync Required)

### Method 1: Dry-Run Mode (Easiest)

No services needed - just prints messages to your terminal.

**Test static detections:**
```bash
python3 test_drone_generator.py --mode replay --dry-run
```

Expected output:
```
======================================================================
[1] DJI Mavic 3 - Stationary Hover
    DJI Mavic hovering at fixed location with pilot and home point
======================================================================
[
  {
    "Basic ID": {
      "id_type": "Serial Number (ANSI/CTA-2063-A)",
      "id": "1581F6BVCA2K0D000123",
      ...
    }
  },
  ...
]
```

**Test animated simulation:**
```bash
python3 test_drone_generator.py --mode simulate --dry-run
```

Expected output:
```
[1] DJI Phantom 4 - Patrol Route @ 10:30:45
  Position: (42.216500, -70.902500) Alt: 75.0m
  Speed: 8.0m/s  Heading: 90°
  Status: En route to waypoint 1 (progress: 15.3%)
```

Press `Ctrl+C` to stop.

---

### Method 2: ZMQ Listener Test (Validates Full Flow)

Tests the complete message pipeline including ZMQ serialization.

**Terminal 1 - Start listener:**
```bash
python3 test_zmq_listener.py
```

Expected output:
```
ZMQ Test Listener connected to tcp://127.0.0.1:4224
Waiting for messages... (Press Ctrl+C to stop)
```

**Terminal 2 - Run generator:**
```bash
python3 test_drone_generator.py --mode replay --loop
```

**Terminal 1 will show:**
```
[0001] 10:30:45
  ID: 1581F6BVCA2K0D000123 | Pos: (42.216568, -70.902473) | Alt: 85.0m | Spd: 0.5m/s | Hdg: 45° | RSSI: -68dBm | Freq: 5.805GHz | Pilot: (42.216345, -70.902689) | Home: (42.216345, -70.902689) | Desc: "DJI Mavic 3 Survey Mission"
```

Press `Ctrl+C` in both terminals to stop.

---

### Method 3: Verbose Listener (See Full JSON)

See complete message structure:

```bash
# Terminal 1
python3 test_zmq_listener.py --verbose

# Terminal 2
python3 test_drone_generator.py --mode replay
```

This shows the full JSON message structure that DragonSync receives.

---

## Test Different Scenarios

### Fast Replay
```bash
python3 test_drone_generator.py --mode replay --interval 0.5 --dry-run
```

### Single Run (No Loop)
```bash
python3 test_drone_generator.py --mode replay --dry-run
# Sends 3 messages then exits
```

### Continuous Simulation
```bash
python3 test_drone_generator.py --mode simulate --loop --dry-run
# Watch drone follow patrol route continuously
```

---

## Testing with DragonSync

Once you've verified the generator works, test with DragonSync:

**Terminal 1 - Test generator:**
```bash
python3 test_drone_generator.py --mode simulate --loop
```

**Terminal 2 - DragonSync:**
```bash
python3 dragonsync.py -c config.ini
```

DragonSync will process the simulated detections and send to TAK/Lattice/MQTT just like real detections.

---

## Expected Results

### Replay Mode (3 static detections)
- **Drone 1**: DJI Mavic 3 hovering, 5.805 GHz, RSSI -68dBm
- **Drone 2**: Autel EVO II in transit, 5.745 GHz, RSSI -72dBm
- **Drone 3**: Parrot ANAFI low altitude, 2.437 GHz, RSSI -55dBm

Each includes:
- Serial number or CAA registration
- GPS position (lat/lon/alt)
- Speed, heading, vertical speed
- Pilot location
- Home point location
- Frequency
- Operator ID

### Simulate Mode (1 animated drone)
- **Drone**: DJI Phantom 4 following rectangular patrol
- 5 waypoints with smooth interpolation
- Auto-calculated heading between waypoints
- Dwell times at each waypoint
- Loops continuously if `--loop` specified

---

## Troubleshooting

### "Address already in use" error
The generator binds to port 4224. If you get this error:
```bash
# Kill any existing process on port 4224
# Linux/Mac:
lsof -ti:4224 | xargs kill -9

# Windows:
netstat -ano | findstr :4224
taskkill /PID <PID> /F
```

Or use dry-run mode which doesn't use ZMQ:
```bash
python3 test_drone_generator.py --mode replay --dry-run
```

### "ModuleNotFoundError: No module named 'zmq'"
```bash
pip3 install pyzmq
```

### Listener receives no messages
1. Make sure listener starts **before** generator
2. Check both are using same port (default 4224)
3. Try with `--dry-run` to verify generator itself works

---

## Customizing Scenarios

Edit `test_scenarios.json` to create your own test scenarios:

1. **Static detections**: Add to `scenarios.static_detections[]`
2. **Animated tracks**: Add to `scenarios.animated_tracks[]`

See the JSON file for format examples.

---

## Summary

**Quickest test (no setup):**
```bash
python3 test_drone_generator.py --mode replay --dry-run
```

**Best test (validates ZMQ):**
```bash
# Terminal 1:
python3 test_zmq_listener.py

# Terminal 2:
python3 test_drone_generator.py --mode simulate --loop
```

**Full integration test:**
```bash
# Terminal 1:
python3 test_drone_generator.py --mode simulate --loop

# Terminal 2:
python3 dragonsync.py -c config.ini
```
