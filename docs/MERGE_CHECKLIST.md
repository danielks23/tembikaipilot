# Upstream Merge Checklist

When merging upstream openpilot (or bukapilot) into this fork, certain files are
**not present in upstream** and will be deleted by a naïve merge/reset.
Verify each section below **before** committing the merge result.

---

## 1. `panda/certs/` — signing certificates (build-critical)

These files are required by `panda/SConscript` to compile panda firmware.
Upstream panda does not ship them; they live only in this fork.

| File | Purpose |
|------|---------|
| `panda/certs/debug` | RSA private key for debug builds |
| `panda/certs/debug.pub` | RSA public key (read by SConscript) |
| `panda/certs/release.pub` | RSA public key for release builds |

**After merge, verify:**
```bash
ls panda/certs/
# must show: debug  debug.pub  release.pub
```

---

## 2. `panda/crypto/` — firmware crypto library (build-critical)

Required by `panda/board/bootstub.c` (`#include "crypto/rsa.h"`).
Upstream panda does not include these files.

| File | Purpose |
|------|---------|
| `panda/crypto/rsa.h` | RSA header |
| `panda/crypto/rsa.c` | RSA implementation |
| `panda/crypto/sha.h` | SHA header |
| `panda/crypto/sha.c` | SHA implementation |
| `panda/crypto/hash-internal.h` | Internal hash helpers |
| `panda/crypto/sign.py` | Signing utility script |

**After merge, verify:**
```bash
ls panda/crypto/
# must show all 6 files above
```

---

## 3. `third_party/libyuv/*/lib/libyuv.a` — pre-built YUV libraries (build-critical)

Referenced by `SConstruct` for all build targets.
Upstream openpilot stores these for each architecture.

| File | Architecture |
|------|-------------|
| `third_party/libyuv/larch64/lib/libyuv.a` | device (ARM64 / KA2) |
| `third_party/libyuv/x86_64/lib/libyuv.a` | Linux dev machine |
| `third_party/libyuv/Darwin/lib/libyuv.a` | macOS dev machine |

**After merge, verify:**
```bash
ls third_party/libyuv/larch64/lib/   # libyuv.a  (~500 KB)
ls third_party/libyuv/x86_64/lib/    # libyuv.a  (~500 KB)
ls third_party/libyuv/Darwin/lib/    # libyuv.a  (~800 KB)
```

---

## 4. KA2-specific files (do not overwrite)

These files are this fork's additions and must **not** be overwritten by upstream content.

| File | Purpose |
|------|---------|
| `selfdrive/modeld/models/supercombo.rknn` | KA2 (Rockchip) supercombo model |
| `selfdrive/modeld/models/dmonitoring_model.rknn` | KA2 dmonitoring model |
| `selfdrive/modeld/models/navmodel.rknn` | KA2 nav model |
| `selfdrive/modeld/models/supercombo.thneed` | Thneed-compiled model |
| `system/camerad/cameras/camera_rk.cc/.h` | Rockchip ISP camera driver |
| `panda/certs/` | (see §1 above) |
| `panda/crypto/` | (see §2 above) |

Upstream uses `.onnx`/`.dlc` models and `camera_qcom2.cc` — **do not replace** the
KA2 equivalents with those.

---

## Recovery

If any of the above are lost, restore from the last good commit before the merge:

```bash
# Find the last good commit (before the merge)
git log --oneline --merges | head -5

# Restore a single file
git checkout <last-good-commit> -- panda/certs/debug.pub

# Restore an entire directory
git checkout <last-good-commit> -- panda/crypto/
git checkout <last-good-commit> -- third_party/libyuv/
```

---

## Quick post-merge validation

Run this after every merge to catch missing files early:

```bash
for f in \
  panda/certs/debug panda/certs/debug.pub panda/certs/release.pub \
  panda/crypto/rsa.h panda/crypto/rsa.c panda/crypto/sha.h panda/crypto/sha.c \
  panda/crypto/hash-internal.h \
  third_party/libyuv/larch64/lib/libyuv.a \
  third_party/libyuv/x86_64/lib/libyuv.a; do
  [ -f "$f" ] || echo "MISSING: $f"
done
echo "check complete"
```
