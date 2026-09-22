# Phase 255C — The junction stores names the tier query cannot match — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-22

---

### 2026-09-22 11:40 — Bug fix #1: a comma inside a thousands separator split a figure in half

**Issue.** `known_issue_models` held `'000 km'` (3 rows), `'F3 at 30'`,
`'Rivale at 12'`, and the bare numbers `'10'`, `'24'`, `'45'`, `'60'` as
model names. A bare `'10'` in the model vocabulary matches almost any text,
so the damage was not limited to the junction — it reached the resolver's
matching pool.

**Root cause.** `models._model_tokens` splits a model value on
`,|;|—|–|/| and`. A comma **between digits** is a thousands separator, not a
list delimiter, and nothing distinguished the two. `"Rivale at 12,000 km"`
split into `"Rivale at 12"` and `"000 km"`; `"Diavel V4 (V4 Granturismo,
60,000 km)"` contributed `"60"` and `"000 km)"`.

**Fix.** `_THOUSANDS_COMMA` (`(?<=\d),(?=\d)`) is substituted for a hold
character before the split and restored after, exactly as `_COMPOUND_SLASH`
already does for a slash inside a compound designation. The idiom was
already in the file; the digit case was simply not covered.

**Files.** `src/motodiag/knowledge/models.py` — `_THOUSANDS_COMMA` and
`_COMMA_HOLD` added beside `_SLASH_HOLD`; the hold and restore added in
`_model_tokens`.

**Verified.** Junction rebuilt on a copy of the live database: 2,433 → 2,430
rows, 706 → 705 distinct strings.

```
GONE : '000 km', '10', '24', '45', '60', 'F3 at 30', 'Rivale at 12'
NEW  : '10,000 km', '24,000 km', '45,000 km', '60,000 km',
       'F3 at 30,000 km', 'Rivale at 12,000 km'
```

Positive control — a real comma list must still split:
`"Agility 50, Agility 125, People S 250"` → three tokens;
`"PCX125, PCX150, PCX160"` → three tokens.

**Known consequence, recorded rather than fixed here.** The fix turns
torn-in-half debris into *whole* debris. The six new strings carry a code
token (`000`) and therefore fall in group (B), which the extraction gate
does not reject and which the operator's decision of 2026-09-22 leaves as
it is, filed on the general-applicability ticket. The fix is still strictly
better: four bare numbers leave the model vocabulary, where they could match
almost any text.

**Commit.** `8fd680f`.

> **The bug-fix register for this phase is #1 through #7**, one dated entry
> each, in the shape Issue / Root cause / Fix / Files / Verified / Commit.
> #1 is here; #2–#4 are at 15:40, #5–#6 at 16:20, #7 at 18:05.

### 2026-09-22 12:20 — The positive gate at extraction

**What it replaces.** `CONTRAST`, `_PROSE_WORD`, `_NEGATED_PAREN` and
`is_scope` are all blacklists, and every debris root cause found was a gap in
one of them. Four gaps in a single pass is the signature of the wrong shape
of check: **a blacklist admits everything nobody thought to name.**

**The rule.** `admits_as_model` rejects a fragment that contains a bare
lowercase word and carries no designation code. Parentheticals are stripped
first, so `R-series (airhead)` is judged on `R-series`.

**The bypass that the whole-corpus control found.** `is_plain_model` is used
as an early-accept in **two** places — `_model_tokens` and `extract_models`
— and neither consulted any filter. A short delimiter-free prose sentence
took that branch in both. `"Piaggio Group marques only"` is 26 characters
with no comma and reached the junction whole through each of them. Gating
one left the other open, and only running the gate over all 705 strings
showed it.

**Result, on a copy of the live database:** junction 2,430 → 2,334 rows,
705 → 650 distinct strings. The gate rejects **exactly** the 55 pinned
group (A) strings and admits the other 650, every group (B) string included.

