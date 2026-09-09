# Phase 240C — Severity sorts backwards — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-09 | **Closed:** 2026-09-09
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-09 — Plan v1.0 written

Phase 240B's uncapped audit found that `ORDER BY severity DESC` on a TEXT
column sorts `medium, low, high, critical` — `critical` last — and deliberately
recorded it rather than fixing it, because it reorders every knowledge query in
the product. This phase fixes it.

**Step 0 — existing-code audit.** Three findings changed the shape of the work
before any code was written.

**1. It is six sites, not the three the audit named.** The sweep was by
**shape** (`grep` for every `ORDER BY … severity` in `src/`), not by name,
because a name-keyed sweep has missed family members three times on this
project. Beyond `knowledge/issues_repo.py:119,154,164` the same defect sits in
`advanced/recall_repo.py:361`, `inventory/recall_repo.py:52` and
`cli/advanced.py:2911`. `recalls.severity` carries the same four-value
vocabulary, so an open-recall list also returns the critical campaigns last —
a safety surface. Fixing only the named three would have left it broken.
`shop/analytics.py:417` was inspected and ruled **out** of scope: its
`severity ASC` is a determinism tiebreaker on a `GROUP BY` aggregate ordered by
count, not a priority claim.

**2. The naive fix silently reintroduces a performance regression the project
already paid to remove.** Migration 206 added
`idx_known_issues_sort ON known_issues(severity DESC, title)` precisely because
`EXPLAIN QUERY PLAN` showed `SCAN` + `USE TEMP B-TREE FOR ORDER BY`. A `CASE`
expression cannot use that index. Verified on a 917-row fixture:

```
CASE ordering, old index         -> SCAN known_issues
                                    USE TEMP B-TREE FOR ORDER BY
CASE ordering, expression index  -> SCAN known_issues USING INDEX idx_rank
```

So the fix needs migration 053 creating an index on the same expression the
query uses, and `SCHEMA_VERSION` 52 → 53. The index definition appears in
**three** places in `migrations.py` — the original 206 migration plus the two
table-rebuild migrations (051, 052) that drop and recreate it; missing one
leaves a database whose plan degrades silently after a rollback cycle.

**3. The mapping already exists eleven times.** The six broken SQL sites plus
five already-correct copies: `advanced/predictor.py:78` and `:821`,
`advanced/tsb_repo.py:63`, `engine/correlation.py:436`, and the inline SQL
`CASE` at `shop/issue_repo.py:440`. All five agree on
`critical: 4, high: 3, medium: 2, low: 1`. This phase adds one canonical
mapping and uses it in the six sites it fixes; it does **not** rewrite the five
correct ones, because that is a refactor this phase was not asked for and
touching working code inside a correctness fix is how regressions arrive. A
guard asserts the five agree with the canonical value so they cannot drift
while consolidation waits for its own phase.

**Correctness confirmed before planning**, on a 917-row fixture: lexicographic
ordering returns six `medium` rows first; ranked ordering returns six
`critical`. Nothing in the docs claims the lexicographic order was intended —
the only documented severity sort is `shop/issue_repo`'s, which is correct.

**Blast-radius spike in flight.** 73 test files assert on `results[0]`. A full
regression with the three knowledge sites changed is running to measure how
many actually encode the wrong order. Plan v1.0 is written without that number
rather than guessing it; it lands in v1.1 with each changed expectation
justified individually. Bulk re-baselining is explicitly forbidden for this
phase — a test that breaks for a *different* reason would otherwise hide in
the noise.

Plan v1.0 written to `docs/phases/in_progress/240C_implementation.md`.

---

## 2026-09-09 — Build complete

**The feared blast radius did not materialise; a different one did, and the
first version of these docs got it wrong.** Plan v1.0 carried Phase 240B's
"73 test files assert on `results[0]`" forward as if it sized the work. It did
not: the spike — three knowledge sites only — returned 5991 passed, identical
to baseline, because those files overwhelmingly filter to a single entry, use
single-severity fixtures, or assert on content.

**"Zero blast radius" then went into the docs before the full change had been
run once.** The complete change — six sites plus migration 053 — came back
**red with three failures**. The spike measured a third of the work and the
conclusion was generalised to all of it. That is recorded here in the form it
actually happened, not the flattering one.

**All six sites fixed** through one canonical `motodiag/core/severity.py`.
`SEVERITY_RANK_SQL` is built from `SEVERITY_RANK` rather than written out
twice, and it is shared with migration 053's index deliberately: SQLite only
uses an expression index when the `ORDER BY` expression matches the indexed one
textually, so a second hand-written copy would have silently cost the
optimisation.

