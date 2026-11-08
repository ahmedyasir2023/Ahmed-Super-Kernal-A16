#!/system/bin/sh
# Read-only thermal snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "THERMAL ZONES"; for f in /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp /sys/class/thermal/thermal_zone*/mode; do readp "$f"; done
section "COOLING DEVICES"; for d in /sys/class/thermal/cooling_device*; do [ -d "$d" ] || continue; for f in type cur_state max_state; do readp "$d/$f"; done; done
section "CPU POLICIES"; for p in /sys/devices/system/cpu/cpufreq/policy*; do [ -d "$p" ] || continue; readp "$p/scaling_cur_freq"; readp "$p/scaling_max_freq"; done
section "BATTERY"; for f in temp capacity status current_now voltage_now; do readp "/sys/class/power_supply/battery/$f"; done
section "THERMAL LOGS"; dmesg 2>/dev/null | grep -Ei 'thermal|throttl|cooling|overheat' | tail -n 100
section "END"; echo "Read-only: no thermal or cooling policy changed."
