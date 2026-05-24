# KA2 Device Guide

Complete reference for the KA2 device — a Rockchip-based hardware platform running a fork of openpilot for ADAS functionality.

## Table of Contents

- [Overview](#overview)
- [Hardware Specifications](#hardware-specifications)
- [GPIO Pinout](#gpio-pinout)
- [Power Management](#power-management)
- [Network & Connectivity](#network--connectivity)
- [Cellular Modem](#cellular-modem)
- [eSIM Configuration](#esim-configuration)
- [WiFi](#wifi)
- [WiFi Hotspot](#wifi-hotspot)
- [Audio Subsystem](#audio-subsystem)
- [Status LEDs](#status-leds)
- [Cameras](#cameras)
- [Thermal Management](#thermal-management)
- [System Initialization](#system-initialization)
- [Boot & Updates](#boot--updates)
- [Remote Support](#remote-support)
- [SSH Access](#ssh-access)
- [Hostname](#hostname)
- [Log Management](#log-management)
- [Hardware Diagnostics](#hardware-diagnostics)
- [Storage & Partitioning](#storage--partitioning)
- [Troubleshooting](#troubleshooting)
- [File Reference](#file-reference)

---

## Overview

The KA2 device runs openpilot's ADAS features (ACC, ALC, FCW, LDW) on custom Rockchip SoC hardware. Unlike the upstream comma 3/3X devices, KA2 is:

- **Headless** — no display output
- **Rockchip SoC** — ARM64 architecture
- **Bluetooth LE telemetry** — data transmitted to phone app
- **RK-AGNOS** — comma's custom Linux (AGNOS) adapted for Rockchip, OTA update capable

**Source code:** `system/hardware/ka2/` and `/usr/kommu/`

---

## Hardware Specifications

| Component | Details |
|------|------|
| **SoC** | Rockchip RK3588 (ARM64/aarch64) |
| **NPU** | 1 GHz (configured via devfreq) |
| **DDR** | 2.112 GHz (configured via devfreq) |
| **OS** | RK-AGNOS |
| **Architecture** | aarch64 |
| **Device Type** | `cereal.log.DeviceType::KA2` |
| **Hardware Name** | "KommuAssist2" |
| **Product Name** | KommuAssist 2.0 |
| **Store** | [kommu.ai/store](https://kommu.ai/store) |
| **Cooling** | Passive (no fan) |
| **Cameras** | 3 (wide, narrow, driver-facing) |

### Accessories

Available from the Kommu store:
- Second Car Kit
- KA2 Mount
- ADAS Relay
- OBD Connector
- ADAS Connector
- USB-C 3.1 Cables (short/long)
- Nano SIM card
- Micro SD card

### NPU & DDR Configuration

Located in `hardware.py::initialize_hardware()`:

```bash
# NPU governor
echo userspace > /sys/class/devfreq/fdab0000.npu/governor
echo 1000000000 > /sys/class/devfreq/fdab0000.npu/userspace/set_freq

# DDR governor
echo userspace > /sys/class/devfreq/dmc/governor
echo 2112000000 > /sys/class/devfreq/dmc/userspace/set_freq
```

---

## GPIO Pinout

### Openpilot GPIO Definitions

Defined in `system/hardware/ka2/pins.py`:

```python
class GPIO:
    STM_RST_N   = 124   # STM32 reset (active-high — high = reset)
    STM_BOOT0   = 134   # STM32 BOOT0 (firmware recovery mode)
```

**Note:** `SOM_ST_IO` is pin 49 in `gpio.sh`, not pin 4. The `pins.py` definition may be outdated.

### Full Board Pinout (from `/usr/kommu/gpio.sh`)

| Pin | Name | Direction | Purpose |
|-----|-|------|------|
| 30 | HUB_RST_N | out | USB hub reset (set HIGH on boot) |
| 49 | SOM_ST_IO | — | GPIO4_B2_u / P26 (peripheral I/O) |
| 134 | STM_BOOT0 | — | STM32 BOOT0 (firmware recovery mode) |
| 41 | PANDA_1V8_EN_N | — | Panda 1.8V power enable (N = active-low) |
| 50 | LTE_RST_N | — | Cellular modem reset |
| 116 | LTE_PWRKEY | — | Cellular modem power key button |
| 124 | STM_RST_N | — | STM32 reset (active-high — high = reset) |
| 34 | GPS_PWR_EN | — | GPS module power enable |
| 33 | GPS_SAFEBOOT_N | — | GPS safeboot mode select |
| 32 | GPS_RST_N | — | GPS module reset |
| 52 | LTE_BOOT | — | LTE modem boot mode select |
| 1264 | POWER_ALERT | — | Power fault alert signal (eFUSE GPIO) |

### STM32 Recovery Procedure

1. Set `STM_BOOT0` (pin 134) HIGH for recovery mode
2. Toggle `STM_RST_N` (pin 124) to reset
3. STM32 boots into firmware update mode

*Note: The `STM_RST_N` name is misleading — it is active-high, not active-low.*

---

## Power Management

### Power Monitoring

Power sensor is on I2C bus 0, address `0-0040` (hwmon1):

```python
# Read current power (watts)
power = open("/sys/bus/i2c/devices/0-0040/hwmon/hwmon1/power1_input").read() / 1e6

# Sample power over N seconds
from openpilot.system.hardware.ka2.power_monitor import get_power
watts = get_power(seconds=5)

# Wait for power to enter a range (e.g., panda detection)
from openpilot.system.hardware.ka2.power_monitor import wait_for_power
wait_for_power(min_pwr=0.5, max_pwr=5.0, min_secs_in_range=2, timeout=10)
```

### Power Save Mode

Toggles between power saving and performance:

```python
from openpilot.system.hardware.ka2.hardware import Ka2

ka2 = Ka2()
ka2.set_power_save(True)   # Enable power save
ka2.set_power_save(False)  # Enable performance
```

**Implementation:**
- **Power Save:** Cores 5-8 offline, cores 0/4 use `ondemand` governor
- **Performance:** All cores online, cores 0/4 use `performance` governor
- Core 4 is reserved for `boardd` (never offlined)

### IRQ Affinity

Power save mode also adjusts IRQ affinity to concentrate interrupts on specific cores.

---

## Network & Connectivity

### Network Types

```python
from openpilot.system.hardware.ka2.hardware import Ka2

ka2 = Ka2()
net_type = ka2.get_network_type()  # 'ethernet' | 'wifi' | 'cell4G' | 'cell3G' | 'cell2G' | 'none'
net_strength = ka2.get_network_strength()  # 'poor' | 'moderate' | 'good' | 'great'
```

**Signal strength thresholds:** poor (<25%), moderate (<50%), good (<75%), great (>=75%)

### Ethernet

Ethernet connectivity is detected via NetworkManager. Network strength is reported via NM statistics.

---

## Cellular Modem

### Modem State Detection (Python API)

```python
from openpilot.system.hardware.ka2.hardware import Ka2

ka2 = Ka2()
modem = ka2.get_modem()  # Returns ModemManager DBus object

if modem:
    state = modem.Properties.Get("org.freedesktop.ModemManager1.Modem", "State")
    # States: FAILED(0), UNKNOWN(1), INITIALIZING(2), LOCKED(3),
    #          DISABLED(4), ENABLING(5), ENABLED(6), SEARCHING(7),
    #          REGISTERED(8), DISCONNECTING(9), CONNECTING(10), CONNECTED(11)
```

### Modem Initialization (Shell Script)

`/usr/kommu/lte/lte.sh`:

```bash
# Functions in lte.sh:
gpio $LTE_RST_N 1           # Reset modem (pin 50)
gpio $LTE_RST_N 0
gpio $LTE_PWRKEY 1          # Power button pulse (pin 116)
gpio $LTE_PWRKEY 0

# Modem detection via USB IDs
lsusb -d "0x05c6:"  # Qualcomm
lsusb -d "0x2c7c:"  # Quectel
```

### IMEI Generation

IMEI is derived from the wlan0 MAC address via SHA-256:

```python
imei = ka2.get_imei(slot=0)  # Returns 15-digit IMEI string
```

### Modem NV Items

```python
nv = ka2.get_modem_nv()
# Returns: mmode/ue_usage_setting, ims/IMS_enable, sms_only
```

### Modem Temperature

```python
temps = ka2.get_modem_temperatures()  # Returns list of ints (AT+QTEMP)
```

### Modem Data Usage

```python
usage = ka2.get_modem_data_usage()  # Returns TxBytes/RxBytes from NM
```

### Modem Restart

```bash
# Run the restart script
sudo bash /usr/kommu/lte/restart_modem.sh
```

Or manually:
```bash
sudo nmcli connection reload
sudo systemctl stop ModemManager
nmcli con down lte
nmcli con down blue-prime
sudo systemctl start ModemManager
sudo systemctl restart NetworkManager
```

---

## eSIM Configuration

### eSIM Hardware

- **Serial port:** `/dev/ttyUSB2` at 57600 baud
- **Interface:** GSMA LPA (Local Profile Assistant) via AT commands

### AT Commands

| Operation | AT Command |
|------|------|
| OTA download | `AT+QESIM="ota","{qr}"` |
| Profile download | `AT+QESIM="download","{qr}"` |
| Enable profile | `AT+QESIM="enable","{iccid}"` |
| Disable profile | `AT+QESIM="disable","{iccid}"` |
| Delete profile | `AT+QESIM="delete","{iccid}"` |
| List profiles | `AT+QESIM="list"` |

### eSIM Network Config

Located at `system/hardware/ka2/esim.nmconnection`:

```ini
[connection]
id=esim
type=gsm
autoconnect=true
autoconnect-retries=100
metered=1

[gsm]
apn=                    # empty = auto-detect by MCC/MNC
home-only=false
auto-config=true

[ipv4]
method=auto             # DHCP
route-metric=1000
dns-priority=1000

[ipv6]
method=auto
ddr-gen-mode=stable-privacy
route-metric=1000
dns-priority=1000
```

### WWAN Interface Setup

`/usr/kommu/lte/wwan0-setup.sh` — Uses carrier-provided APN from the mobile-broadband database:

```bash
# Usage: sudo bash /usr/kommu/lte/wwan0-setup.sh {MCCMNC}
# Example: sudo bash /usr/kommu/lte/wwan0-setup.sh 310410

# Steps:
# 1. Extract APN from /usr/share/mobile-broadband-provider-info/apns-conf.xml
# 2. Bring up wwan0 interface
# 3. Start network via qmicli with APN
# 4. DHCP via udhcpc

sudo ip link set wwan0 up
sudo qmicli -p -d /dev/cdc-wdm0 \
  --device-open-net='net-raw-ip|net-no-qos-header' \
  --wds-start-network="apn='$APN',ip-type=4"
sudo udhcpc -q -f -i wwan0
```

### APN Configuration (Manual Override)

```bash
sudo ip link set wwan0 up
sudo qmicli -d /dev/cdc-wdm0 --device-open-proxy \
  --wds-start-network="apn=your.apn,ip-type=4" --client-no-release-cid
sudo udhcpc -i wwan0
```

---

## WiFi

### WiFi Interface

WiFi interface: `wlan0`

NetworkManager manages WiFi connections. Scan available networks:

```python
from openpilot.system.hardware.ka2.iwlist import scan

networks = scan("wlan0")
for net in networks:
    print(f"MAC: {net['mac']}, Signal: {net['rss']} dBm")
```

---

## WiFi Hotspot

### Hotspot Setup

`/usr/kommu/hotspot-setup.sh` — Generates a unique SSID/password from device serial + IMEI:

```bash
# SSID: KommuAssist_{dongleid}
# Password: {dongleid}

# Derivation:
serial  = grep Serial /proc/cpuinfo | awk '{print $3}'
imei    = sha256(wlan0_mac_address)[:15]
dongleid = sha224(imei + serial)[:16]

# hostapd config:
interface=wlan1
ssid=KommuAssist_{dongleid}
hw_mode=g          # 2.4 GHz
channel=6
wpa=2              # WPA2-PSK
wpa_pairwise=CCMP
```

**Key detail:** Hotspot uses `wlan1` (not `wlan0`). `wlan0` is the cellular modem's network interface.

---

## Audio Subsystem

### Sound Initialization

`/usr/kommu/sound/sound_init.sh` boot sequence:

1. Starts Hexagon DSP via `adsp-start.sh`
2. Loads kernel modules: `snd-soc-wcd9xxx.ko`, `snd-soc-sdm845.ko`
3. Waits for sound card to come online
4. Configures audio routing via `tinymix`:
   - `SEC_MI2S_RX Audio Mixer MultiMedia1` → enabled
   - `MultiMedia1 Mixer TERT_MI2S_TX` → enabled
   - `TERT_MI2S_TX Channels` → Two
5. Runs `amplifier.py` to configure MAX98089 registers

| Component | Details |
|------|------|
| **DAC/AMP** | MAX98089 (I2C bus 0, addr 0x10) |
| **Channels** | 2 (stereo) |
| **DSP** | Hexagon ADSP (QDSP6) |

### Amplifier API

Defined in `system/hardware/ka2/amplifier.py`:

```python
from openpilot.system.hardware.ka2.amplifier import Amplifier

amp = Amplifier()

# Apply configuration
amp.initialize_configuration("ka2")

# Manual config
from openpilot.system.hardware.ka2.amplifier import AmpConfig
configs = [
    AmpConfig("MCLK prescaler", 0b01, 0x10, 0, 0b11),
    AmpConfig("Enable speakers", 0b11, 0x4D, 0, 0b11),
    # ... more register settings
]
amp.set_configs(configs)
```

### Key Register Settings

| Register | Parameter | Value | Purpose |
|------|------|------|--|
| 0x10 | MCLK prescaler | 0b01 | Clock setup |
| 0x4D | PM: enable speakers | 0b11 | Speaker power |
| 0x4D | PM: enable DACs | 0b11 | DAC power |
| 0x12 | Enable PLL1 | 0b1 | PLL enable |
| 0x1A | Enable PLL2 | 0b1 | PLL enable |
| 0x14 | DAI1: I2S mode | 0b00100 | Audio interface |
| 0x1C | DAI2: I2S mode | 0b00100 | Audio interface |
| 0x43 | ALC enable | 0b1 | Automatic level control |
| 0x51 | Global shutdown | 0b1/0b0 | Power state |

**Note:** Amplifier initialization retries 10 times with 20ms delay to handle panda I2C conflicts.

---

## Status LEDs

### LED Hardware

WS2812 addressable LEDs controlled via `/usr/kommu/ws2812.py`.

### LED Colors (BGR format)

| Color | BGR Hex |
|------|------|
| WHITE | FF0000 |
| RED | 0000FF |
| GREEN | 00FF00 |
| BLUE | FF0000 |
| CYAN | FF0088 |
| ORANGE | 00FF25 |
| YELLOW | 00DD88 |

### LED Control

```python
from openpilot.system.hardware.ka2.status_led import set_led

# Solid color
set_led("GREEN")

# Blinking
set_led("RED", mode="blink", rate="fast")

# With brightness
set_led("BLUE", mode="solid", brightness="50")

# Upload status (cluster B)
set_led("BLUE", mode="blink", cluster="B")

# Parameters
set_led(
    a_color="GREEN",
    b_color=None,        # Optional second color (cluster B)
    mode="solid",        # 'solid' | 'blink' | 'run'
    rate=None,           # 'fast' | 'slow' (for blink)
    duration=None,       # '600' default
    brightness="100",    # '0'..'100'
    fire_and_forget=True
)
```

### Alert LED Service

`alert_ledd.py` maps openpilot alerts to LED colors:

| Alert Type | Color | Mode |
|------|------|------|
| Immediate danger | RED | blink fast |
| Soft warning | ORANGE | blink fast |
| Normal (active) | GREEN | solid |
| No entry | ORANGE | solid |
| Malfunction/error | RED | solid |
| Calibration needed | ORANGE | solid |
| GPS fix | CYAN | solid |
| Inactive (openpilot off) | BLUE | solid |
| Not running (no heartbeat) | YELLOW | solid |

### Brightness Mapping

Brightness is auto-adjusted based on camera integration lines:
- `integ <= 100` → brightness 200 (max)
- `integ >= 892` → brightness 50 (min)
- Between: linear interpolation

### Upload Status

The LED service also shows upload status on a secondary cluster (cluster B):

| Upload State | Cluster B LED |
|------|------|
| Idle | OFF |
| Uploading | BLUE blink |
| Success | GREEN |
| Failed | RED blink |

Check upload status:
```python
# Via messaging
sm = messaging.SubMaster(['uploaderState'])
sm.update(timeout=100)
if sm.updated['uploaderState']:
    status = sm['uploaderState'].status  # 'idle' | 'uploading' | 'success' | 'failed'
```

---

## Cameras

KA2 has 3 cameras:

| Camera | FOV | Purpose |
|------|------|------|
| Wide | Wide-angle | Forward road view, lane detection, traffic signs, lead vehicles |
| Narrow | Narrow-angle | Extended forward view for distant objects |
| Driver | Interior-facing | Driver monitoring (alertness detection) |

Camera feeds are handled by the `camerad` process and published as:
- `roadCameraState` — wide camera
- `wideRoadCameraState` — narrow camera
- `driverCameraState` — driver camera

---

## Thermal Management

**Note:** KA2 is **passive cooled** (no fan). Thermal management is critical — sustained loads will cause thermal throttling. Monitor thermal zones during development.

### Thermal Zones

Configured via `ThermalConfig` in `hardware.py`:

| Component | Thermal Zones | Trip Point |
|------|------|------|
| CPU (big cores) | bigcore0-thermal, bigcore1-thermal | 100.0°C (1000 m°C) |
| GPU/NPU | gpu-thermal, npu-thermal | 100.0°C (1000 m°C) |
| Memory | center-thermal | 100.0°C (1000 m°C) |
| Battery | None | 1.0°C (native) |
| PMIC | soc-thermal, center-thermal | 100.0°C (1000 m°C) |

### NPU Usage

```python
usage = ka2.get_npu_usage_percent()  # Reads /sys/kernel/debug/rknpu/load
```

---

## System Initialization

### Boot Sequence (`/usr/kommu/kommu.sh`)

The `kommu.sh` daemon handles early boot:

1. Sources `/etc/profile`
2. Sets up `/data` ownership (`kommu:kommu`)
3. Creates `/data/tmp` and symlinks VS Code server directories
4. Sets up default SSH keys (from `/usr/kommu/setup_keys`)
5. Symlinks `installer.sh` to `/tmp/installer.sh`
6. Waits for `/data/continue.sh` (handoff to main system)

```bash
# Key paths
RESET="/usr/kommu/reset"
CONTINUE="/data/continue.sh"
INSTALLER="/tmp/installer.sh"
RESET_TRIGGER="/data/__system_reset__"
```

### Installer (`/usr/kommu/installer.sh`)

Main OTA installer logic, triggered via symlink at `/tmp/installer.sh`.

```bash
# Default settings
DEFAULT_GITHUB_OWNER="kommuai"
DEFAULT_GITHUB_BRANCH="release_ka2"

# Usage: installer.sh [owner] [branch]
# Clones to /data/openpilot, creates continue.sh, then reboots
```

### Filesystem Setup

`/usr/kommu/fs_setup.sh` provisions the filesystem layout:

| Mount/Path | Purpose |
|------|------|
| `/home` | Overlay mount (lower: `/usr/default/home`, upper: `/tmprw/home_upper`) |
| `/data/etc` | Config directory (timezone, localtime, NetworkManager) |
| `/data/media` | EMMC mount point |
| `/data/ssh` | SSH keys directory |
| `/data/tmp` | Temporary files (cleared on boot) |

`/usr/kommu/rename_labels.sh` manages A/B slot partition labels.

`/usr/kommu/safe_change_partlabel.sh` changes GPT partition labels with CRC32 repair.

### Library Shims

`/usr/kommu/shims/` — RK-specific library compatibility shims.

---

## Boot & Updates

### OTA Updates (AGNOS)

AGNOS is comma's custom Linux distribution that runs on their hardware devices. On KA2 it's called **RK-AGNOS** (Rockchip AGNOS). It provides the bootloader, partition management, cellular modem support, and OTA update infrastructure that openpilot runs on top of. The `/AGNOS` marker file on-device indicates the custom OS is present.

OTA updates use dual-slot (A/B) partitioning with sparse image format:

```bash
# Check current slot
cat /boot/abctl  # Returns "_a" or "_b"

# Slot suffix mapping
# Slot 0 → "" (slot A)
# Slot 1 → "_b" (slot B)
```

### Update Manifest

Located in `agnos.json`:

| Partition | Format | Size | Verification |
|------|------|------|--|
| rootfs | Sparse, XZ compressed | 8.18 GB | SHA-256 |
| boot | XZ compressed | 256 MB | SHA-256 |
| uboot | XZ compressed | 8 MB | SHA-256 |

### Differential Updates (casync)

CAIBX format for differential updates:

```python
# Chunk reader types
FileChunkReader    # Read from local file
RemoteChunkReader  # Download from {store_url}/{sha4}/{sha}.cacnk (LZMA)
```

### Device Reset

```python
# Soft reset via openpilot
ka2.uninstall()  # Touches __system_reset__, reboots

# Raw commands
sudo reboot
sudo poweroff
```

---

## Hardware Diagnostics

### Test Suite (`/usr/kommu/tests/`)

| Script | Purpose |
|------|------|
| `test_modem.py` | Full modem verification (manufacturer, model, revision, SIM, carrier) |
| `test_sounds.py` | Audio subsystem verification (journalctl output comparison) |
| `test_weston.py` | Display compositor verification (socket, service, UI launch) — may not apply to headless KA2 |
| `benchmark_weston.py` | Weston performance benchmark (socket creation time, UI/spinner launch times) — may not apply to headless KA2 |
| `analyze-boot-time.py` | Boot time analysis (XBL, ABL, kernel, systemd, weston timings) |
| `test_agnos.py` | AGNOS OS update verification (setup, reset, modem checks) |
| `watch-irqs.sh` | IRQ monitoring via `irqtop` |

### Test Modem (full modem verification)

```python
# test_modem.py checks:
# 1. Wait for modem to come up after flashing
# 2. Verify exactly 1 modem in ModemManager
# 3. Verify SIM present
# 4. Assert hardware identity:
#    - Manufacturer: QUALCOMM INCORPORATED
#    - Model: QUECTEL Mobile Broadband Module
#    - Revision: EG25GGBR07A08M2G
#    - Capabilities: gsm-umts, lte
#    - Carrier config: VoLTE-ATT or Commercial-TMO_VoLTE
#    - Operator: AT&T or T-Mobile
# 5. Results logged to /data/tmp/modem_log
```

### Benchmark Weston (performance)

```python
# benchmark_weston.py measures:
# 1. Wayland socket creation time (after weston restart)
# 2. /usr/kommu/setup launch time
# 3. ./spinner UI launch time
# Logs results to stdout
```

### Analyze Boot Time

```python
# analyze-boot-time.py tracks:
# - PON: Power-on to XBL (est. 1.5s)
# - XBL: eXtensible Boot Loader (2.4s)
# - ABL: Android Boot Loader (3.7s, includes fastboot wait)
# - kernel: Kernel boot time (from systemd-analyze)
# - weston: systemd to weston-ready (from journalctl)
# Output: tabulated boot time breakdown
```

---

## Storage & Partitioning

### Partition Management

| Script | Purpose |
|------|------|
| `/usr/kommu/rename_labels.sh` | Rename SD card partition labels |
| `/usr/kommu/safe_change_partlabel.sh` | Safe partition label changes |
| `/usr/kommu/crc32` | CRC32 checksum utility |

### Var Watch Daemon

`/usr/kommu/varwatch.py` — Variable change monitoring daemon.

### Device Formatting

```python
# Format internal storage
from openpilot.system.hardware.ka2.formatdevice import format_device
format_device("/dev/mmcblk1p1")  # umount + mkfs.ext4
```
Triggered when `pandaStates.ignitionLine=False`.

---

## Remote Support

KA2 supports remote debugging via SSH reverse tunnel.

### Tunnel Configuration

`/usr/kommu/support_tunnel.py`:

| Parameter | Value |
|------|------|
| **Server** | `x.kommu.ai` |
| **Port** | 6021 |
| **SSH User** | `tunneluser` |
| **SSH Key** | `/usr/kommu/id_ed25519` |
| **Local Port** | 22 |
| **Max Duration** | 24 hours |

### Connection Requirements

The tunnel requires either:
1. **WiFi** with IPv4 on `wlan0`, OR
2. **Cellular** with SIM present + IPv4 on `wwan0`

### Tunnel Behavior

- Generates random remote port (10000-60000)
- Prints only the port number on success
- Uses `ServerAliveInterval=30` and `ServerAliveCountMax=3` for keepalive
- Automatically terminates after 24 hours

---

## SSH Access

### SSH Control

`/usr/kommu/set_ssh.sh` — Enables/disables SSH based on params:

```bash
# SSH is enabled when /data/params/d/SshEnabled contains "1"
systemctl start ssh   # when enabled
systemctl stop ssh    # when disabled
```

### Setup Keys

During first boot, `kommu.sh` installs default SSH keys from `/usr/kommu/setup_keys` to `/data/params/d/GithubSshKeys` if no keys exist yet.

---

## Hostname

`/usr/kommu/set-hostname.sh` — Sets hostname from DongleId:

```bash
# If DongleId exists: kommu-{dongleid}
# If DongleId missing: kommu
sysctl kernel.hostname="$HOSTNAME"
```

---

## Log Management

`/usr/kommu/varwatch.py` — Prevents `/var/log` from filling up:

- Monitors disk usage every second
- When usage exceeds 70%, truncates all files in `/var/log`
- Last line of defense against log flooding

---

## Troubleshooting

### Common Issues

#### Modem Not Connecting

1. Check modem state:
   ```python
   from openpilot.system.hardware.ka2.hardware import Ka2
   ka2 = Ka2()
   modem = ka2.get_modem()
   # Check if modem is None (not found)
   ```

2. Check signal strength:
   ```python
   strength = ka2.get_network_strength()
   ```

3. Try restarting the modem:
   ```bash
   sudo bash /usr/kommu/lte/restart_modem.sh
   ```

---

## File Reference

| File | Purpose |
|------|------|
| `/usr/kommu/kommu.sh` | Main boot daemon / installer loop |
| `/usr/kommu/installer.sh` | OTA installer logic |
| `/usr/kommu/gpio.sh` | GPIO pin initialization (12 pins) |
| `/usr/kommu/hotspot-setup.sh` | WiFi hotspot with unique SSID/password |
| `/usr/kommu/lte/lte.sh` | Cellular modem power/reset control |
| `/usr/kommu/lte/wwan0-setup.sh` | WWAN interface + APN setup |
| `/usr/kommu/sound/sound_init.sh` | Audio subsystem initialization |
| `/usr/kommu/sound/adsp-start.sh` | Hexagon DSP boot sequence |
| `/usr/kommu/sound/amplifier.py` | MAX98089 register config |
| `/usr/kommu/ws2812.py` | WS2812 LED strip control |
| `/usr/kommu/support_tunnel.py` | SSH reverse tunnel for remote support |
| `/usr/kommu/set_ssh.sh` | SSH enable/disable via params |
| `/usr/kommu/set-hostname.sh` | Device hostname configuration |
| `/usr/kommu/varwatch.py` | Log cleanup daemon (truncates at 70% usage) |
| `/usr/kommu/fs_setup.sh` | Filesystem layout provisioning |
| `/usr/kommu/rename_labels.sh` | SD card partition label management |
| `/usr/kommu/safe_change_partlabel.sh` | Safe partition rename utility |
| `/usr/kommu/wait_for_file.sh` | File existence wait utility |
| `/usr/kommu/tmpfiles.conf` | systemd-tmpfiles config |
| `/usr/kommu/tests/` | Hardware test suite (7 scripts) |
| `/usr/kommu/apt_setup.sh` | APT package setup |
| `/usr/kommu/apt_teardown.sh` | APT cleanup |
| `/usr/kommu/reset` | Device reset trigger |

---

*Source: `/usr/kommu/` directory extracted from KA2 hardware and `system/hardware/ka2/` in the openpilot fork.*
