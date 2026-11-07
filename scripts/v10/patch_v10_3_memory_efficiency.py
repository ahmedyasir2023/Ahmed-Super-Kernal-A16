#!/usr/bin/env python3
"""V10.3: make the experimental V9.1 background reclaim follow-up opt-in.

The V9.1 extra pass is bounded, but it can still spend CPU reclaiming after
allocator waiters have disappeared. Existing RMX2170 measurements did not
isolate a repeatable latency or battery benefit from enabling it. V10.3
therefore restores the vendor waiter-zero exit by default while preserving
the exact guarded extra-pass code behind its root-only runtime switch.

This changes one default and its description only. It does not change the
reclaim algorithm, watermarks, swappiness, ZRAM, kswapd count, CPUFreq,
touch, DeepDoze, thermal policy, or userspace services.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = root / "kernel/mm/vmscan.c"
s = source.read_text()

old_default = "static bool ay_v91_bounded_reclaim = true;"
new_default = "static bool ay_v91_bounded_reclaim = false;"
old_desc = (
    'MODULE_PARM_DESC(ay_v91_bounded_reclaim,\n'
    '                 "1: max one post-progress pass per kswapd cycle and per second");'
)
new_desc = (
    'MODULE_PARM_DESC(ay_v91_bounded_reclaim,\n'
    '                 "0: vendor waiter exit (default), 1: opt-in bounded extra pass");'
)

assert s.count(old_default) == 1, "Expected exactly one V9.1 default"
assert s.count(old_desc) == 1, "Expected exactly one V9.1 parameter description"
assert s.count(new_default) == 0, "V10.3 already applied"
s = s.replace(old_default, new_default, 1)
s = s.replace(old_desc, new_desc, 1)

# The rollback/opt-in mechanism and its bounded safety guards must remain.
for token in (
    "module_param_named(ay_v91_bounded_reclaim, ay_v91_bounded_reclaim, bool, 0600);",
    "READ_ONCE(ay_v91_bounded_reclaim)",
    "!ay_v91_extra_this_cycle",
    "sc.nr_reclaimed > nr_reclaimed",
    "!pgdat_balanced(pgdat, sc.order, classzone_idx)",
    "msecs_to_jiffies(1000)",
    "try_to_freeze() || kthread_should_stop()",
):
    assert token in s, token

assert s.count("static bool ay_v91_bounded_reclaim = false;") == 1
source.write_text(s)
print("V10.3: V9.1 extra background reclaim is OFF by default.")
print("V10.3: root-only ay_v91_bounded_reclaim=1 retains the bounded experiment.")
print("V10.3: vendor waiter-zero exit, reclaim guards and all other memory/power defaults retained.")
