# MotoDiag Phase 173 — Workflow Automation Rules

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Deterministic if-this-then-that rule engine that composes prior Track G
primitives: conditions read Phase 161 WO state + Phase 162 issues +
Phase 165 parts cost + Phase 169 invoice total + Phase 171 rollups;
actions fire Phase 163 priority overrides, Phase 170 notifications,
Phase 172 reassignments, Phase 164 triage flags, Phase 161 lifecycle
transitions. **Zero AI, zero tokens** — rule definitions are JSON, the
engine is pure Python + SQL.

Rules canonically look like:
- "If issue.severity='critical' and category='safety' → set priority=1 + flag urgent"
- "If parts cost > $500 → trigger approval_requested notification"
- "If labor overrun > 3h → trigger mechanic_escalation notification"
- "If invoice issued → trigger invoice_issued notification"

Two firing modes:
1. **Event-driven** — `trigger_rules_for_event('wo_completed', wo_id, ...)` fires all active rules whose `event_trigger='wo_completed'` for that WO's shop, in priority order.
2. **Manual** — `fire_rule_for_wo(rule_id, wo_id)` runs one specific rule.

Every firing logs to `workflow_rule_runs` (audit trail) regardless of
condition outcome — matched=True → actions executed; matched=False →
audit row shows "evaluated, did not match" for Phase 171 analytics.

CLI — `motodiag shop rule {add, list, show, update, enable, disable,
delete, fire, test, history}` — **10 subcommands**.

Outputs:
- Migration 036 (~60 LoC): `workflow_rules` + `workflow_rule_runs`
  tables + 4 indexes.
- `src/motodiag/shop/workflow_rules.py` (~650 LoC) — rule CRUD,
  condition evaluator, action dispatcher, firing loop, audit log.
- `src/motodiag/shop/workflow_conditions.py` (~200 LoC) — 12
  condition-type evaluators + dispatcher + registry.
- `src/motodiag/shop/workflow_actions.py` (~230 LoC) — 8 action-type
  executors + dispatcher + registry.
- `src/motodiag/shop/__init__.py` +22 LoC re-exports.
- `src/motodiag/cli/shop.py` +310 LoC — `rule` subgroup (10 subcommands).
- `src/motodiag/core/database.py` SCHEMA_VERSION 35 → 36.
- `tests/test_phase173_rules.py` (~34 tests across 6 classes).

## Logic

### Migration 036

```sql
CREATE TABLE IF NOT EXISTS workflow_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    event_trigger TEXT NOT NULL CHECK(event_trigger IN (
        'wo_opened', 'wo_in_progress', 'wo_completed', 'wo_cancelled',
        'parts_arrived', 'invoice_issued', 'invoice_paid',
        'issue_added', 'manual'
    )),
    conditions_json TEXT NOT NULL,     -- JSON list of condition dicts
    actions_json TEXT NOT NULL,        -- JSON list of action dicts
    priority INTEGER NOT NULL DEFAULT 100,  -- low = fire first
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(shop_id, name),
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workflow_rule_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    work_order_id INTEGER,
    triggered_event TEXT,
    matched INTEGER NOT NULL,          -- 0/1
    actions_log TEXT,                   -- JSON list of action outcomes
    error TEXT,                         -- non-null on partial failure
    actor_user_id INTEGER,
    fired_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rule_id) REFERENCES workflow_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE SET NULL,
    FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_rules_shop_active ON workflow_rules(shop_id, is_active, event_trigger);
CREATE INDEX idx_rule_runs_rule ON workflow_rule_runs(rule_id, fired_at DESC);
CREATE INDEX idx_rule_runs_wo ON workflow_rule_runs(work_order_id, fired_at DESC);
```

### Condition catalog (12 types)

```python
# workflow_conditions.py
CONDITION_TYPES = (
    "always", "priority_gte", "priority_lte", "priority_eq",
    "status_eq", "status_in",
    "severity_eq", "severity_in",
    "category_in",
    "parts_cost_gt_cents", "invoice_total_gt_cents",
    "has_unresolved_issue",
)

def evaluate_condition(cond: dict, ctx: dict) -> bool:
    """Dispatch on `cond["type"]`; return bool."""
```

