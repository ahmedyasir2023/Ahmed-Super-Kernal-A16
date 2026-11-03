#!/usr/bin/env python3
"""Fail-closed local ROM source preflash audit (never creates a flashable ZIP).

This validates the four original Evolution X Android 16 image files against
their pinned recorded SHA-256 values. The V5 Android 14 OrangeFox ZIP is not
a valid substitute. This check does NOT authorize flashing or AVB bypass.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "reference" / "boot-manifest.json"

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def verify(path: Path, entry: dict, label: str) -> str:
    if not path.is_file():
        raise ValueError(f"{label}: missing input file: {path}")
    if path.stat().st_size != entry["bytes"]:
        raise ValueError(f"{label}: wrong byte length; refuses outdated/mismatched ROM")
    actual=sha(path)
    if actual != entry["sha256"]:
        raise ValueError(f"{label}: SHA-256 does not match pinned Android 16 ROM")
    return actual

def validate_manifest(manifest: dict) -> None:
    if manifest["device"] != "Realme 7 Pro RMX2170":
        raise ValueError("Device is not pinned RMX2170")
    if not manifest["rom"].startswith("EvolutionX-16.0-"):
        raise ValueError("ROM is not Evolution X Android 16")
    if manifest["boot"]["header_version"] != 2 or manifest["boot"]["page_size"] != 4096:
        raise ValueError("Boot header/page changed; manual review required")
    if sum(x["size"] for x in manifest["original_boot_dtbs"]) != manifest["boot"]["dtb_size"]:
        raise ValueError("Original DTB manifest is inconsistent")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--boot",type=Path)
    ap.add_argument("--dtbo",type=Path)
    ap.add_argument("--vbmeta",type=Path)
    ap.add_argument("--vbmeta-system",type=Path)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    m=json.loads(MANIFEST.read_text())
    validate_manifest(m)
    if args.self_test:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as d:
            p=Path(d)/"small.bin"
            p.write_bytes(b"correct")
            good={"bytes":7,"sha256":hashlib.sha256(b"correct").hexdigest()}
            assert verify(p,good,"test") == good["sha256"]
            try:
                verify(p,{"bytes":7,"sha256":"0"*64},"test")
            except ValueError:
                pass
            else:
                raise AssertionError("Hash mismatch was not rejected")
            try:
                verify(p,{"bytes":8,"sha256":good["sha256"]},"test")
            except ValueError:
                pass
            else:
                raise AssertionError("Length mismatch was not rejected")
        print("ROM SHA-256/size mismatch and pinned manifest self-tests PASS")
        return
    pairs={"boot":args.boot,"dtbo":args.dtbo,"vbmeta":args.vbmeta,
           "vbmeta_system":args.vbmeta_system}
    if any(v is None for v in pairs.values()):
        ap.error("All four files required: --boot --dtbo --vbmeta --vbmeta-system")
    verified={}
    for key,path in pairs.items():
        verified[key]=verify(path,m[key],key)
    # Verify the expected Android boot image header without mutating it.
    with args.boot.open("rb") as f:
        header=f.read(1660)
    if header[:8]!=b"ANDROID!":
        raise ValueError("Boot magic mismatches Android boot image")
    boot_version=struct.unpack_from("<I",header,8+8*4)[0]
    if boot_version!=2:
        raise ValueError("Unexpected boot header version")
    output=[
      "RMX2170 Evolution X A16 — ORIGINAL ROM IMAGE PREFLIGHT",
      "Matching ROM inputs: PASS (all four exact SHA-256 and lengths)",
      "Boot image header: Android v2",
      *[f"{k}: {v}" for k,v in verified.items()],
      "STATUS: PREFLIGHT ONLY, NOT A FLASH AUTHORIZATION",
      "Bootloader, external AVB signature, replacement kernel and hardware boot: NOT VERIFIED",
      "Do NOT flash any output from source-only CI. No boot.img/OrangeFox ZIP is generated."
    ]
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text("\n".join(output)+"\n")
    print("\n".join(output))

if __name__=="__main__":
    main()
