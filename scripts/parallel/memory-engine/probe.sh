#!/system/bin/sh
# Read-only memory/reclaim snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "MEMORY"; readp /proc/meminfo; readp /proc/pressure/memory; readp /proc/vmstat
section "RECLAIM"; readp /proc/ay_reclaim_status; ps -A -o PID,NAME,THREADS 2>/dev/null | grep -E 'kswapd|lmkd|zygote'
section "ZRAM"; readp /sys/block/zram0/mm_stat; readp /sys/block/zram0/stat; readp /sys/block/zram0/disksize
section "VM TUNABLES"; for f in /proc/sys/vm/swappiness /proc/sys/vm/vfs_cache_pressure /proc/sys/vm/watermark_scale_factor /proc/sys/vm/page-cluster; do readp "$f"; done
section "CPU PRESSURE"; readp /proc/pressure/cpu
section "END"; echo "Read-only: no VM or ZRAM tunables changed."
