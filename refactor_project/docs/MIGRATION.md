# Migration Guide - Legacy to Refactored Code

This guide helps migrate from the original DragonSync codebase to the refactored version.

## Overview

The refactoring transforms a monolithic design into a modular, testable architecture:

```
BEFORE (Monolithic)                    AFTER (Modular)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dragonsync.py (794 lines)    →    Application orchestration
                                   ├── models/drone.py
                                   ├── parsers/drone_parser.py
                                   ├── managers/drone_manager.py
                                   ├── messaging/cot_messenger.py
                                   └── config/settings.py

drone.py (456 lines)         →    models/drone.py (pure data)
                                   + messaging/cot_generator.py (CoT logic)

mqtt_sink.py (725 lines)     →    sinks/mqtt_sink.py
                                   + sinks/ha_sink.py (HA-specific)
                                   + clients/mqtt_client.py (low-level)

messaging.py (366 lines)     →    messaging/cot_messenger.py
                                   + messaging/multicast_handler.py

telemetry_parser.py          →    parsers/drone_parser.py
                                   + parsers/protocol_parsers/

utils.py                     →    config/config_loader.py
                                   + utils/geo_utils.py
                                   + utils/network_utils.py
                                   + utils/tls_utils.py
```

## File-by-File Migration Map

### Core Application

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `dragonsync.py` | `main.py` | 🔴 TODO | Main application entry point |

### Models

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `drone.py` | `models/drone.py` | 🔴 TODO | Extract pure data model |
| `system_status.py` | `models/system_status.py` | 🔴 TODO | Extract system status model |

### Parsers

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `telemetry_parser.py` | `parsers/drone_parser.py` | 🔴 TODO | Refactor with BaseParser |

### Managers

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `manager.py` | `managers/drone_manager.py` | 🔴 TODO | Add dependency injection |

### Messaging

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `messaging.py` | `messaging/cot_messenger.py` | 🔴 TODO | Split CoT generation |
| (drone.py) | `messaging/cot_generator.py` | 🔴 TODO | Extract from Drone model |

### Sinks

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `mqtt_sink.py` | `sinks/mqtt_sink.py` | 🔴 TODO | Separate HA logic |
| (mqtt_sink.py) | `sinks/ha_sink.py` | 🔴 TODO | HA-specific features |
| `lattice_sink.py` | `sinks/lattice_sink.py` | 🔴 TODO | Inject client |

### Clients

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `tak_client.py` | `clients/tak_client.py` | 🔴 TODO | Extract from messaging |
| `tak_udp_client.py` | `clients/tak_udp_client.py` | 🔴 TODO | Extract from messaging |
| (mqtt_sink.py) | `clients/mqtt_client.py` | 🔴 TODO | Extract MQTT I/O |
| (lattice_sink.py) | `clients/lattice_client.py` | 🔴 TODO | Extract HTTP I/O |

### Configuration

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| `utils.py` | `config/config_loader.py` | 🔴 TODO | Config loading only |
| (utils.py) | `config/settings.py` | 🔴 TODO | Typed settings |

### Utilities

| Legacy File | Refactored Location | Status | Notes |
|------------|---------------------|--------|-------|
| (messaging.py) | `utils/network_utils.py` | 🔴 TODO | Network helpers |
| (dragonsync.py) | `utils/tls_utils.py` | 🔴 TODO | TLS/SSL helpers |
| (drone.py) | `utils/geo_utils.py` | 🔴 TODO | Geographic calculations |
| (drone.py) | `utils/xml_utils.py` | 🔴 TODO | XML escaping |

## Migration Phases

### Phase 1: Core Models ✅ READY
**Goal**: Extract pure domain models with tests

**Tasks**:
1. ✅ Create `models/` directory structure
2. 🔴 Extract `Drone` from `drone.py`
   - Remove CoT generation (move to `messaging/`)
   - Keep only data and validation
   - Add type hints
   - Write tests
3. 🔴 Extract `SystemStatus` from `system_status.py`
   - Add type hints
   - Write tests
4. 🔴 Create `models/location.py` for geographic types
5. 🔴 Create `models/telemetry.py` for base structures

