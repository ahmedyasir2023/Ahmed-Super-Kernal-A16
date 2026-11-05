#!/usr/bin/env python3
"""Analyze V7.7 live memory-stall snapshots. Never modifies Android/kernel."""
import argparse
import json
import re
from pathlib import Path

BEGIN=re.compile(r"^=== SAMPLE idx=(\d+) ===$")
PSI=re.compile(r"^PSI memory (full|some) .*total=(\d+)$")
VM=re.compile(r"^VM (\w+) (\d+)$")
CPU=re.compile(r"^KSWAPD (\d+) ticks=(\d+)$")
STATE=re.compile(r"^RECLAIM (\w+)=(\d+)$")
MEM=re.compile(r"^MEM (\w+) (\d+)$")

def parse(report):
    if not report.startswith("AY_V77_LIVE_STALL_V1\n"):
        raise ValueError("Wrong report format")
    if "NO_TRIGGER" in report:
        if "COMPLETE" not in report:
            raise ValueError("Incomplete no-trigger report")
        return None
    if "TRIGGERED avg10=" not in report:
        raise ValueError("No pressure trigger recorded")
    snapshots=[]
    active=None
    for line in report.splitlines():
        start=BEGIN.fullmatch(line)
        if start:
            if active is not None or int(start[1])!=len(snapshots):
                raise ValueError("Out of order / duplicate sample")
            active={"time":None,"psi":{},"vm":{},"cpu":{},"state":{},"mem":{}}
            continue
        if line=="=== END SAMPLE ===":
            if active is None:
                raise ValueError("Unexpected closing marker")
            snapshots.append(active)
            active=None
            continue
        if active is None: continue
        if line.startswith("TIME_EPOCH "):
            active["time"]=int(line.split()[1]); continue
        for regex,field,index_key,index_val in (
            (PSI,"psi",1,2),(VM,"vm",1,2),(CPU,"cpu",1,2),
            (STATE,"state",1,2),(MEM,"mem",1,2)
        ):
            match=regex.fullmatch(line)
            if match:
                active[field][match[index_key]]=int(match[index_val])
                break
    if active is not None or len(snapshots)!=4 or "COMPLETE" not in report:
        raise ValueError("Four completed snapshots required")
    pids=set(snapshots[0]["cpu"])
    for s in snapshots:
        if s["time"] is None or set(s["psi"]) != {"full","some"}:
            raise ValueError("Missing timestamps or PSI")
        if s["state"].get("reclaim_progress_enabled") != 0:
            raise ValueError("Reclaim mode changed during capture")
        if not pids or set(s["cpu"]) != pids:
            raise ValueError("Missing or changing kswapd PID")
    return snapshots

def difference(first,last,name):
    if name not in first or name not in last: return None
    value=last[name]-first[name]
    if value<0: raise ValueError("Counter reset for "+name)
    return value

def analyze(report):
    s=parse(report)
    if s is None:
        return {"status":"NO_TRIGGER","decision":"No observed event; keep V7.7 unchanged."}
    intervals=[]
    for a,b in zip(s,s[1:]):
        seconds=b["time"]-a["time"]
        if seconds<1 or seconds>20:
            raise ValueError("Invalid sampling interval")
        pressure={}
        for k in ("some","full"):
            d=difference(a["psi"],b["psi"],k)
            if d > seconds*1_050_000:
                raise ValueError("Invalid cumulative PSI value")
            pressure[k]=round(d/seconds/10_000,2)
        ticks=sum(difference(a["cpu"],b["cpu"],pid) for pid in a["cpu"])
        reclaim={}
        for k in ("pgscan_kswapd","pgsteal_kswapd","pgscan_direct","pgsteal_direct","pswpin","pswpout","workingset_refault"):
            v=difference(a["vm"],b["vm"],k)
            reclaim[k]=round(v/seconds,1) if v is not None else None
        intervals.append({"seconds":seconds,"memory_full_stall_percent":pressure["full"],
                          "memory_some_stall_percent":pressure["some"],
                          "kswapd_combined_ticks_per_sec":round(ticks/seconds,1),
                          "vm_events_per_sec":reclaim,
                          "mem_available_kib_start":a["mem"].get("MemAvailable")})
    scanned=difference(s[0]["vm"],s[-1]["vm"],"pgscan_kswapd")
    stolen=difference(s[0]["vm"],s[-1]["vm"],"pgsteal_kswapd")
    return {"status":"TRIGGERED","kswapd_workers":len(s[0]["cpu"]),"intervals":intervals,
            "kswapd_reclaim_efficiency_percent":round(100*stolen/scanned,2) if scanned and stolen is not None else None,
            "note":"High/low zone watermarks need allocator context; kswapd CPU ticks are not CPU percentage without USER_HZ.",
            "decision":"Use evidence for source diagnosis only; no persistent tuning or flashing."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    print(json.dumps(analyze(args.report.read_text(errors="replace")),indent=2))

if __name__=="__main__":main()
