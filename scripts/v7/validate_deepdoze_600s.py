#!/usr/bin/env python3
"""V7 source and static transition-contract validation.

This is NOT proof of device suspend, touch, battery savings or runtime clocks.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
driver = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
touch = (root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
config_path = root / "kernel/out/.config"
config = config_path.read_text() if config_path.exists() else ""

required = (
    "static bool ay_deepdoze_enabled = true;",
    "module_param(ay_deepdoze_enabled, bool, 0444);",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "module_param(ay_deepdoze_delay_seconds, uint, 0444);",
    "static bool ay_deepdoze_active;",
    "module_param(ay_deepdoze_active, bool, 0444);",
    "module_param(ay_deepdoze_entries, uint, 0444);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "msecs_to_jiffies(600000)",
    "if (!READ_ONCE(ay_screen_on) &&",
    "READ_ONCE(ay_deepdoze_active))",
    "unsigned int floor = max(policy->min,",
    "policy->cpuinfo.min_freq);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "queue_work(cpu_boost_wq, &ay_deepdoze_release);",
    "static void ay_deepdoze_restore(struct work_struct *work)",
    "update_policy_online();",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "MSM_DRM_BLANK_UNBLANK",
    "MSM_DRM_BLANK_POWERDOWN",
    "MSM_DRM_PRIMARY_DISPLAY",
)
for needle in required:
    assert needle in driver, f"Missing safety contract: {needle}"
for bad in ("policy->max =", "thermal_disable", "selinux_enforcing = 0",
            "CPU_FREQ_GOV_PERFORMANCE=y", "msleep(600000)",
            "schedule_delayed_work(&ay_deepdoze_timer"):
    assert bad not in driver, f"Forbidden driver code: {bad}"
assert driver.count("msecs_to_jiffies(600000)") == 1
assert "uint8_t DouTap_enable = 1;" in touch
assert "ts->gesture_enable = 1;" in touch
if config:
    assert "CONFIG_CPU_BOOST=y" in config
    assert "CONFIG_DRM_MSM=y" in config

# Pure transition model tests: off->premature wake, off->10min->wake,
# off->10min->rapid reblank. The real kernel must still be device-tested.
class Panel:
    def __init__(self):
        self.on, self.timer, self.cap = True, False, False
    def blank(self):
        if self.on:
            self.on, self.timer = False, True
    def expire(self):
        if self.timer and not self.on:
            self.cap = True
            self.timer = False
    def unblank(self):
        if not self.on:
            self.on, self.timer, self.cap = True, False, False

a = Panel()
a.blank()
a.unblank()
a.expire()
assert a.on and not a.cap
b = Panel()
b.blank()
b.expire()
assert not b.on and b.cap
b.unblank()
assert b.on and not b.cap
b.blank()
assert not b.on and b.timer and not b.cap
print("V7 static and model validation passed. Physical RMX2170 tests required.")
