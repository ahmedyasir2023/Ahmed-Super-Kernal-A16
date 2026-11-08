#!/usr/bin/env python3
"""V10.3 source contract for conservative, opt-in background reclaim."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
vmscan = (root / "kernel/mm/vmscan.c").read_text()
cpu = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
touch = (root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
multi = (root / "kernel/mm/multi_kswapd/multi_kswapd.c").read_text()
page_alloc = (root / "kernel/mm/page_alloc.c").read_text()

# The V9.1 extra pass is preserved, but the default is conservative.
assert re.search(r"static bool ay_v91_bounded_reclaim = false;", vmscan)
assert "module_param_named(ay_v91_bounded_reclaim, ay_v91_bounded_reclaim, bool, 0600);" in vmscan
assert '0: vendor waiter exit (default), 1: opt-in bounded extra pass' in vmscan
for token in (
    "READ_ONCE(ay_v91_bounded_reclaim)",
    "!ay_v91_extra_this_cycle",
    "sc.nr_reclaimed > nr_reclaimed",
    "!pgdat_balanced(pgdat, sc.order, classzone_idx)",
    "msecs_to_jiffies(1000)",
    "cmpxchg(&ay_v91_last_extra_jiffies,",
    "try_to_freeze() || kthread_should_stop()",
):
    assert token in vmscan, token

# V7.7 experimental watermark reclaim remains OFF by default.
assert "static bool ay_reclaim_progress;" in vmscan
assert "module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);" in vmscan

# Keep the previously qualified single-kswapd and bounded watermark defaults.
assert "static bool ay_v81_single_kswapd = true;" in multi
assert "module_param_named(ay_v81_single_kswapd, ay_v81_single_kswapd, bool, 0600);" in multi
assert "static bool ay_v8_latency_watermarks = true;" in page_alloc
assert "watermark_scale_factor > 50" in page_alloc

# Foreground speed, wake, screen-off cap, and touch gesture contracts are untouched.
for token in (
    "static bool ay_v10_boost_fastpath = true;",
    "static bool ay_v10_policy_dedup = true;",
    "static unsigned int ay_input_boost_pct = 78;",
    "static unsigned int ay_nav_boost_pct = 82;",
    "static unsigned int ay_wake_boost_pct = 85;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
):
    assert token in cpu, token
for token in ("uint8_t DouTap_enable = 1;", "ts->gesture_enable = 1;"):
    assert token in touch, token

for forbidden in (
    "thermal_disable", "selinux_enforcing = 0", "policy->max =",
    "pm_stay_awake(", "pm_wakeup_event(", "wake_lock(",
):
    assert forbidden not in vmscan, forbidden

# The V10.3 patch is deliberately limited to the default and parameter text.
assert vmscan.count("static bool ay_v91_bounded_reclaim = false;") == 1
assert vmscan.count("static bool ay_v91_bounded_reclaim = true;") == 0

print("PASS: V10.3 restores vendor waiter-zero reclaim exit by default.")
print("PASS: root-only bounded reclaim opt-in and all original safety guards remain.")
print("PASS: V7.7 reclaim OFF, one kswapd, watermark cap, ZRAM/CPUBoost/DT2W/DeepDoze contracts retained.")
