# Memory Engine / Reclaim / ZRAM track

**Branch:** `v10-parallel-memory-engine`

## Engineering scope
- Diagnose memory PSI, direct reclaim, kswapd activity, allocation stalls and ZRAM accounting as one system.
- Review the existing V10.3 conservative reclaim default and V8 watermark cap.
- Examine LMKD interaction and memory pressure under realistic app-switching workloads.
- Avoid increasing swappiness, ZRAM size, reclaim aggressiveness or kswapd count without controlled evidence.

## Current milestone
Adds a source contract for the already staged conservative baseline and a read-only memory probe. The next patch must target a demonstrated stall or accounting defect, not optimize a single counter in isolation.

## Acceptance gates
1. V10.3 bounded reclaim remains opt-in by default.
2. No reclaim loop, extra scan or wake source without a proven bounded condition.
3. ZRAM counters reconcile with block and memory accounting.
4. No OOM increase, memory PSI regression or app-reload regression.
5. Compare the same app workload and observation window before/after.