**Validation**:
- [ ] All model tests pass
- [ ] Models have no external dependencies
- [ ] 100% type coverage
- [ ] >90% test coverage

### Phase 2: Parsers 🔴 TODO
**Goal**: Extract telemetry parsing with abstraction

**Tasks**:
1. Create `parsers/base_parser.py` abstract class
2. Refactor `telemetry_parser.py` → `parsers/drone_parser.py`
3. Create protocol-specific parsers (WiFi, BLE, DJI)
4. Write parser tests with sample messages

**Validation**:
- [ ] All parser tests pass
- [ ] Parsers implement BaseParser interface
- [ ] >85% test coverage

### Phase 3: Managers 🔴 TODO
**Goal**: Business logic with dependency injection

**Tasks**:
1. Extract `DroneManager` with injected dependencies
2. Create `RateLimiter` utility
3. Create `TimeoutManager` utility
4. Write manager tests with mocked sinks

**Validation**:
- [ ] Manager tests pass with mocked dependencies
- [ ] No hardcoded sinks or clients
- [ ] >80% test coverage

### Phase 4: Messaging 🔴 TODO
**Goal**: Separate CoT generation from models

**Tasks**:
1. Create `messaging/cot_generator.py`
2. Extract CoT logic from `Drone` model
3. Refactor `CotMessenger` with client injection
4. Create `MulticastHandler`
5. Write CoT XML validation tests

**Validation**:
- [ ] CoT XML validates against schema
- [ ] Messenger tests pass with mocked client
- [ ] >80% test coverage

### Phase 5: Sinks 🔴 TODO
**Goal**: Output adapters with clean interfaces

**Tasks**:
1. Create `sinks/base_sink.py` interface
2. Refactor `MqttSink` with client injection
3. Extract HA logic to `sinks/ha_sink.py`
4. Refactor `LatticeSink` with client injection
5. Create `TakSink` wrapper
6. Write sink tests with mocked clients

**Validation**:
- [ ] All sinks implement BaseSink
- [ ] Sink tests pass with mocked clients
- [ ] >75% test coverage

### Phase 6: Clients 🔴 TODO
**Goal**: Low-level I/O abstraction

**Tasks**:
1. Create `clients/base_client.py` interface
2. Extract `TakClient` and `TakUdpClient`
3. Create `MqttClient` wrapper
4. Create `LatticeClient` for HTTP
5. Write client tests with mocked network

**Validation**:
- [ ] Clients implement BaseClient
- [ ] Connection retry logic works
- [ ] >70% test coverage

### Phase 7: Configuration 🔴 TODO
**Goal**: Type-safe configuration management

**Tasks**:
1. Extract `ConfigLoader` from `utils.py`
2. Create `ConfigValidator` with validation rules
3. Create typed `Settings` dataclasses
4. Add environment variable overrides
5. Write configuration tests

**Validation**:
- [ ] Invalid configs rejected with clear errors
- [ ] Type hints throughout
- [ ] >85% test coverage

### Phase 8: Integration 🔴 TODO
**Goal**: Wire up all components

**Tasks**:
1. Create `main.py` entry point
2. Implement dependency injection
3. Write integration tests
4. Performance benchmarking
5. Side-by-side comparison with legacy

**Validation**:
- [ ] Integration tests pass
- [ ] Performance comparable to legacy
- [ ] All features work end-to-end

## Code Migration Examples

### Example 1: Drone Model

**Before** (`drone.py`):
```python
class Drone:
    def __init__(self, id, lat, lon, ...):
        self.id = id
        self.lat = lat
        # ... 50+ lines of initialization

    def to_cot_xml(self):
        # 100+ lines of CoT generation
        pass

    def update(self, lat, lon, ...):
        # Update logic
        pass
```

