# Phase 198 — Offline Mode + Local Database — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-02 | **Completed:** 2026-09-02
**Repos:** `Kubanjaze/moto-diag-mobile` + `Kubanjaze/moto-diag`, both on
branch `phase-198-offline-local-db`

---

### 2026-09-02 10:45 — Plan written (Step 0 audit + v1.0)

- **Step 0 findings:** mobile SQLite greenfield; backend kb.py has no bulk
  export → Commit 0 required (193 pattern); **dtc_codes = 55 rows** →
  user's "first-connect + delta" choice honestly refined to
  version-stamped full-snapshot sync (delta machinery would outweigh the
  data ~100:1; refinement flagged in the plan, not silently built).
- **User decisions:** DTC offline via first-connect sync; op-queue MVP =
  sessions + notes with pending badge.
- **Spike Gate carried forward (196B lesson):** `@op-engineering/op-sqlite`
  + netinfo must prove New-Arch viability on-device before dependent code.
- **Next milestone:** plan commit + push → backend Commit 0 → mobile spike
  → build.

---

### 2026-09-02 11:20 — Commit 0 + Spike Gate + mobile build complete; device smoke pending

- **Backend Commit 0 (`a2c3614`):** `GET /v1/kb/export` + sha256 content-
  hash `kb_version`; 4 tests green on the canonical interpreter.
- **Spike Gate PASS:** op-sqlite open/create/insert/select round trip +
  netinfo connectivity, on-device under mandatory New Arch. Spike file
  deleted in the build commit per pattern.
- **Mobile build (`e652197`):** schema v1 + DtcCacheStore (atomic
  replace-all ingest) + kbSync (stamp compare) + op-queue (durable FIFO,
  stop-on-first-failure, temp-id remap, retriable/terminal semantics) +
  offlineBoot (cold mount + regain; cold-start guard extended) + hook
  cache fallbacks (`fromCache`) + NewSessionScreen offline queue path +
  PendingOpsBadge. openapi snapshot + generated types refreshed with the
  export route. **68 suites / 851 tests green; tsc clean.**
- **Commit-infra note:** first commit attempt tripped lint-staged
  (jest.setup.js missing `eslint-env jest`) and its auto-revert
  conflicted, parking the edits in lint-staged's backup stash ABOVE the
  protected video-task stash; recovered via `stash apply` + verified
  restore + drop — video-task stash back at stash@{0}. Watch-item: on
  this repo, lint-staged failures can shuffle stash positions.
- **Remaining gate (device smoke):** airplane mode → DTC lookup from
  cache (offline chip) + create session (Saved offline + badge) → radio
  on → queue replays server-side + badge clears.

---

### 2026-09-02 14:50 — Bug fix #1: silent offline-pass failures made loud + stamp-wedge self-heal

- **Issue:** first device smoke — offline DTC search returned empty;
  offline session create fell through to "Start failed"; no diagnostics.
- **Root cause (as then understood; CORRECTED by fix #2):** attributed to
  op-sqlite `transaction()` semantics. The real killer was fix #2's
  constraint; this fix's lasting value: explicit BEGIN/COMMIT over the
  spike-proven `execute` surface, `[198 offline]` diagnostics replacing
  silent catches, and the stamp-without-rows self-heal in kbSync.
- **Files:** src/db/database.ts, src/db/dtcCache.ts, src/services/kbSync.ts,
  src/services/offlineBoot.ts, src/screens/NewSessionScreen.tsx (+tests)
- **Verified:** commit `2194145`; 852 green; the diagnostics then surfaced
  fix #2's true error on the next device run — exactly their job.

### 2026-09-02 15:00 — Bug fix #2: DTC identity is (code, make) — schema v2

- **Issue:** retest console: `[op-sqlite] constraint failed:
  dtc_codes.code` — ingest still aborted.
- **Root cause:** v1 schema declared `code TEXT PRIMARY KEY`; backend DTC
  identity is **(code, make)** (make-specific overrides; real data holds
  P0562 twice: generic + Harley-Davidson). One duplicate aborted every
  snapshot ingest. F9 substrate mismatch — assumed invariant never
  checked against real data.
- **Fix:** schema v2 migration (rowid PK + code index, kb_meta cleared for
  clean resync; sequential MIGRATIONS list); `getDtc` mirrors backend
  `get_dtc(code, make=None)` generic-first semantics; duplicate-pair
  fixture + regression guard.
- **Files:** src/db/database.ts, src/db/dtcCache.ts (+fakes/tests)
- **Verified:** commit `2fa13e4`; 853 green; device retest — P0171 cached
  AND both P0562 rows rendered offline.

### 2026-09-02 15:05 — Bug fix #3: pending badge moved to where users look

- **Issue:** smoke beats passed except "visible pending badge" — it lived
  only on the New Session form, which the Saved-offline alert navigates
  away from. User looked at the Sessions list; badge effectively invisible.
- **Fix:** `PendingOpsBadge` also rendered atop SessionsListScreen. Local
  pending-session ROWS in the list stay a filed follow-up (F50) — the
  server-backed list stays honest.
- **Files:** src/screens/SessionsListScreen.tsx
- **Verified:** commit `59140e3`; device retest — badge visible offline,
  cleared on replay.

### 2026-09-02 15:05 — >2-bugs STOP-rule cluster analysis

Three fixes in one build → mandated common-cause diagnosis: fixes #1+#2
share one root — **the Spike Gate proved too little** (verified `execute`,
built on `transaction()`) **and Step 0 verified shapes, not data
invariants** (the duplicate-code check was a 10-second SELECT run only
after failure). Fix #3 is UX placement, separate. **Process lesson for
future phases:** spike gates must exercise every driver surface the build
will touch; Step 0 audits must probe key data invariants (uniqueness,
nullability) of any dataset being mirrored, not just its schema shape.

### 2026-09-02 15:10 — DEVICE SMOKE: FULL PASS — Phase 198 ✅ Complete

- **Beats, both sides of the wire:** boot sync (`GET /v1/kb/export 200`
  server-witnessed; migration v2 forced clean resync) → airplane mode:
  P0171 served from cache, P0562 shows BOTH rows (the fixed pair),
  session create → "Saved offline", **"1 pending sync — will send when
  online" badge on the Sessions list** → radio on: **`POST /v1/sessions
  201 Created`** (server-witnessed replay), badge cleared, session row
  appeared. User verdict on the badge copy: "I like that, looks good."
- Environment note: Xcode attached over network dies at airplane-mode —
  cable attach for offline-phase console (recorded for future smokes).
- Docs → `completed/` in this commit; mobile project docs updated in the
  mobile close-out commit (F50 filed).
