# Phase 196B — OBD Classic-Bluetooth / MFi Provider (ClassicBtObdProvider)

**Version:** 1.0.1 | **Tier:** Standard | **Date:** 2026-08-23
*(v1.0.1: Spike Gate PASSED same day — dep New-Arch compat confirmed
on-device, MFi protocol string pinned to `com.obdlink` from vendor-app plist
+ live accessory, CB-state race bounded at ~1 s. Full evidence in
`196B_phase_log.md` 15:45 entry. Scope unchanged; fallback TurboModule path
no longer needed.)*

## Existing-code audit (Step 0 — run 2026-08-23, before this plan)

- **Substrate (Phase 196 locked surfaces, treat as immutable):** `ObdProvider`
  7-member contract in `src/obd/ObdConnection.ts` (scan/stopScan/connect/
  writeCommand/disconnect/onUnexpectedDisconnect/getStatus + `transport`);
  `ObdTransport` already reserves `'classic-bt'`; `ObdDevice` is
  transport-neutral (`rssi` optional); `elm327.ts` handshake + framing
  transport-shared; `ObdConnectionError` union transport-neutral by design
  (`ble_*` kinds = *local radio preconditions* — a classic-BT provider
  legitimately emits them; Wi-Fi never does). Seam-closure property pinned by
  `__tests__/obd/seamClosure.test.ts`.
- **Greenfield check:** zero classic/ExternalAccessory code in `src/`; only
  forward-looking comments. No classic dep in `package.json`.
- **Integration point:** `useObdConnection` lazily defaults to
  `BleObdProvider` — provider selection is the ONE shared-integration-point
  change (regression-guard required per integration-gap discipline).
- **Reference device:** user-owned **OBDLink MX+ (model MX201)** — classic
  Bluetooth 3.0 + Apple MFi; STN-chip, ELM327-compatible AT surface;
  vendor-app-verified against the vehicle 2026-08-23.

## Goal

Ship `ClassicBtObdProvider` — the second of three committed transports behind
the `ObdConnection` seam — covering classic-Bluetooth ELM327 adapters:
Android via RFCOMM/SPP, iOS via the ExternalAccessory (MFi) framework. The
reference device is the OBDLink MX+. Purely additive: zero edits to the
machine, screen logic, handshake, or `BleObdProvider` (seam-closure property
extended, not weakened).

Run (no CLI — mobile phase):
- Unit layer: `npx jest __tests__/obd/`
- Device smoke: Xcode Run (Debug) + Metro; MX+ paired in iOS Settings.

Outputs (mobile repo, branch `phase-196B-classic-bt-obd`):
- `src/obd/ClassicBtObdProvider.ts` — the provider
- Provider-selection wiring in `src/hooks/useObdConnection.ts` (+ screen
  transport affordance per plan Logic)
- `ios/MotoDiag/Info.plist` — `UISupportedExternalAccessoryProtocols`
- `__tests__/obd/ClassicBtObdProvider.test.ts` + seam-closure extension +
  provider-wiring regression guard
- Dependency: `react-native-bluetooth-classic` (pending Spike Gate below)

## Logic

- **iOS semantics delta (EA, not a radio scan):** ExternalAccessory cannot
  scan the radio. `scan(onDevice)` on iOS enumerates
  `EAAccessoryManager.connectedAccessories` filtered by the OBDLink protocol
  string and emits each as an `ObdDevice` (`transport: 'classic-bt'`, no
  rssi; `id` = accessory serial/connectionID). Precondition surfaced in UI
  copy: the adapter must be paired in Settings ▸ Bluetooth and powered.
- **Android semantics:** bonded-device list + classic discovery → RFCOMM/SPP
  socket to the adapter (standard SPP UUID).
- **connect(deviceId):** iOS opens an EASession for the protocol string and
  wires input/output streams; Android connects the socket. Both then hand a
  line-oriented read/write pair to the same `writeCommand` implementation.