**Two pins moved deliberately.** Phase 250C's `BEFORE` table asserts no
marque's pool may shrink; Ducati 83 → 78 and Triumph 82 → 77, because what
left was `dry clutch`, `wet slipper clutch`, `spring valves`, `rear radar`,
`belt-driven cams`, `carburetted`, `injected`, `independent`, `related` and
`per handbook`. Each is in `REJECTED_BY_THE_GATE`. First time that table has
been lowered, and it stays a pin: a pool may only shrink by strings named in
the pinned set.

**Break-it.** Disabling the gate in `_model_tokens` fails 2 tests; disabling
only the `extract_models` plain-model accept fails the whole-corpus control
specifically — which is the test that found that bypass in the first place.

### 2026-09-22 15:05 — The fork on single-token models, and a remedy for a non-problem

**Issue.** Building the pair form raised a case v1.0 had not decided: a model
name that is a single token also present as a marque or a common word. `ONE`
is the specimen — LiveWire's model, and an English word.

**Two branches drafted, both rejected.** Each kept or reintroduced the marque
inside the model string, which decision 3 forbids. The operator's ruling was
*neither branch* — the fork is an extraction problem, not a canonical-form
one.

**The mechanism tried.** Admit a single-token model only when it appears
adjacent to its marque in the source string. Measured before committing, as
instructed: it **lost 457 legitimate rows across 108 models.** `SR` 33 → 1,
`DS` 28 → 1, `Experia` 26 → 0, `DSR` 26 → 2, `FX` 20 → 1, `Alpinista` and
`Mulholland` 16 → 0 each, plus `Grom`, `Thruxton`, `Speedmaster`. Named and
stopped, per the standing instruction not to reach for a list. Stripped out.

**Why it was ever built.** The "32 false `One` rows" it was meant to remove
do not exist. The count was read off the rows' **titles** rather than the
**model columns** that produced the junction entries. Forty-two model columns
literally contain `LiveWire ONE`, and a bare `One` was the correct canonical
on every one of them. Recorded as D7 in the plan, and on the CLAUDE.md
instance list as *measure what produced the number*.

**Resolution.** Decision 3's plain rule, nothing added. `One` stays bare;
`Zuma` collapses against `Zuma 125` by containment. `_stands_alone` and
`_is_single_token` removed. The per-marque dedupe restructuring is kept
regardless — under the pair form `dedupe_contained` must compare within one
make, which is right whether or not a cross-make collision exists today.

**Measured after.**

| quantity | before | after |
|---|---|---|
| PCX 150 rows at tier `model` | 2 | **11** |
| PCX 150 retrieved / kept | 166 | **166, unchanged** |
| distinct `(issue, model)` | 2,433 | **2,397** (ceiling was 2,412) |
| total `(issue, make, model)` | — | **2,795** (+398 = the marque dimension) |
| PCX spellings in the junction | 6 | **1** |
| Guard 2 violations, per marque | — | **0** |
| strings the whole-corpus gate rejects | — | **55, exactly** |

**Break-it.** Guard 1 and Guard 2 were each broken on purpose and seen to
fail before the commit landed.

### 2026-09-22 15:40 — Bug fix #2: migration 065's post_apply wrote the wrong table shape

**Issue.** Any database at schema 64 or 65 could not migrate. The failure is
a write against a table that does not have the column being written.

**Root cause.** Migration 065's `post_apply` calls
`models:rebuild_model_index`. Phase 255C changed that function to write the
`(issue_id, make, model)` pair form — but 065 runs while the junction is
still the 2-column `(issue_id, model)` table, because the column is added by
066, which has not run yet. The function was correct for the schema it ends
at and wrong for the schema it runs at.

**Fix.** `index_models_for_issue` reads `PRAGMA table_info(known_issue_models)`
and writes 3 columns when `make` is present, 2 (deduped) when it is not. It
writes to suit the shape in front of it rather than the shape it expects.

**Files.** `src/motodiag/knowledge/models.py` — `index_models_for_issue`.

**Verified.** A database seeded at 64 migrates to 66 without error; the
255B round-trip test exercises the 64 → 66 → 64 path end to end.

**Commit.** `f11505b`.

### 2026-09-22 15:40 — Bug fix #3: the schema-56 degradation path crashed on placeholder count

