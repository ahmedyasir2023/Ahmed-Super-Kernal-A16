#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[3]
FILES=["kernel/drivers/input/touchscreen/oppo_touchscreen/touchpanel_common_driver.c","kernel/drivers/cpufreq/cpu-boost.c"]
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing: raise SystemExit("Missing source inputs: "+", ".join(missing))
audit=ROOT/"audit"; audit.mkdir(exist_ok=True)
lines=["track=input-touch","mode=read-only-source-audit"]
for p in FILES: lines.append(p+" sha256="+hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
(audit/"parallel-input-touch-source-audit.txt").write_text("\n".join(lines)+"\n")
print("PASS: input/touch sources fingerprinted; kernel files unchanged.")
