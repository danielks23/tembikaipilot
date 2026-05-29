---
name: ka2-sync
description: Apply code changes to both the local repo and the KA2 device via SSH. Use when editing any file that exists on the KA2 at /data/openpilot/. ALWAYS apply the same edit locally AND on KA2 to keep them in sync. Trigger on any file edit under selfdrive/, cereal/, system/, common/, panda/, or tools/ that the KA2 would use.
---

# KA2 Sync

Syncs files edited locally during this session to the KA2 device at `/data/openpilot/`.

## Workflow

1. **Identify changed files** (e.g., `git status` or `git diff --name-only`)
2. **Copy to KA2** using `scp`:
   ```powershell
   scp "local/path/to/file.py" Kommu:/data/openpilot/local/path/to/file.py
   ```
3. **Clear Python cache** on KA2:
   ```powershell
   ssh Kommu "find /data/openpilot -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null"
   ```
4. **Delete prebuilt marker** to force rebuild:
   ```powershell
   ssh Kommu "rm -f /data/openpilot/prebuilt"
   ```
5. **Restart manager** (see ka2-ssh skill):
   ```powershell
   ssh Kommu "sudo systemctl restart kommu"
   ```
6. **Check for errors** (see ka2-ssh skill):
   ```powershell
   ssh Kommu "tmux capture-pane -t 0 -S - -p"
   ssh Kommu "journalctl -u kommu --no-pager -n 50"
   ```
   Look for tracebacks, crash loops, or failed processes.
   **System is running** if you see a process list line containing: `logmessaged, pandad, thermald, tombstoned, updated, uploader, statsd, streamdatad`, etc.

**If errors are found:** Report what went wrong and ask the user for next steps. Do NOT attempt to fix automatically.

## Rules

- Sync **all** files changed locally. No filtering or allowlists.
- Path mapping: local `selfdrive/manager/foo.py` -> KA2 `/data/openpilot/selfdrive/manager/foo.py`

## See Also

- **ka2-ssh** for connection details and restart commands
- **ka2-deploy** for full git repo sync (commits)
