#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/drivers/thermal/thermal_core.c","thermal_zone_device_update"),
("kernel/drivers/thermal/thermal_core.c","thermal_cdev_update"),
("kernel/drivers/cpufreq/cpu-boost.c","cpufreq_verify_within_limits"),
("kernel/drivers/gpu/msm/kgsl_pwrctrl.c","kgsl_pwrctrl"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
for rel,token in [("kernel/drivers/thermal/thermal_core.c","thermal_zone_device_disable("),("kernel/drivers/cpufreq/cpu-boost.c","thermal_disable")]:
    assert token not in (ROOT/rel).read_text(errors="replace"), f"Forbidden thermal bypass pattern: {token}"
print("PASS: thermal-zone, cooling-device and bounded CPUFreq contracts.")
