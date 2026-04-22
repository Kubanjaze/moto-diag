# MotoDiag Phase 173 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
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

### 2026-04-22 — Build complete

Files shipped (total ~900 LoC across 3 modules):

1. **Migration 036** (schema v35→v36): `workflow_rules` (id, shop_id,
   name, description, event_trigger CHECK, conditions_json,
   actions_json, priority, is_active, created_by_user_id +
   UNIQUE(shop_id, name) + FK shop CASCADE + FK user SET NULL) +
   `workflow_rule_runs` (id, rule_id, work_order_id, triggered_event,
   matched 0/1, actions_log JSON, error, actor_user_id, fired_at + FK
   rule CASCADE + FK wo SET NULL + FK actor SET NULL) + 3 indexes
   (rules shop+active+event; runs rule+fired_at DESC; runs wo+fired_at
   DESC).

2. **`shop/workflow_conditions.py`** (~195 LoC): 12 condition type
   evaluators in `_REGISTRY` dict (always, priority_gte/lte/eq,
   status_eq/in, severity_eq/in, category_in, parts_cost_gt_cents,
   invoice_total_gt_cents, has_unresolved_issue) + `validate_condition`
   (shape-check) + `evaluate_conditions` (AND-compose, empty list →
   True).

3. **`shop/workflow_actions.py`** (~229 LoC): 8 action executors
   (set_priority, flag_urgent, skip_triage, reassign_to_user, unassign,
   trigger_notification, add_issue_note, change_status). **Every
   executor routes through the canonical Track G repo for mutation** —
   set_priority → Phase 161 update_work_order, flag_urgent / skip_triage
   → Phase 164 triage_queue, reassign_to_user / unassign → Phase 172
   rbac.reassign_work_order, trigger_notification → Phase 170
   notifications.trigger_notification, add_issue_note → Phase 162
   update_issue, change_status → Phase 161 lifecycle transition
   functions (start_work / pause_work / complete_work_order /
   cancel_work_order / reopen_work_order). Anti-regression grep test
   enforces no raw `UPDATE work_orders` SQL.

4. **`shop/workflow_rules.py`** (~470 LoC):
   - 4 Pydantic models: `WorkflowRule`, `WorkflowRuleRun`,
     `RuleRunResult`
   - 3 exceptions: `InvalidEventError`, `RuleNotFoundError`,
     `DuplicateRuleNameError`
   - `build_wo_context(wo_id)` assembles the one-time context dict
     (wo + issues + parts + invoice + shop) — condition evaluators
     read from it, no N+1 queries
   - CRUD: `create_rule`, `get_rule`, `require_rule`, `list_rules`,
     `update_rule` (with `_UPDATABLE_FIELDS` whitelist), `enable_rule`,
     `disable_rule`, `delete_rule`
   - Engine: `evaluate_rule`, `fire_rule_for_wo` (writes run row
     whether matched or not; fail-one-continue-rest on action errors),
     `trigger_rules_for_event` (fires active rules for shop+event in
     priority order; rejects `event='manual'` with remediation hint),
     `list_rule_runs`

5. **`shop/__init__.py`** +38 re-exports.

6. **`cli/shop.py`** +335 LoC — `rule` subgroup with **10 subcommands**
   (`add`, `list`, `show`, `update`, `enable`, `disable`, `delete`,
   `fire`, `test`, `history`) + `_parse_json_opt` helper. Total
   `cli/shop.py` now ~5500 LoC across **16 subgroups and 123
   subcommands**.

7. **`tests/test_phase173_rules.py`** (42 tests across 7 classes):
   TestMigration036×4 + TestConditions×12 + TestActions×8 +
   TestRuleCRUD×6 + TestFiring×6 + TestRuleCLI×5 + TestAntiRegression×1.

**Bug fixes during build:**
- **Bug fix #1: issue category CHECK constraint violations.** First
  pass of condition tests used `'safety'` as an issue category; Phase
  162's CHECK restricts to a 13-category whitelist (`brakes`,
  `electrical`, etc). Switched all fixtures to `'brakes'` via replace-
  all. Tests exercise the same condition logic.
- **Bug fix #2: mock-patch target**. First draft mocked
  `motodiag.shop.workflow_actions._a_set_priority` but the
  `_REGISTRY` dict holds direct function references, so patching the
  module attribute doesn't intercept registry calls. Fixed by using
  `patch.object(work_order_repo, "update_work_order")` — catches the
  actual discipline under test.

Single-pass-after-fix: **42 GREEN in 29.93s.**

**Targeted regression: 648 GREEN in 413.15s (6m 53s)** covering Phase
113 + 118 + 131 + 153 + Track G 160-173 + 162.5. Zero regressions.

Build deviations vs plan:
- Renamed action `add_issue_tag` → `add_issue_note` (Phase 162 has no
  tags column; action appends to `description` via whitelist).
- Mock-patch audit approach changed (see Bug fix #2).
- 42 tests vs ~34 planned (+8 for fail-one semantics, manual-event
  rejection, CLI dry-run verification).

### 2026-04-22 — Documentation finalization

`implementation.md` promoted to v1.1. All `[x]` in Verification
Checklist. Deviations + Results sections appended. Key finding
captures "rules are data, engine is code" — operators can author new
rules without a code change; adding a new condition or action type is
a 5-line registry + validator change.

Project-level updates:
- `implementation.md` schema_version footnote v35 → v36
- `implementation.md` Database Tables: append `workflow_rules` +
  `workflow_rule_runs`
- `implementation.md` Phase History: append Phase 173 row
- `implementation.md` Shop CLI Commands: 113 → 123 subcommands; added
  `motodiag shop rule` row (16th subgroup)
- `phase_log.md` project-level: Phase 173 closure entry
- `docs/ROADMAP.md`: Phase 173 row → ✅
- Project version 0.10.4 → **0.10.5** (Track G automation layer closed)

**Key finding:** Phase 173 closes Track G's automation pillar. The
engine composes every prior Track G primitive (Phase 161 lifecycle +
Phase 162 issues + Phase 163 priority + Phase 164 triage + Phase 165
parts + Phase 170 notifications + Phase 172 RBAC) **without touching
any of them** — action executors are thin wrappers that call existing
whitelists. Operators author rules as JSON: condition list +
action list = the entire rule body. The dispatcher + registry pattern
keeps the engine a thin spine; adding a 13th condition type or 9th
action type is a 5-line change. Phase 174 Gate 8 can now run an
end-to-end intake → triage → WO → parts → labor → bay → completion
→ invoice → revenue → notification chain with automation rules
firing between each phase without any new code — just JSON rules
in the DB.
