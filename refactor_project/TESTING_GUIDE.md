# DragonSync Refactor - Testing & Compatibility Guide

**Date**: 2025-11-16
**Status**: Phases 1-2 Complete (Models + Parsers)
**Ready for Hardware Testing**: Yes ✅

---

## What's Available for Testing

### ✅ Phase 1: Core Models (100% Complete)

All domain models are implemented and ready to replace legacy code:

| Model | Legacy File | Refactored File | Status | Tests | Coverage |
|-------|-------------|-----------------|--------|-------|----------|
| Drone | `drone.py` | `refactor_project/models/drone.py` | ✅ | 14 | 88% |
| SystemStatus | `system_status.py` | `refactor_project/models/system_status.py` | ✅ | 17 | 91% |
| Location | N/A (new) | `refactor_project/models/location.py` | ✅ | 18 | 100% |
| Telemetry | N/A (new) | `refactor_project/models/telemetry.py` | ✅ | 14 | 100% |

### ✅ Phase 2: Parsers (100% Complete)

Telemetry parsers are ready for real-world ZMQ data:

| Parser | Legacy File | Refactored File | Status | Tests | Coverage |
|--------|-------------|-----------------|--------|-------|----------|
| DroneParser | `telemetry_parser.py` | `refactor_project/parsers/drone_parser.py` | ✅ | 14 | 92% |

**Supported Formats**:
- ✅ DJI/AntSDR (Remote ID list format)
- ✅ ESP32 BLE (Remote ID dict format)
- ✅ CAA Registration IDs
- ✅ All Remote ID message types (Basic ID, Location/Vector, Self-ID, System, Operator ID, Frequency)

---

## Compatibility Testing Checklist

### 1. Parser Compatibility Tests

#### Test 1.1: DJI/AntSDR Format Parsing
**Objective**: Verify refactored parser produces same output as legacy for DJI messages

```python
# Test setup
import sys
sys.path.insert(0, '/home/user/DragonSync')

from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.tests.fixtures.sample_messages import UA_TYPE_MAPPING

# Legacy parser (for comparison)
from telemetry_parser import parse_and_create_drone as legacy_parse

# Create parser instance
parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)

# Test with real ZMQ message (DJI format)
# Get from your actual ZMQ stream or use sample from fixtures
from refactor_project.tests.fixtures.sample_messages import SAMPLE_DJI_MESSAGE

# Parse with both parsers
refactored_drone = parser.parse(SAMPLE_DJI_MESSAGE)
legacy_drone = legacy_parse(SAMPLE_DJI_MESSAGE)  # If legacy function exists

# Compare outputs
print(f"Refactored Drone ID: {refactored_drone.id}")
print(f"Refactored Lat/Lon: {refactored_drone.lat}, {refactored_drone.lon}")
print(f"Refactored Speed: {refactored_drone.speed} m/s")
print(f"Refactored UA Type: {refactored_drone.ua_type}")
```

**Success Criteria**:
- ✅ Both parsers extract same drone ID
- ✅ Both parsers extract same lat/lon/alt
- ✅ Both parsers extract same speed/vspeed
- ✅ Both parsers extract same pilot location
- ✅ Both parsers handle UA type codes identically

#### Test 1.2: ESP32 BLE Format Parsing
**Objective**: Verify ESP32 dict format parsing

```python
from refactor_project.tests.fixtures.sample_messages import SAMPLE_ESP32_MESSAGE

# Parse ESP32 message
drone = parser.parse(SAMPLE_ESP32_MESSAGE)

# Verify key fields
assert drone is not None, "Parser should handle ESP32 format"
assert drone.lat != 0.0, "Should extract latitude"
assert drone.lon != 0.0, "Should extract longitude"
assert drone.mac is not None, "Should extract MAC address"
assert drone.rssi is not None, "Should extract RSSI"

print(f"✅ ESP32 parsing: {drone.id} at ({drone.lat}, {drone.lon})")
```

**Success Criteria**:
- ✅ Parser correctly detects ESP32 dict format
- ✅ Extracts all BLE-specific fields (MAC, RSSI)
- ✅ Creates valid Drone model instance

