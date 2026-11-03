#!/usr/bin/env python3
"""Read-only acceptance check for Realme RMX2170 AY Always-On DT2W.

Reads /proc/touchpanel/double_tap_enable and gesture_enable. Optional
--reboot explicitly reboots the phone, then samples DT2W after ADB reconnects
and after Android boot completes. Does not require Root or write to proc.
A successful check cannot prove physical double-tap wake; test manually too.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def adb(serial: str, *args: str, timeout: int = 30) -> str:
    cmd = ["adb", "-s", serial, *args]
    p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=timeout,
                       check=False, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError("ADB command failed: " + " ".join(cmd) + "\n" + p.stdout)
    return p.stdout.strip()


def select_serial(requested: str | None) -> str:
    p = subprocess.run(["adb", "devices"], text=True,
                       capture_output=True, check=True)
    serials = [row.split()[0] for row in p.stdout.splitlines()[1:]
               if len(row.split()) == 2 and row.split()[1] == "device"]
    if requested:
        if requested not in serials:
            raise RuntimeError("Specified ADB device not authorized.")
        return requested
    if len(serials) != 1:
        raise RuntimeError("Connect exactly one authorized device or pass --serial.")
    return serials[0]


def snapshot(serial: str, tag: str) -> dict[str, str]:
    entries: dict[str, str] = {
        "stage": tag,
        "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    for name, command in {
        "dt2w": ("shell", "cat", "/proc/touchpanel/double_tap_enable"),
        "other_gestures": ("shell", "cat", "/proc/touchpanel/gesture_enable"),
        "boot_completed": ("shell", "getprop", "sys.boot_completed"),
        "kernel": ("shell", "uname", "-r"),
        "selinux": ("shell", "getenforce"),
    }.items():
        try:
            entries[name] = adb(serial, *command)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            entries[name] = "Unavailable: " + str(exc)
    return entries


def verify(snap: dict[str, str]) -> tuple[bool, str]:
    if snap["dt2w"] == "1":
        return True, "DT2W vendor proc state enabled"
    if snap["dt2w"] == "0":
        return False, "DT2W disabled; Android/HAL or kernel may have reset the state"
    return False, "DT2W proc state unavailable or unexpected"


def wait_for_android(serial: str, max_seconds: int = 180) -> None:
    start = time.monotonic()
    while time.monotonic() - start < max_seconds:
        try:
            if adb(serial, "shell", "getprop", "sys.boot_completed", timeout=12) == "1":
                return
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
        time.sleep(2)
    raise RuntimeError("Android did not report boot completion within timeout.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--serial", help="ADB serial when multiple phones are connected")
    p.add_argument("--reboot", action="store_true", help="Explicitly reboot the phone to test persistence")
    p.add_argument("--out", type=Path, default=Path("perf-results"))
    args = p.parse_args()
    if not shutil.which("adb"):
        p.error("Install Android Platform Tools first.")
    serial = select_serial(args.serial)
    identity = (
        adb(serial, "shell", "getprop", "ro.product.model") + " " +
        adb(serial, "shell", "getprop", "ro.product.device")
    ).lower()
    if not any(k in identity for k in ("rmx2170", "realme 7 pro", "reatoll")):
        p.error("This acceptance check is only for the Realme 7 Pro / RMX2170.")

    samples = [snapshot(serial, "before-reboot")]
    if args.reboot:
        print("Reboot was explicitly requested; no boot partition modifications.")
        adb(serial, "reboot")
        # Reconnect once ADB is available: it is later than kernel touch probe.
        subprocess.run(["adb", "-s", serial, "wait-for-device"], check=True,
                       timeout=180)
        samples.append(snapshot(serial, "first-adb-online"))
        wait_for_android(serial)
        samples.append(snapshot(serial, "android-boot-completed"))
    else:
        print("Read-only check only. Use --reboot to validate restart persistence.")

    status = [verify(sample) for sample in samples]
    result = {
        "model": identity,
        "status": "PASS" if all(ok for ok, _ in status) else "FAIL",
        "remark": ("This measures readable proc state only. It does not verify "
                   "actual physical double-tap wake, touch IRQ, or standby power."),
        "checks": [
            {**sample, "pass": ok, "note": note}
            for sample, (ok, note) in zip(samples, status)
        ],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    filename = args.out / f"rmx2170-dt2w-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    filename.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    for sample, (ok, note) in zip(samples, status):
        print(f"{sample['stage']}: {'PASS' if ok else 'FAIL'}; "
              f"double_tap_enable={sample['dt2w']!r}, "
              f"other_gestures={sample['other_gestures']!r}; {note}")
    print("Manual validation still required: lock screen, double tap to wake, repeat after reboot.")
    print("Local report:", filename)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print("Check aborted:", exc, file=sys.stderr)
        raise SystemExit(2)
