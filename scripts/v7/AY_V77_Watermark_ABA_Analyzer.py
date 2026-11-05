#!/usr/bin/env python3
"""Assess AY V7.7 short, reversible watermark-scale-factor A-B-A report.

This offline tool never connects to Android or changes any kernel setting.
It does NOT authorize automatic tuning or a flashable kernel release.
"""
import argparse
import json
import re
from pathlib import Path

STAGES=("A1 START mode=200", "A1 END mode=200", "B START mode=50",
        "B END mode=50", "A2 START mode=200", "A2 END mode=200")
HEADER=re.compile(r"^=== SNAPSHOT (.*?) ===$")
PSI=re.compile(r"^PSI memory (some|full) .*?\btotal=(\d+)$")
VM=re.compile(r"^VM (\w+) (\d+)$")
MEM=re.compile(r"^MEM (\w+) (\d+)$")
CPU=re.compile(r"^KSWAPD (\d+) ticks=(\d+)$")
ZONE_HEAD=re.compile(r"^ZONE Node (\d+), zone\s+(\w+)$")
ZONE_VAL=re.compile(r"^ZONE\s+(pages free|min|low|high|managed)\s+(\d+)$")


def parse(report):
    if not report.startswith("AY_V77_WATERMARK_ABA_V1\n"):
        raise ValueError("Not a V7.7 watermark A-B-A file")
    if "NO_TRIGGER\n" in report:
        if "COMPLETE\n" not in report:
            raise ValueError("Incomplete no-trigger report")
        return {}, "NO_TRIGGER", False
    if "BASELINE_QUIET:" in report:
        if "COMPLETE\n" not in report:
            raise ValueError("Incomplete baseline-quiet report")
        return {}, "BASELINE_QUIET", False
    out={}
    current=None
    zone=None
    for line in report.splitlines():
        h=HEADER.fullmatch(line)
        if h:
            if h[1] not in STAGES or h[1] in out:
                raise ValueError("Unexpected or duplicate snapshot name: "+h[1])
            current={"epoch":None,"wm":None,"psi":{},"vm":{},"cpu":{},"mem":{},"zones":{}}
            out[h[1]]=current
            zone=None
            continue
        if line == "=== END SNAPSHOT ===":
            current=None
            zone=None
            continue
        if current is None:continue
        if line.startswith("TIME_EPOCH "):
            current["epoch"]=int(line.partition(" ")[2]);continue
        if line.startswith("WATERMARK "):
            current["wm"]=int(line.partition(" ")[2]);continue
        h=PSI.fullmatch(line)
        if h:current["psi"][h[1]]=int(h[2]);continue
        h=VM.fullmatch(line)
        if h:current["vm"][h[1]]=int(h[2]);continue
        h=MEM.fullmatch(line)
        if h:current["mem"][h[1]]=int(h[2]);continue
        h=CPU.fullmatch(line)
        if h:current["cpu"][h[1]]=int(h[2]);continue
        h=ZONE_HEAD.fullmatch(line)
        if h:
            zone=f"{h[1]}:{h[2]}"
            current["zones"][zone]={}
            continue
        h=ZONE_VAL.fullmatch(line)
        if h and zone:
            current["zones"][zone][h[1].replace(" ","_")]=int(h[2]);continue
    if list(out)!=list(STAGES) or "COMPLETE\n" not in report:
        raise ValueError("Incomplete or out-of-order A-B-A window")
    restored="RESTORED watermark_scale_factor=200" in report
    oldworkers=None
    for name,r in out.items():
        expected=50 if name.startswith("B ") else 200
        if r["wm"]!=expected:
            raise ValueError("Unexpected active watermark value: "+name)
        if r["epoch"] is None or set(r["psi"]) != {"some","full"}:
            raise ValueError("Missing time or PSI totals: "+name)
        if not r["cpu"] or (oldworkers is not None and set(r["cpu"]) != oldworkers):
            raise ValueError("kswapd PID set missing or changed")
        oldworkers=set(r["cpu"])
    return out,"COMPLETE",restored


