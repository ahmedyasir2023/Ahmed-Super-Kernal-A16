#!/usr/bin/env python3
"""RMX2170 V7.6 preflash DRY RUN: NO images or partitions are written.

Given the user's trusted V7.2 OrangeFox ZIP and two CI artifact ZIPs, this
simulates a kernel-only Android boot v2 substitution in RAM. It refuses an
unknown boot, a kernel that crosses its page-span, signed AVB, altered DTB,
ramdisk, hash descriptors or footer. Outputs a JSON report only.

The report is NOT a guarantee of hardware boot, AVB external verification,
battery life, working root, fingerprint, or DT2W.
"""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

V72_BOOT_SHA="afdc040fc98dc03009d1fdab81cba4d8c23f3d1d42e2a0e4a151ee787e326f3a"
V72_KERNEL_SHA="a8ba69d8ae9f5583ee03810d35f25679594e6a519b56454e637dd220e249d822"
V72_RAMDISK_SHA="9907076b0a45ce9afc1fb950d42f860e29e25f02cea3172e3dda288c406bf923"
V72_DTB_SHA="212d8e40f9d3025c92f1c11c2dc40761820dc5310c41bafbc48a88bd39d23af8"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def require(c, reason):
    if not c:
        raise ValueError(reason)

def boot_layout(b):
    require(len(b)==67108864 and b[:8]==b"ANDROID!", "Not the pinned Android boot partition")
    k, r, sec = (struct.unpack_from("<I",b,n)[0] for n in (8,16,24))
    page, vers, rec, hsz, dt = (struct.unpack_from("<I",b,n)[0] for n in (36,40,1632,1644,1648))
    require(page==4096 and vers==2 and hsz==1660, "Unexpected boot v2 header")
    require(10_000_000<k<32_000_000 and 0<r<16_000_000 and dt>0, "Unexpected section sizes")
    require(sec==rec==0, "Second or recovery DTBO payload needs a different validator")
    align=lambda x:(x+page-1)//page*page
    roff=page+align(k); doff=roff+align(r); payload=doff+align(dt)
    require(payload<len(b)-64,"Section size out of bounds")
    return dict(kernel_size=k,ramdisk_size=r,dtb_size=dt,
                kernel_offset=page,ramdisk_offset=roff,dtb_offset=doff,
                payload_end=payload,header_version=vers)

def legacy_sha1(b,layout):
    h=hashlib.sha1()
    for size,offset in (
        (layout["kernel_size"],layout["kernel_offset"]),
        (layout["ramdisk_size"],layout["ramdisk_offset"]),
        (0,None),(0,None),(layout["dtb_size"],layout["dtb_offset"])):
        if offset is not None:
            h.update(b[offset:offset+size])
        h.update(struct.pack("<I",size))
    return h.digest()

def avb_descriptor(b,layout):
    footer=b[-64:]
    magic,major,minor,original,voff,vsize=struct.unpack_from(">4sIIQQQ",footer)
    require(magic==b"AVBf" and major==1 and minor==0,"Unexpected AVB footer")
    require(original==voff==layout["payload_end"],"Unexpected AVB vbmeta offset")
    require(voff+vsize<=len(b)-64,"AVB vbmeta out of bounds")
    vb=b[voff:voff+vsize]
    require(vb[:4]==b"AVB0","AVB magic mismatch")
    require(struct.unpack_from(">I",vb,28)[0]==0,"Signed AVB: no local re-signing supported")
    require(struct.unpack_from(">Q",vb,12)[0]==0,"Expected no auth block")
    desc_off,desc_size=struct.unpack_from(">QQ",vb,96)
    require(desc_off==0 and desc_size>0,"No AVB descriptors")
    aux=vb[256:]
    matches=[]
    n=desc_off
    while n<desc_off+desc_size:
        require(n+16<=len(aux),"Descriptor header out of bounds")
        tag,length=struct.unpack_from(">QQ",aux,n)
        require(length>0 and n+16+length<=len(aux),"Descriptor length invalid")
        if tag==2:
            size=struct.unpack_from(">Q",aux,n+16)[0]
            algo=aux[n+24:n+56].split(b"\0",1)[0]
            pn,sn,dn,flags=struct.unpack_from(">IIII",aux,n+56)
            start=n+16+8+32+16+60
            require(size==voff and algo==b"sha256" and (pn,sn,dn,flags)==(4,32,32,0),
                    "Unexpected hash descriptor")
            require(aux[start:start+4]==b"boot","Not a boot descriptor")
            salt=aux[start+4:start+4+sn]
            digest_pos=voff+256+start+4+sn
            digest=b[digest_pos:digest_pos+dn]
            require(hashlib.sha256(salt+b[:size]).digest()==digest,"Embedded AVB hash mismatch")
            matches.append((salt,digest_pos,size))
        n+=16+length
    require(n==desc_off+desc_size and len(matches)==1,"Unexpected descriptors")
    return matches[0]

