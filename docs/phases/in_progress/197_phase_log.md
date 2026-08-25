# Phase 197 — Live Sensor Data Dashboard — Phase Log

**Status:** 📋 Planned
**Started:** 2026-08-25 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag-mobile` branch `phase-197-live-sensor-dashboard`
(code); `Kubanjaze/moto-diag` (this ledger doc)

---

### 2026-08-25 12:05 — Plan written (Step 0 audit + v1.0)

- **Pre-work:** 196+196B stack merged to main (`5519495`, union-resolved
  phase_log.md conflict with the 2026-06-13 Mac-provisioning entry; 804-test
  regression green on merged main). Branch cut from clean main.
- **Step 0 findings:** mobile PID/gauge layer is greenfield within the
  seam; backend `hardware/sensors.py` (Phase 141) is the canonical J1979
  catalog — mobile MIRRORS it (names/units/decoders pinned by test, F9-SSOT
  discipline); `writeCommand` seam is strictly sequential → poller owns
  cadence, round-robin, adaptive rate.
- **User decisions:** core-six gauges (RPM/speed/coolant/throttle/intake/
  voltage-via-ATRV) · grid + swipe + landscape (OBDLink app as UX
  reference; standard J1979 data is vehicle-equitable) · iOS background
  mode DEFERRED (screen-on only; follow-up pairs with 198) · merged-main
  branch base.
- **Next milestone:** plan commit + push, then build (pids.ts → poller →
  hook → screen → wiring guard), then device smoke with the MX+.
