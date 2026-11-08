# V10 — AY HyperCore: source audit and staged engineering plan

## Target and immutable inputs

- Device: Realme 7 Pro RMX2170 / Qualcomm SM7125 Atoll.
- ROM target: Evolution X Android 16 (SDK 36).
- Kernel: Linux 4.14.336, pinned upstream source commit
  `10380039ddcd6ead841e1fc4ca744a2dd6e92fb8`.
- Compiler: pinned Android Clang 21 `clang-r563880c`.
- Root integration: KernelSU Next UAPI 6, pinned commit
  `b933b1f728116a456fbebf27b6a8772a640cdf23`.
- SUSFS: 4.14 patch commit
  `77905b5a071e6f3669e3b1814cea30147c0801da`.
- Development parent: V9.2 source commit
  `6e6303eef5148c442ceb76bb1cb0c36d02083abb`.

## Repository audit findings

1. `main` is an earlier experimental source baseline. It is not the V9.2 branch and its README correctly says that its normal CI outputs are non-flashable.
2. PR #17 (V8.1), PR #19 (V9.1), and PR #20 (V9.2) remain open Draft PRs. V10 is isolated in a new branch and does not rewrite those branches.
3. V8 is the known user-confirmed bootable baseline. V9.1 has user-reported experimental boot evidence. V9.2 Run #39 completed CI successfully, but its OrangeFox package did not complete on-device; the reported failure occurred in the installer before a successful Boot write was established.
4. V9.2 source CI proves compilation and static integration contracts only. It does not prove physical performance, root runtime, SUSFS runtime, fingerprint, DT2W, suspend residency, or battery improvement.
5. The kernel source itself is fetched at a pinned external commit during CI; the project repository stores patch scripts, validators, manifests, and audit artifacts rather than a complete kernel checkout.
6. The existing foreground boost path calls `cancel_delayed_work_sync()` before checking whether an active same-profile boost can be reused. That can make the high-priority input worker wait for an expiry callback that is already running and doing CPUFreq policy updates. V10.1 targets this specific avoidable wait without changing boost strengths or durations.
7. The current SUSFS feature mask is documented as `0x301` (path, uname, logging). Mount/kstat hiding is not enabled and must not be described as enabled.

## V10.1 implemented in this branch

### Nonblocking same-profile boost renewal

- Move the same-profile reuse decision ahead of synchronous delayed-work cancellation.
- Add an IRQ-safe spinlock protecting the active profile/deadline handoff.
- Keep the existing one-shot `input_boost_rem` work item; no new timer/workqueue/daemon/wake source.
- If the same ordinary-touch or navigation profile is still active and screen is on, extend the same deadline with `mod_delayed_work()` and skip repeated CPUFreq policy transactions.
- Wake boosts, profile transitions, expired boosts, and disabled fast-path settings use the original full path.
- Expiry rechecks the latest deadline under the same lock; a newer renewal is not cleared early.
- Screen-off takes precedence: the expiry callback does not defer an off-screen release, and both renewal paths recheck panel state after requeue.
- Existing boost values remain unchanged: touch 78%/115ms, navigation 82%/145ms, wake 85%/170ms. Existing 100ms input debounce is unchanged.
- Runtime opt-out: `/sys/module/cpu_boost/parameters/ay_v10_boost_fastpath` (root-writable mode 0600).

This is a source-level latency optimization hypothesis. It is not yet a measured device speedup.

## V10 development sequence

### V10.1 — Foreground boost latency
- Nonblocking same-profile renewal (this branch).
- Validate race ordering, panel-off release, and existing thermal policy bounds.
- Do not add Android ActivityManager claims: the kernel input driver does not directly know that an app launch has begun.

### V10.2 — Shared CPUFreq policy refresh (implemented in this branch)
- Replace repeated per-online-CPU policy refreshes with one update per distinct `policy->cpu` leader.
- Read the policy leader under `policy->rwsem`; retain `get_online_cpus()` across enumeration.
- Keep the original per-online-CPU loop behind root-only `ay_v10_policy_dedup` opt-out.
- The RMX2170's observed two-policy topology is expected to need two policy refreshes instead of eight when all eight CPUs are online. This is a source/topology expectation, not a measured latency result.

