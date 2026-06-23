import math
from cereal import car
from opendbc.can.packer import CANPacker
import cereal.messaging as messaging

from openpilot.selfdrive.car import apply_std_steer_angle_limits, AngleRateLimit
from openpilot.selfdrive.car.interfaces import CarControllerBase
from openpilot.selfdrive.car.byd.bydcan import create_can_steer_command, send_buttons, create_lkas_hud, create_accel_command, create_steering_torque_spoof_camera
from openpilot.selfdrive.car.byd.values import DBC, CAR, ACCEL_MULT, CANBUS
from openpilot.common.numpy_fast import clip

GearShifter = car.CarState.GearShifter

STEER_LOWPASS_HZ = 3  # Reduced filter delay for better curve tracking
MIN_STEER_SPEED = 0.8  # m/s (~3 kph) — don't steer at near-standstill

def lowpass_1pole(x, y_prev):
    """
    x:       current (raw) steer angle prediction [deg]
    y_prev:  previous filtered angle [deg]
    0.02:      timestep 50hz [s]
    STEER_LOWPASS_HZ: filter cutoff frequency [Hz] (lower = smoother)
    """
    if y_prev is None:
        return x
    alpha = math.exp(-2.0 * math.pi * STEER_LOWPASS_HZ * 0.02)
    return alpha * y_prev + (1.0 - alpha) * x


class CarControllerParams():
  ANGLE_RATE_LIMIT_UP = AngleRateLimit(speed_bp=[0., 5., 15.], angle_v=[6., 3., 1.])
  ANGLE_RATE_LIMIT_DOWN = AngleRateLimit(speed_bp=[0., 5., 15.], angle_v=[8., 7., 4.])

  def __init__(self, CP):
    pass

