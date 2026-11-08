#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c","uint8_t DouTap_enable = 1;"),
("kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c","ts->gesture_enable = 1;"),
("kernel/drivers/cpufreq/cpu-boost.c","MSM_DRM_BLANK_POWERDOWN"),
("kernel/drivers/cpufreq/cpu-boost.c","MSM_DRM_BLANK_UNBLANK"),
("kernel/drivers/cpufreq/cpu-boost.c","ay_deepdoze_delay_seconds = 600"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
print("PASS: touch gesture, panel wake and DeepDoze contracts.")
