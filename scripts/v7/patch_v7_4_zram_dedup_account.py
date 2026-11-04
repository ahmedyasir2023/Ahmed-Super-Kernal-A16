#!/usr/bin/env python3
"""Correct ZRAM compressed-byte accounting for shared dedup objects."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=root/"kernel/drivers/block/zram/zram_drv.c"
h=root/"kernel/drivers/block/zram/zram_drv.h"
s=c.read_text()
hdr=h.read_text()
def one(old,new,label):
    global s
    assert s.count(old)==1,"Unexpected vendor layout: "+label
    s=s.replace(old,new,1)
one("void zram_entry_free(struct zram *zram, struct zram_entry *entry)\n",
    "bool zram_entry_free(struct zram *zram, struct zram_entry *entry)\n","return type")
one("\tif (!zram_dedup_put_entry(zram, entry))\n\t\treturn;\n",
    "\tif (!zram_dedup_put_entry(zram, entry))\n\t\treturn false;\n","shared reference")
one("\tif (!zram_dedup_enabled(zram))\n\t\treturn;\n\n\tkfree(entry);\n",
    "\tif (!zram_dedup_enabled(zram))\n\t\treturn true;\n\n\tkfree(entry);\n","non-dedup return")
one("\tatomic64_sub(sizeof(*entry), &zram->stats.meta_data_size);\n}\n",
    "\tatomic64_sub(sizeof(*entry), &zram->stats.meta_data_size);\n\treturn true;\n}\n","final release")
one("\tzram_entry_free(zram, entry);\n\n\tatomic64_sub(zram_get_obj_size(zram, index),\n\t\t\t&zram->stats.compr_data_size);\n",
    "\t/* Count compressed bytes only on the last physical release. */\n"
    "\tif (zram_entry_free(zram, entry))\n"
    "\t\tatomic64_sub(zram_get_obj_size(zram, index),\n"
    "\t\t\t\t&zram->stats.compr_data_size);\n","accounting")
a="void zram_entry_free(struct zram *zram, struct zram_entry *entry);"
assert hdr.count(a)==1
hdr=hdr.replace(a,"/* True only when physical backing was freed. */\nbool zram_entry_free(struct zram *zram, struct zram_entry *entry);",1)
stat=r'''
/* Read-only existing dedup counters; no background sampling. */
static ssize_t dedup_stat_show(struct device *dev,
        struct device_attribute *attr, char *buf)
{
    struct zram *zram = dev_to_zram(dev);
    ssize_t ret;

    down_read(&zram->init_lock);
    ret = scnprintf(buf, PAGE_SIZE, "%llu %llu\n",
            (u64)zram_dedup_dup_size(zram),
            (u64)zram_dedup_meta_size(zram));
    up_read(&zram->init_lock);
    return ret;
}

'''
one("static ssize_t mm_stat_show(struct device *dev,\n",stat+"static ssize_t mm_stat_show(struct device *dev,\n","read-only counters")
one("static DEVICE_ATTR_RO(initstate);\n","static DEVICE_ATTR_RO(initstate);\nstatic DEVICE_ATTR_RO(dedup_stat);\n","attribute")
one("\t&dev_attr_mm_stat.attr,\n","\t&dev_attr_mm_stat.attr,\n\t&dev_attr_dedup_stat.attr,\n","sysfs list")
assert s.count('"%8llu %8llu %8llu %8lu %8ld %8llu %8lu\\n",')==1
c.write_text(s)
h.write_text(hdr)
print("V7.4 ZRAM integrity patch applied (dedup accounting + read-only stats)")
