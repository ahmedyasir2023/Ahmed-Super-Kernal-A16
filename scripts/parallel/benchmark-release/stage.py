#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[3]
FILES=["scripts/verify_boot_dtb.py","scripts/v7/preflash_audit.py",".github/workflows/v10-hypercore-build.yml"]
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing: raise SystemExit("Missing release inputs: "+", ".join(missing))
audit=ROOT/"audit"; audit.mkdir(exist_ok=True)
lines=["track=benchmark-release","mode=read-only-release-input-audit"]
for p in FILES: lines.append(p+" sha256="+hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
(audit/"parallel-benchmark-release-source-audit.txt").write_text("\n".join(lines)+"\n")
print("PASS: release inputs fingerprinted; no image or ZIP created.")
