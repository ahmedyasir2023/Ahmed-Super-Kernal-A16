# Network Stack / Radio Wakeups track

**Branch:** `v10-parallel-network-stack`

## Engineering scope
- Audit TCP/IP packet processing, network wakeup sources and screen-off radio activity.
- Separate kernel networking effects from vendor WLAN, modem, firmware and Android connectivity services.
- Preserve normal Wi-Fi/mobile-data reconnect behavior after screen wake.

## Current milestone
Adds source checks and a read-only network probe. No TCP congestion-control default, WLAN driver, modem firmware or radio power policy is changed at this stage.

## Acceptance gates
1. Wi-Fi and mobile data reconnect reliably after suspend/resume.
2. No packet loss, DNS delay or app-offline regression.
3. No vendor WLAN/modem driver or firmware replacement.
4. Screen-off radio wakeups are attributed before any suppression is considered.
