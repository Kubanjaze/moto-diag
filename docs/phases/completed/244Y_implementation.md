# Phase 244Y — Dead code leaves with its evidence

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-18

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

- [x] Every file and def in S0-2 is gone; `git diff --stat` matches the before-state
- [x] No `__init__` re-exports a deleted name; `base.py` has no `:class:` reference to `protocols.models`
- [x] `categorize_symptoms` still imports and `media/transcript_extraction.py` still works
- [x] `advanced/recall_repo.list_recalls_for_vehicle` delegation still works (`advanced recall lookup` path)
- [x] `compile_vehicle` still importable; `test_phase244M` untouched and green
- [x] Gate 3: 33 tests remain and pass; docstring names the six removed and why
- [x] Gate 5 and Gate R: green, with their notes
- [x] Allowlist: zero stale entries in all three tables; pins 95 / 13 / 37 with history
- [x] Roadmap rows 86/88/89/94/109/112/134 annotated, still ✅
- [x] Mutations: restore one deleted module (stale test fails); leave one allowlist entry (stale test fails); leave one re-export (import error or stale test)
- [x] Full regression green — **6,947 passed, 0 failed, 25:45**

---

## Results (v1.1)

**Built as planned, with the gate finding a second order the plan could not
have listed, and one permission I could not grant myself.**

### The deletion

Seven modules and twelve defs — the plan's ten, plus two the gate surfaced
once the ten were gone — **1,904 source lines**, all with their table entry
naming the live replacement. Four whole test files went with their modules;
nine were trimmed by AST (a test goes if its source names a deleted name; a
class goes if that empties it); the three gate tests carry a docstring
naming what left and why the gate's meaning survives. Six package inits
pruned; `base.py`'s three Sphinx references reworded. 288 tests across the
trimmed files, the three gates and 244M pass unchanged in their assertions.

### Deviation 1 — the auto-mode classifier declined the eleven `git rm`s

"Irreversible Local Destruction." They are on a branch and git-reversible,
but that is the classifier's call, and the operator's rule is that
destructive changes are theirs. Every other build step is an *edit*, so the
build ran with step 1 replaced by an existence check that printed the exact
removal command; the operator ran it. The intentionally red tree in between
— table entries removed, files still present — was the gate reporting
exactly that, which is what it is for.

### Deviation 2 — the gate found the second order

With the first-order dead code gone, the gate's new-orphan test reported
three names whose only callers had just left: `engine/symptoms.py::
build_differential_prompt` (42 lines, called only by `SymptomAnalyzer`),
`cli/subscription.py::TierAccessDenied` (16 lines, raised only by
`requires_tier`), and `auth/models.py::Permission` (5 lines, constructed
only by `roles_repo`). The first two exist to serve deleted code and were
cascade-deleted, with the one test that named the prompt builder. The third
is a data model for the live `permissions` table, which `shop/rbac.py` reads
with its own SQL; its four siblings were already `public-api`, and it joined
them. A second gate run then reported a **third order**: removing the
now-unused `Recall` import from `recall_repo` cut the last live thread to
`inventory/models.py`, whose other consumers — the three substrate repos —
were already on `MODULE_ISLANDS`. It is Phase 118 substrate like them,
awaiting the same rows, and joined the table (19 → 13 → 14) rather than the
deletion. A third run reported nothing new. Nothing found the second order
until the first was gone, and nothing needed to: the stale-and-new tests are
the loop. The before-state grew from 1,846 to 1,904 lines and this section
says so rather than the plan being edited.

### Deviation 3 — my own list missed two names, and the surface diff caught it

`DELETED_NAMES` listed ten of `roles_repo`'s twelve public functions;
`user_has_permission` and `list_user_permissions` were not on it, so the
init pruner left them in `auth/__init__.py`'s `__all__` and `test_phase112`
kept an import of one. A diff of every deleted module's full AST surface
against the list found them before anything was committed. Both had no live
caller — the gate had been right about the module — and the test that used
one, alone in its class, went with the class.

### Deviation 4 — a mutation survived the static suites, and that is a finding

M3, a dead re-export left in `engine/__init__`, passed all three gate
suites: they read files and never import the package. It would have died in
the full regression, but a phase's own tests should catch its own failure
mode, so `test_phase244Y_delete_pass.py` imports every pruned package and
checks every `__all__` name resolves — the check that had been run by hand
after every step, made into a test. M3 dies against it. Recorded as 4/4
with that caveat, not as 3/4 quietly rounded up.

### Deviation 5 — 244G's meta-guard caught this file reading raw source

The first full regression failed exactly one test: 244G's
`test_no_test_asserts_a_literal_against_raw_python_source`, on three
assertions in this phase's own test file — the delegation check read
`advanced/recall_repo.py` raw, and the `base.py` and gate-note checks read
raw text on purpose, because what they check *is* a docstring. 244G exists
because a guard that reads source text will eventually read a comment; it
was right to fire. The import check now reads `code_of(...)`, where an
import statement survives blanking; the two docstring checks carry
`raw-source-ok` with the reason. Re-run in full rather than partially.

### Two corrections carried from Step 0

The recall repo 244X called a duplicate is delegated to by the live one for
`list_recalls_for_vehicle` (`advanced/recall_repo.py:301`); the four
orphaned functions went, the file stayed, and 244X's entries were corrected
before commit. `compile_vehicle` and `compile_all` stay as `public-api`
because 45 tests in `test_phase244M` call one of them.

### Verification

- 50 tests in `test_phase244Y_delete_pass.py`: the deletions by module,
  def and file; every pruned package imports and its `__all__` resolves;
  the surviving names; the live delegation; the lists let go; the second-
  order model's classification; the gate notes.
- **4/4 mutations**: a deleted def restored (stale-entry test fails); a
  deleted module's entry left behind (stale-entry test fails); a deleted
  module restored with its entry gone (new-island test fails); a dead
  re-export left in an init — survived the static suites, killed by the
  phase's import test.
- `ruff`: seven unused imports the strips left, removed; `auth/__init__`
  12 → 1 findings; the new file's 4 remaining findings are its `f9-noqa`
  pin lines and the two `raw-source-ok` markers 244G requires on the assert
  line itself.
- Allowlist: `ORPHANS` 104 → 96, `MODULE_ISLANDS` 19 → 13 → 14,
  `UNREACHABLE_MODULES` 38 → 37, zero stale in any table.
- No schema change; every table these touched stays.
- Full regression **6,947 passed, 0 failed, 25:45** (7,145 → +50 new, −248 removed with their code).
