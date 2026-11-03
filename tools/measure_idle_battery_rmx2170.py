#!/usr/bin/env python3
"""Read-only RMX2170 screen-off battery baseline for AY SmartSleep design.

Use wireless ADB, not a powered USB cable. The computer sleeps between
snapshots; there is NO device-side timer, polling loop, forced-idle command,
CPU/thermal change, Root requirement or persistent background process.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


def adb(serial: str, *args: str, timeout: int = 35) -> str:
    cmd = ["adb", "-s", serial, *args]
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        errors="replace", timeout=timeout, check=False,
    )
    if result.returncode:
        raise RuntimeError("ADB command failed: " + " ".join(cmd) + "\n" + result.stdout)
    return result.stdout.strip()


def battery_data(raw: str) -> dict:
    """Parse public dumpsys battery values without inferring missing fields."""
    def line_value(key: str) -> str | None:
        m = re.search(rf"(?im)^\s*{re.escape(key)}:\s*(.*?)\s*$", raw)
        return m.group(1) if m else None

    def number(key: str) -> int | None:
        v = line_value(key)
        return int(v) if v is not None and re.fullmatch(r"-?\d+", v) else None

    charging = {
        "ac_powered": line_value("AC powered"),
        "usb_powered": line_value("USB powered"),
        "wireless_powered": line_value("Wireless powered"),
        "dock_powered": line_value("Dock powered"),
    }
    connected_power = any(v is not None and v.lower() == "true"
                          for v in charging.values())
    return {
        "level_percent": number("level"),
        "status_android": number("status"),
        "charge_counter_uah": number("Charge counter"),
        "voltage_mv": number("voltage"),
        "temperature_tenths_c": number("temperature"),
        "power_flags": charging,
        "power_connected": connected_power,
        "raw": raw,
    }


def measure_delta(start: dict, end: dict, elapsed_seconds: float) -> dict:
    result: dict = {
        "duration_minutes": round(elapsed_seconds / 60, 2),
        "percent_drop": None,
        "consumption_mah": None,
        "avg_current_ma": None,
    }
    a, b = start["level_percent"], end["level_percent"]
    if a is not None and b is not None:
        result["percent_drop"] = a - b

    c0, c1 = start["charge_counter_uah"], end["charge_counter_uah"]
    if c0 is not None and c1 is not None and c0 > 0 and c1 >= 0 and c0 >= c1 and elapsed_seconds > 0:
        consumed = (c0 - c1) / 1000
        result["consumption_mah"] = round(consumed, 3)
        result["avg_current_ma"] = round(consumed * 3600 / elapsed_seconds, 3)
    return result


def select_serial(optional: str | None) -> str:
    devices = subprocess.run(["adb", "devices"], text=True, capture_output=True, check=True)
    serials = [line.split()[0] for line in devices.stdout.splitlines()[1:]
               if len(line.split()) == 2 and line.split()[1] == "device"]
    if optional:
        if optional not in serials:
            raise RuntimeError("Selected ADB serial is not authorized or connected.")
        return optional
    if len(serials) != 1:
        raise RuntimeError("Expected exactly one authorized device; specify --serial.")
    return serials[0]


def snapshot(serial: str) -> dict:
    fields = {}
    for name, args in {
        "battery": ("shell", "dumpsys", "battery"),
        "power": ("shell", "dumpsys", "power"),
        "deviceidle": ("shell", "dumpsys", "deviceidle"),
        "kernel": ("shell", "uname", "-r"),
    }.items():
        try:
            fields[name] = adb(serial, *args)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            fields[name] = "Unavailable: " + str(exc)
    fields["battery_parsed"] = battery_data(fields["battery"])
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=25, help="Idle duration (10–180 minutes)")
    parser.add_argument("--serial", help="ADB serial for multi-device configurations")
    parser.add_argument("--out", type=Path, default=Path("perf-results"))
    opt = parser.parse_args()
    if not 10 <= opt.minutes <= 180:
        parser.error("Choose 10 to 180 minutes; battery readings are quantized.")
    if not shutil.which("adb"):
        parser.error("Install Android Platform Tools; adb not found.")

    serial = select_serial(opt.serial)
    model = adb(serial, "shell", "getprop", "ro.product.model").lower()
    device = adb(serial, "shell", "getprop", "ro.product.device").lower()
    if not any(v in model + " " + device for v in ["rmx2170", "realme 7 pro", "reatoll"]):
        parser.error("This read-only tool targets the RMX2170 / Realme 7 Pro.")

    print("This measurement requires wireless ADB, no charging, and the screen already off.")
    start = snapshot(serial)
    b0 = start["battery_parsed"]
    if b0["power_connected"]:
        parser.error("Charging/powered device: disconnect USB and use wireless ADB.")
    if b0["level_percent"] is None:
        parser.error("Battery level unavailable; refusing to record ungrounded data.")
    power = start["power"]
    if "mWakefulness=Awake" in power or "Display Power: state=ON" in power:
        parser.error("Turn the display off BEFORE starting this baseline.")
    start_at = dt.datetime.now(dt.timezone.utc)
    t0 = time.monotonic()
    print(f"Collecting two snapshots separated by {opt.minutes} minutes; no device polling.")
    time.sleep(opt.minutes * 60)
    end = snapshot(serial)
    elapsed = time.monotonic() - t0
    end_at = dt.datetime.now(dt.timezone.utc)
    b1 = end["battery_parsed"]
    if b1["power_connected"]:
        print("WARNING: external power detected at end; battery result invalid.")
    delta = measure_delta(b0, b1, elapsed)
    result = {
        "device_model": model,
        "device_code": device,
        "start_utc": start_at.isoformat(),
        "end_utc": end_at.isoformat(),
        "method": "two wireless-ADB snapshots; no device-side polling",
        "valid_unplugged_interval": not b0["power_connected"] and not b1["power_connected"],
        "idle_interval_uninterrupted": "NOT VERIFIED (no continuous screen/event monitor)",
        "note": "Wireless ADB itself can alter idle power. Compare with identical radio conditions.",
        "battery_delta": delta,
        "start": start, "end": end,
    }
    opt.out.mkdir(parents=True, exist_ok=True)
    outfile = opt.out / f"rmx2170-idle-{start_at:%Y%m%d-%H%M%S}.json"
    outfile.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"Battery percentage change: {delta['percent_drop']}")
    if delta["consumption_mah"] is not None:
        print(f"Charge-counter change: {delta['consumption_mah']} mAh; "
              f"average current: {delta['avg_current_ma']} mA")
    else:
        print("No reliable charge-counter delta. Do not infer mAh from percentage alone.")
    print(f"Saved locally: {outfile} (never uploaded)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print("Measurement aborted: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
