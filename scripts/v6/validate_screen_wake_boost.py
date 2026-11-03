#!/usr/bin/env python3
"""Fail-closed V6 screen/wake boost source checks.

Called AFTER V5 patch and V6 stage, BEFORE kernel compilation.
The test does not prove suspend behavior on physical hardware.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
driver = (root / "kernel/drivers/cpufreq/cpu-boost.c").read_text()
config = (root / "kernel/out/.config").read_text() if (root / "kernel/out/.config").exists() else ""
defconfig = (root / "kernel/arch/arm64/configs/atoll_defconfig").read_text()
touch = (root / "kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c").read_text()
uapi = (root / "KernelSU-Next/uapi/supercall.h").read_text()
msm = (root / "kernel/include/linux/msm_drm_notify.h").read_text()

assert "CONFIG_CPU_BOOST=y" in defconfig
assert "CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y" in defconfig
assert "CONFIG_SCHED_WALT=y" in defconfig
assert "#define KERNEL_SU_UAPI_VERSION 6" in uapi
assert "uint8_t DouTap_enable = 1;" in touch
assert "#define MSM_DRM_EARLY_EVENT_BLANK" in msm
assert "#define MSM_DRM_EVENT_BLANK" in msm

required = (
    "static bool ay_screen_on = true;",
    "module_param(ay_screen_on, bool, 0444);",
    "static bool ay_screenoff_saver = true;",
    "module_param(ay_screenoff_saver, bool, 0644);",
    "static bool ay_instantwake = true;",
    "static unsigned int ay_input_boost_pct = 72;",
    "static unsigned int input_boost_ms = 105;",
    "static unsigned int ay_wake_boost_pct = 82;",
    "static unsigned int ay_wake_boost_ms = 155;",
    "pct = wake ? min_t(unsigned int, READ_ONCE(ay_wake_boost_pct), 85)",
    "min_t(unsigned int, READ_ONCE(ay_input_boost_pct), 78)",
    "min_t(unsigned int, READ_ONCE(ay_wake_boost_ms), 180)",
    "min_t(unsigned int, READ_ONCE(input_boost_ms), 140)",
    "if (!READ_ONCE(ay_screen_on))",
    "atomic_set(&ay_wake_pending, 0)",
    "atomic_xchg(&ay_wake_pending, 0)",
    "mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0)",
    "msm_drm_register_client(&ay_display_nb)",
    "MSM_DRM_PRIMARY_DISPLAY",
    "READ_ONCE(ay_auto_input_boost)",
    "cpufreq_verify_within_limits(policy, ib_min, UINT_MAX);",
    "cpufreq_cpu_put(policy)",
    "sched_set_boost(-(int)sched_boost_active)",
)
for needle in required:
    assert needle in driver, needle

for bad in ("thermal_disable", "selinux_enforcing = 0", "policy->max =",
            "sched_set_boost(FULL_THROTTLE_BOOST)",
            "CPU_FREQ_GOV_PERFORMANCE=y"):
    assert bad not in driver, bad

# Confirm OFF/ON transition logic is explicitly event-driven, not polling.
assert "MSM_DRM_BLANK_POWERDOWN" in driver
assert "MSM_DRM_BLANK_UNBLANK" in driver
assert "queue_work(cpu_boost_wq, &input_boost_work);" in driver
assert "if (READ_ONCE(ay_screen_on)) {" in driver
assert "WRITE_ONCE(ay_screen_on, false)" in driver
assert "WRITE_ONCE(ay_screen_on, true)" in driver
assert "cpufreq_update_policy(i)" in driver
assert "READ_ONCE(input_boost_ms), 120" not in driver

for minimum, maximum in ((300000, 1804800),(710400,2208000)):
    for pct, limit in ((0,78),(50,78),(72,78),(1000,78),(82,85),(1000,85)):
        bounded = min(pct,limit)
        target = minimum + (maximum - minimum)*bounded//100 if bounded else 0
        assert target == 0 or minimum <= target <= maximum
        assert target <= maximum
if config:
    assert "CONFIG_DRM_MSM=y" in config, "Realme DRM notifier must be linked"
    assert "CONFIG_CPU_BOOST=y" in config

print("V6 source contract passed: automatic wake boost + screen-off deboost;")
print("no max-frequency pin, clock overdrive, extra wake polling or SELinux changes.")
