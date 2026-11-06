#!/usr/bin/env python3
"""V9.2 RC1: add passive PM suspend-cycle telemetry to the existing CPUBoost driver.

This patch observes PM_SUSPEND_PREPARE / PM_POST_SUSPEND only. It does not
change suspend policy, CPUFreq limits, DeepDoze timers, wake locks, touch,
thermal handling, SELinux, or device trees.

The measured interval is CLOCK_BOOTTIME elapsed time between the two PM
notifier events. It includes suspend time, but also includes preparation and
resume work; it is NOT a direct hardware suspend-residency measurement.
Use suspend_stats and CPUIdle residency alongside it.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/cpufreq/cpu-boost.c"
s = driver.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    assert old != new and s.count(old) == 1, (
        "V9.2 CPUBoost source contract failed at " + label
    )
    s = s.replace(old, new, 1)


one(
    "#include <linux/time.h>\n",
    """#include <linux/time.h>
#include <linux/atomic.h>
#include <linux/ktime.h>
#include <linux/timekeeping.h>
#include <linux/suspend.h>
#ifdef CONFIG_PROC_FS
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#endif
""",
    "explicit PM/timekeeping and read-only procfs headers",
)

telemetry = r"""
/*
 * V9.2 passive suspend-cycle telemetry.
 *
 * PM notifier callbacks run only when the system is already entering or
 * leaving system suspend. No timer, work item, wake lock, wakeup event,
 * CPUFreq update, or polling loop is introduced here.
 *
 * The elapsed value is CLOCK_BOOTTIME from PREPARE to POST_SUSPEND. It
 * includes suspend time but also PM preparation/resume overhead. The kernel
 * suspend_stats and CPUIdle state time counters remain the authoritative
 * companion measurements for failures and idle residency.
 */
static atomic64_t ay_pm_prepare_events = ATOMIC64_INIT(0);
static atomic64_t ay_pm_post_events = ATOMIC64_INIT(0);
static atomic64_t ay_pm_unmatched_post_events = ATOMIC64_INIT(0);
static atomic64_t ay_pm_last_cycle_ms = ATOMIC64_INIT(0);
static atomic64_t ay_pm_max_cycle_ms = ATOMIC64_INIT(0);
static atomic64_t ay_pm_total_cycle_ms = ATOMIC64_INIT(0);
static atomic_t ay_pm_cycle_pending = ATOMIC_INIT(0);
static ktime_t ay_pm_prepare_boottime;

static void ay_pm_update_max_cycle_ms(s64 elapsed_ms)
{
	s64 old = atomic64_read(&ay_pm_max_cycle_ms);

	while (elapsed_ms > old) {
		s64 previous = atomic64_cmpxchg(&ay_pm_max_cycle_ms,
						old, elapsed_ms);

		if (previous == old)
			break;
		old = previous;
	}
}

static int ay_pm_suspend_notifier(struct notifier_block *nb,
				  unsigned long event, void *unused)
{
	switch (event) {
	case PM_SUSPEND_PREPARE:
		WRITE_ONCE(ay_pm_prepare_boottime, ktime_get_boottime());
		atomic_set(&ay_pm_cycle_pending, 1);
		atomic64_inc(&ay_pm_prepare_events);
		break;

	case PM_POST_SUSPEND:
		if (atomic_xchg(&ay_pm_cycle_pending, 0)) {
			s64 elapsed_ms = ktime_ms_delta(
				ktime_get_boottime(),
				READ_ONCE(ay_pm_prepare_boottime));

			/* Guard against an invalid clock delta; never wrap counters. */
			if (elapsed_ms < 0)
				elapsed_ms = 0;

			atomic64_set(&ay_pm_last_cycle_ms, elapsed_ms);
			atomic64_add(elapsed_ms, &ay_pm_total_cycle_ms);
			ay_pm_update_max_cycle_ms(elapsed_ms);
			atomic64_inc(&ay_pm_post_events);
		} else {
			atomic64_inc(&ay_pm_unmatched_post_events);
		}
		break;
	}

	return NOTIFY_OK;
}

