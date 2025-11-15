# Getting Started with DragonSync 2.0

This guide will help you set up and start developing with the refactored DragonSync.

## 📋 Prerequisites

- Python 3.9 or higher
- pip package manager
- Git (for cloning)
- (Optional) Virtual environment tool (venv, conda, etc.)

## 🚀 Initial Setup

### 1. Clone and Navigate

```bash
cd /path/to/your/DragonSync
```

### 2. Create Virtual Environment (Recommended)

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n dragonsync python=3.11
conda activate dragonsync
```

### 3. Install Dependencies

```bash
# For running only
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

### 4. Configure

```bash
# Copy example config
cp config.ini.example config.ini

# Edit configuration
nano config.ini  # or your preferred editor
```

**Minimum config for testing:**
```ini
[SETTINGS]
enable_multicast = true
```

## ✅ Verify Installation

### Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=dragonsync --cov-report=term-missing
```

Expected output:
```
tests/unit/config/test_loader.py ......        [ 50%]
tests/unit/core/test_models.py .............   [100%]

---------- coverage: platform linux, python 3.11 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
dragonsync/__init__.py                7      0   100%
dragonsync/config/loader.py         125     25    80%   ...
dragonsync/config/models.py          65      0   100%
dragonsync/config/validator.py       98     12    88%   ...
dragonsync/core/models.py           112      5    96%   ...
---------------------------------------------------------------
TOTAL                               407     42    90%

========== 19 passed in 1.23s ==========
```

### Run Code Quality Checks

```bash
# Check code style with ruff
ruff check dragonsync/

# Check type hints with mypy
mypy dragonsync/

# Format code with black (optional)
black dragonsync/ tests/
```

### Test the Main Entry Point

```bash
# This will validate your config and show startup info
python -m dragonsync.main -c config.ini

# Or with debug logging
python -m dragonsync.main -c config.ini --log-level DEBUG
```

Expected output:
```
============================================================
DragonSync 2.0 - Drone Detection Gateway
============================================================
2024-01-15 12:34:56 - dragonsync.main - INFO - Loading configuration from config.ini
2024-01-15 12:34:56 - dragonsync.main - INFO - Configuration loaded and validated successfully
2024-01-15 12:34:56 - dragonsync.main - INFO - DragonSync initialized (Phase 1 - Core models only)
2024-01-15 12:34:56 - dragonsync.main - INFO - ZMQ listening on 127.0.0.1:4224
2024-01-15 12:34:56 - dragonsync.main - INFO - TAK multicast enabled: 239.2.3.1:6969
2024-01-15 12:34:56 - dragonsync.main - INFO - Press Ctrl+C to stop
```

## 📂 Project Structure Overview

```
DragonSync_Refactor/
├── dragonsync/                 # Main package
│   ├── core/                   # ✅ COMPLETE - Domain models
│   │   └── models.py           # Drone, Aircraft, Position, etc.
│   ├── config/                 # ✅ COMPLETE - Configuration
│   │   ├── loader.py           # Load from INI files
│   │   ├── models.py           # Config dataclasses
│   │   └── validator.py        # Validation logic
│   ├── utils/                  # ✅ COMPLETE - Utilities
│   │   └── logging.py          # Logging setup
│   ├── inputs/                 # 🚧 TODO - Phase 3
│   ├── outputs/                # 🚧 TODO - Phase 4
│   ├── services/               # 🚧 TODO - Phase 5
│   └── main.py                 # Entry point
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   │   ├── core/               # ✅ Model tests
│   │   └── config/             # ✅ Config tests
│   ├── integration/            # 🚧 TODO - Phase 6
│   └── fixtures/               # Test data
│       ├── sample_zmq_messages.json
│       ├── sample_adsb_response.json
│       └── mock_config.ini
│
├── config.ini.example          # Example configuration
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
└── pyproject.toml              # Project metadata
```

## 🧪 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Write Tests First (TDD)

```bash
# Create test file
touch tests/unit/core/test_new_feature.py

# Write your test
cat > tests/unit/core/test_new_feature.py << 'EOF'
import pytest
from dragonsync.core.models import YourNewModel

def test_your_feature():
    # Arrange
    model = YourNewModel(...)
    
    # Act
    result = model.do_something()
    
    # Assert
    assert result == expected_value
EOF

# Run test (it should fail)
pytest tests/unit/core/test_new_feature.py
```

### 3. Implement Feature

```bash
# Edit the implementation
nano dragonsync/core/models.py

# Run test again (it should pass)
pytest tests/unit/core/test_new_feature.py
```

### 4. Run Full Test Suite

```bash
pytest
```

### 5. Check Code Quality

```bash
ruff check dragonsync/
mypy dragonsync/
black --check dragonsync/
```

### 6. Commit and Push

```bash
git add .
git commit -m "Add: Your feature description"
git push origin feature/your-feature-name
```

## 🐛 Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'dragonsync'`:

```bash
# Make sure you're in the project root
pwd  # Should show .../DragonSync_Refactor

# Install in development mode
pip install -e .
```

### Test Failures

```bash
# Run with verbose output to see details
pytest -v

# Run specific test
pytest tests/unit/core/test_models.py::TestDrone::test_drone_creation -v

# Run with print statements visible
pytest -v -s
```

### Type Checking Errors

```bash
# See detailed mypy output
mypy dragonsync/ --show-error-codes --pretty

# Ignore specific errors (add to pyproject.toml)
# [tool.mypy]
# ignore_errors = false
```

## 📚 Next Steps

Now that you have Phase 1 complete, you can:

1. **Review the refactor plan**: See `dragonsync_refactor_plan.md`
2. **Start Phase 2**: Implement CoT generation and tracking logic
3. **Add integration tests**: Test end-to-end flows
4. **Implement input adapters**: ZMQ and ADS-B clients
5. **Implement output adapters**: TAK, MQTT, Lattice

## 🎯 Current Status (Phase 1 Complete)

✅ **Completed:**
- Project structure and packaging
- Core data models (Drone, Aircraft, Position, SystemStatus)
- Configuration management (loading, validation)
- Logging infrastructure
- Unit tests for models and config
- CI/CD pipeline (GitHub Actions)
- Development tooling setup

🚧 **TODO (See refactor plan):**
- CoT message generation (Phase 2)
- Tracking and state management (Phase 2)
- Input adapters: ZMQ, ADS-B (Phase 3)
- Output adapters: TAK, MQTT, Lattice (Phase 4)
- Main orchestrator (Phase 5)
- Integration tests (Phase 6)

## 💡 Tips

- **Always run tests** before committing
- **Use type hints** - they catch bugs early
- **Keep modules small** - aim for <500 lines per file
- **Write docstrings** - explain *why*, not just *what*
- **Follow the plan** - resist scope creep

## 🤝 Need Help?

- Check `dragonsync_refactor_plan.md` for detailed tasks
- Review existing code for patterns
- Run `pytest -v` to see what's tested
- Ask questions in GitHub issues

Happy coding! 🚀