- **writeCommand:** identical contract to BLE — append `\r`, accumulate
  chunks via `appendChunk` until `>` prompt, resolve framed response,
  8000 ms timeout. Reused handshake: `runElm327Handshake` untouched (STN
  chips answer ATZ with an ELM327-family banner).
- **Errors:** map to the existing union — radio-off → `ble_powered_off`
  (semantically "local radio"), missing/unpaired accessory →
  `device_not_found`, session/socket failure → `connect_failed`, stream drop
  → `disconnected_unexpectedly`. NO new error kinds.
- **Provider selection:** `useObdConnection` accepts the provider today
  (constructor-injectable) — wiring adds a transport chooser at the screen
  level (BLE default, classic-bt selectable), plus a regression-guard test
  asserting the chooser actually constructs/injects `ClassicBtObdProvider`.

## Key Concepts

- **Spike Gate (blocking, before full build):** `react-native-bluetooth-classic`
  is an old-style NativeModule with unverified New-Arch compatibility; our
  build compiles legacy arch OUT (`-DRCT_REMOVE_LEGACY_ARCH=1`). Step 1 of
  the build is a minimal spike: install dep, pod install, compile, call one
  module method on-device under the New-Arch interop layer. PASS → proceed;
  FAIL → fallback path (below) without having written provider code against
  a dead dep.
- **Fallback if spike fails:** small custom Swift TurboModule wrapping
  `EAAccessoryManager` + `EASession` streams (iOS) and a thin Kotlin SPP
  module (Android) — modest, well-bounded surface (list/connect/read/write/
  close), spec'd in a v1.0.1 amendment if needed.
- **MFi protocol string:** not publicly documented; pinned empirically at
  build time by logging `accessory.protocolStrings` for the paired MX+
  (candidate `com.obdlink.mx`, unverified). Dev/debug builds work with the
  string in `UISupportedExternalAccessoryProtocols`; App-Store submission
  later requires OBD Solutions' app-whitelist step (Track J concern, noted
  not blocking).
- **F40 parity checklist:** iOS `UISupportedExternalAccessoryProtocols`
  (this phase's Info.plist key) ⇔ Android classic-BT permissions
  (`BLUETOOTH_CONNECT` already present from 196; verify `BLUETOOTH_SCAN`
  covers classic discovery on API 31+) — both in the same PR.
- **SSOT discipline:** protocol string + SPP UUID exported as canonical
  constants; tests import, never literal-pin (191D).

## Verification Checklist

- [ ] Spike Gate: dep compiles + one native call succeeds under New Arch
      interop on-device (or documented FAIL → fallback amendment)
- [ ] Unit: ClassicBtObdProvider suite green (Fake EA/SPP layer injected,
      mirroring `BleServiceLike` pattern); full `__tests__/obd/` green
- [ ] Seam closure extended: classic provider admitted with zero edits to
      machine/screen-logic/handshake/errors/BleObdProvider
- [ ] Provider-wiring regression guard green (chooser → ClassicBtObdProvider)
- [ ] Info.plist protocol string present; F40 parity items checked
- [ ] Device smoke (MX+, Debug): paired accessory enumerated → connect →
      ATZ→ATE0→ATL0→ATSP0 → banner displayed; result recorded in ADR-002
      running record + this doc v1.1

## Risks

- **Dep New-Arch incompatibility (top risk):** mitigated by the Spike Gate +
  scoped fallback TurboModule plan.
- **EA session quirks:** stream delegate threading + partial reads — handled
  by the same `appendChunk` accumulation; timeout generous (8 s).
- **Protocol-string mismatch:** if the probe shows a different string than
  candidate, constants update — no code shape change.
- **iOS pairing UX:** classic requires Settings-level pairing first; screen
  copy must say so or users will report "not found" (device_not_found path).
- **App-Store MFi whitelist:** known later gate (Track J), not a dev blocker.
