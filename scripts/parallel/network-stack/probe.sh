#!/system/bin/sh
# Read-only network/radio snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "INTERFACES"; readp /proc/net/dev; ip -s link 2>/dev/null
section "TCP"; readp /proc/net/snmp; readp /proc/net/netstat; readp /proc/pressure/cpu
section "ROUTES"; ip route 2>/dev/null; ip -6 route 2>/dev/null
section "RADIO STATE"; getprop | grep -Ei 'wifi|wlan|radio|mobile_data|telephony'
section "WAKEUP SOURCES"; readp /sys/kernel/debug/wakeup_sources
section "NETWORK LOGS"; dmesg 2>/dev/null | grep -Ei 'wlan|wifi|wakeup|suspend|resume|tcp|rmnet' | tail -n 100
section "END"; echo "Read-only: no network, radio or firmware setting changed."
