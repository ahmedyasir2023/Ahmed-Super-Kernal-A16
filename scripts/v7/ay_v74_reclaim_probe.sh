#!/system/bin/sh
# Read-only snapshot. No persistent tuning and no background process.
echo '=== KERNEL ==='
uname -r
echo '=== VM ==='
for f in /proc/sys/vm/swappiness /proc/sys/vm/direct_swappiness /proc/sys/vm/kswapd_threads /proc/sys/vm/watermark_scale_factor /sys/fs/cgroup/memory/bg/memory.swappiness /sys/block/zram0/use_dedup; do
  [ -r "$f" ] && { printf '%s = ' "$f"; cat "$f"; }
done
echo '=== ZRAM ==='
cat /sys/block/zram0/mm_stat
[ -r /sys/block/zram0/dedup_stat ] && cat /sys/block/zram0/dedup_stat
echo '=== PRESSURE ==='
cat /proc/pressure/memory
cat /proc/pressure/io
echo '=== ZONES ==='
cat /proc/buddyinfo
echo '=== RECLAIM 0 ==='
grep -E '^(pgscan_kswapd|pgsteal_kswapd|pgscan_direct|pgsteal_direct|pswpin|pswpout|allocstall)' /proc/vmstat
sleep 5
echo '=== RECLAIM 5 ==='
grep -E '^(pgscan_kswapd|pgsteal_kswapd|pgscan_direct|pgsteal_direct|pswpin|pswpout|allocstall)' /proc/vmstat
