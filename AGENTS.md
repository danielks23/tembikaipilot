# AGENTS.md

This file provides guidance to AI coding assistants when working with code in this repository.

## Project Overview

**KommuAssist 2.0** — an adaptation of openpilot for the Malaysian market, running on custom **KA2 hardware** powered by **Rockchip RK3588** (aarch64).

**Key constraints:**
- **Headless target:** No display. All monitoring via Bluetooth LE telemetry (KommuAI app).
- **Storage:** Micro SD card (no NVMe).
- **Inference:** Rockchip NPU via RKNN (no Qualcomm SNPE/ION).
- **Single target:** KA2 only. TICI/TIZI/Qualcomm support removed.
- **Malaysia market:** Only car brands sold in Malaysia are retained.

## Build System

Uses **SCons**. Device detection via marker file: `/KA2` (KA2 hardware).

```bash
# Build everything (default: KA2 if /KA2 marker exists)
scons -j$(nproc)

# Minimal build (no tests/tools)
scons --minimal -j$(nproc)

# Build with address sanitizer
scons --asan -j$(nproc)

# Build with coverage instrumentation
scons --coverage -j$(nproc)

# Regenerate kaitai struct parsers
scons --kaitai

# Build specific component
scons -j8 selfdrive/ui/

# Build cereal (regenerates Python bindings from .capnp)
scons cereal/

# Generate clang compilation database
scons --compile_db
```

**Architecture targets:** `larch64` (KA2 ARM64), `x86_64` (Linux PC), `Darwin` (macOS). Detection at `SConstruct` lines 14-20.

## Python Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (pyproject.toml defines all deps)
uv sync
```

## Testing

```bash
# Run all tests
pytest .

# Run specific test directory
cd system/loggerd && pytest .

# Skip slow tests
pytest -m "not slow"

# Run only device-specific tests
pytest -m ka2

# Linting
ruff check .
mypy .
codespell

# Pre-commit hooks (ruff, mypy, codespell)
pre-commit run --all
```

Tests use `pytest` with `hypothesis` property-based testing (seed 0 for reproducibility). Test fixtures in `conftest.py` auto-setup `OpenpilotPrefix` for clean env per test.

## Architecture

### Process Architecture (microservices via ZMQ/cereal messaging)
- **manager** (`selfdrive/manager/manager.py`): Process supervisor
- **cereal** (`cereal/`): Cap'n Proto-based messaging system — all inter-process communication
- **services** (`cereal/services.py`): Message buses with frequencies and logging policies
- **controlsd** (`selfdrive/controls/`): Main control loop at 100Hz
- **plannerd** (`selfdrive/planner/`): Path planning and trajectory generation
- **radard** (`selfdrive/radar/`): Radar fusion and lead vehicle tracking
- **modeld** (`selfdrive/modeld/`): Neural network inference via RKNN (Rockchip NPU)
- **boardd** (`selfdrive/boardd/`): Interface to panda (CAN hardware)
- **locationd** (`selfdrive/locationd/`): Sensor fusion (GPS, IMU, wheel sensors)

### Car Interface Pattern (`selfdrive/car/<brand>/`)
Each supported car brand follows this structure:
- `interface.py`: Main CarInterface class
- `carstate.py`: Parses CAN messages into CarState
- `carcontroller.py`: Generates CAN commands
- `values.py`: Car-specific constants and limits
- `fingerprints.py`: CAN message patterns for car identification
- `radar_interface.py`: Optional radar data parsing

**Supported brands (Malaysia):** byd, dnga (Perodua), honda, hyundai, mazda, nissan, proton, subaru, toyota, volkswagen, mock (testing).

### Safety Model (`panda/`)
Panda firmware enforces safety guarantees on STM32 microcontrollers. Safety modes prevent unsafe CAN messages. `controls_allowed` state gates critical commands.

### Data Serialization
- All messages use Cap'n Proto schemas in `cereal/log.capnp` (2400+ lines)
- Service definitions map message types to ports and frequencies
- Custom fork extensions in `cereal/custom.capnp`

### KA2 Hardware Abstraction (`system/hardware/ka2/`)
- `hardware.py`: Main KA2 hardware class (extends `system/hardware/base.py`)
- `esim.py`: Cellular/eSIM management
- `casync.py`: OTA update handling
- `amplifier.py`: Audio amplifier control
- `pins.py`: GPIO pin definitions
- `power_monitor.py`: Power monitoring
- `agnos.py`: AGNOS OS updater (downloads, verifies, and flashes OTA updates via casync)
- `status_led/`: LED status indicators
- `iwlist.py`: WiFi management

### UI (`selfdrive/ui/qt/`)
Qt5-based Qt/C++ UI. Main files: `onroad.cc/h` (driving view), `offroad/` (off-road screens), `home.cc/h` (home screen), `sidebar.cc/h` (sidebar), `window.cc/h` (main window). **Not used on KA2** — headless target. Display power/brightness calls are no-ops.

### Key Directories
- `cereal/`: Cap'n Proto schemas and messaging
- `selfdrive/`: Core ADAS processes (controls, car interfaces, manager, modeld, boardd)
- `system/`: System daemons (camerad, loggerd, sensord, hardware abstraction)
- `system/hardware/ka2/`: **KA2-specific hardware abstraction**
- `opendbc/`: DBC files for CAN message parsing
- `panda/`: Panda board firmware (C, STM32)
- `tools/`: Developer tools (replay, cabana, simulator, plotjuggler)
- `third_party/`: External dependencies (acados, onnx runtime, Qt, etc.)
- `rednose/`: Kalman filter library (Cython)

## Code Conventions

### Python
- Type hints required (mypy enforced)
- ruff for linting (`line-length=160`, 2-space indent)
- numpy 2.0+ syntax
- Use `openpilot.` prefix for imports (e.g., `from openpilot.common.params import Params`)
- Services communicate via cereal messaging, not direct imports

### Messaging Pattern
```python
from cereal import messaging

