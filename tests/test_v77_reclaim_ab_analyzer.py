"""Reclaim A/B offline triage regression tests. No device/sysfs access."""
import importlib.util
from pathlib import Path
import unittest

src=Path(__file__).resolve().parents[1]/"scripts/v7/AY_V77_Reclaim_AB_Analyzer.py"
spec=importlib.util.spec_from_file_location("ab",src)
ab=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ab)


def snapshot(label, t, full, some, ticks, scan, reclaim, mode):
    return (f"=== {label} ===\n"
            f"TIME_EPOCH {t}\n"
            f"MEM_PSI some avg10=10.00 avg60=9.00 avg300=8.00 total={some}\n"
            f"MEM_PSI full avg10=10.00 avg60=9.00 avg300=8.00 total={full}\n"
            f"VM pgscan_kswapd {scan}\n"
            f"VM pgsteal_kswapd {reclaim}\n"
            f"VM pswpin {scan+2}\n"
            f"VM pswpout {scan+10}\n"
            f"VM workingset_refault {scan*2}\n"
            f"balance_calls={scan}\n"
            f"reclaim_progress_enabled={mode}\n"
            f"KSWAPD 99 cpu_ticks={ticks}\n"
            f"KSWAPD 3400 cpu_ticks={ticks}\n")


def report(mode1full=1000000,restore=True):
    s=(snapshot("BASELINE START / mode=0",100,5000000,6000000,100,1000,300,0)+
       snapshot("BASELINE END / mode=0",110,10000000,11000000,1100,2000,600,0)+
       snapshot("EXPERIMENT START / mode=1",110,10000000,11000000,1100,2000,600,1)+
       snapshot("EXPERIMENT END / mode=1",120,10000000+mode1full,11000000+mode1full,1500,3000,1000,1))
    if restore:
        s+="RESTORED reclaim_progress_enabled=0\n"
    return s


class TestAB(unittest.TestCase):
    def test_good_short_sample(self):
        obj=ab.analyze(report())
        self.assertTrue(obj["restore_confirmed"])
        self.assertEqual(obj["baseline_mode_0"]["psi_full_stalled_percent"],50)
        self.assertEqual(obj["experiment_mode_1"]["psi_full_stalled_percent"],10)
        self.assertEqual(obj["baseline_mode_0"]["workers"],2)
        self.assertEqual(obj["baseline_mode_0"]["kswapd_reclaim_efficiency_percent"],30)
        self.assertEqual(obj["experiment_mode_1"]["kswapd_reclaim_efficiency_percent"],40)
        self.assertTrue(obj["decision"].startswith("PROMISING_SHORT_SAMPLE"))

    def test_missing_restoration_must_never_approve(self):
        obj=ab.analyze(report(restore=False))
        self.assertEqual(obj["restore_confirmed"],False)
        self.assertTrue(obj["decision"].startswith("NO_RESTORE_CONFIRMATION"))

    def test_psi_worse_is_rejected(self):
        obj=ab.analyze(report(mode1full=8000000))
        self.assertEqual(obj["decision"],"WORSE_SHORT_SAMPLE: keep kernel default 0")

    def test_missing_mode_or_corrupt_report(self):
        with self.assertRaises(ValueError):
            ab.analyze(report().replace("reclaim_progress_enabled=1","reclaim_progress_enabled=0"))
        with self.assertRaises(ValueError):
            ab.analyze(report().replace("=== EXPERIMENT END / mode=1 ===","=== DIFFERENT ==="))

    def test_duplicate_snapshot(self):
        raw=report()+snapshot("BASELINE START / mode=0",110,5000000,6000000,100,1000,200,0)
        with self.assertRaises(ValueError):
            ab.analyze(raw)

    def test_counter_reset_and_elapsed_guard(self):
        raw=report().replace("MEM_PSI full avg10=10.00 avg60=9.00 avg300=8.00 total=10000000",
                            "MEM_PSI full avg10=10.00 avg60=9.00 avg300=8.00 total=100000")
        with self.assertRaises(ValueError):
            ab.analyze(raw)
        raw=report().replace("TIME_EPOCH 120","TIME_EPOCH 111")
        with self.assertRaises(ValueError):
            ab.analyze(raw)

    def test_snapshot_is_structured_not_guesswork(self):
        raw=report().replace("KSWAPD 99 cpu_ticks=1500", "KSWAPD 99 cpu_ticks=0")
        with self.assertRaises(ValueError):
            ab.analyze(raw)

if __name__=="__main__":
    unittest.main(verbosity=2)
