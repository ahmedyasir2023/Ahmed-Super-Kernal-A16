#!/usr/bin/env python3
"""Verify every generated DTB against the exact DTB members in original Boot."""
from pathlib import Path
import hashlib
import json
import struct
import sys

root = Path(__file__).resolve().parent.parent
manifest = json.loads((root / "reference/boot-manifest.json").read_text())
dtb_root = root / "kernel/out/arch/arm64/boot/dts"
expected = {item["path"]: item for item in manifest["original_boot_dtbs"]}
actual_paths = sorted(p for p in dtb_root.rglob("*.dtb") if p.is_file())
actual = {p.relative_to(dtb_root).as_posix(): p for p in actual_paths}

if set(actual) != set(expected):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    raise SystemExit(f"DTB set mismatch; missing={missing}, extra={extra}")

rows = []
for name, item in expected.items():
    data = actual[name].read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if len(data) != item["size"]:
        raise SystemExit(f"{name}: size mismatch {len(data)} != {item['size']}")
    if digest != item["sha256"]:
        raise SystemExit(f"{name}: SHA-256 mismatch: {digest}")
    if len(data) < 40 or data[:4] != bytes.fromhex("d00dfeed"):
        raise SystemExit(f"{name}: invalid flattened device tree header")
    total_size = struct.unpack_from(">I", data, 4)[0]
    if total_size != len(data):
        raise SystemExit(f"{name}: FDT totalsize mismatch {total_size} != {len(data)}")
    rows.append((name, len(data), digest))

if sum(row[1] for row in rows) != manifest["boot"]["dtb_size"]:
    raise SystemExit("DTB members do not sum to the original Boot DTB size")

report = [
    "Original Boot DTB compatibility audit",
    f"Device: {manifest['device']}",
    f"Original boot SHA-256: {manifest['boot']['sha256']}",
    f"Original concatenated DTB SHA-256: {manifest['boot']['dtb_blob_sha256']}",
    f"Matched DTB entries: {len(rows)}",
    "All generated DTBs match the original Boot entries byte-for-byte.",
    "",
]
report.extend(f"{name} | {size} bytes | SHA256 {digest}" for name, size, digest in rows)
out = root / "audit/boot-dtb-compatibility.txt"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(report) + "\n")
print("\n".join(report))
