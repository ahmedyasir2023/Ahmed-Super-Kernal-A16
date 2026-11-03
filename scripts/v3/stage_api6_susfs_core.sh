#!/usr/bin/env bash
# V3 proof-of-compile: retain known-working KernelSU Next API 6.
# Integrate only SUSFS 4.14 filesystem core, not root hiding or userspace commands.
# Explicitly NEVER generate flashable Boot images or recovery ZIPs from this source.
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
KS="$ROOT/KernelSU-Next"
SU="$ROOT/susfs4ksu"
mkdir -p "$ROOT/audit"

test "$(git -C "$K" rev-parse HEAD)" = "$KERNEL_SHA"
test "$(git -C "$KS" rev-parse HEAD)" = "$KSU_SHA"
test "$(git -C "$SU" rev-parse HEAD)" = "$SUSFS_SHA"
test -f "$K/arch/arm64/configs/atoll_defconfig"
grep -Fq '#define KERNEL_SU_UAPI_VERSION 6' "$KS/uapi/supercall.h"
grep -Fq '#define SUSFS_VERSION "v1.5.5"' "$SU/kernel_patches/include/linux/susfs.h"
if grep -Fq 'config KSU_SUSFS' "$KS/kernel/Kconfig"; then
  echo "New upstream SUSFS Kconfig needs review; aborting"
  exit 1
fi
# SUSFS kernel-side patch from the pinned version. Do not include the old
# KernelSU-side bridge patch, which is incompatible with current API 6.
cp -a "$SU/kernel_patches/fs/." "$K/fs/"
cp -a "$SU/kernel_patches/include/." "$K/include/"
python3 - <<'PY'
from pathlib import Path
p = Path("kernel/fs/susfs.c")
s = p.read_text()
old = "spoofed_size: '%u'"
assert s.count(old) == 2
p.write_text(s.replace(old, "spoofed_size: '%lld'"))
PY
python3 "$ROOT/scripts/port_susfs_patch.py"
git -C "$K" apply --check "$ROOT/audit/susfs-4.14-atoll.patch"
git -C "$K" apply "$ROOT/audit/susfs-4.14-atoll.patch"

# Apply the *known-working* API-6 Manual Hooks to the patched 4.14 kernel.
bash "$ROOT/scripts/v2/integrate_root.sh"
# Read-only metadata bridge only (SUSFS SHOW_VERSION + zero-feature report).
python3 "$ROOT/scripts/v3/patch_api6_susfs_logging.py"

# Enable only the filesystem-core object and its initialization in the build
# probe. No SUSFS command bridge or functionality is claimed or published.
python3 - <<'PY'
from pathlib import Path

cfg = Path("KernelSU-Next/kernel/Kconfig")
s = cfg.read_text()
assert s.count('config KSU\n') == 1
assert 'config KSU_SUSFS\n' not in s
s += """
menu "SUSFS 4.14 API6 kernel-core compile probe (NOT FUNCTIONAL)"

config KSU_SUSFS
    bool "Build SUSFS 1.5.5 filesystem core without userspace ABI (CI ONLY)"
    depends on KSU
    default n
    help
      Compile-time validation only. This build has no SUSFS supercall bridge
      and must not be used as a root-hiding release.

endmenu
"""
cfg.write_text(s)

core = Path("KernelSU-Next/kernel/core/init.c")
s = core.read_text()
inc = '#include "ksu.h"\n'
assert s.count(inc) == 1
s = s.replace(inc, inc + '#ifdef CONFIG_KSU_SUSFS\n#include <linux/susfs.h>\n#endif\n', 1)
anchor = '\tksu_feature_init();\n'
assert s.count(anchor) == 1
s = s.replace(anchor,
    '#ifdef CONFIG_KSU_SUSFS\n\tsusfs_init();\n#endif\n' + anchor, 1)
core.write_text(s)

# Provenance and intentionally narrow runtime gate.
assert '#define KERNEL_SU_UAPI_VERSION 6' in Path("KernelSU-Next/uapi/supercall.h").read_text()
assert 'config KSU_SUSFS\n' in cfg.read_text()
assert 'susfs_init();' in core.read_text()
PY

# Do not silently modify vendor hardware drivers, DTBs or modem sources.
if git -C "$K" diff --name-only | grep -E '^(drivers/(input|gpu|media|power|soc|staging|fingerprint|misc)|sound|arch/arm64/boot/dts)/'; then
  echo "VENDOR DRIVER MODIFICATION — refusing build"
  exit 2
fi
git -C "$K" -c core.whitespace=-blank-at-eol diff --check
{
 echo "V3 API6 SUSFS CORE-ONLY COMPILE PROBE — NEVER FLASH"
 echo "Kernel: $(git -C "$K" rev-parse HEAD)"
 echo "Official KernelSU API6: $(git -C "$KS" rev-parse HEAD)"
 echo "SUSFS: $(git -C "$SU" rev-parse HEAD)"
 echo "No SUSFS supercall handler or user-space ABI: NOT FUNCTIONAL AS HIDING"
 echo "No device flash, no partition change."
} | tee "$ROOT/audit/v3-api6-core-probe.txt"
