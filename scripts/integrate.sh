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
test -f "$KS/kernel/supercalls.c" || { echo "Review legacy KernelSU Next fork layout"; exit 1; }
# Link exact pinned KernelSU Next kernel directory into the stock drivers tree.
ln -s ../../KernelSU-Next/kernel "$K/drivers/kernelsu"
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$K/drivers/Makefile"
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$K/drivers/Kconfig"
# Copy the 4.14 SUSFS support files, then require exact patch application.
cp -a "$SU/kernel_patches/fs/." "$K/fs/"
cp -a "$SU/kernel_patches/include/." "$K/include/"
cd "$K"
git apply --check "$SU/kernel_patches/50_add_susfs_in_kernel-4.14.patch"
git apply "$SU/kernel_patches/50_add_susfs_in_kernel-4.14.patch"
grep -q 'config KSU_SUSFS' "$KS/kernel/Kconfig"
grep -q 'susfs.o' fs/Makefile
grep -q 'source "drivers/kernelsu/Kconfig"' drivers/Kconfig
git diff --stat > "$ROOT/audit/patch-stat.txt"
echo "Integration applied; no vendor drivers edited."
