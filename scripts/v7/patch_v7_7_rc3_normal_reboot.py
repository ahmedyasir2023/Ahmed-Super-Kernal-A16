#!/usr/bin/env python3
"""RC3: opt-in RC2 warm-reset experiment -> normal-reboot default-on fix.

Patches only the RC2 diagnostic block in the pinned Realme 4.14 source.
The root-only parameter remains writable to opt OUT; reboot reset itself
never changes shutdown, panic, fastboot, recovery, EDL or deep-sleep.
"""
from pathlib import Path

p=Path(__file__).resolve().parents[2]/"kernel/drivers/power/reset/msm-poweroff.c"
s=p.read_text()
def one(old,new,label):
    global s
    assert s.count(old)==1, "Unexpected Realme RC2 reboot source: "+label
    s=s.replace(old,new,1)

one(
    "static bool ay_normal_warm_reset_probe;\n",
    "static bool ay_normal_warm_reset_probe = true;\n",
    "default enabled")

one(
    '"0: vendor default hard reset; 1: normal reboot warm reset test");',
    '"0: legacy normal reboot hard reset; 1: normal reboot warm reset (boot default)");',
    "parameter help")

one(
    "\tif (!in_panic && READ_ONCE(ay_normal_warm_reset_probe) &&\n"
    "\t    (!cmd || !cmd[0])) {\n",
    "\tif (!in_panic && READ_ONCE(ay_normal_warm_reset_probe) &&\n"
    '\t    (!cmd || !cmd[0] || !strcmp(cmd, "reboot") ||\n'
    '\t     !strcmp(cmd, "normal"))) {\n',
    "ordinary reboot selector")

one(
    '\t\tpr_notice("AY reboot probe: ordinary reboot using PMIC warm reset\\n");',
    '\t\tpr_notice("AY RC3: normal restart using PMIC warm reset\\n");',
    "trace message")

p.write_text(s)
print("RC3: default ON for plain/normal reboot, root-only opt-out; named targets unchanged")
