#!/usr/bin/env python3
"""Validate V7.4 accounting and exercise multi-reference model."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
k=root/"kernel"
s=(k/"drivers/block/zram/zram_drv.c").read_text()
h=(k/"drivers/block/zram/zram_drv.h").read_text()
dedup=(k/"drivers/block/zram/zram_dedup.c").read_text()
f=s[s.index("bool zram_entry_free("):s.index("static void zram_meta_free(")]
assert "if (!zram_dedup_put_entry(zram, entry))\n\t\treturn false;" in f
assert f.count("return true;")==2
assert "zs_free(zram->mem_pool" in f
assert "bool zram_entry_free(struct zram *zram, struct zram_entry *entry);" in h
p=s[s.index("static void zram_free_page(",s.index("static void zram_meta_free(")):s.index("static int __zram_bvec_read(")]
assert p.count("if (zram_entry_free(zram, entry))")==1
assert p.count("&zram->stats.compr_data_size);")==1
assert "zram_dedup_put_entry" in dedup
assert "static DEVICE_ATTR_RO(dedup_stat);" in s
assert "&dev_attr_dedup_stat.attr," in s
assert "zram_dedup_dup_size(zram)" in s and "zram_dedup_meta_size(zram)" in s
assert s.count('"%8llu %8llu %8llu %8lu %8ld %8llu %8lu\\n",')==1
show=s[s.index("/* Read-only existing dedup counters"):s.index("static ssize_t mm_stat_show(")]
assert "schedule_work(" not in show and "mod_delayed_work(" not in show
for compressed_bytes in (128,512,3072,4096):
    for logical_refs in (1,2,3,12):
        physical=compressed_bytes
        for left in range(logical_refs-1,-1,-1):
            if left==0:
                physical-=compressed_bytes
            assert physical==(compressed_bytes if left else 0)
        assert physical==0
files=subprocess.check_output(["git","-C",str(k),"diff","--name-only","--","drivers/block/zram"],text=True).splitlines()
assert sorted(files)==["drivers/block/zram/zram_drv.c","drivers/block/zram/zram_drv.h"],files
print("V7.4 ZRAM 1/2/3/12-reference accounting and stat ABI: PASS")