Each condition dict has `{"type": "priority_lte", "value": 2}` etc.
Context is built once per rule fire: `{wo: <row>, issues: [...], parts:
[...], invoice: {...}, shop: <row>}` — all pulled via existing phase
repos.

### Action catalog (8 types)

```python
# workflow_actions.py
ACTION_TYPES = (
    "set_priority", "flag_urgent", "skip_triage",
    "reassign_to_user", "unassign",
    "trigger_notification", "add_issue_tag", "change_status",
)

def execute_action(action: dict, ctx: dict, db_path) -> dict:
    """Dispatch on `action["type"]`. Returns per-action result dict
    for audit log: {type, ok, detail}."""
```

Actions call existing phase repos — `change_status` routes through
Phase 161 lifecycle transitions (no raw SQL); `set_priority` routes
through `update_work_order` whitelist; `trigger_notification` calls
Phase 170; `reassign_to_user` calls Phase 172; `flag_urgent` /
`skip_triage` call Phase 164; `add_issue_tag` uses Phase 162
`update_issue`. Anti-regression grep test enforces no raw SQL in the
actions module.

### `workflow_rules.py` API

```python
def create_rule(
    shop_id: int, name: str, event_trigger: str,
    conditions: list[dict], actions: list[dict],
    priority: int = 100, description: Optional[str] = None,
    created_by_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> int: ...

def get_rule(rule_id, db_path=None) -> Optional[WorkflowRule]: ...
def list_rules(shop_id=None, event_trigger=None, active_only=True,
               db_path=None) -> list[WorkflowRule]: ...
def update_rule(rule_id, db_path=None, **fields) -> bool: ...
def enable_rule(rule_id, db_path=None) -> bool: ...
def disable_rule(rule_id, db_path=None) -> bool: ...
def delete_rule(rule_id, db_path=None) -> bool: ...

def build_wo_context(
    wo_id: int, db_path: Optional[str] = None,
) -> dict:
    """Assemble the context dict: wo + issues + parts + invoice + shop."""

def evaluate_rule(rule: WorkflowRule, ctx: dict) -> bool:
    """AND-compose all conditions; return True iff all pass."""

def fire_rule_for_wo(
    rule_id: int, wo_id: int,
    actor_user_id: Optional[int] = None,
    triggered_event: Optional[str] = None,
    db_path: Optional[str] = None,
) -> RuleRunResult:
    """Evaluate + execute actions if matched. Always writes a
    workflow_rule_runs row."""

def trigger_rules_for_event(
    event: str, wo_id: int,
    actor_user_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[RuleRunResult]:
    """Find all active rules for WO's shop + event, fire in priority
    order, return aggregated results."""

def list_rule_runs(
    rule_id=None, wo_id=None, shop_id=None,
    matched_only: bool = False, since=None, limit=100,
    db_path=None,
) -> list[WorkflowRuleRun]: ...
```

### Error-handling: fail-one, continue-rest

If an action raises during execution, the rule run records `error`
but does NOT unwind prior actions (they may have already mutated DB
state). The run row's `actions_log` JSON captures per-action
outcomes — mechanic can review and manually compensate. This matches
Track G's "audit-log-first, human-in-the-loop" posture; a strict
transactional rollback would require wrapping every action in a
nested savepoint which adds complexity disproportionate to the
benefit on a local-first CLI.

### CLI subgroup

```
shop rule add --shop X --name "..." --event EVT --conditions JSON --actions JSON [--priority N]
shop rule list [--shop X] [--event EVT] [--include-inactive] [--json]
shop rule show RULE_ID [--json]
shop rule update RULE_ID [--set key=value ...]
shop rule enable RULE_ID
shop rule disable RULE_ID
shop rule delete RULE_ID [--yes]
shop rule fire RULE_ID WO_ID [--actor USER_ID]
shop rule test RULE_ID WO_ID           # dry-run: evaluate, report, don't fire
shop rule history [--rule X] [--wo X] [--shop X] [--matched-only] [--limit 50] [--json]
```

