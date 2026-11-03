#!/usr/bin/env python3
"""V6: screen-aware adaptive input boost and short instant-wake CPU boost.

Patch only the Realme CPUBoost driver *after* V5 has been staged. Uses the same
MSM DRM panel notifications as the vendor touchscreen driver; no Android
daemon, no hard CPU-frequency clamp while the screen is dark. As soon as
the screen blanks, queued boosts are retired and normal schedutil can settle
to hardware idle/minimum frequencies. On unblank, apply a brief bounded
boost, never exceeding the currently allowed CPUFreq policy or thermal caps.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
p = root / "kernel/drivers/cpufreq/cpu-boost.c"
src = p.read_text()

def change(old: str, new: str, label: str) -> None:
    global src
    assert src.count(old) == 1, f"V5 source contract changed: {label}"
    src = src.replace(old, new, 1)

change(
    "#include <linux/time.h>\n",
    """#include <linux/time.h>
#include <linux/atomic.h>
#include <linux/notifier.h>
#ifdef CONFIG_DRM_MSM
#include <linux/msm_drm_notify.h>
#elif defined(CONFIG_FB_NOTIFY)
#include <linux/fb.h>
#endif
""",
    "headers"
)

change(
    "static bool input_boost_enabled;\n",
    """static bool input_boost_enabled;

/* Panel blanking is authoritative: do not continuously pin CPU clocks. */
static bool ay_screen_on = true;
module_param(ay_screen_on, bool, 0444);
static bool ay_screenoff_saver = true;
module_param(ay_screenoff_saver, bool, 0644);
static bool ay_instantwake = true;
module_param(ay_instantwake, bool, 0644);
static unsigned int ay_wake_boost_pct = 82;
module_param(ay_wake_boost_pct, uint, 0644);
static unsigned int ay_wake_boost_ms = 155;
module_param(ay_wake_boost_ms, uint, 0644);
static atomic_t ay_wake_pending = ATOMIC_INIT(0);
""",
    "screen and wake parameters"
)
change(
    "static unsigned int ay_input_boost_pct = 60;",
    "static unsigned int ay_input_boost_pct = 72;",
    "higher responsive input default"
)
change(
    "static unsigned int input_boost_ms = 90;",
    "static unsigned int input_boost_ms = 105;",
    "bounded input duration"
)

# Use the existing V5 kernel CPUFreq boost driver, not a new governor.
change(
    "static unsigned int ay_dynamic_input_boost_khz(unsigned int cpu)\n",
    "static unsigned int ay_dynamic_input_boost_khz(unsigned int cpu, bool wake)\n",
    "boost function signature"
)
change(
    "    pct = min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 75);\n",
    """    pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)
               : min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78);
""",
    "profile-specific frequency ceiling"
)
change(
    "static void do_input_boost(struct work_struct *work)\n{\n"
    "\tunsigned int i, ret;\n"
    "\tunsigned int boost = READ_ONCE(sched_boost_on_input);\n",
    """static void do_input_boost(struct work_struct *work)
{
    unsigned int i, ret;
    bool wake;
    unsigned int duration;
    unsigned int boost = READ_ONCE(sched_boost_on_input);
""",
    "worker local variables"
)
change(
    "\tstruct cpu_sync *i_sync_info;\n\n"
    "\tcancel_delayed_work_sync(&input_boost_rem);",
    """\tstruct cpu_sync *i_sync_info;

    /* Off-screen input, including the DT2W gesture itself, never boosts
     * until the primary display actually begins to unblank.
     */
    if (!READ_ONCE(ay_screen_on)) {
        atomic_set(&ay_wake_pending, 0);
        mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
        return;
    }

    wake = atomic_xchg(&ay_wake_pending, 0) != 0;
    if (!READ_ONCE(ay_instantwake))
        wake = false;

\tcancel_delayed_work_sync(&input_boost_rem);

    if (!READ_ONCE(ay_screen_on)) {
        mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
        return;
    }
""",
    "screen safety around cancellation"
)
change(
    "\t\t\ti_sync_info->input_boost_min = ay_dynamic_input_boost_khz(i);",
    "\t\t\ti_sync_info->input_boost_min = ay_dynamic_input_boost_khz(i, wake);",
    "dynamic boost profile"
)
change(
    "\tqueue_delayed_work(cpu_boost_wq, &input_boost_rem,\n"
    "\t\t\t\t\tmsecs_to_jiffies(min_t(unsigned int,\n"
    "\t\t\t\t\t\tREAD_ONCE(input_boost_ms), 120)));",
    """    duration = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)
                    : min_t(unsigned int, READ_ONCE(input_boost_ms), 140);
    queue_delayed_work(cpu_boost_wq, &input_boost_rem,
                       msecs_to_jiffies(max_t(unsigned int, duration, 1)));
