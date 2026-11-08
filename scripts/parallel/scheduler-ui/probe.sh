#!/system/bin/sh
# Read-only scheduler/CPUFreq snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "CPUFREQ"; for p in /sys/devices/system/cpu/cpufreq/policy*; do [ -d "$p" ] || continue; for f in affected_cpus scaling_governor scaling_min_freq scaling_max_freq scaling_cur_freq; do readp "$p/$f"; done; done
section "AY PARAMETERS"; for f in /sys/module/cpu_boost/parameters/ay_* /sys/module/cpufreq_schedutil/parameters/ay_*; do [ -r "$f" ] && { echo "--- $f"; cat "$f"; }; done
section "SCHEDULER"; readp /proc/pressure/cpu; readp /proc/schedstat; readp /proc/loadavg
section "CPU INFO"; readp /proc/cpuinfo
section "END"; echo "Read-only: no governor or frequency changed."
