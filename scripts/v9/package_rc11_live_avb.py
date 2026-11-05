#!/usr/bin/env python3
"""Package V9 RC1.1 by binding exact live RMX2170 AVB hashes.

Inputs: the original RC1 OrangeFox ZIPs and user-supplied vbmeta dumps.
No AVB partition is altered, bundled, flashed, or patched.
All kernel / ramdisk / DTB payload bytes are kept identical.
"""
import argparse
import hashlib
import struct
import zipfile
from pathlib import Path

V8 = "e18a70a5383de73ca8982231d3ce117600b17923b55d6360367a813d52ccb45d"
V9 = "be6aee32892a2217be48287d5c1710ae1d5d67b86c69d6d623e10ac7a9efa653"
DTBO = "97e4041f2bd6541228a1c977fa5ba40d4c4b4dc3a482e588c3892480d16e097b"
OLD = {
    "vbmeta": "4d5141732c6b3df91a55c60b4088be6e2d025a243fa691caf2ac8528c8b24451",
    "vbmeta_system": "ac5372cf528c85d698baa4bf6c98cde09368ec4306909fc123a9227dc9deb7ee",
}
LIVE = {
    "vbmeta": "9d927f1bf9f2e668132da825ad5556c1fe182844ef4714fff22fa7637a1b60a3",
    "vbmeta_system": "d5cd209716d46085a07ff90178b89f2ef9387ee9374222ddc2830d269cae9305",
}
PATCH_MEMBER = "META-INF/com/google/android/update-binary"
BOOT_SIZE = 67108864

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_avb(blob, name):
    assert len(blob) == 65536 and sha(blob) == LIVE[name], "Live AVB hash: " + name
    assert blob[:4] == b"AVB0", "AVB0 header: " + name
    auth_size, aux_size = struct.unpack_from(">QQ", blob, 12)
    algorithm = struct.unpack_from(">I", blob, 28)[0]
    flags = struct.unpack_from(">I", blob, 120)[0]
    assert (auth_size, algorithm, flags) == (576, 2, 3 if name == "vbmeta" else 0)
    assert 256 + auth_size + aux_size <= len(blob)

def check_boot(blob, expected):
    assert len(blob) == BOOT_SIZE and sha(blob) == expected, "Unexpected boot payload"
    assert blob[:8] == b"ANDROID!"
    assert struct.unpack_from("<I", blob, 36)[0] == 4096
    assert struct.unpack_from("<I", blob, 40)[0] == 2
    assert blob[-64:-60] == b"AVBf"

def patch_script(raw):
    script = raw.decode("utf-8")
    assert script.startswith("#!/sbin/sh")
    assert script.count(V8) == 1 and script.count(V9) == 1
    assert script.count(DTBO) == 1
    for name in OLD:
        assert script.count(OLD[name]) == 1
        assert LIVE[name] not in script
        script = script.replace(OLD[name], LIVE[name], 1)
    assert script.count('of="$BOOT"') >= 1
    assert 'check_partition_hash "$VBMETA"' in script
    assert 'check_partition_hash "$VBMETA_SYSTEM"' in script
    return script.replace("V9 RC1", "V9 RC1.1").encode()