""",
    "short bounded boost duration"
)
change(
    "\tif (!READ_ONCE(input_boost_enabled) &&\n"
    "\t    !READ_ONCE(ay_auto_input_boost))\n"
    "\t\treturn;",
    """\tif (!READ_ONCE(ay_screen_on))
        return;

\tif (!READ_ONCE(input_boost_enabled) &&
\t    !READ_ONCE(ay_auto_input_boost))
\t\treturn;""",
    "input event must not boost with display off"
)

# Panel notifications trigger a near-immediate worker for each transition.
# No periodic polling: no additional wakeups while the phone is asleep.
notifier = """#if defined(CONFIG_DRM_MSM) || defined(CONFIG_FB_NOTIFY)
static int ay_display_notifier(struct notifier_block *nb,
                               unsigned long event, void *data)
{
    int *blank;
#ifdef CONFIG_DRM_MSM
    struct msm_drm_notifier *panel = data;

    if (event != MSM_DRM_EARLY_EVENT_BLANK &&
        event != MSM_DRM_EVENT_BLANK)
        return NOTIFY_DONE;
    if (!panel || panel->id != MSM_DRM_PRIMARY_DISPLAY || !panel->data)
        return NOTIFY_DONE;
    blank = panel->data;
    if (*blank != MSM_DRM_BLANK_POWERDOWN &&
        *blank != MSM_DRM_BLANK_UNBLANK)
        return NOTIFY_DONE;
#else
    struct fb_event *panel = data;

    if (event != FB_EARLY_EVENT_BLANK && event != FB_EVENT_BLANK)
        return NOTIFY_DONE;
    if (!panel || !panel->data)
        return NOTIFY_DONE;
    blank = panel->data;
    if (*blank != FB_BLANK_POWERDOWN && *blank != FB_BLANK_UNBLANK)
        return NOTIFY_DONE;
#endif

    if (!READ_ONCE(ay_screenoff_saver))
        return NOTIFY_DONE;

#ifdef CONFIG_DRM_MSM
    if (*blank == MSM_DRM_BLANK_POWERDOWN) {
#else
    if (*blank == FB_BLANK_POWERDOWN) {
#endif
        if (READ_ONCE(ay_screen_on)) {
            WRITE_ONCE(ay_screen_on, false);
            atomic_set(&ay_wake_pending, 0);
            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
        }
    } else if (!READ_ONCE(ay_screen_on)) {
        WRITE_ONCE(ay_screen_on, true);
        if (READ_ONCE(ay_instantwake) &&
            (READ_ONCE(ay_auto_input_boost) ||
             READ_ONCE(input_boost_enabled))) {
            atomic_set(&ay_wake_pending, 1);
            queue_work(cpu_boost_wq, &input_boost_work);
        }
    }
    return NOTIFY_OK;
}

static struct notifier_block ay_display_nb = {
    .notifier_call = ay_display_notifier,
};
#endif

"""
change(
    "static int cpu_boost_init(void)\n{\n",
    notifier + "static int cpu_boost_init(void)\n{\n",
    "panel notifier"
)
change(
    "\tret = input_register_handler(&cpuboost_input_handler);\n"
    "\treturn 0;",
    """    ret = input_register_handler(&cpuboost_input_handler);
    if (ret) {
        pr_err("AY: failed to register input booster (%d)\\n", ret);
        return ret;
    }

#if defined(CONFIG_DRM_MSM)
    ret = msm_drm_register_client(&ay_display_nb);
#elif defined(CONFIG_FB_NOTIFY)
    ret = fb_register_client(&ay_display_nb);
#else
    ret = 0;
#endif
    if (ret)
        pr_warn("AY: panel notifier unavailable; off-screen boost guard unverified (%d)\\n",
                ret);
    return 0;""",
    "register panel notifications"
)

required = [
    "module_param(ay_screen_on, bool, 0444);",
    "static bool ay_screenoff_saver = true;",
    "static bool ay_instantwake = true;",
    "static unsigned int ay_wake_boost_pct = 82;",
    "static unsigned int ay_wake_boost_ms = 155;",
    "static unsigned int ay_input_boost_pct = 72;",
    "static unsigned int input_boost_ms = 105;",
    "pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78)",
    "min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)",
    "min_t(unsigned int, READ_ONCE(input_boost_ms), 140)",
    "if (!READ_ONCE(ay_screen_on))",
    "atomic_xchg(&ay_wake_pending, 0)",
    "mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0)",
    "MSM_DRM_PRIMARY_DISPLAY",
    "msm_drm_register_client(&ay_display_nb)",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_cpu_put(policy)",
    "sched_set_boost(-(int)sched_boost_active)",
]
for item in required:
    assert item in src, item

p.write_text(src)
print("V6 screen-off aware HyperSpeed staged: no input boost while screen off,")
print("quick release of existing CPU/WALT boosts and 155-ms 82% wake response.")
print("Schedutil, SELinux, DT2W, Root, thermal and all vendor DTBs unchanged.")
