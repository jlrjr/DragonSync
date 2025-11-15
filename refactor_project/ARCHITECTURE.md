# DragonSync 2.0 Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Data Sources                        │
├─────────────┬───────────────┬──────────────┬────────────────────┤
│  ZMQ 4224   │   ZMQ 4225    │  ADS-B HTTP  │   GPS/Static       │
│  (Drones)   │   (Status)    │  (Aircraft)  │   (Position)       │
└─────┬───────┴───────┬───────┴──────┬───────┴──────────┬─────────┘
      │               │              │                  │
      ▼               ▼              ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT ADAPTERS                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ ZMQDroneInput│ZMQStatusInput│  ADSBInput   │  GPSHandler  │  │
│  │  (Phase 3)   │  (Phase 3)   │  (Phase 3)   │  (Phase 3)   │  │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬────────┘  │
│         │              │              │              │           │
│         └──────────────┴──────────────┴──────────────┘           │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CORE DOMAIN                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  MODELS (Phase 1 ✅)                                        │ │
│  │  • Drone      • Position     • DroneType                   │ │
│  │  • Aircraft   • SystemStatus • AircraftCategory            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                             │                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  BUSINESS LOGIC (Phase 2)                                  │ │
│  │  ┌──────────────────┬─────────────────────────────────┐   │ │
│  │  │  CoT Generator   │  Tracking Manager               │   │ │
│  │  │  • from_drone()  │  • update_drone()               │   │ │
│  │  │  • from_aircraft│  • check_timeouts()             │   │ │
│  │  │  • from_system() │  • rate_limiting                │   │ │
│  │  └──────────────────┴─────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER (Phase 5)                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Orchestrator                             │ │
│  │  • Coordinates all adapters                                │ │
│  │  • Manages event loop                                      │ │
│  │  • Handles graceful shutdown                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT ADAPTERS                            │
│  ┌───────────┬────────────┬──────────────┬─────────────────┐    │
│  │TAKMulticast│TAKServer  │ MQTTOutput   │ LatticeOutput   │    │
│  │ (Phase 4) │ (Phase 4)  │  (Phase 4)   │   (Phase 4)     │    │
│  └─────┬─────┴──────┬─────┴──────┬───────┴──────┬──────────┘    │
│        │            │            │              │               │
└────────┼────────────┼────────────┼──────────────┼───────────────┘
         ▼            ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Destinations                         │
├─────────────┬────────────┬──────────────┬──────────────────────┤
│ TAK/ATAK    │ TAK Server │     MQTT     │  Anduril Lattice     │
│ Multicast   │ TCP/UDP    │  (Home Asst) │      API             │
└─────────────┴────────────┴──────────────┴──────────────────────┘
```

## Data Flow Example: Drone Detection

```
1. DETECTION
   ┌────────────┐
   │ BLE Sniffer│ → ZMQ Message → Port 4224
   └────────────┘

2. INPUT ADAPTER
   ZMQDroneInput
   • Receives raw JSON
   • Parses into Drone object
   • Validates data
   
   ┌─────────────────────┐
   │  Drone              │
   │  id: "AA:BB:..."    │
   │  type: REMOTE_ID_BLE│
   │  position: {...}    │
   │  speed: 12.5 m/s    │
   └─────────────────────┘

3. TRACKING MANAGER
   • Checks rate limit (last update < 3s ago?)
   • Updates existing drone or adds new
   • Returns Drone if should send, None if rate-limited
   
4. COT GENERATOR
   • Converts Drone → CoT XML
   • Adds position, speed, heading
   • Calculates stale time
   • Formats for TAK
   
   ┌─────────────────────┐
   │  <?xml version...   │
   │  <event type="..."  │
   │    <point lat=...   │
   │    <detail>...      │
   └─────────────────────┘

5. OUTPUT ADAPTERS (parallel)
   
   TAKMulticast          MQTTOutput           LatticeOutput
   • Send UDP            • Publish state      • POST to API
   • Multicast group     • Update HA          • Include metadata
   • Port 6969           • Discovery msgs     • Rate limit
   
