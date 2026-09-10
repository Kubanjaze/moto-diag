# Phase 244F — A make column that holds prose cannot be queried

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

`known_issues.make` is a single free-text column carrying, variously: a marque,
a list of marques, a scope phrase, and in one case a whole sentence of findings:

> `"BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia, Moto Guzzi have none"`

The consequence has a name and a number. **LiveWire and Damon do not exist as
queryable makes at all.** All 24 LiveWire rows are tagged
`"Harley-Davidson, LiveWire"`; all 10 Damon rows are inside
`"Zero, Harley-Davidson, LiveWire, Energica, Damon"`. So **Phase 243's entire
output is unreachable**, and `make = 'LiveWire'` returns nothing while the
corpus documents that machine.

The same defect quietly narrows the European makes: an entry tagged
`"BMW, Ducati, KTM, MV Agusta"` is invisible to every one of those four.

## Step 0 findings

**12 distinct multi-value make strings cover 38 entries.** Small enough to
audit individually, and each was:

| value | entries | reading |
|---|---|---|
| `Harley-Davidson, LiveWire` | 14 | two marques |
| `Zero, Harley-Davidson, LiveWire, Energica, Damon` | 10 | five marques |
| 8 further comma/and lists | 11 | marque lists |
| `All European makes` | 2 | genuinely a scope — TEXA licence tiers, valve-train job types |
| `All makes` | 1 | genuinely universal — how to read a vendor compatibility table |
| the sentence above | 1 | a *finding summary* in the make column; its six marques are correct |

**The marque vocabulary can be derived, not invented.** Splitting the
delimiter-separated values on `,` and ` and ` yields clean tokens, and unioning
those with the corpus's single-marque values produces **16 marques including
LiveWire and Damon** — the two that appear nowhere else. Extraction by
whole-word match against that vocabulary resolves 11 of the 12 strings
correctly, the prose sentence included.

**The European set is derivable too.** Seed files named `known_issues_european_*`
contain exactly seven marques: BMW, KTM, Ducati, Moto Guzzi, MV Agusta, Aprilia,
Triumph. That is what `All European makes` expands to.

## Non-goals

- **Not editing 100 seed files.** The `make` strings stay as written; the fix is
  a derived index over them. Rewriting the corpus by script is a larger and
  riskier change than the defect warrants.
- **Not fixing the `model` column.** It has the same disease and needs the same
  treatment, but combining two data migrations under one set of guards means
  neither is verified properly. Phase 244E already makes retrieval survive it.

## Logic

**Migration 055 adds `known_issue_makes (issue_id, make)`** — one row per
(issue, marque) pair, with an index on `make` and a UNIQUE pair constraint, and
a backfill over existing rows. The `known_issues.make` column is left exactly as
it is: it remains what the author wrote, and the junction table is what queries
use. Nothing is rewritten, so nothing is lost.

**Extraction lives in `knowledge/marques.py`** and runs in this order:

1. the value is a known marque → itself
2. `All makes` → the wildcard marker `*`
3. `All European makes` → the seven European marques
4. otherwise → every vocabulary marque appearing as a whole word

**Vocabulary is derived from the corpus at load time**, never hard-coded: single
marque values, unioned with clean tokens split out of the list-valued ones. This
is what makes LiveWire and Damon appear — the same discipline as Phase 244C,
where an alias table would drift the moment a phase adds a make.

**`add_known_issue` populates the junction on insert**, so a re-seed keeps it
correct; it stays idempotent under Phase 244D's `ON CONFLICT DO NOTHING`.

**`known_makes()` returns the marque vocabulary rather than raw column values.**
Today it returns 26 strings including a sentence, and Phase 244C's resolver uses
it as its matching pool. Sixteen real marques is both more correct and the
reason `LiveWire` will resolve at all.

**Retrieval joins the junction**, with wildcard rows included for any make.
Phase 244E's tiers are unchanged.

## Key Concepts

- **One column cannot be both prose and a key.** The fix is not to argue with
  the prose but to derive a key beside it.
- **Derive the vocabulary; never write the list.** Hard-coding 16 marques would
  be wrong the next time a phase adds one.
- **The `make` column is not corrected, only indexed.** What the author wrote
  stays; a lossy rewrite of 970 entries is a bigger risk than the bug.
- **A scope phrase is not a marque.** `All makes` and `All European makes` mean
  something real and are expanded deliberately, not pattern-matched away.

## Verification Checklist

- [x] `make = 'LiveWire'` reaches all 24 LiveWire entries
- [x] `Damon` reaches its 10 entries
- [x] An entry tagged `BMW, Ducati, KTM, MV Agusta` is reachable from each of the four
- [x] `All makes` entries reach any make queried
- [x] `All European makes` reaches the seven European marques and **not** Honda
- [x] The prose sentence's six marques are all reachable
- [x] The marque vocabulary is derived from the corpus, with no hard-coded marque list
- [x] `known_makes()` returns marques, not raw column values
- [x] Re-seeding twice leaves the junction table unchanged
- [x] No make gains an entry that does not name it
- [x] Phase 244E's monotonicity invariant still holds corpus-wide
- [x] Mutation: hard-code the vocabulary → a guard fails
- [x] Mutation: drop the wildcard handling → a guard fails
- [x] Full regression green

