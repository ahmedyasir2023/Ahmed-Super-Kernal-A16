# Ahmed Super Kernal A16 — RMX2170

**STATUS: EXPERIMENTAL SOURCE BUILD ONLY — NOT FLASHABLE.**

Target: Realme 7 Pro (RMX2170), Evolution X Android 16, Linux 4.14.336 (non-GKI), Qualcomm Atoll / SM7125.

## Immutable base
- Kernel: https://github.com/realme-atoll/android_kernel_realme_sm7125/tree/aosp-16
- Kernel commit: `10380039ddcd6ead841e1fc4ca744a2dd6e92fb8`.
- Defconfig: `arch/arm64/configs/atoll_defconfig`.
- KernelSU Next / SUSFS legacy integration candidate (community fork, review before flashing): https://github.com/dawood333/KernelSU-Next-susfs/tree/next-v1.5.5, commit `f28feddf9e02ce10548a1e0ed6d15a3a3f5733dc`.
- SUSFS 4.14 kernel-side patch: https://github.com/kutemeikito/susfs4ksu/tree/kernel-4.14, commit `77905b5a071e6f3669e3b1814cea30147c0801da`, mirrored from the [original SUSFS project](https://gitlab.com/simonpunk/susfs4ksu/-/tree/kernel-4.14).
- Build compiler: Android Clang 21 / `clang-r563880c`, matching the original boot kernel compiler. CI downloads the pinned prebuilt archive and verifies SHA-256 `57b456636aa9c3f5e159bc1dd6eddd7c6de654281cad84376e408a5d35f91bab`.

The user-supplied partial ROM ZIP contains `boot.img`, `dtbo.img`, `vbmeta.img`, and `vbmeta_system.img`. Only the local reference images were examined; **original boot-related images are NOT committed to GitHub**.

## CI safety policy

GitHub Actions:
1. Pins/validates the exact source and integration commits.
2. Checks the SUSFS patch applies cleanly; fails if it doesn't.
3. Enables just KernelSU Next and SUSFS on the original Atoll defconfig.
4. Compiles kernel `Image.gz` and device trees.
5. Checks generated config, symbols, gzip integrity, expected version, and unchanged source device drivers.
6. Publishes **non-flashable diagnostic artifacts** only after all checks pass.

**CI does not create AnyKernel3, a flashable ZIP, a modified boot.img, automatic installation, root-hiding userspace modules, or AVB/vbmeta modifications.** The optional local `scripts/repack_boot_nonflashable.py` can create a Boot v2 structure-test image only; it recalculates the unsigned embedded footer but deliberately leaves the separately signed `vbmeta.img` untouched, so the result is not flashable and must never be installed.

A passing CI build does **not** guarantee that the kernel boots on the device; physical device verification and ROM-specific DTB/ramdisk/AVB checks are mandatory before any flash packaging.

Original partial-ROM reference manifest: [reference/boot-manifest.json](reference/boot-manifest.json).

Links: [Workflow runs](../../actions) | [KernelSU Next](https://github.com/KernelSU-Next/KernelSU-Next) | [SUSFS](https://gitlab.com/simonpunk/susfs4ksu).
