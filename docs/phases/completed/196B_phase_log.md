# Phase 196B — OBD Classic-Bluetooth / MFi Provider — Phase Log

**Status:** ✅ Complete
**Started:** 2026-08-23 | **Completed:** 2026-08-25
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

---

### 2026-08-23 15:45 — SPIKE GATE: PASSED (all build unknowns resolved on-device)

**Verdict evidence (Debug build on iPhone 16 Pro, mandatory New Arch):**
```
attempt 1: isBluetoothEnabled = false → retry
attempt 2: isBluetoothEnabled = true → getBondedDevices OK
device count: 1
{ name: "OBDLink MX+", id: "225530513625", address: "225530513625",
  bonded: true, deviceClass: "MX201", type: "CLASSIC",
  protocolStrings: ["com.obdlink"], extra: {} }
VERDICT: module responds under New Arch — PASS
```

**Answers banked for the build:**
1. `react-native-bluetooth-classic@1.73.0-rc.17` loads, initializes, and
   round-trips native calls under RN 0.85's mandatory New Arch (interop) —
   the plan's top risk is CLEARED; no fallback TurboModule needed.
2. **MFi protocol string = `com.obdlink`** (single string). Pinned two ways:
   extracted from the vendor app's own Info.plist (OBDLink 7.4.0 .ipa via
   Apple Configurator download-cache; bundle `com.obdsol.obdlink`) AND
   confirmed by the live accessory's `protocolStrings`. Now declared in
   `ios/MotoDiag/Info.plist` (with provenance comment).
3. **CBCentralManager state race is real and bounded** — the lib's lazy
   `CBCentralManager` reports not-enabled on first touch, settles by ~1 s.
   Provider MUST gate first EA call on state readiness (mirror
   `BleService.waitForPoweredOn`); retry evidence above.
4. **Lib crash pinned:** `RNBluetoothClassic.swift:69` force-unwraps
   `UISupportedExternalAccessoryProtocols` — key absent = init crash. Key is
   now permanent in Info.plist with a never-remove warning comment.
5. **Enumeration requires the accessory EA-active**, not merely paired:
   Settings-"Connected" with an idle/asleep adapter still yields count 0.
   Provider UX must surface "wake the adapter / reconnect in Settings"
   guidance on empty enumeration (device_not_found copy).
6. **Device shape** for `ObdDevice` mapping: `id`/`address` (stable numeric),
   `name`, `bonded`, `deviceClass` ("MX201"), `type` ("CLASSIC"),
   `protocolStrings`, `extra`.

**Session engineering notes (cross-machine/env, same day):**
- Xcode CoreDevice "tunnel connection failed" attach-loop root-caused to the
  **VPN network extension being Active** (System Settings ▸ Network showed
  VPN Active despite the Tailscale app being quit). Disabling the VPN
  profiles restored the device tunnel instantly. Finder/usbmuxd seeing the
  phone while Xcode/devicectl reports `unavailable` is the diagnostic
  signature (candidate CLAUDE.md addition — pending user approval).
- iAP logging profile route was a dead end for the protocol string (payloads
  stay `<private>`); the **Configurator .ipa cache extraction**
  (`~/Library/Group Containers/K36BKF7T3D.group.com.apple.configurator/
  Library/Caches/Assets/TemporaryItems/MobileApps/<uuid>/<id>/*.ipa`,
  file exists only during download; nested one level below the obvious glob)
  is the reusable method of record.
- Spike artifacts currently on branch `phase-196B-classic-bt-obd`:
  `src/obd/classicBtSpike.SPIKE.ts` + labeled wiring in
  `ObdConnectScreen.tsx` — DELETE in the provider build commit per plan.
- `implementation.md` bumped v1.0 → v1.0.1 (Spike Gate result noted; scope
  unchanged).

**Next milestone:** build `ClassicBtObdProvider` per plan (dep verified, all
constants known). Device smoke follows immediately after — same adapter.

---

### 2026-08-23 16:10 — Build complete: provider + wiring + tests, full regression green

- **Shipped:** `src/obd/ClassicBtObdProvider.ts` (delimiter-framed transport,
  poll-based radio wait, single-slot sequential command channel,
  unexpected-disconnect bridge with other-accessory filtering);
  `src/obd/providerFactory.ts` (transport → provider SSOT +
  SELECTABLE_TRANSPORTS/TRANSPORT_LABELS); ObdConnectScreen idle-state
  transport picker (BLE default, Classic selectable, per-transport pairing
  copy). Spike artifacts DELETED as planned.
- **Tests:** +26 (16 provider / 6 factory+seam-admission / 4 wiring guard —
  including THE guard: chooser → ClassicBtObdProvider injected into the
  hook). obd suite 83/83; **full mobile regression 62 suites / 804 tests,
  0 failures**; `tsc --noEmit` clean.
- **Deviations** (recorded in impl doc v1.1): appendChunk unnecessary at
  this layer (delimiter framing), poll-based radio wait (spike-proven
  envelope), picker via existing Button component.
- **Remaining gate:** device smoke — Classic transport → MX+ enumerated →
  connect → 4-command handshake → banner. One Xcode Run away; recorded into
  ADR-002 + this ledger when it lands, then docs move to `completed/`.

---

### 2026-08-25 11:35 — DEVICE SMOKE: PASS — Phase 196B ✅ Complete

- **Run (Debug, mandatory New Arch, iPhone 16 Pro):** Classic transport
  selected in the idle picker → Scan → **OBDLink MX+ enumerated** over
  ExternalAccessory → tap-connect → `connecting → handshaking → connected` →
  **banner "ELM327 v1.4b"** (the STN chip's ELM-compat identity) rendered on
  the connected screen. Full `ATZ→ATE0→ATL0→ATSP0` conversation over the
  MFi session — the 196-built handshake/machine layers untouched.
- Datapoint recorded in mobile `docs/adr/002` running record; mobile project
  docs updated (`implementation.md` 0.1.8 w/ Phase History row + F9-#9
  header correction, ROADMAP 196B ✅, root `phase_log.md` completion entry).
- Docs moved `in_progress/` → `completed/` in this commit. Verification
  checklist fully ticked in `196B_implementation.md` (final).
- **Follow-ons already on the roadmap:** 196 BLE half (pending BLE adapter),
  196C Wi-Fi provider, Release-config smoke + OBD Solutions MFi whitelist
  before Track J ships.
