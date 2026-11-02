#!/usr/bin/env bash
set -euo pipefail
ROOT="$PWD"
cd "$ROOT/kernel"
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
export CLANG_TRIPLE=aarch64-linux-gnu-
: "${CLANG_BIN:?Pinned Android Clang 21 toolchain was not installed}"
test -x "$CLANG_BIN/clang"
test -x "$CLANG_BIN/ld.lld"
export PATH="$CLANG_BIN:$PATH"
export CC="$CLANG_BIN/clang"
export LD="$CLANG_BIN/ld.lld"
export AR="$CLANG_BIN/llvm-ar"
export NM="$CLANG_BIN/llvm-nm"
export OBJCOPY="$CLANG_BIN/llvm-objcopy"
export OBJDUMP="$CLANG_BIN/llvm-objdump"
export STRIP="$CLANG_BIN/llvm-strip"
export HOSTCC="$CLANG_BIN/clang"
export HOSTCXX="$CLANG_BIN/clang++"
export HOSTLD="$CLANG_BIN/ld.lld"
mkdir -p out
TOOLCHAIN=(
  "CC=$CLANG_BIN/clang"
  "HOSTCC=$CLANG_BIN/clang"
  "HOSTCXX=$CLANG_BIN/clang++"
  "HOSTLD=$CLANG_BIN/ld.lld"
  "LD=$CLANG_BIN/ld.lld"
  "AR=$CLANG_BIN/llvm-ar"
  "NM=$CLANG_BIN/llvm-nm"
  "OBJCOPY=$CLANG_BIN/llvm-objcopy"
  "OBJDUMP=$CLANG_BIN/llvm-objdump"
  "STRIP=$CLANG_BIN/llvm-strip"
)
"$CLANG_BIN/clang" --version
make O=out "${TOOLCHAIN[@]}" atoll_defconfig
scripts/config --file out/.config -e KPROBES -e EXT4_FS -e KSU -e KSU_SUSFS
make O=out "${TOOLCHAIN[@]}" olddefconfig
grep -qx 'CONFIG_KSU=y' out/.config
grep -qx 'CONFIG_KSU_SUSFS=y' out/.config
make O=out "${TOOLCHAIN[@]}" -j"$(nproc)" Image.gz dtbs
