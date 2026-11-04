#!/usr/bin/env python3
"""Lock requested HyperSpeed defaults so ROM init scripts cannot override them.

Runtime reports of 80ms/2 diverged from compiled 105ms/3. Make only these five
numeric module parameters read-only; keep screen/power state and thermal gates.
"""
from pathlib import Path

p = Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c"
s = p.read_text()
defaults = (
    "static unsigned int ay_input_boost_pct = 72;",
    "static unsigned int input_boost_ms = 105;",
    "static unsigned int sched_boost_on_input = 3;",
    "static unsigned int ay_wake_boost_pct = 82;",
    "static unsigned int ay_wake_boost_ms = 155;",
)
for item in defaults:
    assert s.count(item) == 1, f"Unexpected HyperSpeed setting: {item}"
for key in ("ay_input_boost_pct", "input_boost_ms", "sched_boost_on_input", "ay_wake_boost_pct", "ay_wake_boost_ms"):
    old = f"module_param({key}, uint, 0644);"
    new = f"module_param({key}, uint, 0444);"
    assert s.count(old) == 1 and new not in s, f"Unexpected parameter {key}"
    s = s.replace(old, new, 1)
p.write_text(s)
print("V7.2: HyperSpeed values unchanged and guarded against runtime sysfs overrides")
