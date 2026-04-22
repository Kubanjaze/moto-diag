# MotoDiag Phase 173 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session. Scope: if-this-then-that rule engine
composing all prior Track G primitives. Conditions read WO + issues +
parts + invoice + shop state; actions fire Phase 161 lifecycle + Phase
163 priority + Phase 164 triage + Phase 170 notifications + Phase 172
reassignments. **Zero AI, zero tokens** — rules are JSON data, engine
is pure Python + SQL.

Key design decisions:
- Rules are data (JSON in DB columns); engine is a fixed dispatcher
  over condition + action registries. Operators author new rules
  without code changes.
- 12 condition types × 8 action types = enough coverage for the
  rulebook mechanics will actually write.
- `build_wo_context(wo_id)` fetches everything once; condition
  evaluators read from the same dict (no N+1 queries).
- Audit every firing, matched or not. `matched=0` rows feed Phase 171
  analytics ("rules that never match" = deletion candidates).
- **Fail-one, continue-rest** action semantics: action raises → error
  logged, sibling actions continue. Strict rollback would require
  nested savepoints; not worth the complexity on a local-first CLI.
- No raw SQL in `workflow_actions.py` — every mutation routes through
  the appropriate Phase 161/162/163/164/170/172 repo. Anti-regression
  grep test enforces.
- Manual-trigger rules (`event_trigger='manual'`) never fire on
  events; only via CLI `rule fire`.

Migration 036 adds `workflow_rules` + `workflow_rule_runs` tables + 4
indexes. Rollback drops cleanly.
