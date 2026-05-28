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

# Check network
ssh Kommu "ip addr show && ping -c 3 8.8.8.8"

# Check NPU status
ssh Kommu "cat /sys/class/rk_npu/*/version"
```

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
