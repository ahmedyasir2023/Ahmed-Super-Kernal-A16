#!/usr/bin/env python3
"""V3 API-6 lab: SUSFS 1.5.5 metadata and logging-only userspace bridge.

Actual supported commands: SHOW_VERSION, SHOW_VARIANT, SHOW_ENABLED_FEATURES,
ENABLE_LOG. All commands require UID 0. This intentionally does NOT enable
or report any hiding features, and produces no boot image / flashable ZIP.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys_file = root / "kernel/kernel/sys.c"
def_file = root / "kernel/include/linux/susfs_def.h"
h_file = root / "kernel/include/linux/susfs.h"
uapi_file = root / "KernelSU-Next/uapi/supercall.h"
cfg = root / "KernelSU-Next/kernel/Kconfig"

source = sys_file.read_text()
defs = def_file.read_text()
header = h_file.read_text()
api = uapi_file.read_text()
kconfig = cfg.read_text()

assert '#define KERNEL_SU_UAPI_VERSION 6' in api
assert '#define SUSFS_VERSION "v1.5.5"' in header
assert '#define SUSFS_VARIANT "NON-GKI"' in header
for name, number in {
    "CMD_SUSFS_SHOW_VERSION": "0x555e1",
    "CMD_SUSFS_SHOW_ENABLED_FEATURES": "0x555e2",
    "CMD_SUSFS_SHOW_VARIANT": "0x555e3",
    "CMD_SUSFS_ENABLE_LOG": "0x555a0",
}.items():
    assert f"#define {name} {number}" in defs, name
assert "config KSU_SUSFS\\n" in kconfig
assert "config KSU_SUSFS_ENABLE_LOG\\n" not in kconfig
cfg.write_text(kconfig + """
config KSU_SUSFS_ENABLE_LOG
    bool "SUSFS logging ABI experiment (not root hiding)"
    depends on KSU_SUSFS
    default n
    help
      Only the root-gated SUSFS logging toggle is added alongside
      read-only metadata calls. No SUSFS hiding features are activated.
""")

includes = "#include <linux/prctl.h>\\n"
assert source.count(includes) == 1
source = source.replace(includes, includes + """#ifdef CONFIG_KSU_SUSFS
#include <linux/susfs.h>
#include <linux/susfs_def.h>
#endif

""", 1)

anchor = """\\tlong error;

\\terror = security_task_prctl(option, arg2, arg3, arg4, arg5);"""
assert source.count(anchor) == 1, "Unexpected Realme 4.14 prctl source"
bridge = """\\tlong error;

#ifdef CONFIG_KSU_SUSFS
    /*
     * SUSFS v1.5.5 userspace legacy PRCTL ABI (NOT KernelSU root API).
     * Root-only, precisely enumerated command values. Hiding is disabled.
     */
    if ((unsigned int)option == 0xDEADBEEF &&
        (arg2 == CMD_SUSFS_SHOW_VERSION ||
         arg2 == CMD_SUSFS_SHOW_VARIANT ||
         arg2 == CMD_SUSFS_SHOW_ENABLED_FEATURES ||
         arg2 == CMD_SUSFS_ENABLE_LOG)) {
        int result = 0;

        if (current_uid().val != 0)
            return -EPERM;
        if (!arg5)
            return -EFAULT;

        switch (arg2) {
        case CMD_SUSFS_SHOW_VERSION:
            if (!arg3 || copy_to_user((void __user *)arg3,
                                      SUSFS_VERSION, sizeof(SUSFS_VERSION)))
                result = -EFAULT;
            break;

        case CMD_SUSFS_SHOW_VARIANT:
            if (!arg3 || copy_to_user((void __user *)arg3,
                                      SUSFS_VARIANT, sizeof(SUSFS_VARIANT)))
                result = -EFAULT;
            break;

        case CMD_SUSFS_SHOW_ENABLED_FEATURES: {
            /* bit 9 is the one and only supported SUSFS feature here. */
            u64 enabled_features = 1ULL << 9;

            if (!arg3 || copy_to_user((void __user *)arg3,
                                      &enabled_features,
                                      sizeof(enabled_features)))
                result = -EFAULT;
            break;
        }

        case CMD_SUSFS_ENABLE_LOG:
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
            if (arg3 > 1)
                result = -EINVAL;
            else
                susfs_set_log(arg3 != 0);
#else
            result = -EOPNOTSUPP;
#endif
            break;
        }

        if (put_user(result, (int __user *)arg5))
            return -EFAULT;
        return result;
    }
#endif

\\terror = security_task_prctl(option, arg2, arg3, arg4, arg5);"""

source = source.replace(anchor, bridge, 1)
sys_file.write_text(source)
print("SUSFS v1.5.5: API6 root-gated version/variant/features and functional logging control staged")
print("Features mask=0x200 (logging only); no path, mount, kstat, uname or open redirect enabled")
