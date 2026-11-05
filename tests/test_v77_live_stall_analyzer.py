"""Offline synthetic tests for V7.7 event-triggered PSI flight recorder."""
import importlib.util
from pathlib import Path
import unittest

script=Path(__file__).resolve().parents[1]/"scripts/v7/AY_V77_Live_Stall_Analyzer.py"
spec=importlib.util.spec_from_file_location("live",script)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample(i,tm,psi_full,psi_some,ticks,scan,stolen,mode=0):
    return (f"=== SAMPLE idx={i} ===\nTIME_EPOCH {tm}\n"
            f"PSI memory some avg10=35.20 avg60=10.00 avg300=4.00 total={psi_some}\n"
            f"PSI memory full avg10=30.00 avg60=8.00 avg300=2.00 total={psi_full}\n"
            f"VM pgscan_kswapd {scan}\nVM pgsteal_kswapd {stolen}\n"
            f"VM pswpin {scan}\nVM pswpout {scan}\nVM workingset_refault {scan}\n"
            f"MEM MemAvailable 560000\nRECLAIM reclaim_progress_enabled={mode}\n"
            f"KSWAPD 99 ticks={ticks}\nKSWAPD 3400 ticks={ticks}\n=== END SAMPLE ===\n")

def event():
    return ("AY_V77_LIVE_STALL_V1\nTRIGGERED avg10=35.00\n"+
            sample(0,100,1_000_000,1_000_000,100,1000,300)+
            sample(1,105,3_500_000,3_700_000,600,2000,800)+
            sample(2,110,6_000_000,6_400_000,1100,3000,1300)+
            sample(3,115,8_500_000,9_100_000,1600,4000,1800)+
            "COMPLETE\n")

class TestLiveStall(unittest.TestCase):
    def test_real_event_computation(self):
        r=m.analyze(event())
        self.assertEqual(r["status"],"TRIGGERED")
        self.assertEqual(len(r["intervals"]),3)
        self.assertEqual(r["kswapd_workers"],2)
        self.assertEqual(r["intervals"][0]["memory_full_stall_percent"],50)
        self.assertEqual(r["intervals"][0]["kswapd_combined_ticks_per_sec"],200)
        self.assertEqual(r["kswapd_reclaim_efficiency_percent"],50)
    def test_no_trigger_not_a_fix(self):
        r=m.analyze("AY_V77_LIVE_STALL_V1\nWATCH idx=0 avg10=2\nNO_TRIGGER\nCOMPLETE\n")
        self.assertEqual(r["status"],"NO_TRIGGER")
        self.assertIn("unchanged",r["decision"])
    def test_no_trigger_without_completion(self):
        with self.assertRaises(ValueError):m.analyze("AY_V77_LIVE_STALL_V1\nNO_TRIGGER\n")
    def test_missing_sample(self):
        with self.assertRaises(ValueError):
            m.analyze(event().replace("=== SAMPLE idx=3 ===","=== MISSING ==="))
    def test_mode_change_rejected(self):
        with self.assertRaises(ValueError):
            m.analyze(event().replace("RECLAIM reclaim_progress_enabled=0","RECLAIM reclaim_progress_enabled=1",1))
    def test_counter_reset_rejected(self):
        with self.assertRaises(ValueError):
            m.analyze(event().replace("VM pgscan_kswapd 3000","VM pgscan_kswapd 1"))
    def test_worker_churn_rejected(self):
        with self.assertRaises(ValueError):
            m.analyze(event().replace("KSWAPD 3400 ticks=1600","KSWAPD 5000 ticks=1600"))
    def test_report_is_read_only_and_bounded(self):
        sh=(script.parent/"AY_V77_Live_Stall_Recorder.sh").read_text()
        lines="\n".join(x for x in sh.splitlines() if not x.strip().startswith("#"))
        for forbidden in ("setprop ","swapoff ","swapon ","fastboot ","reboot ","stop vendor.",
                          "dd if=","echo 1 > /sys/","echo 0 > /sys/"):
            self.assertNotIn(forbidden,lines)
        self.assertIn('while [ "$i" -lt 20 ]',sh)
        self.assertIn('sleep 5',sh)
        self.assertIn('reclaim_progress_enabled=0',sh)

if __name__=="__main__":unittest.main(verbosity=2)
