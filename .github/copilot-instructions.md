# openpilot AI Coding Instructions

## Project Overview

openpilot is an advanced driver assistance system (ADAS) that provides Adaptive Cruise Control (ACC), Automated Lane Centering (ALC), Forward Collision Warning (FCW), and Lane Departure Warning (LDW) for 250+ supported vehicles. The system runs on comma 3/3X devices and is built with safety as the top priority (ISO26262 guidelines).

## Architecture & Key Components

### Process Architecture
openpilot uses a microservices architecture where processes communicate via ZMQ messaging (cereal). Main components:
- **manager**: Process supervisor that starts/stops all other processes ([selfdrive/manager/manager.py](selfdrive/manager/manager.py))
- **cereal**: Cap'n Proto-based messaging system defining all inter-process communication ([cereal/](cereal/))
- **services**: Message buses with defined frequencies and logging policies ([cereal/services.py](cereal/services.py))
- **controlsd**: Main control loop running at 100Hz
- **plannerd**: Path planning and trajectory generation
- **radard**: Radar fusion and lead vehicle tracking
- **modeld**: Neural network inference for vision
- **boardd**: Interface to panda (CAN hardware)

### Car Interface Pattern
Each supported car brand has a standardized structure in [selfdrive/car/](selfdrive/car/):
- `interface.py`: Main CarInterface class, entry point for car communication
- `carstate.py`: Parses CAN messages into openpilot's CarState format
- `carcontroller.py`: Generates CAN commands to control the car
- `values.py`: Car-specific constants, limits, and supported models
- `fingerprints.py`: CAN message patterns to identify specific car models
- `radar_interface.py`: (optional) Parses radar data if available

### Safety Model (panda)
The [panda firmware](panda/) enforces openpilot's safety guarantees in C code on STM32 microcontrollers:
- Safety modes prevent unsafe CAN messages
- `controls_allowed` state gates critical commands
- Extensive unit tests in `panda/tests/safety/` verify every car's safety logic
- Hardware-in-the-loop testing validates all functionality

### Data Serialization
- All messages use Cap'n Proto schemas defined in [cereal/log.capnp](cereal/log.capnp)
- Service definitions map message types to ports and frequencies
- Custom fork extensions go in [cereal/custom.capnp](cereal/custom.capnp) (reserved structs)

## Build System

Uses SCons (not Make/CMake):
```bash
# Build everything
scons -j$(nproc)

# Build specific component
scons -j8 selfdrive/ui/

# Common flags
scons --asan          # Enable address sanitizer
scons --coverage      # Build with coverage instrumentation
```

Build targets defined in `SConscript` files throughout the repo. The build is multi-architecture aware:
- `larch64`: TICI/comma device ARM64
- `x86_64`: Linux PC
- `Darwin`: macOS
- Platform detection at [SConstruct](SConstruct) lines 77-87

## Development Workflow

### Setup
```bash
# Clone and setup environment
git clone https://github.com/commaai/openpilot.git
cd openpilot
tools/op.sh setup
source .venv/bin/activate
scons -u -j$(nproc)
```

### Testing
```bash
# Run all tests
pytest .

# Run specific test directory
cd system/loggerd && pytest .

# Test with markers
pytest -m "not slow"          # Skip slow tests
pytest -m tici                # Run only device-specific tests

# Linting
pre-commit run --all
```

Test fixtures auto-setup via [conftest.py](conftest.py) with `OpenpilotPrefix` providing clean environments per test.

### Replay for Debugging
The replay system replays logged driving data to reproduce issues:
```bash
# Authenticate to access your routes
python tools/lib/auth.py

# Replay a route
tools/replay/replay 'a2a0ccea32023010|2023-07-27--13-01-19'
# or
tools/replay/replay --demo

# Run UI to visualize
cd selfdrive/ui && ./ui
```

### CI/CD
GitHub Actions runs comprehensive tests ([.github/workflows/selfdrive_tests.yaml](.github/workflows/selfdrive_tests.yaml)):
- Multi-architecture builds (x86_64, aarch64)
- pytest suite with hypothesis property testing
- pre-commit hooks (ruff, mypy, codespell)
- Docker-based testing environment
- Release build verification

## Code Conventions

### Python
- Type hints required (mypy enforced)
- ruff for linting/formatting
- Use numpy 2.0+ (recent migration)
- Prefer `openpilot.` prefix for imports from project root
- Services communicate via cereal messaging, not direct imports

### Message Passing
```python
from cereal import messaging

# Publishing
pm = messaging.PubMaster(['controlsState'])
msg = messaging.new_message('controlsState')
msg.controlsState.active = True
pm.send('controlsState', msg)

# Subscribing
sm = messaging.SubMaster(['carState'])
sm.update(timeout=100)
if sm.updated['carState']:
    speed = sm['carState'].vEgo
```

### Car Ports
When adding car support:
1. Capture CAN fingerprint with comma device
2. Implement CarInterface/CarState/CarController following existing patterns
3. Add to [selfdrive/car/values.py](selfdrive/car/values.py)
4. Create panda safety mode in C
5. Write safety tests in `panda/tests/safety/`
6. Document in [docs/CARS.md](docs/CARS.md)

### Testing Patterns
- Use `@pytest.mark.slow` for tests >5s
- Use `@pytest.mark.tici` for device-only tests
- hypothesis for property-based testing (seed 0 for reproducibility)
- Mock CAN with fake event handles: `messaging.fake_event_handle()`

## Important Files & Directories

- [pyproject.toml](pyproject.toml): Python dependencies and project metadata
- [cereal/log.capnp](cereal/log.capnp): All message type definitions (2400+ lines)
- [selfdrive/controls/](selfdrive/controls/): Control algorithms (lateral, longitudinal, radar fusion)
- [system/](system/): System-level daemons (cameras, logging, sensors)
- [tools/](tools/): Developer tools (replay, cabana, simulator, plotjuggler)
- [docs/](docs/): Contributor guides, safety documentation, integration details

## What Gets Merged

PRs must have clear purpose with every line contributing to that goal. Priorities: safety > stability > quality > features.

**Merged:**
- Bug fixes with clear before/after evidence
- Car ports with proper safety implementation
- Performance improvements with benchmarks
- Code cleanup removing unused code

**Not merged:**
- Style-only changes
- 500+ line PRs (break into smaller)
- New features (openpilot is considered feature-complete)
- UI design changes (no review process yet)

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

## Common Gotchas

1. **Services must be defined in cereal/services.py** - Add new message types there first
2. **Build after changing .capnp files** - `scons cereal/` regenerates Python bindings
3. **Panda safety changes require hardware testing** - Never merge without verification
4. **Use absolute imports** - `from openpilot.common.params import Params`, not relative
5. **Tests run with PYTHONWARNINGS=error** - All warnings are errors in CI
6. **SCons caching** - Delete `.sconsign.dblite` if builds act weird
7. **Multiprocessing** - Each process gets own params/messaging context, can't share directly
