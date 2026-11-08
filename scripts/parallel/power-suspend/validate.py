#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/drivers/cpufreq/cpu-boost.c","ktime_get_boottime()"),
("kernel/drivers/cpufreq/cpu-boost.c","INIT_DEFERRABLE_WORK(&ay_deepdoze_timer, ay_deepdoze_expire);"),
("kernel/drivers/cpufreq/cpu-boost.c","ay_deepdoze_delay_seconds = 600"),
("kernel/drivers/cpufreq/cpu-boost.c","ay_pm_suspend_nb"),
("kernel/kernel/power/suspend.c","suspend_devices_and_enter"),
("kernel/drivers/base/power/wakeup.c","wakeup_source"),
]
for rel,token in CHECKS:
    assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
cpu=(ROOT/"kernel/drivers/cpufreq/cpu-boost.c").read_text(errors="replace")
for token in ("pm_stay_awake(","pm_wakeup_event(","wake_lock("):
    assert token not in cpu, f"DeepDoze CPUBoost must not add wake source: {token}"
print("PASS: power/suspend source contracts; no added CPUBoost wakelock.")