**Issue.** `sqlite3.ProgrammingError: Incorrect number of bindings supplied`
on any database that has not taken migration 057.

**Root cause.** The tier query gained a binding when the junction test
became a `(make, model)` pair. The make-only fallback — the branch that
keeps a pre-057 database returning rows rather than silence — kept its five
placeholders while being handed the new six-parameter list.

**Fix.** A separate `make_only_params` built for that branch, five bindings
to five placeholders.

**Files.** `src/motodiag/knowledge/vehicle_resolver.py` —
`known_issues_for_vehicle`.

**Verified.** `test_the_degradation_path_still_binds` builds a database at
the older schema and executes the fallback; it fails with the shared
parameter list and passes with the separate one.

**Commit.** `f11505b`.

### 2026-09-22 15:40 — Bug fix #4: migration 065's rollback restored a string no rebuild produces

**Issue.** A full rollback to schema 64 landed the junction one row short —
2,385 → 2,384 — with `(164, 'Symba')` lost and `'SYM Symba'` left behind.

**Root cause.** `known_issue_models` is derived, and the rollback path has no
`post_apply` to rebuild it, so 065's `rollback_sql` restores two junction
rows by hand. One literal read `'SYM Symba'` — the form the model **column**
spells. Phase 255C canonicalises that machine to `'Symba'`, so the rollback
inserted a string no rebuild would ever produce. The 2,385 baseline was
inflated by the same spurious insert, so the correct figure on both sides is
2,384.

**Fix.** The literal changed to the canonical `'Symba'`, with the reasoning
left in the SQL comment so the next canonicalisation finds it.
`'Filly LX 50'` needed no change: its marque is Kymco, which the column does
not prefix. **Junction literals are written in the form the extractor
produces, never the form the column spells.**

**Files.** `src/motodiag/core/migrations.py` — migration 065 `rollback_sql`.

**Verified.** The round trip is exact in both directions,
`LOST: []  GAINED: []`, measured on an independently reconstructed
pre-255B seed.

**Commit.** `f11505b`.

**Process note.** 255C's first three commits were made on `master` rather
than on a phase branch, against the convention every prior phase follows.
Corrected before this commit: `phase-255C-junction-identity` was created at
the tip and local `master` rewound to the pushed v1.0 at `297780a`. Nothing
that had been pushed was discarded.

### 2026-09-22 16:20 — The full regression found two the narrow run could not

The four-file run was green and the first commit landed at `f11505b`. The
full regression — 8,088 collected — came back **2 failed / 8,086 passed** in
30m56s. Both failures were real, and neither was reachable from the files
255C had touched. This is the case for running the whole thing.

**Failure 1 — `test_phase245_damon_absence`: `'HyperSport' != 'Damon
HyperSport'`.** A **17th** pinned literal, where D4's AST enumeration named
sixteen. The pin was stale, not wrong-to-move: the caller asks for
`("Damon", "HyperSport")` and was handed back a model carrying its own
marque, because the vocabulary was built from Phase 241's column, which
spells it `Damon HyperSport`. **The canonical a caller got back could not be
typed by that caller** — 255C's defect in miniature. Moved to `HyperSport`;
`corpus_hits == 0` still pins what the file exists to guard.

**D4's enumeration missed one, and the reason is worth recording:** it
enumerated consumers of canonical strings in `src/`. This pin is in a test,
asserting a resolver return value. The enumeration's positive control proved
it found what it looked for; it did not prove it looked in the right places.

**Failure 2 — 209B's orphan pin: `knowledge/models.py::extract_models`.** The
pair form superseded its one `src/` caller, leaving a public function
referenced by nothing but its own tests — the F9 integration gap, exactly
what that pin is for.

**It was deleted rather than allowlisted, and measuring is what decided
that.** `extract_models` and `extract_model_pairs` disagree on **3 of 1,003**
live rows, and every disagreement is a marque-prefixed raw string:
`Energica Experia`, `KTM 690 Duke (LC4 single)`, `KTM LC8 75-degree V-twin`.
A superseded function still emitting the defect its replacement removes is a
loaded gun for the next caller.

