# Phase 244Y — Dead code leaves with its evidence

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Four phases sharpened the reachability gate — 209B, 244U, 244W, 244X — until
it could say, by itself and in both directions, which modules and names no
live code uses. This phase acts on the part of that report the allowlist's own
vocabulary already calls a removal candidate: **`superseded` — replaced by a
live implementation elsewhere.** Plus the two engine modules the 2026-09-17
audit named for deletion with three verifiers each and no dissent.

Nothing here is deleted because an agent said so. Every removal has a table
entry that names its live replacement, a measured line count printed below
before anything is touched, and a stale-entry test that will fail the moment
it is gone — which is the gate proving it was tracking the right thing.

## Step 0 — findings

Gathered read-only while 244X's regression ran; every number measured on
this tree.

**S0-1. The candidates, from the tables.** Every `superseded` entry across
`UNREACHABLE_MODULES`, `MODULE_ISLANDS` and `ORPHANS`, plus `engine/cost` and
`engine/evaluation` (audit consensus 2.0/10, "nothing here to preserve").
Excluded on inspection: the `knowledge.seed*` entries, which are a data-loader
package, not files.

**S0-2. Before-state.** The operator's rule for destructive changes, applied
to source: what exists, printed before it goes.

```
  WHOLE MODULES (7 files, 1,604 lines)          live replacement
   367  engine/history.py                       core/session_repo over diagnostic_sessions
   308  engine/cost.py                          shop/invoicing.py (integer cents; refuses to guess a rate)
   301  engine/retrieval.py                     reads ONLY history.py; goes with it
   196  engine/evaluation.py                    its data source has 0 rows and no writer
   180  hardware/protocols/models.py            ProtocolAdapter's plain return types (base.py:101-143)
   134  auth/roles_repo.py                      shop/rbac.py:303 walks the same tables with its own SQL
   118  cli/registry.py                         cli/main.py registers with direct register_*(cli) calls

  DEFS INSIDE LIVE FILES (10 defs, 242 lines)
    87  engine/symptoms.py::SymptomAnalyzer     DiagnosticClient.diagnose() via cli/diagnose.py
    22  engine/symptoms.py::assess_urgency      its only caller is SymptomAnalyzer (symptoms.py:242)
    39  cli/subscription.py::requires_tier      API-side tier enforcement (its refs are its own docstring)
     4  cli/subscription.py::has_feature        same
    14  inventory/recall_repo.py::add_recall    advanced/recall_repo (Phase 155) — see S0-4
     7  inventory/recall_repo.py::get_recall    same
    12  inventory/recall_repo.py::list_recalls  same
     6  inventory/recall_repo.py::delete_recall same
    22  accounting/invoice_repo.py::recalculate_invoice_totals   shop/invoicing.py computes its own
    29  shop/extracted_symptom_repo.py::create_extracted_symptom  (allowlist: superseded since 244U)

  1,846 source lines. No schema change: every table these touched stays.
```

**S0-3. Three gate tests depend on candidates.** `test_phase95_gate3_integration.py`
imports every audit-named module by name and has six tests on them
(`test_cost_module`, `test_history_module`, `test_retrieval_module`,
`test_evaluation_module`, `test_cost_estimation_pipeline`,
`test_evaluation_pipeline`); `test_phase133_gate_5.py:719` imports
`cli.registry` under a `noqa`; `test_phase121_gate_r.py` exercises the recall
repo and `recalculate_invoice_totals`. Gate 3's definition — "Track C modules
importable and functional" — was written when these modules were the track.
The gate's *meaning*, that Track C's engine works end to end, is carried by
its other 33 tests; the six that assert a dead module is importable are
removed with a docstring saying so, and this plan says so here, because a
gate test being edited is the kind of thing an operator should hear before
rather than after.

**S0-4. The recall repo is delegated to, not duplicated.** 244X's Step 0
called `inventory/recall_repo` a Phase 118 duplicate of Phase 155's; this
Step 0 found `advanced/recall_repo.py:301` lazily importing its
`list_recalls_for_vehicle`. The four orphaned functions go; the file stays
with the one the live repo needs. 244X's entries were corrected before commit.

**S0-5. `engine/symptoms.py` stays.** `categorize_symptoms` is live
(`media/transcript_extraction.py`). Only the class and the helper it alone
calls come out.

