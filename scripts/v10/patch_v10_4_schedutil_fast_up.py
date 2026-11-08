#!/usr/bin/env python3
"""V10.4: bounded schedutil upward response, with a root-only runtime rollback.

The Atoll schedutil implementation applies a minimum rate gate before it knows
whether the next frequency is an up or down transition. V10.4 makes that
minimum gate aware of a bounded upward-only delay cap, then applies the same
cap to the upward transition check. Downward rate limiting is unchanged.

The cap can only reduce the existing upward delay to at most 250 us. It never
raises frequency limits, changes OPP tables, bypasses thermal policy, adds a
timer/work item, or alters screen-off/DeepDoze behavior.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / "kernel/sched/cpufreq_schedutil.c"
s = source.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    assert old != new and s.count(old) == 1, (
        "V10.4 source contract failed at " + label +
        "; matches=" + str(s.count(old))
    )
    s = s.replace(old, new, 1)


one(
    "#include <linux/sched/sysctl.h>\n",
    "#include <linux/sched/sysctl.h>\n#include <linux/moduleparam.h>\n",
    "explicit module parameter declarations",
)

one(
    "static unsigned int stale_ns;\n"
    "static DEFINE_PER_CPU(struct sugov_tunables *, cached_tunables);\n",
    "static unsigned int stale_ns;\n"
    "static DEFINE_PER_CPU(struct sugov_tunables *, cached_tunables);\n"
    "\n"
    "/* V10.4: cap only upward schedutil rate limiting; root can disable it. */\n"
    "#define AY_V10_4_FAST_UP_CAP_US 250\n"
    "static bool ay_v10_4_schedutil_fast_up = true;\n"
    "module_param_named(ay_v10_4_schedutil_fast_up, ay_v10_4_schedutil_fast_up, bool, 0600);\n"
    "MODULE_PARM_DESC(ay_v10_4_schedutil_fast_up,\n"
    "\t\t "1: cap upward schedutil delay at 250us; 0: vendor rate limits");\n",
    "root-only V10.4 fast-up parameter",
)

one(
    "/************************ Governor internals ***********************/\n\n"
    "static bool sugov_should_update_freq(struct sugov_policy *sg_policy, u64 time)\n"
    "{\n"
    "\ts64 delta_ns;\n",
    "/************************ Governor internals ***********************/\n\n"
    "static inline s64 sugov_effective_up_rate_delay_ns(\n"
    "\t\tstruct sugov_policy *sg_policy)\n"
    "{\n"
    "\ts64 delay_ns = sg_policy->up_rate_delay_ns;\n"
    "\n"
    "\tif (READ_ONCE(ay_v10_4_schedutil_fast_up))\n"
    "\t\tdelay_ns = min_t(s64, delay_ns,\n"
    "\t\t\t\t (s64)AY_V10_4_FAST_UP_CAP_US * NSEC_PER_USEC);\n"
    "\n"
    "\treturn delay_ns;\n"
    "}\n\n"
    "static bool sugov_should_update_freq(struct sugov_policy *sg_policy, u64 time)\n"
    "{\n"
    "\ts64 delta_ns;\n"
    "\ts64 min_rate_limit_ns;\n",
    "effective upward rate helper and pre-computation gate",
)

one(
    "\tdelta_ns = time - sg_policy->last_freq_update_time;\n"
    "\treturn delta_ns >= sg_policy->min_rate_limit_ns;\n"
    "}\n\n"
    "static bool sugov_up_down_rate_limit(struct sugov_policy *sg_policy, u64 time,\n"
    "\t\t\t\t     unsigned int next_freq)\n"
    "{\n"
    "\ts64 delta_ns;\n",
    "\tdelta_ns = time - sg_policy->last_freq_update_time;\n"
    "\tif (READ_ONCE(ay_v10_4_schedutil_fast_up)) {\n"
    "\t\tmin_rate_limit_ns = min(sugov_effective_up_rate_delay_ns(sg_policy),\n"
    "\t\t\t\t\t sg_policy->down_rate_delay_ns);\n"
    "\t\treturn delta_ns >= min_rate_limit_ns;\n"
    "\t}\n"
    "\treturn delta_ns >= sg_policy->min_rate_limit_ns;\n"
    "}\n\n"
    "static bool sugov_up_down_rate_limit(struct sugov_policy *sg_policy, u64 time,\n"
    "\t\t\t\t     unsigned int next_freq)\n"
    "{\n"
    "\ts64 delta_ns;\n"
    "\ts64 up_rate_delay_ns;\n",
    "direction-aware pre-computation gate",
)

one(
    "\tdelta_ns = time - sg_policy->last_freq_update_time;\n\n"
    "#ifdef OPLUS_FEATURE_UIFIRST\n"
    "\t// XuHaifeng@BSP.KERNEL.PERFORMANCE, 2020/08/18, Add for UIFirst(slide boost)\n"
    "\tif (sg_policy->flags & SCHED_CPUFREQ_BOOST)\n"
    "\t\treturn false;\n"
    "#endif\n\n"
    "\tif (next_freq > sg_policy->next_freq &&\n"
    "\t    delta_ns < sg_policy->up_rate_delay_ns)\n",
    "\tdelta_ns = time - sg_policy->last_freq_update_time;\n"
    "\tup_rate_delay_ns = sugov_effective_up_rate_delay_ns(sg_policy);\n\n"
    "#ifdef OPLUS_FEATURE_UIFIRST\n"
    "\t// XuHaifeng@BSP.KERNEL.PERFORMANCE, 2020/08/18, Add for UIFirst(slide boost)\n"
    "\tif (sg_policy->flags & SCHED_CPUFREQ_BOOST)\n"
    "\t\treturn false;\n"
    "#endif\n\n"
    "\tif (next_freq > sg_policy->next_freq &&\n"
    "\t    delta_ns < up_rate_delay_ns)\n",
    "upward transition delay cap",
)

assert "delta_ns < sg_policy->down_rate_delay_ns" in s
assert "sg_policy->down_rate_delay_ns);" in s
assert s.count("static bool ay_v10_4_schedutil_fast_up = true;") == 1
assert s.count("AY_V10_4_FAST_UP_CAP_US 250") == 1

source.write_text(s)
print("V10.4: schedutil upward rate delay capped at 250us (root-only runtime opt-out).")
print("V10.4: down-rate delay, frequency limits, OPPs, thermal policy and power-state code unchanged.")
