# Log Uploader Authentication

## Overview

The KommuAssist log uploader (`system/loggerd/uploader.py`) uploads driving segments to `web.kommu.ai` using a two-phase authentication system:
1. **Kratos login** — authenticates device credentials to obtain a session token
2. **Bearer token** — attaches the session token to every API request

## Files Involved

| File | Role |
|------|------|
| `common/kommu.py` | Auth logic and API wrapper |
| `system/loggerd/kommu.py` | FIA upload functions |
| `system/loggerd/uploader.py` | Main uploader daemon |
| `system/hardware/ka2/hardware.py` | Hardware credential source |

## Authentication Credentials

The device authenticates using **hardware-derived credentials**:

| Field | Source | Example |
|-------|--------|---------|
| Username | `Params().get("DongleId")` | `0b4c08ef3e99cfb2` |
| Password | `HARDWARE.get_imei(1) + HARDWARE.get_serial()` | `650926c870301d481659a1925537199` |

### Password Composition

The password is a concatenation of two hardware-derived values:

```
Password = IMEI(15 chars) + Serial(variable)
```

**IMEI generation** (`system/hardware/ka2/hardware.py:217-222`):
```python
def get_imei(self, slot):
    mac = subprocess.getoutput("cat /sys/class/net/wlan0/address")
    clean_mac = mac.replace(':', '').replace('-', '')
    return hashlib.sha256(clean_mac.encode()).hexdigest()[:15]
```

**Serial generation** (`system/hardware/ka2/hardware.py:142-143`):
```python
def get_serial(self):
    return subprocess.check_output("grep 'Serial' /proc/cpuinfo | sed 's/.*: //'", shell=True, text=True).strip()
```

### Example

```
wlan0 MAC:      9c:b8:b4:60:70:e2
SHA256(clean):  650926c870301d4...
IMEI ([:15]):   650926c870301d4
CPU Serial:     81659a1925537199
Password:       650926c870301d481659a1925537199
```

## Authentication Flow

### Phase 1: Kratos Login (`common/kommu.py:13-29`)

```
Device                          web.kommu.ai
  |                                    |
  |  GET /self-service/login/api       |
  |---------------------------------->|
  |  200 OK + {ui: {action: URL}}      |
  |<-----------------------------------|
  |                                    |
  |  POST {action}                     |
  |  body: {method, password_identifier, password}
  |---------------------------------->|
  |  200 OK + {session_token}          |
  |<-----------------------------------|
  |                                    |
  |  params.put("RsjSession", token)   |
  |  (stored in D-Bus params)          |
  |                                    |
```

If the POST returns non-200, raises `AuthException("can't login into system")`.

### Phase 2: Bearer Token API Calls (`common/kommu.py:32-52`)

Every API call goes through the `kapi()` wrapper:

```python
def kapi(func, *args, **kwargs):
    resp = _kapi_raw(func, *args, **kwargs)
    if resp.status_code == 401:
        # Token expired — refresh once and retry
        refresh_session()
        return _kapi_raw(func, *args, **kwargs)
    return resp
```

The `_kapi_raw()` function injects the token:
```python
headers["Authorization"] = "Bearer " + params.get("RsjSession")
```

**Key behavior:** On 401, `kapi()` calls `refresh_session()` once and retries the same request with the new token. If the retry also fails, the exception propagates.

## Upload Flow

### Regular Upload (`system/loggerd/kommu.py:5-18`)

```
1. GET /fia/get_upload_url   → returns signed upload path
2. PUT /fia{signed_path}     → uploads file data
```

Both requests go through `kapi()`, so they carry the Bearer token and auto-refresh on 401.

### Upload Headers

```
X-Fia-Class: drive_log
X-Fia-Filename: {dongle_id}---{logdir}---{filename}
X-Fia-Tag: v0
Authorization: Bearer {session_token}
```

### Pending Full Upload Check (`system/loggerd/uploader.py:81-100`)

```python
resp = kapi(
    requests.get,
    WEB_BASE + "/fia/pending_full_uploads",
    headers={"X-Kaac-Id": dongle_id},
)
```

This endpoint returns a list of segment logdirs the server wants uploaded. If auth fails here, the exception is caught and logged, then returns `[]`.

## Session Token Storage

The session token is stored in D-Bus params as `RsjSession`. It persists across uploader restarts but not across reboots.

```python
# Storage
params.put("RsjSession", resp.json()["session_token"])

# Retrieval
auth = params.get("RsjSession", encoding="utf-8")
```

## Common Failure Modes

| Error | Cause | Fix |
|-------|-------|-----|
| `AuthException: can't login into system` | Credentials rejected by Kratos (400/401) | Re-register device on server |
| `can't init kratos login flow` | Server unreachable or Kratos down | Check network/server status |
| `keyError: 'session_token'` | Login succeeded but no token in response | Server-side bug |
| Silent failure in `get_pending_full_upload_segments` | Any exception caught at line 98 | Check cloudlog for details |

### Credential Mismatch

The most common failure is **credential mismatch**. This happens when:
- WiFi module was replaced → new MAC → new IMEI
- KA2 board was replaced → new CPU serial
- Device was re-provisioned with new DongleId

**Diagnosis:**
```bash
# Check DongleId
cat /data/params/d/DongleId

# Check IMEI source
cat /sys/class/net/wlan0/address
python3 -c "import hashlib; print(hashlib.sha256('9cb8b46070e2'.encode()).hexdigest()[:15])"

# Check Serial
grep 'Serial' /proc/cpuinfo | sed 's/.*: //'
```

**Fix:** Update the stored password on `web.kommu.ai` to match `IMEI + Serial`.

## Uploader Main Loop

```
while not exit_event:
    1. Check memory pressure → skip if critical
    2. Check network type → sleep if none
    3. uploader.step():
       a. Check pending full uploads (WiFi only)
       b. Upload next pending file
    4. Update queue stats
    5. Publish uploaderState
    6. Sleep with backoff
```

## Testing

```bash
# Fake upload mode (skips actual network calls)
FAKEUPLOAD=1 python3 system/loggerd/uploader.py

# Force WiFi network type
FORCEWIFI=1 python3 system/loggerd/uploader.py
```