**And chasing that disagreement found bug fix #5, which is the real one.**
The three rows above are indexed by the pair form as **nothing at all**. The
plain-model early accept tests **exact** vocabulary membership, and
`Energica Experia` is not in a pool that now correctly holds `Experia`. So
row 868 names the Experia and an Experia can never reach tier 0 on it —
**255C's own defect, reintroduced on three rows by 255C.**

The accept is removed, not patched. It skipped `covered_part` *and* the
vocabulary and returned the raw column text, which is a second normaliser in
a phase whose decision 1 says extraction has none.

| | |
|---|---|
| rows unchanged | **985** |
| rows changed | **18** |
| rows lost | **0** |
| rescued from being indexed as nothing | **3** |
| distinct `(issue, model)` | 2,393 → **2,397** |
| total `(issue, make, model)` | 2,791 → **2,795** (ceiling 2,412 on the distinct form still holds) |

The fifteen others traded a raw string for the canonical:
`S1000XR (2015-2019)` → `S 1000 XR`, `Road King (FLHR)` → `Road King`,
`R-series (Paralever)` → `R-series`, and `R1150/R1200 (Integral ABS)` →
**both** `R1150` and `R1200` — one row reaching two machines it always named.

**Where the gate went.** It stays in `_model_tokens`, at vocabulary
construction, which is where a name is first admitted and where the
whole-corpus negative control measures. Nothing reaches `extract_model_pairs`
that the vocabulary did not already admit, so the second gate had nothing
left to gate.

### 2026-09-22 17:10 — Deploy verification, measured like for like

**A correction to this log's first deploy report.** The before/after table
posted at deploy took its "before" column by running **255C's code against
the pre-255C schema**, which is the degradation path, not the old behaviour.
Totals are unaffected by that — a total does not depend on tier — but every
"before" tier-0 figure in it was understated, some to zero. A table that
reads as like-for-like must be like-for-like, so it was measured again.

**Method.** A detached worktree at `3a5fbdb` (the pre-255C master tip,
`SCHEMA_VERSION = 65`) run against
`~/backups/motodiag/motodiag_pre255C_20260922_150946.db`, the backup taken
immediately before migration 066. Old code, old schema, old data. The "after"
column is `709a335` against the live database at schema 66. Same sixteen
machines, same query, same limit.

| machine | total | tier `model` | resolved model |
|---|---|---|---|
| Honda PCX 150 | 166 → 166 | **2 → 11** | `PCX 150` |
| Honda Gold Wing | 166 → 166 | 1 → 1 | `GL1800 Gold Wing` |
| Honda Grom | 166 → 166 | 8 → 8 | `Grom` |
| Kawasaki Ninja 400 | 141 → 141 | 7 → 7 | `Ninja 400` |
| Yamaha R1 | 128 → 128 | 0 → 0 | *unresolved* |
| Yamaha XS650 | 128 → 128 | 5 → 5 | `XS650` |
| Yamaha Zuma 125 | 128 → 128 | **6 → 14** | `Zuma 125` |
| Kymco Agility 50 | 17 → 17 | **1 → 9** | `Agility 50` |
| Vespa LX 50 | 19 → 19 | **1 → 9** | `LX50` → **`LX 50`** |
| Genuine Buddy 125 | 16 → 16 | **2 → 10** | `Buddy 125` |
| Energica Experia | 43 → 43 | 26 → 27 | `Experia` |
| BMW R1200 | 63 → 63 | 3 → 4 | `R1200` |
| Harley-Davidson Road King | 166 → 166 | 1 → 4 | `Road King` |
| LiveWire ONE | 47 → 47 | **0 → 42** | *unresolved* → **`One`** |
| SYM Symba | 15 → 15 | 3 → 4 | `Symba` |
| Damon HyperSport | 11 → 11 | 10 → 10 | `Damon HyperSport` → **`HyperSport`** |

**Retrieved total changed on zero of sixteen machines.** Tier-0 rows summed
over the sixteen go **76 → 165**. Nothing is added or removed; rows move up a
tier, which is what 244I's monotonicity pin requires.

**What the honest column changes about the story.**

