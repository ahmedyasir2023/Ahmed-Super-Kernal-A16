"""Unit tests for finite three-arm kernel reclaim comparison, no device writes."""
from pathlib import Path
import importlib.util
import sys
import unittest

src=Path(__file__).resolve().parents[1]/"scripts/v7/AY_V77_Reclaim_ABA_Analyzer.py"
sys.path.insert(0,str(src.parent))
spec=importlib.util.spec_from_file_location("aba",src)
aba=importlib.util.module_from_spec(spec)
spec.loader.exec_module(aba)

def snap(stage, t, full, some, ticks, scan, stolen, mode):
    return (f"=== {stage} ===\n"
            f"TIME_EPOCH {t}\n"
            f"MEM_PSI some avg10=55 avg60=20 avg300=10 total={some}\n"
            f"MEM_PSI full avg10=50 avg60=20 avg300=10 total={full}\n"
            f"VM pgscan_kswapd {scan}\nVM pgsteal_kswapd {stolen}\n"
            f"VM pswpin {scan}\nVM pswpout {scan}\nVM workingset_refault {scan}\n"
            f"reclaim_progress_enabled={mode}\n"
            f"KSWAPD 99 cpu_ticks={ticks}\nKSWAPD 3400 cpu_ticks={ticks}\n")

def report(restored=True):
    out=(
        snap("A1 START / mode=0",100,1000000,1000000,0,1000,500,0)+
        snap("A1 END / mode=0",115,10000000,11000000,1500,3000,1000,0)+
        snap("B START / mode=1",118,10000000,11000000,1500,3100,1100,1)+
        snap("B END / mode=1",133,10450000,11450000,1560,5100,2500,1)+
        snap("A2 START / mode=0",136,10450000,11450000,1560,5200,2550,0)+
        snap("A2 END / mode=0",151,19450000,20450000,3060,7200,3200,0))
    if restored:
        out+="RESTORED reclaim_progress_enabled=0\n"
    return out

class TestReclaimABA(unittest.TestCase):
    def test_reversal(self):
        r=aba.analyze(report())
        self.assertTrue(r["restore_confirmed"])
        self.assertEqual(r["A1_mode0"]["psi_full_stalled_percent"],60.0)
        self.assertEqual(r["B_mode1"]["psi_full_stalled_percent"],3.0)
        self.assertEqual(r["A2_mode0"]["psi_full_stalled_percent"],60.0)
        self.assertEqual(r["full_psi_improvement_vs_both_A_windows_pp"],57.0)
        self.assertTrue(r["verdict"].startswith("REPRODUCIBLE_SHORT_WINDOWS"))

    def test_missing_restore_blocks_release(self):
        self.assertTrue(aba.analyze(report(False))["verdict"].startswith("STOP:"))

    def test_no_auto_approval_if_return_to_a_does_not_regress(self):
        raw=report().replace("total=19450000","total=10600000").replace("total=20450000","total=11600000")
        r=aba.analyze(raw)
        self.assertTrue(r["verdict"].startswith("INCONCLUSIVE"))

    def test_missing_mode_rejected(self):
        with self.assertRaises(ValueError):
            aba.analyze(report().replace("reclaim_progress_enabled=1","reclaim_progress_enabled=0"))

    def test_duplicate_snapshot_rejected(self):
        with self.assertRaises(ValueError):
            aba.analyze(report()+snap("A1 START / mode=0",160,100,100,100,100,100,0))

    def test_counter_reset_rejected(self):
        raw=report().replace("total=10450000","total=100")
        with self.assertRaises(ValueError):
            aba.analyze(raw)

    def test_script_restores_on_exit_and_checks_thermal(self):
        sh=(src.parent/"AY_V77_Reclaim_ABA_Confirm.sh").read_text()
        for needle in ("trap restore 0","RESTORED reclaim_progress_enabled=0",
                       "init.svc.vendor.thermal-hal","set_mode 0",
                       "set_mode 1","check_safety","/proc/pressure/memory"):
            self.assertIn(needle,sh)
        for forbidden in ("swapoff ","swapon ","reboot ","setprop ","stop vendor.",
                          "dd if=","fastboot "):
            commands='\n'.join(line for line in sh.splitlines() if line.strip() and not line.lstrip().startswith('#'))
            self.assertNotIn(forbidden,commands)

if __name__=="__main__":
    unittest.main(verbosity=2)