## Risks

- **Over-extraction is the dangerous direction.** Attaching an entry to a marque
  it does not concern puts another machine's documented fault in front of a
  mechanic. Matching is whole-word against a closed vocabulary derived from the
  corpus — never substring, never inferred.
- **`All European makes` excludes Energica**, which is an Italian manufacturer,
  because it appears in its own seed file rather than a `european_*` one. The
  two affected entries concern valve-train work and TEXA ICE tooling, so the
  exclusion is defensible — but it is a derivation artefact, not a judgment
  about Energica, and it is recorded rather than hidden.
- **The junction must not drift from the column.** It is rebuilt from the make
  string on every insert, and the migration backfills, so the column stays the
  single source. A guard asserts every issue has at least one junction row.
- **Wildcard rows could swamp a query.** `*` entries are few (one today) and
  Phase 244E's tiering orders them below model-specific rows.

---

## Deviations from Plan

**I reintroduced the exact disease this line of work exists to cure.** Joining
the junction made eleven existing tests go **silently empty**: a database below
schema 55 has no junction table, so the join returned zero rows — and zero rows
is indistinguishable from *"the corpus has nothing to say about this machine."*
That is the same failure as `make = 'Homda'` returning nothing, which is what
started this chain at Phase 244C. Built the cure, rebuilt the disease one layer
down.

A missing junction now falls back to matching the `make` column — exactly the
pre-244F behaviour — and the fallback is guarded to still refuse cross-make
results and still attach Phase 244E's tiers. Degrading must not degrade the
safety property.

**The vocabulary was being derived from the wrong database.**
`index_makes_for_issue` derived its marque list by `db_path`, defaulting to the
configured production database, so writing to any other database indexed it
against production's vocabulary — the write path and the read path could
disagree about what a marque is. Now derived from the connection in hand, which
makes the disagreement impossible rather than unlikely.

**The index is order-dependent until the corpus is complete, and that is
structural.** The vocabulary is a function of the *whole* corpus, so a row
inserted before the entry that establishes a marque cannot index against it. A
rebuild after seeding produced more rows than the inserts had. `rebuild_make_index`
is therefore the authoritative pass and `db init` runs it once loading finishes;
incremental indexing on insert is a convenience, not the contract. **A derived
vocabulary means the derivation is only correct over a complete corpus** — worth
stating, because nothing about the incremental path looks wrong while it is
being wrong.

**One guard could not be written honestly, and says so.** The fallback is scoped
to junction errors so an unrelated SQL failure cannot be absorbed into
silently column-matched results. That scoping is **not behaviourally testable**:
the junction query and the fallback depend on the same columns, so any error one
hits the other hits too and both raise. Mutation testing proved the first
version of that guard passed with the condition deleted. It is now a source
assertion whose docstring states that the behaviour is unreachable and that the
structure is what is pinned — a guard that admits its reach beats one implying a
check it does not perform.

**My own fixture was unrepresentative, and the code was right.** Triumph and
Moto Guzzi initially appeared only inside the prose sentence, so the extractor
declined to treat them as marques. That is correct and conservative — the
vocabulary is what the corpus *establishes*, not what a sentence *mentions* —
and it is now a guard in its own right.

## Results

| Metric | Value |
|--------|-------|
| **LiveWire** | **0 → 24 entries** (25 with the wildcard) |
| **Damon** | **0 → 10 entries** |
| Zero / Energica / Triumph / Ducati | 17→27, 12→22, 55→62, 46→55 |
| Marque vocabulary | 26 raw column values → **16 real marques** |
| Orphaned issues | 0 |
| `make` column rewrites | **0 — the author's text is untouched** |
| Guards | 34 |
| Mutations run / caught | 7 / 7 (one after repairing a vacuous guard) |
| Regression | **6212 passed / 0 failed** (baseline 6178; +34 guards). First run **red, 16 failed** — 11 of them a silent-empty regression I introduced, see Deviations |

**Key finding: a column that holds prose cannot be queried, and the fix is not
to argue with the prose.** The `make` values were not mistakes to be corrected —
`All European makes` is a real editorial scope, and the sentence is a real
finding. What was missing was a key derived *beside* them. Nothing was rewritten,
so nothing was lost, and the junction can be rebuilt from the column at any time.

**And the vocabulary that fixes it comes out of the strings that caused it.**
LiveWire and Damon exist nowhere in the corpus as standalone makes; the only
reason they can now be resolved is that splitting the multi-marque strings —
the very strings that were hiding them — establishes them as marques.

## Follow-up recorded

**`All European makes` excludes Energica.** It is an Italian manufacturer but
ships in its own seed file rather than a `european_*` one, so the derivation
does not see it. Both affected entries concern valve-train work and ICE
diagnostic tooling, neither applicable to an electric machine, so the exclusion
is defensible — but it is an artefact of how the set is derived, not a judgment
about the marque.

**The `model` column has the same disease**, and Phase 244E only makes retrieval
survive it. 30.7% of entries carry prose there.
