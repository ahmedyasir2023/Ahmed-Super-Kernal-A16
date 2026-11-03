#!/usr/bin/env python3
"""V4 lab: default-on double tap to wake directly in RMX2170 touch driver.

Changes ONLY DouTap_enable initial default 0 -> 1. Existing probe already
initializes ts->gesture_enable=1; the vendor suspend function then enters
MODE_GESTURE and enables IRQ wake on supported panel hardware.

- Works from initial touch-driver probe on every reboot (no late init script).
- Does not enable other drawings or single-tap gesture features.
- Does not override explicit proc settings, touch firmware or Android HAL.
- Fails closed if the pinned Realme driver changes unexpectedly.
- Not boot/runtime validated: no flashable package.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c"
s = driver.read_text()
before = "uint8_t DouTap_enable = 0;\t\t\t\t // double tap"
after = "uint8_t DouTap_enable = 1;\t\t\t\t // AY DT2W: enabled from touch probe on every boot"

checks = {
    "initial DT2W state": before,
    "touch probe's gesture mode": "    ts->gesture_enable = 1;",
    "DT2W filtered by key": "enabled = DouTap_enable;",
    "double-tap event key": "key = KEY_DOUBLE_TAP;",
    "proc control retained": "GESTURE_ATTR(double_tap, DouTap_enable);",
    "original other-gesture default": "uint8_t gesture_enable = 0;",
    "suspend gesture switch": "ts->ts_ops->mode_switch(ts->chip_data, MODE_GESTURE, true);",
    "hardware suspend enable IRQ": "enable_irq_wake(ts->irq);",
    "touch support gating": "if (ts->black_gesture_support) {",
}
for name, fragment in checks.items():
    assert fragment in s, f"Unexpected Realme touch driver: missing {name}"
assert s.count(before) == 1
assert "uint8_t DouTap_enable = 1;" not in s
assert s.count("    ts->gesture_enable = 1;") == 1
assert s.count("GESTURE_ATTR(double_tap, DouTap_enable);") == 1

updated = s.replace(before, after, 1)
assert len(updated.splitlines()) == len(s.splitlines())
assert updated.count("uint8_t gesture_enable = 0;") == 1
assert updated.count("enabled = DouTap_enable;") == 1
assert updated.count("key = KEY_DOUBLE_TAP;") == 1
assert updated.count("enable_irq_wake(ts->irq);") == s.count("enable_irq_wake(ts->irq);")
assert updated.replace(after, before, 1) == s, "Modification would touch unintended source code"
driver.write_text(updated)
print("AY Always-On DT2W: vendor boot default enabled; hardware/suspend logic unchanged")
print("Vendor still supports explicit proc override; no forced override of Android settings")
print("No flashable boot image or APK generated")
