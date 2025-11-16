# ZMQ Testing Guide - Testing Without Hardware

This guide shows you how to test the refactored DragonSync parsers using simulated ZMQ telemetry streams, no hardware required!

## Prerequisites

Install testing dependencies first:
```bash
cd /home/user/DragonSync
pip install -r test_requirements.txt
```

This installs:
- `pyzmq` - ZMQ library for message streaming
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting

## Quick Start (2 terminals)

### Terminal 1: Start the ZMQ Publisher (simulates hardware)
```bash
cd /home/user/DragonSync
python3 test_zmq_publisher.py --num-drones 3 --simulate-movement
```

### Terminal 2: Start the Live Tester (simulates DragonSync)
```bash
cd /home/user/DragonSync
python3 test_live_zmq.py --host 127.0.0.1 --port 5555 --verbose
```

You should see drones being detected and parsed in Terminal 2!

---

## Publisher Options

### Basic Usage
```bash
# Default: 3 drones, mixed DJI/ESP32 formats, 1s updates
python3 test_zmq_publisher.py
```

### Simulate Many Drones
```bash
# Test with 10 drones
python3 test_zmq_publisher.py --num-drones 10
```

### Fast Updates
```bash
# Send updates every 100ms (10 Hz)
python3 test_zmq_publisher.py --interval 0.1
```

### Only DJI or ESP32 Format
```bash
# Test only DJI/AntSDR format
python3 test_zmq_publisher.py --format dji

# Test only ESP32 BLE format
python3 test_zmq_publisher.py --format esp32

# Test mixed (default)
python3 test_zmq_publisher.py --format mixed
```

### Simulate Realistic Movement
```bash
# Drones will fly around realistically
python3 test_zmq_publisher.py --simulate-movement --num-drones 5
```

### Test Error Handling
```bash
# Occasionally send malformed messages (5% of the time)
python3 test_zmq_publisher.py --random-errors
```

### Custom Location
```bash
# Start drones near San Francisco
python3 test_zmq_publisher.py --lat 37.7749 --lon -122.4194
```

### Custom Port
```bash
# Use a different port
python3 test_zmq_publisher.py --port 5556
```

---

## Subscriber/Tester Options

### Basic Usage
```bash
# Connect and display drones
python3 test_live_zmq.py
```

### Verbose Mode
```bash
# Show all drone details
python3 test_live_zmq.py --verbose
```

### Save Results
```bash
# Save parsed drone data to JSON
python3 test_live_zmq.py --save test_results.json
```

### Limited Testing
```bash
# Stop after 60 seconds
python3 test_live_zmq.py --timeout 60

# Stop after 100 drones
python3 test_live_zmq.py --max-drones 100

# Combine both
python3 test_live_zmq.py --timeout 30 --max-drones 50
```

### Show Parse Errors
```bash
# Display messages that failed to parse
python3 test_live_zmq.py --show-errors
```

---

## Example Testing Scenarios

### Scenario 1: Quick Smoke Test
Verify everything works with minimal output:
```bash
# Terminal 1
python3 test_zmq_publisher.py --num-drones 1

# Terminal 2
python3 test_live_zmq.py --max-drones 5
```

**Expected Result**: Should parse 5 messages successfully, 0 errors

---

### Scenario 2: Multi-Drone Stress Test
Test with many drones and fast updates:
```bash
# Terminal 1
python3 test_zmq_publisher.py --num-drones 20 --interval 0.1 --simulate-movement

# Terminal 2
python3 test_live_zmq.py --timeout 10 --save stress_test.json
```

**Expected Result**: Should handle 200+ messages/second with high success rate

---

### Scenario 3: Format Compatibility Test
Test DJI and ESP32 formats separately:
```bash
# Terminal 1 - DJI only
python3 test_zmq_publisher.py --format dji --num-drones 3

# Terminal 2
python3 test_live_zmq.py --verbose --max-drones 10 --save dji_test.json

# Then restart Terminal 1 with ESP32
python3 test_zmq_publisher.py --format esp32 --num-drones 3

# Terminal 2 again
python3 test_live_zmq.py --verbose --max-drones 10 --save esp32_test.json
```

**Expected Result**: Both formats parse successfully with correct field extraction

---

### Scenario 4: Error Handling Test
Verify graceful handling of malformed messages:
```bash
# Terminal 1
python3 test_zmq_publisher.py --random-errors --num-drones 5

# Terminal 2
python3 test_live_zmq.py --show-errors --timeout 30
```

**Expected Result**: ~5% parse errors, rest succeed. No crashes.

---

### Scenario 5: Movement Simulation
Watch drones move realistically:
```bash
# Terminal 1
python3 test_zmq_publisher.py --num-drones 5 --simulate-movement --interval 1.0

# Terminal 2
python3 test_live_zmq.py --verbose
```