**The five already-correct copies of the mapping were guarded, not rewritten.**
`advanced/predictor.py` (×2), `advanced/tsb_repo.py`, `engine/correlation.py`
and the inline SQL `CASE` in `shop/issue_repo.py` all agree on
`critical: 4, high: 3, medium: 2, low: 1`. Rewriting eleven call sites is a
refactor this phase was not asked for, and touching working code inside a
correctness fix is how regressions arrive. A test asserts they agree with the
canonical value, so they cannot drift while consolidation waits.

**Migration 053 exists because the obvious fix would have undone migration
206.** That phase added `idx_known_issues_sort` after measuring `SCAN` +
`USE TEMP B-TREE FOR ORDER BY`; a `CASE` expression cannot use it. 053 replaces
it with an index on the same expression, and the plan is back to
`SCAN known_issues USING INDEX idx_known_issues_sort`. The guard asserts the
**plan**, not the index definition — an index that exists but is not used is
worth nothing.

**Two bugs caught by the phase's own guards, both mine.** The first version of
053 was appended and *then* a global replace updated the remaining
lexicographic definitions — which reached into 053's own `rollback_sql` and
made the rollback a no-op. The rollback test failed on exactly that; redone
with the table-rebuild copies updated before 053 is appended. The shape guard
then fired on `migrations.py`, which legitimately holds the old form in
migration 049 and in 053's rollback; scoped out, with the live state covered by
the plan guard instead.

**Six test expectations changed, each justified, none re-baselined.** Five are
the deliberate `SCHEMA_VERSION` contract pins whose own `f9-noqa` annotations
say "bumping requires a corresponding new migration" — migration 053 is that
migration, and each rationale was extended with the reason. The sixth,
`test_phase235b_regulation_provenance.py`, pinned
`apply_pending_migrations(...) == [52]`: a constant list any later migration
breaks. Rewritten to assert what the test is about — that 052's rebuild
survives a live foreign-key child and the database lands at `SCHEMA_VERSION`.

**The three failures, and what each one was.**

1. **A bug this phase introduced.** Substituting the rank expression in
   `advanced/recall_repo.py` dropped the `ORDER BY` keyword — it was inside
   the matched text and the replacement did not restore it. The resulting SQL
   was malformed, and `list_open_for_bike` wraps its query in
   `except sqlite3.OperationalError: return []` to degrade gracefully on a
   pre-migration database, so the syntax error surfaced as "no open recalls
   for this bike" instead of raising. On a recall lookup that is the worst
   available failure mode. Phase 155's test caught it. **This phase's own
   guards did not** — the recall ordering test covered
   `inventory/recall_repo.py` and not this one. Gap closed with a guard that
   asserts the result is non-empty before asserting its order, mutation-tested
   by re-dropping the keyword.
2. **`test_phase206_performance.py`** hardcoded `ORDER BY severity DESC,
   title`. Correct at the time, but a constant standing in for an invariant:
   once the ordering moved to a `CASE` rank and 053 reindexed on that
   expression, it was measuring a query the product no longer issues. Verified
   first that all three real query shapes use the new index and only the
   retired text does not, then rewired it to the shared constant.
3. **`test_phase235b_regulation_provenance.py`** pinned
   `apply_pending_migrations(...) == [52]` — a constant list any later
   migration breaks.

Two of the three were the constant-for-invariant family, in tests written by
earlier phases. The third was mine.

**Four mutation scenarios, all caught:** reverting the ordering fails the
ordering and shape guards; dropping the expression index fails both plan
guards; perturbing one of the five correct copies fails the drift guard.

**A process error, recorded because the working agreement asks for it.** One
mutation test reverted `migrations.py` with `git checkout --` instead of a file
backup. Only the plan docs were committed at that point, so it discarded the
migration work and it had to be redone. The other two mutations used `cp`
backups and were unaffected.

**Product-visible behaviour change.** `predictor`, `core/search` and
`cli/diagnose` all consume `search_known_issues`, so what a diagnosis surfaces
first changes — that is the fix, and it is stated here as a behaviour change
rather than buried as an implementation detail. Recall listings likewise now
put critical campaigns first.

15 new guards. F9 lint clean. Regression ****6007 passed / 0 failed** (baseline 5991; +16 guards. First run was red with 3 failures — see Deviations)**.
