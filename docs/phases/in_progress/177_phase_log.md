# MotoDiag Phase 177 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session. Scope: first full-CRUD domain router
in Track H. `GET/POST/PATCH/DELETE /v1/vehicles*` exposes the Phase
04 vehicles table via HTTP with owner scoping + tier-gated quotas.

Key design decisions:
- **Retrofit owner_user_id** via migration 038 (Phase 112 pattern).
  Pre-retrofit rows default to system user id=1 — invisible via API
  until an operator explicitly re-owns them.
- **Owner scope at the repo layer**, not in middleware. New
  `_for_owner` helpers take owner_user_id as a required arg.
  Existing unscoped helpers stay working (CLI + background jobs).
- **Tier quota at POST time** (not schema CHECK). Count-then-insert
  races are acceptable for Phase 177; serializable transactions
  deferred.
- **404 for cross-user vehicles**, not 403. Prevents enumeration
  attacks.
- **No CLI changes.** `garage` CLI continues to operate globally;
  Phase 178+ may add session auth + current-user scoping.
- **Tier limits** hardcoded in the route module for Phase 177:
  individual=5, shop=50, company=unlimited. Aligns with Phase 109
  TIER_LIMITS but avoids the CLI→API coupling for now.

Outputs: migration 038 + ~80 LoC in vehicles/registry.py + ~230 LoC
in new api/routes/vehicles.py + 2 new exceptions mapped in
api/errors.py + ~28 tests. Zero AI.
