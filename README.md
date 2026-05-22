# KommuAssist 2.0

KommuAssist 2.0 is an open source driver assistance system for the Malaysian market, running on the custom **KA2** device powered by **Rockchip RK3588** (aarch64).

KommuAssist provides Adaptive Cruise Control (ACC), Automated Lane Centering (ALC), Forward Collision Warning (FCW), and Lane Departure Warning (LDW) for supported vehicles available in Malaysia.

## Hardware

- **Device:** KommuAssist 2.0 (KA2)
- **SoC:** Rockchip RK3588 (ARM64)
- **NPU:** Rockchip NPU (RKNN for model inference)
- **Storage:** Micro SD card
- **Display:** Headless — no display output, monitoring via Bluetooth LE telemetry
- **CAN:** Internal panda hardware for OBD-II communication
- **Price:** RM4,999

## Supported Brands

byd, dnga (Perodua), honda, hyundai, mazda, nissan, proton, subaru, toyota, volkswagen

## Getting Started

See [KA2 Hardware Guide](docs/KA2_HARDWARE_GUIDE.md) for hardware specifications and setup.

## Developing

```bash
# Setup environment
source .venv/bin/activate
uv sync

# Build (KA2 target)
scons -j$(nproc)

# Run tests
pytest .

# Linting
ruff check .
mypy .
```

## Architecture

Microservices architecture communicating via ZMQ and Cap'n Proto (cereal messaging):
- **controlsd**: Main control loop at 100Hz
- **modeld**: Neural network inference via RKNN (Rockchip NPU)
- **boardd**: Interface to panda CAN hardware
- **camerad**: Camera capture and encoding
- **loggerd**: Route data logging to micro SD

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Safety

KommuAssist follows ISO26262 guidelines. The safety-critical code runs on the panda STM32 microcontroller, enforcing CAN message safety limits independently of the main application.

---

**THIS IS ALPHA QUALITY SOFTWARE FOR RESEARCH PURPOSES ONLY.
YOU ARE RESPONSIBLE FOR COMPLYING WITH LOCAL LAWS AND REGULATIONS.
NO WARRANTY EXPRESSED OR IMPLIED.**
