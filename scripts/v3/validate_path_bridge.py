#!/usr/bin/env python3
"""Fail-closed SUSFS v1.5.5 path-only source/ABI contract for API-6 build."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
cfg = (root / "KernelSU-Next/kernel/Kconfig").read_text()
build = (root / "scripts/v3/build_api6_susfs_path.sh").read_text()
sysc = (root / "kernel/kernel/sys.c").read_text()
hook = (root / "KernelSU-Next/kernel/hook/setuid_hook.c").read_text()
api = (root / "KernelSU-Next/uapi/supercall.h").read_text()
d = (root / "kernel/include/linux/susfs_def.h").read_text()
susfs = (root / "kernel/fs/susfs.c").read_text()
assert "#define KERNEL_SU_UAPI_VERSION 6" in api
assert cfg.count("config KSU_SUSFS_SUS_PATH\n") == 1
assert "    depends on KSU_SUSFS && KSU_SUSFS_PROC_TRACK" in cfg
for name in ("KSU_SUSFS", "KSU_SUSFS_ENABLE_LOG", "KSU_SUSFS_SPOOF_UNAME",
             "KSU_SUSFS_PROC_TRACK", "KSU_SUSFS_SUS_PATH"):
    assert "CONFIG_" + name + "=y" in build, name
for k in ("CMD_SUSFS_ADD_SUS_PATH",
          "susfs_add_sus_path(", "current_uid().val != 0",
          "u64 enabled_features = (1ULL << 0) | (1ULL << 8) | (1ULL << 9);"):
    assert k in sysc, k
assert "current->susfs_task_state |= TASK_STRUCT_NON_ROOT_USER_APP_PROC" in hook
assert "if (!is_zygote(current_cred()))" in hook
assert "int susfs_add_sus_path(struct st_susfs_sus_path*" in susfs
assert "#define CMD_SUSFS_ADD_SUS_PATH 0x55550" in d
for forbidden in ("KSU_SUSFS_SUS_MOUNT", "KSU_SUSFS_SUS_KSTAT",
                  "KSU_SUSFS_TRY_UMOUNT", "KSU_SUSFS_OPEN_REDIRECT",
                  "KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS"):
    assert "-e " + forbidden not in build, forbidden
    assert "config " + forbidden + "\n" not in cfg, forbidden
print("Source ABI contract passed: API6 + zygote-gated SUS_PATH; mount/stat/redirect hiding OFF.")
