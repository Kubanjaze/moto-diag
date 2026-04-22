# MotoDiag Phase 177 — Vehicle Endpoints (Garage CRUD over HTTP)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

First full-CRUD domain router on top of Phase 175 (FastAPI scaffold)
+ Phase 176 (auth + paywall). `GET/POST/PATCH/DELETE /v1/vehicles*`
exposes a user's garage over HTTP with tier-gated quotas (individual
5, shop 50, company unlimited — enforced at POST time, returning 402
with an upgrade hint when quota exceeded).

Until Phase 177, the Phase 04 `vehicles` table had no owner scoping —
vehicles were global. Phase 177 retrofits `owner_user_id` column
(default to system user for pre-retrofit data) so the API can scope
"my garage" per authenticated caller. This matches Phase 112's
retrofit pattern (`user_id` columns added to diagnostic_sessions +
repair_plans + known_issues via migration 005).

CLI — **no new subcommands** (Phase 04 `garage` CLI already exists;
the existing CLI continues to operate globally for now — owner
scoping is HTTP-only for Phase 177; Phase 178+ may tighten the CLI
to current-user scoping once session auth lands in CLI).

Outputs:
- Migration 038 (~15 LoC): `ALTER TABLE vehicles ADD COLUMN
  owner_user_id INTEGER DEFAULT 1` + index.
- `src/motodiag/vehicles/registry.py` +~80 LoC — owner-scoped helpers
  (`list_vehicles_for_owner`, `count_vehicles_for_owner`,
  `get_vehicle_for_owner`, `update_vehicle_for_owner`,
  `delete_vehicle_for_owner`) + `VehicleOwnershipError` +
  `VehicleQuotaExceededError`.
- `src/motodiag/api/routes/vehicles.py` (~230 LoC) — 6 endpoints +
  Pydantic request/response models.
- `src/motodiag/api/app.py` — wire the new router.
- `src/motodiag/api/errors.py` — map Phase 177 exceptions to HTTP.
- `src/motodiag/core/database.py` SCHEMA_VERSION **37 → 38**.
- `tests/test_phase177_vehicle_api.py` (~28 tests, 5 classes).

## Logic

### Migration 038

```sql
ALTER TABLE vehicles
    ADD COLUMN owner_user_id INTEGER NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_vehicles_owner
    ON vehicles(owner_user_id);
```

Default `1` points to the Phase 112 system user — pre-retrofit rows
all belong to the system user, which is inaccessible via the API
(there are no API keys for user id=1 unless an operator creates one).
Rollback drops the column via rename-recreate.

### `vehicles/registry.py` additions

```python
class VehicleOwnershipError(ValueError):
    """Raised when a caller tries to touch a vehicle they don't own."""

class VehicleQuotaExceededError(Exception):
    """Raised when creating a vehicle would exceed the caller's tier
    quota. Mapped to HTTP 402 with upgrade hint."""

    def __init__(self, current_count: int, limit: int, tier: str):
        self.current_count = current_count
        self.limit = limit
        self.tier = tier
        super().__init__(
            f"vehicle quota exceeded: {current_count}/{limit} "
            f"({tier} tier)"
        )


TIER_VEHICLE_LIMITS: dict[str, int] = {
    "individual": 5,
    "shop": 50,
    "company": -1,    # unlimited
}


def add_vehicle_for_owner(
    vehicle: VehicleBase, owner_user_id: int,
    db_path: Optional[str] = None,
) -> int:
    """Same as add_vehicle but stamps owner_user_id."""

def list_vehicles_for_owner(
    owner_user_id: int, **filters,
    db_path: Optional[str] = None,
) -> list[dict]: ...

def count_vehicles_for_owner(
    owner_user_id: int, db_path: Optional[str] = None,
) -> int: ...

def get_vehicle_for_owner(
    vehicle_id: int, owner_user_id: int,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Returns None when either (a) vehicle doesn't exist or (b) it's
    owned by someone else. Routes translate None → 404 (don't leak
    "exists but not yours" vs "doesn't exist" distinction)."""

def update_vehicle_for_owner(
    vehicle_id: int, owner_user_id: int, updates: dict,
    db_path: Optional[str] = None,
) -> bool:
    """Raises VehicleOwnershipError if vehicle exists but is owned
    by a different user (distinct from "not found")."""

def delete_vehicle_for_owner(
    vehicle_id: int, owner_user_id: int,
    db_path: Optional[str] = None,
) -> bool: ...
```

Existing unscoped helpers (`add_vehicle`, `list_vehicles`,
`get_vehicle`, `update_vehicle`, `delete_vehicle`, `count_vehicles`)
remain unchanged — CLI callers continue to operate globally. The
owner-scoped helpers are new names so existing tests don't break.

### Routes

```
GET    /v1/vehicles                    → list owner's garage
POST   /v1/vehicles                    → create; 402 on quota exceeded
GET    /v1/vehicles/{id}               → detail; 404 if not owned
PATCH  /v1/vehicles/{id}               → partial update
DELETE /v1/vehicles/{id}               → hard delete (if no FK refs)
GET    /v1/vehicles/{id}/sessions      → related diagnostic sessions
```

