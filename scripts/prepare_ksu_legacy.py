#!/usr/bin/env python3
"""Prepare pinned KernelSU Next 4.14 compatibility hooks *before* Kbuild.

The legacy KernelSU Next Makefile inserts source code with sed while its own
objects are compiling. On parallel builds, fs/namespace.o is already compiled,
producing a missing path_umount linker symbol. Modify exact, validated source
locations before invoking make. Do not modify any device drivers or device trees.
"""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
kernel = root / "kernel"

def patch(path: str, old: str, new: str) -> None:
    file = kernel / path
    source = file.read_text()
    if source.count(old) != 1:
        raise RuntimeError(f"Unexpected {path} source; refusing to patch ({old[:70]!r})")
    file.write_text(source.replace(old, new, 1))
    print(f"Patched {path} before compiling")


ns = (kernel / "fs/namespace.c").read_text()
assert "int path_umount(struct path *path, int flags)" not in ns
assert "static int can_umount(const struct path *path, int flags)" not in ns
assert "static int do_umount(struct mount *mnt, int flags)" in ns
assert "static bool is_mnt_ns_file(struct dentry *dentry)" in ns

# Faithful to the pinned KernelSU Next fork's legacy compatibility functions.
# path_umount owns its path references, matching core_hook.c's call contract.
compat = """/* KernelSU Next 4.14 compatibility: installed before Kbuild, never during it. */
static int can_umount(const struct path *path, int flags)
{
    struct mount *mnt = real_mount(path->mnt);

    if (flags & ~(MNT_FORCE | MNT_DETACH | MNT_EXPIRE | UMOUNT_NOFOLLOW))
        return -EINVAL;
    if (!may_mount())
        return -EPERM;
    if (path->dentry != path->mnt->mnt_root)
        return -EINVAL;
    if (!check_mnt(mnt))
        return -EINVAL;
    if (mnt->mnt.mnt_flags & MNT_LOCKED)
        return -EINVAL;
    if (flags & MNT_FORCE && !capable(CAP_SYS_ADMIN))
        return -EPERM;
    return 0;
}

int path_umount(struct path *path, int flags)
{
    struct mount *mnt = real_mount(path->mnt);
    int ret;

    ret = can_umount(path, flags);
    if (!ret)
        ret = do_umount(mnt, flags);

    /* Do not use path_put: that would clear mnt_expiry_mark. */
    dput(path->dentry);
    mntput_no_expire(mnt);
    return ret;
}

"""
patch("fs/namespace.c", "static bool is_mnt_ns_file(struct dentry *dentry)",
      compat + "static bool is_mnt_ns_file(struct dentry *dentry)")
patch("fs/internal.h", "extern void __init mnt_init(void);",
      "extern void __init mnt_init(void);\nint path_umount(struct path *path, int flags);")

# KernelSU Makefile would insert this same helper late into cred.h. It must be
# present before other translation units start compiling, with the corrected
# atomic_long_t access used by the original Realme source.
cred = (kernel / "include/linux/cred.h").read_text()
assert "get_cred_rcu(" not in cred
assert "atomic_long_t\tusage;" in cred
rcu_helper = """static inline const struct cred *get_cred_rcu(const struct cred *cred)
{
    struct cred *nonconst_cred = (struct cred *)cred;

    if (!cred)
        return NULL;
    if (!atomic_long_inc_not_zero(&nonconst_cred->usage))
        return NULL;
    validate_creds(cred);
    return cred;
}

"""
patch("include/linux/cred.h", "static inline void put_cred(const struct cred *_cred)",
      rcu_helper + "static inline void put_cred(const struct cred *_cred)")

# Prevent the legacy KSU Makefile from expanding struct seccomp after the build
# has already compiled other users of that structure.
patch("include/linux/seccomp.h", "#include <linux/thread_info.h>",
      "#include <linux/thread_info.h>\n#include <linux/atomic.h>")
patch("include/linux/seccomp.h", "struct seccomp {\n\tint mode;",
      "struct seccomp {\n\tint mode;\n\tatomic_t filter_count;")

print("Validated deterministic legacy compatibility: path_umount, cred, seccomp")
