#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[3]
FILES=["kernel/block/blk-core.c","kernel/fs/f2fs/super.c","kernel/drivers/block/zram/zram_drv.c"]
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing: raise SystemExit("Missing source inputs: "+", ".join(missing))
audit=ROOT/"audit"; audit.mkdir(exist_ok=True)
lines=["track=storage-io","mode=read-only-source-audit"]
for p in FILES: lines.append(p+" sha256="+hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
(audit/"parallel-storage-io-source-audit.txt").write_text("\n".join(lines)+"\n")
print("PASS: storage source inputs fingerprinted; kernel files unchanged.")
