# Phase 197 — Live Sensor Data Dashboard (Mobile)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-08-25
*(v1.1: build complete + unit-verified same day (`48d2fbc`). Results,
Deviations, checklist below; device smoke is the remaining unticked gate.)*

## Existing-code audit (Step 0 — run 2026-08-25, before this plan)

- **Substrate (196/196B locked, immutable):** `ObdProvider.writeCommand`
  is the transport-neutral request/response seam — STRICTLY SEQUENTIAL
  (single pending slot; concurrent commands reject loudly). Both shipped
  providers (BLE `BleObdProvider`, classic/MFi `ClassicBtObdProvider`)
  smoke-verified; connection lifecycle owned by `useObdConnection` +
  `obdConnectionMachine` (`connected` state carries device + banner).
- **Backend substrate (SSOT for PID semantics):** `motodiag/hardware/
  sensors.py` (Phase 141) is the canonical SAE J1979 Mode 01 catalog —
  `SensorSpec(pid, name, unit, byte_count, decoder)`: 0x05 coolant
  (`raw-40` °C), 0x0C RPM (`raw/4`), 0x0D speed (identity km/h), 0x0F
  intake temp (`raw-40`), 0x11 throttle (`raw*100/255` %), plus the
  supported-PID bitmask convention (0100). The mobile catalog MIRRORS
  these names/units/formulas — a divergent vocabulary would be F9 SSOT
  drift; a unit test pins the mobile table against the backend's values.
- **Mobile greenfield check:** no PID/gauge/dashboard code exists in
  `src/` (broad-noun grep = noise only). New isolated modules + one screen.
- **User decisions (2026-08-25):** core-six gauge set · grid + swipe pages
  + landscape · iOS background mode DEFERRED (screen-on only; follow-up
  filed, pairs with 198 logging) · branch `phase-197-live-sensor-dashboard`
  off freshly-merged main (`5519495`; 196+196B stack merged, 804 green).

## Goal

Turn the smoked OBD link into the product's first live-data feature: a
real-time gauge dashboard (grid of compact gauges, swipeable pages,
landscape support) polling the core six channels — RPM, speed, coolant
temp, throttle %, intake temp, battery voltage — over whichever transport
is connected. Screen-on only (no background entitlement this phase).
Vendor-app dashboards (OBDLink) are the UX reference; data surface is
standard J1979, equitable across motorcycles and cars — the supported-PID
probe adapts the dashboard to what each bike actually exposes.

Run (no CLI — mobile phase):
- Unit layer: `npx jest __tests__/obd/ __tests__/screens/`
- Device smoke: connected MX+ (or BLE adapter) → Live Data → gauges move
  with the engine.

Outputs (mobile repo, branch `phase-197-live-sensor-dashboard`):
- `src/obd/pids.ts` — Mode 01 catalog mirror (core six + bitmask decode):
  PID hex command builder (`010C` etc.), response parser (`41 0C …`),
  per-PID decoder, unit + display name — pinned to backend semantics
- `src/obd/pidPoller.ts` — sequential round-robin scheduler over
  `writeCommand` (respects the single-slot channel; configurable tick;
  skips unsupported PIDs; ATRV interleave for voltage; error-tolerant per
  reading — one bad PID never kills the loop)
- `src/hooks/useLiveSensorData.ts` — hook: supported-probe on start
  (0100 bitmask), start/stop polling, latest `SensorReading[]` + staleness
- `src/screens/LiveDataScreen.tsx` — gauge grid + swipe pages + landscape;
  entry from the OBD connected state ("Live data" button)
- `src/components/SensorGauge.tsx` — single gauge (value, unit, name,
  stale/unsupported states)
- Tests: pids decode table (cross-checked against backend canonical
  values), poller scheduling/error-tolerance vs FakeObdProvider, hook
  lifecycle, screen smoke + wiring guard (connected-state button →
  LiveDataScreen wired in navigator)

## Logic

- **Supported probe:** on dashboard mount with a connected provider, send
  `0100` → 32-bit bitmask → intersect with the core six; unsupported
  gauges render "n/a" (motorcycles expose subsets — probe, don't assume).
- **Polling:** round-robin one PID per `writeCommand` round trip
  (sequential seam!), default ~2 Hz full-cycle target; each reading
  timestamped; a failed/`?` response marks that gauge stale and continues.
  Voltage via `ATRV` (ELM adapter command, not a PID) in the rotation.
- **Parsing:** `41 <pid> <bytes…>` hex → int → catalog decoder → value +
  unit. Malformed/NO DATA → per-reading error, no throw out of the loop.
- **Screen:** gauges in a responsive grid (portrait 2-col / landscape
  3-col), swipeable pages when gauges exceed a page, banner + transport
  badge from the connected state; leave-screen stops the poller
  (useEffect cleanup) — no background polling this phase.
- **Navigation:** button on ObdConnectScreen's `connected` pane →
  `LiveData` route (HomeStack). Wiring guard test pins it.

## Key Concepts

- **SSOT mirror discipline (191D):** mobile catalog values cross-checked
  in tests against the backend's canonical examples (RPM `0x1AF8 → 1726`,
  coolant `0x5A → 50 °C`, throttle formula `*100/255`); names/units copied
  verbatim from `sensors.py`.
