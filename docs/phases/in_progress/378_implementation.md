# Phase 378 — Process clean-up 2 (K18–K25)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-07

---

## Goal

Eight process items from the 2026-10-07 triage
(`docs/reports/2026-10-07_process_kinks_triage.md`), approved by the
operator on 2026-10-07 (`docs/prompts/378_process_cleanup_2.txt`):

> approved: 378 = K18–K25. K22: fix the README line too. K23: the standing
> lines move into checks or CLAUDE.md's "How a phase runs". K24: add the
> line to the close-out skill. K26: (a). K27: (a) now, (b) once the first
> shop's real data is in. K11: I'll decide by Oct 23.

No `src/`, no migration. Tooling, tests, skills and rule text, as 358 was.

## Logic

### K18. One deploy order, enforced

- **The order**, stated in the close-out skill's sequence (step 8
  rewritten):
  1. the regression of record;
  2. `deploy.py apply-live` from the branch, which reads the scope and the
     approved diff from `in_progress/`;
  3. the close-out commit, which moves the deploy files;
  4. the merge.
- **`apply-live` refuses**, before touching live, unless:
  - `docs/phases/in_progress/<phase>_phase_log.md` has a regression line
    that A5's parser reads (`closeout_check.regression_line`);
  - no path changed between that commit and HEAD is code, by
    `code_after_regression.is_code` (verify_phase's check 2; so
    `.claude/` and `scripts/` count, not only `src/` and `tests/`);
  - the working tree holds no uncommitted change to a code path, since
    `apply-live` migrates with the working tree's `src/`.
- **Fixtures:** `.claude/skills/deploy/fixtures/k18/`, hand-written logs:
  one with no regression line, one with a line A5 cannot parse, one good.
  The contract test builds the "behind a code change" case in a temporary
  git repository. 358's `env` fixture records a regression line, so the
  existing apply tests keep passing for the reason they test.

### K19. Tests that read the real clock: a census and a script

- **The census,** `tests/test_phase378_test_clock_census.py`, parses every
  `tests/**/*.py`; 244G's lesson is to parse, not grep.
  - **A real-clock read** is a call of `.now(…)`, `.utcnow()` or
    `.today()` on a name or attribute ending in `datetime` or `date`.
  - **A test line turns it into a day, month, year or minute** when the
    read, or a name assigned from one in the same file, meets one of:
    - `.date()`;
    - `.year`, `.month`, `.day`, `.hour` or `.minute`;
    - `.strftime(fmt)` whose literal format stops at a day, month, year
      or minute (no `%S`, `%f` or `%s`);
    - `.isoformat()` of `date.today()` or of a `.date()`;
    - a `[:n]` slice with n ≤ 16.
  - **Pinned** as (file, line text), as 377 pins `src/`. The census must
    equal the pin, so a new line fails and a line that goes must leave
    the pin in the same commit.
  - **Exempt by rule:** a file that imports `support.frozen_clock`. Its
    clock is the frozen one where the test sets it. That is the
    convention the census holds, and its limit.
  - **The control:** a planted file holding each shape must be reported,
    and a planted file using the frozen clock must not.
- **The script,** `.claude/skills/closeout/clock_check.sh`, runs the files
  the census pins plus every file holding a fixed line (the 275 and 274
  files), under libfaketime with `TZ=America/New_York` at 375's four
  moments:
  - 2026-10-31 21:00;
  - an ordinary 21:00;
  - New Year's Eve 21:00;
  - 00:30.

  It refuses when `faketime` is missing. It first checks its own control:
  Python's local clock and SQLite's `'now'` read the faked moment.
- **The close-out skill names it:** before a regression of record on a
  month's last evening, from 20:00 to midnight local, run the script; red
  is a clock-made failure to fix first.
