#!/system/bin/sh
# AY RMX2170: read-only reboot/power-off diagnostics.
# Does not trigger a restart, flash anything, or change kernel properties.
set -u
OUT=/sdcard/Download/AY_RMX2170_Reboot_Diagnostics.txt
FILTER='reboot|restart|power.?off|ps.?hold|qpnp|pon_|pmic|watchdog|wdog|crash|panic|shutdown|thermal|pstore|ramoops|dload|bootreason|reset.reason|recovery'
{
 echo '=== AY RMX2170 REBOOT DIAGNOSTICS (READ ONLY) ==='
 date '+%Y-%m-%d %H:%M:%S %z' 2>/dev/null
 echo '=== KERNEL AND REBOOT REASON ==='
 uname -a
 for k in ro.product.device ro.build.version.release ro.boot.bootreason sys.boot.reason persist.sys.boot.reason ro.bootmode sys.boot_completed; do
   printf '%s=' "$k"
   getprop "$k"
 done
 echo '=== PERSISTENT PREVIOUS KERNEL LOGS ==='
 [ -d /sys/fs/pstore ] && ls -l /sys/fs/pstore || echo 'pstore unavailable'
 FOUND=0
 for p in /sys/fs/pstore/console-ramoops* /sys/fs/pstore/dmesg-ramoops* /sys/fs/pstore/pmsg-ramoops*; do
   [ -r "$p" ] || continue
   FOUND=1
   echo "== $p (matching events) =="
   grep -iE "$FILTER" "$p" 2>/dev/null | tail -n 100
   echo "== $p (final 25 lines) =="
   tail -n 25 "$p" 2>/dev/null
 done
 [ "$FOUND" = 0 ] && echo 'No readable persisted reboot records'
 echo '=== CURRENT DMESG ==='
 dmesg 2>/dev/null | grep -iE "$FILTER" | tail -n 180 || true
 echo '=== ANDROID SYSTEM / INIT ==='
 logcat -d -b system -b main -b kernel -t 2500 2>/dev/null | grep -iE 'sys.powerctl|reboot|shutdown|restarting|bootreason|power.?off|msm.restart|qpnp|watchdog|thermal' | tail -n 110 || true
 echo '=== BATTERY ==='
 for f in /sys/class/power_supply/battery/status /sys/class/power_supply/battery/capacity /sys/class/power_supply/battery/temp; do
   [ -r "$f" ] && { printf '%s=' "$f"; cat "$f"; }
 done
 echo '=== COMPLETE: NO POWER ACTIONS EXECUTED ==='
} > "$OUT" 2>&1
chmod 600 "$OUT" 2>/dev/null || true
printf 'Read-only report saved: %s\n' "$OUT"