### V10.3 — Memory Engine: conservative reclaim default (implemented in this branch)
- Keep the V9.1 bounded extra-pass implementation intact, but change `ay_v91_bounded_reclaim` from boot-default ON to boot-default OFF.
- Restore the vendor waiter-zero exit as the normal path. A root-only `0600` runtime opt-in remains available at `/sys/module/vmscan/parameters/ay_v91_bounded_reclaim`.
- The opt-in still requires positive reclaim progress, an unbalanced node, at most one extra pass per balance cycle, and a global >=1-second rate limit; freezer and kthread-stop exits remain unconditional.
- Keep V7.7 `ay_reclaim_progress` OFF, V8.1 single-kswapd enabled, the V8 watermark cap at 50, and the existing LZ4 ZRAM configuration. Do not increase swappiness, ZRAM size, or watermarks.
- Scope is deliberately limited to the default and parameter description in `mm/vmscan.c`; no CPUFreq, touch, DT2W, DeepDoze, thermal, SELinux, vendor driver, or DTB changes.
- Rationale: prior V9/V9.1 device observations were not a matched A/B experiment. V9 reported MemAvailable 1.22 GiB and memory PSI full avg60 35.35%; V9.1 reported 1.35 GiB and avg60 14.27%, with OOM=0 in both reports, but workload and observation windows differed. These numbers do not establish a causal benefit or battery effect. Default-off is a conservative way to stop unproven background reclaim work while retaining an explicit root opt-in.
- No battery or UI improvement is claimed until matched measurements are available.

### V10.4 — Bounded schedutil upward response (implemented in this branch)
- Source audit confirmed the pinned Atoll defconfig enables WALT and schedutil. The pinned kernel implements schedutil in `kernel/sched/cpufreq_schedutil.c`; the source does not contain the previously assumed `drivers/cpufreq/cpufreq_schedutil.c` path.
- Add root-only runtime switch `/sys/module/cpufreq_schedutil/parameters/ay_v10_4_schedutil_fast_up` (mode `0600`), default ON. If the active governor is not schedutil, this parameter has no effect.
- Cap only the configured upward rate-limit delay at 250 microseconds. Existing lower values remain unchanged. The pre-calculation minimum-rate gate is made direction-aware so it does not continue enforcing the old, larger up delay before the upward transition check.
- The down-rate delay is unchanged. Existing UIFirst `SCHED_CPUFREQ_BOOST` bypass remains unchanged. The feature never sets a frequency directly and never changes policy min/max, OPP tables, hispeed settings, WALT placement, scheduler boost values, or thermal limits.
- Root rollback: write `0` to the parameter to restore the vendor schedutil up/down rate-limit behavior without reboot.
- No timers, workqueues, wake locks, wake sources, or screen-off code are added. DeepDoze 600-second timing and screen-off cap are unchanged.
- CI validator checks the 250us cap, dynamic minimum gate, unchanged down-rate delay, boost bypass, and a deterministic model across configured up/down delay combinations.
- This is a bounded responsiveness hypothesis, not a measured device speedup. Runtime A/B and power measurements on RMX2170 are required before claiming improvement.

### V10.5 — DeepDoze and suspend
- Keep the 600-second CLOCK_BOOTTIME deadline and deferrable timer.
- Distinguish CPUFreq cap from actual suspend/CPUIdle residency.
- Do not add wake locks or periodic polling.

### V10.5 — DeepDoze and suspend
- Keep the 600-second CLOCK_BOOTTIME deadline and deferrable timer.
- Distinguish CPUFreq cap from actual suspend/CPUIdle residency.
- Do not add wake locks or periodic polling.

### V10.6 — Integration and release qualification
- Preserve KernelSU Next API6, SUSFS path/uname/logging, SELinux Enforcing, original DTB/vendor drivers, fingerprint, and DT2W.
- Keep V8 and V9.1 recovery images untouched.
- Build and static checks precede any new OrangeFox packaging.
- Physical first boot, root/SUSFS, fingerprint, DT2W, network, thermal, and battery tests are required before a stable V10 claim.

## Release gates

- CI compilation and all legacy source contracts pass.
- New V10.1 race model passes.
- No unauthorized driver, DTB, thermal, SELinux, or suspend-policy changes.
- A V10 kernel artifact remains non-flashable until device-specific Boot/AVB inputs are verified.
- No performance or battery improvement is claimed without matched on-device measurements.

**Version status:** V10.4 development branch / source experiment. V10.1–V10.3 source stages are inherited; V10.4 schedutil fast-up patch and validator are added in this branch. ARM64 CI compilation and source-contract checks are pending. Physical boot, root/SUSFS runtime, fingerprint, DT2W, network, thermal, UI latency, suspend residency, and battery tests are not established. Not a stable release and not authorized for flashing.