**Expected Result**: Lat/lon/alt should change over time as drones "fly"

---

## Sample Output

### Publisher Output
```
🚁 ZMQ Drone Telemetry Publisher
======================================================================
   Binding to: tcp://127.0.0.1:5555
   Simulating: 3 drone(s)
   Format: mixed
   Interval: 1.0s
   Movement: Yes (static)
   Random Errors: No
   Starting Position: 42.3601, -71.0589
======================================================================

📡 Publishing messages... (Ctrl+C to stop)

✅ Created: SIM-DRONE-001 (DJI format) at (42.361234, -71.058123)
✅ Created: SIM-DRONE-002 (ESP32 format) at (42.359876, -71.059234)
✅ Created: SIM-DRONE-003 (DJI format) at (42.360456, -71.057890)

📤 Publishing telemetry...

📊 Sent: 150 messages (5.0/sec) | Errors: 0
```

### Subscriber Output
```
🎯 DragonSync Refactor - Live ZMQ Testing
======================================================================
   ZMQ Connection: tcp://127.0.0.1:5555
   Timeout: None (run forever)
   Max Drones: Unlimited
   Verbose: Yes
======================================================================

📡 Listening for drone telemetry... (Ctrl+C to stop)

✅ Drone #1 (unique: 1)
   ID: SIM-DRONE-001
   Position: 42.361234, -71.058123, 150.5m
   Speed: 12.3 m/s (vertical: 1.8 m/s)
   Height AGL: 105.4m
   Pilot: 42.360234, -71.059123
   Type: Helicopter or Multirotor
   MAC: AA:BB:CC:DD:EE:FF, RSSI: -65

✅ Drone #2 (unique: 2)
   ID: SIM-DRONE-002
   Position: 42.359876, -71.059234, 120.2m
   Speed: 8.5 m/s (vertical: -1.5 m/s)
   Height AGL: 84.1m
   Pilot: 42.358876, -71.060234
   Type: Helicopter or Multirotor
   MAC: 11:22:33:44:55:66, RSSI: -72
```

---

## Troubleshooting

### Problem: "Address already in use"
**Solution**: Another process is using the port. Try a different port:
```bash
python3 test_zmq_publisher.py --port 5556
python3 test_live_zmq.py --port 5556
```

### Problem: "No module named 'zmq'"
**Solution**: Install pyzmq:
```bash
pip install pyzmq
```

### Problem: Subscriber sees no messages
**Possible causes**:
1. Publisher and subscriber using different ports
2. Publisher started after subscriber (ZMQ PUB/SUB needs publisher first)
3. Firewall blocking localhost

**Solution**:
- Always start publisher FIRST
- Check port numbers match
- Try restarting both

### Problem: All messages fail to parse
**Solution**: Check the format matches what parser expects:
```bash
# Publisher sends as JSON
# Subscriber should receive and parse correctly
# If not, check Python version (needs 3.7+)
```

---

## Integration with Real Hardware

When you get real hardware, the workflow is similar:

1. **Stop the test publisher**
2. **Start your real WarDragon hardware** (it will publish to ZMQ)
3. **Run the subscriber** pointing to the hardware:
   ```bash
   python3 test_live_zmq.py --host <hardware-ip> --port 5555
   ```

The refactored parser should handle real messages the same way it handles simulated ones!

---

## Performance Benchmarking

To test parser performance:

```bash
# Terminal 1: Fast publisher
python3 test_zmq_publisher.py --num-drones 10 --interval 0.01

# Terminal 2: Measure throughput
python3 test_live_zmq.py --timeout 60 --save benchmark.json

# After 60 seconds, check the "Throughput" stat
```

**Target**: Should handle 100+ drones/second easily

---

## Debugging Tips

### Enable verbose logging in both scripts
```bash
# Publisher with movement tracking
python3 test_zmq_publisher.py --simulate-movement --num-drones 1 --interval 2

# Subscriber with all details and error reporting
python3 test_live_zmq.py --verbose --show-errors
```

### Capture raw ZMQ messages
```bash
# Use tcpdump or zmq monitoring
python3 -c "
import zmq
import time

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect('tcp://127.0.0.1:5555')
socket.setsockopt_string(zmq.SUBSCRIBE, '')

for i in range(10):
    msg = socket.recv()
    print(f'Message {i}:')
    print(msg.decode('utf-8'))
    print()
    time.sleep(1)
"
```

---

## Next Steps

Once you've validated the parser with simulated data:

1. ✅ Run the compatibility test: `python3 test_refactor.py`
2. ✅ Run the full unit tests: `pytest refactor_project/tests/ -v`
3. ✅ Test with simulated ZMQ stream (this guide)
4. 🔜 Test with real WarDragon hardware
5. 🔜 Integrate into production DragonSync

Happy testing! 🚁
