#!/system/bin/sh
# Read-only storage/I/O snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "MOUNTS"; mount | grep -E 'f2fs|ext4|/data|/metadata'
section "SPACE"; df -h /data /metadata 2>/dev/null
section "BLOCK STATS"; readp /proc/diskstats
section "IO PRESSURE"; readp /proc/pressure/io
section "BLOCK QUEUES"; for d in /sys/block/*; do [ -d "$d/queue" ] || continue; for f in scheduler nr_requests read_ahead_kb rotational; do readp "$d/queue/$f"; done; done
section "F2FS"; for f in /sys/fs/f2fs/*/features /sys/fs/f2fs/*/gc_idle /sys/fs/f2fs/*/dirty_nat_ratio; do readp "$f"; done
section "END"; echo "Read-only: no scheduler, queue or filesystem setting changed."
