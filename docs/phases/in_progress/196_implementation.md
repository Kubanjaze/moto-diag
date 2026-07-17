# Phase 196 — Bluetooth OBD Adapter Connection (BleObdProvider)

**Version:** 1.0 (labeled reconstruction of unpersisted v1.0.2) | **Tier:** Standard | **Date:** 2026-07-17

> **RECONSTRUCTION NOTICE (CLAUDE.md Session Continuity rule 3).** The original
> Phase 196 plan document ("plan v1.0.2", cited by `docs/ROADMAP.md` row 196 and
> by in-code comments) was written in a prior session and never persisted to
> git — confirmed absent from both repos at `moto-diag` master `8e58e69` and
> `moto-diag-mobile` `phase-196-bluetooth-obd` `9c3bef2` on 2026-07-17. This
> document is an explicitly-labeled rebuild, sourced from: ROADMAP row 196 +
> 196B/196C rows, in-code plan references (`elm327.ts` "plan Step 2",
> `obdConnectionMachine.ts` "plan Step 3", `obdErrors.ts` "plan v1.0.2" seam
> notes), mobile root `phase_log.md` Bug fix #1 (2026-06-22), ADR-002's
> designated-evidence section (added 2026-05-17 "Phase 196 plan review"), and
> the shipped code + test suite. Where the original plan's wording is unknown,
> the as-built code is described; deltas discovered against the user-stated
> plan summary are flagged inline as **[recon note]**.

## Goal

Ship the **`BleObdProvider`** — the first of three committed transport
providers behind a transport-agnostic **`ObdConnection`** seam — giving the app
scan → pair → ELM327-handshake connectivity to BLE OBD-II dongles. The build
phase is device-independent (BLE mocked in the unit layer); the **real-dongle
smoke gate is held for a device session** and is the designated
evidence-gathering event for **ADR-002 reversal-trigger condition #2**. Phase
196 does NOT flip New Architecture; it only produces condition #2's pass/fail
data point.

Run (no CLI — mobile phase):
- Device build: `npx react-native run-ios --device` (must include Podfile
  New-Arch disable, commit `8a1f8ee`)
- Metro: `npx react-native start`
- Unit layer: `npx jest __tests__/obd/`

Outputs (mobile repo, branch `phase-196-bluetooth-obd`):
- `src/obd/ObdConnection.ts` — transport-agnostic provider seam (`ObdDevice`, `ObdProvider`)
- `src/obd/elm327.ts` — ELM327 handshake + response framing (transport-shared)
- `src/obd/obdConnectionMachine.ts` — pure connection state machine
- `src/obd/obdErrors.ts` — 7-kind `ObdConnectionError` discriminated union + UI copy map
- `src/ble/BleService.ts` — singleton `react-native-ble-plx` wrapper
- `src/hooks/useObdConnection.ts` — side-effect layer driving the reducer
- `src/screens/ObdConnectScreen.tsx` — scan/connect UI
- `__tests__/obd/` — 5 suites + `FakeObdProvider` test double
- `patches/react-native-ble-plx+3.5.1.patch`

## Logic

- **State machine (pure reducer, Phase 191/195 capture-machine idiom):**
  `idle → scanning → connecting → handshaking → connected` with terminal-for-now
  `failed` (carries `ObdConnectionError`) and user-initiated `disconnected`.
  RESET returns to `idle` from any state. Invalid (state, event) pairs no-op
  with a dev-only warn. Exhaustive switch + `never` assertion.
  **[recon note]** the user-stated summary omitted the distinct `handshaking`
  state; it exists between `connecting` and `connected`.
- **Unexpected-disconnect distinction (load-bearing):** a link drop without
  user intent → `failed` + `disconnected_unexpectedly`, distinct from the clean
  `disconnected` state.
- **Hook owns side effects:** `useObdConnection` calls provider
  scan/connect/handshake/disconnect and dispatches callback events into the
  reducer; screens stay declarative. Default provider is a lazily-created
  `BleObdProvider`.