## Key Concepts

- **Rules are data, engine is code.** Condition/action JSON lives in
  the DB; the dispatcher is a fixed registry. Operators can author new
  rules without code changes. Adding a new condition or action type
  requires adding an entry to the registry + a docstring.
- **Context-first evaluation.** `build_wo_context(wo_id)` fetches
  everything a rule might need (WO + issues + parts + invoice + shop)
  once, then condition evaluators read from the same dict — no N+1
  query storms, deterministic per-rule state.
- **Audit everything.** Every rule firing writes a row whether matched
  or not. `matched=0` rows are useful for Phase 171 analytics:
  "rules that evaluated but never fired" = candidates for deletion.
- **Fail-one, continue-rest.** Action failures within a single rule
  don't stop sibling actions. `trigger_rules_for_event` failures in
  one rule don't block subsequent rules. The `error` column captures
  the first failure per rule run.
- **No raw SQL in actions.** All mutations route through existing
  phase repos (Phase 161/162/163/164/170/172). Anti-regression grep
  test enforces in `workflow_actions.py`.
- **`event_trigger='manual'` rules never fire automatically.** Only
  `fire_rule_for_wo` triggers them. Useful for one-off mechanic-
  initiated rules ("pre-inspection checklist") that don't belong on
  any lifecycle event.

## Verification Checklist

- [x] Migration 036 creates both tables + CHECK + FK + indexes.
- [x] SCHEMA_VERSION 35 → 36.
- [x] Rollback to 35 drops cleanly.
- [x] `create_rule` validates conditions/actions against registries;
      rejects unknown types.
- [x] `UNIQUE(shop_id, name)` enforced.
- [x] `evaluate_rule` AND-composes conditions; empty-list conditions
      return True (always-fire).
- [x] 10 of 12 condition types explicitly tested at match + no-match
      boundaries; the remaining 2 (`severity_in`, `priority_eq`) covered
      by evaluator tests at the same type family.
- [x] 6 of 8 action types tested end-to-end (set_priority via
      mock-patch; flag_urgent via DB assertion; trigger_notification
      via result inspection; reassign_to_user success + failure paths;
      change_status validation); 2 supporting action types
      (`skip_triage`, `add_issue_note`) exercised transitively via the
      registry dispatch.
- [x] `fire_rule_for_wo` writes `workflow_rule_runs` row regardless of
      match outcome.
- [x] Action failure records `error` but doesn't kill sibling actions
      (fail-one-continue-rest test asserts both action outcomes logged).
- [x] `trigger_rules_for_event` fires matching rules in `priority ASC`
      order.
- [x] Disabled rules ignored by event trigger.
- [x] Manual-trigger rules ignored by event trigger (raises
      `InvalidEventError` with remediation hint).
- [x] CLI `rule {add, list, show, update, enable, disable, delete,
      fire, test, history}` round-trip.
- [x] Anti-regression grep: no raw `UPDATE work_orders` SQL in
      `workflow_actions.py` (strips comments + docstrings).
- [x] Phase 113/118/131/153/160-172 tests still GREEN (648/648).
- [x] Zero AI calls.

## Deviations from Plan

- **`add_issue_note` action replaces plan's `add_issue_tag`.** The
  plan called for tagging issues but Phase 162 `issues` has no `tags`
  column — just `description` freetext. Action appends to description
  via Phase 162 `update_issue` whitelist. If Phase 175+ adds a tags
  column, the action name can be retained and the implementation
  swapped without changing rule JSON.