* **Grom 8 → 8 and Damon HyperSport 10 → 10 are FLAT.** The degradation-path
  table showed both starting at 0, which read as a gain. Neither gained.
* **Energica Experia is 26 → 27, not 0 → 27.** The single row is the bug fix
  #5 rescue of row 868 — real, and exactly one row, not twenty-seven.
* **LiveWire ONE 0 → 42 survives the honest measurement**, and is the largest
  single gain in the table. `resolve_vehicle("LiveWire", "ONE")` returned
  **nothing at all** before — the model did not resolve, so no row could
  reach tier 0 by name. These are the 42 rows the "32 false `One` rows"
  measurement would have destroyed.
* **Two canonical forms are visible in the resolver itself**: `LX50` → `LX 50`
  and `Damon HyperSport` → `HyperSport`, the latter being F136's pin, now
  confirmed on live data rather than in a fixture.
* **The four non-CVT controls are unchanged in both columns** — Gold Wing
  1 → 1, Ninja 400 7 → 7, R1 0 → 0, XS650 5 → 5 — which the degradation-path
  table could not have established, because it was not measuring the old
  behaviour on any of them either.

**The rule this is an instance of** is the one added to CLAUDE.md the same
day: *measure what produced the number.* A "before" column produced by new
code is not a number about the old code, however carefully the rest of the
table is built.

### 2026-09-22 16:20 — Bug fix #5: the plain-model early accept bypassed canonicalisation

**Issue.** Three live rows — 868, 1290 and 1307 — were indexed into the
junction as **nothing at all**. Row 868 names the Energica Experia, so an
Experia could never reach tier 0 on the row that names it: Phase 255C's own
defect, reintroduced on three rows by Phase 255C.

**Root cause.** 244I short-circuits a delimiter-free model value straight
into the index, skipping `covered_part` *and* the vocabulary, so the raw
column text became the junction entry. The pair form's version of that
accept tested **exact** vocabulary membership, and `Energica Experia` is not
in a pool that now correctly holds `Experia`, so no marque owned it and the
row produced no pair. Decision 1 says extraction has no normaliser of its
own; an accept that returns the input unchanged is a second normaliser, and
the worst kind.

**Fix.** The accept is removed, not patched. Every value goes through the
vocabulary, which is canonical. The gate stays in `_model_tokens`, at
vocabulary construction, where a name is first admitted.

**Files.** `src/motodiag/knowledge/models.py` — `extract_model_pairs`.

**Verified.** Measured over the corpus: **985 rows unchanged, 18 changed, 0
lost**, three rescued from being indexed as nothing. The other fifteen
traded a raw string for the canonical: `S1000XR (2015-2019)` → `S 1000 XR`,
`Road King (FLHR)` → `Road King`, `R-series (Paralever)` → `R-series`, and
`R1150/R1200 (Integral ABS)` → **both** `R1150` and `R1200`.

**Commit.** `0e438ca`.

### 2026-09-22 16:20 — Bug fix #6: extract_models was orphaned and still emitting the old defect

**Issue.** Phase 209B's orphan pin failed:
`knowledge/models.py::extract_models` is referenced by no code anywhere in
`src/`. The F9 integration gap — a public function kept alive only by its
own tests.

**Root cause.** The pair form superseded its single `src/` caller.

**Fix.** Deleted rather than allowlisted, and measuring is what decided
that: `extract_models` and `extract_model_pairs` disagree on **3 of 1,003**
live rows, and every disagreement is a marque-prefixed raw string —
`Energica Experia`, `KTM 690 Duke (LC4 single)`, `KTM LC8 75-degree V-twin`.
A superseded function that still emits the defect its replacement removes is
a loaded gun for the next caller.

**Files.** `src/motodiag/knowledge/models.py` (deletion plus a note where it
stood); `tests/test_phase244I_model_vocabulary.py` — four assertions about
exclusion parsing now project the pair form through one `_extracted` helper.

**Verified.** 209B's orphan pin passes; 244I's four assertions test the same
property through the projection.

**Commit.** `0e438ca`.

### 2026-09-22 18:05 — Bug fix #7: canonicalise stripped only the pool's own marque

