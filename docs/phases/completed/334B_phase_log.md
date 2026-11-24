# Phase 334B — phase log

**Status:** Complete

## 2026-11-22 — Step 0 and v1.0

The operator, 2026-11-22 (K128): "im taking all your recommendations, log
it all, prompt me when its time to continue and you give me the next prompt
for main". Among them: 334B is next for the app, its prompt read again
first. Then: "334B: finish the plan and hand me the prompt. Do not build it
yourself. I run app phases as a separate session that opens the PR in
moto-diag-mobile only; you keep the moto-diag record, same split as 303B.
Include in the prompt the small wording fix from 303B: the sign-in
screen's "Set an API key first." line."

Step 0 (`334B_step0.md`) read the app at `2f6739c` and this repository at
`b95f3d0`:
- nothing in the app calls the terms routes yet, and no web link is opened
  anywhere;
- 303B left the host, the client hook, the events module and the sign-out
  sequence to build on;
- the wording line is the home screen's "Authed smoke" block, line 574.
Classification: extension.

v1.0 (`334B_implementation.md`): the terms box rendered by `SignInHost`;
the 403 hook in `customFetch`, once per burst; agreeing, with the stale 422
read again; one sign-out shared with the home screen; the wording line;
and their tests. Row 334B is marked 🚧 in the same commit.

**Two changes from the prompt as first written,** made when it was read
again, with the reasons:
- **The box opens only when the server asks** (its 403), not at start-up.
  K128 turns the switch on after 334B and after 293's new terms version so
  that every user accepts once, and a start-up box while the switch is off
  would ask each user twice.
- **The 403 hook sits in `customFetch`,** not in `use()` middleware, as
  303B found: the middleware runs before the credential is added.

**Who builds and who records.** The build is the operator's own session in
`moto-diag-mobile` on `phase-334B-the-apps-terms-screen`. It opens its pull
request there only, and writes nothing in this repository. The advisor
keeps this log, the row and the close-out here, from the app's pull
request, as for 303B.

**Where these files live until the close-out.** On this repository's branch
of the same name, as 303B's did: the push guard refuses a phase's files on
master before its close-out (303B's log, 2026-11-20). Row 334B is marked 🚧
on master in its own commit, with its pin in
`tests/test_phase334_legal_texts.py`.

## 2026-11-22 — the build, the review and the merge

**The build.** The operator's own session built it from v1.0 on this
repository's branch (`919fb51`) and opened moto-diag-mobile's pull request
#12: five commits, `1297d0f`, `902fd4d`, `2de9962`, `1ff6193` and
`e71fd74`. Its description is the build's record, and v1.1 is written from
it, including three additions beyond the plan (v1.1, Deviations 1 to 3).

**The advisor's review,** at the operator's "Review it as you did PR 11
and tell me safe to merge or not":
- read against v1.0, item by item, and against the server's terms routes
  (`src/motodiag/api/routes/terms.py`), the exempt paths
  (`src/motodiag/auth/terms_acceptance.py`) and the two problem types
  (`src/motodiag/api/errors.py`);
- tsc, eslint and jest run again on the Mac, in a scratchpad clone at
  `e71fd74` with the same lockfile as the app checkout: tsc exit 0; eslint
  exit 0, 0 errors and 143 warnings, as on `main`; jest 109 suites, 1271
  tests passed. The pull request adds test files only and removes no line
  of a test;
- "Safe to merge: yes". One minor point for a later app session:
  `termsEvents.ts` sets its "pending" flag even when no listener is
  subscribed yet, so a refusal that arrived before the host's listener
  would keep the box shut until the app restarts. In practice the host
  subscribes before any reply can arrive.

**The merge.** The operator merged #12 as `58142e4` (moto-diag-mobile
`main`) at 20:30 UTC.

**The check on a phone has not run.** The box opens only when a server
refuses a call for unaccepted terms, so it needs a server with the terms
switch on. Live's switch stays off until after 293's new terms version
(K128). The check is open in the handoff.

## 2026-11-22 — the close-out

The operator: "PR 12 merged as 58142e4. Write the 334B record and give me
the sha when it is on master."

Master (`4649cb0`) was merged into this branch as `445e000`, with no
conflict. Row 334B and its pin had been changed the same way on both sides,
so the merge brought only the prompt and its README row. The whole-tree
command passed on it before the commit (2966 passed, 1 skipped).
`wholetree.sh --full` then ran on `445e000`: 5461 passed, 1 skipped, exit 0 (14 min 56 s).

Regression of record: 13086 passed, 0 failed, 49 skipped, 0 errors at `445e000` (36 min 50 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py
Skipped in the regression of record: [1] tests/test_phase390_space.py:327: bubblewrap is the desktop's
Line coverage of record: 88.48% at `445e000` (the pin is 88.00%)

This repository's code did not change in this phase: the regression of
record is master's code at the close-out, with this phase's documents. It
ran on battery.

The close-out: v1.1; row 334B ✅, and its pin in
`tests/test_phase334_legal_texts.py` moved to ✅; `implementation.md`
0.13.144 and its history row; the handoff
`docs/handoffs/2026-11-22_334B_closed.md`; the three phase files moved to
`completed/`.
