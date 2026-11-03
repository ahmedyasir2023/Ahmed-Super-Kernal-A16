#!/usr/bin/env python3
"""Fail-closed API6 SUSFS task-state compile-only source contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
api = (root / "KernelSU-Next/uapi/supercall.h").read_text()
cfg = (root / "KernelSU-Next/kernel/Kconfig").read_text()
hook = (root / "KernelSU-Next/kernel/hook/setuid_hook.c").read_text()
sysc = (root / "kernel/kernel/sys.c").read_text()
defh = (root / "kernel/include/linux/susfs_def.h").read_text()
sched = (root / "kernel/include/linux/sched.h").read_text()
build = (root / "scripts/v3/build_api6_susfs_appstate.sh").read_text()
assert "#define KERNEL_SU_UAPI_VERSION 6" in api
assert cfg.count("config KSU_SUSFS_PROC_TRACK\n") == 1
assert "    depends on KSU_SUSFS" in cfg
assert "-e KSU_SUSFS_PROC_TRACK" in build
assert "CONFIG_KSU_SUSFS_PROC_TRACK=y" in build
assert "#define TASK_STRUCT_NON_ROOT_USER_APP_PROC BIT(24)" in defh
assert "u64 susfs_task_state;" in sched
for needle in [
    '#include "selinux/selinux.h"',
    "if (old_uid != 0 || new_uid == 0)",
    "if (!is_zygote(current_cred()))",
    "app_id >= 10000 && app_id <= 19999",
    "app_id >= 99000 && app_id <= 99999",
    "is_uid_manager(new_uid)",
    "ksu_is_allow_uid_for_current(new_uid)",
    "current->susfs_task_state |= TASK_STRUCT_NON_ROOT_USER_APP_PROC",
    "susfs_track_zygote_app(old_uid, new_uid);",
]:
    assert needle in hook, needle

# Identical SUSFS features to prior successful uname+logging build.
assert "u64 enabled_features = (1ULL << 8) | (1ULL << 9);" in sysc
for name in [
    "KSU_SUSFS_SUS_PATH", "KSU_SUSFS_SUS_MOUNT",
    "KSU_SUSFS_SUS_KSTAT", "KSU_SUSFS_OPEN_REDIRECT",
    "KSU_SUSFS_TRY_UMOUNT", "KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS",
]:
    assert "-e " + name not in build, "Unreviewed hiding feature enabled: " + name
    assert "config " + name + "\n" not in cfg, "Unreviewed hiding Kconfig: " + name
print("API6 zygote app-state source contract passed; SUSFS path/mount hiding DISABLED.")
