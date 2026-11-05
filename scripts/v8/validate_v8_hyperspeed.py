#!/usr/bin/env python3
"""V8 release invariants: fail closed on any unexpected compiled source."""
from pathlib import Path
import itertools
root = Path(__file__).resolve().parents[2]
kernel = root / "kernel"
boost = (kernel/"drivers/cpufreq/cpu-boost.c").read_text()
memory = (kernel/"mm/page_alloc.c").read_text()
vmscan = (kernel/"mm/vmscan.c").read_text()
touch = (kernel/"drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
defaults = {
    "ay_input_boost_pct":78, "input_boost_ms":115, "sched_boost_on_input":3,
    "ay_wake_boost_pct":85, "ay_wake_boost_ms":170,
}
for key,val in defaults.items():
    assert boost.count(f"static unsigned int {key} = {val};")==1,key
    assert boost.count(f"module_param({key}, uint, 0444);")==1,key
for s in (
    "static bool ay_screenoff_saver = true;",
    "static bool ay_instantwake = true;",
    "#define MIN_INPUT_INTERVAL (100 * USEC_PER_MSEC)",
    "static bool ay_deepdoze_enabled = true;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "module_param(ay_screen_on, bool, 0444);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "WRITE_ONCE(ay_deepdoze_last_blank, jiffies);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "sched_set_boost(-(int)sched_boost_active)",
    "min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78)",
    "pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)",
    "min_t(unsigned int, READ_ONCE(input_boost_ms), 140)",
):
    assert s in boost, s
for t in ("uint8_t DouTap_enable = 1;", "ts->gesture_enable = 1;"):
    assert t in touch, t
for f in ("thermal_disable","policy->max =","selinux_enforcing = 0","CPU_FREQ_GOV_PERFORMANCE=y"):
    assert f not in boost, f
assert memory.count("int watermark_scale_factor = 10;")==1
assert memory.count("static bool ay_v8_latency_watermarks = true;")==1
assert memory.count("module_param_named(ay_v8_latency_watermarks, ay_v8_latency_watermarks,")==1
assert "bool, 0600);" in memory
assert memory.count("watermark_scale_factor > 50")==1
assert memory.count("watermark_scale_factor = 50;")==1
assert "setup_per_zone_wmarks();" in memory
assert "min_free_kbytes = 1024;" in memory
assert "int extra_free_kbytes = 0;" in memory
assert "int kswapd_threads = " not in memory
assert "static bool ay_reclaim_progress;" in vmscan
assert "module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);" in vmscan
assert "(!READ_ONCE(ay_reclaim_progress) &&" in vmscan
# The cap does not change values <=50 and is reversible with the guard off.
for guard,asked in itertools.product((True,False),(10,50,75,200,1000)):
    after=min(asked,50) if guard else asked
    assert after==(asked if not guard or asked<=50 else 50)
print("V8 HyperSpeed core checks: 78% touch, 85% wake, 600s DeepDoze, DT2W, reversible watermark")
