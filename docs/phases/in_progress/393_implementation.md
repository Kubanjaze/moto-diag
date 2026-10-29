# Phase 393 — The code itself gets checked

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-29

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

- [ ] the pins and the fleet venv
- [ ] the safe fixes, and the integration-gap pins
- [ ] bug fix #1 and bug fix #2
- [ ] `scripts/code_quality.py`, the baseline and the ratchet
- [ ] the coverage gate in `regression.sh`
- [ ] Q10–Q12
- [ ] the Red Team's five questions
- [ ] the weekly page and its stage
- [ ] the Actions workflow
- [ ] the documents and the two findings

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-10-29 | the plan |
