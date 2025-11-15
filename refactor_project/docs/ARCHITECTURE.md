# DragonSync Refactored Architecture

## System Overview

DragonSync is a drone detection gateway that:
1. Receives drone telemetry from ZMQ feeds (WiFi RID, BLE RID, DJI)
2. Parses and validates drone data
3. Manages active drone state with rate limiting and timeouts
4. Publishes drone data to multiple sinks (TAK/ATAK, MQTT, Lattice)

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

### Layer 4: Output Adapters (Sinks)
```
┌─────────────────────────────────────┐
│            Sinks                    │
│  • MqttSink                         │
│  • LatticeSink                      │
│  • TakSink                          │
│                                     │
│  Depends on: Models, Clients        │
└─────────────────────────────────────┘
```

**Characteristics**:
- Implement BaseSink interface
- Convert models → protocol formats
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

### Layer 6: Messaging (CoT Generation)
```
┌─────────────────────────────────────┐
│          Messaging                  │
│  • CotGenerator                     │
│  • CotMessenger                     │
│  • MulticastHandler                 │
│                                     │
│  Depends on: Models, Clients        │
└─────────────────────────────────────┘
```

**Characteristics**:
- CoT XML generation
- Type mapping (UA type → CoT type)
- Multicast group management
- CoT protocol specifics

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

## Data Flow

```
┌──────────────┐
│  ZMQ Source  │
│  (Port 4224) │
└──────┬───────┘
       │ Raw JSON messages
       ▼
┌──────────────────┐
│   DroneParser    │
│  Parse & Validate│
└──────┬───────────┘
       │ Drone model
       ▼
┌──────────────────┐
│  DroneManager    │
│  • Rate limit    │
│  • Timeout check │
│  • State mgmt    │
└──────┬───────────┘
       │
       ├────────────────┬─────────────────┬─────────────────┐
       ▼                ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ CotMessenger │ │  MqttSink    │ │ LatticeSink  │ │   TakSink    │
│ (CoT XML)    │ │ (JSON+HA)    │ │ (JSON API)   │ │ (CoT XML)    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                 │                 │
       ▼                ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│TAK Multicast │ │ MQTT Broker  │ │ Lattice API  │ │  TAK Server  │
│239.2.3.1:6969│ │   (MQTT)     │ │   (HTTPS)    │ │ (TCP/TLS)    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

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
    def publish_drone(self, drone: Drone) -> None:
        pass

    def publish_pilot(self, drone_id: str, lat: float, lon: float, alt: float) -> None:
        pass

    def publish_home(self, drone_id: str, lat: float, lon: float, alt: float) -> None:
        pass

    def mark_inactive(self, drone_id: str) -> None:
        pass

    def close(self) -> None:
        pass
```

DroneManager doesn't know which sinks are connected - it just calls the interface.

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

### Adding a New Sink
1. Implement `BaseSink` interface
2. Create corresponding client if needed
3. Add configuration options
4. Wire up in main app
5. Add tests

### Adding a New Protocol Parser
1. Implement `BaseParser` interface
2. Handle protocol-specific message format
3. Convert to domain models
4. Add tests with sample messages

### Adding a New Output Format
1. Add method to domain model (e.g., `Drone.to_gpx()`)
2. Create sink that uses new format
3. Add tests

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
