# Phase 196 — Bluetooth OBD adapter connection

**Version:** 1.0 (plan — written before any code) | **Tier:** Standard | **Date:** 2026-05-17

> **Track I phase.** Phase 196 is the next phase in the locked sequence (195B → 195C → 196). Per `ROADMAP_AUTHORITY.md`, 196 is in the 185–204 range — a Track I phase — so its per-phase status is recorded in `Kubanjaze/moto-diag-mobile/docs/ROADMAP.md`; this per-phase doc lives in the backend ledger (`Kubanjaze/moto-diag/docs/phases/`) per the same contract. The work itself is **mobile-only** (see Logic + the F33 audit).

## Goal

Phase 196 ships the Bluetooth OBD-II adapter connection layer for the mobile app: scan for nearby BLE OBD-II dongles, connect, and complete the ELM327 protocol handshake so the app holds a live, identified OBD link. It extends the Phase 186 `BleService` substrate with an OBD-specific `ObdConnection` abstraction + connection UX, gated behind an `OBD_SUPPORT` feature flag for phased release. This is the first phase that touches physical diagnostic hardware from the phone — the foundation Phase 197 (live sensor dashboard) and later OBD-data phases build on.

**Surface (mobile only):** a new OBD-adapter scan/connect screen; `useObdConnection` hook; `OBD_SUPPORT` feature flag. No backend surface — the backend Track E `hardware/` package is the separate desktop/CLI serial-port OBD path; mobile↔backend OBD-data integration is a later-phase concern (out of scope here, see F33 audit).

