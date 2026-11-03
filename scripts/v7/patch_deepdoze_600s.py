#!/usr/bin/env python3
"""V7: 600-second one-shot screen-off CPU cap with immediate wake recovery.

Apply after the pinned V5 and V6 patches. Never touch vendor touch, thermal,
SELinux, device trees, root configuration or GPU drivers. This CPUFreq policy
notifier runs only on the existing boost driver's workqueue, and a deferrable
timer does not wake an otherwise idle device just to engage the cap.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
driver = root / "kernel/drivers/cpufreq/cpu-boost.c"
src = driver.read_text()

def change(old: str, new: str, label: str) -> None:
    global src
    assert src.count(old) == 1, f"V6 contract changed at {label}: {src.count(old)} matches"
    src = src.replace(old, new, 1)

change(
    "static atomic_t ay_wake_pending = ATOMIC_INIT(0);\n",
    """static atomic_t ay_wake_pending = ATOMIC_INIT(0);

/* A one-shot, deferrable 600-second screen-off timer. Defaults are immutable
 * at runtime to avoid racing parameter writes with CPU policy transitions.
 * The cap never reduces frequency below an existing policy minimum.
 */
static bool ay_deepdoze_enabled = true;
module_param(ay_deepdoze_enabled, bool, 0444);
static unsigned int ay_deepdoze_delay_seconds = 600;
module_param(ay_deepdoze_delay_seconds, uint, 0444);
static bool ay_deepdoze_active;
module_param(ay_deepdoze_active, bool, 0444);
static unsigned int ay_deepdoze_entries;
module_param(ay_deepdoze_entries, uint, 0444);
static struct delayed_work ay_deepdoze_timer;
static struct work_struct ay_deepdoze_release;
""",
    "DeepDoze state and parameters",
)

change(
    "\tcase CPUFREQ_ADJUST:\n\t\tif (!ib_min)\n",
    """\tcase CPUFREQ_ADJUST:
        /* Respect existing policy minima and all thermal ceilings.  The
         * display must STILL be off here, closing the unblank/timer race.
         * Do not clamp to a value below a caller's already-required min.
         */
        if (!READ_ONCE(ay_screen_on) &&
            READ_ONCE(ay_deepdoze_active)) {
            unsigned int floor = max(policy->min,
                                     policy->cpuinfo.min_freq);
            cpufreq_verify_within_limits(policy, 0, floor);
            break;
        }
\t\tif (!ib_min)
""",
    "notifier cap with policy guard",
)

change(
    "#if defined(CONFIG_DRM_MSM) || defined(CONFIG_FB_NOTIFY)\nstatic int ay_display_notifier",
    """/* Deferrable: if Linux has already entered suspend/idle, do not wake it
 * merely to lower clocks.  The next normal wake schedules this work.
 */
static void ay_deepdoze_expire(struct work_struct *work)
{
    if (!READ_ONCE(ay_deepdoze_enabled) ||
        READ_ONCE(ay_screen_on))
        return;

    WRITE_ONCE(ay_deepdoze_active, true);
    /* A display unblank may race the timer. Never retain a stale cap. */
    if (READ_ONCE(ay_screen_on)) {
        WRITE_ONCE(ay_deepdoze_active, false);
        update_policy_online();
        return;
    }
    WRITE_ONCE(ay_deepdoze_entries,
               READ_ONCE(ay_deepdoze_entries) + 1);
    update_policy_online();
}

static void ay_deepdoze_restore(struct work_struct *work)
{
    /* Runs in process context: never call CPUFreq synchronously in the DRM
     * blank callback, and never acquire CPUFreq locks from the notifier.
     */
    update_policy_online();
}

#if defined(CONFIG_DRM_MSM) || defined(CONFIG_FB_NOTIFY)
static int ay_display_notifier""",
    "one-shot timer and restore work",
)

change(
    """            WRITE_ONCE(ay_screen_on, false);
            atomic_set(&ay_wake_pending, 0);
            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
""",
    """            WRITE_ONCE(ay_screen_on, false);
            atomic_set(&ay_wake_pending, 0);
            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
            if (READ_ONCE(ay_deepdoze_enabled))
                mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,
                                 msecs_to_jiffies(600000));
""",
    "arm 10-minute timer exactly once when panel darkens",
)

change(
    """    } else if (!READ_ONCE(ay_screen_on)) {
        WRITE_ONCE(ay_screen_on, true);
        if (READ_ONCE(ay_instantwake) &&
""",
    """    } else if (!READ_ONCE(ay_screen_on)) {
        /* Drop cap before any wake boost even if the timer is running.
         * cancel_delayed_work is nonblocking in atomic notifier context.
         */
        WRITE_ONCE(ay_screen_on, true);
        cancel_delayed_work(&ay_deepdoze_timer);
        WRITE_ONCE(ay_deepdoze_active, false);
        queue_work(cpu_boost_wq, &ay_deepdoze_release);
        if (READ_ONCE(ay_instantwake) &&
""",
    "cancel and release before instant wake",
)

change(
    "\tINIT_DELAYED_WORK(&input_boost_rem, do_input_boost_rem);\n",
    """\tINIT_DELAYED_WORK(&input_boost_rem, do_input_boost_rem);
    INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);
    INIT_WORK(&ay_deepdoze_release, ay_deepdoze_restore);
""",
    "initialize deferrable one-shot timer and release worker",
)

required = [
    "static bool ay_deepdoze_enabled = true;",
    "static unsigned int ay_deepdoze_delay_seconds = 600;",
    "module_param(ay_deepdoze_active, bool, 0444);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "msecs_to_jiffies(600000)",
    "WRITE_ONCE(ay_screen_on, true);",
    "cancel_delayed_work(&ay_deepdoze_timer);",
    "WRITE_ONCE(ay_deepdoze_active, false);",
    "queue_work(cpu_boost_wq, &ay_deepdoze_release);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "MSM_DRM_PRIMARY_DISPLAY",
    "uint8_t DouTap_enable = 1;"  # touch lives in different source; not a driver requirement
]
for item in required[:-1]:
    assert item in src, item
assert src.count("msecs_to_jiffies(600000)") == 1
assert "policy->max =" not in src
assert "thermal_disable" not in src
driver.write_text(src)
print("V7 staged: one-shot 600s deferrable DeepDoze, policy-clamped CPU ceilings.")
print("On display unblank: immediate cap release and existing 155-ms InstantWake.")
print("DT2W touch init, thermal controls, SELinux and original DTBs untouched.")