# Publishing
pm = messaging.PubMaster(['controlsState'])
msg = messaging.new_message('controlsState')
pm.send('controlsState', msg)

# Subscribing
sm = messaging.SubMaster(['carState'])
sm.update(timeout=100)
if sm.updated['carState']:
    speed = sm['carState'].vEgo
```

### Testing
- Use `@pytest.mark.slow` for tests >5s
- Use `@pytest.mark.ka2` for device-only tests
- hypothesis for property-based testing
- Mock CAN with `messaging.fake_event_handle()`

### Car Ports
When adding car support:
1. Capture CAN fingerprint with comma device
2. Implement CarInterface/CarState/CarController following existing patterns
3. Add to `selfdrive/car/values.py`
4. Create panda safety mode in C
5. Write safety tests in `panda/tests/safety/`
6. Document in `docs/04-reference/Supported-Cars.md`

## Prebuilt Marker

The `prebuilt` file (empty, in `.gitignore`) is a build-status marker:

- **CI builds** (`.github/workflows/prebuilt.yaml`) create a Docker image with everything pre-built, placing a `prebuilt` marker file in the image.
- **On-device** (`launch_chffrplus.sh:81`): If `prebuilt` exists → skip `build.py`, launch manager directly. If missing → run `build.py` first.
- **Version info** (`system/version.py:83-84`): `is_prebuilt()` checks for the file to report whether the system is running from a prebuilt image or building from source.

## Important Gotchas

1. **Services must be defined in `cereal/services.py`** first before using new message types
2. **Build after changing `.capnp` files**: `scons cereal/` regenerates Python bindings
3. **Panda safety changes require hardware testing** — never merge without verification
4. **Use absolute imports**: `from openpilot.common.params import Params`, not relative
5. **Tests run with `PYTHONWARNINGS=error`** — all warnings are errors in CI
6. **SCons caching**: Delete `.sconsign.dblite` if builds act weird
7. **Multiprocessing**: Each process gets own params/messaging context, can't share directly
8. **KA2 is headless**: No display. `set_display_power()` and `set_brightness()` are no-ops in `HardwareNone` base class.
9. **KA2 uses micro SD**: No NVMe. Storage mount point is `/data/media`.
10. **KA2 uses RKNN**: No Qualcomm SNPE, ION, or KGSL. Model inference via Rockchip NPU.
11. **KA2 CPU cores**: RK3588 has 8 cores (4x A55 [0-3] @ 1.8GHz, 4x A76 [4-7] @ 2.4GHz). Cores 5-7 are offlined by `rkaiq_3A_server` at ~25s boot and **re-offlined periodically** (~24 min after any restore). Bring back via `echo 1 > /sys/devices/system/cpu/cpu{5,6,7}/online`. See `docs/01-hardware/KA2-Hardware-Reference.md#cpu-core-offlining`.
12. **libyuv.a**: Not tracked in git (LFS deleted from server). Must be built locally on KA2 via `third_party/libyuv/build.sh` or copied manually.
13. **UI build skipped on KA2**: Headless target — only `_text` and `_spinner` are built. Main `ui` binary and translations are skipped for `larch64`.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:
- `selfdrive_tests.yaml`: Main test suite (pytest + hypothesis)
- `compile-openpilot`: Multi-architecture build verification
- `release.yaml`: Release build pipeline
- `tools_tests.yaml`: Tools-specific tests

## Removed Components (TICI/Qualcomm-specific)

These have been removed or disabled for KA2-only builds:
- Car brands: `body`, `chrysler`, `ford`, `gm`, `tesla`
- Qualcomm: `third_party/snpe/`, `sensors_qcom2.cc`, `msm_kgsl.h`, `thneed_qcom2.cc`
- NVMe: bootlog NVMe smart-log, reset NVMe wipe, thermald NVMe model check
- Display: sysfs backlight writes, display power toggles (no-ops on KA2)
- UI: main `ui` binary and translations skipped for `larch64` (headless). Only `_text` and `_spinner` built.
