#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/kernel/sys.c","CMD_SUSFS_SHOW_ENABLED_FEATURES"),
("kernel/kernel/sys.c","susfs_set_uname("),
("kernel/kernel/sys.c","susfs_set_log("),
("kernel/kernel/sys.c","u64 enabled_features = (1ULL << 0) | (1ULL << 8) | (1ULL << 9)"),
("KernelSU-Next/uapi/supercall.h","#define KERNEL_SU_UAPI_VERSION 6"),
("kernel/security/selinux/hooks.c","selinux"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
source=(ROOT/"kernel/kernel/sys.c").read_text(errors="replace")
assert "selinux_enforcing = 0" not in source
print("PASS: KernelSU API6, SUSFS feature mask 0x301 and SELinux source contracts.")
