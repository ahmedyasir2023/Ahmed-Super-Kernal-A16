#!/usr/bin/env python3
"""V3 API6 lab: record zygote-spawned, unprivileged Android app task state.

This is **tracking only**: it never enables SUSFS path/mount concealment,
does not change Root privileges, SELinux or any driver's source, and cannot
produce a flashable artifact. Do not deploy without verified on-device tests.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cfg = root / "KernelSU-Next/kernel/Kconfig"
hook = root / "KernelSU-Next/kernel/hook/setuid_hook.c"
task_header = root / "kernel/include/linux/sched.h"
flags_header = root / "kernel/include/linux/susfs_def.h"
selinux_header = root / "KernelSU-Next/kernel/selinux/selinux.h"

config = cfg.read_text()
source = hook.read_text()
assert "#define TASK_STRUCT_NON_ROOT_USER_APP_PROC BIT(24)" in flags_header.read_text()
assert "u64 susfs_task_state;" in task_header.read_text()
assert "bool is_zygote(const struct cred* cred);" in selinux_header.read_text()
assert "config KSU_SUSFS_SPOOF_UNAME\n" in config
assert "config KSU_SUSFS_PROC_TRACK\n" not in config

config += """
config KSU_SUSFS_PROC_TRACK
    bool "Track zygote child app state for SUSFS (CI experiment ONLY)"
    depends on KSU_SUSFS
    default n
    help
      Marks unprivileged zygote-spawned Android application tasks.
      No SUSFS path/mount hiding or root visibility changes are enabled.
"""
cfg.write_text(config)

anchor = '#include "feature/kernel_umount.h"\n'
assert source.count(anchor) == 1, "Unexpected KernelSU Next setuid source"
source = source.replace(anchor, anchor + """#ifdef CONFIG_KSU_SUSFS_PROC_TRACK
#include <linux/susfs_def.h>
#include "selinux/selinux.h"
#endif
""", 1)

entry = "int ksu_handle_setresuid(uid_t old_uid, uid_t new_uid)\n{\n"
assert source.count(entry) == 1, "Unexpected KernelSU Next setresuid declaration"

tracking = """#ifdef CONFIG_KSU_SUSFS_PROC_TRACK
/*
 * A zygote fork starts privileged and drops to an Android application UID.
 * This marks its copied task_struct for a later SUSFS userspace-lifecycle
 * audit, but does not activate any existing SUSFS path/mount checks.
 *
 * Android appId is the per-user UID modulo AID_USER_OFFSET (100000).
 * Isolated service UIDs are kept distinct from manager/root-allowed UIDs.
 */
static void susfs_track_zygote_app(uid_t old_uid, uid_t new_uid)
{
    uid_t app_id = new_uid % 100000;

    if (old_uid != 0 || new_uid == 0)
        return;
    if (!is_zygote(current_cred()))
        return;
    if (!((app_id >= 10000 && app_id <= 19999) ||
          (app_id >= 99000 && app_id <= 99999)))
        return;
    if (is_uid_manager(new_uid) || ksu_is_allow_uid_for_current(new_uid))
        return;

    current->susfs_task_state |= TASK_STRUCT_NON_ROOT_USER_APP_PROC;
}
#endif

"""
source = source.replace(entry, tracking + entry, 1)
source = source.replace(entry, entry + """#ifdef CONFIG_KSU_SUSFS_PROC_TRACK
    susfs_track_zygote_app(old_uid, new_uid);
#endif
""", 1)
assert source.count("susfs_track_zygote_app(old_uid, new_uid);") == 1
hook.write_text(source)
print("SUSFS process-state lab staged: zygote/UID/Root-manager gates, no hiding features")
