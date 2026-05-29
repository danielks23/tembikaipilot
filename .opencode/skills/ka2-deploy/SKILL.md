---
name: ka2-deploy
description: Sync the KA2 git repo to match the local repo's latest commit. Use when deploying changes to KA2, resetting KA2 repo, ensuring commit parity, or when the user says deploy, sync repo, reset KA2, pull changes, or git sync.
---

# KA2 Deploy

Keep KA2 `/data/openpilot/` on the same commit as the local repo.

## SSH Details

See **ka2-ssh** skill for connection details.

## Deploy to KA2

**Test first, commit later.** Sync changes to KA2, verify they work, then commit and git sync.

```powershell
# 1. Sync local changes to KA2 (see ka2-sync skill)
#    - scp changed files to /data/openpilot/
#    - clear __pycache__
#    - delete prebuilt marker
#    - restart kommu
#    - check errors via tmux capture-pane + journalctl

# 2. ONLY if no errors were found — commit locally and git sync
git add -A
git commit -m "describe changes"
git push
ssh Kommu "cd /data/openpilot && git pull && git checkout -- . && cd third_party/acados/larch64/lib && rm -f libqpOASES_e.so && cp libqpOASES_e.so.3.1 libqpOASES_e.so && cd /data/openpilot/third_party/maplibre-native-qt/larch64/lib && rm -f libQMapLibre.so && cp libQMapLibre.so.3.0.0 libQMapLibre.so"

# 3. Verify commits match
$local = git rev-parse --short HEAD
$remote = ssh Kommu "cd /data/openpilot && git rev-parse --short HEAD"
Write-Host "local=$local remote=$remote"
# If they do NOT match, the git pull on KA2 failed. Investigate or use Hard Reset.
```

**NEVER commit on KA2** — it has no SSH key for pushing, which causes merge conflicts.

## Hard Reset KA2

Force KA2 to match local HEAD exactly (destroys all local changes on KA2). Use only when KA2 is broken and needs recovery.

```powershell
# 1. Get local commit
$commit = git rev-parse HEAD

# 2. Stop manager (see ka2-ssh skill)
ssh Kommu "sudo systemctl stop kommu"

# 3. Reset to local commit + fix LFS symlinks
ssh Kommu "cd /data/openpilot && git fetch && git reset --hard $commit && git checkout -- . && cd third_party/acados/larch64/lib && rm -f libqpOASES_e.so && cp libqpOASES_e.so.3.1 libqpOASES_e.so && cd /data/openpilot/third_party/maplibre-native-qt/larch64/lib && rm -f libQMapLibre.so && cp libQMapLibre.so.3.0.0 libQMapLibre.so"

# 4. Delete prebuilt marker to force rebuild
ssh Kommu "rm -f /data/openpilot/prebuilt"

# 5. Verify
ssh Kommu "cd /data/openpilot && git status"

# 6. Restart manager (see ka2-ssh skill)
ssh Kommu "sudo systemctl start kommu"

# 7. Monitor build progress
#    Build takes several minutes. Periodically check:
ssh Kommu "tmux capture-pane -t 0 -S - -p | tail -20"
#    Look for "scons: done building targets." to confirm completion.
#    After build, kommu starts automatically. Verify processes are running:
#    Look for a process list line containing: logmessaged, pandad, thermald, tombstoned, updated, uploader, statsd, streamdatad, etc.
#    Also check journalctl for errors:
ssh Kommu "journalctl -u kommu --no-pager -n 30"
```

## Restart Manager

See **ka2-ssh** skill for restart commands.

## Critical Rule

**NEVER automatically commit, push, or deploy.** Always ask the user for explicit confirmation before:
- Running `git commit`
- Running `git push`
- Running `git pull` or `git reset` on KA2
- Stopping or restarting services on KA2

Show the user what will happen and wait for approval.

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