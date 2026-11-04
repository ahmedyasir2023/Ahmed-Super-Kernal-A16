#!/system/bin/sh
# AY A16 V7.3 Memory Compatibility: strictly scoped and fail-closed.
# Uses AY_TEST_ROOT only for offline unit tests. On-device this is unset.
MODDIR=\${0%/*}
ROOT=\${AY_TEST_ROOT:-}
CG="$ROOT/sys/fs/cgroup/memory/bg/memory.swappiness"
RC="$ROOT/vendor/etc/init/hw/init.qcom.rc"
STATE="$MODDIR/original_swappiness"
PAUSE="$MODDIR/paused"
LOG="$MODDIR/ay-memory-compat.log"

ay_log() {
  printf '%s\n' "$*" >> "$LOG"
}

ay_target_ok() {
  [ "$(getprop ro.product.vendor.name)" = RMX2170 ] || return 1
  [ "$(getprop ro.vendor.build.version.sdk)" = 36 ] || return 1
  [ "$(getprop ro.vendor.build.security_patch)" = 2026-10-01 ] || return 1
  [ "$(getprop ro.vendor.build.date)" = 'Mon Nov  2 01:02:30 UTC 2026' ] || return 1
  [ -f "$RC" ] || return 1
  # Only fix the exact, observed ROM bug. A different ROM is out of scope.
  grep -Eq '^[[:space:]]*write[[:space:]]+/sys/fs/cgroup/memory/bg/memory.swappiness[[:space:]]+140[[:space:]]*$' "$RC" || return 1
  [ -r "$CG" ] && [ -w "$CG" ] || return 1
}

ay_valid_num() {
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
  [ "$1" -ge 0 ] && [ "$1" -le 100 ]
}

ay_apply() {
  [ ! -f "$PAUSE" ] || { ay_log 'Module paused: no writes'; return 0; }
  ay_target_ok || { ay_log 'Target mismatch or cgroup path absent: no writes'; return 0; }
  before=$(cat "$CG" 2>/dev/null) || return 1
  ay_valid_num "$before" || { ay_log 'Unexpected live memcg value: no writes'; return 0; }
  [ "$before" != 100 ] || { ay_log 'Already at 100: no changes'; return 0; }
  # Save the actual value that Android applied, not the invalid 140 from RC.
  if [ ! -f "$STATE" ]; then
    printf '%s\n' "$before" > "$STATE" || return 1
  fi
  prior=$(cat "$STATE" 2>/dev/null)
  ay_valid_num "$prior" || { ay_log 'Saved baseline invalid: no writes'; return 1; }
  printf '%s\n' 100 > "$CG" || { ay_log 'Write failed'; return 1; }
  after=$(cat "$CG" 2>/dev/null)
  if [ "$after" != 100 ]; then
    ay_log 'Verification failed: restoring original baseline'
    printf '%s\n' "$prior" > "$CG" 2>/dev/null
    return 1
  fi
  ay_log "Applied background memcg swappiness $before -> 100; original=$prior"
}

ay_rollback() {
  [ -f "$STATE" ] || { ay_log 'No saved value to restore'; return 0; }
  original=$(cat "$STATE" 2>/dev/null)
  ay_valid_num "$original" || { ay_log 'Corrupt baseline: refuse write'; return 1; }
  [ -w "$CG" ] || { ay_log 'Cgroup unavailable; reboot restores ROM default'; return 0; }
  current=$(cat "$CG" 2>/dev/null)
  ay_valid_num "$current" || return 1
  # Do not trample another service's subsequent tuning.
  if [ "$current" = 100 ]; then
    printf '%s\n' "$original" > "$CG" || return 1
    ay_log "Rollback: restored original $original"
  else
    ay_log "Rollback skipped: live cgroup now $current, not our 100"
  fi
  rm -f "$STATE"
}
