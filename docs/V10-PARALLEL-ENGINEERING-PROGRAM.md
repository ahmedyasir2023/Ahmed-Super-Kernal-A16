# AY HyperCore V10 — Parallel Engineering Program

## Objective

Develop the next kernel as ten isolated engineering tracks in parallel, then combine only the tracks that pass source review, static validation, ARM64 compilation, and integration checks. The user should not have to flash and test every intermediate branch. Device testing is reserved for the integrated release candidate, except for one-time baseline collection if a specific hardware measurement is needed.

Target remains Realme 7 Pro RMX2170 / Qualcomm SM7125 Atoll, Evolution X Android 16, Linux 4.14.336, Android Clang 21, KernelSU Next UAPI 6, and the currently pinned SUSFS 4.14 source.

## Branch topology

- Parent/integration branch: `v10-parallel-integration`
- Feature branches: `v10-parallel-<track>`
- Final integration branch: `v10-final-integration` (created after feature review)
- Every feature branch starts from the same integration baseline and owns only its directory under `scripts/parallel/<track>/` plus its track documentation.
- Each feature branch receives its own CI run. The workflow applies only the matching track on a feature branch.
- The integration branch runs every track already merged, in the fixed order in `scripts/parallel/INTEGRATION_ORDER.txt`.
- The final branch requires all ten tracks to exist, then runs the complete combined build and release gates.
- Feature PRs remain Draft until their source contracts and ARM64 build pass. No automatic merge is permitted.

## Parallel tracks

| Track | Branch | Scope and intended engineering output |
|---|---|---|
| 1. Power and suspend | `v10-parallel-power-suspend` | DeepDoze 600 s, PM suspend cycles, wakeup-source attribution, CPUIdle residency, screen-off current. First isolate the cause of overnight drain; do not add wakelocks or periodic polling. |
| 2. Memory engine | `v10-parallel-memory-engine` | kswapd, direct reclaim, PSI, page allocation stalls, ZRAM accounting and LMKD interaction. Preserve conservative V10.3 defaults until controlled evidence supports a change. |
| 3. Scheduler and UI latency | `v10-parallel-scheduler-ui` | WALT, schedutil, CPUFreq policy updates, runqueue behavior, foreground input response and bounded boost coalescing. Preserve thermal caps and policy min/max limits. |
| 4. Input and touch | `v10-parallel-input-touch` | Double-tap-to-wake, touch event path, panel blank/unblank ordering, wake latency and race safety. Fingerprint and DT2W are hard regression gates. |
| 5. Storage and I/O | `v10-parallel-storage-io` | Block layer, F2FS, writeback, I/O scheduling, fsync latency and storage-related wakeups. No destructive filesystem operations or unmeasured queue-depth changes. |
| 6. GPU and display | `v10-parallel-gpu-display` | KGSL/devfreq, DRM/display pipeline, frame pacing, refresh behavior and GPU idle. No permanent GPU frequency pinning, panel/DTB edits or thermal bypass. |
| 7. Thermal efficiency | `v10-parallel-thermal-efficiency` | Thermal framework, cooling-device behavior, CPU/GPU throttling coordination and performance per watt. Never disable, bypass or raise safety limits. |
| 8. Network stack | `v10-parallel-network-stack` | TCP/IP behavior, Wi-Fi/mobile data wakeups, packet processing and suspend interaction. Preserve vendor WLAN/modem drivers and firmware. |
| 9. Root and security | `v10-parallel-root-security` | KernelSU Next API6, SUSFS compatibility, SELinux Enforcing, root detection surface and fail-closed behavior. Existing feature mask is 0x301 (path, uname, logging); mount/kstat hiding must not be claimed or enabled without a separate audited implementation. |
| 10. Benchmark and release | `v10-parallel-benchmark-release` | Reproducible latency, memory, power, thermal and boot qualification; artifact hashes; rollback and final packaging audit. No flashable ZIP until exact device boot/AVB inputs are verified. |

## Shared engineering invariants

1. Preserve KernelSU Next UAPI 6 and the existing root integration.
2. Preserve the currently supported SUSFS feature set and never claim unsupported hiding features.
3. Keep SELinux Enforcing.
4. Preserve fingerprint, double-tap-to-wake, panel wake, Wi-Fi/mobile data and normal suspend/resume.
5. Preserve the original device tree and vendor drivers unless a separately reviewed, device-specific defect proves a change is necessary.
6. Never bypass thermal protection, pin maximum CPU/GPU frequencies, or introduce a performance governor as a shortcut.
7. DeepDoze remains screen-off only, starts after 600 seconds, and must not create a wake source merely to apply a CPU cap.
8. No active polling loops, permanent wakelocks, or background daemons without measured justification.
9. Every tunable must have a safe default, a root-only runtime rollback where applicable, and a validator.
10. No performance or battery claim is accepted without matched measurements and explicit workload/window reporting.

## CI and merge gates

For each feature branch:
- Python/shell syntax validation.
- Track-specific source contract checks.
- No unauthorized source-tree changes.
- Full ARM64 build against the same pinned kernel, toolchain, KSU and SUSFS commits.
- Existing V7/V8/V9/V10 validators remain mandatory.

For integration:
- Apply all merged tracks in manifest order to one clean pinned source checkout.
- Run every legacy and track-specific validator after all patches have been applied.
- Build once from the combined source.
- Compare the combined diff against the allowlist and preserve the original DTB/vendor compatibility.
- Publish source-only/non-flashable artifacts until device-specific packaging is audited.

## Device test strategy

Do not ask the user to flash each feature branch. First collect read-only subsystem baselines only where needed. After all tracks are integrated and CI passes, prepare one final candidate and one consolidated device-validation checklist covering:
- first boot, root and SUSFS status;
- fingerprint and DT2W;
- Wi-Fi, mobile data, calls and Bluetooth;
- foreground launch/scroll/touch latency;
- memory PSI, kswapd, ZRAM and OOM;
- thermal behavior under sustained load;
- screen-off suspend residency and wake-source deltas;
- battery current and charge loss over a controlled overnight interval.

If the integrated candidate fails a gate, revert or disable only the responsible track and rebuild the candidate. Do not restart the entire project from scratch.

## Current baseline and status

The feature baseline is the V10.4 source branch at commit `57355b5d2bccc47ba7e7b225ea5c96e1eddd4120`, with the parallel CI orchestration added on this branch. V10.4 is a source experiment, not a user-validated stable release. The previously user-confirmed V8 baseline and existing V9 branches are not rewritten.

**Release naming:** the integrated result will be assigned a final version only after the ten tracks pass the combined gates. Do not call an individual feature branch a stable release.
