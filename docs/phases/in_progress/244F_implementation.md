# Phase 244F — A make column that holds prose cannot be queried

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

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

- [ ] `make = 'LiveWire'` reaches all 24 LiveWire entries
- [ ] `Damon` reaches its 10 entries
- [ ] An entry tagged `BMW, Ducati, KTM, MV Agusta` is reachable from each of the four
- [ ] `All makes` entries reach any make queried
- [ ] `All European makes` reaches the seven European marques and **not** Honda
- [ ] The prose sentence's six marques are all reachable
- [ ] The marque vocabulary is derived from the corpus, with no hard-coded marque list
- [ ] `known_makes()` returns marques, not raw column values
- [ ] Re-seeding twice leaves the junction table unchanged
- [ ] No make gains an entry that does not name it
- [ ] Phase 244E's monotonicity invariant still holds corpus-wide
- [ ] Mutation: hard-code the vocabulary → a guard fails
- [ ] Mutation: drop the wildcard handling → a guard fails
- [ ] Full regression green

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
