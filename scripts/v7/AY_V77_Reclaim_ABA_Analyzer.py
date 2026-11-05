#!/usr/bin/env python3
"""Offline analysis for the bounded AY V7.7 A-B-A reclaim reversal trial.

This script never changes the device or assumes hardware success.
"""
from pathlib import Path
import argparse
import json
import re
from AY_V77_Reclaim_AB_Analyzer import interval

STAGES = ("A1 START / mode=0", "A1 END / mode=0",
          "B START / mode=1", "B END / mode=1",
          "A2 START / mode=0", "A2 END / mode=0")
HEAD = re.compile(r"^=== (.+) ===$")
PSI = re.compile(r"^MEM_PSI (some|full) .*total=(\d+)$")
VM = re.compile(r"^VM (\w+) (\d+)$")
WORKER = re.compile(r"^KSWAPD (\d+) cpu_ticks=(\d+)$")
STATUS = re.compile(r"^(\w+)=(\d+)$")

def read(text: str):
    samples = {}
    active = None
    for line in text.splitlines():
        m=HEAD.fullmatch(line)
        if m:
            active=m[1] if m[1] in STAGES else None
            if active:
                if active in samples:
                    raise ValueError("Duplicate sample "+active)
                samples[active]={"psi":{},"vm":{},"cpu":{},"status":{}}
            continue
        if active is None:
            continue
        d=samples[active]
        if line.startswith("TIME_EPOCH "):
            d["epoch"]=int(line.split()[1])
            continue
        m=PSI.fullmatch(line)
        if m: d["psi"][m[1]]=int(m[2]); continue
        m=VM.fullmatch(line)
        if m: d["vm"][m[1]]=int(m[2]); continue
        m=WORKER.fullmatch(line)
        if m: d["cpu"][m[1]]=int(m[2]); continue
        m=STATUS.fullmatch(line)
        if m: d["status"][m[1]]=int(m[2])
    if list(samples)!=list(STAGES):
        raise ValueError("Missing or out-of-order A-B-A windows")
    for name,record in samples.items():
        want=1 if name.startswith("B ") else 0
        if record["status"].get("reclaim_progress_enabled")!=want:
            raise ValueError("Mode readback mismatch: "+name)
        if "epoch" not in record or "full" not in record["psi"] or "some" not in record["psi"] or not record["cpu"]:
            raise ValueError("Incomplete snapshot: "+name)
    return samples

def analyze(text: str)->dict:
    samples=read(text)
    arms={}
    for label in ("A1","B","A2"):
        arms[label]=interval(samples[f"{label} START / mode={'1' if label=='B' else '0'}"],
                             samples[f"{label} END / mode={'1' if label=='B' else '0'}"])
    restored="RESTORED reclaim_progress_enabled=0" in text
    baseline_high=min(arms["A1"]["psi_full_stalled_percent"],
                      arms["A2"]["psi_full_stalled_percent"])
    cpu_baseline_high=min(arms["A1"]["kswapd_cpu_ticks_per_second_total"],
                          arms["A2"]["kswapd_cpu_ticks_per_second_total"])
    diff=round(baseline_high-arms["B"]["psi_full_stalled_percent"],2)
    cpu_diff=round(cpu_baseline_high-arms["B"]["kswapd_cpu_ticks_per_second_total"],2)
    if not restored:
        verdict="STOP: mode 0 restoration not confirmed; inspect sysfs before any further test"
    elif diff>=20 and cpu_diff>=20:
        verdict="REPRODUCIBLE_SHORT_WINDOWS: prepare source-only candidate; still require idle/battery, root, DT2W, thermal hardware checks before flashing"
    elif arms["B"]["psi_full_stalled_percent"]>max(
         arms["A1"]["psi_full_stalled_percent"],arms["A2"]["psi_full_stalled_percent"])+10:
        verdict="EXPERIMENT_WORSE: keep mode 0"
    else:
        verdict="INCONCLUSIVE_OR_TRANSIENT: keep installed V7.7 mode 0"
    return {"restore_confirmed":restored,"A1_mode0":arms["A1"],
            "B_mode1":arms["B"],"A2_mode0":arms["A2"],
            "full_psi_improvement_vs_both_A_windows_pp":diff,
            "kswapd_cpu_tick_rate_reduction_vs_both_A_windows":cpu_diff,
            "verdict":verdict,
            "limitation":"Three short consecutive windows, not a battery/thermal/sleep stability test. No automatic flash or permanent tuning authorization."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    print(json.dumps(analyze(args.report.read_text(errors="replace")),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
