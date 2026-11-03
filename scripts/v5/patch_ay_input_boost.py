#!/usr/bin/env python3
"""V5 AY HyperSpeed: bounded automatic touch/input CPU frequency boost.

Apply one targeted change to the pinned Realme Atoll cpu-boost.c:
- use vendor's existing WALT/schedutil cpufreq boost infrastructure
- on touch/key input only, request ~60% of the current allowed policy range
- automatically undo boost after 90 ms, with the vendor's 150-ms debounce
- short restrained scheduler boost while active
- never exceed policy->max, bypass thermal limits, or force performance governor
- allow runtime adjustments through existing/new module parameters.

No change to SUSFS, KernelSU, GPU, dtbo, touch drivers, ZRAM or deep idle.
This is an experimental compile build: not proof of speedup and not flashable.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = root / "kernel/drivers/cpufreq/cpu-boost.c"
s = src.read_text()

def replace_exact(old: str, new: str) -> None:
    global s
    assert s.count(old) == 1, f"Unexpected original driver layout: {old[:90]!r}"
    s = s.replace(old, new, 1)

replace_exact(
    "static bool input_boost_enabled;\n\n"
    "static unsigned int input_boost_ms = 40;\n"
    "module_param(input_boost_ms, uint, 0644);\n\n"
    "static unsigned int sched_boost_on_input;\n"
    "module_param(sched_boost_on_input, uint, 0644);",
    """static bool input_boost_enabled;

/*
 * AY HyperSpeed: the vendor input boost had no frequencies configured by
 * default and was therefore inactive. Enable an adaptive boost on actual
 * input without requiring an Android init script or modifying the power HAL.
 * A disabled auto mode + zero manual frequencies restores stock behavior.
 */
static bool ay_auto_input_boost = true;
module_param(ay_auto_input_boost, bool, 0644);

/* Position in the active policy's allowed [cpuinfo.min, policy.max] range.
 * Runtime values are capped at 75%, avoiding permanent max-frequency pins.
 */
static unsigned int ay_input_boost_pct = 60;
module_param(ay_input_boost_pct, uint, 0644);

/* Original vendor duration: 40 ms. AY boosts briefly but more responsively;
 * never sustain boosts indefinitely, regardless of the runtime parameter.
 */
static unsigned int input_boost_ms = 90;
module_param(input_boost_ms, uint, 0644);

/* WALT restrained boost (3): only for the bounded input window; unlike
 * FULL_THROTTLE_BOOST (1), this does not force the big CPU cluster online.
 */
static unsigned int sched_boost_on_input = 3;
module_param(sched_boost_on_input, uint, 0644);"""
)

anchor = "static void do_input_boost(struct work_struct *work)\n{\n"
dynamic_function = """/* Compute an input boost on demand, after the CPUFreq policy exists.
 * Use only existing driver-supported frequencies; never overclock.
 */
static unsigned int ay_dynamic_input_boost_khz(unsigned int cpu)
{
    struct cpufreq_policy *policy;
    unsigned int pct, min_freq, max_freq, target = 0;

    if (!READ_ONCE(ay_auto_input_boost))
        return 0;

    policy = cpufreq_cpu_get(cpu);
    if (!policy)
        return 0;

    min_freq = policy->cpuinfo.min_freq;
    max_freq = policy->max;
    pct = min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 75);

    if (max_freq > min_freq && pct)
        target = min_freq + (max_freq - min_freq) * pct / 100;

    cpufreq_cpu_put(policy);
    return target;
}

"""
replace_exact(anchor, dynamic_function + anchor)

replace_exact(
    "\t\ti_sync_info->input_boost_min = i_sync_info->input_boost_freq;",
    "\t\t/* Explicit per-CPU frequencies override the adaptive default. */\n"
    "\t\ti_sync_info->input_boost_min = i_sync_info->input_boost_freq ?: \n"
    "\t\t\tay_dynamic_input_boost_khz(i);"
)
replace_exact(
    "\t\t\t\t\tmsecs_to_jiffies(input_boost_ms));",
    "\t\t\t\t\tmsecs_to_jiffies(min_t(unsigned int,\n"
    "\t\t\t\t\t\tREAD_ONCE(input_boost_ms), 120)));"
)
replace_exact(
    "\tif (!input_boost_enabled)\n\t\treturn;\n\n"
    "\tnow = ktime_to_us(ktime_get());",
    """\tif (!READ_ONCE(input_boost_enabled) &&
\t    !READ_ONCE(ay_auto_input_boost))
\t\treturn;

\t/* Skip synchronization packets and key releases to avoid idle work. */
\tif (type == EV_SYN || (type == EV_KEY && !value))
\t\treturn;

\tnow = ktime_to_us(ktime_get());"""
)

# The original normal processing, 150-ms debounce, worker lifetime, hardware
# boost framework and cpufreq policy notifier must all remain intact.
required = [
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_update_policy(i);",
    "queue_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "#define MIN_INPUT_INTERVAL (150 * USEC_PER_MSEC)",
    "cpufreq_register_notifier(&boost_adjust_nb, CPUFREQ_POLICY_NOTIFIER);",
    "input_register_handler(&cpuboost_input_handler)",
    "static unsigned int sched_boost_on_input = 3;",
    "static unsigned int input_boost_ms = 90;",
    "static unsigned int ay_input_boost_pct = 60;",
    "min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 75)",
    "cpufreq_cpu_put(policy);",
    "if (type == EV_SYN || (type == EV_KEY && !value))",
]
for symbol in required:
    assert symbol in s, symbol
assert "static unsigned int input_boost_ms = 40;" not in s
assert "static unsigned int sched_boost_on_input;" not in s
src.write_text(s)
print("AY HyperSpeed adaptive input boost applied to vendor CPUFREQ driver")
print("Input boost = 60% of allowed CPU policy range, <=90ms by default, <=120ms hard cap")
print("Original WALT/schedutil, thermal, DT2W, SU and suspend behavior preserved")
