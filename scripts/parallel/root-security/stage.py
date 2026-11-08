#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[3]
FILES=["kernel/kernel/sys.c","KernelSU-Next/uapi/supercall.h","kernel/security/selinux/hooks.c"]
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing: raise SystemExit("Missing source inputs: "+", ".join(missing))
audit=ROOT/"audit"; audit.mkdir(exist_ok=True)
lines=["track=root-security","mode=read-only-source-audit"]
for p in FILES: lines.append(p+" sha256="+hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
(audit/"parallel-root-security-source-audit.txt").write_text("\n".join(lines)+"\n")
print("PASS: root/security source inputs fingerprinted; kernel files unchanged.")
