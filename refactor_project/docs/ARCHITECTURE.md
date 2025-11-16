# DragonSync Refactored Architecture

## System Overview

DragonSync is a multi-source tracking gateway that:
1. Receives telemetry from multiple sources (Remote ID, ADS-B, AIS, etc.)
2. Parses and normalizes data into domain models
3. Converts all sources to Cursor on Target (CoT) XML - the universal interchange format
4. Distributes CoT to multiple output sinks (TAK/ATAK, MQTT, Lattice)

**Key Architectural Decision**: CoT serves as the universal internal format, enabling linear scaling (N sources + M sinks) instead of N×M conversions.

## Architectural Layers

### Layer 1: Data Models (Pure Domain)
```
┌─────────────────────────────────────┐
│         Domain Models               │
│  • Drone                            │
│  • SystemStatus                     │
│  • Location                         │
│  • Telemetry                        │
│                                     │
│  No dependencies on infrastructure  │
└─────────────────────────────────────┘
```

**Characteristics**:
- Pure Python data classes
- Validation logic
- Data transformations
- No I/O operations
- No external service dependencies

### Layer 2: Parsers (Data Translation)
```
┌─────────────────────────────────────┐
│           Parsers                   │
│  • DroneParser                      │
│  • SystemParser                     │
│  • Protocol-specific parsers        │
│                                     │
│  Depends on: Models                 │
└─────────────────────────────────────┘
```

**Characteristics**:
- Convert raw data → domain models
- Protocol knowledge (ZMQ message formats)
- Validation and error handling
- Stateless processing

### Layer 3: Business Logic (Use Cases)
```
┌─────────────────────────────────────┐
│          Managers                   │
│  • DroneManager                     │
│  • RateLimiter                      │
│  • TimeoutManager                   │
│                                     │
│  Depends on: Models, Sinks          │
└─────────────────────────────────────┘
```

**Characteristics**:
- Business rules (rate limiting, timeouts)
- State management (active drones)
- Orchestration across sinks
- Dependency injection for sinks

### Layer 5: Output Adapters (Sinks)
```
┌─────────────────────────────────────┐
│            Sinks                    │
│  • TakSink (CoT passthrough)        │
│  • MqttSink (CoT → JSON)            │
│  • LatticeSink (CoT → Custom)       │
│                                     │
│  Depends on: CoT XML input          │
└─────────────────────────────────────┘
```

**Characteristics**:
- **Consume CoT XML as input** (universal format)
- TAK Sink: Passes CoT through to multicast/TCP
- MQTT Sink: Parses CoT → JSON for Home Assistant
- Lattice Sink: Converts CoT → custom API format
- Delegate I/O to clients
- Handle sink-specific logic (HA discovery, etc.)

### Layer 5: External Clients (Infrastructure)
```
┌─────────────────────────────────────┐
│           Clients                   │
│  • TakClient (TCP/TLS)              │
│  • TakUdpClient (UDP)               │
│  • MqttClient                       │
│  • LatticeClient (HTTP)             │
│                                     │
│  Handles low-level I/O              │
└─────────────────────────────────────┘
```

**Characteristics**:
- Low-level protocol implementation
- Connection management
- Retry logic
- TLS/SSL handling

### Layer 4: Messaging (Universal CoT Generation)
```
┌─────────────────────────────────────┐
│    Messaging (CoT Generator)        │
│  • CotGenerator                     │
│  • generate_drone_event()           │
│  • generate_aircraft_event() [FUTR] │
│  • generate_vessel_event() [FUTURE] │
│                                     │
│  Depends on: Models only            │
└─────────────────────────────────────┘
```

**Characteristics**:
- **UNIVERSAL CONVERTER**: All sources → CoT XML
- MIL-STD-2525 type code mapping
- Timezone-aware timestamps (Python 3.12+ compatible)
- Dynamic CE/LE accuracy from telemetry
- Pure function - no I/O, fully testable
- CoT 2.0 XML schema compliant

### Layer 7: Configuration
```
┌─────────────────────────────────────┐
│        Configuration                │
│  • ConfigLoader                     │
│  • ConfigValidator                  │
│  • Settings                         │
│                                     │
│  Pure configuration management      │
└─────────────────────────────────────┘
```

**Characteristics**:
- Load INI files
- Validate settings
- Typed configuration access
- Environment overrides

## Data Flow (CoT-Centric Architecture)

