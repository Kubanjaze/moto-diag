# Phase 202 — Mechanic Time Tracking — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-04 | **Completed:** —
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
