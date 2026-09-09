# Phase 240C — Severity sorts backwards: `critical` comes back last

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

Fix the defect Phase 240B's uncapped audit found and deliberately did not fix:
six query paths order results by `severity DESC` on a **TEXT** column, so
SQLite sorts them lexicographically and returns

```
medium, low, high, critical
```

`critical` comes back **last** on every one of them. On the knowledge paths
this means a `medium`-rated stale entry outranks the `high`- and
`critical`-rated entry written to correct it — which is the mechanism behind
Track K's whole contradiction pattern. On the recall paths it means an
open-recall list puts the critical campaigns at the bottom.

This is unambiguously a defect rather than a design choice: five other places
in the same repository map severity to a numeric rank correctly, and nothing in
the docs claims the lexicographic order is intended.

CLI: no new commands. Behaviour of existing commands changes — `kb search`,
`kb symptom`, `kb dtc`, `diagnose`, `advanced recalls` and the recall lookups
now return worst-first.

Outputs:
- corrected ordering on 6 query sites across 4 modules
- one canonical severity rank (Python + SQL) replacing 6 inline copies
- migration 053 + `SCHEMA_VERSION` 52 → 53 (expression index)
- `tests/test_phase240c_severity_ordering.py`

## Logic

### The six sites (found by shape sweep, not by name)

| module | line | query | index? |
|---|---|---|---|
| `knowledge/issues_repo.py` | 119 | `search_known_issues` | **yes** |
| `knowledge/issues_repo.py` | 154 | `find_issues_by_symptom` | no |
| `knowledge/issues_repo.py` | 164 | `find_issues_by_dtc` | no |
| `advanced/recall_repo.py` | 361 | open recalls for a vehicle | no |
| `inventory/recall_repo.py` | 52 | recall lookup | no |
| `cli/advanced.py` | 2911 | `recalls` listing | no |

Phase 240B named only the first three. The sweep was by **shape** — every
`ORDER BY … severity` in `src/` — because a name-keyed sweep has missed family
members three times on this project. Fixing three of six would leave the
safety-relevant recall path broken.

`shop/analytics.py:417` (`ORDER BY n DESC, i.category ASC, i.severity ASC`) is
**not** in scope: that is a determinism tiebreaker on a `GROUP BY` aggregate
ordered primarily by count, not a priority claim.

### The index problem, which the audit did not mention

Migration 206 added `idx_known_issues_sort ON known_issues(severity DESC,
title)` *specifically* because `EXPLAIN QUERY PLAN` showed `SCAN` +
`USE TEMP B-TREE FOR ORDER BY` — "every listing sorted the whole table to
return 50". A `CASE` expression cannot use that index, so the naive fix
silently reintroduces the regression that migration was written to remove.

Measured on a 917-row fixture:

```
CASE ordering, old index         -> SCAN known_issues
                                    USE TEMP B-TREE FOR ORDER BY
CASE ordering, expression index  -> SCAN known_issues USING INDEX idx_rank
```

So migration 053 creates an index on the **same expression** the query uses.
SQLite here is 3.53.2, far past the 3.9.0 that expression indexes need.

The index definition appears in **three** places in `migrations.py` — the
original 206 migration and the two table-rebuild migrations (051, 052) that
drop and recreate it. All three need the new form, or a rollback-then-upgrade
cycle restores the old index and the query silently loses its plan.

### One canonical rank, not a seventh copy

The mapping `critical: 4, high: 3, medium: 2, low: 1` already exists **eleven**
times: the 6 broken SQL sites plus 5 already-correct copies
(`advanced/predictor.py:78` and `:821`, `advanced/tsb_repo.py:63`,
`engine/correlation.py:436`, `shop/issue_repo.py:440`).

This phase adds a canonical `SEVERITY_RANK` (dict) and `SEVERITY_RANK_SQL`
(the `CASE` expression derived from it) and uses them in the six sites it
fixes. It does **not** rewrite the five correct copies — that is a refactor
this phase was not asked for, and touching working code inside a correctness
fix is how regressions arrive. Instead a guard asserts the five agree with the
canonical mapping, so they cannot drift while consolidation waits for its own
phase.

