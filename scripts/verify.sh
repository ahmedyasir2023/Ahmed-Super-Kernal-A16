#!/usr/bin/env bash
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
C="$K/out/.config"
IMG="$K/out/arch/arm64/boot/Image.gz"
mkdir -p "$ROOT/audit"
test -s "$IMG"
gzip -t "$IMG"
test "$(sed -n '2s/[^0-9]//gp' "$K/Makefile")" = "4"
grep -qx 'PATCHLEVEL = 14' "$K/Makefile"
grep -qx 'SUBLEVEL = 336' "$K/Makefile"
grep -qx 'CONFIG_KSU=y' "$C"
grep -qx 'CONFIG_KSU_SUSFS=y' "$C"
grep -q '^CONFIG_OPPO_FINGERPRINT_GOODIX_OPTICAL=y' "$C"
test -s "$K/out/vmlinux"
# SUSFS must be built, not merely configured.
test -s "$K/out/fs/susfs.o"
test -s "$K/out/drivers/kernelsu/built-in.o"
find "$K/out/arch/arm64/boot/dts" -type f -name '*.dtb' -size +0c | grep -q .
# Never modify any stock vendor hardware driver paths.
if git -C "$K" diff --name-only | grep -E '^(drivers/(input|gpu|media|power|soc|staging|fingerprint|misc)|sound|arch/arm64/boot/dts)/'; then
  echo "Unexpected change in device driver or DTS source — blocking"
  exit 1
fi
cp "$C" "$ROOT/audit/config.txt"
{
 echo "Ahmed Super Kernal A16 — NON-FLASHABLE CI audit"
 echo "Kernel revision: $(git -C "$K" rev-parse HEAD)"
 echo "KernelSU revision: $(git -C "$ROOT/KernelSU-Next" rev-parse HEAD)"
 echo "SUSFS revision: $(git -C "$ROOT/susfs4ksu" rev-parse HEAD)"
 echo "Kernel release: 4.14.336"
 echo "Image.gz size: $(stat -c %s "$IMG") bytes"
 echo "SHA256: $(sha256sum "$IMG")"
 echo "DTBs: $(find "$K/out/arch/arm64/boot/dts" -name '*.dtb' | wc -l)"
 echo "KernelSU Next configured: yes"
 echo "SUSFS configured and compiled: yes"
 echo "Boot image repack: NOT DONE"
 echo "ROM boot-chain verification: NOT DONE"
 echo "Flashable archive: NOT CREATED"
 echo "Device boot/hardware tests: NOT DONE"
} | tee "$ROOT/audit/build-report.txt"
