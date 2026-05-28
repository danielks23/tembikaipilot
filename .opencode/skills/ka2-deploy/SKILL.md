---
name: ka2-deploy
description: Sync the KA2 git repo to match the local repo's latest commit. Use when deploying changes to KA2, resetting KA2 repo, ensuring commit parity, or when the user says deploy, sync repo, reset KA2, pull changes, or git sync.
---

# KA2 Deploy

Keep KA2 `/data/openpilot/` on the same commit as the local repo.

## SSH Details

| Field | Value |
|-------|-------|
| Host alias | `Kommu` |
| IP address | `192.168.1.193` |
| User | `kommu` |
| SSH key | `~/.ssh/kommu_ed25519` |

## Check Commit Parity

Before deploying, verify if commits match:

```powershell
$local = git rev-parse --short HEAD
$remote = ssh Kommu "cd /data/openpilot && git rev-parse --short HEAD"
if ($local -ne $remote) { Write-Host "MISMATCH: local=$local remote=$remote" } else { Write-Host "In sync: $local" }
```

## Deploy to KA2

**ALWAYS commit and push from local first, then pull on KA2.** Never commit on KA2 — it has no SSH key for pushing, which causes merge conflicts.

```powershell
# 1. Commit locally
git add -A
git commit -m "describe changes"

# 2. Push from local
git push

# 3. Pull on KA2 — NEVER use `git clean -fdx` (removes .sconsign.dblite which breaks scons deps)
# After pull, fix LFS symlinks that git checkout breaks:
ssh Kommu "cd /data/openpilot && git pull && git checkout -- . && cd third_party/acados/larch64/lib && rm -f libqpOASES_e.so && cp libqpOASES_e.so.3.1 libqpOASES_e.so && cd /data/openpilot/third_party/maplibre-native-qt/larch64/lib && rm -f libQMapLibre.so && cp libQMapLibre.so.3.0.0 libQMapLibre.so"

# 4. Verify commits match
$local = git rev-parse --short HEAD
$remote = ssh Kommu "cd /data/openpilot && git rev-parse --short HEAD"
Write-Host "local=$local remote=$remote"
```

## Hard Reset KA2

Force KA2 to match local HEAD exactly (destroys all local changes on KA2):

  ```powershell
   # Stop manager (service is "kommu", not "chffrplus")
   ssh Kommu "sudo systemctl stop kommu"

   # Reset to local commit
   $commit = git rev-parse HEAD
   ssh Kommu "cd /data/openpilot && git fetch && git reset --hard $commit && git checkout -- . && cd third_party/acados/larch64/lib && rm -f libqpOASES_e.so && cp libqpOASES_e.so.3.1 libqpOASES_e.so && cd /data/openpilot/third_party/maplibre-native-qt/larch64/lib && rm -f libQMapLibre.so && cp libQMapLibre.so.3.0.0 libQMapLibre.so"

   # Verify
   ssh Kommu "cd /data/openpilot && git status"

   # Restart manager
   ssh Kommu "sudo systemctl start kommu"
   ```

## When to use

- After committing changes locally that need to run on KA2
- KA2 repo has drifted from local (manual edits, stale files)
- Startup fails with stale bytecode or missing modules
- Before testing a new release

## Warnings

- **Stops all running processes** on KA2 during hard reset
- **Destroys all local changes** on KA2 (modified + untracked files)
- User data in `/data/media/` is unaffected
- Requires KA2 `/data/openpilot/` to be a valid git repo