#!/usr/bin/env python3
"""V7.6: read-only event counters for Realme 4.14 kswapd reclaim.

The counters help distinguish repeated wakeups, zero-waiter balance passes
and complete reclaim failure. No timers, write controls, daemons, CPU or
screen-off policy changes. Built only where CONFIG_PROC_FS is present.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/"kernel/mm/vmscan.c"
s=p.read_text()
def change(old,new,label):
    global s
    assert s.count(old)==1,"Unexpected vmscan source at "+label
    s=s.replace(old,new,1)
change("#include <linux/psi.h>\n",
       "#include <linux/psi.h>\n#include <linux/proc_fs.h>\n#include <linux/seq_file.h>\n#include <linux/atomic.h>\n",
       "kernel headers")
new_block=r'''
#ifdef CONFIG_PROC_FS
/* V7.6: event-only telemetry; none of these counters trigger work. */
static atomic64_t ay_reclaim_balance_calls = ATOMIC64_INIT(0);
static atomic64_t ay_reclaim_zero_waiter_calls = ATOMIC64_INIT(0);
static atomic64_t ay_reclaim_balanced_exits = ATOMIC64_INIT(0);
static atomic64_t ay_reclaim_no_progress = ATOMIC64_INIT(0);
static atomic64_t ay_reclaim_wakeups = ATOMIC64_INIT(0);

static int ay_reclaim_status_show(struct seq_file *m, void *v)
{
    seq_printf(m, "balance_calls=%lld\n",
               (long long)atomic64_read(&ay_reclaim_balance_calls));
    seq_printf(m, "balance_zero_waiters=%lld\n",
               (long long)atomic64_read(&ay_reclaim_zero_waiter_calls));
    seq_printf(m, "balanced_exits=%lld\n",
               (long long)atomic64_read(&ay_reclaim_balanced_exits));
    seq_printf(m, "zero_progress_cycles=%lld\n",
               (long long)atomic64_read(&ay_reclaim_no_progress));
    seq_printf(m, "wakeup_requests=%lld\n",
               (long long)atomic64_read(&ay_reclaim_wakeups));
    return 0;
}

static int ay_reclaim_status_open(struct inode *inode, struct file *file)
{
    return single_open(file, ay_reclaim_status_show, NULL);
}

static const struct file_operations ay_reclaim_status_fops = {
    .owner = THIS_MODULE,
    .open = ay_reclaim_status_open,
    .read = seq_read,
    .llseek = seq_lseek,
    .release = single_release,
};
#endif /* CONFIG_PROC_FS */

'''
change("static int balance_pgdat(pg_data_t *pgdat, int order, int classzone_idx)\n",
       new_block+"static int balance_pgdat(pg_data_t *pgdat, int order, int classzone_idx)\n",
       "read-only proc helpers")
change("\tpsi_memstall_enter(&pflags);\n\tcount_vm_event(PAGEOUTRUN);\n",
       "\tpsi_memstall_enter(&pflags);\n\tcount_vm_event(PAGEOUTRUN);\n"
       "#ifdef CONFIG_PROC_FS\n"
       "\tatomic64_inc(&ay_reclaim_balance_calls);\n"
       "\tif (!atomic_long_read(&kswapd_waiters))\n"
       "\t\tatomic64_inc(&ay_reclaim_zero_waiter_calls);\n"
       "#endif\n",
       "balance entry counters")
change("\t\tif (pgdat_balanced(pgdat, sc.order, classzone_idx))\n\t\t\tgoto out;\n",
       "\t\tif (pgdat_balanced(pgdat, sc.order, classzone_idx)) {\n"
       "#ifdef CONFIG_PROC_FS\n"
       "\t\t\tatomic64_inc(&ay_reclaim_balanced_exits);\n"
       "#endif\n"
       "\t\t\tgoto out;\n"
       "\t\t}\n",
       "balanced exit")
change("\tif (!sc.nr_reclaimed)\n\t\tpgdat->kswapd_failures++;\n",
       "\tif (!sc.nr_reclaimed) {\n"
       "\t\tpgdat->kswapd_failures++;\n"
       "#ifdef CONFIG_PROC_FS\n"
       "\t\tatomic64_inc(&ay_reclaim_no_progress);\n"
       "#endif\n"
       "\t}\n",
       "zero-progress cycle")
change("\ttrace_mm_vmscan_wakeup_kswapd(pgdat->node_id, classzone_idx, order);\n"
       "\twake_up_interruptible(&pgdat->kswapd_wait);\n",
       "\ttrace_mm_vmscan_wakeup_kswapd(pgdat->node_id, classzone_idx, order);\n"
       "#ifdef CONFIG_PROC_FS\n"
       "\tatomic64_inc(&ay_reclaim_wakeups);\n"
       "#endif\n"
       "\twake_up_interruptible(&pgdat->kswapd_wait);\n",
       "wakeups counter")
change("\tWARN_ON(ret < 0);\n\treturn 0;\n}\n\nmodule_init(kswapd_init)\n",
       "\tWARN_ON(ret < 0);\n"
       "#ifdef CONFIG_PROC_FS\n"
       "\tif (!proc_create(\"ay_reclaim_status\", 0444, NULL,\n"
       "\t                 &ay_reclaim_status_fops))\n"
       "\t\tpr_warn(\"AY reclaim read-only diagnostics unavailable\\n\");\n"
       "#endif\n"
       "\treturn 0;\n}\n\nmodule_init(kswapd_init)\n",
       "proc registration")
p.write_text(s)
print("V7.6: event-only /proc/ay_reclaim_status counters injected")
