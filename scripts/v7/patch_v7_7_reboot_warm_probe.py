#!/usr/bin/env python3
"""V7.7 RC2: root-only opt-in NORMAL reboot PMIC warm-reset diagnostic.

No behaviour change by default, no changes to shutdown, recovery, bootloader,
panic, EDL, DTB, DeepDoze, input boost, root or fingerprints. Requires a
deliberate root action for ONE supervised reboot. Resets OFF on boot.
"""
from pathlib import Path
p=Path(__file__).resolve().parents[2]/"kernel/drivers/power/reset/msm-poweroff.c"
s=p.read_text()

def one(old,new,name):
    global s
    assert s.count(old)==1,"Unexpected Realme restart source: "+name
    s=s.replace(old,new,1)

one(
    "static bool force_warm_reboot;\n\nstatic int in_panic;\n",
    """static bool force_warm_reboot;
/* Diagnostic only: defaults to false on every boot, root-only (0600).
 * Select PMIC warm reset only for an ordinary, non-panic reboot.
 */
static bool ay_normal_warm_reset_probe;
module_param_named(ay_normal_warm_reset_probe,
                   ay_normal_warm_reset_probe, bool, 0600);
MODULE_PARM_DESC(ay_normal_warm_reset_probe,
                 "0: vendor default hard reset; 1: normal reboot warm reset test");

static int in_panic;
""",
    "root-only nonpersistent probe")

one(
    "\tif (in_panic)\n\t\tneed_warm_reset = true;\n\n\t/* Hard reset the PMIC unless memory contents must be maintained. */\n",
    """\tif (in_panic)
\t\tneed_warm_reset = true;

\t/* AY supervised A/B: retain vendor behaviour unless root opted in.
\t * Do not modify reboot-to-recovery/bootloader/EDL or a panic path.
\t */
\tif (!in_panic && READ_ONCE(ay_normal_warm_reset_probe) &&
\t    (!cmd || !cmd[0])) {
\t\tneed_warm_reset = true;
\t\tpr_notice("AY reboot probe: ordinary reboot using PMIC warm reset\\n");
\t}

\t/* Hard reset the PMIC unless memory contents must be maintained. */
""",
    "ordinary reboot warm reset selector")
p.write_text(s)
print("V7.7 reboot probe: default OFF, root-only warm normal reboot test staged")
