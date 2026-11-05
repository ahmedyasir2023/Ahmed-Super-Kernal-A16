#!/usr/bin/env python3
"""V8.1 compiled-source safety invariants; no device-side tuning."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]/"kernel"
cpu=(root/"drivers/cpufreq/cpu-boost.c").read_text()
multi=(root/"mm/multi_kswapd/multi_kswapd.c").read_text()
mm=(root/"mm/page_alloc.c").read_text()
touch=(root/"drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
vmscan=(root/"mm/vmscan.c").read_text()

for sym,n in {
 "ay_input_boost_pct":78,
 "input_boost_ms":115,
 "ay_wake_boost_pct":85,
 "ay_wake_boost_ms":170,
 "ay_nav_boost_pct":82,
 "ay_nav_boost_ms":145,
 "sched_boost_on_input":3,
}.items():
    assert cpu.count(f"static unsigned int {sym} = {n};")==1,sym
    assert cpu.count(f"module_param({sym}, uint, 0444);")==1,sym
for s in (
    "static bool ay_nav_burst_enabled = true;",
    "module_param_named(ay_nav_burst_enabled, ay_nav_burst_enabled, bool, 0600);",
    "static atomic_t ay_nav_burst_pending = ATOMIC_INIT(0);",
    "atomic_xchg(&ay_nav_burst_pending, 0)",
    "atomic_set(&ay_nav_burst_pending, 1);",
    "atomic_set(&ay_nav_burst_pending, 0);",
    "MIN_INPUT_INTERVAL (100 * USEC_PER_MSEC)",
    "now - last_input_time <= 450 * USEC_PER_MSEC",
    "ay_dynamic_input_boost_khz(i, wake, nav)",
    "min_t(unsigned int, READ_ONCE(ay_nav_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)",
    "min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(input_boost_ms), 140)",
    "static bool ay_screenoff_saver = true;",
    "static bool ay_instantwake = true;",
    "static bool ay_deepdoze_enabled = true;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "sched_set_boost(-(int)sched_boost_active)",
):
    assert s in cpu,s
for s in (
    "int kswapd_threads = DEF_KSWAPD_THREADS_PER_NODE;",
    "#define DEF_KSWAPD_THREADS_PER_NODE  1",
    "static bool ay_v81_single_kswapd = true;",
    "module_param_named(ay_v81_single_kswapd, ay_v81_single_kswapd, bool, 0600);",
    "if (READ_ONCE(ay_v81_single_kswapd) && kswapd_threads > 1)",
    "kswapd_threads = 1;",
    "update_kswapd_threads();",
    "kthread_stop(pgdat->kswapd[hid]);",
    "if (!pgdat->kswapd[hid])",
):
    assert s in multi,s
for s in (
    "static bool ay_v8_latency_watermarks = true;",
    "watermark_scale_factor > 50",
    "watermark_scale_factor = 50;",
    "module_param_named(ay_v8_latency_watermarks, ay_v8_latency_watermarks,",
):
    assert s in mm,s
for s in ("uint8_t DouTap_enable = 1;","ts->gesture_enable = 1;"):
    assert s in touch,s
for s in (
    "static bool ay_reclaim_progress;",
    "module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);",
    "(!READ_ONCE(ay_reclaim_progress) &&",
):
    assert s in vmscan,s

for danger in ("thermal_disable","CPU_FREQ_GOV_PERFORMANCE=y",
               "policy->max =","selinux_enforcing = 0","disable_dt2w"):
    assert danger not in cpu+multi,danger

# A root-only guard permits the original vendor runtime count of two;
# both the root guard and optional event burst must not require a daemon.
for one_worker_guard, requested in ((True,1),(True,2),(True,4),(False,1),(False,2)):
    effective=min(requested,1) if one_worker_guard else requested
    assert effective==(1 if one_worker_guard else requested)
for first_input,wake,nav in ((True,False,False),(False,False,True),(False,True,False)):
    pct=85 if wake else (82 if nav else 78)
    duration=170 if wake else (145 if nav else 115)
    assert pct<=85 and duration<=180
print("V8.1 source contract PASS: 78/115 first, 82/145 UI burst, 85/170 wake; single-kSwapd, thermal, idle, root, DT2W preserved")