`ELSE 0` matches the existing house pattern at `shop/issue_repo.py:440`.
Neither `known_issues.severity` nor `recalls.severity` carries a CHECK
constraint (both are `TEXT NOT NULL DEFAULT 'medium'`), so an unrecognised
value is possible and sorts below `low`.

## Key Concepts

- **Lexicographic vs. semantic ordering.** `ORDER BY severity DESC` on TEXT is
  reverse-alphabetical. The four values happen to alphabetise into almost
  exactly the wrong order, which is why this survived: the results always
  looked plausibly sorted.
- **Expression indexes.** SQLite can index an expression, but the index is
  only usable when the query's `ORDER BY` expression matches the indexed one
  textually. The constant is therefore shared between the query and the
  migration rather than written twice.
- **Sweep by shape, not by name.** The audit named three sites; the defect had
  six.
- **Constant-for-invariant.** The new guards assert the *property* (a
  `critical` row precedes a `medium` row through the real API) rather than
  pinning a row order.
- **Mutation-test every gate.** Reintroduce the lexicographic sort, confirm
  each guard fails, revert.

## Verification Checklist

- [x] All six sites ordered by the canonical rank; zero `ORDER BY severity`
      on a TEXT column left in `src/`
- [x] A shape guard fails if a seventh site reintroduces the pattern
- [x] Migration 053 creates the expression index; all three definitions in
      `migrations.py` updated
- [x] `EXPLAIN QUERY PLAN` guard asserts the known-issues sort uses an index,
      so the 206 optimisation cannot silently regress again
- [x] `SCHEMA_VERSION` 52 → 53 and Gate 12's pin updated
- [x] Ordering asserted end-to-end through the real front doors, not the repo
      layer — `critical` before `high` before `medium` before `low`
- [x] The five already-correct copies asserted to agree with the canonical rank
- [x] Migration rollback tested: 053 down then up leaves the correct index
- [x] Every new guard mutation-tested
- [x] Full regression green, with every changed expectation explained

## Risks

- **Blast radius is the whole point and is not yet known.** 73 test files
  assert on `results[0]`. A spike applying the fix to the three knowledge sites
  is running to measure it. Any test that breaks is doing so because it encoded
  the wrong order — but each one must be read individually, because a test that
  breaks for a *different* reason would be hidden in the noise.
- **A changed expectation can hide a real regression.** Every test that needs
  updating will be inspected and its change justified in the phase log. Bulk
  re-baselining is forbidden here.
- **The index is recreated in table-rebuild migrations.** Missing one leaves a
  DB whose plan silently degrades after a rollback cycle.
- **Schema bump touches the gate.** Gate 12 pins `SCHEMA_VERSION == 52`;
  the pin moves to 53. If any other test pins 52, it must move too.
- **Ranking changes diagnostic output.** `predictor`, `core/search` and
  `cli/diagnose` all consume `search_known_issues`, so this changes what a
  diagnosis surfaces first. That is the intended fix, but it is a
  product-visible behaviour change and belongs in the phase log as one.
- **`ELSE 0` is a judgement call.** An unrecognised severity sorts below `low`
  rather than being surfaced. It matches the house pattern; noted so a later
  phase can revisit it deliberately.

---

## Deviations from Plan

**The feared blast radius did not materialise; a different one did.** Plan
v1.0 carried "73 test files assert on `results[0]`" forward from Phase 240B's
audit as though it sized the work. It does not — it counts files that *could*
be order-sensitive, and the spike (the three knowledge sites only) returned
5991 passed, identical to baseline. Almost all of those 73 files filter to a
single entry, use single-severity fixtures, or assert on content rather than
order.

**But "zero blast radius" was written into these docs before the full change
had ever been run, and it was wrong.** The complete change — six sites plus
migration 053 — produced **three failures**. One was a bug this phase
introduced; two were tests pinning constants that the fix legitimately moved.
The spike measured a third of the change and the conclusion was generalised to
all of it. Recorded plainly rather than in the flattering form.

**Six sites, not the three the audit named** — established in Step 0 and
carried into plan v1.0, so not a deviation from the plan, but worth restating
as the reason this phase is not a one-line change.

