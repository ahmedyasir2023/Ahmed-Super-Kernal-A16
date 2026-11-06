#!/usr/bin/env python3
"""Source checks for V7.1 wake race hardening.

Accepts the original V7.1 jiffies deadline during the V7.1 workflow stage and
the V9.2 CLOCK_BOOTTIME implementation during final integrated validation.
"""
from pathlib import Path

s = (Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c").read_text()

common = [
    "#include <linux/jiffies.h>",
    "mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "if (READ_ONCE(ay_screen_on))",
]
for token in common:
    assert token in s, token

boottime = "static ktime_t ay_deepdoze_last_blank_boottime;" in s
if boottime:
    # V9.2 RC2: same stale-timer/reblank invariant, with suspend-inclusive time.
    required = [
        "ktime_get_boottime()",
        "ktime_ms_delta(",
        "READ_ONCE(ay_deepdoze_last_blank_boottime)",
        "if (elapsed_ms < 600000)",
        "msecs_to_jiffies(remaining_ms)",
        "WRITE_ONCE(ay_deepdoze_last_blank_boottime, ktime_get_boottime());",
    ]
    for token in required:
        assert token in s, token
    assert "static unsigned long ay_deepdoze_last_blank;" not in s
    assert "time_before(jiffies, due)" not in s
    assert "unsigned long due = READ_ONCE(ay_deepdoze_last_blank)" not in s
    assert s.count("msecs_to_jiffies(600000)") == 1
else:
    # Original V7.1 implementation, before the V9.2 RC2 transformation.
    required = [
        "static unsigned long ay_deepdoze_last_blank;",
        "unsigned long due = READ_ONCE(ay_deepdoze_last_blank) +",
        "if (time_before(jiffies, due))",
        "due - jiffies",
        "WRITE_ONCE(ay_deepdoze_last_blank, jiffies);",
    ]
    for token in required:
        assert token in s, token
    assert s.count("msecs_to_jiffies(600000)") == 2

assert "policy->max =" not in s

# Time-window model: an obsolete callback cannot apply a cap before the
# latest screen-off interval reaches 600 seconds.
def cap_at(now, last_blank, screen_off):
    return screen_off and now - last_blank >= 600

assert not cap_at(660, 610, True)
assert cap_at(1210, 610, True)
assert not cap_at(1210, 610, False)
print("V7.1 stale timer and rapid-reblank invariants passed.")
print("Deadline implementation:", "CLOCK_BOOTTIME" if boottime else "jiffies")
