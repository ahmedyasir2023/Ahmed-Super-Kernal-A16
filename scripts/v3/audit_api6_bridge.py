#!/usr/bin/env python3
"""Audit a V3 SUSFS bridge from the ABI-4 SUSFS-aware reference to working ABI-6 KSU.

READ-ONLY. This script never patches a kernel, builds a boot image or emits ZIPs.
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
official = root / "KernelSU-Next"
fork = root / "KSU-SUSFS-Reference"
sus = root / "susfs4ksu"
out = root / "audit"
out.mkdir(exist_ok=True)

def head(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

def all_source(repo: Path) -> dict[str, str]:
    return {str(p.relative_to(repo)): p.read_text(errors="replace")
            for p in (repo / "kernel").rglob("*")
            if p.is_file() and p.suffix in {".c", ".h"}}

def version(repo: Path) -> int:
    s = (repo / "uapi/supercall.h").read_text()
    match = re.search(r"KERNEL_SU_UAPI_VERSION\s*=\s*(\d+)|#define\s+KERNEL_SU_UAPI_VERSION\s+(\d+)", s)
    if not match:
        raise RuntimeError("Cannot locate UAPI version in " + str(repo))
    return int(next(v for v in match.groups() if v))

assert version(official) == 6, "Working official UAPI changed; do not port blindly"
assert version(fork) == 4, "Reference UAPI changed; do not port blindly"
assert (sus / "kernel_patches/include/linux/susfs.h").read_text().count('#define SUSFS_VERSION "v1.5.5"') == 1
assert (fork / "kernel/Kconfig").read_text().count('config KSU_SUSFS\n') == 1
assert 'config KSU_SUSFS\n' not in (official / "kernel/Kconfig").read_text(), "Official bridge already present; re-audit"

base_sources = all_source(official)
fork_sources = all_source(fork)
terms = re.compile(r"\b(?:susfs_[A-Za-z0-9_]+|ksu_susfs_[A-Za-z0-9_]+|CMD_SUSFS_[A-Z0-9_]+)\b")

def mention_map(sources: dict[str, str]) -> dict[str, list[str]]:
    mentions: dict[str, set[str]] = {}
    for path, source in sources.items():
        for name in set(terms.findall(source)):
            mentions.setdefault(name, set()).add(path)
    return {name: sorted(paths) for name, paths in sorted(mentions.items())}

source_symbols = mention_map(fork_sources)
base_symbols = mention_map(base_sources)
only_fork = {key: value for key, value in source_symbols.items() if key not in base_symbols}
in_both = sorted(set(source_symbols) & set(base_symbols))

patch_file = sus / "kernel_patches/KernelSU/10_enable_susfs_for_ksu.patch"
patch_text = patch_file.read_text()
old_layout = sorted(set(re.findall(r"^diff --git a/(kernel/[^ ]+) b/", patch_text, re.M)))
renamed = [path for path in old_layout if not (official / path).is_file()]
# Audit key interfaces that must be independently ported to the working ABI-6 base.
required = {
    "kernel core init": "kernel/core/init.c",
    "setuid/mount lifecycle": "kernel/hook/setuid_hook.c",
    "supercall handling": "kernel/supercall/dispatch.c",
    "unmount behavior": "kernel/feature/kernel_umount.c",
    "SELinux domain checks": "kernel/selinux/selinux.c",
    "module daemon integration": "kernel/runtime/ksud_integration.c",
}
presence = {k: {
    "api6": (official / path).is_file(),
    "reference_api4": (fork / path).is_file(),
    "path": path
} for k, path in required.items()}

report = {
    "status": "SOURCE AUDIT ONLY; SUSFS NOT COMPILED/ENABLED/RELEASED",
    "official_api6": head(official),
    "reference_api4": head(fork),
    "susfs_4_14": head(sus),
    "api_versions": {"official": 6, "reference": 4},
    "legacy_patch_source_paths": old_layout,
    "legacy_patch_paths_missing_in_api6": renamed,
    "reference_susfs_symbols": len(source_symbols),
    "official_susfs_symbols": len(base_symbols),
    "reference_symbols_not_present_in_api6": only_fork,
    "common_symbols": in_both,
    "critical_integration_sites": presence,
    "release_gates": [
        "Keep working KernelSU API 6 (no version spoofing or API 4 swap).",
        "Port SUSFS kernel filesystem changes and missing process-state ABI in isolated CI.",
        "Implement reviewed init, setuid, mount, SELinux and supercall handlers in API 6.",
        "Build with Clang 21 and confirm seven original DTBs match exactly.",
        "Verify device root, SUSFS userspace commands, SELinux Enforcing and hardware.",
        "No boot.img, flashable ZIP or AVB modification from this source audit."
    ]
}
(out / "v3-api6-bridge-gap.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
lines = [
    "Ahmed Super Kernal A16 V3: Working API-6 <-> SUSFS 1.5.5 compatibility gap",
    "STATUS: SOURCE AUDIT ONLY, NOT FLASHABLE",
    f"Official API-6 source: {report['official_api6']}",
    f"Reference API-4 SUSFS source: {report['reference_api4']}",
    f"SUSFS 4.14 source: {report['susfs_4_14']}",
    f"Older SUSFS-KSU patch paths missing in modern API-6: {len(renamed)} / {len(old_layout)}",
    f"Reference SUSFS-related symbols: {len(source_symbols)}",
    f"Not present in API-6: {len(only_fork)}",
    "",
    "Missing / renamed legacy source paths:",
    *(" - " + x for x in renamed),
    "",
    "Critical sites:",
    *(f" - {name}: {info['path']} | official={info['api6']} | old fork={info['reference_api4']}" for name, info in presence.items()),
    "",
    "Examples of symbols requiring actual bridge review:",
    *(" - " + name + " (" + ", ".join(paths[:3]) + ")" for name, paths in list(only_fork.items())[:70]),
    "",
    "Root API-6 baseline must remain unchanged until a full bridge passes real-world tests.",
    "No kernel patches were applied, no binaries or installation packages created."
]
(out / "v3-api6-bridge-gap.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines[:16]))
