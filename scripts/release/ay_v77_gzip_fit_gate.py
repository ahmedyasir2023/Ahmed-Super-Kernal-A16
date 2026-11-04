#!/usr/bin/env python3
"""Fail closed when exact V7.7 CI kernel cannot fit trusted V7.2 Boot.

Lossless gzip-9 recompression is only permitted for pinned V7.7 CI bytes.
No Android boot image is written. The full user-owned boot image and
rollback archives must be audited separately offline.
"""
import argparse
import gzip
import hashlib
from pathlib import Path
import zipfile

PINNED_SHA="53b287560741f83e64b672c3cde2ea6bdbd97310ea2e7febe7b73731ced747ba"
RECOMPRESSED_SHA="33367173900cd24093c5dc4c3ba64c94ceddc2f790a3439cb612e81b98023ab2"
SPAN=19648512

def sha(b):
    return hashlib.sha256(b).hexdigest()

def validate(data):
    if sha(data)!=PINNED_SHA:
        raise ValueError("Refusing unpinned V7.7 Image.gz")
    unpacked=gzip.decompress(data)
    new=gzip.compress(unpacked,compresslevel=9,mtime=0)
    if gzip.decompress(new)!=unpacked:
        raise ValueError("Kernel decompression differs after gzip9")
    if len(new)>SPAN:
        raise ValueError("Image.gz crosses original V7.2 ramdisk boundary")
    if sha(new)!=RECOMPRESSED_SHA:
        raise ValueError("Unexpected gzip compressor output, abort")
    return new

def main():
    a=argparse.ArgumentParser()
    a.add_argument("ci_artifact_zip",type=Path)
    a.add_argument("--image-only-output",type=Path)
    args=a.parse_args()
    with zipfile.ZipFile(args.ci_artifact_zip) as z:
        data=z.read("kernel/out/arch/arm64/boot/Image.gz")
    candidate=validate(data)
    print(f"V7.7 gzip9 PASS: {len(data)} -> {len(candidate)} bytes; span {SPAN}; free {SPAN-len(candidate)}")
    if args.image_only_output:
        args.image_only_output.write_bytes(candidate)

if __name__=="__main__":
    main()
