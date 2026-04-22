# MotoDiag Phase 178 — Diagnostic Session Endpoints

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

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

- [ ] `_for_owner` helpers added to session_repo.
- [ ] `count_sessions_this_month_for_owner` resets at UTC month
      boundary (tested with monkey-patched clock).
- [ ] `SessionOwnershipError` + `SessionQuotaExceededError` mapped
      (404, 402).
- [ ] GET /v1/sessions scopes to owner; supports filters.
- [ ] POST /v1/sessions happy path; 402 on monthly quota exceeded.
- [ ] Shop tier gets 500/mo quota.
- [ ] Company tier is unlimited.
- [ ] GET /v1/sessions/{id} 404 cross-user.
- [ ] PATCH applies allowed fields; rejects bogus status transitions.
- [ ] POST /close transitions status → closed + stamps closed_at.
- [ ] POST /reopen works only from closed status.
- [ ] POST /symptoms + /fault-codes append to JSON lists.
- [ ] POST /notes appends.
- [ ] Unauthenticated → 401.
- [ ] Phase 175/176/177 + Track G regression still GREEN.
- [ ] Zero AI calls.

## Risks

- **Monthly quota boundary races.** Two concurrent POSTs at the
  49th session could both pass the check + create session #51.
  Acceptable for Phase 178 — Phase 184+ can add serializable txn
  if abuse shows up. Phase 176 rate limit (60/min individual) makes
  sustained abuse costly anyway.
- **No user_id on pre-Phase-112 sessions.** All pre-retrofit
  sessions default to user_id=1 (system user, no API keys).
  Invisible via API just like Phase 177 vehicles.
