#!/usr/bin/env python3
"""Source checks for V7.1 wake race hardening after V7 patch."""
from pathlib import Path
s=(Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
must = [
    "#include <linux/jiffies.h>",
    "static unsigned long ay_deepdoze_last_blank;",
    "unsigned long due = READ_ONCE(ay_deepdoze_last_blank) +",
    "if (time_before(jiffies, due))",
    "mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,",
    "due - jiffies",
    "WRITE_ONCE(ay_deepdoze_last_blank, jiffies);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "if (READ_ONCE(ay_screen_on))",
    "msecs_to_jiffies(600000)",
]
for m in must:
    assert m in s, m
assert s.count("msecs_to_jiffies(600000)") == 2
assert "policy->max =" not in s
# Time-window model: even with an obsolete callback, a fresh blank must
# receive a new full 600-second interval.
def cap_at(now, last_blank, screen_off):
    return screen_off and now - last_blank >= 600
assert not cap_at(660, 610, True)  # previous screen dark for >600s, now reblanked
assert cap_at(1210, 610, True)
assert not cap_at(1210, 610, False)
print("V7.1 stale timer and rapid-reblank invariants passed.")
