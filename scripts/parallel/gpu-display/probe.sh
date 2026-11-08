#!/system/bin/sh
# Read-only GPU/display snapshot. Run as root; redirect output to a file.
section(){ printf '\n===== %s =====\n' "$1"; }
readp(){ [ -r "$1" ] && { echo "--- $1"; cat "$1" 2>/dev/null; } || echo "--- $1: unavailable"; }
section "KGSL"; for f in /sys/class/kgsl/kgsl-3d0/gpuclk /sys/class/kgsl/kgsl-3d0/gpubusy /sys/class/kgsl/kgsl-3d0/gpu_busy_percentage /sys/class/kgsl/kgsl-3d0/max_gpuclk /sys/class/kgsl/kgsl-3d0/min_gpuclk; do readp "$f"; done
section "GPU DEVFREQ"; for d in /sys/class/devfreq/*gpu* /sys/class/devfreq/*kgsl*; do [ -d "$d" ] || continue; for f in name cur_freq min_freq max_freq available_frequencies governor; do readp "$d/$f"; done; done
section "DISPLAY"; for f in /sys/class/drm/card0-*/status /sys/class/drm/card0-*/modes /sys/class/graphics/fb0/blank; do readp "$f"; done
section "THERMAL"; for f in /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp; do readp "$f"; done
section "END"; echo "Read-only: no GPU frequency or display mode changed."
