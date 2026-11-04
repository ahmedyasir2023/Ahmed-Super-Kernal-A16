#!/usr/bin/env python3
"""V7.7 invariant and exact A/B predicate truth table."""
from pathlib import Path
import itertools
import subprocess

root=Path(__file__).resolve().parents[2]
kernel=root/"kernel"
s=(kernel/"mm/vmscan.c").read_text()
param=("static bool ay_reclaim_progress;\n"
       "module_param_named(ay_reclaim_progress, ay_reclaim_progress, bool, 0600);")
assert s.count(param)==1,"A/B must default false and be root-only"
assert s.count("MODULE_PARM_DESC(ay_reclaim_progress,")==1
assert 'reclaim_progress_enabled=%d\\n' in s
assert "READ_ONCE(ay_reclaim_progress) ? 1 : 0" in s

start=s.index("static int balance_pgdat(")
end=s.index("static enum zone_type kswapd_classzone_idx(",start)
balance=s[start:end]
expected=("if (try_to_freeze() || kthread_should_stop() ||\n"
          "\t\t    (!READ_ONCE(ay_reclaim_progress) &&\n"
          "\t\t     !atomic_long_read(&kswapd_waiters)))\n"
          "\t\t\tbreak;")
assert balance.count(expected)==1
assert balance.count("pgdat_balanced(pgdat, sc.order, classzone_idx)")==1
for invariant in ("if (raise_priority || !nr_reclaimed)",
                  "pgdat->kswapd_failures++", "psi_memstall_leave(&pflags)"):
    assert invariant in balance,invariant

sleep=s[s.index("static void kswapd_try_to_sleep("):
        s.index("/*\n * The background pageout daemon")]
for invariant in ("schedule_timeout(HZ/10);","prepare_kswapd_sleep(",
                  "if (freezing(current) || kthread_should_stop())",
                  "if (!kthread_should_stop())","schedule();"):
    assert invariant in sleep,invariant

# 2 modes × 3 waiter counts × 2 freeze × 2 stop = 24 combinations.
for mode,waiters,frozen,stopped in itertools.product(
    (False,True),(0,1,3),(False,True),(False,True)
):
    actual=frozen or stopped or (not mode and not bool(waiters))
    vendor=frozen or stopped or not bool(waiters)
    upstream=frozen or stopped
    assert actual==(upstream if mode else vendor)

for n in ("ay_reclaim_balance_calls","ay_reclaim_zero_waiter_calls",
          "ay_reclaim_balanced_exits","ay_reclaim_no_progress",
          "ay_reclaim_wakeups"):
    assert s.count("atomic64_inc(&"+n+");")==1,n
assert 'proc_create("ay_reclaim_status", 0444, NULL,' in s
assert 'static bool ay_reclaim_progress = true' not in s
assert 'static bool ay_reclaim_progress = 1' not in s
assert subprocess.check_output(
    ["git","-C",str(kernel),"diff","--name-only","--","mm/vmscan.c"],
    text=True
).strip()=="mm/vmscan.c"
print("V7.7: default OFF, root-only 0600, 24 A/B states, old idle policy PASS")
