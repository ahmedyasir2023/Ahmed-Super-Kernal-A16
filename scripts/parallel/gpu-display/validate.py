#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/drivers/gpu/msm/kgsl_pwrctrl.c","kgsl_pwrctrl_pwrlevel_change"),
("kernel/drivers/gpu/msm/kgsl_pwrctrl.c","devfreq"),
("kernel/drivers/gpu/msm/kgsl_pwrctrl.c","kgsl_pwrctrl"),
("kernel/drivers/gpu/msm/kgsl.c","kgsl"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
source=(ROOT/"kernel/drivers/gpu/msm/kgsl_pwrctrl.c").read_text(errors="replace")
assert "thermal_disable" not in source
print("PASS: KGSL/devfreq source contract; no thermal-disable pattern.")
