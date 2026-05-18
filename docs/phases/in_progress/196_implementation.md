# Phase 196 — Bluetooth OBD adapter connection

**Version:** 1.1 (built — as-built; plan history in "v1.0.1 amendment" / "v1.0.2 amendment" / "Deviations from Plan". **Status: build complete + unit-verified; device smoke gate HELD.**) | **Tier:** Standard | **Date:** 2026-05-17

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
- iOS `ios/MotoDiag/Info.plist` — `NSBluetoothAlwaysUsageDescription` key with **non-empty descriptive copy**; Android `AndroidManifest.xml` — `BLUETOOTH_SCAN` + `BLUETOOTH_CONNECT` (+ `ACCESS_FINE_LOCATION` where required). Both in the **same PR** (F40 cross-platform-parity — named-artifact discipline; see "v1.0.1 amendment").
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

## Pre-plan Q&A — architect-ruled (2026-05-17)

- **Q1 — ADR-002 flip — RULED: do NOT flip + designate the 196 smoke as ADR-002 reversal-trigger evidence.** New Architecture stays disabled; ADR-002's reversal trigger (ble-plx New-Arch release **and** a passing real-dongle smoke) is unmet, so flipping now acts on speculation the trigger exists to forbid. 196 builds on the Old-Arch status quo. **Two-action ruling** — the second action is load-bearing: ADR-002 is amended (mobile repo) to record that the **Phase 196 real-dongle smoke is the designated evidence-gathering event for reversal-trigger condition #2**. Without that, the smoke passes and the architecture data point is never harvested back to ADR-002 — forfeiting a scarce device session's dual yield (a 196 gate pass *and* a logged ADR-002 evidence point). Do NOT flip speculatively; do NOT defer 196 to "resolve ADR-002 first" (circular — ADR-002 is resolved by evidence 196 produces).
- **Q2 — scope boundary — RULED: confirmed as written.** 196 is mobile-only and terminates at "live identified OBD link." DTC/PID reading + backend integration are later phases — the substrate-then-feature split (196 = link substrate; reading = separate feature/gate). Do NOT pull in "read one DTC to prove it works" — that makes the smoke gate test two layers and defeats failure isolation.
- **Q3 — build now / smoke gate held — RULED: confirmed.** "iOS-blocked" = gate-only, not build-blocked. The full build + unit verification run to completion now; only the real-dongle smoke is device-held. **Required mitigation, named now:** the `FakeObdProvider` test double MUST model the real ELM327 handshake byte sequence (`ATZ` → `ATE0` → `ATL0` → `ATSP0`, with the expected response shapes + the `>` prompt terminator) — **not a trivial stub**. A weak fake gives false confidence; faithfully modeling the byte sequence is how the device-independent build genuinely covers the handshake. The phase reaches an explicit, legitimate intermediate state: "build complete, unit-verified, smoke gate held."
- **Q4 — transport target — RULED (v1.0.1: BLE-only) → SUPERSEDED by v1.0.2.** The v1.0.1 ruling scoped 196 to ELM327-BLE only with Wi-Fi/classic-BT out of scope. The v1.0.2 amendment **reverses the exclusion**: the product must support the popular dongles, and the most popular dongle of all — the ~$13 generic ELM327 v1.5 clone — is **classic Bluetooth 2.x (SPP)**, a different radio protocol that `react-native-ble-plx` physically cannot reach. The plan therefore now **commits to full transport coverage** across a sequenced provider roadmap (see "Transport-provider roadmap" below). Phase 196 itself still ships **only the BLE provider** + the device-smoke is BLE-only — but it is now explicitly *the first of three committed transport providers*, not the whole of transport support. The transport-agnostic `ObdConnection` seam (a v1.0.1 folded-in nicety) is **promoted to a load-bearing requirement** — 196B and 196C depend on it. See the v1.0.2 amendment.

## Verification Checklist

