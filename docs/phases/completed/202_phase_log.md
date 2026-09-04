# Phase 202 — Mechanic Time Tracking — Phase Log

**Status:** ✅ Complete (device-UI leg outstanding — see the smoke entry)
**Started:** 2026-09-04 | **Completed:** 2026-09-04
**Repos:** `Kubanjaze/moto-diag` + `Kubanjaze/moto-diag-mobile`, both on
branch `phase-202-time-tracking`

---

### 2026-09-04 15:11 — Plan written (Step 0 audit + v1.0)

- **Step 0 ran as a six-reader parallel audit with a completeness
  critic.** The critic paid for itself: it raised three findings no
  reader did, two of which changed the plan — the permission trap and
  the Android push gap. (The verification and synthesis stages hit the
  session usage limit; the readers' and critic's results were cached and
  the remaining claims were settled by hand.)
- **Time intervals are greenfield AND unreconstructible.** `start_work`
  overwrites `started_at` on every start; `pause_work` stamps nothing.
  A started/paused/resumed WO keeps one timestamp and no gap record.
- **The sink exists and is pinned.** `work_orders.actual_hours` feeds
  invoicing (with an `estimated_hours` fallback), reconciliation and
  analytics, and **Gate 9 pins it over HTTP** — complete with 2.0 hours
  must still bill 20000 cents.
- **Critic finding — permission trap:** `tech` and `apprentice` hold no
  `manage_shop`; only `owner` and `service_writer` do. Gating clock-in
  on it would lock out the mechanics and admit the front desk. No seeded
  permission is time-related.
- **Critic finding — no Android push:** no FCM anywhere, the sender is
  APNs-only, and 202 is on the Android-only critical path. The
  forgotten-timer answer had to be server-side.
- **Critic finding — bump ritual:** two annotated `f9-noqa: ssot-pin`
  contract pins at 46 plus the TAG_CATALOG double-check are part of the
  cost of migration 047.
- **User decisions:** any active member, caller-attributed · auto-fill
  `actual_hours` on complete only when none supplied (manual wins) ·
  one open entry per mechanic, clocking in elsewhere auto-closes ·
  server-side cap auto-closes a forgotten entry and flags it.
- **Two things flagged, not fixed:** offline clock-in (replay would
  record the wrong time) and the per-mechanic subscription requirement
  (no seat model exists).
- **Next milestone:** plan commit + push → migration 047 + time-entry
  repo + router + complete-integration → mobile hook/formatter/section/
  actions → device smoke incl. the background-recompute check.

---

### 2026-09-04 15:37 — Build complete (backend + mobile), regression green

- **Backend (`6120bf0`):** migration 047 `work_order_time_entries`
  (SCHEMA_VERSION 46→47, both annotated pins advanced) ·
  `shop/time_entries.py` · `api/routes/time_tracking.py` with 5 routes ·
  `time-tracking` TAG_CATALOG entry · two new ProblemDetail mappings ·
  the complete-transition auto-fill. **33 tests.** Full regression
  **4735 passed, 0 failed**.
- **Mobile (`cd4b304`):** `formatDuration.ts` (three pure functions) ·
  `useWorkOrderTimeEntries` · the 9th section variant and its card
  branch · clock in/out in the Actions card with the running elapsed
  shown large · an Alert naming the auto-closed work order · time added
  to the focus refresh. **+35 tests → 75 suites / 931**; tsc clean;
  eslint 0 errors repo-wide.
- **Two invariants were pushed down rather than guarded.** One open
  entry per mechanic is a **partial unique index**, and its test inserts
  straight past the repo to prove the database refuses. Elapsed time is
  **derived from the server timestamp on every tick and every AppState
  'active'**, never accumulated — the hook test simulates a ten-minute
  JS-thread suspension and pins that foregrounding yields 690s, not 90
  plus whatever ticks happened to fire.
- **Two test-fixture bugs, both mine, caught on the first run:** the
  auto-close test put its second work order in a *different* shop (the
  404 was correct), and the Gate 9 re-assertion read a `subtotal_cents`
  column that does not exist — the API exposes it, the table stores
  `subtotal`. The second was worth the trip: routing the assertion
  through the same `/invoices/generate` route Gate 9 uses makes the two
  tests pin the same surface.

### 2026-09-04 15:37 — SMOKE: server leg verified end to end; device leg blocked

Run against the live dev server. Every server-side behaviour confirmed:

- clock in → entry created; `mine/open` reports it
- **clock in on a second job auto-closed the first after 25s**, and the
  response named the entry and work order it stopped
- only one open entry remained afterwards
- completing with nothing supplied **auto-filled from the ledger**
  (`filled 0.01h from 25s of tracked labor`, logged server-side)
- **manual wins: 9h on the clock, 2.0 typed → `actual_hours` 2.0**, and
  the 9h entry was still closed and recorded rather than discarded
- completing closed the running timer
- **a 30h forgotten entry capped at 12.0h with `needs_review = 1`**, and
  logged `auto-closed stale time entry … at the 12.0h cap`

**The device leg did not run.** The tailnet HTTPS proxy is wedged —
nothing listening on 443 while the tunnel itself is healthy and pings
the phone in 59ms — so the LAN fallback was prepared instead; then the
Mac moved onto a different network (en0 became a hotspot address) and
the wireless device tunnel failed with `RemotePairingError 4`. The build
succeeds and installs are the only blocked step. Outstanding: the
ticking display, the clock buttons, and the background→foreground
recompute on real hardware.

### 2026-09-04 15:37 — Documentation update + close

- `202_implementation.md` → v1.1 (checklist with an honest `[~]` on the
  device row, deviations, results, key finding). Docs → `completed/`.
- Mobile project docs: `implementation.md` 0.2.3 → 0.2.4 + Phase History
  row, root `phase_log.md` entry, ROADMAP 202 ✅, **F59/F60/F61** filed.
- Branches fast-forwarded into `master` / `main`, pushed.
