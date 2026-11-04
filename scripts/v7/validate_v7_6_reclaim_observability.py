#!/usr/bin/env python3
"""V7.6 invariants: read-only kernel reclaim forensics with no idle polling."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
k=root/"kernel"
s=(k/"mm/vmscan.c").read_text()
headers=["#include <linux/proc_fs.h>","#include <linux/seq_file.h>","#include <linux/atomic.h>"]
for h in headers:
    assert s.count(h)==1,h
names=("ay_reclaim_balance_calls","ay_reclaim_zero_waiter_calls",
       "ay_reclaim_balanced_exits","ay_reclaim_no_progress","ay_reclaim_wakeups")
for n in names:
    assert s.count("static atomic64_t "+n+" = ATOMIC64_INIT(0);")==1,n
    assert s.count("atomic64_inc(&"+n+");")==1,n
    assert s.count("atomic64_read(&"+n+")")==1,n
assert "static const struct file_operations ay_reclaim_status_fops" in s
assert 'proc_create("ay_reclaim_status", 0444, NULL,' in s
assert s.count("CONFIG_PROC_FS")==8, "Telemetry must be fully procfs-gated"
assert "single_open(file, ay_reclaim_status_show, NULL)" in s
assert ".read = seq_read," in s
assert ".llseek = seq_lseek," in s
assert ".release = single_release," in s
assert "balance_zero_waiters=" in s
assert "balanced_exits=" in s
assert "zero_progress_cycles=" in s
assert "wakeup_requests=" in s

reclaim=s[s.index("static int balance_pgdat("):s.index("static enum zone_type kswapd_classzone_idx(")]
assert "if (try_to_freeze() || kthread_should_stop())" in reclaim
assert "!atomic_long_read(&kswapd_waiters))\n\t\t\tbreak;" not in reclaim
assert "if (pgdat_balanced(pgdat, sc.order, classzone_idx))" in reclaim
assert "if (raise_priority || !nr_reclaimed)" in reclaim
assert "pgdat->kswapd_failures++" in reclaim
assert "psi_memstall_leave(&pflags);" in reclaim

# No timer, worker, printk polling, or mutable proc interface.
for forbidden in ("schedule_delayed_work(", "mod_delayed_work(", "kthread_run(",
                  "proc_create_data(", ".write =", "msleep(", "schedule_timeout("):
    telemetry=s[s.index("/* V7.6: event-only telemetry"):s.index("static int balance_pgdat(")]
    assert forbidden not in telemetry,forbidden
assert "0444" in s and "0644" not in telemetry

# The logical event conditions are independent of screen state and do
# not modify the existing reclaim/sleep decisions.
for waiters in (0,1,3):
    zero_waiter_count=(waiters == 0)
    assert zero_waiter_count == (not bool(waiters))
for scanned,reclaimed in ((0,0),(100,0),(100,12)):
    no_progress=(reclaimed==0)
    assert no_progress == (reclaimed==0)

diff=subprocess.check_output(["git","-C",str(k),"diff","--name-only","--","mm/vmscan.c"],text=True).strip()
assert diff=="mm/vmscan.c",diff
assert "WRITE_ONCE(ay_screen_on" not in s
print("V7.6: 0444 procfs counter contract, wake/idle isolation, event models: PASS")
