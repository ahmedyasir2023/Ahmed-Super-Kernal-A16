#!/usr/bin/env python3
"""Validate only the source-level formatting repair, not memory stability."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
src = (root / "kernel/drivers/block/zram/zram_drv.c").read_text()
begin = src.index("static ssize_t mm_stat_show(")
end = src.index("#ifdef CONFIG_ZRAM_WRITEBACK", begin)
block = src[begin:end]
fmt = '"%8llu %8llu %8llu %8lu %8ld %8llu %8lu\\n",'
assert block.count(fmt) == 1, "mm_stat must publish exactly 7 supported fields"
assert len(re.findall(r"%(?:\\d+)?(?:llu|lu|ld)", fmt)) == 7
assert block.count("scnprintf(") == 1
required = (
    "orig_size << PAGE_SHIFT,",
    "(u64)atomic64_read(&zram->stats.compr_data_size),",
    "mem_used << PAGE_SHIFT,",
    "zram->limit_pages << PAGE_SHIFT,",
    "max_used << PAGE_SHIFT,",
    "(u64)atomic64_read(&zram->stats.same_pages),",
    "atomic_long_read(&pool_stats.pages_compacted)",
)
assert all(block.count(item) == 1 for item in required), "ZRAM stats semantics changed"
for danger in ("atomic64_set(", "atomic64_sub(", "zram_dedup_fini(", "zram_entry_free(", "zram_free_page("):
    assert danger not in block, "Unexpected behavioral modification to mm_stat"
print("V7.2 ZRAM mm_stat seven-field contract: PASS")
