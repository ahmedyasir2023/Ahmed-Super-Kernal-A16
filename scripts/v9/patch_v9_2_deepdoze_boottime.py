#!/usr/bin/env python3
"""V9.2 RC2: measure the 600-second DeepDoze deadline with CLOCK_BOOTTIME.

The existing one-shot timer remains deferrable. This change does NOT wake a
suspended device to apply a CPU cap. When the callback next gets CPU time, it
checks actual elapsed screen-off time including suspend and reschedules the
same deferrable work if the 600-second deadline has not elapsed.

Apply after patch_v9_2_power_suspend_telemetry.py, which supplies ktime and
timekeeping headers. No foreground CPUFreq, touch, thermal, root or DTB change.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/cpufreq/cpu-boost.c"
s = driver.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    assert old != new and s.count(old) == 1, (
        "V9.2 DeepDoze CLOCK_BOOTTIME source contract failed at " + label
    )
    s = s.replace(old, new, 1)


one(
    "static unsigned long ay_deepdoze_last_blank;\n"
    "static struct delayed_work ay_deepdoze_timer;\n",
    "static ktime_t ay_deepdoze_last_blank_boottime;\n"
    "static struct delayed_work ay_deepdoze_timer;\n",
    "replace jiffies deadline with CLOCK_BOOTTIME timestamp",
)

old_guard = """    {
        unsigned long due = READ_ONCE(ay_deepdoze_last_blank) +
                            msecs_to_jiffies(600000);

        if (time_before(jiffies, due)) {
            mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,
                             due - jiffies);
            return;
        }
    }
    if (READ_ONCE(ay_screen_on))
        return;
"""
new_guard = """    /*
     * CLOCK_BOOTTIME includes time spent in system suspend. The timer itself
     * remains deferrable, so this check never wakes the phone just to apply
     * the CPUFreq cap. If it runs before 600 real screen-off seconds, defer
     * the SAME work until the remaining time has elapsed.
     */
    {
        s64 elapsed_ms = ktime_ms_delta(
            ktime_get_boottime(),
            READ_ONCE(ay_deepdoze_last_blank_boottime));

        if (elapsed_ms < 0)
            elapsed_ms = 0;

        if (elapsed_ms < 600000) {
            unsigned int remaining_ms =
                (unsigned int)(600000 - elapsed_ms);
            unsigned long remaining_jiffies =
                msecs_to_jiffies(remaining_ms);

            if (READ_ONCE(ay_screen_on))
                return;
            if (!remaining_jiffies)
                remaining_jiffies = 1;
            mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,
                             remaining_jiffies);
            return;
        }
    }
    if (READ_ONCE(ay_screen_on))
        return;
"""
one(old_guard, new_guard, "boottime threshold and deferrable reschedule")

one(
    "WRITE_ONCE(ay_deepdoze_last_blank, jiffies);",
    "WRITE_ONCE(ay_deepdoze_last_blank_boottime, ktime_get_boottime());",
    "timestamp the most recent panel blank with CLOCK_BOOTTIME",
)

assert "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);" in s
assert "msecs_to_jiffies(600000)" in s
assert "ktime_get_boottime()" in s
assert "ktime_ms_delta(" in s
assert "READ_ONCE(ay_deepdoze_last_blank_boottime)" in s
assert "mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer," in s
assert "time_before(jiffies, due)" not in s
assert not re.search(r"\bay_deepdoze_last_blank\b", s)
assert s.count("WRITE_ONCE(ay_deepdoze_last_blank_boottime, ktime_get_boottime())") == 1

# The deadline must remain a single deferrable work item, not a wake source.
for forbidden in (
    "schedule_delayed_work(&ay_deepdoze_timer",
    "pm_stay_awake(",
    "pm_wakeup_event(",
    "wake_lock(",
    "alarm_start(",
    "alarm_start_relative(",
    "schedule_timeout(",
):
    assert forbidden not in s, "V9.2 must not create a wake source: " + forbidden

driver.write_text(s)
print("V9.2 RC2: DeepDoze 600s deadline now uses CLOCK_BOOTTIME.")
print("The existing timer remains deferrable; no suspend wakeup is added.")
print("Rapid reblank, screen-on release, CPUFreq floors and thermal limits remain.")
