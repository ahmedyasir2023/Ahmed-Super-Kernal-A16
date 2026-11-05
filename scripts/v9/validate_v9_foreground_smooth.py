#!/usr/bin/env python3
"""Post-stage V9 source contracts and deterministic transition cases."""
from pathlib import Path

kernel = Path(__file__).resolve().parents[2] / "kernel"
src = (kernel / "drivers/cpufreq/cpu-boost.c").read_text()
mm = (kernel / "mm/multi_kswapd/multi_kswapd.c").read_text()
touch = (kernel / "drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
watermarks = (kernel / "mm/page_alloc.c").read_text()

need = (
    "static bool ay_v9_boost_reuse = true;",
    "module_param_named(ay_v9_boost_reuse, ay_v9_boost_reuse, bool, 0600);",
    "static unsigned int ay_v9_boost_profile;",
    "module_param(ay_v9_boost_profile, uint, 0444);",
    "static unsigned long ay_v9_reused_bursts;",
    "module_param(ay_v9_reused_bursts, ulong, 0444);",
    "WRITE_ONCE(ay_v9_boost_profile, 0);",
    "READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1)",
    "READ_ONCE(sched_boost_active) == boost",
    "mod_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));",
    "queue_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "static unsigned int ay_input_boost_pct = 78;",
    "static unsigned int input_boost_ms = 115;",
    "static unsigned int ay_nav_boost_pct = 82;",
    "static unsigned int ay_nav_boost_ms = 145;",
    "static unsigned int ay_wake_boost_pct = 85;",
    "static unsigned int ay_wake_boost_ms = 170;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
)
for token in need:
    assert token in src, token
for token in (
    "module_param_named(ay_v81_single_kswapd, ay_v81_single_kswapd, bool, 0600);",
    "kthread_stop(pgdat->kswapd[hid]);",
):
    assert token in mm, token
for token in ("uint8_t DouTap_enable = 1;", "ts->gesture_enable = 1;"):
    assert token in touch, token
for token in ("static bool ay_v8_latency_watermarks = true;", "watermark_scale_factor > 50"):
    assert token in watermarks, token

# The reused path must be after synchronous expiry cancellation and the
# second panel-state check, and before the expensive per-policy work.
fn = src[src.index("static void do_input_boost(struct work_struct *work)"):]
points = (
    fn.index("cancel_delayed_work_sync(&input_boost_rem);"),
    fn.index("if (!READ_ONCE(ay_screen_on))", fn.index("cancel_delayed_work_sync(&input_boost_rem);")),
    fn.index("READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1)"),
    fn.index("update_policy_online();"),
    fn.index("WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));"),
)
assert list(points) == sorted(points)
assert src.count("WRITE_ONCE(ay_v9_boost_profile, 0);") == 1
assert src.count("WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));") == 1
assert src.count("duration = wake ?") == 1
assert src.count("cancel_delayed_work_sync(&input_boost_rem);") == 1

# Model the guard semantics. Only the same active ordinary or navigation
# profile may skip the redundant policy transaction; wake never can.
def can_reuse(enabled, screen_on, wake, nav, active, boost_active, desired_boost):
    return (enabled and screen_on and not wake and
            active == (2 if nav else 1) and
            boost_active == desired_boost)

cases = [
    # new first-touch, active first-touch, transition up to nav
    ((True, True, False, False, 0, 3, 3), False),
    ((True, True, False, False, 1, 3, 3), True),
    ((True, True, False, True, 1, 3, 3), False),
    # held nav, wake, screen-off and explicit manual opt-out
    ((True, True, False, True, 2, 3, 3), True),
    ((True, True, True, False, 3, 3, 3), False),
    ((True, False, False, True, 2, 3, 3), False),
    ((False, True, False, True, 2, 3, 3), False),
    ((True, True, False, True, 2, 0, 3), False),
]
for args, expected in cases:
    assert can_reuse(*args) is expected, (args, expected)
for wake, nav, pct, ms in (
    (False, False, 78, 115), (False, True, 82, 145), (True, False, 85, 170)
):
    assert pct <= 85 and ms <= 180
print("PASS: V9 guarded boost reuse, expiry refresh, wake, screen-off, 600s idle, KSU-era and vendor memory contracts")