**Issue.** Raised by the operator's terminal check. **59 junction rows carry
a model string that begins with a marque name**, which decision 3 forbids:
`LiveWire One` (42 rows) and `LiveWire S2 Del Mar` (17 rows), both filed
under `Harley-Davidson`.

**Root cause, in two parts.**

*The code.* `canonicalise(marque, names)` strips `marque.lower() + " "` —
the pool's OWN marque only. `LiveWire One` does not begin with
`harley-davidson `, so it survived with the marque attached. A sub-brand's
name in its parent's pool is invisible to that rule.

*The rationale.* The docstring stated the narrowing was deliberate: that
`LiveWire One` under Harley-Davidson "is a machine there and **not a
redundant prefix**". **That was asserted, never measured.** Measured: all 59
are redundant. Every issue holding `(Harley-Davidson, 'LiveWire One')`
already held `(LiveWire, 'One')`; every issue holding
`(Harley-Davidson, 'LiveWire S2 Del Mar')` already held
`(LiveWire, 'S2 Del Mar')`. **Not one issue had only the prefixed form.**

**And the guard that should have caught it did not exist.** Decision 6
specified *no junction string starts with a marque name*, and `0` was
reported against it. That `0` was S0-5's **cross-marque collision** count —
no normalised key carrying two explicit marques — which is a different
question that also answers 0. Guard 1 could not see this class (a
marque-leading string is in the vocabulary, so it resolves to itself
perfectly) and Guard 2 could not either (it is scoped per marque, and these
are two different marques' pools). The specified guard was never written.

**Fix.** `canonicalise` takes the marque vocabulary and strips a leading
**known marque, whoever owns the pool**, longest prefix first. Guard 3 is
now written as specified and run over the whole junction, with a positive
control that plants `Yamaha Zuma 125` under Honda and asserts the rule
returns it and only it — guard and control sharing one rule function,
because a control that reimplements the rule proves only that two
implementations agree.

**Files.** `src/motodiag/knowledge/models.py` — `canonicalise` and its call
site in `model_vocabulary`; `tests/test_phase255C_junction_identity.py` —
Guard 3, its positive control, and a unit test of `canonicalise`;
`tests/test_phase250C_model_vocabulary.py` — see below.

**Verified.** Guard 3 over the live junction: **59 → 0**. Rebuild is
surgical — junction total unchanged at 2,795, `LiveWire One` → `One` (42),
`LiveWire S2 Del Mar` → `S2 Del Mar` (17), nothing else moves. Retrieval
re-measured across all sixteen machines: **no machine's total or tier-0
count changes**, which is what "all 59 were redundant" predicts. Break-it:
with the fix reverted, Guard 3 fails listing all 59 and the positive control
fails too.

**One test moved with it, and it is the same lesson again.** 250C's
`test_a_sub_marques_models_stay_with_its_parent` asserted that
Harley-Davidson's pool contains a string with the **substring `"LiveWire"`**
in it — the marque's *spelling* standing in for the sub-marque's *machines*.
Decision 3 removed the marque from every model string, so the proxy went to
zero while the property it stood for was completely intact: every one of
LiveWire's nine models, `One` and `S2 Del Mar` included, is still reachable
from Harley-Davidson. The assertion now names the machines and checks
containment directly, which is what its docstring always claimed it did.
**Measure what produced the number** applies to assertions as well as to
counts.

**Commit.** See the close-out commit for this fix.

### 2026-09-22 19:30 — Closing regression and final state

Added at Phase 255D's close-out check, which found the phase log carried no
line recording the final regression with both its commit and its count. The
figures were in the commit messages and the `implementation.md` row but not
here, which is the one place a reader looks for them.

**Regression 8,091 passed / 0 failed / 0 skipped / 31:37 at `f279533`.**
Merged at `090615b`. Schema 65 → 66. `COLLECTED_TEST_FLOOR` 7,999 → 8,091.
Live junction 2,795 rows, marque-leading strings 0, `integrity_check: ok`.
Backup `motodiag_pre255Cfix7_20260922_162542.db`, 5 retained.
