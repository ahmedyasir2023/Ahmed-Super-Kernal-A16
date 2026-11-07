#!/usr/bin/env python3
"""V10.2: refresh each shared CPUFreq policy once, not once per online CPU.

The vendor helper iterates all online CPUs and calls cpufreq_update_policy()
for each. On a shared-policy SoC, several CPUs point to the same policy, so
the same CPUFREQ_ADJUST notifier and governor limit update can be repeated.
V10.2 deduplicates by policy->cpu while holding the policy read semaphore,
then calls cpufreq_update_policy() once per distinct policy leader.

A root-only opt-out restores the exact original per-online-CPU loop.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/cpufreq/cpu-boost.c"
s = driver.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    assert old != new and s.count(old) == 1, (
        "V10.2 source contract failed at " + label +
        "; matches=" + str(s.count(old))
    )
    s = s.replace(old, new, 1)


one(
    "#include <linux/cpu.h>\n",
    "#include <linux/cpu.h>\n#include <linux/cpumask.h>\n#include <linux/rwsem.h>\n",
    "cpumask and policy semaphore headers",
)

one(
    "static unsigned long ay_v10_boost_expires;\n",
    "static unsigned long ay_v10_boost_expires;\n"
    "/* Root-only fallback to the vendor per-online-CPU refresh loop. */\n"
    "static bool ay_v10_policy_dedup = true;\n"
    "module_param_named(ay_v10_policy_dedup, ay_v10_policy_dedup, bool, 0600);\n",
    "V10.2 reversible policy-dedup switch",
)

old = """static void update_policy_online(void)
{
\tunsigned int i;

\t/* Re-evaluate policy to trigger adjust notifier for online CPUs */
\tget_online_cpus();
\tfor_each_online_cpu(i) {
\t\tpr_debug("Updating policy for CPU%d\\n", i);
\t\tcpufreq_update_policy(i);
\t}
\tput_online_cpus();
}
"""
new = """static void update_policy_online(void)
{
\tunsigned int i;
\tcpumask_t updated;

\t/*
\t * The vendor loop refreshes a shared CPUFreq policy once for every
\t * online CPU in that policy. Only the policy leader needs one update:
\t * CPUFREQ_ADJUST applies to the complete shared policy.
\t *
\t * Keep the original loop available as a root-only rollback.
\t */
\tget_online_cpus();
\tif (!READ_ONCE(ay_v10_policy_dedup)) {
\t\tfor_each_online_cpu(i) {
\t\t\tpr_debug("Updating policy for CPU%d\\n", i);
\t\t\tcpufreq_update_policy(i);
\t\t}
\t\tput_online_cpus();
\t\treturn;
\t}

\tcpumask_clear(&updated);
\tfor_each_online_cpu(i) {
\t\tstruct cpufreq_policy *policy;
\t\tunsigned int policy_cpu = i;

\t\tif (cpumask_test_cpu(i, &updated))
\t\t\tcontinue;

\t\tpolicy = cpufreq_cpu_get(i);
\t\tif (policy) {
\t\t\tdown_read(&policy->rwsem);
\t\t\tpolicy_cpu = policy->cpu;
\t\t\tup_read(&policy->rwsem);
\t\t\tcpufreq_cpu_put(policy);
\t\t}

\t\tif (policy_cpu >= nr_cpu_ids)
\t\t\tpolicy_cpu = i;

\t\tif (cpumask_test_cpu(policy_cpu, &updated)) {
\t\t\tcpumask_set_cpu(i, &updated);
\t\t\tcontinue;
\t\t}

\t\tcpumask_set_cpu(policy_cpu, &updated);
\t\tcpumask_set_cpu(i, &updated);
\t\tpr_debug("Updating shared policy via CPU%d\\n", policy_cpu);
\t\tcpufreq_update_policy(policy_cpu);
\t}
\tput_online_cpus();
}
"""
one(old, new, "deduplicate shared policy updates")

for required in (
    "#include <linux/cpumask.h>",
    "#include <linux/rwsem.h>",
    "static bool ay_v10_policy_dedup = true;",
    "module_param_named(ay_v10_policy_dedup, ay_v10_policy_dedup, bool, 0600);",
    "cpumask_t updated;",
    "cpufreq_cpu_get(i)",
    "down_read(&policy->rwsem)",
    "policy_cpu = policy->cpu;",
    "up_read(&policy->rwsem)",
    "cpufreq_cpu_put(policy);",
    "cpufreq_update_policy(policy_cpu);",
    "cpufreq_update_policy(i);",
):
    assert required in s, required

fn = s[s.index("static void update_policy_online(void)"):
       s.index("static void do_input_boost_rem(struct work_struct *work)")]
assert fn.count("get_online_cpus();") == 1
assert fn.count("put_online_cpus();") == 2
assert fn.count("cpufreq_update_policy(i);") == 1
assert fn.count("cpufreq_update_policy(policy_cpu);") == 1
assert fn.index("cpufreq_cpu_get(i)") < fn.index("down_read(&policy->rwsem)") < fn.index("up_read(&policy->rwsem)") < fn.index("cpufreq_cpu_put(policy);") < fn.index("cpufreq_update_policy(policy_cpu);")

for forbidden in (
    "pm_stay_awake(", "pm_wakeup_event(", "wake_lock(",
    "thermal_disable", "selinux_enforcing = 0", "policy->max =",
):
    assert forbidden not in s, forbidden

driver.write_text(s)
print("V10.2: one CPUFreq refresh per shared policy, with root-only vendor-loop rollback.")
print("V10.2: no frequency values, boost windows, thermal limits, screen-off or DeepDoze changes.")
