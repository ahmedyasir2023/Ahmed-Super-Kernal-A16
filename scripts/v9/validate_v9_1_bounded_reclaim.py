#!/usr/bin/env python3
"""V9.1 compile-time contract + deterministic exit-model regression tests.

This does not assert that one additional background scan reduces actual PSI.
Compare owner-observed PSI and battery against V9 RC1.1 after safe boot.
"""
from pathlib import Path

kernel = Path(__file__).resolve().parents[2] / "kernel"
s = (kernel / "mm/vmscan.c").read_text()
cpu = (kernel / "drivers/cpufreq/cpu-boost.c").read_text()
touch = (kernel / "drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
multi = (kernel / "mm/multi_kswapd/multi_kswapd.c").read_text()
watermarks = (kernel / "mm/page_alloc.c").read_text()

for term in (
    "#include <linux/jiffies.h>",
    "static bool ay_v91_bounded_reclaim = true;",
    "module_param_named(ay_v91_bounded_reclaim, ay_v91_bounded_reclaim, bool, 0600);",
    "static unsigned long ay_v91_last_extra_jiffies;",
    "atomic64_t ay_v91_extra_passes = ATOMIC64_INIT(0);",
    "atomic64_t ay_v91_waiter_exits = ATOMIC64_INIT(0);",
    "v91_bounded_reclaim_enabled=%d",
    "v91_extra_passes=%lld",
    "v91_waiter_exits=%lld",
    "unsigned int ay_v91_extra_this_cycle = 0;",
    "if (try_to_freeze() || kthread_should_stop())",
    "if (!READ_ONCE(ay_reclaim_progress) &&",
    "!atomic_long_read(&kswapd_waiters)",
    "READ_ONCE(ay_v91_bounded_reclaim)",
    "!ay_v91_extra_this_cycle",
    "sc.nr_reclaimed > nr_reclaimed",
    "!pgdat_balanced(pgdat, sc.order, classzone_idx)",
    "msecs_to_jiffies(1000)",
    "ay_v91_extra_this_cycle++;",
    "cmpxchg(&ay_v91_last_extra_jiffies,",
    "atomic64_inc(&ay_v91_extra_passes);",
    "atomic64_inc(&ay_v91_waiter_exits);",
    "module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);",
    "INIT_DEFERRABLE_WORK",  # present in cpu, not vmscan; verified separately
):
    if term == "INIT_DEFERRABLE_WORK":
        assert term in cpu, term
    else:
        assert term in s, term

fn = s[s.index("static int balance_pgdat(pg_data_t *pgdat, int order, int classzone_idx)"):]
order = [
    fn.index("unsigned int ay_v91_extra_this_cycle = 0;"),
    fn.index("psi_memstall_enter(&pflags);"),
    fn.index("if (try_to_freeze() || kthread_should_stop())"),
    fn.index("if (!READ_ONCE(ay_reclaim_progress) &&"),
    fn.index("ay_v91_extra_this_cycle++;"),
    fn.index("nr_reclaimed = sc.nr_reclaimed - nr_reclaimed;"),
]
assert order == sorted(order), order
assert fn.count("ay_v91_extra_this_cycle++;") == 1
assert fn.count("cmpxchg(&ay_v91_last_extra_jiffies,") == 1
assert s.count("msecs_to_jiffies(1000)") == 1

for term in (
    "static bool ay_v9_boost_reuse = true;",
    "static unsigned int ay_nav_boost_pct = 82;",
    "static unsigned int ay_wake_boost_pct = 85;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
):
    assert term in cpu, term
for term in ("uint8_t DouTap_enable = 1;", "ts->gesture_enable = 1;"):
    assert term in touch, term
for term in (
    "static bool ay_v81_single_kswapd = true;",
    "if (READ_ONCE(ay_v81_single_kswapd) && kswapd_threads > 1)",
):
    assert term in multi, term
for term in ("static bool ay_v8_latency_watermarks = true;", "watermark_scale_factor > 50"):
    assert term in watermarks, term
for bad in ("policy->max =", "thermal_disable", "selinux_enforcing = 0"):
    assert bad not in s, bad

# Model only the additional-pass guard; does not attempt to simulate reclaim.
# Even if no direct allocator waits, 2nd pass is allowed only with positive
# progress and unbalanced zones, after full 1000ms rate-limit window.
def extra_pass(opt_in, old_unlimited, waiting, first_pass,
               progress, balanced, elapsed_ms, frozen=False, stopping=False):
    return (
        not frozen and not stopping and not old_unlimited and not waiting
        and opt_in and first_pass and progress and not balanced
        and elapsed_ms >= 1000
    )

cases = [
    ((True, False, False, True, True, False, 1000), True),
    ((True, False, False, False, True, False, 1000), False),
    ((True, False, False, True, False, False, 1000), False),
    ((True, False, False, True, True, True, 1000), False),
    ((True, False, False, True, True, False, 999), False),
    ((False, False, False, True, True, False, 1000), False),
    ((True, True, False, True, True, False, 1000), False),
    ((True, False, True, True, True, False, 1000), False),
]
for args, expected in cases:
    assert extra_pass(*args) is expected, (args, expected)
assert not extra_pass(True, False, False, True, True, False, 1000, frozen=True)
assert not extra_pass(True, False, False, True, True, False, 1000, stopping=True)
print("PASS: V9.1 max one guarded extra kswapd scan / >=1s rate limit")
print("PASS: waiter-zero vendor fallback, freeze/stop, old A/B switch, root opt-out")
print("PASS: V9 CPUBoost, DT2W, DeepDoze, single kswapd, watermark and thermal preserved")
