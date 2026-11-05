# Ahmed Super Kernal A16 V8 — HyperSpeed / Realme 7 Pro RMX2170

Target: **Evolution X Android 16 (2026-11-02)**, original Realme Linux **4.14.336**, KernelSU Next API 6 and the established SUSFS kernel integration. Retain the confirmed bootable V7.7 hardware-driver base.

## V8 changes (kernel source, automatic at boot)

| Area | V7.7 baseline | V8 |
|---|---|---|
| Adaptive touch CPU boost | 72% of allowed policy range, 105 ms | **78%, 115 ms** |
| Touch-event debounce | 150 ms | **100 ms** |
| InstantWake CPU boost on unblank | 82% of allowed policy range, 155 ms | **85%, 170 ms** |
| WALT scheduler input boost | 3 | **3, unchanged** |
| Screen-off boost | disabled by existing panel notifier | **unchanged; no input boost while display is off** |
| DeepDoze | 600 seconds after display blank, restore on unblank | **unchanged** |
| DT2W | built-in touch init enabled after reboot | **unchanged** |
| Memory watermark handling | Vendor ROM requests `watermark_scale_factor=200` | **kernel caps excessive userspace writes at 50** |
| KernelSU Next / SUSFS | API6 legacy hooks and path+uname+logging bridge | **unchanged** |
| Thermal HAL / thermal control | stock vendor drivers with Thermal Bypass disabled | **unchanged** |
| Maximum CPU frequency/governor | schedutil, hardware thermal ceilings | **unchanged; NO max-frequency pin** |
| kswapd threads | vendor runtime 2 | **unchanged** |

The memory setting is based on the owner's 17s-per-arm real-stall A-B-A result with Memory PSI full at `70.69% → 45.46% → 76.51%` (watermark 200→50→200) and kswapd combined CPU ticks 3422→2160→3433. A factor of 50 **improved but did not eliminate** stalls. Direct-reclaim scans, allocation stalls and major faults continued in the factor-50 period. It is therefore not accurate to claim that V8 eliminates memory pressure or that its performance and battery are device-verified.

### Built-in safety rollback — no module or app required for normal use

If memory latency or app launch becomes worse, root can opt out of the new watermark cap without flashing, and the original ROM's value can be restored:

```sh
su -c 'echo 0 > /sys/module/page_alloc/parameters/ay_v8_latency_watermarks; echo 200 > /proc/sys/vm/watermark_scale_factor'
```

The default cap is enabled when V8 boots; no Magisk/KernelSU startup scripts are required. The guard is exposed root-only (`0600`). This optional troubleshooting command should not be necessary during normal use, and it **does not change V8's bounded touch/wake profile**. Reboot resets the root-only guard to enabled. Do not disable Thermal HAL or SELinux to gain speed.

### Build and release boundaries

Full pinned Android Clang 21 kernel build in `.github/workflows/v8-hyperspeed-build.yml` compiles ARM64 `Image.gz` and original device trees after staging the entire V7.7 KernelSU Next/SUSFS/DT2W/DeepDoze chain. Source checks protect read-only sysfs defaults, untouched touch-driver hardware and original DTB, and unchanged thermal/boot/power drivers.

The workflow currently outputs a **kernel Image.gz, not a guaranteed flashable OrangeFox ZIP**. Any recovery ZIP must use the verified owner's *known-good installed V7.7 boot image*, reproduce exactly its original Android 16 ramdisk and DTB, update the boot image ID and embedded checksum, check the 64 MiB partition length, and verify its source SHA256 on the phone before writing. External vbmeta/AVB compatibility and first hardware boot cannot be validated from CI alone.

After first flash, validate normal reboot, KernelSU root, fingerprint, DT2W, thermal services and screen-off suspend. Keep the independent V7.7 boot backup before any installation.

Known limitation: boosting short CPU bursts can increase screen-on power draw. Bigger boosts are not guaranteed to make app process startup faster when Android's launcher, storage or memory reclaim is the bottleneck.

**Do not claim success until CI build and device boot are confirmed.**