- **Sequential-channel scheduling:** the 196B provider REJECTS concurrent
  commands by design; the poller is the one caller and owns the cadence.
- **Transport-agnostic by construction:** poller/hook/screen depend on
  `ObdProvider` only — works identically over BLE and classic (and 196C
  Wi-Fi later) with zero edits (seam property, again).
- **Echo/headers variance (Risk):** handshake already ran ATE0/ATL0; the
  parser still tolerates echoed command prefixes and whitespace (clone
  variance, same tolerance philosophy as banner matching).
- **Deferred:** iOS background polling entitlement (follow-up filed with
  198), per-user gauge selection (196-era FOLLOWUPS style), imperial units
  toggle.

## Verification Checklist

- [x] pids.ts decode table green, cross-checked against backend canonical
      values (RPM 0x1AF8→1726, coolant 0x5A→50 °C, throttle, speed, intake,
      bitmask, ATRV) — 17 tests
- [x] Poller: round-robin order, NEVER-overlaps guard (single-slot
      contract), per-reading error tolerance, channel-death surfacing,
      idempotent start / clean stop — 8 tests vs scripted provider
- [x] Hook surface exercised via screen smoke (mocked-hook render states)
      + wiring guard (holder publish on connected, clear on unmount)
- [x] Screen smoke: not-connected pane, live values + banner + transport
      label, unsupported n/a, stale tag, link-error banner — 6 tests
- [x] Wiring guard: connected-pane "Live data" button → navigate('LiveData')
      + holder populated/cleared (ObdConnect.smoke)
- [x] Full mobile regression: 65 suites / 837 tests green; tsc clean
- [x] Device smoke (2026-09-02, car ECU — protocol-identical J1979; the
      stronger functional check since all six channels exercise): engine
      running — RPM and voltage responding, coolant + intake temps correct,
      throttle tracking, vehicle speed moved while driving. No n/a on this
      vehicle (full core-six support). Motorcycle subset/n-a-path
      verification filed as **F49** (deterministic Step-0 watcher).

## Deviations from Plan

- **Cross-screen provider handoff via `activeObdConnection` holder module**
  (not in v1.0): providers are stateful class instances and cannot ride
  navigation params (non-serializable). A tiny module-level slot +
  subscribe replaced the implicit assumption that LiveData could reach the
  provider; ObdConnectScreen publishes on `connected`, clears otherwise
  and on unmount. Guarded by the wiring test.
- **SEARCHING-preamble framing fix (build-phase):** the initial marker
  parity guard broke on "SEARCHING…" residue ("E/A/C" survive hex
  cleaning); parity requirement dropped — only post-marker bytes matter.
  Caught by the phase's own tolerance tests pre-commit.
- **Hook-level unit test folded into screen tests:** useLiveSensorData is
  exercised through the LiveData/ObdConnect smoke layers (mocked-hook
  render states + real holder lifecycle) rather than a standalone
  hook-harness file — same coverage, one less harness.

## Results

| Metric | Value |
|--------|-------|
| New modules | pids.ts, pidPoller.ts, activeObdConnection.ts, useLiveSensorData.ts, SensorGauge.tsx, LiveDataScreen.tsx |
| New tests | +33 (catalog 17, poller 8, LiveData smoke 6, wiring guards 2) |
| Full regression | 65 suites / 837 tests, 0 failures; tsc clean |
| Build commit | `48d2fbc` (13 files, +1342) |

Key finding: the sequential-channel constraint from 196B turned out to be
a feature — the poller's awaited round-robin gives adaptive cadence for
free, and the same loop runs unmodified over BLE, classic, and future
Wi-Fi (third consecutive proof of the seam).

## Risks

- **Motorcycle PID coverage varies wildly** — mitigated by the 0100 probe
  + n/a states; the smoke bike may expose as few as 2-3 of the six.
- **Slow adapters vs 2 Hz ambition:** classic MX+ round trips are fast
  (~50-100 ms) but cheap BLE clones aren't — cadence is adaptive (next
  tick starts when the previous answers), never fixed-rate.
- **ATRV is ELM-specific** (adapter, not ECU) — if a future transport
  lacks it, voltage gauge degrades to n/a (already handled by design).
- **Engine-off smoke:** ignition-on/engine-off yields RPM 0 + static
  values — fine for the gate; note reading provenance in the record.
