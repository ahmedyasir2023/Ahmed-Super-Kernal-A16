# Input / Touch / Wake / Fingerprint track

**Branch:** `v10-parallel-input-touch`

## Engineering scope
- Audit touch event delivery, double-tap gesture wake, DRM blank/unblank ordering and wake boost.
- Preserve the existing touch controller and vendor fingerprint integration.
- Find avoidable wake latency and race conditions without changing the sensor firmware or DTB.
- Treat fingerprint and DT2W as release-blocking invariants.

## Current milestone
Adds source regression checks and a read-only device probe. Any subsequent code change must be isolated to the smallest verified event path and must include wake/reblank race tests.

## Acceptance gates
1. Fingerprint unlock succeeds repeatedly after screen-off and deep idle.
2. DT2W wakes reliably after short and long screen-off intervals.
3. No missed first touch after resume.
4. No stuck input boost or stale DeepDoze cap.
5. No additional periodic work or wake lock.


## CI execution
This pull request is configured to run the track validator and the pinned ARM64 source build. No intermediate image is intended for device flashing.
