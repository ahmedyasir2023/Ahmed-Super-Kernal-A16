#!/system/bin/sh
# AY V7.7: reversible reclaim test. Volatile root-only kernel parameter.
# Keep display ON. Do not invoke if vendor thermal HAL is not running.
# SIGKILL cannot be trapped; after SIGKILL, the knob may stay enabled until reboot.
set -u
OUT=/sdcard/Download/AY_V77_Reclaim_AB_Result.txt
PARAM=''
COUNT=0
for f in /sys/module/*/parameters/ay_reclaim_progress; do
  [ -f "$f" ] || continue
  PARAM="$f"
  COUNT=$((COUNT + 1))
done
if [ "$(id -u)" != 0 ] || [ "$COUNT" -ne 1 ] || [ ! -w "$PARAM" ]; then
  echo 'ABORT: root and exactly one writable ay_reclaim_progress parameter required.'
  exit 1
fi
if [ "$(getprop init.svc.vendor.thermal-hal)" != running ] || [ "$(getprop init.svc.thermal-engine)" != running ]; then
  echo 'ABORT: thermal services are not running.'
  exit 1
fi
if [ ! -r /proc/ay_reclaim_status ] || ! grep -q '^reclaim_progress_enabled=0$' /proc/ay_reclaim_status; then
  echo 'ABORT: V7.7 baseline is not reclaim_progress_enabled=0.'
  exit 1
fi
if [ ! -r /proc/pressure/memory ]; then echo 'ABORT: PSI missing'; exit 1; fi
check_temp() {
  f=/sys/class/power_supply/battery/temp
  [ -r "$f" ] || return 0
  t=$(cat "$f" 2>/dev/null) || return 0
  case "$t" in ''|*[!0-9]*) return 0;; esac
  if [ "$t" -gt 420 ]; then echo "ABORT: battery temperature $t deci-C"; return 1; fi
}
check_temp || exit 1
if ! ( : > "$OUT" ) 2>/dev/null; then echo "Cannot write $OUT"; exit 1; fi
ARMED=0
restore() {
  if [ "$ARMED" -eq 1 ]; then
    if echo 0 > "$PARAM" && grep -q '^reclaim_progress_enabled=0$' /proc/ay_reclaim_status; then
      printf '%s\n' 'RESTORED reclaim_progress_enabled=0' | tee -a "$OUT"
    else
      printf '%s\n' 'RESTORE FAILED: reboot returns this option to 0; inspect the parameter.' | tee -a "$OUT"
    fi
  fi
}
trap restore 0
trap 'exit 130' 2
trap 'exit 143' 15
trap 'exit 129' 1
snapshot() {
  echo "=== $1 ==="
  echo "TIME_EPOCH $(date +%s)"
  grep -E '^(some|full) ' /proc/pressure/memory | sed 's/^/MEM_PSI /'
  awk '/^(pgscan_kswapd|pgsteal_kswapd|pswpin|pswpout|workingset_refault)( |$|_)/ {print "VM", $1, $2}' /proc/vmstat
  grep -E '^(MemAvailable|SwapFree):' /proc/meminfo
  cat /proc/ay_reclaim_status
  for c in /proc/[0-9]*/comm; do
    [ -r "$c" ] || continue
    IFS= read -r name < "$c" || :
    case "$name" in
      kswapd*) pid=$(basename "$(dirname "$c")")
        [ -r "/proc/$pid/stat" ] && awk -v pid="$pid" '{print "KSWAPD",pid,"cpu_ticks=" $14+$15}' "/proc/$pid/stat" 2>/dev/null
        ;;
    esac
  done
}
{
  echo 'AY V7.7 KSWAPD RECLAIM A/B — VOLATILE, RESTORED'
  echo "PARAM=$PARAM"
  echo "KERNEL=$(uname -r)"
  echo 'Keep screen ON and do not run intensive workloads.'
  snapshot 'BASELINE START / mode=0'
  sleep 10
  snapshot 'BASELINE END / mode=0'
  check_temp || exit 1
  ARMED=1
  if ! echo 1 > "$PARAM" || ! grep -q '^reclaim_progress_enabled=1$' /proc/ay_reclaim_status; then
    echo 'ABORT: kernel refused mode 1; restoring mode 0.'
    exit 1
  fi
  echo 'EXPERIMENT: mode=1 for 10 seconds; automatic restore on exit.'
  snapshot 'EXPERIMENT START / mode=1'
  sleep 5
  check_temp || exit 1
  sleep 5
  snapshot 'EXPERIMENT END / mode=1'
  echo 'Test complete; restoring.'
} > "$OUT" 2>&1
printf 'A/B report saved: %s\n' "$OUT"
