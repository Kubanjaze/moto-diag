# Phase 240C — Severity sorts backwards — phase log

**Status:** Planned
**Opened:** 2026-09-09

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
