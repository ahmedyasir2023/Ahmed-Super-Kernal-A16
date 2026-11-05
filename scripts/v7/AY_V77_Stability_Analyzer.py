#!/usr/bin/env python3
"""Analyze AY V7.7 on-device memory snapshots, without device access."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

SAMPLE_RE = re.compile(r"^=== SAMPLE t=(\d+) ===$")
PSI_RE = re.compile(r"^PSI (memory|cpu|io) (some|full) (.*)$")
FIELD_RE = re.compile(r"([a-z0-9]+)=([0-9.]+)")


def parse(raw: str) -> list[dict]:
    records = []
    current = None
    for line in raw.splitlines():
        match = SAMPLE_RE.match(line)
        if match:
            if current is not None:
                raise ValueError("Nested snapshot marker")
            current = {"t": int(match.group(1)), "vm": {}, "mem": {}, "psi": {}, "kswapd": {}}
            continue
        if line == "=== END SAMPLE ===":
            if current is None:
                raise ValueError("End marker without sample")
            records.append(current)
            current = None
            continue
        if current is None:
            continue
        if line.startswith("TIME_EPOCH "):
            try:
                current["epoch"] = int(line.split()[1])
            except (ValueError, IndexError):
                pass
        elif line.startswith("KSWAPD "):
            parts = line.split()
            if len(parts) == 5:
                try:
                    current["kswapd"][parts[1]] = int(parts[3].split("=", 1)[1]) + int(parts[4].split("=", 1)[1])
                except (ValueError, IndexError):
                    pass
        elif line.startswith("VM "):
            parts = line.split()
            if len(parts) == 3:
                try:
                    current["vm"][parts[1]] = int(parts[2])
                except ValueError:
                    pass
        elif line.startswith("MEM "):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    current["mem"][parts[1].rstrip(":")] = int(parts[2])
                except ValueError:
                    pass
        else:
            m = PSI_RE.match(line)
            if m:
                fields = {k: float(v) for k, v in FIELD_RE.findall(m.group(3))}
                current["psi"][f"{m.group(1)}_{m.group(2)}"] = fields
    if current is not None:
        raise ValueError("Incomplete snapshot")
    if len(records) < 2:
        raise ValueError("Need at least two snapshots")
    if any(b["t"] <= a["t"] for a, b in zip(records, records[1:])):
        raise ValueError("Sample times must increase")
    return records


def delta_sum(a: dict, b: dict, prefixes: tuple[str, ...]) -> int | None:
    keys = {k for k in a if any(k == p or k.startswith(p + "_") for p in prefixes)}
    keys &= b.keys()
    if not keys:
        return None
    diffs = [b[k] - a[k] for k in keys]
    if any(d < 0 for d in diffs):
        return None
    return sum(diffs)


def analyze(records: list[dict]) -> dict:
    a, b = records[0], records[-1]
    nominal_seconds = b["t"] - a["t"]
    seconds = (b["epoch"] - a["epoch"]) if "epoch" in a and "epoch" in b else nominal_seconds
    if seconds <= 0:
        raise ValueError("Invalid interval")
    vm_a, vm_b = a["vm"], b["vm"]
    scans = delta_sum(vm_a, vm_b, ("pgscan_kswapd",))
    stolen = delta_sum(vm_a, vm_b, ("pgsteal_kswapd",))
    report = {
        "duration_seconds": seconds,
        "duration_seconds_nominal": nominal_seconds,
        "samples": len(records),
        "kswapd_cpu_ticks_all_workers": sum(b["kswapd"][pid] - ticks for pid, ticks in a["kswapd"].items() if pid in b["kswapd"] and b["kswapd"][pid] >= ticks) if a["kswapd"] else None,
        "kernel_reclaim_scanned_pages": scans,
        "kernel_reclaim_stolen_pages": stolen,
        "kswapd_reclaim_efficiency_percent": round(100 * stolen / scans, 2) if scans and stolen is not None else None,
        "swap_in_pages": delta_sum(vm_a, vm_b, ("pswpin",)),
        "swap_out_pages": delta_sum(vm_a, vm_b, ("pswpout",)),
        "direct_scan_pages": delta_sum(vm_a, vm_b, ("pgscan_direct",)),
        "direct_stolen_pages": delta_sum(vm_a, vm_b, ("pgsteal_direct",)),
        "available_memory_kib_start": a["mem"].get("MemAvailable"),
        "available_memory_kib_end": b["mem"].get("MemAvailable"),
        "psi": {},
        "note": "Counters and PSI support triage; a short observation cannot establish long-term cause or battery performance.",
    }
    for kind in ("memory_some", "memory_full", "io_some", "io_full", "cpu_some"):
        start = a["psi"].get(kind)
        end = b["psi"].get(kind)
        if not start or not end:
            continue
        rec = {"avg10_last_percent": end.get("avg10")}
        x, y = start.get("total"), end.get("total")
        if x is not None and y is not None and y >= x:
            rec["total_stall_interval_percent"] = round((y - x) / (seconds * 10000), 2)
        report["psi"][kind] = rec
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    d = analyze(parse(args.report.read_text(errors="replace")))
    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        print("AY V7.7 — Memory analysis (read-only input)")
        print(f"Interval: {d['duration_seconds']} s, samples: {d['samples']}")
        for k in ("kswapd_cpu_ticks_all_workers", "kernel_reclaim_scanned_pages", "kernel_reclaim_stolen_pages", "kswapd_reclaim_efficiency_percent", "swap_in_pages", "swap_out_pages", "direct_scan_pages", "available_memory_kib_end"):
            print(f"{k}: {d[k] if d[k] is not None else 'not available'}")
        for kind, v in d["psi"].items():
            print(f"PSI {kind}: avg10={v.get('avg10_last_percent')}%, interval={v.get('total_stall_interval_percent')}%")
        print(d["note"])


if __name__ == "__main__":
    main()
