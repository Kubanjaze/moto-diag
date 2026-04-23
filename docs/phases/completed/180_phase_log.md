# MotoDiag Phase 180 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0. Scope: 24 HTTP endpoints across 9 shop subsurfaces
(profile, members, customers, intake, work-orders, issues, invoices,
notifications, analytics). Pragmatic mapping — NOT 1:1 for Track G's
123 subcommands. Zero migration — Phase 160-173 shipped all the
repos. All routes require `require_tier("shop")` + shop membership
check via Phase 172 RBAC.

### 2026-04-22 — Build + finalize complete

Files shipped (~840 LoC):
- `api/routes/shop_mgmt.py` (838 LoC): 24 endpoints + 11 Pydantic
  schemas + `require_shop_access` helper (mode-aware: bare =
  membership check, `permission=manage_shop` = stricter check) +
  `TransitionAction` Literal for 7-state work-order lifecycle
  dispatch in one POST.
- `api/app.py` +2 LoC: mount shop_mgmt_router.

Bug fixes during build:
- **Bug #1**: Original plan used `permission="read_shop"` on read
  routes, but Phase 112's permission catalog has no `read_shop` —
  only `manage_shop`. Refactored `require_shop_access` to default to
  membership check (any active member) and only require `manage_shop`
  on the 3 admin write endpoints (update_shop_profile, add_member,
  deactivate_member). This is actually better product UX — techs can
  write WOs without owner permission.
- **Bug #2**: `update_shop` repo signature is `(id, dict, db_path)`
  not `**kwargs`. Caller fixed.
- **Bug #3**: Triple-imported `add_shop_member` due to a placeholder
  walrus-op-in-import I left during scaffolding. Cleaned.

22 tests GREEN in 31.13s after fixes. Zero regressions in focused
API + Track G run.

Project-level updates:
- `implementation.md` Phase History: append Phase 180
- `implementation.md` endpoint inventory +24 shop endpoints
- `docs/ROADMAP.md`: Phase 180 → ✅
- Project version 0.12.3 → **0.12.4**

**Key finding:** Phase 180 is the biggest pure-composer router on
Track H so far (838 LoC, 24 endpoints, zero new business logic).
With 175-180 done, Track H has **51 HTTP endpoints across 8 sub-
surfaces** — the full mechanic + shop API surface that Track I's
mobile app will consume. Phase 181 WebSocket adds live OBD streams,
182 PDF reports, 183 OpenAPI enrichment, 184 Gate 9 closes Track H.
