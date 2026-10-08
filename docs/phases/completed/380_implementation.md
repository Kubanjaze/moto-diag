# Phase 380 — Row identity and the junction per make

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-08 (v1.0 the same day)

---

## Goal

Section C of the 2026-10-08 open-findings triage. **F129:** a known-issue
row's identity was its prose `(make, model, title)`, so correcting any of
the three duplicated the row on a re-seed. **F142:** a multi-make row put
every model under every make in the junction. Then the content batch, which
waited for F129.

The operator's choices (verbatim in the log): **1A, 2A, 3A**, and:
- with 1A, a test fails on any seed entry with no key or a duplicate key;
- with 2A, each content migration's dry run shows that the changed rows
  equal a fresh seed build, by key, so the seed and live cannot drift;
- 379's plural fix stays (F200 covers words with two meanings).

## Logic

### F129 (1A, 2A)

- **The key.** Every seed entry gets a `"key"`, generated once and then
  frozen: the first make's slug and the title's slug (ASCII, lowercase,
  hyphens, at most 60 characters at a word break), with `-2`, `-3` … for a
  repeat, in file and entry order.
- **The generator** is `380_add_keys.py`, committed in the phase folder
  (K24). It inserts one line before each entry's `"title"` line, at the
  same indent, and checks:
  - the file parses to the old data plus the key;
  - the diff is exactly one added line per entry.
- **Migration 085** (schema 84 → 85):
  - `known_issues.row_key TEXT`;
  - a `post_apply` that fills it: from the seed entry with the same
    `(make, model, title)`, else (a row no seed holds) a derived
    `auto-<sha1 of make|model|title>`;
  - the unique index `idx_known_issues_row_key`, which replaces the prose
    `idx_known_issues_identity`;
  - the rollback restores the prose index and drops the column.
- **`add_known_issue(key=…)`:**
  - the seed loader passes the entry's key;
  - a caller with no key gets the derived key, so a keyless caller keeps
    the old `(make, model, title)` semantics;
  - insert-only (`ON CONFLICT DO NOTHING`), as 2A says;
  - a duplicate resolves its id by key.
- **`update_known_issue_by_key(conn, key, fields)`** is the pattern a
  content migration uses. The past migrations' prose-keyed hooks
  (`reconcile_255B_rows`, `backfill_row_applicability`) stay as they are:
  they run at their own schema, before the column exists.

### The parity check (2A's condition)

- `deploy.py`'s dry run and `apply-live` compare every `known_issues` row
  the migration adds or changes with the row of the same `row_key` in a
  fresh seed build at HEAD: a scratch database, `init_db`, every seed file
  loaded, the junctions rebuilt.
- They compare every column but `id`, `created_at` and `updated_at`. A
  difference is a scope problem, so the dry run records it and the apply
  refuses.
- It runs only when the copy has `row_key`.
- For 085 itself, all 1060 rows change, by gaining a key, and each must
  equal the fresh build.

### F142 (3A)

- `vocabulary_from_conn` gains a rung before its fallback. A token on a
  multi-marque row that the transmission lookup places under one of the
  row's marques belongs to that marque.
- The fallback (every marque in the row) remains for the rest. That is
  3A's list, pinned in a test that it may only shrink.
- Migration 085's `post_apply` rebuilds the junction.
- Step 0 measured 104 junction rows leaving (a model under a make not its
  own), with the lookup and single-make evidence combined. The build
  re-measures with the real rung, and the dry run shows the exact rows.

### Live

One migration, 085: the key on all 1060 rows, and the junction rows that
move. It changes existing live rows, so after the regression of record its
dry-run diff goes to the operator, and the apply waits for their words.

### Then the content batch

It runs after 085 is live, on the key, one migration per finding (F152,
F153, F156, F149, F164 and F171, F158). Each has its dry run with the
parity check, and each is a stop. **Moved to Phase 381** by the operator
(2026-10-08), in a fresh session; see Deviations.

## Tests

- **Seed keys:** every entry has one; none repeats; the shape
  `^[a-z0-9]+(-[a-z0-9]+)*$`. Known-bad fixtures: a file with a missing key
  and one with a repeated key.
- **F129's measured case:** a title, make or model edited in a seed and
  re-seeded does not add a row.
- **Migration 085:**
  - every row keyed and unique;
  - a row no seed holds gets `auto-`;
  - the rollback;
  - the post_apply on a database holding rows.
- **Parity:**
  - a stand-in content migration that writes what the seed says passes;
  - one that writes otherwise is a scope problem;
  - apply-live refuses it.
- **F142:**
  - no model the lookup places appears under another make in the
    junction;
  - the unassigned list equals its pin;
  - Energica's `Ego` is not under Harley-Davidson.
- Mutations in `380_mutate.py`.

## Non-goals

The 37 unassigned models' makes (3A keeps them; Step 0 estimated 35); the content batch (Phase 381); F135 (what a "model"
is); rewriting past migrations' hooks.

## Planned items

- [x] keys in the seed, the generator, the seed-key test and fixtures
- [x] migration 085, `add_known_issue(key=)`, `update_known_issue_by_key`
- [x] the parity check in deploy.py
- [x] F142's rung and the pin
- [x] tests, mutations, the floor, the regression
- [x] 085's dry run, shown to the operator; the apply on their words
- [x] the content batch: moved to Phase 381 by the operator, not done here
- [x] the close-out, the handoff

## Deviations

- **The content batch moved to Phase 381.** The operator, 2026-10-08:
  "Close 380 now with F129 and F142 … The content batch becomes its own
  phase, 381, in a fresh session; don't start it here." 380 ships the
  substrate it needs: the key, `update_known_issue_by_key`, and the parity
  check.
- **F142's evidence** includes a single-make row's token with its marque
  stripped ("Energica Ego" owns "ego"); without it only 19 junction rows
  moved. 109 leave, 0 added; 37 unassigned, not 35 (log, D1).
- **085 syncs the junction rather than rebuilding it**
  (`sync_model_index`), so rowids that stay are kept (D2).
- **The scope was generated from the seed** (`380_scope.py`), with a
  `"to"` for every row's key, which found bug fix #1 in `deploy.diff`.
- **Six pins moved** with the change (D6 and the 244U count).
- **F201 was filed** at the operator's word: "Piaggio LX50" reaches 0 of
  the 7 scooter CVT rows, before and after 085.

## Results

- **Seed:** 1060 keys in 110 files, distinct, inserted lines only.
- **Live (migration 085, the operator's words verbatim in the log):**
  1060 rows keyed, 109 junction rows removed, the key index in place.
  Equals the approved exact diff; `verify-live 380` exit 0; integrity and
  foreign keys ok. Live 5866 → 5758 rows.
- **Tests:** four new files (26 tests), 11/11 mutations, 244G 0 hits,
  floor 10769 → 10798.
- **Bug fix #1:** the deploy diff lines both sides up on the union of the
  two column lists (`ad7aceb`).
- **Regression of record:** 10798 passed, 0 failed at `9530473`.
