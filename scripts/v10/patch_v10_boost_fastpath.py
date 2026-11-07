#!/usr/bin/env python3
"""V10.1: nonblocking renewal of an already-active same-profile input boost.

The V9 fast path still called cancel_delayed_work_sync() BEFORE deciding
whether the active boost could be reused. If the expiry worker was running,
the input worker could wait for its CPUFreq policy updates before returning.
V10 moves same-profile renewal ahead of that synchronous cancellation and
serializes the deadline/profile handoff with a small IRQ-safe spinlock.

No new work item, timer, workqueue, wake lock, wake source, governor, frequency
ceiling, thermal change, touch-driver change, or screen-off policy is added.
Wake/profile transitions and expired boosts retain the original full path.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/cpufreq/cpu-boost.c"
s = driver.read_text()


def one(old: str, new: str, label: str) -> None:
    global s
    assert old != new and s.count(old) == 1, (
        "V10.1 source contract failed at " + label +
        "; matches=" + str(s.count(old))
    )
    s = s.replace(old, new, 1)


one(
    "#include <linux/slab.h>\n",
    "#include <linux/slab.h>\n#include <linux/spinlock.h>\n",
    "explicit IRQ-safe state lock header",
)

one(
    "static unsigned long ay_v9_reused_bursts;\n"
    "module_param(ay_v9_reused_bursts, ulong, 0444);\n",
    "static unsigned long ay_v9_reused_bursts;\n"
    "module_param(ay_v9_reused_bursts, ulong, 0444);\n"
    "\n"
    "/* V10.1: serialize the active boost deadline against its expiry worker. */\n"
    "static bool ay_v10_boost_fastpath = true;\n"
    "module_param_named(ay_v10_boost_fastpath, ay_v10_boost_fastpath, bool, 0600);\n"
    "static DEFINE_SPINLOCK(ay_v10_boost_state_lock);\n"
    "static unsigned long ay_v10_boost_expires;\n",
    "V10 opt-out and expiry state",
)

one(
    "static void do_input_boost_rem(struct work_struct *work)\n"
    "{\n"
    "\tunsigned int i, ret;\n"
    "\tstruct cpu_sync *i_sync_info;\n\n"
    "    /* Expiry is the authoritative end of the active CPU boost. */\n"
    "    WRITE_ONCE(ay_v9_boost_profile, 0);\n",
    """static void do_input_boost_rem(struct work_struct *work)
{
\tunsigned int i, ret;
\tstruct cpu_sync *i_sync_info;
    unsigned long flags, remaining;

    /*
     * A same-profile input may have extended the deadline while this
     * delayed work was becoming runnable. Serialize the decision with the
     * fast path; never clear a renewed boost early.
     */
    spin_lock_irqsave(&ay_v10_boost_state_lock, flags);
    if (READ_ONCE(ay_screen_on) &&
        READ_ONCE(ay_v9_boost_profile) &&
        time_before(jiffies, ay_v10_boost_expires)) {
        remaining = ay_v10_boost_expires - jiffies;
        spin_unlock_irqrestore(&ay_v10_boost_state_lock, flags);
        if (!remaining)
            remaining = 1;
        mod_delayed_work(cpu_boost_wq, &input_boost_rem, remaining);
        /* A panel blank racing this requeue always wins. */
        if (!READ_ONCE(ay_screen_on))
            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
        return;
    }
    ay_v10_boost_expires = 0;
    WRITE_ONCE(ay_v9_boost_profile, 0);
    spin_unlock_irqrestore(&ay_v10_boost_state_lock, flags);
""",
    "expiry worker honors a concurrently renewed deadline",
)

one(
    "    bool wake;\n"
    "    bool nav;\n"
    "    unsigned int duration;\n",
    "    bool wake;\n"
    "    bool nav;\n"
    "    unsigned int duration;\n"
    "    unsigned long duration_jiffies, flags;\n",
    "boost worker deadline and lock locals",
)

# Exact V9.2 source has a tab before cancel_delayed_work_sync.
old_duration = (
    "    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)\n"
    "                    : nav ? min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)\n"
    "                          : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);\n\n"
    "\tcancel_delayed_work_sync(&input_boost_rem);"
)
new_duration = """    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)
                    : nav ? min_t(unsigned int, READ_ONCE(ay_nav_boost_ms), 160)
                          : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);
    duration_jiffies = msecs_to_jiffies(max_t(unsigned int, duration, 1));

    /*
     * Fast path: a live boost of the exact same profile already has the
     * required CPU minima and WALT level. Extend its existing expiry without
     * waiting for the expiry worker or repeating eight policy transactions.
     * The lock makes expiry-vs-renewal ordering deterministic.
     */
    if (!wake && READ_ONCE(ay_v10_boost_fastpath) &&
        READ_ONCE(ay_v9_boost_reuse)) {
        bool reused = false;

        spin_lock_irqsave(&ay_v10_boost_state_lock, flags);
        if (READ_ONCE(ay_screen_on) &&
            READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1) &&
            READ_ONCE(sched_boost_active) == boost &&
            time_before(jiffies, ay_v10_boost_expires)) {
            ay_v10_boost_expires = jiffies + duration_jiffies;
            reused = true;
        }
        spin_unlock_irqrestore(&ay_v10_boost_state_lock, flags);

        if (reused) {
            WRITE_ONCE(ay_v9_reused_bursts,
                       READ_ONCE(ay_v9_reused_bursts) + 1);
            mod_delayed_work(cpu_boost_wq, &input_boost_rem,
                             duration_jiffies);
            /* Do not let a concurrent panel blank inherit this renewal. */
            if (!READ_ONCE(ay_screen_on))
                mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
            return;
        }
    }

