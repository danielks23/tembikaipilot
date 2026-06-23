import time

from openpilot.common.params import Params
from openpilot.selfdrive.statsd import statlog

CAR_VOLTAGE_LOW_PASS_K = 0.011  # LPF gain for 45s tau
SHUTDOWN_DELAY_S = 300  # 5 min after ignition off
LOW_VOLTAGE_mV = 11800  # shutdown if car battery < 11.8V
LOW_VOLTAGE_DURATION_S = 30  # voltage must be low for 30s before shutdown
MIN_ON_TIME_S = 3600


class PowerMonitoring:
  def __init__(self):
    self.params = Params()
    self.car_voltage_mV = 12e3
    self.low_voltage_start_time = None

  def calculate(self, voltage: int | None):
    if voltage is None:
      return

    now = time.monotonic()
    self.car_voltage_mV = ((voltage * CAR_VOLTAGE_LOW_PASS_K) + (self.car_voltage_mV * (1 - CAR_VOLTAGE_LOW_PASS_K)))
    statlog.gauge("car_voltage", self.car_voltage_mV / 1e3)

    if self.car_voltage_mV < LOW_VOLTAGE_mV:
      if self.low_voltage_start_time is None:
        self.low_voltage_start_time = now
    else:
      self.low_voltage_start_time = None

  def get_power_used(self) -> int:
    return 0

  def get_car_battery_capacity(self) -> int:
    return 0

  def should_shutdown(self, ignition: bool, in_car: bool, offroad_timestamp: float | None, started_seen: bool):
    if offroad_timestamp is None:
      return False

    if ignition or not in_car or self.params.get_bool("DisablePowerDown"):
      return False

    now = time.monotonic()
    offroad_time = now - offroad_timestamp

    low_voltage_shutdown = (self.low_voltage_start_time is not None and
                            (now - self.low_voltage_start_time) > LOW_VOLTAGE_DURATION_S)

    time_based_shutdown = (offroad_time > SHUTDOWN_DELAY_S and
                           (started_seen or now > MIN_ON_TIME_S))

    return low_voltage_shutdown or time_based_shutdown
