# Getting Started with DragonSync Refactoring

Welcome to the DragonSync refactoring project! This guide will help you get up to speed quickly.

## What We've Built

We've created a comprehensive refactoring infrastructure with:
- **2,063 lines** of documentation
- **20 files** of project structure
- **10 directories** for organized code
- **Complete testing framework** with pytest
- **Architecture documentation** and migration guides

## Quick Overview

```
refactor_project/
├── README.md              ⭐ Start here - Project overview
├── STATUS.md              📊 Current progress and next steps
├── GETTING_STARTED.md     👋 This file
│
├── docs/
│   ├── ARCHITECTURE.md    🏗️  System architecture (534 lines)
│   └── MIGRATION.md       🔄 Migration from legacy (461 lines)
│
├── models/                💎 Domain models (Phase 1 - NEXT)
├── parsers/               🔍 Telemetry parsing
├── managers/              🎯 Business logic
├── messaging/             📨 CoT generation
├── sinks/                 📤 Output adapters
├── clients/               🔌 External clients
├── config/                ⚙️  Configuration
├── utils/                 🛠️  Utilities
│
└── tests/                 ✅ Test suite
    ├── README.md          📖 Testing guide (321 lines)
    ├── conftest.py        🔧 Shared fixtures
    ├── test_models/       Tests for models
    ├── test_parsers/      Tests for parsers
    └── ...
```

## Understanding the Current Codebase

### Legacy Code Structure
```
DragonSync (Legacy)
├── dragonsync.py         794 lines - Main app
├── drone.py              456 lines - Drone model + CoT
├── mqtt_sink.py          725 lines - MQTT + HA
├── lattice_sink.py       423 lines - Lattice
├── messaging.py          366 lines - CoT messaging
├── manager.py            179 lines - Drone management
├── telemetry_parser.py   203 lines - Parsing
└── utils.py              181 lines - Mixed utilities
```

**Issues with Legacy Code**:
- Monolithic files (up to 794 lines)
- Mixed concerns (Drone model includes CoT generation)
- Hard to test (tight coupling, no DI)
- No type hints
- Limited modularity

### Refactored Structure (Target)
```
refactor_project/
├── models/drone.py              Pure data model
├── parsers/drone_parser.py      Parse ZMQ → Drone
├── managers/drone_manager.py    Business logic with DI
├── messaging/cot_generator.py   Drone → CoT XML
├── sinks/mqtt_sink.py           MQTT output
├── clients/mqtt_client.py       MQTT I/O
└── tests/test_models/           Comprehensive tests
```

**Benefits of Refactored Code**:
- ✅ Single responsibility per module
- ✅ Dependency injection (testable)
- ✅ Type hints throughout
- ✅ Comprehensive tests (>80% coverage target)
- ✅ Clear separation of concerns
- ✅ Easy to extend (add new sinks, parsers)

## Next Steps - Phase 1: Core Models

### What We're Building First

**Phase 1** focuses on extracting pure domain models:

1. **Drone Model** (`models/drone.py`)
   - Pure data model (no CoT generation)
   - Type hints for all fields
   - Validation methods
   - Update logic

2. **SystemStatus Model** (`models/system_status.py`)
   - WarDragon system status
   - GPS data
   - Hardware metrics

3. **Location Types** (`models/location.py`)
   - Geographic coordinates
   - Validation

4. **Telemetry Base** (`models/telemetry.py`)
   - Common telemetry structures

### How to Start

#### 1. Read the Documentation
```bash
cd refactor_project

# Start with the README
cat README.md

# Understand the architecture
cat docs/ARCHITECTURE.md

# Review migration strategy
cat docs/MIGRATION.md

# Check current status
cat STATUS.md
```

#### 2. Examine Legacy Code
```bash
cd ..

# Look at current Drone model
less drone.py

# Note what's data (keep) vs. logic (extract)
# Lines 1-150: Data fields ✅ Keep in model
# Lines 200-450: CoT generation ❌ Move to messaging/
```

#### 3. Set Up Development Environment
```bash
cd refactor_project

# Install dependencies
pip install -r requirements.txt

# Verify pytest works
pytest --version

# Run tests (none yet, but should work)
pytest
```

#### 4. Start with TDD (Test-Driven Development)

**Write the test FIRST**:
```bash
# Create test file
touch tests/test_models/test_drone.py
```

**Example test** (in `tests/test_models/test_drone.py`):
```python
import pytest
from refactor_project.models.drone import Drone

def test_drone_initialization():
    """Test Drone model can be created with required fields."""
    drone = Drone(
        id="TEST-123",
        lat=42.3601,
        lon=-71.0589,
        alt=150.0,
        height=100.0,
        speed=12.5,
        vspeed=2.0,
        pilot_lat=42.36,
        pilot_lon=-71.06,
        description="Test Drone",
        mac="AA:BB:CC:DD:EE:FF",
        rssi=-65
    )

    assert drone.id == "TEST-123"
    assert drone.lat == 42.3601
    assert drone.lon == -71.0589
```

