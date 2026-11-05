#!/system/bin/sh
# AY V7.7 / RMX2170 -- bounded, reversible watermark A-B-A experiment.
# Change ONLY vm.watermark_scale_factor from observed 200 to 50, then 200.
# No boot changes, daemons, remount, swap, ZRAM, CPU or thermal changes.
# Run foreground in Termux with the DISPLAY ON. SIGKILL cannot run traps.
set -u

OUT=/sdcard/Download/AY_V77_Watermark_ABA_Report.txt
KNOB=/proc/sys/vm/watermark_scale_factor
RECLAIM=/proc/ay_reclaim_status
PSI=/proc/pressure/memory
BASE=200
CANDIDATE=50
CHANGED=0

if [ "$(id -u)" != 0 ] || [ ! -r "$KNOB" ] || [ ! -w "$KNOB" ] || \
   [ ! -r "$PSI" ] || [ ! -r "$RECLAIM" ]; then
  echo 'ABORT: root, PSI, V7.7 counters and writable watermark knob required'
  exit 1
fi
if [ "$(cat "$KNOB")" != "$BASE" ] || \
   ! grep -q '^reclaim_progress_enabled=0$' "$RECLAIM"; then
  echo 'ABORT: expected baseline watermark=200 and reclaim_progress=0'
  exit 1
fi

safe() {
  if [ "$(getprop init.svc.vendor.thermal-hal)" != running ] || \
     [ "$(getprop init.svc.thermal-engine)" != running ]; then
    echo 'ABORT: thermal services are not both running'
    return 1
  fi
  if [ -r /sys/class/power_supply/battery/temp ]; then
    t=$(cat /sys/class/power_supply/battery/temp 2>/dev/null) || return 1
    case "$t" in ''|*[!0-9]*) echo 'ABORT: invalid battery temperature'; return 1;; esac
    if [ "$t" -gt 420 ]; then echo "ABORT: battery temp $t deci-C"; return 1; fi
  fi
  if [ -r /sys/kernel/ay_shadow/telemetry ] && \
     grep -Eq '(^|[ ;])screen_on=0($|[ ;])' /sys/kernel/ay_shadow/telemetry; then
    echo 'ABORT: screen switched off'
    return 1
  fi
  if ! grep -q '^reclaim_progress_enabled=0$' "$RECLAIM"; then
    echo 'ABORT: reclaim mode changed externally'
    return 1
  fi
  return 0
}

restore() {
  if [ "$CHANGED" -eq 1 ]; then
    printf '%s\n' "$BASE" > "$KNOB" 2>/dev/null || :
    actual=$(cat "$KNOB" 2>/dev/null || echo UNKNOWN)
    if [ "$actual" = "$BASE" ]; then
      echo 'RESTORED watermark_scale_factor=200' >> "$OUT"
    else
      echo "RESTORE_FAILED watermark_scale_factor=$actual; manually restore value 200" >> "$OUT"
    fi
  fi
}
trap restore 0
trap 'exit 129' 1
trap 'exit 130' 2
trap 'exit 143' 15

full_avg10() {
  awk '$1=="full" {for(i=2;i<=NF;i++) if($i ~ /^avg10=/) {split($i,a,"=");print a[2];exit}}' "$PSI"
}
full_total() {
  awk '$1=="full" {for(i=2;i<=NF;i++) if($i ~ /^total=/) {split($i,a,"=");print a[2];exit}}' "$PSI"
}

