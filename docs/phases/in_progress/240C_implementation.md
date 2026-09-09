# Phase 240C — Severity sorts backwards: `critical` comes back last

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-09

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

- [ ] All six sites ordered by the canonical rank; zero `ORDER BY severity`
      on a TEXT column left in `src/`
- [ ] A shape guard fails if a seventh site reintroduces the pattern
- [ ] Migration 053 creates the expression index; all three definitions in
      `migrations.py` updated
- [ ] `EXPLAIN QUERY PLAN` guard asserts the known-issues sort uses an index,
      so the 206 optimisation cannot silently regress again
- [ ] `SCHEMA_VERSION` 52 → 53 and Gate 12's pin updated
- [ ] Ordering asserted end-to-end through the real front doors, not the repo
      layer — `critical` before `high` before `medium` before `low`
- [ ] The five already-correct copies asserted to agree with the canonical rank
- [ ] Migration rollback tested: 053 down then up leaves the correct index
- [ ] Every new guard mutation-tested
- [ ] Full regression green, with every changed expectation explained

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
