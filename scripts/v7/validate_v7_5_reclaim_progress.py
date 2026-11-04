#!/usr/bin/env python3
"""Fail-closed V7.5 source and no-waiter reclaim regression checks."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
kernel = root / "kernel"
s = (kernel / "mm/vmscan.c").read_text()
start = s.index("static int balance_pgdat(")
end = s.index("static enum zone_type kswapd_classzone_idx(", start)
body = s[start:end]

# The only intended behavioural change: no premature reclaim exit when
# the number of waiting allocators drops to zero.
assert "if (try_to_freeze() || kthread_should_stop())" in body
assert "!atomic_long_read(&kswapd_waiters)" not in body
assert "if (pgdat_balanced(pgdat, sc.order, classzone_idx))" in body
assert "if (raise_priority || !nr_reclaimed)" in body
assert "pgdat->kswapd_failures++;" in body
assert "if (kswapd_shrink_node(pgdat, &sc))" in body
assert "psi_memstall_enter(&pflags);" in body
assert "psi_memstall_leave(&pflags);" in body

# No modifications to the standard kswapd wait-for-watermark/freezer path.
sleep = s[s.index("static void kswapd_try_to_sleep("):
          s.index("/*\n * The background pageout daemon")]
assert "prepare_kswapd_sleep(pgdat, reclaim_order, classzone_idx)" in sleep
assert "schedule_timeout(HZ/10);" in sleep
assert "if (!kthread_should_stop())" in sleep
assert "schedule();" in sleep
assert "if (freezing(current) || kthread_should_stop())" in sleep

# Do not touch the vendor's separate allocator waiter accounting.
assert "atomic_long_inc(&kswapd_waiters);" in s
assert "atomic_long_dec(&kswapd_waiters);" in s
assert "if (unlikely(!using_kswapd && !wmark_ok))" in s

# State model: when zone remains unbalanced, zero current waiters must not
# short-circuit the reclaim cycle. Freeze and stop must still exit.
for waiters in (0, 1, 3):
    for balanced in (False, True):
        for frozen in (False, True):
            for stopped in (False, True):
                old_exit = frozen or stopped or not waiters
                fixed_exit = frozen or stopped
                if not balanced and not frozen and not stopped:
                    assert not fixed_exit
                    if waiters == 0:
                        assert old_exit
                if frozen or stopped:
                    assert fixed_exit

# Single source hunk with precisely the expected branch change.
diff = subprocess.check_output(
    ["git", "-C", str(kernel), "diff", "--", "mm/vmscan.c"],
    text=True
)
assert diff.count("@@") == 2, "Unexpected number of vmscan hunks"
assert diff.count("-\t\t    !atomic_long_read(&kswapd_waiters))") == 1
assert diff.count("+\t\tif (try_to_freeze() || kthread_should_stop())") == 1
assert subprocess.check_output(
    ["git", "-C", str(kernel), "diff", "--name-only", "--", "mm/vmscan.c"],
    text=True
).strip() == "mm/vmscan.c"

print("V7.5 reclaim watermark progress; zero-waiter/freezer/stop regression: PASS")
