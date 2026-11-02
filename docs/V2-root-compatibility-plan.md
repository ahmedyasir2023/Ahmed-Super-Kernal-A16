# Ahmed Super Kernal A16 — V2 root compatibility investigation

**Status: Research / diagnosis only. NOT A FLASHABLE RELEASE.**

Target: Realme 7 Pro RMX2170, Evolution X Android 16, Linux 4.14.336.

## Device evidence (user screenshots, 2026-11-03)

- Boot succeeded with the A16 experimental kernel, Android 16 (API 36) and Linux 4.14.336.
- KernelSU Next Manager v3.4.2 (33355-5) displays `Working` and `BUILT-IN (LEGACY)`.
- KernelSU kernel reports `Unknown (12883-0)`: kernel build code is 12883 and its reported userspace API is 0.
- Manager shows `Kernel update required` and `SUCOMPAT DISABLED`.
- The `SU compatibility`, `Kernel umount`, `SU Log`, and `ADB Root` controls are greyed out.
- Termux `su -c id` reports `No su program found on this device`.
- SELinux is **Enforcing** (must remain enabled).
- **Interpretation:** the old kernel integration is recognized but the current manager's required userspace API and root features are not working. A successful boot is not a functional-root test. Do not assume the presence of KernelSU grants usable superuser access.

## Reproducible source diagnosis

The successful initial build pins:
- KernelSU fork: `dawood333/KernelSU-Next-susfs` @ `f28feddf9e02ce10548a1e0ed6d15a3a3f5733dc`
- SUSFS 4.14 kernel patches: `kutemeikito/susfs4ksu` @ `77905b5a071e6f3669e3b1814cea30147c0801da`
- Atoll 4.14.336 source: `realme-atoll/android_kernel_realme_sm7125` @ `10380039ddcd6ead841e1fc4ca744a2dd6e92fb8`

The old KernelSU fork computes `KSU_VERSION=10000+git-version+198` (the observed value is 12883). Its userspace/kernel API implementation predates the modern manager.

Manager code for v3.4.2 compares `managerUAPIVersion` and `kernelUAPIVersion` and warns when the manager version exceeds the kernel version. The manager shows the SUCOMPAT badge if `!Natives.isSuEnabled()`. The corresponding Settings switch can be disabled if the kernel reports no support.

**New source candidate for research**: official `KernelSU-Next/KernelSU-Next` `legacy` branch @ `b933b1f728116a456fbebf27b6a8772a640cdf23` (2026-10-28), rather than the old community fork. This is NOT yet established as compatible with SUSFS or the RMX2170 kernel.

## Critical 4.14 compatibility constraints

1. Preserve **all hardware drivers, original DTB, stock ramdisk and AVB partition metadata**.
2. Pin the original A16 source / Clang 21 build and the reference boot manifest.
3. KernelSU's current legacy branch offers manual hooks. Its Kconfig explicitly warns against KPROBES hook mode below Linux 5.10, and syscall-table patching requires Linux >=4.17; **do not assume either hook mechanism will work on 4.14**. A reviewed manual-hook integration may be necessary.
4. Modern KernelSU's source layout changed significantly (new `kernel/core`, `kernel/feature`, `kernel/hook`, `kernel/supercall` etc.). Do **not** reuse old fork-specific Makefile or helper-function injection scripts against it without a source review.
5. SUSFS must be integrated only after checking that its version, Kconfig symbols, LSM hooks, procfs changes and feature interfaces match the newer KernelSU code. Compiling `fs/susfs.o` alone is not sufficient evidence.
6. Do not spoof/version-bump 12883 to 33355 as a substitute for implementing and verifying the actual required UAPI.
7. Keep SELinux enforcing; no unrelated tuning or root-hiding features.

## V2 release gates

- Reviewed, explicit KernelSU Next version and UAPI; manager v3.4.2 detects a compatible implementation without version spoofing.
- Manual hook mode compiled and verified for Linux 4.14, including root permission authorization and mount namespace behavior.
- SUSFS version/ABI checked at source and runtime. No unresolved patch hunks.
- Linux 4.14.336, Clang 21, original seven DTBs, fingerprint, touch, modem and Wi-Fi configs validated.
- CI produces `Image.gz`, detailed source/config report and DTBs **only**; no flashable ZIP until successful ROM-specific boot validation.
- Backup of the **current bootable modified Boot** saved and verified by checksum prior to any on-device test.
- On-device A16 V2 test: Android boots, fingerprint/touch/network work, manager recognizes current API, SU Compatibility can be enabled, Termux `su -c id` reports `uid=0(root)` *after explicit root grant*, SUSFS functional test passes, SELinux remains Enforcing.

## Official upstream references

- https://github.com/KernelSU-Next/KernelSU-Next/tree/legacy
- https://github.com/KernelSU-Next/KernelSU-Next/blob/v3.4.2/manager/app/src/main/java/com/rifsxd/ksunext/ui/screen/Home.kt
- https://github.com/KernelSU-Next/KernelSU-Next/blob/v3.4.2/manager/app/src/main/java/com/rifsxd/ksunext/ui/screen/Settings.kt
- https://github.com/KernelSU-Next/KernelSU-Next/blob/v3.4.2/manager/app/src/main/java/com/rifsxd/ksunext/ui/util/KsuCli.kt

**Do not flash any new images until each gate is demonstrably satisfied.**
