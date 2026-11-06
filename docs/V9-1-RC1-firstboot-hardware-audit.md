# V9.1 RC1 — first physical boot and reclaim telemetry audit

**Source:** owner-provided full read-only diagnostic report from Realme 7 Pro RMX2170 / Evolution X Android 16, taken **2026-11-06 01:38:49–01:39:45 EET**. The private raw report is **not** copied to this public repository. The preceding V9 RC1.1 report was taken **2026-11-06 00:43:16–00:44:17 EET**.

## Hardware execution: successful limited validation

- V9.1 sys.boot_completed=1; Linux 4.14.336 Clang 21, built Nov 5 23:17:40 UTC.
- KernelSU root UID0, SELinux Enforcing; KernelSU internal version 33455.
- V9 CPUBoost first touch 78%/115ms, nav 82%/145ms, wake 85%/170ms; boost reuse enabled, 21 events counted.
- DT2W procfs enabled; physical tap-to-wake not separately verified.
- DeepDoze enabled, delay 600s; entries=0 while screen ON during this 2–3 minute post-boot sample. Not a DeepDoze test.
- One kswapd worker, V8.1 guard enabled, VM watermark factor 50 unchanged. ZRAM LZ4/3GiB; 0 OOM kills and 0 zero-progress cycles. Thermal HAL and engine running.
- **V9.1 runtime active:** v91_bounded_reclaim_enabled=1, v91_extra_passes=76 initially and **82** by the final window, v91_waiter_exits=613 final, balance_calls=636, balance_zero_waiters=605, unbounded reclaim_progress_enabled=0.
- Between snapshots 0 and 10 seconds, extra_passes remained 82 while memory PSI full avg10 fell from 12.99% to 4.24%; the decline cannot be directly credited to the new pass policy.

## V9 RC1.1 vs V9.1 RC1 (different time since boot)

| Metric | V9 RC1.1 | V9.1 RC1 |
|---|---:|---:|
| Uptime at start | 2212.65 s (36.9 min) | 163.73 s (2.7 min) |
| MemAvailable | 1,282,220 KiB (~1.22 GiB) | 1,435,200 KiB (~1.37 GiB) |
| Memory PSI full avg10 initial | 16.64% | 10.80% |
| Memory PSI full avg60 initial | 35.35% | 22.00% |
| Memory PSI full avg10 final | 0.20% | 4.24% |
| CPU PSI some avg60 initial | 3.79% | 19.53% |
| CPU policy0 min | 576,000 kHz | **1,324,800 kHz** |
| CPU policy6 min | 652,800 kHz | 652,800 kHz |
| 1-minute load average initial | 5.95 | 13.67 |
| ZRAM used | 1,155,544 KiB | 871,600 KiB |
| kswapd workers | 1 | 1 |
| OOM kills reported | 0 | 0 |

**No causal speed improvement or regression is proven.** V9.1 was measured during heavy early boot and is not comparable to the older V9 report after 37 minutes. Elevated policy0 minimum can be produced by ROM/Power HAL or transient boost; this version did not change CPUBoost code. Do not change CPU policy based on these two snapshots.

## Workqueue warning — detailed source diagnosis is pending

Two boot-time WARN entries were captured:
- +1.218198s CPU7 PID228, kernel/workqueue.c line 1492, __queue_work+0x450/0x498
- +1.327645s CPU7 PID228, same site.

The exact pinned vendor source [workqueue.c:1489–1496](https://github.com/realme-atoll/android_kernel_realme_sm7125/blob/10380039ddcd6ead841e1fc4ca744a2dd6e92fb8/kernel/workqueue.c#L1489-L1496) executes WARN_ON(!list_empty(&work->entry)): a queued work item is still linked when another queue attempt occurs. The report logs only selected warnings and **omits the warning call trace**; no responsible driver or subsystem is identified. Previous V9 report showed only later dmesg output, so the warning could have been present before V9.1.

Do not patch the workqueue core or assign V9.1 fault based on these two lines. Capturing the full boot call trace is the next step only if the warning persists or stability symptoms occur.

## Release guidance

- **Hardware boot and KernelSU: confirmed.** V9.1 memory policy execution: confirmed.
- Memory PSI reduction versus V9: **unproven** due to severely unmatched workload/uptime.
- Fingerprint, physical DT2W, screen-off battery drain, deepdoze: not measured in this log.
- Keep PR #19 draft and experimental V9.1 RC1; maintain verified V9 RC1.1 restore package.
- One follow-up steady-state check >=10 minutes after boot could record PSI, CPU policy min and basic reclaim counters without re-running 16-stage diagnostic.
- Preserve CPUFreq governor, CPU min/max, kswapd worker count, swappiness, thermal, SUSFS, SELinux and DeepDoze pending evidence.
- Kernel PSI semantics: https://www.kernel.org/doc/html/latest/accounting/psi.html
- CPU frequency sysfs semantics: https://docs.kernel.org/admin-guide/pm/cpufreq.html
