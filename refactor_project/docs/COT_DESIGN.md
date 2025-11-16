# CoT (Cursor on Target) Generator - Design Document

**Date**: 2025-11-16
**Phase**: 4 (Messaging)
**Status**: Design & Implementation

---

## Research Summary: Current CoT Standards & TAK Best Practices

### CoT Protocol Overview

**Cursor on Target (CoT)** is an XML-based machine-to-machine schema developed by MITRE Corporation for tactical situational awareness. It's the primary data exchange format for the TAK (Team Awareness Kit) ecosystem.

### Core Schema Structure

CoT messages have 3 main XML elements:

1. **`<event>`** - Root element with metadata
   - `version`: Protocol version (typically "2.0")
   - `uid`: Unique identifier for the entity
   - `type`: Hierarchical type from MIL-STD-2525
   - `time`: When message was generated (ISO 8601)
   - `start`: When event became of interest
   - `stale`: When event is no longer valid
   - `how`: How the position was determined (e.g., "m-g" for GPS)

2. **`<point>`** - Geospatial location
   - `lat`: Latitude (WGS84, decimal degrees)
   - `lon`: Longitude (WGS84, decimal degrees)
   - `hae`: Height Above Ellipsoid (meters)
   - `ce`: Circular Error probable (meters) - horizontal accuracy
   - `le`: Linear Error probable (meters) - vertical accuracy

3. **`<detail>`** - Extensible metadata container
   - `<contact>`: Callsign and other contact info
   - `<track>`: Course and speed for moving entities
   - `<precisionlocation>`: GPS source metadata
   - `<remarks>`: Human-readable notes
   - `<usericon>`: Custom icon path
   - `<color>`: Display color (ARGB format)
   - Custom schemas per Community of Interest

### CoT Type Hierarchy (MIL-STD-2525 Based)

**Format**: `atoms-affiliation-dimension-function`

**Affiliation** (2nd character):
- `a-f-...` = Friendly
- `a-u-...` = Unknown
- `a-n-...` = Neutral
- `a-h-...` = Hostile

**Battle Dimension** (3rd character - uppercase from MIL-STD-2525):
- `A` = Air
- `G` = Ground
- `S` = Sea Surface
- `U` = Sea Subsurface
- `P` = Space

**Function Code** (remaining characters):
- `M` = Military
- `C` = Civilian
- `F` = Fixed Wing
- `H` = Rotary Wing (Helicopter)
- `Q` = **Unmanned/Drone** (UAV/UAS designator)

### Drone-Specific CoT Types (Modern Standards)

Based on research of current TAK implementations and CoTtypes.xml:

| UA Type | Description | Legacy Code | **Modern Code** | Rationale |
|---------|-------------|-------------|-----------------|-----------|
| 1 | Fixed Wing | `a-f-A-f` | `a-u-A-M-F-Q` | Military Fixed Wing **Drone** (Q suffix) |
| 2 | Multirotor | `a-u-A-M-H-R` | `a-u-A-M-H-Q` | Military Rotary **Drone** (Q suffix) |
| 3 | Gyroplane | `a-u-A-M-H-R` | `a-u-A-M-H-Q` | Treat as rotary drone |
| 4 | VTOL | `a-u-A-M-H-R` | `a-u-A-M-H-Q` | Vertical takeoff drone |
| 6 | Glider | `a-f-A-f` | `a-u-A-C-F-q` | Civilian Fixed drone (lowercase q) |
| 7-15 | Other | `b-m-p-s-m` | `a-u-A-M-H-Q` | Default to rotary drone |

**Key Change**: Use `-Q` suffix for military drones, `-q` for civilian drones. Default affiliation to `unknown` (`u`) since most Remote ID drones are civilian/recreational.

### Timestamp Best Practices (2024)

**CRITICAL**: Use timezone-aware UTC timestamps

```python
# ❌ DEPRECATED (Python 3.12+)
datetime.datetime.utcnow()

# ✅ CORRECT
datetime.datetime.now(datetime.timezone.utc)
```

**Format**: ISO 8601 with Zulu suffix
**Example**: `2024-11-16T17:30:00.123456Z`

**Stale Time Guidelines**:
- Rapidly moving entities: `time + 10-30 seconds`
- Slow moving entities: `time + 1-2 minutes`
- Static points: `time + 10-30 minutes`
- For drones: Recommend `time + (2 × update_interval)`

