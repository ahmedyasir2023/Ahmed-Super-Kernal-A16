#!/usr/bin/env python3
"""Fail-closed static contract for V3 SUSFS logging-only experimental kernel.

Run after the source staging script and before compilation. Proves that only
SUSFS logging, not any hiding feature, is enabled. Does not test runtime.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
config = (root / "KernelSU-Next/kernel/Kconfig").read_text()
prctl = (root / "kernel/kernel/sys.c").read_text()
api = (root / "KernelSU-Next/uapi/supercall.h").read_text()
build = (root / "scripts/v3/build_api6_susfs_logging.sh").read_text()

assert "#define KERNEL_SU_UAPI_VERSION 6" in api, "Root API must remain 6"
assert config.count("config KSU_SUSFS_ENABLE_LOG") == 1
assert "    depends on KSU_SUSFS" in config
assert "-e KSU_SUSFS_ENABLE_LOG" in build
assert "CONFIG_KSU_SUSFS_ENABLE_LOG=y" in build

required = (
    "arg2 == CMD_SUSFS_SHOW_VERSION",
    "arg2 == CMD_SUSFS_SHOW_VARIANT",
    "arg2 == CMD_SUSFS_SHOW_ENABLED_FEATURES",
    "arg2 == CMD_SUSFS_ENABLE_LOG",
    "u64 enabled_features = 1ULL << 9",
    "if (current_uid().val != 0)",
    "susfs_set_log(arg3 != 0)",
    "if (arg3 > 1)",
    "if (put_user(result, (int __user *)arg5))",
)
for needle in required:
    assert needle in prctl, f"Missing contract: {needle}"

# All feature commands except logging must remain disabled in this laboratory.
prohibited = (
    "-e KSU_SUSFS_SUS_PATH",
    "-e KSU_SUSFS_SUS_MOUNT",
    "-e KSU_SUSFS_SUS_KSTAT",
    "-e KSU_SUSFS_SPOOF_UNAME",
    "-e KSU_SUSFS_OPEN_REDIRECT",
    "-e KSU_SUSFS_TRY_UMOUNT",
)
for option in prohibited:
    assert option not in build, f"Unreviewed hiding feature enabled: {option}"

allowed_options = (
    "CMD_SUSFS_SHOW_VERSION",
    "CMD_SUSFS_SHOW_VARIANT",
    "CMD_SUSFS_SHOW_ENABLED_FEATURES",
    "CMD_SUSFS_ENABLE_LOG",
)
for option in allowed_options:
    assert prctl.count(option) >= 2, f"Unexpected ABI command references: {option}"
assert "CONFIG_KSU_SUSFS_SUS_PATH" not in config, "Unreviewed SUSFS path hide configured"
assert "CONFIG_KSU_SUSFS_SUS_MOUNT" not in config, "Unreviewed mount hide configured"
assert "CONFIG_KSU_SUSFS_SUS_KSTAT" not in config, "Unreviewed stat hide configured"
print("API-6 logging-only source contract accepted. SUSFS hiding features remain disabled.")
