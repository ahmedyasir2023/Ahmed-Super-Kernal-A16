# Ahmed Super Kernal A16 V2 — performance design (NO PERFORMANCE PATCHES YET)

**Target**: RMX2170, Evolution X Android 16, Linux 4.14.336. **Status**: performance experiments planned, but none are applied in the current V2 Root-only build. No ZIP to flash from this branch.

## Existing hardware-compatible baseline (observed in pinned Atoll defconfig)

- `CONFIG_SCHED_WALT=y`: vendor's WALT task load estimator
- `CONFIG_CPU_FREQ_GOV_SCHEDUTIL=y`: CPU frequency scaling governor available
- `CONFIG_PREEMPT=y`: kernel preemption
- `CONFIG_HZ_250=y`: scheduler tick configuration
- `CONFIG_ZRAM=y` and `CONFIG_ZSMALLOC=y`: compressed swap support
- `CONFIG_PSI=y` and `CONFIG_MEMCG=y`: memory pressure tracking and cgroups
- `CONFIG_SCHED_TUNE=y`: scheduler boost hooks

These are **existing features**, not added performance optimizations. The presence of `CONFIG_ZRAM=y` does not show the runtime swap allocation, algorithm or actual utilization.

## Performance profiles (future implementation — require runtime testing)

| Area | Balanced (safe default) | Turbo (opt-in and temporary) |
| --- | --- | --- |
| CPU scheduling | Keep stock WALT + schedutil and original governor limits | Short, bounded scheduler/uclamp boost for foreground app launch if supported by this kernel; auto-reset |
| CPU frequencies | Respect stock power HAL and input boosts | Temporary minimum-frequency hint, never disable thermal throttling |
| GPU | Preserve Adreno firmware, driver and stock thermal policies | Evaluate frame-time stutter and responsiveness; no unsafe permanent overclock |
| Memory | Keep PSI/MEMCG/ZRAM stock until baseline is collected | Test a supported ZRAM compression change only after measuring memory pressure, CPU cost and app retention |
| I/O | Preserve verified vendor I/O scheduler defaults | Evaluate only on real storage workload and latency data |
| Standby | Preserve suspend, interrupts and DT2W | No forced deep doze that breaks notifications or double-tap wake |
| Security | SELinux Enforcing, AVB untouched | Same policy; never turn off SELinux or security checks for speed |

**No permanent performance governor.** High continuous frequencies raise temperature/power, and can lead to thermal throttling that reduces sustained speed.

## Measurements required (same ROM, battery and temperature)

1. Warm and cold launch times (median and 95th percentile) for the same five apps across 10 trials; use `am start -W` and timing logs.
2. Foreground/scroll/game frame-time median, p95/p99; count jank frames before/after.
3. Number of retained apps after a reproducible multitasking sequence; record `dumpsys meminfo`, `/proc/pressure/memory`, zram usage and swap compression.
4. CPU frequencies, thermal state and battery drain during a 20-minute fixed-load run.
5. Wi-Fi, fingerprint, camera, charging, suspend/resume, DT2W, and Root/KernelSU/SUSFS state after every change.
6. Rollback after thermal, idle, boot, USB/ADB or battery regression.

## Release gates

- The current V2 Root-only test must **boot and grant effective Root** on device first. CI compilation success alone is insufficient.
- SUSFS 4.14 requires a dedicated modern KernelSU bridge; see `v2-susfs-compatibility`.
- Implement **one tuning change per CI build**, not dozens of simultaneous tweaks. Require seven unchanged DTBs and keep hardware drivers unmodified.
- Publish metrics as before/after deltas with uncertainty, not claims of '100% faster' or 'more physical RAM'.
- Do not flash or generate an installer from this design-only branch.

## Related evidence

- Successful Root-only build: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41548897129
- Kernel source: https://github.com/realme-atoll/android_kernel_realme_sm7125/tree/aosp-16