- **ELM327 handshake (transport-shared, reused verbatim by 196B/196C):** init
  sequence `ATZ → ATE0 → ATL0 → ATSP0`. **[recon note]** four commands — the
  user-stated summary listed three (omitted `ATL0`); code + SSOT export are
  authoritative. ATZ response must contain an ELM-family marker
  (`ELM327`, `ELM 327`, `OBDII`, `OBD II`, `OBD-II`, case-insensitive) else
  `handshake_failed`; banner extracted for display. Config-command errors after
  a good ATZ banner = degraded success (the link is a genuine adapter — all
  Phase 196 asserts). Responses framed on the `>` prompt; `appendChunk`
  accumulates multi-chunk BLE notifies and carries pipeline remainders.
- **BleService:** singleton `BleManager` (multiple instances crash Android);
  `waitForPoweredOn` gates on adapter state and rejects on
  Unauthorized/Unsupported.

## Key Concepts

- `react-native-ble-plx` ^3.5.1 + `patches/react-native-ble-plx+3.5.1.patch`
  (patch-package) on RN 0.85.2, React 19.
- **ADR-002 dependency:** New Architecture must be OFF on both platforms
  (ble-plx upstream #1277). Android `newArchEnabled=false`; iOS
  `ENV['RCT_NEW_ARCH_ENABLED'] = '0'` at `ios/Podfile:1` (Bug fix #1,
  commit `8a1f8ee`, F9 cross-platform-parity family).
- **Permissions parity (F40 checklist):** Android `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`
  in `AndroidManifest.xml`; iOS `NSBluetoothAlwaysUsageDescription` at
  `ios/MotoDiag/Info.plist:47`.
- **SSOT exports (Phase 191D discipline):** `ELM327_INIT_SEQUENCE`,
  `OBD_ERROR_KINDS`, `ELM_PROMPT` — tests and `FakeObdProvider` import the
  canonical lists, never literal-pin.
- **Typed error contract (F37 kin):** 7-kind discriminated union
  (`ble_powered_off`, `ble_unauthorized`, `ble_unsupported`,
  `device_not_found`, `connect_failed`, `handshake_failed`,
  `disconnected_unexpectedly`) + exhaustive `ObdErrorCopy` map with
  `canRetry`/`needsSettings` affordance flags.
- **Seam closure:** `seamClosure.test.ts` pins that the machine + handshake
  reference only `ObdConnection`/`obdErrors` types, keeping 196B (classic-BT)
  and 196C (Wi-Fi) drop-in.

## Verification Checklist

- [x] Unit layer green: 54 tests / 5 suites in `__tests__/obd/`
      (elm327 17, machine 15, BleObdProvider 9, obdErrors 9, seamClosure 4)
- [ ] Fresh device build installs and launches with New Architecture disabled
      (build postdates `8a1f8ee`; verify via build/Metro log)
- [ ] Real-dongle smoke: dongle appears in scan → connect →
      `idle → scanning → connecting → handshaking → connected` with banner
- [ ] Evidence captured: banner text, state transitions, any
      `ObdConnectionError` kind on failure (Metro + build logs)
- [ ] ADR-002 condition #2 data point appended (pass OR fail — both valid)

## Risks

- **Clone banner variance** (~$13 clones): family-marker matching, not
  exact-version — a no-marker response is a real non-adapter, not a parse gap.
- **BLE notify chunking:** responses can arrive fragmented; `appendChunk`
  framing is unit-tested against split chunks.
- **New-Arch crash (upstream #1277):** mitigated by ADR-002 + `8a1f8ee`; the
  currently-installed phone build PREDATES the fix — a stale-build smoke run
  would test the wrong configuration (F9 substrate-state family). Fresh cable
  build is mandatory first.
- **Permission hard-crash:** mitigated (Info.plist:47 + manifest) — F40
  checklist satisfied.
- **Smoke may fail for environmental reasons** (dongle unpowered, bike ECU
  asleep): distinguish `ObdConnectionError` kinds — `handshake_failed` vs
  `disconnected_unexpectedly` vs BLE-layer — before attributing to code.
- Backend not required for the smoke (pure BLE path); if needed later:
  `motodiag serve --host 0.0.0.0` (default binds 127.0.0.1 only).
