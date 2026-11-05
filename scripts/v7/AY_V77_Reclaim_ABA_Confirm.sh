#!/system/bin/sh
# AY V7.7 A-B-A corroboration. No flash, no daemon, no persistent setting.
# Runs A=original, B=opt-in reclaim, A=original while screen is awake.
# Shell trap restores 0. SIGKILL/power loss cannot run traps; reboot defaults 0.
set -u
OUT=/sdcard/Download/AY_V77_Reclaim_ABA_Confirm.txt
PARAM=''
N=0
for f in /sys/module/*/parameters/ay_reclaim_progress; do
  [ -f "$f" ] || continue
  PARAM="$f"
  N=$((N + 1))
done
if [ "$(id -u)" != 0 ] || [ "$N" -ne 1 ] || [ ! -w "$PARAM" ]; then
  echo 'ABORT: require root and exactly one writable reclaim mode parameter.'
  exit 1
fi
if [ "$(getprop init.svc.vendor.thermal-hal)" != running ] || [ "$(getprop init.svc.thermal-engine)" != running ]; then
  echo 'ABORT: both vendor thermal services must be running.'
  exit 1
fi
if [ ! -r /proc/ay_reclaim_status ] || ! grep -q '^reclaim_progress_enabled=0$' /proc/ay_reclaim_status; then
  echo 'ABORT: original V7.7 reclaim mode 0 is required.'
  exit 1
fi
if [ ! -r /proc/pressure/memory ]; then echo 'ABORT: memory PSI unavailable'; exit 1; fi

check_safety() {
  if [ "$(getprop init.svc.vendor.thermal-hal)" != running ]; then
    echo 'ABORT: thermal HAL stopped.'
    return 1
  fi
  if [ -r /sys/class/power_supply/battery/temp ]; then
    t=$(cat /sys/class/power_supply/battery/temp 2>/dev/null) || return 1
    case "$t" in ''|*[!0-9]*) echo 'ABORT: temperature reading invalid'; return 1;; esac
    [ "$t" -le 420 ] || { echo "ABORT: battery temperature too high: $t"; return 1; }
  fi
  if [ -r /sys/kernel/ay_shadow/telemetry ]; then
    if grep -Eq '(^|[ ;])screen_on=0($|[ ;])' /sys/kernel/ay_shadow/telemetry; then
      echo 'ABORT: screen no longer on.'
      return 1
    fi
  fi
  return 0
}
check_safety || exit 1
if ! ( : > "$OUT" ) 2>/dev/null; then echo 'ABORT: output file not writable'; exit 1; fi
ARMED=0
restore() {
  if [ "$ARMED" -eq 1 ]; then
    echo 0 > "$PARAM" 2>/dev/null || :
    if grep -q '^reclaim_progress_enabled=0$' /proc/ay_reclaim_status; then
      echo 'RESTORED reclaim_progress_enabled=0' >> "$OUT"
    else
      echo 'RESTORE FAILED: check /sys/module/vmscan/parameters/ay_reclaim_progress' >> "$OUT"
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
      kswapd*)
        pid=$(basename "$(dirname "$c")")
        [ -r "/proc/$pid/stat" ] && awk -v pid="$pid" '{print "KSWAPD",pid,"cpu_ticks=" $14+$15}' "/proc/$pid/stat" 2>/dev/null
        ;;
    esac
  done
}
set_mode() {
  echo "$1" > "$PARAM" || return 1
  grep -q "^reclaim_progress_enabled=$1$" /proc/ay_reclaim_status
}
sleep_window() {
  for second in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    sleep 1
    check_safety || return 1
  done
}
{
  echo 'AY V7.7 RECLAIM A-B-A CONFIRMATION: 15s + 15s + 15s'
  echo "KERNEL=$(uname -r)"
  echo "PARAM=$PARAM"
  echo 'Safety: screen on, thermal services running, backup mode 0.'
  snapshot 'A1 START / mode=0'
  sleep_window || exit 1
  snapshot 'A1 END / mode=0'
  ARMED=1
  set_mode 1 || { echo 'ABORT: could not verify mode 1'; exit 1; }
  echo 'WARMUP B 3 seconds'
  sleep 3
  check_safety || exit 1
  snapshot 'B START / mode=1'
  sleep_window || exit 1
  snapshot 'B END / mode=1'
  set_mode 0 || { echo 'ABORT: could not restore mode 0'; exit 1; }
  echo 'WARMUP A2 3 seconds'
  sleep 3
  check_safety || exit 1
  snapshot 'A2 START / mode=0'
  sleep_window || exit 1
  snapshot 'A2 END / mode=0'
  echo 'END OF ALL THREE WINDOWS, EXIT TRAP CONFIRMS MODE 0.'
} > "$OUT" 2>&1
echo "Saved: $OUT"
