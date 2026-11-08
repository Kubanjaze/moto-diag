# Phase 398 — phase log: the two stalls at the Red Team's clear (F251, F252)

**Status:** In progress

**Started 2026-11-08** (UTC; 2026-11-07 evening EST) on the home desktop
(WSL2), the only writer, on `phase-398-the-two-stalls`. The prompt is
`docs/prompts/398_the_two_stalls.txt` (the operator's words, verbatim);
the operator's word is K67.

## 2026-11-08 01:14 UTC — start

- Master fetched at 01:14 at `f6aead1` (the prompt, row 398 🔲, K67 and
  row 12 of "Next, in order" already on it). `pgrep -x bwrap` empty: no
  fleet stage running.
- Read before planning: `CLAUDE.md`, `docs/decisions.md` (K65–K67),
  F251 and F252 in `docs/FOLLOWUPS.md`, the plan of record's "Changes to
  the order", and the code each finding names.
- F253 was the next free number (`next_f_number.sh`; no `### F25[3-9]`
  or `### F26` on any local or remote branch).
- Issue #54 and its hold untouched.
- Row 398 🚧 on the branch before Step 0.

## 2026-11-08 01:20 UTC — Step 0

`398_step0.md`. (a) A5 fails both refused logs and passes both hand
fixes; reading only lines that begin with the prefix reads the real
record in both refused logs (12186 at `c2b0767`; 12292 at `ca580f6`) and
changes what A5 reads in no closed log (the three bullets that do not
begin their line, 258–260, are on `A5_COMMAND_EXEMPT`). No reason not to
build F251's first fix. (b) The stop path, the due rule and the round
count are as F252 says; the real stop comments on #45 and #50 and the
label events (2 h 8 min, 9 h 13 min) re-measured. Auditing the other
readers of the prefix found Q4's counts read the old way: filed as
**F253**, left.

**Decision (recorded, not a stop):** the hold catches any `Stop` from the
record push, not only the gate's G6, since a failed push or a fast run
held for space leaves the same nothing-due state; the operator's step is
the same (fix, then take `needs-hands` off).

- `f8c7e62`: Step 0, v1.0, row 398 🚧, F253. wholetree fast passed first
  (2588 passed, 10 skipped, exit 0). Pushed on its own.

## 2026-11-08 01:25 UTC — the build

- **(a)** `closeout_check.regression_record`: `ln.startswith(PREFIX)`, the
  docstring saying why (F251).
- **(b)** `dispatcher.py`: in `stage_red_team`'s clear path, a `Stop` from
  `push_once` holds the run (`journal.hold`, `why: record`, the table, the
  round, the branch, the wording finding's number and rows) and
  `hold_record` escalates with `needs-hands` (the comment names the gate's
  reasons and what to do); `review:open` stays. A clear that pushes
  releases older record holds. `held_record` and `stage_red_record` as
  v1.0 says; when the kept table is already on the branch (the operator
  pushed it, as on #45 and #50), nothing is committed and `review:clear`
  is set. `held_for` skips record holds. `STAGE_RANK`, `resume`, and the
  kill point in `fixtures/resume/kill_points.json` (390's contract test
  gained 398's module).
- **Design choices (recorded):** the hold is said through `escalate`, so a
  stage cut off between the comment and the label is resumed like the
  Engineer's escalation (`not_resumable` reads the `escalate` step), and a
  resumed `stage_red_team` or `stage_red_record` whose label step is done
  returns at once. Its due rule reads list order, not times, because the
  verdict marker and the hold can share a second.
- **Fixtures:** `.claude/skills/closeout/fixtures/f251/`, the two refused
  logs byte for byte (sha256 `87d97cb5…` for 345's at `9555925`,
  `997b7233…` for 343's at `41370d2`), and `a5_bad_table_row_only.md`;
  `.claude/skills/fleet/fixtures/f252/stops.json`, the stop comments on #45
  and #50 as `gh issue view` returned them.
- `tests/test_phase398_two_stalls.py`: 17 passed (7.8 s).
- **Red on the old code** (master's `closeout_check.py` and `dispatcher.py`
  copied in, then restored): 14 failed, 3 passed. The 3 that pass are the
  known-bad controls, which must fail A5 under either rule (a refused log
  with its record lines removed, twice, and the exemption pins). The 4
  fixture replays of (a) and the 10 of (b) are red.
- `398_mutate.py`, 01:32–01:33: **8/8 mutations red**; output kept as
  `398_mutate.out`.
- `COLLECTED_TEST_FLOOR` 12397 to 12416, by a diff of collected ids against
  master at `f6aead1` (12398): +18 −0.
- wholetree fast at 01:36 (89 files): 2606 passed, 10 skipped, exit 0.
  `pgrep -x bwrap` empty before it.
