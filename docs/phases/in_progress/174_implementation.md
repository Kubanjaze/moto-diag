# MotoDiag Phase 174 — Gate 8: Intake-to-Invoice Integration Test

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Close Track G (phases 160-173) with an **end-to-end integration test
that exercises every shop CLI subgroup against a single WO lifecycle**
— from bike arrival through paid invoice. This phase ships no new
code, no new schema, no CLI additions — only tests + documentation
that verify the 16-subgroup / 123-subcommand Track G surface holds
together as a coherent mechanic workflow.

The gate test walks through:

1. **Shop profile** → register shop + set hours
2. **Membership** → add owner + tech (Phase 172)
3. **Customer** → add + link bike (Phase 113/160)
4. **Intake** → log arrival (Phase 160)
5. **Work order** → create WO from intake (Phase 161)
6. **Issue logging** → record a critical brakes issue (Phase 162)
7. **Priority scoring** → simulate AI scoring without API call (Phase 163 `_default_scorer_fn` seam)
8. **Triage queue** → build + next WO (Phase 164)
9. **Parts needs** → add parts + build requisition (Phase 165)
10. **Sourcing** → recommendation (simulated via seam — Phase 166)
11. **Labor estimate** → simulate AI labor (Phase 167 seam)
12. **Bay scheduling** → add bay + schedule slot (Phase 168)
13. **Work start** → start_work + start_slot (Phase 161 + 168)
14. **Reassignment** → reassign WO mid-repair (Phase 172)
15. **Notification trigger** → wo_in_progress (Phase 170)
16. **Completion** → complete WO + slot + mark parts installed (Phase 161 + 168 + 165)
17. **Invoice** → generate invoice from WO (Phase 169)
18. **Revenue rollup** → confirm revenue visible (Phase 169)
19. **Mark paid** → close invoice (Phase 169)
20. **Analytics** → dashboard snapshot includes this WO (Phase 171)
21. **Automation rule** → rule fires on wo_completed, triggers follow-up notification (Phase 173)
22. **Notification queue** → verify both notifications persisted (Phase 170)
23. **Rule firing history** → audit trail confirms rule ran (Phase 173)

The test runs **entirely via CLI invocations** — no direct repo calls
— so it validates the actual user-facing contract. Where phases have
AI seams (Phase 163/166/167), we inject deterministic `_default_scorer_fn`
stubs so the gate remains zero-token.

CLI — **no new subcommands**; this phase is pure integration coverage.

**Design rule:** zero AI (injection seams supply fake AI responses),
zero migrations, zero new modules. Only additions: the gate test file
+ doc entry + track-closure summary.

Outputs:
- `tests/test_phase174_gate8.py` (~500 LoC, 4-6 tests) —
  `TestEndToEndHappyPath` (one big-bang) + `TestShopScopedIsolation`
  (two shops don't see each other's WOs/invoices/analytics) +
  `TestRuleFiresAcrossLifecycle` (same rule wired to different
  events).
- `docs/phases/completed/TRACK_G_SUMMARY.md` (~300 LoC, NEW) —
  closure document capturing Track G's 14-phase build: design pillars,
  composition patterns, file/LoC inventory, the canonical `motodiag
  shop *` surface.
- No code changes.
- No migration / SCHEMA_VERSION bump (remains 36).

## Logic

### Integration test structure

```python
class TestEndToEndHappyPath:
    """Single WO from intake through paid invoice — exercises every
    Track G subgroup via CLI invocation."""

    def test_full_lifecycle(self, cli_db):
        runner = CliRunner()
        root = _make_cli()

        # 1. shop profile init
        r = runner.invoke(root, ["shop", "profile", "init",
                                 "--name", "Bob's Moto",
                                 "--state", "CA", "--phone", "555-0100"])
        assert r.exit_code == 0

        # 2. member add (owner)
        owner_id = _add_user(cli_db, username="bob")
        runner.invoke(root, ["shop", "member", "add",
                             "--shop", "Bob's Moto",
                             "--user", str(owner_id),
                             "--role", "owner"])
        tech_id = _add_user(cli_db, username="alice")
        runner.invoke(root, ["shop", "member", "add",
                             "--shop", "Bob's Moto",
                             "--user", str(tech_id),
                             "--role", "tech"])

        # 3. customer add + link bike
        # 4. intake create
        # 5. work-order create (from intake)
        # 6. issue add --severity critical --category brakes
        # 7. priority score (injection seam)
        # 8. triage queue → WO appears
        # 9. parts-needs add + mark-ordered + mark-received
        # 10. sourcing recommend (injection seam)
        # 11. labor estimate (injection seam)
        # 12. bay add + schedule
        # 13. work-order start + bay start
        # 14. work-order reassign (owner → tech)
        # 15. notify trigger wo_in_progress
        # 16. work-order complete + bay complete + parts installed
        # 17. invoice generate
        # 18. revenue rollup
        # 19. invoice mark-paid
        # 20. analytics snapshot
        # 21. rule add (wo_completed → trigger_notification)
        # 22. manually fire trigger_rules_for_event OR verify
        #     the rule can be matched (integration test doesn't
        #     assume automatic rule firing on CLI status transitions —
        #     Phase 173 doesn't wire hooks into CLI path yet)
        # 23. notify list + rule history
```

### AI injection seams

Phase 163 priority scorer exposes `_default_scorer_fn` kwarg. Tests
inject:

