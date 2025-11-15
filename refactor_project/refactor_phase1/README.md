# DragonSync 2.0 (Refactored)

A modular, testable, production-ready gateway that converts drone detections (Remote ID, DJI) and ADS-B aircraft data into Cursor on Target (CoT) messages for TAK/ATAK, with optional MQTT/Home Assistant and Lattice integration.

## 🎯 What's New in 2.0

This is a **complete refactor** of DragonSync with:

- ✅ **Clean Architecture** - Separation of concerns, no spaghetti code
- ✅ **Type Safety** - Full type hints and mypy checking
- ✅ **Comprehensive Tests** - Unit and integration tests with >80% coverage
- ✅ **Modern Python** - Async/await throughout, Python 3.9+
- ✅ **Easy Maintenance** - Modular design, clear interfaces
- ✅ **Production Ready** - Proper logging, error handling, validation

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/jlrjr/DragonSync.git
cd DragonSync

# Install dependencies
pip install -r requirements.txt

# Copy example config and customize
cp config.ini.example config.ini
nano config.ini

# Run DragonSync
python -m dragonsync.main -c config.ini
```

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=dragonsync --cov-report=html

# Check code quality
ruff check dragonsync/
mypy dragonsync/
black --check dragonsync/
```

## 📁 Project Structure

```
DragonSync/
├── dragonsync/              # Main package
│   ├── core/               # Domain models & logic
│   │   └── models.py       # Drone, Aircraft, Position, etc.
│   ├── inputs/             # Data ingestion adapters
│   │   ├── zmq_drone.py    # ZMQ drone telemetry
│   │   ├── zmq_status.py   # ZMQ system status
│   │   └── adsb.py         # ADS-B HTTP client
│   ├── outputs/            # Data export adapters
│   │   ├── tak_multicast.py
│   │   ├── tak_server.py
│   │   ├── mqtt.py
│   │   └── lattice.py
│   ├── config/             # Configuration management
│   ├── services/           # Business logic & orchestration
│   └── utils/              # Utilities (logging, etc.)
│
├── tests/                  # Comprehensive test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
│
└── docs/                  # Documentation
```

## 🔧 Configuration

DragonSync uses an INI-style configuration file. See `config.ini.example` for all options.

### Minimal Configuration

```ini
[SETTINGS]
# At minimum, enable one output
enable_multicast = true
```

### Common Configurations

**TAK Server (TCP with TLS):**
```ini
[SETTINGS]
tak_host = your-tak-server.com
tak_port = 8089
tak_protocol = tcp
tak_tls_p12 = /path/to/cert.p12
tak_tls_p12_pass = your-password
```

**Home Assistant via MQTT:**
```ini
[SETTINGS]
mqtt_enabled = true
mqtt_host = 192.168.1.100
ha_enabled = true
```

**ADS-B Integration:**
```ini
[SETTINGS]
adsb_enabled = true
adsb_json_url = http://127.0.0.1:8080/?all_with_pos
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/core/test_models.py

# Run with coverage
pytest --cov=dragonsync --cov-report=term-missing

# Run only integration tests
pytest tests/integration/
```

## 📊 Architecture

DragonSync follows **clean architecture** principles:

1. **Core Layer** - Domain models (Drone, Aircraft, etc.) with no external dependencies
2. **Adapter Layer** - Input and output adapters that implement abstract interfaces
3. **Service Layer** - Orchestration, rate limiting, timeout management
4. **Infrastructure** - Configuration, logging, utilities

### Data Flow

```
[ZMQ/ADS-B] → [Input Adapters] → [Tracking Manager] → [CoT Generator] → [Output Adapters] → [TAK/MQTT/Lattice]
                                         ↓
                                 [Rate Limiter]
                                 [Timeout Manager]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure tests pass (`pytest`)
5. Ensure code quality (`ruff check`, `mypy`)
6. Commit your changes
7. Push to the branch
8. Open a Pull Request

## 📝 Migration from v1.x

If you're upgrading from the original DragonSync:

1. Your existing `config.ini` should work with minimal changes
2. The new version runs alongside the old (different entry point)
3. See `MIGRATION.md` for detailed migration guide

## 📄 License

Apache License 2.0 - See LICENSE file for details

## 🙏 Acknowledgments

- Original DragonSync by cemaxecuter
- DroneID by @alphafox02
- WarDragon community

## 📞 Support

- GitHub Issues: [Report bugs or request features](https://github.com/jlrjr/DragonSync/issues)
- Documentation: See `docs/` directory
- Original project: [alphafox02/DragonSync](https://github.com/alphafox02/DragonSync)
