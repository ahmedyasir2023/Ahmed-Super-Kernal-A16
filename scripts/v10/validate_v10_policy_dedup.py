#!/usr/bin/env python3
"""V10.2 source and deterministic policy-domain deduplication checks."""
from pathlib import Path

cpu = (Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
fn = cpu[cpu.index("static void update_policy_online(void)"):
         cpu.index("static void do_input_boost_rem(struct work_struct *work)")]

for token in (
    "#include <linux/cpumask.h>",
    "#include <linux/rwsem.h>",
    "static bool ay_v10_policy_dedup = true;",
    "module_param_named(ay_v10_policy_dedup, ay_v10_policy_dedup, bool, 0600);",
    "cpumask_t updated;",
    "cpumask_clear(&updated);",
    "cpumask_test_cpu(i, &updated)",
    "cpufreq_cpu_get(i)",
    "down_read(&policy->rwsem)",
    "policy_cpu = policy->cpu;",
    "up_read(&policy->rwsem)",
    "cpufreq_cpu_put(policy);",
    "cpumask_set_cpu(policy_cpu, &updated);",
    "cpufreq_update_policy(policy_cpu);",
    "if (!READ_ONCE(ay_v10_policy_dedup))",
    "cpufreq_update_policy(i);",
    "get_online_cpus();",
    "put_online_cpus();",
):
    assert token in cpu if token.startswith("#include") or token.startswith("static bool") or token.startswith("module_param") else token in fn, token

assert fn.count("get_online_cpus();") == 1
assert fn.count("put_online_cpus();") == 2
assert fn.count("cpufreq_update_policy(i);") == 1
assert fn.count("cpufreq_update_policy(policy_cpu);") == 1
assert fn.index("get_online_cpus();") < fn.index("if (!READ_ONCE(ay_v10_policy_dedup))")
assert fn.index("cpufreq_cpu_get(i)") < fn.index("down_read(&policy->rwsem)") < fn.index("up_read(&policy->rwsem)") < fn.index("cpufreq_cpu_put(policy);") < fn.index("cpufreq_update_policy(policy_cpu);")

# The observed RMX2170 topology has two shared CPUFreq policies (little
# policy leader 0 and big policy leader 6). Model all-online and partial-online
# sets; the dedup path must update each present policy exactly once.
leaders = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:6, 7:6}
def updates(online):
    seen = set()
    out = []
    for cpu_id in sorted(online):
        if cpu_id in seen:
            continue
        leader = leaders[cpu_id]
        if leader in seen:
            seen.add(cpu_id)
            continue
        seen.add(leader)
        seen.add(cpu_id)
        out.append(leader)
    return out

assert updates(set(range(8))) == [0, 6]
assert updates({1, 2, 4, 6, 7}) == [0, 6]
assert updates({1, 2, 3}) == [0]
assert updates({7}) == [6]
assert updates({0, 6}) == [0, 6]

# Previous V10/V9 safety contracts must remain in the same driver.
for token in (
    "static bool ay_v10_boost_fastpath = true;",
    "static DEFINE_SPINLOCK(ay_v10_boost_state_lock);",
    "time_before(jiffies, ay_v10_boost_expires)",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
):
    assert token in cpu, token

for forbidden in (
    "pm_stay_awake(", "pm_wakeup_event(", "wake_lock(",
    "thermal_disable", "selinux_enforcing = 0", "policy->max =",
):
    assert forbidden not in cpu, forbidden

print("PASS: V10.2 shared-policy refresh deduplication and topology model")
print("PASS: original vendor per-CPU update loop retained behind root-only opt-out")
print("PASS: V10.1 boost expiry, DeepDoze, CPUFreq bounds and safety contracts retained")