def audit(base,oldkernel,newkernel):
    require(sha(base)==V72_BOOT_SHA,"Trusted V7.2 Boot SHA mismatch")
    require(sha(oldkernel)==V72_KERNEL_SHA,"V7.2 CI kernel hash mismatch")
    p=boot_layout(base)
    ko,ro,do=p["kernel_offset"],p["ramdisk_offset"],p["dtb_offset"]
    require(base[ko:ko+p["kernel_size"]]==oldkernel,"V7.2 Boot does not contain CI kernel")
    require(len(newkernel)>12_000_000 and newkernel[:3]==b"\x1f\x8b\x08","Invalid new gzip kernel")
    require(len(newkernel)<=ro-ko,"New kernel crosses ramdisk boundary")
    ramdisk=base[ro:ro+p["ramdisk_size"]]
    dtb=base[do:do+p["dtb_size"]]
    require(sha(ramdisk)==V72_RAMDISK_SHA and sha(dtb)==V72_DTB_SHA,
            "Original Ramdisk/DTB hashes differ from V7.2 baseline")
    require(legacy_sha1(base,p)==base[576:596],"Original Boot header SHA1 invalid")
    salt,digpos,original=avb_descriptor(base,p)

    # Simulate rebuilding the image in RAM; no image output.
    new=bytearray(base)
    new[ko:ro]=newkernel+b"\0"*(ro-ko-len(newkernel))
    struct.pack_into("<I",new,8,len(newkernel))
    newer=boot_layout(new)
    require((newer["ramdisk_offset"],newer["dtb_offset"],newer["payload_end"])==
            (ro,do,p["payload_end"]),"Repacking moves nonkernel sections")
    new[576:596]=legacy_sha1(new,newer)
    new[digpos:digpos+32]=hashlib.sha256(salt+new[:original]).digest()
    require(legacy_sha1(new,newer)==new[576:596],"Repacked legacy SHA1 mismatch")
    avb_descriptor(new,newer)
    require(new[ro:p["payload_end"]]==base[ro:p["payload_end"]],"Ramdisk or DTB altered")
    require(new[-64:]==base[-64:],"AVB footer altered")
    lhs,rhs=bytearray(base[:4096]),bytearray(new[:4096])
    for off,n in ((8,4),(576,20)):
        lhs[off:off+n]=rhs[off:off+n]
    require(lhs==rhs,"Unexpected header change")
    lhs,rhs=bytearray(base[p["payload_end"]:]),bytearray(new[p["payload_end"]:])
    pos=digpos-p["payload_end"]
    lhs[pos:pos+32]=rhs[pos:pos+32]
    require(lhs==rhs,"Unexpected trailing metadata change")

    return {
      "status":"OFFLINE_STRUCTURAL_PASS_ONLY",
      "base_v72_boot_sha256":sha(base),
      "candidate_v76_kernel_sha256":sha(newkernel),
      "hypothetical_boot_sha256":sha(new),
      "old_kernel_size":len(oldkernel),
      "new_kernel_size":len(newkernel),
      "same_kernel_page_span":True,
      "ramdisk_sha256_unchanged":sha(ramdisk),
      "dtb_sha256_unchanged":sha(dtb),
      "boot_header_sha1_verified":True,
      "embedded_unsigned_avb_sha256_verified":True,
      "external_vbmeta_verified":False,
      "hardware_boot_tested":False,
      "flashable_artifact_created":False
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--known-boot-zip",type=Path,required=True)
    ap.add_argument("--v72-ci-zip",type=Path,required=True)
    ap.add_argument("--new-ci-zip",type=Path,required=True)
    ap.add_argument("--report",type=Path)
    a=ap.parse_args()
    with zipfile.ZipFile(a.known_boot_zip) as z:
        boot=z.read("payload/V7-2-TEST-BOOT.img")
    with zipfile.ZipFile(a.v72_ci_zip) as z:
        old=z.read("kernel/out/arch/arm64/boot/Image.gz")
    with zipfile.ZipFile(a.new_ci_zip) as z:
        newer=z.read("kernel/out/arch/arm64/boot/Image.gz")
    result=audit(boot,old,newer)
    output=json.dumps(result,indent=2,sort_keys=True)+"\n"
    print(output,end="")
    if a.report:
        a.report.write_text(output)

if __name__=="__main__":
    main()
