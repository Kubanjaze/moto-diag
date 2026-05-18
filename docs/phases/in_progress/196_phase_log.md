# Phase 196 — Phase Log

**Status:** 🚧 Build complete + unit-verified — device smoke gate HELD | **Started:** 2026-05-17 | **Completed:** —
**Repo:** code in `Kubanjaze/moto-diag-mobile` (mobile-only phase); per-phase docs in `Kubanjaze/moto-diag/docs/phases/` per `ROADMAP_AUTHORITY.md`.
**Branch:** `phase-196-bluetooth-obd`

---

### 2026-05-17 — Plan v1.0 written

Phase 196 (Bluetooth OBD adapter connection) opens as the next phase in the
locked sequence (195B → 195C → 196), after 195C landed on master (`d1dfd6a`)
and its status was recorded in the mobile ROADMAP (`ca26ab2`). Architect
authorized writing plan v1.0 now; the build is largely device-independent and
the plan holds for architect review before any code.

**F33 Step-0 existing-code-overlap audit ran first** (both repos). Key
findings — **Phase 196 is extension territory, not greenfield**, and the plan
is written as extension from line one:

- `moto-diag-mobile/src/ble/BleService.ts` **already exists** — a Phase 186
  stub (`1c3b165`), 72 LoC: a singleton `react-native-ble-plx` wrapper with
  `waitForPoweredOn` / `scan` / `stopScan` / `connect` (+ service/characteristic
  discovery) / `disconnect` / `destroy`. Phase 196 **extends** it; no rewrite.
- `react-native-ble-plx@^3.5.1` is **installed** (Phase 185/186, per ADR-001).
  No new dependency.
- The `ObdConnection` provider seam + `OBD_SUPPORT` feature flag that ADR-001
  *anticipated* were **never built** — they are genuinely new (greenfield on
  top of `BleService`).
- The backend `moto-diag/src/motodiag/hardware/` package (Track E:
  `connection.py`, `ecu_detect.py`, `protocols/`, `compat_data/`) is the
  **desktop/CLI serial-port** OBD path — a *different transport*. ADR-001
  deliberately gave mobile its own `ObdConnection` seam. No coupling; mobile
  196 does not consume the backend hardware package.
- ADR-002 keeps New Architecture OFF, gated on `ble-plx` issue #1277 + a
  real-dongle smoke.

**Scope:** mobile-only. `ObdConnection` over `BleService`; `elm327.ts`
handshake (`ATZ`/`ATE0`/`ATL0`/`ATSP0`, tolerant family recognition);
connection state machine; `useObdConnection` hook; `ObdConnectScreen`;
`OBD_SUPPORT` feature flag; typed `ObdConnectionError` union; BLE
permission parity (Android manifest + iOS Info.plist, same PR per F40). No
backend change. Reading DTCs/PIDs + backend integration deferred to later
phases (pre-plan Q2).

**Four pre-plan questions surfaced for architect review:** Q1 ADR-002 flip
(resolved-recommendation: do NOT flip — ADR-002's own reversal trigger is
unmet; 196 builds Old-Arch status quo); Q2 mobile-only / connection-layer
scope; Q3 build-device-independent / smoke-gate-device-held; Q4
ELM327-family-over-BLE only. See `196_implementation.md` → "Pre-plan Q&A".

**Build/gate split:** the build is device-independent (`react-native-ble-plx`
is mockable; `BleService` is a thin wrapper) — `ObdConnection`, the handshake,
the state machine, error mapping, and the screen are all unit-testable with
zero hardware. Only the architect smoke gate (scan + connect + handshake
against a real OBD-II dongle) is device-gated — and that smoke doubles as
ADR-002's reversal-trigger evidence.

**Status:** plan v1.0 holds for architect review. No production code written.

**Next:** architect review of plan v1.0 (Q1–Q4) → on approval, build the
mobile connection layer + mocked tests to completion; hold the device smoke
gate for a device session.

---

### 2026-05-17 — Plan v1.0 → v1.0.1 amendment (architect review, pre-code)

Architect reviewed plan v1.0 — sound; F33 audit correctly framed 196 as
extension territory. Four pre-plan questions ruled + one blocking correction:

- **Q1 — do NOT flip ADR-002**, and (second action) ADR-002 is amended to
  record that the 196 real-dongle smoke is the designated reversal-trigger
  condition-#2 evidence event. ADR-002 amendment committed to the mobile repo.
