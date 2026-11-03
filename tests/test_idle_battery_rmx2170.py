#!/usr/bin/env python3
"""Offline unit tests; no ADB, device or network is accessed."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tools/measure_idle_battery_rmx2170.py"
spec = importlib.util.spec_from_file_location("measure_idle_battery_rmx2170", path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BatteryParsingTests(unittest.TestCase):
    def test_charge_counter_and_unplugged(self):
        output = """Current Battery Service state:
  AC powered: false
  USB powered: false
  Wireless powered: false
  status: 3
  level: 86
  voltage: 4024
  temperature: 275
  Charge counter: 3073000"""
        values = module.battery_data(output)
        self.assertEqual(values["level_percent"], 86)
        self.assertEqual(values["charge_counter_uah"], 3073000)
        self.assertFalse(values["power_connected"])

    def test_charge_and_counter_delta(self):
        a = {"level_percent": 86, "charge_counter_uah": 3073000}
        b = {"level_percent": 85, "charge_counter_uah": 3058000}
        delta = module.measure_delta(a, b, 30 * 60)
        self.assertEqual(delta["percent_drop"], 1)
        self.assertEqual(delta["consumption_mah"], 15.0)
        self.assertEqual(delta["avg_current_ma"], 30.0)

    def test_no_invented_charge_counter(self):
        a = {"level_percent": 60, "charge_counter_uah": None}
        b = {"level_percent": 59, "charge_counter_uah": None}
        delta = module.measure_delta(a, b, 1500)
        self.assertEqual(delta["percent_drop"], 1)
        self.assertIsNone(delta["consumption_mah"])

    def test_power_connection_detection(self):
        values = module.battery_data("USB powered: true\nlevel: 92\nstatus: 2")
        self.assertTrue(values["power_connected"])

    def test_invalid_counter_delta(self):
        a = {"level_percent": 55, "charge_counter_uah": 500000}
        b = {"level_percent": 56, "charge_counter_uah": 505000}
        self.assertIsNone(module.measure_delta(a, b, 1200)["consumption_mah"])


if __name__ == "__main__":
    unittest.main()
