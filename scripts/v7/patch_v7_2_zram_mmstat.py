#!/usr/bin/env python3
"""V7.2: correct zram mm_stat format/argument mismatch in pinned Realme source.

The original 4.14 vendor code passes exactly seven values to scnprintf(), but
has ten format conversions, exposing unrelated stack data as trailing fields.
No compression, reclaim, dedup or swap behavior is changed by this patch.
"""
from pathlib import Path

src = Path(__file__).resolve().parents[2] / "kernel/drivers/block/zram/zram_drv.c"
s = src.read_text()
before = '"%8llu %8llu %8llu %8lu %8ld %8llu %8lu %8llu %8llu %8llu\\n",'
after = '"%8llu %8llu %8llu %8lu %8ld %8llu %8lu\\n",'
assert s.count(before) == 1, "Unexpected vendor mm_stat layout: refuse patch"
assert s.count(after) == 0, "Already patched or unsupported source"
s = s.replace(before, after, 1)
src.write_text(s)
print("V7.2 ZRAM mm_stat: 7 conversions match 7 arguments; memory logic unchanged")