static struct notifier_block ay_pm_suspend_nb = {
	.notifier_call = ay_pm_suspend_notifier,
};

#ifdef CONFIG_PROC_FS
static int ay_power_suspend_status_show(struct seq_file *m, void *unused)
{
	seq_printf(m, "pm_suspend_prepare_events=%lld\n",
		   (long long)atomic64_read(&ay_pm_prepare_events));
	seq_printf(m, "pm_post_suspend_events=%lld\n",
		   (long long)atomic64_read(&ay_pm_post_events));
	seq_printf(m, "pm_unmatched_post_events=%lld\n",
		   (long long)atomic64_read(&ay_pm_unmatched_post_events));
	seq_printf(m, "pm_cycle_pending=%d\n",
		   atomic_read(&ay_pm_cycle_pending));
	seq_printf(m, "pm_last_prepare_to_post_boottime_ms=%lld\n",
		   (long long)atomic64_read(&ay_pm_last_cycle_ms));
	seq_printf(m, "pm_max_prepare_to_post_boottime_ms=%lld\n",
		   (long long)atomic64_read(&ay_pm_max_cycle_ms));
	seq_printf(m, "pm_total_prepare_to_post_boottime_ms=%lld\n",
		   (long long)atomic64_read(&ay_pm_total_cycle_ms));
	seq_puts(m, "elapsed_semantics=PM_SUSPEND_PREPARE_to_PM_POST_SUSPEND_CLOCK_BOOTTIME_including_suspend_and_PM_overhead\n");
	seq_puts(m, "suspend_success_semantics=use_kernel_suspend_stats_not_this_notifier\n");
	return 0;
}

static int ay_power_suspend_status_open(struct inode *inode,
					struct file *file)
{
	return single_open(file, ay_power_suspend_status_show, NULL);
}

static const struct file_operations ay_power_suspend_status_fops = {
	.open = ay_power_suspend_status_open,
	.read = seq_read,
	.llseek = seq_lseek,
	.release = single_release,
};
#endif /* CONFIG_PROC_FS */

"""

one(
    "static int cpu_boost_init(void)\n{\n",
    telemetry + "\nstatic int cpu_boost_init(void)\n{\n",
    "passive PM notifier and read-only status implementation",
)

one(
    "\tcpufreq_register_notifier(&boost_adjust_nb, CPUFREQ_POLICY_NOTIFIER);\n\n"
    "\tret = input_register_handler(&cpuboost_input_handler);\n",
    """\tcpufreq_register_notifier(&boost_adjust_nb, CPUFREQ_POLICY_NOTIFIER);

	/* Observe system PM transitions without changing their outcome. */
	ret = register_pm_notifier(&ay_pm_suspend_nb);
	if (ret)
		pr_warn("V9.2 PM suspend telemetry registration failed: %d\\n",
			ret);

#ifdef CONFIG_PROC_FS
	if (!proc_create("ay_power_suspend_status", 0444, NULL,
			 &ay_power_suspend_status_fops))
		pr_warn("V9.2 read-only suspend status endpoint unavailable\\n");
#endif

	ret = input_register_handler(&cpuboost_input_handler);
""",
    "register observer and expose read-only /proc endpoint",
)

assert s.count("register_pm_notifier(&ay_pm_suspend_nb)") == 1
assert s.count('proc_create("ay_power_suspend_status", 0444') == 1
assert s.count("case PM_SUSPEND_PREPARE:") == 1
assert s.count("case PM_POST_SUSPEND:") == 1
assert "mod_delayed_work" not in telemetry
assert "queue_work" not in telemetry
assert "pm_stay_awake" not in telemetry
assert "pm_wakeup_event" not in telemetry
assert "cpufreq_update_policy" not in telemetry
assert "policy->max" not in telemetry

driver.write_text(s)
print("V9.2 passive PM telemetry staged in CPUBoost only.")
print("No suspend policy, CPUFreq, timer, wake-lock, touch, thermal or DT2W changes.")
print("Read-only endpoint: /proc/ay_power_suspend_status")
