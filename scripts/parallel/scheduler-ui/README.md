# Scheduler / WALT / UI Latency track

**Branch:** `v10-parallel-scheduler-ui`

## Engineering scope
- Audit schedutil rate limiting, WALT utilization signals, policy-domain updates and boost renewal.
- Reduce avoidable foreground latency without pinning frequencies or bypassing the governor.
- Measure app-launch, touch-to-response and scroll-frame latency with repeatable workloads.
- Keep the downward rate limit and thermal policy intact.

## Current milestone
Adds a source contract for V10.1, V10.2 and V10.4 plus a read-only scheduler probe. Future changes must be bounded, reversible and supported by latency distributions rather than a single best run.

## Acceptance gates
1. Existing UIFirst boost path and down-rate limiting remain unchanged.
2. CPUFreq min/max and thermal ceilings remain authoritative.
3. No busy polling or new high-priority worker.
4. p50/p95/p99 input latency improves without idle power regression.
