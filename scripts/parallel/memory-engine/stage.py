#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[3]
FILES=['kernel/mm/vmscan.c','kernel/mm/page_alloc.c','kernel/mm/multi_kswapd/multi_kswapd.c','kernel/drivers/block/zram/zram_drv.c']
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing: raise SystemExit('Missing source inputs: '+', '.join(missing))
audit=ROOT/'audit'; audit.mkdir(exist_ok=True)
lines=['track=memory-engine','mode=read-only-source-audit']
for p in FILES: lines.append(p+' sha256='+hashlib.sha256((ROOT/p).read_bytes()).hexdigest())
(audit/'parallel-memory-engine-source-audit.txt').write_text('\n'.join(lines)+'\n')
print('PASS: memory source inputs fingerprinted; kernel files unchanged.')
