# Phase 378 — Process clean-up 2 (K18–K25) — phase log

**Status:** 🚧 In progress (2026-10-07)
**Branch:** `phase-378` (Opus session, main checkout)

---

### 2026-10-07 — Opened

The operator's approval of the 2026-10-07 triage, in their own words in
this session, is `docs/prompts/378_process_cleanup_2.txt` (written into
the repository by this session). The triage was merged by the advisor
session as `481832c`; master was fast-forwarded to it before branching.
Row 378 went 🚧 before Step 0 (`12b21f6`); `roadmap_check.py` exit 0.

### 2026-10-07 — Step 0 and v1.0

`378_step0.md`: every code fact the triage states re-verifies. One adds
a limit. 370's minute failure was the product's rate limiter on the real
clock, not a test line, so K19's census cannot see that kind. No item
offers a fork (S0-3), so there is no stop. `378_implementation.md` v1.0.

### 2026-10-07 — The build

- **K18:** `deploy.py`'s `regression_problem`, called first in
  `preflight`. Fixtures `deploy/fixtures/k18/` (no line; a line A5 cannot
  read). 358's `env` records a regression line, so 357's, 358's and 359's
  apply tests still pass, 30 of them. The close-out skill states the one
  order, its sequence renumbered to eleven steps.
- **K19:** `tests/support/clock_census.py`, its census pinned at **8 lines
  in 6 files**:
  - the 7 of 375's 9 still in place (274's P&L pair was fixed);
  - **`test_phase281_intake_month.py:51`**, `now.year` and `now.month` on a
    name bound to the clock, which 375's search missed. Its file had
    already passed under libfaketime at all four moments.

  `clock_check.sh`: 137 passed at each of the four moments (2 min 16 s in
  all), exit 0.
- **K20:** B1 on its own file. `finding/fixtures/k20/`. The backend header
  says "(this file)".
- **K21:** the folds derived by a column parse, equal to the regex parse;
  the 18 are a floor, not a pin.
- **K22:** two labels and README.
- **K23, K26:** CLAUDE.md's rule 6, rule 4's order, a change-log entry.
- **K24:** the close-out skill's step 5.
- **K25:** `deploy.py verify-live`; check 8 opens live read-only and calls
  it. On real live, `verify-live 375` matches the approved diff, with
  integrity ok and foreign keys ok.
- **K27:** the deploy skill's text. `KEEP` is unchanged.
- Three skill changelogs.

**Decisions taken while building, not stops:**
- **D1. K18 uses verify_phase's check 2 scope** (`code_after_regression`),
  not the triage's "src/ or tests/". `.claude/` and `scripts/` are code
  too (F137), so the apply and the close-out cannot disagree. Mutation D4.
- **D2. K18 also refuses uncommitted code,** since the apply migrates with
  the working tree's `src/`.
- **D3. K19's census exempts a file importing `support.frozen_clock`,**
  the stated convention. It is pinned by (file, line text), as 377's is,
  so line numbers can move.
- **D4. `clock_check.sh` runs the pinned files and the two cleared ones**
  (`CLEARED`), and checks its own control at every moment. A clock that
  was not faked is exit 2, never a pass.
- **D5. `verify-live` prints a difference from the approved diff without
  failing,** since later work may change live. It fails on integrity or
  foreign keys.
- **D6. The working-rules index is not changed:** it indexes the workspace
  `CLAUDE.md` (`check_working_rules.py` reads `workspace-docs/CLAUDE.md`).
  v1.0 said it would be updated.

**The guards:**
- the edit guard refused a Python heredoc that edited `CLAUDE.md`,
  because its text named `tests/` and it wrote through a variable path. It
  "blocks what it cannot resolve". The edits were made with the Edit tool;
- `CHANGELOG.md` and the deploy skill were edited by scripts writing
  literal paths in `.claude/`, which the guard does not cover.

Neither guard was changed.

**Controls found while building:**
- the planted file caught a bare `.date()` the walk had missed;
- the WAL backup case was added, because the first "no file left" test
  could not fail on a database that was not in WAL mode;
- `shape_gaps` got a unit test, because no fixture writes a timestamp.

**Mutations: 18/18 red** (`378_mutate.out`). The first run had 20 entries:
- S3 ("a red moment does not fail the script") was dropped as framed
  wrong. Its check was the script itself, so the mutation made the check
  pass. The script's `rc=1` is held by S1, which is red;
- L2's text spanned a line break and was corrected.

244G's scanner: 0 hits on `tests/`, and its planted control is reported.
`COLLECTED_TEST_FLOOR` 10685 → 10723, by a diff of collected ids against
`481832c`: +37 in five new files, +2 −1 in `test_roadmap_continuity.py`.
