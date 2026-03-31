# KA2 Camera Offset Calibration Fix

## Problem
The KA2 device has a dual-camera setup where cameras are physically offset from the device center:
- **Telephoto camera** (right side, main model input) — 4cm **RIGHT** of device center
- **Wide-angle camera** (left side, extra model input) — 4cm **LEFT** of device center

Because the neural network outputs steering commands to center the **camera** in the lane (not the car center), a laterally offset camera creates a steady-state lane-following bias:
- Telephoto 4cm right → model centers camera → **car drives 4cm LEFT of lane center** ✓ (observed)
- Wide camera 4cm left → model centers camera → car drives 4cm right of lane center (wide-only mode)

## Why the Previous Fix Did Not Work

The original approach modified `RPY_INIT` and `WIDE_FROM_DEVICE_EULER_INIT` in `calibrationd.py`. This failed because:

1. **`WIDE_FROM_DEVICE_EULER_INIT` is ignored by `modeld.py`** — `modeld.py` uses only `liveCalibration.rpyCalib`, never `liveCalibration.wideFromDeviceEuler`, for warp matrix computation.
2. **`RPY_INIT` is overwritten by calibration** — it only seeds the value before calibration collects data. Once `CalibrationParams` has converged (after ~50 straight-road driving blocks), it is permanently replaced with the measured device mounting angle (~0°). If `CalibrationParams` was never deleted on-device, the previous fix had zero effect from day one.
3. **Magnitude was 20× too large** — 4cm lateral offset at 20m lookahead = `arctan(0.04/20) ≈ 0.002 rad`, not `0.04 rad (2.3°)`.

## Solution Applied (Current)

### Persistent warp correction in `modeld.py`
The correction is applied **after** reading `liveCalibration.rpyCalib`, directly to `device_from_calib_euler` before the warp matrices are computed. This is **permanent** — it cannot be calibrated or overridden away.

```python
# Physical offset is fixed hardware (4cm). Param stores the yaw correction directly in radians.
KA2_CAM_OFFSET_YAW_CONST = 0.002  # default: 0.04m / 20m = 0.002 rad

if use_extra_client:
    # Both cameras: telephoto=main (subtract yaw), wide=extra (add yaw)
    main_euler[2]  -= KA2_CAM_OFFSET_YAW_CONST
    extra_euler[2] += KA2_CAM_OFFSET_YAW_CONST
else:
    # Wide-only mode
    main_euler[2]  += KA2_CAM_OFFSET_YAW_CONST
```

**Effect**: Subtracting yaw from `device_from_calib_euler` for the telephoto shifts the warped image to the right in model input space. The model then perceives itself as slightly left of lane center and continuously applies a right-corrective curvature, keeping the car at true lane center.

### `calibrationd.py` — seed values corrected
- `RPY_INIT` reverted to `[0.0, 0.0, 0.0]` — the previous `-0.04` value was wrong layer, wrong magnitude
- `WIDE_FROM_DEVICE_EULER_INIT` kept at `[0.0, 0.0, 0.04]` — used as a seed for the wide camera odometry averaging buffer (harmless)

## Tuning

The physical 4cm camera offset is fixed hardware — it does not change. The only tunable value is the yaw correction in radians (`KA2CameraYaw` param, default `0.002`).

Tune on-device without reflashing:
```bash
# Still drifts left → increase
python -c "from openpilot.common.params import Params; Params().put('KA2CameraYaw', '0.003')"

# Overcorrects right → decrease
python -c "from openpilot.common.params import Params; Params().put('KA2CameraYaw', '0.001')"

pkill -f modeld   # restart to pick up new value
```

Typical tuning range: `0.001` – `0.005` rad. Each `0.001` increment shifts the car ~2 cm toward center at highway speed.

> **Note**: No need to delete `CalibrationParams` — this fix is independent of the calibration system.

## Files Modified
- `selfdrive/modeld/modeld.py`: KA2 persistent camera warp offset correction (the real fix)
- `selfdrive/locationd/calibrationd.py`: Reverted wrong `RPY_INIT`, kept `WIDE_FROM_DEVICE_EULER_INIT` seed


## Problem
The KA2 device has a dual-camera setup where the wide-angle camera is **physically positioned 4cm left of the device center** (device width: 12.5cm, cameras are 8cm apart), while openpilot's calibration system assumes all cameras are centered on the device.

This causes the car to drive **left of lane center** because the neural network receives images with an inherent left bias.

## Root Cause
1. **Hardware Layout**: KA2 has two road cameras:
   - Wide-angle camera (left side) - used for lane detection at low speeds
   - Telephoto camera (right side) - used at highway speeds
   - Both cameras are NOT centered on the device

2. **Software Assumption**: `calibrationd.py` initializes with:
   ```python
   WIDE_FROM_DEVICE_EULER_INIT = np.array([0.0, 0.0, 0.0])
   ```
   This assumes **zero yaw offset** (camera pointing straight ahead from device center)

3. **Missing Hardware Compensation**: The codebase has camera intrinsics for TICI/EON but no KA2-specific extrinsic calibration

## Solution Applied

### 1. Updated Default Camera Calibration
```python
# KA2: Device width 12.5cm, cameras 8cm apart (4cm each side of center)
# Wide-angle camera is 4cm left of device center, requires yaw compensation
WIDE_FROM_DEVICE_EULER_INIT = np.array([0.0, 0.0, 0.04])  # ~2.3° yaw offset for 4cm lateral offset
```

### 2. How It Works
The `wide_from_device_euler` parameter represents the rotation from device frame to camera frame as [roll, pitch, yaw]:
- **Roll**: Camera tilt (left/right)
- **Pitch**: Camera vertical angle
- **Yaw**: Camera horizontal angle

For KA2:
- **Yaw = +0.04 radians (~2.3°)** compensates for 4cm camera offset (left of center)
- This rotates the image coordinate system to the right
- Result: Lane detection sees centered lanes instead of left-biased lanes

## Tuning the Offset

The `0.04` value is based on **measured camera position** (4cm left of 12.5cm device center). To fine-tune:

1. **Drive on a straight, well-marked road** at 30-40 km/h
2. **Observe lane positioning** in UI
3. **Adjust the offset** if needed:
   - If car still pulls **left**: INCREASE value (e.g., 0.045, 0.05)
   - If car now pulls **right**: DECREASE value (e.g., 0.035, 0.03)
4. **Test range**: Try values between 0.03 - 0.05 radians (1.7-2.9 degrees)

## Alternative: Measure Exact Offset

For precise calibration:

1. **Physical measurements** (already done):
   ```
   device_width_cm = 12.5   # KA2 device width
   camera_spacing_cm = 8    # distance between camera centers
   camera_offset_cm = 4     # wide camera is 4cm left of device center
   yaw_offset = 0.04        # radians (~2.3°)
   ```

2. **Or use visual calibration**:
   - Record a drive on straight road
   - Analyze `liveCalibration.wideFromDeviceEuler[2]` values
   - Average converged yaw values = actual camera offset

## Files Modified
- `selfdrive/locationd/calibrationd.py`: Added KA2 hardware detection and camera offset constant

## Testing
After applying this fix:
1. Delete saved calibration: `rm /data/params/d/CalibrationParams`
2. Restart openpilot
3. Drive on straight road and observe lane centering
4. Monitor `/data/params/d/CalibrationParams` - should converge to offset near 0.035

## Expected Result
- Car maintains **lane center** instead of left bias
- `liveCalibration.wideFromDeviceEuler[2]` converges to ~0.04 ± 0.01
- Lane lines appear centered in UI visualization
