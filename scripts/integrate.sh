#!/usr/bin/env bash
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
KS="$ROOT/KernelSU-Next"
SU="$ROOT/susfs4ksu"
mkdir -p "$ROOT/audit"
test -d "$K/arch/arm64" && test -f "$KS/kernel/Kconfig"
test -f "$SU/kernel_patches/50_add_susfs_in_kernel-4.14.patch"
test -f "$SU/kernel_patches/fs/susfs.c"
test -f "$KS/kernel/ksu.c" || { echo "Review legacy KernelSU Next fork layout"; exit 1; }
# KernelSU-Next legacy SUSFS Makefile injects get_cred_rcu into cred.h during Kbuild.
# This Atoll kernel uses atomic_long_t for cred.usage, not atomic_t.
# Fix only the pinned external KernelSU fork in the ephemeral build checkout.
python3 - <<'PY'
from pathlib import Path
p = Path("KernelSU-Next/kernel/Makefile")
s = p.read_text()
old = "atomic_inc_not_zero(&nonconst_cred->usage)"
new = "atomic_long_inc_not_zero(&nonconst_cred->usage)"
assert s.count(old) == 1, "KernelSU Makefile changed; review needed"
p.write_text(s.replace(old, new))
PY
# Link exact pinned KernelSU Next kernel directory into the stock drivers tree.
ln -s ../../KernelSU-Next/kernel "$K/drivers/kernelsu"
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$K/drivers/Makefile"
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$K/drivers/Kconfig"
# Copy the 4.14 SUSFS support files, then require exact patch application.
cp -a "$SU/kernel_patches/fs/." "$K/fs/"
cp -a "$SU/kernel_patches/include/." "$K/include/"
# SUSFS legacy 4.14 has a signed 64-bit spoofed_size printed with %u.
# Correct the format in the copied SUSFS file without editing vendor sources.
python3 - <<'PY'
from pathlib import Path
p = Path("kernel/fs/susfs.c")
s = p.read_text()
old = "spoofed_size: '%u'"
new = "spoofed_size: '%lld'"
assert s.count(old) == 2, "unexpected legacy SUSFS source, needs review"
p.write_text(s.replace(old, new))
PY
cd "$K"
python3 "$ROOT/scripts/port_susfs_patch.py"
git apply --check "$ROOT/audit/susfs-4.14-atoll.patch"
git apply "$ROOT/audit/susfs-4.14-atoll.patch"
grep -q 'config KSU_SUSFS' "$KS/kernel/Kconfig"
grep -q 'susfs.o' fs/Makefile
grep -q 'source "drivers/kernelsu/Kconfig"' drivers/Kconfig
git diff --stat > "$ROOT/audit/patch-stat.txt"
echo "Integration applied; no vendor drivers edited."