```python
from motodiag.shop.priority_scorer import score_work_order
def _stub_priority(*args, **kwargs):
    return PriorityScoreResponse(
        priority=1, confidence=0.9,
        rationale="fake stub for gate 8 test",
        safety_risk=True,
    ), TokenUsage(...), None  # (response, usage, cache_hit)

score_work_order(wo_id, _default_scorer_fn=_stub_priority, db_path=cli_db)
```

Similarly for Phase 166 sourcing and Phase 167 labor.

Note: tests invoke the SHOP CLI surface, but the priority score /
sourcing / labor commands each accept `--no-ai` or stub through the
same seams — when CLI-invoked, they use the injection mechanism that
the CLI wraps. If the CLI path doesn't expose the seam, the gate test
calls the repo function directly for those three steps only, and
verifies CLI surface separately via the per-phase tests (already
GREEN).

### Shop-isolation test

```python
class TestShopScopedIsolation:
    """Two shops with overlapping names/customers/vehicles don't
    cross-pollinate analytics / notifications / assignments."""

    def test_two_shops_stay_isolated(self, cli_db):
        # Create shop A + WO A + invoice A
        # Create shop B + WO B + invoice B
        # analytics snapshot shop A → only WO A in counts
        # notify list shop A → only customer A
        # member add tech to A → tech can't be reassigned to B's WO
```

### Rule-firing-across-lifecycle test

```python
class TestRuleFiresAcrossLifecycle:
    """One rule on wo_completed + one rule on invoice_issued
    both fire when their events are triggered."""

    def test_event_triggered_rules(self, cli_db):
        # Set up full shop with WO + invoice
        # Create rule A: event=wo_completed, action=trigger_notification(wo_completed)
        # Create rule B: event=invoice_issued, action=trigger_notification(invoice_issued)
        # Manually call trigger_rules_for_event('wo_completed', wo_id)
        # Assert notification queue has wo_completed row
        # Call trigger_rules_for_event('invoice_issued', wo_id)
        # Assert second notification row exists
        # Check workflow_rule_runs has 2 matched rows
```

### `TRACK_G_SUMMARY.md`

Captures:
- 14-phase inventory (161-173 including 162.5)
- Design pillars: write-back-through-whitelist, anti-regression grep
  tests, canonical AI composition pattern (Phase 162.5 ShopAIClient),
  fail-one-continue-rest, rules-are-data / engine-is-code,
  compose-don't-duplicate
- DB schema: 14 Track G tables + 12 migrations
- File + LoC inventory: ~5500 LoC in cli/shop.py, ~4700 LoC across
  shop/* modules, ~500 LoC tests per phase
- The `motodiag shop *` surface: 16 subgroups, 123 subcommands,
  end-to-end mechanic workflow

## Key Concepts

- **No new code, all integration coverage.** This phase's purpose is
  to verify prior phases compose correctly; adding new code would
  defeat that purpose. Every line added here is test or doc.
- **CLI-invoked, not repo-invoked.** The gate test uses
  `CliRunner().invoke()` for every step — no direct Python calls
  except for (a) test fixture setup, (b) injection of AI seams
  that aren't exposed through the CLI yet.
- **AI seams are stubs.** Phase 163/166/167 AI calls use their
  `_default_scorer_fn` injection seam to supply deterministic
  responses. The gate test must pass zero-token; any accidental
  network call would make the test non-hermetic.
- **Track closure doc ships alongside**. `TRACK_G_SUMMARY.md` is the
  artifact external collaborators read to understand "what did the
  mechanic's shop console turn out to be". Condensed, opinionated,
  with a call-to-action for what Track H should build on top.

## Verification Checklist

- [ ] `test_full_lifecycle` walks all 23 steps successfully via CLI.
- [ ] Zero AI calls (injection seams stub all AI phases).
- [ ] `test_two_shops_stay_isolated` confirms cross-shop isolation.
- [ ] `test_event_triggered_rules` confirms rule firing + audit trail.
- [ ] Phase 113/118/131/153/160-173 tests still GREEN.
- [ ] `TRACK_G_SUMMARY.md` shipped in `docs/phases/completed/`.
- [ ] Project version 0.10.5 → 0.11.0 (major Track closure bump).

## Risks

- **CLI path for AI phases may not expose seam.** Priority/sourcing/
  labor CLI subcommands accept `--skill-tier` etc but might
  unconditionally hit the AI. Mitigation: if the CLI path forces an
  API call, the gate test calls the repo function directly for those
  three steps (Phase 163/166/167 per-phase tests already prove the
  CLI path works in isolation). Document this in Deviations if so.
- **Timestamp ordering in a fast CI run.** Two actions in the same
  second may collide (Phase 171 already saw this). Mitigation: tests
  use monotonic `id` ordering where relevant, not `created_at`.
- **Phase 173 rule firing is manual in CLI.** CLI status transitions
  (work-order complete, etc.) do NOT currently call
  `trigger_rules_for_event` automatically — that's Phase 175+ scope.
  The gate test calls `trigger_rules_for_event` manually. Document
  this as a Track G known-limitation in the summary doc.
- **Regression runtime grows.** Gate test adds ~4-6 multi-step CLI
  invocations, each building a fresh DB. Expected impact: ~10-20s on
  targeted regression runtime (already 6m 53s → ~7m 15s).
