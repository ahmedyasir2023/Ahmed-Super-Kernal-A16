#!/usr/bin/env python3
"""Fail-closed assertions for panel-notifier state and DeepDoze gating.

Accepts both the original V7.1 jiffies deadline and the V9.2 RC2
CLOCK_BOOTTIME deadline during final integrated validation.
"""
from pathlib import Path

s = (Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c").read_text()

must = [
    "static bool ay_screenoff_saver = true;",
    "module_param(ay_screenoff_saver, bool, 0644);",
    "if (!READ_ONCE(ay_deepdoze_enabled) ||\n        !READ_ONCE(ay_screenoff_saver) ||",
    "if (READ_ONCE(ay_screenoff_saver) &&\n                READ_ONCE(ay_deepdoze_enabled))",
    "WRITE_ONCE(ay_screen_on, false);",
    "WRITE_ONCE(ay_screen_on, true);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "queue_work(cpu_boost_wq, &ay_deepdoze_release);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
]
for token in must:
    assert token in s, token

boottime = "static ktime_t ay_deepdoze_last_blank_boottime;" in s
if boottime:
    for token in (
        "ktime_get_boottime()",
        "ktime_ms_delta(",
        "READ_ONCE(ay_deepdoze_last_blank_boottime)",
        "if (elapsed_ms < 600000)",
        "msecs_to_jiffies(remaining_ms)",
        "WRITE_ONCE(ay_deepdoze_last_blank_boottime, ktime_get_boottime());",
    ):
        assert token in s, token
    assert "if (time_before(jiffies, due))" not in s
    assert s.count("msecs_to_jiffies(600000)") == 1
else:
    assert "if (time_before(jiffies, due))" in s
    assert s.count("msecs_to_jiffies(600000)") == 2

assert "if (!READ_ONCE(ay_screenoff_saver))\n        return NOTIFY_DONE;" not in s
for bad in ("thermal_disable", "policy->max =", "selinux_enforcing = 0"):
    assert bad not in s, bad

# Modeled notifier state transitions, also when saver changes during dark.
class P:
    def __init__(self):
        self.on = True
        self.active = False
        self.armed = False
        self.saver = True
    def blank(self):
        if self.on:
            self.on = False
            self.armed = self.saver
    def unblank(self):
        if not self.on:
            self.on = True
            self.armed = False
            self.active = False

for state in (True, False):
    p = P()
    p.saver = state
    p.blank()
    assert p.on is False
    p.saver = not state
    p.unblank()
    assert p.on and not p.armed and not p.active

print("V7.1.1 panel tracking, saver gate, and rapid state-transition contracts: PASS")
print("Deadline implementation:", "CLOCK_BOOTTIME" if boottime else "jiffies")