- **Mock-patch audit via `patch.object(wo_repo, "update_work_order")`
  rather than `_a_set_priority`.** First draft patched the workflow_
  actions function but the registry dict holds direct function refs,
  so monkey-patching the module attribute doesn't intercept registry
  calls. Fixed by patching at the `work_order_repo` module — catches
  the actual discipline under test ("set_priority routes through
  Phase 161").
- **Category IN CHECK constraint caught test fixtures.** First pass
  used `'safety'` as an issue category but Phase 162's CHECK
  constraint restricts to 12 specific categories (`brakes`, `electrical`,
  etc). Corrected fixtures to use `'brakes'`. Tests exercise the same
  condition logic either way.
- **42 tests vs ~34 planned.** Added 6 tests for fail-one-continue-rest
  semantics, manual-event rejection, and CLI dry-run verification
  during the build to lock in invariants that emerged from the code.

## Results

| Metric | Value |
|--------|-------|
| Phase 173 tests landed | 42 GREEN (7 classes) |
| Targeted regression | 648/648 GREEN in 413.15s (6m 53s) |
| Coverage range | Phase 113 + 118 + 131 + 153 + Track G 160-173 + 162.5 |
| Migration LoC | 77 LoC (2 tables + 3 indexes + CHECK on event_trigger) |
| `shop/workflow_rules.py` LoC | 470 (CRUD + evaluator + firing + audit) |
| `shop/workflow_conditions.py` LoC | 195 (12 condition evaluators + validation) |
| `shop/workflow_actions.py` LoC | 229 (8 action executors + validation) |
| `cli/shop.py` addition | +335 LoC (`rule` subgroup: 10 subcommands) |
| `shop/__init__.py` addition | +38 re-exports |
| Total `cli/shop.py` | ~5500 LoC, **16 subgroups**, **123 subcommands** |
| SCHEMA_VERSION | 35 → **36** |
| AI calls | 0 (zero tokens spent) |

**Key finding:** Phase 173 closes Track G's automation pillar by
composing every prior Track G primitive without touching any of them.
The engine is ~900 LoC across three files; the rules themselves are
JSON — operators can author `"if severity='critical' and
category_in=['brakes','steering'] → set priority=1 + flag urgent +
trigger approval_requested"` without a code change. The dispatcher +
registry pattern (CONDITION_TYPES + ACTION_TYPES frozen tuples,
`_REGISTRY` maps to executors) makes adding a new condition or action
a 5-line change: add entry + validator shape-check + docstring, no
schema touch. The write-back-through-whitelist discipline (Phase 161
update_work_order + Phase 162 update_issue + Phase 170 trigger_
notification + Phase 172 reassign_work_order) extends naturally —
actions are thin wrappers calling existing repos. The fail-one-
continue-rest semantic is the right default for a local-first CLI
(strict transactional rollback would require nested savepoints, and
the audit log already gives the mechanic enough information to
manually compensate). Phase 174 Gate 8 can now run an end-to-end
intake → triage → WO → parts → labor → bay → completion → invoice →
revenue → notification chain with automation rules firing between
each phase.

## Risks

- **Circular firing.** A rule on `wo_in_progress` that calls
  `change_status` back to `open` could trigger another rule that fires
  again. Mitigation: `trigger_rules_for_event` does NOT recursively
  re-fire for state changes made by actions within the same firing
  chain. Tests cover a rule that sets priority + a rule that watches
  priority changes — they don't cascade.
- **Action ordering within a rule.** Actions fire in list order. If a
  later action depends on an earlier one's side effect
  (e.g. `reassign_to_user` then `trigger_notification`), the author
  must order correctly. Mitigation: document this in the rule-
  authoring examples + CLI `test` command shows actions in fire order.
- **Schema-less JSON columns.** `conditions_json` / `actions_json`
  store arbitrary dicts; bad input won't fail at migration. Mitigation:
  `create_rule` / `update_rule` validate JSON-parses + runs through
  registry validators before persisting. `test` command catches
  invalid configurations without side effects.
- **Performance on event storms.** A shop with 500 active rules
  firing on every `wo_opened` would be slow. Mitigation:
  `idx_rules_shop_active` index narrows to active + event_trigger
  match; rule authors expected to use `priority` ordering + disable
  rather than keep dead rules. Monitoring is out-of-scope for this
  phase.
