#!/usr/bin/env python3
"""Enable the SUSFS 1.5.5 root-only uname feature on top of the API-6 log bridge.

The pinned SUSFS 4.14 patch already hooks newuname with CONFIG_KSU_SUSFS_SPOOF_UNAME.
Only accept userland SET_UNAME when running as UID 0. No filesystem hiding yet.
EXPERIMENTAL COMPILE PROBE; no flashable ZIP.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
cfg_file = root / "KernelSU-Next/kernel/Kconfig"
sys_file = root / "kernel/kernel/sys.c"
susfs_file = root / "kernel/fs/susfs.c"
header = root / "kernel/include/linux/susfs.h"
defs = root / "kernel/include/linux/susfs_def.h"

config = cfg_file.read_text()
source = sys_file.read_text()
susfs = susfs_file.read_text()
assert "config KSU_SUSFS_ENABLE_LOG\n" in config
assert "config KSU_SUSFS_SPOOF_UNAME\n" not in config
assert "#define CMD_SUSFS_SET_UNAME 0x55590" in defs.read_text()
assert "void susfs_spoof_uname(struct new_utsname*" in susfs
assert "int susfs_set_uname(struct st_susfs_uname*" in susfs
assert "#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME" in source
assert "susfs_spoof_uname(&tmp);" in source
assert "struct st_susfs_uname {" in header.read_text()

config += """
config KSU_SUSFS_SPOOF_UNAME
    bool "SUSFS legacy uname redirection (API6 lab only)"
    depends on KSU_SUSFS
    default n
    help
      Enable the existing SUSFS 4.14 uname hook and root-only set command.
      Not a complete SUSFS path or mount hiding implementation.
"""
cfg_file.write_text(config)

old_condition = """         arg2 == CMD_SUSFS_ENABLE_LOG)) {"""
new_condition = """         arg2 == CMD_SUSFS_ENABLE_LOG ||
         arg2 == CMD_SUSFS_SET_UNAME)) {"""
assert source.count(old_condition) == 1
source = source.replace(old_condition, new_condition, 1)

old_case = """        case CMD_SUSFS_ENABLE_LOG:
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG"""
new_case = """        case CMD_SUSFS_SET_UNAME: {
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
            struct st_susfs_uname request;
            if (!arg3 || copy_from_user(&request,
                                        (void __user *)arg3,
                                        sizeof(request))) {
                result = -EFAULT;
            } else if (request.release[__NEW_UTS_LEN] != '\\0' ||
                       request.version[__NEW_UTS_LEN] != '\\0') {
                /* SUSFS uses strncpy; do not permit unterminated strings. */
                result = -EINVAL;
            } else {
                result = susfs_set_uname(
                    (struct st_susfs_uname __user *)arg3);
            }
#else
            result = -EOPNOTSUPP;
#endif
            break;
        }

        case CMD_SUSFS_ENABLE_LOG:
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG"""
assert source.count(old_case) == 1
source = source.replace(old_case, new_case, 1)

old_mask = "u64 enabled_features = 1ULL << 9;"
new_mask = "u64 enabled_features = (1ULL << 8) | (1ULL << 9);"
assert source.count(old_mask) == 1
source = source.replace(old_mask, new_mask, 1)
source = source.replace("/* bit 9 is the one and only supported SUSFS feature here. */",
                        "/* bits 8 (uname) and 9 (logging) are the only enabled features. */", 1)
sys_file.write_text(source)
print("SUSFS 1.5.5 API6: root-only uname+logging commands enabled; path/mount hiding disabled")
