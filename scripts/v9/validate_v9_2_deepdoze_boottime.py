#!/usr/bin/env python3
"""V9.2 RC2: source and model checks for suspend-aware DeepDoze deadline."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
cpu = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()

required = (
    "#include <linux/ktime.h>",
    "#include <linux/timekeeping.h>",
    "static ktime_t ay_deepdoze_last_blank_boottime;",
    "WRITE_ONCE(ay_deepdoze_last_blank_boottime, ktime_get_boottime());",
    "ktime_ms_delta(",
    "ktime_get_boottime()",
    "READ_ONCE(ay_deepdoze_last_blank_boottime)",
    "if (elapsed_ms < 600000)",
    "msecs_to_jiffies(remaining_ms)",
    "mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
)
for token in required:
    assert token in cpu, f"Missing RC2 DeepDoze contract: {token}"

assert "time_before(jiffies, due)" not in cpu
assert not re.search(r"\bay_deepdoze_last_blank\b", cpu)
assert cpu.count("INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);") == 1
assert cpu.count(
    "WRITE_ONCE(ay_deepdoze_last_blank_boottime, ktime_get_boottime());"
) == 1

# Confirm the screen-off callback still schedules the existing deferrable work.
assert "msecs_to_jiffies(600000)" in cpu
assert "mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer," in cpu

# Validate the generated kernel C source, not the Python patcher's own
# assertion strings. The old check searched the patch script text and therefore
# matched its own forbidden-token list (a false positive).
for forbidden in (
    "schedule_delayed_work(&ay_deepdoze_timer",
    "pm_stay_awake(",
    "pm_wakeup_event(",
    "wake_lock(",
    "alarm_start(",
    "alarm_start_relative(",
    "schedule_timeout(",
):
    assert forbidden not in cpu, (
        f"Forbidden DeepDoze wake source in generated CPUBoost C: {forbidden}"
    )

# No active polling loop may be added to the DeepDoze expiry callback.
start = cpu.index("static void ay_deepdoze_expire(")
end = cpu.index("\n}\n", start)
expire_body = cpu[start:end]
assert "while (1)" not in expire_body
assert "for (;;)" not in expire_body

# Pure timebase model: suspend time counts toward 600s, but never causes an
# early cap. A deferrable callback only schedules remaining time when it runs.
def deadline(now_boottime_ms, last_blank_boottime_ms, screen_on=False):
    if screen_on:
        return ("inactive", 0)
    elapsed = max(0, now_boottime_ms - last_blank_boottime_ms)
    if elapsed < 600000:
        return ("defer", 600000 - elapsed)
    return ("activate", 0)

cases = [
    ((1000, 1000, False), ("defer", 600000)),
    ((600999, 1000, False), ("defer", 1)),
    ((601000, 1000, False), ("activate", 0)),
    # 8h asleep: CLOCK_BOOTTIME counts the suspended interval.
    ((28_801_000, 1000, False), ("activate", 0)),
    # A rapid reblank resets the timestamp; old delayed work cannot cap early.
    ((300_000, 200_000, False), ("defer", 500_000)),
    ((601_000, 200_000, True), ("inactive", 0)),
]
for args, expected in cases:
    actual = deadline(*args)
    assert actual == expected, (args, actual, expected)

print("PASS: DeepDoze uses actual CLOCK_BOOTTIME elapsed time, including suspend.")
print("PASS: no early cap; latest blank timestamp protects rapid OFF/ON/OFF.")
print("PASS: existing 600s timer remains deferrable; no new wake source or polling.")
print("PASS: screen-on release, CPUFreq policy floor and existing boost contract retained.")
print("LIMIT: power savings and physical DT2W/fingerprint behavior require RMX2170 testing.")