```
                    ┌─────────────────────────────────┐
                    │      INPUT SOURCES              │
                    ├─────────────────────────────────┤
┌──────────────┐    │  • Remote ID (ZMQ 4224)        │    ┌──────────────┐
│   Future:    │    │  • ADS-B (1090MHz)   [FUTURE]  │    │   Future:    │
│   ADS-B      │───▶│  • Ships/AIS         [FUTURE]  │◀───│   AIS/Ships  │
│   Aircraft   │    │  • Ground Vehicles   [FUTURE]  │    │   Vessels    │
└──────────────┘    └─────────────┬───────────────────┘    └──────────────┘
                                  │
                    ┌─────────────┴───────────────┐
                    │      PROTOCOL PARSERS       │
                    │   • RemoteIDParser          │
                    │   • ADSBParser    [FUTURE]  │
                    │   • AISParser     [FUTURE]  │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │      DOMAIN MODELS          │
                    │   • Drone (dataclass)       │
                    │   • Aircraft    [FUTURE]    │
                    │   • Vessel      [FUTURE]    │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │      BUSINESS LOGIC         │
                    │   • DroneManager            │
                    │   • Rate limiting           │
                    │   • Timeout detection       │
                    │   • State management        │
                    └─────────────┬───────────────┘
                                  │
        ╔═════════════════════════▼════════════════════════╗
        ║         CoT GENERATOR (Universal Hub)            ║
        ║   • generate_drone_event()                       ║
        ║   • generate_aircraft_event()        [FUTURE]    ║
        ║   • generate_vessel_event()          [FUTURE]    ║
        ║   • MIL-STD-2525 type codes (-Q suffix)          ║
        ║   • Timezone-aware timestamps                    ║
        ╚═════════════════════════╤════════════════════════╝
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
                  ▼               ▼               ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │  TAK SINK    │ │  MQTT SINK   │ │ LATTICE SINK │
          ├──────────────┤ ├──────────────┤ ├──────────────┤
          │ CoT → TAK    │ │ CoT → JSON   │ │ CoT → Custom │
          │ (passthru)   │ │ (convert)    │ │ (convert)    │
          └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                 │                │                 │
                 ▼                ▼                 ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │TAK Multicast │ │ MQTT Broker  │ │ Lattice API  │
          │239.2.3.1:6969│ │ Home Assist. │ │   (HTTPS)    │
          │  ATAK/WinTAK │ │   (MQTT)     │ │              │
          └──────────────┘ └──────────────┘ └──────────────┘
```

**Key Points**:
- **CoT is the universal format** - all sources normalize to CoT XML
- **Sinks consume CoT** - not Drone objects directly
- **TAK Sink**: Passes CoT through (native format)
- **MQTT/Lattice Sinks**: Convert CoT → their specific formats
- **Scalability**: Adding new source = implement parser + CoT conversion
- **Future-proof**: ADS-B, AIS, ground vehicles slot in naturally

## Component Interactions

### Initialization Flow
```python
# 1. Load configuration
config = ConfigLoader.load("config.ini")
settings = ConfigValidator.validate(config)

# 2. Create clients
tak_client = TakClient(settings.tak_host, settings.tak_port, ...)
mqtt_client = MqttClient(settings.mqtt_host, settings.mqtt_port, ...)
lattice_client = LatticeClient(settings.lattice_endpoint, ...)

# 3. Create sinks
mqtt_sink = MqttSink(mqtt_client, settings)
lattice_sink = LatticeSink(lattice_client, settings)

# 4. Create messaging
cot_messenger = CotMessenger(tak_client, settings)

# 5. Create manager
drone_manager = DroneManager(
    cot_messenger=cot_messenger,
    extra_sinks=[mqtt_sink, lattice_sink],
    rate_limit=settings.rate_limit,
    inactivity_timeout=settings.inactivity_timeout
)

# 6. Create parser
drone_parser = DroneParser()

# 7. Main loop
while True:
    raw_message = zmq_socket.recv()
    drone = drone_parser.parse(raw_message)
    drone_manager.update_or_add_drone(drone.id, drone)
    drone_manager.send_updates()
```

### Update Flow
```
┌─────────────────────────────────────────────────────────┐
│ DroneManager.update_or_add_drone(drone_id, drone_data) │
└────────────────────┬────────────────────────────────────┘
                     │
    ┌────────────────┴─────────────────┐
    │                                  │
    ▼ New drone?                       ▼ Existing drone?
┌─────────────────┐              ┌──────────────────┐
│ Add to deque    │              │ Update telemetry │
│ Initialize state│              │ Update timestamp │
└─────────────────┘              └──────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ DroneManager.send_updates()                             │
│                                                          │
│ For each active drone:                                  │
│   1. Check inactivity timeout → remove if timed out     │
│   2. Check rate limit → skip if too soon                │
│   3. Generate CoT XML → send via CotMessenger           │
│   4. Publish to each sink → sink.publish_drone(drone)   │
│   5. Update last_sent_time, last_sent_lat/lon           │
└─────────────────────────────────────────────────────────┘
```

## Design Patterns

