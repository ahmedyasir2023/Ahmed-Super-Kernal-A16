#!/usr/bin/env python3
"""Port missing SUSFS 1.5.5 process-umount flag accessors for ARM64 4.14.

The pinned SUSFS 1.5.5 include/linux/susfs_def.h lacks helpers required by
sidex15 legacy-susfs-v2 setuid_hook.c. A related crDroid Realme sm7125 kernel
implements them with bit 33 of arm64 thread_info.flags. Fail closed if bit 33
is used, layout changes, or the new helper implementation already exists.

Reference:
https://github.com/crdroidandroid/android_kernel_realme_sm7125/blob/60f3427322632b19e8bc3e22731ecc7ce0baac25/include/linux/susfs_def.h
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
arm64 = root / "kernel/arch/arm64/include/asm/thread_info.h"
susfs = root / "kernel/include/linux/susfs_def.h"
setuid = root / "KernelSU-Next/kernel/hook/setuid_hook.c"

arch_source = arm64.read_text()
susfs_source = susfs.read_text()
setuid_source = setuid.read_text()

flags = re.findall(r"^#define\s+TIF_(?!PROC_UMOUNTED)(\w+)\s+(\d+)\b", arch_source, re.M)
assert len(flags) > 10, "Unexpected ARM64 TIF flag layout"
assert 33 not in {int(number) for _, number in flags}, "ARM64 thread-info flag 33 already allocated"
assert "#define TIF_PROC_UMOUNTED" not in arch_source, "TIF_PROC_UMOUNTED already exists in ARM64 header"
assert "susfs_set_current_proc_umounted();" in setuid_source, "Unexpected SUSFS-aware fork source"
assert setuid_source.count("susfs_set_current_proc_umounted();") == 1
assert "susfs_set_current_proc_umounted" not in susfs_source
assert "susfs_is_current_proc_umounted" not in susfs_source
assert susfs_source.startswith("#ifndef KSU_SUSFS_DEF_H\n#define KSU_SUSFS_DEF_H\n")
assert susfs_source.count("#endif // #ifndef KSU_SUSFS_DEF_H") == 1
assert "#include <linux/bits.h>" in susfs_source

add = """
/* ARM64 Linux 4.14: SUSFS per-thread umount tracking.
 * Ported from crDroid's Realme SM7125 SUSFS-compatible kernel.
 * Thread flag 33 is verified unused in the pinned source above.
 */
#define TIF_PROC_UMOUNTED 33

static inline bool susfs_is_current_proc_umounted(void)
{
    return test_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED);
}

static inline void susfs_set_current_proc_umounted(void)
{
    set_ti_thread_flag(&current->thread_info, TIF_PROC_UMOUNTED);
}
"""
susfs.write_text(susfs_source.replace("#endif // #ifndef KSU_SUSFS_DEF_H", add + "#endif // #ifndef KSU_SUSFS_DEF_H"))
print("Patched missing process umount tracking helpers with verified ARM64 thread-info bit 33")
