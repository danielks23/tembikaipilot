#!/usr/bin/env python3
from cereal import car
from openpilot.selfdrive.car import get_safety_config
from openpilot.selfdrive.car.interfaces import CarInterfaceBase
from openpilot.selfdrive.car.byd.values import CAR, HUD_MULTIPLIER

EventName = car.CarEvent.EventName

class CarInterface(CarInterfaceBase):

  @staticmethod
  def _get_params(ret, candidate, fingerprint, car_fw, experimental_long, docs):
    ret.carName = "byd"

    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.byd)] # BYD safety model
    ret.safetyConfigs[0].safetyParam = 1    # Default safety param, can be overridden per model

    ret.steerControlType = car.CarParams.SteerControlType.angle # angle-based steering control
    ret.steerLimitTimer = 0.2               # time before steerLimitAlert is issued
    ret.steerActuatorDelay = 0.01           # Steering wheel actuator delay in seconds

    ret.lateralTuning.init('pid')

    ret.centerToFront = ret.wheelbase * 0.44
    ret.tireStiffnessFactor = 0.9871

    # Car-specific parameters
    if candidate == CAR.ATTO3:
      # ========== BYD ATTO3 Configuration ==========
      # Full openpilot control (steering + gas/brake)
      ret.openpilotLongitudinalControl = True

      # Wheel speed calibration factor (converts CAN wheel speed to actual speed)
      # Higher values = openpilot thinks car is going faster, will show lower speedometer reading
      # Lower values = openpilot thinks car is going slower, will show higher speedometer reading
      # Calibrated to match speedometer: ACC 80 km/h = Speedometer 80 km/h
      ret.wheelSpeedFactor = 0.660

      # --- Lateral Control (Steering) ---
      # Maximum steering torque limit
      ret.lateralParams.torqueBP, ret.lateralParams.torqueV = [[0.], [530]]

      # PID gains for steering control (angle-based steering)
      # kpBP/kiBP: Speed breakpoints [0 m/s, 5 m/s, 20 m/s] = [0, 18, 72 km/h]
      ret.lateralTuning.pid.kpBP = [0., 5., 20.]
      ret.lateralTuning.pid.kiBP = [0., 5., 20.]
      # kpV: Proportional gains - immediate steering response at each speed
      # Higher = more aggressive steering, lower = gentler steering
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      # kiV: Integral gains - corrects persistent steering errors
      # Higher = faster correction, lower = smoother but slower correction
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      # kf: Feedforward gain - predictive steering component
      ret.lateralTuning.pid.kf = 0.00015

      # --- Longitudinal Control (Speed/Acceleration) ---
      # Speed breakpoints for acceleration control [0, 18, 72 km/h]
      ret.longitudinalTuning.kpBP = [0., 5., 20.]
      ret.longitudinalTuning.kiBP = [0., 5., 20.]
      # kpV: Proportional gains - immediate throttle/brake response
      # [0.7, 0.6, 0.4] provides responsive acceleration without excessive jerk
      ret.longitudinalTuning.kpV = [0.7, 0.6, 0.4]
      # kiV: Integral gains - corrects sustained speed errors
      # Slightly higher to smooth response and prevent jerking
      # [0.25, 0.2, 0.12] prevents aggressive corrections while staying responsive
      ret.longitudinalTuning.kiV = [0.25, 0.2, 0.12]
      # Actuator delay: time between command and actual throttle/brake response
      ret.longitudinalActuatorDelayLowerBound = 0.2  # Best case (light throttle)
      ret.longitudinalActuatorDelayUpperBound = 0.3  # Worst case (heavy brake)

      # --- Starting/Stopping Behavior ---
      ret.startingState = True  # Enable special resume-from-stop logic
      # startAccel: Initial acceleration when resuming from stop (m/s²)
      # 1.8 m/s² = responsive launch that matches increased kpV tuning
      # Lower = smoother but slower, higher = quicker but jerkier
      ret.startAccel = 1.8
      # stoppingDecelRate: Final deceleration when approaching complete stop (m/s²)
      # 0.25 m/s² = gentle comfortable stop with no head-bob
      # Lower = smoother but longer, higher = quicker but firmer
      ret.stoppingDecelRate = 0.25
      # minEnableSpeed: Minimum speed to engage openpilot (-1 = no minimum, can engage at 0 km/h)
      ret.minEnableSpeed = -1
      # enableBsm: Use car's blind spot monitoring for lane change assists
      ret.enableBsm = True

    elif candidate == CAR.M6:
      # ========== BYD M6 Configuration ==========
      # Full openpilot control with more aggressive tuning for larger vehicle
      ret.openpilotLongitudinalControl = True
      ret.wheelSpeedFactor = 0.695
      # M6 uses different safety configuration
      ret.safetyConfigs[0].safetyParam = 3

      # --- Lateral Control (Steering) ---
      ret.lateralParams.torqueBP, ret.lateralParams.torqueV = [[0.], [530]]
      ret.lateralTuning.pid.kpBP = [0., 5., 20.]
      ret.lateralTuning.pid.kiBP = [0., 5., 20.]
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      ret.lateralTuning.pid.kf = 0.00015

      # --- Longitudinal Control (Speed/Acceleration) ---
      # More aggressive tuning for M6 (larger, heavier vehicle)
      ret.longitudinalTuning.kpBP = [0., 5., 20.]
      ret.longitudinalTuning.kiBP = [0., 5., 20.]
      # Higher gains [1.2, 1.0, 0.8] = more responsive speed control
      # More immediate throttle/brake response for better performance feel
      ret.longitudinalTuning.kpV = [1.2, 1.0, 0.8]
      ret.longitudinalTuning.kiV = [0.5, 0.4, 0.3]
      # Deadzone: ignore small speed errors to prevent jerkiness in traffic
      # Below 9 m/s (32 km/h), ignore errors up to 0.15 m/s (0.5 km/h)
      ret.longitudinalTuning.deadzoneBP = [0., 9.]
      ret.longitudinalTuning.deadzoneV = [0., 0.15]
      ret.longitudinalActuatorDelayLowerBound = 0.2
      ret.longitudinalActuatorDelayUpperBound = 0.3

      # --- Starting/Stopping Behavior ---
      ret.startingState = True
      # Higher startAccel (3 m/s²) for more responsive resume
      # Matches aggressive longitudinal tuning above
      ret.startAccel = 3.0
      # Firmer stops (0.3 m/s²) for more confident braking feel
      ret.stoppingDecelRate = 0.3
      ret.minEnableSpeed = -1
      ret.enableBsm = True

    elif candidate in (CAR.SEAL, CAR.SEALION7):
      # ========== BYD SEAL/SEALION7 Configuration ==========
      # Lane Keep Assist only - uses stock ACC for speed control
      ret.openpilotLongitudinalControl = False  # Stock ACC handles gas/brake
      ret.radarUnavailable = True  # No radar data available to openpilot
      ret.wheelSpeedFactor = 0.695
      ret.safetyConfigs[0].safetyParam = 2

      # --- Lateral Control (Steering Only) ---
      ret.lateralParams.torqueBP, ret.lateralParams.torqueV = [[0.], [530]]
      ret.lateralTuning.pid.kpBP = [0., 5., 20.]
      ret.lateralTuning.pid.kiBP = [0., 5., 20.]
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      ret.lateralTuning.pid.kf = 0.00015

      # No longitudinal tuning parameters (stock ACC controls speed)
      # openpilot only provides steering assistance for lane centering
      ret.minEnableSpeed = -1
      ret.enableBsm = True

    else:
      # ========== Unknown BYD Model ==========
      # Dashcam mode only - no active control
      ret.dashcamOnly = True
      ret.safetyModel = car.CarParams.SafetyModel.noOutput

    return ret

  # returns a car.CarState
  def _update(self, c):
    ret = self.CS.update(self.cp, self.cp_cam)

    # events
    events = self.create_common_events(ret)
    ret.events = events.to_msg()

    return ret

  # pass in a car.CarControl to be called at 100hz
  def apply(self, c, now_nanos):
    return self.CC.update(c, self.CS, now_nanos)

