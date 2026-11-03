# RMX2170 V2 Root Baseline and V3 Migration Gates (2026-11-03)

## Confirmed user-device status

The user reported that Android 16 boots on the V2 **root-only** kernel, and after updating the KernelSU Next Manager and rebooting, **Root now works**. Prior screenshots show:
- Kernel version `4.14.336`; Android 16 (API 36).
- `KernelSU Next v3.4.0-legacy (33318-6)` and Manual hook mode.
- `KernelSU Next` manager initially displayed UAPI 5-to-6 mismatch; the development manager was updated to API 6 and re-detected after reboot.
- SELinux was `Enforcing` in the previous screenshots.

This is user-reported **functional Root**, not a complete regression test. Do not mislabel it as a SUSFS-enabled build or a benchmarked performance kernel. No screenshot of the final `su -c id` success output is preserved in this branch.

Known-good V2 Root-only build: [GitHub Actions 41548897129](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41548897129), commit `412cb9a3ca69faea4c7503ab10a26c1df967dd99`.

## Current source engineering status

1. **V3 KernelSU API 4 SUSFS reference laboratory**: source integration and manual hooks validated. An initial build [41655249789](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41655249789) failed at an undefined `susfs_set_current_proc_umounted()` helper. A pinned helper port from the Realme SM7125 crDroid SUSFS-aware kernel was added with thread flag collision checks. CI re-run [41658824203](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41658824203) compiles the reference. **Even successful reference output must never be installed: its Root UAPI is 4, not 6.**
2. **Working API 6 SUSFS bridge audit**: [41659525950](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41659525950) succeeded. The legacy SUSFS patch has 13/18 paths missing in modern API 6. The SUSFS-aware reference contains 58 distinct SUSFS-prefixed references absent from the pinned official API-6 codebase. This proves that silently cherry-picking the old patch would be unsafe.
3. **Performance**: the read-only benchmark collector passed CI [41655060968](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41655060968). App launch latency, memory/PSI/ZRAM state and thermal baseline have not been measured on the device.

## V3 execution gates

1. Keep the functional V2 API-6 kernel unchanged as a recovery baseline.
2. Use the API-4 SUSFS reference strictly as a source implementation guide. Never spoof its `KERNEL_SU_UAPI_VERSION` to 6.
3. Implement or validate the real API-6 equivalents of the SUSFS init, task/setuid and mount-state logic, SELinux domain logic, supercall handlers, userspace command IDs and feature guards. Require source-reviewed interfaces.
4. Compile using pinned Android Clang 21 and independently verify generated DTBs match the original Boot.
5. Test SUSFS with the correct userspace tool and reproduce root, app launch, network, fingerprint, suspend and SELinux functionality on a real RMX2170 device.
6. Establish baseline performance measurements before applying any CPU, scheduler, ZRAM or thermal changes. Change only one tunable at a time.
7. **No flashable ZIP and no vbmeta modifications** until the full API-6 bridge is built, structurally checked and runtime validated.

Sources:
- https://github.com/KernelSU-Next/KernelSU-Next/tree/legacy
- https://github.com/kutemeikito/susfs4ksu/tree/kernel-4.14
- https://github.com/crdroidandroid/android_kernel_realme_sm7125
