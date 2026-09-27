# Phase 358 — Process clean-up: one whole-tree command, one deploy script, and close-out checks in place of prose

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-27

## Goal

Turn the operator-approved kinks K1–K9 from the 2026-09-27 triage
(`docs/reports/2026-09-27_process_kinks_triage.md`) into tooling and checks.
Each check is seen red on a planted case before it is trusted.

Scope:
- tooling, tests and rule text only;
- no code under `src/`, no migration, and no change to the live database.

Step 0 is `358_step0.md`. The operator's decisions are recorded verbatim in
`358_phase_log.md`.

## Logic

### K1 — one whole-tree command, two modes

- **The command:** `.claude/skills/closeout/wholetree.sh [--full]`.
  - It is a thin wrapper, like `pre_push_guard.sh`, over `wholetree.py`.
- **Membership is computed by the Step 0 rule on every run**, not kept as a
  list.
  - A test file is whole-tree when it enumerates a repo directory, or
    imports or loads a helper that does.
  - A new whole-tree test joins on its own, which is the defect K1 exists
    to end. The counts are 25 and 72 today; the tests 358 adds will raise
    them.
- **The classes:**
  - *code and ledger:* enumerates `src/`, `tests/`, the ledger or git's
    file list;
  - *seed data:* enumerates only the seed JSON;
  - *outside:* enumerates only a library outside the repo.
- **Fast mode:**
  - runs the code-and-ledger class, minus gate files (`test_*gate*.py`,
    which re-run earlier gates) and the wheel build
    (`test_phase209_packaging.py`);
  - then runs `finding_check` over `completed/` and over `in_progress/`.
- **`--full`:** runs every census member, then the same two
  `finding_check` scopes.
- **How it runs:** in parallel (`-n auto --dist load`, as the regression
  of record does). It prints each mode's member count, the pass/fail
  line and the wall time.
- **`--full` writes a stamp,** `.git/motodiag_wholetree_full`, holding the
  index tree hash it tested. It writes one only when the run passed and
  the working tree equals the index.
- **Where it is enforced:**
  - *Every push:* the push guard runs fast mode. A failure blocks with
    exit 2.
  - *The regression of record:* `regression.sh` refuses to start unless
    the stamp names HEAD's tree.
  - *Commits in a content phase:* the guard also recognises `git commit`.
    When the commit would change `src/motodiag/knowledge/seed/**` or
    `src/motodiag/core/migrations.py`, it refuses unless the stamp names
    the tree being committed. For `-a` or `--all`, that tree is computed
    with a temporary index. The stamp check reads two hashes; it runs no
    tests.
- **Rule 3 in `CLAUDE.md`** names the command and its two modes, and
  nothing else. The list of four goes.

### K2 — one pin per count

- **The three counts get one home:** `tests/support/integration_gaps_counts.py`
  (`UNREACHABLE_COUNT`, `MODULE_ISLAND_COUNT`, `ORPHAN_COUNT`).
  - The trend comments of all six current pins merge there.
- **One assertion per count,** each in a file fast mode runs: 209B for
  unreachable, 244W for islands, 244U for orphans.
- **The other three pins are removed:** 244Y's two and 244Z's one. Each
  file that still wants the number imports it.
- **A guard in F124's shape,** `tests/test_phase358_one_pin_per_count.py`:
  - it scans `tests/` for `len(UNREACHABLE_MODULES|MODULE_ISLANDS|ORPHANS)`
    compared with an integer literal;
  - any hit fails;
  - its control plants a second literal pin in a copied file and must
    see it.

### K3 — the deploy script, in the repo

- **A new skill folder,** `.claude/skills/deploy/`:
  - `SKILL.md`, `CHANGELOG.md`, `deploy.py` and `fixtures/`;
  - a contract test, `tests/test_phase358_deploy_contract.py`.
- **It is built from 262's `deploy262.py`,** kept verbatim in Step 0's
  appendix.
- **The scope is data:** `docs/phases/in_progress/<phase>_deploy_scope.json`
  holds:
  - the tables allowed to change;
  - per table, the number of rows added;
  - the changed rows (template slug + locator), each with its allowed
    fields.
- **`deploy.py dryrun <phase>`:**
  - reads live's before-state, read-only;
  - backs up to `~/backups/motodiag/` and keeps 5;
  - migrates a copy of the backup and diffs every table by rowid;
  - runs the K4 census on the copy and checks the scope;
  - writes `docs/phases/in_progress/<phase>_dryrun_diff.md`, headed with the
    backup's path and sha256, the scope file's sha256 and the census count.