\tcancel_delayed_work_sync(&input_boost_rem);"""
one(old_duration, new_duration, "move same-profile renewal before synchronous expiry cancellation")

old_reuse = """    /* After cancellation has synchronized with an executing expiry, a live
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
"""
one(old_reuse, "", "remove obsolete post-cancel reuse block")

old_arm = """    WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));
    queue_delayed_work(cpu_boost_wq, &input_boost_rem,
                       msecs_to_jiffies(max_t(unsigned int, duration, 1)));
"""
new_arm = """    spin_lock_irqsave(&ay_v10_boost_state_lock, flags);
    WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));
    ay_v10_boost_expires = jiffies + duration_jiffies;
    spin_unlock_irqrestore(&ay_v10_boost_state_lock, flags);
    queue_delayed_work(cpu_boost_wq, &input_boost_rem, duration_jiffies);
    /* If blanking raced the policy update, release immediately. */
    if (!READ_ONCE(ay_screen_on))
        mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
"""
one(old_arm, new_arm, "arm serialized expiry deadline with the applied profile")

for required in (
    "#include <linux/spinlock.h>",
    "static bool ay_v10_boost_fastpath = true;",
    "module_param_named(ay_v10_boost_fastpath, ay_v10_boost_fastpath, bool, 0600);",
    "static DEFINE_SPINLOCK(ay_v10_boost_state_lock);",
    "static unsigned long ay_v10_boost_expires;",
    "time_before(jiffies, ay_v10_boost_expires)",
    "READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1)",
    "READ_ONCE(sched_boost_active) == boost",
    "duration_jiffies = msecs_to_jiffies(max_t(unsigned int, duration, 1));",
    "cancel_delayed_work_sync(&input_boost_rem);",
    "queue_delayed_work(cpu_boost_wq, &input_boost_rem, duration_jiffies);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
):
    assert required in s, required

assert s.count("cancel_delayed_work_sync(&input_boost_rem);") == 1
assert s.count("static DEFINE_SPINLOCK(ay_v10_boost_state_lock);") == 1
assert "pm_stay_awake(" not in s
assert "pm_wakeup_event(" not in s
assert "wake_lock(" not in s
assert "thermal_disable" not in s
assert "selinux_enforcing = 0" not in s
assert "policy->max =" not in s

driver.write_text(s)
print("V10.1: same-profile input boost renewal no longer waits synchronously for expiry work.")
print("V10.1: wake/profile transitions and expired boosts retain the original full policy path.")
print("V10.1: no new workqueue/timer/wake source; screen-off and DeepDoze contracts retained.")
