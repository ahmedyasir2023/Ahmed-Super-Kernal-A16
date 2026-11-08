# Storage / Block I/O / F2FS track

**Branch:** `v10-parallel-storage-io`

## Engineering scope
- Audit block request dispatch, queue policy, F2FS writeback/GC and fsync behavior.
- Identify storage stalls that appear as app-launch or UI latency.
- Check interaction with ZRAM and background writeback.
- Preserve filesystem integrity and the ROM's existing mount policy.

## Current milestone
Adds source checks and a read-only storage probe. No queue scheduler or F2FS tunable is changed until the device's actual block topology and I/O latency distribution are known.

## Acceptance gates
1. No data-integrity or fsck regression.
2. No increase in write amplification or idle write activity.
3. p95/p99 random-read and fsync latency improve or remain neutral.
4. No change to partition layout, encryption or mount flags.
