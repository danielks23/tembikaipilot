---
name: ka2-ssh
description: SSH into the KA2 device for remote command execution. Use when the user wants to check KA2 status, run commands, check logs, monitor processes, or access the headless device. SSH host alias is "Kommu" at 192.168.1.193.
---

# KA2 SSH Access

## Connection Details

| Field | Value |
|-------|-------|
| Host alias | `Kommu` |
| IP address | `192.168.1.193` |
| User | `kommu` |
| SSH key | `~/.ssh/kommu_ed25519` |
| Key type | ed25519 |

SSH config is in `~/.ssh/config` under the `Host Kommu` entry.

**Hostname fallback:** If the IP `192.168.1.193` doesn't work, try the hostname `kommu-0b4c08ef3e99cfb2`:
```powershell
ssh kommu@kommu-0b4c08ef3e99cfb2 "command here"
```
Note: Hostname resolution may not work on Windows without mDNS/LLMNR configured. IP is more reliable.

## Usage

Run non-interactive commands remotely:

```powershell
ssh Kommu "command here"
```

### Common commands

```powershell
# Check system status
ssh Kommu "uptime && free -h && df -h /data"

# Check running processes
ssh Kommu "ps aux"

# Check KA2 services
ssh Kommu "systemctl status"

# View recent logs
ssh Kommu "journalctl -n 50 --no-pager"

# Check if openpilot is running
ssh Kommu "ps aux | grep manager"

# Verify system is running — look for a process list line in tmux output containing:
# logmessaged, pandad, thermald, tombstoned, updated, uploader, statsd, streamdatad, etc.

# Check network
ssh Kommu "ip addr show && ping -c 3 8.8.8.8"

# Check NPU status
ssh Kommu "cat /sys/class/rk_npu/*/version"

# Capture full tmux scrollback history (from beginning)
ssh Kommu "tmux capture-pane -t 0 -S - -p"

# Check build progress (last 20 lines)
ssh Kommu "tmux capture-pane -t 0 -S - -p | tail -20"
```

## Restart Manager

The openpilot service on KA2 is `kommu` (not `chffrplus`):

```powershell
# Restart service
ssh Kommu "sudo systemctl restart kommu"

# Stop service
ssh Kommu "sudo systemctl stop kommu"

# Start service
ssh Kommu "sudo systemctl start kommu"

# Check status
ssh Kommu "sudo systemctl status kommu"
```

## System Power

```powershell
# Reboot KA2
ssh Kommu "sudo reboot"

# Shutdown KA2
ssh Kommu "sudo shutdown now"
```

## Storage

```powershell
# Check disk usage
ssh Kommu "df -h /data"

# Check SD card partitions
ssh Kommu "sudo lsblk"
```

**SD card layout (`/dev/mmcblk0`):**

| Partition | Mount | Purpose |
|-----------|-------|---------|
| `mmcblk0p12` | `/data` | openpilot + logs (8.4G) |
| `mmcblk0p11` | `/root-ro` | Root filesystem (10G) |
| `mmcblk0p10` | (unmounted) | Reserved (10G) |
| `mmcblk0p6` | `/cache` | Cache (64M) |
| `mmcblk0p7` | `/persist` | Persist (16M) |
| `mmcblk0p8` | `/boot` | Boot (256M) |

**Secondary storage (`/dev/mmcblk1`):**

| Partition | Mount | Purpose |
|-----------|-------|---------|
| `mmcblk1p1` | `/data/media` | User media (119G) |

**WARNING:** Never format `mmcblk0` partitions — it will brick the device. Always confirm with the user before any format operation.

## Limitations

- **No interactive TTY**: Tools like `tmux a`, `top`, `vim`, `nano` require an interactive terminal and will fail.
- **No real-time bidirectional I/O**: Commands run in a pipe, not a live session.
- **Long-running commands**: Use `timeout` or redirect output to a file, then cat it.

For interactive sessions, the user must run commands in their own terminal:
```powershell
ssh Kommu "tmux a"
ssh Kommu
```

## Troubleshooting

```powershell
# Test connectivity
ssh -o ConnectTimeout=10 Kommu "echo OK"

# Force key auth
ssh -i ~/.ssh/kommu_ed25519 -o IdentitiesOnly=yes kommu@192.168.1.193 "hostname"

# Check if SSH service is running on KA2
ssh -o ConnectTimeout=5 Kommu "exit" 2>&1
```

If connection fails, verify:
1. KA2 is powered on and on the same network
2. IP address hasn't changed (check router DHCP table)
3. SSH key exists at `~/.ssh/kommu_ed25519`
4. Try hostname fallback: `ssh kommu@kommu-0b4c08ef3e99cfb2 "echo OK"`

## See Also

- **ka2-debug-logs** for detailed log investigation (tmux scrollback, journalctl, dmesg, tmux file logs)
- **ka2-sync** for deploying local changes
- **ka2-deploy** for full git repo sync
