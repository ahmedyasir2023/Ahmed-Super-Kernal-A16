#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/block/blk-core.c","submit_bio"),
("kernel/block/blk-core.c","blk_start_plug"),
("kernel/block/blk-core.c","blk_finish_plug"),
("kernel/fs/f2fs/super.c","f2fs_mount"),
("kernel/fs/f2fs/super.c","f2fs_put_super"),
("kernel/drivers/block/zram/zram_drv.c","mm_stat"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
print("PASS: block dispatch, F2FS and ZRAM source contracts.")