### Circular Error (CE) and Linear Error (LE)

**Modern Practice**: Use actual accuracy from Remote ID when available

```python
# If horizontal_accuracy available (e.g., "10m")
ce = parse_accuracy(drone.horizontal_accuracy)  # Extract numeric value

# Otherwise use conservative default
ce = 35.0  # meters (default for GPS)

# Vertical error
le = parse_accuracy(drone.vertical_accuracy) if available else 999999.0
```

**Note**: `le=999999` indicates unknown/poor vertical accuracy (legacy default)

### Track Element for Moving Entities

```xml
<track course="180.5" speed="12.5"/>
```

**Best Practices**:
- `course`: True heading in degrees (0-360)
- `speed`: Meters per second (m/s)
- Always include for airborne entities
- Omit if stationary

### Contact/Callsign Standards

**UID vs Callsign**:
- `uid`: Machine identifier (stable, unique) - e.g., "16:AA:BB:CC:DD:EE:FF" (drone MAC)
- `callsign`: Human-readable label - e.g., "DJI-MAVIC-123456"

**Best Practice**: Use same value for both unless there's a specific display name.

### Icon Standards

TAK/ATAK icon paths use standard format:
- **Drones**: Default to type-based icon (don't override with `usericon`)
- **Pilots**: `com.atakmap.android.maps.public/Civilian/Person.png`
- **Home**: `com.atakmap.android.maps.public/Civilian/House.png`

**Modern Approach**: Let TAK derive icon from event `type` attribute rather than hardcoding `usericon`.

### Remarks Field Best Practices

Include operationally relevant information in human-readable format:

```
MAC: AA:BB:CC:DD:EE:FF, RSSI: -65dBm; UA Type: Multirotor (2);
Operator: [CAA: OP-123]; Speed: 12.5 m/s; Course: 180°;
Alt: 100.5m AGL; Freq: ~2437 MHz
```

**Security Note**: Escape XML special characters using proper escaping.

---

## Design Decisions for Refactored Implementation

### 1. Separation of Concerns

**Legacy**: CoT generation mixed into Drone model (`drone.to_cot_xml()`)
**Refactored**: Pure function generator (`CotGenerator.generate_drone_event()`)

**Benefits**:
- Testable without Drone instances
- Can generate CoT from any data source
- Easier to mock and validate
- No model pollution

### 2. Configurability

```python
class CotGenerator:
    def __init__(
        self,
        default_stale_seconds: float = 60.0,
        default_ce: float = 35.0,
        default_le: float = 999999.0,
        version: str = "2.0",
        use_modern_types: bool = True  # Use -Q suffix for drones
    ):
        ...
```

### 3. Three Message Types

1. **Drone Event** - Main telemetry
2. **Pilot Event** - Operator location (if available)
3. **Home Event** - Home point (if available)

Each has dedicated method with proper type codes and icons.

### 4. Accuracy Parsing

```python
def _parse_accuracy(accuracy_str: str) -> Optional[float]:
    """Parse Remote ID accuracy strings like '10m' to float"""
    if not accuracy_str:
        return None
    # Extract numeric value from strings like "10m", "3.5m", etc.
    ...
```

### 5. Type Mapping with Modern Codes

```python
# Modern UAV/drone type codes (MIL-STD-2525 compliant)
UA_TYPE_TO_COT_TYPE = {
    1: 'a-u-A-M-F-Q',   # Fixed wing drone (military, unmanned)
    2: 'a-u-A-M-H-Q',   # Multirotor drone (military, unmanned)
    3: 'a-u-A-M-H-Q',   # Gyroplane (rotary drone)
    4: 'a-u-A-M-H-Q',   # VTOL drone
    5: 'a-u-A-C-F-q',   # Ornithopter (civilian fixed, lowercase q)
    6: 'a-u-A-C-F-q',   # Glider (civilian fixed)
    # ... rest default to a-u-A-M-H-Q (unknown rotary drone)
}
```

**Rationale**:
- Most Remote ID drones are recreational/civilian → use `unknown` affiliation
- `-Q` suffix explicitly marks as unmanned/drone
- Helps TAK systems properly categorize and display

### 6. Timezone-Aware Timestamps

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)  # NOT datetime.utcnow()
time_str = now.isoformat().replace('+00:00', 'Z')
stale = now + timedelta(seconds=stale_offset)
```

### 7. XML Generation

**Options Considered**:
1. lxml (current) - Fast, but extra dependency
2. xml.etree.ElementTree (stdlib) - Good balance
3. String templates - Fast but error-prone

**Choice**: Use `xml.etree.ElementTree` (stdlib) for refactored code
- No extra dependencies
- Fast enough for our use case
- Proper escaping built-in
- Can upgrade to lxml later if needed

### 8. Validation

```python
def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate WGS84 coordinates"""
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
```

### 9. Performance Considerations

- Generate XML only when needed (not on every drone update)
- Reuse ElementTree builder
- Avoid string concatenation for XML
- Consider caching formatted timestamps for high-frequency updates

---

## API Design

### CotGenerator Class

```python
class CotGenerator:
    """
    Generates Cursor on Target (CoT) XML messages compliant with TAK standards.

    Features:
    - Modern MIL-STD-2525 type codes with drone designators (-Q suffix)
    - Timezone-aware timestamps
    - Accurate CE/LE from Remote ID data
    - Configurable stale times
    - Proper XML escaping
    """

    def generate_drone_event(
        self,
        drone: Drone,
        stale_seconds: Optional[float] = None
    ) -> bytes:
        """Generate CoT XML for drone main event"""

    def generate_pilot_event(
        self,
        drone: Drone,
        stale_seconds: Optional[float] = None
    ) -> bytes:
        """Generate CoT XML for pilot location"""

    def generate_home_event(
        self,
        drone: Drone,
        stale_seconds: Optional[float] = None
    ) -> bytes:
        """Generate CoT XML for home point"""
```

### Usage Example

```python
from refactor_project.messaging.cot_generator import CotGenerator
from refactor_project.models.drone import Drone

generator = CotGenerator(
    default_stale_seconds=30.0,  # 30 second stale time for drones
    use_modern_types=True  # Use -Q suffix
)

# Generate drone CoT
drone_xml = generator.generate_drone_event(drone, stale_seconds=30.0)

# Generate pilot CoT (if pilot location available)
if drone.pilot_lat != 0.0 or drone.pilot_lon != 0.0:
    pilot_xml = generator.generate_pilot_event(drone)

# Generate home CoT (if home location available)
if drone.home_lat != 0.0 or drone.home_lon != 0.0:
    home_xml = generator.generate_home_event(drone)
```

---

## Testing Strategy

### Test Coverage Goals: >80%

1. **Unit Tests**:
   - XML structure validation
   - Type code mapping
   - Timestamp formatting
   - Accuracy parsing
   - Coordinate validation
   - Escaping special characters

2. **Integration Tests**:
   - Full Drone → CoT workflow
   - Pilot and Home event generation
   - Stale time calculations

3. **Validation Tests**:
   - XML schema compliance (if XSD available)
   - TAK server compatibility
   - Round-trip parsing

### Test Data

Use existing Drone models from Phase 1 tests, plus:
- Drones with all fields populated
- Drones with minimal fields
- Edge cases (special characters in remarks, extreme coordinates, etc.)

---

## Migration from Legacy

| Legacy Code | Refactored Code |
|-------------|-----------------|
| `drone.to_cot_xml()` | `generator.generate_drone_event(drone)` |
| `drone.to_pilot_cot_xml()` | `generator.generate_pilot_event(drone)` |
| `drone.to_home_cot_xml()` | `generator.generate_home_event(drone)` |
| Mixed in model | Separate messaging layer |
| `datetime.utcnow()` | `datetime.now(timezone.utc)` |
| `a-u-A-M-H-R` | `a-u-A-M-H-Q` (modern drone code) |
| Hardcoded CE/LE | Parsed from Remote ID accuracy |

---

## Future Enhancements (Post-Phase 4)

1. **TAK Protobuf Support**: Add protobuf encoding for TAK Protocol v1
2. **CoT Parsing**: Parse incoming CoT messages
3. **Mesh Networking**: CoT relay/forwarding
4. **Advanced Detail Blocks**: Custom schemas for specific COIs
5. **Compression**: Support for compressed CoT streams
6. **Batching**: Combine multiple events in single message

---

## References

- MIL-STD-2525: Common Warfighting Symbology
- MITRE CoT Developer's Guide
- TAK Product Center Documentation
- FreeTAK Server CoT Implementation
- DoD XML Registry (Event.xsd)

---

**Next Steps**: Implement CotGenerator following TDD approach with comprehensive tests.