- **Q2** — scope boundary confirmed as written (mobile-only, ends at "live
  identified OBD link"; DTC/PID reading + backend integration are later).
- **Q3** — build-now / smoke-gate-held confirmed; named requirement folded
  in: `FakeObdProvider` must model the real ELM327 handshake byte sequence
  (`ATZ`/`ATE0`/`ATL0`/`ATSP0` + `>` terminator), not a trivial stub.
- **Q4** — ELM327-BLE only confirmed; folded-in discipline: the
  `ObdConnection` seam is transport-agnostic (future Wi-Fi/classic-BT provider
  additive, not a rewrite — ADR-001 provider-seam pattern).
- **Blocking correction** — iOS BLE permission promoted from a general note to
  a **named checklist artifact**: `Info.plist` key `NSBluetoothAlwaysUsage
  Description` with non-empty descriptive copy (verify the value, not just key
  presence — the F-B failure mode), same PR as the Android permissions. This
  blocked v1.0 sign-off; now in Outputs + two Verification Checklist lines.

All rulings reflected inline in `196_implementation.md` (Pre-plan Q&A section
+ Verification Checklist + the "v1.0.1 amendment" section). Plan v1.0.1 holds
for architect sign-off.

**Parallel de-risk (architect/owner real-world action, not gated on sign-off):**
source a known-good ELM327-BLE dongle from the Phase 145 compat DB + confirm
the mechanic's adapter model — runs this week, independent of plan review.

**Next:** architect sign-off of plan v1.0.1 → "build 196" authorizes the
device-independent build to completion; device smoke gate held for a session.

---

### 2026-05-17 — Plan v1.0.1 → v1.0.2 amendment (full transport coverage, sequenced — pre-code)

Architect directive after the v1.0.1 review: *"build support for all available
dongles, at least the most popular."* This **reverses v1.0.1's Q4** (BLE-only).

**Why Q4 had to give:** the single most popular OBD-II dongle — the generic
ELM327 v1.5 clone (~$13, 50+ brand names) — is **classic Bluetooth 2.x (SPP)**,
which `react-native-ble-plx` physically cannot reach. "Most popular dongles"
spans three transport stacks: BLE / classic-BT / Wi-Fi.

**Architect ruling — "sequenced, plan commits to all 3":** the plan commits to
full transport coverage delivered across gate-sized sequenced phases behind the
transport-agnostic `ObdConnection` seam — not crammed into one phase. Committed
transport-provider roadmap:
- **196** — `BleObdProvider` (BLE / `react-native-ble-plx`) — this phase.
- **196B** — `ClassicBtObdProvider` (classic Bluetooth 2.x SPP; new RN dep) —
  covers the ~$13 generic clone, *the* most popular dongle.
- **196C** — `WifiObdProvider` (Wi-Fi / TCP sockets) — ELM327 Wi-Fi clones.

Each is an additive provider behind the same seam (the shared
`ObdConnectScreen` / state machine / `elm327.ts` handshake / typed errors are
built once in 196); each carries its own device smoke.

**Effect on Phase 196:** scope unchanged — 196 still builds + smokes BLE only.
The one hardening: the transport-agnostic `ObdConnection` seam is promoted from
a v1.0.1 "folded-in nicety" to a **load-bearing requirement with its own
closure check** (a stub non-BLE provider must be admissible behind the seam
without touching `BleObdProvider`) — because 196B/196C are now committed.

196B + 196C added to the Track I roadmap (mobile `docs/ROADMAP.md`) as
committed reserved phases.

**Next:** architect sign-off of plan v1.0.2 → "build 196" authorizes the
BLE-provider build; 196B/196C get their own plan-v1.0 cycles when 196 closes.

---

### 2026-05-17 — Build complete + unit-verified (v1.1) — device smoke gate HELD

Plan v1.0.2 signed; "build 196" authorized. Built via the Builder/Architect
split (as for 195C): a Builder agent wrote the BLE-provider build against
v1.0.2; the Architect ran the suite/tsc/lint (Builder sandbox blocks them),
fixed what surfaced, and finalized.

**Delivered** (mobile repo `moto-diag-mobile`, branch `phase-196-bluetooth-obd`):
`src/obd/{ObdConnection,elm327,obdConnectionMachine,obdErrors}.ts` +
`useObdConnection` hook + `ObdConnectScreen` + `src/config/features.ts`
(`OBD_SUPPORT`) + nav registration (HomeStack/HomeScreen, flag-gated) + iOS
`Info.plist` `NSBluetoothAlwaysUsageDescription` (non-empty copy) + Android
`AndroidManifest` BLE-permission hardening; 7 test suites / 78 tests. No new
dependency; mobile `package.json` 0.4.0 → 0.5.0. Build commit on the mobile
branch.

**Architect trust-but-verify fixes** (Builder built v1.0.2 faithfully; these
are harness/strict-mode gaps the Builder's sandbox couldn't catch — none a
production-logic bug):
- *Bug fix #1 — 3 test-harness issues.* `FakeObdProvider.ts` is a test double,
  not a suite → added to `jest.config.js testPathIgnorePatterns`.
  `seamClosure.test.ts` missing the `jest.mock('react-native-ble-plx', …)`
  block → added. `ObdConnect.smoke.test.tsx` happy-path pressed via the
  `toJSON()` host tree (where `TouchableOpacity.onPress` is absent) → switched
  to a `pressByTestId` helper using `renderer.root`. Verified: 7/7 obd suites.
- *Bug fix #2 — 4 strict-`tsc` errors + 1 eslint error.* `ObdConnection.ts`
  `globalThis.atob/btoa` → typed `base64Globals` view; smoke-test nav-props
  `as never` → `as unknown as React.ComponentProps<…>` (a `never` is not
  spreadable); removed an unused `ELM_PROMPT` import. Verified: `tsc` clean,
  eslint 0 errors.

**Verification:** full mobile Jest **778 passed / 60 suites / 0 fail** (+78
from 196, no regression); `tsc --noEmit` clean; eslint 0 errors (12 tolerated
`no-void`/`no-bitwise` warnings, codebase-parity). Closure gates both green —
the seam closure-check (`seamClosure.test.ts`, stub non-BLE provider
admissible) and the `FakeObdProvider` real-ELM327-byte-sequence requirement.

**Status: build complete, unit-verified, device smoke gate HELD** — the
explicit intermediate state plan v1.0.2 named. The real-dongle smoke (scan +
connect + handshake against a real ELM327-BLE dongle) is the one device-gated
step; it runs at a coordinated device session and its result (a) closes the
phase (doc → v1.2, this log → ✅, mobile ROADMAP 196 → ✅) and (b) is recorded
as ADR-002 reversal-trigger condition-#2 evidence. Phase doc stays in
`in_progress/` until then.

**Next:** architect's call on merging `phase-196-bluetooth-obd` (mobile code +
backend docs); device smoke at a device session; then 196B (classic-BT) plan
v1.0.
