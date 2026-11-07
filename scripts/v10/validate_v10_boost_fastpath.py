#!/usr/bin/env python3
"""V10.1 source and state-machine checks for the nonblocking boost fast path."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cpu = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
touch = (root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()

for token in (
    "#include <linux/spinlock.h>",
    "static bool ay_v10_boost_fastpath = true;",
    "module_param_named(ay_v10_boost_fastpath, ay_v10_boost_fastpath, bool, 0600);",
    "static DEFINE_SPINLOCK(ay_v10_boost_state_lock);",
    "static unsigned long ay_v10_boost_expires;",
    "spin_lock_irqsave(&ay_v10_boost_state_lock, flags);",
    "spin_unlock_irqrestore(&ay_v10_boost_state_lock, flags);",
    "time_before(jiffies, ay_v10_boost_expires)",
    "READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1)",
    "READ_ONCE(sched_boost_active) == boost",
    "duration_jiffies = msecs_to_jiffies(max_t(unsigned int, duration, 1));",
    "queue_delayed_work(cpu_boost_wq, &input_boost_rem, duration_jiffies);",
    "INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_verify_within_limits(policy, 0, floor);",
):
    assert token in cpu, token

assert cpu.count("cancel_delayed_work_sync(&input_boost_rem);") == 1
fn = cpu[cpu.index("static void do_input_boost(struct work_struct *work)"):]

fast = fn.index("if (!wake && READ_ONCE(ay_v10_boost_fastpath)")
cancel = fn.index("cancel_delayed_work_sync(&input_boost_rem);")
screen_recheck = fn.index("if (!READ_ONCE(ay_screen_on))", cancel)
policy = fn.index("update_policy_online();")
profile_arm = fn.index("WRITE_ONCE(ay_v9_boost_profile, wake ? 3 : (nav ? 2 : 1));")
assert fast < cancel < screen_recheck < policy < profile_arm

# The fast path is strictly same-profile, screen-on, non-wake, unexpired.
assert "if (!wake && READ_ONCE(ay_v10_boost_fastpath)" in fn
assert "READ_ONCE(ay_v9_boost_profile) == (nav ? 2 : 1)" in fn
assert "READ_ONCE(ay_screen_on)" in fn[fast:cancel]
assert "time_before(jiffies, ay_v10_boost_expires)" in fn[fast:cancel]
assert "mod_delayed_work(cpu_boost_wq, &input_boost_rem," in fn[fast:cancel]
assert "if (!READ_ONCE(ay_screen_on))" in fn[fast:cancel]

# Expiry checks the latest deadline before clearing state. Screen-off wins.
expiry = cpu[cpu.index("static void do_input_boost_rem(struct work_struct *work)"):
             cpu.index("static void do_input_boost(struct work_struct *work)")]
assert expiry.index("time_before(jiffies, ay_v10_boost_expires)") < expiry.index("WRITE_ONCE(ay_v9_boost_profile, 0);")
assert "if (READ_ONCE(ay_screen_on) &&" in expiry
assert "mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);" in expiry

# Preserve all previous bounded profiles and the 100ms input event throttle.
for key, value in (
    ("ay_input_boost_pct", 78), ("input_boost_ms", 115),
    ("ay_nav_boost_pct", 82), ("ay_nav_boost_ms", 145),
    ("ay_wake_boost_pct", 85), ("ay_wake_boost_ms", 170),
):
    assert f"static unsigned int {key} = {value};" in cpu
assert "#define MIN_INPUT_INTERVAL (100 * USEC_PER_MSEC)" in cpu
assert "uint8_t DouTap_enable = 1;" in touch
assert "ts->gesture_enable = 1;" in touch

for forbidden in (
    "pm_stay_awake(", "pm_wakeup_event(", "wake_lock(",
    "schedule_delayed_work(&input_boost_rem", "thermal_disable",
    "selinux_enforcing = 0", "policy->max =",
):
    assert forbidden not in cpu, forbidden

# Deterministic state-machine model: a renewal extends only a live, matching
# foreground profile. A wake/profile transition, screen-off, or expired
# deadline falls back to the full path. Expiry cannot clear a newer deadline.
def try_reuse(screen_on, wake, enabled, old_profile, new_profile,
              old_sched, new_sched, now, expires):
    return (screen_on and not wake and enabled and
            old_profile == new_profile and old_sched == new_sched and
            now < expires)

cases = [
    ((True, False, True, 1, 1, 3, 3, 100, 115), True),
    ((True, False, True, 2, 2, 3, 3, 200, 220), True),
    ((True, False, True, 1, 2, 3, 3, 100, 115), False),
    ((True, True, True, 3, 1, 3, 3, 100, 115), False),
    ((False, False, True, 1, 1, 3, 3, 100, 115), False),
    ((True, False, False, 1, 1, 3, 3, 100, 115), False),
    ((True, False, True, 1, 1, 3, 3, 115, 115), False),
    ((True, False, True, 1, 1, 2, 3, 100, 115), False),
]
for args, expected in cases:
    assert try_reuse(*args) is expected, (args, expected)

# Expiry ordering: input renews first -> expiry observes the new future
# deadline; expiry clears first -> profile becomes zero and renewal is refused.
now, expires = 100, 115
renewed_expires = 100 + 115
assert now < renewed_expires
assert 110 < renewed_expires
cleared_profile = 0
assert not try_reuse(True, False, True, cleared_profile, 1, 3, 3, 110, renewed_expires)

print("PASS: V10.1 nonblocking same-profile renewal and expiry race model")
print("PASS: wake/profile transitions, screen-off, thermal bounds, DT2W and DeepDoze preserved")
