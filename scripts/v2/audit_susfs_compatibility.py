#!/usr/bin/env python3
"""READ-ONLY SUSFS 1.5.5 source compatibility audit for modern KSU Legacy.

Do not confuse an audit with a functional SUSFS build. It deliberately makes
no edits to source files and generates no image or flashable package.
"""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent.parent.parent
ksu = root / "KernelSU-Next"
kernel = root / "kernel"
susfs = root / "susfs4ksu"
out = root / "audit/V2-SUSFS-compatibility-preflight.txt"
out.parent.mkdir(parents=True, exist_ok=True)

patch = susfs / "kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch"
kernel_patch = susfs / "kernel_patches/50_add_susfs_in_kernel-4.14.patch"
susfs_h = susfs / "kernel_patches/include/linux/susfs.h"
assert patch.is_file() and kernel_patch.is_file() and susfs_h.is_file()
text = patch.read_text()
paths = sorted(set(re.findall(r"^diff --git a/(kernel/[^ ]+) b/", text, re.M)))
assert len(paths) >= 10, "Unexpected SUSFS KSU patch format"
present = [p for p in paths if (ksu / p).exists()]
absent = [p for p in paths if not (ksu / p).exists()]
version = re.search(r'^#define SUSFS_VERSION "([^"]+)"', susfs_h.read_text(), re.M)
assert version, "SUSFS header version missing"
assert version.group(1) == "v1.5.5", "Unreviewed SUSFS version"
assert (ksu / "kernel/Kbuild").is_file()
assert (ksu / "kernel/core/init.c").is_file()
assert (ksu / "kernel/feature/sucompat.c").is_file()
assert (ksu / "kernel/supercall/dispatch.c").is_file()
assert (ksu / "kernel/feature/kernel_umount.c").is_file()
assert (kernel / "arch/arm64/configs/atoll_defconfig").is_file()

# Git apply --check makes no changes, but proves a patch does/does not apply.
check = subprocess.run(
    ["git", "-C", str(ksu), "apply", "--check", str(patch)],
    capture_output=True, text=True,
)

legacy_symbols = sorted(set(re.findall(r"\b(?:susfs|ksu_susfs)_[a-zA-Z0-9_]+\b", text)))
modern = {
    "core init": "kernel/core/init.c",
    "SU compatibility": "kernel/feature/sucompat.c",
    "kernel umount": "kernel/feature/kernel_umount.c",
    "supercall dispatcher": "kernel/supercall/dispatch.c",
    "LSM hooks": "kernel/hook/lsm_hooks.c",
    "mount namespace": "kernel/infra/su_mount_ns.c",
    "boot lifecycle": "kernel/runtime/boot_event.c",
}
lines = [
    "Ahmed Super Kernal A16 V2 — SUSFS SOURCE COMPATIBILITY PREFLIGHT",
    "STATUS: READ-ONLY SOURCE AUDIT; NOT A SUSFS BUILD, NOT FLASHABLE",
    f"SUSFS version: {version.group(1)} (non-GKI Linux 4.14)",
    f"Legacy KernelSU patch files: {len(paths)}",
    f"Matching modern KernelSU source file paths: {len(present)}",
    f"Missing/renamed paths in modern KernelSU: {len(absent)}",
    "",
    "Legacy patch path(s) present:",
    *[f"  {p}" for p in present],
    "",
    "Legacy patch path(s) missing or renamed:",
    *[f"  {p}" for p in absent],
    "",
    f"Legacy KernelSU patch cleanly applies to modern source: {'yes' if check.returncode == 0 else 'NO'}",
    "First context conflicts:",
    *[f"  {s}" for s in (check.stderr or check.stdout).splitlines()[:30]],
    "",
    "Modern integration locations to review:",
    *[f"  {k}: {v} (exists={ (ksu / v).is_file() })" for k, v in modern.items()],
    f"Legacy SUSFS API symbol references: {len(legacy_symbols)}",
    "",
    "Required: a separately implemented and reviewed KernelSU-SUSFS ABI bridge.",
    "Do not enable CONFIG_KSU_SUSFS solely to make a build pass.",
    "Do not edit kernel vendor driver or DTB sources or use obsolete KernelSU Makefile hooks.",
    "No patches applied; no Boot, ZIP, or user partitions changed.",
]
out.write_text("\n".join(lines) + "\n")
print("\n".join(lines))
