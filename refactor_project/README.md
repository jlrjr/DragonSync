# DragonSync Refactoring Project

This directory contains the refactored DragonSync components following SOLID principles, clean architecture, and test-driven development practices.

## Goals

1. **Modularity**: Break monolithic code into well-defined, single-responsibility modules
2. **Testability**: Enable comprehensive unit testing with dependency injection
3. **Maintainability**: Clear separation of concerns and consistent patterns
4. **Extensibility**: Easy to add new sinks, parsers, and protocols
5. **Type Safety**: Comprehensive type hints throughout
6. **Documentation**: Well-documented code with docstrings and architecture docs

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        DragonSync App                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┬────────────────┐
        │               │               │                │
   ┌────▼────┐    ┌────▼────┐    ┌────▼─────┐   ┌─────▼─────┐
   │ Parsers │    │ Managers│    │Messaging │   │  Sinks    │
   └────┬────┘    └────┬────┘    └────┬─────┘   └─────┬─────┘
        │              │              │               │
   ┌────▼────┐    ┌────▼────┐    ┌────▼─────┐   ┌─────▼─────┐
   │ Models  │    │ Clients │    │  Config  │   │  Utils    │
   └─────────┘    └─────────┘    └──────────┘   └───────────┘
```

## Directory Structure

### `/models`
**Domain models and data classes**
- `drone.py` - Drone telemetry data model
- `system_status.py` - WarDragon system status model
- `location.py` - Geographic location data types
- `telemetry.py` - Base telemetry structures

**Responsibilities**:
- Pure data models with minimal logic
- Validation and property methods
- Data transformations (e.g., to CoT XML)
- No external dependencies (except for serialization libs)

### `/parsers`
**Telemetry parsing and data extraction**
- `base_parser.py` - Abstract base parser interface
- `drone_parser.py` - Drone telemetry parsing
- `system_parser.py` - System status parsing
- `protocol_parsers/` - Protocol-specific parsers (WiFi RID, BLE RID, DJI)

**Responsibilities**:
- Parse raw ZMQ messages
- Extract and validate telemetry data
- Convert to domain models
- Handle parsing errors gracefully

### `/managers`
**Business logic and orchestration**
- `drone_manager.py` - Drone collection management
- `rate_limiter.py` - Rate limiting logic
- `timeout_manager.py` - Inactivity timeout handling

**Responsibilities**:
- Coordinate between parsers, models, and sinks
- Implement business rules (rate limiting, timeouts)
- Manage state (active drones, last update times)
- Orchestrate updates across sinks

### `/messaging`
**Cursor on Target (CoT) message generation**
- `cot_messenger.py` - CoT message sending
- `cot_generator.py` - CoT XML generation
- `cot_types.py` - CoT type mappings
- `multicast_handler.py` - Multicast CoT handling

**Responsibilities**:
- Generate CoT XML messages
- Handle TAK server connections
- Manage multicast groups
- Protocol-specific formatting

### `/sinks`
**Output adapters for various protocols**
- `base_sink.py` - Abstract sink interface
- `mqtt_sink.py` - MQTT publishing
- `lattice_sink.py` - Lattice integration
- `ha_sink.py` - Home Assistant specific logic
- `tak_sink.py` - TAK server sink

**Responsibilities**:
- Publish drone data to external systems
- Handle protocol-specific formatting
- Manage connections and reconnection logic
- Implement sink-specific rate limiting

### `/clients`
**External service clients**
- `base_client.py` - Abstract client interface
- `tak_client.py` - TAK server TCP/TLS client
- `tak_udp_client.py` - TAK server UDP client
- `mqtt_client.py` - MQTT broker client
- `lattice_client.py` - Lattice API client

**Responsibilities**:
- Handle low-level protocol communications
- Connection management and retries
- TLS/SSL handling
- Error handling and logging

### `/config`
**Configuration management**
- `config_loader.py` - Configuration file loading
- `config_validator.py` - Configuration validation
- `settings.py` - Settings data classes
- `defaults.py` - Default configuration values

**Responsibilities**:
- Load and parse INI configuration
- Validate configuration values
- Provide typed configuration access
- Environment variable overrides

### `/utils`
**Shared utilities**
- `geo_utils.py` - Geographic calculations
- `xml_utils.py` - XML escaping and formatting
- `time_utils.py` - Time/timestamp utilities
- `network_utils.py` - Network interface resolution
- `tls_utils.py` - TLS/SSL certificate handling

**Responsibilities**:
- Reusable utility functions
- No business logic
- Pure functions where possible
- Well-tested helper functions

### `/tests`
**Comprehensive unit tests**
- `test_models/` - Model tests
- `test_parsers/` - Parser tests
- `test_managers/` - Manager tests
- `test_messaging/` - CoT messaging tests
- `test_sinks/` - Sink tests
- `test_clients/` - Client tests
- `fixtures/` - Test data and fixtures
- `mocks/` - Mock objects

**Testing approach**:
- Unit tests for all modules
- Integration tests for complex flows
- Mock external dependencies
- High code coverage (target: >80%)
- Test edge cases and error conditions

### `/docs`
**Architecture and design documentation**
- `ARCHITECTURE.md` - System architecture
- `DESIGN_PATTERNS.md` - Design patterns used
- `API.md` - Module APIs
- `MIGRATION.md` - Migration guide from legacy code

## Design Principles

### 1. Single Responsibility Principle (SRP)
Each class/module has one reason to change. For example:
- `Drone` model only handles drone data
- `DroneParser` only parses drone telemetry
- `MqttSink` only publishes to MQTT

### 2. Open/Closed Principle (OCP)
Open for extension, closed for modification:
- Abstract base classes for parsers, sinks, clients
- New protocols/sinks added without modifying existing code
- Plugin architecture for extensibility

### 3. Liskov Substitution Principle (LSP)
All sinks implement the same interface:
```python
class BaseSink(ABC):
    @abstractmethod
    def publish_drone(self, drone: Drone) -> None:
        pass
