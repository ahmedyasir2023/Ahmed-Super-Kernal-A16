# V4 RMX2170 release gates (nonflashable)

## Verified facts from the 2026-11-03 build

- Source branch: `v4-susfs-dt2w-integration`, commit `2467eeac481d0b64b1f5c68f4e5b6b0f359b56f9`.
- GitHub Actions run [41680846239](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41680846239): **SUCCESS**.
- Official KernelSU Next Legacy API 6, SUSFS v1.5.5 Path-only + uname + log, and Realme double-tap default patch compiled using pinned Android Clang 21.
- V4 Image.gz SHA-256: `c68cb06389a81682802836c896b1ad4b75117d019fdc884273734b267131c21e`.
- Seven compiled DTBs match the ROM concatenated DTBs byte-for-byte.
- User previously confirmed **V2 Root works on-device**. This does not establish V4 boot or Root.

## Independently checked original BOOT structure

Validated against the original Evolution X Android 16 RMX2170 ROM and the user's OrangeFox BOOT backup:

| Property | Verified |
|---|---|
| Boot header | Android boot image header v2, header size 1660 |
| Partition size | 64 MiB (67,108,864 bytes) |
| Page size | 4096 |
| Original kernel size | 19,590,365 bytes |
| New V4 kernel size | 19,647,971 bytes |
| Preserved original Ramdisk | 1,581,241 bytes; SHA-256 `9907076b0a45ce9afc1fb950d42f860e29e25f02cea3172e3dda288c406bf923` |
| Preserved original concatenated DTB | 2,775,467 bytes; SHA-256 `212d8e40f9d3025c92f1c11c2dc40761820dc5310c41bafbc48a88bd39d23af8` |
| Original ROM BOOT SHA-256 | `4101a2db9a8fdc388f44a3ce4a23c14b2a856c5a902126513624b9c6c4db2653` |
| OrangeFox BOOT backup SHA-256 | `9f6bf13ea3ad98ae3613cb53f7e9e4bf56fac02c939b73cd01a1bd5642470d08` |
| Boot internal ID and embedded AVB boot hash descriptor | Verified individually for both originals |
| New hypothetical Ramdisk offset | 19,652,608 |
| New hypothetical DTB offset | 21,237,760 |
| New hypothetical AVB start | 24,014,848 |

Important: These are **structural checks of components, not a built Boot image**. When repacking, Android Boot v2 ID and the embedded AVB SHA-256 hash descriptor must be recalculated and independently verified. The original AVB hash descriptor is unsigned and does not imply the external AVB chain or installation policy can be ignored. No device partition was written.

## Known DT2W limitation

`scripts/v4/patch_dt2w_default.py` makes exactly one source change: sets `DouTap_enable=1` instead of `0` in `touchpanel_common_driver.c`. The original vendor initialization already has `ts->gesture_enable=1`. **This does not prevent Android or the touchscreen HAL from overwriting the setting**. Physical double-tap wake, charging state, suspend IRQ, wake after reboot, after overnight suspend and touchpanel variations all require on-device checks. The kernel setting is not a promise of wake behavior when powered off or before the touch driver has probed.

## V4 acceptance sequence

1. Keep V2 working Root BOOT, OrangeFox recovery and a tested rollback path. Do not wipe.
2. Run read-only tooling first:
   - `python tools/verify_dt2w_after_reboot.py` to inspect touchscreen proc state.
   - `python tools/verify_dt2w_after_reboot.py --reboot` **only if you deliberately approve an actual phone restart**; script does not write `/proc` but reboots the device.
   - `python tools/benchmark_rmx2170.py --runs 10 --cold` for comparable app launch measurements.
   - `python tools/measure_idle_battery_rmx2170.py --help` for battery baseline.
3. Independently assemble and check an experimental V4 BOOT **only after explicit device acceptance and known-good rollback are confirmed**, preserving the original Ramdisk/DTB/header and recalculating ID/AVB metadata. Do not publish a flash ZIP prematurely.
4. V4 on-device checks, in order: Boot, root `su -c id`, KernelSU API 6 manager, SELinux Enforcing, DT2W on reboot and repeated suspend, calls/SMS, network, fingerprint, camera, charging, 1h and overnight standby, then SUSFS userspace functionality.
5. Keep screen-off optimizations and performance profiles on separate branches and measure them independently. No permanent `performance` governor, thermal-safety disable, or unbounded wake boost.

## Current release status

- V2: user-reported working Root.
- V4: compiled, source checks and DTBs passed; BOOT component structure independently checked; **device runtime not verified**.
- SUSFS path hiding: compiled; **not confirmed active on the device**.
- Full DT2W persistence: compile-only; **not confirmed after reboot**.
- Battery and performance improvements: measurement tools available; **no measured gains and no tuned power profile**.

No flashable V4 ZIP has been generated in this release-gate branch.
