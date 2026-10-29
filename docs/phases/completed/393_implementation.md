# Phase 393 — The code itself gets checked

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-29 (v1.0 `a9f1212`)

---

## Goal

The rules for how a phase is built, recorded and closed are strong; nothing
checks how the code itself is written. The linter is configured and never
run, the type hints are written and never checked, nobody measures which
lines the tests run, and the Red Team and the Quartermaster read the plan,
the documents and the test results, not the code. The operator,
2026-10-27: "how do i make sure and maintain the quality of code thats been
written leading up to this point ?" (assessment:
https://claude.ai/artifact/8uRg5xkuDrJEzpnKBqRWgU).

After this phase:
1. ruff, mypy and coverage are pinned, and run in the fence with no network;
2. ruff's safe automatic fixes are applied across `src/` (not the
   migrations), with no product change;
3. two bugs are fixed: the PDF renderer's escape, shadowed by the HTML
   renderer's, and the customer-data erase's three handlers that swallow
   every error;
4. seven quality counts are pinned once, in `tests/support/quality_counts.py`,
   and a ratchet test holds each with every suite: up fails, down fails
   until the pin is lowered in the same commit; coverage may not fall;
5. every pull request the Quartermaster checks gets Q10 (lint and types per
   touched file), Q11 (85% of changed lines covered) and Q12 (no new or
   changed function over McCabe 20, no file past 100 KB, the files over it
   not growing), model-free in the fence;
6. the Red Team asks five questions of the code, each answered with a file
   and a line, two of them also checked by script;
7. a weekly page, "Code health, weekly", posted by the dispatcher on
   Monday 08:00 local, and a GitHub Actions workflow that runs the lint and
   type ratchet and `roadmap_check.py` on every pull request.

## The plan of record

Row 4 of "Next, in order" in `docs/reports/2026-10-12_plan_of_record.md`
(`| 4 | 393 | fleet | builder | nothing | 2026-10-27 · K54 |`), after 303
and before 348, built by a builder, on the operator's K54 in
`docs/decisions.md`: "Approved: Phase 393 as drafted, after 303 and before
348, built by a builder session; its numbers are mine." The prompt calls it
row 3; the table, read by `plan_order.py`, numbers it 4 (row 3 is 394,
inserted by K55 after the prompt was written). The first-shop phases it
protects are 348 and every phase after it: each is built under these
checks. A fleet-only phase: it unblocks 348, a Wave 1 phase whose row is
not ✅.

## Logic

1. **The tools, pinned** (`pyproject.toml`, the `dev` extra):
   `ruff==0.16.9`, `mypy==2.3.1`, `pytest-cov==7.1.0`, `coverage==7.14.1`.
   Changed-line coverage is a function of `scripts/code_quality.py`, not
   diff-cover (smaller, and no new dependency). `[tool.mypy]` checks
   `src/motodiag` with `ignore_missing_imports` and `no_site_packages`, so
   the count does not depend on which libraries an environment has
   installed (Step 0, S0-3: 284 errors with the dev venv's site-packages,
   204 without). `[tool.ruff.lint.mccabe] max-complexity = 20`, read only
   when C901 is selected on purpose. The fleet's venv gains the same pins.
