#!/usr/bin/env python3
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.selfdrive.thermald.power_monitoring import PowerMonitoring, SHUTDOWN_DELAY_S, LOW_VOLTAGE_mV, LOW_VOLTAGE_DURATION_S


ssb = 0.
def mock_time_monotonic():
  global ssb
  ssb += 1.
  return ssb

GOOD_VOLTAGE = 12 * 1e3
LOW_VOLTAGE = (LOW_VOLTAGE_mV / 1e3 - 1) * 1e3


@patch("time.monotonic", new=mock_time_monotonic)
class TestPowerMonitoring(unittest.TestCase):
  def setUp(self):
    self.params = Params()

  def test_none_voltage(self):
    pm = PowerMonitoring()
    for _ in range(10):
      pm.calculate(None)
    self.assertEqual(pm.get_power_used(), 0)
    self.assertEqual(pm.get_car_battery_capacity(), 0)

  def test_voltage_filtering(self):
    pm = PowerMonitoring()
    for _ in range(100):
      pm.calculate(GOOD_VOLTAGE)
    self.assertLess(abs(pm.car_voltage_mV - GOOD_VOLTAGE), 100)

  def test_low_voltage_tracking(self):
    pm = PowerMonitoring()
    start_time = ssb
    for _ in range(100):
      pm.calculate(LOW_VOLTAGE)
    self.assertIsNotNone(pm.low_voltage_start_time)
    self.assertAlmostEqual(pm.low_voltage_start_time, start_time, delta=2)

  def test_low_voltage_reset(self):
    pm = PowerMonitoring()
    for _ in range(100):
      pm.calculate(LOW_VOLTAGE)
    self.assertIsNotNone(pm.low_voltage_start_time)
    for _ in range(100):
      pm.calculate(GOOD_VOLTAGE)
    self.assertIsNone(pm.low_voltage_start_time)

  def test_shutdown_after_delay(self):
    pm = PowerMonitoring()
    start_time = ssb
    while ssb < start_time + SHUTDOWN_DELAY_S:
      pm.calculate(GOOD_VOLTAGE)
      if ssb - start_time < SHUTDOWN_DELAY_S:
        self.assertFalse(pm.should_shutdown(False, True, start_time, True))
    self.assertTrue(pm.should_shutdown(False, True, start_time, True))

  def test_shutdown_low_voltage(self):
    pm = PowerMonitoring()
    start_time = ssb
    for _ in range(100):
      pm.calculate(LOW_VOLTAGE)
    while ssb < start_time + LOW_VOLTAGE_DURATION_S + 10:
      pm.calculate(LOW_VOLTAGE)
    self.assertTrue(pm.should_shutdown(False, True, start_time, True))

  def test_shutdown_low_voltage_bypasses_min_on_time(self):
    global ssb
    ssb = 0
    pm = PowerMonitoring()
    start_time = ssb
    for _ in range(100):
      pm.calculate(LOW_VOLTAGE)
    while ssb < start_time + LOW_VOLTAGE_DURATION_S + 10:
      pm.calculate(LOW_VOLTAGE)
    self.assertTrue(pm.should_shutdown(False, True, start_time, False))

  def test_no_shutdown_with_ignition(self):
    pm = PowerMonitoring()
    start_time = ssb
    while ssb < start_time + SHUTDOWN_DELAY_S + 10:
      pm.calculate(GOOD_VOLTAGE)
    self.assertFalse(pm.should_shutdown(True, True, start_time, True))

  def test_no_shutdown_not_in_car(self):
    pm = PowerMonitoring()
    start_time = ssb
    while ssb < start_time + SHUTDOWN_DELAY_S + 10:
      pm.calculate(GOOD_VOLTAGE)
    self.assertFalse(pm.should_shutdown(False, False, start_time, True))

  def test_no_shutdown_disable_power_down(self):
    self.params.put_bool("DisablePowerDown", True)
    pm = PowerMonitoring()
    start_time = ssb
    while ssb < start_time + SHUTDOWN_DELAY_S + 10:
      pm.calculate(GOOD_VOLTAGE)
    self.assertFalse(pm.should_shutdown(False, True, start_time, True))

  def test_no_shutdown_before_min_on_time(self):
    global ssb
    ssb = 0
    pm = PowerMonitoring()
    start_time = ssb
    while ssb < start_time + SHUTDOWN_DELAY_S + 10:
      pm.calculate(GOOD_VOLTAGE)
    self.assertFalse(pm.should_shutdown(False, True, start_time, False))

  def test_no_shutdown_offroad_timestamp_none(self):
    pm = PowerMonitoring()
    self.assertFalse(pm.should_shutdown(False, True, None, True))


if __name__ == "__main__":
  unittest.main()