**S0-6. Two wrappers stay, and are reclassified.** `memory/compile.py::
compile_vehicle` and `compile_all` are one-line wrappers over the `_detailed`
forms 209C wired — and 45 tests in `test_phase244M_client_memory.py` call
`compile_vehicle`. Deleting a one-line wrapper to force 45 test rewrites is
the wrong trade. They move from `superseded` to `public-api` with that reason.

**S0-7. The test estate.** Fifteen test files name a candidate (6,676 lines,
530 tests, 201 of them naming one). Four go whole with their module —
`test_phase86_cost` (34 tests), `test_phase88_history` (45),
`test_phase89_retrieval` (32), `test_phase94_evaluation` (21) — about 1,393
lines. The rest are trimmed: `test_phase134_protocol_base` (19 of 30 name the
models, but the file also tests `base.py`), `test_phase109_cli_foundation`
(23 of 41: registry and the tier helpers), `test_phase112_auth_layer` (14 of
40: roles), `test_phase80_symptom_analysis` (5 of 28), `test_phase118`,
`test_phase195`, and the three gates. Two of this series' own tests change:
244W's `test_history_and_retrieval_are_reported` cannot assert on modules
that no longer exist and is removed (the synthetic-tree tests carry the
mechanism); 244X's named-entry list loses `add_recall` and its
duplicate-repo classification test goes with the entries.

**S0-8. Allowlist and pins.** `ORPHANS` 104 → 95 (−9), `MODULE_ISLANDS`
19 → 13 (−6), `UNREACHABLE_MODULES` 38 → 37 (−1). Running-count pins in 209B,
244U, 244W and 244X move with their history. The stale-entry tests are what
force this: nothing can be deleted and left on a list.

**S0-9. Roadmap rows 86, 88, 89, 94, 109, 112 and 134 are ✅.** They stay ✅
— the phases were done — and each gets *"code removed at 244Y: …"* naming
the replacement. History is not rewritten; it is annotated.

## Scope

1. **Delete the seven modules and ten defs in S0-2**, and every re-export of
   their names in `engine/__init__`, `auth/__init__`,
   `hardware/protocols/__init__`, `inventory/__init__`, `accounting/__init__`
   and `shop/__init__`. `base.py`'s three `:class:` docstring references to
   the protocol models are reworded.
2. **Tests go with their code**: the four whole files deleted; the partial
   files trimmed to the tests of what remains; the three gate tests edited
   with a docstring naming what 244Y removed and why the gate's meaning
   survives.
3. **The allowlist loses every entry for deleted code** (the stale-entry
   tests enforce it), `compile_vehicle`/`compile_all` move to `public-api`,
   and the pins move with history.
4. **Roadmap rows annotated**, status unchanged.
5. **Proof in both directions**: the full regression shows nothing live
   needed what left; the gate's stale-entry tests show the list tracked it.

## Non-goals

- **The six kept-shelved engine modules stay** — `repair`, `parts`,
  `workflows`, `intermittent`, `correlation`, `confidence`. The audit's word
  was *keep shelved*: they are the only path to content the knowledge base
  does not carry. Their content hazards are 244Z.
- **No wiring**, no new surface, no schema change, no table dropped.
- **No status change on any roadmap row.**

## Verification Checklist

- [ ] Every file and def in S0-2 is gone; `git diff --stat` matches the before-state
- [ ] No `__init__` re-exports a deleted name; `base.py` has no `:class:` reference to `protocols.models`
- [ ] `categorize_symptoms` still imports and `media/transcript_extraction.py` still works
- [ ] `advanced/recall_repo.list_recalls_for_vehicle` delegation still works (`advanced recall lookup` path)
- [ ] `compile_vehicle` still importable; `test_phase244M` untouched and green
- [ ] Gate 3: 33 tests remain and pass; docstring names the six removed and why
- [ ] Gate 5 and Gate R: green, with their notes
- [ ] Allowlist: zero stale entries in all three tables; pins 95 / 13 / 37 with history
- [ ] Roadmap rows 86/88/89/94/109/112/134 annotated, still ✅
- [ ] Mutations: restore one deleted module (stale test fails); leave one allowlist entry (stale test fails); leave one re-export (import error or stale test)
- [ ] Full regression green
