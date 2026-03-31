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
    ret.steerLimitTimer = 0.8               # time before steerLimitAlert is issued (0.8s avoids false alarms on sharp curves)
    ret.steerActuatorDelay = 0.10           # EPS mechanical+electrical delay ~100ms

    ret.lateralTuning.init('pid')

    ret.centerToFront = ret.wheelbase * 0.44
    ret.tireStiffnessFactor = 0.9871

    # Shared defaults for all BYD models
    ret.openpilotLongitudinalControl = True
    ret.lateralParams.torqueBP, ret.lateralParams.torqueV = [[0.], [530]]
    ret.lateralTuning.pid.kpBP = [0., 5., 20.]
    ret.lateralTuning.pid.kiBP = [0., 5., 20.]
    ret.longitudinalTuning.kpBP = [0., 5., 20.]
    ret.longitudinalTuning.kiBP = [0., 5., 20.]
    ret.longitudinalTuning.kpV = [0.8, 0.7, 0.6]
    ret.longitudinalTuning.kiV = [0.5, 0.4, 0.3]
    ret.lateralTuning.pid.kf = 0.00015
    ret.longitudinalActuatorDelayLowerBound = 0.1
    ret.longitudinalActuatorDelayUpperBound = 0.2
    ret.wheelSpeedFactor = 0.66

    # Car-specific parameters
    if candidate == CAR.ATTO3:
      # ========== BYD ATTO3 Configuration ==========
      ret.centerToFront = ret.wheelbase * 0.48  # EV: floor battery = near 50/50 weight dist
      ret.longitudinalActuatorDelayLowerBound = 0.08  # EV instant torque: faster than ICE
      ret.longitudinalActuatorDelayUpperBound = 0.16
      ret.wheelSpeedFactor = 0.660
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      ret.longitudinalTuning.kpV = [0.7, 0.6, 0.4]
      ret.longitudinalTuning.kiV = [0.10, 0.08, 0.05]  # EV: low ki reduces accel/brake hunting that wastes energy
      ret.longitudinalTuning.deadzoneBP = [0., 8.33, 16.67, 25.0]   # 0, 30, 60, 90 kph
      ret.longitudinalTuning.deadzoneV  = [0., 0.42,  0.83,  1.25]  # 5% of each speed
      ret.startingState = True
      ret.startAccel = 2.0
      ret.stoppingDecelRate = 0.6  # EV: 0.6 m/s²/s — firm enough for traffic lights, slower ramp = more regen time before friction brakes
      ret.minEnableSpeed = -1
      ret.enableBsm = True

    elif candidate == CAR.M6:
      # ========== BYD M6 Configuration ==========
      ret.wheelSpeedFactor = 0.695
      ret.safetyConfigs[0].safetyParam = 3
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      ret.longitudinalTuning.kpV = [1.2, 1.0, 0.8]
      ret.longitudinalTuning.kiV = [0.5, 0.4, 0.3]
      ret.longitudinalTuning.deadzoneBP = [0., 9.]
      ret.longitudinalTuning.deadzoneV = [0., 0.15]
      ret.startingState = True
      ret.startAccel = 3.0
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
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]

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

