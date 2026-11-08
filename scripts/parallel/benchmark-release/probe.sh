#!/system/bin/sh
# Consolidated read-only release baseline. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "IDENTITY"; date; uname -a; getprop ro.build.fingerprint; getprop ro.build.version.sdk
section "UPTIME / BATTERY"; readp /proc/uptime; dumpsys battery 2>/dev/null
section "CPU"; for p in /sys/devices/system/cpu/cpufreq/policy*; do [ -d "$p" ] || continue; for f in scaling_governor scaling_min_freq scaling_max_freq scaling_cur_freq; do readp "$p/$f"; done; done
section "MEMORY"; readp /proc/meminfo; readp /proc/pressure/memory; readp /proc/pressure/cpu; readp /sys/block/zram0/mm_stat
section "POWER"; readp /proc/ay_power_suspend_status; readp /sys/kernel/debug/suspend_stats; readp /sys/kernel/debug/wakeup_sources
section "THERMAL"; for f in /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp; do readp "$f"; done
section "END"; echo "Read-only release baseline; no settings changed."
