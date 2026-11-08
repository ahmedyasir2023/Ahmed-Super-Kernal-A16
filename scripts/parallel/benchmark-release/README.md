# Benchmark / Integration / Release track

**Branch:** `v10-parallel-benchmark-release`

## Engineering scope
- Define reproducible foreground, memory, thermal, storage and screen-off power measurements.
- Verify pinned source/toolchain/KSU/SUSFS inputs, DTB compatibility, image integrity and artifact hashes.
- Build the final combined candidate once all other tracks pass.
- Keep outputs non-flashable until the exact device boot/AVB and installer inputs are audited.

## Current milestone
Adds release source contracts and a consolidated read-only device baseline script. It does not create or label a flashable ZIP.

## Acceptance gates
1. All nine engineering tracks are present and pass in integration order.
2. Full ARM64 build and all legacy validators pass.
3. Image and configuration hashes are recorded.
4. Boot, root, SUSFS, fingerprint, DT2W, connectivity, thermal and power gates are checked on the integrated candidate.
5. No final release claim until device validation succeeds.


## CI execution
This pull request is configured to run the track validator and the pinned ARM64 source build. No intermediate image is intended for device flashing.