#### Test 1.3: Error Handling
**Objective**: Verify graceful handling of malformed messages

```python
# Test with invalid messages
invalid_cases = [
    None,
    {},
    [],
    {"invalid": "format"},
    [{"no_basic_id": True}],
]

for invalid_msg in invalid_cases:
    result = parser.parse(invalid_msg)
    assert result is None, f"Should return None for invalid: {invalid_msg}"

print("✅ Error handling: All invalid messages correctly rejected")
```

**Success Criteria**:
- ✅ Returns `None` for all invalid formats
- ✅ No exceptions thrown
- ✅ Logs appropriate warnings (if logging enabled)

---

### 2. Model Compatibility Tests

#### Test 2.1: Drone Model Fields
**Objective**: Verify Drone model has all legacy fields

```python
from refactor_project.models.drone import Drone

# Create drone with minimal required fields
drone = Drone(
    id="test-drone-1",
    lat=37.7749,
    lon=-122.4194,
    speed=5.5,
    vspeed=0.2,
    alt=100.0,
    height=50.0,
    pilot_lat=37.7750,
    pilot_lon=-122.4195,
    description="Test Drone",
    mac="AA:BB:CC:DD:EE:FF",
    rssi=-65
)

# Verify all legacy fields exist
legacy_fields = [
    'id', 'lat', 'lon', 'speed', 'vspeed', 'alt', 'height',
    'pilot_lat', 'pilot_lon', 'description', 'mac', 'rssi',
    'timestamp', 'last_update_time', 'ua_type', 'caa_id'
]

for field in legacy_fields:
    assert hasattr(drone, field), f"Missing field: {field}"

print(f"✅ Drone model: All {len(legacy_fields)} legacy fields present")
```

**Success Criteria**:
- ✅ All legacy `drone.py` fields are present
- ✅ Field types match legacy expectations
- ✅ Default values work correctly

#### Test 2.2: Drone Model Update Method
**Objective**: Verify update() method maintains position history

```python
# Test update method
original_lat = drone.lat
original_lon = drone.lon

drone.update(lat=37.7760, lon=-122.4200, speed=7.0)

assert drone.lat == 37.7760, "Should update latitude"
assert drone.lon == -122.4200, "Should update longitude"
assert drone.speed == 7.0, "Should update speed"
assert drone.prev_lat == original_lat, "Should store previous latitude"
assert drone.prev_lon == original_lon, "Should store previous longitude"

print("✅ Drone update: Position history correctly maintained")
```

**Success Criteria**:
- ✅ `update()` method updates specified fields
- ✅ Previous position stored in `prev_lat`/`prev_lon`
- ✅ Timestamp updated on each update

#### Test 2.3: SystemStatus Model
**Objective**: Verify SystemStatus matches legacy behavior

```python
from refactor_project.models.system_status import SystemStatus

# Create system status
status = SystemStatus(
    serial_number="WD-12345",
    lat=37.7749,
    lon=-122.4194,
    alt=50.0,
    cpu_usage=45.2,
    memory_total=8192.0,
    memory_used=4096.0
)

# Verify computed fields
assert status.id == "wardragon-WD-12345", "Should generate ID from serial"
assert status.memory_percent == 50.0, "Should calculate memory percentage"
assert hasattr(status, 'last_update_time'), "Should have timestamp"

print(f"✅ SystemStatus: {status.id} at ({status.lat}, {status.lon})")
```

**Success Criteria**:
- ✅ ID generated from serial number
- ✅ Memory percentage calculated correctly
- ✅ All GPS fields present

---

### 3. Integration Tests

#### Test 3.1: End-to-End ZMQ → Parser → Model
**Objective**: Verify complete flow from raw ZMQ to Drone model