**My own test caught a bug I introduced in the migration.** The first version
of migration 053 was appended to `migrations.py` and *then* a global replace
updated every remaining lexicographic index definition to the expression form
— which reached into 053's own `rollback_sql`, making the rollback a silent
no-op. `test_rollback_then_upgrade_restores_the_expression_index` failed on
exactly that. Redone with the two table-rebuild copies updated **before** 053
is appended, so the replace cannot reach it.

**The shape guard needed scoping, and the scoping needed justifying.** It fired
on `core/migrations.py`, which legitimately contains the old index form in
migration 049 (the original) and in 053's rollback. `migrations.py` is DDL
history, not a live query path, so it is skipped — and the live state is
covered instead by a guard that asserts the query **plan**, not the file text.
An index that exists but is not used would be worth nothing.

**One test expectation changed for a reason unrelated to ordering.**
`test_phase235b_regulation_provenance.py` asserted
`apply_pending_migrations(...) == [52]` — a constant list that any later
migration breaks. That is the constant-for-invariant family again. Rewritten to
assert what the test is actually about: migration 052's table rebuild survives
a live foreign-key child, and the database lands at `SCHEMA_VERSION`.

**A process error worth recording.** For one mutation test I reverted
`migrations.py` with `git checkout --` rather than a file backup. Only the plan
docs were committed at that point, so it discarded all the migration work and
it had to be redone. The other two mutations used `cp` backups and were
unaffected.

**I broke a query, and it failed silently.** Substituting the rank expression
in `advanced/recall_repo.py` dropped the `ORDER BY` keyword — it was part of
the matched text and the replacement did not restore it. That left malformed
SQL, and `list_open_for_bike` wraps its query in
`except sqlite3.OperationalError: return []` to degrade gracefully on a
pre-migration database, so a syntax error became "no open recalls for this
bike". On a recall lookup that is the worst available failure mode. Phase 155's
test caught it; **this phase's own guards did not**, because the recall
ordering test covered `inventory/recall_repo.py` and not this one. That gap is
closed with a guard that asserts non-empty before it asserts order, and it is
mutation-tested.

**Phase 206's performance test failed, and correctly.** It hardcoded
`ORDER BY severity DESC, title` — the query at the time, but a constant
standing in for an invariant. Once the ordering moved to a `CASE` rank and
migration 053 reindexed on that expression, the test was measuring a query the
product no longer issues. Verified before changing it that all three real query
shapes (bare, `WHERE 1=1` + `LIMIT`, and `make LIKE` + `LIMIT`) use the new
index, and only the retired text does not. It now takes the expression from the
same constant the repository uses.

## Results

| Metric | Value |
|--------|-------|
| Defective query sites found by shape sweep | **6** (audit named 3) |
| Sites fixed | 6 of 6 |
| Copies of the mapping in the tree | 11 (6 fixed, 5 guarded against drift, 0 rewritten) |
| Blast radius — spike (3 knowledge sites) | 0 test changes (5991, == baseline) |
| Blast radius — full change (6 sites + migration) | **3 failures**: 1 bug introduced, 2 constant-for-invariant tests |
| Test expectations changed | 8 — five deliberate schema pins, three constant-for-invariant |
| Migration | 053, index-only, no data touched |
| `SCHEMA_VERSION` | 52 → 53 |
| Query plan after fix | `SCAN known_issues USING INDEX idx_known_issues_sort` (no temp B-tree) |
| New guards | 15 |
| Mutation scenarios | 3, all caught |
| Regression | **6007 passed / 0 failed** (baseline 5991; +16 guards. First run was red with 3 failures — see Deviations) |

**Key finding: the fix that restores correctness can silently undo an
optimisation, and only the query plan will tell you.** Changing
`ORDER BY severity DESC` to a `CASE` rank is correct and looks complete — but
`idx_known_issues_sort` exists precisely because migration 206 measured
`SCAN` + `USE TEMP B-TREE FOR ORDER BY` and removed it. A `CASE` expression
cannot use that index, so the obvious fix would have quietly restored the
regression a previous phase paid to eliminate, with every test green. The guard
that matters here asserts the **plan**, not the index definition.
