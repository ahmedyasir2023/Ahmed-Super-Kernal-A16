#!/usr/bin/env python3
"""Synthetic tests for V7.7 strict gzip recompression gate."""
import importlib.util
from pathlib import Path
import gzip
import hashlib
import unittest

p=Path(__file__).resolve().parents[1]/"scripts/release/ay_v77_gzip_fit_gate.py"
spec=importlib.util.spec_from_file_location("v77",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestV77GzipGate(unittest.TestCase):
    def test_unknown_kernel_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate(gzip.compress(b"Android Linux kernel",mtime=0))
    def test_corrupt_gzip_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate(b"no valid gzip image")
    def test_expected_hash_is_64_hex(self):
        for s in (mod.PINNED_SHA,mod.RECOMPRESSED_SHA):
            self.assertEqual(len(s),64)
            int(s,16)
    def test_reserved_span_pinned(self):
        self.assertEqual(mod.SPAN,19648512)

if __name__=="__main__":
    unittest.main()
