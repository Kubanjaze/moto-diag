# Phase 189 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-04-27
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile (code) + https://github.com/Kubanjaze/moto-diag (docs)
**Branch:** `phase-189-diagnostic-session-ui` (will be created in mobile repo at Commit 1)

---

### 2026-04-27 — Plan v1.0 written, ROADMAP swap committed

**Roadmap swap:** Phase 189 was originally "DTC code lookup screen" and Phase 190 was "Interactive diagnostic session (mobile)." Swapped at plan time so the canonical mechanic workflow lands first; DTC lookup as a standalone screen + tap-from-SessionDetail integration becomes Phase 190. Both ROADMAP rows updated in the same commit as the plan push.

**Scope locked (after Q&A with Kerwyn):**

1. **Swap confirmed** — 189 = Diagnostic session UI; 190 = DTC code lookup screen (gets the cross-link integration from SessionDetail).
2. **Bottom-tab nav** — first tab nav in the app: Home / Garage / Sessions. `@react-navigation/bottom-tabs` is the one new runtime dep. Each tab is its own native-stack so back-nav within a tab is independent.
3. **Freeze-frame deferred** — no placeholder; Phase 197 live-data screen has the better surface.
4. **Voice input deferred** — Phase 195 owns it. Phase 189 uses plain TextInput throughout.
5. **F1 follow-up folded in as Commit 1** — battery_chemistry → SelectField (extract `BatteryChemistryLiteral` into vehicleEnums.ts; ships the post-merge follow-up before it rots; demonstrates vehicleEnums pattern generalizes to any closed-set Pydantic Literal).

**Backend surfaces consumed (all Phase 178, all gated by `Depends(get_current_user)` + monthly session quota):**

- `GET /v1/sessions` — list + monthly quota metadata
- `POST /v1/sessions` — create (quota-checked)
- `GET /v1/sessions/{id}` — single fetch
- `PATCH /v1/sessions/{id}` — update diagnosis/severity/confidence/cost_estimate
- `POST /v1/sessions/{id}/symptoms` / `/fault-codes` / `/notes` — append-only journals
- `POST /v1/sessions/{id}/close` / `/reopen` — lifecycle

**8 distinct POSTs across the phase.** Every body-bearing or empty-body POST from a new code path is implicitly a Phase 187 transport-regression check (Phase 188 lesson). 2 new client.test.ts regression-guards in Commit 6.

**Critical schema-key difference vs Phase 188 vehicles:** sessions list uses `total_this_month` / `monthly_quota_limit` / `monthly_quota_remaining` (NOT vehicles' `total` / `quota_limit` / `quota_remaining`). Quota is monthly (resets each calendar month) vs vehicles' active count. Plan calls this out + a hook test asserts the keys.

**Files plan:**

- New (8): SessionsListScreen / SessionDetailScreen / NewSessionScreen / useSessions / useSession / TabNavigator + associated types.
- Modified (8): RootNavigator (refactor to tabs) / HomeScreen (drop garage section) / NewVehicleScreen + VehicleDetailScreen (battery_chemistry SelectField) / api.ts (session type aliases) / vehicleEnums.ts (battery_chemistry options) / api/index.ts (re-exports) / package.json+lock / README.md.
- New tests (~25-30): hooks/useSessions, hooks/useSession, types/sessionEnums, types/vehicleEnums (extend), api/client (extend with 2 new POST regression-guards). Target ~115 total tests (90 baseline + ~25).

**Commit plan (7 commits on `phase-189-diagnostic-session-ui` feature branch):**

1. F1 cleanup: battery_chemistry → SelectField + vehicleEnums extraction.
2. Bottom-tab nav refactor + screen stubs (`@react-navigation/bottom-tabs` install + gradle smoke).
3. `useSessions` + SessionsListScreen list rendering + quota footer + RefreshControl.
4. `useSession(id)` + SessionDetailScreen view-only mode + lifecycle buttons.
5. NewSessionScreen form + create (freehand + pick-from-garage paths).
6. SessionDetail mutations: append symptom/fault-code/note + diagnosis edit (PATCH) + close/reopen wiring + 2 transport-guard tests.
7. README + project structure update + version bump 0.0.3 → 0.0.4.

If architect gate finds bugs (Phase 188 precedent: 5 build + 3 fix), follow-up commits 8+ land before rebase-merge.

**Versioning targets at v1.1 finalize:**

- Mobile `package.json`: 0.0.3 → 0.0.4.
- Mobile `implementation.md`: 0.0.5 → 0.0.6.
- Backend `implementation.md`: 0.13.4 → 0.13.5 (Phase History row added).
- Backend `pyproject.toml`: unchanged (Track I is mobile-side; backend package bumps only at backend-side gates).

**Smoke-test plan written into v1.0** (18 steps mirroring Phase 188's 11-step format), to be executed by Kerwyn on emulator at the architect gate after Commit 7 lands.

**Next:** plan commit on backend `master` (this file + 189_implementation.md v1.0 + ROADMAP.md swap), then create `phase-189-diagnostic-session-ui` branch in mobile repo and start Commit 1 (F1 cleanup).