**After** (`models/drone.py`):
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Drone:
    """Pure drone telemetry data model."""

    id: str
    lat: float
    lon: float
    # ... with type hints

    def update(self, **kwargs) -> None:
        """Update drone telemetry."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
```

**CoT generation moved to** (`messaging/cot_generator.py`):
```python
class CotGenerator:
    """Generates CoT XML from domain models."""

    @staticmethod
    def drone_to_cot(drone: Drone, stale_offset: float) -> str:
        """Convert Drone model to CoT XML."""
        # CoT generation logic here
        pass
```

### Example 2: DroneManager

**Before** (`manager.py`):
```python
class DroneManager:
    def __init__(self, max_drones, rate_limit, ...):
        self.cot_messenger = None  # Set later
        self.extra_sinks = []      # Set later
```

**After** (`managers/drone_manager.py`):
```python
from typing import List, Optional

class DroneManager:
    """Manages drone collection with dependency injection."""

    def __init__(
        self,
        cot_messenger: Optional[CotMessenger],
        extra_sinks: List[BaseSink],
        rate_limit: float,
        inactivity_timeout: float
    ):
        self.cot_messenger = cot_messenger
        self.extra_sinks = extra_sinks
        # Dependencies injected, not created internally
```

### Example 3: Configuration

**Before** (`dragonsync.py`):
```python
config = configparser.ConfigParser()
config.read("config.ini")
zmq_host = config.get("SETTINGS", "zmq_host", fallback="127.0.0.1")
zmq_port = int(config.get("SETTINGS", "zmq_port", fallback="4224"))
# ... repeated throughout
```

**After** (`config/settings.py` + `main.py`):
```python
# config/settings.py
@dataclass
class Settings:
    zmq_host: str
    zmq_port: int
    rate_limit: float
    # ... all settings with types

# main.py
config = ConfigLoader.load("config.ini")
settings = ConfigValidator.validate(config)
# Type-safe access: settings.zmq_host
```

## Testing Migration

Each refactored component requires tests:

```python
# tests/test_models/test_drone.py
import pytest
from refactor_project.models import Drone

def test_drone_initialization():
    """Test Drone model initialization."""
    drone = Drone(
        id="test-1",
        lat=42.0,
        lon=-71.0,
        # ...
    )
    assert drone.id == "test-1"
    assert drone.lat == 42.0

def test_drone_update():
    """Test Drone model update method."""
    drone = Drone(id="test-1", lat=42.0, lon=-71.0, ...)
    drone.update(lat=43.0, lon=-72.0)
    assert drone.lat == 43.0
    assert drone.lon == -72.0
```

## Import Changes

**Before**:
```python
from drone import Drone
from manager import DroneManager
from messaging import CotMessenger
```

**After**:
```python
from refactor_project.models import Drone
from refactor_project.managers import DroneManager
from refactor_project.messaging import CotMessenger
```

## Configuration Changes

No changes needed! The refactored code uses the same `config.ini` format.

## Backward Compatibility

During migration, both versions coexist:
- Legacy: `/dragonsync.py` (still runs)
- Refactored: `/refactor_project/main.py` (new version)

## Rollback Plan

If issues arise:
1. Stop refactored version
2. Restart legacy version
3. No data loss (ZMQ streams continue)
4. Fix issues in refactored code
5. Retry when ready

## Performance Comparison

Track these metrics during migration:

| Metric | Legacy | Refactored | Change |
|--------|--------|------------|--------|
| Startup time | TBD | TBD | TBD |
| Memory usage | TBD | TBD | TBD |
| CPU usage | TBD | TBD | TBD |
| Message latency | TBD | TBD | TBD |
| Throughput (msg/s) | TBD | TBD | TBD |

## Troubleshooting

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'refactor_project'`

**Solution**: Run from correct directory or adjust PYTHONPATH:
```bash
cd /path/to/DragonSync
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m refactor_project.main
```

### Type Errors
**Problem**: `mypy` reports type errors

**Solution**: Add type stubs or ignore specific errors:
```python
# type: ignore[import]
```

### Test Failures
**Problem**: Tests fail on CI but pass locally

**Solution**: Check for:
- Environment differences (Python version, OS)
- Missing dependencies in CI
- Hardcoded paths (use relative paths)
- Time-dependent tests (use freezegun)

## Next Steps

1. Start with Phase 1 (Models)
2. Write tests first (TDD)
3. Refactor incrementally
4. Run both versions in parallel
5. Compare outputs
6. Gradually migrate

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Status**: Active Migration