**This test will FAIL** (Drone doesn't exist yet) - that's expected!

#### 5. Implement the Model

Create `models/drone.py`:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Drone:
    """Drone telemetry data model."""

    # Required fields
    id: str
    lat: float
    lon: float
    alt: float
    height: float
    speed: float
    vspeed: float
    pilot_lat: float
    pilot_lon: float
    description: str
    mac: str
    rssi: int

    # Optional fields
    home_lat: float = 0.0
    home_lon: float = 0.0
    ua_type: Optional[int] = None
    # ... more fields

    def update(self, **kwargs) -> None:
        """Update drone telemetry fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
```

#### 6. Run Tests
```bash
pytest tests/test_models/test_drone.py -v
```

Test should now PASS! ✅

#### 7. Add More Tests
```python
def test_drone_update():
    """Test updating drone fields."""
    drone = Drone(id="TEST", lat=42.0, lon=-71.0, ...)
    drone.update(lat=43.0, lon=-72.0)

    assert drone.lat == 43.0
    assert drone.lon == -72.0

def test_drone_validation():
    """Test drone validates coordinates."""
    with pytest.raises(ValueError):
        Drone(id="TEST", lat=200.0, lon=-71.0, ...)  # Invalid lat
```

#### 8. Iterate

Repeat: Test → Code → Test → Refine

## Development Workflow

### Daily Workflow
1. **Pull latest code**: `git pull origin claude/review-refactor-branch-01QyuCcPN6mpa4wbBV1q1JJA`
2. **Pick a task** from `STATUS.md`
3. **Write tests first** (TDD)
4. **Implement code**
5. **Run tests**: `pytest`
6. **Check coverage**: `pytest --cov=models`
7. **Commit**: `git commit -m "feat: Add Drone model with tests"`
8. **Push**: `git push`

### Testing Workflow
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_models/test_drone.py

# Run with coverage
pytest --cov=models --cov-report=html

# Run only unit tests (fast)
pytest -m unit

# View coverage report
open htmlcov/index.html
```

### Code Quality
```bash
# Format code
black models/

# Sort imports
isort models/

# Type check
mypy models/

# Lint
pylint models/
```

## Key Principles

### 1. Test-Driven Development (TDD)
- ✅ Write test FIRST
- ✅ Watch it FAIL
- ✅ Write minimal code to PASS
- ✅ Refactor
- ✅ Repeat

### 2. Single Responsibility
Each module does ONE thing:
- `Drone` = data only
- `CotGenerator` = Drone → CoT XML
- `DroneParser` = ZMQ → Drone

### 3. Dependency Injection
```python
# ❌ Bad: Creates dependencies internally
class DroneManager:
    def __init__(self):
        self.mqtt_sink = MqttSink()  # Hard-coded!

# ✅ Good: Dependencies injected
class DroneManager:
    def __init__(self, mqtt_sink: MqttSink):
        self.mqtt_sink = mqtt_sink  # Testable!
```

### 4. Type Hints
```python
# ❌ Bad: No types
def update_drone(id, data):
    pass

# ✅ Good: Clear types
def update_drone(id: str, data: Drone) -> None:
    pass
```

## Common Tasks

### Add a New Model
1. Create `models/new_model.py`
2. Create `tests/test_models/test_new_model.py`
3. Write tests
4. Implement model
5. Update `models/__init__.py`

### Add a New Sink
1. Create `sinks/new_sink.py`
2. Inherit from `BaseSink`
3. Implement required methods
4. Create tests with mocked client
5. Update `sinks/__init__.py`

### Debug a Test Failure
```bash
# Run with verbose output
pytest -vv

# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s
```

## Resources

### Documentation
- `README.md` - Project overview
- `docs/ARCHITECTURE.md` - System design
- `docs/MIGRATION.md` - Migration guide
- `tests/README.md` - Testing guide
- `STATUS.md` - Current progress

### External Resources
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## Getting Help

### Questions?
- Check `README.md` for overview
- Check `docs/ARCHITECTURE.md` for design
- Check `tests/README.md` for testing help
- Check `STATUS.md` for current progress

### Common Issues

**Import Error**:
```bash
# Make sure you're in the right directory
cd /path/to/DragonSync
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Test Not Found**:
```bash
# Tests must be named test_*.py
# Functions must be named test_*
```

**Coverage Low**:
```bash
# See what's not covered
pytest --cov=models --cov-report=term-missing
```

## Next Steps

1. ✅ Read this document
2. ✅ Read `README.md`
3. ✅ Skim `docs/ARCHITECTURE.md`
4. → Start Phase 1: Create `models/drone.py`
5. → Write comprehensive tests
6. → Move to next model
7. → Continue through phases

## Success Criteria

Phase 1 is complete when:
- [ ] All models implemented
- [ ] All model tests pass
- [ ] >90% test coverage
- [ ] 100% type hint coverage
- [ ] Documentation complete
- [ ] Code review passed

---

**Ready to start?** Begin with `models/drone.py`!

**Questions?** Check the documentation or ask for help.

**Happy refactoring!** 🚀
