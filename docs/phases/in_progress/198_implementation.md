# Phase 198 — Offline Mode + Local Database (Mobile)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-02

## Existing-code audit (Step 0 — run 2026-09-02, before this plan)

- **Mobile:** SQLite is greenfield (no dep, no db module). AsyncStorage
  exists (Phase 193 `activeShopStorage` — key-value only, stays for prefs).
  DTC surface today: `useDTC` → `GET /v1/kb/dtc/{code}`, `useDTCSearch` →
  `GET /v1/kb/dtc` — both online-only. Session create: `POST /v1/sessions`
  (NewSessionScreen); notes/symptoms ride session payloads + transcripts.
- **Backend:** `api/routes/kb.py` exposes categories/search/get — **no bulk
  export, no version stamp** → backend Commit 0 required (193 pattern).
- **Scale finding (changes the sync design):** `dtc_codes` = **55 rows**,
  `dtc_category_meta` = 20 — the "full DTC cache" is a few KB. Delta-sync
  machinery would outweigh the data ~100:1.
- **User decisions (2026-09-02):** first-connect sync (see Deviation-in-plan
  below) · op-queue MVP = **sessions + notes** with pending badge ·
  read-only flows (WO lists etc.) stay online-only this phase.
- **Scope refinement vs the user's "first-connect + delta" choice:** at 55
  rows, "delta" degrades honestly to **version-stamped full snapshot** —
  `GET /v1/kb/export` returns everything + a `kb_version` stamp; the app
  refetches the whole snapshot when the stamp changes. Same UX (first-
  connect sync, cheap re-checks), a tenth of the code. Flagged here rather
  than silently built.

## Goal

Make the app's core shop loop survive dead connectivity: DTC lookup/search
work fully offline from a device-local SQLite snapshot (version-stamped,
synced on first connect and re-checked opportunistically), and diagnostic
sessions + notes created offline queue durably and replay in order when
connectivity returns (visible pending state). Screen-on foreground sync
only (the deferred 197 background entitlement remains deferred).

Run:
- Backend: `motodiag serve --host 0.0.0.0`; `pytest tests/ -k kb_export`
- Mobile unit: `npx jest __tests__/db/ __tests__/offline/`
- Device smoke: airplane mode → DTC lookup + create session → radio on →
  queue replays.

Outputs:
- **Backend (branch `phase-198-offline-local-db`, Commit 0):**
  `GET /v1/kb/export` (dtc_codes + dtc_category_meta + `kb_version` stamp
  = max(updated_at)-hash) + tests
- **Mobile (branch `phase-198-offline-local-db`):**
  - dep: `@op-engineering/op-sqlite` — **SPIKE GATE before build** (196B
    lesson: native dep New-Arch viability proven on-device before provider
    code; fallback candidate `react-native-nitro-sqlite`)
  - `src/db/database.ts` (open/migrate; schema v1: `dtc_codes`,
    `dtc_category_meta`, `kb_meta`, `op_queue`)
  - `src/db/dtcCache.ts` (snapshot ingest + offline lookup/search)
  - `src/services/kbSync.ts` (first-connect sync, stamp re-check on app
    foreground + connectivity regain)
  - `src/services/opQueue.ts` (durable FIFO: enqueue session/note ops,
    replay on connectivity, per-op status; conflict posture: server wins,
    failed ops surface for manual retry/discard)
  - `useDTC`/`useDTCSearch` offline fallback (network-first → cache);
    NewSessionScreen offline path (enqueue + pending badge); a small
    offline/pending indicator surface
  - Tests: schema/migration, ingest+lookup parity vs API shapes, sync
    stamp logic, queue FIFO/replay/failure, hook fallbacks, screen smoke
    + wiring guards

## Logic

- **Sync:** on app start with connectivity (and on regain): GET export →
  compare `kb_version` to `kb_meta` → replace-all in one transaction when
  changed. First run blocks DTC-offline availability only (UI shows
  "syncing knowledge base…" once).
- **Offline reads:** hooks try network with a short timeout; on failure,
  serve SQLite (search: `LIKE` over code/name/summary — 55 rows needs no
  FTS) and tag results `fromCache` so screens can show a subtle
  offline chip.
- **Op-queue:** ops persisted as `{id, kind, payload, created_at, status,
  attempts, last_error}`; kinds v1: `create_session`, `add_note`. Replay:
  strict FIFO, stop-on-first-failure (order preserved), auto-retry on
  next regain, badge counts pending; failures beyond N retries surface in
  UI for retry/discard. Server-assigned ids reconciled on replay
  (local temp-id → server id remap for any dependent queued note).
- **Connectivity signal:** `@react-native-community/netinfo` (also needs
  the spike pass — trivial JS-native surface) or fetch-probe fallback;
  plan picks netinfo, spike verifies.

## Key Concepts

- **Spike Gate (blocking):** op-sqlite + netinfo compile + one call each
  on-device under New Arch before any dependent code (196B pattern).
- **SSOT:** DTC row shape mirrors the backend `DTCResponse` schema
  (openapi types already in `src/api-types.ts` — the cache stores what
  the API returns, no divergent shape).
- **Transactional replace-all** for snapshot ingest (never a half-updated
  KB); **transactional enqueue** so an offline create is durable before
  the UI confirms it.
- **F49 watcher check (per its Step-0 trigger):** this phase's nouns do
  not touch pids/poller/LiveData — F49 stays parked.
- **iOS background sync remains out of scope** (197 deferral holds; op-
  queue replays on foreground/regain only).

## Verification Checklist

- [ ] Backend Commit 0: /v1/kb/export + kb_version + tests green
- [ ] Spike Gate: op-sqlite (+netinfo) on-device under New Arch — PASS
      recorded (or fallback dep swapped via documented amendment)
- [ ] Schema v1 migrations + dtcCache ingest/lookup/search green
- [ ] kbSync: stamp-unchanged no-op; stamp-changed atomic replace; first-
      run behavior
- [ ] opQueue: FIFO, stop-on-failure, retry, temp-id remap, durable across
      restart (test via re-open)
- [ ] Hooks fallback + screens: offline chip, pending badge, NewSession
      offline path — smoke + wiring guards green
- [ ] Full mobile regression + backend suite green; tsc clean
- [ ] Device smoke: airplane-mode DTC lookup + offline session create →
      radio on → replay lands server-side; recorded here + phase log

## Risks

- **Native-dep New-Arch surprises** — mitigated by the Spike Gate; two
  candidate deps named.
- **Temp-id reconciliation** is the op-queue's hard edge (note referencing
  an unsynced session) — constrained v1: notes queue only against local
  sessions created in the same offline window or already-synced sessions.
- **Sync races** (sync mid-replay): serialize — replay first, then KB
  sync; both idempotent.
- **Clock skew** on `created_at` ordering — queue order is insertion id,
  not wall clock.
- **55-row KB will grow** (Track B expansion): replace-all stays fine to
  ~10k rows; revisit (FTS + delta) only if the KB 100×es — noted, not
  built.