- **`deploy.py apply-live <phase>` refuses, before touching live, unless:**
  1. the diff file exists;
  2. it is tracked by git and unchanged from HEAD (the operator's
     condition);
  3. live equals the backup it names, every table and every row;
  4. a fresh dry run on a new copy of that backup stays in scope.

  Then it applies live, writes `<phase>_live_diff.md` and re-checks the
  scope.
- **Nothing under `/private/tmp`, and no scratch copies:** copies go to
  `data/deploy_scratch/` (gitignored), which the script cleans up.
- **Paths are arguments,** defaulting to the live paths, so tests use
  fixture databases. **358 never runs it against live.**

### K4 — one F158 census, and its ratchet

- **The census,** `scripts/f158_census.py`, is 262's `f158.py` made
  importable:
  - four patterns: "Phase N", "Track X", F-numbers and "this phase";
  - every text column of every table;
  - `--plant` is its own control.
- **The ratchet,** `tests/test_phase358_f158_ratchet.py`:
  - builds a database the way `db init` does (migrations, then the seed
    loaders);
  - the census count must equal `F158_CEILING`. Above it fails; below it
    fails with "lower the ceiling to N", so the count can only fall;
  - `workflow_templates` and `checklist_items` must carry 0 hits.
- **The ceiling is 75,** the count Step 0 measured on a built database. It
  is re-measured at the build, and its source is written beside it.
- **Controls:**
  - a planted "Phase 999" in a copy's `known_issues` row raises the
    count;
  - one in a checklist item trips the workflow rule.
- **What it cannot see:** operational rows (`shops`,
  `customer_notifications`), and live rows that lag the seed. The file
  says so.

### K5 — roadmap_check R7

- **The rule:** a row whose status is ✅ and whose body opens with
  "Folded into NNN" must name a phase with a row that is ✅ and carries
  `**CLOSED`.
- **`fixtures/roadmap_bad` gains two cases:** a fold into a number with
  no row, and a fold into a 🚧 row.
- **The exclusion control:** `fixtures/roadmap_good` gains a ✅ row whose
  prose says "folded". R7 must not fire on it.
- **The real ledger's eight folds pass.**

### K6 — A5 parses the regression line

- **A5 requires a line that parses as `regression.sh` prints it:**
  "Regression of record: N passed … at \`HASH\` (…, \`CMD\` …)", where
  CMD contains `pytest`.
- **The exemption is a pinned list** of the 10 phases Step 0 measured:
  255B, 255C, 255D, 257B, 257, 258, 259, 260, 353, 354.
  - Its control recomputes the set of closed logs that pass the old A5
    and fail the new one, and requires it to equal the list exactly.
- **The known-bad fixture:** a log with a hash and a count and no command.
  A5 must fire on it.

### K7 — A8: refute recorded without its checklist

- **The operator's words, applied literally:** "a log mentioning refute
  without a refute checklist fails."
  - A log that mentions refute must carry a `## Refuter pass` block, or
    one line saying no refute pass ran ("No refute pass ran …").
  - When the block is present, A8 also runs `refute_check`.
- **The exemption is a pinned list:** the 40 closed logs Step 0's
  measurement fails. Its control recomputes the set and requires
  equality.
- **Fixtures:**
  - bad: a prose refute with no block, in the shape of 259;
  - good: the block, the one-line none, and a log that never mentions
    refute.

### K8 — the Step 0 item

- **Where:** workspace `CLAUDE.md`, "Step 0 — Existing-code overlap
  audit". The item is added as number 6, in the operator's words: every
  action the row promises has a way for a user to do it, or the row is
  rewritten before v1.0.
- **The rest of the change,** in the same workspace-docs commit, pushed:
  - a dated change-log entry;
  - `claude/working-rules.md`'s Step 0 line updated;
  - `claude/check_working_rules.py` passing.

### K9 — at most three refute rounds

- **`SKILL.md` takes the operator's rule verbatim.**
- **The checklist gains one fifth column,** `round · kind · outcome`, for
  example `2 · factual · fixed` or `3 · wording · open F<n>`:
  - *kind* is wording, factual or citation;
  - *outcome* is kept, fixed, deleted or open.
- **`refute_check.py` gains:**
  - **C5:** no round above 3;
  - **C6:** no factual or citation defect still open;
  - **C7:** every open wording defect cites the same single F-number.
    `finding_check` resolves it.
- **The seven existing blocks have four columns.** Their phases (257,
  260, 261, 262, 264, 353, 354) are a pinned exemption from the column,
  with the same equality control.
- **Held as text only:** "delete rather than rewrite" and "rounds 2+ read
  the diff plus its surrounding sentences". No script can see either.

## Key Concepts

- **Membership by rule, not by list.** A hand-kept list of checks is what
  produced five red regressions in 257–260.
