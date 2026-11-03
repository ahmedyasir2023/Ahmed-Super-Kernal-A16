# V2 SUSFS compatibility investigation: Linux 4.14.336 / KernelSU-Next Legacy

**Status: NOT INTEGRATED / NOT FLASHABLE.**

## Confirmed Root baseline

GitHub Actions build #41548897129 (commit `412cb9a3ca69faea4c7503ab10a26c1df967dd99`) succeeded with:
- Device source: `realme-atoll/android_kernel_realme_sm7125` @ `10380039ddcd6ead841e1fc4ca744a2dd6e92fb8`
- Official KernelSU Next Legacy @ `b933b1f728116a456fbebf27b6a8772a640cdf23`
- Android Clang 21.0.0 r563880c
- `CONFIG_KSU=y`, `CONFIG_KSU_MANUAL_HOOK=y`
- `Image.gz` SHA-256: `b9edaa34a90270fb35f6d886966e29123e4e752c55da51ea5f0e27345f2f8691`
- Exactly seven generated DTBs match original Boot by SHA-256
- Root **not** validated on device; SUSFS deliberately not enabled.

## SUSFS source findings

The `kernel-4.14` branch of `kutemeikito/susfs4ksu` at `77905b5a071e6f3669e3b1814cea30147c0801da` defines `SUSFS_VERSION "v1.5.5"` in `kernel_patches/include/linux/susfs.h`.

Its kernel-side patch `50_add_susfs_in_kernel-4.14.patch` targets Linux 4.14 filesystem code. Its **separate KernelSU-side patch** `KernelSU/10_enable_susfs_for_ksu.patch` modifies paths including:
- `kernel/Makefile`, `kernel/Kconfig`
- `kernel/core_hook.c`, `kernel/allowlist.c`, `kernel/ksu.c`, `kernel/ksud.c`
- `kernel/selinux/...`

The official KernelSU-Next Legacy baseline uses a materially different source layout:
- `kernel/Kbuild`, `kernel/core/`, `kernel/hook/`, `kernel/feature/`, `kernel/runtime/`, `kernel/supercall/`.
- That pinned official Legacy commit does **not** contain the separately integrated `kernel/susfs/` tree.

**Therefore, the legacy SUSFS KernelSU-side patch cannot safely be applied verbatim** to the successfully built modern KernelSU Next. Compiling `fs/susfs.o` without the matching KernelSU bridge/user-space ABI is not a working solution.

## Required implementation gates before attempting combined CI

1. Keep V2 modern KernelSU Root-only baseline as immutable reference; preserve the known bootable A16 v1 recovery backup.
2. Review the modern KernelSU supercall dispatcher, `sucompat`, `kernel_umount`, mount namespace lifecycle, and userspace daemon against SUSFS v1.5.5 command IDs and ABI.
3. Port only the needed SUSFS kernel-side hooks to 4.14.336 with exact context checks; reject conflicting hunks; keep Oplus/Realme-specific code.
4. Implement and review a dedicated **version-correct** KernelSU Next ↔ SUSFS bridge. Do not claim SUSFS is functional from Kconfig or object-file presence alone.
5. Enforce `CONFIG_KSU_MANUAL_HOOK=y`, with KPROBES/SYSCALL_TABLE hook modes off for Linux 4.14. Preserve SELinux enforcing.
6. Compile with pinned Clang 21 and compare all seven generated DTBs byte-for-byte with the stock ROM.
7. Publish diagnostic artifacts only; no flashable ZIP, image overwrite, forced vbmeta modifications, or device deployment from CI.
8. Test new KernelSU Root alone on the actual phone first: manager detects a compatible UAPI; SU Compatibility can be enabled; `su -c id` yields `uid=0(root)` with permission granted; no regression to fingerprint/touch/wifi/camera.
9. Test combined SUSFS user-space commands and mounting behavior only after that baseline passes on device.

**Source links**
- Modern Legacy: https://github.com/KernelSU-Next/KernelSU-Next/tree/legacy
- SUSFS kernel 4.14: https://github.com/kutemeikito/susfs4ksu/tree/kernel-4.14
- Compatibility reference: https://github.com/kutemeikito/susfs4ksu/blob/kernel-4.14/kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch
- Successful baseline: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41548897129

## Performance tuning follows root validation

Original RMX2170 source already enables `CONFIG_SCHED_WALT`, `CONFIG_CPU_FREQ_GOV_SCHEDUTIL`, `CONFIG_ZRAM`, `CONFIG_PSI`, `CONFIG_MEMCG`, and `CONFIG_PREEMPT`. Any subsequent Balanced/Turbo profile should be benchmarked for launch latency, retained app count, frame-time consistency, thermal throttling and battery impact; don't just set permanent performance governor or claim RAM has been physically increased.

No feature can be called 'strongest' or 'fastest' without measured comparison.