```

### 4. Interface Segregation Principle (ISP)
Clients don't depend on methods they don't use:
- Separate interfaces for drone/pilot/home publishing
- Optional capabilities (mark_inactive, close)

### 5. Dependency Inversion Principle (DIP)
Depend on abstractions, not concretions:
- Managers receive sink interfaces, not concrete implementations
- Configuration injected, not hardcoded
- Mock-friendly for testing

## Refactoring Strategy

### Phase 1: Core Models ✓
1. Extract `Drone` model with tests
2. Extract `SystemStatus` model with tests
3. Create base data types (Location, Telemetry)

### Phase 2: Parsers
1. Create `BaseParser` abstract class
2. Refactor `telemetry_parser.py` → `parsers/drone_parser.py`
3. Add comprehensive parser tests
4. Support protocol-specific parsers

### Phase 3: Managers
1. Extract `DroneManager` with dependency injection
2. Create `RateLimiter` utility
3. Create `TimeoutManager` utility
4. Add manager tests with mocked sinks

### Phase 4: Messaging
1. Extract CoT generation logic from `Drone` model
2. Create `CotGenerator` class
3. Refactor `CotMessenger` with client injection
4. Add CoT XML validation tests

### Phase 5: Sinks
1. Create `BaseSink` interface
2. Refactor `MqttSink` with client injection
3. Refactor `LatticeSink` with client injection
4. Create `TakSink` wrapper
5. Add sink tests with mocked clients

### Phase 6: Clients
1. Create `BaseClient` interface
2. Extract `TakClient` and `TakUdpClient`
3. Create `MqttClient` wrapper
4. Create `LatticeClient`
5. Add client tests with mocked network

### Phase 7: Configuration
1. Extract configuration loading
2. Add validation layer
3. Create typed settings classes
4. Add configuration tests

### Phase 8: Integration
1. Create new `dragonsync_refactored.py` main app
2. Wire up all components
3. Integration tests
4. Performance testing
5. Side-by-side comparison

## Testing Strategy

### Unit Tests
- Test each module in isolation
- Mock all external dependencies
- Test edge cases and error handling
- Aim for >80% code coverage

### Integration Tests
- Test component interactions
- Test with real-ish data (from test fixtures)
- Test error propagation
- Test configuration scenarios

### Test Fixtures
- Sample drone telemetry messages
- Sample CoT XML
- Sample configuration files
- Mock ZMQ messages

### Running Tests
```bash
# Run all tests
python -m pytest refactor_project/tests/

# Run with coverage
python -m pytest --cov=refactor_project --cov-report=html refactor_project/tests/

# Run specific test module
python -m pytest refactor_project/tests/test_models/test_drone.py

# Run with verbose output
python -m pytest -v refactor_project/tests/
```

## Code Standards

### Style
- Follow PEP 8
- Use Black formatter (line length: 100)
- Use isort for import sorting
- Use pylint/flake8 for linting

### Type Hints
- All functions have type hints
- Use `Optional`, `Union`, `Dict`, `List` from `typing`
- Use `dataclasses` or `pydantic` for data models
- Use `Protocol` for structural typing where appropriate

### Documentation
- All modules have docstrings
- All public classes/functions have docstrings
- Use Google-style docstrings
- Include examples in docstrings where helpful

### Error Handling
- Use specific exception types
- Log errors appropriately
- Graceful degradation where possible
- Don't swallow exceptions silently

## Migration Path

The refactored code lives alongside the original code:
- Original: `/dragonsync.py`, `/drone.py`, etc.
- Refactored: `/refactor_project/*`

This allows:
1. Incremental development
2. Side-by-side testing
3. Gradual migration
4. Easy rollback if needed

Once refactored code is stable:
1. Deprecate original files
2. Move refactored code to root
3. Update imports
4. Remove old files

## Development Workflow

1. **Pick a module** to refactor (follow phase order)
2. **Write tests first** (TDD approach)
3. **Extract and refactor** the module
4. **Run tests** - ensure all pass
5. **Update documentation**
6. **Commit changes** with descriptive message
7. **Move to next module**

## Contributing

When adding new refactored modules:
1. Follow the directory structure
2. Add comprehensive tests
3. Update this README
4. Add docstrings
5. Run linters and formatters
6. Ensure tests pass

## Dependencies

```
# Core
python >= 3.9

# Required
zmq
lxml
cryptography

# Optional (for specific sinks)
paho-mqtt  # MQTT sink
requests   # Lattice sink
netifaces  # Network interface resolution

# Development/Testing
pytest
pytest-cov
pytest-mock
black
isort
pylint
flake8
mypy
```

## Next Steps

1. ✓ Create directory structure
2. ✓ Write this README
3. → Start Phase 1: Extract and test core models
4. → Continue through phases systematically
5. → Build comprehensive test suite
6. → Create integration tests
7. → Performance benchmarking
8. → Migration to production

## Resources

- [Original DragonSync README](../README.md)
- [Testing Documentation](../tests/README.md)
- [CoT Specification](https://www.mitre.org/sites/default/files/pdf/09_4937.pdf)
- [MQTT Protocol](https://mqtt.org/)
- [Home Assistant MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/)

---

**Status**: 🚧 Active Development
**Last Updated**: 2025-11-15
**Maintained By**: DragonSync Contributors
