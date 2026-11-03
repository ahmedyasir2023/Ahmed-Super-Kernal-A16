# V7: 10-minute DeepDoze CPU policy cap (experimental)

**This branch builds source and diagnostic artifacts only. NO FLASHABLE ZIP.**

## What is implemented

- Built on the successful V6 Realme 7 Pro (RMX2170) Android 16 pinned source build.
- A DRM primary-display POWERDOWN notification releases V6 touch/WALT boost and arms **one deferrable timer for 600 seconds**, without an Android daemon or periodic polling.
- On timer expiry while the panel is still off, the existing CPUFreq policy adjust notifier caps **maximum policy frequency to the minimum allowed by that policy**, preserving any higher pre-existing policy minimum. This is not a forced lower hardware frequency, and does not override thermal limits or force a governor change.
- On the earliest UNBLANK notification, the cap is disabled immediately, the timer is canceled without blocking the notifier, and policy reevaluation is queued in work context before/alongside the V6 bounded InstantWake boost (82%, 155 ms).
- A one-shot timer may be deferred while the CPU is idle/suspended. That is intentional: never wake the phone solely to engage a frequency cap when it is already asleep.
- KernelSU Next/SUSFS path+uname+logging and DT2W original driver initialization remain unchanged.
- Read-only module parameters (when exposed by the built-in driver): ay_deepdoze_enabled, ay_deepdoze_delay_seconds, ay_deepdoze_active, ay_deepdoze_entries.

## Limits / acceptance criteria

This is *not* Android framework Doze integration, a CPU hardware suspend state, GPU underclocking, or proof of zero standby drain. It may delay background tasks when screen is off for 10 minutes. Stock hardware suspend and cpuidle remain authoritative.

CI checks source contracts, compiled Image.gz, DTB matching, root/SUSFS objects, and forbidden vendor modifications. CI does not validate physical device wake timings or application launch speed.

Before an installable artifact can be released:
1. Match exact installed Evolution X ROM boot, ramdisk, dtb, dtbo, vbmeta chain and partition boot format. Keep untouched copies and a recovery route.
2. Verify an intact signed/verified boot flow appropriate for that device. **Never silently disable AVB or flash vbmeta.**
3. After the experimental kernel boots, confirm KernelSU root, fingerprint, DT2W directly after reboot and after 15 minutes screen-off, and screen-on CPUPolicy update.
4. Test 15 minutes screen-off with no power source and inspect module parameters, CPU policy limits, sleep suspend counters, thermals, Wi-Fi and mobile data before declaring battery savings.
5. Test consecutive off->on->off cycles for a stuck max-frequency cap and verify normal thermal throttling.

Observe on device (only after a separately validated bootable image is installed):

    su -c 'for x in ay_screen_on ay_deepdoze_enabled ay_deepdoze_delay_seconds ay_deepdoze_active ay_deepdoze_entries; do cat /sys/module/cpu_boost/parameters/$x 2>/dev/null || true; done'
    su -c 'for p in /sys/devices/system/cpu/cpufreq/policy*; do echo "$p"; cat "$p/scaling_min_freq" "$p/scaling_max_freq"; done'

No claim of measured battery savings, instantaneous wake, or DT2W persistence is made until device testing.
