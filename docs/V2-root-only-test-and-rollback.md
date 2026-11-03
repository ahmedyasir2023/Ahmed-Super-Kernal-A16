# V2 Root-only test package and safety gate

**Experimental. No SUSFS. No performance profile. Not a final release.**

The known V2 Root-only build passed GitHub Actions on run [41548897129](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41548897129) using official KernelSU-Next Legacy and manual hooks for Linux 4.14. The produced ARM64 Image.gz SHA-256 is `b9edaa34a90270fb35f6d886966e29123e4e752c55da51ea5f0e27345f2f8691`. Seven DTBs match the original ROM.

An **offline-only** boot assembly was checked against the user's previously bootable V1 image. The Ramdisk and concatenated DTB were retained byte-for-byte, and Android boot header v2, SHA-1 ID, embedded unsigned AVB hash and AVB Footer were recalculated and independently checked.

## Reproducible SHA-256 identifiers

| Item | SHA-256 |
|---|---|
| Old bootable V1 (also rollback target) | `6f395e68190aea8addfbad358ba47acde4cf0f0f604f6c71229661230224bf1e` |
| Previous OrangeFox Boot backup (private, not committed) | `9f6bf13ea3ad98ae3613cb53f7e9e4bf56fac02c939b73cd01a1bd5642470d08` |
| V2 Root-only Image.gz | `b9edaa34a90270fb35f6d886966e29123e4e752c55da51ea5f0e27345f2f8691` |
| V2 Root-only test boot image | `4d9008935e5a9f096903a9d3c037b41676b7ed4c83631a6f0fa5d3fbbb3b08d6` |
| Preserved Ramdisk | `9907076b0a45ce9afc1fb950d42f860e29e25f02cea3172e3dda288c406bf923` |
| Preserved concatenated DTB | `212d8e40f9d3025c92f1c11c2dc40761820dc5310c41bafbc48a88bd39d23af8` |

The root-only test boot is 64 MiB; new kernel size is 19,639,879 bytes. Its new Ramdisk offset is 19,644,416 bytes; DTB offset 21,229,568 bytes; embedded AVB starts at 24,006,656 bytes. External vbmeta is not modified. Hardware behavior remains unverified.

## Recovery-only guarded test ZIP

If the owner elects to conduct the on-device test, the recovery package must:

- accept only verified RMX2170/reatoll,
- require a SHA-256 match to the specific known-good V1 boot **before** writing,
- save another complete verified Boot backup under internal storage,
- unpack an embedded boot.img and check its exact SHA-256 and length,
- write only BOOT, then read back and check SHA-256, attempting recovery from the backup after a failed post-write checksum,
- leave vbmeta, dtbo, recovery, userdata and system untouched, with no wipe,
- be accompanied by a pretested rollback ZIP that restores the previous bootable V1 only from the exact known V2 image, as well as the separate original OrangeFox backup.

Neither kernel boots nor root permissions are guaranteed by offline checks. The recoverable V1 image and original OrangeFox backup must remain available.

## Device acceptance tests

Before adding SUSFS or performance changes, verify:

1. Boot to Android 16; fingerprint, touchscreen, Wi-Fi, mobile data, camera, Bluetooth, charging and wake/suspend work.
2. KernelSU Next Manager recognizes the new kernel API, without `Kernel update required`.
3. The SU Compatibility setting is available and enabled; Termux is explicitly granted Root in the manager.
4. `su -c id` returns `uid=0(root)`; SELinux remains Enforcing.
5. Root persists through one normal reboot.
6. If any boot regression occurs, restore previous bootable V1 from OrangeFox and stop.

Do not claim Root, SUSFS or speedups are functional until measured. This branch does not contain root hiding.
