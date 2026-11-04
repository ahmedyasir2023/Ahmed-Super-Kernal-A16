#!/usr/bin/env python3
"""V7.3: fail closed on source-level multi-kswapd callback guard."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
target = "mm/multi_kswapd/multi_kswapd.c"
s = (root / "kernel" / target).read_text()
body = s[s.index("#if(LINUX_VERSION_CODE >= KERNEL_VERSION(4,14,0))"):
         s.index("#else", s.index("#if(LINUX_VERSION_CODE >= KERNEL_VERSION(4,14,0))"))]
guard = (
    "if (!pgdat->kswapd[hid])\n"
    "\t\t\t\t\tcontinue;\n"
    "\t\t\t\tset_cpus_allowed_ptr(pgdat->kswapd[hid], mask);"
)
assert body.count(guard) == 1, "Expected one NULL guard in arm64 CPU online path"
assert "int kswapd_run_ext(int nid)" in s
assert "update_kswapd_threads_node" in s
assert "kthread_run(kswapd, pgdat" in s
diff = subprocess.check_output(["git", "-C", str(root / "kernel"), "diff", "--numstat", "--", target], text=True)
parts = diff.strip().split("\t")
assert len(parts) == 3 and parts[0] == "2" and parts[1] == "0", f"Unexpected patch size: {diff!r}"
print("V7.3 multi-kswapd two-line NULL guard (not algorithm tuning): PASS")
