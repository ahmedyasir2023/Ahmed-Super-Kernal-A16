# GPU / KGSL / Display track

**Branch:** `v10-parallel-gpu-display`

## Engineering scope
- Audit KGSL power levels, devfreq transitions, GPU idle residency and DRM/display interactions.
- Improve frame pacing and GPU response without pinning maximum clocks.
- Distinguish CPU-bound, GPU-bound and display-pipeline stalls.
- Preserve vendor KGSL, panel timing and original device tree.

## Current milestone
Adds source checks and a read-only GPU/display probe. Any tuning must be thermal-aware and must not write directly to GPU frequency limits.

## Acceptance gates
1. No GPU or display instability, flicker or resume regression.
2. No thermal limit bypass or permanent frequency pin.
3. Frame-time p95/p99 improves under the same workload.
4. Screen-off GPU residency returns to idle and does not increase drain.
