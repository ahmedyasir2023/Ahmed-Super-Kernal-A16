# V10 — AY HyperCore: source audit and staged engineering plan

## Target and immutable inputs

- Device: Realme 7 Pro RMX2170 / Qualcomm SM7125 Atoll.
- ROM target: Evolution X Android 16 (SDK 36).
- Kernel: Linux 4.14.336, pinned upstream source commit
  \`10380039ddcd6ead841e1fc4ca744a2dd6e92fb8\`.
- Compiler: pinned Android Clang 21 \`clang-r563880c\`.
- Root integration: KernelSU Next UAPI 6, pinned commit
  \`b933b1f728116a456fbebf27b6a8772a640cdf23\`.
- SUSFS: 4.14 patch commit
  \`77905b5a071e6f3669e3b1814cea30147c0801da\`.
- Development parent: V9.2 source commit
  \`6e6303eef5148c442ceb76bb1cb0c36d02083abb\`.

## Repository audit findings

1. \`main\` is an earlier experimental source baseline. It is not the V9.2 branch and its README correctly says that its normal CI outputs are non-flashable.
2. PR #17 (V8.1), PR #19 (V9.1), and PR #20 (V9.2) remain open Draft PRs. V10 is isolated in a new branch and does not rewrite those branches.
3. V8 is the known user-confirmed bootable baseline. V9.1 has user-reported experimental boot evidence. V9.2 Run #39 completed CI successfully, but its OrangeFox package did not complete on-device; the reported failure occurred in the installer before a successful Boot write was established.
4. V9.2 source CI proves compilation and static integration contracts only. It does not prove physical performance, root runtime, SUSFS runtime, fingerprint, DT2W, suspend residency, or battery improvement.
5. The kernel source itself is fetched at a pinned external commit during CI; the project repository stores patch scripts, validators, manifests, and audit artifacts rather than a complete kernel checkout.
6. The existing foreground boost path calls \`cancel_delayed_work_sync()\` before checking whether an active same-profile boost can be reused. That can make the high-priority input worker wait for an expiry callback that is already running and doing CPUFreq policy updates. V10.1 targets this specific avoidable wait without changing boost strengths or durations.
7. The current SUSFS feature mask is documented as \`0x301\` (path, uname, logging). Mount/kstat hiding is not enabled and must not be described as enabled.

## V10.1 implemented in this branch

### Nonblocking same-profile boost renewal

- Move the same-profile reuse decision ahead of synchronous delayed-work cancellation.
- Add an IRQ-safe spinlock protecting the active profile/deadline handoff.
- Keep the existing one-shot \`input_boost_rem\` work item; no new timer/workqueue/daemon/wake source.
- If the same ordinary-touch or navigation profile is still active and screen is on, extend the same deadline with \`mod_delayed_work()\` and skip repeated CPUFreq policy transactions.
- Wake boosts, profile transitions, expired boosts, and disabled fast-path settings use the original full path.
- Expiry rechecks the latest deadline under the same lock; a newer renewal is not cleared early.
- Screen-off takes precedence: the expiry callback does not defer an off-screen release, and both renewal paths recheck panel state after requeue.
- Existing boost values remain unchanged: touch 78%/115ms, navigation 82%/145ms, wake 85%/170ms. Existing 100ms input debounce is unchanged.
- Runtime opt-out: \`/sys/module/cpu_boost/parameters/ay_v10_boost_fastpath\` (root-writable mode 0600).

This is a source-level latency optimization hypothesis. It is not yet a measured device speedup.

## V10 development sequence

### V10.1 — Foreground boost latency
- Nonblocking same-profile renewal (this branch).
- Validate race ordering, panel-off release, and existing thermal policy bounds.
- Do not add Android ActivityManager claims: the kernel input driver does not directly know that an app launch has begun.

### V10.2 — Memory latency and reclaim
- Audit actual V8.1 single-kswapd and V9.1 bounded-reclaim interactions.
- Preserve vendor freeze/stop, watermark, PSI, and memcg semantics.
- Avoid changing the default reclaim policy until there is a concrete code-level reason; retain a root-only rollback switch for any experiment.
- No arbitrary ZRAM size, swappiness, or watermark increases.

### V10.3 — Scheduler and UI latency
- Inspect WALT/schedutil, CPU placement, policy transition costs, and input-to-frame path.
- No performance governor lock, no out-of-range frequencies, no disabling thermal limits.

### V10.4 — DeepDoze and suspend
- Keep the 600-second CLOCK_BOOTTIME deadline and deferrable timer.
- Distinguish CPUFreq cap from actual suspend/CPUIdle residency.
- Do not add wake locks or periodic polling.

### V10.5 — Integration and release qualification
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

**Version status:** V10 development branch / V10.1 source experiment. Not a stable release and not authorized for flashing.
