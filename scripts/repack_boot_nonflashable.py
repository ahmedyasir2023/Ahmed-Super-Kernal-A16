#!/usr/bin/env python3
"""Build a NON-FLASHABLE Android boot-image structure test.

This replaces only the compressed kernel payload. It preserves the original
boot header, ramdisk, second stage, recovery DTBO and concatenated DTB bytes.
The embedded AVB footer's unsigned boot hash descriptor is recalculated, but
the separately signed vbmeta.img is never changed. Therefore the output is
strictly a structural test image and MUST NOT be flashed.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def parse_vbmeta(blob: bytes) -> dict:
    if len(blob) < 256 or blob[:4] != b"AVB0":
        raise ValueError("Invalid AVB0 metadata block")
    v = struct.unpack_from(">4sIIQQIQQQQQQQQQQQII", blob, 0)
    return {
        "required_major": v[1], "required_minor": v[2],
        "auth_size": v[3], "aux_size": v[4], "algorithm": v[5],
        "descriptors_offset": v[14], "descriptors_size": v[15],
        "flags": v[17],
    }


def hash_descriptors(blob: bytes):
    h = parse_vbmeta(blob)
    start = 256 + h["auth_size"] + h["descriptors_offset"]
    end = start + h["descriptors_size"]
    if end > len(blob):
        raise ValueError("AVB descriptor range exceeds metadata block")
    p = start
    while p < end:
        if p + 16 > end:
            raise ValueError("Truncated AVB descriptor header")
        tag, size = struct.unpack_from(">QQ", blob, p)
        q = p + 16
        z = q + size
        if z > end:
            raise ValueError("Truncated AVB descriptor payload")
        if tag == 2:
            if size < 116:
                raise ValueError("Short AVB hash descriptor")
            image_size = struct.unpack_from(">Q", blob, q)[0]
            algorithm = blob[q + 8:q + 40].split(b"\0", 1)[0].decode("ascii")
            name_len, salt_len, digest_len, flags = struct.unpack_from(">IIII", blob, q + 40)
            base = q + 116
            name = blob[base:base + name_len]
            salt = blob[base + name_len:base + name_len + salt_len]
            digest_offset = base + name_len + salt_len
            digest = blob[digest_offset:digest_offset + digest_len]
            if digest_offset + digest_len > z:
                raise ValueError("AVB hash descriptor fields exceed payload")
            yield {
                "descriptor_start": p, "payload_start": q, "size": size,
                "image_size_offset": q, "digest_offset": digest_offset,
                "image_size": image_size, "algorithm": algorithm,
                "name": name.decode("ascii"), "salt": salt,
                "digest": digest, "flags": flags,
            }
        p = z


def replace_boot_hash_descriptor(vbmeta: bytes, image: bytes) -> tuple[bytes, dict]:
    info = parse_vbmeta(vbmeta)
    if info["algorithm"] != 0 or info["auth_size"] != 0:
        raise ValueError("Embedded boot vbmeta is signed; refusing to rewrite it")
    matches = [d for d in hash_descriptors(vbmeta) if d["name"] == "boot"]
    if len(matches) != 1:
        raise ValueError(f"Expected one embedded boot hash descriptor, found {len(matches)}")
    d = matches[0]
    if d["algorithm"] != "sha256" or len(d["digest"]) != 32:
        raise ValueError("Unsupported embedded boot hash algorithm")
    updated = bytearray(vbmeta)
    struct.pack_into(">Q", updated, d["image_size_offset"], len(image))
    digest = hashlib.sha256(d["salt"] + image).digest()
    updated[d["digest_offset"]:d["digest_offset"] + 32] = digest
    return bytes(updated), {
        "partition": "boot", "algorithm": "sha256",
        "image_size": len(image), "digest": digest.hex(),
        "salt": d["salt"].hex(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", required=True, type=Path)
    ap.add_argument("--kernel", required=True, type=Path, help="CI Image.gz")
    ap.add_argument("--vbmeta", required=True, type=Path)
    ap.add_argument("--dtbo", required=True, type=Path)
    ap.add_argument("--vbmeta-system", required=True, type=Path)
    ap.add_argument("--dtb-dir", required=True, type=Path, help="Root containing the seven generated DTBs")
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    args = ap.parse_args()

    if args.output.resolve() == args.boot.resolve():
        raise ValueError("Output must not overwrite the original boot image")
    manifest = json.loads(args.manifest.read_text())
    boot = args.boot.read_bytes()
    kernel = args.kernel.read_bytes()
    external_vbmeta = args.vbmeta.read_bytes()
    dtbo = args.dtbo.read_bytes()
    vbmeta_system = args.vbmeta_system.read_bytes()

    # Pin every supplied ROM image to the previously recorded source manifest.
    for label, data, record in (
        ("boot", boot, manifest["boot"]),
        ("dtbo", dtbo, manifest["dtbo"]),
        ("vbmeta", external_vbmeta, manifest["vbmeta"]),
        ("vbmeta_system", vbmeta_system, manifest["vbmeta_system"]),
    ):
        if len(data) != record["bytes"] or sha(data) != record["sha256"]:
            raise ValueError(f"{label} does not match the original ROM manifest")

    if boot[:8] != b"ANDROID!":
        raise ValueError("Original boot image magic is invalid")
    (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr,
     second_size, second_addr, tags_addr, page_size,
     header_version, os_version) = struct.unpack_from("<10I", boot, 8)
    if header_version != 2 or page_size != 4096:
        raise ValueError(f"Expected Android boot header v2/page 4096, got v{header_version}/{page_size}")
    recovery_dtbo_size, recovery_dtbo_offset, header_size = struct.unpack_from("<IQI", boot, 1632)
    dtb_size, dtb_addr = struct.unpack_from("<IQ", boot, 1648)
    if header_size != 1660 or second_size != 0 or recovery_dtbo_size != 0 or recovery_dtbo_offset != 0:
        raise ValueError("Unexpected boot v2 optional component layout; refusing to repack")

    kernel_off = page_size
    ramdisk_off = align(kernel_off + kernel_size, page_size)
    second_off = align(ramdisk_off + ramdisk_size, page_size)
    recovery_dtbo_off = align(second_off + second_size, page_size)
    dtb_off = align(recovery_dtbo_off + recovery_dtbo_size, page_size)
    original_image_size = align(dtb_off + dtb_size, page_size)

    footer = struct.unpack(">4sIIQQQ28s", boot[-64:])
    if footer[0] != b"AVBf" or footer[1:3] != (1, 0):
        raise ValueError("Original boot image has no supported AVB v1.0 footer")
    _, _, _, footer_image_size, vbmeta_offset, vbmeta_size, reserved = footer
    if footer_image_size != original_image_size or vbmeta_offset != original_image_size:
        raise ValueError("Original AVB footer offsets disagree with boot component layout")
    if reserved != bytes(28):
        raise ValueError("Unexpected nonzero AVB footer reserved bytes")
    embedded_vbmeta = boot[vbmeta_offset:vbmeta_offset + vbmeta_size]
    if len(embedded_vbmeta) != vbmeta_size:
        raise ValueError("Embedded AVB metadata is truncated")
    old_hash = [d for d in hash_descriptors(embedded_vbmeta) if d["name"] == "boot"]
    if len(old_hash) != 1:
        raise ValueError("Original embedded AVB metadata has no unique boot hash descriptor")
    if old_hash[0]["image_size"] != original_image_size:
        raise ValueError("Original embedded AVB boot hash descriptor size mismatch")
    if hashlib.sha256(old_hash[0]["salt"] + boot[:original_image_size]).digest() != old_hash[0]["digest"]:
        raise ValueError("Original embedded AVB boot digest does not verify")

    old_kernel = boot[kernel_off:kernel_off + kernel_size]
    ramdisk = boot[ramdisk_off:ramdisk_off + ramdisk_size]
    second = boot[second_off:second_off + second_size]
    recovery_dtbo = boot[recovery_dtbo_off:recovery_dtbo_off + recovery_dtbo_size]
    dtb_blob = boot[dtb_off:dtb_off + dtb_size]
    if sha(old_kernel) != manifest["boot"]["kernel_sha256"]:
        raise ValueError("Original kernel payload does not match manifest")
    if sha(ramdisk) != manifest["boot"]["ramdisk_sha256"]:
        raise ValueError("Original ramdisk does not match manifest")
    if sha(dtb_blob) != manifest["boot"]["dtb_blob_sha256"]:
        raise ValueError("Original DTB blob does not match manifest")
    gzip.decompress(ramdisk)

    new_uncompressed = gzip.decompress(kernel)
    if len(new_uncompressed) < 64 or struct.unpack_from("<I", new_uncompressed, 0x38)[0] != 0x644D5241:
        raise ValueError("New kernel is not a valid ARM64 Image payload")
    if b"Linux version 4.14.336" not in new_uncompressed:
        raise ValueError("New kernel does not identify as Linux 4.14.336")

    # Compare every individual DTB emitted by CI against the exact original boot members.
    expected = {x["path"]: x for x in manifest["original_boot_dtbs"]}
    actual = {p.relative_to(args.dtb_dir).as_posix(): p for p in args.dtb_dir.rglob("*.dtb")}
    if set(actual) != set(expected):
        raise ValueError(f"Generated DTB file set mismatch: expected {sorted(expected)}, got {sorted(actual)}")
    for name, item in expected.items():
        data = actual[name].read_bytes()
        if len(data) != item["size"] or sha(data) != item["sha256"]:
            raise ValueError(f"Generated DTB differs from original Boot: {name}")
        if data[:4] != bytes.fromhex("d00dfeed") or struct.unpack_from(">I", data, 4)[0] != len(data):
            raise ValueError(f"Invalid FDT structure in {name}")
    if sum(x["size"] for x in expected.values()) != dtb_size:
        raise ValueError("Individual DTB sizes do not equal original Boot DTB size")

    # Assemble v2 boot payload, preserving all original non-kernel components.
    header_page = bytearray(boot[:page_size])
    struct.pack_into("<I", header_page, 8, len(kernel))
    new_id = hashlib.sha1()
    for part in (kernel, ramdisk, second, recovery_dtbo, dtb_blob):
        new_id.update(part)
        new_id.update(struct.pack("<I", len(part)))
    header_page[576:608] = new_id.digest() + bytes(12)

    body = bytearray(header_page)
    body.extend(kernel)
    body.extend(bytes(align(len(body), page_size) - len(body)))
    new_ramdisk_off = len(body)
    body.extend(ramdisk)
    body.extend(bytes(align(len(body), page_size) - len(body)))
    body.extend(second)
    body.extend(bytes(align(len(body), page_size) - len(body)))
    body.extend(recovery_dtbo)
    body.extend(bytes(align(len(body), page_size) - len(body)))
    new_dtb_off = len(body)
    body.extend(dtb_blob)
    body.extend(bytes(align(len(body), page_size) - len(body)))

    if new_ramdisk_off != align(page_size + len(kernel), page_size):
        raise AssertionError("New ramdisk offset calculation mismatch")
    if new_dtb_off != align(new_ramdisk_off + ramdisk_size, page_size):
        raise AssertionError("New DTB offset calculation mismatch")
    if len(body) >= len(boot):
        raise ValueError("Repacked boot payload exceeds original partition capacity")

    new_embedded_vbmeta, embedded_report = replace_boot_hash_descriptor(embedded_vbmeta, bytes(body))
    new_footer = struct.pack(">4sIIQQQ28s", b"AVBf", 1, 0, len(body), len(body),
                             len(new_embedded_vbmeta), bytes(28))
    padding_size = len(boot) - len(body) - len(new_embedded_vbmeta) - 64
    if padding_size < 0:
        raise ValueError("Repacked payload plus AVB metadata exceeds original boot partition")
    candidate = bytes(body) + new_embedded_vbmeta
    candidate += bytes(padding_size)
    candidate += new_footer
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(candidate)

    # The external vbmeta is signed and intentionally left untouched. Its boot
    # descriptor still authenticates the old kernel, so this candidate is not flashable.
    ext_info = parse_vbmeta(external_vbmeta)
    ext_boot = [d for d in hash_descriptors(external_vbmeta) if d["name"] == "boot"]
    if len(ext_boot) != 1:
        raise ValueError("Expected one external vbmeta boot descriptor")
    external_digest_matches_original = (
        ext_boot[0]["image_size"] == original_image_size and
        hashlib.sha256(ext_boot[0]["salt"] + boot[:original_image_size]).digest() == ext_boot[0]["digest"]
    )
    external_digest_matches_new = (
        ext_boot[0]["image_size"] == len(body) and
        hashlib.sha256(ext_boot[0]["salt"] + bytes(body)).digest() == ext_boot[0]["digest"]
    )
    if not external_digest_matches_original:
        raise ValueError("External vbmeta boot descriptor did not verify against original boot")
    if external_digest_matches_new:
        raise ValueError("Unexpected: external vbmeta already matches the repacked boot image")

    # Re-open and verify the written candidate's boot header, component payloads and AVB footer.
    out = args.output.read_bytes()
    if len(out) != len(boot) or out[:8] != b"ANDROID!":
        raise ValueError("Repacked candidate has invalid partition size or magic")
    out_kernel_size = struct.unpack_from("<I", out, 8)[0]
    out_ramdisk_size = struct.unpack_from("<I", out, 16)[0]
    out_dtb_size = struct.unpack_from("<I", out, 1648)[0]
    if out_kernel_size != len(kernel) or out_ramdisk_size != ramdisk_size or out_dtb_size != dtb_size:
        raise ValueError("Repacked header component sizes do not match payloads")
    if out[page_size:page_size + len(kernel)] != kernel:
        raise ValueError("Repacked kernel payload differs from CI Image.gz")
    out_ro = align(page_size + out_kernel_size, page_size)
    out_dtb_off = align(out_ro + out_ramdisk_size, page_size)
    if out[out_ro:out_ro + ramdisk_size] != ramdisk or out[out_dtb_off:out_dtb_off + dtb_size] != dtb_blob:
        raise ValueError("Repacked ramdisk/DTB bytes differ from original")
    out_footer = struct.unpack(">4sIIQQQ28s", out[-64:])
    if out_footer[0] != b"AVBf" or out_footer[3] != len(body) or out_footer[4] != len(body):
        raise ValueError("Repacked AVB footer is inconsistent")
    out_vbmeta = out[out_footer[4]:out_footer[4] + out_footer[5]]
    new_desc = [d for d in hash_descriptors(out_vbmeta) if d["name"] == "boot"]
    if len(new_desc) != 1 or hashlib.sha256(new_desc[0]["salt"] + out[:len(body)]).digest() != new_desc[0]["digest"]:
        raise ValueError("Repacked embedded AVB boot digest failed verification")

    report = [
        "Ahmed Super Kernal A16 — BOOT STRUCTURE TEST",
        "STATUS: NON-FLASHABLE. DO NOT FLASH OR INSTALL.",
        f"Original boot SHA-256: {sha(boot)}",
        f"Repacked candidate SHA-256: {sha(candidate)}",
        f"Partition size: {len(candidate)} bytes (unchanged)",
        f"Header version/page size: {header_version}/{page_size}",
        f"Kernel payload: {len(kernel)} bytes; uncompressed {len(new_uncompressed)} bytes",
        f"Kernel release: Linux 4.14.336; ARM64 Image magic verified",
        f"Ramdisk: {ramdisk_size} bytes; byte-for-byte preserved: yes",
        f"DTB blob: {dtb_size} bytes; byte-for-byte preserved: yes",
        f"Individual original DTBs: {len(expected)}; all SHA-256/size checks passed",
        f"New ramdisk offset: {new_ramdisk_off}",
        f"New DTB offset: {new_dtb_off}",
        f"New pre-vbmeta image size: {len(body)}",
        f"Embedded AVB footer/hash descriptor: internally recalculated and verified ({embedded_report['algorithm']})",
        f"External vbmeta flags: 0x{ext_info['flags']:x}",
        "External vbmeta: NOT MODIFIED; its signed boot descriptor still matches the ORIGINAL boot only",
        "External vbmeta boot digest matches candidate: no",
        "AVB signing/re-signing: NOT DONE (no signing key supplied)",
        "Physical device boot test: NOT DONE",
        "Flashable ZIP: NOT CREATED",
        "",
        "This file is only for offline header/ramdisk/DTB/embedded-footer inspection.",
        "It is not a verified install image. Do not use fastboot, recovery, or any flashing tool with it.",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main()
