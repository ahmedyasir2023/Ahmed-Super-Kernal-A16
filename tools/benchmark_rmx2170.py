#!/usr/bin/env python3
"""Read-only performance baseline for Realme 7 Pro / Evolution X Android 16.

Requires Android Platform Tools (adb) and USB debugging. No Root required.
The sole temporary action is opening Android Settings for repeated launch timing.
No kernel settings, CPU governor, SELinux, ZRAM or files on the phone are modified.
Outputs remain on this computer; nothing is uploaded.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


def adb(args: list[str], serial: str | None, timeout: int = 30) -> str:
    command = ["adb"]
    if serial:
        command.extend(["-s", serial])
    command += args
    result = subprocess.run(command, check=False, text=True,
                            encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command}\n{result.stdout}")
    return result.stdout.strip()


def snapshot(serial: str) -> dict[str, str]:
    commands = {
        "model": ["shell", "getprop", "ro.product.model"],
        "device": ["shell", "getprop", "ro.product.device"],
        "fingerprint": ["shell", "getprop", "ro.build.fingerprint"],
        "kernel": ["shell", "uname", "-r"],
        "selinux": ["shell", "getenforce"],
        "meminfo": ["shell", "cat", "/proc/meminfo"],
        "swaps": ["shell", "cat", "/proc/swaps"],
        "memory_pressure": ["shell", "cat", "/proc/pressure/memory"],
        "zram_mm_stat": ["shell", "cat", "/sys/block/zram0/mm_stat"],
        "zram_compression": ["shell", "cat", "/sys/block/zram0/comp_algorithm"],
        "battery": ["shell", "dumpsys", "battery"],
        "thermal": ["shell", "dumpsys", "thermalservice"],
    }
    result = {}
    for name, argv in commands.items():
        try:
            result[name] = adb(argv, serial, timeout=35)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            result[name] = f"Unavailable: {exc}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="ADB device serial when multiple devices connected")
    parser.add_argument("--runs", type=int, default=7, help="Number of launches (3 to 30)")
    parser.add_argument("--cold", action="store_true",
                        help="Force-stop Android Settings before each launch")
    parser.add_argument("--out", type=Path, default=Path("perf-results"))
    opt = parser.parse_args()
    if not 3 <= opt.runs <= 30:
        parser.error("--runs must be between 3 and 30")
    if not shutil.which("adb"):
        parser.error("adb not found: install official Android Platform Tools first")

    devices = adb(["devices"], None)
    active = [line.split()[0] for line in devices.splitlines()[1:]
              if len(line.split()) >= 2 and line.split()[1] == "device"]
    if opt.serial:
        if opt.serial not in active:
            parser.error("Selected serial not shown as authorized by adb devices")
        serial = opt.serial
    elif len(active) == 1:
        serial = active[0]
    else:
        parser.error(f"Expected one authorized device, found {len(active)}; use --serial")

    before = snapshot(serial)
    identifier = (before.get("model", "") + " " + before.get("device", "") +
                  " " + before.get("fingerprint", "")).lower()
    if not any(x in identifier for x in ("rmx2170", "realme 7 pro", "reatoll")):
        parser.error("Device does not identify as Realme 7 Pro / RMX2170; refusing benchmark")

    rows: list[dict] = []
    print("Launching Android Settings for timing; leave the screen unlocked.")
    for number in range(1, opt.runs + 1):
        try:
            if opt.cold:
                adb(["shell", "am", "force-stop", "com.android.settings"], serial)
            output = adb(["shell", "am", "start", "-W", "-n",
                          "com.android.settings/.Settings"], serial, timeout=50)
            raw = dict((k.strip(), v.strip()) for k, v in
                       re.findall(r"^([A-Za-z]+Time):\s*([0-9]+)\s*$", output, re.M))
            if "TotalTime" not in raw or "WaitTime" not in raw:
                raise RuntimeError(f"No usable ActivityManager timing:\n{output}")
            row = {"run": number, "cold": opt.cold,
                   "ThisTime_ms": int(raw["ThisTime"]) if "ThisTime" in raw else None,
                   "TotalTime_ms": int(raw["TotalTime"]),
                   "WaitTime_ms": int(raw["WaitTime"])}
            rows.append(row)
            print(f"{number}/{opt.runs}: TotalTime={row['TotalTime_ms']} ms")
            adb(["shell", "input", "keyevent", "KEYCODE_HOME"], serial)
            time.sleep(1.5)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print(f"Trial {number} failed: {exc}", file=sys.stderr)
            return 2

    after = snapshot(serial)
    times = [v["TotalTime_ms"] for v in rows]
    report = {
        "device": serial,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "method": "adb shell am start -W Android Settings",
        "cold_launch": opt.cold,
        "runs": rows,
        "summary": {
            "median_ms": statistics.median(times),
            "mean_ms": round(statistics.mean(times), 1),
            "minimum_ms": min(times), "maximum_ms": max(times),
            "p95_nearest_rank_ms": sorted(times)[max(0, (95 * len(times) + 99)//100 - 1)]
        },
        "before": before, "after": after
    }
    opt.out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = opt.out / f"rmx2170-baseline-{stamp}.json"
    csv_path = opt.out / f"rmx2170-launches-{stamp}.csv"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Median launch: {report['summary']['median_ms']} ms")
    print(f"Results saved locally: {json_path} and {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
