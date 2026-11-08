# Power / DeepDoze / Suspend track

**Branch:** `v10-parallel-power-suspend`

## Engineering scope
- Explain the reported screen-off battery loss using PM suspend cycles, wakeup-source deltas, CPUIdle residency, battery current and DeepDoze state.
- Keep the 600-second CLOCK_BOOTTIME deadline and deferrable timer.
- Separate a CPUFreq cap from real system suspend and deep CPU idle.
- Identify wakeup-source ownership before proposing any suppression or policy change.

## Current milestone
This branch adds a reproducible source audit and a read-only on-device probe. It does not yet alter suspend policy. The next implementation change must be driven by the collected evidence and must not introduce a wakelock, alarm, polling loop or new wake source.

## Acceptance gates
1. Existing V9.2 PM notifier and DeepDoze contracts pass.
2. Suspend statistics and wakeup-source accounting remain intact.
3. Screen-on releases the cap immediately; DT2W and fingerprint remain functional.
4. No new wake source or polling loop.
5. Final power claim requires matched screen-off current and charge-loss measurements.


## CI execution
This pull request is configured to run the track validator and the pinned ARM64 source build. No intermediate image is intended for device flashing.
