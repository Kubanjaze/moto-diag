# MotoDiag Phase 180 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0. Scope: 24 HTTP endpoints across 9 shop subsurfaces
(profile, members, customers, intake, work-orders, issues, invoices,
notifications, analytics). Pragmatic mapping — NOT 1:1 for Track G's
123 subcommands. Zero migration — Phase 160-173 shipped all the
repos. All routes require `require_tier("shop")` + shop membership
check via Phase 172 RBAC.
