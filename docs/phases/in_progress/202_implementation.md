# Phase 202 — Mechanic Time Tracking

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-04

## Existing-code audit (Step 0 — run 2026-09-04, before this plan)

Six parallel readers plus a completeness critic. The critic earned its
place: it caught three things no reader raised, two of which change the
plan (the permission trap and the Android push gap).

- **Time intervals — GREENFIELD, and not reconstructible.** No table,
  column, function, route or CLI command records a per-mechanic time
  interval. Worse than absent: the lifecycle timestamps actively cannot
  stand in for one. `start_work` **overwrites `started_at` on every
  start** (`shop/work_order_repo.py`, docstring says so explicitly) and
  `pause_work` writes **no timestamp at all** — it flips status and sets
  `on_hold_reason`. So a WO that was started, paused and resumed retains
  exactly one timestamp and no record of the gap. Nearest precedents are
  spans of a different kind: `work_order_assignments`
  (assigned_at/unassigned_at, per mechanic but about assignment) and
  `bay_schedule_slots` (actual_start/end, per bay). The first is the DDL
  template; neither is the thing.
- **The sink already exists and is load-bearing — EXTENSION.**
  `work_orders.actual_hours` is a manually-supplied REAL with three live
  consumers: invoicing bills labor as hours × rate with an
  `estimated_hours` fallback and raises when both are absent
  (`shop/invoicing.py:344,349`); the labor reconciler compares AI
  estimates against it; analytics reports on it. It is in
  `update_work_order`'s whitelist (`work_order_repo.py:98`). **Gate 9
  pins the contract over HTTP**: complete with `actual_hours: 2.0` must
  still yield `subtotal_cents == 20000`
  (`tests/test_phase184_gate9.py:271,288`). Any auto-fill must leave
  that path byte-identical.
- **Router shape — pure composition.** `api/routes/parts.py` (Phase 201)
  is the template: `require_shop_access` + a WO-belongs-to-shop 404 +
  `Literal` verbs + best-effort `notify_*` with self-suppression.
  Domain exceptions already map to ProblemDetail in `api/errors.py`.
- **CRITIC FINDING — the permission trap.** The seeded matrix
  (`core/migrations.py:220-233`) gives **`tech` and `apprentice` no
  `manage_shop`**; only `owner` and `service_writer` hold it. Gating
  clock-in on the one permission mode routes use today would lock the
  mechanics out while letting the front desk clock in. None of the 12
  seeded permissions is time-related. Note also that **assignment is
  enforced nowhere today** — any active member may transition or assign
  any WO.
- **CRITIC FINDING — push cannot be the safety net.** There is no
  Firebase/FCM dependency in `package.json` or `android/app/build.gradle`,
  the mobile lib is `@react-native-community/push-notification-ios`
  (no-ops off iOS), and the backend sender speaks only APNs headers —
  yet 202 sits on the **Android-only shippable critical path**
  (201 → 202 → 203 → 204). A "you're still clocked in" push would reach
  iOS only. The forgotten-timer answer must therefore be server-side.
- **CRITIC FINDING — the schema-bump ritual.** Two tests hard-pin the
  live number with `f9-noqa: ssot-pin` annotations
  (`test_phase184_gate9.py:591`, `test_phase191b_serve_migrations.py:100`)
  and the SSOT lint requires exactly that annotated form. Migration 047
  costs: migration + `SCHEMA_VERSION` + both pins with updated rationale
  + rollback_sql. A new router tag is contract-checked twice
  (`test_phase183_openapi.py::test_all_tags_present` and
  `scripts/check_f9_patterns.py`), so `time-tracking` must land in
  TAG_CATALOG in the same commit.
