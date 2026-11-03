#!/usr/bin/env python3
"""Enable a minimal, root-only SUSFS v1.5.5 read-only PRCTL ABI probe.

Experimental CI ONLY: VERSION and ENABLED_FEATURES reports. No mount/path
hiding, no modifications to SUSFS state, no flashable boot artifacts.
This is intentionally NOT a full SUSFS bridge.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys_file = root / "kernel/kernel/sys.c"
def_file = root / "kernel/include/linux/susfs_def.h"
h_file = root / "kernel/include/linux/susfs.h"
uapi_file = root / "KernelSU-Next/uapi/supercall.h"

s = sys_file.read_text()
defs = def_file.read_text()
header = h_file.read_text()
api = uapi_file.read_text()
assert "#define KERNEL_SU_UAPI_VERSION 6" in api
assert '#define SUSFS_VERSION "v1.5.5"' in header
assert "#define CMD_SUSFS_SHOW_VERSION 0x555e1" in defs
assert "#define CMD_SUSFS_SHOW_ENABLED_FEATURES 0x555e2" in defs

includes = "#include <linux/prctl.h>\n"
assert s.count(includes) == 1
s = s.replace(includes, includes + """#ifdef CONFIG_KSU_SUSFS
#include <linux/susfs.h>
#include <linux/susfs_def.h>
#endif

""", 1)

entry = """\tlong error;

\terror = security_task_prctl(option, arg2, arg3, arg4, arg5);"""
assert s.count(entry) == 1

# The v1.5.5 user-space ksu_susfs compatibility tool uses prctl magic
# 0xDEADBEEF; arg2=command, arg3=data, arg5=int result. Root-only and
# const/read-only, so it cannot affect other APIs or hide anything.
probe = """\tlong error;

#ifdef CONFIG_KSU_SUSFS
\tif ((unsigned int)option == 0xDEADBEEF &&
\t    (arg2 == CMD_SUSFS_SHOW_VERSION ||
\t     arg2 == CMD_SUSFS_SHOW_ENABLED_FEATURES)) {
\t\tint result = 0;

\t\tif (current_uid().val != 0)
\t\t\treturn -EPERM;
\t\tif (!arg3 || !arg5)
\t\t\treturn -EFAULT;

\t\tif (arg2 == CMD_SUSFS_SHOW_VERSION) {
\t\t\tif (copy_to_user((void __user *)arg3, SUSFS_VERSION,
\t\t\t\t\t sizeof(SUSFS_VERSION)))
\t\t\t\tresult = -EFAULT;
\t\t} else {
\t\t\t/* No real SUSFS features implemented yet. */
\t\t\tu64 enabled_features = 0;

\t\t\tif (copy_to_user((void __user *)arg3,
\t\t\t\t\t &enabled_features,
\t\t\t\t\t sizeof(enabled_features)))
\t\t\t\tresult = -EFAULT;
\t\t}
\t\tif (put_user(result, (int __user *)arg5))
\t\t\treturn -EFAULT;
\t\treturn result;
\t}
#endif

\terror = security_task_prctl(option, arg2, arg3, arg4, arg5);"""
s = s.replace(entry, probe, 1)
sys_file.write_text(s)
print("API6 SUSFS 1.5.5 read-only PRCTL metadata probe: VERSION and FEATURES=0")
print("Not a SUSFS hiding implementation; all other SUSFS commands unsupported")
