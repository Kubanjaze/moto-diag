# Phase 244W — The gate can see a module that only talks to itself

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

Phase 209B built a reachability gate with three checks — name-level orphans,
package-level islands, and an import-graph walk — and Phase 244U closed its
first blind spot (a package re-export counted as a use). Auditing what 244U
exposed found the second: **a module whose public names refer only to each
other, inside a package that is otherwise alive, is invisible to all three
checks.**

`engine/history.py` and `engine/retrieval.py` — 668 lines, `DiagnosticHistory`,
`CaseRetriever`, two more never-measured scoring weight vectors — have no
caller anywhere in `src/`. They are not on the allowlist, because the gate has
never reported them. Nothing asks the module-level question.

## Step 0 — findings

Every number here was measured on this tree, not carried over from the audit
that raised it.

**S0-1. The mechanism, exactly.** `find_orphans` treats a name as used when
`elsewhere = total[n] - own[n] > 0` **or** `here = own[n] - 1 > 0`. The second
clause exists so a helper called within its own module is not an orphan, and
it is right to exist. But it also means a class that names itself launders
itself, and a dead module that imports a second dead module launders that one:

```
engine/retrieval.py   CaseRetriever      own=3  total=3  -> laundered  self-refs=2
                      SimilarityScore    own=5  total=5  -> laundered  self-refs=4
engine/history.py     DiagnosticHistory  own=1  total=4  -> laundered  elsewhere=3
                                            (all three references are in retrieval.py)
                      HistoryStatistics  own=4  total=4  -> laundered  self-refs=3
```

**S0-2. Why the other two checks do not catch it either.** `find_islands` is
*package*-level and `engine/` has dozens of live names, so it is not an island.
`find_unreachable_modules` walks imports, and `engine/__init__.py:24-25`
imports both modules — the same "a re-export is a real import edge but not a
use" distinction 244U pinned in `test_a_re_export_is_still_an_import_edge`.
Both existing answers are correct on their own terms. The gap is that nothing
composes them.

**S0-3. Scale: 19 modules, 4,270 lines — reconciled from three independent
measurements, after my own was wrong three times.** A module-level island
fixpoint (a module is an island if no public name it defines is referenced
from any non-island module, package inits excluded as referrers per 244U)
first reported **55 modules / 15,669 lines**. False: without treating FastAPI
route modules as live, the sweep transitively swallowed everything only a
route handler calls (`billing/webhook_handlers.py::dispatch_event` is called
at `api/routes/billing.py:188`; the prototype called it dead). Corrected to
**25 modules / 5,278 lines** — also wrong: the allowlist has *two* tables and
I had checked one; sixteen of the 25 were already in `UNREACHABLE_MODULES`.
Hand-verified floor: **nine modules / 1,398 lines** that neither table holds.

Two independent prototypes written against this tree — an island fixpoint
pre-seeded with the 38 modules the import walk already calls dead, and a
use-graph rewrite of that walk — then agreed with each other on **18
modules** and with my nine on all nine, and found what my prototype missed:

- `inventory/item_repo.py` (131 lines): zero external references to any of
  its eight names, verified by hand. My throwaway script had a false negative
  here, and the reason is instructive: `pricing/repair_plan.py:125` defines
  its *own* `add_item`, and `pricing` is already on `UNREACHABLE_MODULES`. An
  identifier count that does not first treat the 38 known-dead modules as
  dead sees that as a live referrer. **A name collision with a dead module
  shields a second dead module** — the same laundering as S0-1, one step
  removed — and pre-seeding the existing check's answer is what removes it.
- **Eight engine modules** — `confidence`, `correlation`, `cost`,
  `evaluation`, `intermittent`, `parts`, `repair`, `workflows` (2,644 lines)
  — whose *modules* are wholly dead while the gate today reports only some
  of their *names* as orphans (13 of their names are on `ORPHANS`). A file
  with one live name is a live file; a file with none is a dead file the
  per-name check can only describe piecemeal. This is a strictly stronger
  reading, not a re-slice: a false-negative probe found no module whose
  public defs are all orphans yet escapes the module flag.

The use-graph then found a 19th the fixpoint could not:
`feedback/learning_hook.py` (97 lines, `FeedbackReader`). Its only reference
outside its own file and the package init is `core/migrations.py:545` —
inside a **string literal** in a migration's description: *"phases 318-327
consume this via FeedbackReader read-only hook."* Docstring blanking does not
touch string literals, so an identifier count sees a live referrer; a graph
that follows imports and resolved names sees nothing. The mention-vs-use
family, in a disguise the existing guard does not strip.

