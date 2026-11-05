# V9 RC1.1 — first successful physical boot diagnostic (RMX2170)

Date captured: **2026-11-06 00:43–00:44 EET**. Source: owner's completed 1,941-line read-only diagnostic report (local upload, not committed due to device/mod metadata). User reports V9 RC1.1 boots successfully; system confirms `sys.boot_completed=1` on RMX2170, Evolution X Android 16. Kernel 4.14.336 built Nov 5 at 18:43:13 UTC with Android Clang21 and LLD21.

## Physically observed successes
- Full Android boot completed; no fatal failure in the selected dmesg portion.
- Root UID0, SELinux `u:r:ksu:s0`, KernelSU userspace version `3.4.2-100-ga6c81fa4`, SELinux **Enforcing**.
- CPUFreq governors `schedutil` on both policies; eight cores online.
- V9 runtime module options: first-touch 78%/115ms, nav 82%/145ms, wake 85%/170ms, sched_boost=3, `ay_v9_boost_reuse=Y`; `ay_v9_reused_bursts=137` since boot. This proves V9 feature path runs, NOT a measured app-launch performance gain.
- `/proc/touchpanel/double_tap_enable=1` (kernel-side enable; physical wake gesture not separately tested).
- V8.1 reclaim: `vm.kswapd_threads=1`, one `[kswapd0:0]`, `ay_v81_single_kswapd=Y`; watermark factor=50 with `ay_v8_latency_watermarks=Y`; reclaim_progress disabled.
- ZRAM: 3GiB, LZ4, use_dedup=1. `mm_stat` orig=1,137,025,024 bytes, compressed=305,397,500 bytes, physical memory=323,936,256 bytes (~3.72x and 3.51x).
- Both thermal services run; battery temperature 34.3C while AC charging, CPU sensors mostly ~40–42.7C. Only a snapshot.
- Runtime GPU governor msm-adreno-tz and 267MHz current, 750MHz cap.
- `CONFIG_KSU_SUSFS=y` compiled; missing SUSFS proc/sysfs status interfaces means full API/runtime functionality is not demonstrated. Do not infer mount/path hiding from config alone.

## Major performance finding: high but transient memory PSI
- Initial memory PSI: `some avg10=17.72 avg60=37.85 avg300=30.24`; `full avg10=16.64 avg60=35.35 avg300=28.30`.
- During three subsequent observations memory PSI `some avg10=0.72 -> 0.39 -> 0.21` and `full avg10=0.67 -> 0.37 -> 0.20`; full avg60 still declined from 20.75 to 17.00.
- MemAvailable initial 1,282,220 KiB (~1.22GiB). Repeated 1,255,836 -> 1,396,440 -> 1,400,428 KiB (~141MiB recovered in 13 seconds).
- Report shows 0 OOM kills (snapshot cumulative vmstat), 0 zero-progress reclaim cycles, but workload-stall data and historic 15,327 `balance_calls` warrant follow-up attribution. 15,191 `balance_zero_waiters` (99.11%), only 156 wake requests; all counts remained unchanged during 13-sec snapshots, so no proof of ongoing kswapd spin in the observation interval.
- Do not overstate the high initial PSI as permanent, and do not claim V9 alone cured the memory problem. No V8-to-V9 controlled A/B benchmark was recorded.

## CPU operating profile
- Little policy 0: 576–1,804.8 MHz, schedutil. Big policy 6: 652.8–2,323.2 MHz, schedutil; realtime big cluster sampled at its minimum.
- Cumulative time_in_state since boot indicates the big cluster spent ~40.1% at 2,323.2 MHz, and little cluster ~16.1% at 1,804.8 MHz. Such cumulative percentages are not a stand-alone battery-drain diagnosis. Kernel stats units are 10ms per tick.
- Runtime compiled `CONFIG_CPU_FREQ_DEFAULT_GOV_PERFORMANCE=y` is not the active governor; schedutil is active.

## DeepDoze / battery
- `ay_deepdoze_enabled=Y`, delay=600s, `ay_deepdoze_active=N`, `ay_deepdoze_entries=0`. During diagnostic `mScreenOn=true`, `mCharging=true`, so no eligible unplugged screen-off interval was assessed. Android DeviceIdle state ACTIVE.
- Battery is AC charging 100%; gauge `charge_full=3172000` microAh, `charge_full_design=4500000` microAh (ratio ~70.5%), but custom-ROM/BMS scaling and gauge metadata may invalidate a capacity-health inference; do not conclude 70.5% actual SOH from these fields alone.
- Wakelock log mentions repeated 'battery suspend wakelock' while charging. Not evidence of offscreen drain.
- No overnight screen-off drain measurement or DeepDoze residence confirmation is in the report.

## Other qualifications / next engineering focus
- Display service enumerates 1080×2400, 61.000004Hz active/available mode; there is no grounded 90Hz panel mode in this log.
- SUSFS feature procfs nodes absent; no claim of fully operational hide functions.
- Filtered kernel warnings show periodic msm_watchdog diagnostics but no proven crash; full logs were not collected.
- First engineering priority: find root cause of intermittent high Memory PSI and distinguish ROM userspace/background service pressure from allocator/reclaim behavior, without raising CPU min clocks, forcing a performance governor, disabling thermal, or indiscriminately increasing ZRAM.
- Second: confirm DeepDoze after unplugged ≥600s screen-off only if battery testing later warrants it.
- Track user-reported boot/root as physically validated and keep PR draft pending fingerprint/DT2W and stability evidence.

Sources for metric semantics:
- https://docs.kernel.org/accounting/psi.html
- https://www.kernel.org/doc/html/latest/admin-guide/blockdev/zram.html
- https://docs.kernel.org/cpu-freq/cpufreq-stats.html
