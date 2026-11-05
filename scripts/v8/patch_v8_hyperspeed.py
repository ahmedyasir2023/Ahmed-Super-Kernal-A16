#!/usr/bin/env python3
"""Ahmed Super Kernal A16 V8 HyperSpeed -- narrow, reversible kernel changes.

Apply after the COMPLETE pinned V7.7 patch chain and before compilation:
  * Short, higher touch/wake boosts within the vendor's existing caps.
  * Screen-on responsiveness: no continuous max-frequency/performance governor.
  * Keep the proven 600-second DeepDoze and panel transitions untouched.
  * Cap the ROM's excessive runtime watermark request of 200 to 50; owner
    measured 70.69->45.46->76.51% memory-full PSI in a 200/50/200 reversal.
    This is a partial measured improvement, NOT a proven full remedy.
  * Opt-out is an explicit root-only module bool; without opt-out no scripts
    or module managers are needed. No changes to LMKD, ZRAM, kswapd threads.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
boost_file = root / "kernel/drivers/cpufreq/cpu-boost.c"
memory_file = root / "kernel/mm/page_alloc.c"
boost = boost_file.read_text()
memory = memory_file.read_text()

def one(text: str, old: str, new: str, label: str) -> str:
    assert text.count(old) == 1, "Unexpected pinned V7.7 source: " + label
    assert old != new
    return text.replace(old, new, 1)

boost_defaults = {
    "ay_input_boost_pct": (72, 78),
    "input_boost_ms": (105, 115),
    "ay_wake_boost_pct": (82, 85),
    "ay_wake_boost_ms": (155, 170),
}
for key, (old, new) in boost_defaults.items():
    boost = one(boost,
        f"static unsigned int {key} = {old};",
        f"static unsigned int {key} = {new};",
        "boost parameter "+key)
    assert boost.count(f"module_param({key}, uint, 0444);") == 1

# Lower the vendor 150ms event debounce to 100ms so consecutive real taps
# and launcher swipes can refresh the bounded 115ms boost; no periodic loop.
boost = one(boost,
    "#define MIN_INPUT_INTERVAL (150 * USEC_PER_MSEC)",
    "#define MIN_INPUT_INTERVAL (100 * USEC_PER_MSEC)",
    "touch event reboost interval")

# The original run-time sysctl handler is how EvolutionX/vendor init requests
# factor=200. The guard changes ONLY requests above 50 while it is active.
# An emergency root-only opt-out is possible (not applied automatically).
# Kernel's original boot default 10 remains unchanged.
memory = one(memory,
    "int watermark_scale_factor = 10;\n",
    """int watermark_scale_factor = 10;

/* AY V8: bound excessive high-watermarks for responsive app launching.
 * Owner-observed factor 50 is only a partial improvement vs factor 200.
 * This is reversible at runtime with root, without flashing a new kernel.
 * Both values still pass through the standard zone watermark calculation.
 */
static bool ay_v8_latency_watermarks = true;
module_param_named(ay_v8_latency_watermarks, ay_v8_latency_watermarks,
                   bool, 0600);
MODULE_PARM_DESC(ay_v8_latency_watermarks,
                 "1: cap userspace watermark scale requests to 50, 0: stock sysctl");
""",
    "root-only guard declaration")

memory = one(memory,
    "int watermark_scale_factor_sysctl_handler(struct ctl_table *table, int write,\n"
    "\tvoid __user *buffer, size_t *length, loff_t *ppos)\n"
    "{\n"
    "\tint rc;\n\n"
    "\trc = proc_dointvec_minmax(table, write, buffer, length, ppos);\n"
    "\tif (rc)\n"
    "\t\treturn rc;\n\n"
    "\tif (write)\n"
    "\t\tsetup_per_zone_wmarks();\n\n"
    "\treturn 0;\n"
    "}\n",
    """int watermark_scale_factor_sysctl_handler(struct ctl_table *table, int write,
\tvoid __user *buffer, size_t *length, loff_t *ppos)
{
\tint rc;

\trc = proc_dointvec_minmax(table, write, buffer, length, ppos);
\tif (rc)
\t\treturn rc;

\tif (write) {
\t\t/* V8 reduces unnecessary kswapd CPU pressure caused by very
\t\t * high vendor watermarks. Do not override low user requests.
\t\t * Disabling ay_v8_latency_watermarks restores stock behavior.
\t\t */
\t\tif (READ_ONCE(ay_v8_latency_watermarks) &&
\t\t    watermark_scale_factor > 50)
\t\t\twatermark_scale_factor = 50;
\t\tsetup_per_zone_wmarks();
\t}

\treturn 0;
}
""",
    "bounded sysctl adjustment")

for required in (
    "static bool ay_screenoff_saver = true;",
    "static bool ay_instantwake = true;",
    "static bool ay_deepdoze_enabled = true;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "static unsigned int sched_boost_on_input = 3;",
    "pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78)",
    "min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)",
    "min_t(unsigned int, READ_ONCE(input_boost_ms), 140)",
):
    assert required in boost, required
for forbidden in ("thermal_disable", "selinux_enforcing = 0", "policy->max =", "CPU_FREQ_GOV_PERFORMANCE=y"):
    assert forbidden not in boost, forbidden

# Do not write partial files on invalid source.
boost_file.write_text(boost)
memory_file.write_text(memory)
print("AY Super Kernal A16 V8 HyperSpeed staged")
print("Input: 78% 115ms; wake: 85% 170ms; WALT sched boost unchanged at 3")
print("Vendor sysctl 200 capped at 50; root-only opt-out, no boot scripts")
print("DeepDoze 600s, DT2W, fingerprint, KSU Next and thermal unchanged")