- [x] `ObdConnection` wraps the existing `BleService` singleton; `BleService.ts` unchanged (`BleObdProvider` wraps it, no edits to BleService).
- [x] BLE serial service/characteristic discovery probes the discovered set (writable + notifiable) rather than hardcoding a single vendor UUID.
- [x] `elm327.ts` runs the `ATZ`/`ATE0`/`ATL0`/`ATSP0` init sequence; recognizes the ELM327 family banner tolerantly; a non-ELM response → `handshake_failed`.
- [x] `obdConnectionMachine` covers `idle/scanning/connecting/handshaking/connected/failed/disconnected`; unexpected disconnect transitions to `failed`.
- [x] `ObdConnectScreen` — scan → device list → connect → live status → disconnect; OBD-adapter filtering on the scan list.
- [x] `ObdConnectionError` typed union (7 kinds) + user-facing copy for each.
- [x] `OBD_SUPPORT` feature flag gates the screen's nav entry; default on-in-`__DEV__` / off-in-release.
- [x] **`ObdConnection` seam is transport-agnostic — LOAD-BEARING closure check (v1.0.2):** transport-neutral `ObdProvider` interface; `BleObdProvider` is one implementation behind it. **Verified** — `__tests__/obd/seamClosure.test.ts` defines a stub `StubClassicBtProvider implements ObdProvider` that drives the shared `runElm327Handshake` + `obdConnectionMachine` with zero edits to `BleObdProvider`/machine/screen/`elm327`/errors; it compiles + passes.
- [x] **`FakeObdProvider` models the real ELM327 handshake byte sequence** (Q3): `ATZ`→banner(+echo)/`ATE0`/`ATL0`/`ATSP0`→`OK`/unknown→`?`, all `>`-terminated; reuses the production `appendChunk` framing; supports chunked delivery. Not a trivial stub — verified by inspection.
- [x] **iOS BLE permission — named artifact (BLOCKING, F40):** `ios/MotoDiag/Info.plist` carries `NSBluetoothAlwaysUsageDescription` with non-empty descriptive copy.
- [x] **Android BLE permissions:** `AndroidManifest.xml` carries `BLUETOOTH_SCAN` (+ `neverForLocation`) + `BLUETOOTH_CONNECT`; `ACCESS_FINE_LOCATION` scoped `maxSdkVersion=30` — same change set as the iOS plist key (F40 parity).
- [x] Full mobile Jest suite green; BLE fully mocked — **778/778 (60 suites; +78 from 196), `tsc --noEmit` clean, eslint 0 errors**. No test requires hardware.
- [ ] **Device smoke gate** (scan + connect + handshake against a real OBD-II dongle) — **HELD for a device session** (intentionally unchecked; the one device-blocked step per Q3). Result appended to `196_phase_log.md` when run; also ADR-002 reversal-trigger evidence.

## Risks

1. **ELM327 clone variance.** Cheap clones differ in banner strings, timing, and which BLE service they expose. Mitigation: tolerant family-recognition (not exact-version), characteristic *probing* not hardcoding, generous response timeouts.
2. **Device-gated smoke.** The real-dongle gate cannot run without hardware. Mitigation: the build + unit verification are fully device-independent (mocked BLE); the gate is explicitly the one held step (Q3) — the phase does not *close* until the smoke runs, but it can *build* to completion.
3. **ADR-002 / New Architecture.** Building Old-Arch is the status quo and correct (Q1); the risk is only if a dependency bump forces New Arch. Mitigation: no dependency changes in 196.
4. **BLE permission UX** — Android 12+ split `BLUETOOTH_SCAN`/`CONNECT` runtime permissions; iOS Bluetooth permission prompt. Mitigation: explicit permission-request flow before scan; the cross-platform-parity checklist item (F40) is in the Verification Checklist.
5. **iOS background BLE** — out of scope for 196 (foreground scan/connect only); noted so a later phase owns background-mode entitlements.

## v1.0.1 amendment — architect review rulings (pre-code, 2026-05-17)

Plan v1.0 reviewed by the architect; v1.0 was sound (F33 audit correctly framed 196 as extension territory). Four pre-plan questions ruled — all reflected inline in the "Pre-plan Q&A — architect-ruled" section above — plus one **blocking plan correction**:

