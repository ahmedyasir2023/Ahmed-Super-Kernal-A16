#!/usr/bin/env python3
"""V10.4 source and deterministic rate-limit contract checks."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = (root / "kernel/kernel/sched/cpufreq_schedutil.c").read_text()

for token in (
    "#include <linux/moduleparam.h>",
    "#define AY_V10_4_FAST_UP_CAP_US 250",
    "static bool ay_v10_4_schedutil_fast_up = true;",
    "module_param_named(ay_v10_4_schedutil_fast_up, ay_v10_4_schedutil_fast_up, bool, 0600);",
    '1: cap upward schedutil delay at 250us; 0: vendor rate limits',
    "static inline s64 sugov_effective_up_rate_delay_ns(",
    "READ_ONCE(ay_v10_4_schedutil_fast_up)",
    "min_t(s64, delay_ns,",
    "(s64)AY_V10_4_FAST_UP_CAP_US * NSEC_PER_USEC",
):
    assert token in src, token

helper = src[src.index("static inline s64 sugov_effective_up_rate_delay_ns("):
             src.index("static bool sugov_should_update_freq(")]
assert "delay_ns = sg_policy->up_rate_delay_ns;" in helper
assert "return delay_ns;" in helper

should = src[src.index("static bool sugov_should_update_freq("):
             src.index("static bool sugov_up_down_rate_limit(")]
assert should.index("if (READ_ONCE(ay_v10_4_schedutil_fast_up))") < should.index(
    "min(sugov_effective_up_rate_delay_ns(sg_policy),")
assert "sg_policy->down_rate_delay_ns" in should
assert "return delta_ns >= sg_policy->min_rate_limit_ns;" in should
# Existing UIFirst boost bypass must still run before rate limiting.
assert should.index("SCHED_CPUFREQ_BOOST") < should.index(
    "if (READ_ONCE(ay_v10_4_schedutil_fast_up))")

rate = src[src.index("static bool sugov_up_down_rate_limit("):
           src.index("static inline bool use_pelt(")]
assert "up_rate_delay_ns = sugov_effective_up_rate_delay_ns(sg_policy);" in rate
assert "delta_ns < up_rate_delay_ns" in rate
assert "delta_ns < sg_policy->down_rate_delay_ns" in rate
assert "SCHED_CPUFREQ_BOOST" in rate

# Deterministic model: cap only the upward delay; never alter downward delay.
CAP = 250_000  # ns
def effective(up, down, enabled):
    up_effective = min(up, CAP) if enabled else up
    gate = min(up_effective, down) if enabled else min(up, down)
    return up_effective, down, gate

assert effective(500_000, 500_000, True) == (250_000, 500_000, 250_000)
assert effective(100_000, 500_000, True) == (100_000, 500_000, 100_000)
assert effective(500_000, 100_000, True) == (250_000, 100_000, 100_000)
assert effective(500_000, 500_000, False) == (500_000, 500_000, 500_000)
assert effective(0, 500_000, True) == (0, 500_000, 0)

for forbidden in (
    "pm_stay_awake(", "pm_wakeup_event(", "wake_lock(",
    "thermal_disable", "selinux_enforcing = 0",
    "cpufreq_driver_target(policy, UINT_MAX",
):
    assert forbidden not in src, forbidden

# No timers, workqueues, wake sources, or scheduler placement edits in V10.4.
assert "schedule_delayed_work" not in src
assert "INIT_WORK(" not in src
assert "wake_lock(" not in src

print("PASS: V10.4 upward-only schedutil delay cap and runtime rollback.")
print("PASS: downward rate limit and UIFirst boost bypass unchanged.")
print("PASS: deterministic rate-limit model and no wake/timer/thermal-policy additions.")
