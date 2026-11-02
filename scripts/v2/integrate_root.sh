#!/usr/bin/env bash
# Experimental V2: official KernelSU-Next Legacy, root baseline only.
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
KS="$ROOT/KernelSU-Next"

test -f "$KS/kernel/Kbuild"
test -f "$KS/kernel/Kconfig"
test -f "$K/arch/arm64/configs/atoll_defconfig"
test "$(git -C "$KS" rev-parse HEAD)" = "$KSU_SHA"
test "$(git -C "$K" rev-parse HEAD)" = "$KERNEL_SHA"

# Insert source-pinned hooks before parallel compilation.
ln -s ../../KernelSU-Next/kernel "$K/drivers/kernelsu"
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$K/drivers/Makefile"
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$K/drivers/Kconfig"

python3 "$ROOT/scripts/v2/manual_hooks.py"
python3 "$ROOT/scripts/prepare_ksu_legacy.py"

# Check actual Kconfig declaration, not generated .config syntax.
grep -Fq 'config KSU' "$KS/kernel/Kconfig"
grep -Fq 'path_umount(struct path' "$K/fs/namespace.c"
grep -Fq 'source "drivers/kernelsu/Kconfig"' "$K/drivers/Kconfig"

git -C "$K" diff --stat > "$ROOT/audit/patch-stat.txt"
echo 'Modern official KSU manual hooks installed. SUSFS intentionally not yet integrated.'