```
  fully invisible to every check (11 modules, 1,626 lines):
    367  engine/history.py           131  inventory/item_repo.py
    301  engine/retrieval.py          122  media/photo_annotation_repo.py
    180  hardware/protocols/models.py  97  feedback/learning_hook.py
    134  auth/roles_repo.py            76  inventory/vendor_repo.py
     75  billing/payment_repo.py       73  inventory/warranty_repo.py
     70  media/photo_annotation.py
  wholly dead, partially on ORPHANS (8 modules, 2,644 lines):
    652  engine/intermittent.py       230  engine/repair.py
    455  engine/correlation.py        198  engine/confidence.py
    411  engine/workflows.py          196  engine/evaluation.py
    308  engine/cost.py               194  engine/parts.py
```

**S0-4. Every one of the eleven was verified by hand, not by a prototype.**
For each, a grep over `src/` for every public name, excluding the module's own
file and every `__init__.py`, returns nothing. The two mentions that looked
like callers were not: `PIDResponse` appears in `hardware/protocols/base.py:137`
inside a Sphinx `:class:` docstring reference, which the gate's own
docstring-blanking already discounts, and `auth/__init__.py`'s two real
functions are a lazy `__getattr__` loader for `auth.deps`, not a caller of
`roles_repo`. Every `__init__.py` that imports one of the nine is a pure
re-export (import + `__all__` + docstring, verified by AST), which is exactly
the edge 244U ruled is not a use. The shape is consistent: the nine are
repository and model layers built for a package whose *other* modules are
live, so the package is not an island and the import edge is real, and the
module sits in the gap between the two.

**S0-4b. Three of the nine are superseded, and one of those is an unfulfilled
contract.** `hardware/protocols/models.py`'s docstring says the adapters
"populate these on the way out"; the adapters Phases 135-139 built return
plain `list[str]` / `Optional[int]` through `ProtocolAdapter`
(`base.py:101-143`), and nothing in the tree constructs `PIDResponse`,
`DTCReadResult` or `ProtocolConnection`. `auth/roles_repo.py`'s read path was
reimplemented inline — `shop/rbac.py:303` walks the same
`roles → role_permissions → permissions` tables with its own SQL — and its
write path exists only as migration-005 seed data. `engine/history.py` is an
in-memory session store beside the live `core/session_repo`. Five are
substrate for named roadmap rows (307, 273, 280, 282-286). `retrieval.py`
reads only from `history.py`. None of this is a delete decision; it is what
the allowlist entries will say, so the delete phase inherits evidence rather
than a list.

**S0-7. Phase 244U's fix has a hole of its own, found by one of the four
design prototypes and verified here.** `blank_exports` blanks the alias list
of a package-init `from … import` with the regex
`(from\s+[\w\.]+\s+import\s*\(?)([^)\n]*\)?)` — and `[^)\n]*` stops at
a newline, so a **parenthesised multi-line import is never blanked**:

```
from demo.shelf import ShelfSitter, Other        -> ShelfSitter blanked: True
from demo.shelf import (\n    ShelfSitter,\n)     -> ShelfSitter blanked: False
```

On this tree `auth/__init__.py`, `inventory/__init__.py`,
`billing/__init__.py` and `feedback/__init__.py` each carry five, five, five
and two imports in that form, and `create_role`, `add_vendor`,
`record_payment` and `FeedbackReader` all survive their init's blanking. So
244U's rule — a re-export is not a use — has silently not applied to most of
the packages where it mattered. 244U's own fixture used single-line imports,
which is why its conjunctive test passed and still passes. This is the same
instrument, so it is fixed here, with a multi-line case in the fixture.

**What the fix costs, measured.** A second blanking pass whose alias group
may cross newlines takes the live orphan count from 58 to 157: **99 newly
reported**, zero stale. 43 of the 99 are inside the 19 dead modules and
disappear the moment a module-level check feeds the pipeline's existing
"orphans in dead files are not reported" filter. The **56 residual** are in
live modules and are what 244U was written to find: names a package init
re-exports and nothing uses. Two of them this repo has already pinned as
callerless by test — `feedback/feedback_repo.py::submit_feedback`
(`diagnostic_feedback` has 0 rows and no writer, per the audit) and
`advanced/recall_repo.py::load_recalls_from_json` (F86's
`test_nothing_in_the_product_seeds_them`). Most of the rest are `count_*` /
`list_*` / `delete_*` repository helpers, data models and exception types —
the `public-api` shape the allowlist already has 19 of. Allowlist writing is
most of the work, and every entry must be classified from evidence, not
bulk-imported; a bulk import is the rubber stamp S0-5 warns about.