- **The known limit:** a product's own clock is not a test line
  (370's 429 test, the rate limiter). The census cannot see it.

### K20. B1 per repository

- B1 compares the header's "highest assigned" with the highest entry in
  **its own file**. B2 keeps the union, since a citation may name a
  mobile finding. `next_f_number.sh` keeps allocating from the union.
- The backend header says "(this file)", as mobile's does, and points to
  `next_f_number.sh` for the next number.
- **Fixtures:** `fixtures/k20/`:
  - a sibling whose highest is above this file's must not fail B1;
  - a stale own header must fail;
  - the 255D contract test's docstring claim about "the same global max"
    is updated.

### K21. The fold pin, derived

- `TestR7OnTheRealLedger` derives the folds with a second, independent
  parse: split each table line on `|`, take the status cell and the notes
  cell's opening words. It requires:
  - equality with `roadmap_check`'s regex parse;
  - that the 18 folds closed by 2026-10-07 are among them (a number is
    never reused, so the set only grows);
  - that R7 passes on the real ledger.
- R7's planted fixtures (`roadmap_bad`: 266, 267, 268) and the
  reopened-261 test stay as the control. A batch close no longer edits
  this test.

### K22. Labels

- verify_phase's check 11 heading and the close-out SKILL description say
  eight artefacts.
- README lines 231–232 lose the removed clause and carry CLAUDE.md's
  2026-09-27 observation, at the operator's word.

### K23. The standing lines

Per `378_step0.md` S0-2:
- the lines enforced by a check go;
- the five that are rules with no check join CLAUDE.md's "How a phase
  runs" as one item, 6, "Standing practice":
  - "record a guard's block, never loosen it";
  - "run the whole-tree command on its own and read its exit code";
  - "raise the floor with the reason";
  - "a lost worker's record first";
  - "file a finding before citing it".
- K26's rule joins the same item (below).
- A dated change-log entry in CLAUDE.md, and the working-rules index line
  updated in workspace-docs in the same change, per its change-management
  rule.

### K24. Generators committed with their output

One line in the close-out skill's sequence: a script whose output ships
in `src/`, or whose output a migration loads, is committed in the phase
folder with it, before the close-out. Recorded in the skill's
`CHANGELOG.md`.

### K25. `deploy.py verify-live <phase>`, read-only

- It copies live through SQLite's backup API, and the phase's backup
  (named in its dry-run diff, in `in_progress/` or `completed/`) opened
  with `immutable=1`, into `data/deploy_scratch/`. It deletes both copies
  after.
- It prints:
  - schema objects added, removed and changed;
  - each table whose rows differ, with counts added, changed and removed;
  - whether that equals the approved exact diff, with a `<clock>` field
    matched by shape;
  - `PRAGMA integrity_check` and `foreign_key_check` on the live copy.
- Exit 1 on an integrity or foreign-key failure, or a missing diff or
  backup. A difference from the approved diff is printed, with exit 0,
  since later work may change live. Exit 2 when the phase has no deploy.
- verify_phase's check 8 calls it for a phase with a dry-run diff, and
  keeps the schema line for one without. Check 8 now opens live
  read-only.
- **The test:** fixture databases. A backup is left with no `-shm` or
  `-wal`, and live is unchanged. A planted out-of-diff row is reported,
  and a foreign-key break exits 1.

### K26 and K27 (the operator's calls), recorded

- **K26 (a):** CLAUDE.md's standing practice: a builder may install a
  Homebrew core tool a test needs, naming it in the phase log and the
  handoff.
- **K27:** the deploy skill's text records 5 kept now. Keep 5 plus the
  first backup of each week once the first shop's real data is in, the
  operator's (b), recorded with its trigger. `KEEP` does not change.

## Tests

- `tests/test_phase378_deploy_order.py` (K18)
- `tests/test_phase378_test_clock_census.py` (K19)
- `tests/test_phase378_verify_live.py` (K25)
- the finding contract, with K20's fixtures
- `test_roadmap_continuity.py`'s derived folds (K21)
- a label test (K22, K24): the close-out skill says eight artefacts, names
  `clock_check.sh` and the generator rule; README carries no removed
  clause
- mutations in `378_mutate.py`

## Non-goals

K11 (the operator's, by Oct 23); K28–K31 and K14 (parked or dropped);
any `src/` change; the mobile repository's own `finding_check`, which
needs a mobile session if it has one.

## Planned items

- [ ] K18 the order, the refusal, fixtures, tests
- [ ] K19 the census, the pin, the script, the skill line
- [ ] K20 B1 per file, the header, fixtures
- [ ] K21 the derived folds
- [ ] K22 the labels and README
- [ ] K23 CLAUDE.md's standing practice, change log, the index
- [ ] K24 the skill line
- [ ] K25 verify-live, check 8
- [ ] K26, K27 recorded
- [ ] mutations, the floor, the regression, the close-out, the handoff
