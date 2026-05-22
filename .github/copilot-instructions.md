# KommuAssist 2.0 — AI Coding Instructions

## Project Overview

**KommuAssist 2.0** — an adaptation of openpilot for the Malaysian market, running on custom **KA2 hardware** powered by **Rockchip RK3588** (aarch64).

The base project, [openpilot](https://github.com/commaai/openpilot), provides Adaptive Cruise Control (ACC), Automated Lane Centering (ALC), Forward Collision Warning (FCW), and Lane Departure Warning (LDW). This fork ports that ADAS functionality to the KA2 device for Malaysian vehicles.

### KA2 Hardware Specifics
- **SoC:** Rockchip RK3588 (ARM64)
- **NPU:** Rockchip NPU via RKNN for model inference (no Qualcomm SNPE)
- **Storage:** Micro SD card (no NVMe)
- **Display:** Headless — no display, monitoring via Bluetooth LE (KommuAI app)
- **Hardware abstraction:** [`system/hardware/ka2/`](system/hardware/ka2/)
- **CAN:** Internal panda hardware for OBD-II communication
- **Build target:** aarch64 only (KA2)

### Supported Brands (Malaysia)
byd, dnga (Perodua), honda, hyundai, mazda, nissan, proton, subaru, toyota, volkswagen

**Removed brands:** body, chrysler, ford, gm, tesla (not sold in Malaysia)

## Architecture & Key Components

### Process Architecture
Microservices communicating via ZMQ and cereal (Cap'n Proto) messaging:
- **manager**: Process supervisor ([selfdrive/manager/manager.py](selfdrive/manager/manager.py))
- **cereal**: Cap'n Proto messaging ([cereal/](cereal/))
- **services**: Message buses ([cereal/services.py](cereal/services.py))
- **controlsd**: Main control loop at 100Hz
- **plannerd**: Path planning and trajectory generation
- **radard**: Radar fusion and lead vehicle tracking
- **modeld**: Neural network inference via RKNN (Rockchip NPU)
- **boardd**: Interface to panda (CAN hardware)
- **locationd**: Sensor fusion (GPS, IMU, wheel sensors)

### Car Interface Pattern
Each supported car brand in [selfdrive/car/](selfdrive/car/):
- `interface.py`: Main CarInterface class
- `carstate.py`: Parses CAN messages into CarState
- `carcontroller.py`: Generates CAN commands
- `values.py`: Car-specific constants and limits
- `fingerprints.py`: CAN message patterns for car identification
- `radar_interface.py`: (optional) Radar data parsing

### Safety Model (panda)
The [panda firmware](panda/) enforces safety guarantees on STM32 microcontrollers:
- Safety modes prevent unsafe CAN messages
- `controls_allowed` state gates critical commands
- Tests in `panda/tests/safety/`

### Data Serialization
- Cap'n Proto schemas in [cereal/log.capnp](cereal/log.capnp) (2400+ lines)
- Custom fork extensions in [cereal/custom.capnp](cereal/custom.capnp)

## Build System

SCons-based. Targets KA2 (Rockchip RK3588, aarch64):

```bash
# Build everything (KA2 if /KA2 marker exists)
scons -j$(nproc)

# Minimal build (no tests/tools)
scons --minimal -j$(nproc)

# Address sanitizer
scons --asan -j$(nproc)

# Coverage instrumentation
scons --coverage -j$(nproc)

# Build cereal (regenerates Python bindings from .capnp)
scons cereal/
```

Platform detection at [SConstruct](SConstruct) — checks `/KA2` marker file.

## Development Workflow

### Setup
```bash
source .venv/bin/activate
uv sync
scons -j$(nproc)
```

### Testing
```bash
pytest .
pytest -m "not slow"    # Skip slow tests
pytest -m ka2           # Device-specific tests
ruff check .
mypy .
pre-commit run --all
```

### CI/CD
GitHub Actions ([.github/workflows/](.github/workflows/)):
- `selfdrive_tests.yaml`: pytest + hypothesis
- `compile-openpilot`: Multi-architecture build verification
- `release.yaml`: Release pipeline

## Code Conventions

### Python
- Type hints required (mypy enforced)
- ruff linting (`line-length=160`, 2-space indent)
- numpy 2.0+ syntax
- Use `openpilot.` prefix for imports
- Services communicate via cereal messaging

### Messaging Pattern
```python
from cereal import messaging

pm = messaging.PubMaster(['controlsState'])
msg = messaging.new_message('controlsState')
pm.send('controlsState', msg)

sm = messaging.SubMaster(['carState'])
sm.update(timeout=100)
if sm.updated['carState']:
    speed = sm['carState'].vEgo
```

### Testing Patterns
- `@pytest.mark.slow` for tests >5s
- `@pytest.mark.ka2` for device-only tests
- hypothesis for property-based testing
- Mock CAN with `messaging.fake_event_handle()`

## Important Files & Directories

- [cereal/log.capnp](cereal/log.capnp): All message type definitions
- [selfdrive/controls/](selfdrive/controls/): Control algorithms
- [system/hardware/ka2/](system/hardware/ka2/): **KA2 hardware abstraction**
- [system/hardware/base.py](system/hardware/base.py): Hardware base class
- [panda/](panda/): Panda board firmware (C, STM32)
- [tools/](tools/): Developer tools

## Common Gotchas

1. **Services must be defined in cereal/services.py** first
2. **Build after changing .capnp files**: `scons cereal/` regenerates Python bindings
3. **Panda safety changes require hardware testing**
4. **Use absolute imports**: `from openpilot.common.params import Params`
5. **Tests run with PYTHONWARNINGS=error**
6. **SCons caching**: Delete `.sconsign.dblite` if builds act weird
7. **KA2 is headless**: `set_display_power()` and `set_brightness()` are no-ops
8. **KA2 uses micro SD**: No NVMe. Storage at `/data/media`.
9. **KA2 uses RKNN**: No Qualcomm SNPE, ION, or KGSL.
