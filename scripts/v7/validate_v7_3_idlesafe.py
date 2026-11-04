#!/usr/bin/env python3
"""V7.3 pre/post build contract: preserve V7.2's low-power behavior.

Pure state-machine checks validate invariants, not battery runtime.
The CI SHA-256 snapshot separately guarantees bit-identical V7.2 touch,
ZRAM and CPU-boost sources after V7.3 changes.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cpu = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
touch = (root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()

assert cpu.count("msecs_to_jiffies(600000)") == 2
assert cpu.count("INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);") == 1
for snippet in (
    "static bool ay_screenoff_saver = true;",
    "static bool ay_instantwake = true;",
    "static unsigned int ay_wake_boost_pct = 82;",
    "static unsigned int ay_wake_boost_ms = 155;",
    "static unsigned int ay_input_boost_pct = 72;",
    "static unsigned int input_boost_ms = 105;",
    "static unsigned int sched_boost_on_input = 3;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "module_param(ay_screen_on, bool, 0444);",
    "module_param(ay_deepdoze_active, bool, 0444);",
    "WRITE_ONCE(ay_deepdoze_last_blank, jiffies);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "queue_work(cpu_boost_wq, &ay_deepdoze_release);",
    "if (time_before(jiffies, due))",
    "mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);",
):
    assert snippet in cpu, f"Missing V7.2 power contract: {snippet}"
for snippet in (
    "uint8_t DouTap_enable = 1;",
    "ts->gesture_enable = 1;",
):
    assert snippet in touch, snippet
for forbidden in ("thermal_disable", "selinux_enforcing = 0",
                  "msleep(600000)", "policy->max =", "CPU_FREQ_GOV_PERFORMANCE=y"):
    assert forbidden not in cpu, forbidden

# A model of the existing event-driven power contract. Not a runtime simulator.
class IdleModel:
    def __init__(self):
        self.on = True
        self.boost = False
        self.timer = False
        self.cap = False
        self.last_off = None
    def blank(self, now):
        if self.on:
            self.on = False
            self.boost = False
            self.timer = True
            self.last_off = now
    def expire(self, now):
        if self.timer and not self.on and now - self.last_off >= 600:
            self.cap = True
            self.timer = False
    def unblank(self, now):
        if not self.on:
            self.on = True
            self.timer = False
            self.cap = False
            self.boost = True

# 30 minutes with screen off: no wake boost and no recurring timer.
m = IdleModel()
m.blank(0)
m.expire(599)
assert not m.cap and m.timer and not m.boost
m.expire(600)
assert m.cap and not m.timer and not m.boost
m.expire(1800)
assert m.cap and not m.timer and not m.boost
m.unblank(1801)
assert m.on and not m.cap and m.boost

# Rapid OFF/ON/OFF: never allow old timer to cap before new deadline.
m = IdleModel()
m.blank(0)
m.unblank(100)
m.blank(105)
m.expire(600)
assert not m.cap and m.timer
m.expire(705)
assert m.cap and not m.on
m.unblank(706)
assert not m.cap and m.on

print("V7.3 idle-contract source/model tests: PASS (hardware validation pending)")
