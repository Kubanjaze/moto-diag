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