README = """Ahmed Super Kernal A16 V9 RC1.1 - live AVB-bound guarded OrangeFox test.
DEVICE: Realme 7 Pro RMX2170. ROM: Evolution X A16 Nov 2, 2026.
STATUS: EXPERIMENTAL - PHYSICAL BOOT NOT YET TESTED. NEVER FLASH ON ANOTHER DEVICE.
The install ZIP requires exact known working V8 Boot, live vbmeta, live
vbmeta_system and dtbo SHA-256 hashes before writing BOOT ONLY.
New Boot is hash-checked before the write and on the partition after the write.
The install ZIP includes an exact V8 Boot for automatic rollback on a detected
post-write mismatch. The separate restore ZIP accepts only exact V9 or V8 Boot.
External vbmeta, vbmeta_system, dtbo, recovery, system, vendor and data are NOT written.
V8 current Boot SHA256: e18a70a5383de73ca8982231d3ce117600b17923b55d6360367a813d52ccb45d
V9 candidate Boot SHA256: be6aee32892a2217be48287d5c1710ae1d5d67b86c69d6d623e10ac7a9efa653
Live vbmeta SHA256: 9d927f1bf9f2e668132da825ad5556c1fe182844ef4714fff22fa7637a1b60a3
Live vbmeta_system SHA256: d5cd209716d46085a07ff90178b89f2ef9387ee9374222ddc2830d269cae9305
Live dtbo SHA256: 97e4041f2bd6541228a1c977fa5ba40d4c4b4dc3a482e588c3892480d16e097b

IMPORTANT: Valid AVB metadata signatures do not establish that a different
kernel image will boot. Android properties report bootloader 'locked'/'green',
which could reflect ROM property spoofing; without bootloader confirmation
there is residual boot risk. No assertion of boot success or AVB compatibility.
Keep an independent V8 Boot backup outside the phone and a working recovery.
Do not use the old V9 RC1 ZIPs. No format, wipe, vbmeta/verity flags changes.
If unexpected state is reported by the installer, STOP; do not bypass guards.
Project: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/pull/18
"""

REPORT = """V9 RC1.1 PACKAGING: exact live AVB hash rebinding only.
Live vbmeta and vbmeta_system full dumps verified by SHA256, 64KiB, AVB0 headers, AVB flags.
RSA-4096/SHA256 signatures independently verified in offline preflight.
Boot V8 and V9 payload bytes unmodified; V8/V9 SHA256 pinned.
All non-updater ZIP binaries byte-for-byte identical to RC1.
No AVB partitions are modified by these ZIPs.
CI kernel build: 42081736260 (PASS); physical boot: NOT TESTED.
Previous failure due to stale hardcoded vbmeta hashes; this release binds the exact dumps.
"""

def repack(src, out, restore):
    with zipfile.ZipFile(src) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        expected = {PATCH_MEMBER, "META-INF/com/google/android/updater-script",
                    "payload/boot-v8.img", "README-AR.txt",
                    "V9-RC1-OFFLINE-VERIFICATION-REPORT.txt"}
        if not restore:
            expected.add("payload/boot-v9.img")
        assert names == expected, names ^ expected
        check_boot(z.read("payload/boot-v8.img"), V8)
        if not restore:
            check_boot(z.read("payload/boot-v9.img"), V9)
        with zipfile.ZipFile(out, "w", allowZip64=False) as w:
            for item in z.infolist():
                data = z.read(item)
                if item.filename == PATCH_MEMBER:
                    data = patch_script(data)
                elif item.filename == "README-AR.txt":
                    data = README.encode()
                elif item.filename == "V9-RC1-OFFLINE-VERIFICATION-REPORT.txt":
                    data = REPORT.encode()
                w.writestr(item, data)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for name in LIVE:
            assert LIVE[name].encode() in z.read(PATCH_MEMBER)
            assert OLD[name].encode() not in z.read(PATCH_MEMBER)
        check_boot(z.read("payload/boot-v8.img"), V8)
        if not restore:
            check_boot(z.read("payload/boot-v9.img"), V9)
    print(out.name, out.stat().st_size, sha(out.read_bytes()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", type=Path, required=True)
    ap.add_argument("--restore", type=Path, required=True)
    ap.add_argument("--vbmeta", type=Path, required=True)
    ap.add_argument("--vbmeta-system", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    check_avb(a.vbmeta.read_bytes(), "vbmeta")
    check_avb(a.vbmeta_system.read_bytes(), "vbmeta_system")
    a.output_dir.mkdir(parents=True, exist_ok=True)
    repack(a.install, a.output_dir / "Ahmed-Super-Kernal-A16-V9-RC1.1-LIVE-AVB-OrangeFox-GUARDED-TEST.zip", False)
    repack(a.restore, a.output_dir / "Ahmed-Super-Kernal-A16-V9-RC1.1-LIVE-AVB-OrangeFox-RESTORE-V8.zip", True)

if __name__ == "__main__":
    main()
