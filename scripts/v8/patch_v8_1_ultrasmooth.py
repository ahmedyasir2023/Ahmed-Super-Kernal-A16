#!/usr/bin/env python3
"""V8.1 UltraSmooth: bounded burst boost and single-owner reclaim policy.

Must run after the EXACT V8 HyperSpeed build patch. No userspace daemon.
- A repeated genuine touchscreen/key input within 450ms of the previous
  accepted input requests a short UI transition boost (~82%, 145ms).
- The first input remains V8's 78%/115ms, wake remains 85%/170ms.
- All boosts use vendor policy->max and existing delayed expiry, so thermal
  frequency limits and screen-off DeepDoze remain authoritative.
- Oplus multi-kswapd defaults to one worker, but ROM sysctl may request two.
  On this single-node device shared pgdat work can duplicate and starve UI:
  cap runtime requests to one worker unless root explicitly opts out.
- Reclaim thread sysctl path is existing tested vendor kthread_stop/start;
  we DO NOT change kswapd internals or kill active threads asynchronously.
"""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
cpu_path=root/"kernel/drivers/cpufreq/cpu-boost.c"
mm_path=root/"kernel/mm/multi_kswapd/multi_kswapd.c"
s=cpu_path.read_text()
m=mm_path.read_text()

def one(txt,old,new,reason):
    assert old!=new and txt.count(old)==1, "Unexpected V8.0 source: "+reason
    return txt.replace(old,new,1)

s=one(s,
    "static atomic_t ay_wake_pending = ATOMIC_INIT(0);",
    """static atomic_t ay_wake_pending = ATOMIC_INIT(0);

/* V8.1: transient navigation burst based on consecutive accepted user
 * inputs, NOT a claim to identify Android activity launches.
 * Default ON; manual opt-out root-only. No additional timer or daemon.
 */
static bool ay_nav_burst_enabled = true;
module_param_named(ay_nav_burst_enabled, ay_nav_burst_enabled, bool, 0600);
static atomic_t ay_nav_burst_pending = ATOMIC_INIT(0);
static unsigned int ay_nav_boost_pct = 82;
module_param(ay_nav_boost_pct, uint, 0444);
static unsigned int ay_nav_boost_ms = 145;
module_param(ay_nav_boost_ms, uint, 0444);""",
    "navigation burst state")

s=one(s,
    "static unsigned int ay_dynamic_input_boost_khz(unsigned int cpu, bool wake)",
    "static unsigned int ay_dynamic_input_boost_khz(unsigned int cpu, bool wake, bool nav)",
    "bounded CPUFreq helper signature")

s=one(s,
    "    pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)\n"
    "               : min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78);",
    """    pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)
               : nav ? min_t(unsigned int, READ_ONCE(ay_nav_boost_pct), 85)
                     : min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78);""",
    "wake/nav/first-touch frequency percentages")

s=one(s,
    "    bool wake;\n    unsigned int duration;",
    "    bool wake;\n    bool nav;\n    unsigned int duration;",
    "transient worker nav state")

s=one(s,
    "    wake = atomic_xchg(&ay_wake_pending, 0) != 0;",
    """    wake = atomic_xchg(&ay_wake_pending, 0) != 0;
    nav = atomic_xchg(&ay_nav_burst_pending, 0) != 0;
    if (wake || !READ_ONCE(ay_nav_burst_enabled))
        nav = false;""",
    "drain burst flag including on wake")

s=one(s,
    "ay_dynamic_input_boost_khz(i, wake);",
    "ay_dynamic_input_boost_khz(i, wake, nav);",
    "CPUFreq policy helper call")

s=one(s,
    "    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)\n"
    "                    : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);",
    """    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)
                    : nav ? min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)
                          : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);""",
    "short navigation duration without persistent pin")

# The event handler has already removed EV_SYN and EV_KEY releases, and
# rejected screen-off inputs. It has a 100ms throttling check in V8.
s=one(s,
    "\tqueue_work(cpu_boost_wq, &input_boost_work);\n"
    "\tlast_input_time = ktime_to_us(ktime_get());",
    """    /* Consider only actual accepted touch/key events; repeats during
     * a swipe get a 145ms boost rather than expensive max-frequency pins.
     */
    if (READ_ONCE(ay_nav_burst_enabled) && last_input_time &&
        now > last_input_time &&
        now - last_input_time <= 450 * USEC_PER_MSEC &&
        (type == EV_ABS || (type == EV_KEY && value)))
        atomic_set(&ay_nav_burst_pending, 1);

\tqueue_work(cpu_boost_wq, &input_boost_work);
\tlast_input_time = now;""",
    "event-driven UI burst detection")

# Avoid stale rapid-tap state crossing display-off notifications.
s=one(s,
    "            atomic_set(&ay_wake_pending, 0);\n"
    "            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);",
    "            atomic_set(&ay_wake_pending, 0);\n"
    "            atomic_set(&ay_nav_burst_pending, 0);\n"
    "            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);",
    "panel-off navigation state cleanup")

# Oplus originally boots with ONE kswapd per node. EvolutionX requests two
# through sysctl; preserve original mode as an opt-out, not a direct stop call.
m=one(m,
    "int max_kswapd_threads = MAX_KSWAPD_THREADS;",
    """int max_kswapd_threads = MAX_KSWAPD_THREADS;

/* V8.1: one worker per memory node by default, matching vendor boot
 * defaults. Reduces concurrent reclaim on the same pgdat. Root may disable
 * this guard, then request 2 via vm.kswapd_threads if needed.
 */
static bool ay_v81_single_kswapd = true;
module_param_named(ay_v81_single_kswapd, ay_v81_single_kswapd, bool, 0600);
MODULE_PARM_DESC(ay_v81_single_kswapd,
                 "1: cap runtime kswapd count at 1, 0: allow vendor sysctl");""",
    "per-node reclaim parallelism guard")

m=one(m,
    "\tif (write)\n\t\tupdate_kswapd_threads();\n\n\treturn 0;\n}\n",
    """\tif (write) {
        if (READ_ONCE(ay_v81_single_kswapd) && kswapd_threads > 1)
            kswapd_threads = 1;
\t\tupdate_kswapd_threads();
    }

\treturn 0;
}
""",
    "existing vendor worker-count sysctl handler")

# Fail before writing either source file.
for required in (
    "module_param(ay_nav_boost_pct, uint, 0444);",
    "module_param(ay_nav_boost_ms, uint, 0444);",
    "if (!READ_ONCE(ay_screen_on))",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "min_t(unsigned int, READ_ONCE(ay_nav_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)",
):
    assert required in s,required
for required in ("static bool ay_v81_single_kswapd = true;",
                 "module_param_named(ay_v81_single_kswapd, ay_v81_single_kswapd, bool, 0600);",
                 "update_kswapd_threads();",
                 "kthread_stop(pgdat->kswapd[hid]);"):
    assert required in m,required
cpu_path.write_text(s)
mm_path.write_text(m)
print("V8.1: first input 78%/115ms, nav burst 82%/145ms, wake 85%/170ms")
print("V8.1: default single-kSwapd guard with root opt-out; watermark 50 unchanged")
print("V8.1: 600s DeepDoze, DT2W, fingerprint, KernelSU and thermal untouched")
