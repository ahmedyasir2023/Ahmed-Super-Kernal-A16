#!/usr/bin/env python3
"""Fail closed on immutable V7.2 boost defaults and unchanged DeepDoze."""
from pathlib import Path

s = (Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
values = {
    "ay_input_boost_pct": 72,
    "input_boost_ms": 105,
    "sched_boost_on_input": 3,
    "ay_wake_boost_pct": 82,
    "ay_wake_boost_ms": 155,
}
for key, value in values.items():
    assert s.count(f"static unsigned int {key} = {value};") == 1
    assert s.count(f"module_param({key}, uint, 0444);") == 1
    assert f"module_param({key}, uint, 0644);" not in s
for gate in (
    "static bool ay_auto_input_boost = true;",
    "static bool ay_screenoff_saver = true;",
    "static bool ay_instantwake = true;",
    "static bool ay_deepdoze_enabled = true;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "sched_set_boost(-(int)sched_boost_active)",
    "cpufreq_verify_within_limits(policy, 0, floor);",
):
    assert gate in s, gate
assert "thermal_disable" not in s and "policy->max =" not in s
print("V7.2 immutable HyperSpeed + DeepDoze 600s contracts: PASS")
