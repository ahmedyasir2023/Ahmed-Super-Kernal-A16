#!/usr/bin/env python3
"""Verify exact warm reboot probe scope and 48-mode decision combinations."""
from pathlib import Path
import itertools,subprocess

root=Path(__file__).resolve().parents[2]
k=root/"kernel"
s=(k/"drivers/power/reset/msm-poweroff.c").read_text()
assert "static bool ay_normal_warm_reset_probe;" in s
assert "module_param_named(ay_normal_warm_reset_probe," in s
assert "ay_normal_warm_reset_probe, bool, 0600);" in s
assert "READ_ONCE(ay_normal_warm_reset_probe)" in s
assert "(!cmd || !cmd[0])" in s
assert "if (!in_panic && READ_ONCE(ay_normal_warm_reset_probe) &&" in s
assert 'pr_notice("AY reboot probe: ordinary reboot using PMIC warm reset\\n");' in s
a=s.index("static void msm_restart_prepare(const char *cmd)")
b=s.index("static void deassert_ps_hold(",a)
prepare=s[a:b]
assert "qpnp_pon_check_hard_reset_stored()" in prepare
assert "qpnp_pon_system_pwr_off(PON_POWER_OFF_WARM_RESET);" in prepare
assert "qpnp_pon_system_pwr_off(PON_POWER_OFF_HARD_RESET);" in prepare
assert "if (force_warm_reboot || need_warm_reset)" in prepare
assert "qpnp_pon_set_restart_reason(" in prepare
power=s[s.index("static void do_msm_poweroff(void)"):s.index("#ifdef CONFIG_QCOM_DLOAD_MODE",s.index("static void do_msm_poweroff(void)"))]
assert "PON_POWER_OFF_SHUTDOWN" in power
assert "deassert_ps_hold();" in power

# For ALL mode / command / panic / hardware reason combinations:
# only explicit ordinary reboots are modified; panic and named targets
# keep vendor behaviour regardless of the knob.
for enable,cmd,panic,stored in itertools.product(
  (False,True),(None,"","recovery","bootloader","edl","android"),
  (False,True),(False,True)
):
    special=bool(cmd)
    vendor_warm=panic or ((cmd=="edl") if stored else special)
    override=enable and not panic and not special
    actual=vendor_warm or override
    if not override:
        assert actual==vendor_warm
    if panic:
        assert actual
    if enable and not panic and not special:
        assert actual

diff=subprocess.check_output(["git","-C",str(k),"diff","--",
  "drivers/power/reset/msm-poweroff.c"],text=True)
assert diff.count("@@")==4,"Expected only two small source hunks"
assert diff.count("+static bool ay_normal_warm_reset_probe;")==1
assert diff.count("+\tif (!in_panic && READ_ONCE(ay_normal_warm_reset_probe) &&")==1
assert diff.count("+\t\tneed_warm_reset = true;")==1
assert "-\t\tqpnp_pon_system_pwr_off(PON_POWER_OFF_HARD_RESET);" not in diff
assert "-\t\tqpnp_pon_system_pwr_off(PON_POWER_OFF_WARM_RESET);" not in diff
print("V7.7 warm reboot: default OFF; root 0600; scoped ordinary-only A/B PASS")
