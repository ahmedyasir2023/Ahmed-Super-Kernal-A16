#!/usr/bin/env python3
"""V2 experimental, source-pinned manual hooks for the Atoll 4.14.336 kernel.

Kernelsu-Next legacy (Oct 2026) requires manual hooking on this Linux 4.14
tree; do not select its kprobe mode (requires 5.10+) or syscall table
patching (requires >=4.17). Every source anchor is validated; never skip.
Only this experimental root-only CI branch should run this code.
"""
from pathlib import Path

base = Path(__file__).resolve().parent.parent.parent / "kernel"

def insert(path, needle, repl):
    file = base / path
    s = file.read_text()
    if s.count(needle) != 1:
        raise RuntimeError(f"Unrecognized base source in {path}, refusing to modify: {needle[:70]!r}, occurrences={s.count(needle)}")
    file.write_text(s.replace(needle, repl, 1))
    print(f"Manual hook: {path}")

prefix = """#ifdef CONFIG_KSU_MANUAL_HOOK
/* KernelSU Next manual hooks: pinned to original Linux 4.14.336 source */
extern int ksu_handle_execveat(int *fd, struct filename **name,
                               void *argv, void *envp, int *flags);
#endif

"""
insert("fs/exec.c",
       "int do_execve(struct filename *filename,",
       prefix + "int do_execve(struct filename *filename,")

# Scope substitutions to function bodies to avoid changing unrelated code.
def scope_exec(name, next_name, call, fd, flags):
    path = base / "fs/exec.c"
    s = path.read_text()
    a = s.index(name)
    b = s.index(next_name, a + len(name))
    section = s[a:b]
    exact = f"\treturn do_execveat_common({call});"
    if section.count(exact) != 1:
        raise RuntimeError(f"Missing precise call in {name}")
    hook = (
        "#ifdef CONFIG_KSU_MANUAL_HOOK\n"
        f"\tint ksu_dfd = {fd};\n"
        f"\tint ksu_flags = {flags};\n"
        "\tksu_handle_execveat(&ksu_dfd, &filename, &argv, &envp, &ksu_flags);\n"
        f"\treturn do_execveat_common({call});\n"
        "#else\n" + exact + "\n#endif"
    )
    # In C89/older Kbuild, declarations must appear after argv/envp.
    section = section.replace(exact, hook, 1)
    path.write_text(s[:a] + section + s[b:])

scope_exec("int do_execve(struct filename *filename,", "int do_execveat(",
           "AT_FDCWD, filename, argv, envp, 0", "AT_FDCWD", "0")
scope_exec("int do_execveat(", "#ifdef CONFIG_COMPAT",
           "fd, filename, argv, envp, flags", "fd", "flags")
scope_exec("static int compat_do_execve(struct filename *filename,",
           "static int compat_do_execveat(",
           "AT_FDCWD, filename, argv, envp, 0", "AT_FDCWD", "0")
scope_exec("static int compat_do_execveat(", "#endif\n\nvoid set_binfmt(",
           "fd, filename, argv, envp, flags", "fd", "flags")

insert("fs/open.c",
       "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)",
       """#ifdef CONFIG_KSU_MANUAL_HOOK
extern int ksu_handle_faccessat(int *dfd, const char __user **filename,
                                 int *mode, int *flags);
#endif
SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)""")
insert("fs/open.c",
       "\tunsigned int lookup_flags = LOOKUP_FOLLOW;\n\n\tif (mode & ~S_IRWXO)",
       """\tunsigned int lookup_flags = LOOKUP_FOLLOW;
#ifdef CONFIG_KSU_MANUAL_HOOK
\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);
#endif

\tif (mode & ~S_IRWXO)""")

insert("fs/read_write.c",
       "SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)",
       """#ifdef CONFIG_KSU_MANUAL_HOOK
extern bool ksu_vfs_read_hook;
extern void ksu_handle_sys_read(unsigned int fd);
#endif
SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)""")
# The vendor uses this same OPLUS read-time snippet in multiple syscalls.
# Scope the insertion strictly to the read() syscall body.
path = base / "fs/read_write.c"
s = path.read_text()
a = s.index("SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)")
b = s.index("SYSCALL_DEFINE3(write, unsigned int, fd,", a)
block = s[a:b]
needle = "\\tssize_t ret = -EBADF;\\n#if defined(OPLUS_FEATURE_IOMONITOR)"
replacement = """\\tssize_t ret = -EBADF;
#ifdef CONFIG_KSU_MANUAL_HOOK
\\tif (unlikely(ksu_vfs_read_hook))
\\t\\tksu_handle_sys_read(fd);
#endif
#if defined(OPLUS_FEATURE_IOMONITOR)"""
assert block.count(needle) == 1, "Unable to locate exact read() entry"
path.write_text(s[:a] + block.replace(needle, replacement, 1) + s[b:])


insert("fs/stat.c",
       "#if !defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_SYS_NEWFSTATAT)\nSYSCALL_DEFINE4(newfstatat",
       """#ifdef CONFIG_KSU_MANUAL_HOOK
extern int ksu_handle_stat(int *dfd, const char __user **filename, int *flags);
#endif
#if !defined(__ARCH_WANT_STAT64) || defined(__ARCH_WANT_SYS_NEWFSTATAT)
SYSCALL_DEFINE4(newfstatat""")
# Scoped body patch: only the first newfstatat function, not other stat helpers.
path = base / "fs/stat.c"
s = path.read_text()
start = s.index("SYSCALL_DEFINE4(newfstatat")
end = s.index("#endif", start)
section = s[start:end]
needle = "\terror = vfs_fstatat(dfd, filename, &stat, flag);"
assert section.count(needle) == 1
section = section.replace(needle, """#ifdef CONFIG_KSU_MANUAL_HOOK
\tksu_handle_stat(&dfd, &filename, &flag);
#endif
""" + needle, 1)
path.write_text(s[:start] + section + s[end:])

insert("kernel/reboot.c",
       "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,",
       """#ifdef CONFIG_KSU_MANUAL_HOOK
extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd,
                                  void __user **arg);
#endif
SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,""")
insert("kernel/reboot.c",
       "\tint ret = 0;\n\n\t/* We only trust the superuser",
       """\tint ret = 0;
#ifdef CONFIG_KSU_MANUAL_HOOK
\tksu_handle_sys_reboot(magic1, magic2, cmd, &arg);
#endif

\t/* We only trust the superuser""")

print("Root-only V2 manual hook integration complete; SUSFS is intentionally not yet integrated.")
