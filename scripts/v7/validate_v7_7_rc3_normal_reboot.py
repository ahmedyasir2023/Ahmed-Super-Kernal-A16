#!/usr/bin/env python3
"""RC3 reboot safety: only ordinary reboots warm by default; 0600 opt-out."""
from pathlib import Path
import itertools
import subprocess

root=Path(__file__).resolve().parents[2]
kernel=root/"kernel"
source=kernel/"drivers/power/reset/msm-poweroff.c"
s=source.read_text()

assert s.count("static bool ay_normal_warm_reset_probe = true;")==1
assert s.count("ay_normal_warm_reset_probe, bool, 0600);")==1
assert "if (!in_panic && READ_ONCE(ay_normal_warm_reset_probe) &&" in s
assert ('(!cmd || !cmd[0] || !strcmp(cmd, "reboot") ||\n'
        '\t     !strcmp(cmd, "normal")))' in s
assert 'AY RC3: normal restart using PMIC warm reset' in s

prepare=s[s.index("static void msm_restart_prepare(const char *cmd)"):
          s.index("static void deassert_ps_hold(",s.index("static void msm_restart_prepare("))]
assert prepare.count("PON_POWER_OFF_HARD_RESET")==1
assert prepare.count("PON_POWER_OFF_WARM_RESET")>=2
assert 'if (force_warm_reboot || need_warm_reset)' in prepare
assert "if (in_panic)" in prepare
assert 'qpnp_pon_set_restart_reason(' in prepare
shutdown=s[s.index("static void do_msm_poweroff(void)"):
           s.index("#ifdef CONFIG_QCOM_DLOAD_MODE",s.index("static void do_msm_poweroff(void)"))]
assert "PON_POWER_OFF_SHUTDOWN" in shutdown

# Source semantic regression: no change to panic, named recovery/fastboot,
# EDL or shutdown, nor opt-out behaviour.
for enabled,panic,cmd in itertools.product(
    (False,True),(False,True),
    (None,"","reboot","normal","recovery","bootloader","edl","fastboot","shutdown,thermal","android")
):
    normalized=cmd is None or cmd in ("","reboot","normal")
    override=enabled and not panic and normalized
    if not enabled or panic or not normalized:
        assert not override
    if enabled and not panic and normalized:
        assert override

changed=subprocess.check_output(["git","-C",str(kernel),"diff",
        "--name-only","--","drivers/power/reset/msm-poweroff.c"],text=True).strip()
assert changed=="drivers/power/reset/msm-poweroff.c"
diff=subprocess.check_output(["git","-C",str(kernel),"diff",
        "--","drivers/power/reset/msm-poweroff.c"],text=True)
# Only the designated vendor reset driver may differ; no original PMIC
# reset/poweroff calls removed.
for command in ("-\\t\\tqpnp_pon_system_pwr_off(PON_POWER_OFF_HARD_RESET);",
                "-\\t\\tqpnp_pon_system_pwr_off(PON_POWER_OFF_WARM_RESET);",
                "-\\tqpnp_pon_system_pwr_off(PON_POWER_OFF_SHUTDOWN);"):
    assert command not in diff
assert "+static bool ay_normal_warm_reset_probe = true;" in diff
assert "+\t    (!cmd || !cmd[0] || !strcmp(cmd, \"reboot\") ||" in diff
print("V7.7 RC3: safe default normal-reboot warm reset, opt-out, recovery/panic/shutdown preserved PASS")
