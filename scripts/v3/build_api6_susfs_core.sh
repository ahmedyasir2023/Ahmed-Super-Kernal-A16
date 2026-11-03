#!/usr/bin/env bash
set -euo pipefail
ROOT="$PWD"
K="$ROOT/kernel"
: "${CLANG_BIN:?Missing verified Android Clang 21 toolchain}"
for tool in clang clang++ ld.lld llvm-ar llvm-nm llvm-objcopy llvm-objdump llvm-strip; do
  test -x "$CLANG_BIN/$tool" || { echo "Compiler tool absent: $tool"; exit 1; }
done
cd "$K"
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
export CLANG_TRIPLE=aarch64-linux-gnu-
export PATH="$CLANG_BIN:$PATH"
TOOLS=(
 "CC=$CLANG_BIN/clang" "HOSTCC=$CLANG_BIN/clang"
 "HOSTCXX=$CLANG_BIN/clang++" "HOSTLD=$CLANG_BIN/ld.lld"
 "LD=$CLANG_BIN/ld.lld" "AR=$CLANG_BIN/llvm-ar"
 "NM=$CLANG_BIN/llvm-nm" "OBJCOPY=$CLANG_BIN/llvm-objcopy"
 "OBJDUMP=$CLANG_BIN/llvm-objdump" "STRIP=$CLANG_BIN/llvm-strip"
)
mkdir -p out
make O=out "${TOOLS[@]}" atoll_defconfig
scripts/config --file out/.config -e KSU -e KSU_MANUAL_HOOK -d KSU_KPROBES_HOOK -d KSU_SYSCALL_TABLE_HOOK -e EXT4_FS -e KSU_SUSFS
make O=out "${TOOLS[@]}" olddefconfig
grep -qx 'CONFIG_KSU=y' out/.config
grep -qx 'CONFIG_KSU_MANUAL_HOOK=y' out/.config
grep -qx 'CONFIG_KSU_SUSFS=y' out/.config
! grep -qx 'CONFIG_KSU_KPROBES_HOOK=y' out/.config
! grep -qx 'CONFIG_KSU_SYSCALL_TABLE_HOOK=y' out/.config
echo "V3 API-6 SUSFS core compile probe: SUSFS FEATURE ABI NOT IMPLEMENTED — NEVER FLASH"
make O=out "${TOOLS[@]}" -j"$(nproc)" Image.gz dtbs
