# Phase 391 — phase log: the Quartermaster, in shadow

**Status:** In progress
**Branch:** `phase-391-quartermaster`
**Prompt:** `docs/prompts/391_quartermaster.txt`

## 2026-10-26 — start, and the operator's two items first

- Read the plan: rows 389A to 390A, `ROADMAP_AUTHORITY.md` (391 is backend,
  205+), the newest handoff (`2026-10-26_390_closed.md`), `FOLLOWUPS.md`
  to F221, the fleet proposal's step 8 and its decisions table, the
  `fleet` skill and `dispatcher.py`, `captain.py`, `red_team.py`,
  `rank_call.py`, `journal.py`, `yeoman.py`, `verify_phase.sh`,
  `closeout_check.py`, `roadmap_check.py`, the push guard.
- 13:05:48: #14's model-free run on `e15b462` was running (`dispatcher.log`,
  two `bwrap` processes). Nothing of #14, PR #15 or their labels was
  touched; no test run of mine until it ended.
- **Item 1, row 390A** (the operator: "Close the row honestly per the
  ledger rule (what it proved, that it did not ship), with its handoff").
  Row 390A ✅, "Did not ship", and `docs/handoffs/2026-10-26_390A_closed.md`.
  Found while writing it: the branch `phase-390A-quartermaster-row` is no
  longer on GitHub (`git ls-remote origin 'refs/heads/phase-39*'` lists only
  `phase-390-resume`); `refs/pull/20/head` is `f987bf3`. The handoff and
  the row say so. The row is 91 words (`roadmap_words.py 390A --check`).
- **Item 2, F222** (the operator: "Make that a check (a close-out or
  fixture rule over handoffs' paste blocks), fix 390's handoff block in
  place, and file it as a finding"). Where it lives: `roadmap_check.py`,
  as R8, because R1–R7 already read the handoffs and run with every suite
  and on every push; a closeout A-rule would see only the phase being
  closed, and 390's block was added after its merge. Census first (a
  scratch script over every fenced block printing ALL GOOD): 45 handoffs,
  one block calling `gh` (390's); `docs/phases/`, one more (389's operator
  steps, whose `gh api` paths name the repository). R8 fired on 390's block
  and on nothing else; the good fixture first gave two false hits (an
  inline `GH_REPO=` and `cd … && gh` on one line), fixed by reading the
  text up to the `gh` word. `tests/test_roadmap_continuity.py`: 35 passed.
- **Guard blocks, two, both kept as they are:**
  - the edit guard refused `sed -i '1s/R1-R6/R1-R8/' tests/test_roadmap_continuity.py`
    ("`sed -i` edits a file in place, and is blocked wherever it points");
    done with the Edit tool;
  - the edit guard refused a mutation loop that copied the original back
    with `cp $D/orig.py` ("cannot tell where `cp` `$D/orig.py` writes");
    R8's mutations moved into this phase's `391_mutate.py`.
- **13:58:11, #14 failed its model-free run again** (`dispatcher.log`:
  "needs-admiral (engineer) … Regression run FAILED"): 11294 passed,
  3 failed, 105 skipped at `e15b462`, all three nested gates
  (`test_phase205_gate11`, `test_phase240_gate12` re-running gate 6;
  `test_phase258_gate14` re-running gate 13). The output
  (`runs/20261026_130548_check/run/check.txt`) prints no traceback. The
  gates' time limits on `e15b462` equal master's (900 s and 1800 s), so it
  is not 390's bug fix #3 missing. Read only; #14 is the operator's.
- `wholetree.sh` exit 0 (2210 passed, 10 skipped, 61 s), then two commits
  on `master`: `d3c0cc1` (R8, F222), `133dc26` (row 390A, row 391 🚧, the
  prompt), pushed `edd286c..133dc26`. Branch `phase-391-quartermaster`
  from `133dc26`.

## 2026-10-26 — Step 0

`391_step0.md`. The dry run's driver is kept as `391_dry_run.py` (it ran
from the session's scratch folder; its paths are that folder's).
- `verify_phase.sh 390A 44f846d f987bf3` in the fence, no model, no token:
  first with no virtualenv bound, when check 10 printed "No module named
  pytest" (a trap the reading of V10 must catch), then with the fleet's
  venv, 36 s, exit 1 from check 8.
- One Quartermaster call on PR #20: 61,300 tokens read, 1,093 written,
  3 turns, 11 s, $0.28 at list price. Verdict refuse, as the operator
  ruled; but it named checks of its own, so the brief lists the ids and
  the script refuses an unknown one.
- Decided, not stops (rule 1 does not reserve them):
  - **Q2, a Captain's hold refuses.** The proposal names "all 14 checks
    pass and the Red Team is clear"; the Captain's recommendation is the
    rank the operator reads first, and the one real refusal on record
    (PR #20) was on it. Stricter than the proposal, never looser.
  - **`quartermaster_since`.** The stage acts on an application of
    `merge:needs-review` made after it first ran on the machine. It keeps
    the new rank off #14 and PR #15, as the operator asked, and off older
    issues; applying the label again is the way in, as for every rank.
  - **An unchanged v1.0 section is not a stub** (S0-1's measurement).

## 2026-10-26 — v1.0, then the build

- **v1.0 committed** (`d2947f5`), after `plan_check.py 391` passed P1–P8
  (its first run failed P3 four times, counts in Step 0 with no command
  beside them, and P5 on the plan's own `data/` in Goal and Logic; both
  reworded). Pushed as a separate command: the push guard refused
  `git commit … && git push` in one ("This command runs `git commit` before
  `git push`"), as it should.
- **`quartermaster.py`, Q1–Q9 and the call**, tried on the real record
  before any test: 390 at its close-out (`48e7d2c`) passes Q1, Q6, Q7, Q9
  and **fails Q8 on R8**: its handoff's paste block, the one that failed
  for the operator today. So the Quartermaster would have refused 390's
  handoff as it shipped. PR #20's fence output fails V12 alone.
- **One shared reader**: `plan_check.classification`, P4's parse, now used
  by P4 and Q1.
- **The dispatcher**: `stage_quartermaster`, `quartermaster_due`,
  `quartermaster_since` (set by the first cycle), `Check.out`, the
  `resume()` branch, `STAGE_RANK`, `RANK_PREFIXES`, the sweep's text, the
  digest's verdicts. `yeoman.shadow` writes the digest's section.
- **389's and 390's tests carried on**: 389's walk-through now meets the
  Quartermaster after `merge:needs-review` (a refusal, no label moved);
  390's contract finds kill-point tests in 391's file too, and reads the
  CHANGELOG's 390 entry wherever it stands (it read only the newest).
- **A bug before any commit**: `_text` raised on a missing file (389's
  walk-through has no `implementation.md` at the root). Fixed in place;
  not a bug-fix entry, as no commit held it.
- **Guard blocks, three more, each kept as it is:**
  - the edit guard refused a Python script writing
    `tests/test_phase391_dispatcher.py` ("a Python script body writes
    tests/…"); done with Edit;
  - the edit guard refused a Python script writing `SKILL.md` because its
    text named `tests/`; done with Edit;
  - 244G's meta-guard (a test, in `wholetree.sh`) refused the contract
    test's raw-source asserts; they read `code_of` now.
- Tests: `test_phase391_quartermaster.py` 49, `test_phase391_dispatcher.py`
  15, `test_phase391_contract.py` 8; with 387–390's and the ledger's, 549
  passed. `wholetree.sh` exit 0 (2271 passed, 10 skipped).
