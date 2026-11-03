# Ahmed Super Kernal A16: V3 SUSFS API6 integration status

Target: Realme 7 Pro RMX2170, Evolution X Android 16, Linux 4.14.336.

## Verified starting point

- User reported that official KernelSU Next Legacy Root UAPI 6 is working on the phone.
- Root-only V2 compile: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41548897129
- SUSFS filesystem core plus API6 compile: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41660453562
- SUSFS v1.5.5 read-only command handshake compile: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41662832233

These GitHub successes establish source and build compatibility, not runtime hiding.

## Active incremental feature branches

Logging experiment: v3-api6-susfs-logging-lab
- Adds root-only official SUSFS commands SHOW_VERSION, SHOW_VARIANT, SHOW_ENABLED_FEATURES and ENABLE_LOG.
- Build-time feature bitmap: 0x200 (logging only).
- No hiding operations; no Boot or flashable recovery ZIP.

Uname experiment: v3-api6-susfs-uname-lab (this branch)
- Extends the logging branch with root-only SET_UNAME, bounded input checks, and upstream SUSFS 4.14 newuname hook.
- Feature bitmap: 0x300 (uname bit 8 plus logging bit 9).
- No path hiding, mount hiding, kstat spoofing or redirection.
- No device-facing installation package.

## Blockers to general SUSFS hiding

1. Review and port the SUSFS v1.5.5 per-task zygote/app state tracking into the official KernelSU API6 SELinux and setuid logic. The 4.14 filesystem patch checks current->susfs_task_state and requires correct lifecycle signals.
2. Audit locking and potential sleeps in the old SUSFS mount/path list implementations, especially kern_path under spinlock.
3. Preserve the original vendor drivers, untouched DTBs, original Ramdisk and boot header.
4. Require compile/link success, checked userland ABI and device-side runtime verification of SU, SELinux, networking, camera, fingerprint, DT2W and suspend stability.
5. Preserve the working V2 boot and a verified rollback method. No ZIP until the complete Boot assembly and on-device acceptance tests can be safely planned.

Performance changes follow verified SUSFS and baseline measurements. Never force unsafe clocks or permanently disable thermal/SELinux protections.

Source: https://github.com/kutemeikito/susfs4ksu/tree/kernel-4.14
