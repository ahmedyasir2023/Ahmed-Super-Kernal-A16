#!/system/bin/sh
MODDIR=\${0%/*}
. "$MODDIR/common.sh"
# KernelSU Manager action button toggles live test + reverts without reboot.
if [ -f "$PAUSE" ]; then
  rm -f "$PAUSE"
  ay_apply
  echo 'AY V7.3 compatibility trial enabled (only on verified ROM)'
else
  touch "$PAUSE"
  ay_rollback
  echo 'AY V7.3 compatibility trial paused; original value restored where possible'
fi
