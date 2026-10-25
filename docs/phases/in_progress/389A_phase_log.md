# Phase 389A — 385's ROADMAP row — phase log

**Status:** 🚧 In progress
**Branch:** `phase-389A-385s-roadmap-row` (the Chief Engineer, Opus, in the fleet's fence: a fresh clone, no push)

---

### 2026-10-25 — Before the build: what was on the branch

The plan, `389A_implementation.md` v1.0, was committed before this session
by the Captain: `4eee8ab` (the plan), `a28256b` (round 1 revision),
`f13d170` (round 2 revision), approved by the Executive Officer on issue #14.
Step 0 is `ffe1691`. `93e1df0` merged `master` into the branch (389's fence
pins and guard fix), so this round starts from 389's close.

Read first: `docs/handoffs/2026-10-25_389_closed.md` (the newest, by
`git log -1 --name-only --format= -- docs/handoffs/`); rows 384–389A;
`ROADMAP_AUTHORITY.md` (385 and 389A are this repository's); F212, F216;
the 385 prompt.

What changed since the plan was written: 389 closed with the operator's
"Sandbox counts (Recommended)": a regression run inside the fleet's fence is
of record. The plan's section 4 and its anticipated stop assumed F216 made
that impossible here. The plan's own Tests section covers the case ("If it
unexpectedly passes with every skip pinned, that is a regression of record
and the merge recommendation says so as a change from this plan"), so if
the run here is of record, the close-out is done on the branch and the
change is a Deviation, not a fork.

The stage clone now has a local `master` (389's bug fix #3). The diff is
still taken against `origin/master`, as the plan says.

### 2026-10-25 — Row 385 added; row 389A's last sentence moved

- `grep -c '^| 385 |' docs/ROADMAP.md`: 0 before, 1 after.
- `roadmap_words.py 385 --check`: prints `87`, exit 0.
- `roadmap_words.py 389A --check`: prints `60`, exit 0.
- The 121-word control, run from `/fleet/run` on a string of 121 words, not
  on the repository: `roadmap_words.count(...)` returned `121`.
- `roadmap_check.py`: "ok: the ROADMAP, docs/phases/ and
  ROADMAP_AUTHORITY.md agree, and every close has its handoff", exit 0.
  R5 read the mobile copy inside the fence (no complaint).
- `roadmap_check.py --self-test`: R1–R7 each fire on the known-bad tree,
  the good tree passes; exit 0.
- `.venv/bin/python -m pytest tests/test_roadmap_continuity.py`: 28 passed,
  exit 0. (`python3 -m pytest` has no pytest on the host interpreter; the
  clone's `.venv` is the canonical one.)
- `git rev-parse origin/master`: `7ca42e0e515b7ac30e2c862e3db589b3fd6417f1`,
  389's merge. It descends from `6adffc5` (`git merge-base --is-ancestor`)
  and carries row 389A unchanged (the only ROADMAP change between them is
  row 389's close), so the expected shape holds.
- `git diff --stat origin/master -- docs/ROADMAP.md`:
  `1 file changed, 2 insertions(+), 1 deletion(-)`.
- The three row lines of `git diff origin/master -- docs/ROADMAP.md`,
  cut to 80 characters:
  ```
  +| 385 | The push token's own write | 🔲 | `device_tokens.last_seen_at` joins 
  -| 389A | 385's ROADMAP row | 🚧 | The fleet's first trial mission, a follow-o
  +| 389A | 385's ROADMAP row | 🚧 | The fleet's first trial mission, a follow-o
  ```
  Row 389A's "Step 0 next." became "Plan committed; row 385 added;
  awaiting the operator's merge."
- `wholetree.sh` (fast) before the row commit, run on its own: exit 0,
  "2085 passed, 10 skipped" (115.1 s wall).
