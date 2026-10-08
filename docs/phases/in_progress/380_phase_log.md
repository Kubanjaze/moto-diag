# Phase 380 — Row identity, the junction per make, then the content batch — phase log

**Status:** 🚧 Step 0, stopped for the operator (2026-10-08)
**Branch:** `phase-380` (Opus session, main checkout)

---

### 2026-10-08 — Opened, Step 0, and the stop

The operator: "then 380 = F129 + F142, then the content batch." The
prompt is `docs/prompts/380_row_identity_and_content.txt`. Row 380 went 🚧
before Step 0.

`380_step0.md`:
- **F129:** live and seed match one to one on `(make, model, title)`, 1060
  each.
- **F142:** of 125 models in multi-make rows, 90 have their own make on
  disk and 35 do not; assigning the 90 removes 104 junction rows.

Q1 (F129's key) and Q3 (F142's unassigned models) are real forks: each
option ships different behaviour. Q2 decides whether content edits stay
reviewed migrations. Stopped for the operator, with recommendations 1A,
2A, 3A.

**The operator's choices, verbatim (2026-10-08), in this session:**

> 380: 1A, 2A, 3A. With 1A, a test fails on any seed entry with no key or a
> duplicate key. With 2A, each content migration's dry run shows the changed
> rows equal a fresh seed build, by key, so the seed and live can't drift.
> Keep 379's plural fix; F200 covers the words with two meanings.

**Measured before v1.0, for 2A's condition:** live equals a fresh seed
build exactly. On the live copy and a fresh build, all 1060 rows match by
`(make, model, title)`, and every content column is equal. So the parity
check starts true, and any later difference is drift.

**Seed formatting:** 41 of the 110 `known_issues_*.json` files round-trip
through `json.dumps(indent=2)` byte for byte. The other 69 are
hand-formatted, with arrays on one line. So keys are inserted as one line
before each entry's `"title"` line, never by re-serialising a file.

### 2026-10-08 — The build

- **The keys.** `380_add_keys.py` keyed 1060 entries in 110 files; 1060
  distinct, none needing a suffix, longest 81 characters. A second run
  refuses.
  - Its first run wrote 27 files and stopped on the one compact file
    (`known_issues_european_parts.json`, an object per line). That was the
    phase's own new script, before any commit, so it is not a register
    entry. The 27 were restored with `git checkout` (uncommitted, this
    phase's own), and the script now checks every file before writing any.
  - The check: deleting the inserted text gives back each file's original
    bytes.
- **085:** `row_key` keyed from the seed (all 1060 on a live copy, 0
  `auto-`), the prose identity index replaced, and the junction synced.
- **`add_known_issue(key=)`**, `derived_row_key` for keyless callers, and
  `update_known_issue_by_key` for the content batch.
- **2A's parity check** in `deploy.py`.
- **F142:** the lookup rung and `_owned_names`.

**Decisions taken while building, not stops:**
- **D1. F142's evidence** is the lookup and a single-make row's token with
  its own marque stripped ("Energica Ego" owns "ego").
  - Without the stripping only 19 junction rows moved, and Energica's Ego
    stayed under three other makes.
  - With it, **109 leave and none are added**, and the migrated junction
    equals a fresh seed build's, pair for pair.
  - 3A's unassigned list is **37** (Step 0 estimated 35, with a looser
    rule).
  - 9 `LX50` pairs leave Piaggio, because the lookup files the LX under
    Vespa, and the marque vocabulary does not count the two as one family.
- **D2. `sync_model_index`:** 085 applies only the junction pairs that
  move. A rebuild would renumber every rowid, and the dry run showed 1656
  "changed" rows that were only renumbered.
- **D3. The parity check read the backup's columns** on its first run and
  checked nothing (0.0 s). It now reads the copy's: 13.9 s, 0 problems over
  all 1060 rows on the live copy.
- **D4. Keyless callers keep the old identity,** through a derived key of
  `(make, model, title)`.
- **D5. Past migrations' prose-keyed hooks stay** (`reconcile_255B_rows`,
  `backfill_row_applicability`): they run at their own schema, before
  `row_key` exists.
- **D6. Five pins moved with the change:**
  - 244D's index test, now `idx_known_issues_row_key`;
  - 244D's "no OR IGNORE" test, which reads every string constant now that
    the INSERT is built in pieces;
  - 255B's F129 pin, inverted;
  - 359's 072 test, which leaves out `row_key` (a later migration's
    column);
  - 209B's orphan list: `update_known_issue_by_key` (substrate for the
    content batch) and `unassigned_models` (test-infra).
- **The guards:** the edit guard refused heredoc writes of the fixture
  JSON into `tests/`, so they were written with the Write tool. Not
  changed.

**Checks:**
- the whole suite before these adjustments: 5 failed, 10786 passed, each
  failure one of D6;
- mutations 11/11 red (`380_mutate.out`). The first run had 9/11: P2 and
  J4 survived, so two tests were added (a seed edited after the approval;
  a junction whose kept rows sit at rowids a rewrite would change);
- 244G scanner 0 hits;
- floor 10769 → 10795.

`wholetree.sh --full` on the staged build found a sixth pin: 244U's running
orphan count, 117 → 119. The whole-suite run came before the two ORPHANS
entries existed (D6), so the count still read 117 then. Updated with its
reason.

### 2026-10-08 — The regression of record

`wholetree.sh --full` on `a119c28`: 4116 passed.

Regression of record: 10795 passed, 0 failed, 0 skipped, 0 errors at `a119c28` (28 min 11 s wall, `python -m pytest -n auto --dist load`, exit 0)

### 2026-10-08 — 085's dry run

The scope is generated from the seed (`380_scope.py`, committed with its
output):
- 1060 `known_issues` rows, each found by its prose identity, may change
  `row_key` only, and only to its seed key;
- `known_issue_models` loses 109 and gains 0;
- the schema adds the key index, removes the prose index, and rewrites the
  table.

## Bug-fix register

### Bug fix #1 — 2026-10-08

- **Issue:** 085's dry run crashed in `check_scope` with
  `ValueError: list.index(x): x not in list`. The scope's `"to"` names
  `row_key`, a column the migration adds.
- **Root cause:** `deploy.diff` kept only the old table's column list
  (`cols = cols or cols_b`). For a migration that adds a column:
  - a `to` on it could not be checked;
  - `exact()` zipped the old columns with the new rows, so the exact diff
    dropped the new column's values;
  - a changed row's moved fields left it out.

  It had not shown since Phase 357: no migration since added a column to a
  table that has rows. The parity check's first run (D3) was the same
  defect, met in the phase's own new code.
- **Fix:** `diff()` lines both sides up on the union of the two column
  lists (the new table's order first), with None where a side lacks a
  column (`_aligned`).
- **Files:** `.claude/skills/deploy/deploy.py`,
  `tests/test_phase380_deploy_new_column.py`, the deploy skill's
  `CHANGELOG.md`.
- **Verified:**
  - the new test gives 3 failed with the old `diff`, 3 passed with the fix;
  - 79 deploy tests pass (357, 358, 359, 378, 379, 380's parity).
