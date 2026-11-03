#!/usr/bin/env python3
"""Source guard for experimental API-6 SUSFS uname+log feature compile.

Fail if filesystem-hiding config is accidentally turned on, or if Root API
or SUSFS helper signatures differ from pinned sources.
"""
from pathlib import Path
p = Path(__file__).resolve().parents[2]
sysc = (p / "kernel/kernel/sys.c").read_text()
cfg = (p / "KernelSU-Next/kernel/Kconfig").read_text()
api = (p / "KernelSU-Next/uapi/supercall.h").read_text()
build = (p / "scripts/v3/build_api6_susfs_uname.sh").read_text()
susfs = (p / "kernel/fs/susfs.c").read_text()
assert "#define KERNEL_SU_UAPI_VERSION 6" in api
for key in ("config KSU_SUSFS_ENABLE_LOG\n", "config KSU_SUSFS_SPOOF_UNAME\n"):
    assert cfg.count(key) == 1, key
for key in ("-e KSU_SUSFS_ENABLE_LOG", "-e KSU_SUSFS_SPOOF_UNAME",
            "CONFIG_KSU_SUSFS_ENABLE_LOG=y", "CONFIG_KSU_SUSFS_SPOOF_UNAME=y"):
    assert key in build, key
for key in ("CMD_SUSFS_SHOW_VERSION", "CMD_SUSFS_SHOW_VARIANT",
            "CMD_SUSFS_SHOW_ENABLED_FEATURES", "CMD_SUSFS_SET_UNAME",
            "CMD_SUSFS_ENABLE_LOG", "susfs_set_uname(", "susfs_set_log(",
            "susfs_spoof_uname(&tmp);", "request.release[__NEW_UTS_LEN]",
            "request.version[__NEW_UTS_LEN]",
            "u64 enabled_features = (1ULL << 8) | (1ULL << 9);",
            "if (current_uid().val != 0)"):
    assert key in sysc, key
assert "int susfs_set_uname(struct st_susfs_uname*" in susfs
assert "void susfs_spoof_uname(struct new_utsname*" in susfs
for name in ("KSU_SUSFS_SUS_PATH", "KSU_SUSFS_SUS_MOUNT",
             "KSU_SUSFS_SUS_KSTAT", "KSU_SUSFS_OPEN_REDIRECT",
             "KSU_SUSFS_TRY_UMOUNT"):
    assert "-e " + name not in build, name
    assert "config " + name + "\n" not in cfg, name
print("Pinned SUSFS API6 uname+log source contract passed (no path/mount hiding).")
