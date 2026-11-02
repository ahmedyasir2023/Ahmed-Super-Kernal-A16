#!/usr/bin/env python3
"""Port only the two context-only SUSFS 4.14 patch conflicts to RMX2170.

This never discards SUSFS hunks or alters the stock vendor blocks. Unexpected
source layout fails closed, so future upstream changes require manual review.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
kernel = root / "kernel"
patch_path = root / "susfs4ksu/kernel_patches/50_add_susfs_in_kernel-4.14.patch"
patch = patch_path.read_text()
names = ("fs/namespace.c", "fs/proc/task_mmu.c")


def replace_file_hunk(patch_data: str, filename: str, old: str, new: str,
                      before: str, old_count: int, new_count: int) -> str:
    start = patch_data.index("diff --git a/" + filename + " b/" + filename)
    end = patch_data.find("\ndiff --git ", start + 1)
    if end == -1:
        end = len(patch_data)
    section = patch_data[start:end]
    assert section.count(old) == 1, f"{filename}: unexpected patch context"
    assert section.count(before) == 1, f"{filename}: unexpected hunk header"
    section = section.replace(old, new, 1)
    # Recalculate the first hunk sizes after including vendor-specific context.
    delta = len(new.splitlines()) - len(old.splitlines())
    header = re.sub(
        r"@@ -(\d+)," + str(old_count) + r" \+(\d+)," + str(new_count) + r" @@",
        lambda m: f"@@ -{m.group(1)},{old_count+delta} +{m.group(2)},{new_count+delta} @@",
        before,
        count=1,
    )
    assert header != before, f"{filename}: failed to adjust hunk header"
    section = section.replace(before, header, 1)
    return patch_data[:start] + section + patch_data[end:]


ns = (kernel / names[0]).read_text()
ns_marker = '#include "internal.h"\n'
assert ns.count(ns_marker) == 1
vendor = ns.split(ns_marker, 1)[1].split("/* Maximum number of mounts", 1)[0]
assert vendor.startswith("#ifdef CONFIG_OPLUS_SECURE_GUARD\n")
assert vendor.endswith("#endif /* CONFIG_OPLUS_SECURE_GUARD*/\n\n")
assert vendor.count("#ifdef") == 3 and vendor.count("#endif") == 3
old = ' #include "internal.h"\n \n'
new = ' #include "internal.h"\n' + "".join(" " + line for line in vendor.splitlines(keepends=True))
patch = replace_file_hunk(
    patch, names[0], old, new, "@@ -27,10 +27,39 @@", 10, 39
)
mmu = (kernel / names[1]).read_text()
assert mmu.count("#include <linux/mm_inline.h>\n#include <linux/ctype.h>\n") == 1
patch = replace_file_hunk(
    patch, names[1],
    "+#endif\n \n #include <asm/elf.h>\n",
    "+#endif\n #include <linux/ctype.h>\n \n #include <asm/elf.h>\n",
    "@@ -19,6 +19,9 @@", 6, 9,
)
output = root / "audit/susfs-4.14-atoll.patch"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(patch)
print("Ported SUSFS patch contexts to Atoll's original vendor-only include blocks.")
print(f"Source patch bytes: {len(patch_path.read_bytes())}; ported bytes: {len(patch.encode())}")
