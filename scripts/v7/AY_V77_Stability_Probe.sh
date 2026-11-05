#!/system/bin/sh
# AY V7.7 STABLE BASELINE: read-only, 3 snapshots (0, 5, 10 seconds).
# No swap reset, property writes, service restarts, governors, timers, reboot or flashing.
set -u
OUT=/sdcard/Download/AY_V77_Stability_Report.txt
if ! ( : > "$OUT" ) 2>/dev/null; then
  echo 'Cannot create /sdcard/Download/AY_V77_Stability_Report.txt' >&2
  exit 1
fi

print_file() {
  f=$1
  if [ -r "$f" ]; then
    echo "PATH $f"
    cat "$f" 2>/dev/null || :
  else
    echo "UNAVAILABLE $f"
  fi
}

prop() {
  printf 'PROP %s=' "$1"
  getprop "$1" 2>/dev/null || :
}

snapshot() {
  label=$1
  echo "=== SAMPLE t=$label ==="
  echo "TIME_EPOCH $(date +%s 2>/dev/null || echo unavailable)"
  for p in memory io cpu; do
    f="/proc/pressure/$p"
    if [ -r "$f" ]; then
      while IFS= read -r line; do echo "PSI $p $line"; done < "$f"
    fi
  done
  if [ -r /proc/vmstat ]; then
    awk '/^(pgscan_kswapd|pgsteal_kswapd|pgscan_direct|pgsteal_direct|pswpin|pswpout|allocstall|workingset_refault|oom_kill|pgmajfault|compact_fail|compact_success)( |$|_)/ { print "VM",$1,$2 }' /proc/vmstat
  fi
  if [ -r /proc/meminfo ]; then
    awk '/^(MemAvailable|MemFree|MemTotal|SwapFree|SwapTotal|SReclaimable|SUnreclaim|CmaFree):/ { print "MEM",$1,$2,"kB" }' /proc/meminfo
  fi
  for f in /sys/block/zram0/mm_stat /sys/block/zram0/io_stat /sys/kernel/ay_shadow/telemetry /proc/ay_reclaim_status; do
    if [ -r "$f" ]; then
      printf 'STATE %s ' "$f"
      tr '\n' ';' < "$f" 2>/dev/null
      printf '\n'
    fi
  done
  for c in /proc/[0-9]*/comm; do
    [ -r "$c" ] || continue
    IFS= read -r comm < "$c" || :
    case "$comm" in
      kswapd*)
        pid=$(basename "$(dirname "$c")")
        if [ -r "/proc/$pid/stat" ]; then
          awk -v pid="$pid" -v name="$comm" '{print "KSWAPD",pid,name,"utime_ticks=" $14,"stime_ticks=" $15}' "/proc/$pid/stat" 2>/dev/null || :
        fi
      ;;
    esac
  done
  echo '=== END SAMPLE ==='
}
{
  echo 'AY V7.7 MEMORY AND THERMAL HAL FORENSICS -- READ ONLY'
  date '+%Y-%m-%d %H:%M:%S %z' 2>/dev/null || :
  echo '=== DEVICE ==='
  uname -r
  for p in ro.product.device ro.build.version.release ro.build.version.sdk ro.vendor.build.version.sdk ro.vendor.build.version.security_patch ro.lmk.use_psi ro.lmk.thrashing_limit ro.lmk.enable_userspace_lmk ro.config.low_ram; do prop "$p"; done
  echo '=== THERMAL HAL ==='
  for p in init.svc.vendor.thermal-hal init.svc.thermal-engine init.svc.vendor.power-hal-aidl; do prop "$p"; done
  for f in /vendor/bin/hw/android.hardware.thermal-service.realme_sm7125 /vendor/etc/init/android.hardware.thermal-service.realme_sm7125.rc /vendor/etc/vintf/manifest/android.hardware.thermal-service.realme_sm7125.xml /sys/kernel/boot_adsp/boot; do
    if [ -e "$f" ]; then ls -l "$f" 2>/dev/null || :; else echo "MISSING $f"; fi
  done
  echo '=== THERMAL INIT DECLARATION ==='
  f=/vendor/etc/init/android.hardware.thermal-service.realme_sm7125.rc
  [ -r "$f" ] && grep -nE '^(service |    interface |    class |    user |    group |on boot|    wait |    restart )' "$f" || :
  echo '=== THERMAL VINTF DECLARATION ==='
  f=/vendor/etc/vintf/manifest/android.hardware.thermal-service.realme_sm7125.xml
  [ -r "$f" ] && grep -nE '<(hal|name|fqname)' "$f" || :
  echo '=== THERMAL RELEVANT INIT LOGS (LAST 75) ==='
  logcat -d -b all -t 2200 2>/dev/null | grep -iE 'thermal-hal|IThermal/default|thermal-service.realme|boot_adsp/boot|avc: denied|lmkd.*(kill|thrash)' | tail -n 75 || :
  echo '=== THERMAL RELEVANT KERNEL LOGS (LAST 50) ==='
  dmesg 2>/dev/null | grep -iE 'thermal|therm|adsp|avc: denied' | tail -n 50 || :
  echo '=== RECLAIM CONFIG ==='
  for f in /proc/sys/vm/kswapd_threads /proc/sys/vm/swappiness /proc/sys/vm/direct_swappiness /proc/sys/vm/page-cluster /proc/sys/vm/watermark_scale_factor /proc/sys/vm/min_free_kbytes /sys/fs/cgroup/memory/bg/memory.swappiness /sys/block/zram0/comp_algorithm /sys/block/zram0/use_dedup; do print_file "$f"; done
  echo '=== SWAP AND ZONES ==='
  print_file /proc/swaps
  print_file /proc/buddyinfo
  snapshot 0
  sleep 5
  snapshot 5
  sleep 5
  snapshot 10
  echo '=== END; READ-ONLY, NO REBOOT ==='
} > "$OUT" 2>&1
chmod 0600 "$OUT" 2>/dev/null || :
printf 'Report saved: %s\n' "$OUT"