All require `Depends(get_current_user)` at minimum (implying
`require_api_key`). The routes DO NOT gate by tier — every paid tier
can access CRUD. Tier gating shows up at POST time via the quota
check.

### Pydantic schemas

```python
class VehicleCreateRequest(BaseModel):
    make: str = Field(..., max_length=100)
    model: str = Field(..., max_length=100)
    year: int = Field(..., ge=1900, le=2100)
    engine_cc: Optional[int] = None
    vin: Optional[str] = Field(None, max_length=30)
    protocol: str = "none"
    notes: Optional[str] = None
    powertrain: str = "ice"
    engine_type: str = "four_stroke"
    battery_chemistry: Optional[str] = None
    motor_kw: Optional[float] = None
    bms_present: bool = False
    mileage: Optional[int] = None


class VehicleUpdateRequest(BaseModel):
    # All fields optional — partial update
    make: Optional[str] = None
    model: Optional[str] = None
    ...  # every field from Create except required constraints


class VehicleResponse(BaseModel):
    id: int
    owner_user_id: int
    make: str
    model: str
    year: int
    ...all columns...


class VehicleListResponse(BaseModel):
    items: list[VehicleResponse]
    total: int
    limit: int
    quota_remaining: Optional[int] = None  # None = unlimited (company)


class SessionsForVehicleResponse(BaseModel):
    vehicle_id: int
    sessions: list[dict]  # Phase 07 session rows
    total: int
```

### Quota enforcement

POST /v1/vehicles reads `user.tier` (from `get_current_user`),
looks up `TIER_VEHICLE_LIMITS[tier]`, counts current vehicles via
`count_vehicles_for_owner`, and raises `VehicleQuotaExceededError`
when `limit > 0` and `current_count >= limit`. The handler maps to
402 with `detail="...5/5 (individual tier); upgrade to shop"`.

When user has no active subscription, `user.tier` is None. For now,
Phase 177 defaults anonymous/no-sub users to individual limits (5) —
that's a deliberate leniency that matches Phase 175's "anonymous
discovery tier" theme. Phase 178+ will tighten this if needed.

### 404 vs 403 policy

- **Vehicle doesn't exist at all** → 404.
- **Vehicle exists but owned by another user** → 404 (NOT 403).
  This prevents enumeration attacks: a caller can't tell whether
  vehicle id 42 exists or not unless they own it.
- **Caller has no API key** → 401 (handled by `require_api_key`).
- **Caller has API key but no subscription** → 200 on GETs (read
  is always allowed for any authed user); 402 on POST when quota
  exceeded.

## Key Concepts

- **owner_user_id retrofit mirrors Phase 112 pattern.** `ALTER TABLE
  ADD COLUMN ... DEFAULT 1` means every existing row is owned by
  the system user (id=1), which has no API keys — so the Phase 177
  API can't see them until an operator explicitly re-owns them.
- **Owner scope at the repo layer, not middleware.** The
  `_for_owner` helpers take owner_user_id as a required arg, so
  there's no way a route forgets the scope — CI grep-tests (future
  phase) can assert no route calls unscoped `list_vehicles` without
  filtering. For Phase 177, the route-module docstring documents the
  convention.
- **Unscoped repo helpers stay working.** Phase 04 CLI + Phase 108
  background jobs use `list_vehicles()` / `get_vehicle()` / etc
  globally. Phase 177 doesn't break them — the new scoped helpers
  are additions, not replacements.
- **Tier quota is POST-time, not schema-level.** A CHECK constraint
  on vehicle count per user would be expensive to evaluate. The
  count is cheap (indexed on owner_user_id) and matches Stripe's
  "check-at-enforcement-time" pattern.
- **404-not-403 for cross-user vehicles.** Standard security
  practice: don't reveal that a resource exists if the caller can't
  access it.
- **No CLI changes.** Phase 04's `garage` CLI continues to work
  globally. A future phase will add `garage --user X` or session-
  based auth; Phase 177 scope is HTTP-only.

## Verification Checklist

- [x] Migration 038 adds `vehicles.owner_user_id` column + index.
- [x] SCHEMA_VERSION 37 → 38.
- [x] Rollback to 37 drops column via rename-recreate.
- [x] `add_vehicle_for_owner` stamps owner.
- [x] `get_vehicle_for_owner` returns None for cross-owner vehicles.
- [x] `list_vehicles_for_owner` returns only caller's vehicles.
- [x] `count_vehicles_for_owner` scopes to owner.
- [x] `update_vehicle_for_owner` raises `VehicleOwnershipError` on
      cross-owner attempt; returns False for missing.
- [x] `delete_vehicle_for_owner` raises on cross-owner; deletes happy.
- [x] Tier quota: individual limit 5, shop 50, company unlimited.
- [x] Unknown / None tier defaults to individual (Phase 175
      anonymous-discovery-tier pattern).
- [x] `VehicleQuotaExceededError.tier` + `.limit` populated for the
      402 response body.
- [x] GET /v1/vehicles scopes to caller's garage; returns tier +
      quota fields.