- **Q1** — do NOT flip ADR-002; **additionally**, ADR-002 is amended (mobile repo) to record that 196's real-dongle smoke is the designated reversal-trigger-condition-#2 evidence event. Two actions, not one.
- **Q2 / Q3 / Q4** — confirmed as written, with two named requirements folded in: the `FakeObdProvider` must model the real ELM327 handshake byte sequence (Q3), and the `ObdConnection` seam must be transport-agnostic so a future non-BLE provider is additive (Q4).
- **Blocking correction — iOS BLE permission as a named artifact.** Plan v1.0 listed the BLE permission as a general "iOS Info.plist + Android manifest, same PR" note. This session has already produced **F-A** (VisionCamera black-screen) and **F-B** (an *empty-string* `NSLocationWhenInUseUsageDescription` value that fails App Store review) from iOS permission keys treated as general notes rather than named, verified artifacts. v1.0.1 makes the BLE permission a **named checklist artifact with its own verification line**: `ios/MotoDiag/Info.plist` key `NSBluetoothAlwaysUsageDescription`, **non-empty descriptive copy** (verify the *value*, not just key presence), same PR as the Android `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` permissions. This blocked v1.0 sign-off; it is now in the Outputs list + as two dedicated Verification Checklist lines.

**Build authorization:** with this v1.0.1 amendment landed, the plan is ready for architect sign-off. On "build 196": the device-independent build + unit verification run to completion (the `FakeObdProvider` models the real handshake); the real-dongle smoke gate is held for a coordinated device session. Phase reaches the explicit intermediate state "build complete, unit-verified, smoke gate held."

**Parallel, not gated on this plan:** sourcing a known-good ELM327-BLE dongle (Track E Phase 145 compat-DB ranked list) + confirming the mechanic's adapter model — an architect/owner real-world action that de-risks the scarce device session; runs independently of plan sign-off.

## v1.0.2 amendment — full transport coverage, sequenced (pre-code, 2026-05-17)

**Trigger.** Architect directive after the v1.0.1 review: *"build support for all available dongles, at least the most popular."* This reverses v1.0.1's Q4 (BLE-only). **Why it had to give:** the single most popular OBD-II dongle — the generic ELM327 v1.5 clone, sold under 50+ brand names at ~$13 — is **classic Bluetooth 2.x (SPP)**, a radio protocol `react-native-ble-plx` cannot reach. A BLE-only product would not support the dongle most mechanics already own. "Most popular dongles" genuinely spans three transport stacks: BLE (ble-plx), classic-BT (a separate RN library), Wi-Fi (TCP sockets).

**Ruling (architect, "sequenced — plan commits to all 3"):** the plan commits to full transport coverage, delivered across **gate-sized sequenced phases** behind the transport-agnostic `ObdConnection` seam — *not* crammed into one phase. Phase 196 ships the BLE provider; classic-BT and Wi-Fi are their own committed follow-on phases. This honors both the product requirement (all popular dongles supported) and the substrate-then-feature gate-discipline (each transport is its own build + its own device smoke).

### Transport-provider roadmap (committed)

| Phase | Provider | Transport / library | Covers |
|-------|----------|---------------------|--------|
| **196** | `BleObdProvider` | BLE — `react-native-ble-plx` (installed) | OBDLink CX, Vgate iCar Pro BT4.0, newer BLE clones |
| **196B** | `ClassicBtObdProvider` | Classic Bluetooth 2.x SPP — new RN dep (`react-native-bluetooth-classic` or equiv.) | the ~$13 generic ELM327 v1.5 clone (50+ brands) — *the* most popular dongle |
| **196C** | `WifiObdProvider` | Wi-Fi — TCP sockets to the adapter's AP | ELM327 Wi-Fi clones |

Each phase: an **additive new provider behind the same `ObdConnection` seam** — no rewrite of 196's work; the `ObdConnectScreen` / state machine / `elm327.ts` handshake / typed errors are transport-shared and built once in 196. Each phase carries its own device smoke (its own dongle type). 196B/196C are added to the Track I roadmap (mobile `docs/ROADMAP.md`) as committed reserved phases.

**Consequences for Phase 196 itself:** unchanged in scope — 196 still builds + smokes BLE only. The single hardening: the transport-agnostic seam moves from "folded-in nicety" (v1.0.1) to a **load-bearing requirement with its own closure check** — `ObdConnection` must cleanly admit a non-BLE provider, because 196B/196C are now committed, not hypothetical. The `BleObdProvider` is named as one provider implementation, not "the connection."

**Build authorization unchanged:** with v1.0.2 landed the plan is ready for sign-off; "build 196" authorizes the BLE-provider build to completion, device smoke held. 196B/196C plans are written when 196 closes (their own plan-v1.0 cycles).

## Deviations from Plan

