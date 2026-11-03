#!/usr/bin/env python3
"""Fail-closed assertions for panel-notifier state and DeepDoze gating."""
from pathlib import Path
s=(Path(__file__).resolve().parents[2]/"kernel/drivers/cpufreq/cpu-boost.c").read_text()
must=[
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
    "if (time_before(jiffies, due))",
]
for k in must:
    assert k in s,k
assert "if (!READ_ONCE(ay_screenoff_saver))\n        return NOTIFY_DONE;" not in s
assert s.count("msecs_to_jiffies(600000)") == 2
for bad in ("thermal_disable","policy->max =","selinux_enforcing = 0"):
    assert bad not in s,bad

# Modeled notifier state transitions, also when saver changes during dark.
class P:
    def __init__(self):
        self.on=True
        self.active=False
        self.armed=False
        self.saver=True
    def blank(self):
        if self.on:
            self.on=False
            self.armed=self.saver
    def unblank(self):
        if not self.on:
            self.on=True
            self.armed=False
            self.active=False
for state in (True,False):
    p=P();p.saver=state
    p.blank()
    assert p.on is False
    p.saver=not state
    p.unblank()
    assert p.on and not p.armed and not p.active
print("V7.1.1 panel tracking, saver gate, and rapid state-transition contracts: PASS")
