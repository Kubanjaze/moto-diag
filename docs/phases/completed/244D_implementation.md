# Phase 244D — The corpus is stored ten times over, and a naive constraint would not fix it

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

`known_issues` holds **6,600 rows for 660 distinct issues** — every entry
present exactly ten times. There is no uniqueness constraint on the table and
`loader.load_known_issues_file` performs a plain INSERT per entry, so every run
of the seed loop duplicates the whole corpus.

**This is not cosmetic.** It silently degraded a live guidance run at Phase
244C: a request for 20 corpus rows returned **two distinct facts repeated ten
times**, and the model correctly reported that the corpus covered only "fuel
injector issues and float bowl fuel leaks". Retrieval that looks like breadth
is actually a single fact wearing ten hats.

## Step 0 findings — three of them change the design

**1. The seed files are clean, so the key is real.** 970 entries across 100
files, **970 distinct `(make, model, title)`**, zero internal collisions. The
duplication is entirely a load-time defect, and `(make, model, title)` is a
sound uniqueness key — verified, not assumed. (The 100 further files under
`build/lib/` are a build artifact and are not loaded.)

**2. A naive `UNIQUE(make, model, title)` would silently fail on 4.4% of the
corpus.** **43 entries — 430 rows — have `model IS NULL`**, and SQLite treats
NULLs as *distinct* in a UNIQUE constraint. Demonstrated:

| index | inserting the same NULL-model row 3× | rows |
|---|---|---|
| `UNIQUE(make, model, title)` | `INSERT OR IGNORE` | **3** |
| `UNIQUE(make, COALESCE(model,''), title)` | `INSERT OR IGNORE` | **1** |

So the constraint must be a **unique expression index over
`(make, COALESCE(model,''), title)`**. A plain column constraint would ship
looking correct while those 43 entries kept multiplying on every re-seed —
precisely the class of silent defect this phase exists to end.

**3. The local database is stale, not merely duplicated.** It holds 660 of the
970 seeded entries and only five makes — Harley-Davidson, Honda, Kawasaki,
Suzuki, Yamaha. Every European and electric make from Tracks K and L is absent.
So the dedup migration must be correct on a database that is *behind* the seed
corpus, and re-seeding after it must be safe and complete.

## Non-goals

- **Not re-seeding as part of the migration.** The migration deduplicates what
  is there. Loading the missing 310 entries is an operator action, made safe by
  the idempotent loader this phase delivers.
- **Not cleaning the `make` vocabulary.** The audit found the column carries
  multi-make strings and, in one case, a full sentence
  (`"BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia, Moto Guzzi have none"`).
  That is a real defect affecting Phase 244C's resolver vocabulary, and it is
  recorded as separate work rather than smuggled in here.

## Logic

**Migration 054.** SQLite cannot add a constraint in place, so the table is
rebuilt, following migration 052's precedent on this same table:

1. Create `known_issues_dedup` with the current column set.
2. `INSERT ... SELECT` keeping **`MIN(id)` per key**, grouped by
   `(make, COALESCE(model,''), title)` — lowest id wins, so the earliest load
   survives and ids stay stable for anything referencing them.
3. `DROP` the original, `RENAME` the new one.
4. Recreate `idx_known_issues_make_model` **and `idx_known_issues_sort` in its
   Phase 240C expression form** — `CASE severity WHEN 'critical' THEN 4 ...`.
   Recreating the pre-240C `severity DESC` form would silently undo migration
   053: SQLite only uses an expression index when the ORDER BY expression
   matches it exactly, so the optimisation would be lost without any error.
5. Create the unique expression index.

Rollback drops the unique index and restores the plain table. **Rollback cannot
restore the deleted duplicates, and the migration's description must say so** —
a rollback that silently loses rows while claiming to reverse is worse than one
that admits it.

**Idempotent loader.** `add_known_issue` gains an `on_conflict` path so
`load_known_issues_file` uses `INSERT ... ON CONFLICT DO NOTHING`. The return
value becomes rows *actually inserted*, which equals rows processed on a fresh
database and is truthful on a repeat load.

**Test-surface check.** 219 loader call sites across the suite, all building a
fresh `tmp_path` database and loading each file once; no test asserts that
duplicates are created. Since no two seed files collide on the key, idempotent
loading is invisible to them.

## Key Concepts

- **NULL is not a value, and SQLite means it.** The whole difference between a
  fix and the appearance of one is `COALESCE`.
- **A table rebuild must re-declare every index it inherits.** Migration 053's
  index is an *expression* index; recreating its older form would cost the
  optimisation without failing.
- **Keep the lowest id.** Dedup that keeps an arbitrary row churns ids for no
  reason.
- **Idempotency belongs at the write, not the caller.** Guarding the seed script
  would leave every other path able to duplicate.

## Verification Checklist

