#!/usr/bin/env python3
"""V7.7: opt-in, root-only reclaim A/B knob; reboot restores baseline.

Runs after V7.6 telemetry patch. Default mode matches original Realme/V7.2
waiter early-exit. Explicit root enable selects the V7.5 watermark policy.
No periodic work, daemons or changes to touch/DeepDoze.
"""
from pathlib import Path

src=Path(__file__).resolve().parents[2]/"kernel/mm/vmscan.c"
s=src.read_text()

def one(old,new,label):
    global s
    assert s.count(old)==1, "Unexpected patched kernel source: "+label
    s=s.replace(old,new,1)

one("struct scan_control {\n",
    """/* 0=V7.2 vendor reclaim (default); 1=V7.5 watermark experiment.
 * No persistence: each kernel boot resets this flag to false.
 */
static bool ay_reclaim_progress;
module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);
MODULE_PARM_DESC(ay_reclaim_progress,
                 "0: V7.2 waiter exit (default), 1: V7.5 watermark progress");

struct scan_control {
""",
    "root-only A/B flag")

one(
    "\t\t/* Keep reclaiming until balanced, frozen, stopped or exhausted.\n"
    "\t\t * Allocator waiter count alone does not establish watermarks.\n"
    "\t\t */\n"
    "\t\tif (try_to_freeze() || kthread_should_stop())\n"
    "\t\t\tbreak;\n",
    "\t\t/* V7.7: preserve V7.2 reclaim by default. Opt into V7.5\n"
    "\t\t * watermark progress for supervised active-screen A/B tests.\n"
    "\t\t */\n"
    "\t\tif (try_to_freeze() || kthread_should_stop() ||\n"
    "\t\t    (!READ_ONCE(ay_reclaim_progress) &&\n"
    "\t\t     !atomic_long_read(&kswapd_waiters)))\n"
    "\t\t\tbreak;\n",
    "conditional reclaim exit")

one(
    '    seq_printf(m, "wakeup_requests=%lld\\n",\n'
    '               (long long)atomic64_read(&ay_reclaim_wakeups));\n'
    '    return 0;\n',
    '    seq_printf(m, "wakeup_requests=%lld\\n",\n'
    '               (long long)atomic64_read(&ay_reclaim_wakeups));\n'
    '    seq_printf(m, "reclaim_progress_enabled=%d\\n",\n'
    '               READ_ONCE(ay_reclaim_progress) ? 1 : 0);\n'
    '    return 0;\n',
    "read-only A/B status")
src.write_text(s)
print("V7.7: V7.2 reclaim default, V7.5 explicit root opt-in, no idle work")