**S0-5. The false-positive standard.** This gate runs on every regression. A
check that reports 5,000 lines of "dead" code that is not dead is worse than
no check, because the allowlist becomes a rubber stamp within a week. The
design has to be judged on what it gets *wrong*, and every flagged module has
to be spot-checked against real callers before the number is written down.

**S0-6. The audit that found this also found that none of the eight unwired
engine modules should be wired** (highest consensus 4.3/10; `repair.py:106`
instructs the model to invent torque specs with no labelling; CORR-001 in
`correlation.py:71-82` diagnoses a coolant-jacket leak on an air-cooled twin).
That work is deferred behind this phase on purpose: fixing the instrument
first turns "the audit said delete these" into "the gate says these are
unreachable", which is a decision the tree can hold rather than a conversation.

**S0-8. Four independent designs converge on the same modules.** Prototyped
against this tree without sight of each other: a module-level island fixpoint
(18 modules / 4,173 lines), a use-graph rewrite of the import walk (19 /
4,270), a def-level call graph with binding resolution (18 / 3,231 def-lines),
and AST-scoped orphan detection (the same set, reported at name granularity).
The three module-level results name the **same 18 modules**; the use-graph's
19th is `learning_hook`, which only a design that follows resolved names
rather than identifier tokens can see. Every one of the four catches
`history.py` and `retrieval.py`. Whatever wins, the finding is not an
artefact of one method.

The call-graph prototype also earned its cost in a way the others did not:
its author logged six *intermediate* false positives fixed on the way to
zero, and each is a shape a cheaper check can get wrong silently —
a module whose only live name is a **public constant**
(`hardware/scenarios::BUILTIN_NAMES`, imported at `cli/hardware.py:61`); a
**framework subclass** whose methods Starlette calls and nothing names
(`api/middleware.py::RequestIdMiddleware`); an **aliased import** resolved by
the local alias instead of the original (`schedule_wo as bay_schedule_wo`,
`cli/shop.py:154`); **pydantic request models referenced only as a handler's
parameter annotation** (41 of them across `api/routes/`); a **method
signature default** (`live.py:138`); and **nested defs dropped from a function
body** (`cli/serve.py::register_serve`, whose body is where
`motodiag.api:create_app` is named). Its own count swung 65 → 56 → 14 → 16 →
12 → 18 modules across those fixes. Those six are now acceptance cases below.

## Scope

