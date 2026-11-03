# RMX2170 performance baseline — read-only measurement

This stage is independent of the SUSFS compatibility lab and **does not change the working Root kernel**.

The one-command script `tools/benchmark_rmx2170.py` collects an objective baseline for Evolution X Android 16 / Realme 7 Pro RMX2170. It uses official Android Debug Bridge (ADB); Root is not required. It does **not** change CPU governors, ZRAM settings, SELinux, kernel tunables, or boot partitions.

## Requirements

- Install [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools).
- Enable USB debugging and authorize your computer.
- Keep the phone unlocked and reasonably cool; do not charge or play a game during comparison.
- Run Python 3.10 or later on the PC.

## Run

```bash
python tools/benchmark_rmx2170.py --runs 10 --cold
```

On Windows with the Python Launcher:

```powershell
py -3 tools\benchmark_rmx2170.py --runs 10 --cold
```

The script uses **Android Settings only** as a reproducible launch workload. `--cold` adds `am force-stop com.android.settings` before each launch; omit `--cold` to benchmark repeated warm starts. It returns to the home screen between trials. No other apps are force-stopped.

It generates a local JSON file (build fingerprint, kernel version, SELinux, thermal service, battery, memory, PSI, ZRAM and swap snapshots) and a CSV file containing launch times. **The files stay on the user's computer** unless explicitly uploaded.

## Interpretation

Use 10 trials on the **same ROM, same app, same cold/warm mode, same screen/battery/thermal conditions** before and after each performance optimization. Compare median and worst cases; do not claim better speed from one run. If thermal throttling or background load differs, repeat. More ZRAM does not increase physical RAM.

This benchmark cannot prove actual CPU latency, gaming frame-time, kernel safety, SUSFS effectiveness, or storage I/O improvements. Those require additional controlled tests.

Current status: V2 Root functionality is reported working on the device. SUSFS and new performance profiles remain **unvalidated** and no performance tuning is enabled in this branch.
