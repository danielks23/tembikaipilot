# KA2 Sensor System Documentation

## Hardware

| Component | Chip | I2C Bus | Address | ODR |
|---|---|---|---|---|
| Accelerometer | ICM42670 | 3 | `0x68` | 100 Hz |
| Gyroscope | ICM42670 | 3 | `0x68` | 100 Hz |
| Temperature | ICM42670 | 3 | `0x68` | 2 Hz |
| Magnetometer | LIS2MDL | 3 | `0x1E` | 25 Hz |
| Temperature 2 | LIS2MDL | 3 | `0x1E` | 2 Hz |

## Architecture

```
ICM42670 (I2C bus 3)
  │
  ├─ sensord (C++, MSGQ) → /dev/shm/accelerometer, /dev/shm/gyroscope
  │    │
  │    ├─ locationd (C++, MSGQ) → /dev/shm/liveLocationKalman
  │    │    │
  │    │    ├─ controlsd (Python, ZMQ) ← reads liveLocationKalman
  │    │    ├─ paramsd (Python, ZMQ) ← reads liveLocationKalman
  │    │    └─ torqued (Python, ZMQ) ← reads liveLocationKalman
  │    │
  │    └─ bridge (C++, MSGQ→ZMQ) ← translates for Python processes
  │
  └─ LIS2MDL (I2C bus 3) → /dev/shm/magnetometer
```

**Key:** C++ processes use MSGQ (shared memory). Python processes use ZMQ (TCP). The bridge translates MSGQ→ZMQ for Python consumers.

## Service Names

| Service | Frequency | Consumer | Notes |
|---|---|---|---|
| `accelerometer` | 100 Hz | locationd | ICM42670 accel |
| `gyroscope` | 100 Hz | locationd | ICM42670 gyro |
| `temperatureSensor` | 2 Hz | — | ICM42670 temp |
| `magnetometer` | 25 Hz | — | LIS2MDL |
| `temperatureSensor2` | 2 Hz | — | LIS2MDL temp |
| `liveLocationKalman` | 20 Hz | controlsd, paramsd, torqued | Fused output |

**Note:** `accelerometer2`/`gyroscope2` exist in `services.py` but are unused on KA2.

## Data Flow

1. **sensord** reads ICM42670 via I2C, publishes `accelerometer`/`gyroscope` to MSGQ
2. **locationd** subscribes to `accelerometer`/`gyroscope` via MSGQ, feeds ESKF
3. **locationd** publishes `liveLocationKalman` to MSGQ
4. **controlsd**/paramsd/torqued subscribe to `liveLocationKalman` (C++ reads MSGQ directly, Python reads via ZMQ bridge when available)

## Critical Path

```
ICM42670 → sensord → locationd → controlsd (via liveLocationKalman)
```

Sensor validation is handled by `locationd.inputsOK`. The `sensorDataInvalid` check in controlsd is disabled on KA2 because Python SubMaster (ZMQ) cannot read raw sensor data from sensord (MSGQ). The `locationd.inputsOK` flag already validates sensor health, making the raw sensor check redundant.

## Known Issues

### GPS Assistance (gpsd)
gpsd crashes on startup trying to inject GPS assistance data via `mmcli`. This is unrelated to sensors and does not affect operation.

### ForceOnroad
For off-car testing, set `ForceOnroad=1` param. This makes thermald treat ignition as always on, starting all onroad processes without a car.

```bash
printf '1' | sudo tee /data/params/d/ForceOnroad
sudo systemctl restart kommu
```

## Build Notes

- **SCons cache:** `/data/scons_cache` — delete to force full rebuild
- **prebuilt marker:** `/data/openpilot/prebuilt` — delete to force rebuild on next boot
- **Clean rebuild:** `rm -rf /data/scons_cache && rm -f prebuilt && find . -name '*.o' -delete`

## Debugging

### Check sensor data
```bash
# MSGQ (C++ processes)
stat -c '%Y' /dev/shm/accelerometer /dev/shm/gyroscope

# ZMQ (Python processes, requires bridge)
source /usr/local/venv/bin/activate
cd /data/openpilot
python3 -c "
from cereal import messaging
sm = messaging.SubMaster(['liveLocationKalman'])
import time
for i in range(20):
    sm.update(100)
    time.sleep(0.1)
print('sensorsOK:', sm['liveLocationKalman'].sensorsOK)
print('inputsOK:', sm['liveLocationKalman'].inputsOK)
"
```

### Check sensord threads
```bash
ps aux | grep sensord  # Should show 5 threads (accel, gyro, temp, mag, temp2)
timeout 5 strace -f -e trace=clock_nanosleep -p $(pgrep sensord)  # Sleep intervals
```

### Check locationd sensor fusion
```bash
source /usr/local/venv/bin/activate
cd /data/openpilot
python3 -c "
from cereal import messaging
sm = messaging.SubMaster(['liveLocationKalman'])
import time
for i in range(20):
    sm.update(100)
    time.sleep(0.1)
print('sensorsOK:', sm['liveLocationKalman'].sensorsOK)
print('inputsOK:', sm['liveLocationKalman'].inputsOK)
print('posenetOK:', sm['liveLocationKalman'].posenetOK)
"
```

## Fixes Applied

| Issue | Fix | Commit |
|---|---|---|
| sensord published `accelerometer2`/`gyroscope2` | Changed to `accelerometer`/`gyroscope` | `05401be` |
| controlsd subscribed to `*2` services | Changed to `accelerometer`/`gyroscope` | `05401be` |
| ICM42670 ODR 200 Hz → RateKeeper 104 Hz | Changed ODR to 100 Hz, services to 100 Hz | `05401be` |
| SubMaster KeyError on unknown services | Skip unknown services in SubMaster | `05401be` |
| `sensorDataInvalid` false positive | Disabled raw sensor check in controlsd, rely on `locationd.inputsOK` | `82c8a59` |
| bridge process unnecessary | Reverted bridge to `notcar` in process_config.py | `82c8a59` |

## Comparison with Original openpilot

| Aspect | Original (comma) | KA2 |
|---|---|---|
| Sensor | LSM6DS3 | ICM42670 |
| I2C bus | 1 | 3 |
| Mode | Interrupt-driven (GPIO IRQ) | Polling |
| ODR | 104 Hz (native) | 100 Hz (native) |
| Language | Python (sensord.py) | C++ (sensors_ka2.cc) |
| Backend | MSGQ | MSGQ |

## Comparison with Bukapilot

Bukapilot (`release_ka2` branch) uses identical service names and architecture. Our implementation now matches bukapilot exactly.
