#!/system/bin/sh
# AY V7.7: finite, READ-ONLY memory PSI flight recorder.
set -u
OUT=/sdcard/Download/AY_V77_Live_Stall_Report.txt
if [ "$(id -u)" != 0 ] || [ ! -r /proc/pressure/memory ]; then echo 'Need root and PSI'; exit 1; fi
if [ "$(getprop init.svc.vendor.thermal-hal)" != running ] || [ "$(getprop init.svc.thermal-engine)" != running ]; then echo 'Thermal services must run'; exit 1; fi
if ! grep -q '^reclaim_progress_enabled=0$' /proc/ay_reclaim_status; then echo 'Reclaim baseline must be 0'; exit 1; fi
avg() {
  awk '$1=="full" {for(i=2;i<=NF;i++) if($i ~ /^avg10=/) {split($i,a,"=");print a[2];exit}}' /proc/pressure/memory
}
sample() {
  echo "=== SAMPLE idx=$1 ==="
  echo "TIME_EPOCH $(date +%s)"
  for p in memory cpu io; do
    [ -r "/proc/pressure/$p" ] || continue
    while IFS= read -r line; do echo "PSI $p $line"; done < "/proc/pressure/$p"
  done
  awk '/^(pgscan_kswapd|pgsteal_kswapd|pgscan_direct|pgsteal_direct|pswpin|pswpout|workingset_refault|pgmajfault|allocstall|oom_kill)(_| )/ {print "VM",$1,$2}' /proc/vmstat
  awk '/^(MemAvailable|MemFree|SwapFree|SwapTotal):/ {print "MEM",$1,$2}' /proc/meminfo
  awk '/^Node [0-9]+, zone / {print "ZONE",$0} /^[ \t]+(pages free|min|low|high|managed) / {print "ZONE",$0}' /proc/zoneinfo
  [ -r /sys/block/zram0/mm_stat ] && echo "ZRAM_MM $(cat /sys/block/zram0/mm_stat)"
  while IFS= read -r line; do echo "RECLAIM $line"; done < /proc/ay_reclaim_status
  for p in /proc/[0-9]*/comm; do
    [ -r "$p" ] || continue
    IFS= read -r name < "$p" || :
    case "$name" in kswapd*)
      pid=$(basename "$(dirname "$p")")
      [ -r "/proc/$pid/stat" ] && awk -v p="$pid" '{print "KSWAPD",p,"ticks=" $14+$15}' "/proc/$pid/stat" 2>/dev/null || :
    ;; esac
  done
  echo '=== END SAMPLE ==='
}
: > "$OUT" || exit 1
{
  echo 'AY_V77_LIVE_STALL_V1'
  echo "KERNEL $(uname -r)"
  echo 'READ_ONLY=1'
  n=0
  i=0
  triggered=0
  while [ "$i" -lt 20 ]; do
    if [ "$(getprop init.svc.vendor.thermal-hal)" != running ]; then echo 'HAL_STOPPED'; exit 1; fi
    v=$(avg)
    echo "WATCH idx=$i avg10=$v"
    if awk -v v="$v" 'BEGIN{exit !(v+0>=25)}'; then n=$((n+1)); else n=0; fi
    if [ "$n" -ge 2 ]; then echo "TRIGGERED avg10=$v"; triggered=1; break; fi
    i=$((i+1))
    [ "$i" -lt 20 ] && sleep 3
  done
  if [ "$triggered" = 0 ]; then echo 'NO_TRIGGER';echo COMPLETE;exit 0; fi
  for idx in 0 1 2 3; do
    if ! grep -q '^reclaim_progress_enabled=0$' /proc/ay_reclaim_status; then echo 'MODE_CHANGED'; exit 1; fi
    sample "$idx"
    [ "$idx" -ne 3 ] && sleep 5
  done
  echo COMPLETE
} >> "$OUT" 2>&1
echo "Saved: $OUT"
