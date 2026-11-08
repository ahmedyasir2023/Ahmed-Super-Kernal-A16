#!/system/bin/sh
# Read-only touch/wake/fingerprint snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "DEVICE"; getprop ro.product.device; getprop ro.build.version.release; getprop ro.build.fingerprint
section "INPUT DEVICES"; readp /proc/bus/input/devices
section "TOUCH SYSFS"; for f in /proc/touchpanel/* /sys/class/touchscreen/*/* /sys/devices/virtual/touchscreen/*; do [ -f "$f" ] && { echo "--- $f"; cat "$f" 2>/dev/null; }; done
section "WAKE"; readp /sys/power/wakeup_count; readp /sys/power/pm_wakeup_irq; readp /proc/interrupts
section "FINGERPRINT PROPERTIES"; getprop | grep -i fingerprint
section "RECENT LOGS"; dmesg 2>/dev/null | grep -Ei 'touch|gesture|double.?tap|fingerprint|fod|resume|unblank' | tail -n 120
section "END"; echo "Read-only: no gesture or fingerprint settings changed."