2. **`scripts/code_quality.py`**, one implementation of every measure, used
   by the ratchet tests, the Quartermaster, the weekly page and
   `regression.sh`:
   - the seven counts: ruff findings (`ruff check src`), mypy errors,
     functions over McCabe 20 (`ruff check src --select C901`), files in
     `src/` over 100 KB (100,000 bytes, the prompt's KB), private helpers
     named `_money`, `_now` or `_now_iso` (by `ast`), `except Exception`
     handlers whose body is only `pass` (by `ast`), and total line coverage;
   - per file, for Q10: ruff findings and mypy errors, on a tree and on the
     base's `src/` unpacked beside it (`git archive`), both with the base's
     configuration when it has one, so a pull request cannot loosen the
     rules it is checked by;
   - changed lines (`git diff -U0 <base>...HEAD -- src`) against a coverage
     JSON, for Q11; complexity and size per changed function and file, for
     Q12;
   - `pr` (Q10 and Q12, JSON, run in the fence) and `coverage-gate`
     (the coverage line, and exit 1 below the pin).
3. **Clean-up first, no product change.** `ruff check src --fix` (safe
   fixes only) with `--extend-exclude` for `core/migrations.py` and
   `core/migration_*_rows.py`. Step 0 measured what it fixes: import order,
   unused imports and f-strings with no placeholder, and nothing else
   (S0-4); no removed import is imported by name anywhere (S0-5). E501 is
   left alone. Any `__init__.py` re-export ruff would remove is kept as an
   explicit re-export (`import x as x` or `__all__`). Integration-gap pins
   that move get their reason in `integration_gaps_counts.py`'s history.
4. **Bug fix #1, the PDF escape.** `reporting/renderers.py` defines
   `_escape` for reportlab's markup (&, <, >) and later rebinds the name with
   `from html import escape as _escape`, so the PDF renderer runs
   `html.escape`. The PDF renderer's function becomes `_markup_escape`; the
   HTML renderer's import becomes `_html_escape`, at the top of the file. A
   test builds a PDF from text holding `"`, `'`, `<`, `>` and `&` and reads
   its text back with pypdf; a second test proves the PDF renderer calls
   the markup escape and not `html.escape`.
5. **Bug fix #2, the erase.** `memory/erase.py`'s three handlers catch
   `sqlite3.OperationalError` and re-raise unless its message is "no such
   table". A test plants a locked table at each of the three statements and
   sees the erase raise, nothing reported as erased; its control: with the
   tables absent, the erase still works.
6. **The baseline and the ratchet.** `tests/support/quality_counts.py`
   holds one constant per count, with its history. 
   `tests/test_phase393_quality_ratchet.py` asserts each count against its
   constant: above it fails ("went up"), below it fails ("lower the pin in
   this commit"). Coverage: `regression.sh` runs the suite with
   `--cov=motodiag`, and `code_quality.py coverage-gate` turns a total below
   `COVERAGE_PERCENT` into a failed run, not of record; a test holds the
   gate and its wiring into `regression.sh`. A test fails on any other
   file in `tests/` assigning one of the seven names.
7. **The Quartermaster, Q10–Q12**, scripted, model-free, in the fence:
   - **Q10, lint and types:** no `src/` file the pull request touches has
     more ruff findings or mypy errors on the head than on the base;
   - **Q11, coverage:** lines added or changed in `src/` are at least 85%
     covered by the full run on the head (its coverage JSON);
   - **Q12, size:** no new or changed function over McCabe 20; no file in
     `src/` grows past 100 KB, and none already over it grows.
   A failure refuses, naming the file and the number. The dispatcher runs
   `code_quality.py pr` in a fenced check after the full run, with the
   base's copy of the script when the base has one; Q11 is read from the
   full run's coverage JSON in its run directory. Each has a hand-written
   known-bad fixture under `.claude/skills/fleet/fixtures/code_checks/`,
   seen red.
8. **The Red Team's code checklist.** The brief asks five questions of the
   diff, each answered `yes`, `no` or `not-applicable` with a file and line:
   1. is every new public function reached from the CLI or the API, or on
      the integration-gap allowlist with its reason;
   2. does it write a new private money, time or constant helper where one
      module should own it;
   3. does any new handler swallow an error without naming the one it
      expects;
   4. do the new tests check behaviour, or only that some text exists;
   5. if it touches `auth/`, `payments/`, `billing/`, `api/uploads.py` or
      `memory/erase.py`: what can a caller without the right role or tier
      now reach.
   A "no" with a file and line is a factual defect (K9): the verdict is
   back. Questions 2 and 3 are also scanned by script over the added lines
   (`red_team.code_scan`); a scripted "no" makes the verdict back whatever
   the model says. Known-bad: a planted diff with `except Exception: pass`
   in `payments/`.
9. **The weekly page.** `.claude/skills/fleet/quality_report.py`:
   `measure` (the seven counts on a tree, model-free; coverage from the
   newest "Line coverage of record" line in a phase log on that tree),
   `page` (each number, last week's, an arrow; on the first line, the
   counts that went the wrong way two weeks running), `--print` (measure
   here and print, posting nothing). The dispatcher, once a week on Monday
   from 08:00 local, measures master in the fence, keeps the record in
   `quality.jsonl`, posts the page as a comment on one pinned issue "Code
   health, weekly" opened by the fleet's account (never without it), and
   the next digest gains one line naming it.
10. **Off this PC.** `.github/workflows/quality.yml`, on every pull
    request: the ratchet's lint and type tests and `roadmap_check.py`. No
    live-data path, no secret. What cannot run there is named in the log.
11. **Documents.** `CLAUDE.md` rule 6 names the ratchet and the weekly page,
    with a dated change-log entry; the fleet skill's `SKILL.md` lists
    Q10–Q12 and the five questions; two findings, filed with the finding
    skill before v1.0: F234 (the remaining `except Exception` sites) and
    F235 (one module each for money and time).

## The change log's three newest entries

- **2026-10-26, R8: an operator paste block's `gh` names its repository.**
  Held by `tests/test_roadmap_continuity.py`
  (`.claude/skills/closeout/roadmap_check.py` R8). This phase's handoff
  blocks carry `-R Kubanjaze/moto-diag`.
- **2026-10-22, `fleet` joins the procedure folders.** Held by the folder's
  own tests (`tests/test_phase387_fleet_contract.py`); the table row is
  text. This phase extends the folder.
- **2026-10-20, rule 6: plain English to the operator.** No check: "Text
  only; no check holds it." This phase adds to rule 6 and writes the
  handoff's blocks to it.

## Rule-1 stops anticipated

- **A real fork:** none; the prompt fixes the checks and the numbers.
- **A threshold or a rule's definition:** the operator's numbers (K54) are
  applied as given; Step 0 measured that none of the three stop conditions
  holds (S0-8: 35 min 33 s for the fenced run with coverage; fast mode
  76.5 s; the counts identical twice). The stop stays live: if the full run with coverage passes
  45 minutes or fast mode outgrows `FAST_LIMIT_S`, the phase stops.
- **A test that cannot be made green:** none expected.
- **A login or a credential:** the weekly issue needs the fleet's account
  (`~/.config/motodiag/fleet-github.env`, present). The Actions workflow
  holds no secret.
- **A live-database change:** none; nothing here reads live.

**As built:** no stop was reached. The fenced run with coverage measured
35 min 33 s at Step 0; fast mode 64.6 s with the ratchet in it; the counts
held twice on one commit.

## Tests

- `tests/test_phase393_quality_ratchet.py`: the seven counts against their
  pins; the ratchet's two directions and coverage's one, on planted values
  and a planted tree; the coverage gate and its wiring; the one-pin rule.
- `tests/test_phase393_bug_fixes.py`: the PDF text round trip and the
  escape's identity; the erase refusing on a locked table at each of its
  three statements, and its control.
- `tests/test_phase393_code_checks.py`: Q10, Q11 and Q12 on their known-bad
  and good fixtures; the Quartermaster refusing on each, naming the file
  and the number; the dispatcher's fenced run.
- `tests/test_phase393_red_team_code.py`: the brief's five questions; the
  planted `except Exception: pass` in `payments/` made a back.
- `tests/test_phase393_quality_report.py`: `measure`, `page`, `--print`,
  the two-weeks-running line; the dispatcher's weekly stage (Monday 08:00,
  once a week, the pinned issue, the digest's line, nothing without the
  fleet's account).
- `tests/test_phase393_actions.py`: the workflow's shape (on pull_request,
  no secret, no live path).
- `docs/phases/in_progress/393_mutate.py`: every mutation red.
- `wholetree.sh` before each commit; `wholetree.sh --full`, then
  `regression.sh`, for the regression of record.

## Non-goals

- Wiring or deleting unreachable code; consolidating the money and time
  helpers; splitting the large files; fixing E501.
- Any migration, anything under `data/`, seed data, a split or an eval
  protocol, or live.
- Fixing the remaining `except Exception` sites (the finding).

## Planned items

- [x] the pins and the fleet venv (`a0bcabc`; the fleet's venv by hand, Step 0)
- [x] the safe fixes, and the integration-gap pins (`a0bcabc`)
- [x] bug fix #1 (`b0327b2`) and bug fix #2 (`f2149cb`)
- [x] `scripts/code_quality.py`, the baseline and the ratchet (`a0bcabc`, `68aa0e2`, `251a94b`)
- [x] the coverage gate in `regression.sh` (`68aa0e2`)
- [x] Q10–Q12 (`68aa0e2`)
- [x] the Red Team's five questions (`68aa0e2`)
- [x] the weekly page and its stage (`68aa0e2`)
- [x] the Actions workflow (`68aa0e2`; its first run passed)
- [x] the documents and the two findings (F234, F235 at `a9f1212`; the rest at `68aa0e2`)

## Deviations

1. **mypy without site-packages.** The prompt measured
   `mypy src/motodiag --ignore-missing-imports` (203 errors on its copy).
   With this venv's site-packages that command gives 284; the count moves
   with whatever libraries are installed, so this desktop, the fence and
   GitHub's runner would disagree. `[tool.mypy]` sets `no_site_packages`:
   204 at Step 0, the same everywhere (proven by the Actions run).
2. **Five files over 100 KB, not four.** `core/migration_086_rows.py`
   (165967 bytes) is over it too. Q12 holds all five alike. 100 KB is
   100,000 bytes, the prompt's own KB (572812 bytes was its "573 KB").
3. **The five questions are worded so "no" is the defect.** The prompt's
   2, 3 and 5 ask whether a defect is present ("Does it write a new private
   … helper"), while it says "A 'no' with a file and line is a factual
   defect". Each is reworded to ask whether the code is sound, keeping the
   prompt's subject (`red_team.QUESTIONS`).
4. **The weekly page's coverage is the regression of record's.** A full run
   is about 35 minutes in the fence; the page reads the newest "Line
   coverage of record" line in a phase log on master and names its commit,
   rather than running the suite each Monday.
5. **The first page is the first Monday after the stage comes up**
   (`quality_since`, as `quartermaster_since`): Monday 2026-11-02 once the
   service runs this code. The older dispatcher tests' clock crossed a
   Monday 08:00, and the stage must not fire for a week before it existed.
6. **The coverage pin is 87.5, and a rise is said, not failed.** The
   counts' ratchet fails a fall below the pin until the pin moves;
   coverage's only rule in the prompt is "it may not fall below its pin".
   The pin is code, so it is set before the regression of record and is
   Step 0's 87.597% cut to one decimal (`251a94b`). A total 0.5 points or
   more above it prints "raise COVERAGE_PERCENT to lock it in".
7. **Changed-line coverage is `code_quality.changed_coverage`**, not
   diff-cover: the diff's hunks against coverage's JSON. A changed file the
   JSON does not hold counts as missed.
8. **Q10 uses the base's rules and the base's script.** The prompt names
   the comparison; a pull request that changes `pyproject.toml` or
   `code_quality.py` could otherwise loosen what checks it. The base's
   `src/` is unpacked with `git archive`.
9. **Bug fix #1 had no effect a reader could see** (Step 0, S0-7): pypdf
   reads the five characters back exactly from a PDF built on master. The
   fix stands for the function; its behaviour test passes before and after,
   and the tests that fail on the old code are the function's (the spy and
   the name).
10. **Bug fix #2's locked table is planted at the statement**, by a
    connection wrapper raising SQLite's "database table is locked" error.
    A real second connection's lock makes the first, unhandled statement
    raise before any handler is reached (WAL lets readers through, and the
    memory delete takes the write lock first), so it cannot reach the
    three handlers. The control is real: both tables dropped.
11. **The integration-gap orphan pin moved 115 → 124.** Nine shop functions
    whose only reference was an unused import in `cli/shop.py`; listed as
    unwired-feature with the reason, not re-imported.
12. **Existing tests changed:** the Red Team's stand-in replies carry the
    checklist (`red_json`, `support/phase393.ALL_YES`) in 389, 390, 392 and
    394's files; 392's replay of #14's real round 3 adds it (that round
    predates the checklist); 391's two Quartermaster tests count the code
    check's command and stand in passing Q10–Q12; 388's pause test marks its
    crossed Monday done; 256's chokepoint test moves three line numbers up
    one (the import clean-up).
13. **The helper count is three exact names** (`_money`, `_now`, `_now_iso`),
    the prompt's own; the Red Team's scan reads a wider pattern for new ones
    (`_cents`, `_dollars`, `_utcnow`, `_fmt_money`).
14. **A failed weekly measure is tried again after an hour**, not every
    five-minute cycle.
15. **In the Actions run `roadmap_check` runs without the mobile repository**
    (its half of R2, R3 and R5 is not run there); the ratchet runs whole.
16. **A third bug fix** (the phase log): this phase's own test reached
    GitHub through `yeoman.facts`; found by the fence, which has no `gh`.

## Results

- **The baseline**, each count measured twice on `a38a36b` (Step 0, S0-6
  and S0-8), and the pins after the clean-up and the bug fixes:

  | count | Step 0, twice | pin |
  |---|---|---|
  | ruff findings | 1409, 1409 | 1108 |
  | mypy errors | 204, 204 | 202 |
  | functions over McCabe 20 | 25, 25 | 25 |
  | files in `src/` over 100 KB | 5, 5 | 5 |
  | private `_money`/`_now`/`_now_iso` | 19, 19 | 19 |
  | `except Exception: pass` | 25, 25 | 22 |
  | line coverage, fenced | 87.597%, 87.597% | 87.5 |

- **The safe fixes** (`a0bcabc`): 297 fixed in 182 files, import order,
  unused imports and f-strings with no placeholder; mypy unchanged. The full
  suite outside the fence on that tree: 11862 passed, 4 failed (F216's
  four), 33 skipped. ORPHAN_COUNT 115 → 124.
- **Bug fix #1** (`b0327b2`) and **#2** (`f2149cb`):
  `tests/test_phase393_bug_fixes.py`, 12 tests, 8 red on the old code.
  **Bug fix #3** (`0029289`): this phase's own digest test ran the real
  `gh`; the first fenced regression run's `wholetree.sh --full` caught it.
- **Q10–Q12** and the **five questions**, each with its known-bad case
  seen red: `tests/test_phase393_code_checks.py` (17),
  `tests/test_phase393_red_team_code.py` (14); `393_mutate.py`: 31/31 red.
- **The weekly page**: `tests/test_phase393_quality_report.py` (14);
  `quality_report.py --print` on master is in the handoff.
- **The Actions workflow's first run**:
  https://github.com/Kubanjaze/moto-diag/actions/runs/40962596948, success:
  the ratchet 25 passed, `roadmap_check` ok.
- **Fast mode** after the ratchet joined it: 79 files, 64.6 s, against
  `FAST_LIMIT_S` 285 s.
- **The regression of record** (the phase log carries its skip lines):
  "Regression of record: 11882 passed, 0 failed, 105 skipped, 0 errors at
  `0029289` (34 min 26 s wall, `python -m pytest -n auto --dist load
  --cov=motodiag`, exit 0) (run inside the fleet's fence)", after
  `wholetree.sh --full` (4911 passed, 36 skipped, 16 min 20 s). "Line
  coverage of record: 87.62% at `0029289` (the pin is 87.50%)". Without
  coverage, the same suite in the fence: 303's 35 min 1 s at `42f8651`,
  and this commit's in the phase log.

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-10-29 | the plan (`a9f1212`) |
| 1.1 | 2026-10-29 | built: Deviations and Results |
