"""Synthetic tests for V7.7 memory stall accounting, fail closed."""
import importlib.util
import unittest
from pathlib import Path

modpath=Path(__file__).resolve().parents[1]/"scripts/v7/AY_V77_Stability_Analyzer.py"
spec=importlib.util.spec_from_file_location("ay_stability",modpath)
ay=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ay)

def sample(t,scan,steal,pin,pout,total,available):
    return f"""=== SAMPLE t={t} ===
PSI memory some avg10=14.25 avg60=3.00 avg300=1.00 total={total+800}
PSI memory full avg10=9.50 avg60=1.00 avg300=0.50 total={total}
VM pgscan_kswapd {scan}
VM pgsteal_kswapd {steal}
VM pswpin {pin}
VM pswpout {pout}
MEM MemAvailable: {available} kB
=== END SAMPLE ===
"""

class TestAYV77(unittest.TestCase):
    def setUp(self):
        self.text=(sample(0,100,30,2,3,1000000,600000)+
                   sample(5,200,50,10,23,1500000,400000)+
                   sample(10,300,70,20,33,2100000,500000))

    def test_counts(self):
        d=ay.analyze(ay.parse(self.text))
        self.assertEqual(d["samples"],3)
        self.assertEqual(d["kernel_reclaim_scanned_pages"],200)
        self.assertEqual(d["kernel_reclaim_stolen_pages"],40)
        self.assertEqual(d["kswapd_reclaim_efficiency_percent"],20.0)
        self.assertEqual(d["swap_in_pages"],18)
        self.assertEqual(d["swap_out_pages"],30)
        self.assertEqual(d["psi"]["memory_full"]["total_stall_interval_percent"],11.0)

    def test_missing_counters(self):
        t=self.text.replace("VM pgsteal_kswapd 30","").replace("VM pgsteal_kswapd 50","").replace("VM pgsteal_kswapd 70","")
        self.assertIsNone(ay.analyze(ay.parse(t))["kswapd_reclaim_efficiency_percent"])

    def test_zero_denominator(self):
        t=sample(0,0,0,0,0,0,1000)+sample(5,0,0,0,0,0,1000)
        self.assertIsNone(ay.analyze(ay.parse(t))["kswapd_reclaim_efficiency_percent"])

    def test_counter_reset(self):
        t=sample(0,1000,800,0,0,2000,1000)+sample(5,10,5,0,0,1000,1000)
        d=ay.analyze(ay.parse(t))
        self.assertIsNone(d["kernel_reclaim_scanned_pages"])
        self.assertNotIn("total_stall_interval_percent",d["psi"]["memory_full"])

    def test_duplicate_or_incomplete(self):
        with self.assertRaises(ValueError):
            ay.parse(sample(0,10,5,0,0,0,100))
        with self.assertRaises(ValueError):
            ay.parse(sample(0,10,5,0,0,0,100)+sample(0,11,6,0,0,0,100))

    def test_read_only_collector(self):
        sh=(modpath.parent/"AY_V77_Stability_Probe.sh").read_text()
        code="\n".join(line for line in sh.splitlines() if not line.lstrip().startswith("#"))
        for token in ("swapon ","swapoff ","setprop ","stop vendor.","start vendor.",
                      "reboot ","pm disable","killall ","echo 1 > /sys/",
                      "echo 0 > /sys/","service call"):
            self.assertNotIn(token,code,token)
        self.assertIn('chmod 0600 "$OUT"',sh)

if __name__=="__main__":
    unittest.main(verbosity=2)