6. DESTINATIONS
   ATAK App             Home Assistant        Lattice Platform
   • Shows on map       • Device tracker      • Track management
   • Real-time          • History             • Integration
```

## Module Dependency Graph

```
┌───────────────────────────────────────────────────────────┐
│  Configuration Layer                                       │
│  ┌──────────────┬──────────────┬─────────────────────┐    │
│  │config.loader │config.models │config.validator     │    │
│  │   (Phase 1✅)│  (Phase 1✅) │    (Phase 1✅)       │    │
│  └──────────────┴──────────────┴─────────────────────┘    │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────┐
│  Core Domain Layer (No External Dependencies)             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ core.models (Phase 1 ✅)                              │ │
│  │   • Drone, Aircraft, Position, SystemStatus          │ │
│  │   • Pure Python dataclasses                          │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ core.cot (Phase 2)                                   │ │
│  │   • CoT XML generation                               │ │
│  │   • Pure functions (no side effects)                 │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ core.tracking (Phase 2)                              │ │
│  │   • TrackingManager (state management)               │ │
│  │   • Rate limiting, timeouts                          │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────┐
│  Adapter Layer (Depends on Core)                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ inputs.* (Phase 3)                                   │ │
│  │   • zmq_drone, zmq_status, adsb                      │ │
│  │   • Each implements InputAdapter interface           │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ outputs.* (Phase 4)                                  │ │
│  │   • tak_multicast, tak_server, mqtt, lattice         │ │
│  │   • Each implements OutputAdapter interface          │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────┐
│  Service Layer (Orchestration)                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ services.orchestrator (Phase 5)                      │ │
│  │   • Wires everything together                        │ │
│  │   • Main event loop                                  │ │
│  │   • Dependency injection                             │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

## Testing Strategy

```
┌─────────────────────────────────────────────────────────────┐
│  Unit Tests (Fast, Isolated)                                │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Mock all external dependencies                        │ │
│  │  • test_models.py     ✅ (19 tests)                    │ │
│  │  • test_config.py     ✅ (12 tests)                    │ │
│  │  • test_cot.py        (Phase 2)                        │ │
│  │  • test_tracking.py   (Phase 2)                        │ │
│  │  • test_*_input.py    (Phase 3)                        │ │
│  │  • test_*_output.py   (Phase 4)                        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Integration Tests (Slower, End-to-End)                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Use real(ish) connections                             │ │
│  │  • test_zmq_to_tak.py      (Phase 6)                   │ │
│  │  • test_adsb_to_cot.py     (Phase 6)                   │ │
│  │  • test_mqtt_ha.py         (Phase 6)                   │ │
│  │  • test_full_pipeline.py   (Phase 6)                   │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Current Implementation Status

### ✅ Phase 1 Complete
- Project structure
- Core models with validation
- Configuration system
- Logging infrastructure
- Unit tests (19+ tests)
- CI/CD pipeline

### 🚧 Phase 2 (Next)
- CoT message generator
- Tracking manager with rate limiting
- State management for drones/aircraft

### 🚧 Phase 3
- ZMQ input adapters
- ADS-B HTTP polling
- GPS handling

### 🚧 Phase 4
- TAK outputs (multicast + server)
- MQTT/Home Assistant integration
- Lattice API client

### 🚧 Phase 5
- Main orchestrator
- Event loop coordination
- Graceful shutdown

### 🚧 Phase 6
- Integration tests
- Performance optimization
- Documentation

## Key Architectural Principles

1. **Dependency Inversion**
   - Core depends on nothing
   - Adapters depend on core
   - Main wires everything together

2. **Interface Segregation**
   - Small, focused interfaces
   - InputAdapter, OutputAdapter base classes
   - Easy to add new adapters

3. **Single Responsibility**
   - Each module does one thing
   - Models just hold data
   - CoT generator just generates XML
   - Adapters just adapt

4. **Open/Closed**
   - Open for extension (new adapters)
   - Closed for modification (core stable)

5. **Testability**
   - Pure functions where possible
   - Dependency injection
   - Mock-friendly interfaces