**Outputs:**
- `src/obd/ObdConnection.ts` — OBD-specific connection abstraction over `BleService` (ADR-001's anticipated `ObdConnection` provider seam).
- `src/obd/elm327.ts` — the ELM327 AT-command handshake/init sequence + response parsing.
- `src/obd/obdErrors.ts` — typed `ObdConnectionError` discriminated union.
- `src/obd/obdConnectionMachine.ts` — connection state machine.
- `src/hooks/useObdConnection.ts` — React hook surfacing connection state to screens.
- `src/screens/ObdConnectScreen.tsx` — scan list + connect + connection-status UX.
- `src/config/features.ts` (or equivalent) — `OBD_SUPPORT` feature flag.
- iOS `Info.plist` + Android `AndroidManifest.xml` — BLE permission/usage-description keys (cross-platform parity — see Risks).
- `__tests__/` coverage for all of the above (BLE mocked).

## Logic

### Step 1 — OBD-specific connection over the Phase 186 `BleService`

`src/ble/BleService.ts` already exists (Phase 186 stub, 72 LoC): a singleton `react-native-ble-plx` wrapper with `waitForPoweredOn()` / `scan()` / `stopScan()` / `connect()` (does `discoverAllServicesAndCharacteristics()`) / `disconnect()` / `destroy()`. Phase 196 **extends, does not replace** it. New `ObdConnection` wraps `bleService`:
- after `bleService.connect(deviceId)`, locate the BLE serial service + its notify/write characteristics (common ELM327-over-BLE UUIDs — e.g. the `FFE0`/`FFE1` vendor-serial pair and the Nordic-UART-style pairs that ELM327 clones expose; the rule does not hardcode one — it probes the discovered characteristic set for a writable + a notifiable characteristic).
- expose `writeCommand(cmd) -> Promise<string>` — write an AT/OBD command, accumulate notify-characteristic chunks until the ELM327 `>` prompt terminator, return the response.

### Step 2 — ELM327 protocol handshake (`elm327.ts`)

On connect, run the ELM327 init sequence: `ATZ` (reset) → `ATE0` (echo off) → `ATL0` (linefeeds off) → `ATSP0` (auto protocol). Read each response; confirm the adapter identifies as an ELM327 (the `ATZ` response carries an `ELM327 v…` banner — or a clone's variant). A handshake that does not yield a recognizable ELM identifier → `handshake_failed`. The handshake establishes the link is a genuine OBD adapter before the screen reports "connected."

### Step 3 — connection state machine + screen

`obdConnectionMachine.ts` — a reducer with states `idle → scanning → connecting → handshaking → connected` plus `failed` (carrying the typed error) and `disconnected`. `ObdConnectScreen.tsx` drives it: a scan button → device list (filtered to likely OBD adapters by advertised name / service), tap-to-connect, live status, disconnect. Mirrors the Phase 191/194/195 capture-machine + screen pattern (reducer + screen + hook), which the F33 audit confirms transfers directly.

### Step 4 — `OBD_SUPPORT` feature flag

ADR-001 specified an `OBD_SUPPORT` flag for phased release — OBD is the riskiest native surface and should be dark-launchable. Phase 196 introduces it: a single config constant gating the `ObdConnectScreen` nav entry + any OBD affordance. Default for this phase: **on in dev, off in release builds** until the device smoke gate (Step 6) passes.

### Step 5 — typed errors

`obdErrors.ts` — `ObdConnectionError` discriminated union mirroring the Phase 190/192B typed-error pattern: `ble_powered_off` / `ble_unauthorized` / `ble_unsupported` / `device_not_found` / `connect_failed` / `handshake_failed` / `disconnected_unexpectedly`. Each maps to user-facing copy.

### Step 6 — verification + the device-gated gate

The **build is device-independent**: `react-native-ble-plx` is mockable, and `BleService` is already a thin wrapper — `ObdConnection`, `elm327` handshake, the state machine, error mapping, and the screen are all unit-testable against a mocked BLE layer with zero hardware. The **architect smoke gate is device-gated**: scan + connect + handshake against a *real* OBD-II dongle requires a physical device + adapter. That smoke is also exactly **ADR-002's reversal-trigger condition #2** — so it is run once, against the real dongle, when a device session is available (see Risks + the pre-plan Q&A).

## Key Concepts

- **`react-native-ble-plx`** — `BleManager`, `Device`, `Characteristic`; `monitorCharacteristicForService` for notify chunks; `writeCharacteristicWithResponse`/`...WithoutResponse` for commands. Already installed (`^3.5.1`) + wrapped by `BleService` (Phase 186).
- **ELM327 AT-command protocol** — text commands terminated by `\r`; responses terminated by the `>` prompt; the `ATZ` banner identifies the adapter. Clones vary — the handshake is tolerant (recognizes the family, does not demand an exact version string).
- **BLE serial service discovery** — ELM327-over-BLE dongles expose a writable + a notifiable characteristic under a vendor service; the connection probes rather than hardcodes a UUID.
- **Connection state machine** — reducer pattern, same idiom as `videoCaptureMachine` / `audioCaptureMachine` (Phases 191/195).
- **`OBD_SUPPORT` feature flag** — phased-release gate (ADR-001).
- **ADR-002** — New Architecture stays OFF (its reversal trigger is unmet — see pre-plan Q&A); Phase 196 builds on the status-quo Old-Arch + `ble-plx` setup.

## F33 existing-code-overlap audit

Ran the Step-0 audit across both repos before this plan was written. **Phase 196 is extension territory, not greenfield** — the plan is framed as extension from the start.

| Surface | State | 196 disposition |
|---|---|---|
| `moto-diag-mobile` `src/ble/BleService.ts` | **Exists** — Phase 186 stub (`1c3b165`), 72 LoC: singleton `ble-plx` wrapper, `waitForPoweredOn`/`scan`/`stopScan`/`connect`+discovery/`disconnect`/`destroy`. | **Extend.** `ObdConnection` wraps `bleService`; no rewrite. |
| `react-native-ble-plx@^3.5.1` | **Installed** (Phase 185/186 per ADR-001). | Reuse — no new dependency. |
| `ObdConnection` provider seam / `OBD_SUPPORT` flag | **Anticipated by ADR-001, never built** — no stub exists. | **New** (greenfield on top of `BleService`). |
| `moto-diag` `src/motodiag/hardware/` (Track E: `connection.py`, `ecu_detect.py`, `protocols/`, `compat_data/`) | **Exists** — the **desktop/CLI serial-port** OBD path (Phases 134–147). | **Separate transport — not consumed by 196.** Mobile 196 is BLE-to-dongle; the backend hardware package is serial-port-to-adapter. ADR-001 deliberately gave mobile its own `ObdConnection` seam. No coupling; backend integration of mobile-captured OBD data is a later phase. |
| ADR-002 (`docs/adr/002-…`) | New Arch OFF, gated on `ble-plx` #1277 + a real-dongle smoke. | 196 builds New-Arch-OFF; no flip (see pre-plan Q&A). |

**Conclusion:** extension of `BleService`; new `ObdConnection`/handshake/screen/flag layer on top; zero new dependency; zero backend change. No reshape — plan written as extension from line one.

## Pre-plan Q&A (for architect review)

- **Q1 — ADR-002 "flip" (raised at 196 kickoff).** *Resolved, not open.* ADR-002 defines its own reversal trigger: flip New Architecture ON only when (1) `react-native-ble-plx` ships New-Arch support **and** (2) a real-dongle scan+connect smoke passes. Neither holds today. **Recommendation: Phase 196 does NOT flip ADR-002** — it builds on the status-quo Old-Arch + `ble-plx@3.5.1` setup. The flip is a separate future event when the ADR's trigger fires; 196's own device smoke (Step 6) will be the first half of that trigger's evidence, but flipping is out of 196 scope. Architect to confirm.
- **Q2 — backend integration scope.** 196 is proposed as **mobile-only**: scan/pair/connect/handshake, ending at "a live identified OBD link." Reading DTCs/PIDs over that link, and shipping them to a diagnostic session / the backend, is deferred (Phase 197+ territory). Confirm 196 stops at the connection layer.
- **Q3 — device-gated gate.** The build is device-independent (BLE mocked); only the architect smoke gate needs a physical device + dongle. Confirm the phase may **build + unit-verify to completion now**, with the real-dongle smoke gate held as the one device-blocked step (run when a device session is available — and counted toward ADR-002's reversal evidence).
- **Q4 — adapter scope.** ELM327 (+ common clones) over BLE is the target. Wi-Fi OBD adapters and classic-Bluetooth (non-BLE) adapters are explicitly out of scope. Confirm.

## Verification Checklist

- [ ] `ObdConnection` wraps the existing `BleService` singleton; `BleService.ts` itself is unchanged or only additively extended.
- [ ] BLE serial service/characteristic discovery probes the discovered set (writable + notifiable) rather than hardcoding a single vendor UUID.
- [ ] `elm327.ts` runs the `ATZ`/`ATE0`/`ATL0`/`ATSP0` init sequence; recognizes the ELM327 family banner tolerantly; a non-ELM response → `handshake_failed`.
- [ ] `obdConnectionMachine` covers `idle/scanning/connecting/handshaking/connected/failed/disconnected`; unexpected disconnect transitions to `failed`.
- [ ] `ObdConnectScreen` — scan → device list → connect → live status → disconnect; OBD-adapter filtering on the scan list.
- [ ] `ObdConnectionError` typed union (7 kinds) + user-facing copy for each.
- [ ] `OBD_SUPPORT` feature flag gates the screen's nav entry; default on-in-dev / off-in-release.
- [ ] BLE permissions present + cross-platform parity: Android `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` (+ `ACCESS_FINE_LOCATION` where required) in `AndroidManifest.xml`; iOS `NSBluetoothAlwaysUsageDescription` in `Info.plist` — both in the same PR (F40 cross-platform-parity discipline).
- [ ] Full mobile Jest suite green; BLE fully mocked — no test requires hardware.
- [ ] Device smoke gate (scan + connect + handshake against a real OBD-II dongle) — **held for a device session**; result appended to `196_phase_log.md` when run.

## Risks

1. **ELM327 clone variance.** Cheap clones differ in banner strings, timing, and which BLE service they expose. Mitigation: tolerant family-recognition (not exact-version), characteristic *probing* not hardcoding, generous response timeouts.
2. **Device-gated smoke.** The real-dongle gate cannot run without hardware. Mitigation: the build + unit verification are fully device-independent (mocked BLE); the gate is explicitly the one held step (Q3) — the phase does not *close* until the smoke runs, but it can *build* to completion.
3. **ADR-002 / New Architecture.** Building Old-Arch is the status quo and correct (Q1); the risk is only if a dependency bump forces New Arch. Mitigation: no dependency changes in 196.
4. **BLE permission UX** — Android 12+ split `BLUETOOTH_SCAN`/`CONNECT` runtime permissions; iOS Bluetooth permission prompt. Mitigation: explicit permission-request flow before scan; the cross-platform-parity checklist item (F40) is in the Verification Checklist.
5. **iOS background BLE** — out of scope for 196 (foreground scan/connect only); noted so a later phase owns background-mode entitlements.

## Risks / Assumptions / Next step

- **Assumption:** ELM327-family BLE adapters are the sole target (Q4); the connection layer ends at "live identified link" (Q2).
- **Risk:** the real-dongle smoke is the genuine unknown — clone behavior is only fully knowable on hardware.
- **Next step:** architect review of this plan v1.0 (esp. Q1–Q4). On approval, build the mobile `ObdConnection`/handshake/screen/flag layer + mocked tests to completion; hold the device smoke gate for a device session.
