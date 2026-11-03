# Ahmed Super Kernal A16 V6: HyperSpeed screen-aware response

Target **Realme 7 Pro RMX2170**, Linux **4.14.336**, Evolution X **Android 16**. This is an incremental **non-flashable source experiment** based on the V5 build the user installed and verified through its exact Boot SHA-256.

## Observations on the device

Root and kernel V5 were verified by live BOOT SHA-256 `a3631c6ec79f8c6df9037081ac01804fcde8828d7aa8f871bc9a7bef6af00339` with KernelSU Next Legacy API 6 Root (`uid=0`), DT2W proc state `1`, and SELinux Enforcing. The runtime CPU governor on both `policy0` and `policy6` is `schedutil`. Input-boost runtime values previously observed were 60%, 80 ms, and scheduler boost type 2; neither `service.sh` nor `post-fs-data.sh` in the scanned modules had a matching parameter override. The Android Power HAL and other boot services were **not** ruled out.

## V6 source changes (not validated on the physical phone yet)

In the existing vendor `cpu-boost.c` driver, **only**:
- Adaptive input response: default `ay_input_boost_pct=72`; runtime bounded to 78% of the **current allowed** CPUFreq policy span, not maximum hardware clocks.
- Input boost duration: default `input_boost_ms=105` milliseconds, hard-clamped at 140 ms. Existing 150-ms event debounce remains.
- Display-off state: `ay_screen_on` read-only status, `ay_screenoff_saver=Y`, receiving native DRM `MSM_DRM_EARLY_EVENT_BLANK` / `MSM_DRM_EVENT_BLANK` notifications for the primary display; use FB notifier fallback where DRM is absent.
- On display powerdown: suppress additional input CPU boosts, invalidate pending wake requests, expedite the existing boost-release worker; `schedutil` can then select the natural low-idle frequency without the accelerator keeping minimum clocks high.
- On display unblank: optional `ay_instantwake=Y` applies one boost at default 82% of the allowed frequency span, max 85%, for 155 ms, max 180 ms. No permanent high clocks.
- Preserve WALT boost-type 3 default unless overridden by user space; preserve all existing thermal protections, CPUFreq policy maximums, Root hooks, SUSFS Path/Logging/Uname, and DT2W driver changes.

**Do not claim** that "display-off CPU instantly becomes the absolute minimum" or "app launches are now lightning fast": clock selection still depends on system load, cgroup/PowerHAL votes, thermal limits, hardware wakeup sources, RAM pressure, and app storage. DT2W must remain functional during suspend. A busy job, incoming call or alarm may legitimately use higher frequencies with screen off.

The new module parameters should eventually be available under `/sys/module/cpu_boost/parameters/` if the V6 kernel boots and the kernel config enables CPUBoost:

| Parameter | Compiled V6 default |
|---|---|
| ay_auto_input_boost | Y |
| ay_input_boost_pct | 72 |
| input_boost_ms | 105 |
| sched_boost_on_input | 3 |
| ay_screen_on | Y (read-only; tracks display) |
| ay_screenoff_saver | Y |
| ay_instantwake | Y |
| ay_wake_boost_pct | 82 |
| ay_wake_boost_ms | 155 |

Settings may change at runtime through user space. No module or init scripts are required to **enable** the compiled V6 mechanisms.

## Gate to release

1. GitHub CI verifies syntax, V5 source compatibility, V6 static assertions, full Clang 21 ARM64 compilation, KSU API6/SUSFS symbols and unchanged 7 original DTBs.
2. Preserve the **currently installed V5 Boot** as a fresh backup, not the original V2 Boot; its exact image must be read from the device and verified by SHA-256 before any V6 repack. Do not silently repackage V6 from old V2 Ramdisk/AVB without checking the currently installed image.
3. Repack only for a separately approved controlled device test; calculate Boot ID and AVB descriptor and independently verify integrity. Do **not** provide a bootable ZIP based solely on successful CI.
4. After a V6 device boot, verify KernelSU Root, SELinux Enforcing, fingerprint, wireless/cellular, charging, camera, DT2W after reboot and screen-off periods.
5. On-device measurements required: cold/warm launches (10+ repetitions), CPU frequency and core load after display blank and first wake, idle power draw for 30-60 min and overnight, screen-on responsiveness, thermal and game frame-time stability.
6. Test `ay_screenoff_saver=Y` with screen-off notifications and alarms; no permanent frequency cap, watchdog polling, thermal bypass, blanket SELinux changes or artificial wake-lock loops.

**This document describes experimental source changes, not demonstrated battery or speed results.**
