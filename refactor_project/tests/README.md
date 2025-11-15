# DragonSync Refactored - Test Suite

Comprehensive test suite for the refactored DragonSync components.

## Running Tests

### Run all tests
```bash
cd refactor_project
python -m pytest
```

### Run with coverage
```bash
python -m pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Run specific test file
```bash
python -m pytest tests/test_models/test_drone.py
```

### Run specific test function
```bash
python -m pytest tests/test_models/test_drone.py::test_drone_initialization
```

### Run tests by marker
```bash
# Run only unit tests (fast)
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Skip slow tests
python -m pytest -m "not slow"

# Skip network tests (for offline development)
python -m pytest -m "not network"
```

### Run with verbose output
```bash
python -m pytest -v
```

### Run with debug output
```bash
python -m pytest -vv --log-cli-level=DEBUG
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_models/             # Model tests
│   ├── test_drone.py
│   ├── test_system_status.py
│   └── test_location.py
├── test_parsers/            # Parser tests
│   ├── test_drone_parser.py
│   └── test_system_parser.py
├── test_managers/           # Manager tests
│   ├── test_drone_manager.py
│   └── test_rate_limiter.py
├── test_messaging/          # CoT messaging tests
│   ├── test_cot_generator.py
│   └── test_cot_messenger.py
├── test_sinks/              # Sink tests
│   ├── test_mqtt_sink.py
│   ├── test_lattice_sink.py
│   └── test_tak_sink.py
├── test_clients/            # Client tests
│   ├── test_tak_client.py
│   └── test_mqtt_client.py
├── fixtures/                # Test data
│   ├── sample_messages.py
│   ├── sample_cot.py
│   └── sample_configs.py
└── mocks/                   # Mock objects
    ├── mock_clients.py
    └── mock_sinks.py
```

## Test Markers

Tests are categorized with markers:

- `@pytest.mark.unit` - Unit tests (isolated, fast)
- `@pytest.mark.integration` - Integration tests (multiple components)
- `@pytest.mark.slow` - Slow tests (>1 second)
- `@pytest.mark.network` - Tests requiring network access
- `@pytest.mark.zmq` - Tests requiring ZMQ
- `@pytest.mark.mqtt` - Tests requiring MQTT broker

Example:
```python
import pytest

@pytest.mark.unit
def test_drone_initialization():
    """Test Drone model initialization."""
    drone = Drone(id="test", lat=42.0, lon=-71.0, ...)
    assert drone.id == "test"

@pytest.mark.integration
@pytest.mark.mqtt
def test_mqtt_sink_publishes_to_broker():
    """Test MQTT sink publishes to real broker."""
    # Requires MQTT broker running
    pass
```

## Fixtures

Common fixtures available in all tests (defined in `conftest.py`):

### Data Fixtures
- `sample_drone_data` - Sample drone telemetry dict
- `sample_zmq_message` - Sample ZMQ message
- `sample_config` - Sample configuration dict

### Mock Fixtures
- `mock_cot_messenger` - Mock CotMessenger
- `mock_sink` - Mock sink
- `mock_tak_client` - Mock TAK client
- `mock_mqtt_client` - Mock MQTT client

### Helper Functions
- `assert_valid_cot_xml(xml)` - Assert valid CoT XML
- `create_test_drone(**kwargs)` - Create test Drone instance

Example usage:
```python
def test_drone_manager_updates(mock_cot_messenger, mock_sink, sample_drone_data):
    """Test DroneManager sends updates."""
    manager = DroneManager(
        cot_messenger=mock_cot_messenger,
        extra_sinks=[mock_sink]
    )

    drone = Drone(**sample_drone_data)
    manager.update_or_add_drone(drone.id, drone)
    manager.send_updates()

    mock_cot_messenger.send_cot.assert_called_once()
    mock_sink.publish_drone.assert_called_once_with(drone)
```

## Writing Tests

### Test Structure (Arrange-Act-Assert)
```python
def test_example():
    # Arrange - Set up test data and mocks
    mock_client = Mock()
    sink = MqttSink(client=mock_client, config={...})
    drone = create_test_drone(id="test-1")

    # Act - Perform the action
    sink.publish_drone(drone)

    # Assert - Verify the result
    assert mock_client.publish.called
    assert mock_client.publish.call_count == 1
```

### Naming Convention
- Test files: `test_<module>.py`
- Test functions: `test_<what_is_being_tested>`
- Use descriptive names: `test_drone_manager_removes_inactive_drones`

### Docstrings
```python
def test_rate_limiter_prevents_spam():
    """Test that RateLimiter prevents messages sent too quickly.

    Given a rate limit of 5 seconds,
    When two messages are sent 1 second apart,
    Then the second message should be blocked.
    """
    pass
```

### Mocking External Dependencies
```python
from unittest.mock import Mock, patch

def test_tak_client_sends_cot(mock_tak_client):
    """Test TAK client sends CoT message."""
    # Mock socket
    with patch('socket.socket') as mock_socket:
        client = TakClient(host="localhost", port=8087)
        client.send_cot("<event>...</event>")

        mock_socket.return_value.sendall.assert_called_once()
```

### Testing Exceptions
```python
def test_parser_raises_on_invalid_message():
    """Test parser raises ValueError for invalid message."""
    parser = DroneParser()

    with pytest.raises(ValueError, match="Invalid message format"):
        parser.parse({"invalid": "data"})
```

### Parametrized Tests
```python
@pytest.mark.parametrize("ua_type,expected_cot_type", [
    (1, "a-f-A-f"),         # Fixed wing
    (2, "a-u-A-M-H-R"),     # Multirotor
    (4, "a-u-A-M-H-R"),     # VTOL
])
def test_ua_type_to_cot_type(ua_type, expected_cot_type):
    """Test UA type mapping to CoT type."""
    drone = Drone(ua_type=ua_type, ...)
    cot_xml = drone.to_cot_xml()
    assert expected_cot_type in cot_xml
```

## Coverage Goals

Target coverage: >80% for all modules

Check coverage:
```bash
python -m pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Coverage by Module Type
- Models: >90% (should be easy to test)
- Parsers: >85% (test all message formats)
- Managers: >80% (test business logic paths)
- Sinks: >75% (some network code hard to test)
- Clients: >70% (low-level I/O mocked)

## Continuous Integration

Tests run automatically on:
- Every commit (via pre-commit hook)
- Every pull request (via GitHub Actions)
- Nightly (full test suite including slow tests)

CI configuration:
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: cd refactor_project && pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Debugging Tests

### Print debugging
```python
def test_something():
    result = do_something()
    print(f"Result: {result}")  # Will show with pytest -s
    assert result == expected
```

### Use pytest debugger
```bash
# Drop into debugger on failure
python -m pytest --pdb

# Drop into debugger at start of test
python -m pytest --trace
```

### Use logging
```python
import logging

def test_something(caplog):
    """Test with log capture."""
    with caplog.at_level(logging.DEBUG):
        do_something()

    assert "Expected log message" in caplog.text
```

## Best Practices

1. **Test one thing** - Each test should verify one behavior
2. **Use descriptive names** - Test name should describe what's being tested
3. **Keep tests independent** - Tests should not depend on each other
4. **Use fixtures** - Reuse common setup code
5. **Mock external dependencies** - Don't rely on network, database, etc.
6. **Test edge cases** - Empty input, null values, boundary conditions
7. **Test error paths** - Verify exceptions and error handling
8. **Keep tests fast** - Unit tests should run in milliseconds
9. **Document complex tests** - Add docstrings explaining what's being tested

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Status**: Active Development
**Last Updated**: 2025-11-15