- **Mobile — MIXED.** Clock in/out is an extension: the transition hook
  already carries the action union and an **unused `actualHours`
  option**, and the Actions card derives buttons from status. The live
  TIMER is greenfield: no persisted start timestamp, no hours formatter,
  the only elapsed display is an in-memory video tick deliberately
  killed on background, `Info.plist` has **no `UIBackgroundModes`**
  (the Phase 197 deferral holds), and the client has **no notion of its
  own user id** — which shapes the API (the server must answer "my open
  entry", the client cannot ask for a user's entries).
- **Reserved elsewhere, deliberately out of scope:** payroll, shifts and
  timesheets appear in no track; Track O reserves booking/calendars,
  per-mechanic P&L, and variance analysis.

**User decisions (2026-09-04):** any active member may clock in, entry
attributed to the caller · the timer **auto-fills `actual_hours` on
complete only when none is supplied** (manual wins) · **one open entry
per mechanic** — clocking in elsewhere auto-closes the previous one ·
a **server-side cap auto-closes** a forgotten entry and flags it
`needs_review`.

## Goal

A mechanic opens the job they're working and taps Clock in. The card
shows time ticking. They walk to another bike, clock in there, and the
first entry closes itself. When the job is completed, the hours the
timer measured become the hours the customer is billed — unless someone
typed a number, which always wins. A timer left running overnight closes
at a cap and is flagged rather than silently billing sixteen hours.

CLI: none new this phase (the existing `motodiag shop` group gains
nothing). Noted as a follow-up candidate for parity with parts.

Run:
- Backend: `pytest tests/test_phase202_time_tracking.py`
- Device smoke: clock in on WO A → elapsed ticks → background the app
  60s → foreground and confirm elapsed recomputed, not frozen → clock in
  on WO B → A auto-closed → complete A → invoice hours match.

Outputs:
- **Backend (branch `phase-202-time-tracking`):**
  - migration 047 `work_order_time_entries`: id, work_order_id FK
    CASCADE, user_id FK, started_at, ended_at (NULL = open),
    duration_seconds (NULL until closed), source
    CHECK IN ('timer','manual'), needs_review INTEGER DEFAULT 0, note,
    created_at, updated_at; index on work_order_id; **partial UNIQUE
    index on (user_id) WHERE ended_at IS NULL** — the one-open-entry
    invariant enforced by the database, not by convention.
    SCHEMA_VERSION 46 → 47 + both annotated pins.
  - `shop/time_entries.py`: `clock_in` (auto-closes the caller's open
    entry first, returns what it closed), `clock_out`,
    `get_open_entry_for_user`, `list_entries_for_wo`,
    `total_seconds_for_wo`, `adjust_entry`, `close_stale_entries`.
    `MAX_OPEN_ENTRY_HOURS` as a settings-backed constant (default 12).
  - **Stale sweep runs lazily on access** — at the top of clock-in and
    the open-entry read — mirroring the mobile cold-start sweep posture.
    No cron, no background worker, nothing new to operate.
  - `api/routes/time_tracking.py`, tag `time-tracking`, all
    `require_tier("shop")` + membership:
    - `POST …/work-orders/{wo_id}/clock-in` · `POST …/clock-out`
    - `GET  …/work-orders/{wo_id}/time-entries`
    - `GET  /v1/shop/{shop_id}/time-entries/mine/open` — "my active job"
    - `PATCH /v1/shop/{shop_id}/time-entries/{entry_id}` — correct
      times / note / clear needs_review
  - **complete-transition integration** in `shop_mgmt.py`: closes any
    open entries on that WO, then fills `actual_hours` from the summed
    entries **only when `req.actual_hours is None`**.
  - tests: the invariant under concurrent clock-ins, auto-close
    round-trip, cap sweep flags `needs_review`, manual-wins on complete,
    auto-fill on complete, **Gate 9's exact path re-asserted here**,
    zero-entry completion still falls back to estimated_hours, tier +
    membership + cross-shop 404 on every route, TAG_CATALOG guard.
- **Mobile (branch `phase-202-time-tracking`):**
  - `api-schema` + `api-types` refresh
  - `useWorkOrderTimeEntries(shopId, woId)`: entries, `myOpenEntry`,
    `clockIn`, `clockOut`, and a **derived** `elapsedSeconds`
  - `src/screens/formatDuration.ts` — pure, tested, `h:mm:ss`
  - **The elapsed display recomputes from `started_at` on every tick and
    on every AppState 'active'** — it never accumulates a counter. That
    is what makes it survive background, foreground and app kill without
    any background mode.
  - new `time` variant in `buildWorkOrderSections` + its
    `WorkOrderSectionCard` branch (entries, who, duration,
    needs_review badge)
  - Clock in / Clock out in the Actions card, driven by `myOpenEntry`
  - tests: hook vs fake api, formatter, section builder + empty state,
    AppState-recompute guard, screen smoke

## Logic

- **Clock in:** sweep stale → close the caller's open entry anywhere →
  insert a new open entry for (wo, caller). Response reports the closed
  entry so the UI can say "stopped your timer on WO 41".
- **Clock out:** stamp `ended_at`, compute `duration_seconds`.
- **Cap:** an entry open longer than `MAX_OPEN_ENTRY_HOURS` closes AT the
  cap (not at discovery time — the mechanic did not work until whenever
  someone next opened the app) and sets `needs_review = 1`.
- **Complete:** close open entries on the WO, then
  `actual_hours = round(total_seconds / 3600, 2)` **iff** none supplied.
- **Elapsed on the client** is always `now - started_at`, never a
  counter — no drift, no background mode, correct after an app kill.

## Key Concepts

- **The database enforces the invariant.** A partial unique index makes
  "one open entry per mechanic" true even under a double-tap or two
  devices, where an application-level check would race.
- **Manual always wins.** Auto-fill is a default, not an authority. This
  is what keeps Gate 9 and the estimated-hours fallback intact, and it
  leaves the mechanic able to bill honestly for time the timer missed.
- **Recompute, don't accumulate.** The single most common timer bug is a
  counter that pauses when the OS suspends the JS thread. Deriving from
  a server timestamp sidesteps background execution entirely — which
  matters because `UIBackgroundModes` is empty and Android has no push.
- **Caller-attributed, not assignee-gated.** Assignment is enforced
  nowhere else; gating here would be a new rule in one corner. And
  `manage_shop` would have excluded the mechanics themselves.
- **The 201 logging lesson applies.** Every state change logs at INFO
  through a `motodiag` logger, and the tests assert the log, because
  F52's "successful sends log" was inert in production for two phases
  behind a green test.

## Verification Checklist

- [ ] Migration 047 applies; partial unique index rejects a second open
      entry for the same user; SCHEMA_VERSION 47; both pins advanced
- [ ] Clock in → open entry; clock in elsewhere → first auto-closed with
      a correct duration; clock out → duration stamped
- [ ] Cap sweep closes at `started_at + MAX_OPEN_ENTRY_HOURS`, not at
      sweep time, and sets `needs_review`
- [ ] Complete with no actual_hours → filled from entries; complete WITH
      actual_hours → supplied value wins, entries still closed
- [ ] **Gate 9's exact scenario re-asserted in this phase's tests** and
      the original still green; zero-entry WO still falls back to
      estimated_hours and still raises when neither exists
- [ ] Every route: 401 / 402 / 403 non-member / 404 cross-shop
- [ ] TAG_CATALOG contains `time-tracking`; both tag contract checks pass
- [ ] Backend full regression green on the canonical interpreter
- [ ] Mobile: hook + formatter + builder + AppState guard green; tsc
      clean; eslint 0 errors
- [ ] Device smoke incl. **background 60s → foreground shows elapsed
      advanced, not frozen**

## Risks

- **Auto-close is destructive and silent by nature.** Clocking in on B
  ends A's entry. Mitigated by returning what was closed and surfacing
  it in the UI; a mechanic who never sees that message will not
  understand where their time went.
- **Clock skew.** All timestamps are server-side UTC ISO strings; the
  client sends none. That is deliberate — a device clock off by an hour
  would otherwise bill an hour.
- **Offline is NOT supported this phase.** The Phase 198 op queue could
  take a new kind, but a clock-in replayed later would record the replay
  time, not the work time — correct offline behaviour needs
  client-supplied timestamps and a trust model for them. Filed as a
  follow-up rather than half-built.
- **The cap default is a guess.** 12 hours is long enough not to trip a
  double shift and short enough to catch an overnight. It is settings-
  backed so a shop can change it without a deploy.
- **Commercial blocker, flagged not fixed:** every mechanic needs their
  own paid shop-tier subscription to reach any shop route — there is no
  seat or inheritance model (`auth/deps.py`). A real two-mechanic shop
  cannot use this feature today without two subscriptions. Filed as a
  follow-up; the smoke uses the established fixture path.
- **No push safety net on Android.** Accepted consequence of the FCM
  gap; the server-side cap is the entire mitigation.
