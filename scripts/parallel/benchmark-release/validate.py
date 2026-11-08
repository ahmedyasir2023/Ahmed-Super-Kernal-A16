#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
wf=(ROOT/".github/workflows/v10-hypercore-build.yml").read_text(errors="replace")
for token in [
"KERNEL_SHA: 10380039ddcd6ead841e1fc4ca744a2dd6e92fb8",
"KSU_SHA: b933b1f728116a456fbebf27b6a8772a640cdf23",
"SUSFS_SHA: 77905b5a071e6f3669e3b1814cea30147c0801da",
"CLANG_SHA256:",
"verify_boot_dtb.py",
]:
    assert token in wf or token in (ROOT/"scripts/verify_boot_dtb.py").read_text(errors="replace"), f"Missing release pin/check: {token}"
assert (ROOT/"scripts/v7/preflash_audit.py").is_file()
print("PASS: pinned kernel/toolchain/KSU/SUSFS and boot-DTB release checks.")