- [x] Migration 054 reduces the live corpus 6,600 → 660 with no distinct entry lost
- [x] Every surviving row is the lowest-id member of its key group
- [x] `idx_known_issues_sort` exists afterwards in its 240C **expression** form
- [x] `EXPLAIN QUERY PLAN` still reports the index for a severity-ordered listing
- [x] Rows with `model IS NULL` are deduplicated (the case a naive constraint misses)
- [x] Loading the same file twice leaves the row count unchanged
- [x] Loading all 100 seed files twice leaves the row count unchanged
- [x] Mutation: swap the unique index for the naive column form → a guard fails
- [x] Mutation: recreate the pre-240C sort index → a guard fails
- [x] Full regression green

## Risks

- **A rebuild on this table has bitten before.** At Phase 240C a global replace
  rewrote migration 053's own `rollback_sql`, turning a rollback into a no-op.
  Edits here touch only the new migration; existing entries are left alone and
  the file is diffed before commit.
- **Destructive by nature.** The migration deletes 5,940 rows. They are exact
  duplicates by the key, but the dedup query is asserted against a fixture with
  known contents before it runs anywhere else.
- **`ON CONFLICT` requires the conflict target to exist.** On a database at a
  schema version before 054 the unique index is absent, so the loader must not
  assume it. `INSERT OR IGNORE` degrades safely to a plain insert where no
  constraint exists, which is the correct behaviour on an un-migrated database.
- **The stale local database may hide a defect.** It is missing 310 entries, so
  a migration that is correct there is not thereby correct on a full corpus.
  Guards run against a fixture built from the seed files, not against `data/`.

---

## Deviations from Plan

**The plan's idempotency mechanism was wrong, and the regression caught it.**
v1.0 specified `INSERT OR IGNORE`. That spelling suppresses **every**
constraint violation, not only uniqueness — CHECK included. So a typo in
`source` (`"servicemanual"` for `"service-manual"`) would have been **dropped
in silence** rather than raising, losing the row and its provenance with no
signal at all.

Provenance vocabulary is load-bearing across Track K, and two phases already
pin it: `test_the_check_rejects_a_typo` in Phase 211 and Phase 235B. Both went
red. Verified all three spellings against a CHECK constraint before choosing:

| statement | duplicate | invalid CHECK value |
|---|---|---|
| `INSERT OR IGNORE` | ignored ✓ | **silently swallowed** ✗ |
| plain `INSERT` | raises ✗ | raises ✓ |
| `ON CONFLICT DO NOTHING` | ignored ✓ | raises ✓ |

`ON CONFLICT DO NOTHING` conflicts only on uniqueness. **The phase's own 21
guards did not catch this** — they tested uniqueness thoroughly and never the
interaction with a neighbouring constraint. Four guards added, mutation-verified.

**The uniqueness key gained a `COALESCE` on `make` as well as `model`.** The
plan specified `(make, COALESCE(model,''), title)`. No seeded entry has a NULL
make today, but the asymmetry was arbitrary and would have re-opened the exact
hole on `make` the moment one appeared. Both columns are coalesced.

**The loader's return value was a lie for one build.** Made idempotent, it kept
counting *items walked* rather than rows inserted, so a repeat load still
reported the file's full length. It now measures the table before and after —
identical on a fresh database, and on a re-seed the difference is the entire
point. Caught by inspection rather than by a guard, which is worth noting: a
re-seed reporting "970 inserted" while inserting nothing would have looked
exactly like success.

**Four schema-version contract pins required updating** — Gates 9, 11, 12 and
Phase 191B. These are deliberate two-source assertions whose comments state
that the literal is the point, and they behaved correctly: they stopped the
bump and demanded confirmation that a migration accompanied it. F9 lint then
flagged that this phase's *own* pin lacked its `contract-pin` marker.

## Results

| Metric | Value |
|--------|-------|
| Live corpus | **6,600 → 660 rows**, 660 distinct — nothing lost |
| NULL-model rows | 430 → **43** (the case a naive constraint misses) |
| Ids | exactly `MIN(id)` per key, verified as a set |
| `idx_known_issues_sort` | preserved in 240C **expression** form; plan still `SCAN … USING INDEX` |
| Seed loading | 970 / **0** / **0** across three consecutive passes |
| Guards | 21 |
| Mutations run / caught | 6 / 6 |
| Regression | **6161 passed / 0 failed** (baseline 6140; +21 guards). First run **red, 9 failed** — one real bug, see Deviations |

**Key finding: idempotency and integrity are not the same property, and the
cheapest way to get the first silently costs the second.** `INSERT OR IGNORE`
reads as "skip duplicates" and in fact means "skip anything the database
objects to". The distinction is invisible in every test that only inserts valid
rows — which was every test this phase wrote. It took two guards from other
phases, written for an unrelated reason, to expose it.

## Follow-up recorded

**Re-seeding is now safe but has not been done.** The database holds 660 of the
970 seeded entries and five of fourteen makes; every European and electric make
from Tracks K and L is absent. That is an operator action, deliberately outside
the migration.

**The `make` column is not a marque vocabulary.** 38 entries (3.9%) carry
multi-make strings, one of them a full sentence. It is not evenly spread:
**LiveWire and Damon have no standalone entries at all** — all 24 LiveWire rows
are tagged `"Harley-Davidson, LiveWire"`, so Phase 243's entire output is
unreachable by make. Invisible today because those rows are not loaded; it
begins to matter the moment the corpus is re-seeded.
