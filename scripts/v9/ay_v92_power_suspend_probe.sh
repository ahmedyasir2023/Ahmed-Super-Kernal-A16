#!/system/bin/sh
# AY V9.2 Power/Suspend Probe — read-only device snapshot for RMX2170.
# It reads existing kernel interfaces only. It does not write sysfs/procfs,
# change governors, enable/disable wake sources, mount debugfs, or hold wakelocks.

set -u

section() {
    printf '\n===== %s =====\n' "$1"
}

read_path() {
    p="$1"
    if [ -r "$p" ]; then
        printf '\n--- %s ---\n' "$p"
        cat "$p" 2>/dev/null || printf '[read failed]\n'
    else
        printf '\n--- %s: UNAVAILABLE ---\n' "$p"
    fi
}

section "IDENTITY AND TIME"
date 2>/dev/null
uname -a 2>/dev/null
if command -v getprop >/dev/null 2>&1; then
    printf 'ro.build.version.release='
    getprop ro.build.version.release
    printf 'ro.build.version.sdk='
    getprop ro.build.version.sdk
    printf 'ro.build.fingerprint='
    getprop ro.build.fingerprint
fi
read_path /proc/uptime

section "V9.2 PM NOTIFIER TELEMETRY"
read_path /proc/ay_power_suspend_status

section "KERNEL SUSPEND INTERFACES"
read_path /sys/power/state
read_path /sys/power/mem_sleep
read_path /sys/power/wakeup_count
read_path /sys/power/pm_wakeup_irq
read_path /sys/kernel/debug/suspend_stats
read_path /sys/power/suspend_stats

section "WAKEUP SOURCE ACCOUNTING"
read_path /sys/kernel/debug/wakeup_sources
read_path /proc/wakeup_sources

section "CPU IDLE STATE RESIDENCY"
found_idle=0
for state in /sys/devices/system/cpu/cpu[0-9]*/cpuidle/state[0-9]*; do
    [ -d "$state" ] || continue
    found_idle=1
    printf '\n--- %s ---\n' "$state"
    for field in name desc usage time latency residency disable; do
        if [ -r "$state/$field" ]; then
            printf '%s=' "$field"
            cat "$state/$field" 2>/dev/null || printf '[read failed]\n'
        fi
    done
done
if [ "$found_idle" -eq 0 ]; then
    printf 'No readable CPUIdle state directories found.\n'
fi

section "CPUFREQ POLICY SNAPSHOT"
found_policy=0
for policy in /sys/devices/system/cpu/cpufreq/policy[0-9]*; do
    [ -d "$policy" ] || continue
    found_policy=1
    printf '\n--- %s ---\n' "$policy"
    for field in affected_cpus related_cpus scaling_governor scaling_min_freq scaling_max_freq scaling_cur_freq cpuinfo_min_freq cpuinfo_max_freq; do
        if [ -r "$policy/$field" ]; then
            printf '%s=' "$field"
            cat "$policy/$field" 2>/dev/null || printf '[read failed]\n'
        fi
    done
done
if [ "$found_policy" -eq 0 ]; then
    printf 'No readable CPUFreq policy directories found.\n'
fi

section "DEEPDOZE PARAMETERS"
for field in ay_deepdoze_enabled ay_deepdoze_delay_seconds ay_deepdoze_active ay_deepdoze_entries; do
    read_path "/sys/module/cpu_boost/parameters/$field"
done

section "MEMORY AND PRESSURE CONTEXT"
read_path /proc/pressure/cpu
read_path /proc/pressure/memory
read_path /proc/meminfo
read_path /proc/ay_reclaim_status
read_path /sys/block/zram0/mm_stat

section "BATTERY SNAPSHOT"
for field in capacity status current_now voltage_now temp charge_counter charge_full energy_now; do
    read_path "/sys/class/power_supply/battery/$field"
done

section "INTERRUPT COUNTERS"
read_path /proc/interrupts

section "RECENT SUSPEND / WAKE / DEEPDOZE LOGS"
if command -v dmesg >/dev/null 2>&1; then
    dmesg 2>/dev/null | grep -Ei 'suspend|resume|wakeup|wake.?source|PM:|ay_deepdoze|cpu-boost' | tail -n 180
else
    printf 'dmesg command unavailable.\n'
fi

section "END OF READ-ONLY SNAPSHOT"
printf 'No kernel or power-management settings were changed by this probe.\n'
printf 'Interpret PM cycle duration together with suspend_stats and CPUIdle residency.\n'
