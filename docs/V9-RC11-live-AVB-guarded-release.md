# V9 RC1.1 — corrected RMX2170 live AVB installer

**Status: experimental recovery test only. No physical boot verified.**

The original V9 RC1 OrangeFox install aborted safely before writing because its preflight expected vbmeta and vbmeta_system from a stale stock-ROM manifest. Read-only commands and the user's own 64 KiB partition dumps established the real live SHA-256 values. Do not remove exact-state guards.

## Pinned SHA-256 images

| Image | SHA-256 |
|---|---|
| Known-working V8 Boot (64 MiB) | e18a70a5383de73ca8982231d3ce117600b17923b55d6360367a813d52ccb45d |
| V9 candidate Boot (64 MiB) | be6aee32892a2217be48287d5c1710ae1d5d67b86c69d6d623e10ac7a9efa653 |
| Live vbmeta (64 KiB) | 9d927f1bf9f2e668132da825ad5556c1fe182844ef4714fff22fa7637a1b60a3 |
| Live vbmeta_system (64 KiB) | d5cd209716d46085a07ff90178b89f2ef9387ee9374222ddc2830d269cae9305 |
| Live dtbo | 97e4041f2bd6541228a1c977fa5ba40d4c4b4dc3a482e588c3892480d16e097b |
| CI V9 Image.gz | 608e16a182375662e119c25a765c174a6d749805ca0a2c8ed0aba844356c43f9 |

Verified offline using the actual user-extracted vbmeta files: both signed RSA-4096/SHA256 image signatures and signed hash fields validate. Top-level vbmeta has header flags 0x3 and contains a vbmeta_system chain descriptor; chained vbmeta_system flags 0x0 and the embedded public keys match. Its boot hash descriptor corresponds to a different historical boot image; it does not independently validate V8 or V9. Android getprop reported locked/green/enforcing while booting modified V8, so actual bootloader behavior remains unverified.

The previous stock manifest's 8 KiB/4 KiB image sizes and hashes must not be used as installation gates for this device. The new installer checks actual whole-partition SHA-256 values and writes **BOOT ONLY**; it never changes AVB, dtbo, system, vendor, recovery or data partitions.

## Corrected test ZIPs generated from user-provided inputs

- Install: Ahmed-Super-Kernal-A16-V9-RC1.1-LIVE-AVB-OrangeFox-GUARDED-TEST.zip
  - SHA-256: fdd829c946d2b28d70c763324874a60b7cb46be551f8c1339eb8360b49a7c9b9
- Restore: Ahmed-Super-Kernal-A16-V9-RC1.1-LIVE-AVB-OrangeFox-RESTORE-V8.zip
  - SHA-256: b5ccb3f374ecda3adc708b7e82050ad890ba0ac8bb04c34f3933a401d94f777e

The ZIP binary payloads are not published in this public Git repository. The source includes scripts/v9/package_rc11_live_avb.py as a reproduction utility accepting previous RC1 ZIPs and the actual extracted vbmeta files. The complete Boot and vbmeta files are intentionally not placed in source control.

**Only preflight AVB hashes and accompanying report/readme text changed.** The embedded V8 and V9 Boot images remained byte-for-byte identical to the earlier RC1 packages. No new kernel build is necessary.

### Host-side testing

- Both ZIP CRC checks passed.
- The embedded Boot images matched pinned SHA-256 and were identical to RC1.
- Shell syntax checks passed.
- Simulated exact V8 to V9 install passed; simulated exact V9 to V8 restore passed.
- Wrong vbmeta and unknown Boot states failed closed without writing.
- Simulated short write triggered automatic rollback and verified exact V8.
- Physical OrangeFox and hardware boot tests are **NOT TESTED**.

The previous RC1 install and restore packages are withdrawn: never flash them. Retain an independent working V8 backup. A successful mock install is not a guarantee that the bootloader will accept V9, that hardware will boot, or that fingerprint/DT2W/root will work.

CI build: https://github.com/ahmedyasir2023/Ahmed-Super-Kernal-A16/actions/runs/42081736260
