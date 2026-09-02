# Phase 196 — Bluetooth OBD Adapter Connection — Phase Log

**Status:** ✅ Complete — BLE connect/handshake verification re-scoped to F56
(hardware-dependent; see the 2026-09-02 closing entry)
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
  *(Correction, same day: "New-Arch-disabled" proved impossible — see next
  entry. The smoke premise was reframed mid-session with user sign-off.)*

---

### 2026-07-20 09:10 — Device-build sessions (2026-07-17 → 2026-07-20): build works; smoke PARKED (dongle unavailable)

**What happened (chronological):**
1. RN CLI device build failed (exit 70) → root cause: no `DEVELOPMENT_TEAM`
   ever committed. Fixed via Xcode GUI (team `B6QK49DPRZ`).
2. Second failure: Xcode 26 `ENABLE_USER_SCRIPT_SANDBOXING=YES` denied RN's
   bundle script → set `NO` ×2. → **Bug fix #2** (mobile root `phase_log.md`).
3. Mid-session STOP finding: **RN 0.85 mandates New Arch** — `8a1f8ee` flag is
   a no-op; ADR-002 superseded (rewritten with evidence + replacement
   posture); Bug fix #1's Verified claim corrected. User approved proceeding
   under New Arch (Debug) with the smoke evidence reframed.
4. Xcode GUI build succeeded ("Finished running", 2026-07-17 12:10). Then:
   CoreDevice tunnel wedge (attach-loop) → Mac reboot cured it; app was
   deleted from phone and reinstalled via GUI Run.
5. **App launched and rendered under mandatory New Arch (Debug)** with Metro
   serving JS — no `#1277`-style init crash at launch. `BleManager` NOT yet
   exercised (Scan never tapped).
6. Smoke PARKED: dongle physically unavailable. Phone safely disconnected;
   app remains installed.

**Result state:** implementation doc stays **v1.0** (no smoke result — no
fake v1.1). Unit layer re-verified in-session: 32/32 pure-TS tests
(elm327 + machine) green in sandbox.

**RESUME CHECKLIST (next device session — dongle in hand):**
1. Repos: `moto-diag-mobile` branch `phase-196-bluetooth-obd` — pull latest
   (this session's commits); stash@{0} (video task) stays parked.
2. Metro: `cd ~/Projects/moto-diag-mobile && npx react-native start 2>&1 | tee -a ~/Projects/p196_metro.log`
3. Phone: MotoDiag app is installed — tap icon. Red screen → shake →
   Configure Bundler → `kerwyns-macbook-air.local` : `8081`. Only if the app
   is missing: `open ios/MotoDiag.xcworkspace` → Run (signing + sandboxing
   are committed now; Xcode otherwise NOT needed).
4. **Observed smoke, two steps:** (a) tap Scan with dongle UNPOWERED —
   `new BleManager()` moment (#1277 risk point); expect iOS Bluetooth
   permission prompt; record crash-or-not. (b) power dongle → Scan → confirm
   discovery → Connect → record `idle → scanning → connecting → handshaking →
   connected` + adapter banner (or `ObdConnectionError` kind on failure).
5. Record: append datapoint to ADR-002 "Condition #2 evidence"; impl doc
   v1.0 → v1.1 (all sections + Results + Deviations); this ledger log; move
   both ledger docs `in_progress/` → `completed/`; mobile ROADMAP row 196;
   commit + push per CLAUDE.md Step 6.
6. Backend (optional, not needed for smoke): Tailscale.app running on Mac
   (phone VPN toggle ON — status-bar badge is the tell) +
   `cd ~/Projects/moto-diag && motodiag serve --host 0.0.0.0`. Baked API base
   is `https://kerwyns-macbook-air.taila45995.ts.net`.
7. Remember: Debug-config evidence does NOT cover the known Release-mode
   crash profile — a Release smoke is a separate, later gate (Track J).

---

### 2026-08-23 12:55 — Resume session: scan datapoint PASS; hardware pivot to 196B; BLE gate deferred

- **Hardware validated first via vendor app** (per isolate-variables protocol):
  adapter + vehicle ECU + Bluetooth all proven working in the OBDLink app.
- **Adapter identified: OBDLink MX+ (model MX201)** — classic Bluetooth 3.0 +
  MFi, NOT BLE. Undiscoverable by `react-native-ble-plx` by design; the
  vendor app talks ExternalAccessory/MFi.
- **MotoDiag observed scan (dongle unplugged): PASS.** `new BleManager()` +
  live discovery under mandatory New Arch (Debug) — no crash, large device
  list rendered. Recorded in ADR-002's condition-#2 running record.
- **Disposition:** Phase 196 build + init/scan evidence complete;
  connect/handshake half of the smoke gate DEFERRED pending a BLE adapter
  (OBDLink CX / Vgate iCar Pro BT4.0 class). Impl doc stays v1.0 until the
  gate resolves or 196B's plan formally re-scopes it.
- **Next: Phase 196B plan cycle** — `ClassicBtObdProvider` (Android SPP +
  iOS ExternalAccessory/MFi; candidate dep `react-native-bluetooth-classic`,
  to be verified in Step 0 audit), reference device = the MX+. Step 0
  substrate audit of 196's locked seam surfaces before plan v1.0.

---

### 2026-09-02 17:54 — CLOSED: BLE-hardware half re-scoped to F56

Reviewed during the pre-Gate-10 cleanup, which surfaced this phase as the
only Track I row still unchecked while its sibling 196B was long done.

- **Everything this phase set out to build is built and green:**
  `BleObdProvider` behind the `ObdConnection` seam, 54 unit tests, the
  New-Arch Podfile fix (`8a1f8ee`), and a device-verified BLE **scan**
  (2026-08-23, `new BleManager()` + live discovery, no crash).
- **The one open item cannot be closed with the hardware on hand.** The
  reference dongle is an OBDLink MX+ (MX201): classic Bluetooth 3.0 +
  MFi, invisible to `react-native-ble-plx` by design. Connect and
  handshake need a BLE-class adapter. Filed as **F56** with the specific
  candidates named, so it reads as a shopping item rather than a bug.
- **The product is not waiting on it.** Phase 196B's
  `ClassicBtObdProvider` device-smoked PASS against that exact adapter
  ("ELM327 v1.4b", 2026-08-25) — the app talks to the user's real dongle
  through the same seam this phase established.
- **Why close rather than leave open:** the phase sat at 🔄 for ten days
  with finished code, which made every roadmap view misleading and made
  the Track I completion picture look worse than reality. Closing with an
  explicit, tracked gap is more honest than an unchecked box that reads
  as "unfinished work".
- Impl doc → v1.1 (checklist marked with the honest `[~]` on the
  hardware item, deviations, results, key finding); docs → `completed/`;
  mobile ROADMAP row 196 marked with the same caveat.
