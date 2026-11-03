# V5 HyperSpeed: working Boot exact-hash release gate

Device: Realme 7 Pro RMX2170, Evolution X Android 16. V5 source build [41698663363](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41698663363) was **SUCCESS** but is **NOT FLASHABLE**.

## Actual current Boot digest supplied from rooted Termux

```
su -c 'sha256sum /dev/block/bootdevice/by-name/boot'
e2577dc5c167ee0cb25c22be8a41598f5302bb393ea52b3eb8aef8fdb6c2d08d  /dev/block/bootdevice/by-name/boot
```

This digest is authoritative for the live boot partition **at the time it was measured**, but the actual 64-MiB image contents have not yet been received.

It **does not match** either previously supplied source image:

- Original EvolutionX ROM Boot: `4101a2db9a8fdc388f44a3ce4a23c14b2a856c5a902126513624b9c6c4db2653`
- Older OrangeFox backup Boot: `9f6bf13ea3ad98ae3613cb53f7e9e4bf56fac02c939b73cd01a1bd5642470d08`
- Prior **V2 experimental test image** (not evidence of what is currently installed): `4d9008935e5a9f096903a9d3c037b41676b7ed4c83631a6f0fa5d3fbbb3b08d6`

Hash mismatch alone **does not prove that the current Root is broken**, or that the current Ramdisk/DTBs differ. It means repacking from an old Boot image would be an unverified assumption. The actual image must be inspected first.

## Read-only device capture and offline approval

For a rooted Termux session (copy the image to Downloads; **do not flash**):

```sh
su -c 'dd if=/dev/block/bootdevice/by-name/boot of=/sdcard/Download/A16-CURRENT-WORKING-BOOT.img bs=4M && sha256sum /sdcard/Download/A16-CURRENT-WORKING-BOOT.img'
```

Expected SHA-256 is the live digest above. If it differs, stop, recheck the live partition and identify when it changed. Verify the copy is 67,108,864 bytes, then securely preserve the backup and inspect/upload it for analysis. Copy it to a computer or external storage before any installation trial.

Offline comparison gates:

1. Exact full-image digest matches `e2577dc5c167ee0cb25c22be8a41598f5302bb393ea52b3eb8aef8fdb6c2d08d`.
2. Check Boot header v2, layout, OS version, addresses, kernel command line and second-stage parameters against EvolutionX.
3. Compare **current** Ramdisk and DTB to original ROM; preserve any differences unless understood.
4. Independent Boot ID and AVB hash descriptor validation; preserve all 7 DTBs and vendor hardware features.
5. Have a known-working rollback and **only then** consider an explicitly test-labeled, exact-current-hash-guarded installer.
6. Device validation must prove actual Root, SELinux Enforcing, suspend, DT2W after reboot, fingerprint, radios, charging and performance measurements.

This branch is a release gate only; **no flashable ZIP or Boot image is published**. It does not claim a proven V5 boot, Root or performance result.
