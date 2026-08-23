# Phase 196B — OBD Classic-Bluetooth / MFi Provider — Phase Log

**Status:** 📋 Planned
**Started:** 2026-08-23 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag-mobile` branch `phase-196B-classic-bt-obd`
(code, to be created); `Kubanjaze/moto-diag` (this ledger doc)

---

### 2026-08-23 13:10 — Plan written (Step 0 audit + v1.0)

- **Trigger:** 196 resume session identified the user's owned adapter as an
  OBDLink MX+ (MX201) — classic BT/MFi, invisible to BLE → 196B promoted
  with the MX+ as reference device (ledger `196_phase_log.md` 2026-08-23).
- **Step 0 audit findings:** 196's seam surfaces locked and ready
  (`'classic-bt'` transport reserved; error union's `ble_*` kinds defined as
  local-radio preconditions, reusable); zero existing classic code
  (greenfield within the seam); one shared integration point
  (`useObdConnection` provider default) → regression guard planned;
  candidate dep `react-native-bluetooth-classic` (Android SPP + iOS
  ExternalAccessory) has UNVERIFIED New-Arch compatibility → plan gates the
  build on a compile+call spike, with a scoped custom-TurboModule fallback.
- **MFi note:** OBDLink protocol string not public — pinned at build time
  via `EAAccessoryManager.connectedAccessories[].protocolStrings` probe on
  the paired MX+.
- **Next milestone:** plan commit + push, then Spike Gate.
