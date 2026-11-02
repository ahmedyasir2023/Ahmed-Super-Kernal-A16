#!/usr/bin/env bash
# Experimental V2: modern official KernelSU-Next Legacy, root baseline only.
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
KS="$ROOT/KernelSU-Next"
test -f "$KS/kernel/Kbuild"
test -f "$KS/kernel/Kconfig"
test -f "$K/arch/arm64/configs/atoll_defconfig"
test "$(git -C "$KS" rev-parse HEAD)" = "$KSU_SHA"
test "$(git -C "$K" rev-parse HEAD)" = "$KERNEL_SHA"
# Apply fully reviewed manual hook call sites before parallel Kbuild starts.
ln -s ../../KernelSU-Next/kernel "$K/drivers/kernelsu"
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$K/drivers/Makefile"
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$K/drivers/Kconfig"
python3 "$ROOT/scripts/v2/manual_hooks.py"
# Prevent 4.14 Kbuild namespace/seccomp compatibility from modifying headers
# mid-way through a parallel build. Preserve stock driver source.
python3 "$ROOT/scripts/prepare_ksu_legacy.py"
# Namespace helper may be already present due to earlier prep.
grep -q 'int path_umount(struct path \*path, int flags)' "$K/fs/namespace.c"
grep -Eq '^[[:space:]]*config KSU
git -C "$K" diff --stat > "$ROOT/audit/patch-stat.txt"
echo "Modern official KSU manual hooks installed. SUSFS NOT enabled in this root-only baseline."
 "$KS/kernel/Kconfig"
git -C "$K" diff --stat > "$ROOT/audit/patch-stat.txt"
echo "Modern official KSU manual hooks installed. SUSFS NOT enabled in this root-only baseline."
