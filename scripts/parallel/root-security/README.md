# Root / KernelSU Next / SUSFS / Security track

**Branch:** `v10-parallel-root-security`

## Engineering scope
- Preserve KernelSU Next UAPI 6 and the existing manual-hook integration.
- Audit SUSFS path/uname/logging behavior and its actual enabled-feature mask.
- Preserve SELinux Enforcing and fail-closed behavior.
- Separate supported functionality from unimplemented mount/kstat hiding.

## Current milestone
Adds source checks and a read-only root/security probe. The current feature mask remains 0x301 (path, uname, logging). This branch must not claim mount or kstat hiding is active.

## Acceptance gates
1. KernelSU Next UAPI remains exactly 6.
2. SELinux remains Enforcing.
3. SUSFS reports only features actually compiled and enabled.
4. No root loss, bootloop, app permission regression or false hiding claim.
