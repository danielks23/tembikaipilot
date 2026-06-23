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

    ret.safetyConfigs = [get_safety_config(car.CarParams.SafetyModel.byd)]
    ret.safetyConfigs[0].safetyParam = 1

    ret.steerControlType = car.CarParams.SteerControlType.angle
    ret.steerLimitTimer = 0.8              # time before steerLimitAlert is issued (0.8s avoids false alarms on sharp curves)
    ret.steerActuatorDelay = 0.10          # EPS mechanical+electrical delay ~100ms

    ret.lateralTuning.init('pid')

    ret.centerToFront = ret.wheelbase * 0.44
    ret.tireStiffnessFactor = 0.9871

    ret.openpilotLongitudinalControl = True
    # TODO: angle based vehicle needs pid tuning?
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

    if candidate == CAR.ATTO3:
      ret.centerToFront = ret.wheelbase * 0.48  # EV: floor battery = near 50/50 weight dist
      ret.longitudinalActuatorDelayLowerBound = 0.08  # EV instant torque: faster than ICE
      ret.longitudinalActuatorDelayUpperBound = 0.16
      ret.wheelSpeedFactor = 0.660
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      ret.longitudinalTuning.kpV = [0.7, 0.6, 0.4]
      ret.longitudinalTuning.kiV = [0.10, 0.08, 0.05]  # EV: low ki reduces accel/brake hunting
      ret.longitudinalTuning.deadzoneBP = [0., 8.33, 16.67, 25.0]
      ret.longitudinalTuning.deadzoneV  = [0., 0.42,  0.83,  1.25]
      ret.startingState = True
      ret.startAccel = 2.0
      ret.stoppingDecelRate = 0.6  # EV: 0.6 m/s²/s — firm enough for traffic lights
      ret.minEnableSpeed = -1
      ret.enableBsm = True
    elif candidate == CAR.M6:
      ret.lateralTuning.pid.kpV = [1.5, 1.4, 1.1]
      ret.lateralTuning.pid.kiV = [0.52, 0.43, 0.32]
      ret.longitudinalTuning.kpV = [1.2, 1.0, 0.8]
      ret.longitudinalTuning.kiV = [0.5, 0.4, 0.3]
      ret.longitudinalTuning.deadzoneBP = [0., 9.]
      ret.longitudinalTuning.deadzoneV = [0., 0.15]

      ret.safetyConfigs[0].safetyParam = 3
      ret.startingState = True
      ret.startAccel = 3.0
      ret.stoppingDecelRate = 0.3
      ret.minEnableSpeed = -1
      ret.enableBsm = True
    elif candidate in (CAR.SEAL, CAR.SEALION7):
      ret.lateralTuning.pid.kiV, ret.lateralTuning.pid.kpV = [[0.52, 0.43, 0.32], [1.5, 1.4, 1.1]]

      ret.safetyConfigs[0].safetyParam = 2
      ret.openpilotLongitudinalControl = False
      ret.radarUnavailable = True
      ret.minEnableSpeed = -1
      ret.enableBsm = True
    else:
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