class CarController(CarControllerBase):
  def __init__(self, dbc_name, CP, VM):
    self.CP = CP
    self.frame = 0
    self.packer = CANPacker(DBC[CP.carFingerprint]['pt'])
    self.sm = messaging.SubMaster(['radarState'])

    self.lka_active = False
    self.last_apply_angle = 0
    self.accel_mult = ACCEL_MULT[CP.carFingerprint]
    self.lka_cooldown = 0
    self.prev_press = False
    self.lka_latched = False
    self.steering_override_frames = 0
    self.accel_request_frames = 0

    # Lead tracking for gap-aware resume
    self.lead_distance = 0.0
    self.standstill_start_distance = 0.0

    # Adaptive tuning: oscillation detection
    self.angle_history = []
    self.oscillation_detected = False
    self.rate_multiplier = 1.0

    # Per-model steering rate limits (degrees/sec)
    self.rate_limits = {
      CAR.ATTO3: {'up_low': 3, 'down_low': 7, 'up_mid': 2.5, 'down_mid': 7, 'up_high': 2.5, 'down_high': 4.5},
      CAR.SEAL: {'up_low': 6, 'down_low': 8, 'up_mid': 3, 'down_mid': 7, 'up_high': 1, 'down_high': 4},
      CAR.SEALION7: {'up_low': 6, 'down_low': 8, 'up_mid': 3, 'down_mid': 7, 'up_high': 1, 'down_high': 4},
      CAR.M6: {'up_low': 5, 'down_low': 7, 'up_mid': 2.5, 'down_mid': 6, 'up_high': 0.8, 'down_high': 3.5},
    }

    limits = self.rate_limits.get(CP.carFingerprint, self.rate_limits[CAR.ATTO3])

    self.params = type('Params', (), {
      'ANGLE_RATE_LIMIT_UP': AngleRateLimit(
        speed_bp=[0., 1.4, 4.2],
        angle_v=[limits['up_low'], limits['up_mid'], limits['up_high']]
      ),
      'ANGLE_RATE_LIMIT_DOWN': AngleRateLimit(
        speed_bp=[0., 1.4, 4.2],
        angle_v=[limits['down_low'], limits['down_mid'], limits['down_high']]
      )
    })()

    self.button_send_bus = CANBUS.cam_bus if (CP.carFingerprint in (CAR.ATTO3, CAR.M6)) else CANBUS.main_bus

  def update(self, CC, CS, now_nanos):
    can_sends = []

    self.sm.update(0)

    enabled = CC.latActive
    actuators = CC.actuators
    apply_angle = CS.out.steeringAngleDeg
    pcm_cancel_cmd = CC.cruiseControl.cancel

    if self.CP.carFingerprint in (CAR.M6, CAR.SEAL, CAR.SEALION7):
      rising_edge = CS.lkas_rdy_btn and not self.prev_press
      if rising_edge:
        if not self.lka_latched:
          # First rising edge: latch it
          self.lka_latched = True
        else:
          # Second rising edge: unlatch it
          self.lka_latched = False
          self.lka_cooldown = 0
          self.lka_active = False
      self.prev_press = CS.lkas_rdy_btn

      # Comprehensive safety unlatch conditions
      if CS.out.brakePressed:
        self.lka_latched = False
        self.lka_cooldown = 0
        self.lka_active = False
      elif CS.out.gearShifter not in (GearShifter.drive, GearShifter.low):
        self.lka_latched = False
        self.lka_cooldown = 0
        self.lka_active = False
        self.steering_override_frames = 0
      elif abs(CS.out.steeringTorque) > 50:
        self.steering_override_frames += 1
        if self.steering_override_frames > 50:
          self.lka_latched = False
          self.lka_cooldown = 0
          self.lka_active = False
          self.steering_override_frames = 0
      else:
        self.steering_override_frames = 0
        if self.lka_latched:
          self.lka_active = True
          self.lka_cooldown += 1
    else:
      # lkas user activation, cannot tie to lka_on state because it may deactivate itself
      if CS.lka_on:
        self.lka_cooldown += 1
        self.lka_active = True
      if not CS.lka_on and CS.lkas_rdy_btn:
        self.lka_active = False
        self.lka_cooldown = 0

    lat_active = (self.lka_cooldown > 30) and enabled and self.lka_active and CS.out.vEgo > MIN_STEER_SPEED and not CS.out.gasPressed

    if (self.frame % 2) == 0:
      if lat_active:
        # Adaptive oscillation detection
        self.angle_history.append(CS.out.steeringAngleDeg)
        if len(self.angle_history) > 10:
          self.angle_history.pop(0)

          direction_changes = 0
          for i in range(1, len(self.angle_history) - 1):
            prev_trend = self.angle_history[i] - self.angle_history[i-1]
            curr_trend = self.angle_history[i+1] - self.angle_history[i]
            if abs(prev_trend) > 0.2 and abs(curr_trend) > 0.2:
              if (prev_trend > 0 and curr_trend < 0) or (prev_trend < 0 and curr_trend > 0):
                direction_changes += 1

          if direction_changes >= 3 and CS.out.vEgo < 2.8:
            self.oscillation_detected = True
            self.rate_multiplier = max(0.5, self.rate_multiplier - 0.05)
          else:
            self.oscillation_detected = False
            self.rate_multiplier = min(1.0, self.rate_multiplier + 0.01)

        if self.rate_multiplier < 0.99:
          limits = self.rate_limits.get(self.CP.carFingerprint, self.rate_limits[CAR.ATTO3])
          self.params.ANGLE_RATE_LIMIT_UP = AngleRateLimit(
            speed_bp=[0., 1.4, 4.2],
            angle_v=[limits['up_low'] * self.rate_multiplier, limits['up_mid'] * self.rate_multiplier, limits['up_high']]
          )
          self.params.ANGLE_RATE_LIMIT_DOWN = AngleRateLimit(
            speed_bp=[0., 1.4, 4.2],
            angle_v=[limits['down_low'] * self.rate_multiplier, limits['down_mid'] * self.rate_multiplier, limits['down_high']]
          )

        apply_angle = lowpass_1pole(actuators.steeringAngleDeg, self.last_apply_angle)
        apply_angle = apply_std_steer_angle_limits(apply_angle, \
          CS.out.steeringAngleDeg, CS.out.vEgo, self.params)

        # assumption why eps fault:
        # 1. steer rate too high
        # 2. met with resistance while steering
        # 3. applied steer too far away from current steeringAngleDeg
        apply_angle = clip(apply_angle, CS.out.steeringAngleDeg - 10, CS.out.steeringAngleDeg + 10)

        # Low-speed angle limit
        if CS.out.vEgo < 1.4:
          apply_angle = clip(apply_angle, -30, 30)

        self.last_apply_angle = apply_angle
      can_sends.append(create_can_steer_command(self.packer, apply_angle, lat_active, CS.out.standstill, CS.lkas_healthy, CS.lkas_rdy_btn or CS.out.brakePressed))
      can_sends.append(create_lkas_hud(self.packer, lat_active, CS.lss_state, CS.lss_alert, CS.tsr, \
        CS.ahb, CS.passthrough, CS.HMA, CS.pt2, CS.pt3, CS.pt4, CS.pt5, CS.lka_on, self.CP.carFingerprint))

      if self.CP.openpilotLongitudinalControl:
        long_active = CC.enabled and not CS.out.gasPressed
        brake_hold = CS.out.standstill and actuators.accel < 0

        # Track lead data for gap-aware resume
        lead_data = self.sm['radarState'].leadOne
        lead_active = lead_data.status
        if lead_active:
          self.lead_distance = lead_data.dRel
          lead_vrel = lead_data.vRel
        else:
          self.lead_distance = 0.0
          lead_vrel = 0.0

        accel_cmd = actuators.accel

        # Smart standstill resume logic
        if CS.out.standstill and CS.out.vEgo < 0.1:
          if self.accel_request_frames == 0 and accel_cmd <= 0:
            self.standstill_start_distance = self.lead_distance if lead_active else 0.0

          if accel_cmd > 0.05:
            self.accel_request_frames += 1

            lead_moving = lead_active and lead_vrel > 0.5

            gap_growth = 0.0
            gap_grew = False
            if lead_active and self.standstill_start_distance > 0:
              gap_growth = self.lead_distance - self.standstill_start_distance
              gap_grew = gap_growth > 1.5

            if lead_moving or gap_grew or accel_cmd >= 0.3 or self.accel_request_frames >= 8:
              if gap_growth > 2.5 or lead_vrel > 1.5:
                accel_cmd = max(accel_cmd, min(accel_cmd + 0.4, 1.5))
              elif gap_growth > 1.5 or lead_vrel > 0.8:
                accel_cmd = max(accel_cmd, min(accel_cmd + 0.2, 1.2))
            else:
              accel_cmd = 0
          else:
            self.accel_request_frames = 0
            accel_cmd = min(accel_cmd, 0)
        else:
          self.accel_request_frames = 0
          self.standstill_start_distance = 0.0

        # EV efficiency coasting
        if self.CP.carFingerprint == CAR.ATTO3 and -0.15 < accel_cmd < 0:
          accel_cmd = 0.0

        can_sends.append(create_accel_command(self.packer, accel_cmd, long_active, self.accel_mult, brake_hold))
      else:
        if CS.out.genericToggle or (CS.out.standstill and CC.enabled and (self.frame % 100 == 0)):
          can_sends.append(send_buttons(self.packer, 1, 0, self.button_send_bus))

    # Spoof steering torque to simulate hands on wheel
    if self.CP.carFingerprint in (CAR.M6, CAR.SEAL):
      # Time-based spoof: trigger every 3 seconds, sustain for 1 second
      # At 50 Hz: 1 second = 50 frames, 3 seconds = 150 frames
      SPOOF_DURATION_FRAMES = 50   # 1 second at 50 Hz
      SPOOF_CYCLE_FRAMES = 150     # 3 seconds at 50 Hz

      # Calculate position in 3-second cycle (0-149)
      cycle_position = self.frame % SPOOF_CYCLE_FRAMES
      spoof_active = cycle_position < SPOOF_DURATION_FRAMES

      if (self.frame % 5) == 0:
        can_sends.append(create_steering_torque_spoof_camera(self.packer, lat_active, CS.out.steeringTorque, spoof_active))

    if pcm_cancel_cmd:
      can_sends.append(send_buttons(self.packer, 0, 1, self.button_send_bus))

    new_actuators = actuators.copy()
    new_actuators.steeringAngleDeg = apply_angle

    self.frame += 1
    return new_actuators, can_sends
