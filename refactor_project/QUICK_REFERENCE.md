# DragonSync 2.0 - Quick Reference Card

## 🚀 Installation & Setup

```bash
# Extract archive
tar -xzf dragonsync_refactor_phase1.tar.gz
cd DragonSync_Refactor

# Install dependencies
pip install -r requirements-dev.txt

# Create config
cp config.ini.example config.ini
```

## ✅ Verification Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dragonsync --cov-report=term-missing

# Type check
mypy dragonsync/

# Lint
ruff check dragonsync/

# Format check
black --check dragonsync/

# Run application
python -m dragonsync.main -c config.ini
```

## 📂 Project Layout

```
dragonsync/
├── core/models.py          # ✅ Domain models
├── config/                 # ✅ Config management
│   ├── loader.py
│   ├── models.py
│   └── validator.py
├── utils/logging.py        # ✅ Logging setup
├── inputs/                 # 🚧 Phase 3
├── outputs/                # 🚧 Phase 4
└── services/               # 🚧 Phase 5
```

## 🧪 Testing

```bash
# Run specific test file
pytest tests/unit/core/test_models.py -v

# Run specific test
pytest tests/unit/core/test_models.py::TestDrone::test_drone_creation

# Run with print statements
pytest -v -s

# Watch mode (with pytest-watch)
ptw
```

## 📝 Common Tasks

### Add New Model
1. Edit `dragonsync/core/models.py`
2. Create `tests/unit/core/test_your_model.py`
3. Run `pytest tests/unit/core/test_your_model.py`

### Add Config Option
1. Edit `dragonsync/config/models.py` (add field to dataclass)
2. Edit `dragonsync/config/loader.py` (parse from INI)
3. Edit `dragonsync/config/validator.py` (add validation)
4. Update `config.ini.example`

### Debug Tests
```python
# In test file, use pytest's capsys
def test_something(capsys):
    print("Debug output")
    # ... test code ...
    captured = capsys.readouterr()
    print(captured.out)

# Or use breakpoint
def test_something():
    breakpoint()  # Drops into pdb
```

## 🔧 Configuration Quick Reference

```ini
[SETTINGS]
# ZMQ Inputs
zmq_host = 127.0.0.1
zmq_port = 4224
zmq_status_port = 4225

# TAK Multicast (easiest for testing)
enable_multicast = true
tak_multicast_addr = 239.2.3.1
tak_multicast_port = 6969

# TAK Server (optional)
tak_host = your-server.com
tak_port = 8089
tak_protocol = tcp

# MQTT/HA (optional)
mqtt_enabled = true
mqtt_host = 192.168.1.100
ha_enabled = true

# ADS-B (optional)
adsb_enabled = true
adsb_json_url = http://127.0.0.1:8080/?all_with_pos

# Runtime
rate_limit = 3.0
max_drones = 30
inactivity_timeout = 60.0

[gps]
use_static_gps = true
static_lat = 42.3601
static_lon = -71.0589
static_alt = 10.0
```

## 🐍 Python API Examples

### Create Position
```python
from dragonsync.core.models import Position

pos = Position(
    latitude=42.3601,
    longitude=-71.0589,
    altitude=50.0
)
```

### Create Drone
```python
from dragonsync.core.models import Drone, DroneType

drone = Drone(
    id="AA:BB:CC:DD:EE:FF",
    drone_type=DroneType.REMOTE_ID_BLE,
    position=pos,
    speed=12.5,
    heading=180.0
)
```

### Load Config
```python
from dragonsync.config.loader import ConfigLoader

config = ConfigLoader.from_ini("config.ini")
print(f"ZMQ port: {config.zmq.drone_port}")
```

### Validate Config
```python
from dragonsync.config.validator import ConfigValidator

errors = ConfigValidator.validate(config)
if errors:
    for error in errors:
        print(f"Error: {error}")
```

## 🎯 Phase Status

- ✅ Phase 1: Foundation (COMPLETE)
- 🚧 Phase 2: Core Logic (CoT generation, tracking)
- 🚧 Phase 3: Input Adapters (ZMQ, ADS-B)
- 🚧 Phase 4: Output Adapters (TAK, MQTT, Lattice)
- 🚧 Phase 5: Orchestration (Main service)
- 🚧 Phase 6: Integration Tests
- 🚧 Phase 7: Polish & Deploy

## 📚 Key Files

| File | Purpose |
|------|---------|
| `REFACTOR_PLAN.md` | Complete 7-week roadmap |
| `GETTING_STARTED.md` | Developer setup guide |
| `README.md` | Project overview |
| `PHASE1_SUMMARY.md` | What we built |
| `pyproject.toml` | Package configuration |
| `config.ini.example` | Config template |

## 🔗 Important Imports

```python
# Models
from dragonsync.core.models import (
    Drone, Aircraft, SystemStatus, Position,
    DroneType, AircraftCategory
)

# Config
from dragonsync.config.models import DragonSyncConfig
from dragonsync.config.loader import ConfigLoader
from dragonsync.config.validator import ConfigValidator

# Utils
from dragonsync.utils.logging import setup_logging, get_logger
```

## 💡 Tips

- **Run tests often**: `pytest`
- **Use type hints**: MyPy catches bugs early
- **Keep functions small**: <50 lines
- **Write docstrings**: Explain why, not what
- **Follow the plan**: See REFACTOR_PLAN.md

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors | `pip install -e .` |
| Tests fail | `pytest -v` for details |
| Type errors | `mypy dragonsync/ --show-error-codes` |
| Lint errors | `ruff check --fix dragonsync/` |

## 📞 Resources

- Refactor Plan: `REFACTOR_PLAN.md`
- Getting Started: `GETTING_STARTED.md`
- Test Fixtures: `tests/fixtures/`
- Example Config: `config.ini.example`

---

**Current Status:** Phase 1 Complete ✅  
**Next Step:** Phase 2 - CoT Generation & Tracking  
**Questions?** See GETTING_STARTED.md or REFACTOR_PLAN.md
