#!/system/bin/sh
# Read-only RMX2170 power/suspend snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { printf '\n--- %s ---\n' "$1"; cat "$1" 2>/dev/null; } || printf '\n--- %s: unavailable ---\n' "$1"; }
section "TIME / UPTIME"; date; readp /proc/uptime
section "PM SUSPEND"; readp /proc/ay_power_suspend_status; readp /sys/power/state; readp /sys/power/mem_sleep; readp /sys/kernel/debug/suspend_stats
section "WAKEUP SOURCES"; readp /sys/kernel/debug/wakeup_sources; readp /proc/wakeup_sources
section "CPU IDLE"; for f in /sys/devices/system/cpu/cpu*/cpuidle/state*/name /sys/devices/system/cpu/cpu*/cpuidle/state*/usage /sys/devices/system/cpu/cpu*/cpuidle/state*/time /sys/devices/system/cpu/cpu*/cpuidle/state*/latency; do [ -r "$f" ] && { echo "--- $f"; cat "$f"; }; done
section "DEEPDOZE"; for f in /sys/module/cpu_boost/parameters/ay_deepdoze_*; do [ -r "$f" ] && { echo "--- $f"; cat "$f"; }; done
section "CPUFREQ"; for p in /sys/devices/system/cpu/cpufreq/policy*; do [ -d "$p" ] || continue; for f in scaling_governor scaling_min_freq scaling_max_freq scaling_cur_freq; do readp "$p/$f"; done; done
section "BATTERY"; for f in capacity status current_now voltage_now temp charge_counter; do readp "/sys/class/power_supply/battery/$f"; done
section "END"; echo "Read-only: no settings changed."