- **The hook fails open.** Step 0 measured it on 2026-09-27: a
  `PreToolUse` hook that runs past its timeout is killed, and the command
  runs. This was seen twice, with a block-now control and a pass control.
  A guard is only a guard while it finishes inside its timeout.
- **An exemption is a pinned list with an equality control.** It is a
  claim about history, and it is tested as one.

## Decisions

1. **K1: option 3, one command in two modes** (the operator,
   2026-09-27).
2. **K3: the apply refuses unless the diff file is committed and
   unchanged** (accepted by the operator).
3. **K6 and K7: exemptions are pinned lists of phase ids with an equality
   control** (the operator). K6's list is the 10; K7's list is its own
   measurement, 40.
4. **K9: one extra column** (the operator).
5. **Membership is recomputed by rule on every run,** so the counts will
   grow past 25 and 72 as 358 adds whole-tree tests.
6. **`--full`'s requirement is enforced at two points:** `regression.sh`
   reads the stamp, and the guard refuses a content commit without one.
   "Content" means the commit changes seed data or `migrations.py`.
7. **Open for the operator:** whether the guard enforces its own time
   limit, since the hook fails open. See Risks.

## Non-goals

- Fixing F158's rows, the starter templates, or the thermostat drift
  between live and seed. That is the content phase's work.
- Running `deploy.py` against live.
- K10–K17.
- Any change to what the regression of record runs.

## Planned items

1. K2: the counts module, the pin moves, the guard, and its control.
2. K1: `wholetree.py` and `wholetree.sh`, the guard wiring, the stamp in
   `regression.sh`, rule 3, and the controls.
3. K5: R7 and its fixtures.
4. K6 and K7: A5 and A8 with their fixtures and exemption controls.
5. K9: the refute column, C5–C7, `SKILL.md` and `CHANGELOG.md`.
6. K4: the census script, the ratchet, and its controls.
7. K3: the deploy skill, the fixture databases, and the refusal
   controls.
8. K8: the workspace-docs commit.
9. The change log in `CLAUDE.md`, each skill's `CHANGELOG.md`, and the
   test floor.

K2 goes first because K1's fourth plant, a wrong pinned count, needs the
canonical pin to sit in a file fast mode runs.

## Verification Checklist

- [ ] K1: a plant in one of the 47 excluded files. Fast mode passes and
      `--full` fails.
- [ ] K1: four plants, each in turn: a literal model ID in a test, a
      literal schema-head pin, a stale allowlist entry, and a wrong pinned
      count. Fast mode fails on each. Each plant is removed.
- [ ] K1: fast mode's wall time is under 120 s, measured twice.
- [ ] K1: the guard blocks a push on a planted failure, and passes clean.
- [ ] K1: `regression.sh` refuses without a stamp for HEAD.
- [ ] K1: the guard refuses a seed-touching commit without a stamp, and
      allows a docs-only commit.
- [ ] K2: the guard sees a planted second literal pin.
- [ ] K3: apply is refused with no diff file, with an uncommitted diff
      file, with a modified diff file, after live changed since the
      backup, and when a dry run leaves the scope. A clean fixture run
      applies.
- [ ] K4: the ratchet is red on a planted hit, on a planted workflow hit,
      and on a lowered count that the ceiling does not follow.
- [ ] K5: R7 fires on both bad fixtures, not on the prose row, and not on
      the real ledger.
- [ ] K6: A5 fires on the fixture. The exemption equals the 10.
- [ ] K7: A8 fires on the 259-shaped fixture and passes the one-line
      none. The exemption equals the 40.
- [ ] K9: C5, C6 and C7 each fire on a fixture. The exemption equals the
      7.
- [ ] K8: `check_working_rules.py` passes, and workspace-docs is pushed.
- [ ] Mutations: each new check is broken on purpose and seen red.
- [ ] The regression of record, through `regression.sh`, after
      `wholetree.sh --full`.

## Risks

- **The hook fails open.** A fast mode that grows past 120 s, or a slow
  machine (264's throttled run was ×2.3), makes the guard silently pass.
  Fast mode is about 30 s today, so ×2.3 is about 70 s.
  - **For the operator:** should `wholetree.py` stop itself at a time
    limit below the hook timeout (for example 100 s) and block the push
    with "the guard ran out of time", failing closed? The limit is a new
    threshold, so it is asked, not chosen.
- **Every push costs about 30 s,** and every content commit needs a
  `--full` of about 6 min.
- **`-n auto` inside the guard** starts a worker pool from a hook. This
  is measured at the build.
- **209's packaging skips in this shell.** It is in `--full` only; its
  skips are checked on the canonical path.
- **The seed ratchet builds a whole database** and may be slow. It lives
  in `--full`'s seed class by the census rule.
