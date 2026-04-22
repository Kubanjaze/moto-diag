# MotoDiag Phase 178 — Diagnostic Session Endpoints

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Expose Phase 07 `diagnostic_sessions` over HTTP with owner scoping +
monthly session quota (individual=50, shop=500, company=unlimited).
Sessions are the core product activity — a mechanic opening a session
on their bike, logging symptoms + fault codes, getting a diagnosis,
closing it out. This router makes all of that work through
`/v1/sessions*` instead of the Phase 123 `diagnose` CLI.

**No migration needed.** Phase 112's retrofit already added `user_id`
to `diagnostic_sessions` — Phase 178 is pure repo + route additions
on existing substrate. Follows the Phase 177 recipe: `_for_owner`
repo helpers + Literal-typed Pydantic schemas + quota check at POST
+ cross-user 404 policy.

CLI — no new subcommands (Phase 123 `diagnose` CLI remains).

Outputs (~480 LoC + ~32 tests):
- `src/motodiag/core/session_repo.py` +~120 LoC — 6 owner-scoped
  helpers + `SessionOwnershipError` + `SessionQuotaExceededError`
  + `TIER_SESSION_MONTHLY_LIMITS` + `count_sessions_this_month_for_owner`.
- `src/motodiag/api/routes/sessions.py` (~360 LoC) — 9 endpoints +
  Pydantic schemas.
- `src/motodiag/api/app.py` — mount the router.
- `src/motodiag/api/errors.py` — map 2 new exceptions.
- No migration. SCHEMA_VERSION stays at 38.
- `tests/test_phase178_session_api.py` (~32 tests, 5 classes).

## Logic

### Monthly quota tracking

```python
TIER_SESSION_MONTHLY_LIMITS = {
    "individual": 50,
    "shop": 500,
    "company": -1,
}


def count_sessions_this_month_for_owner(
    owner_user_id: int, db_path: Optional[str] = None,
) -> int:
    """Count sessions created by `owner_user_id` in the current
    calendar month (UTC). Uses `created_at >= <month_start>` — no
    new index needed; existing `user_id` query is fast at small N."""
    month_start = (
        datetime.now(timezone.utc)
        .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    ...
```

Quota check at POST: counts month-to-date; raises when at limit.
Response body hint: "upgrade to shop for 500/month".

### Endpoints

```
GET    /v1/sessions                       list owner's sessions
POST   /v1/sessions                       create session; 402 on quota
GET    /v1/sessions/{id}                  fetch one (404 cross-user)
PATCH  /v1/sessions/{id}                  update allowed fields
POST   /v1/sessions/{id}/close            close (status=closed + closed_at)
POST   /v1/sessions/{id}/reopen           reopen (status=open + clear closed_at)
POST   /v1/sessions/{id}/symptoms         add symptom to list
POST   /v1/sessions/{id}/fault-codes      add fault code to list
POST   /v1/sessions/{id}/notes            append note (Phase 120 extension)
```

### Filter params on list

```
GET /v1/sessions?status=open&vehicle_id=42&since=30d&limit=50
```

`since` supports `Nd` / `Nh` / ISO (same parser as Phase 171).

## Key Concepts

- **No migration.** user_id column already present (Phase 112).
  Owner scoping happens at the repo layer via `_for_owner` helpers
  that take `owner_user_id` as a required arg — same pattern as
  Phase 177.
- **Monthly rolling quota**, not total lifetime. Resets at UTC
  month boundary. No per-user bucket state needed — cheap
  `COUNT(*) WHERE user_id = ? AND created_at >= <month_start>`.
- **Cross-user 404**, same as Phase 177.
- **Lifecycle routes separate from PATCH**. `close` + `reopen` are
  distinct POST endpoints (not PATCH) — mirrors Phase 07's
  dedicated transition functions. PATCH is for diagnosis / severity
  / confidence / cost_estimate fields only (generic updates).
- **Symptoms + fault codes are additive via POST.** Neither is a
  PATCH replacement — the session's symptom list grows as the
  mechanic observes more during the session.

## Verification Checklist

- [x] `_for_owner` helpers added to session_repo (create/get/list/
      count-this-month/check-quota/update/close/reopen/symptom/fault-
      code/note = 11 helpers).
- [x] `count_sessions_this_month_for_owner` ignores prior-month rows
      (test inserts a 2020 row; current-month count stays 0).
- [x] `SessionOwnershipError` (404) + `SessionQuotaExceededError`
      (402) mapped in `api/errors.py`.
- [x] GET /v1/sessions scopes to owner; supports status + vehicle_id
      + since filters.
- [x] `since` parser accepts `Nd`/`Nh`/`Nm` + ISO.
- [x] POST /v1/sessions 201 + Location header.
- [x] 402 on monthly quota exceeded (individual=50/month).
- [x] Shop tier quota=500; company unlimited (None in response).
- [x] GET /v1/sessions/{id} 404 cross-user AND nonexistent.
- [x] PATCH applies allowed fields (status, diagnosis, confidence,
      severity, cost_estimate, ai_model_used, tokens_used).
- [x] POST /close + /reopen lifecycle transitions.
- [x] POST /symptoms + /fault-codes append to JSON lists.
- [x] POST /notes appends via Phase 120 append_note.
- [x] Unauthenticated → 401.
- [x] Phase 07 + 175 + 176 + 177 + 178 tests still GREEN (168/168
      focused run).
- [x] Zero AI calls.

## Deviations from Plan

- 35 tests vs ~32 planned (+3 on since-filter + cross-user patch/
  close + sub-tier quota display — same coverage over-shoot pattern
  as Phase 177).
- No other deviations.

## Results

| Metric | Value |
|--------|------:|
| Phase 178 tests landed | 35 GREEN (5 classes) |
| Focused regression | 168/168 GREEN (Phase 07 + 175 + 176 + 177 + 178) in 1m 58s |
| New code | ~480 LoC |
| `core/session_repo.py` additions | +201 LoC (11 helpers + 2 exceptions + tier map + month helper) |
| `api/routes/sessions.py` | 361 LoC |
| `api/errors.py` additions | +6 LoC (2 new mappings) |
| `api/app.py` | +2 LoC (router mount) |
| Migration | **0** (user_id already from Phase 112) |
| SCHEMA_VERSION | unchanged at **38** |
| AI calls | 0 |

**Key finding:** Phase 178 is the first Track H domain router that
needs **zero migration** — Phase 112's retrofit already added
`user_id` to `diagnostic_sessions`. The pattern is the same as Phase
177 but without the ALTER TABLE dance: `_for_owner` repo helpers +
route handlers + Pydantic schemas + quota check + tests. **Single-
pass, no fixups** — the scaffold is now so settled that adding
domain routers feels like filling in a table. Phases 179 (KB search)
and 180 (shop CRUD) should each take <1hr with the same pattern.

## Risks

- **Monthly quota boundary races.** Two concurrent POSTs at the
  49th session could both pass the check + create session #51.
  Acceptable for Phase 178 — Phase 184+ can add serializable txn
  if abuse shows up. Phase 176 rate limit (60/min individual) makes
  sustained abuse costly anyway.
- **No user_id on pre-Phase-112 sessions.** All pre-retrofit
  sessions default to user_id=1 (system user, no API keys).
  Invisible via API just like Phase 177 vehicles.
