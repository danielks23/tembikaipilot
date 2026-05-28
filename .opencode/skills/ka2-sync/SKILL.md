---
name: ka2-sync
description: Apply code changes to both the local repo and the KA2 device via SSH. Use when editing any file that exists on the KA2 at /data/openpilot/. ALWAYS apply the same edit locally AND on KA2 to keep them in sync. Trigger on any file edit under selfdrive/, cereal/, system/, common/, panda/, or tools/ that the KA2 would use.
---

# KA2 Sync

When editing a file that the KA2 device runs, apply the change to **both** locations:

1. **Local repo** — use the `edit` tool on the file in the workspace
2. **KA2 device** — use SSH to apply the same change at `/data/openpilot/`

## SSH Details

| Field | Value |
|-------|-------|
| Host alias | `Kommu` |
| IP address | `192.168.1.193` |
| User | `kommu` |
| SSH key | `~/.ssh/kommu_ed25519` |

## Workflow

### Adding an import line

```powershell
# Local: use edit tool
# KA2: use sed to insert after line N
ssh Kommu "sed -i 'Na/import os/' /data/openpilot/path/to/file.py"
```

### Replacing a string

```powershell
# Local: use edit tool
# KA2: use sed in-place
ssh Kommu "sed -i 's/old_string/new_string/g' /data/openpilot/path/to/file.py"
```

### Removing a line

```powershell
# Local: use edit tool
# KA2: use sed delete pattern
ssh Kommu "sed -i '/pattern_to_match/d' /data/openpilot/path/to/file.py"
```

### Renumbering enum ordinals (multi-line)

```powershell
ssh Kommu "sed -i 's/    old @6;/    old @4;/' /data/openpilot/cereal/log.capnp && sed -i 's/    next @7;/    next @5;/' /data/openpilot/cereal/log.capnp"
```

### Copying entire updated file (last resort)

If the edit is complex and sed is impractical, copy the local file to KA2:

```powershell
scp "path/to/local/file.py" Kommu:/data/openpilot/path/to/file.py
```

## Rules

1. **KA2 must always be on the same commit as local repo** — use `ka2-deploy` skill to sync
2. **Always edit local first**, then apply to KA2 — never skip either side
3. **Verify both sides** after editing with `grep` or `head`
4. **Path mapping**: local `selfdrive/manager/process_config.py` → KA2 `/data/openpilot/selfdrive/manager/process_config.py`
5. **Python cache**: After `.py` edits on KA2, remove stale cache:
   ```powershell
   ssh Kommu "find /data/openpilot -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null"
   ```
6. **Test connectivity** if SSH fails: `ssh -o ConnectTimeout=10 Kommu "echo OK"`

## Files KA2 uses (common edit targets)

- `selfdrive/manager/` — manager, process config
- `cereal/log.capnp` — Cap'n Proto schemas
- `system/hardware/ka2/` — KA2 hardware abstraction
- `selfdrive/car/` — car interfaces
- `common/` — shared utilities
- `selfdrive/controls/` — control loop

## Files KA2 does NOT use (skip SSH sync)

- `selfdrive/ui/` — headless, no display
- `tools/bodyteleop/` — removed for KA2
- `system/hardware/tici/` — TICI hardware removed

## See Also

- **ka2-deploy** — git sync, hard reset, commit parity
- **ka2-ssh** — connection details, common commands
