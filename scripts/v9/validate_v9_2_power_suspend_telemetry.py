#!/usr/bin/env python3
"""V9.2 source-contract checks for passive PM suspend-cycle telemetry.

Static validation only: this does not prove real suspend residency, wake-source
quality, battery savings, or device bootability.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
patch = (root / "scripts/v9/patch_v9_2_power_suspend_telemetry.py").read_text()
cpu = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()

for token in (
    "#include <linux/atomic.h>",
    "#include <linux/ktime.h>",
    "#include <linux/timekeeping.h>",
    "#include <linux/suspend.h>",
    "static atomic64_t ay_pm_prepare_events = ATOMIC64_INIT(0);",
    "static atomic64_t ay_pm_post_events = ATOMIC64_INIT(0);",
    "static atomic64_t ay_pm_unmatched_post_events = ATOMIC64_INIT(0);",
    "static atomic64_t ay_pm_last_cycle_ms = ATOMIC64_INIT(0);",
    "static atomic64_t ay_pm_max_cycle_ms = ATOMIC64_INIT(0);",
    "static atomic64_t ay_pm_total_cycle_ms = ATOMIC64_INIT(0);",
    "case PM_SUSPEND_PREPARE:",
    "case PM_POST_SUSPEND:",
    "ktime_get_boottime()",
    "ktime_ms_delta(",
    "atomic_xchg(&ay_pm_cycle_pending, 0)",
    "atomic64_cmpxchg(&ay_pm_max_cycle_ms",
    "register_pm_notifier(&ay_pm_suspend_nb)",
    'proc_create("ay_power_suspend_status", 0444',
    "pm_last_prepare_to_post_boottime_ms=",
    "pm_max_prepare_to_post_boottime_ms=",
    "pm_total_prepare_to_post_boottime_ms=",
    "elapsed_semantics=PM_SUSPEND_PREPARE_to_PM_POST_SUSPEND_CLOCK_BOOTTIME",
    "suspend_success_semantics=use_kernel_suspend_stats_not_this_notifier",
    r'pr_warn("V9.2 PM suspend telemetry registration failed: %d\n",',
    r'pr_warn("V9.2 read-only suspend status endpoint unavailable\n");',
):
    assert token in cpu, f"Missing V9.2 source contract: {token}"

assert cpu.count("case PM_SUSPEND_PREPARE:") == 1
assert cpu.count("case PM_POST_SUSPEND:") == 1
assert cpu.count("register_pm_notifier(&ay_pm_suspend_nb)") == 1
assert cpu.count('proc_create("ay_power_suspend_status", 0444') == 1

start = cpu.index("/*\n * V9.2 passive suspend-cycle telemetry.")
end = cpu.index("#endif /* CONFIG_PROC_FS */", start) + len("#endif /* CONFIG_PROC_FS */")
telemetry = cpu[start:end]

for forbidden in (
    "queue_work(",
    "mod_delayed_work(",
    "schedule_work(",
    "schedule_delayed_work(",
    "cpufreq_update_policy(",
    "cpufreq_verify_within_limits(",
    "pm_stay_awake(",
    "pm_wakeup_event(",
    "wake_lock(",
    "msleep(",
    "schedule_timeout(",
    "sched_set_boost(",
):
    assert forbidden not in telemetry, f"Power observer must remain passive: {forbidden}"

fops_start = cpu.index("static const struct file_operations ay_power_suspend_status_fops")
fops_end = cpu.index("};", fops_start)
fops = cpu[fops_start:fops_end]
assert ".read = seq_read" in fops
assert ".write" not in fops
assert ".open = ay_power_suspend_status_open" in fops

# The observer is registered after CPUFreq notifier setup and before input hookup.
assert cpu.index("register_pm_notifier(&ay_pm_suspend_nb)") < cpu.index(
    "input_register_handler(&cpuboost_input_handler)"
)

# Existing power/performance contracts must remain present after V9.2 patching.
for token in (
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "static bool ay_v9_boost_reuse = true;",
):
    assert token in cpu, f"Existing V9 power/performance contract lost: {token}"

# PM event model: only paired PREPARE/POST events produce a duration sample.
class PMCycle:
    def __init__(self):
        self.pending = False
        self.prepares = 0
        self.posts = 0
        self.unmatched_posts = 0
        self.last_ms = 0

    def prepare(self, now_ms):
        self.started_ms = now_ms
        self.pending = True
        self.prepares += 1

    def post(self, now_ms):
        if not self.pending:
            self.unmatched_posts += 1
            return
        self.pending = False
        self.posts += 1
        self.last_ms = max(0, now_ms - self.started_ms)


m = PMCycle()
m.post(50)
assert (m.posts, m.unmatched_posts) == (0, 1)
m.prepare(100)
m.post(8120)
assert (m.prepares, m.posts, m.last_ms, m.pending) == (1, 1, 8020, False)
m.prepare(9000)
m.post(8999)
assert m.last_ms == 0
print("PASS: V9.2 PM notifier pair accounting and monotonic duration guard")
print("PASS: read-only /proc endpoint; no new timers, wake locks, workqueues or CPUFreq policy")
print("PASS: V9 DeepDoze, wake restoration and boost contracts remain present")
print("LIMIT: hardware suspend residency and battery impact still require device measurement")