### 1. Strategy Pattern (Sinks)
Multiple sinks implement the same `BaseSink` interface:
```python
class BaseSink(ABC):
    @abstractmethod
    def publish_cot_event(self, cot_xml: bytes) -> None:
        """Publish a CoT event (universal format)"""
        pass

    def mark_inactive(self, uid: str) -> None:
        """Optional: Mark entity as inactive"""
        pass

    def close(self) -> None:
        """Cleanup resources"""
        pass
```

**Key Change**: Sinks now accept CoT XML (bytes) as input, not domain-specific objects.
- TAK Sink: Directly transmits CoT XML
- MQTT Sink: Parses CoT XML → extracts position data → publishes as JSON
- Lattice Sink: Parses CoT XML → converts to Lattice API format

Manager doesn't know which sinks are connected - it just calls the interface.

### 2. Adapter Pattern (Clients)
Clients adapt external protocols to our interfaces:
```python
class MqttClient:
    """Adapts paho-mqtt to our interface"""
    def publish(self, topic: str, payload: str) -> None:
        self._client.publish(topic, payload)

class LatticeClient:
    """Adapts HTTP requests to our interface"""
    def send_entity(self, entity_data: dict) -> None:
        requests.post(self._endpoint, json=entity_data)
```

### 3. Factory Pattern (Parsers)
Create appropriate parser based on message type:
```python
class ParserFactory:
    @staticmethod
    def create_parser(message_type: str) -> BaseParser:
        if message_type == "drone":
            return DroneParser()
        elif message_type == "system":
            return SystemParser()
        else:
            raise ValueError(f"Unknown type: {message_type}")
```

### 4. Dependency Injection
All dependencies injected via constructor:
```python
class DroneManager:
    def __init__(
        self,
        cot_messenger: CotMessenger,
        extra_sinks: List[BaseSink],
        rate_limit: float,
        inactivity_timeout: float
    ):
        self.cot_messenger = cot_messenger
        self.extra_sinks = extra_sinks
        # ...
```

Benefits:
- Easy to test (inject mocks)
- Easy to reconfigure
- Explicit dependencies

### 5. Observer Pattern (Implicit)
Sinks observe drone updates via the manager:
```python
# Manager notifies all sinks when drone updates
for sink in self.extra_sinks:
    sink.publish_drone(drone)
```

## Error Handling Strategy

### Principle: Graceful Degradation
If one sink fails, others continue:

```python
for sink in self.extra_sinks:
    try:
        sink.publish_drone(drone)
    except Exception as e:
        logger.warning(f"Sink failed: {sink}, error: {e}")
        # Continue to next sink
```

### Retry Strategy
Clients implement exponential backoff:
```python
class TakClient:
    def send_cot(self, cot_xml: str, max_retries: int = 3) -> bool:
        for attempt in range(max_retries):
            try:
                return self._send(cot_xml)
            except Exception as e:
                if attempt < max_retries - 1:
                    sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    return False
```

### Logging Levels
- `DEBUG`: Detailed flow (drone updates, position changes)
- `INFO`: Important events (new drone, drone removed, connection established)
- `WARNING`: Recoverable errors (sink failure, retry attempt)
- `ERROR`: Serious errors (configuration invalid, connection failed permanently)

## Testing Strategy

### Unit Tests
Test each component in isolation:

```python
def test_drone_manager_rate_limiting():
    # Arrange
    mock_messenger = Mock(spec=CotMessenger)
    mock_sink = Mock(spec=BaseSink)
    manager = DroneManager(
        cot_messenger=mock_messenger,
        extra_sinks=[mock_sink],
        rate_limit=5.0
    )

    # Act
    drone = create_test_drone()
    manager.update_or_add_drone("test-1", drone)
    manager.send_updates()  # Should send
    manager.send_updates()  # Should NOT send (too soon)

    # Assert
    assert mock_messenger.send_cot.call_count == 1
    assert mock_sink.publish_drone.call_count == 1
```

### Integration Tests
Test component interactions:

```python
def test_end_to_end_drone_flow():
    # Use real components but mock external I/O
    config = load_test_config()
    mock_zmq = create_mock_zmq_source()
    mock_tak_socket = Mock()

    # Wire up system
    app = create_dragonsync_app(config, zmq_source=mock_zmq)

    # Send test message
    mock_zmq.send_drone_message(create_test_drone_message())

    # Verify CoT sent
    assert mock_tak_socket.sendall.called
    cot_xml = mock_tak_socket.sendall.call_args[0][0]
    assert b"<event" in cot_xml
```

## Performance Considerations

### Rate Limiting
- Per-drone rate limiting prevents spam
- Configurable rate limit (default: 3 seconds)
- Tracks last sent time per drone