```python
# Simulate receiving ZMQ message
import zmq
import json

# Setup (this is pseudocode - adapt to your actual ZMQ setup)
# context = zmq.Context()
# socket = context.socket(zmq.SUB)
# socket.connect("tcp://localhost:5555")
# socket.setsockopt_string(zmq.SUBSCRIBE, "")

# For testing without real ZMQ, use fixture
zmq_message = SAMPLE_DJI_MESSAGE

# Parse message
parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
drone = parser.parse(zmq_message)

# Verify complete model
assert drone is not None, "Should parse valid message"
assert drone.id is not None, "Should have drone ID"
assert -90 <= drone.lat <= 90, "Latitude should be valid"
assert -180 <= drone.lon <= 180, "Longitude should be valid"
assert drone.last_update_time > 0, "Should have timestamp"

print(f"✅ End-to-end: Parsed {drone.id} successfully")
```

**Success Criteria**:
- ✅ ZMQ message → Parser → Drone model works
- ✅ All required fields populated
- ✅ Data validation passes

#### Test 3.2: Multiple Message Types
**Objective**: Verify handling of different Remote ID message types

```python
from refactor_project.tests.fixtures.sample_messages import (
    SAMPLE_DJI_MESSAGE,
    SAMPLE_ESP32_MESSAGE,
    SAMPLE_MINIMAL_MESSAGE,
    SAMPLE_CAA_MESSAGE
)

test_cases = [
    ("DJI Complete", SAMPLE_DJI_MESSAGE),
    ("ESP32 BLE", SAMPLE_ESP32_MESSAGE),
    ("Minimal", SAMPLE_MINIMAL_MESSAGE),
    ("CAA ID", SAMPLE_CAA_MESSAGE),
]

parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
results = []

for name, message in test_cases:
    drone = parser.parse(message)
    success = drone is not None
    results.append((name, success, drone.id if drone else None))
    print(f"{'✅' if success else '❌'} {name}: {drone.id if drone else 'FAILED'}")

# All should succeed
assert all(r[1] for r in results), "All message types should parse successfully"
```

**Success Criteria**:
- ✅ DJI format parses correctly
- ✅ ESP32 format parses correctly
- ✅ Minimal message parses correctly
- ✅ CAA ID format parses correctly

---

### 4. Performance Comparison Tests

#### Test 4.1: Parser Performance
**Objective**: Compare parsing speed vs legacy

```python
import time

# Prepare test data
messages = [SAMPLE_DJI_MESSAGE] * 1000

# Time refactored parser
parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
start = time.time()
for msg in messages:
    drone = parser.parse(msg)
refactored_time = time.time() - start

print(f"Refactored parser: {refactored_time:.4f}s for 1000 messages")
print(f"Average: {refactored_time/1000*1000:.2f}ms per message")

# If legacy parser available, compare
# start = time.time()
# for msg in messages:
#     legacy_drone = legacy_parse(msg)
# legacy_time = time.time() - start
# print(f"Legacy parser: {legacy_time:.4f}s for 1000 messages")
# print(f"Speedup: {legacy_time/refactored_time:.2f}x")
```

**Success Criteria**:
- ✅ Parser handles 1000+ messages/second
- ✅ No memory leaks over extended runs
- ✅ Performance comparable to or better than legacy

#### Test 4.2: Memory Usage
**Objective**: Verify no memory leaks in model creation

```python
import tracemalloc

tracemalloc.start()

# Create and parse many drones
parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
drones = []

for i in range(10000):
    drone = parser.parse(SAMPLE_DJI_MESSAGE)
    if i % 1000 == 0:  # Keep every 1000th to prevent GC
        drones.append(drone)

current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()

print(f"Current memory: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
print(f"Average per drone: {peak / 10000:.0f} bytes")
```

**Success Criteria**:
- ✅ Memory usage stays reasonable (< 100 bytes per drone)
- ✅ No unbounded growth over time
- ✅ Garbage collection works correctly

---

## Hardware Testing Guide

### Live ZMQ Stream Testing

#### Setup 1: Connect to Real ZMQ Stream

