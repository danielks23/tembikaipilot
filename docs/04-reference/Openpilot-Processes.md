# Openpilot Process Reference (KA2)

All processes are managed by `selfdrive/manager/manager.py` via the registry in `selfdrive/manager/process_config.py`.

## Active Processes

### Vision & Perception

| Process | Type | When | Description |
|---|---|---|---|
| `camerad` | Native | driverview | Captures frames from road, driver, and wide cameras. Feeds raw images to modeld and encoderd. |
| `modeld` | Native | onroad | Main driving model inference via RKNN on Rockchip NPU. Outputs lane lines, path prediction, and lead vehicle detection. |
| `dmonitoringmodeld` | Python | driverview | Driver attention model inference. Detects face position, eye closure, and phone usage. |
| `sensord` | Native | onroad | Collects sensor data (accelerometer, gyroscope, magnetometer) from available hardware sensors. |

### Control & Planning

| Process | Type | When | Description |
|---|---|---|---|
| `controlsd` | Python | onroad | Main ADAS control loop at 100Hz. Computes steering angle, gas, and brake commands. |
| `plannerd` | Python | onroad | Trajectory planning using MPC (acados solver). Generates longitudinal and lateral plans from modeld output. |
| `radard` | Python | onroad | Radar fusion and lead vehicle tracking. Combines radar data with modeld predictions. |
| `locationd` | Native | onroad | Vehicle localization. Fuses GPS, IMU, and wheel speed into a Kalman filter for position and heading. |
| `calibrationd` | Python | onroad | Camera intrinsic calibration. Estimates camera-to-road geometry (ego2road transform). |
| `torqued` | Python | onroad | Steering torque estimation. Monitors driver torque input for hand-on-wheel detection. |
| `paramsd` | Python | onroad | Live vehicle parameter estimation. Learns mass, drag coefficient, steer ratio, and tire stiffness. |

### Driver Monitoring

| Process | Type | When | Description |
|---|---|---|---|
| `dmonitoringd` | Python | driverview | Driver monitoring daemon. Processes dmonitoringmodeld output to trigger alerts for inattention, drowsiness, and phone use. |

### Logging & Storage

| Process | Type | When | Description |
|---|---|---|---|
| `loggerd` | Native | logging | Route logger. Writes raw (rlog) and compressed (qlog) log files to disk. |
| `encoderd` | Native | onroad | Video encoder. Compresses camera footage to HEVC for storage. |
| `stream_encoderd` | Native | notCar | Streaming video encoder. Encodes camera feed for remote viewing via WebRTC. |
| `deleter` | Python | always | Deletes old route segments when disk space is low. |
| `logcatd` | Native | onroad | Captures system logcat output during driving for debugging. |
| `proclogd` | Native | onroad | Monitors CPU/memory usage per process. Publishes procLog messages. |
| `logmessaged` | Python | always | Routes log messages between services and writes to cloudlog. |

### Hardware Interface

| Process | Type | When | Description |
|---|---|---|---|
| `pandad` | Python | always | Panda CAN board communication. Sends/receives CAN messages over USB to the STM32 panda microcontroller. |
| `alert_ledd` | Python | always | KA2 status LED control. Drives GPIO-connected LEDs for alert indicators. |
| `setapnd` | Python | always | APN configuration for Quectel EC25-EM LTE modem. |
| `gpsd` | Python | onroad | GPS daemon for Quectel EC25-EM LTE modem (integrated GNSS). Reads raw GNSS measurements via the modem's diag protocol on `/dev/ttyUSB0` and publishes `gpsLocation`. |
| `streamdatad` | Python | always | Custom data streaming daemon for KommuAI app telemetry. |
| `sdformatterd` | Python | format_sd | Formats the MicroSD card when `FormatSDCard` param is set. |

### System Management

| Process | Type | When | Description |
|---|---|---|---|
| `thermald` | Python | always | Thermal management. Monitors CPU/GPU/NPU temperatures, manages power states, handles onroad/offroad transitions, and monitors battery power. |
| `tombstoned` | Python | always | Crash dump collection. Captures process tombstones for post-mortem analysis. |
| `updated` | Python | offroad | OTA update checker and downloader. Runs only when offroad. |
| `uploader` | Python | always | Uploads route logs to cloud storage. |
| `statsd` | Python | always | Metrics collection. Gathers and reports system statistics. |
| `timed` | Python | always | System time synchronization. |
| `micd` | Python | car | Driving style classification. Detects aggressive acceleration, braking, and cornering. |

### Audio

| Process | Type | When | Description |
|---|---|---|---|
| `soundd` | Python | onroad | Sound and alert playback. Plays chimes, warnings, and voice prompts. |

### Debug & Development

| Process | Type | When | Description |
|---|---|---|---|
| `bridge` | Native | notCar | Cereal message bridge. Exposes ZMQ messages for debugging tools. |
| `webrtcd` | Python | notCar | WebRTC streaming server for remote camera viewing. |
| `webjoystick` | Python | notCar | Web-based joystick teleoperation (body/robot testing only). |

### Navigation Model

| Process | Type | When | Description |
|---|---|---|---|
| `navmodeld` | Python | onroad | Navigation model inference. Processes map tile images for lane-level predictions. **Note: runs but navd/mapsd are disabled on KA2.** |

---

## Disabled Processes

These processes exist in the codebase but are **not running on KA2** due to hardware mismatch or missing dependencies.

| Process | Reason Disabled |
|---|---|
| `athenad` | Comma's cloud telemetry daemon. KA2 uses its own KommuAI app via Bluetooth LE instead of comma's cloud infrastructure. |
| `boardd` | Native panda USB interface daemon. KA2 has a built-in STM32H725 panda; the USB interface may be handled differently or not yet implemented. (`enabled=False` in process_config) |
| `mapsd` | Map tile downloading and management. Requires navigation display — KA2 is headless with no screen. |
| `navd` | Navigation daemon for routing and turn-by-turn directions. No display on KA2. |
| `ui` | Qt5-based on-screen UI (dashboard, onroad view, menus). KA2 is headless — no display attached. |
| `ubloxd` | U-blox GPS driver. Reads from `ttyHS0` UART on SDM845. KA2 has no U-blox GPS module. |
| `pigeond` | U-blox GPS daemon. Reads raw U-blox binary protocol from `/dev/ttyHS0`. KA2 has no U-blox GPS module — GPS comes from the EC25-EM modem via `gpsd`. |

---

## Process Conditions

Processes use boolean functions to determine when they should run:

| Condition | Meaning |
|---|---|
| `always_run` | Runs at all times (system daemons). |
| `only_onroad` | Runs only when the vehicle is onroad (ignition on + startup conditions met). |
| `only_offroad` | Runs only when offroad (e.g., `updated`). |
| `driverview` | Runs when onroad, driver view is enabled, or device is not fully booted. |
| `iscar` | Runs only when a car is connected (notCar = False). |
| `notcar` | Runs only in notCar/testing mode. |
| `logging` | Runs when onroad and logging is not disabled. |
| `format_sd` | Runs only when `FormatSDCard` param is True. |

---

## Source

Process registry: `selfdrive/manager/process_config.py` (lines 33-76)
Process manager: `selfdrive/manager/manager.py`