### Timeout Management
- Inactive drones removed after timeout (default: 60 seconds)
- Prevents memory growth
- Configurable max drones (default: 30)

### Connection Pooling
- Reuse TCP connections for TAK server
- MQTT persistent connection with reconnect
- HTTP connection pooling for Lattice

### Efficient Data Structures
- `deque` for O(1) add/remove of drones
- Dict lookup for O(1) drone access by ID
- Minimal copying of data

## Security Considerations

### TLS/SSL
- Support for TLS client certificates (PKCS#12)
- Certificate verification (can skip for testing)
- Secure MQTT connections

### Input Validation
- Validate all parsed telemetry data
- Sanitize XML output (escape special chars)
- Validate configuration values

### Secrets Management
- Don't log passwords/tokens
- Support environment variables for secrets
- Secure storage of .p12 files

## Scalability

### Current Design
- Single-threaded event loop
- Handles ~30 concurrent drones
- Suitable for WarDragon use case

### Future Scaling Options
1. **Multi-threading**: Separate threads for ZMQ, CoT, MQTT
2. **Async I/O**: Convert to asyncio for non-blocking I/O
3. **Message Queue**: Redis/RabbitMQ for buffering
4. **Horizontal Scaling**: Multiple DragonSync instances with load balancing

## Extension Points

### Adding a New Input Source (e.g., ADS-B Aircraft)
1. **Create Domain Model**: `refactor_project/models/aircraft.py`
   ```python
   @dataclass
   class Aircraft:
       icao: str
       callsign: str
       latitude: float
       longitude: float
       altitude: float
       # ... more fields
   ```

2. **Create Parser**: `refactor_project/parsers/adsb_parser.py`
   ```python
   class ADSBParser:
       def parse(self, adsb_message: bytes) -> Aircraft:
           # Protocol-specific parsing
   ```

3. **Extend CotGenerator**: Add aircraft conversion method
   ```python
   class CotGenerator:
       def generate_aircraft_event(self, aircraft: Aircraft) -> bytes:
           # Map to CoT type: a-f-A-C (friendly civilian aircraft)
           # Build CoT XML with aircraft data
   ```

4. **Create Manager**: `refactor_project/managers/aircraft_manager.py`
   ```python
   class AircraftManager:
       def __init__(self, cot_generator: CotGenerator, sinks: List[BaseSink]):
           # Similar to DroneManager
   ```

5. **Wire Up**: Connect source → parser → manager → CoT → sinks

**Key Benefit**: Sinks don't change! They already consume CoT, so new sources automatically work.

### Adding a New Sink
1. Implement `BaseSink` interface
2. Implement `publish_cot_event(cot_xml: bytes)` method
3. Parse CoT XML to extract needed data
4. Convert to sink-specific format
5. Create corresponding client if needed
6. Add configuration options
7. Wire up in main app
8. Add tests

### Future CoT Type Codes (MIL-STD-2525)

```python
# refactor_project/messaging/cot_generator.py

# Drones (current)
DRONE_TYPES = {
    'rotary': 'a-u-A-M-H-Q',    # Military rotary unmanned
    'fixed': 'a-u-A-M-F-Q',     # Military fixed unmanned
}

# Aircraft (future)
AIRCRAFT_TYPES = {
    'civilian': 'a-f-A-C',      # Friendly civilian aircraft
    'military': 'a-f-A-M-F',    # Friendly military fixed
}

# Ships (future)
VESSEL_TYPES = {
    'civilian': 'a-f-S-X',      # Friendly sea surface
    'military': 'a-f-S-C',      # Friendly combatant
}

# Ground vehicles (future)
VEHICLE_TYPES = {
    'civilian': 'a-f-G-E-V',    # Friendly ground vehicle
    'military': 'a-f-G-U-C',    # Friendly ground unit combat
}
```

## Migration Strategy

### Phase 1: Parallel Development
- Develop refactored code in `refactor_project/`
- Keep original code running
- Test new code independently

### Phase 2: Integration Testing
- Create `dragonsync_refactored.py` entry point
- Run side-by-side with original
- Compare outputs
- Performance testing

### Phase 3: Gradual Rollout
- Soft launch with select users
- Monitor for issues
- Roll back if needed
- Iterate based on feedback

### Phase 4: Full Migration
- Make refactored version default
- Deprecate original code
- Update documentation
- Remove old code

## Monitoring & Observability

### Metrics to Track
- Drones active
- Messages received (per protocol)
- Messages sent (per sink)
- Errors per sink
- Rate limit hits
- Timeout events

### Logging
- Structured logging (JSON format option)
- Log levels per module
- Contextual information (drone ID, sink type, etc.)

### Health Checks
- ZMQ connection status
- TAK connection status
- MQTT connection status
- Lattice API reachability
- GPS fix status

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: Living Document
