#!/usr/bin/env bash
# V3 LAB: test SUSFS 1.5.5 + SUSFS-aware legacy fork on the stock Atoll tree.
# This is deliberately NOT the working API-6 KernelSU implementation.
# No boot images, flashable ZIPs or device-facing releases are built.
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
KS="$ROOT/KernelSU-Next"
SU="$ROOT/susfs4ksu"
OUT="$ROOT/audit/v3-susfs-stage.txt"
mkdir -p "$ROOT/audit"

{
  echo "Ahmed Super Kernal A16 — V3 SUSFS 4.14 source integration experiment"
  echo "NOT FOR FLASHING OR DEVICE INSTALLATION."
  echo "Fork is intentionally API-4; this test does NOT replace the working API-6 root kernel."
  echo "Device kernel SHA: $(git -C "$K" rev-parse HEAD)"
  echo "Legacy-SUSFS fork SHA: $(git -C "$KS" rev-parse HEAD)"
  echo "SUSFS patch SHA: $(git -C "$SU" rev-parse HEAD)"
} | tee "$OUT"

test "$(git -C "$K" rev-parse HEAD)" = "$KERNEL_SHA"
test "$(git -C "$KS" rev-parse HEAD)" = "$FORK_SHA"
test "$(git -C "$SU" rev-parse HEAD)" = "$SUSFS_SHA"
test -f "$KS/kernel/Kbuild"
grep -Fq 'config KSU_SUSFS' "$KS/kernel/Kconfig"
test -f "$SU/kernel_patches/50_add_susfs_in_kernel-4.14.patch"
test -f "$SU/kernel_patches/fs/susfs.c"
test -f "$SU/kernel_patches/include/linux/susfs.h"

# Install only SUSFS-specific new files; preserve vendor sources and vendor DTBs.
cp -a "$SU/kernel_patches/fs/." "$K/fs/"
cp -a "$SU/kernel_patches/include/." "$K/include/"
python3 - <<'PY'
from pathlib import Path
p=Path("kernel/fs/susfs.c")
s=p.read_text()
old="spoofed_size: '%u'"
new="spoofed_size: '%lld'"
assert s.count(old)==2, "unexpected SUSFS 4.14 format context"
p.write_text(s.replace(old,new))
PY

python3 "$ROOT/scripts/port_susfs_patch.py"
if ! git -C "$K" apply --check "$ROOT/audit/susfs-4.14-atoll.patch" 2>"$ROOT/audit/v3-patch-errors.txt"; then
    echo "SUSFS patch conflict: source review required. No build or image created." | tee -a "$OUT"
    cat "$ROOT/audit/v3-patch-errors.txt"
    exit 3
fi
git -C "$K" apply "$ROOT/audit/susfs-4.14-atoll.patch"
echo "SUSFS 4.14 kernel-side patch applied to stock source." | tee -a "$OUT"

# Install SUSFS-aware fork in an ephemeral CI checkout only.
ln -s ../../KernelSU-Next/kernel "$K/drivers/kernelsu"
printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$K/drivers/Makefile"
printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$K/drivers/Kconfig"

# The already tested V2 manual hooks, after SUSFS patching to catch conflicts.
python3 "$ROOT/scripts/v2/manual_hooks.py"
python3 "$ROOT/scripts/prepare_ksu_legacy.py"
# SUSFS-aware reference fork requires the per-thread umount-state helpers.
# Port from the related Realme SM7125 source, checking TIF bit ownership.
python3 "$ROOT/scripts/v3/port_umount_flag.py"

# Fail closed if a device driver or DTB source was touched.
if git -C "$K" diff --name-only | grep -E '^(drivers/(input|gpu|media|power|soc|staging|fingerprint|misc)|sound|arch/arm64/boot/dts)/'; then
    echo "Vendor driver/DTB source changed: blocked." | tee -a "$OUT"
    exit 4
fi
# The pinned upstream SUSFS patch contains four whitespace-only warnings in
# comments (confirmed in CI 41654446838). Keep all other diff integrity checks,
# while ignoring only trailing whitespace in these upstream comment lines.
echo "Upstream patch has four known trailing-comment-space warnings; ignore blank-at-eol only." | tee -a "$OUT"
git -C "$K" -c core.whitespace=-blank-at-eol diff --check
git -C "$K" diff --stat > "$ROOT/audit/v3-patch-stat.txt"
echo "All source-side preflight checks passed; compile is permitted." | tee -a "$OUT"