```python
#!/usr/bin/env python3
"""
Live testing with real ZMQ drone telemetry
Run this on your WarDragon hardware
"""

import zmq
import json
import sys
sys.path.insert(0, '/home/user/DragonSync')

from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.tests.fixtures.sample_messages import UA_TYPE_MAPPING

# Configure ZMQ connection (adjust to your setup)
ZMQ_HOST = "127.0.0.1"  # or your drone receiver IP
ZMQ_PORT = 5555  # adjust to your port

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(f"tcp://{ZMQ_HOST}:{ZMQ_PORT}")
socket.setsockopt_string(zmq.SUBSCRIBE, "")

# Create parser
parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)

print("🎯 Listening for drone telemetry on ZMQ...")
print(f"   Connected to tcp://{ZMQ_HOST}:{ZMQ_PORT}")
print()

drone_count = 0
error_count = 0

try:
    while True:
        # Receive ZMQ message
        message = socket.recv()

        # Parse JSON (if needed)
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            data = message  # Already in correct format

        # Parse with refactored parser
        drone = parser.parse(data)

        if drone:
            drone_count += 1
            print(f"✅ Drone {drone_count}: {drone.id}")
            print(f"   Location: {drone.lat:.6f}, {drone.lon:.6f}, {drone.alt:.1f}m")
            print(f"   Speed: {drone.speed:.1f} m/s, VSpeed: {drone.vspeed:.1f} m/s")
            print(f"   Pilot: {drone.pilot_lat:.6f}, {drone.pilot_lon:.6f}")
            print(f"   Type: {drone.ua_type}, MAC: {drone.mac}, RSSI: {drone.rssi}")
            print()
        else:
            error_count += 1
            print(f"❌ Failed to parse message (total errors: {error_count})")
            print(f"   Raw data: {data}")
            print()

except KeyboardInterrupt:
    print(f"\n📊 Statistics:")
    print(f"   Total drones parsed: {drone_count}")
    print(f"   Parse errors: {error_count}")
    print(f"   Success rate: {drone_count/(drone_count+error_count)*100:.1f}%")
finally:
    socket.close()
    context.term()
```

#### Expected Output (Success Case)

```
🎯 Listening for drone telemetry on ZMQ...
   Connected to tcp://127.0.0.1:5555

✅ Drone 1: 16:AA:BB:CC:DD:EE:FF
   Location: 37.774929, -122.419416, 100.5m
   Speed: 5.5 m/s, VSpeed: 0.2 m/s
   Pilot: 37.775000, -122.419500
   Type: Multirotor, MAC: AA:BB:CC:DD:EE:FF, RSSI: -65

✅ Drone 2: CAA-GBR-ABC123XYZ
   Location: 37.774950, -122.419450, 105.0m
   Speed: 8.2 m/s, VSpeed: -0.5 m/s
   Pilot: 37.775000, -122.419500
   Type: Fixed Wing, MAC: BB:CC:DD:EE:FF:00, RSSI: -72
```

---

### Comparison Testing Workflow

#### Step 1: Capture Raw ZMQ Data

```bash
# Use zmqcap or similar to capture real messages
python3 -c "
import zmq
import json
import time

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect('tcp://127.0.0.1:5555')
socket.setsockopt_string(zmq.SUBSCRIBE, '')

messages = []
timeout = time.time() + 60  # Capture for 60 seconds

while time.time() < timeout:
    try:
        msg = socket.recv(flags=zmq.NOBLOCK)
        messages.append(json.loads(msg))
    except zmq.Again:
        time.sleep(0.1)

# Save to file
with open('captured_messages.json', 'w') as f:
    json.dump(messages, f, indent=2)

print(f'Captured {len(messages)} messages')
"
```

#### Step 2: Test Both Parsers

```python
import json
from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.tests.fixtures.sample_messages import UA_TYPE_MAPPING

# Load captured messages
with open('captured_messages.json', 'r') as f:
    messages = json.load(f)

parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)

# Parse all messages
results = []
for i, msg in enumerate(messages):
    drone = parser.parse(msg)
    results.append({
        'message_num': i,
        'success': drone is not None,
        'drone_id': drone.id if drone else None,
        'lat': drone.lat if drone else None,
        'lon': drone.lon if drone else None,
    })

# Summary
success_count = sum(1 for r in results if r['success'])
print(f"Parsed {success_count}/{len(messages)} messages ({success_count/len(messages)*100:.1f}%)")

# Save results for comparison
with open('refactored_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

#### Step 3: Compare Against Legacy

```python
# If you have legacy parser results, compare them
import json

