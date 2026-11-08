#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/mm/vmscan.c","static bool ay_v91_bounded_reclaim = false;"),
("kernel/mm/vmscan.c","msecs_to_jiffies(1000)"),
("kernel/mm/page_alloc.c","watermark_scale_factor > 50"),
("kernel/mm/multi_kswapd/multi_kswapd.c","static bool ay_v81_single_kswapd = true;"),
("kernel/drivers/block/zram/zram_drv.c","mm_stat"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
vmscan=(ROOT/"kernel/mm/vmscan.c").read_text(errors="replace")
for token in ("selinux_enforcing = 0","thermal_disable"): assert token not in vmscan, f"Forbidden token: {token}"
print("PASS: conservative reclaim, watermark, kswapd and ZRAM source contracts.")
