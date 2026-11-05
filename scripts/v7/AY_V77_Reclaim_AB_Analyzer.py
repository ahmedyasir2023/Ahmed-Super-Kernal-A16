#!/usr/bin/env python3
"""Analyze an explicit V7.7 reclaim A/B run, never change device state.

Usage:
    python3 scripts/v7/AY_V77_Reclaim_AB_Analyzer.py AY_V77_Reclaim_AB_Result.txt

This report is an observational 10s+10s comparison, NOT proof that
either policy will improve battery life, heat or long-run latency.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

REQUIRED = (
    "BASELINE START / mode=0",
    "BASELINE END / mode=0",
    "EXPERIMENT START / mode=1",
    "EXPERIMENT END / mode=1",
)
HEADER = re.compile(r"^=== (.+) ===$")
PSI = re.compile(r"^MEM_PSI (some|full) .*?\btotal=(\d+)\b$")
VM = re.compile(r"^VM (\w+) (\d+)$")
CPU = re.compile(r"^KSWAPD (\d+) cpu_ticks=(\d+)$")
RECLAIM = re.compile(r"^(\w+)=(\d+)$")


def parse(text: str) -> tuple[dict, bool]:
    """Four snapshots in sequence; restore state must be separately verified."""
    samples: dict[str, dict] = {}
    current_name = None
    for line in text.splitlines():
        h = HEADER.fullmatch(line)
        if h:
            current_name = h.group(1) if h.group(1) in REQUIRED else None
            if current_name:
                if current_name in samples:
                    raise ValueError("Duplicate A/B snapshot: "+current_name)
                samples[current_name] = {"psi": {}, "vm": {}, "cpu": {}, "status": {}}
            continue
        if current_name is None:
            continue
        s = samples[current_name]
        if line.startswith("TIME_EPOCH "):
            try:
                s["epoch"] = int(line.partition(" ")[2])
            except ValueError:
                raise ValueError("Invalid TIME_EPOCH")
            continue
        m = PSI.fullmatch(line)
        if m:
            s["psi"][m.group(1)] = int(m.group(2))
            continue
        m = VM.fullmatch(line)
        if m:
            s["vm"][m.group(1)] = int(m.group(2))
            continue
        m = CPU.fullmatch(line)
        if m:
            s["cpu"][m.group(1)] = int(m.group(2))
            continue
        m = RECLAIM.fullmatch(line)
        if m:
            s["status"][m.group(1)] = int(m.group(2))
    if list(samples) != list(REQUIRED):
        raise ValueError("Incomplete or unordered A/B observations")
    for key, s in samples.items():
        if not all(k in s for k in ("epoch", "psi", "vm", "cpu")):
            raise ValueError(f"Incomplete sample: {key}")
        expected = 0 if "BASELINE" in key else 1
        if s["status"].get("reclaim_progress_enabled") != expected:
            raise ValueError(f"Kernel mode mismatch at {key}")
        if "full" not in s["psi"] or "some" not in s["psi"]:
            raise ValueError(f"Missing memory PSI at {key}")
        if not s["cpu"]:
            raise ValueError(f"Missing kswapd workers at {key}")
    # Shell trap's read-back confirmation MUST be present. It could fail if
    # Termux is SIGKILLed, the phone shuts down, or sysfs rejects the write.
    restored = "RESTORED reclaim_progress_enabled=0" in text
    return samples, restored


def interval(a: dict, b: dict) -> dict:
    seconds = b["epoch"]-a["epoch"]
    if seconds < 5 or seconds > 60:
        raise ValueError("Invalid test interval; expected about ten seconds")
    result: dict = {"seconds": seconds}
    for kind in ("some", "full"):
        delta = b["psi"][kind] - a["psi"][kind]
        if delta < 0 or delta > seconds*1_000_000*1.02:
            raise ValueError("Impossible PSI delta or counter reset")
        result[f"psi_{kind}_stalled_percent"] = round(100*delta/(seconds*1_000_000),2)

    a_workers, b_workers = a["cpu"], b["cpu"]
    if set(a_workers) != set(b_workers):
        raise ValueError("kswapd worker set changed during test")
    cpu_delta = [b_workers[k]-v for k,v in a_workers.items()]
    if any(d<0 for d in cpu_delta):
        raise ValueError("kswapd ticks reset during test")
    result["kswapd_cpu_ticks_per_second_total"] = round(sum(cpu_delta)/seconds,2)
    result["workers"] = len(cpu_delta)
    for key in ("pgscan_kswapd","pgsteal_kswapd","pswpin","pswpout","workingset_refault"):
        if key in a["vm"] and key in b["vm"]:
            diff=b["vm"][key]-a["vm"][key]
            if diff<0:
                raise ValueError("VM counter reset: "+key)
            result[key+"_per_second"] = round(diff/seconds,2)
        else:
            result[key+"_per_second"] = None
    scanned=result["pgscan_kswapd_per_second"]
    stolen=result["pgsteal_kswapd_per_second"]
    result["kswapd_reclaim_efficiency_percent"] = (round(100*stolen/scanned,2)
         if scanned and stolen is not None else None)
    result["balance_calls_delta"] = (
        b["status"]["balance_calls"]-a["status"]["balance_calls"]
        if "balance_calls" in a["status"] and "balance_calls" in b["status"] else None)
    return result


def analyze(text: str) -> dict:
    samples,restored=parse(text)
    base=interval(samples[REQUIRED[0]],samples[REQUIRED[1]])
    experiment=interval(samples[REQUIRED[2]],samples[REQUIRED[3]])
    full_delta=round(experiment["psi_full_stalled_percent"]-base["psi_full_stalled_percent"],2)
    cpu_delta=round(experiment["kswapd_cpu_ticks_per_second_total"]-base["kswapd_cpu_ticks_per_second_total"],2)
    if not restored:
        decision="NO_RESTORE_CONFIRMATION: inspect kernel mode now; do not run another trial"
    elif full_delta <= -10 and cpu_delta <= -10:
        decision="PROMISING_SHORT_SAMPLE_ONLY: repeat independently; never auto-enable without further checks"
    elif full_delta >= 10 or cpu_delta >= 10:
        decision="WORSE_SHORT_SAMPLE: keep kernel default 0"
    else:
        decision="INCONCLUSIVE_SHORT_SAMPLE: keep kernel default 0"
    return {
        "restore_confirmed": restored,
        "baseline_mode_0": base,
        "experiment_mode_1": experiment,
        "changes_experiment_minus_baseline": {
            "psi_full_percentage_points": full_delta,
            "kswapd_cpu_ticks_per_second_total": cpu_delta,
        },
        "decision": decision,
        "caution": "Sequential ten-second A/B observations are confounded by time and workload. CPU ticks are not CPU percent without the device USER_HZ. A returned sysfs readback does not prove changes to energy consumption or device stability.",
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    print(json.dumps(analyze(args.report.read_text(errors="replace")),indent=2))


if __name__=="__main__":
    main()
