# V5 AY HyperSpeed — automatic responsive input boost (experimental)

Target: Realme 7 Pro RMX2170 / Evolution X Android 16 / Linux 4.14.336.
Base: V4 SUSFS Path + KernelSU Next API 6 + Always-On DT2W, build [41680846239](https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/41680846239) (SUCCESS).

## Why this is a real kernel change

The pinned Realme vendor source has `CONFIG_CPU_BOOST=y` and an input handler in `drivers/cpufreq/cpu-boost.c`, but its input boost frequencies default to zero and the handler exits unless frequencies were explicitly configured. Therefore input boosting is not automatically active by default. The V5 patch enables bounded automatic input boosting in the **kernel driver**, independent of a KernelSU module, Android init service or manual commands after reboot.

This branch stages the original V4 SUSFS + DT2W modifications, then patches **only** `drivers/cpufreq/cpu-boost.c` to:

| Property | V5 setting |
|---|---|
| Adaptive input boost | Enabled by default; `ay_auto_input_boost=1` |
| Minimum CPU frequency during an input window | 60% along each currently allowed cpufreq policy range (`cpuinfo.min_freq` to `policy->max`) |
| Runtime max allowed boost percentage | Capped at 75% of the policy range |
| Time from last accepted touch/key to boost expiry | Default 90 ms; clamp at 120 ms |
| Minimum interval between accepted input boost requests | Existing vendor debounce 150 ms |
| WALT/scheduler input boost | Vendor restrained boost type 3; released when the timer expires |
| Manual override | Existing per-CPU `input_boost_freq` takes priority; setting `ay_auto_input_boost=0` restores original default-off behavior if no override exists |
| Screen off | No continuous CPU boost; requests only after input events |
| Governor, thermal limits, SELinux | Unchanged; never force performance governor |
| DT2W, SUSFS, KernelSU API 6 | V4 source inherited unchanged |

The CPUFreq driver itself enforces allowed frequencies; no overclock or thermal bypass is implemented. These are **design settings**, not measured performance gains. An actual user-level `input_boost_freq` or vendor power HAL setting may override automatic boost behavior.

## Build and tests

`scripts/v5/patch_ay_input_boost.py` refuses to modify unrecognized vendor source. `scripts/v5/validate_ay_input_boost.py` verifies the root API and DT2W setting are still present, checks the bounded input-timer math and confirms the stock CPUFreq policy update and scheduler boost-release paths remain intact.

The V5 CI must compile the complete ARM64 kernel under pinned Android Clang 21, retain seven unmodified ROM-compatible DTBs, verify the original WALT/CPUFreq configuration and emit **nonflashable diagnostic artifacts only**.

## Device benchmarks necessary before a release

After a recoverable V5 boot is assembled and independently checked in a future step:

1. Compare at least 10 cold/warm Android Settings and real app launches at similar temperatures, starting from V2/V4 baseline.
2. Compare touch-to-display responsiveness, scrolling smoothness, thermal readings, and battery drain over fixed workloads.
3. Check game frame times and if V5 increases thermal throttling.
4. Validate Root (`su -c id`), SELinux Enforcing, networking, fingerprint, camera, charging, reboot-persistent DT2W, screen-off suspend and overnight drain.
5. Only then experiment separately with ZRAM, app retention, I/O, gaming boosts or SmartSleep; do not combine unmeasured optimizations.

**Release status: experimental. The working V2 Boot on the phone is unchanged. No V5 Boot image or OrangeFox ZIP was created by this branch.**