def delta(a,b,key):
    if key not in a or key not in b:return None
    d=b[key]-a[key]
    if d<0:raise ValueError("Counter reset: "+key)
    return d


def interval(a,b):
    sec=b["epoch"]-a["epoch"]
    if not 10<=sec<=35:
        raise ValueError("Invalid time window")
    psi={}
    for k in ("full","some"):
        d=delta(a["psi"],b["psi"],k)
        if d > sec*1_000_000*1.03:
            raise ValueError("Memory PSI total exceeded interval wall clock")
        psi[k]=round(d/sec/10_000,2)
    ticks=sum(delta(a["cpu"],b["cpu"],pid) for pid in a["cpu"])
    vm={}
    for key in ("pgscan_kswapd","pgsteal_kswapd","pgscan_direct",
                "pgsteal_direct","pswpin","pswpout","workingset_refault",
                "allocstall_normal","allocstall_movable","oom_kill"):
        d=delta(a["vm"],b["vm"],key)
        vm[key]=round(d/sec,2) if d is not None else None
    zones={}
    for z,fields in b["zones"].items():
        if all(k in fields for k in ("pages_free","min","low","high")):
            zones[z]={"free_pages":fields["pages_free"],
                      "low_pages":fields["low"],"high_pages":fields["high"],
                      "free_minus_high_pages":fields["pages_free"]-fields["high"]}
    return {"seconds":sec,"memory_full_PSI_percent":psi["full"],
            "memory_some_PSI_percent":psi["some"],
            "combined_kswapd_CPU_ticks_per_sec":round(ticks/sec,2),
            "vm_events_per_sec":vm,"mem_available_kb_end":b["mem"].get("MemAvailable"),
            "zone_end":zones}


def analyze(report):
    rec,status,restored=parse(report)
    if status!="COMPLETE":
        return {"status":status,"safe_outcome":"No watermark sysctl tuning was attempted."}
    a1=interval(rec[STAGES[0]],rec[STAGES[1]])
    b=interval(rec[STAGES[2]],rec[STAGES[3]])
    a2=interval(rec[STAGES[4]],rec[STAGES[5]])
    if not restored:
        verdict="RESTORE_NOT_CONFIRMED: check watermark_scale_factor manually before further testing"
    else:
        a1_full=a1["memory_full_PSI_percent"]
        b_full=b["memory_full_PSI_percent"]
        a2_full=a2["memory_full_PSI_percent"]
        a1_cpu=a1["combined_kswapd_CPU_ticks_per_sec"]
        b_cpu=b["combined_kswapd_CPU_ticks_per_sec"]
        a2_cpu=a2["combined_kswapd_CPU_ticks_per_sec"]
        direct=b["vm_events_per_sec"].get("pgscan_direct")
        oom=b["vm_events_per_sec"].get("oom_kill")
        alloc=sum(b["vm_events_per_sec"].get(k) or 0 for k in ("allocstall_normal","allocstall_movable"))
        if (oom or 0)>0 or (direct or 0)>50 or alloc>0:
            verdict="WARNING_DIRECT_RECLAIM_OR_OOM: keep original watermark=200"
        elif a1_full>=25 and a1_full-b_full>=20 and a2_full-b_full>=20 and a1_cpu>b_cpu*2 and a2_cpu>b_cpu*2:
            verdict="REPRODUCED_UNDER_STALL: source-only hypothesis; longer controlled tests still required"
        else:
            verdict="INCONCLUSIVE: keep original watermark=200"
    return {"status":status,"restore_confirmed":restored,
            "original_A1_200":a1,"candidate_B_50":b,"original_A2_200":a2,
            "decision":verdict,
            "limitations":"A-B-A changes a live kernel sysctl briefly, but the workloads are not randomized. A short result cannot prove full-time safety, energy savings or thermal safety; no automatic reconfiguration or new flash image."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    print(json.dumps(analyze(args.report.read_text(errors="replace")),indent=2))


if __name__=="__main__":main()
