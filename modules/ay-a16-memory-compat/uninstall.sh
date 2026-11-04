#!/system/bin/sh
MODDIR=\${0%/*}
. "$MODDIR/common.sh"
touch "$PAUSE"
ay_rollback
