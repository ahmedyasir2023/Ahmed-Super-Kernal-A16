#!/usr/bin/env python3
"""Synthetic-only tests: never bundle user boot images or device secrets."""
import hashlib
import importlib.util
import struct
import unittest
from pathlib import Path

source=Path(__file__).resolve().parents[1]/"scripts/release/ay_v76_preflash_dryrun.py"
spec=importlib.util.spec_from_file_location("ay_preflash",source)
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def fixture():
    image=bytearray(64*1024*1024)
    page=4096
    kernel_size=19_645_357
    ramdisk_size=128*1024
    dtb_size=128*1024
    image[:8]=b"ANDROID!"
    for off,value in ((8,kernel_size),(16,ramdisk_size),(24,0),(36,page),
                      (40,2),(1632,0),(1644,1660),(1648,dtb_size)):
        struct.pack_into("<I",image,off,value)
    layout=audit.boot_layout(image)
    image[576:596]=audit.legacy_sha1(image,layout)
    vbstart=layout["payload_end"]
    vb=bytearray(704)
    vb[:4]=b"AVB0"
    struct.pack_into(">Q",vb,20,448) # auxiliary block bytes
    struct.pack_into(">QQ",vb,96,0,200) # descriptors_offset, size
    tag=256
    struct.pack_into(">QQ",vb,tag,2,184)
    struct.pack_into(">Q",vb,tag+16,vbstart)
    vb[tag+24:tag+30]=b"sha256"
    struct.pack_into(">IIII",vb,tag+56,4,32,32,0)
    data=tag+16+8+32+16+60
    vb[data:data+4]=b"boot"
    salt=b"X"*32
    vb[data+4:data+36]=salt
    vb[data+36:data+68]=hashlib.sha256(salt+image[:vbstart]).digest()
    image[vbstart:vbstart+len(vb)]=vb
    struct.pack_into(">4sIIQQQ",image,len(image)-64,b"AVBf",1,0,
                     vbstart,vbstart,len(vb))
    return image,layout

class TestPreflash(unittest.TestCase):
    def test_layout_and_legacy_id(self):
        boot,p=fixture()
        self.assertEqual(p["header_version"],2)
        self.assertEqual(audit.legacy_sha1(boot,p),boot[576:596])
        self.assertTrue(p["ramdisk_offset"]>p["kernel_offset"])
        self.assertEqual(p["dtb_offset"]%4096,0)

    def test_valid_unsigned_avb(self):
        boot,p=fixture()
        salt,offset,length=audit.avb_descriptor(boot,p)
        self.assertEqual(salt,b"X"*32)
        self.assertEqual(length,p["payload_end"])
        self.assertEqual(len(boot[offset:offset+32]),32)

    def test_avb_tamper_rejected(self):
        boot,p=fixture()
        boot[p["dtb_offset"]]^=1
        with self.assertRaises(ValueError):
            audit.avb_descriptor(boot,p)

    def test_signed_avb_rejected(self):
        boot,p=fixture()
        struct.pack_into(">I",boot,p["payload_end"]+28,1)
        with self.assertRaises(ValueError):
            audit.avb_descriptor(boot,p)

    def test_header_mismatch_rejected(self):
        boot,p=fixture()
        struct.pack_into("<I",boot,40,3)
        with self.assertRaises(ValueError):
            audit.boot_layout(boot)

    def test_bad_footer_rejected(self):
        boot,p=fixture()
        boot[-64:-60]=b"XXXX"
        with self.assertRaises(ValueError):
            audit.avb_descriptor(boot,p)

if __name__=="__main__":
    unittest.main(verbosity=2)