Built against v1.0.2; no scope deviations. Build-phase notes:

- **Builder/Architect split** (as for 195C): a Builder agent wrote the BLE-provider build against v1.0.2; the Architect ran the suite/tsc/lint (the Builder's sandbox blocks them) and fixed what they surfaced.
- **3 test-harness fixes** (not production bugs): `FakeObdProvider.ts` is a test double, not a suite — added to `jest.config.js testPathIgnorePatterns` so Jest doesn't fail it as zero-test; `seamClosure.test.ts` needed the `jest.mock('react-native-ble-plx', …)` block the other obd suites carry (its import graph transitively reaches `BleService`); `ObdConnect.smoke.test.tsx` happy-path test pressed via `renderer.toJSON()` (host tree — `TouchableOpacity.onPress` doesn't survive there) → switched to a `pressByTestId` helper using `renderer.root` (component tree).
- **4 strict-`tsc` fixes** (Builder couldn't run `tsc`): `ObdConnection.ts` `globalThis.atob/btoa` → a typed `base64Globals` view (RN TS lib doesn't declare them); `ObdConnect.smoke.test.tsx` nav-props mock `as never` → `as unknown as React.ComponentProps<typeof ObdConnectScreen>` (a `never` cannot be spread).
- **1 eslint-error fix:** removed an unused `ELM_PROMPT` import in `ObdConnection.ts`. 12 `no-void`/`no-bitwise` *warnings* remain — tolerated, codebase-parity (prior phases accepted `no-void` warnings).
- **Nav placement:** `ObdConnectScreen` registered in `HomeStack` (Home owns connection/BLE-status flows) rather than `GarageStack` — Builder judgment call, accepted.
- **Android permissions:** `BLUETOOTH_SCAN`/`CONNECT` already existed from Phase 186 — the change is additive hardening (`neverForLocation` + `ACCESS_FINE_LOCATION maxSdkVersion=30`), F40 parity satisfied in the same change set.

## Results

| Metric | Value |
|--------|-------|
| BLE provider | `BleObdProvider` behind a transport-agnostic `ObdProvider` seam (196 of the 196/196B/196C roadmap) |
| New modules | `src/obd/` (ObdConnection, elm327, obdConnectionMachine, obdErrors) + `useObdConnection` + `ObdConnectScreen` + `src/config/features.ts` |
| Phase tests | `__tests__/obd/*` + hook + screen — 7 suites, 78 tests, all green |
| Full mobile Jest | 778 passed / 60 suites / 0 fail (+78, no regression) |
| tsc / eslint | `tsc --noEmit` clean; eslint 0 errors (12 tolerated warnings) |
| Closure gates | seam closure-check ✓ ; `FakeObdProvider` real-ELM327-sequence ✓ |
| New dependency | none — uses installed `react-native-ble-plx@3.5.1` |
| Mobile `package.json` | 0.4.0 → 0.5.0 |
| Device smoke gate | **HELD** for a device session (Q3) |

**Key finding:** the device-independent build held — the entire BLE provider + handshake + state machine + screen unit-verify with `react-native-ble-plx` mocked, and the `FakeObdProvider` modeling the *real* ELM327 byte sequence (Q3's named requirement) is what makes that verification trustworthy rather than a stub passing itself. The phase reaches the explicit intermediate state v1.0.2 named: **build complete, unit-verified, smoke gate held.**

## Risks / Assumptions / Next step

- **Status:** Phase 196 is **build-complete + unit-verified**, NOT closed — the real-dongle smoke gate is held. Per plan v1.0.2 Q3 this is a legitimate explicit intermediate state, not an incomplete finalize. The phase doc stays in `in_progress/`; it moves to `completed/` (→ v1.2) when the smoke runs.
- **Risk:** the real-dongle smoke is the genuine unknown — clone behavior is only fully knowable on hardware. Mitigation: the parallel dongle-sourcing action.
- **Next step:** (1) architect's call on merging `phase-196-bluetooth-obd` (single-repo: mobile code + backend docs branches) — same merge-discipline as prior phases; (2) the device smoke gate runs at a coordinated device session — its result closes the phase (doc → v1.2, mobile ROADMAP 196 → ✅) and is recorded as ADR-002 reversal-trigger evidence; (3) 196B/196C get their own plan-v1.0 cycles.
