#!/usr/bin/env python3
"""Fail-closed source guard for the V5 adaptive input boost experiment.

Requires an already staged V4 SUSFS+DT2W tree. Compile success does not prove
better performance on actual hardware.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/cpufreq/cpu-boost.c"
config = root / "kernel/arch/arm64/configs/atoll_defconfig"
touch = root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c"
api = root / "KernelSU-Next/uapi/supercall.h"

src = driver.read_text()
assert "CONFIG_CPU_BOOST=y" in config.read_text(), "Vendor CPU boost not compiled"
assert "#define KERNEL_SU_UAPI_VERSION 6" in api.read_text(), "Root API changed"
assert "uint8_t DouTap_enable = 1;" in touch.read_text(), "DT2W override missing"
assert "ts->gesture_enable = 1;" in touch.read_text(), "Gesture mode unsupported"
assert "static bool ay_auto_input_boost = true;" in src
assert "static unsigned int ay_input_boost_pct = 60;" in src
assert "static unsigned int input_boost_ms = 90;" in src
assert "static unsigned int sched_boost_on_input = 3;" in src

required = [
    "cpufreq_cpu_get(cpu)",
    "cpufreq_cpu_put(policy)",
    "policy->cpuinfo.min_freq",
    "max_freq = policy->max",
    "pct = min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 75)",
    "target = min_freq + (max_freq - min_freq) * pct / 100",
    "min_t(unsigned int,",
    "READ_ONCE(input_boost_ms), 120)",
    "if (type == EV_SYN || (type == EV_KEY && !value))",
    "if (!READ_ONCE(input_boost_enabled) &&",
    "#define MIN_INPUT_INTERVAL (150 * USEC_PER_MSEC)",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_update_policy(i)",
    "queue_delayed_work(cpu_boost_wq, &input_boost_rem",
    "sched_set_boost(-(int)sched_boost_active)",
]
for phrase in required:
    assert phrase in src, f"Required safety/performance invariant missing: {phrase}"

for forbidden in [
    "thermal_disable", "thermal_throttle_disable", "disable_thermal",
    "selinux_enforcing = 0", "CONFIG_SECURITY_SELINUX_DISABLE",
    "policy->max =", "cpufreq_driver_target(policy",
]:
    assert forbidden not in src, "Unsafe performance override: " + forbidden

# Integer range simulation: all boosts are inside the real policy range,
# including on both little and big CPU clusters.
for lo, hi in [(300000, 1804800), (710400, 2208000), (300000, 2304000)]:
    for pct in (0, 25, 60, 75, 95, 1000):
        bounded = min(pct, 75)
        target = lo + (hi - lo) * bounded // 100 if hi > lo and bounded else 0
        assert target == 0 or lo <= target <= hi
print("V5 AY HyperSpeed source contract PASS")
print("Touch + auto CPU input boost 60%, 90 ms / 120 ms hard cap, 150 ms debounce")
print("No permanent performance governor or thermal/security bypass")
