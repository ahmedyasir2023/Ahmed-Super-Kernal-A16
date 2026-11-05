#!/usr/bin/env python3
"""V9.1: one bounded, rate-limited background reclaim follow-up pass.

Apply AFTER V7.7 guarded reclaim, V8/V8.1 and V9 source patches.

Rationale from first V9 hardware report:
15,191 of 15,327 kswapd balance entries found zero direct-reclaim waiters
and the screen-on workload had intermittent high memory PSI. The Realme
vendor waiter-zero shortcut ends the current balance pass even if the node
remains below high watermark. V7.5's unbounded alternate behavior was
deliberately left opt-in. V9.1 performs at most ONE extra pass when the
current pass actually reclaimed pages, the node remains unbalanced, no
allocator waits, and >=1 second has elapsed since the last extra pass.

This is a bounded performance experiment, NOT proof of lower PSI on device.
Root-only opt-out at /sys/module/vmscan/parameters/ay_v91_bounded_reclaim.
No touching CPU, thermal, touch, sleep, ZRAM, swappiness or vendor drivers.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "kernel/mm/vmscan.c"
s = path.read_text()

def one(old: str, new: str, reason: str) -> None:
    global s
    assert old != new and s.count(old) == 1, "V9.1 source mismatch: " + reason
    s = s.replace(old, new, 1)

one(
    "#include <linux/psi.h>\n",
    "#include <linux/psi.h>\n#include <linux/jiffies.h>\n",
    "jiffies include"
)
one(
    "static bool ay_reclaim_progress;\n"
    "module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);\n"
    "MODULE_PARM_DESC(ay_reclaim_progress,\n"
    "                 \"0: V7.2 waiter exit (default), 1: V7.5 watermark progress\");\n",
    """static bool ay_reclaim_progress;
module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);
MODULE_PARM_DESC(ay_reclaim_progress,
                 "0: V7.2 waiter exit (default), 1: V7.5 watermark progress");

/* V9.1: make one extra bounded attempt ONLY after demonstrated reclaim
 * progress; preserve the vendor fast exit if the guard is disabled.
 * This is an independent opt-out; the V7.7 unlimited A/B switch remains
 * false. Do not write a persistent boot script.
 */
static bool ay_v91_bounded_reclaim = true;
module_param_named(ay_v91_bounded_reclaim, ay_v91_bounded_reclaim, bool, 0600);
MODULE_PARM_DESC(ay_v91_bounded_reclaim,
                 "1: max one post-progress pass per kswapd cycle and per second");
static unsigned long ay_v91_last_extra_jiffies;
""",
    "root-only rollback knob"
)
one(
    "static atomic64_t ay_reclaim_wakeups = ATOMIC64_INIT(0);\n",
    """static atomic64_t ay_reclaim_wakeups = ATOMIC64_INIT(0);
static atomic64_t ay_v91_extra_passes = ATOMIC64_INIT(0);
static atomic64_t ay_v91_waiter_exits = ATOMIC64_INIT(0);
""",
    "V9.1 event-only counters"
)
one(
    '    seq_printf(m, "reclaim_progress_enabled=%d\\n",\n'
    '               READ_ONCE(ay_reclaim_progress) ? 1 : 0);\n'
    '    return 0;\n',
    '    seq_printf(m, "reclaim_progress_enabled=%d\\n",\n'
    '               READ_ONCE(ay_reclaim_progress) ? 1 : 0);\n'
    '    seq_printf(m, "v91_bounded_reclaim_enabled=%d\\n",\n'
    '               READ_ONCE(ay_v91_bounded_reclaim) ? 1 : 0);\n'
    '    seq_printf(m, "v91_extra_passes=%lld\\n",\n'
    '               (long long)atomic64_read(&ay_v91_extra_passes));\n'
    '    seq_printf(m, "v91_waiter_exits=%lld\\n",\n'
    '               (long long)atomic64_read(&ay_v91_waiter_exits));\n'
    '    return 0;\n',
    "read-only /proc/ay_reclaim_status extension"
)
one(
    "static int balance_pgdat(pg_data_t *pgdat, int order, int classzone_idx)\n"
    "{\n"
    "\tint i;\n",
    "static int balance_pgdat(pg_data_t *pgdat, int order, int classzone_idx)\n"
    "{\n"
    "\tint i;\n"
    "\tunsigned int ay_v91_extra_this_cycle = 0;\n",
    "cycle-local maximum of one extra pass"
)
one(
    "\t\t/* V7.7: preserve V7.2 reclaim by default. Opt into V7.5\n"
    "\t\t * watermark progress for supervised active-screen A/B tests.\n"
    "\t\t */\n"
    "\t\tif (try_to_freeze() || kthread_should_stop() ||\n"
    "\t\t    (!READ_ONCE(ay_reclaim_progress) &&\n"
    "\t\t     !atomic_long_read(&kswapd_waiters)))\n"
    "\t\t\tbreak;\n",
    """		/* V9.1: preserve freeze and thread-stop exits unconditionally. */
		if (try_to_freeze() || kthread_should_stop())
			break;

		/*
		 * V7.7's unlimited watermark mode remains a separate opt-in.
		 * With no allocator waiting, V9.1 can finish ONE additional
		 * successful, unbalanced pass, at most once per second.
		 * Do not spend more CPU on a pass that freed zero pages.
		 */
		if (!READ_ONCE(ay_reclaim_progress) &&
		    !atomic_long_read(&kswapd_waiters)) {
			bool extra_ok = READ_ONCE(ay_v91_bounded_reclaim) &&
				!ay_v91_extra_this_cycle &&
				sc.nr_reclaimed > nr_reclaimed &&
				!pgdat_balanced(pgdat, sc.order, classzone_idx) &&
				!time_before(jiffies,
					READ_ONCE(ay_v91_last_extra_jiffies) +
					msecs_to_jiffies(1000));

			if (!extra_ok) {
#ifdef CONFIG_PROC_FS
				atomic64_inc(&ay_v91_waiter_exits);
#endif
				break;
			}
			ay_v91_extra_this_cycle++;
			WRITE_ONCE(ay_v91_last_extra_jiffies, jiffies);
#ifdef CONFIG_PROC_FS
			atomic64_inc(&ay_v91_extra_passes);
#endif
		}
""",
    "bounded one-pass reclaim fallback"
)
for token in (
    "static bool ay_v91_bounded_reclaim = true;",
    "module_param_named(ay_v91_bounded_reclaim, ay_v91_bounded_reclaim, bool, 0600);",
    "static unsigned long ay_v91_last_extra_jiffies;",
    "unsigned int ay_v91_extra_this_cycle = 0;",
    "msecs_to_jiffies(1000)",
    "sc.nr_reclaimed > nr_reclaimed",
    "!pgdat_balanced(pgdat, sc.order, classzone_idx)",
    "WRITE_ONCE(ay_v91_last_extra_jiffies, jiffies);",
    "atomic64_inc(&ay_v91_extra_passes);",
    "atomic64_inc(&ay_v91_waiter_exits);",
    "(!READ_ONCE(ay_reclaim_progress) &&",
):
    assert token in s, token
for bad in ("policy->max =", "selinux_enforcing = 0", "thermal_disable"):
    assert bad not in s, bad
path.write_text(s)
print("V9.1: one optional guarded extra reclaim pass after progress, rate limit 1s")
print("V9.1: root opt-out and read-only telemetry; V7.7 infinite A/B remains disabled")
print("V9.1: no change to CPUFreq, RAM sysctls, DT2W, DeepDoze or thermal")