with open('refactored_results.json', 'r') as f:
    refactored = json.load(f)

# with open('legacy_results.json', 'r') as f:
#     legacy = json.load(f)

# Compare drone IDs, positions, etc.
# differences = []
# for ref, leg in zip(refactored, legacy):
#     if ref['drone_id'] != leg['drone_id']:
#         differences.append({'type': 'id_mismatch', 'ref': ref, 'leg': leg})
#     # ... more comparisons

# print(f"Found {len(differences)} differences")
```

---

## Quick Start Testing Script

Save this as `test_refactor.py` in the root directory:

```python
#!/usr/bin/env python3
"""Quick compatibility test for refactored DragonSync components"""

import sys
sys.path.insert(0, '/home/user/DragonSync')

from refactor_project.parsers.drone_parser import DroneParser
from refactor_project.tests.fixtures.sample_messages import (
    SAMPLE_DJI_MESSAGE,
    SAMPLE_ESP32_MESSAGE,
    UA_TYPE_MAPPING
)

def test_dji_parsing():
    """Test DJI message parsing"""
    parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
    drone = parser.parse(SAMPLE_DJI_MESSAGE)

    assert drone is not None, "Failed to parse DJI message"
    assert drone.id == "16:AA:BB:CC:DD:EE:FF", f"Wrong ID: {drone.id}"
    assert abs(drone.lat - 37.774929) < 0.000001, f"Wrong lat: {drone.lat}"
    assert abs(drone.lon - (-122.419416)) < 0.000001, f"Wrong lon: {drone.lon}"

    print("✅ DJI parsing test passed")
    return True

def test_esp32_parsing():
    """Test ESP32 BLE message parsing"""
    parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)
    drone = parser.parse(SAMPLE_ESP32_MESSAGE)

    assert drone is not None, "Failed to parse ESP32 message"
    assert drone.mac is not None, "Missing MAC address"
    assert drone.rssi is not None, "Missing RSSI"

    print("✅ ESP32 parsing test passed")
    return True

def test_error_handling():
    """Test error handling"""
    parser = DroneParser(ua_type_mapping=UA_TYPE_MAPPING)

    assert parser.parse(None) is None, "Should handle None"
    assert parser.parse({}) is None, "Should handle empty dict"
    assert parser.parse([]) is None, "Should handle empty list"

    print("✅ Error handling test passed")
    return True

if __name__ == "__main__":
    print("🧪 Running DragonSync Refactor Compatibility Tests\n")

    tests = [
        test_dji_parsing,
        test_esp32_parsing,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} error: {e}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
```

Run it with:
```bash
cd /home/user/DragonSync
python3 test_refactor.py
```

---

## Summary

### ✅ Ready for Testing
- **Models**: All 4 core models (Drone, SystemStatus, Location, Telemetry)
- **Parsers**: DroneParser with DJI and ESP32 support
- **Tests**: 77 unit tests passing, 92% coverage

### 🎯 Recommended Testing Order
1. Run unit tests: `pytest refactor_project/tests/ -v`
2. Run quick compatibility script: `python3 test_refactor.py`
3. Test with captured ZMQ data (offline)
4. Test with live ZMQ stream (hardware)
5. Compare outputs with legacy system
6. Performance benchmarking

### 📊 Success Criteria
- ✅ All parsers handle real ZMQ messages
- ✅ Output matches legacy parser (same drone IDs, positions, fields)
- ✅ No exceptions on malformed data
- ✅ Performance >= legacy system
- ✅ Ready to replace legacy telemetry_parser.py

---

**Next Phase**: Once compatibility verified, proceed to Phase 3 (Managers) to add DroneManager with dependency injection.
