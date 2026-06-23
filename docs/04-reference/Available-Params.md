# Available Parameters

Parameters are stored in `/data/params/d/` and can be read/written via `Params()`.

## Process Control

| Param | Type | Default | Effect |
|---|---|---|---|
| `DisableUploader` | bool | `0` | Prevents `uploader` from running. Set to `1` to disable data uploads to the server. |
| `DisableUpdates` | bool | `0` | Prevents `updated` from running. Set to `1` to disable OTA updates. |
| `DisableLogging` | bool | `0` | Prevents `loggerd` from starting onroad. Set to `1` to disable driving data recording. |

## Camera & Driver Monitoring

| Param | Type | Default | Effect |
|---|---|---|---|
| `IsDriverViewEnabled` | bool | `0` | When `1`, enables driver-facing camera processes offroad (`camerad`, `dmonitoringmodeld`, `dmonitoringd`). |
| `DisableDriverMonitoring` | bool | `0` | When `1`, disables driver monitoring entirely. Stops `dmonitoringmodeld`, `dmonitoringd`, and disables the driver camera stream in `camerad`. AP engagement is **not blocked** — `controlsd` ignores `driverMonitoringState` when this param is set. |

## Development & Testing

| Param | Type | Default | Effect |
|---|---|---|---|
| `ForceOnroad` | bool | `0` | When `1`, thermald treats ignition as always on, starting all onroad processes without a car. Useful for headless testing. |

## Power & Shutdown

| Param | Type | Default | Effect |
|---|---|---|---|
| `DisablePowerDown` | bool | `0` | When `1`, prevents automatic power-down due to low battery. |
| `ForcePowerDown` | bool | `0` | When `1`, forces immediate power-down regardless of battery level. |
| `DoShutdown` | bool | `0` | When `1`, triggers system shutdown on next manager cycle. Automatically cleared after action. |
| `DoReboot` | bool | `0` | When `1`, triggers system reboot on next manager cycle. Automatically cleared after action. |
| `DoUninstall` | bool | `0` | When `1`, triggers device uninstall on next manager cycle. Automatically cleared after action. |

## Storage

| Param | Type | Default | Effect |
|---|---|---|---|
| `FormatSDCard` | bool | `0` | When `1`, triggers SD card formatting via `sdformatterd`. Automatically cleared after action. |
| `RecordFront` | bool | `0` | Enables front camera recording. |
| `RecordFrontLock` | bool | `0` | When `1`, forces `RecordFront` to always be enabled. |

## Tmux Logging

| Param | Type | Default | Effect |
|---|---|---|---|
| `TmuxLogsEnabled` | bool | `0` | When `1`, enables tmuxledd to persist tmux output to `/data/media/0/realdata/tmux/`. |
| `TmuxLogLevel` | string | `"all"` | `"all"` or `"errors"` — filters what tmuxledd logs. |

## Usage

### Python

```python
from openpilot.common.params import Params

params = Params()

# Read
val = params.get_bool("ForceOnroad")

# Write
params.put_bool("ForceOnroad", True)
params.put_bool("ForceOnroad", False)

# Remove (reset to default)
params.remove("ForceOnroad")
```

### SSH (KA2)

```bash
# Set to 1 (True)
echo -n '1' | sudo tee /data/params/d/ForceOnroad

# Set to 0 (False)
echo -n '0' | sudo tee /data/params/d/ForceOnroad

# Remove (reset to default)
sudo rm /data/params/d/ForceOnroad
```

### Common Combinations

**Disable all cloud features:**
```bash
echo -n '1' | sudo tee /data/params/d/DisableUploader
echo -n '1' | sudo tee /data/params/d/DisableUpdates
```

**Headless development (force onroad, no uploads):**
```bash
echo -n '1' | sudo tee /data/params/d/ForceOnroad
echo -n '1' | sudo tee /data/params/d/DisableUploader
sudo systemctl restart kommu
```

**Disable driver monitoring (headless operation):**
```bash
echo -n '1' | sudo tee /data/params/d/DisableDriverMonitoring
sudo systemctl restart kommu
```

**Clean up (reset to normal):**
```bash
rm /data/params/d/ForceOnroad /data/params/d/DisableUploader /data/params/d/DisableUpdates /data/params/d/DisableDriverMonitoring
sudo systemctl restart kommu
```

## Notes

- Boolean params are stored as `"1"` (True) or `"0"` (False)
- Some params are automatically cleared after their action completes (`DoShutdown`, `DoReboot`, `DoUninstall`, `FormatSDCard`)
- Changes to process control params (`DisableUploader`, `DisableUpdates`, `ForceOnroad`, `DisableDriverMonitoring`) require `sudo systemctl restart kommu` to take effect
- Process control params don't prevent the process from appearing in the manager — they cause the process to exit cleanly, showing it in **red** in the tmux process list
- `DisableUploader`, `DisableUpdates`, and `DisableDriverMonitoring` are handled in controlsd to not trigger `processNotRunning` blocking engagement
