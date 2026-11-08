#!/system/bin/sh
# Read-only root/security snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "SELINUX"; getenforce 2>/dev/null; readp /sys/fs/selinux/enforce
section "KERNEL"; uname -a
section "KERNELSU"; command -v ksud; command -v su; su -v 2>/dev/null
section "MODULE PARAMETERS"; for f in /sys/module/*/parameters/*susfs* /sys/module/*/parameters/*ksu*; do [ -r "$f" ] && { echo "--- $f"; cat "$f" 2>/dev/null; }; done
section "MOUNTS"; grep -E ' /system | /vendor | /data ' /proc/mounts
section "SECURITY LOGS"; dmesg 2>/dev/null | grep -Ei 'selinux|avc: denied|kernelsu|susfs' | tail -n 120
section "END"; echo "Read-only: no SELinux, root or SUSFS setting changed."
