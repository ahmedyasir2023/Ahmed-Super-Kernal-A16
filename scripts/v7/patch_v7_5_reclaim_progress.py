#!/usr/bin/env python3
"""V7.5: remove vendor-added kswapd waiter-zero early exit.

This restores the upstream Linux 4.14 balance_pgdat stop condition:
kswapd must reclaim until zones rebalance or priority is exhausted,
regardless of whether any direct allocator is currently waiting.
"""
from pathlib import Path
p = Path(__file__).resolve().parents[2] / "kernel/mm/vmscan.c"
s = p.read_text()
old = (
    "\t\t/* Check if kswapd should be suspending */\n"
    "\t\tif (try_to_freeze() || kthread_should_stop() ||\n"
    "\t\t    !atomic_long_read(&kswapd_waiters))\n"
    "\t\t\tbreak;\n"
)
new = (
    "\t\t/* Keep reclaiming until balanced, frozen, stopped or exhausted.\n"
    "\t\t * Allocator waiter count alone does not establish watermarks.\n"
    "\t\t */\n"
    "\t\tif (try_to_freeze() || kthread_should_stop())\n"
    "\t\t\tbreak;\n"
)
assert s.count(old) == 1, "Unexpected Realme balance_pgdat source"
s = s.replace(old, new, 1)
p.write_text(s)
print("V7.5: removed waiter-zero early exit; preserved freeze/stop checks")
