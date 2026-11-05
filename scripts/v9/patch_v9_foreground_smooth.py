#!/usr/bin/env python3
"""V9: coalesce redundant CPUFreq work during sustained user interaction.

This source patch is deliberately ordered AFTER V8.1 on the pinned Realme
4.14 kernel. Accepted input still refreshes the original bounded timer.
When an already-active boost has the *same* profile, do not repeatedly call
cpufreq_update_policy for every finger movement. A new higher boost (navigation
or wake), an expired boost, or a panel transition always goes through the
original full CPUFreq path. No new daemon, timer, governor or power policy.
"""
from pathlib import Path

source = Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c"
s = source.read_text()

def one(old: str, new: str, reason: str) -> None:
    global s
    assert old != new and s.count(old) == 1, "V8.1 source contract failed: " + reason
    s = s.replace(old, new, 1)

one(
    "static atomic_t ay_nav_burst_pending = ATOMIC_INIT(0);",
    """static atomic_t ay_nav_burst_pending = ATOMIC_INIT(0);

/* V9: on a continuous gesture refresh the short expiry without repeating
 * eight CPUFreq policy transactions on every accepted touch. Profile:
 * 0=none, 1=ordinary touch, 2=navigation, 3=screen wake.
 */
static bool ay_v9_boost_reuse = true;
module_param_named(ay_v9_boost_reuse, ay_v9_boost_reuse, bool, 0600);
static unsigned int ay_v9_boost_profile;
module_param(ay_v9_boost_profile, uint, 0444);
static unsigned long ay_v9_reused_bursts;
module_param(ay_v9_reused_bursts, ulong, 0444);""",
    "read-only telemetry and opt-out"
)

one(
    "static void do_input_boost_rem(struct work_struct *work)\n{\n"
    "\tunsigned int i, ret;\n"
    "\tstruct cpu_sync *i_sync_info;\n",
    "static void do_input_boost_rem(struct work_struct *work)\n{\n"
    "\tunsigned int i, ret;\n"
    "\tstruct cpu_sync *i_sync_info;\n\n"
    "    /* Expiry is the authoritative end of the active CPU boost. */\n"
    "    WRITE_ONCE(ay_v9_boost_profile, 0);\n",
    "clear active profile on expiry"
)

# Compute duration before deciding whether an existing boost can be reused.
one(
    "    if (!READ_ONCE(ay_instantwake))\n"
    "        wake = false;\n\n"
    "\tcancel_delayed_work_sync(&input_boost_rem);",
    "    if (!READ_ONCE(ay_instantwake))\n"
    "        wake = false;\n\n"
    "    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)\n"
    "                    : nav ? min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)\n"
    "                          : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);\n\n"
    "\tcancel_delayed_work_sync(&input_boost_rem);",
    "calculate bounded duration before reuse decision"
)

one(
    "    if (!READ_ONCE(ay_screen_on)) {\n"
    "        mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);\n"
    "        return;\n"
    "    }\n",
    """    if (!READ_ONCE(ay_screen_on)) {
        mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
        return;
    }

    /* After cancellation has synchronized with an executing expiry, a live
     * boost of exactly the same type already has correct CPU minimums and
     * scheduler level. Only renew its existing short expiry. Never reuse
     * wake boosts: a panel transition must recalculate CPUFreq policy.
     */
    if (!wake && READ_ONCE(ay_v9_boost_reuse) &&
        READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1) &&
        READ_ONCE(sched_boost_active) == boost) {
        WRITE_ONCE(ay_v9_reused_bursts,
                   READ_ONCE(ay_v9_reused_bursts) + 1);
        mod_delayed_work(cpu_boost_wq, &input_boost_rem,
                         msecs_to_jiffies(max_t(unsigned int, duration, 1)));
        return;
    }
""",
    "skip redundant policy updates, not actual boost expiration"
)

one(
    "    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)\n"
    "                    : nav ? min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)\n"
    "                          : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);\n"
    "    queue_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "    WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));\n"
    "    queue_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "record applied profile for next input"
)

# Confirm nothing in the event path, wake path, or DeepDoze was removed.
for term in (
    "MIN_INPUT_INTERVAL (100 * USEC_PER_MSEC)",
    "now - last_input_time <= 450 * USEC_PER_MSEC",
    "atomic_xchg(&ay_wake_pending, 0)",
    "atomic_xchg(&ay_nav_burst_pending, 0)",
    "if (!READ_ONCE(ay_screen_on))",
    "WRITE_ONCE(ay_v9_boost_profile, 0);",
    "WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));",
    "cancel_delayed_work_sync(&input_boost_rem);",
    "mod_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "queue_delayed_work(cpu_boost_wq, &input_boost_rem,",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
):
    assert term in s, term
for bad in ("policy->max =", "thermal_disable", "selinux_enforcing = 0"):
    assert bad not in s, bad
source.write_text(s)
print("V9: repeated same-profile touch renews bounded expiry without another CPUFreq update")
print("V9: first touch/nav/wake 78/82/85 percent unchanged; 115/145/170ms unchanged")
print("V9: no new timer, driver, service, wake lock or DeepDoze change")
