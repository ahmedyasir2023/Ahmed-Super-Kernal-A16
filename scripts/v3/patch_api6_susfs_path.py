#!/usr/bin/env python3
"""SUSFS 1.5.5 path hiding: isolated API6 compile probe (NOT FLASHABLE).

Requires the prior app-state tracking feature, so only unprivileged zygote
children are subject to the existing SUSFS 4.14 VFS guards. Root-only
userspace adds hidden path entries through the upstream 0xDEADBEEF PRCTL ABI.
This step does not enable mount hiding, kstat spoofing, symlink rewriting,
SELinux bypasses, hidden kernel symbols or other SUSFS operations.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
config_path = root / "KernelSU-Next/kernel/Kconfig"
sys_path = root / "kernel/kernel/sys.c"
hook_path = root / "KernelSU-Next/kernel/hook/setuid_hook.c"
susfs_path = root / "kernel/fs/susfs.c"
susfs_h = root / "kernel/include/linux/susfs.h"
defs_h = root / "kernel/include/linux/susfs_def.h"
uapi_h = root / "KernelSU-Next/uapi/supercall.h"

config = config_path.read_text()
sysc = sys_path.read_text()
hook = hook_path.read_text()
susfs = susfs_path.read_text()
hdr = susfs_h.read_text()
defs = defs_h.read_text()

assert "#define KERNEL_SU_UAPI_VERSION 6" in uapi_h.read_text()
assert "config KSU_SUSFS_PROC_TRACK\n" in config
assert "config KSU_SUSFS_SUS_PATH\n" not in config
assert "current->susfs_task_state |= TASK_STRUCT_NON_ROOT_USER_APP_PROC;" in hook
assert "if (!is_zygote(current_cred()))" in hook
assert "int susfs_add_sus_path(struct st_susfs_sus_path*" in susfs
assert "struct st_susfs_sus_path {" in hdr
assert "#define CMD_SUSFS_ADD_SUS_PATH 0x55550" in defs
assert "CMD_SUSFS_ADD_SUS_PATH" not in sysc

config += """
config KSU_SUSFS_SUS_PATH
    bool "SUSFS path visibility (API6 isolated CI experiment)"
    depends on KSU_SUSFS && KSU_SUSFS_PROC_TRACK
    default n
    help
      Enable SUSFS v1.5.5's original VFS path checks only for tracked
      unprivileged zygote child tasks. This is an experimental compile
      probe and is not approved for deployment or flashable builds.
"""
config_path.write_text(config)

allowed = "         arg2 == CMD_SUSFS_SET_UNAME)) {"
replacement = "         arg2 == CMD_SUSFS_SET_UNAME ||\n         arg2 == CMD_SUSFS_ADD_SUS_PATH)) {"
assert sysc.count(allowed) == 1, "Unexpected SUSFS PRCTL command dispatcher"
sysc = sysc.replace(allowed, replacement, 1)

case_anchor = """        case CMD_SUSFS_SET_UNAME: {"""
assert sysc.count(case_anchor) == 1
handler = """        case CMD_SUSFS_ADD_SUS_PATH:
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
            if (!arg3)
                result = -EFAULT;
            else
                result = susfs_add_sus_path(
                    (struct st_susfs_sus_path __user *)arg3);
#else
            result = -EOPNOTSUPP;
#endif
            break;

"""
sysc = sysc.replace(case_anchor, handler + case_anchor, 1)

mask_old = "u64 enabled_features = (1ULL << 8) | (1ULL << 9);"
mask_new = "u64 enabled_features = (1ULL << 0) | (1ULL << 8) | (1ULL << 9);"
assert sysc.count(mask_old) == 1
sysc = sysc.replace(mask_old, mask_new, 1)
sysc = sysc.replace(
    "/* bits 8 (uname) and 9 (logging) are the only enabled features. */",
    "/* bits 0 (sus_path), 8 (uname), and 9 (logging) are enabled. */", 1)
sys_path.write_text(sysc)
print("SUSFS API6 isolated path compile probe: root-only ADD_SUS_PATH, zygote app-state required")
print("No mount hiding / kstat / redirects / symbol hiding / boot image / ZIP")
