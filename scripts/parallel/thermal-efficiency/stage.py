#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[3]
FILES=["kernel/drivers/thermal/thermal_core.c","kernel/drivers/cpufreq/cpu-boost.c","kernel/drivers/gpu/msm/kgsl_pwrctrl.c"]
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing: raise SystemExit("Missing source inputs: "+", ".join(missing))
audit=ROOT/"audit"; audit.mkdir(exist_ok=True)
lines=["track=thermal-efficiency","mode=read-only-source-audit"]
for p in FILES: lines.append(p+" sha256="+hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
(audit/"parallel-thermal-efficiency-source-audit.txt").write_text("\n".join(lines)+"\n")
print("PASS: thermal source inputs fingerprinted; kernel files unchanged.")
