#!/usr/bin/env python3
"""V7.3: guard missing multi-kswapd task pointer during CPU online.

Vendor code can leave an entry NULL if kthread_run() failed or if the
number of workers is being changed. This branch only prevents dereferencing
a missing pointer in the CPU-online callback; reclaim itself is unmodified.
"""
from pathlib import Path

p = Path(__file__).resolve().parents[2] / "kernel/mm/multi_kswapd/multi_kswapd.c"
s = p.read_text()
anchor = (
    "\t\tif (cpumask_any_and(cpu_online_mask, mask) < nr_cpu_ids)\n"
    "\t\t\tfor (hid = 0; hid < nr_threads; hid++) {\n"
    "\t\t\t\t/* One of our CPUs online: restore mask */\n"
    "\t\t\t\tset_cpus_allowed_ptr(pgdat->kswapd[hid], mask);\n"
    "\t\t\t}"
)
fix = (
    "\t\tif (cpumask_any_and(cpu_online_mask, mask) < nr_cpu_ids)\n"
    "\t\t\tfor (hid = 0; hid < nr_threads; hid++) {\n"
    "\t\t\t\t/* One of our CPUs online: restore mask */\n"
    "\t\t\t\tif (!pgdat->kswapd[hid])\n"
    "\t\t\t\t\tcontinue;\n"
    "\t\t\t\tset_cpus_allowed_ptr(pgdat->kswapd[hid], mask);\n"
    "\t\t\t}"
)
assert s.count(anchor) == 1, "Unexpected multi_kswapd source: fail closed"
assert s.count(fix) == 0, "Already modified"
p.write_text(s.replace(anchor, fix, 1))
print("V7.3: multi-kswapd CPU hotplug NULL guard applied; reclaim unchanged")
