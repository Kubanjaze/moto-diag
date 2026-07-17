# Phase 196 — Bluetooth OBD Adapter Connection — Phase Log

**Status:** 🔄 In progress — build complete (unit layer green); real-dongle
smoke gate pending
**Started:** 2026-05-17 (plan review referenced in ADR-002) | **Completed:** —
**Repos:** `Kubanjaze/moto-diag-mobile` branch `phase-196-bluetooth-obd`
(code); `Kubanjaze/moto-diag` (this ledger doc)

---

### 2026-06-22 18:55 — Bug fix #1: iOS New-Arch flag missing from Podfile (ADR-002 iOS half)

Recorded in full in mobile root `phase_log.md` (commit `8a1f8ee`). Summary:
`ENV['RCT_NEW_ARCH_ENABLED'] = '0'` was never added to `ios/Podfile`, so Mac
`pod install` configured iOS with New Arch ON while `implementation.md` claimed
it disabled — F9 cross-platform-parity family. Fixed at `ios/Podfile:1`.

---

### 2026-07-17 12:05 — Plan doc reconstructed into ledger (labeled)

- Original plan v1.0.2 was never persisted to git (Session Continuity rule 3
  breach caught during today's Mac session; confirmed absent at `8e58e69` /
  `9c3bef2`). `196_implementation.md` v1.0 written as an explicitly-labeled
  reconstruction from ROADMAP row 196, in-code plan references, Bug fix #1,
  ADR-002, and the shipped code + 54-test unit layer.
- Two deltas vs the informal plan summary flagged: init sequence is FOUR
  commands (`ATZ/ATE0/ATL0/ATSP0`), and a distinct `handshaking` state exists.
- Next milestone: real-dongle BLE smoke on a fresh New-Arch-disabled device
  build — the ADR-002 reversal-trigger condition #2 evidence event.
