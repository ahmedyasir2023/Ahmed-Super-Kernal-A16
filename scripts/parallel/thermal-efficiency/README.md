# Thermal Efficiency track

**Branch:** `v10-parallel-thermal-efficiency`

## Engineering scope
- Audit thermal zones, cooling devices, CPU/GPU throttling and performance-per-watt behavior.
- Detect whether foreground responsiveness is being lost to thermal oscillation or conflicting limits.
- Coordinate CPU/GPU behavior while retaining all safety limits.

## Current milestone
Adds source contracts and a read-only thermal probe. No trip point, cooling map, thermal service or safety limit is changed in this stage.

## Acceptance gates
1. Thermal trip points and cooling-device limits remain intact.
2. No thermal disable/bypass or forced high-frequency state.
3. Sustained performance and temperature are measured together.
4. Battery and surface-temperature behavior do not regress.


## CI execution
This pull request is configured to run the track validator and the pinned ARM64 source build. No intermediate image is intended for device flashing.