1. **`find_module_islands` — a module-level island fixpoint, in its honest
   core.** A module is an island when no public top-level name it defines —
   functions, classes *and* module-level constants, framework-decorated names
   included — is referenced from any module that is not itself, not a package
   `__init__`, and not already an island. The island set starts as the import
   walk's dead set (the one seed that changes the answer: it stops a name
   collision with an already-dead module, `add_item` in `pricing/repair_plan`,
   from shielding `inventory/item_repo`) and iterates to a fixpoint; on this
   tree, two generations. It reports only what the existing checks do not.

   Chosen over the use-graph (false-positives judge) and the def-level call
   graph (coverage judge) on the maintenance judge's evidence: with all nine
   of its author's seed rules stripped, its answer is unchanged, so the check
   is ~50 lines with one seed; its "why" is a sentence a reader can grep —
   *`DiagnosticHistory` is named only by `retrieval.py`, which is also dead*;
   and it is immune to both false-positive classes the adversary found in the
   use-graph (package-object attribute access; PEP 562 `__getattr__`, which
   `auth/__init__.py:78` already uses). The surface definition is the
   load-bearing part: reusing `_public_defs`, which strips route handlers,
   leaves route modules with an empty surface that is vacuously dead and
   swallows everything they call — the 55-module blow-up, reproduced to the
   line. Its own limitation is inherited from the existing gate and recorded
   as such: a name collision with a *live* module hides a dead one
   (`advanced/models.py::ServiceInterval` vs `engine/service_data.py`'s).
2. ~~Fix 244U's blanking~~ — **split out as Phase 244X.** S0-7 is a
   distinct defect with a distinct finding: fixing it reports 56 more
   orphans in live modules, each needing its own classification. The
   module-level check does not depend on it (it excludes package inits as
   *referrers*, not by text blanking — the prototype found all 18 with the
   regex still broken), and the adversary's point stands: a single commit
   that adds 19 module entries and 56 name entries is the bulk edit S0-5
   forbids, however well each is reasoned. 244X inherits S0-7's measurement
   (99 → 43 filtered by this phase → 56 residual) and the buckets.
3. **Orphans inside a module the new check calls dead are not reported as
   orphans.** The pipeline already does this for the import walk's dead set
   (`_current_live_orphans` filters by `dead_files`); the module check's
   output joins that filter. A dead file is one finding, not thirty.
4. **The allowlist gains a third table for the 19 modules and loses the 13
   `ORPHANS` entries that sit inside them** (58 → 45), because the file's
   own convention (`allowlist.py:120`) says orphans inside a dead module are
   implied by the module entry and not listed twice. Eleven of the 13 were
   added by 244U one phase ago; they are reclassified from dead name to dead
   file, not lost. Each of the 19 is classified from S0-4/S0-4b evidence;
   substrate entries name their roadmap phase. The stale direction is proven
   on a synthetic tree.
5. **Tests through the gate**, on synthetic trees for every shape in the
   checklist and on the real tree for the 19 by name.
6. **Identifiers inside prose string literals are blanked in the shared
   loader**, so a name that appears only in an error message or a migration
   description is a mention, not a use. Tokenizer-based like the existing
   docstring blanking; a literal with no space (a dotted path, a `post_apply`
   hook, a table name) is left alone. This is what lets the check see
   `learning_hook` (S0-3). Measured on `find_orphans`: 58 → 61, +3, 0 stale —
   `FeedbackReader` (inside a dead module, so filtered), and two names whose
   only reference is prose, added to `ORPHANS` with their evidence.

## Non-goals

- **No deletion in this phase.** The gate reports; the delete decision is a
  separate phase with the gate's output as its evidence.
- **No wiring of anything the audit scored.** See S0-6.
- **No change to what 244U fixed.** `blank_exports` and its conjunctive test
  stay as they are; this composes with them.

## Verification Checklist

Written before the design was chosen, on purpose: these describe the shape of
the blind spot, not the mechanism that closes it, so the winning design is
held to them rather than the other way round.

*On the real tree*
- [x] `engine/history.py` and `engine/retrieval.py` are reported
- [x] All 19 modules from S0-3 are reported — the 11 fully invisible ones and the 8 wholly-dead engine modules — and **nothing else** that is not already in `UNREACHABLE_MODULES`
- [x] `feedback/learning_hook.py` is reported despite `FeedbackReader` appearing in a string literal at `core/migrations.py:545`
- [x] `inventory/item_repo.py` is reported (my own prototype's false negative)
- [x] `billing/webhook_handlers.py` is NOT reported (called only from a route handler — the false positive my first prototype produced)
- [x] No module in `api/routes/` or `cli/` is reported
- [x] The existing gate is unchanged: `test_phase209B` and `test_phase244U` stay green without edits to their assertions, except pins that record a count

*On synthetic trees* (`TestTheScannerIsNotFooled` shape)
- [x] A class that names itself, imported only by a package `__init__`, is reported
- [x] A dead module importing a second dead module reports **both**
- [x] A module called only from a `@router.get` handler is not reported
- [x] A module reached only by module-object access (`import x; x.f()`) is not reported
- [x] A module whose only reference outside itself is in a docstring is reported
- [x] A module whose only reference is a lazy import inside a live function is not reported
- [x] A missing entry point is an error, not an empty answer
- [x] A module whose only live name is a public **constant** imported elsewhere is not reported
- [x] A module used only through an **aliased import** (`from x import f as g`) is not reported
- [x] A module whose only use is as a **parameter or return annotation** of a live def is not reported
- [x] A **framework subclass** (base resolves outside the package) whose methods nothing in-tree names is not reported
- [x] A name used only as a **signature default** of a live def is not reported
- [x] A module named only inside a **nested def** of a live function is not reported

*The allowlist*
- [x] A new entry for each of the 19, classified from S0-4/S0-4b evidence, each reason ≥ 20 chars, substrate entries naming their roadmap phase
- [x] The stale direction works: removing a real caller's reference in a synthetic tree makes an entry stale, and the test says which

*Discipline*
- [x] Mutations: drop the `__init__` exclusion; drop the framework seeding; drop the transitive step; count docstring mentions — each caught
- [x] Runtime of the full gate stays under the 209B budget (it was optimised from ~300k regex scans)
- [x] Full regression green — **7,011 passed, 0 failed, 20:21**

---

## Results (v1.1)

**Built as planned, with one defect the synthetic trees caught that the real
tree could not have.**

`find_module_islands` is 40 lines of logic in
`tests/support/integration_gaps.py`, the fourth check beside the three 209B
built. On the real tree it reports **exactly the 19** — both directions
clean against `MODULE_ISLANDS` — in 1.72s, taking the whole gate from 3.58s
to 5.30s. `billing/webhook_handlers` is not reported; nothing under
`api/routes/` or `cli/` is.

### Deviation 1 — an entry point can never be a candidate

Every synthetic-tree test failed on first run with one signature: the
result was `{'demo.cli.main'}`. The entry-point module defines `cli()`,
nothing references `cli` in a three-file tree, so the module was flagged —
and once it was an island its references stopped counting, and everything
it called was swept in on the next generation. **On the real tree this was
masked because `cli` is named in dozens of files**: the "accident of
naming" the fixpoint's author warned about for `router`, seen from the
other side. The fix is structural, not a seed rule — the roots the question
is asked from are excluded from candidacy — and the docstring now says that
route modules survive today through `app.py` naming each `router`, and that
a framework registering handlers by discovery would need a seed.

### Deviation 2 — the fixture convention

The remaining six failures were the fixture's: 209B's real-tree
`ENTRY_POINTS` includes the package root (`import motodiag` runs its
`__init__`) and my synthetic trees passed only `demo.cli.main`, so
`demo/__init__` was unreachable, everything only it imported was already
dead, and the check correctly declined to report what the import walk
already does. Measured for the record: with only `cli.main` as root,
`demo`, `demo.cli` and `demo.shelf` are all in the import walk's dead set.
The fixture now passes the root, with a comment saying why.

### The 244U regex — split out as 244X

Scope item 2 as planned; see the plan. The measurement is done (99 → 43
filtered by this phase → 56 residual in live modules) and the buckets are
written; the fix and its 56 classifications are one coherent phase of their
own. Fixing it here alongside 19 module entries would have been the bulk
edit S0-5 forbids.

### Prose strings

Scope item 6 shipped in the shared loader. Tokenizer-based, so an f-string's
`{expr}` stays code; a literal with no space is left alone. On `find_orphans`
it surfaced exactly the three predicted: `FeedbackReader` (inside a dead
module, so filtered) and two names whose only reference is prose —
`fleet_repo::list_fleets_for_bike` (a migration description,
`migrations.py:1221`) and `compat_repo::update_adapter` (its own error
message, `compat_repo.py:276`) — both added to `ORPHANS` with that evidence.

### The allowlist

`ORPHANS` 58 → 47: thirteen entries inside the 19 dead modules removed under
the file's own convention (a dead file is one entry), two added. Eleven of
the thirteen were 244U's, one phase ago; they are reclassified, not lost, and
`test_no_orphan_entry_inside_a_dead_module` now enforces the convention
rather than leaving it as a comment. `MODULE_ISLANDS` has 19 entries, every
one classified from S0-4/S0-4b evidence; the eight engine entries carry the
audit's consensus score so the phase that deletes or wires them inherits a
number. Every substrate entry names its roadmap row, checked for all of them
rather than 209B's top-level-only rule. 244U's running-count pin moved 58 →
47 with its history.

### Verification

- 61 tests in `test_phase244W_module_islands.py`: nine on the real tree, the
  table's consistency, thirteen synthetic-tree shapes including the six
  false-positive classes the def-level prototype logged, and five on prose
  blanking. 180 across the three gate suites.
- **11/11 mutations killed**: a re-export counts as a use; no pre-seed; no
  transitive step; `_public_defs` as the surface; prose not blanked; own
  mentions count; entry points as candidates; every string blanked; orphans
  in dead modules re-reported; constants dropped from the surface; the
  import walk's set re-reported.
- `ruff`: the gate file clean (0 → 0); the allowlist's 16 pre-existing E501s
  unchanged; the new test file's one finding is the `f9-noqa` pin line, as
  209B's and 244U's are.
- No schema change, no source change under `src/`.
- Full regression **7,011 passed, 0 failed, 20:21** (6,961 → 7,011: +61 new tests, −11 parametrised allowlist cases).

## Verification Checklist — outcome

Every item in the checklist above is covered by a named test in
`test_phase244W_module_islands.py`; the runtime item was measured (1.72s
added to a 3.58s gate) rather than asserted, because a timing assertion is
how a suite acquires a flaky test.