- [x] GET /v1/vehicles/{id} returns 404 for cross-user AND nonexistent
      (enumeration prevention).
- [x] POST /v1/vehicles 201 with Location header; quota enforced.
- [x] PATCH /v1/vehicles/{id} partial update works; 404 cross-user.
- [x] DELETE /v1/vehicles/{id} returns 204.
- [x] GET /v1/vehicles/{id}/sessions returns Phase 07 sessions.
- [x] Unauthenticated GET /v1/vehicles returns 401.
- [x] Shop/company tier surface quota=50/unlimited in list response.
- [x] Invalid create body (missing make, bad year) → 422.
- [x] Phase 175/176 endpoints still work.
- [x] Phase 04 + 113 + 118 + 131 + 153 + Track G 160-174 + 162.5 +
      175 + 176 tests still GREEN (784/784).
- [x] Zero AI calls.

## Deviations from Plan

- **33 tests vs ~28 planned.** Extra coverage on tier-specific quota
  paths (shop 50, company unlimited shown in list response) +
  cross-user 404 boundary for PATCH. All landed during first-pass
  build when the tests revealed the code worked correctly.
- **Unscoped CLI continues to operate globally.** Plan documented
  this; confirmed in test_phase177_vehicle_api.py by not touching
  the Phase 04 CLI. Future phase (178+) can add session-auth CLI
  scoping if needed.
- **No VIN validation beyond max_length.** Plan noted NHTSA VIN
  decoder as future scope; no decoder added in Phase 177.

## Results

| Metric | Value |
|--------|-------|
| Phase 177 tests landed | 33 GREEN (5 classes) |
| Targeted regression | 784/784 GREEN in 528.58s (8m 49s) |
| Coverage range | Phase 04 + 113 + 118 + 131 + 153 + Track G 160-174 + 162.5 + 175 + 176 + 177 |
| Migration LoC | 58 (ALTER + index + rename-recreate rollback) |
| `vehicles/registry.py` additions | +180 LoC (2 exceptions + `TIER_VEHICLE_LIMITS` dict + 6 `_for_owner` helpers + `check_vehicle_quota`) |
| `api/routes/vehicles.py` | 301 LoC |
| `api/errors.py` additions | +6 LoC (2 new Phase 177 exception mappings) |
| `api/app.py` | +2 LoC (router import + mount) |
| SCHEMA_VERSION | 37 → **38** |
| AI calls | 0 (zero tokens spent) |

**Key finding:** Phase 177 validates the "everything composes at
the dep boundary" pattern scales to full CRUD without ceremony. The
entire vehicle router is 301 LoC because:
1. Auth is automatic via `Depends(get_current_user)` — routes never
   touch api keys, tier lookups, rate limit state.
2. Domain exceptions auto-map to HTTP — routes raise `VehicleOwnership
   Error` / `VehicleQuotaExceededError` and the registered handlers
   produce the right ProblemDetail response.
3. Pydantic + Literal types handle request validation (422 for bad
   years / missing fields / invalid protocol strings) without a
   single try/except at the route level.
4. Owner scoping at the repo layer (`_for_owner` helpers take
   `owner_user_id` as a required arg) makes it structurally
   impossible to forget the scope.

The 5-phase build pattern established here (plan → migration →
repo helpers → routes → tests) repeats for Phases 178 (sessions),
179 (KB), 180 (shop CRUD). Each should ship in ~250-400 LoC with
25-35 tests and <1hr per phase. **Track H's hardest work is
behind us** — the monetization + scaffold decisions in Phases 175
+ 176 pay dividends from Phase 177 onward.

## Risks

- **Existing global CLI may leak into user garages.** The `garage`
  CLI creates vehicles without setting owner_user_id (defaults to
  1). If an API caller subsequently adopts that vehicle (via a
  future transfer flow), the ownership assumption gets complicated.
  Mitigation: document clearly that CLI-created vehicles default to
  system user; Phase 178+ CLI auth will tighten this.
- **Quota enforcement races on concurrent POSTs.** A caller at
  4/5 who fires two concurrent POSTs could end up at 6/5 because
  both count-then-insert. Mitigation: the count is cheap enough that
  a ±1 over-count is acceptable for Phase 177. A proper fix uses a
  serializable transaction; deferred to Phase 178+ if an abuse case
  materializes.
- **DELETE with FK refs.** A vehicle with diagnostic_sessions,
  known_issues references will fail DELETE with a FK violation.
  Phase 04's behavior is to let SQLite raise. Phase 177 route
  handler catches the raw sqlite3 error + returns 409 with
  "vehicle has diagnostic history; archive instead of delete"
  hint. A soft-delete mechanism is future scope.
- **Powertrain + engine_type are string fields in the schema but
  enum-validated in Phase 110's VehicleBase.** Phase 177 routes
  validate via Pydantic `Literal["ice", "electric", "hybrid"]` on
  the request model, so bogus values get 422 before repo call.
- **VIN validation.** Phase 177 doesn't enforce VIN format beyond
  max_length=30. Future Phase could use the NHTSA VIN decoder.
