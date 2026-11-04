#!/system/bin/sh
MODDIR=\${0%/*}
. "$MODDIR/common.sh"
# KernelSU late-start service stage; never change early-boot policy.
[ -f "$PAUSE" ] && exit 0
n=0
while [ "$(getprop sys.boot_completed)" != 1 ] && [ "$n" -lt 36 ]; do
  sleep 5
  n=$((n + 1))
done
[ "$(getprop sys.boot_completed)" = 1 ] || { ay_log 'Boot not completed: no writes'; exit 0; }
ay_apply