snapshot() {
  echo "=== SNAPSHOT $1 ==="
  echo "TIME_EPOCH $(date +%s)"
  echo "WATERMARK $(cat "$KNOB")"
  for p in memory cpu io; do
    [ -r "/proc/pressure/$p" ] || continue
    while IFS= read -r line; do echo "PSI $p $line"; done < "/proc/pressure/$p"
  done
  awk '/^(pgscan_kswapd|pgsteal_kswapd|pgscan_direct|pgsteal_direct|pswpin|pswpout|workingset_refault|pgmajfault|allocstall|oom_kill)(_| )/ {print "VM",$1,$2}' /proc/vmstat
  awk '/^(MemAvailable|MemFree|SwapFree|SwapTotal):/ {print "MEM",$1,$2}' /proc/meminfo
  awk '/^Node [0-9]+, zone / {print "ZONE",$0} /^[ \t]+(pages free|min|low|high|managed) / {print "ZONE",$0}' /proc/zoneinfo
  while IFS= read -r line; do echo "RECLAIM $line"; done < "$RECLAIM"
  for c in /proc/[0-9]*/comm; do
    [ -r "$c" ] || continue
    IFS= read -r name < "$c" || :
    case "$name" in
      kswapd*)
        pid=$(basename "$(dirname "$c")")
        [ -r "/proc/$pid/stat" ] && awk -v pid="$pid" '{print "KSWAPD",pid,"ticks=" $14+$15}' "/proc/$pid/stat" 2>/dev/null || :
        ;;
    esac
  done
  echo '=== END SNAPSHOT ==='
}

window() {
  n=0
  while [ "$n" -lt 15 ]; do
    sleep 1
    safe || return 1
    n=$((n+1))
  done
  return 0
}

safe || exit 1
if ! ( : > "$OUT" ) 2>/dev/null; then echo "ABORT: cannot write $OUT"; exit 1; fi
{
  echo 'AY_V77_WATERMARK_ABA_V1'
  echo "KERNEL $(uname -r)"
  echo "BASE=$BASE CANDIDATE=$CANDIDATE"
  echo "EXTRA_FREE_KBYTES $(cat /proc/sys/vm/extra_free_kbytes 2>/dev/null || echo unreadable)"
  echo 'One reversible sysctl experiment, normal Thermal HAL, no other kernel settings touched'
  seen=0
  tries=0
  while [ "$tries" -lt 20 ]; do
    safe || exit 2
    a=$(full_avg10)
    echo "WATCH trial=$tries memory_full_avg10=$a"
    if awk -v x="$a" 'BEGIN{exit !(x+0>=25)}'; then seen=$((seen+1)); else seen=0; fi
    if [ "$seen" -ge 2 ]; then echo "TRIGGERED full_avg10=$a"; break; fi
    tries=$((tries+1))
    [ "$tries" -lt 20 ] && sleep 3
  done
  if [ "$seen" -lt 2 ]; then echo 'NO_TRIGGER'; echo COMPLETE; exit 0; fi

  start_t=$(date +%s)
  start_psi=$(full_total)
  snapshot 'A1 START mode=200'
  window || exit 2
  snapshot 'A1 END mode=200'
  end_t=$(date +%s)
  end_psi=$(full_total)
  if ! awk -v a="$start_psi" -v b="$end_psi" -v sec="$((end_t-start_t))" \
          'BEGIN {exit !(sec>0 && b>=a && (b-a)/(sec*10000)>=25)}'; then
    echo 'BASELINE_QUIET: no persistent stall in A1; no watermark was changed'
    echo COMPLETE
    exit 0
  fi

  # The original knob is preserved in BASE and restored by trap even on
  # catchable signals. This modification is VOLATILE and opt-in only.
  CHANGED=1
  if ! printf '%s\n' "$CANDIDATE" > "$KNOB" || [ "$(cat "$KNOB")" != "$CANDIDATE" ]; then
    echo 'CHANGE_FAILED: candidate rejected, exiting through restoration trap'
    exit 2
  fi
  echo 'B_WARMUP=3sec'
  sleep 3
  safe || exit 2
  snapshot 'B START mode=50'
  window || exit 2
  snapshot 'B END mode=50'

  if ! printf '%s\n' "$BASE" > "$KNOB" || [ "$(cat "$KNOB")" != "$BASE" ]; then
    echo 'EARLY_RESTORE_FAILED: exit trap will retry'
    exit 2
  fi
  echo 'A2_WARMUP=3sec'
  sleep 3
  safe || exit 2
  snapshot 'A2 START mode=200'
  window || exit 2
  snapshot 'A2 END mode=200'
  echo COMPLETE
} >> "$OUT" 2>&1
# trap will verify restoration when the shell exits.
echo "Report saved: $OUT"
