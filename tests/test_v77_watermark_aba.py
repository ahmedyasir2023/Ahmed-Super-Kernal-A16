"""Nine offline tests for bounded V7.7 watermark sysctl experiment."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "scripts/v7"
P = ROOT / "AY_V77_Watermark_ABA_Analyzer.py"
spec = importlib.util.spec_from_file_location("watermark", P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def stamp(label, when, wm, full, some, ticks, scanned, stolen, direct=0, oom=0):
    zone_high = 54898 if wm == 200 else 20750
    return (f"=== SNAPSHOT {label} ===\n"
            f"TIME_EPOCH {when}\nWATERMARK {wm}\n"
            f"PSI memory some avg10=50.00 avg60=30.00 avg300=10.00 total={some}\n"
            f"PSI memory full avg10=50.00 avg60=30.00 avg300=10.00 total={full}\n"
            f"VM pgscan_kswapd {scanned}\nVM pgsteal_kswapd {stolen}\n"
            f"VM pgscan_direct {direct}\nVM oom_kill {oom}\n"
            "VM pswpin 200\nVM pswpout 200\nVM workingset_refault 200\n"
            "VM allocstall_normal 0\nVM allocstall_movable 0\n"
            "MEM MemAvailable: 559504\n"
            "ZONE Node 0, zone   Normal\nZONE   pages free     24332\n"
            "ZONE         min      1728\nZONE         low      32130\n"
            f"ZONE         high     {zone_high}\n"
            f"KSWAPD 99 ticks={ticks}\nKSWAPD 3400 ticks={ticks}\n"
            "=== END SNAPSHOT ===\n")


def report(fail_restore=False):
    header = "AY_V77_WATERMARK_ABA_V1\nTRIGGERED full_avg10=68.00\n"
    all_parts = (
        stamp("A1 START mode=200", 100, 200, 1000000, 1000000, 10, 1000, 200) +
        stamp("A1 END mode=200", 115, 200, 10500000, 11000000, 1510, 5000, 2000) +
        stamp("B START mode=50", 118, 50, 10500000, 11000000, 1510, 5000, 2000) +
        stamp("B END mode=50", 133, 50, 10800000, 11300000, 1550, 5200, 2200) +
        stamp("A2 START mode=200", 136, 200, 10800000, 11300000, 1550, 5200, 2200) +
        stamp("A2 END mode=200", 151, 200, 20300000, 21300000, 3050, 9200, 4000))
    tail="COMPLETE\n"+("" if fail_restore else "RESTORED watermark_scale_factor=200\n")
    return header+all_parts+tail


class Tests(unittest.TestCase):
    def test_reproduced_stall(self):
        data=mod.analyze(report())
        self.assertEqual(data["original_A1_200"]["memory_full_PSI_percent"], 63.33)
        self.assertEqual(data["candidate_B_50"]["memory_full_PSI_percent"], 2.0)
        self.assertEqual(data["original_A2_200"]["memory_full_PSI_percent"], 63.33)
        self.assertTrue(data["decision"].startswith("REPRODUCED"))
        self.assertTrue(data["restore_confirmed"])
        self.assertEqual(data["candidate_B_50"]["zone_end"]["0:Normal"]["high_pages"],20750)
    def test_no_trigger(self):
        d=mod.analyze("AY_V77_WATERMARK_ABA_V1\nNO_TRIGGER\nCOMPLETE\n")
        self.assertEqual(d["status"],"NO_TRIGGER")
    def test_quiet_baseline(self):
        d=mod.analyze("AY_V77_WATERMARK_ABA_V1\nBASELINE_QUIET: no persistent stall in A1; no watermark was changed\nCOMPLETE\n")
        self.assertEqual(d["status"],"BASELINE_QUIET")
    def test_no_restore(self):
        d=mod.analyze(report(True))
        self.assertIn("RESTORE_NOT_CONFIRMED",d["decision"])
    def test_bad_mode(self):
        with self.assertRaises(ValueError):
            mod.analyze(report().replace("SNAPSHOT B END mode=50 ===\nTIME_EPOCH 133\nWATERMARK 50",
                                         "SNAPSHOT B END mode=50 ===\nTIME_EPOCH 133\nWATERMARK 200"))
    def test_missing_sample(self):
        with self.assertRaises(ValueError):
            mod.analyze(report().replace("=== SNAPSHOT A2 END mode=200 ===","=== SNAPSHOT MISSING ==="))
    def test_ticks_or_psi_reset(self):
        with self.assertRaises(ValueError):
            mod.analyze(report().replace("VM pgscan_kswapd 9200","VM pgscan_kswapd 5"))
        with self.assertRaises(ValueError):
            mod.analyze(report().replace("TIME_EPOCH 151","TIME_EPOCH 120"))
    def test_no_auto_release(self):
        data=mod.analyze(report())
        self.assertIn("source-only hypothesis",data["decision"])
        self.assertIn("no automatic reconfiguration",data["limitations"])
    def test_script_restore_and_safety(self):
        sh=(ROOT/"AY_V77_Watermark_ABA_Trial.sh").read_text()
        for frag in ("trap restore 0","CHANGED=1","CANDIDATE=50","BASE=200",
                     "BASELINE_QUIET","reclaim_progress_enabled=0",
                     "init.svc.vendor.thermal-hal","RESTORED watermark_scale_factor=200"):
            self.assertIn(frag,sh)
        commands="\n".join(x for x in sh.splitlines() if x.strip() and not x.lstrip().startswith("#"))
        for bad in ("swapoff ","swapon ","setprop ","fastboot ","flash_image ","dd if=","reboot "):
            self.assertNotIn(bad,commands)


if __name__=="__main__":unittest.main(verbosity=2)
