#!/usr/bin/env bash
set -euo pipefail
ROOT="$PWD"
cd "$ROOT/kernel"
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
export CLANG_TRIPLE=aarch64-linux-gnu-
export CC=clang-18
export LD=ld.lld-18
export AR=llvm-ar-18
export NM=llvm-nm-18
export OBJCOPY=llvm-objcopy-18
export OBJDUMP=llvm-objdump-18
export STRIP=llvm-strip-18
export HOSTCC=clang-18
export HOSTCXX=clang++-18
mkdir -p out
# Command-line tool overrides are mandatory: legacy kernel Makefiles redefine CC.
# Environment-only CC=clang is ignored by the recursive Kbuild invocation.
TOOLCHAIN=(CC=clang-18 HOSTCC=clang-18 HOSTCXX=clang++-18
           LD=ld.lld-18 AR=llvm-ar-18 NM=llvm-nm-18
           OBJCOPY=llvm-objcopy-18 OBJDUMP=llvm-objdump-18 STRIP=llvm-strip-18)
make O=out "${TOOLCHAIN[@]}" atoll_defconfig
scripts/config --file out/.config -e KPROBES -e EXT4_FS -e KSU -e KSU_SUSFS
make O=out "${TOOLCHAIN[@]}" olddefconfig
grep -qx 'CONFIG_KSU=y' out/.config
grep -qx 'CONFIG_KSU_SUSFS=y' out/.config
make O=out "${TOOLCHAIN[@]}" -j"$(nproc)" Image.gz dtbs
